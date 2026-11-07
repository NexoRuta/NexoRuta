"""Collect bounded infrastructure signals; run as root on each demo VM every minute."""

import argparse
from datetime import datetime, timezone
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import socket
import ssl
import subprocess
import time
import urllib.request

from vm_deploy import BASE, secret, token

PROJECT = "nexoruta-demo"
APPLICATIONS = ("api", "admin", "backoffice", "commerce", "tracking", "grafana",
                "worker-rabbit", "worker-kafka", "worker-push", "sql-proxy", "otel-collector", "alloy")
INFRASTRUCTURE = (
    "rabbitmq", "kafka", "mongo", "mailpit", "proxy", "prometheus", "prometheus-write-gateway",
    "gcp-metrics-collector", "loki", "tempo"
)
HTTP_PORTS = {"api": 18080, "admin": 18081, "backoffice": 18082,
              "commerce": 18083, "tracking": 18084, "monitor": 13000}
TRANSPORTS = ("RabbitMq", "Kafka", "PushFcm")
OUTBOX_STATES = ("Pendiente", "Procesando", "Error")
KAFKA_GROUPS = {
    "recovery": "nexoruta.password-recovery.mongo.v1",
    "board": "nexoruta-operational-board-v1",
    "history": "nexoruta-operational-history-v1",
}


def command(*arguments, timeout=10, env=None):
    return subprocess.run(arguments, check=True, capture_output=True, text=True,
                          timeout=timeout, env=env).stdout.strip()


def metadata(path):
    request = urllib.request.Request("http://metadata.google.internal/computeMetadata/v1/" + path,
                                     headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.read(4096).decode().strip()


def read_config(path):
    config = json.loads(path.read_text(encoding="utf-8"))
    if config["node"] not in ("a", "b") or not re.fullmatch(r"[a-z][a-z0-9-]{4,61}[a-z0-9]", config["project_id"]):
        raise ValueError("Invalid monitoring identity")
    address = ipaddress.ip_address(config["private_ip"])
    if not address.is_private and not address.is_loopback:
        raise ValueError("Monitoring probes require private addresses")
    host = config["services_host"]
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        expected = f"nexoruta-demo.southamerica-west1-a.c.{config['project_id']}.internal"
        if host != expected:
            raise ValueError("Monitoring shared-service DNS is not the configured node A")
        addresses = [ipaddress.ip_address(entry[4][0]) for entry in socket.getaddrinfo(host, None)]
    if not addresses or any(not address.is_private for address in addresses):
        raise ValueError("Monitoring shared services must resolve to private addresses")
    expected_redis = f"nexoruta-demo-b.{config['redis_zone']}.c.{config['project_id']}.internal"
    if (config["redis_zone"] not in ("southamerica-west1-b", "southamerica-west1-c")
            or config["redis_host"] != expected_redis or config["redis_port"] != 6378):
        raise ValueError("Redis monitoring must use the configured VM B DNS endpoint on TLS port 6378")
    redis_subnet = ipaddress.ip_network(config["redis_subnet_cidr"], strict=True)
    redis_addresses = {ipaddress.ip_address(entry[4][0]) for entry in
                       socket.getaddrinfo(config["redis_host"], config["redis_port"], type=socket.SOCK_STREAM)}
    if not redis_addresses or any(address not in redis_subnet for address in redis_addresses):
        raise ValueError("Redis monitoring DNS resolved outside the configured private subnet")
    for service, port in config.get("service_ports", {}).items():
        if service not in HTTP_PORTS or not isinstance(port, int) or not 1024 <= port <= 65535:
            raise ValueError("Invalid monitoring service port")
    return config


def expires_at(value):
    if isinstance(value, (int, float)):
        return float(value)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Session expiry needs an explicit timezone")
    return parsed.timestamp()


def kafka_lag(output, group):
    total, partitions = 0, 0
    for line in output.splitlines():
        columns = line.split()
        if not columns or columns[0] != group:
            continue
        if len(columns) < 6 or not columns[5].isdigit():
            raise ValueError("Kafka partition lag is unavailable")
        total += int(columns[5])
        partitions += 1
    if not partitions:
        raise ValueError("Kafka consumer group has no committed partition lag")
    return total


def rabbit_queues(output):
    values = {"rabbitmq_queue_messages_ready": 0.0, "rabbitmq_queue_messages_unacked": 0.0}
    found = set()
    for line in output.splitlines():
        match = re.fullmatch(r"(rabbitmq_queue_messages_ready|rabbitmq_queue_messages_unacked)(?:\{[^\n]*\})?\s+([0-9.eE+-]+)", line)
        if match:
            value = float(match[2])
            if not math.isfinite(value) or value < 0:
                raise ValueError("Invalid RabbitMQ queue sample")
            values[match[1]] += value
            found.add(match[1])
    if found != set(values):
        raise ValueError("RabbitMQ queue metrics are unavailable")
    return values


def _redis_response(reader):
    line = reader.readline(4096)
    if not line.endswith(b"\r\n"):
        raise ValueError("Malformed Redis response")
    prefix, payload = line[:1], line[1:-2]
    if prefix == b"-":
        raise RuntimeError("Redis rejected an authenticated monitoring operation")
    if prefix in (b"+", b":"):
        return payload
    if prefix != b"$":
        raise ValueError("Unsupported Redis response")
    length = int(payload)
    if length < 0:
        return None
    if length > 1_048_576:
        raise ValueError("Redis monitoring response exceeded its bound")
    data = reader.read(length + 2)
    if len(data) != length + 2 or not data.endswith(b"\r\n"):
        raise ValueError("Truncated Redis response")
    return data[:-2]


def redis_command(connection, reader, *parts):
    encoded = [part.encode("utf-8") if isinstance(part, str) else part for part in parts]
    connection.sendall(b"*" + str(len(encoded)).encode() + b"\r\n" + b"".join(
        b"$" + str(len(part)).encode() + b"\r\n" + part + b"\r\n" for part in encoded))
    return _redis_response(reader)


def redis_info_fields(payload):
    if not isinstance(payload, bytes):
        raise ValueError("Redis INFO response is unavailable")
    fields = {}
    for line in payload.decode("ascii", errors="strict").splitlines():
        if not line or line.startswith("#") or ":" not in line:
            continue
        name, value = line.split(":", 1)
        if name in {"used_memory", "used_memory_rss", "maxmemory", "evicted_keys", "connected_clients"}:
            if not value.isdigit():
                raise ValueError("Redis INFO contains an invalid numeric field")
            fields[name] = int(value)
    if set(fields) != {"used_memory", "used_memory_rss", "maxmemory", "evicted_keys", "connected_clients"}:
        raise ValueError("Redis INFO is missing bounded memory or client fields")
    return fields


def docker_bytes(value):
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(B|kB|MB|GB|KiB|MiB|GiB)\s*", value)
    if not match:
        raise ValueError("Docker reported an unsupported memory unit")
    factors = {"B": 1, "kB": 1000, "MB": 1000**2, "GB": 1000**3,
               "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}
    return int(float(match[1]) * factors[match[2]])


class Collector:
    def __init__(self, config):
        self.config = config
        self.resource = {"type": "gce_instance", "labels": {
            "project_id": config["project_id"], "instance_id": metadata("instance/id"),
            "zone": metadata("instance/zone").rsplit("/", 1)[-1]}}
        self.runtime = None
        self.runtime_loaded = 0.0
        self.redis_credentials = None
        self.redis_credentials_loaded = 0.0
        self.samples = []
        self.containers = {}

    def metric(self, name, value, **labels):
        if not math.isfinite(float(value)):
            raise ValueError("Monitoring sample must be finite")
        self.samples.append({"metric": {"type": "custom.googleapis.com/nexoruta/" + name,
                                         "labels": {"node": self.config["node"], **labels}},
                             "resource": self.resource, "metricKind": "GAUGE", "valueType": "DOUBLE",
                             "points": [{"interval": {"endTime": self.timestamp},
                                         "value": {"doubleValue": float(value)}}]})

    def attempt(self, name, operation):
        try:
            operation()
            self.metric("collection_success", 1, collector=name)
        except Exception as error:
            self.metric("collection_success", 0, collector=name)
            print(json.dumps({"collector": name, "error_type": type(error).__name__}), flush=True)

    def collect_containers(self):
        identifiers = command("docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=" + PROJECT).split()
        expected = (APPLICATIONS + (INFRASTRUCTURE if self.config["node"] == "a" else ())
                    + (("redis",) if self.config["node"] == "b" else ()))
        self.containers = {}
        if identifiers:
            if len(identifiers) > 40:
                raise ValueError("Unexpected container count")
            template = ('{"id":{{json .Id}},"service":{{json (index .Config.Labels "com.docker.compose.service")}},'
                        '"running":{{json .State.Running}},"oom":{{json .State.OOMKilled}},"restarts":{{json .RestartCount}}}')
            for line in command("docker", "inspect", "--format", template, *identifiers).splitlines():
                container = json.loads(line)
                if container["service"] in expected:
                    previous = self.containers.get(container["service"])
                    if previous is None or container["running"]:
                        self.containers[container["service"]] = container
        for service in expected:
            state = self.containers.get(service, {})
            self.metric("container_up", int(state.get("running", False)), service=service)
            self.metric("container_restarts", state.get("restarts", 0), service=service)
            self.metric("container_oom", int(state.get("oom", False)), service=service)

    def probe_services(self):
        for service, port in {**HTTP_PORTS, **self.config.get("service_ports", {})}.items():
            path = "/api/health" if service == "monitor" else "/health/ready"
            try:
                with urllib.request.urlopen(f"http://{self.config['private_ip']}:{port}{path}", timeout=3) as response:
                    healthy = response.status == 200
            except Exception:
                healthy = False
            self.metric("service_up", int(healthy), service=service)
        for service, port in (("rabbitmq", 5672), ("kafka", 19092), ("mongo", 27017), ("smtp", 1025)):
            try:
                with socket.create_connection((self.config["services_host"], port), timeout=2):
                    healthy = True
            except OSError:
                healthy = False
            self.metric("service_up", int(healthy), service=service + "_tcp")
        try:
            self.redis_exchange()
            redis_healthy = True
        except Exception:
            redis_healthy = False
        self.metric("service_up", int(redis_healthy), service="redis")

    def redis_identity(self):
        if self.redis_credentials is None or time.monotonic() - self.redis_credentials_loaded > 300:
            self.redis_credentials = secret(self.config["project_id"], "nexoruta-demo-redis")
            self.redis_credentials_loaded = time.monotonic()
        identity = self.redis_credentials
        if (not isinstance(identity, dict) or identity.get("dns_name") != self.config["redis_host"]
                or not isinstance(identity.get("password"), str) or len(identity["password"]) < 48
                or not isinstance(identity.get("ca_certificate"), str)):
            raise ValueError("The Redis monitoring identity is invalid")
        return identity

    def redis_exchange(self, *commands):
        identity = self.redis_identity()
        context = ssl.create_default_context(cadata=identity["ca_certificate"])
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        with socket.create_connection((self.config["redis_host"], self.config["redis_port"]), timeout=3) as raw:
            raw.settimeout(3)
            with context.wrap_socket(raw, server_hostname=self.config["redis_host"]) as connection:
                with connection.makefile("rb") as reader:
                    if redis_command(connection, reader, "AUTH", identity["password"]) != b"OK":
                        raise RuntimeError("Redis authentication failed")
                    if redis_command(connection, reader, "PING") != b"PONG":
                        raise RuntimeError("Redis PING failed")
                    return [redis_command(connection, reader, *parts) for parts in commands]

    def collect_redis(self):
        if self.config["node"] != "b":
            return
        values = redis_info_fields(self.redis_exchange(("INFO",))[0])
        self.metric("redis_memory_used_bytes", values["used_memory"])
        self.metric("redis_memory_rss_bytes", values["used_memory_rss"])
        self.metric("redis_maxmemory_bytes", values["maxmemory"])
        self.metric("redis_evicted_keys", values["evicted_keys"])
        self.metric("redis_connected_clients", values["connected_clients"])

        container = self.containers.get("redis")
        if not container or not container.get("running"):
            raise ValueError("The Redis container on node B is not running")
        output = command("docker", "stats", "--no-stream", "--format",
                         "{{.CPUPerc}}|{{.MemUsage}}|{{.PIDs}}", container["id"], timeout=10)
        fields = output.split("|")
        if len(fields) != 3 or not fields[0].endswith("%") or not fields[2].isdigit():
            raise ValueError("Docker Redis resource statistics are malformed")
        cpu_percent = float(fields[0][:-1])
        used, separator, limit = fields[1].partition("/")
        if not separator or not math.isfinite(cpu_percent) or cpu_percent < 0:
            raise ValueError("Docker Redis resource statistics are invalid")
        self.metric("redis_container_cpu_percent", cpu_percent)
        self.metric("redis_container_memory_bytes", docker_bytes(used))
        self.metric("redis_container_memory_limit_bytes", docker_bytes(limit))
        self.metric("redis_container_pids", int(fields[2]))

    def collect_outbox(self):
        if self.runtime is None or time.monotonic() - self.runtime_loaded > 300:
            self.runtime = secret(self.config["project_id"], "nexoruta-demo-runtime")
            self.runtime_loaded = time.monotonic()
        environment = {**os.environ, "PGPASSWORD": self.runtime["passwords"]["monitor"]}
        name = "nexoruta-monitor-sql-" + self.config["node"]
        try:
            output = command("docker", "run", "--rm", "--pull=never", "--name", name,
                             "--network", PROJECT + "_default", "-e", "PGPASSWORD", "postgres:18-alpine",
                             "psql", "-h", "sql-proxy", "-U", "nexoruta_monitor_runtime", "-d", "nexoruta",
                             "-v", "ON_ERROR_STOP=1", "-At", "-c",
                             "SELECT row_to_json(m) FROM nexoruta_hosting.outbox_metrics() m",
                             timeout=15, env=environment)
        finally:
            try:
                command("docker", "rm", "-f", name, timeout=5)
            except Exception:
                pass
        rows = {}
        for line in output.splitlines():
            row = json.loads(line)
            if row["transport"] in TRANSPORTS and row["state"] in OUTBOX_STATES:
                rows[(row["transport"], row["state"])] = row
        for transport in TRANSPORTS:
            for state in OUTBOX_STATES:
                row = rows.get((transport, state), {})
                self.metric("outbox_pending", row.get("messages", 0), transport=transport, status=state)
                self.metric("outbox_oldest_seconds", row.get("oldest_age_seconds", 0), transport=transport, status=state)

    def collect_kafka(self):
        for name, group in KAFKA_GROUPS.items():
            output = command("docker", "exec", self.containers["kafka"]["id"],
                             "/opt/kafka/bin/kafka-consumer-groups.sh", "--bootstrap-server", "kafka:9092",
                             "--group", group, "--describe", timeout=10)
            lag = kafka_lag(output, group)
            if name == "recovery":
                self.metric("kafka_lag", lag)
            else:
                self.metric("kafka_group_lag", lag, group=name)

    def collect_rabbit(self):
        with urllib.request.urlopen(f"http://{self.config['services_host']}:15692/metrics", timeout=5) as response:
            values = rabbit_queues(response.read(2 * 1024 * 1024).decode())
        self.metric("rabbit_queue_pending", values["rabbitmq_queue_messages_ready"])
        self.metric("rabbit_queue_unacknowledged", values["rabbitmq_queue_messages_unacked"])

    def collect_mongo(self):
        script = ('const u=encodeURIComponent(process.env.MONGO_INITDB_ROOT_USERNAME);'
                  'const p=encodeURIComponent(process.env.MONGO_INITDB_ROOT_PASSWORD);'
                  'const c=new Mongo("mongodb://"+u+":"+p+"@127.0.0.1:27017/admin");'
                  'if(c.getDB("admin").runCommand({ping:1}).ok!==1) quit(2);'
                  'const d=c.getDB("nexoruta");'
                  'const n=d.getCollectionNames().includes("operational_history_v1");'
                  'const s=n?d.runCommand({collStats:"operational_history_v1"}):{count:0,size:0};'
                  'print(JSON.stringify({count:s.count,size:s.size}));')
        output = command("docker", "exec", self.containers["mongo"]["id"], "mongosh", "--quiet", "--nodb", "--eval", script)
        values = json.loads(output)
        if (not isinstance(values, dict)
                or any(isinstance(values.get(name), bool) or not isinstance(values.get(name), (int, float))
                       or not math.isfinite(values[name]) or values[name] < 0
                       for name in ("count", "size"))):
            raise ValueError("MongoDB operational history metrics are unavailable")
        self.metric("service_up", 1, service="mongo_ping")
        self.metric("mongo_history_documents", values["count"])
        self.metric("mongo_history_data_bytes", values["size"])

    def collect(self):
        self.samples = []
        self.timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        self.attempt("containers", self.collect_containers)
        self.attempt("services", self.probe_services)
        if self.config["node"] == "b":
            self.attempt("redis", self.collect_redis)
        if self.config["node"] == "a":
            self.attempt("outbox", self.collect_outbox)
            self.attempt("rabbitmq", self.collect_rabbit)
            self.attempt("kafka", self.collect_kafka)
            self.attempt("mongo", self.collect_mongo)
        self.metric("session_remaining", max(0, expires_at(self.config["expires_at"]) - time.time()))
        self.metric("last_sample", time.time())
        current = BASE / "current-release"
        release = current.read_text().strip() if current.exists() else "none"
        if release != "none" and not re.fullmatch(r"release-[a-f0-9]{32}", release):
            raise ValueError("Invalid applied release")
        self.metric("applied_release", 1, release=release)
        return self.samples

    def publish(self):
        samples = self.collect()
        for offset in range(0, len(samples), 200):
            request = urllib.request.Request(
                f"https://monitoring.googleapis.com/v3/projects/{self.config['project_id']}/timeSeries",
                data=json.dumps({"timeSeries": samples[offset:offset + 200]}).encode(), method="POST",
                headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=15) as response:
                response.read(4096)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=BASE / "monitor.json")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    collector = None
    while True:
        started = time.monotonic()
        try:
            config = read_config(args.config)
            if collector is None or collector.config != config:
                collector = Collector(config)
            collector.publish()
        except Exception as error:
            print(json.dumps({"collector": "agent", "error_type": type(error).__name__}), flush=True)
            if args.once:
                raise SystemExit(1) from None
        if args.once:
            break
        time.sleep(max(1, 60 - (time.monotonic() - started)))


if __name__ == "__main__":
    main()
