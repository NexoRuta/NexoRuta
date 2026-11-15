"""Validate the non-secret host toolchain snapshot written by VM startup."""

from datetime import datetime, timezone
import json
import os
import platform
from pathlib import Path
import re
import secrets
import subprocess


PACKAGE_NAMES = (
    "docker-ce", "docker-ce-cli", "containerd.io", "docker-buildx-plugin",
    "docker-compose-plugin", "google-cloud-ops-agent", "python3",
)
VERSION_FIELDS = (
    "kernel", "architecture", "docker_server", "docker_compose",
    "docker_buildx", "containerd",
)
RECORD_FIELDS = {
    "schema_version", "recorded_at", "os_id", "os_version_id", *VERSION_FIELDS, "packages",
}
_SAFE_TEXT = re.compile(r"[A-Za-z0-9][A-Za-z0-9 .:+~_/-]{0,159}\Z", re.ASCII)


def sanitize_host_versions(value):
    """Return only the bounded, non-secret host version fields or fail closed."""
    if not isinstance(value, dict) or set(value) != RECORD_FIELDS:
        raise ValueError("The host version record has an unexpected schema")
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("The host version record has an unsupported schema version")
    recorded_at = value.get("recorded_at")
    if not isinstance(recorded_at, str) or len(recorded_at) > 64:
        raise ValueError("The host version record has no valid timestamp")
    try:
        timestamp = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("The host version record has no valid timestamp") from error
    if timestamp.tzinfo is None:
        raise ValueError("The host version timestamp must include a timezone")

    result = {"schema_version": 1, "recorded_at": recorded_at}
    for field in ("os_id", "os_version_id", *VERSION_FIELDS):
        field_value = value.get(field)
        if (not isinstance(field_value, str) or not _SAFE_TEXT.fullmatch(field_value)
                or any(ord(char) < 32 for char in field_value)):
            raise ValueError("The host version record contains an invalid version value")
        result[field] = field_value
    if result["os_id"] != "debian" or result["os_version_id"] != "12":
        raise ValueError("The VM host does not match the configured Debian 12 image family")
    if result["architecture"] not in ("x86_64", "amd64"):
        raise ValueError("The VM host architecture is not supported by the deployment image")

    packages = value.get("packages")
    if not isinstance(packages, dict) or set(packages) != set(PACKAGE_NAMES):
        raise ValueError("The host package inventory is incomplete")
    result["packages"] = {}
    for name in PACKAGE_NAMES:
        package_version = packages[name]
        if not isinstance(package_version, str) or not _SAFE_TEXT.fullmatch(package_version):
            raise ValueError("The host package inventory contains an invalid package version")
        result["packages"][name] = package_version
    return result


def sanitize_node_map(value):
    if not isinstance(value, dict) or set(value) != {"a", "b"}:
        raise ValueError("Host version evidence must cover exactly nodes A and B")
    return {node: sanitize_host_versions(value[node]) for node in ("a", "b")}


def read_host_versions(path):
    source = Path(path)
    try:
        if source.stat().st_size > 32 * 1024:
            raise ValueError("The host version record exceeds its size limit")
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("The host version record is missing or unreadable") from error
    return sanitize_host_versions(value)


def collect_host_versions(path, *, os_release_path="/etc/os-release", runner=None):
    """Refresh the safe version snapshot from the current host without a shell."""
    runner = subprocess.run if runner is None else runner
    os_values = {}
    try:
        for line in Path(os_release_path).read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                os_values[key] = value.strip('"')
        package_format = "${Package}\\t${Version}\\n"
        package_output = runner(
            ["dpkg-query", "-W", f"-f={package_format}", *PACKAGE_NAMES],
            check=True, capture_output=True, text=True, timeout=15,
        ).stdout
        packages = {}
        for line in package_output.splitlines():
            name, separator, version = line.partition("\t")
            if not separator or name not in PACKAGE_NAMES or name in packages:
                raise ValueError("The host package inventory is malformed")
            packages[name] = version
        if set(packages) != set(PACKAGE_NAMES):
            raise ValueError("The host package inventory is incomplete")

        def command(*arguments):
            return runner(list(arguments), check=True, capture_output=True,
                          text=True, timeout=10).stdout.strip()

        record = {
            "schema_version": 1,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "os_id": os_values.get("ID"),
            "os_version_id": os_values.get("VERSION_ID"),
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "docker_server": command("docker", "version", "--format", "{{.Server.Version}}"),
            "docker_compose": command("docker", "compose", "version", "--short"),
            "docker_buildx": command("docker", "buildx", "version"),
            "containerd": command("containerd", "--version"),
            "packages": packages,
        }
        evidence = sanitize_host_versions(record)
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp-" + secrets.token_hex(8))
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                output.write(json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return evidence
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("The current host version inventory could not be collected") from error
