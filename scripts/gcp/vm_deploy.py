"""Run as root on the VM; credentials come from its attached service account."""

import argparse
import base64
from contextlib import contextmanager
import hashlib
import io
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import shutil
import selectors
import socket
import subprocess
import tarfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

BASE = Path("/srv/nexoruta")
APPS = ("api", "worker-rabbit", "worker-kafka", "worker-push", "admin", "backoffice", "commerce", "tracking", "grafana")
SHARED = ("rabbitmq", "kafka", "mongo", "mailpit", "proxy")
RINGS = ("api", "admin", "backoffice", "commerce", "tracking")
LOAD_BALANCER_PROXIES = ("35.191.0.0/16", "130.211.0.0/22")
DIRECT_PORTS = {"api": 18080, "admin": 18081, "backoffice": 18082,
                "commerce": 18083, "tracking": 18084, "monitor": 13000}
MIGRATION_LOCK = 74200344171234
OPS_AGENT_CONFIG = Path("/etc/google-cloud-ops-agent/config.yaml")


def measure(timings, phase, operation):
    started = time.perf_counter()
    try:
        return operation()
    finally:
        timings[phase] = round((time.perf_counter() - started) * 1000)


def token():
    request = urllib.request.Request(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
        headers={"Metadata-Flavor": "Google"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)["access_token"]


def google(url):
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token()})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def secret(project, name):
    data = json.loads(google(f"https://secretmanager.googleapis.com/v1/projects/{project}/secrets/{name}/versions/latest:access"))
    return json.loads(base64.b64decode(data["payload"]["data"]))


def object_bytes(bucket, name):
    return google(f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{urllib.parse.quote(name, safe='')}?alt=media")


def extract(data, destination):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = archive.getmembers()
        targets = []
        seen = set()
        for member in members:
            relative = Path(member.name)
            if (not member.isfile() or relative.is_absolute() or not relative.parts
                    or any(part in (".", "..") for part in relative.parts)):
                raise ValueError("Unsafe release archive")
            target = destination.joinpath(*relative.parts)
            if member.name in seen or not target.resolve().is_relative_to(destination):
                raise ValueError("Unsafe release archive")
            seen.add(member.name)
            parent = target.parent
            while parent != destination:
                if parent.is_symlink():
                    raise ValueError("Unsafe release archive")
                parent = parent.parent
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise ValueError("Unsafe release archive")
            targets.append((member, target))

        # Extract regular files ourselves so deployment also works on Debian 12's
        # Python 3.11, whose tarfile.extractall() has no filter parameter.
        for member, target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.parent.resolve().is_relative_to(destination) or target.is_symlink():
                raise ValueError("Unsafe release archive")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError("Unsafe release archive")
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            with source, os.fdopen(os.open(target, flags, 0o600), "wb") as output:
                shutil.copyfileobj(source, output)
            target.chmod(member.mode & 0o755)
    # Grafana runs as UID 472; the release itself stays private under umask 077.
    provisioning = destination / "grafana/provisioning"
    if provisioning.exists():
        for directory in (destination / "grafana", provisioning, *provisioning.rglob("*")):
            if directory.is_dir():
                directory.chmod(0o755)
            elif directory.is_file():
                directory.chmod(0o644)
        dashboards = destination / "grafana/dashboards"
        if dashboards.exists():
            dashboards.chmod(0o755)
            for path in dashboards.rglob("*"):
                path.chmod(0o755 if path.is_dir() else 0o644)


def private_file(path, value):
    private_bytes(path, value.encode("utf-8"))


def private_bytes(path, value):
    temporary = path.with_name(path.name + ".tmp-" + str(os.getpid()))
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(value)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def env_line(key, value):
    value = str(value)
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError(f"Multiline configuration is not accepted for {key}")
    return key + "='" + value.replace("\\", "\\\\").replace("'", "\\'") + "'\n"


def connection(username, password):
    password = str(password)
    if any(character in password for character in ';"\r\n'):
        password = '"' + password.replace('"', '""') + '"'
    return f"Host=sql-proxy;Port=5432;Database=nexoruta;Username={username};Password={password};SSL Mode=Disable;Maximum Pool Size=20"


def bootstrap_config(runtime):
    passwords, ids = runtime["passwords"], runtime["organization_ids"]
    return {
        "PlatformInitialization": {"Enabled": True, "Email": "admin@nexoruta.test", "Password": passwords["admin"]},
        "AccesoInicial": {
            "OperadorId": ids["operator"], "ComercioId": ids["commerce"],
            "OperadorNombre": "Operador Demo Uruguay", "ComercioNombre": "Comercio Demo Uruguay",
            "OperadorUsuarioEmail": "operador@nexoruta.test", "UsuarioEmail": "comercio@nexoruta.test",
            "OperadorUsuarioPassword": passwords["operator"], "UsuarioPassword": passwords["commerce"],
            "OperadorRolCodigo": "propietario-operador", "ComercioRolCodigo": "propietario-comercio",
        },
        "Bootstrap": {"Roles": [
            {"Codigo": "propietario-operador", "Nombre": "Propietario Operador", "OperadorId": ids["operator"], "Permisos": []},
            {"Codigo": "propietario-comercio", "Nombre": "Propietario Comercio", "ComercioId": ids["commerce"], "Permisos": []},
        ]},
    }


def environment(runtime, integrations, images, mail_hash, hosting=None, node=None,
                private_ip=None, release=None, docker_subnets=()):
    passwords, keys, endpoints = runtime["passwords"], runtime["keys"], runtime["endpoints"]
    result = {
        "PROJECT_ID": runtime["project_id"], "SQL_CONNECTION_NAME": runtime["sql_connection"],
        "MIGRATOR_PASSWORD": passwords["migrator"], "API_DB_PASSWORD": passwords["api"],
        "WORKER_DB_PASSWORD": passwords["worker"], "BOOTSTRAP_DB_PASSWORD": passwords["bootstrap"],
        "MIGRATOR_CONNECTION": connection("postgres", passwords["migrator"]),
        "API_CONNECTION": connection("nexoruta_api_runtime", passwords["api"]),
        "WORKER_CONNECTION": connection("nexoruta_worker_runtime", passwords["worker"]),
        "BOOTSTRAP_CONNECTION": connection("nexoruta_bootstrap_runtime", passwords["bootstrap"]),
        "JWT_KEY": keys["jwt"], "TRACKING_KEY": keys["tracking"],
        "PUSH_KEY": keys["push"], "EVIDENCE_KEY": keys["evidence"],
        "RABBIT_PASSWORD": passwords["rabbit"], "MONGO_PASSWORD": passwords["mongo"],
        "MAIL_PASSWORD_HASH": mail_hash,
        "SMTP_HOST": integrations["smtp_host"], "SMTP_PORT": integrations["smtp_port"],
        "SMTP_SSL": str(integrations["smtp_ssl"]).lower(), "SMTP_FROM": integrations["smtp_from"],
        "SMTP_USERNAME": integrations.get("smtp_username", ""), "SMTP_PASSWORD": integrations.get("smtp_password", ""),
        "GEOAPIFY_API_KEY": integrations.get("geoapify_api_key", ""),
    }
    for name, url in endpoints.items():
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != "https" or parsed.username or parsed.port or parsed.path
                or parsed.query or parsed.fragment or not parsed.hostname):
            raise ValueError("Application endpoints must be HTTPS origins")
        result[f"{name.upper()}_URL"] = url
        result[f"{name.upper()}_HOST"] = parsed.hostname
    for name in ("api", "worker", "admin", "backoffice", "commerce", "tracking"):
        image = images[name]
        if not image.startswith(runtime["registry"] + "/" + name + "@sha256:") or not re.search(r"@sha256:[a-f0-9]{64}$", image):
            raise ValueError("Release image must be pinned to a digest in the expected repository")
        result[f"{name.upper()}_IMAGE"] = image
    if hosting is not None:
        if node not in ("a", "b") or not re.fullmatch(r"release-[a-f0-9]{32}", release or ""):
            raise ValueError("A shared deployment needs a valid node and release")
        for address in (private_ip, runtime["frontend_ip"]):
            ipaddress.IPv4Address(address)
        if not re.fullmatch(r"[A-Za-z0-9.-]+", runtime["services_host"]):
            raise ValueError("Invalid private services host")
        allowed_hosts = {urllib.parse.urlsplit(url).hostname for url in endpoints.values()}
        allowed_hosts.update((private_ip, "localhost", "127.0.0.1"))
        networks = [runtime["frontend_ip"] + "/32", *LOAD_BALANCER_PROXIES]
        for subnet in docker_subnets:
            network = ipaddress.ip_network(subnet, strict=False)
            if network.prefixlen == 0:
                raise ValueError("A default route cannot be a trusted proxy network")
            networks.append(str(network))
        emails = integrations.get("monitor_allowed_emails", [])
        if (not isinstance(emails, list) or not 1 <= len(emails) <= 50
                or any(not isinstance(email, str) or not re.fullmatch(
                    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", email) for email in emails)):
            raise ValueError("Google monitoring access requires an explicit email allowlist")
        email_literals = ",".join("'" + email.lower() + "'" for email in sorted(set(emails)))
        result.update({
            "NODE_NAME": node, "NODE_PRIVATE_IP": private_ip, "RELEASE_ID": release,
            "SERVICES_HOST": runtime["services_host"], "ALLOWED_HOSTS": ";".join(sorted(allowed_hosts)),
            "TRUSTED_NETWORKS": ",".join(networks),
            "MONITOR_DB_PASSWORD": passwords["monitor"], "GRAFANA_DB_PASSWORD": passwords["grafana"],
            "GRAFANA_SECRET_KEY": hosting["grafana_secret_key"],
            "HOSTING_CERT_PASSWORD": hosting["certificate_password"],
            "MONITOR_GOOGLE_CLIENT_ID": integrations["monitor_google_client_id"],
            "MONITOR_GOOGLE_CLIENT_SECRET": integrations["monitor_google_client_secret"],
            "MONITOR_ROLE_EXPRESSION": f"contains([{email_literals}], email) && 'Viewer' || 'None'",
        })
        if not all(result[name] for name in ("MONITOR_GOOGLE_CLIENT_ID", "MONITOR_GOOGLE_CLIENT_SECRET", "GRAFANA_SECRET_KEY")):
            raise ValueError("Monitoring authentication secrets must be configured")
        for ring in RINGS:
            password = passwords["keys_" + ring]
            result[f"KEYS_{ring.upper()}_PASSWORD"] = password
            result[f"KEYS_{ring.upper()}_CONNECTION"] = connection("nexoruta_keys_" + ring, password)
        if result["SMTP_HOST"] == "mailpit":
            result["SMTP_HOST"] = runtime["services_host"]
    return result


class Deploy:
    def __init__(self, directory, log):
        self.directory, self.log = directory, log
        self.lock_process = None
        self.timings_ms = {}

    def measure(self, phase, operation):
        return measure(self.timings_ms, phase, operation)

    def execute(self, *args, capture=False, **kwargs):
        result = subprocess.run(args, cwd=self.directory, check=True, text=True,
                                stdout=subprocess.PIPE if capture else self.log, stderr=self.log, **kwargs)
        return result.stdout.strip() if capture else None

    def compose(self, *args, **kwargs):
        self.check_lock()
        result = self.execute(*self.compose_arguments(*args), **kwargs)
        self.check_lock()
        return result

    def compose_arguments(self, *args):
        return ("docker", "compose", "--project-name", "nexoruta-demo", "--env-file", ".env", "-f", "compose.yaml", *args)

    def check_lock(self):
        if self.lock_process is not None and self.lock_process.poll() is not None:
            raise RuntimeError("The PostgreSQL deployment lock connection was lost")

    @contextmanager
    def migration_lock(self, deadline):
        remaining = deadline - time.time()
        if remaining <= 0:
            raise RuntimeError("The demo session expired before migration")
        name = "nexoruta-migration-lock"
        process = subprocess.Popen(self.compose_arguments(
            "run", "--rm", "--no-deps", "-T", "--name", name, "db-tools",
            "psql", "-X", "-qAt", "-v", "ON_ERROR_STOP=1"), cwd=self.directory,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, text=True)
        try:
            process.stdin.write(f"SET lock_timeout = '{min(60, max(1, int(remaining)))}s';\n"
                                f"SELECT pg_advisory_lock({MIGRATION_LOCK});\n"
                                "\\echo NEXORUTA_LOCK_ACQUIRED\n")
            process.stdin.flush()
            wait_until = time.monotonic() + min(75, remaining)
            buffer = b""
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while b"NEXORUTA_LOCK_ACQUIRED" not in buffer:
                    if process.poll() is not None or time.monotonic() >= wait_until:
                        raise RuntimeError("Unable to acquire the PostgreSQL deployment lock")
                    if selector.select(timeout=1):
                        chunk = os.read(process.stdout.fileno(), 4096)
                        if not chunk:
                            raise RuntimeError("The PostgreSQL deployment lock connection closed")
                        buffer += chunk
            self.lock_process = process
            yield
            self.check_lock()
        finally:
            self.lock_process = None
            try:
                if process.poll() is None:
                    process.communicate(f"SELECT pg_advisory_unlock({MIGRATION_LOCK});\n\\q\n", timeout=10)
            except (BrokenPipeError, subprocess.TimeoutExpired):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            finally:
                if process.stdin:
                    process.stdin.close()
                if process.stdout:
                    process.stdout.close()
                try:
                    self.execute("docker", "rm", "-f", name, timeout=10)
                except subprocess.SubprocessError:
                    pass

    def wait_sql(self):
        for attempt in range(60):
            try:
                self.compose("run", "--rm", "--no-deps", "db-tools", "pg_isready", "-h", "sql-proxy", "-U", "postgres", "-d", "nexoruta")
                break
            except subprocess.CalledProcessError:
                time.sleep(5)
        else:
            raise RuntimeError("Database connection did not become ready")

    def sql(self, query):
        return self.compose("run", "--rm", "--no-deps", "-T", "db-tools", "psql",
                            "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-c", query, capture=True)

    def migrate(self, deadline=None):
        self.measure("wait_for_sql", self.wait_sql)
        lock_started = time.perf_counter()
        with self.migration_lock(deadline if deadline is not None else time.time() + 600):
            self.timings_ms["migration_lock_wait"] = round((time.perf_counter() - lock_started) * 1000)
            self.measure("sql_preflight", lambda: self.compose("run", "--rm", "--no-deps", "db-tools", "psql", "-v", "ON_ERROR_STOP=1", "-f", "/deploy/sql/preflight.sql"))
            self.measure("schema_migrations", lambda: self.compose("run", "--rm", "--no-deps", "migrate"))
            def provision_roles_and_hosting():
                for name in ("runtime-roles.sql", "hosting.sql", "postflight.sql"):
                    self.compose("run", "--rm", "--no-deps", "db-tools", "psql", "-v", "ON_ERROR_STOP=1", "-f", "/deploy/sql/" + name)
            self.measure("provision_runtime_and_hosting", provision_roles_and_hosting)
            self.measure("import_department_catalog", lambda: self.compose("run", "--rm", "--no-deps", "migrate", "department-catalog-import"))
            self.measure("bootstrap_data", lambda: self.compose("run", "--rm", "--no-deps", "bootstrap"))


def metadata(path):
    request = urllib.request.Request("http://metadata.google.internal/computeMetadata/v1/" + path,
                                     headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read(4096).decode().strip()


def current_release():
    current = BASE / "current-release"
    if not current.exists():
        return None
    release = current.read_text().strip()
    if not re.fullmatch(r"release-[a-f0-9]{32}", release):
        raise ValueError("Invalid applied release marker")
    return release


def error_location(error):
    frames = traceback.extract_tb(error.__traceback__)
    if not frames:
        return ""
    frame = frames[-1]
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", frame.name) or not 1 <= frame.lineno <= 99999:
        return ""
    return f"{frame.name}:{frame.lineno}"


def direct_health(private_ip, attempts=18):
    for name, port in DIRECT_PORTS.items():
        path = "/api/health" if name == "monitor" else "/health/ready"
        for attempt in range(attempts):
            try:
                with urllib.request.urlopen(f"http://{private_ip}:{port}{path}", timeout=5) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError):
                pass
            if attempt + 1 < attempts:
                time.sleep(3)
        else:
            raise RuntimeError("Direct node health failed for " + name)


def bridge_subnets(deployment):
    try:
        networks = json.loads(deployment.execute("docker", "network", "inspect", "nexoruta-demo_default", capture=True))
    except subprocess.CalledProcessError:
        deployment.execute("docker", "network", "create", "--driver", "bridge",
                           "--label", "com.docker.compose.project=nexoruta-demo",
                           "--label", "com.docker.compose.network=default", "nexoruta-demo_default")
        networks = json.loads(deployment.execute("docker", "network", "inspect", "nexoruta-demo_default", capture=True))
    subnets = [config["Subnet"] for network in networks for config in network["IPAM"]["Config"] if config.get("Subnet")]
    if not subnets:
        raise RuntimeError("The Docker bridge has no trusted subnet")
    return subnets


def prepare(args, deployment, runtime, integrations, hosting, manifest, private_ip):
    def configure_and_pull():
        registry_host = runtime["registry"].split("/")[0]
        deployment.execute("docker", "login", registry_host, "--username", "oauth2accesstoken", "--password-stdin", input=token() + "\n")
        try:
            mail_hash = deployment.execute("docker", "run", "--rm", "-i", "caddy:2.10.2-alpine", "caddy", "hash-password",
                                           capture=True, input=runtime["passwords"]["mail"] + "\n")
            values = environment(runtime, integrations, manifest["images"], mail_hash, hosting,
                                 args.node, private_ip, args.release, bridge_subnets(deployment))
            private_file(deployment.directory / ".env", "".join(env_line(key, value) for key, value in values.items()))
            private_file(deployment.directory / "bootstrap.json", json.dumps(bootstrap_config(runtime)))
            certificate = base64.b64decode(hosting["certificate_pfx"], validate=True)
            if not certificate:
                raise ValueError("The shared Data Protection certificate is empty")
            private_bytes(deployment.directory / "hosting.pfx", certificate)
            deployment.compose("--profile", "administration", "--profile", "shared", "config", "--quiet")
            services = APPS + ("migrate", "bootstrap", "db-tools") + (SHARED if args.node == "a" else ())
            deployment.compose("--profile", "administration", "--profile", "shared", "pull", *services)
        finally:
            deployment.execute("docker", "logout", registry_host)
    deployment.measure("configure_validate_and_pull_images", configure_and_pull)

    def start_sql_and_shared_services():
        deployment.compose("up", "-d", "--wait", "--wait-timeout", "300", "sql-proxy")
        if args.node == "a":
            existing = deployment.execute("docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=nexoruta-demo", capture=True).split()
            existing_services = {}
            for identifier in existing:
                service = deployment.execute("docker", "inspect", "--format", '{{index .Config.Labels "com.docker.compose.service"}}', identifier, capture=True)
                if service in SHARED:
                    existing_services[service] = identifier
            for service, identifier in existing_services.items():
                deployment.execute("docker", "start", identifier)
            missing = tuple(service for service in SHARED if service not in existing_services)
            if missing:
                deployment.compose("--profile", "shared", "up", "-d", "--no-deps", "--wait", "--wait-timeout", "300", *missing)
            for topic in ("nexoruta.envios.creados.v1", "nexoruta.password-recovery.requested.v1"):
                deployment.compose("--profile", "shared", "exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh", "--bootstrap-server", "kafka:9092",
                                   "--create", "--if-not-exists", "--topic", topic, "--partitions", "1", "--replication-factor", "1")
    deployment.measure("start_sql_proxy_and_shared_services", start_sql_and_shared_services)
    def install_monitoring_configuration():
        deploy_dir = BASE / "deploy"
        deploy_dir.mkdir(exist_ok=True)
        private_bytes(deploy_dir / "monitor_agent.py", (deployment.directory / "monitor_agent.py").read_bytes())
        services_ip = socket.gethostbyname(runtime["services_host"])
        if not ipaddress.IPv4Address(services_ip).is_private:
            raise ValueError("Monitoring services must resolve to a private address")
        private_file(BASE / "monitor.json", json.dumps({"project_id": runtime["project_id"], "node": args.node,
                     "services_host": services_ip, "private_ip": private_ip, "expires_at": args.deadline}))
        if OPS_AGENT_CONFIG.parent.exists():
            private_bytes(OPS_AGENT_CONFIG, (deployment.directory / "monitoring/ops-agent.yaml").read_bytes())
            try:
                deployment.execute("systemctl", "is-active", "--quiet", "google-cloud-ops-agent")
            except subprocess.CalledProcessError:
                pass
            else:
                deployment.execute("systemctl", "restart", "google-cloud-ops-agent")
        deployment.execute("systemctl", "restart", "nexoruta-monitor.service")
        private_file(deployment.directory / "prepared.json", json.dumps({"node": args.node, "deadline": args.deadline}))
    deployment.measure("install_monitoring_and_mark_prepared", install_monitoring_configuration)
    return {}


def apply(args, deployment, private_ip):
    try:
        deployment.measure("start_and_wait_for_apps", lambda: deployment.compose("up", "-d", "--no-deps", "--force-recreate", "--wait", "--wait-timeout", "300", *APPS))
        deployment.measure("direct_health_checks", lambda: direct_health(private_ip))
        private_file(BASE / "current-release", args.release + "\n")
    except Exception:
        print(json.dumps({"stage": "apply", "node": args.node, "release": args.release,
                          "status": "failed"}))
        raise RuntimeError("Node application update failed; it remains out of the load balancer") from None


def smoke(runtime, check_accounts=True):
    endpoints = runtime["endpoints"]
    for name in ("api", "admin", "backoffice", "commerce", "tracking", "monitor"):
        path = "/health/ready" if name in ("api", "tracking") else "/ingresar"
        if name == "monitor":
            path = "/api/health"
        url = endpoints[name] + path
        for attempt in range(60):
            try:
                with urllib.request.urlopen(url, timeout=10) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Unexpected HTTP status for {name}")
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(5)
        else:
            raise RuntimeError(f"HTTPS smoke test failed: {name}")
    try:
        urllib.request.urlopen(endpoints["monitor"] + "/api/search?query=nexoruta", timeout=10)
    except urllib.error.HTTPError as error:
        if error.code != 401:
            raise RuntimeError("The monitoring dashboard API must require Google authentication") from None
    else:
        raise RuntimeError("The monitoring dashboard API is publicly accessible")
    try:
        urllib.request.urlopen(endpoints["mail"] + "/", timeout=10)
    except urllib.error.HTTPError as error:
        if error.code != 401:
            raise RuntimeError("The demo mail inbox must remain password-protected") from None
    else:
        raise RuntimeError("The demo mail inbox is publicly accessible")
    # A database-backed login exercises the migrated schema and runtime RLS role.
    accounts = (("admin", "admin@nexoruta.test"), ("operator", "operador@nexoruta.test"), ("commerce", "comercio@nexoruta.test")) if check_accounts else ()
    for role, email in accounts:
        payload = json.dumps({"email": email, "password": runtime["passwords"][role]}).encode()
        request = urllib.request.Request(endpoints["api"] + "/api/auth/login", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"Bootstrap login failed: {role}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--stage", choices=("prepare", "stop", "migrate", "apply", "verify"), required=True)
    parser.add_argument("--node", choices=("a", "b"), required=True)
    parser.add_argument("--deadline", type=float, required=True)
    args = parser.parse_args()
    timings = {}
    try:
        result = run_stage(args, timings)
        print(json.dumps({"release": args.release, "node": args.node, "stage": args.stage,
                          "status": "healthy", **result, "timings_ms": timings}))
    except Exception as error:
        print(json.dumps({"release": args.release, "node": args.node, "stage": args.stage,
                          "status": "failed", "error_type": type(error).__name__,
                          "error_location": error_location(error), "timings_ms": timings}))
        raise SystemExit(1) from None


def run_stage(args, timings=None):
    timings = timings if timings is not None else {}
    started = time.perf_counter()
    try:
        return _run_stage(args, timings)
    finally:
        timings["stage_total"] = round((time.perf_counter() - started) * 1000)


def _run_stage(args, timings):
    import fcntl
    if not re.fullmatch(r"release-[a-f0-9]{32}", args.release):
        raise ValueError("Invalid release ID")
    if not math.isfinite(args.deadline) or args.deadline <= time.time():
        raise RuntimeError("The demo session has expired")
    if args.stage == "migrate" and args.node != "a":
        raise ValueError("Only node A may run shared migrations")
    os.umask(0o077)
    BASE.mkdir(exist_ok=True)
    with open("/run/lock/nexoruta-deploy.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        directory = BASE / "releases" / args.release
        manifest = None
        if args.stage == "prepare":
            manifest = measure(timings, "download_manifest", lambda: json.loads(object_bytes(args.bucket, f"releases/{args.release}/manifest.json")))
            if manifest["release"] != args.release:
                raise ValueError("Manifest/release mismatch")
            bundle = measure(timings, "download_bundle", lambda: object_bytes(args.bucket, f"releases/{args.release}/bundle.tar.gz"))
            if hashlib.sha256(bundle).hexdigest() != manifest["bundle_sha256"]:
                raise ValueError("Bundle checksum mismatch")
            directory.mkdir(parents=True, exist_ok=True)
            measure(timings, "verify_and_extract_bundle", lambda: extract(bundle, directory))
        else:
            prepared = json.loads((directory / "prepared.json").read_text(encoding="utf-8"))
            if prepared != {"node": args.node, "deadline": args.deadline}:
                raise RuntimeError("The node was prepared for a different session")
        project = measure(timings, "read_vm_project_identity", lambda: metadata("project/project-id"))
        private_ip = measure(timings, "read_vm_private_ip", lambda: metadata("instance/network-interfaces/0/ip"))
        runtime = measure(timings, "read_runtime_secret", lambda: secret(project, "nexoruta-demo-runtime"))
        ipaddress.IPv4Address(private_ip)
        identity = runtime["nodes"][args.node]
        if (runtime["project_id"] != project or identity["name"] != metadata("instance/name")
                or identity["zone"] != metadata("instance/zone").rsplit("/", 1)[-1]):
            raise RuntimeError("The requested node does not match this VM identity")
        log_dir = BASE / "logs"
        log_dir.mkdir(exist_ok=True)
        with open(log_dir / f"{args.release}.log", "a") as log:
            deployment = Deploy(directory, log)
            deployment.timings_ms = timings
            result = {}
            if args.stage == "prepare":
                integrations = measure(timings, "read_integrations_secret", lambda: secret(project, "nexoruta-demo-integrations"))
                hosting = measure(timings, "read_hosting_secret", lambda: secret(project, "nexoruta-demo-hosting"))
                result = prepare(args, deployment, runtime, integrations, hosting, manifest, private_ip)
            elif args.stage == "stop":
                deployment.measure("stop_apps", lambda: deployment.compose("stop", *APPS))
            elif args.stage == "migrate":
                deployment.migrate(args.deadline)
            elif args.stage == "apply":
                apply(args, deployment, private_ip)
            else:
                deployment.measure("direct_health_checks", lambda: direct_health(private_ip))
                deployment.measure("public_https_and_login_smoke", lambda: smoke(runtime))
                result = {"endpoints": runtime["endpoints"]}
            return result


if __name__ == "__main__":
    main()
