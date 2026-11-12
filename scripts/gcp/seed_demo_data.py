"""Run the authorized general synthetic seed from a GCP demo VM.

The VM's attached runtime identity reads its Secret Manager configuration. No
credential or bearer token is written to disk or printed to stdout.
"""

import base64
import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


METADATA = "http://metadata.google.internal/computeMetadata/v1/"
SECRET_NAME = "nexoruta-demo-runtime"
ADMIN_EMAIL = "admin@nexoruta.test"
MAX_RESPONSE_BYTES = 1024 * 1024


def read_url(request, timeout):
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        return error.code, error.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError("A required remote request did not complete.") from None


def read_metadata(path):
    request = urllib.request.Request(
        METADATA + path,
        headers={"Metadata-Flavor": "Google"},
    )
    status, body = read_url(request, timeout=15)
    if status != 200 or len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError("Could not read the VM's authorized metadata.")
    return body.decode("utf-8").strip()


def read_runtime_secret():
    project = read_metadata("project/project-id")
    metadata_token = read_metadata("instance/service-accounts/default/token")
    try:
        metadata_value = json.loads(metadata_token)
        access_token = metadata_value["access_token"]
        if not isinstance(access_token, str) or not access_token:
            raise ValueError
    except (json.JSONDecodeError, KeyError, ValueError):
        raise RuntimeError("The VM did not provide a valid runtime identity token.") from None

    secret_url = (
        "https://secretmanager.googleapis.com/v1/projects/"
        + urllib.parse.quote(project, safe="")
        + "/secrets/"
        + urllib.parse.quote(SECRET_NAME, safe="")
        + "/versions/latest:access"
    )
    request = urllib.request.Request(
        secret_url,
        headers={"Authorization": "Bearer " + access_token},
    )
    status, body = read_url(request, timeout=30)
    if status != 200 or len(body) > MAX_RESPONSE_BYTES:
        raise RuntimeError(f"Runtime configuration access failed (HTTP {status}).")
    try:
        payload = json.loads(body)["payload"]["data"]
        runtime = json.loads(base64.b64decode(payload, validate=True))
        password = runtime["passwords"]["admin"]
        origin = runtime["endpoints"]["api"]
        if not isinstance(password, str) or len(password) < 12:
            raise ValueError
        if not isinstance(origin, str):
            raise ValueError
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise RuntimeError("Runtime configuration is missing the platform login settings.") from None
    return origin, password


def validate_api_origin(origin):
    parsed = urllib.parse.urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.startswith("api.")
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("The API origin in runtime configuration is invalid.")
    return origin.rstrip("/")


def api_request(origin, method, path, bearer=None, payload=None, timeout=30):
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    request = urllib.request.Request(
        origin + path,
        data=body,
        headers=headers,
        method=method,
    )
    status, response_body = read_url(request, timeout)
    if len(response_body) > MAX_RESPONSE_BYTES:
        raise RuntimeError("The application returned an oversized response.")
    try:
        value = json.loads(response_body) if response_body else {}
    except json.JSONDecodeError:
        raise RuntimeError(f"The application returned invalid JSON (HTTP {status}).") from None
    if not isinstance(value, dict):
        raise RuntimeError(f"The application returned an invalid object (HTTP {status}).")
    return status, value


def seed_status(origin, bearer):
    status, value = api_request(
        origin,
        "GET",
        "/api/admin/demo-data",
        bearer=bearer,
    )
    if status != 200 or not isinstance(value.get("sembrada"), bool):
        raise RuntimeError(f"Could not read general seed status (HTTP {status}).")
    return value


def recent_seed_errors():
    """Return only error type and PostgreSQL identifiers from the target route."""
    try:
        containers = subprocess.run(
            [
                "sudo", "-n", "docker", "ps",
                "--filter", "label=com.docker.compose.service=api",
                "--format", "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"logsAvailable": False, "reason": "container-discovery-failed", "matchingEvents": 0, "errors": []}
    if containers.returncode != 0:
        return {"logsAvailable": False, "reason": "container-discovery-failed", "matchingEvents": 0, "errors": []}
    names = [line.strip() for line in containers.stdout.splitlines() if line.strip()]
    if len(names) != 1 or not re.fullmatch(r"[A-Za-z0-9_.-]+", names[0]):
        return {"logsAvailable": False, "reason": "api-container-not-unique", "matchingEvents": 0, "errors": []}

    try:
        result = subprocess.run(
            ["sudo", "-n", "docker", "logs", "--since=30m", "--tail=1000", names[0]],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"logsAvailable": False, "reason": "container-logs-unavailable", "matchingEvents": 0, "errors": []}
    if result.returncode != 0:
        return {"logsAvailable": False, "reason": "container-logs-unavailable", "matchingEvents": 0, "errors": []}

    errors = []
    lines = (result.stdout + "\n" + result.stderr).splitlines()
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        properties = event.get("Properties", {})
        if not isinstance(properties, dict):
            continue
        path = str(properties.get("RequestPath", properties.get("Route", "")))
        message = str(event.get("Message", event.get("MessageTemplate", "")))
        if not any(value in path or value in message for value in ("/api/admin/demo-data", "api/admin/demo-data")):
            continue
        exception = event.get("Exception", "")
        first_line = exception.splitlines()[0] if isinstance(exception, str) and exception else ""
        exception_match = re.search(r"\b([A-Za-z0-9_.+]*(?:Exception|Error))(?=[: (])", first_line)
        exception_summary = first_line.partition(": ")[2].strip()
        if exception_summary:
            exception_summary = re.sub(
                r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
                "<id>",
                exception_summary,
            )
            exception_summary = re.sub(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
                "<email>",
                exception_summary,
            )
            exception_summary = re.sub(
                r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
                "<ip>",
                exception_summary,
            )
            exception_summary = re.sub(r"\bAP04-[A-Za-z0-9-]+\b", "<fixture>", exception_summary)
            exception_summary = exception_summary[:200]
        sqlstate_match = re.search(r"\b([0-9A-Z]{5}):", exception if isinstance(exception, str) else "")
        constraint_match = re.search(
            r'constraint\s+["\']([A-Za-z0-9_.-]{1,120})["\']',
            exception if isinstance(exception, str) else "",
            flags=re.IGNORECASE,
        )
        error_type = properties.get("ErrorType")
        if not isinstance(error_type, str) or error_type == "none":
            error_type = exception_match.group(1) if exception_match else "unknown"
        errors.append({
            "type": error_type,
            "summary": exception_summary or None,
            "sqlstate": sqlstate_match.group(1) if sqlstate_match else None,
            "constraint": constraint_match.group(1) if constraint_match else None,
            "httpStatus": properties.get("StatusCode"),
        })
    return {
        "logsAvailable": True,
        "reason": None,
        "matchingEvents": len(errors),
        "errors": errors[-5:],
    }


def counts(value):
    result = {
        "operators": value.get("operadores"),
        "commerces": value.get("comercios"),
        "shipments": value.get("envios"),
        "routes": value.get("rutas"),
        "operations": value.get("operaciones"),
    }
    if any(not isinstance(item, int) or item < 0 for item in result.values()):
        raise RuntimeError("The general seed returned invalid counts.")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument("--diagnose-last-failure", action="store_true")
    options = parser.parse_args()

    origin, password = read_runtime_secret()
    origin = validate_api_origin(origin)

    status, login = api_request(
        origin,
        "POST",
        "/api/auth/login",
        payload={"email": ADMIN_EMAIL, "password": password},
    )
    if status != 200 or login.get("contexto") != "Plataforma":
        raise RuntimeError(f"Platform login failed or returned the wrong context (HTTP {status}).")
    bearer = login.get("accessToken")
    if not isinstance(bearer, str) or not bearer:
        raise RuntimeError("Platform login did not return an access token.")

    before = seed_status(origin, bearer)
    if options.status_only:
        result = {
            "result": "status-only",
            "seeded": before["sembrada"],
            **counts(before),
        }
        if options.diagnose_last_failure:
            result["recentErrors"] = recent_seed_errors()
        print(json.dumps(result, separators=(",", ":")))
        return

    # This is one idempotent call. An existing seed synchronizes synthetic
    # actor credentials/permissions and returns 200 without deleting history.
    status, result = api_request(
        origin,
        "POST",
        "/api/admin/demo-data",
        bearer=bearer,
        payload={},
        timeout=600,
    )
    if status != 200 or result.get("sembrada") is not True:
        after = seed_status(origin, bearer)
        failure = {
            "result": "failed",
            "httpStatus": status,
            "seededAfter": after["sembrada"],
            **counts(after),
        }
        failure["recentErrors"] = recent_seed_errors()
        print(json.dumps(failure, separators=(",", ":")), file=sys.stderr)
        raise RuntimeError(f"The general seed did not complete (HTTP {status}).")

    print(json.dumps({
        "result": "created" if not before["sembrada"] else "synchronized-existing",
        "seededBefore": before["sembrada"],
        **counts(result),
    }, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"General demo seed failed safely: {error}", file=sys.stderr)
        sys.exit(1)
