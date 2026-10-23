"""Run as root on the VM; credentials come from its attached service account."""

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = Path("/srv/nexoruta")
APPS = ("api", "worker-rabbit", "worker-kafka", "worker-push", "admin", "backoffice", "commerce", "tracking", "proxy")


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
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile() or not (destination / member.name).resolve().is_relative_to(destination.resolve()):
                raise ValueError("Unsafe release archive")
        archive.extractall(destination)


def private_file(path, value):
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)


def env_line(key, value):
    value = str(value)
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError(f"Multiline configuration is not accepted for {key}")
    return key + "='" + value.replace("\\", "\\\\").replace("'", "\\'") + "'\n"


def connection(username, password):
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


def environment(runtime, integrations, images, mail_hash):
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
        if parsed.scheme != "https" or parsed.username or parsed.port or parsed.path:
            raise ValueError("Application endpoints must be HTTPS origins")
        result[f"{name.upper()}_URL"] = url
        result[f"{name.upper()}_HOST"] = parsed.hostname
    for name in ("api", "worker", "admin", "backoffice", "commerce", "tracking"):
        image = images[name]
        if not image.startswith(runtime["registry"] + "/" + name + "@sha256:") or not re.search(r"@sha256:[a-f0-9]{64}$", image):
            raise ValueError("Release image must be pinned to a digest in the expected repository")
        result[f"{name.upper()}_IMAGE"] = image
    return result


class Deploy:
    def __init__(self, directory, log):
        self.directory, self.log = directory, log

    def execute(self, *args, capture=False, **kwargs):
        result = subprocess.run(args, cwd=self.directory, check=True, text=True,
                                stdout=subprocess.PIPE if capture else self.log, stderr=self.log, **kwargs)
        return result.stdout.strip() if capture else None

    def compose(self, *args, **kwargs):
        return self.execute("docker", "compose", "--project-name", "nexoruta-demo", "--env-file", ".env", "-f", "compose.yaml", *args, **kwargs)

    def migrate(self):
        for attempt in range(60):
            try:
                self.compose("run", "--rm", "--no-deps", "db-tools", "pg_isready", "-h", "sql-proxy", "-U", "postgres", "-d", "nexoruta")
                break
            except subprocess.CalledProcessError:
                time.sleep(5)
        else:
            raise RuntimeError("Database connection did not become ready")
        self.compose("run", "--rm", "--no-deps", "db-tools", "psql", "-v", "ON_ERROR_STOP=1", "-f", "/deploy/sql/preflight.sql")
        self.compose("run", "--rm", "--no-deps", "migrate")
        self.compose("run", "--rm", "--no-deps", "db-tools", "psql", "-v", "ON_ERROR_STOP=1", "-f", "/deploy/sql/runtime-roles.sql")
        self.compose("run", "--rm", "--no-deps", "db-tools", "psql", "-v", "ON_ERROR_STOP=1", "-f", "/deploy/sql/postflight.sql")
        self.compose("run", "--rm", "--no-deps", "migrate", "department-catalog-import")
        self.compose("run", "--rm", "--no-deps", "bootstrap")


def smoke(runtime, check_accounts=True):
    endpoints = runtime["endpoints"]
    for name in ("api", "admin", "backoffice", "commerce", "tracking"):
        path = "/health/ready" if name == "api" else "/" if name == "tracking" else "/ingresar"
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
    # A database-backed login exercises the migrated schema and runtime RLS role.
    accounts = (("admin", "admin@nexoruta.test"), ("operator", "operador@nexoruta.test"), ("commerce", "comercio@nexoruta.test")) if check_accounts else ()
    for role, email in accounts:
        payload = json.dumps({"email": email, "password": runtime["passwords"][role]}).encode()
        request = urllib.request.Request(endpoints["api"] + "/api/auth/login", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"Bootstrap login failed: {role}")


def main():
    import fcntl
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--release", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"release-[a-f0-9]{32}", args.release):
        raise ValueError("Invalid release ID")
    os.umask(0o077)
    BASE.mkdir(exist_ok=True)
    with open("/run/lock/nexoruta-deploy.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        manifest = json.loads(object_bytes(args.bucket, f"releases/{args.release}/manifest.json"))
        if manifest["release"] != args.release:
            raise ValueError("Manifest/release mismatch")
        bundle = object_bytes(args.bucket, f"releases/{args.release}/bundle.tar.gz")
        if hashlib.sha256(bundle).hexdigest() != manifest["bundle_sha256"]:
            raise ValueError("Bundle checksum mismatch")
        directory = BASE / "releases" / args.release
        directory.mkdir(parents=True, exist_ok=True)
        extract(bundle, directory)
        project = urllib.request.urlopen(urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/project/project-id",
            headers={"Metadata-Flavor": "Google"}), timeout=15).read().decode()
        runtime = secret(project, "nexoruta-demo-runtime")
        integrations = secret(project, "nexoruta-demo-integrations")
        log_dir = BASE / "logs"
        log_dir.mkdir(exist_ok=True)
        with open(log_dir / f"{args.release}.log", "a") as log:
            deployment = Deploy(directory, log)
            registry_host = runtime["registry"].split("/")[0]
            deployment.execute("docker", "login", registry_host, "--username", "oauth2accesstoken", "--password-stdin", input=token() + "\n")
            try:
                mail_hash = deployment.execute("docker", "run", "--rm", "caddy:2.10.2-alpine", "caddy", "hash-password", "--plaintext", runtime["passwords"]["mail"], capture=True)
                values = environment(runtime, integrations, manifest["images"], mail_hash)
                private_file(directory / ".env", "".join(env_line(key, value) for key, value in values.items()))
                private_file(directory / "bootstrap.json", json.dumps(bootstrap_config(runtime)))
                deployment.compose("config", "--quiet")
                deployment.compose("--profile", "administration", "pull")
            finally:
                deployment.execute("docker", "logout", registry_host)
            current = BASE / "current-release"
            previous = current.read_text().strip() if current.exists() else None
            try:
                deployment.compose("stop", *APPS)
                deployment.compose("up", "-d", "--wait", "--wait-timeout", "300", "sql-proxy", "rabbitmq", "kafka", "mongo", "mailpit")
                for topic in ("nexoruta.envios.creados.v1", "nexoruta.password-recovery.requested.v1"):
                    deployment.compose("exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh", "--bootstrap-server", "kafka:9092", "--create", "--if-not-exists", "--topic", topic, "--partitions", "1", "--replication-factor", "1")
                deployment.migrate()
                deployment.compose("up", "-d", "--force-recreate", "--wait", "--wait-timeout", "300", *APPS)
                smoke(runtime, check_accounts=previous is None)
                private_file(current, args.release + "\n")
                print(json.dumps({"release": args.release, "endpoints": runtime["endpoints"], "status": "healthy"}))
            except Exception:
                if previous and previous != args.release:
                    try:
                        rollback = Deploy(BASE / "releases" / previous, log)
                        rollback.compose("up", "-d", "--wait", "--wait-timeout", "180", *APPS)
                        print("Previous application containers restored; database migrations were not rolled back.")
                    except Exception:
                        print("Container rollback failed; inspect the private deployment log.")
                raise RuntimeError(f"Deployment failed. Private log: /srv/nexoruta/logs/{args.release}.log") from None


if __name__ == "__main__":
    main()
