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
import subprocess
import time
import urllib.request

from vm_deploy import BASE, secret, token

PROJECT = "nexoruta-demo"
APPLICATIONS = ("api", "admin", "backoffice", "commerce", "tracking", "grafana",
                "worker-rabbit", "worker-kafka", "worker-push", "sql-proxy")
INFRASTRUCTURE = ("rabbitmq", "kafka", "mongo", "mailpit", "proxy")
HTTP_PORTS = {"api": 18080, "admin": 18081, "backoffice": 18082,
              "commerce": 18083, "tracking": 18084, "monitor": 13000}
TRANSPORTS = ("RabbitMq", "Kafka", "PushFcm")
OUTBOX_STATES = ("Pendiente", "Procesando", "Error")
KAFKA_GROUP = "nexoruta.password-recovery.mongo.v1"


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


def kafka_lag(output):
    total, partitions = 0, 0
    for line in output.splitlines():
        columns = line.split()
        if not columns or columns[0] != KAFKA_GROUP:
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


class Collector:
    def __init__(self, config):
        self.config = config
        self.resource = {"type": "gce_instance", "labels": {
            "project_id": config["project_id"], "instance_id": metadata("instance/id"),
            "zone": metadata("instance/zone").rsplit("/", 1)[-1]}}
        self.runtime = None
        self.runtime_loaded = 0.0
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
        expected = APPLICATIONS + (INFRASTRUCTURE if self.config["node"] == "a" else ())
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
        output = command("docker", "exec", self.containers["kafka"]["id"],
                         "/opt/kafka/bin/kafka-consumer-groups.sh", "--bootstrap-server", "kafka:9092",
                         "--group", KAFKA_GROUP, "--describe", timeout=10)
        self.metric("kafka_lag", kafka_lag(output))

    def collect_rabbit(self):
        with urllib.request.urlopen(f"http://{self.config['services_host']}:15692/metrics", timeout=5) as response:
            values = rabbit_queues(response.read(2 * 1024 * 1024).decode())
        self.metric("rabbit_queue_pending", values["rabbitmq_queue_messages_ready"])
        self.metric("rabbit_queue_unacknowledged", values["rabbitmq_queue_messages_unacked"])

    def collect_mongo(self):
        script = ('const u=encodeURIComponent(process.env.MONGO_INITDB_ROOT_USERNAME);'
                  'const p=encodeURIComponent(process.env.MONGO_INITDB_ROOT_PASSWORD);'
                  'const c=new Mongo("mongodb://"+u+":"+p+"@127.0.0.1:27017/admin");'
                  'quit(c.getDB("admin").runCommand({ping:1}).ok===1?0:1);')
        command("docker", "exec", self.containers["mongo"]["id"], "mongosh", "--quiet", "--nodb", "--eval", script)
        self.metric("service_up", 1, service="mongo_ping")

    def collect(self):
        self.samples = []
        self.timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        self.attempt("containers", self.collect_containers)
        self.attempt("services", self.probe_services)
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
