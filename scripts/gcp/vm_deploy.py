"""Run as root on the VM; credentials come from its attached service account."""

import argparse
import base64
from contextlib import contextmanager
import hashlib
import hmac
import io
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import selectors
import socket
import ssl
import subprocess
import sys
import tarfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

BASE = Path("/srv/nexoruta")
APPS = ("api", "worker-rabbit", "worker-kafka", "worker-push", "worker-webhooks", "admin", "backoffice", "commerce", "tracking",
        "grafana", "otel-collector", "alloy")
APP_IMAGE_SERVICES = ("api", "worker", "admin", "backoffice", "commerce", "tracking")
DEMO_SEED_PASSWORD = "ChangeMe123!"
DEMO_ADMIN_PASSWORD = "AdminPass123!"
SHARED = ("rabbitmq", "kafka", "mongo", "mailpit", "proxy", "prometheus", "prometheus-write-gateway",
          "gcp-metrics-collector", "loki", "tempo")
OBSERVABILITY_CORE = ("prometheus", "prometheus-write-gateway", "gcp-metrics-collector", "loki", "tempo")
RINGS = ("api", "admin", "backoffice", "commerce", "tracking")
LOAD_BALANCER_PROXIES = ("35.191.0.0/16", "130.211.0.0/22")
DIRECT_PORTS = {"api": 18080, "admin": 18081, "backoffice": 18082,
                "commerce": 18083, "tracking": 18084, "monitor": 13000}
MIGRATION_LOCK = 74200344171234
OPS_AGENT_CONFIG = Path("/etc/google-cloud-ops-agent/config.yaml")
REDIS_RUNTIME_COMMANDS = (
    "ping", "get", "set", "del", "unlink", "hmget", "hmset", "hset", "expire", "pexpire", "eval", "evalsha",
    "client|setname", "client|setinfo", "info", "command|info", "hello", "echo",
)


def measure(timings, phase, operation):
    started = time.perf_counter()
    try:
        return operation()
    except Exception as error:
        if not hasattr(error, "nexoruta_phase"):
            error.nexoruta_phase = phase
        raise
    finally:
        timings[phase] = round((time.perf_counter() - started) * 1000)


def bootstrap_failure_diagnostic(log, start_offset):
    """Return a small allowlisted category from bootstrap output, never raw logs."""
    try:
        if hasattr(log, "getvalue"):
            text = log.getvalue()[start_offset:]
        else:
            log.flush()
            with open(log.name, "rb") as source:
                source.seek(start_offset)
                text = source.read(65536).decode("utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        return "BootstrapProcessFailed"
    categories = (
        ("Existing platform account email differs from configured initialization", "BootstrapPlatformEmailMismatch"),
        ("Existing platform account has no password hash", "BootstrapPlatformPasswordHashMissing"),
        ("Existing platform account is inactive", "BootstrapPlatformAccountInactive"),
        ("Existing platform role is incompatible with configured initialization", "BootstrapPlatformRoleIncompatible"),
        ("Existing platform role permissions differ from the protected catalog", "BootstrapPlatformPermissionsMismatch"),
        ("Existing platform account also has organization access", "BootstrapPlatformHasOrganizationAccess"),
        ("Configured platform password differs from the existing password", "BootstrapPlatformPasswordMismatch"),
        ("Platform initialization email belongs to an existing identity", "BootstrapPlatformEmailConflict"),
        ("Existing platform account is incompatible", "BootstrapPlatformIdentityIncompatible"),
        ("No existing platform account was found to synchronize", "BootstrapPlatformAccountMissing"),
        ("Configured platform administrator credentials are missing or invalid", "BootstrapPlatformConfigurationInvalid"),
    )
    for message, category in categories:
        if message in text:
            return category
    match = re.search(r"(?:Unhandled exception\.?\s+|\n)(?:[\w.]+\.)?([A-Za-z][A-Za-z0-9]*(?:Exception|Error)):", text)
    if match:
        return "Bootstrap" + match.group(1)
    return "BootstrapProcessFailed"


class BootstrapFailureError(RuntimeError):
    def __init__(self, diagnostic):
        super().__init__("Demo bootstrap failed")
        self.safe_diagnostic = diagnostic


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


def validate_release_manifest(manifest, release, project_id, zone):
    sha = r"[a-f0-9]{40}"
    hex_256 = r"[a-f0-9]{64}"
    release_pattern = r"release-[a-f0-9]{32}"

    def matches(pattern, value):
        return isinstance(value, str) and re.fullmatch(pattern, value) is not None

    def valid_sources(value):
        return (isinstance(value, dict) and set(value) == {"backend", "frontend", "mobile"}
                and all(matches(sha, item) for item in value.values()))

    if (not isinstance(manifest, dict) or manifest.get("manifest_version") != 2
            or manifest.get("release") != release or manifest.get("project_id") != project_id
            or not matches(r"[a-z]+-[a-z]+[0-9]", manifest.get("region"))):
        raise ValueError("Release manifest identity is invalid")
    region = zone.rsplit("-", 1)[0]
    if manifest["region"] != region:
        raise ValueError("Release manifest region does not match this VM")
    if not matches(hex_256, manifest.get("bundle_sha256")):
        raise ValueError("Release manifest has no valid bundle checksum")
    sources = manifest.get("sources")
    if not valid_sources(sources) or not matches(sha, manifest.get("root_sha")):
        raise ValueError("Release manifest has invalid root or component sources")
    registry = f"{region}-docker.pkg.dev/{project_id}/nexoruta"
    images = manifest.get("images")
    if (not isinstance(images, dict) or set(images) != set(APP_IMAGE_SERVICES)
            or any(not matches(re.escape(f"{registry}/{name}@sha256:") + hex_256, images.get(name))
                   for name in APP_IMAGE_SERVICES)):
        raise ValueError("Release manifest has incomplete or unpinned application images")
    image_sources = manifest.get("image_sources")
    if (not isinstance(image_sources, dict) or set(image_sources) != set(APP_IMAGE_SERVICES)
            or any(image_sources[name] != sources["backend" if name in ("api", "worker") else "frontend"]
                   for name in APP_IMAGE_SERVICES)):
        raise ValueError("Release images do not match the recorded source gitlinks")
    built = manifest.get("built_images")
    reused = manifest.get("reused_images")
    if (not isinstance(built, list) or any(not isinstance(name, str) or name not in APP_IMAGE_SERVICES for name in built)
            or len(built) != len(set(built)) or not isinstance(reused, dict)
            or set(built).intersection(reused) or set(built).union(reused) != set(APP_IMAGE_SERVICES)
            or any(not matches(release_pattern, value) for value in reused.values())):
        raise ValueError("Release manifest has incomplete image provenance")
    order = manifest.get("publication_order")
    if (not isinstance(order, list) or len(order) != 2
            or any(type(value) is not int or value < 1 for value in order)):
        raise ValueError("Release manifest has invalid publication order")
    bundle_source = manifest.get("bundle_source")
    if (not isinstance(bundle_source, dict) or not matches(sha, bundle_source.get("root_sha"))
            or not matches(sha, bundle_source.get("backend_sha"))
            or type(manifest.get("bundle_rebuilt")) is not bool
            or not matches(hex_256, manifest.get("deployment_images_sha256"))):
        raise ValueError("Release manifest has incomplete bundle provenance")
    if manifest["bundle_rebuilt"] and (
        bundle_source["root_sha"] != manifest["root_sha"]
        or bundle_source["backend_sha"] != sources["backend"]
    ):
        raise ValueError("Release bundle does not match the recorded source snapshot")
    channel = manifest.get("channel")
    if channel == "main":
        ci = manifest.get("ci_evidence")
        if (not matches(r"integration-[1-9][0-9]*-[1-9][0-9]*", manifest.get("integration_tag"))
                or not isinstance(ci, dict) or ci.get("schema_version") != 1
                or not isinstance(ci.get("repository_id"), str) or not ci["repository_id"].isdigit()
                or ci.get("workflow_path") != ".github/workflows/ci.yml"
                or ci.get("event") != "pull_request" or ci.get("base_branch") != "main"
                or ci.get("head_branch") != "develop"
                or ci.get("release_root_sha") != manifest["root_sha"]
                or ci.get("sources") != sources or not matches(sha, ci.get("root_sha"))
                or not matches(sha, ci.get("root_tree")) or not matches(hex_256, ci.get("plan_sha256"))):
            raise ValueError("Main release manifest has no valid protected CI identity")
        artifact = ci.get("artifact")
        if (type(ci.get("run_id")) is not int or ci["run_id"] < 1
                or type(ci.get("run_attempt")) is not int or ci["run_attempt"] < 1
                or type(ci.get("pull_request")) is not int or ci["pull_request"] < 1
                or not isinstance(artifact, dict) or type(artifact.get("id")) is not int or artifact["id"] < 1
                or artifact.get("name") != f"nfr14-ci-evidence-{ci['run_attempt']}"
                or not matches(r"sha256:[a-f0-9]{64}", artifact.get("digest"))):
            raise ValueError("Main release manifest has an invalid CI artifact identity")
        proof = manifest.get("android_verification")
        if (not isinstance(proof, dict) or proof.get("schema_version") != 1
                or not matches(hex_256, proof.get("android_input_sha256"))
                or proof.get("android_input_sha256") != manifest.get("android_input_sha256")
                or not matches(sha, proof.get("mobile_sha"))
                or proof.get("mobile_sha") != manifest.get("android_verified_mobile_sha")
                or not matches(release_pattern, proof.get("origin_release"))):
            raise ValueError("Main release manifest has no valid Android verification proof")
        proof_ci = proof.get("verified_by")
        if not isinstance(proof_ci, dict):
            raise ValueError("Main release Android proof has no CI identity")
        proof_artifact = proof_ci.get("artifact")
        proof_sources = proof_ci.get("sources")
        if (proof_ci.get("workflow_path") != ".github/workflows/ci.yml"
                or proof_ci.get("event") != "pull_request"
                or proof_ci.get("base_branch") != "main" or proof_ci.get("head_branch") != "develop"
                or proof_ci.get("head_repository_id") != proof_ci.get("repository_id")
                or not isinstance(proof_ci.get("repository_id"), str) or not proof_ci["repository_id"].isdigit()
                or type(proof_ci.get("run_id")) is not int or proof_ci["run_id"] < 1
                or type(proof_ci.get("run_attempt")) is not int or proof_ci["run_attempt"] < 1
                or not valid_sources(proof_sources) or proof_sources["mobile"] != proof.get("mobile_sha")
                or not matches(sha, proof_ci.get("root_sha")) or not matches(sha, proof_ci.get("root_tree"))
                or not isinstance(proof_artifact, dict) or type(proof_artifact.get("id")) is not int
                or proof_artifact["id"] < 1
                or proof_artifact.get("name") != f"nfr14-ci-evidence-{proof_ci.get('run_attempt')}"
                or not matches(r"sha256:[a-f0-9]{64}", proof_artifact.get("digest"))):
            raise ValueError("Main release Android proof is not linked to a completed CI artifact")
    elif channel == "develop":
        if (manifest.get("source_ref") != "refs/heads/develop" or manifest.get("ci_evidence") is not None
                or manifest.get("android_verification") is not None
                or manifest.get("android_input_sha256") is not None
                or manifest.get("android_verified_mobile_sha") is not None):
            raise ValueError("Develop release cannot claim protected CI or Android verification")
    else:
        raise ValueError("Release manifest has an unsupported channel")
    return manifest


def validate_bundle_inventory(manifest, release_directory):
    module_path = Path(release_directory) / "image_inventory.py"
    inventory_path = Path(release_directory) / "image-inventory.json"
    ci_path = Path(release_directory) / "ci_evidence.py"
    integration_path = Path(release_directory) / "integration.py"
    host_versions_path = Path(release_directory) / "host_versions.py"
    deployment_health_path = Path(release_directory) / "deployment_health.py"
    if (not module_path.is_file() or not inventory_path.is_file() or not ci_path.is_file()
            or not integration_path.is_file() or not host_versions_path.is_file()
            or not deployment_health_path.is_file()):
        raise ValueError("Release bundle is missing its deployment image inventory")
    import importlib.util
    spec = importlib.util.spec_from_file_location("nexoruta_release_image_inventory", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    module.validate_inventory(inventory)
    module.validate_inventory(manifest.get("deployment_images"))
    if (inventory != manifest.get("deployment_images")
            or module.checksum(inventory) != manifest.get("deployment_images_sha256")):
        raise ValueError("Release bundle image inventory does not match its manifest")
    previous_integration = sys.modules.pop("integration", None)
    release_path = str(Path(release_directory))
    sys.path.insert(0, release_path)
    try:
        ci_spec = importlib.util.spec_from_file_location("nexoruta_release_ci_evidence", ci_path)
        ci_module = importlib.util.module_from_spec(ci_spec)
        ci_spec.loader.exec_module(ci_module)
        if manifest.get("channel") == "main":
            ci_module.validate_manifest_android(manifest)
    finally:
        sys.path.remove(release_path)
        sys.modules.pop("integration", None)
        if previous_integration is not None:
            sys.modules["integration"] = previous_integration
    return inventory


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


def mongo_runtime_password(root_password, application):
    if (application not in ("api", "worker") or not isinstance(root_password, str)
            or not root_password or any(character in root_password for character in "\r\n\x00")):
        raise ValueError("MongoDB runtime credentials require the protected root secret and a known application")
    return hmac.new(root_password.encode("utf-8"),
                     ("nexoruta-mongodb-" + application + "-v1").encode("ascii"),
                     hashlib.sha256).hexdigest()


def validate_operational_topic(topic_description, topic_config):
    if not isinstance(topic_description, str) or not isinstance(topic_config, str):
        raise RuntimeError("Kafka operational topic configuration could not be verified")
    if not re.search(r"(?:^|\s)PartitionCount:\s*3(?:\s|$)", topic_description):
        raise RuntimeError("Kafka operational topic must have exactly three partitions")
    if not re.search(r"(?:^|\s)ReplicationFactor:\s*1(?:\s|$)", topic_description):
        raise RuntimeError("Kafka operational topic must match the single-broker replication factor")
    for setting in ("retention.ms", "retention.bytes"):
        if not re.search(r"(?<![A-Za-z0-9_.-])" + re.escape(setting) + r"=-1(?![A-Za-z0-9_.-])", topic_config):
            raise RuntimeError("Kafka operational topic has incompatible retention configuration")


def ensure_operational_topic(deployment):
    topic = "nexoruta.operacion.v1"
    deployment.compose("--profile", "shared", "exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh",
                       "--bootstrap-server", "kafka:9092", "--create", "--if-not-exists", "--topic", topic,
                       "--partitions", "3", "--replication-factor", "1", "--config", "min.insync.replicas=1",
                       "--config", "retention.ms=-1", "--config", "retention.bytes=-1")
    description = deployment.compose("--profile", "shared", "exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh",
                                     "--bootstrap-server", "kafka:9092", "--describe", "--topic", topic,
                                     capture=True)
    config = deployment.compose("--profile", "shared", "exec", "-T", "kafka", "/opt/kafka/bin/kafka-configs.sh",
                                "--bootstrap-server", "kafka:9092", "--entity-type", "topics", "--entity-name", topic,
                                "--describe", "--all", capture=True)
    validate_operational_topic(description, config)


def ensure_mongo_runtime_users(deployment):
    deployment.compose("--profile", "shared", "run", "--rm", "mongo-provisioner")


def bootstrap_config(runtime):
    ids = runtime["organization_ids"]
    return {
        "PlatformInitialization": {"Enabled": True, "Email": "admin-demo@nexoruta.test", "Password": DEMO_ADMIN_PASSWORD},
        "AccesoInicial": {
            "OperadorId": ids["operator"], "ComercioId": ids["commerce"],
            "OperadorNombre": "Operador Demo Uruguay", "ComercioNombre": "Comercio Demo Uruguay",
            "OperadorUsuarioEmail": "operador@nexoruta.test", "UsuarioEmail": "comercio@nexoruta.test",
            "OperadorUsuarioPassword": DEMO_SEED_PASSWORD, "UsuarioPassword": DEMO_SEED_PASSWORD,
            "OperadorRolCodigo": "propietario-operador", "ComercioRolCodigo": "propietario-comercio",
        },
        "Bootstrap": {"Roles": [
            {"Codigo": "propietario-operador", "Nombre": "Propietario Operador", "OperadorId": ids["operator"], "Permisos": []},
            {"Codigo": "propietario-comercio", "Nombre": "Propietario Comercio", "ComercioId": ids["commerce"], "Permisos": []},
        ]},
    }


def environment(runtime, integrations, images, mail_hash, hosting=None, node=None,
                private_ip=None, release=None, docker_subnets=(), redis_identity=None):
    passwords, keys, endpoints = runtime["passwords"], runtime["keys"], runtime["endpoints"]
    redis = runtime.get("redis")
    firebase_project_id = integrations.get("firebase_project_id")
    if not isinstance(firebase_project_id, str) or not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", firebase_project_id):
        raise ValueError("Firebase project ID must be configured for mobile push")
    result = {
        "PROJECT_ID": runtime["project_id"], "SQL_CONNECTION_NAME": runtime["sql_connection"],
        "FIREBASE_PROJECT_ID": firebase_project_id,
        "MIGRATOR_PASSWORD": passwords["migrator"], "API_DB_PASSWORD": passwords["api"],
        "WORKER_DB_PASSWORD": passwords["worker"], "BOOTSTRAP_DB_PASSWORD": passwords["bootstrap"],
        "MIGRATOR_CONNECTION": connection("postgres", passwords["migrator"]),
        "API_CONNECTION": connection("nexoruta_api_runtime", passwords["api"]),
        "WORKER_CONNECTION": connection("nexoruta_worker_runtime", passwords["worker"]),
        "BOOTSTRAP_CONNECTION": connection("nexoruta_bootstrap_runtime", passwords["bootstrap"]),
        "JWT_KEY": keys["jwt"], "TRACKING_KEY": keys["tracking"],
        "PUSH_KEY": keys["push"], "EVIDENCE_KEY": keys["evidence"],
        "RABBIT_PASSWORD": passwords["rabbit"], "MONGO_PASSWORD": passwords["mongo"],
        "MONGO_API_PASSWORD": mongo_runtime_password(passwords["mongo"], "api"),
        "MONGO_WORKER_PASSWORD": mongo_runtime_password(passwords["mongo"], "worker"),
        "MAIL_PASSWORD_HASH": mail_hash,
        "SMTP_HOST": integrations["smtp_host"], "SMTP_PORT": integrations["smtp_port"],
        "SMTP_SSL": str(integrations["smtp_ssl"]).lower(), "SMTP_FROM": integrations["smtp_from"],
        "SMTP_USERNAME": integrations.get("smtp_username", ""), "SMTP_PASSWORD": integrations.get("smtp_password", ""),
        "GEOAPIFY_API_KEY": integrations.get("geoapify_api_key", ""),
        "WEBHOOK_ALLOWED_ORIGINS": ";".join(integrations.get("webhook_allowed_origins", [])),
        "WEBHOOK_ALLOW_ANY_PUBLIC_HTTPS_ORIGIN": str(
            integrations.get("webhook_allow_any_public_https_origin", False)).lower(),
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
        actor_password = DEMO_SEED_PASSWORD
        if node not in ("a", "b") or not re.fullmatch(r"release-[a-f0-9]{32}", release or ""):
            raise ValueError("A shared deployment needs a valid node and release")
        for address in (private_ip, runtime["frontend_ip"]):
            ipaddress.IPv4Address(address)
        if not re.fullmatch(r"[A-Za-z0-9.-]+", runtime["services_host"]):
            raise ValueError("Invalid private services host")
        cache_enabled = integrations.get("cache_enabled", "true")
        if not isinstance(cache_enabled, str) or cache_enabled.strip().lower() not in ("true", "false"):
            raise ValueError("The distributed-cache deployment flag must be true or false")
        cache_enabled = cache_enabled.strip().lower()
        expected_redis_host = redis_dns_name(runtime)
        if (not isinstance(redis, dict) or redis.get("host") != expected_redis_host
                or redis.get("port") != 6378):
            raise ValueError("Redis must use the TLS endpoint derived from VM B")
        if cache_enabled == "true" and (
                not isinstance(redis_identity, dict)
                or redis_identity.get("dns_name") != expected_redis_host
                or not isinstance(redis_identity.get("password"), str)
                or len(redis_identity["password"]) < 48
                or any(character in redis_identity["password"] for character in "\r\n\x00")
                or not isinstance(redis_identity.get("ca_certificate"), str)
                or "-----BEGIN CERTIFICATE-----" not in redis_identity["ca_certificate"]):
            raise ValueError("Enabled Redis requires an authenticated TLS identity derived from VM B")
        redis_password = redis_identity["password"] if redis_identity else ""
        redis_ca = redis_identity["ca_certificate"] if redis_identity else ""
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
            "DEMO_DATA_ACTOR_PASSWORD": actor_password,
            "NEXORUTA_CACHE_ENABLED": cache_enabled,
            "REDIS_HOST": redis["host"], "REDIS_PORT": redis["port"], "REDIS_AUTH": redis_password,
            "REDIS_CONFIG_DIR": str(BASE / "redis"),
            "REDIS_CA_CERTIFICATES_BASE64_JSON": json.dumps(
                [base64.b64encode(redis_ca.encode("ascii")).decode("ascii")] if redis_ca else [],
                separators=(",", ":")),
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


def redis_dns_name(runtime):
    try:
        identity = runtime["nodes"]["b"]
        host = f"{identity['name']}.{identity['zone']}.c.{runtime['project_id']}.internal"
    except (KeyError, TypeError):
        raise ValueError("Runtime inventory is missing VM B's Redis DNS identity") from None
    redis = runtime.get("redis")
    if (not re.fullmatch(r"nexoruta-demo-b\.southamerica-west1-[bc]\.c\.[a-z][a-z0-9-]{4,28}[a-z0-9]\.internal", host)
            or not isinstance(redis, dict) or redis.get("host") != host or redis.get("port") != 6378):
        raise ValueError("Redis host does not match the configured VM B identity")
    return host


def redis_addresses(runtime):
    host = redis_dns_name(runtime)
    try:
        subnet = ipaddress.ip_network(runtime["subnet_cidr"], strict=True)
        addresses = {ipaddress.ip_address(result[4][0]) for result in
                     socket.getaddrinfo(host, 6378, type=socket.SOCK_STREAM)}
    except (KeyError, OSError, ValueError):
        raise ValueError("Redis DNS could not be resolved inside the configured private subnet") from None
    if not addresses or any(address not in subnet for address in addresses):
        raise ValueError("Redis DNS resolved outside the configured private subnet")
    return addresses


def _resp_command(connection, reader, *parts):
    encoded = [part.encode("utf-8") if isinstance(part, str) else part for part in parts]
    connection.sendall(b"*" + str(len(encoded)).encode() + b"\r\n" + b"".join(
        b"$" + str(len(part)).encode() + b"\r\n" + part + b"\r\n" for part in encoded))
    line = reader.readline(4096)
    if not line.endswith(b"\r\n"):
        raise RuntimeError("Redis returned a malformed response")
    prefix, payload = line[:1], line[1:-2]
    if prefix == b"-":
        raise RuntimeError("Redis rejected an authenticated client operation")
    if prefix in (b"+", b":"):
        return payload
    if prefix != b"$":
        raise RuntimeError("Redis returned an unsupported response")
    length = int(payload)
    if length < 0:
        return None
    if length > 2 * 1024 * 1024:
        raise RuntimeError("Redis response exceeded the smoke-test bound")
    data = reader.read(length + 2)
    if len(data) != length + 2 or not data.endswith(b"\r\n"):
        raise RuntimeError("Redis returned a truncated response")
    return data[:-2]


def redis_smoke(host, port, password, ca_certificate, release, node):
    context = ssl.create_default_context(cadata=ca_certificate)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    key = f"nexoruta:nexoruta-gcp-demo:cache:v1:operator_branding:smoke:{release}:{node}:{secrets.token_hex(8)}"
    value = secrets.token_urlsafe(24)
    raw = socket.create_connection((host, port), timeout=3)
    try:
        raw.settimeout(3)
        with context.wrap_socket(raw, server_hostname=host) as connection:
            with connection.makefile("rb") as reader:
                if _resp_command(connection, reader, "AUTH", password) != b"OK":
                    raise RuntimeError("Redis authentication failed")
                if _resp_command(connection, reader, "PING") != b"PONG":
                    raise RuntimeError("Redis TLS health probe failed")
                if _resp_command(connection, reader, "SET", key, value, "EX", "60") != b"OK":
                    raise RuntimeError("Redis smoke write failed")
                try:
                    if _resp_command(connection, reader, "GET", key) != value.encode("ascii"):
                        raise RuntimeError("Redis smoke read did not match")
                except Exception:
                    try:
                        _resp_command(connection, reader, "DEL", key)
                    except Exception:
                        pass
                    raise
                if _resp_command(connection, reader, "DEL", key) != b"1":
                    raise RuntimeError("Redis smoke cleanup failed")
    finally:
        raw.close()
    return {"redis_node": "b", "redis_client_node": node, "redis_port": port,
            "redis_probe": "tls-auth-set-get-delete-passed"}


def _private_group_file(path, value):
    if path.is_file() and not path.is_symlink() and path.read_bytes() == value:
        os.chown(path, 0, 1000)
        path.chmod(0o440)
        return
    private_bytes(path, value)
    os.chown(path, 0, 1000)
    path.chmod(0o440)


def configure_redis_files(release_directory, identity, node):
    directory = BASE / "redis"
    if directory.is_symlink():
        raise ValueError("Redis configuration directory cannot be a symlink")
    directory.mkdir(mode=0o750, parents=True, exist_ok=True)
    directory.chmod(0o750)
    os.chown(directory, 0, 1000)
    config_source = release_directory / "redis" / "redis.conf"
    if not config_source.is_file():
        raise FileNotFoundError("The release is missing its Redis server configuration")
    config = config_source.read_bytes()
    _private_group_file(directory / "redis.conf", config)
    password = identity["password"]
    key_pattern = "nexoruta:nexoruta-gcp-demo:cache:v1:*"
    acl = ("user default on #" + hashlib.sha256(password.encode("utf-8")).hexdigest()
           + " ~" + key_pattern + " -@all "
           + " ".join("+" + command for command in REDIS_RUNTIME_COMMANDS) + "\n")
    _private_group_file(directory / "users.acl", acl.encode("ascii"))
    _private_group_file(directory / "redis-auth", (password + "\n").encode("ascii"))
    _private_group_file(directory / "ca.crt", identity["ca_certificate"].encode("ascii"))
    if node == "b":
        _private_group_file(directory / "server.crt", identity["server_certificate"].encode("ascii"))
        _private_group_file(directory / "server.key", identity["server_private_key"].encode("ascii"))
    fingerprint = hashlib.sha256(
        config + b"\0" + acl.encode("ascii") + b"\0"
        + identity["server_certificate"].encode("ascii") + b"\0"
        + identity["server_private_key"].encode("ascii") + b"\0"
        + identity["ca_certificate"].encode("ascii")
    ).hexdigest()
    return directory, fingerprint


def caching_enabled(integrations):
    value = integrations.get("cache_enabled", "true")
    if not isinstance(value, str) or value.strip().lower() not in ("true", "false"):
        raise ValueError("cache_enabled must be true or false")
    return value.strip().lower() == "true"


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
            def bootstrap_data():
                self.log.flush()
                try:
                    start_offset = os.fstat(self.log.fileno()).st_size
                except (AttributeError, OSError, ValueError):
                    start_offset = len(self.log.getvalue()) if hasattr(self.log, "getvalue") else 0
                try:
                    self.compose("run", "--rm", "--no-deps", "bootstrap")
                except subprocess.CalledProcessError:
                    raise BootstrapFailureError(bootstrap_failure_diagnostic(self.log, start_offset)) from None
            self.measure("bootstrap_data", bootstrap_data)


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
        path = "/api/health" if name == "monitor" else "/ready"
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


def direct_mail_health(private_ip, endpoint, attempts=3):
    host = urllib.parse.urlsplit(endpoint).hostname
    if not host:
        raise RuntimeError("The mail health check has no valid host")
    request = urllib.request.Request(
        f"http://{private_ip}:18025/healthz", headers={"Host": host},
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.status == 200:
                    return
                raise RuntimeError(f"Direct node health failed for mail (HTTP {response.status})")
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"Direct node health failed for mail (HTTP {error.code})") from None
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 < attempts:
                time.sleep(2)
    raise RuntimeError("Direct node health failed for mail")


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


def collect_release_host_versions(module, path):
    return module.collect_host_versions(path)


def release_module(directory, filename, module_name):
    import importlib.util
    path = Path(directory) / filename
    if not path.is_file():
        raise FileNotFoundError(f"The release bundle is missing {filename}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"The release bundle module {filename} cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compose_health_snapshot(deployment, node, cache_enabled):
    module = release_module(deployment.directory, "deployment_health.py",
                            "nexoruta_release_deployment_health")
    container_ids = deployment.execute(
        "docker", "ps", "--quiet", "--filter", "label=com.docker.compose.project=nexoruta-demo",
        capture=True,
    ).splitlines()
    if (not container_ids or any(not re.fullmatch(r"[a-f0-9]{12,64}", item)
                                 for item in container_ids)):
        raise RuntimeError("The active Compose container inventory is empty or invalid")
    template = (
        '{{index .Config.Labels "com.docker.compose.service"}}\t'
        '{{.State.Status}}\t'
        '{{if .State.Health}}{{.State.Health.Status}}{{else}}not-configured{{end}}'
    )
    output = deployment.execute("docker", "inspect", "--format=" + template, *container_ids, capture=True)
    lines = output.splitlines()
    if len(lines) != len(container_ids):
        raise RuntimeError("Docker returned an incomplete Compose health inventory")
    services = []
    for line in lines:
        fields = line.split("\t")
        if len(fields) != 3:
            raise RuntimeError("Docker returned an invalid Compose health record")
        service, state, health = fields
        services.append({"service": service, "state": state, "health": health})
    return module.sanitize_node_snapshot({"node": node, "services": services}, node, cache_enabled)


def prepare(args, deployment, runtime, integrations, hosting, redis_identity, manifest, private_ip):
    host_versions_path = deployment.directory / "host_versions.py"
    if not host_versions_path.is_file():
        raise FileNotFoundError("The release bundle is missing host version validation")
    import importlib.util
    spec = importlib.util.spec_from_file_location("nexoruta_release_host_versions", host_versions_path)
    host_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host_module)
    host_version_record = collect_release_host_versions(host_module, BASE / "host-versions.json")
    cache_enabled = caching_enabled(integrations)

    def configure_and_pull():
        registry_host = runtime["registry"].split("/")[0]
        deployment.execute("docker", "login", registry_host, "--username", "oauth2accesstoken", "--password-stdin", input=token() + "\n")
        try:
            mail_hash = deployment.execute("docker", "run", "--rm", "-i", "caddy:2.10.2-alpine", "caddy", "hash-password",
                                           capture=True, input=runtime["passwords"]["mail"] + "\n")
            if cache_enabled:
                redis_addresses(runtime)
            if cache_enabled:
                redis_directory, redis_fingerprint = configure_redis_files(
                    deployment.directory, redis_identity, args.node)
            else:
                redis_directory, redis_fingerprint = BASE / "redis", "cache-bypass"
            values = environment(runtime, integrations, manifest["images"], mail_hash, hosting,
                                 args.node, private_ip, args.release, bridge_subnets(deployment), redis_identity)
            values["REDIS_CONFIG_FINGERPRINT"] = redis_fingerprint
            values["REDIS_CONFIG_DIR"] = str(redis_directory)
            private_file(deployment.directory / ".env", "".join(env_line(key, value) for key, value in values.items()))
            private_file(deployment.directory / "bootstrap.json", json.dumps(bootstrap_config(runtime)))
            certificate = base64.b64decode(hosting["certificate_pfx"], validate=True)
            if not certificate:
                raise ValueError("The shared Data Protection certificate is empty")
            private_bytes(deployment.directory / "hosting.pfx", certificate)
            deployment.compose("--profile", "administration", "--profile", "shared", "config", "--quiet")
            if args.node == "b" and cache_enabled:
                deployment.compose("--profile", "cache-b", "config", "--quiet")
            services = APPS + ("migrate", "bootstrap", "db-tools") + (SHARED if args.node == "a" else ())
            deployment.compose("--profile", "administration", "--profile", "shared", "pull", *services)
            if args.node == "b" and cache_enabled:
                deployment.compose("--profile", "cache-b", "pull", "redis")
        finally:
            deployment.execute("docker", "logout", registry_host)
    deployment.measure("configure_validate_and_pull_images", configure_and_pull)

    def install_host_monitoring_agent():
        ops_agent_source = deployment.directory / "monitoring/ops-agent.yaml"
        if not ops_agent_source.is_file():
            raise FileNotFoundError("The release bundle is missing monitoring/ops-agent.yaml")
        # Older releases configured the Ops Agent OTLP receiver on host port 4317.
        # Apply the current host-metrics-only config before Tempo claims that port.
        private_bytes(OPS_AGENT_CONFIG, ops_agent_source.read_bytes())
        deployment.execute("systemctl", "restart", "google-cloud-ops-agent")
        deployment.execute("systemctl", "is-active", "--quiet", "google-cloud-ops-agent")
    deployment.measure("install_host_monitoring_agent", install_host_monitoring_agent)

    def start_sql_and_shared_services():
        deployment.compose("up", "-d", "--wait", "--wait-timeout", "300", "sql-proxy")
        if args.node == "a":
            # Resume brokers through Compose and wait for health before issuing
            # topic commands. A raw `docker start` returns before Kafka is ready
            # and can leave a restarted broker without its current network aliases.
            brokers_and_mail = tuple(service for service in SHARED
                                     if service not in ("proxy", *OBSERVABILITY_CORE))
            if brokers_and_mail:
                deployment.compose("--profile", "shared", "up", "-d", "--no-deps",
                                   "--wait", "--wait-timeout", "300", *brokers_and_mail)
            # Recreate the observability core from this release's versioned config.
            # Compose preserves its named data volumes while replacing containers.
            deployment.measure("reconcile_observability_core", lambda: deployment.compose(
                "--profile", "shared", "up", "-d", "--no-deps", "--force-recreate",
                "--wait", "--wait-timeout", "300", *OBSERVABILITY_CORE))
            # Reconcile Caddy with this release's Compose file so its bind mount
            # and published 18025/tcp mapping are applied. Named Caddy volumes
            # remain attached because this does not remove volumes.
            deployment.measure("reconcile_mail_proxy", lambda: deployment.compose(
                "--profile", "shared", "up", "-d", "--no-deps", "--force-recreate",
                "--wait", "--wait-timeout", "300", "proxy"))
            deployment.measure("direct_mail_health_check", lambda: direct_mail_health(
                private_ip, runtime["endpoints"]["mail"]))
            for topic, partitions in (("nexoruta.envios.creados.v1", 1),
                                      ("nexoruta.password-recovery.requested.v1", 1),
                                      ("nexoruta.comercios.v2", 3)):
                deployment.compose("--profile", "shared", "exec", "-T", "kafka", "/opt/kafka/bin/kafka-topics.sh", "--bootstrap-server", "kafka:9092",
                                   "--create", "--if-not-exists", "--topic", topic, "--partitions", str(partitions), "--replication-factor", "1")
            ensure_operational_topic(deployment)
            ensure_mongo_runtime_users(deployment)
        elif cache_enabled:
            # Redis is an infrastructure service owned by node B, outside the
            # application list that an ordinary update drains and recreates.
            deployment.measure("reconcile_redis_b", lambda: deployment.compose(
                "--profile", "cache-b", "up", "-d", "--no-deps", "--wait",
                "--wait-timeout", "120", "redis"))
    deployment.measure("start_sql_proxy_and_shared_services", start_sql_and_shared_services)
    def install_monitoring_configuration():
        deploy_dir = BASE / "deploy"
        deploy_dir.mkdir(exist_ok=True)
        private_bytes(deploy_dir / "monitor_agent.py", (deployment.directory / "monitor_agent.py").read_bytes())
        services_ip = socket.gethostbyname(runtime["services_host"])
        if not ipaddress.IPv4Address(services_ip).is_private:
            raise ValueError("Monitoring services must resolve to a private address")
        private_file(BASE / "monitor.json", json.dumps({"project_id": runtime["project_id"], "node": args.node,
                     "services_host": services_ip, "private_ip": private_ip,
                     "redis_host": runtime["redis"]["host"], "redis_port": runtime["redis"]["port"],
                     "redis_zone": runtime["nodes"]["b"]["zone"],
                     "redis_subnet_cidr": runtime["subnet_cidr"],
                     "expires_at": args.deadline}))
        deployment.execute("systemctl", "restart", "nexoruta-monitor.service")
        private_file(deployment.directory / "prepared.json", json.dumps({
            "node": args.node, "deadline": args.deadline, "cache_enabled": cache_enabled,
        }))
    deployment.measure("install_monitoring_and_mark_prepared", install_monitoring_configuration)
    return {"cache_enabled": cache_enabled, "host_versions": host_version_record,
            "redis_node": "b", "redis_port": runtime["redis"]["port"],
            "redis_server_reconciled": args.node == "b" and cache_enabled}


def apply(args, deployment, private_ip, cache_enabled):
    try:
        def start_apps():
            try:
                deployment.compose("up", "-d", "--no-deps", "--force-recreate", "--wait", "--wait-timeout", "300", *APPS)
            except Exception:
                print(json.dumps({"stage": "apply", "node": args.node, "release": args.release,
                                  "status": "retrying_apps_readiness"}), flush=True)
                time.sleep(15)
                deployment.compose("up", "-d", "--no-deps", "--wait", "--wait-timeout", "300", *APPS)
        deployment.measure("start_and_wait_for_apps", start_apps)
        deployment.measure("direct_health_checks", lambda: direct_health(private_ip))
        compose_health = deployment.measure(
            "compose_service_health_inventory",
            lambda: compose_health_snapshot(deployment, args.node, cache_enabled),
        )
        private_file(BASE / "current-release", args.release + "\n")
        return {"compose_health": compose_health}
    except Exception as error:
        print(json.dumps({"stage": "apply", "node": args.node, "release": args.release,
                          "status": "failed"}))
        failure = RuntimeError("Node application update failed; it remains out of the load balancer")
        if hasattr(error, "nexoruta_phase"):
            failure.nexoruta_phase = error.nexoruta_phase
        raise failure from None


class MailSmokeError(RuntimeError):
    def __init__(self, message, http_status=None):
        super().__init__(message)
        self.http_status = http_status


def validate_authenticated_identity(identity, role, email, organization_ids):
    expected = {
        "admin": ("admin-demo@nexoruta.test", "Plataforma"),
        "operator": ("operador@nexoruta.test", "Operador"),
        "commerce": ("comercio@nexoruta.test", "Comercio"),
    }
    if role not in expected or not isinstance(identity, dict):
        raise RuntimeError(f"Authenticated actor read returned an invalid identity: {role}")
    expected_email, expected_type = expected[role]
    if (not isinstance(email, str) or email.casefold() != expected_email
            or not isinstance(identity.get("usuarioEmail"), str)
            or identity["usuarioEmail"].casefold() != expected_email
            or identity.get("tipo") != expected_type):
        raise RuntimeError(f"Authenticated actor read returned the wrong actor: {role}")
    operator_id = identity.get("operadorId")
    commerce_id = identity.get("comercioId")
    if role == "admin":
        valid_organization = operator_id is None and commerce_id is None
    elif role == "operator":
        expected_operator_id = organization_ids.get("operator")
        valid_organization = (isinstance(expected_operator_id, str) and bool(expected_operator_id)
                              and operator_id == expected_operator_id and commerce_id is None)
    else:
        expected_commerce_id = organization_ids.get("commerce")
        valid_organization = (isinstance(expected_commerce_id, str) and bool(expected_commerce_id)
                              and commerce_id == expected_commerce_id and operator_id is None)
    if not valid_organization:
        raise RuntimeError(f"Authenticated actor read returned the wrong organization: {role}")


def smoke(runtime, check_accounts=True):
    endpoints = runtime["endpoints"]
    for name in ("api", "admin", "backoffice", "commerce", "tracking", "monitor"):
        path = "/ready" if name in ("api", "tracking") else "/ingresar"
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
    last_status = None
    for attempt in range(60):
        try:
            with urllib.request.urlopen(endpoints["mail"] + "/", timeout=10) as response:
                raise MailSmokeError("The demo mail inbox is publicly accessible", response.status)
        except urllib.error.HTTPError as error:
            last_status = error.code
            if error.code == 401:
                break
            if not 500 <= error.code <= 599:
                raise MailSmokeError("The demo mail inbox must remain password-protected", error.code) from None
        except (urllib.error.URLError, TimeoutError):
            last_status = None
        if attempt < 59:
            time.sleep(5)
    else:
        raise MailSmokeError("The demo mail inbox did not become available", last_status)
    # A database-backed login exercises the migrated schema and runtime RLS role.
    accounts = (("admin", "admin-demo@nexoruta.test"), ("operator", "operador@nexoruta.test"), ("commerce", "comercio@nexoruta.test")) if check_accounts else ()
    authenticated_reads = []
    for role, email in accounts:
        payload = json.dumps({"email": email, "password": DEMO_ADMIN_PASSWORD if role == "admin" else DEMO_SEED_PASSWORD}).encode()
        request = urllib.request.Request(endpoints["api"] + "/api/auth/login", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"Bootstrap login failed: {role}")
            try:
                login = json.loads(response.read())
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise RuntimeError(f"Bootstrap login returned an invalid response: {role}") from error
        access_token = login.get("accessToken") if isinstance(login, dict) else None
        if not isinstance(access_token, str) or not access_token or any(c in access_token for c in "\r\n\x00"):
            raise RuntimeError(f"Bootstrap login returned no access token: {role}")
        request = urllib.request.Request(
            endpoints["api"] + "/api/usuarios/actual",
            headers={"Authorization": "Bearer " + access_token, "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"Authenticated actor read failed: {role}")
            try:
                identity = json.loads(response.read())
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise RuntimeError(f"Authenticated actor read returned an invalid response: {role}") from error
        validate_authenticated_identity(identity, role, email, runtime["organization_ids"])
        authenticated_reads.append({"role": role, "login": "passed", "actor_read": "passed"})
    return {"authenticated_reads": authenticated_reads}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--stage", choices=("prepare", "stop", "migrate", "apply", "verify", "redis-smoke"), required=True)
    parser.add_argument("--node", choices=("a", "b"), required=True)
    parser.add_argument("--deadline", type=float, required=True)
    args = parser.parse_args()
    timings = {}
    try:
        result = run_stage(args, timings)
        print(json.dumps({"release": args.release, "node": args.node, "stage": args.stage,
                          "status": "healthy", **result, "timings_ms": timings}))
    except Exception as error:
        failed_phase = getattr(error, "nexoruta_phase", "")
        http_status = getattr(error, "http_status", None)
        safe_diagnostic = getattr(error, "safe_diagnostic", "")
        print(json.dumps({"release": args.release, "node": args.node, "stage": args.stage,
                          "status": "failed", "error_type": type(error).__name__,
                          "error_location": error_location(error), "failed_phase": failed_phase,
                          "safe_diagnostic": safe_diagnostic if re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,63}", safe_diagnostic) else None,
                          "http_status": http_status if type(http_status) is int and 100 <= http_status <= 599 else None,
                          "timings_ms": timings}))
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
        project = None
        zone_name = None
        cache_enabled = None
        if args.stage == "prepare":
            project = measure(timings, "read_vm_project_identity", lambda: metadata("project/project-id"))
            zone_name = measure(timings, "read_vm_zone_identity", lambda: metadata("instance/zone").rsplit("/", 1)[-1])
            manifest = measure(timings, "download_manifest", lambda: json.loads(object_bytes(args.bucket, f"releases/{args.release}/manifest.json")))
            validate_release_manifest(manifest, args.release, project, zone_name)
            bundle = measure(timings, "download_bundle", lambda: object_bytes(args.bucket, f"releases/{args.release}/bundle.tar.gz"))
            if hashlib.sha256(bundle).hexdigest() != manifest["bundle_sha256"]:
                raise ValueError("Bundle checksum mismatch")
            directory.mkdir(parents=True, exist_ok=True)
            measure(timings, "verify_and_extract_bundle", lambda: extract(bundle, directory))
            validate_bundle_inventory(manifest, directory)
        else:
            prepared = json.loads((directory / "prepared.json").read_text(encoding="utf-8"))
            if (not isinstance(prepared, dict)
                    or set(prepared) != {"node", "deadline", "cache_enabled"}
                    or type(prepared.get("cache_enabled")) is not bool
                    or prepared != {"node": args.node, "deadline": args.deadline,
                                    "cache_enabled": prepared.get("cache_enabled")}):
                raise RuntimeError("The node was prepared for a different session")
            cache_enabled = prepared["cache_enabled"]
        if project is None:
            project = measure(timings, "read_vm_project_identity", lambda: metadata("project/project-id"))
        private_ip = measure(timings, "read_vm_private_ip", lambda: metadata("instance/network-interfaces/0/ip"))
        runtime = measure(timings, "read_runtime_secret", lambda: secret(project, "nexoruta-demo-runtime"))
        ipaddress.IPv4Address(private_ip)
        identity = runtime["nodes"][args.node]
        if (runtime["project_id"] != project or identity["name"] != metadata("instance/name")
                or identity["zone"] != (zone_name or metadata("instance/zone").rsplit("/", 1)[-1])):
            raise RuntimeError("The requested node does not match this VM identity")
        log_dir = BASE / "logs"
        log_dir.mkdir(exist_ok=True)
        with open(log_dir / f"{args.release}.log", "a") as log:
            deployment = Deploy(directory, log)
            deployment.timings_ms = timings
            result = {}
            if args.stage == "prepare":
                integrations = measure(timings, "read_integrations_secret", lambda: secret(project, "nexoruta-demo-integrations"))
                redis_identity = None
                if caching_enabled(integrations):
                    sys.path.insert(0, str(directory))
                    from redis_identity import validate_identity
                    identity = measure(timings, "read_redis_identity_secret",
                                       lambda: secret(project, "nexoruta-demo-redis"))
                    redis_identity = measure(timings, "validate_redis_identity",
                                             lambda: validate_identity(identity, redis_dns_name(runtime)))
                hosting = measure(timings, "read_hosting_secret", lambda: secret(project, "nexoruta-demo-hosting"))
                result = prepare(args, deployment, runtime, integrations, hosting, redis_identity, manifest, private_ip)
            elif args.stage == "stop":
                deployment.measure("stop_apps", lambda: deployment.compose("stop", *APPS))
            elif args.stage == "migrate":
                deployment.migrate(args.deadline)
            elif args.stage == "apply":
                result = apply(args, deployment, private_ip, cache_enabled)
            elif args.stage == "redis-smoke":
                sys.path.insert(0, str(directory))
                from redis_identity import validate_identity
                identity = measure(timings, "read_redis_identity_secret",
                                   lambda: secret(project, "nexoruta-demo-redis"))
                redis_identity = measure(timings, "validate_redis_identity",
                                         lambda: validate_identity(identity, redis_dns_name(runtime)))
                result = redis_smoke(runtime["redis"]["host"], runtime["redis"]["port"],
                                     redis_identity["password"], redis_identity["ca_certificate"],
                                     args.release, args.node)
            else:
                deployment.measure("direct_health_checks", lambda: direct_health(private_ip))
                smoke_result = deployment.measure("public_https_and_login_smoke", lambda: smoke(runtime))
                result = {"endpoints": runtime["endpoints"], **smoke_result}
            return result


if __name__ == "__main__":
    main()
