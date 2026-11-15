"""NFR-14 isolated-project reproduction controls and protected CI evidence binding."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

import ci_evidence
import image_inventory
import integration

REPOSITORY = "NexoRuta/NexoRuta"
ENVIRONMENT = "nexoruta-demo"
WORKFLOW_REF = f"{REPOSITORY}/.github/workflows/reproduce.yml@refs/heads/main"
REGION = "southamerica-west1"
ZONE = REGION + "-a"
SECONDARY_ZONE = REGION + "-b"
RUN_ID = re.compile(r"[a-f0-9]{32}\Z")
PROJECT_ID = re.compile(r"nfr14-r-[a-f0-9]{16}\Z")
SHA_256 = re.compile(r"[a-f0-9]{64}\Z")
RELEASE_ID = re.compile(r"release-[a-f0-9]{32}\Z")
SERVICES = ("api", "worker", "admin", "backoffice", "commerce", "tracking")
REPRO_LOCK_OBJECT = "locks/nfr14-repro-control.json"
RUN_INVENTORY_PREFIX = "nfr14/reproduction/runs"
REPRO_WORK_ROOT = Path(tempfile.gettempdir()) / "nfr14-reproduction"
INVENTORY_SCHEMA = 1
VARIABLE_NAMES = (
    "NFR14_REPRO_RUN_ID", "NFR14_REPRO_INTEGRATION_TAG", "NFR14_REPRO_PROJECT_ID",
    "NFR14_REPRO_PROJECT_NUMBER", "NFR14_REPRO_STATE_BUCKET", "NFR14_REPRO_DELIVERY_BUCKET",
    "NFR14_REPRO_WORKLOAD_IDENTITY_PROVIDER", "NFR14_REPRO_DEPLOY_SERVICE_ACCOUNT",
)


class GCSJsonObjects:
    """Generation-guarded JSON and private plan objects in the external control bucket."""

    def __init__(self, bucket, access_token, *, opener=urllib.request.urlopen):
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", bucket):
            raise ValueError("Invalid NFR-14 control bucket")
        if not isinstance(access_token, str) or not access_token.strip():
            raise ValueError("No Google access token is available for the control bucket")
        self.bucket, self.access_token, self.opener = bucket, access_token.strip(), opener
        self.base = ("https://storage.googleapis.com/storage/v1/b/"
                     + urllib.parse.quote(bucket, safe="") + "/o/")

    @staticmethod
    def _object_name(name):
        if (not isinstance(name, str) or not name or name.startswith("/")
                or any(part in ("", ".", "..") for part in name.split("/"))
                or any(character in name for character in ("\\", "\x00"))):
            raise ValueError("Invalid control object name")
        return name

    def request(self, method, url, body=None):
        headers = {"Authorization": "Bearer " + self.access_token}
        if body is not None:
            headers["Content-Type"] = "application/json" if isinstance(body, dict) else "application/octet-stream"
        data = json.dumps(body, sort_keys=True, separators=(",", ":")).encode() if isinstance(body, dict) else body
        request = urllib.request.Request(url, method=method, data=data, headers=headers)
        try:
            with self.opener(request, timeout=30) as response:
                payload = response.read(4 * 1024 * 1024 + 1)
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise RuntimeError("Could not access the NFR-14 control bucket") from error
        if len(payload) > 4 * 1024 * 1024:
            raise ValueError("NFR-14 control object exceeds the allowed size")
        if not payload:
            return {}
        try:
            return json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return payload

    def read(self, name):
        name = self._object_name(name)
        url = self.base + urllib.parse.quote(name, safe="")
        try:
            metadata = self.request("GET", url + "?fields=generation,name")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return "0", None
            raise RuntimeError("Could not inspect the NFR-14 control object") from None
        generation = str(metadata.get("generation", ""))
        if not generation.isdigit() or int(generation) < 1:
            raise ValueError("The NFR-14 control object has an invalid generation")
        try:
            value = self.request("GET", url + "?alt=media&generation=" + generation)
        except urllib.error.HTTPError:
            raise RuntimeError("Could not read the exact NFR-14 control object generation") from None
        return generation, value

    def write(self, name, expected_generation, payload):
        name = self._object_name(name)
        query = urllib.parse.urlencode({"uploadType": "media", "name": name,
                                        "ifGenerationMatch": str(expected_generation)})
        url = ("https://storage.googleapis.com/upload/storage/v1/b/"
               + urllib.parse.quote(self.bucket, safe="") + "/o?" + query)
        result = self.request("POST", url, payload)
        generation = str(result.get("generation", ""))
        if not generation.isdigit() or int(generation) < 1:
            raise ValueError("The NFR-14 control write returned an invalid generation")
        return generation

    def delete(self, name, generation):
        name = self._object_name(name)
        query = urllib.parse.urlencode({"ifGenerationMatch": str(generation)})
        try:
            self.request("DELETE", self.base + urllib.parse.quote(name, safe="") + "?" + query)
        except urllib.error.HTTPError as error:
            if error.code not in (404, 412):
                raise RuntimeError("Could not delete the exact NFR-14 control object generation") from None
            raise


def _access_token():
    token = os.environ.get("CLOUDSDK_AUTH_ACCESS_TOKEN") or os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN")
    if token and token.strip():
        return token.strip()
    result = subprocess.run(["gcloud", "auth", "print-access-token"],
                            capture_output=True, text=True, check=False)
    if result.returncode or not result.stdout.strip():
        raise RuntimeError("No Google Cloud preparation identity is available")
    return result.stdout.strip()


def _github_token():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token and token.strip():
        return token.strip()
    result = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False)
    if result.returncode or not result.stdout.strip():
        raise RuntimeError("No GitHub token is available for the NFR-14 control operation")
    return result.stdout.strip()


@contextmanager
def _github_token_scope(token):
    previous = os.environ.get("GH_TOKEN")
    os.environ["GH_TOKEN"] = token
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("GH_TOKEN", None)
        else:
            os.environ["GH_TOKEN"] = previous


def _github_api(method, path, token, payload=None, *, opener=urllib.request.urlopen):
    if not isinstance(token, str) or not token.strip():
        raise ValueError("A GitHub token is required for this NFR-14 control operation")
    repository = os.environ.get("GITHUB_REPOSITORY", REPOSITORY)
    if repository != REPOSITORY or path.startswith(("/", "//")):
        raise ValueError("GitHub control operations are restricted to the NexoRuta repository")
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    body = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{base}/repos/{repository}/{path}", method=method, data=body,
        headers={"Authorization": "Bearer " + token.strip(),
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 **({"Content-Type": "application/json"} if body is not None else {})},
    )
    try:
        with opener(request, timeout=30) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError("GitHub returned an oversized NFR-14 control response")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        # Never include response bodies: a service may echo request data.
        raise RuntimeError(f"GitHub NFR-14 control request failed (HTTP {error.code})") from None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise RuntimeError("Could not complete the GitHub NFR-14 control request") from error


def _environment_variables(token):
    environment = urllib.parse.quote(ENVIRONMENT, safe="")
    values = {}
    page = 1
    while True:
        result = _github_api(
            "GET", f"environments/{environment}/variables?per_page=100&page={page}", token,
        )
        rows = result.get("variables")
        if not isinstance(rows, list):
            raise ValueError("GitHub returned a malformed environment variable list")
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str):
                raise ValueError("GitHub returned a malformed environment variable identity")
            if row["name"] in values:
                raise ValueError("GitHub returned duplicate environment variable names")
            values[row["name"]] = row
        if len(rows) < 100:
            break
        page += 1
    return values


def _set_reproduction_variables(token, values):
    if set(values) != set(VARIABLE_NAMES) or any(not isinstance(value, str) or not value for value in values.values()):
        raise ValueError("The exact eight public NFR-14 reproduction variables are required")
    existing = _environment_variables(token)
    if any(name in existing for name in VARIABLE_NAMES):
        raise ValueError("NFR-14 reproduction variables appeared during preparation; refusing to overwrite them")
    environment = urllib.parse.quote(ENVIRONMENT, safe="")
    for name in VARIABLE_NAMES:
        encoded = urllib.parse.quote(name, safe="")
        payload = {"name": name, "value": values[name]}
        _github_api("POST", f"environments/{environment}/variables", token, payload)


def _delete_reproduction_variables(token, expected_values):
    if set(expected_values) != set(VARIABLE_NAMES):
        raise ValueError("Cleanup requires the exact eight NFR-14 reproduction variable identities")
    existing = _environment_variables(token)
    # Validate every existing value before deleting any variable. These values are
    # public GitHub variables, never secrets; they are not included in diagnostics.
    for name in VARIABLE_NAMES:
        row = existing.get(name)
        if row is not None and row.get("value") != expected_values[name]:
            raise ValueError("GitHub NFR-14 variables belong to another run; refusing cleanup")
    environment = urllib.parse.quote(ENVIRONMENT, safe="")
    for name in VARIABLE_NAMES:
        if name in existing:
            _github_api("DELETE", f"environments/{environment}/variables/{urllib.parse.quote(name, safe='')}", token)


def _dispatch_reproduction(token, run_id, integration_tag):
    _github_api("POST", "actions/workflows/reproduce.yml/dispatches", token,
                {"ref": "main", "inputs": {"run_id": run_id, "integration_tag": integration_tag}})
    return datetime.now(timezone.utc)


def _matching_reproduction_runs(token, run_id):
    result = _github_api(
        "GET", "actions/workflows/reproduce.yml/runs?branch=main&event=workflow_dispatch&per_page=100", token,
    )
    rows = result.get("workflow_runs")
    if not isinstance(rows, list):
        raise ValueError("GitHub returned a malformed NFR-14 workflow run list")
    expected_title = "NexoRuta reproduction / " + run_id
    matches = [row for row in rows if isinstance(row, dict)
               and row.get("display_title") == expected_title
               and row.get("event") == "workflow_dispatch"
               and row.get("head_branch") == "main"
               and row.get("path", "").split("@", 1)[0] == ".github/workflows/reproduce.yml"]
    return matches


def _wait_reproduction(token, run_id, dispatched_at, *, timeout_seconds=6 * 60 * 60,
                       poll_seconds=20, sleep=time.sleep, clock=time.monotonic, report=print):
    deadline = clock() + timeout_seconds
    run = None
    while clock() < deadline:
        matches = _matching_reproduction_runs(token, run_id)
        if len(matches) > 1:
            raise ValueError("More than one workflow run matches this unique NFR-14 run ID")
        if matches:
            run = matches[0]
            try:
                created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            except (KeyError, AttributeError, TypeError, ValueError):
                raise ValueError("GitHub returned an invalid NFR-14 workflow creation time") from None
            if created < dispatched_at - timedelta(minutes=2):
                raise ValueError("The matching workflow run predates this NFR-14 dispatch")
            if run.get("status") == "completed":
                return run
            report(f"Reproducción NFR-14: run {run.get('id')} en estado {run.get('status', 'desconocido')}.")
        sleep(poll_seconds)
    raise TimeoutError("The exact NFR-14 reproduction workflow did not finish within six hours")


def validate_run_id(value):
    if not isinstance(value, str) or not RUN_ID.fullmatch(value):
        raise ValueError("run_id must be a unique 32-character lowercase hexadecimal ID")
    return value


def project_id_for_run(run_id):
    validate_run_id(run_id)
    return "nfr14-r-" + run_id[:16]


def validate_runtime_environment(environment, *, input_run_id=None, input_tag=None):
    """Fail closed on mixed demo/reproduction destinations before any cloud mutation."""
    run_id = validate_run_id(environment.get("NFR14_REPRO_RUN_ID", ""))
    tag = environment.get("NFR14_REPRO_INTEGRATION_TAG", "")
    if not re.fullmatch(integration.TAG, tag):
        raise ValueError("The reproduction integration tag is missing or invalid")
    if input_run_id is not None and input_run_id != run_id:
        raise ValueError("workflow_dispatch run_id does not match the locked reproduction environment")
    if input_tag is not None and input_tag != tag:
        raise ValueError("workflow_dispatch integration_tag does not match the locked reproduction environment")
    project_id = environment.get("NFR14_REPRO_PROJECT_ID", "")
    if not PROJECT_ID.fullmatch(project_id) or project_id != project_id_for_run(run_id):
        raise ValueError("The reproduction project ID does not match its unique run identity")
    project_number = environment.get("NFR14_REPRO_PROJECT_NUMBER", "")
    if not re.fullmatch(r"[1-9][0-9]{4,19}", str(project_number)):
        raise ValueError("The reproduction project number is missing or invalid")

    state_bucket = environment.get("NFR14_REPRO_STATE_BUCKET", "")
    delivery_bucket = environment.get("NFR14_REPRO_DELIVERY_BUCKET", "")
    provider = environment.get("NFR14_REPRO_WORKLOAD_IDENTITY_PROVIDER", "")
    deployer = environment.get("NFR14_REPRO_DEPLOY_SERVICE_ACCOUNT", "")
    if state_bucket != f"{project_id}-tofu-state" or delivery_bucket != f"{project_id}-nexoruta-delivery":
        raise ValueError("Reproduction buckets do not belong to the explicit reproduction project")
    expected_provider = (
        f"projects/{project_number}/locations/global/workloadIdentityPools/nexoruta-github/providers/demo-vm"
    )
    if provider != expected_provider:
        raise ValueError("The reproduction WIF provider does not belong to the expected project number")
    if deployer != f"nexoruta-demo-deployer@{project_id}.iam.gserviceaccount.com":
        raise ValueError("The reproduction deployer does not belong to the explicit reproduction project")

    main_project = environment.get("NFR14_MAIN_PROJECT_ID", "")
    main_state = environment.get("NFR14_MAIN_STATE_BUCKET", "")
    main_delivery = environment.get("NFR14_MAIN_DELIVERY_BUCKET", "")
    main_provider = environment.get("NFR14_MAIN_WORKLOAD_IDENTITY_PROVIDER", "")
    main_deployer = environment.get("NFR14_MAIN_DEPLOY_SERVICE_ACCOUNT", "")
    if not main_project or not main_state or not main_delivery or not main_provider or not main_deployer:
        raise ValueError("The main-project identities are required to reject mixed deployment targets")
    if (project_id == main_project or state_bucket == main_state or delivery_bucket == main_delivery
            or provider == main_provider or deployer == main_deployer):
        raise ValueError("A reproduction target points to the persistent main project")

    mapped = {
        "GCP_PROJECT_ID": project_id,
        "GCP_REGION": REGION,
        "GCP_ZONE": ZONE,
        "GCP_SECONDARY_ZONE": SECONDARY_ZONE,
        "GCP_STATE_BUCKET": state_bucket,
        "GCP_DELIVERY_BUCKET": delivery_bucket,
        "GCP_WORKLOAD_IDENTITY_PROVIDER": provider,
        "GCP_DEPLOY_SERVICE_ACCOUNT": deployer,
    }
    if environment.get("NEXORUTA_EXECUTION_PROFILE") != "reproduction":
        raise ValueError("NEXORUTA_EXECUTION_PROFILE must explicitly be reproduction")
    if environment.get("BOOTSTRAP_WIF_PROFILE") != "reproduction":
        raise ValueError("BOOTSTRAP_WIF_PROFILE must explicitly be reproduction")
    if any(environment.get(name) != expected for name, expected in mapped.items()):
        raise ValueError("GCP environment values do not match the explicit reproduction target")
    if environment.get("GCP_BASE_DOMAIN", "") != "" or environment.get("GCP_MANAGE_DNS", "false") != "false":
        raise ValueError("The reproduction must not use or manage the demo's DNS domain")
    if environment.get("RELEASE_CHANNEL") not in (None, "main"):
        raise ValueError("The reproduction must publish only its isolated main channel")

    if environment.get("GITHUB_ACTIONS") == "true":
        if (environment.get("GITHUB_REPOSITORY") != REPOSITORY
                or environment.get("GITHUB_REF") != "refs/heads/main"
                or environment.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
                or environment.get("GITHUB_WORKFLOW_REF") != WORKFLOW_REF):
            raise ValueError("Reproduction WIF is only valid for reproduce.yml dispatched from main")
    return {
        "run_id": run_id, "integration_tag": tag, "project_id": project_id,
        "project_number": str(project_number), "state_bucket": state_bucket,
        "delivery_bucket": delivery_bucket, "workload_identity_provider": provider,
        "deploy_service_account": deployer,
    }


def validate_admin_profile(*, run_id, integration_tag, control_project_id, control_bucket,
                           parent, billing_account_id, monthly_alert_budget_usd,
                           approved_cost_ceiling_usd, estimated_window_cost_usd, window_hours,
                           main_project_id):
    validate_run_id(run_id)
    if not re.fullmatch(integration.TAG, integration_tag or ""):
        raise ValueError("The requested integration tag is invalid")
    project_id = project_id_for_run(run_id)
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", main_project_id or ""):
        raise ValueError("The persistent main project ID is required for an isolation check")
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", control_project_id or ""):
        raise ValueError("control_project_id must be explicit and valid")
    if control_project_id in (project_id, main_project_id):
        raise ValueError("The control state must be outside both the demo and disposable project")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", control_bucket or ""):
        raise ValueError("control_bucket must be explicit and valid")
    if control_bucket in (f"{main_project_id}-tofu-state", f"{main_project_id}-nexoruta-delivery",
                          f"{project_id}-tofu-state", f"{project_id}-nexoruta-delivery"):
        raise ValueError("The control state cannot reuse an application state or delivery bucket")
    if not re.fullmatch(r"(?:organizations|folders)/[1-9][0-9]{3,19}", parent or ""):
        raise ValueError("parent must be the explicitly approved organizations/<id> or folders/<id>")
    if not re.fullmatch(r"[A-Z0-9-]{6,30}", billing_account_id or ""):
        raise ValueError("billing_account_id must be explicitly approved")
    try:
        budget = Decimal(str(monthly_alert_budget_usd))
        ceiling = Decimal(str(approved_cost_ceiling_usd))
        estimate = Decimal(str(estimated_window_cost_usd))
        hours = Decimal(str(window_hours))
    except InvalidOperation as error:
        raise ValueError("Budget, estimate, cost ceiling, and window must be explicit numbers") from error
    if (not budget.is_finite() or budget < 1 or budget > 10000 or budget != budget.to_integral_value()
            or not ceiling.is_finite() or ceiling <= 0
            or not estimate.is_finite() or estimate < 0
            or estimate > ceiling
            or not hours.is_finite() or hours < 1 or hours > 4):
        raise ValueError("The approved cost window is missing, exceeds its ceiling, or exceeds four hours")
    return {
        "run_id": run_id, "integration_tag": integration_tag, "project_id": project_id,
        "control_project_id": control_project_id, "control_bucket": control_bucket,
        "parent": parent, "billing_account_id": billing_account_id,
        "monthly_alert_budget_usd": str(budget), "approved_cost_ceiling_usd": str(ceiling),
        "estimated_window_cost_usd": str(estimate), "window_hours": str(hours),
    }


def _gcloud_json(*arguments, allow_not_found=False):
    import bootstrap_setup
    return bootstrap_setup._json_command("gcloud", *arguments, allow_not_found=allow_not_found)


def _validate_control_bucket(control_project_id, control_bucket, access_token):
    project = _gcloud_json("projects", "describe", control_project_id, "--format=json")
    if project.get("projectId") != control_project_id or project.get("lifecycleState") != "ACTIVE":
        raise ValueError("The explicit control project is missing or inactive")
    project_number = str(project.get("projectNumber", ""))
    if not project_number.isdigit():
        raise ValueError("The control project has no stable project number")
    request = urllib.request.Request(
        "https://storage.googleapis.com/storage/v1/b/" + urllib.parse.quote(control_bucket, safe=""),
        headers={"Authorization": "Bearer " + access_token},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            bucket = json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Could not inspect the control bucket (HTTP {error.code})") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise RuntimeError("Could not inspect the explicit control bucket") from None
    iam = bucket.get("iamConfiguration") or {}
    if (bucket.get("name") != control_bucket or str(bucket.get("projectNumber", "")) != project_number
            or (bucket.get("versioning") or {}).get("enabled") is not True
            or (iam.get("uniformBucketLevelAccess") or {}).get("enabled") is not True
            or iam.get("publicAccessPrevention") != "enforced"):
        raise ValueError("The control bucket must belong to the explicit control project, be private, and be versioned")
    return project_number, bucket


def _inventory_name(run_id):
    validate_run_id(run_id)
    return f"{RUN_INVENTORY_PREFIX}/{run_id}/inventory.json"


def _read_inventory(objects, run_id):
    generation, value = objects.read(_inventory_name(run_id))
    if value is None:
        return generation, None
    if (not isinstance(value, dict) or type(value.get("schema_version")) is not int
            or value.get("schema_version") != INVENTORY_SCHEMA or value.get("run_id") != run_id
            or value.get("project_id") != project_id_for_run(run_id)):
        raise ValueError("The NFR-14 run inventory is malformed or belongs to another project")
    return generation, value


def _write_inventory(objects, run_id, generation, value):
    if not isinstance(value, dict) or value.get("run_id") != run_id:
        raise ValueError("Cannot write an inventory for a different NFR-14 run")
    value = {**value, "schema_version": INVENTORY_SCHEMA, "run_id": run_id,
             "project_id": project_id_for_run(run_id),
             "updated_at": datetime.now(timezone.utc).isoformat()}
    return objects.write(_inventory_name(run_id), generation, value)


@contextmanager
def _locked_control(control_bucket, token):
    from control_lock import JsonStorage, control_lock
    store = JsonStorage(control_bucket, token, object_name=REPRO_LOCK_OBJECT)
    with control_lock({}, store=store, object_name=REPRO_LOCK_OBJECT,
                      label="NFR-14 reproduction") as lease:
        yield lease


def _private_path(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except OSError:
        pass
    return path


def _prepare_evidence_directory(path):
    destination = Path(path).expanduser().resolve()
    repository = Path(__file__).resolve().parents[2]
    if destination == repository or destination.is_relative_to(repository):
        raise ValueError("NFR-14 evidence must be stored outside the repository")
    if destination.exists():
        if not destination.is_dir():
            raise ValueError("The NFR-14 evidence path must be a directory")
        if any(destination.iterdir()):
            raise ValueError("The NFR-14 evidence directory must be empty for a new reproduction run")
    else:
        destination.mkdir(parents=True, exist_ok=True)
    try:
        destination.chmod(0o700)
    except OSError:
        pass
    return destination


def _project_workdir(profile):
    run_id = validate_run_id(profile["run_id"])
    workdir = REPRO_WORK_ROOT / run_id / "project"
    _private_path(workdir.parent)
    marker = workdir / ".nfr14-owner.json"
    identity = {
        "run_id": run_id, "project_id": profile["project_id"],
        "control_project_id": profile["control_project_id"],
        "control_bucket": profile["control_bucket"],
        "backend_prefix": f"{RUN_INVENTORY_PREFIX}/{run_id}/project-state",
    }
    if marker.exists():
        try:
            recorded = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("The private NFR-14 OpenTofu workspace marker is unreadable") from error
        if recorded != identity:
            raise ValueError("The private OpenTofu workspace belongs to a different reproduction target")
    else:
        if workdir.exists() and any(workdir.iterdir()):
            raise ValueError("The private OpenTofu workspace is nonempty and has no ownership marker")
        workdir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).resolve().parents[2] / "infra/gcp/reproduction-project"
        for path in source.iterdir():
            if path.is_file() and (path.suffix == ".tf" or path.name == ".terraform.lock.hcl"):
                shutil.copy2(path, workdir / path.name)
        marker.write_text(json.dumps(identity, sort_keys=True), encoding="utf-8")
        try:
            marker.chmod(0o600)
        except OSError:
            pass
    if not (workdir / ".terraform.lock.hcl").is_file() or not (workdir / "main.tf").is_file():
        raise RuntimeError("The private OpenTofu workspace is missing its pinned project module")
    if any(workdir.glob("terraform.tfstate*")):
        raise ValueError("The private OpenTofu project module contains unexpected local state")
    return workdir, identity


def _tofu(profile, *arguments, capture=False):
    workdir, _ = _project_workdir(profile)
    result = subprocess.run(["tofu", f"-chdir={workdir}", *arguments], text=True,
                            capture_output=True, check=False)
    if result.returncode:
        detail = (result.stderr or "").strip()
        raise RuntimeError(f"OpenTofu {arguments[0] if arguments else 'command'} failed: {detail[:1200]}")
    return result.stdout if capture else None


def _tofu_init(profile):
    prefix = f"{RUN_INVENTORY_PREFIX}/{profile['run_id']}/project-state"
    _tofu(profile, "init", "-reconfigure", "-input=false", "-lockfile=readonly",
          f"-backend-config=bucket={profile['control_bucket']}", f"-backend-config=prefix={prefix}")
    _tofu(profile, "validate")


def _module_inputs(profile):
    return {
        "project_id": profile["project_id"], "run_id": profile["run_id"],
        "control_project_id": profile["control_project_id"],
        "parent": profile["parent"], "billing_account_id": profile["billing_account_id"],
        "approved_budget_usd": int(Decimal(profile["monthly_alert_budget_usd"])),
    }


def _private_inputs(profile):
    workdir, _ = _project_workdir(profile)
    path = workdir / ".nfr14-inputs.json"
    path.write_text(json.dumps(_module_inputs(profile), sort_keys=True, separators=(",", ":")), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def _resource_changes(plan):
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        raise ValueError("OpenTofu project plan is malformed")
    result = {}
    for item in changes:
        if not isinstance(item, dict) or not isinstance(item.get("change"), dict):
            raise ValueError("OpenTofu project plan contains a malformed resource change")
        actions = item["change"].get("actions")
        if not isinstance(actions, list) or any(not isinstance(action, str) for action in actions):
            raise ValueError("OpenTofu project plan contains invalid actions")
        address = item.get("address")
        if item.get("mode", "managed") == "data":
            if address != "data.google_project.reproduction" or actions not in (["read"], ["no-op"]):
                raise ValueError("OpenTofu project plan contains an unexpected data-source action")
            continue
        if item.get("mode", "managed") != "managed":
            raise ValueError("OpenTofu project plan contains an unsupported resource mode")
        if actions != ["no-op"]:
            if address in result:
                raise ValueError("OpenTofu project plan repeats a resource address")
            result[address] = item
    return result


def _validate_project_plan(plan, profile, *, operation):
    changes = _resource_changes(plan)
    expected = {"google_project.reproduction", "google_billing_budget.reproduction"}
    if operation == "create":
        if changes and set(changes) != expected:
            raise ValueError("Project creation plan includes resources outside the disposable project and its budget")
        for address, item in changes.items():
            if item["change"]["actions"] != ["create"]:
                raise ValueError("Project creation plan contains a delete, replacement, or unexpected action")
        project = changes.get("google_project.reproduction")
        if project:
            after = project["change"].get("after") or {}
            if (after.get("project_id") != profile["project_id"]
                    or after.get("billing_account") != profile["billing_account_id"]
                    or after.get("deletion_policy") != "DELETE"):
                raise ValueError("Project creation plan does not match the exact approved target and deletion policy")
        budget = changes.get("google_billing_budget.reproduction")
        if budget:
            after = budget["change"].get("after") or {}
            if after.get("billing_account") != profile["billing_account_id"]:
                raise ValueError("Project budget plan targets a different billing account")
    elif operation == "destroy":
        if set(changes) != expected:
            raise ValueError("Destroy plan must contain exactly the disposable project and its budget")
        for address, item in changes.items():
            if item["change"].get("actions") != ["delete"]:
                raise ValueError("Destroy plan contains a replacement, create, or unsupported action")
        before = changes["google_project.reproduction"]["change"].get("before") or {}
        if (before.get("project_id") != profile["project_id"]
                or not re.fullmatch(r"[1-9][0-9]{4,19}", str(before.get("number", "")))):
            raise ValueError("Destroy plan does not identify the exact registered reproduction project")
        budget_before = changes["google_billing_budget.reproduction"]["change"].get("before") or {}
        if budget_before.get("billing_account") != profile["billing_account_id"]:
            raise ValueError("Destroy plan budget belongs to a different billing account")
    else:
        raise ValueError("Unsupported NFR-14 project plan operation")
    return [{"address": address, "actions": changes[address]["change"]["actions"]}
            for address in sorted(changes)]


def _plan_project(profile, *, operation):
    _tofu_init(profile)
    inputs = _private_inputs(profile)
    workdir, _ = _project_workdir(profile)
    plan_file = workdir / ("nfr14-create.tfplan" if operation == "create" else "nfr14-destroy.tfplan")
    command = ["plan", "-input=false", "-lock-timeout=5m", f"-var-file={inputs}", f"-out={plan_file}"]
    if operation == "destroy":
        command.insert(1, "-destroy")
    _tofu(profile, *command)
    plan = json.loads(_tofu(profile, "show", "-json", str(plan_file), capture=True))
    actions = _validate_project_plan(plan, profile, operation=operation)
    digest = hashlib.sha256(plan_file.read_bytes()).hexdigest()
    return plan_file, {"actions": actions, "plan_sha256": digest, "operation": operation}


def _project_state(profile):
    state = json.loads(_tofu(profile, "show", "-json", capture=True))
    if not isinstance(state, dict) or not isinstance(state.get("values"), dict):
        raise ValueError("External reproduction project state is missing or unreadable")
    resources = []
    def collect(module):
        if not isinstance(module, dict):
            return
        resources.extend(module.get("resources", []))
        for child in module.get("child_modules", []):
            collect(child)
    collect(state["values"].get("root_module") or {})
    expected = {("google_project", "reproduction"), ("google_billing_budget", "reproduction")}
    managed = [item for item in resources if isinstance(item, dict) and item.get("mode", "managed") == "managed"]
    data = [item for item in resources if isinstance(item, dict) and item.get("mode") == "data"]
    identities = {(item.get("type"), item.get("name")) for item in managed}
    data_identities = {(item.get("type"), item.get("name")) for item in data}
    if resources and (identities != expected or data_identities != {("google_project", "reproduction")}):
        raise ValueError("External project state contains resources outside the registered project and budget")
    outputs = state["values"].get("outputs") or {}
    def output(name):
        value = (outputs.get(name) or {}).get("value")
        if value is None:
            raise ValueError(f"External project state is missing the {name} output")
        return value
    result = {
        "lineage": state.get("lineage"), "serial": state.get("serial"),
        "project_id": output("project_id"), "project_number": str(output("project_number")),
        "budget_id": output("budget_id"),
        "budget_filter_project_number": str(output("budget_filter_project_number")),
    }
    if resources:
        project = next(item for item in managed if item.get("type") == "google_project")
        budget = next(item for item in managed if item.get("type") == "google_billing_budget")
        project_values = project.get("values") or {}
        budget_values = budget.get("values") or {}
        filters = budget_values.get("budget_filter") or []
        projects = filters[0].get("projects", []) if filters else []
        parent_kind, parent_id = profile["parent"].split("/", 1)
        expected_parent_key = "folder_id" if parent_kind == "folders" else "org_id"
        opposite_parent_key = "org_id" if expected_parent_key == "folder_id" else "folder_id"
        if (project_values.get("project_id") != profile["project_id"]
                or project_values.get("deletion_policy") != "DELETE"
                or project_values.get("billing_account") != profile["billing_account_id"]
                or str(project_values.get(expected_parent_key, "")) != parent_id
                or project_values.get(opposite_parent_key) not in (None, "")
                or budget_values.get("billing_account") != profile["billing_account_id"]
                or projects != [f"projects/{result['project_number']}"]
                or result["budget_filter_project_number"] != result["project_number"]):
            raise ValueError("External project state does not match the exact project/billing/budget identity")
    if (result["project_id"] != profile["project_id"]
            or not re.fullmatch(r"[1-9][0-9]{4,19}", result["project_number"])
            or not isinstance(result["lineage"], str) or not result["lineage"]
            or type(result["serial"]) is not int or result["serial"] < 0):
        raise ValueError("External project state outputs are incomplete or invalid")
    return result


def _verify_project_identity(profile, expected_number=None):
    project = _gcloud_json("projects", "describe", profile["project_id"], "--format=json")
    number = str(project.get("projectNumber", ""))
    if (project.get("projectId") != profile["project_id"] or project.get("lifecycleState") != "ACTIVE"
            or not re.fullmatch(r"[1-9][0-9]{4,19}", number)
            or (expected_number is not None and number != str(expected_number))
            or (project.get("labels") or {}).get("nfr14_owner") != "nfr-14"
            or (project.get("labels") or {}).get("nfr14_run") != profile["run_id"][:16]):
        raise ValueError("Google Cloud project is not the active project owned by this NFR-14 run")
    parent_kind, parent_id = profile["parent"].split("/", 1)
    parent = project.get("parent") or {}
    expected_parent_type = "folder" if parent_kind == "folders" else "organization"
    if str(parent.get("id", "")) != parent_id or parent.get("type") != expected_parent_type:
        raise ValueError("Google Cloud project is attached to a different organization or folder")
    billing = _gcloud_json("billing", "projects", "describe", profile["project_id"], "--format=json")
    if (billing.get("billingEnabled") is not True
            or billing.get("billingAccountName") != "billingAccounts/" + profile["billing_account_id"]):
        raise ValueError("Reproduction project billing does not match the explicitly approved account")
    return number


def _fetch_google_json(url, access_token):
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + access_token})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise RuntimeError(f"Could not inspect the approved Google resource (HTTP {error.code})") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise RuntimeError("Could not inspect the approved Google resource") from None


def _verify_budget(profile, state, access_token):
    name = state.get("budget_id", "")
    if not isinstance(name, str) or not re.fullmatch(
        r"billingAccounts/[A-Z0-9-]{6,30}/budgets/[A-Za-z0-9-]+", name,
    ) or not name.startswith("billingAccounts/" + profile["billing_account_id"] + "/budgets/"):
        raise ValueError("The isolated project budget has an invalid or unexpected identity")
    budget = _fetch_google_json("https://billingbudgets.googleapis.com/v1/" + name, access_token)
    expected_project = f"projects/{state['project_number']}"
    amount = (budget or {}).get("amount", {}).get("specifiedAmount", {})
    budget_filter = (budget or {}).get("budgetFilter", {})
    thresholds = {(item.get("thresholdPercent"), item.get("spendBasis", "CURRENT_SPEND"))
                  for item in (budget or {}).get("thresholdRules", [])}
    if (not isinstance(budget, dict) or budget.get("name") != name
            or budget_filter.get("projects") != [expected_project]
            or budget_filter.get("creditTypesTreatment") != "EXCLUDE_ALL_CREDITS"
            or amount.get("currencyCode") != "USD"
            or str(amount.get("units")) != profile["monthly_alert_budget_usd"]
            or not {(0.5, "CURRENT_SPEND"), (0.8, "CURRENT_SPEND"), (1.0, "CURRENT_SPEND")}.issubset(thresholds)):
        raise ValueError("The disposable project budget does not match its approved project and thresholds")
    return name


def _apply_project_create(profile, access_token, *, plan_file=None, summary=None):
    if plan_file is None or summary is None:
        plan_file, summary = _plan_project(profile, operation="create")
    else:
        plan = json.loads(_tofu(profile, "show", "-json", str(plan_file), capture=True))
        actions = _validate_project_plan(plan, profile, operation="create")
        digest = hashlib.sha256(plan_file.read_bytes()).hexdigest()
        if (summary.get("operation") != "create" or summary.get("actions") != actions
                or summary.get("plan_sha256") != digest):
            raise ValueError("The saved project-creation plan changed before apply")
    workdir, _ = _project_workdir(profile)
    _tofu(profile, "apply", "-input=false", "-lock-timeout=5m", str(plan_file))
    state = _project_state(profile)
    project_number = _verify_project_identity(profile, state["project_number"])
    budget_id = _verify_budget(profile, state, access_token)
    if project_number != state["project_number"]:
        raise ValueError("OpenTofu state and Google Cloud report different project numbers")
    return {
        **summary, "project_id": state["project_id"], "project_number": project_number,
        "budget_id": budget_id, "state_lineage": state["lineage"], "state_serial": state["serial"],
        "state_prefix": f"{RUN_INVENTORY_PREFIX}/{profile['run_id']}/project-state",
        "workdir": str(workdir),
    }


def _inventory_update(objects, run_id, mutate):
    generation, inventory = _read_inventory(objects, run_id)
    if inventory is None:
        raise ValueError("The NFR-14 run has no external control inventory")
    updated = mutate(dict(inventory))
    return _write_inventory(objects, run_id, generation, updated), updated


def _inventory_profile(inventory):
    profile = inventory.get("approval")
    if not isinstance(profile, dict):
        raise ValueError("The NFR-14 inventory has no approved administrative profile")
    validated = validate_admin_profile(
        run_id=inventory.get("run_id"), integration_tag=inventory.get("integration_tag"),
        control_project_id=profile.get("control_project_id"), control_bucket=profile.get("control_bucket"),
        parent=profile.get("parent"), billing_account_id=profile.get("billing_account_id"),
        monthly_alert_budget_usd=profile.get("monthly_alert_budget_usd"),
        approved_cost_ceiling_usd=profile.get("approved_cost_ceiling_usd"),
        estimated_window_cost_usd=profile.get("estimated_window_cost_usd"),
        window_hours=profile.get("window_hours"), main_project_id=profile.get("main_project_id"),
    )
    if validated["project_id"] != inventory.get("project_id"):
        raise ValueError("The NFR-14 inventory approval belongs to a different disposable project")
    return validated


def _validate_empty_admin_checkout():
    root = integration.ROOT
    branch = integration.git("branch", "--show-current")
    if branch != "main":
        raise ValueError("Administrative recreation must run from a clean main checkout")
    status = integration.git("status", "--porcelain", "--untracked-files=all", "--ignore-submodules=none")
    if status:
        raise ValueError("Administrative recreation requires a clean checkout including exact gitlinks")
    prohibited = (".env", "backend/.env", "frontend/.env", "mobile/.env", ".local",
                  "backend/.local", "frontend/.local", "mobile/.local")
    if any((root / item).exists() for item in prohibited):
        raise ValueError("Administrative recreation checkout contains a local environment or credential directory")
    for component in ("backend", "frontend", "mobile"):
        for relative in ("bin", "obj", "node_modules"):
            if (root / component / relative).exists():
                raise ValueError("Administrative recreation checkout contains reusable build outputs")


def _download_verification_artifact(actions_run_id, reproduction_run_id, token, *, opener=urllib.request.urlopen):
    if type(actions_run_id) is not int or actions_run_id < 1:
        raise ValueError("The completed GitHub Actions run ID is invalid")
    expected_name = "nfr14-reproduction-verification-" + validate_run_id(reproduction_run_id)
    result = _github_api(
        "GET", f"actions/runs/{actions_run_id}/artifacts?per_page=100", token, opener=opener,
    )
    rows = result.get("artifacts")
    if not isinstance(rows, list):
        raise ValueError("GitHub returned a malformed NFR-14 verification artifact list")
    matches = [row for row in rows if isinstance(row, dict) and row.get("name") == expected_name]
    if len(matches) != 1 or matches[0].get("expired"):
        raise ValueError("The exact NFR-14 verification artifact is missing, duplicated, or expired")
    artifact = matches[0]
    digest = artifact.get("digest")
    if type(artifact.get("id")) is not int or not isinstance(digest, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("The NFR-14 verification artifact has no immutable API identity")
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    repository = os.environ.get("GITHUB_REPOSITORY", REPOSITORY)
    request = urllib.request.Request(
        f"{base}/repos/{repository}/actions/artifacts/{artifact['id']}/zip",
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    opener_no_redirect = urllib.request.build_opener(ci_evidence._NoRedirect)
    try:
        opener_no_redirect.open(request, timeout=30)
        raise RuntimeError("GitHub returned an unexpected verification artifact response")
    except urllib.error.HTTPError as response:
        if response.code not in (301, 302, 303, 307, 308):
            raise RuntimeError(f"Could not download NFR-14 verification artifact (HTTP {response.code})") from None
        location = response.headers.get("Location", "")
    parsed = urllib.parse.urlsplit(location)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("GitHub returned an invalid verification artifact download location")
    try:
        with opener(location, timeout=60) as response:
            archive = response.read(2 * 1024 * 1024 + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RuntimeError("Could not download NFR-14 verification evidence") from error
    if len(archive) > 2 * 1024 * 1024 or "sha256:" + hashlib.sha256(archive).hexdigest() != digest:
        raise ValueError("NFR-14 verification artifact size or digest is invalid")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            files = [item for item in zipped.infolist() if not item.is_dir()]
            if len(files) != 1 or files[0].filename != "nfr14-verification.json" or files[0].file_size > 128 * 1024:
                raise ValueError("NFR-14 verification artifact has an unexpected file layout")
            data = zipped.read(files[0])
    except zipfile.BadZipFile as error:
        raise ValueError("NFR-14 verification artifact is not a valid zip archive") from error
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("NFR-14 verification artifact is not valid JSON") from error
    if (not isinstance(value, dict) or type(value.get("schema_version")) is not int or value.get("schema_version") != 1
            or value.get("run_id") != reproduction_run_id
            or value.get("status") not in ("passed", "failed")):
        raise ValueError("NFR-14 verification artifact does not identify this reproduction")
    allowed = {"schema_version", "status", "run_id", "integration_tag", "project_id", "project_number",
               "observed_at", "finalized_at", "tested_integration", "deployed_release", "checks",
               "session_stop", "failure", "scope"}
    if set(value) - allowed:
        raise ValueError("NFR-14 verification artifact contains fields outside the sanitized evidence allowlist")
    if (not isinstance(value.get("integration_tag"), str)
            or not re.fullmatch(integration.TAG, value["integration_tag"])
            or value.get("project_id") != project_id_for_run(reproduction_run_id)
            or not isinstance(value.get("project_number"), str)
            or not re.fullmatch(r"[1-9][0-9]{4,19}", value["project_number"])
            ):
        raise ValueError("NFR-14 verification artifact does not identify the exact reproduction project")
    if value["status"] == "passed":
        release = value.get("deployed_release")
        tested = value.get("tested_integration")
        images = release.get("images") if isinstance(release, dict) else None
        scope = value.get("scope")
        if (value.get("session_stop") != "passed" or not isinstance(tested, dict)
                or tested.get("tag") != value["integration_tag"]
                or not isinstance(release, dict)
                or not isinstance(release.get("id"), str)
                or not RELEASE_ID.fullmatch(release["id"])
                or not isinstance(images, dict) or set(images) != set(SERVICES)
                or any(not isinstance(images[name], str)
                       or not re.search(r"@sha256:[a-f0-9]{64}\Z", images[name]) for name in SERVICES)
                or not isinstance(scope, dict)
                or not isinstance(scope.get("verified"), list)
                or not isinstance(scope.get("pending"), list)
                or any(not isinstance(item, str) for item in scope["verified"] + scope["pending"])):
            raise ValueError("Passing NFR-14 evidence is incomplete or identifies another release")
    return artifact, data, value


def _reproduction_variables(run_id, integration_tag, project):
    return {
        "NFR14_REPRO_RUN_ID": run_id,
        "NFR14_REPRO_INTEGRATION_TAG": integration_tag,
        "NFR14_REPRO_PROJECT_ID": project["project_id"],
        "NFR14_REPRO_PROJECT_NUMBER": str(project["project_number"]),
        "NFR14_REPRO_STATE_BUCKET": project["state_bucket"],
        "NFR14_REPRO_DELIVERY_BUCKET": project["delivery_bucket"],
        "NFR14_REPRO_WORKLOAD_IDENTITY_PROVIDER": project["workload_identity_provider"],
        "NFR14_REPRO_DEPLOY_SERVICE_ACCOUNT": project["deploy_service_account"],
    }


def recreate(*, run_id, integration_tag, evidence_dir, control_project_id, control_bucket,
             parent, billing_account_id, monthly_alert_budget_usd, approved_cost_ceiling_usd,
             estimated_window_cost_usd, window_hours, main_project_id):
    """Prepare one isolated project and dispatch its immutable main-tag verification workflow."""
    approval = validate_admin_profile(
        run_id=run_id, integration_tag=integration_tag, control_project_id=control_project_id,
        control_bucket=control_bucket, parent=parent, billing_account_id=billing_account_id,
        monthly_alert_budget_usd=monthly_alert_budget_usd,
        approved_cost_ceiling_usd=approved_cost_ceiling_usd,
        estimated_window_cost_usd=estimated_window_cost_usd, window_hours=window_hours,
        main_project_id=main_project_id,
    )
    _validate_empty_admin_checkout()
    destination = _prepare_evidence_directory(evidence_dir)
    token = _access_token()
    github_token = _github_token()
    with _github_token_scope(github_token):
        _, manifest, ci = _release_manifest(integration_tag, os.environ.get("GITHUB_REPOSITORY_ID"))
        ci_file = destination / "nfr14-ci-evidence.json"
        resolved = resolve_release_ci_evidence(
            integration_tag, ci_file, expected_repository_id=os.environ.get("GITHUB_REPOSITORY_ID"),
        )
        if resolved.get("run", {}).get("id") != ci["run_id"]:
            raise ValueError("Resolved protected CI evidence differs from the release manifest")

    control_project_number, _ = _validate_control_bucket(control_project_id, control_bucket, token)
    objects = GCSJsonObjects(control_bucket, token)
    generation, existing_inventory = _read_inventory(objects, run_id)
    if generation != "0" or existing_inventory is not None:
        raise ValueError("This NFR-14 run identity is already registered; inspect it before recovery")
    variables = _environment_variables(github_token)
    if any(name in variables for name in VARIABLE_NAMES):
        raise ValueError("NFR-14 reproduction variables already exist; refusing to overwrite another run")

    project_info = _gcloud_json("projects", "describe", approval["project_id"],
                                "--format=json", allow_not_found=True)
    if project_info is not None:
        raise ValueError("The unique NFR-14 project ID already exists or is pending deletion")

    with _locked_control(control_bucket, token) as lock:
        lock.check()
        generation, existing_inventory = _read_inventory(objects, run_id)
        if generation != "0" or existing_inventory is not None:
            raise ValueError("This NFR-14 run identity was registered concurrently")
        inventory = {
            "schema_version": INVENTORY_SCHEMA, "run_id": run_id,
            "project_id": approval["project_id"], "integration_tag": integration_tag,
            "status": "project_preparation", "approval": {**approval, "main_project_id": main_project_id},
            "control_project_number": control_project_number,
            "release": {"release": manifest["release"], "root_sha": manifest["root_sha"],
                        "sources": manifest["sources"], "ci_run": ci["run_id"],
                        "ci_attempt": ci["run_attempt"], "ci_artifact": ci["artifact"]},
            "resolved_ci_sha256": hashlib.sha256(ci_file.read_bytes()).hexdigest(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        generation = _write_inventory(objects, run_id, "0", inventory)
        lock.check()
        try:
            plan_file, project_plan = _plan_project(approval, operation="create")
            print(json.dumps({
                "action": "create disposable NFR-14 project and project-filtered budget",
                "project_id": approval["project_id"],
                "project_plan": project_plan["actions"],
                "project_plan_sha256": project_plan["plan_sha256"],
                "approved_cost_ceiling_usd": approval["approved_cost_ceiling_usd"],
                "estimated_window_cost_usd": approval["estimated_window_cost_usd"],
                "window_hours": approval["window_hours"],
            }, sort_keys=True))
            _inventory_update(objects, run_id, lambda current: {
                **current, "status": "project_plan_ready", "project_create_plan": project_plan,
            })
            lock.check()
            project = _apply_project_create(
                approval, token, plan_file=plan_file, summary=project_plan,
            )
        except Exception as error:
            _inventory_update(objects, run_id, lambda current: {
                **current, "status": "project_preparation_incomplete",
                "failure_type": type(error).__name__,
            })
            raise
        vars_for_workflow = _reproduction_variables(run_id, integration_tag, project)
        _inventory_update(objects, run_id, lambda current: {
            **current, "status": "project_created", "project": project,
            "variables_sha256": hashlib.sha256(json.dumps(vars_for_workflow, sort_keys=True).encode()).hexdigest(),
        })
        lock.check()

        import bootstrap_setup
        foundation = bootstrap_setup.run_setup(
            project["project_id"], REPOSITORY, ENVIRONMENT, REGION,
            skip_budget=True, wif_profile="reproduction",
        )
        if foundation["project_number"] != project["project_number"]:
            raise ValueError("Bootstrap project number differs from the external reproduction state")
        output = _json_command(
            "tofu", f"-chdir={bootstrap_setup.MODULE}", "output", "-json", "github_variables",
        )
        required_output = {"GCP_PROJECT_ID", "GCP_STATE_BUCKET", "GCP_DELIVERY_BUCKET",
                           "GCP_WORKLOAD_IDENTITY_PROVIDER", "GCP_DEPLOY_SERVICE_ACCOUNT"}
        if not isinstance(output, dict) or not required_output.issubset(output):
            raise ValueError("The isolated bootstrap did not produce the exact deployment identities")
        if (output["GCP_PROJECT_ID"] != project["project_id"]
                or output["GCP_STATE_BUCKET"] != project["project_id"] + "-tofu-state"
                or output["GCP_DELIVERY_BUCKET"] != project["project_id"] + "-nexoruta-delivery"):
            raise ValueError("The isolated bootstrap outputs do not match the approved project identity")
        vars_for_workflow = _reproduction_variables(run_id, integration_tag, {
            **project, "project_number": foundation["project_number"],
            "state_bucket": output["GCP_STATE_BUCKET"], "delivery_bucket": output["GCP_DELIVERY_BUCKET"],
            "workload_identity_provider": output["GCP_WORKLOAD_IDENTITY_PROVIDER"],
            "deploy_service_account": output["GCP_DEPLOY_SERVICE_ACCOUNT"],
        })
        if vars_for_workflow["NFR14_REPRO_WORKLOAD_IDENTITY_PROVIDER"] != (
                f"projects/{project['project_number']}/locations/global/workloadIdentityPools/"
                "nexoruta-github/providers/demo-vm"):
            raise ValueError("Bootstrap produced an unexpected immutable WIF provider")
        _inventory_update(objects, run_id, lambda current: {
            **current, "status": "foundation_ready", "foundation": foundation,
        })
        lock.check()
        with _github_token_scope(github_token):
            _set_reproduction_variables(github_token, vars_for_workflow)
            dispatched_at = _dispatch_reproduction(github_token, run_id, integration_tag)
            run = _wait_reproduction(github_token, run_id, dispatched_at)
        run_summary = {
            "id": run.get("id"), "attempt": run.get("run_attempt"),
            "number": run.get("run_number"), "head_sha": run.get("head_sha"),
            "status": run.get("status"), "conclusion": run.get("conclusion"),
            "html_url": run.get("html_url"), "created_at": run.get("created_at"),
        }
        _inventory_update(objects, run_id, lambda current: {
            **current, "status": "workflow_completed", "workflow": run_summary,
        })
        artifact = None
        try:
            artifact, artifact_bytes, verification = _download_verification_artifact(
                run["id"], run_id, github_token,
            )
        except (RuntimeError, ValueError):
            if run.get("conclusion") == "success":
                raise
            verification = None
            artifact_bytes = None
        if artifact is not None:
            if verification.get("integration_tag") != integration_tag:
                raise ValueError("The NFR-14 workflow artifact belongs to a different integration tag")
            evidence_name = f"{RUN_INVENTORY_PREFIX}/{run_id}/evidence/verification.json"
            evidence_generation = objects.write(evidence_name, "0", artifact_bytes)
            evidence_path = destination / "nfr14-verification.json"
            evidence_path.write_bytes(artifact_bytes)
            try:
                evidence_path.chmod(0o600)
            except OSError:
                pass
            _inventory_update(objects, run_id, lambda current: {
                **current, "status": "workflow_evidence_collected",
                "workflow_artifact": {"id": artifact["id"], "digest": artifact["digest"],
                                      "object": evidence_name, "generation": evidence_generation,
                                      "sha256": hashlib.sha256(artifact_bytes).hexdigest()},
                "verification": verification,
            })
        if run.get("conclusion") != "success":
            raise RuntimeError("The exact NFR-14 reproduction workflow did not succeed; inspect its run and project")
        if (artifact is None or verification.get("status") != "passed"
                or verification.get("integration_tag") != integration_tag):
            raise ValueError("The NFR-14 workflow artifact does not prove the expected successful release")
        _inventory_update(objects, run_id, lambda current: {
            **current, "status": "reproduction_verified",
        })
        lock.check()
    return {"status": "reproduction_verified", "run_id": run_id,
            "project_id": approval["project_id"], "workflow_run_id": run_summary["id"],
            "evidence_dir": str(destination)}


def _load_inventory_context(run_id, control_project_id, control_bucket, *, access_token=None):
    token = access_token or _access_token()
    project_number, _ = _validate_control_bucket(control_project_id, control_bucket, token)
    objects = GCSJsonObjects(control_bucket, token)
    generation, inventory = _read_inventory(objects, run_id)
    if inventory is None:
        raise ValueError("No NFR-14 reproduction inventory exists for this run ID")
    profile = _inventory_profile(inventory)
    if (profile["control_project_id"] != control_project_id
            or profile["control_bucket"] != control_bucket
            or str(inventory.get("control_project_number", "")) != str(project_number)):
        raise ValueError("The external control inventory is stored under a different approved control project")
    return token, objects, generation, inventory, profile


def _read_active_marker(objects, name, *, now=None):
    _, value = objects.read(name)
    if value is None:
        return False
    now = time.time() if now is None else now
    if name.endswith("demo-control.json"):
        if (not isinstance(value, dict) or not re.fullmatch(r"[a-f0-9]{32}", value.get("owner", ""))
                or type(value.get("expires_at")) not in (int, float)
                or not math.isfinite(value["expires_at"])):
            raise ValueError("The isolated project control lock is malformed; refusing cleanup")
        return value["expires_at"] > now
    if (not isinstance(value, dict)
            or type(value.get("expires_at")) not in (int, float)
            or type(value.get("provisioning_until", 0)) not in (int, float)
            or not math.isfinite(value["expires_at"])
            or not math.isfinite(value.get("provisioning_until", 0))):
        raise ValueError("The isolated project session lease is malformed; refusing cleanup")
    return max(value["expires_at"], value.get("provisioning_until", 0)) > now


def _check_project_quiescent(profile, inventory, access_token):
    blockers = []
    state_bucket = (inventory.get("foundation") or {}).get("state_bucket")
    if not state_bucket:
        # If foundation bootstrap never completed, no VM session, load job, or
        # object lock can have been created by reproduce.yml.
        return blockers
    objects = GCSJsonObjects(state_bucket, access_token)
    if _read_active_marker(objects, "leases/demo.json"):
        blockers.append("active session/provisioning lease")
    if _read_active_marker(objects, "locks/demo-control.json"):
        blockers.append("active application control lock")

    instances = _gcloud_json("compute", "instances", "list", f"--project={profile['project_id']}",
                             "--format=json", allow_not_found=True) or []
    if not isinstance(instances, list):
        raise ValueError("The disposable project VM inventory is malformed")
    for vm in instances:
        if not isinstance(vm, dict) or not isinstance(vm.get("name"), str):
            raise ValueError("The disposable project VM inventory contains a malformed instance")
        if vm.get("status") != "TERMINATED":
            blockers.append("VM not terminated " + vm["name"])
        labels = vm.get("labels") or {}
        if labels.get("application") != "nexoruta" or labels.get("managed_by") != "opentofu":
            blockers.append("unowned VM " + vm["name"])

    builds = _gcloud_json("builds", "list", f"--project={profile['project_id']}", "--format=json",
                          allow_not_found=True) or []
    if not isinstance(builds, list):
        raise ValueError("The disposable project Cloud Build inventory is malformed")
    active_builds = {"QUEUED", "PENDING", "WORKING", "CANCELLING"}
    if any(isinstance(item, dict) and item.get("status") in active_builds for item in builds):
        blockers.append("active Cloud Build")

    executions = _gcloud_json(
        "run", "jobs", "executions", "list", f"--region={REGION}",
        f"--project={profile['project_id']}", "--format=json", allow_not_found=True,
    ) or []
    if not isinstance(executions, list):
        raise ValueError("The disposable project Cloud Run execution inventory is malformed")
    for execution in executions:
        if not isinstance(execution, dict):
            raise ValueError("The disposable project Cloud Run execution inventory is malformed")
        conditions = execution.get("conditions") or []
        if any(isinstance(condition, dict) and condition.get("type") == "Completed"
               and condition.get("status") == "Unknown" for condition in conditions):
            blockers.append("active Cloud Run job execution")
    return blockers


def inspect(*, run_id, control_project_id, control_bucket):
    token, _, _, inventory, profile = _load_inventory_context(run_id, control_project_id, control_bucket)
    project = _gcloud_json("projects", "describe", profile["project_id"], "--format=json",
                           allow_not_found=True)
    blockers = _check_project_quiescent(profile, inventory, token) if project else []
    budget_id = (inventory.get("project") or {}).get("budget_id")
    budget_present = None
    if budget_id:
        budget_present = _fetch_google_json(
            "https://billingbudgets.googleapis.com/v1/" + budget_id, token,
        ) is not None
    return {
        "run_id": run_id, "project_id": profile["project_id"],
        "inventory_status": inventory.get("status"),
        "project_lifecycle": (project or {}).get("lifecycleState", "ABSENT"),
        "project_number": str((project or {}).get("projectNumber", "")) or None,
        "budget_present": budget_present, "blockers": blockers,
        "workflow": inventory.get("workflow"),
        "verification_status": (inventory.get("verification") or {}).get("status"),
        "destroy_plan": inventory.get("destroy_plan"),
    }


def plan(*, run_id, control_project_id, control_bucket):
    token, objects, _, inventory, profile = _load_inventory_context(run_id, control_project_id, control_bucket)
    with _locked_control(control_bucket, token) as lock:
        lock.check()
        state = _project_state(profile)
        _verify_project_identity(profile, state["project_number"])
        _verify_budget(profile, state, token)
        plan_file, summary = _plan_project(profile, operation="create")
        if summary["actions"]:
            raise ValueError("The disposable project has drift; plan reports unexpected changes and will not apply them")
        _, inventory = _inventory_update(objects, run_id, lambda current: {
            **current, "last_project_plan": {**summary,
                "state_lineage": state["lineage"], "state_serial": state["serial"]},
        })
        lock.check()
    return {"run_id": run_id, "project_id": profile["project_id"],
            "actions": summary["actions"], "plan_sha256": summary["plan_sha256"],
            "state_lineage": state["lineage"], "state_serial": state["serial"]}


def destroy_plan(*, run_id, control_project_id, control_bucket):
    token, objects, _, inventory, profile = _load_inventory_context(run_id, control_project_id, control_bucket)
    if inventory.get("status") in ("destroyed", "project_deletion_requested"):
        raise ValueError("The disposable project is already being deleted or was destroyed")
    with _locked_control(control_bucket, token) as lock:
        lock.check()
        state = _project_state(profile)
        project_number = _verify_project_identity(profile, state["project_number"])
        if project_number != state["project_number"]:
            raise ValueError("External project state differs from the live Google Cloud project number")
        budget_id = _verify_budget(profile, state, token)
        blockers = _check_project_quiescent(profile, inventory, token)
        if blockers:
            raise RuntimeError("Cleanup is blocked: " + "; ".join(blockers))
        if inventory.get("status") == "reproduction_verified" and not inventory.get("workflow_artifact"):
            raise ValueError("Verified reproduction inventory is missing its sanitized external evidence")
        plan_file, summary = _plan_project(profile, operation="destroy")
        plan_state = {"lineage": state["lineage"], "serial": state["serial"]}
        plan_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + os.urandom(8).hex()
        object_name = f"{RUN_INVENTORY_PREFIX}/{run_id}/plans/destroy-{plan_id}.tfplan"
        plan_generation = objects.write(object_name, "0", plan_file.read_bytes())
        metadata = {**summary, "object": object_name, "generation": plan_generation,
                    "state_lineage": plan_state["lineage"], "state_serial": plan_state["serial"],
                    "budget_id": budget_id, "created_at": datetime.now(timezone.utc).isoformat()}
        _inventory_update(objects, run_id, lambda current: {
            **current, "status": "destroy_planned", "destroy_plan": metadata,
        })
        lock.check()
    return {"run_id": run_id, "project_id": profile["project_id"], **metadata}


def _verify_deletion_requested(profile, inventory, access_token):
    project = _gcloud_json("projects", "describe", profile["project_id"], "--format=json",
                           allow_not_found=True)
    if project is not None:
        if project.get("lifecycleState") != "DELETE_REQUESTED":
            raise RuntimeError("Google Cloud has not confirmed deletion of the disposable project")
        labels = project.get("labels") or {}
        if labels.get("nfr14_owner") != "nfr-14" or labels.get("nfr14_run") != profile["run_id"][:16]:
            raise ValueError("Pending project deletion no longer matches the NFR-14 run ownership labels")
        raise RuntimeError("Project deletion is still pending; reproduction variables were retained for retry")
    budget_id = (inventory.get("project") or {}).get("budget_id")
    if not isinstance(budget_id, str):
        raise ValueError("The disposable project budget identity is missing from the control inventory")
    budget = _fetch_google_json("https://billingbudgets.googleapis.com/v1/" + budget_id, access_token)
    if budget is not None:
        raise RuntimeError("The disposable project budget still exists; reproduction variables were retained")


def destroy(*, run_id, control_project_id, control_bucket, confirm_project):
    token, objects, _, inventory, profile = _load_inventory_context(run_id, control_project_id, control_bucket)
    if confirm_project != profile["project_id"]:
        raise ValueError("--confirm-project must exactly match the registered disposable project ID")
    if inventory.get("status") not in ("destroy_planned", "project_deletion_requested"):
        raise ValueError("Run destroy-plan and inspect its exact saved plan before destroy")
    with _locked_control(control_bucket, token) as lock:
        lock.check()
        inventory_generation, inventory = _read_inventory(objects, run_id)
        profile = _inventory_profile(inventory)
        if inventory.get("status") == "destroy_planned":
            metadata = inventory.get("destroy_plan")
            if (not isinstance(metadata, dict) or metadata.get("operation") != "destroy"
                    or metadata.get("object") != _inventory_plan_name(run_id, metadata.get("object"))
                    or not SHA_256.fullmatch(metadata.get("plan_sha256", ""))
                    or not str(metadata.get("generation", "")).isdigit()):
                raise ValueError("The saved disposable-project destroy plan metadata is invalid")
            blockers = _check_project_quiescent(profile, inventory, token)
            if blockers:
                raise RuntimeError("Cleanup is blocked: " + "; ".join(blockers))
            state = _project_state(profile)
            if (state["lineage"] != metadata.get("state_lineage")
                    or state["serial"] != metadata.get("state_serial")):
                raise ValueError("External project state changed after destroy-plan; create a new plan")
            _verify_project_identity(profile, state["project_number"])
            _verify_budget(profile, state, token)
            generation, plan_bytes = objects.read(metadata["object"])
            if (generation != str(metadata["generation"]) or not isinstance(plan_bytes, bytes)
                    or hashlib.sha256(plan_bytes).hexdigest() != metadata["plan_sha256"]):
                raise ValueError("The exact versioned destroy-plan object is missing or has changed")
            _tofu_init(profile)
            workdir, _ = _project_workdir(profile)
            plan_file = workdir / "nfr14-destroy.tfplan"
            plan_file.write_bytes(plan_bytes)
            try:
                plan_file.chmod(0o600)
            except OSError:
                pass
            plan = json.loads(_tofu(profile, "show", "-json", str(plan_file), capture=True))
            actions = _validate_project_plan(plan, profile, operation="destroy")
            if actions != metadata.get("actions"):
                raise ValueError("The saved destroy plan actions differ from its registered summary")
            _inventory_update(objects, run_id, lambda current: {
                **current, "status": "destroy_applying",
            })
            lock.check()
            _tofu(profile, "apply", "-input=false", "-lock-timeout=5m", str(plan_file))
            _inventory_update(objects, run_id, lambda current: {
                **current, "status": "project_deletion_requested",
                "project_deletion_requested_at": datetime.now(timezone.utc).isoformat(),
            })
        elif inventory.get("status") == "project_deletion_requested":
            metadata = inventory.get("destroy_plan") or {}
        _verify_deletion_requested(profile, inventory, token)
        github_token = _github_token()
        with _github_token_scope(github_token):
            _delete_reproduction_variables(github_token, _reproduction_variables(
                run_id, inventory["integration_tag"], inventory["project"],
            ))
        lock.check()
        _inventory_update(objects, run_id, lambda current: {
            **current, "status": "destroyed", "destroyed_at": datetime.now(timezone.utc).isoformat(),
        })
    return {"status": "destroyed", "run_id": run_id, "project_id": profile["project_id"]}


def _inventory_plan_name(run_id, value):
    prefix = f"{RUN_INVENTORY_PREFIX}/{validate_run_id(run_id)}/plans/destroy-"
    if not isinstance(value, str) or not value.startswith(prefix) or not value.endswith(".tfplan"):
        return ""
    suffix = value[len(prefix):-len(".tfplan")]
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{16}", suffix):
        return ""
    return value


def _release_manifest(tag, expected_repository_id=None):
    if not re.fullmatch(integration.TAG, tag):
        raise ValueError("Invalid tested integration tag")
    snapshot = integration.snapshot_for_tag(tag)
    _validate_reproduction_tag(snapshot)
    release = integration.github("releases/tags/" + tag)
    if (release.get("tag_name") != tag or release.get("draft") is not False
            or release.get("prerelease") is not True):
        raise ValueError("The tested integration tag has no complete main prerelease")
    match = re.search(r"```json\s*(\{.*?\})\s*```", release.get("body", ""), re.DOTALL)
    if not match:
        raise ValueError("The main prerelease has no published delivery manifest")
    manifest = json.loads(match.group(1))
    if (not isinstance(manifest, dict) or manifest.get("manifest_version") != 2
            or manifest.get("channel") != "main" or manifest.get("integration_tag") != tag
            or manifest.get("root_sha") != snapshot["root_sha"] or manifest.get("sources") != snapshot["sources"]
            or not RELEASE_ID.fullmatch(manifest.get("release", ""))
            or not SHA_256.fullmatch(manifest.get("bundle_sha256", ""))):
        raise ValueError("The published manifest does not identify the exact tested main snapshot")
    if expected_repository_id is not None:
        ci_identity = manifest.get("ci_evidence")
        if not isinstance(ci_identity, dict) or ci_identity.get("repository_id") != str(expected_repository_id):
            raise ValueError("The main release CI evidence belongs to a different repository")
    images = manifest.get("images")
    if (not isinstance(images, dict) or set(images) != set(SERVICES)
            or any(not isinstance(images[name], str)
                   or not re.search(r"@sha256:[a-f0-9]{64}\Z", images[name]) for name in SERVICES)):
        raise ValueError("The published main manifest does not contain all six immutable application images")
    image_sources = manifest.get("image_sources")
    if (not isinstance(image_sources, dict) or set(image_sources) != set(SERVICES)
            or any(image_sources[name] != snapshot["sources"]["backend" if name in ("api", "worker") else "frontend"]
                   for name in SERVICES)):
        raise ValueError("The published main images do not match the exact source gitlinks")
    inventory = image_inventory.validate_inventory(manifest.get("deployment_images"))
    if image_inventory.checksum(inventory) != manifest.get("deployment_images_sha256"):
        raise ValueError("The published auxiliary image inventory checksum is invalid")
    ci = ci_evidence.validate_ci_identity(
        manifest.get("ci_evidence"), root_sha=snapshot["root_sha"], sources=snapshot["sources"],
    )
    root_tree = integration.git("rev-parse", f"{snapshot['root_sha']}^{{tree}}")
    if ci.get("root_tree") != root_tree:
        raise ValueError("The protected CI evidence does not match the published Git tree")
    ci_evidence.validate_manifest_android(manifest)
    return snapshot, manifest, ci


def _validate_reproduction_tag(snapshot):
    """Require a main release that contains the exact NFR-14 execution controls."""
    commit = snapshot.get("root_sha") if isinstance(snapshot, dict) else None
    if not isinstance(commit, str) or not re.fullmatch(integration.SHA, commit):
        raise ValueError("The selected integration tag has no immutable root commit")
    required = {
        "scripts/gcp/reproduce.py": ("def validate_runtime_environment", "def resolve_release_ci_evidence"),
        "scripts/gcp/verify_nfr14.py": ("def verify_live", "def finalize_stop"),
        "scripts/gcp/bootstrap_setup.py": ("WIF_PROFILES", '"reproduction"'),
        "scripts/gcp/bootstrap.py": ("wif_profile", "validate_runtime_environment"),
        "scripts/gcp/demo_session.py": ("validate_runtime_environment", 'wif_profile="reproduction"'),
        "scripts/gcp/github_environment.py": ("validate_runtime_environment", "reproduction"),
        "scripts/gcp/delivery.py": ("selected_build_services", "reproduction=reproduction"),
        "scripts/gcp/integration.py": ("def snapshot_for_tag", "def verify_checkout"),
        "infra/gcp/bootstrap/main.tf": ('variable "wif_profile"', "reproduce.yml@refs/heads/main"),
        "infra/gcp/reproduction-project/main.tf": ('deletion_policy     = "DELETE"', "google_billing_budget"),
        ".github/workflows/reproduce.yml": ("workflow_dispatch", "nexoruta-demo"),
    }
    for path, markers in required.items():
        result = subprocess.run(
            ["git", "-C", str(integration.ROOT), "show", f"{commit}:{path}"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode or any(marker not in result.stdout for marker in markers):
            raise ValueError("The selected main integration predates the required NFR-14 reproduction controls")


def resolve_release_ci_evidence(tag, output_path, *, expected_repository_id=None):
    """Re-fetch the exact successful protected CI artifact named by the main release."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("A GitHub token with Actions read access is required")
    snapshot, manifest, identity = _release_manifest(tag, expected_repository_id)
    artifact_identity = identity["artifact"]
    run = ci_evidence._api(f"actions/runs/{identity['run_id']}", token)
    if (run.get("id") != identity["run_id"] or run.get("run_attempt") != identity["run_attempt"]
            or run.get("run_number") != identity["run_number"] or run.get("event") != "pull_request"
            or run.get("status") != "completed" or run.get("conclusion") != "success"
            or run.get("path", "").split("@", 1)[0] != ci_evidence.WORKFLOW_PATH):
        raise ValueError("The main release does not resolve to its successful protected Integrated CI run")
    expected_pr = identity["pull_request"]
    pulls = ci_evidence._run_pull_requests(run, token)
    expected_repository_id = int(identity["repository_id"])
    if not any(
        item.get("number") == expected_pr
        and item.get("base", {}).get("ref") == "main"
        and item.get("head", {}).get("ref") == "develop"
        and (item.get("base", {}).get("repo", {}) or {}).get("id") == expected_repository_id
        and (item.get("head", {}).get("repo", {}) or {}).get("id") == expected_repository_id
        for item in pulls
    ):
        raise ValueError("The recorded CI run is not for the protected same-repository develop-to-main PR")
    artifacts = ci_evidence._api(f"actions/runs/{identity['run_id']}/artifacts?per_page=100", token).get("artifacts", [])
    matches = [item for item in artifacts if item.get("id") == artifact_identity["id"]]
    if len(matches) != 1 or matches[0].get("expired"):
        raise ValueError("The protected Integrated CI evidence artifact is missing or expired")
    artifact = matches[0]
    if (artifact.get("name") != artifact_identity["name"]
            or artifact.get("digest") != artifact_identity["digest"]):
        raise ValueError("The protected Integrated CI artifact identity differs from the published manifest")
    evidence = ci_evidence._download_artifact(artifact["id"], token, artifact["digest"])
    resolved = ci_evidence._validate_resolved(
        evidence, artifact, run, {"number": expected_pr},
        {"repository_id": identity["repository_id"], "root_sha": identity["root_sha"],
         "root_tree": identity["root_tree"], "sources": snapshot["sources"],
         "android_input_sha256": manifest["android_input_sha256"]},
    )
    jobs = ci_evidence._api(
        f"actions/runs/{identity['run_id']}/jobs?filter=latest&per_page=100", token,
    ).get("jobs", [])
    final_jobs = [job for job in jobs if job.get("name") == "Integrated CI / result"]
    if len(final_jobs) != 1 or final_jobs[0].get("conclusion") != "success":
        raise ValueError("The recorded Integrated CI result job is not successful")
    resolved["run"] = {
        "id": identity["run_id"], "attempt": identity["run_attempt"],
        "number": identity["run_number"], "workflow_path": ci_evidence.WORKFLOW_PATH,
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(resolved, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    try:
        destination.chmod(0o600)
    except OSError:
        pass
    if os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as output:
            output.write("NEXORUTA_CI_EVIDENCE_FILE=" + str(destination) + "\n")
    if os.environ.get("GITHUB_OUTPUT"):
        plan = json.dumps(evidence["plan"], sort_keys=True, separators=(",", ":"))
        delimiter = "NFR14_PLAN_" + os.urandom(12).hex()
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"plan<<{delimiter}\n{plan}\n{delimiter}\n")
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    workflow = commands.add_parser("validate-workflow", help="validate the locked reproduction inputs")
    workflow.add_argument("--run-id", required=True)
    workflow.add_argument("--integration-tag", required=True)
    evidence = commands.add_parser("resolve-ci-evidence", help="resolve the CI artifact bound to a main release")
    evidence.add_argument("--integration-tag", required=True)
    evidence.add_argument("--output", required=True)
    admin = commands.add_parser("recreate", help="prepare and verify one explicitly approved isolated project")
    admin.add_argument("--run-id", required=True)
    admin.add_argument("--integration-tag", required=True)
    admin.add_argument("--evidence-dir", required=True)
    admin.add_argument("--control-project-id", required=True)
    admin.add_argument("--control-bucket", required=True)
    admin.add_argument("--main-project-id", required=True)
    admin.add_argument("--parent", required=True)
    admin.add_argument("--billing-account-id", required=True)
    admin.add_argument("--monthly-alert-budget-usd", required=True)
    admin.add_argument("--approved-cost-ceiling-usd", required=True)
    admin.add_argument("--estimated-window-cost-usd", required=True)
    admin.add_argument("--window-hours", required=True)
    for command_name in ("plan", "inspect", "destroy-plan"):
        command = commands.add_parser(command_name)
        command.add_argument("--run-id", required=True)
        command.add_argument("--control-project-id", required=True)
        command.add_argument("--control-bucket", required=True)
    destroy_command = commands.add_parser("destroy", help="apply the exact registered disposable-project plan")
    destroy_command.add_argument("--run-id", required=True)
    destroy_command.add_argument("--control-project-id", required=True)
    destroy_command.add_argument("--control-bucket", required=True)
    destroy_command.add_argument("--confirm-project", required=True)
    args = parser.parse_args()
    if args.command == "validate-workflow":
        target = validate_runtime_environment(
            os.environ, input_run_id=args.run_id, input_tag=args.integration_tag,
        )
        _release_manifest(args.integration_tag, os.environ.get("GITHUB_REPOSITORY_ID"))
        print(json.dumps({"status": "valid", **target}, sort_keys=True))
    elif args.command == "resolve-ci-evidence":
        result = resolve_release_ci_evidence(
            args.integration_tag, args.output, expected_repository_id=os.environ.get("GITHUB_REPOSITORY_ID"),
        )
        print(json.dumps({"status": "resolved", "run": result["run"]}, sort_keys=True))
    elif args.command == "recreate":
        result = recreate(
            run_id=args.run_id, integration_tag=args.integration_tag, evidence_dir=args.evidence_dir,
            control_project_id=args.control_project_id, control_bucket=args.control_bucket,
            main_project_id=args.main_project_id, parent=args.parent,
            billing_account_id=args.billing_account_id,
            monthly_alert_budget_usd=args.monthly_alert_budget_usd,
            approved_cost_ceiling_usd=args.approved_cost_ceiling_usd,
            estimated_window_cost_usd=args.estimated_window_cost_usd, window_hours=args.window_hours,
        )
        print(json.dumps(result, sort_keys=True))
    elif args.command == "plan":
        print(json.dumps(plan(run_id=args.run_id, control_project_id=args.control_project_id,
                              control_bucket=args.control_bucket), sort_keys=True))
    elif args.command == "inspect":
        print(json.dumps(inspect(run_id=args.run_id, control_project_id=args.control_project_id,
                                 control_bucket=args.control_bucket), sort_keys=True))
    elif args.command == "destroy-plan":
        print(json.dumps(destroy_plan(run_id=args.run_id, control_project_id=args.control_project_id,
                                      control_bucket=args.control_bucket), sort_keys=True))
    elif args.command == "destroy":
        print(json.dumps(destroy(run_id=args.run_id, control_project_id=args.control_project_id,
                                 control_bucket=args.control_bucket, confirm_project=args.confirm_project),
                         sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
