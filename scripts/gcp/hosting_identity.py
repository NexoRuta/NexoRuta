"""Create hosting credentials once; callers must serialize deployment jobs.

The existing Secret Manager version is authoritative. A malformed version must be
repaired explicitly: replacing it here could invalidate shared sessions and
Grafana's encrypted data.
"""

import base64
import binascii
import contextlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile

import demo_session as session


SECRET = "nexoruta-demo-hosting"
PASSWORD_ENV = "NEXORUTA_HOSTING_PFX_PASSWORD"


@contextlib.contextmanager
def private_directory():
    previous = os.umask(0o077)
    try:
        with tempfile.TemporaryDirectory(prefix="nexoruta-hosting-") as directory:
            yield Path(directory)
    finally:
        os.umask(previous)


def openssl(*arguments, password):
    executable = shutil.which("openssl")
    if not executable:
        raise RuntimeError("Install OpenSSL before creating or validating the hosting identity.")
    try:
        return subprocess.run(
            [executable, *map(str, arguments)], check=True, capture_output=True,
            env={**os.environ, PASSWORD_ENV: password},
        )
    except subprocess.CalledProcessError:
        # Do not expose private file contents, passwords, or captured diagnostics.
        raise ValueError("OpenSSL could not create or validate the hosting certificate.") from None


def generate_identity():
    password = secrets.token_urlsafe(48)
    with private_directory() as directory:
        key = directory / "private-key.pem"
        certificate = directory / "certificate.pem"
        pfx = directory / "certificate.pfx"
        openssl(
            "req", "-x509", "-newkey", "rsa:3072", "-nodes", "-sha256",
            "-subj", "/CN=NexoRutaDataProtection", "-days", "3650",
            "-keyout", key, "-out", certificate, password=password,
        )
        openssl(
            "pkcs12", "-export", "-inkey", key, "-in", certificate,
            "-out", pfx, "-passout", f"env:{PASSWORD_ENV}", password=password,
        )
        return {
            "certificate_pfx": base64.b64encode(pfx.read_bytes()).decode("ascii"),
            "certificate_password": password,
            "grafana_secret_key": secrets.token_urlsafe(48),
        }


def validate_identity(value):
    message = "The existing hosting identity is invalid; repair its Secret Manager version explicitly."
    required = ("certificate_pfx", "certificate_password", "grafana_secret_key")
    if not isinstance(value, dict) or any(not isinstance(value.get(key), str) or not value[key] for key in required):
        raise ValueError(message)
    if len(value["certificate_password"]) < 32 or len(value["grafana_secret_key"]) < 32:
        raise ValueError(message)
    if any(character in value[key] for key in required for character in ("\r", "\n", "\x00")):
        raise ValueError(message)
    try:
        pfx = base64.b64decode(value["certificate_pfx"], validate=True)
        if not pfx:
            raise ValueError(message)
        with private_directory() as directory:
            path = directory / "certificate.pfx"
            path.write_bytes(pfx)
            openssl("pkcs12", "-info", "-noout", "-in", path,
                    "-passin", f"env:{PASSWORD_ENV}", password=value["certificate_password"])
    except (binascii.Error, ValueError):
        raise ValueError(message) from None
    return value


def ensure(project):
    versions = session.command(
        "gcloud", "secrets", "versions", "list", SECRET,
        f"--project={project}", "--filter=state=ENABLED", "--format=value(name)",
        capture=True,
    )
    if versions.strip():
        payload = session.command(
            "gcloud", "secrets", "versions", "access", "latest", f"--secret={SECRET}",
            f"--project={project}", capture=True,
        )
        try:
            value = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("The existing hosting identity is invalid; repair its Secret Manager version explicitly.") from None
        return validate_identity(value)

    value = generate_identity()
    with private_directory() as directory:
        path = directory / "hosting.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        session.command(
            "gcloud", "secrets", "versions", "add", SECRET,
            f"--project={project}", f"--data-file={path}", "--quiet", capture=True,
        )
    return value
