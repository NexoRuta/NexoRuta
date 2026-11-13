"""Ensure the OPT-06 application fixture exists and pin its replay dataset."""

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import load_tests


FIXTURE_SECRET = "nexoruta-load-fixtures"
PREPARER_SECRET = "nexoruta-load-preparer-credentials"
READ_PATH = "/api/mobile/perfil"
MAX_BATCH = 5


def access_token(project):
    return subprocess.run(["gcloud", "auth", "print-access-token", f"--project={project}"],
                          check=True, capture_output=True, text=True, timeout=20).stdout.strip()


def google_request(token, method, url, body=None, content_type="application/json"):
    request = urllib.request.Request(url, method=method, data=body, headers={
        "Authorization": "Bearer " + token,
        "Content-Type": content_type,
    })
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read(8 * 1024 * 1024)
    except urllib.error.HTTPError as error:
        return error.code, error.read(4096)


def api_request(origin, bearer, method, path, payload=None):
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
    request = urllib.request.Request(origin + path, method=method, data=body, headers={
        "Authorization": "Bearer " + bearer,
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            content = response.read(2 * 1024 * 1024)
            return response.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Application fixture request failed with HTTP {error.code}") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise RuntimeError("Application fixture request did not complete safely") from None


def secret_version(token, project):
    name = urllib.parse.quote(FIXTURE_SECRET, safe="")
    url = f"https://secretmanager.googleapis.com/v1/projects/{project}/secrets/{name}/versions/latest:access"
    status, body = google_request(token, "GET", url)
    if status == 404:
        return None, None, None
    if status != 200:
        raise RuntimeError(f"Could not read the current fixture secret (HTTP {status})")
    value = json.loads(body)
    plaintext = base64.b64decode(value["payload"]["data"], validate=True)
    if len(plaintext) > 64 * 1024:
        raise RuntimeError("The current fixture secret exceeds the Secret Manager payload limit")
    try:
        version = re.fullmatch(
            rf"projects/(?:{re.escape(project)}|[1-9][0-9]*)/secrets/{re.escape(FIXTURE_SECRET)}/versions/([1-9][0-9]*)",
            value.get("name", ""),
        )
        if not version:
            raise RuntimeError("The current fixture secret has an invalid version name")
        return json.loads(plaintext), plaintext, version.group(1)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RuntimeError("The current fixture secret is not valid JSON") from None


def add_secret_version(token, project, value):
    body = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    if len(body) > 64 * 1024:
        raise RuntimeError("The generated fixture secret exceeds the Secret Manager payload limit")
    name = urllib.parse.quote(FIXTURE_SECRET, safe="")
    url = f"https://secretmanager.googleapis.com/v1/projects/{project}/secrets/{name}:addVersion"
    payload = json.dumps({"payload": {"data": base64.b64encode(body).decode("ascii")}},
                         separators=(",", ":")).encode()
    status, response = google_request(token, "POST", url, payload)
    if status != 200:
        raise RuntimeError(f"Could not persist the fixture secret (HTTP {status})")
    return json.loads(response)["name"].rsplit("/", 1)[-1]


def preparer_credentials(token, project):
    name = urllib.parse.quote(PREPARER_SECRET, safe="")
    url = f"https://secretmanager.googleapis.com/v1/projects/{project}/secrets/{name}/versions/latest:access"
    status, body = google_request(token, "GET", url)
    if status != 200:
        raise RuntimeError(f"Could not read the fixture-preparer credential (HTTP {status})")
    value = json.loads(base64.b64decode(json.loads(body)["payload"]["data"], validate=True))
    email, password = value.get("email"), value.get("password")
    if email != "admin@nexoruta.test" or not isinstance(password, str) or len(password) < 12:
        raise RuntimeError("The fixture-preparer secret has no valid platform credential")
    return email, password


def existing_accounts(value):
    accounts = value.get("accounts") if isinstance(value, dict) else None
    expected = [f"opt06-load-{number:03d}@nexoruta.test" for number in range(1, 51)]
    if not isinstance(accounts, list):
        return {}
    indexed = {item.get("email"): item for item in accounts if isinstance(item, dict)}
    return {email: indexed[email]["password"] for email in expected
            if email in indexed and isinstance(indexed[email].get("password"), str)
            and len(indexed[email]["password"]) >= 12}


def fixture_accounts(value, token, project):
    indexed = existing_accounts(value or {})
    expected = [f"opt06-load-{number:03d}@nexoruta.test" for number in range(1, 51)]
    accounts = [{"email": email, "password": indexed.get(email) or
                 base64.urlsafe_b64encode(os.urandom(36)).decode("ascii").rstrip("=")} for email in expected]
    if len(indexed) == len(expected) and isinstance(value, dict) and value.get("fixtureStatus") == "ready":
        return accounts
    if len(indexed) == len(expected) and isinstance(value, dict) and value.get("fixtureStatus") == "preparing":
        return accounts
    # Persist credentials before touching SQL so an interrupted seed can resume.
    add_secret_version(token, project, {"fixtureStatus": "preparing", "readPath": READ_PATH,
                                        "accounts": accounts})
    return accounts


def assert_preparation_active(config, access, run_id):
    state = load_tests.Storage(config["GCP_STATE_BUCKET"], access)
    leases = load_tests.Storage(load_tests.load_control_bucket(config), access)
    with load_tests.demo_control_lock(config, access):
        _, active = leases.read(load_tests.LEASE_OBJECT)
        now = time.time()
        if (not active or active.get("run_id") != run_id
                or active.get("owner") != os.environ.get("GITHUB_RUN_ID", "manual")
                or active.get("status") != "preparing_fixture"
                or active.get("expires_at", 0) <= now):
            raise RuntimeError("The fixture-preparation lease was cancelled, expired or replaced")
        _, session = state.read("leases/demo.json")
        if (not session or session.get("expires_at", 0) <= now
                or session.get("expires_at") != active.get("session_expires_at")
                or session["expires_at"] - now < load_tests.PROFILES[active["profile"]] + 600):
            raise RuntimeError("The active VM session changed or lacks time for this profile and cleanup")


def prepare_application(origin, admin_email, admin_password, accounts, check_active=None):
    if check_active:
        check_active()
    status, response = api_request(origin, "", "POST", "/api/auth/login",
                                   {"email": admin_email, "password": admin_password})
    if status != 200 or not isinstance(response.get("accessToken"), str):
        raise RuntimeError("Platform administrator login failed; load data was not seeded")
    bearer = response["accessToken"]
    seeded = []
    for start in range(0, len(accounts), MAX_BATCH):
        if check_active:
            check_active()
        status, value = api_request(origin, bearer, "POST", "/api/admin/demo-data/load-fixture",
                                    {"cuentas": accounts[start:start + MAX_BATCH]})
        if status != 200 or not isinstance(value.get("cuentas"), list):
            raise RuntimeError("The application load-fixture seeder rejected a synthetic account batch")
        seeded.extend(value["cuentas"])
        if check_active:
            check_active()
    if [item.get("email") for item in seeded] != [item["email"] for item in accounts]:
        raise RuntimeError("The application load-fixture seeder returned an incomplete account set")
    return seeded


def pin_operations(token, project, seeded):
    operations = {}
    accounts = []
    all_ids = set()
    for account in seeded:
        email = account.get("email")
        journey = account.get("jornadaId")
        events = account.get("operaciones")
        if (not isinstance(email, str) or not re.fullmatch(r"opt06-load-(?:00[1-9]|0[1-4][0-9]|050)@nexoruta\.test", email)
                or not isinstance(journey, str) or not re.fullmatch(
                    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", journey)
                or journey in operations or not isinstance(events, list) or len(events) != 50):
            raise RuntimeError("The application returned an invalid synthetic journey fixture")
        for sequence, event in enumerate(events, start=2):
            event_id = event.get("id") if isinstance(event, dict) else None
            if (not isinstance(event_id, str) or not re.fullmatch(
                    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", event_id)
                    or event_id in all_ids or event.get("tipo") != "Posicion"
                    or event.get("secuencia") != sequence or event.get("envioId") is not None
                    or event.get("versionEnvio") is not None or not isinstance(event.get("ocurridaEn"), str)):
                raise RuntimeError("The application returned an invalid position replay sequence")
            all_ids.add(event_id)
        operations[journey] = events
        accounts.append({"email": email, "jornadaId": journey})

    operation_bytes = json.dumps(operations, separators=(",", ":"), sort_keys=True).encode()
    digest = hashlib.sha256(operation_bytes).hexdigest()
    object_name = f"fixtures/opt06-{digest[:32]}/operations.json"
    bucket = f"{project}-nexoruta-load-fixtures"
    encoded_bucket = urllib.parse.quote(bucket, safe="")
    encoded_object = urllib.parse.quote(object_name, safe="")
    upload_url = ("https://storage.googleapis.com/upload/storage/v1/b/" + encoded_bucket
                  + "/o?uploadType=media&ifGenerationMatch=0&name=" + encoded_object)
    status, _ = google_request(token, "POST", upload_url, operation_bytes, "application/json")
    if status not in (200, 201):
        if status != 412:
            raise RuntimeError(f"Could not create the immutable operation fixture (HTTP {status})")
        read_url = f"https://storage.googleapis.com/storage/v1/b/{encoded_bucket}/o/{encoded_object}?alt=media"
        read_status, stored = google_request(token, "GET", read_url)
        if read_status != 200 or hashlib.sha256(stored).hexdigest() != digest:
            raise RuntimeError("An existing immutable operation fixture does not match its checksum")
    return accounts, object_name, digest


def main():
    config = load_tests.config()
    project = config["GCP_PROJECT_ID"]
    run_id = os.environ.get("NEXORUTA_LOAD_PREPARATION_RUN_ID", "")
    if not re.fullmatch(r"[a-f0-9-]{36}", run_id):
        raise ValueError("A valid fixture-preparation run ID is required")
    token = access_token(project)
    current, current_bytes, current_version = secret_version(token, project)
    admin_email, password = preparer_credentials(token, project)
    origin = load_tests.application_origin(config)
    check_active = lambda: assert_preparation_active(config, token, run_id)
    check_active()
    status, _ = api_request(origin, "", "GET", "/ready")
    if status != 200:
        raise RuntimeError("The remote application is not ready for fixture preparation")
    accounts = fixture_accounts(current, token, project)
    seeded = prepare_application(origin, admin_email, password, accounts, check_active)
    check_active()
    prepared_accounts, object_name, digest = pin_operations(token, project, seeded)
    credentials = {item["email"]: item["password"] for item in accounts}
    fixture = {
        "fixtureStatus": "ready",
        "readPath": READ_PATH,
        "operationsObject": object_name,
        "operationsSha256": digest,
        "accounts": [{**item, "password": credentials[item["email"]]} for item in prepared_accounts],
    }
    final_bytes = json.dumps(fixture, separators=(",", ":"), sort_keys=True).encode()
    check_active()
    if current_bytes != final_bytes:
        version = add_secret_version(token, project, fixture)
    else:
        version = current_version
    print(json.dumps({"fixture_version": version, "accounts": len(prepared_accounts),
                      "operations": len(prepared_accounts) * 50, "operations_object": object_name,
                      "operations_sha256": digest}))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"fixture_version={version}\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, RuntimeError, ValueError, subprocess.SubprocessError,
            urllib.error.URLError, json.JSONDecodeError) as error:
        print(f"Load fixture preparation failed safely: {error}", file=sys.stderr)
        raise SystemExit(1)
