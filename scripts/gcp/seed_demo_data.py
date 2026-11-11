"""Run the authorized general synthetic seed from a GCP demo VM.

The VM's attached runtime identity reads its Secret Manager configuration. No
credential or bearer token is written to disk or printed to stdout.
"""

import base64
import json
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


def main():
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

    status, before = api_request(
        origin,
        "GET",
        "/api/admin/demo-data",
        bearer=bearer,
    )
    if status != 200 or not isinstance(before.get("sembrada"), bool):
        raise RuntimeError(f"Could not read general seed status (HTTP {status}).")

    # This is one idempotent call. An existing seed synchronizes synthetic
    # actor credentials/permissions and returns 409 without deleting history.
    status, result = api_request(
        origin,
        "POST",
        "/api/admin/demo-data",
        bearer=bearer,
        payload={},
        timeout=600,
    )
    if status not in (200, 409) or result.get("sembrada") is not True:
        raise RuntimeError(f"The general seed did not complete (HTTP {status}).")

    counts = {
        "operators": result.get("operadores"),
        "commerces": result.get("comercios"),
        "shipments": result.get("envios"),
        "routes": result.get("rutas"),
        "operations": result.get("operaciones"),
    }
    if any(not isinstance(value, int) or value < 0 for value in counts.values()):
        raise RuntimeError("The general seed returned invalid counts.")
    print(json.dumps({
        "result": "created" if not before["sembrada"] else "synchronized-existing",
        "seededBefore": before["sembrada"],
        **counts,
    }, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(f"General demo seed failed safely: {error}", file=sys.stderr)
        sys.exit(1)
