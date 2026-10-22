"""Apply a bounded VM session, from GitHub Actions or a local terminal."""

import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
INFRA = ROOT / "infra" / "gcp" / "demo"
VM_NAME = "nexoruta-demo"
MAX_SECONDS = 4 * 60 * 60
REGION = "southamerica-west1"


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
    return values


def command(*args, capture=False):
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


def instance(config):
    # `list` distinguishes a missing VM from authentication/API/network failures.
    result = json.loads(gcloud(
        config, "compute", "instances", "list",
        f"--filter=name={VM_NAME}", "--format=json", capture=True,
    ))
    matches = [vm for vm in result if vm["name"] == VM_NAME]
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
    try:
        vm = instance(config)
        if (
            vm and vm.get("labels", {}).get("application") == "nexoruta"
            and vm.get("labels", {}).get("managed_by") == "opentofu"
            and vm.get("status") == "RUNNING"
        ):
            gcloud(config, "compute", "instances", "stop", VM_NAME)
    except (RuntimeError, subprocess.CalledProcessError, ValueError) as error:
        print(f"Could not stop after failure: {error}", file=sys.stderr)
    for cleanup in (end_lease, stop_database):
        try:
            cleanup(config)
        except (RuntimeError, subprocess.CalledProcessError, ValueError) as error:
            print(f"Cleanup will be retried by the independent guard: {error}", file=sys.stderr)


def write_lease(config, expires_at, provisioning_until=0):
    with tempfile.TemporaryDirectory(prefix="nexoruta-lease-") as temp:
        path = Path(temp) / "demo.json"
        path.write_text(json.dumps({"expires_at": expires_at, "provisioning_until": provisioning_until}), encoding="utf-8")
        command("gcloud", "storage", "cp", str(path),
                f"gs://{config['GCP_STATE_BUCKET']}/leases/demo.json",
                "--content-type=application/json", "--quiet")


def end_lease(config):
    write_lease(config, 0)


def stop_database(config):
    project = config["GCP_PROJECT_ID"]
    databases = json.loads(command("gcloud", "sql", "instances", "list", f"--project={project}",
                                   "--filter=name=nexoruta-demo-db", "--format=json", capture=True))
    for database in databases:
        if database["name"] == "nexoruta-demo-db":
            if database.get("settings", {}).get("userLabels", {}).get("managed_by") != "opentofu":
                raise RuntimeError("Refusing to stop a database not owned by this deployment")
            if database["settings"]["activationPolicy"] != "NEVER":
                command("gcloud", "sql", "instances", "patch", "nexoruta-demo-db", f"--project={project}",
                        "--activation-policy=NEVER", "--quiet")


def run(config):
    operation = config["DEMO_OPERATION"]
    if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise RuntimeError("VM operations require a manual workflow_dispatch; pushes only publish images")
    existing = instance(config)
    if operation == "update":
        if not existing or existing.get("status") != "RUNNING":
            print("Demo is off. Use start to begin a four-hour session.")
            return
        check_existing(existing, operation)
        check_deadline(existing)
        from delivery import deploy, latest_release
        deployed = deploy(config, latest_release(config))
        after = instance(config)
        if after.get("lastStartTimestamp") != existing.get("lastStartTimestamp"):
            raise RuntimeError("An application update must not restart the VM")
        print("Application updated without extending the existing four-hour session.")
        publish_endpoints(config, deployed["endpoints"])
        return
    if operation == "stop" and existing is None:
        end_lease(config)
        stop_database(config)
        print("No VM exists. Cloud SQL cleanup completed without creating infrastructure.")
        return
    check_existing(existing, operation)
    if operation == "start" and not re.fullmatch(r"release-[a-f0-9]{32}", os.environ.get("DEMO_RELEASE", "")):
        raise ValueError("A tested, published DEMO_RELEASE is required before starting the VM")
    if operation == "start":
        now = dt.datetime.now(dt.timezone.utc).timestamp()
        write_lease(config, now + MAX_SECONDS + 1800, now + 1800)
    else:
        end_lease(config)
        if existing.get("status") == "RUNNING":
            gcloud(config, "compute", "instances", "stop", VM_NAME)
        stop_database(config)
    tofu = ("tofu", f"-chdir={INFRA}")
    command(
        *tofu, "init", "-input=false", "-lockfile=readonly",
        f"-backend-config=bucket={config['GCP_STATE_BUCKET']}",
        "-backend-config=prefix=demo/vm",
    )
    command(*tofu, "validate")
    with tempfile.TemporaryDirectory(prefix="nexoruta-session-") as temp:
        inputs = Path(temp) / "session.tfvars.json"
        inputs.write_text(json.dumps({
            "project_id": config["GCP_PROJECT_ID"],
            "zone": config["GCP_ZONE"],
            "running": operation == "start",
            "base_domain": os.environ.get("GCP_BASE_DOMAIN", ""),
            "manage_dns": os.environ.get("GCP_MANAGE_DNS", "false").lower() == "true",
        }), encoding="utf-8")
        plan_file = Path(temp) / "session.tfplan"
        command(
            *tofu, "plan", "-input=false", "-lock-timeout=5m",
            f"-var-file={inputs}", f"-out={plan_file}",
        )
        plan = json.loads(command(*tofu, "show", "-json", str(plan_file), capture=True))
        check_plan(plan, operation)
        try:
            command(*tofu, "apply", "-input=false", "-lock-timeout=5m", str(plan_file))
            vm = json.loads(gcloud(
                config, "compute", "instances", "describe", VM_NAME,
                "--format=json", capture=True,
            ))
            if operation == "start":
                deadline = check_deadline(vm)
                write_lease(config, dt.datetime.fromisoformat(deadline.replace("Z", "+00:00")).timestamp())
                from delivery import deploy
                deploy(config, os.environ["DEMO_RELEASE"])
                message = (
                    f"VM {VM_NAME} running. Automatic stop: {deadline}.\n\n"
                    "The four hours start when Compute Engine starts the VM, including bootstrap. "
                    "HTTPS health and initial database-backed login checks passed.\n"
                )
            else:
                if vm.get("status") != "TERMINATED":
                    raise RuntimeError("The VM did not reach TERMINATED.")
                message = f"VM {VM_NAME} and Cloud SQL stopped. Persistent storage and static IP retained.\n"
        except Exception:
            if operation == "start":
                stop_after_failure(config)
            raise
    print(message)
    if operation == "start":
        publish_endpoints(config)
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
        run(config)
    else:
        print("Session configuration is valid.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Session failed: {error}", file=sys.stderr)
        sys.exit(1)
