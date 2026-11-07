"""Create and validate the demo Redis identity in Secret Manager.

Callers must serialize this operation with the repository's deployment lock.
An existing version is authoritative and is never regenerated implicitly.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile

SECRET = "nexoruta-demo-redis"
PASSWORD_BYTES = 48
MINIMUM_CERTIFICATE_LIFETIME = timedelta(days=30)


def private_directory():
    return tempfile.TemporaryDirectory(prefix="nexoruta-redis-", dir=None)


def _openssl(*arguments):
    executable = shutil.which("openssl")
    if not executable:
        raise RuntimeError("OpenSSL is required to manage the Redis TLS identity.")
    try:
        return subprocess.run([executable, *map(str, arguments)], check=True,
                              capture_output=True, text=True)
    except subprocess.CalledProcessError:
        raise ValueError("OpenSSL could not create or validate the Redis TLS identity.") from None


def _valid_dns_name(value):
    return isinstance(value, str) and bool(re.fullmatch(
        r"nexoruta-demo-b\.southamerica-west1-[bc]\.c\.[a-z][a-z0-9-]{4,28}[a-z0-9]\.internal", value))


def generate_identity(dns_name):
    if not _valid_dns_name(dns_name):
        raise ValueError("The Redis server DNS name is outside the demo's secondary-zone inventory.")
    password = secrets.token_urlsafe(PASSWORD_BYTES)
    with private_directory() as temporary:
        directory = Path(temporary)
        ca_key = directory / "ca-key.pem"
        ca_certificate = directory / "ca-certificate.pem"
        server_key = directory / "server-key.pem"
        request = directory / "server.csr"
        server_certificate = directory / "server-certificate.pem"
        extensions = directory / "server-extensions.cnf"
        extensions.write_text(
            "basicConstraints=critical,CA:FALSE\n"
            "keyUsage=critical,digitalSignature,keyEncipherment\n"
            "extendedKeyUsage=serverAuth\n"
            f"subjectAltName=DNS:{dns_name}\n",
            encoding="ascii",
        )
        _openssl("req", "-x509", "-newkey", "rsa:3072", "-nodes", "-sha256",
                 "-days", "365", "-subj", "/CN=NexoRuta demo Redis CA",
                 "-addext", "basicConstraints=critical,CA:TRUE",
                 "-addext", "keyUsage=critical,keyCertSign,cRLSign",
                 "-keyout", ca_key, "-out", ca_certificate)
        _openssl("req", "-new", "-newkey", "rsa:2048", "-nodes", "-sha256",
                 "-subj", f"/CN={dns_name}", "-keyout", server_key, "-out", request)
        _openssl("x509", "-req", "-sha256", "-days", "365", "-in", request,
                 "-CA", ca_certificate, "-CAkey", ca_key, "-CAcreateserial",
                 "-extfile", extensions, "-out", server_certificate)
        result = {
            "password": password,
            "dns_name": dns_name,
            "ca_certificate": ca_certificate.read_text(encoding="ascii"),
            "server_certificate": server_certificate.read_text(encoding="ascii"),
            "server_private_key": server_key.read_text(encoding="ascii"),
        }
        return validate_identity(result, dns_name)


def validate_identity(value, expected_dns_name):
    message = "The existing Redis identity is invalid or near expiry; repair it explicitly."
    if not _valid_dns_name(expected_dns_name) or not isinstance(value, dict):
        raise ValueError(message)
    required = ("password", "dns_name", "ca_certificate", "server_certificate", "server_private_key")
    if any(not isinstance(value.get(key), str) or not value[key] for key in required):
        raise ValueError(message)
    password = value["password"]
    if (value["dns_name"] != expected_dns_name or len(password) < 48
            or any(character in password for character in "\r\n\x00")):
        raise ValueError(message)
    if any(len(value[key]) > 16_384 or "-----BEGIN " not in value[key]
           for key in required[2:]):
        raise ValueError(message)

    try:
        with private_directory() as temporary:
            directory = Path(temporary)
            ca = directory / "ca.pem"
            certificate = directory / "server.pem"
            key = directory / "server-key.pem"
            ca.write_text(value["ca_certificate"], encoding="ascii")
            certificate.write_text(value["server_certificate"], encoding="ascii")
            key.write_text(value["server_private_key"], encoding="ascii")
            _openssl("verify", "-CAfile", ca, "-verify_hostname", expected_dns_name, certificate)
            _openssl("x509", "-checkend", str(int(MINIMUM_CERTIFICATE_LIFETIME.total_seconds())),
                     "-noout", "-in", certificate)
            certificate_public_key = _openssl("x509", "-in", certificate, "-pubkey", "-noout").stdout.strip()
            private_public_key = _openssl("pkey", "-in", key, "-pubout").stdout.strip()
            if not certificate_public_key or certificate_public_key != private_public_key:
                raise ValueError(message)
            not_after = _openssl("x509", "-enddate", "-noout", "-in", certificate).stdout.strip()
            if not not_after.startswith("notAfter="):
                raise ValueError(message)
            expires = datetime.strptime(not_after.removeprefix("notAfter="), "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
        raise ValueError(message) from None

    if expires <= datetime.now(timezone.utc) + MINIMUM_CERTIFICATE_LIFETIME:
        raise ValueError(message)
    return {**value, "expires_at": expires.isoformat().replace("+00:00", "Z")}


def ensure(project, zone):
    import demo_session as session

    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project):
        raise ValueError("Invalid project id for Redis identity.")
    if zone not in ("southamerica-west1-b", "southamerica-west1-c"):
        raise ValueError("Redis must use the configured secondary zone.")
    dns_name = f"nexoruta-demo-b.{zone}.c.{project}.internal"
    versions = session.command("gcloud", "secrets", "versions", "list", SECRET,
                               f"--project={project}", "--filter=state=ENABLED",
                               "--format=value(name)", capture=True)
    if versions.strip():
        payload = session.command("gcloud", "secrets", "versions", "access", "latest",
                                  f"--secret={SECRET}", f"--project={project}", capture=True)
        try:
            value = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("The existing Redis identity is invalid or near expiry; repair it explicitly.") from None
        return validate_identity(value, dns_name)

    identity = generate_identity(dns_name)
    # expires_at is derived from the signed certificate and isn't needed in the secret.
    payload = {key: value for key, value in identity.items() if key != "expires_at"}
    with private_directory() as temporary:
        path = Path(temporary) / "redis-identity.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        path.chmod(0o600)
        session.command("gcloud", "secrets", "versions", "add", SECRET,
                        f"--project={project}", f"--data-file={path}", "--quiet", capture=True)
    return identity


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--zone", required=True)
    args = parser.parse_args()
    identity = ensure(args.project, args.zone)
    print(json.dumps({"secret": SECRET, "dns_name": identity["dns_name"],
                      "expires_at": identity["expires_at"], "status": "valid"}))


if __name__ == "__main__":
    main()
