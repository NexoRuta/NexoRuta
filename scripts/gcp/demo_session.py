"""Apply a bounded VM session, from GitHub Actions or a local terminal."""

import datetime as dt
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import json


ROOT = Path(__file__).resolve().parents[2]
INFRA = ROOT / "infra" / "gcp" / "demo"
VM_NAME = "nexoruta-demo"
MAX_SECONDS = 4 * 60 * 60
REGION = "southamerica-west1"
ACTIVE_CONTROL_LOCK = None


def measure(phase, operation, **dimensions):
    started = time.perf_counter()
    status = "passed"
    try:
        return operation()
    except Exception:
        status = "failed"
        raise
    finally:
        print("NEXORUTA_SESSION_TIMING " + json.dumps({
            "phase": phase,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "status": status,
            **dimensions,
        }, sort_keys=True), flush=True)


def configuration():
    patterns = {
        "GCP_PROJECT_ID": r"[a-z][a-z0-9-]{4,28}[a-z0-9]",
        "GCP_ZONE": r"[a-z]+(?:-[a-z]+)*[0-9]-[a-z]",
        "GCP_STATE_BUCKET": r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]",
        "DEMO_OPERATION": r"start|stop|update",
    }
    values = {}
    for key, pattern in patterns.items():
        value = os.environ.get(key, "")
        if not re.fullmatch(pattern, value):
            raise ValueError(f"Missing or invalid {key}")
        values[key] = value
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for key in ("GCP_WORKLOAD_IDENTITY_PROVIDER", "GCP_DEPLOY_SERVICE_ACCOUNT"):
            if not os.environ.get(key):
                raise ValueError(f"Missing GitHub environment variable {key}")
    if values["GCP_ZONE"] != REGION + "-a":
        raise ValueError("Use southamerica-west1-a (Santiago), close to Uruguay")
    values["GCP_SECONDARY_ZONE"] = os.environ.get("GCP_SECONDARY_ZONE", REGION + "-b")
    if values["GCP_SECONDARY_ZONE"] not in (REGION + "-b", REGION + "-c"):
        raise ValueError("Use southamerica-west1-b or southamerica-west1-c for the second VM")
    return values


def command(*args, capture=False):
    if ACTIVE_CONTROL_LOCK is not None:
        ACTIVE_CONTROL_LOCK.check()
    # Resolve .cmd wrappers on Windows as well as native Linux executables.
    executable = shutil.which(args[0])
    if not executable:
        raise RuntimeError(f"Install {args[0]} and refresh the terminal PATH first.")
    result = subprocess.run(
        [executable, *args[1:]], check=True, text=True, capture_output=capture,
    )
    return result.stdout if capture else None


def gcloud(config, *args, capture=False):
    zone_flag = "--zones" if args[:3] == ("compute", "instances", "list") else "--zone"
    return command(
        "gcloud", *args, f"--project={config['GCP_PROJECT_ID']}",
        f"{zone_flag}={config['GCP_ZONE']}", "--quiet", capture=capture,
    )


def node_configs(config):
    return [
        {**config, "NODE_ID": "a", "VM_NAME": VM_NAME, "GCP_ZONE": config.get("GCP_ZONE", REGION + "-a")},
        {**config, "NODE_ID": "b", "VM_NAME": VM_NAME + "-b", "GCP_ZONE": config.get("GCP_SECONDARY_ZONE", REGION + "-b")},
    ]


def instance(config):
    # `list` distinguishes a missing VM from authentication/API/network failures.
    name = config.get("VM_NAME", VM_NAME)
    result = json.loads(gcloud(
        config, "compute", "instances", "list",
        f"--filter=name={name}", "--format=json", capture=True,
    ))
    matches = [vm for vm in result if vm["name"] == name]
    if len(matches) > 1:
        raise RuntimeError("Unexpected duplicate VM names in the selected zone.")
    return matches[0] if matches else None


def check_existing(vm, operation):
    if vm is None:
        if operation == "stop":
            raise RuntimeError("No VM exists to stop; refusing to create infrastructure.")
        return
    labels = vm.get("labels", {})
    if labels.get("application") != "nexoruta" or labels.get("managed_by") != "opentofu":
        raise RuntimeError("The existing VM is not labeled as this OpenTofu deployment.")
    status = vm.get("status")
    if operation == "start" and status == "RUNNING":
        deadline = vm.get("resourceStatus", {}).get("scheduling", {}).get("terminationTimestamp", "unknown")
        raise RuntimeError(
            f"A session is already running (deadline: {deadline}). "
            "It will not be restarted or extended; stop it before a new session."
        )
    if status not in ("TERMINATED", "RUNNING"):
        raise RuntimeError(f"VM is {status}; wait for its current operation to finish.")


def check_plan(plan, operation="start"):
    for resource in plan.get("resource_changes", []):
        if operation == "stop" and "create" in resource["change"]["actions"]:
            raise RuntimeError("Stopping a session must not create missing resources")
        if "delete" in resource["change"]["actions"]:
            # New immutable secret versions retain their predecessors (ABANDON).
            # This exception never permits deleting a secret or persistent resource.
            if (resource.get("type") == "google_secret_manager_secret_version"
                    and resource["change"].get("before", {}).get("deletion_policy") == "ABANDON"
                    and resource["change"].get("after", {}).get("deletion_policy") == "ABANDON"
                    and "create" in resource["change"]["actions"]):
                continue
            raise RuntimeError(
                f"Plan would delete or replace {resource['address']}. "
                "This session workflow does not destroy resources; review locally."
            )


def check_deadline(vm, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    scheduling = vm.get("scheduling", {})
    if (
        vm.get("status") != "RUNNING"
        or int(scheduling.get("maxRunDuration", {}).get("seconds", 0)) != MAX_SECONDS
        or scheduling.get("instanceTerminationAction") != "STOP"
        or scheduling.get("automaticRestart") is not False
    ):
        raise RuntimeError("The VM does not have the required four-hour STOP policy.")
    timestamp = vm.get("resourceStatus", {}).get("scheduling", {}).get("terminationTimestamp")
    if not timestamp:
        raise RuntimeError("Google Cloud did not report a VM termination timestamp.")
    deadline = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    remaining = (deadline - now).total_seconds()
    if not 0 < remaining <= MAX_SECONDS + 60:
        raise RuntimeError("The reported termination timestamp exceeds this session's limit.")
    return timestamp


def stop_after_failure(config):
    errors = measure("failure_cleanup", lambda: stop_session(config))
    for error in errors:
        print(f"Cleanup will be retried by the independent guard: {error}", file=sys.stderr)


def stop_session(config):
    # Close the lease first; stop both VMs independently and leave SQL running.
    errors = []
    try:
        measure("close_session_lease", lambda: end_lease(config))
    except (RuntimeError, subprocess.CalledProcessError, ValueError) as error:
        errors.append(f"lease: {error}")
    def stop_node(node):
        try:
            vm = measure("find_vm", lambda: instance(node), node=node["NODE_ID"])
            if vm is None:
                return None
            check_existing(vm, "stop")
            if vm.get("status") == "RUNNING":
                measure("stop_vm", lambda: gcloud(node, "compute", "instances", "stop", node["VM_NAME"]), node=node["NODE_ID"])
        except (RuntimeError, subprocess.CalledProcessError, ValueError) as error:
            return f"{node['VM_NAME']}: {error}"
        return None
    with ThreadPoolExecutor(max_workers=2) as executor:
        for error in executor.map(stop_node, node_configs(config)):
            if error:
                errors.append(error)
    return errors


def write_lease(config, expires_at, provisioning_until=0):
    with tempfile.TemporaryDirectory(prefix="nexoruta-lease-") as temp:
        path = Path(temp) / "demo.json"
        path.write_text(json.dumps({"expires_at": expires_at, "provisioning_until": provisioning_until}), encoding="utf-8")
        command("gcloud", "storage", "cp", str(path),
                f"gs://{config['GCP_STATE_BUCKET']}/leases/demo.json",
                "--content-type=application/json", "--quiet")


def end_lease(config):
    write_lease(config, 0)


def start_database(config):
    # Cloud SQL cannot list PostgreSQL users while stopped. Wake it before
    # OpenTofu refreshes google_sql_user, while the provisioning lease protects it.
    project = config["GCP_PROJECT_ID"]
    databases = json.loads(command("gcloud", "sql", "instances", "list", f"--project={project}",
                                   "--filter=name=nexoruta-demo-db", "--format=json", capture=True))
    for database in databases:
        if database["name"] != "nexoruta-demo-db":
            continue
        if database.get("settings", {}).get("userLabels", {}).get("managed_by") != "opentofu":
            raise RuntimeError("Refusing to start a database not owned by this deployment")
        if database["settings"]["activationPolicy"] != "ALWAYS":
            command("gcloud", "sql", "instances", "patch", "nexoruta-demo-db", f"--project={project}",
                    "--activation-policy=ALWAYS", "--quiet")
        elif database.get("state") == "RUNNABLE":
            return
        for _ in range(120):
            ready = json.loads(command("gcloud", "sql", "instances", "describe", "nexoruta-demo-db",
                                       f"--project={project}", "--format=json", capture=True))
            if ready.get("state") == "RUNNABLE":
                return
            time.sleep(5)
        raise RuntimeError("Cloud SQL did not become RUNNABLE before refreshing its users")


def run(config):
    operation = config["DEMO_OPERATION"]
    if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise RuntimeError("VM operations require a manual workflow_dispatch; pushes only publish images")
    if operation == "stop":
        errors = stop_session(config)
        if errors:
            raise RuntimeError("Cleanup incomplete; independent guard will retry: " + "; ".join(errors))
        message = "Both demo VMs stopped or absent. Cloud SQL remains running.\n"
        print(message)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as output:
                output.write(message)
        return
    nodes = node_configs(config)
    existing = [instance(node) for node in nodes]
    for vm in existing:
        check_existing(vm, operation)
    if operation == "update":
        running = sum(vm is not None and vm.get("status") == "RUNNING" for vm in existing)
        if running == 0:
            print("Demo is off. Use start to begin a four-hour session.")
            return
        if running != len(nodes):
            raise RuntimeError("Demo is degraded: both VMs must be RUNNING before update; the session will not be extended.")
        for vm in existing:
            check_deadline(vm)
        from delivery import deploy, latest_release
        release = measure("select_latest_release", lambda: latest_release(config))
        deployed = measure("application_deployment", lambda: deploy(config, release))
        for node, before in zip(nodes, existing):
            after = instance(node)
            if not after or after.get("status") != "RUNNING" or after.get("lastStartTimestamp") != before.get("lastStartTimestamp"):
                raise RuntimeError("An application update must not restart or stop either VM")
            check_deadline(after)
        print("Application updated without extending the existing four-hour session.")
        publish_endpoints(config, deployed["endpoints"])
        return
    from delivery import latest_release
    release = measure("select_latest_release", lambda: latest_release(config))
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    measure("set_provisioning_lease", lambda: write_lease(config, now + MAX_SECONDS + 1800, now + 1800))
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            database = executor.submit(measure, "start_cloud_sql", lambda: start_database(config))
            tofu_setup = executor.submit(initialize_tofu, config)
            database.result()
            tofu_setup.result()
        measure("start_session_total", lambda: start_session(config, release))
    except Exception:
        stop_after_failure(config)
        raise


def initialize_tofu(config):
    tofu = ("tofu", f"-chdir={INFRA}")
    measure("tofu_init", lambda: command(
        *tofu, "init", "-input=false", "-lockfile=readonly",
        f"-backend-config=bucket={config['GCP_STATE_BUCKET']}",
        "-backend-config=prefix=demo/vm",
    ))
    measure("tofu_validate", lambda: command(*tofu, "validate"))


def start_session(config, release):
    tofu = ("tofu", f"-chdir={INFRA}")
    with tempfile.TemporaryDirectory(prefix="nexoruta-session-") as temp:
        inputs = Path(temp) / "session.tfvars.json"
        inputs.write_text(json.dumps({
            "project_id": config["GCP_PROJECT_ID"],
            "zone": config["GCP_ZONE"],
            "secondary_zone": config.get("GCP_SECONDARY_ZONE", REGION + "-b"),
            "running": True,
            "base_domain": os.environ.get("GCP_BASE_DOMAIN", ""),
            "manage_dns": os.environ.get("GCP_MANAGE_DNS", "false").lower() == "true",
        }), encoding="utf-8")
        plan_file = Path(temp) / "session.tfplan"
        measure("tofu_plan", lambda: command(
            *tofu, "plan", "-input=false", "-lock-timeout=5m",
            f"-var-file={inputs}", f"-out={plan_file}",
        ))
        plan = measure("tofu_show_and_safety_check", lambda: json.loads(command(*tofu, "show", "-json", str(plan_file), capture=True)))
        measure("tofu_check_plan", lambda: check_plan(plan))
        measure("tofu_apply", lambda: command(*tofu, "apply", "-input=false", "-lock-timeout=5m", str(plan_file)))
        deadlines = []
        for node in node_configs(config):
            vm = json.loads(measure("read_vm_deadline", lambda: gcloud(
                node, "compute", "instances", "describe", node["VM_NAME"],
                "--format=json", capture=True,
            ), node=node["NODE_ID"]))
            deadlines.append(dt.datetime.fromisoformat(check_deadline(vm).replace("Z", "+00:00")))
        deadline = min(deadlines)
        measure("set_common_session_lease", lambda: write_lease(config, deadline.timestamp()))
        from delivery import deploy
        measure("application_deployment", lambda: deploy(config, release))
        message = (
            f"Both demo VMs running with {release}. Common automatic stop: {deadline.isoformat()}.\n\n"
            "The four hours start when Compute Engine starts the VM, including bootstrap. "
            "HTTPS health and initial database-backed login checks passed.\n"
        )
    print(message)
    measure("publish_application_endpoints", lambda: publish_endpoints(config))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write(message)


def publish_endpoints(config, endpoints=None):
    if endpoints is None:
        endpoints = json.loads(command("tofu", f"-chdir={INFRA}", "output", "-json", "endpoints", capture=True))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"api_origin={endpoints['api']}\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as output:
            for name, url in endpoints.items():
                output.write(f"- {name}: {url}\n")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("check", "run"):
        raise ValueError("Usage: demo_session.py check|run")
    config = configuration()
    if sys.argv[1] == "run":
        from control_lock import control_lock
        global ACTIVE_CONTROL_LOCK
        with control_lock(config) as lock:
            ACTIVE_CONTROL_LOCK = lock
            try:
                run(config)
            finally:
                ACTIVE_CONTROL_LOCK = None
    else:
        print("Session configuration is valid.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Session failed: {error}", file=sys.stderr)
        sys.exit(1)
