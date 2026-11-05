"""Reserve, run, cancel and reconcile the bounded Cloud Run load-test job."""

import datetime as dt
from contextlib import ExitStack, contextmanager, nullcontext
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import control_lock
import demo_session as session

REGION = "southamerica-west1"
JOB = "nexoruta-load-tests"
LEASE_OBJECT = "leases/load-test.json"
PROFILES = {"smoke": 300, "baseline": 1260, "sync": 1500, "stress": 2700, "soak": 5100}
CONTROL_LOCK_BUSY = "Another demo control operation holds the shared lock"
SUITE_SOURCES = ("tests/load/Dockerfile", "tests/load/profiles.json", "tests/load/scenario.js",
                 "deploy/load/runner.py", "deploy/load/supervision.py", "deploy/load/sessions.py")
RELEASE_MARKER_START = "__NEXORUTA_RELEASE_BEGIN__"
RELEASE_MARKER_END = "__NEXORUTA_RELEASE_END__"


def config():
    values = {key: os.environ.get(key, "") for key in (
        "GCP_PROJECT_ID", "GCP_ZONE", "GCP_STATE_BUCKET", "GCP_DELIVERY_BUCKET")}
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", values["GCP_PROJECT_ID"]):
        raise ValueError("Invalid GCP_PROJECT_ID")
    if values["GCP_ZONE"] != REGION + "-a":
        raise ValueError("GCP_ZONE must identify the active Santiago demo")
    for key in ("GCP_STATE_BUCKET", "GCP_DELIVERY_BUCKET"):
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", values[key]):
            raise ValueError(f"Invalid {key}")
    values["GCP_LOAD_CONTROL_BUCKET"] = f"{values['GCP_PROJECT_ID']}-nexoruta-load-control"
    values["GCP_LOAD_RESULTS_BUCKET"] = f"{values['GCP_PROJECT_ID']}-nexoruta-load-results"
    values["GCP_BASE_DOMAIN"] = os.environ.get("GCP_BASE_DOMAIN", "")
    return values


def load_control_bucket(config):
    return config.get("GCP_LOAD_CONTROL_BUCKET") or f"{config['GCP_PROJECT_ID']}-nexoruta-load-control"


def demo_control_lock(config, access):
    store = control_lock.JsonStorage(config["GCP_STATE_BUCKET"], access)
    return control_lock.control_lock(config, store=store)


@contextmanager
def demo_control_lock_retry(config, access, *, wait_seconds=60, retry_interval=1):
    """Wait briefly for an in-flight VM control operation before saving load state."""
    deadline = time.monotonic() + max(0, wait_seconds)
    while True:
        stack = ExitStack()
        try:
            lease = stack.enter_context(demo_control_lock(config, access))
        except RuntimeError as error:
            stack.close()
            remaining = deadline - time.monotonic()
            if str(error) != CONTROL_LOCK_BUSY or remaining <= 0:
                raise
            time.sleep(min(retry_interval, remaining))
            continue
        try:
            yield lease
        finally:
            stack.close()
        return


def token(project):
    return subprocess.run(["gcloud", "auth", "print-access-token", f"--project={project}"],
                          check=True, capture_output=True, text=True, timeout=20).stdout.strip()


class Storage:
    def __init__(self, bucket, access_token):
        self.bucket, self.access_token = bucket, access_token

    def request(self, method, url, body=None):
        request = urllib.request.Request(url, method=method, data=body,
            headers={"Authorization": "Bearer " + self.access_token, "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=20) as response:
            content = response.read(1_000_000)
        return json.loads(content) if content else {}

    def base(self, name):
        return ("https://storage.googleapis.com/storage/v1/b/" + urllib.parse.quote(self.bucket, safe="")
                + "/o/" + urllib.parse.quote(name, safe=""))

    def read(self, name):
        try:
            generation = str(self.request("GET", self.base(name) + "?fields=generation")["generation"])
            value = self.request("GET", self.base(name) + "?alt=media&ifGenerationMatch=" + generation)
            return generation, value
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return "0", None
            raise

    def write(self, name, generation, value):
        query = urllib.parse.urlencode({"uploadType": "media", "name": name, "ifGenerationMatch": generation})
        url = "https://storage.googleapis.com/upload/storage/v1/b/" + urllib.parse.quote(self.bucket, safe="") + "/o?" + query
        result = self.request("POST", url, json.dumps(value).encode())
        return str(result["generation"])

    def delete(self, name, generation):
        self.request("DELETE", self.base(name) + "?ifGenerationMatch=" + generation)


def gcp_request(method, url, project, body=None):
    access = token(project)
    request = urllib.request.Request(url, method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + access, "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=25) as response:
        content = response.read(1_000_000)
    return json.loads(content) if content else {}


def find_execution(project, run_id):
    parent = f"projects/{project}/locations/{REGION}/jobs/{JOB}"
    page_token = ""
    while True:
        query = {"pageSize": "100"}
        if page_token:
            query["pageToken"] = page_token
        url = "https://run.googleapis.com/v2/" + parent + "/executions?" + urllib.parse.urlencode(query)
        result = gcp_request("GET", url, project)
        matches = []
        for execution in result.get("executions", []):
            task = execution.get("template", {})
            containers = task.get("containers", [])
            for container in containers:
                if any(env.get("name") == "NEXORUTA_RUN_ID" and env.get("value") == run_id
                       for env in container.get("env", [])):
                    matches.append(execution.get("name", ""))
                    break
        if len(matches) > 1:
            raise RuntimeError("Multiple Cloud Run executions match the same run ID; refusing to guess")
        if matches:
            return matches[0]
        page_token = result.get("nextPageToken", "")
        if not page_token:
            return None


def execution_reference(project, run_id, operation=""):
    """Resolve the execution resource without waiting for its task to finish.

    Cloud Run's jobs.run operation may remain pending while the job is running.
    The execution carries the run ID supplied in the container override, so use
    that exact marker as soon as Cloud Run publishes the execution resource.
    """
    execution = find_execution(project, run_id)
    if execution or not operation:
        return execution
    result = gcp_request("GET", "https://run.googleapis.com/v2/" + operation, project)
    if not result.get("done"):
        return None
    if "error" in result:
        raise RuntimeError("Cloud Run rejected the load-test execution request")
    return result.get("response", {}).get("name") or None


def wait_for_execution_reference(project, run_id, operation="", timeout=120):
    deadline = time.monotonic() + timeout
    while True:
        execution = execution_reference(project, run_id, operation)
        if execution:
            return execution
        if time.monotonic() >= deadline:
            break
        time.sleep(2)
    raise RuntimeError("Cloud Run has not exposed the exact execution yet; the lease remains reserved for recovery")


def reconcile_execution(leases, project, run_id):
    generation, active = leases.read(LEASE_OBJECT)
    if not active or active.get("run_id") != run_id:
        return True
    execution = active.get("execution")
    if (not execution and not active.get("operation") and not active.get("launch_requested_at")):
        if active.get("expires_at", 0) <= time.time():
            active.update(status="failed", completed_at=time.time(), failure_reason="expired_before_launch")
            leases.write(LEASE_OBJECT, generation, active)
            return True
        return False
    if not execution:
        execution = find_execution(project, run_id)
    if not execution and active.get("operation"):
        operation = gcp_request("GET", "https://run.googleapis.com/v2/" + active["operation"], project)
        if operation.get("done") and "error" in operation:
            active.update(status="failed", completed_at=time.time(), execution_status="CREATE_FAILED")
            leases.write(LEASE_OBJECT, generation, active)
            return True
        if operation.get("done"):
            execution = operation.get("response", {}).get("name", "")
        else:
            return False
    if not execution and not active.get("operation"):
        return False
    if execution:
        generation, current = leases.read(LEASE_OBJECT)
        if not current or current.get("run_id") != run_id:
            return True
        current["execution"] = execution
        leases.write(LEASE_OBJECT, generation, current)
    if not execution:
        return active.get("status") not in ("starting", "running", "cancelling")
    remote = gcp_request("GET", "https://run.googleapis.com/v2/" + execution, project)
    completed = next((item for item in remote.get("conditions", []) if item.get("type") == "Completed"), None)
    if completed and completed.get("state") in ("CONDITION_SUCCEEDED", "CONDITION_FAILED"):
        generation, current = leases.read(LEASE_OBJECT)
        if current and current.get("run_id") == run_id:
            current.update(status="completed" if completed["state"] == "CONDITION_SUCCEEDED" else "failed",
                           completed_at=time.time(), execution_status=completed["state"])
            leases.write(LEASE_OBJECT, generation, current)
        return True
    return False


def parse_release_marker(output):
    if output.count(RELEASE_MARKER_START) != 1 or output.count(RELEASE_MARKER_END) != 1:
        raise RuntimeError("Could not isolate the applied VM release marker")
    _, output = output.split(RELEASE_MARKER_START, 1)
    marker, _ = output.split(RELEASE_MARKER_END, 1)
    marker = marker.strip()
    if not re.fullmatch(r"release-[a-f0-9]{32}", marker):
        raise RuntimeError("The VM returned an invalid applied release marker")
    return marker


def immutable_manifest(config, run_id, profile, session_expires_at, fixture_version):
    project = config["GCP_PROJECT_ID"]
    delivery = config["GCP_DELIVERY_BUCKET"]
    nodes = session.node_configs(config)
    applied = {}
    for node in nodes:
        vm = session.instance(node)
        if not vm or vm.get("status") != "RUNNING":
            raise RuntimeError(f"Demo VM {node['VM_NAME']} is not RUNNING")
        session.check_deadline(vm)
        output = session.gcloud(
            node, "compute", "ssh", node["VM_NAME"], "--tunnel-through-iap",
            "--command=printf '__NEXORUTA_RELEASE_BEGIN__\\n'; sudo cat /srv/nexoruta/current-release; "
            "printf '\\n__NEXORUTA_RELEASE_END__\\n'", capture=True,
        )
        applied[node["NODE_ID"]] = parse_release_marker(output)
    if len(set(applied.values())) != 1:
        raise RuntimeError(
            "The two VMs do not run the same application release "
            f"(node a: {applied['a']}, node b: {applied['b']})"
        )
    release = applied["a"]
    manifest = json.loads(session.command(
        "gcloud", "storage", "cat", f"gs://{delivery}/releases/{release}/manifest.json",
        f"--project={project}", capture=True,
    ))
    if manifest.get("release") != release:
        raise RuntimeError("The active VM release manifest does not match its applied marker")
    images = manifest.get("images", {})
    required = ("api", "worker", "admin", "backoffice", "commerce", "tracking")
    if any(not re.fullmatch(rf"southamerica-west1-docker\.pkg\.dev/{re.escape(project)}/nexoruta/{name}@sha256:[a-f0-9]{{64}}", images.get(name, "")) for name in required):
        raise RuntimeError("The applied manifest is missing a digest-pinned application image")
    sql = json.loads(session.command(
        "gcloud", "sql", "instances", "describe", "nexoruta-demo-db",
        f"--project={project}", "--format=json", capture=True,
    ))
    if sql.get("state") != "RUNNABLE":
        raise RuntimeError("Cloud SQL is not RUNNABLE")
    for service_name in ("api", "admin", "backoffice", "commerce", "tracking", "monitor"):
        output = session.command(
            "gcloud", "compute", "backend-services", "get-health", f"nexoruta-demo-{service_name}",
            "--global", f"--project={project}", "--format=json", capture=True, timeout=30,
        )
        health = [item for backend in json.loads(output)
                  for item in backend.get("status", {}).get("healthStatus", [])]
        by_vm = {node["VM_NAME"]: [item.get("healthState") for item in health
                                   if item.get("instance", "").endswith("/" + node["VM_NAME"])]
                 for node in nodes}
        if any(states != ["HEALTHY"] for states in by_vm.values()):
            raise RuntimeError(f"The {service_name} backend does not report both VMs healthy")
    for node in nodes:
        for worker in ("worker-rabbit", "worker-kafka", "worker-push", "otel-collector", "alloy"):
            running = session.gcloud(
                node, "compute", "ssh", node["VM_NAME"], "--tunnel-through-iap",
                "--command=sudo docker ps -q --filter label=com.docker.compose.project=nexoruta-demo "
                f"--filter label=com.docker.compose.service={worker} --filter status=running",
                capture=True,
            ).strip()
            if not running:
                raise RuntimeError(f"The required {worker} service is not running on node {node['NODE_ID']}")
    origin = application_origin(config)
    request = urllib.request.Request(origin + "/health/ready")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError("Public API readiness check failed")
    except urllib.error.URLError as error:
        raise RuntimeError("Public API readiness check failed") from error
    root = Path(__file__).resolve().parents[2]
    return {
        "run_id": run_id, "profile": profile, "release": release,
        "image_digests": images, "integration_tag": manifest.get("integration_tag"),
        "source_shas": manifest.get("sources"), "fixture_version": fixture_version,
        "suite_sha256": suite_sha256(root), "session_expires_at": session_expires_at,
        "thresholds_version": json.loads((root / "tests/load/profiles.json").read_text(encoding="utf-8"))["version"],
        "created_at": time.time(), "api_origin": origin,
    }


def suite_sha256(root):
    digest = hashlib.sha256()
    for relative in SUITE_SOURCES:
        digest.update((root / relative).read_bytes())
    return digest.hexdigest()


def application_origin(config):
    domain = config.get("GCP_BASE_DOMAIN", "")
    if not domain:
        address = session.command(
            "gcloud", "compute", "addresses", "describe", "nexoruta-demo-frontend",
            "--global", f"--project={config['GCP_PROJECT_ID']}", "--format=value(address)", capture=True,
        ).strip()
        ipaddress.IPv4Address(address)
        domain = address.replace(".", "-") + ".sslip.io"
    if not re.fullmatch(r"[a-z0-9.-]+", domain):
        raise ValueError("Invalid GCP_BASE_DOMAIN")
    return f"https://api.{domain}"


def latest_fixture_version(project):
    name = subprocess.run([
        "gcloud", "secrets", "versions", "list", "nexoruta-load-fixtures",
        f"--project={project}", "--filter=state=ENABLED", "--sort-by=~createTime",
        "--limit=1", "--format=value(name)",
    ], check=True, capture_output=True, text=True, timeout=30).stdout.strip()
    # `gcloud secrets versions list --format=value(name)` returns the short
    # version ID (for example, "1"), not the full resource path.
    match = re.fullmatch(
        r"(?:projects/[^/]+/secrets/nexoruta-load-fixtures/versions/)?([1-9][0-9]*)",
        name,
    )
    if not match:
        raise RuntimeError("No enabled synthetic fixture version exists in Secret Manager")
    return match.group(1)


def run(config, profile, run_id=None):
    if profile not in PROFILES:
        raise ValueError("Select one of smoke, baseline, sync, stress or soak")
    run_id = run_id or str(uuid.uuid4())
    if not re.fullmatch(r"[a-f0-9-]{36}", run_id):
        raise ValueError("Invalid run id")
    access = token(config["GCP_PROJECT_ID"])
    state = Storage(config["GCP_STATE_BUCKET"], access)
    leases = Storage(load_control_bucket(config), access)
    image = os.environ.get("NEXORUTA_LOAD_IMAGE", "")
    if not re.fullmatch(rf"southamerica-west1-docker\.pkg\.dev/{re.escape(config['GCP_PROJECT_ID'])}/nexoruta/load-tests@sha256:[a-f0-9]{{64}}", image):
        raise ValueError("The load-test image must be pinned to an Artifact Registry digest")
    with demo_control_lock(config, access):
        generation, active = leases.read(LEASE_OBJECT)
        now = time.time()
        reserved_here = bool(active and active.get("run_id") == run_id
                             and active.get("owner") == os.environ.get("GITHUB_RUN_ID", "manual")
                             and active.get("status") == "reserved")
        expired_reservation = bool(active and active.get("status") == "reserved" and active.get("expires_at", 0) <= now)
        if active and active.get("status") in ("reserved", "starting", "running", "cancelling") and not reserved_here and not expired_reservation:
            if active.get("status") == "reserved" or not reconcile_execution(leases, config["GCP_PROJECT_ID"], active["run_id"]):
                raise RuntimeError("A load-test execution is active or its cancellation is pending")
            generation, active = leases.read(LEASE_OBJECT)
        session_generation, session = state.read("leases/demo.json")
        if not session or session.get("expires_at", 0) <= now:
            raise RuntimeError("The remote demo session is not active")
        margin = PROFILES[profile] + 600
        if session["expires_at"] - now < margin:
            raise RuntimeError("The active VM session does not have enough time for this profile and cleanup")
        if reserved_here and active.get("expires_at", 0) <= now:
            raise RuntimeError("The load-test build reservation expired; cancel it and reserve again")
        manifest = active if reserved_here else {"run_id": run_id, "profile": profile,
                    "owner": os.environ.get("GITHUB_RUN_ID", "manual"), "created_at": now,
                    "session_expires_at": session["expires_at"]}
        if manifest.get("fixture_version") != os.environ.get("NEXORUTA_FIXTURE_VERSION"):
            raise RuntimeError("The fixture version changed after the run was reserved")
        manifest.update(status="starting", image=image,
                        expires_at=min(session["expires_at"], now + PROFILES[profile] + 600))
        try:
            leases.write(LEASE_OBJECT, generation, manifest)
        except urllib.error.HTTPError as error:
            if error.code == 412:
                raise RuntimeError("Another workflow reserved a load test concurrently") from None
            raise
    run_manifest = immutable_manifest(config, run_id, profile, manifest["session_expires_at"],
                                      manifest["fixture_version"])
    run_manifest.update(image=image, status="starting", expires_at=manifest["expires_at"])
    leases.write(f"runs/{run_id}/manifest.json", "0", run_manifest)
    generation, current = leases.read(LEASE_OBJECT)
    if (not current or current.get("run_id") != run_id or current.get("status") != "starting"
            or current.get("expires_at", 0) <= time.time()):
        if current and current.get("run_id") == run_id and current.get("status") == "starting" and not current.get("operation"):
            current.update(status="failed", completed_at=time.time(), failure_reason="preflight_cancelled_or_expired")
            leases.write(LEASE_OBJECT, generation, current)
        raise RuntimeError("The load-test lease was cancelled or expired during remote preflight")
    with demo_control_lock(config, access):
        generation, current = leases.read(LEASE_OBJECT)
        if (not current or current.get("run_id") != run_id or current.get("status") != "starting"
                or current.get("expires_at", 0) <= time.time()):
            raise RuntimeError("The load-test lease changed before Cloud Run launch")
        current["launch_requested_at"] = time.time()
        leases.write(LEASE_OBJECT, generation, current)
    url = f"https://run.googleapis.com/v2/projects/{config['GCP_PROJECT_ID']}/locations/{REGION}/jobs/{JOB}:run"
    try:
        operation = gcp_request("POST", url, config["GCP_PROJECT_ID"], {"overrides": {"containerOverrides": [{"env": [
            {"name": "NEXORUTA_LOAD_PROFILE_NAME", "value": profile},
            {"name": "NEXORUTA_RUN_ID", "value": run_id},
            {"name": "NEXORUTA_LOAD_FIXTURE_VERSION", "value": manifest["fixture_version"]},
        ]}]}})
        name = operation.get("name", "")
        if not name:
            raise RuntimeError("Cloud Run did not return an execution operation")
        with demo_control_lock_retry(config, access):
            generation, current = leases.read(LEASE_OBJECT)
            if not current or current.get("run_id") != run_id:
                raise RuntimeError("The load-test lease changed after Cloud Run accepted the execution")
            current["operation"] = name
            cancelled_or_expired = (current.get("status") != "starting"
                                    or current.get("expires_at", 0) <= time.time())
            if cancelled_or_expired:
                current["status"] = "cancelling"
                current["cancel_requested_at"] = current.get("cancel_requested_at", time.time())
            leases.write(LEASE_OBJECT, generation, current)
        execution = wait_for_execution_reference(config["GCP_PROJECT_ID"], run_id, name)
        with demo_control_lock_retry(config, access):
            generation, current = leases.read(LEASE_OBJECT)
            if (not current or current.get("run_id") != run_id or current.get("status") != "starting"
                    or current.get("expires_at", 0) <= time.time()):
                if current and current.get("run_id") == run_id:
                    current["execution"] = execution
                    current["status"] = "cancelling"
                    current["cancel_requested_at"] = current.get("cancel_requested_at", time.time())
                    leases.write(LEASE_OBJECT, generation, current)
                should_cancel = True
            else:
                current.update(status="running", execution=execution)
                leases.write(LEASE_OBJECT, generation, current)
                should_cancel = False
        if should_cancel:
            try:
                gcp_request("POST", "https://run.googleapis.com/v2/" + execution + ":cancel", config["GCP_PROJECT_ID"], {})
            except urllib.error.HTTPError as error:
                if error.code not in (404, 409):
                    raise
            raise RuntimeError("The load-test lease changed while Cloud Run started; the execution was cancelled")
    except urllib.error.HTTPError as error:
        if error.code < 500:
            generation, failed = leases.read(LEASE_OBJECT)
            if failed and failed.get("run_id") == run_id and failed.get("status") == "starting":
                failed.update(status="failed", completed_at=time.time(), failure_reason=f"cloud_run_http_{error.code}")
                leases.write(LEASE_OBJECT, generation, failed)
            raise RuntimeError(f"Cloud Run rejected the load-test request with HTTP {error.code}") from None
        raise RuntimeError("Cloud Run returned a server error; execution state remains ambiguous for reconciliation") from None
    except Exception:
        # Leave the reservation recoverable if the API response was lost; a new
        # execution must never race an ambiguous jobs.run request.
        raise
    result = {"run_id": run_id, "operation": name, "execution": execution, "profile": profile}
    print(json.dumps(result))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            for key, value in result.items():
                stream.write(f"{key}={value}\n")


def reserve(config, profile):
    if profile not in PROFILES:
        raise ValueError("Select one of smoke, baseline, sync, stress or soak")
    run_id = str(uuid.uuid4())
    access = token(config["GCP_PROJECT_ID"])
    state = Storage(config["GCP_STATE_BUCKET"], access)
    leases = Storage(load_control_bucket(config), access)
    fixture_version = latest_fixture_version(config["GCP_PROJECT_ID"])
    with demo_control_lock(config, access):
        generation, active = leases.read(LEASE_OBJECT)
        now = time.time()
        expired_reservation = bool(active and active.get("status") == "reserved" and active.get("expires_at", 0) <= now)
        if active and active.get("status") in ("reserved", "starting", "running", "cancelling") and not expired_reservation:
            if active.get("status") == "reserved" or not reconcile_execution(leases, config["GCP_PROJECT_ID"], active["run_id"]):
                raise RuntimeError("A load-test execution is already reserved; finish or cancel it first")
            generation, active = leases.read(LEASE_OBJECT)
        _, session = state.read("leases/demo.json")
        if not session or session.get("expires_at", 0) <= now:
            raise RuntimeError("The remote demo session is not active")
        if session["expires_at"] - now < PROFILES[profile] + 600:
            raise RuntimeError("The active VM session does not have enough time for this profile and cleanup")
        manifest = immutable_manifest(config, run_id, profile, session["expires_at"], fixture_version)
        manifest.update(status="reserved", owner=os.environ.get("GITHUB_RUN_ID", "manual"),
                        created_at=now, expires_at=min(session["expires_at"], now + 900))
        leases.write(LEASE_OBJECT, generation, manifest)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"run_id={run_id}\n")
            stream.write(f"fixture_version={fixture_version}\n")
    print(json.dumps({"run_id": run_id, "profile": profile, "fixture_version": fixture_version, "status": "reserved"}))


def execution_report(active, cloud_state, summary):
    run_id = active["run_id"]
    if not isinstance(summary, dict) or summary.get("run_id") != run_id:
        cancelled = bool(active.get("cancel_requested_at"))
        return {"run_id": run_id, "status": "cancelled" if cancelled else "failed",
                "classification": "cancelled" if cancelled else "infrastructure_failed",
                "stop_reason": "runner_summary_missing_or_mismatched"}
    if cloud_state != "CONDITION_SUCCEEDED" and summary.get("status") == "passed":
        return {**summary, "status": "failed", "classification": "infrastructure_failed",
                "stop_reason": "cloud_execution_failed_after_runner"}
    if summary.get("status") == "passed" and (summary.get("classification") != "passed"
            or not summary.get("evidence", {}).get("measured_requests")
            or not (summary.get("evidence", {}).get("measurement_report") or {}).get("valid")
            or not (summary.get("evidence", {}).get("measurement_report") or {}).get("complete")
            or not summary.get("evidence", {}).get("generator_cpu_samples")
            or not summary.get("evidence", {}).get("generator_memory_samples")
            or not summary.get("authentication", {}).get("ready")
            or summary.get("authentication", {}).get("fault")
            or not summary.get("session_cleanup", {}).get("complete")):
        return {**summary, "status": "failed", "classification": "incomplete_evidence"}
    return summary


def wait(config, run_id):
    access = token(config["GCP_PROJECT_ID"])
    leases = Storage(load_control_bucket(config), access)
    results = Storage(config["GCP_LOAD_RESULTS_BUCKET"], access)
    generation, active = leases.read(LEASE_OBJECT)
    if not active or active.get("run_id") != run_id:
        raise RuntimeError("No matching Cloud Run execution is recorded")
    execution_name = active.get("execution") or wait_for_execution_reference(
        config["GCP_PROJECT_ID"], run_id, active.get("operation", ""))
    if not active.get("execution"):
        with demo_control_lock_retry(config, access):
            generation, current = leases.read(LEASE_OBJECT)
            if not current or current.get("run_id") != run_id:
                raise RuntimeError("The load-test lease changed while recovering its execution")
            current["execution"] = execution_name
            if current.get("status") == "starting":
                current["status"] = "running"
            leases.write(LEASE_OBJECT, generation, current)
        active["execution"] = execution_name
    remaining_lease = active.get("expires_at", 0) - time.time()
    recovery_window = min(PROFILES[active["profile"]] + 180, max(60, remaining_lease))
    deadline = time.monotonic() + recovery_window
    execution = "https://run.googleapis.com/v2/" + execution_name
    while time.monotonic() < deadline:
        current = gcp_request("GET", execution, config["GCP_PROJECT_ID"])
        completed = next((item for item in current.get("conditions", []) if item.get("type") == "Completed"), None)
        if completed and completed.get("state") in ("CONDITION_SUCCEEDED", "CONDITION_FAILED"):
            generation, lease = leases.read(LEASE_OBJECT)
            _, summary = results.read(f"runs/{run_id}/summary.json")
            observed = lease if lease and lease.get("run_id") == run_id else active
            report = execution_report(observed, completed["state"], summary)
            report.update(execution=execution_name, cloud_state=completed["state"])
            _, existing = results.read(f"runs/{run_id}/controller-summary.json")
            if existing is None:
                try:
                    results.write(f"runs/{run_id}/controller-summary.json", "0", report)
                except urllib.error.HTTPError as error:
                    if error.code != 412:
                        raise
            if lease and lease.get("run_id") == run_id:
                lease.update(status="completed" if report.get("status") == "passed" else "failed",
                             completed_at=time.time(), execution_status=completed["state"])
                leases.write(LEASE_OBJECT, generation, lease)
            print(json.dumps({"run_id": run_id, "execution": execution_name,
                              "status": completed["state"], "result": report}))
            return completed["state"] == "CONDITION_SUCCEEDED" and report.get("status") == "passed"
        time.sleep(10)
    raise RuntimeError("The load-test execution exceeded its bounded deadline and remains available for cancellation")


def cancel(config, run_id=None, wait_seconds=120):
    access = token(config["GCP_PROJECT_ID"])
    state = Storage(config["GCP_STATE_BUCKET"], access)
    leases = Storage(load_control_bucket(config), access)
    lock = (nullcontext() if os.environ.get("NEXORUTA_CONTROL_LOCK_HELD") == "true"
            else demo_control_lock_retry(config, access))
    with lock:
        generation, active = leases.read(LEASE_OBJECT)
        if not active or (run_id and active.get("run_id") != run_id):
            return "No matching load-test execution is active."
        if active.get("status") not in ("reserved", "starting", "running", "cancelling"):
            return "The matching load-test execution is already finished."
        if active.get("status") == "reserved" and not active.get("operation"):
            active.update(status="cancelled", completed_at=time.time())
            leases.write(LEASE_OBJECT, generation, active)
            return "Load-test reservation cancelled before Cloud Run started."
        active["cancel_requested_at"] = time.time()
        active["status"] = "cancelling"
        active["expires_at"] = min(active.get("expires_at", time.time()), time.time())
        leases.write(LEASE_OBJECT, generation, active)
    execution_name = active.get("execution")
    discovery_deadline = time.monotonic() + wait_seconds
    while not execution_name and time.monotonic() < discovery_deadline:
        _, current_lease = leases.read(LEASE_OBJECT)
        if not current_lease or current_lease.get("run_id") != active.get("run_id"):
            return "Load-test execution finished."
        execution_name = current_lease.get("execution") or execution_reference(
            config["GCP_PROJECT_ID"], active["run_id"], current_lease.get("operation", ""))
        if execution_name:
            with demo_control_lock_retry(config, access):
                generation, current_lease = leases.read(LEASE_OBJECT)
                if current_lease and current_lease.get("run_id") == active.get("run_id"):
                    current_lease["execution"] = execution_name
                    leases.write(LEASE_OBJECT, generation, current_lease)
            break
        time.sleep(2)
    if not execution_name:
        raise RuntimeError("Cancellation is pending while Cloud Run exposes the exact execution; the guard must retry")
    if execution_name:
        current = gcp_request("GET", "https://run.googleapis.com/v2/" + execution_name,
                              config["GCP_PROJECT_ID"])
        completed = next((item for item in current.get("conditions", []) if item.get("type") == "Completed"), None)
        if completed and completed.get("state") in ("CONDITION_SUCCEEDED", "CONDITION_FAILED"):
            return "Load-test execution already finished."
        endpoint = "https://run.googleapis.com/v2/" + execution_name + ":cancel"
        try:
            gcp_request("POST", endpoint, config["GCP_PROJECT_ID"], {})
        except urllib.error.HTTPError as error:
            if error.code not in (404, 409):
                raise
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        generation, active = leases.read(LEASE_OBJECT)
        if not active or (run_id and active.get("run_id") != run_id):
            return "Load-test execution finished."
        current = gcp_request("GET", "https://run.googleapis.com/v2/" + execution_name, config["GCP_PROJECT_ID"]) if execution_name else {}
        completed = next((item for item in current.get("conditions", []) if item.get("type") == "Completed"), None)
        if completed and completed.get("state") in ("CONDITION_SUCCEEDED", "CONDITION_FAILED"):
            return "Load-test execution finished."
        time.sleep(5)
    raise RuntimeError("Cancellation is still pending; the independent session guard must retry")


def assert_no_active(config):
    leases = Storage(load_control_bucket(config), token(config["GCP_PROJECT_ID"]))
    _, active = leases.read(LEASE_OBJECT)
    if not active or active.get("status") not in ("reserved", "starting", "running", "cancelling"):
        return
    if active.get("status") == "reserved":
        if active.get("expires_at", 0) <= time.time():
            return
        raise RuntimeError("A load-test image is being prepared; wait or cancel its reservation before VM start/update")
    if not reconcile_execution(leases, config["GCP_PROJECT_ID"], active["run_id"]):
        raise RuntimeError("A remote load test is active; cancel it before starting or updating the demo")


def main(args):
    settings = config()
    if args[0] == "run" and len(args) == 2:
        run(settings, args[1])
    elif args[0] == "run" and len(args) == 3:
        run(settings, args[1], args[2])
    elif args[0] == "reserve" and len(args) == 2:
        reserve(settings, args[1])
    elif args[0] == "cancel" and len(args) <= 2:
        print(cancel(settings, args[1] if len(args) == 2 else None))
    elif args[0] == "wait" and len(args) == 2:
        if not wait(settings, args[1]):
            raise SystemExit(1)
    elif args[0] == "check-active" and len(args) == 1:
        assert_no_active(settings)
    else:
        raise ValueError("Usage: load_tests.py reserve PROFILE | run PROFILE [RUN_ID] | wait RUN_ID | cancel [RUN_ID]")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(f"Load-test control failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
