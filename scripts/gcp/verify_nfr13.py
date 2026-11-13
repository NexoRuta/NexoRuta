"""Inspect NFR-13's GCP demo or run one explicitly authorized failover scenario.

The default command is read-only. Fault commands require an explicit subcommand,
the exact expected release, the demo API origin, and a typed confirmation. All
mutations are serialized with the existing deployment/guard control lock.
"""

import argparse
import datetime as dt
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import control_lock
import demo_session
import delivery


PROJECT = "nexoruta-demo-20261022"
STATE_BUCKET = PROJECT + "-tofu-state"
DELIVERY_BUCKET = PROJECT + "-nexoruta-delivery"
ZONE_A = "southamerica-west1-a"
ZONE_B = "southamerica-west1-b"
API_BACKEND = "nexoruta-demo-api"
MIN_FAULT_WINDOW_SECONDS = 90 * 60
RECOVERY_SECONDS = 60
OBSERVATION_SECONDS = 90
STABLE_SUCCESSES = 10
EXPECTED_LABELS = {"application": "nexoruta", "environment": "demo", "managed_by": "opentofu"}
EXPECTED_MACHINE_TYPE = "n4-custom-6-16384"


def configuration(project=None, state_bucket=None, zone_a=None, zone_b=None):
    """Return the one permitted demo inventory; never infer a production target."""
    project = project or os.environ.get("GCP_PROJECT_ID") or PROJECT
    state_bucket = state_bucket or os.environ.get("GCP_STATE_BUCKET") or STATE_BUCKET
    zone_a = zone_a or os.environ.get("GCP_ZONE") or ZONE_A
    zone_b = zone_b or os.environ.get("GCP_SECONDARY_ZONE") or ZONE_B
    if project != PROJECT or state_bucket != STATE_BUCKET or zone_a != ZONE_A or zone_b != ZONE_B:
        raise ValueError("NFR-13 verification is restricted to the registered NexoRuta demo inventory")
    return {
        "GCP_PROJECT_ID": project,
        "GCP_STATE_BUCKET": state_bucket,
        "GCP_DELIVERY_BUCKET": DELIVERY_BUCKET,
        "GCP_ZONE": zone_a,
        "GCP_SECONDARY_ZONE": zone_b,
    }


def api_origin(value):
    parsed = urllib.parse.urlsplit(value or "")
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.port is not None or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment or not parsed.hostname.startswith("api.")):
        raise ValueError("API origin must be the HTTPS api.* origin from the demo deployment")
    return value.rstrip("/")


def instance_summary(config, node, vm):
    if vm is None:
        return {"node": node["NODE_ID"], "name": node["VM_NAME"], "status": "MISSING"}
    if vm.get("name") != node["VM_NAME"] or vm.get("zone", "").rsplit("/", 1)[-1] != node["GCP_ZONE"]:
        raise RuntimeError("Compute returned an instance outside the exact registered NFR-13 inventory")
    labels = vm.get("labels", {})
    if any(labels.get(key) != value for key, value in EXPECTED_LABELS.items()):
        raise RuntimeError("A demo VM is missing its required OpenTofu/demo ownership labels")
    machine_type = vm.get("machineType", "").rsplit("/", 1)[-1]
    if machine_type != EXPECTED_MACHINE_TYPE:
        raise RuntimeError("A demo VM does not match the registered NFR-13 machine type")
    return {
        "node": node["NODE_ID"],
        "name": node["VM_NAME"],
        "zone": node["GCP_ZONE"],
        "status": vm.get("status", "UNKNOWN"),
        "machine_type": machine_type,
        "boot_disk": next((disk.get("source", "").rsplit("/", 1)[-1]
                            for disk in vm.get("disks", []) if disk.get("boot")), None),
    }


def read_session_lease(config):
    raw = demo_session.command(
        "gcloud", "storage", "cat", f"gs://{config['GCP_STATE_BUCKET']}/leases/demo.json", capture=True,
    )
    value = json.loads(raw)
    expires_at = value.get("expires_at")
    if type(expires_at) not in (int, float) or not expires_at > 0:
        raise RuntimeError("The bounded demo session lease is missing or malformed")
    return value


def database_summary(config):
    raw = demo_session.command(
        "gcloud", "sql", "instances", "describe", "nexoruta-demo-db",
        f"--project={config['GCP_PROJECT_ID']}", "--format=json", capture=True,
    )
    database = json.loads(raw)
    labels = database.get("settings", {}).get("userLabels", {})
    if (database.get("name") != "nexoruta-demo-db" or labels.get("application") != "nexoruta"
            or labels.get("environment") != "demo" or labels.get("managed_by") != "opentofu"):
        raise RuntimeError("Cloud SQL is not the registered OpenTofu-managed demo database")
    return {
        "name": database["name"],
        "state": database.get("state", "UNKNOWN"),
        "availability": database.get("settings", {}).get("availabilityType", "UNKNOWN"),
        "automated_backups": database.get("settings", {}).get("backupConfiguration", {}).get("enabled"),
    }


def backend_health(config):
    raw = demo_session.command(
        "gcloud", "compute", "backend-services", "get-health", API_BACKEND,
        "--global", f"--project={config['GCP_PROJECT_ID']}", "--format=json", capture=True,
    )
    result = json.loads(raw)
    instances = []
    for backend in result:
        for item in backend.get("status", {}).get("healthStatus", []):
            url = item.get("instance", "").rstrip("/").rsplit("/", 1)[-1]
            if url in ("nexoruta-demo", "nexoruta-demo-b"):
                instances.append({"instance": url, "health": item.get("healthState", "UNKNOWN")})
    instances.sort(key=lambda item: item["instance"])
    return instances


def inspect(config):
    nodes = demo_session.node_configs(config)
    vms = [demo_session.instance(node) for node in nodes]
    lease = None
    lease_error = None
    try:
        lease = read_session_lease(config)
    except (RuntimeError, subprocess.CalledProcessError, ValueError, OSError) as error:
        lease_error = type(error).__name__
    now = time.time()
    report = {
        "project": config["GCP_PROJECT_ID"],
        "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "nodes": [instance_summary(config, node, vm) for node, vm in zip(nodes, vms)],
        "session": ({"active": lease["expires_at"] > now,
                     "remaining_seconds": max(0, int(lease["expires_at"] - now))}
                    if lease else {"active": False, "error_type": lease_error}),
        "database": database_summary(config),
        "api_backends": backend_health(config),
    }
    return report


def frontend_address(config):
    raw = demo_session.command(
        "gcloud", "compute", "addresses", "describe", "nexoruta-demo-frontend", "--global",
        f"--project={config['GCP_PROJECT_ID']}", "--format=json", capture=True,
    )
    address = json.loads(raw)
    if address.get("name") != "nexoruta-demo-frontend":
        raise RuntimeError("The public frontend IP is not the registered demo address")
    value = address.get("address", "")
    try:
        parsed = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError:
        raise RuntimeError("The registered demo frontend address is not an IPv4 address") from None
    if parsed.is_private or parsed.is_loopback or parsed.is_unspecified:
        raise RuntimeError("The registered demo frontend address is not public")
    return str(parsed)


def validate_origin(config, origin, expected_address=None, resolver=socket.getaddrinfo):
    origin = api_origin(origin)
    hostname = urllib.parse.urlsplit(origin).hostname
    configured_domain = os.environ.get("GCP_BASE_DOMAIN", "").strip().lower().rstrip(".")
    if configured_domain:
        if hostname != "api." + configured_domain:
            raise ValueError("API origin does not match the configured demo domain")
        if expected_address is not None:
            try:
                resolved = {item[4][0] for item in resolver(hostname, 443, type=socket.SOCK_STREAM)}
            except OSError:
                raise ValueError("Configured API domain did not resolve to the demo frontend IP") from None
            if expected_address not in resolved:
                raise ValueError("Configured API domain did not resolve to the demo frontend IP")
    elif not re.fullmatch(r"api\.(?:[0-9]{1,3}-){3}[0-9]{1,3}\.sslip\.io", hostname):
        raise ValueError("API origin must use the registered demo sslip.io address")
    elif expected_address is not None:
        expected_host = "api." + expected_address.replace(".", "-") + ".sslip.io"
        if hostname != expected_host:
            raise ValueError("API origin does not resolve from the registered demo frontend IP")
    return origin


def strict_inventory(config, expected_release, origin):
    if not re.fullmatch(r"release-[a-f0-9]{32}", expected_release or ""):
        raise ValueError("An exact published release ID is required")
    if not re.fullmatch(r"nexoruta-demo-20261022", config["GCP_PROJECT_ID"]):
        raise ValueError("Fault tests are blocked outside the NexoRuta demo project")
    address = frontend_address(config)
    origin = validate_origin(config, origin, expected_address=address)

    channel = os.environ.get("RELEASE_CHANNEL", "develop")
    if channel not in ("main", "develop"):
        raise ValueError("RELEASE_CHANNEL must be main or develop")
    previous_channel = os.environ.get("RELEASE_CHANNEL")
    os.environ["RELEASE_CHANNEL"] = channel
    try:
        manifest = delivery.latest_manifest(config)
    finally:
        if previous_channel is None:
            os.environ.pop("RELEASE_CHANNEL", None)
        else:
            os.environ["RELEASE_CHANNEL"] = previous_channel
    if manifest["release"] != expected_release:
        raise RuntimeError("Expected release is not the exact currently published channel release")

    session_lease = read_session_lease(config)
    remaining = float(session_lease["expires_at"]) - time.time()
    if remaining < MIN_FAULT_WINDOW_SECONDS:
        raise RuntimeError("At least 90 minutes must remain in the existing bounded VM session")
    nodes = demo_session.node_configs(config)
    vms = [demo_session.instance(node) for node in nodes]
    summaries = []
    releases = []
    for node, vm in zip(nodes, vms):
        if vm is None or vm.get("status") != "RUNNING":
            raise RuntimeError("Both registered demo VMs must be RUNNING before a fault test")
        summary = instance_summary(config, node, vm)
        deadline = demo_session.check_deadline(vm)
        if abs(float(session_lease["expires_at"]) - dt.datetime.fromisoformat(
                deadline.replace("Z", "+00:00")).timestamp()) > 120:
            raise RuntimeError("VM four-hour deadline and shared session lease do not match")
        current = demo_session.gcloud(
            node, "compute", "ssh", node["VM_NAME"], "--tunnel-through-iap",
            "--command=sudo cat /srv/nexoruta/current-release", capture=True,
        ).strip()
        if current != expected_release:
            raise RuntimeError("Both VM release markers must match the exact expected release")
        summaries.append(summary)
        releases.append(current)
    database = database_summary(config)
    if database["state"] != "RUNNABLE":
        raise RuntimeError("Cloud SQL must be RUNNABLE before a fault test")
    health = backend_health(config)
    if sorted((item["instance"] for item in health if item["health"] == "HEALTHY")) != [
            "nexoruta-demo", "nexoruta-demo-b"]:
        raise RuntimeError("Both load-balancer API backends must be healthy before a fault test")
    return {"origin": origin, "manifest": manifest, "lease": session_lease,
            "nodes": nodes, "vms": vms, "node_summaries": summaries,
            "database": database, "api_backends": health, "releases": releases}


def probe(origin):
    started = time.monotonic()
    status = None
    error_type = None
    try:
        request = urllib.request.Request(origin + "/ready", headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=3) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    except Exception as error:
        error_type = type(error).__name__
    return {"at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": status, "error_type": error_type,
            "duration_ms": round((time.monotonic() - started) * 1000)}


def wait_stable(origin, *, since=None, recovery_limit=RECOVERY_SECONDS,
                observation_limit=OBSERVATION_SECONDS, check_lock=None, sleeper=time.sleep,
                clock=time.monotonic, request=probe):
    started = clock()
    deadline = started + observation_limit
    samples = []
    consecutive = 0
    first_success = None
    while clock() < deadline:
        if check_lock:
            check_lock()
        sample = request(origin)
        samples.append(sample)
        if sample["status"] == 200:
            consecutive += 1
            if first_success is None:
                first_success = clock()
        else:
            consecutive = 0
        if consecutive >= STABLE_SUCCESSES:
            recovery_seconds = None if since is None else first_success - since
            if recovery_seconds is not None and recovery_seconds > recovery_limit:
                raise ObservationError("Load-balancer recovery exceeded the 60-second NFR-13 threshold", samples)
            return {"samples": samples,
                    "recovery_seconds": round(recovery_seconds, 3) if recovery_seconds is not None else None,
                    "stable_successes": consecutive}
        sleeper(1)
    raise ObservationError("The load balancer did not produce ten consecutive successful readiness responses", samples)


class ObservationError(RuntimeError):
    def __init__(self, message, samples):
        super().__init__(message)
        self.samples = samples


def wait_backend_transition(config, failed_node, *, timeout=RECOVERY_SECONDS,
                            check_lock=None, clock=time.monotonic, sleeper=time.sleep,
                            read_health=backend_health):
    target = "nexoruta-demo" if failed_node == "a" else "nexoruta-demo-b"
    survivor = "nexoruta-demo-b" if failed_node == "a" else "nexoruta-demo"
    deadline = clock() + timeout
    observations = []
    while clock() < deadline:
        if check_lock:
            check_lock()
        health = read_health(config)
        observations.append(health)
        states = {item["instance"]: item["health"] for item in health}
        if states.get(target) not in (None, "HEALTHY") and states.get(survivor) == "HEALTHY":
            return {"target": target, "target_health": states[target], "survivor": survivor,
                    "survivor_health": states[survivor], "observations": observations}
        sleeper(5)
    raise ObservationError("The load balancer did not mark the faulted backend unhealthy with its peer healthy",
                           observations)


def wait_all_backends_healthy(config, *, timeout=300, check_lock=None,
                              clock=time.monotonic, sleeper=time.sleep, read_health=backend_health):
    deadline = clock() + timeout
    observations = []
    while clock() < deadline:
        if check_lock:
            check_lock()
        health = read_health(config)
        observations.append(health)
        if sorted(item["instance"] for item in health if item["health"] == "HEALTHY") == [
                "nexoruta-demo", "nexoruta-demo-b"]:
            return {"api_backends": health, "observations": observations}
        sleeper(5)
    raise ObservationError("Both registered API backends did not return to healthy state", observations)


def remote_command(node, command):
    return demo_session.gcloud(
        node, "compute", "ssh", node["VM_NAME"], "--tunnel-through-iap",
        "--command=" + command, capture=True,
    )


def api_container_id(node):
    output = remote_command(node,
        "sudo docker ps --filter label=com.docker.compose.project=nexoruta-demo "
        "--filter label=com.docker.compose.service=api --format '{{.ID}}'")
    identifiers = output.split()
    if len(identifiers) != 1 or not re.fullmatch(r"[a-f0-9]{12,64}", identifiers[0]):
        raise RuntimeError("The selected node must have exactly one running demo API container")
    return identifiers[0]


def kill_api(node, identifier):
    identifier = shlex.quote(identifier)
    remote_command(node, "sudo docker update --restart=no " + identifier
                   + " && sudo docker kill --signal KILL " + identifier)


def restore_api(node, release):
    directory = "/srv/nexoruta/releases/" + release
    command = ("sudo docker compose --project-name nexoruta-demo --env-file "
               + shlex.quote(directory + "/.env") + " -f " + shlex.quote(directory + "/compose.yaml")
               + " up -d --no-deps --force-recreate --wait --wait-timeout=300 api")
    remote_command(node, command)


def vm_status(node):
    value = demo_session.instance(node)
    if value is None:
        raise RuntimeError("The registered demo VM disappeared during the fault test")
    instance_summary(node, node, value)
    return value.get("status")


def start_vm(node, timeout=900, *, check_lock=None, clock=time.monotonic, sleeper=time.sleep):
    status = vm_status(node)
    if status == "TERMINATED":
        if check_lock:
            check_lock()
        demo_session.gcloud(node, "compute", "instances", "start", node["VM_NAME"])
    elif status != "RUNNING":
        raise RuntimeError("Cannot restore a VM while Compute reports an in-progress/unknown state")
    deadline = clock() + timeout
    while clock() < deadline:
        if check_lock:
            check_lock()
        if vm_status(node) == "RUNNING":
            return
        sleeper(5)
    raise RuntimeError("The original demo VM did not return to RUNNING within 15 minutes")


def execute_fault(config, *, kind, node_id, expected_release, origin, confirmation):
    if confirmation != "NFR13-FAULT-" + kind.upper() + "-" + node_id.upper():
        raise ValueError("Type the exact --confirm-fault value shown by the fault command")
    with control_lock.control_lock(config) as lease:
        previous_lock = demo_session.ACTIVE_CONTROL_LOCK
        demo_session.ACTIVE_CONTROL_LOCK = lease
        preflight = None
        node = None
        report = None
        fault_started = None
        fault_attempted = False
        fault_observation_error = None
        operation_error = None
        restore_error = None
        try:
            # The shared reservation covers every read and mutation in the scenario.
            preflight = strict_inventory(config, expected_release, origin)
            node = next(item for item in preflight["nodes"] if item["NODE_ID"] == node_id)
            report = {
                "project": config["GCP_PROJECT_ID"], "release": expected_release,
                "channel": preflight["manifest"]["channel"], "scenario": kind,
                "node": node_id, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "baseline": wait_stable(preflight["origin"], check_lock=lease.check),
                "fault_samples": [], "recovery": None, "restored": False,
            }
            lease.check()
            current_lease = read_session_lease(config)
            if current_lease["expires_at"] != preflight["lease"]["expires_at"]:
                raise RuntimeError("The active session lease changed after the NFR-13 reservation")
            for item in preflight["nodes"]:
                current = demo_session.instance(item)
                if not current or current.get("status") != "RUNNING":
                    raise RuntimeError("A demo VM changed state after the NFR-13 reservation")
            lease.check()
            if kind == "api-container":
                identifier = api_container_id(node)
                report["fault_target"] = {"service": "api", "container_id_prefix": identifier[:12]}
                fault_attempted = True
                fault_started = time.monotonic()
                kill_api(node, identifier)
            else:
                report["fault_target"] = {"vm": node["VM_NAME"], "zone": node["GCP_ZONE"]}
                fault_attempted = True
                fault_started = time.monotonic()
                demo_session.gcloud(node, "compute", "instances", "stop", node["VM_NAME"])
            try:
                transition = wait_backend_transition(
                    config, node_id, check_lock=lease.check,
                )
                observation = wait_stable(
                    preflight["origin"], since=fault_started, check_lock=lease.check,
                )
                report["fault_samples"] = observation.pop("samples")
                report["fault_observation"] = observation
                report["backend_transition"] = transition
            except ObservationError as error:
                fault_observation_error = error
                report["fault_samples"] = error.samples if isinstance(error.samples, list) else []
                report["fault_error_type"] = type(error).__name__
            except Exception as error:
                fault_observation_error = error
                report["fault_error_type"] = type(error).__name__
                if isinstance(getattr(error, "samples", None), list):
                    report["fault_samples"] = error.samples
        except BaseException as error:
            operation_error = error
            if report is None:
                raise
            report["fault_error_type"] = type(error).__name__
        finally:
            if fault_attempted:
                # Recovery remains best-effort even if the shared reservation was lost.
                demo_session.ACTIVE_CONTROL_LOCK = None
                try:
                    if kind == "vm":
                        start_vm(node)
                    else:
                        if vm_status(node) == "TERMINATED":
                            start_vm(node)
                        restore_api(node, expected_release)
                    recovered = wait_stable(preflight["origin"], observation_limit=300)
                    healthy = wait_all_backends_healthy(config)
                    report["recovery"] = {
                        "samples": recovered["samples"],
                        "stable_successes": recovered["stable_successes"],
                        "api_backends": healthy["api_backends"],
                    }
                    report["restored"] = True
                except Exception as error:
                    restore_error = error
                    report["restore_error_type"] = type(error).__name__
                finally:
                    demo_session.ACTIVE_CONTROL_LOCK = lease
            demo_session.ACTIVE_CONTROL_LOCK = previous_lock
        if restore_error:
            manual = recovery_command(config, node, kind, expected_release)
            report["manual_recovery"] = manual
            report["status"] = "failed_restore"
        elif fault_observation_error or operation_error:
            report["status"] = "failed_acceptance"
        else:
            report["status"] = "passed"
        report["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        report["session_remaining_seconds"] = max(0, int(
            preflight["lease"]["expires_at"] - time.time()))
        return report


def recovery_command(config, node, kind, release):
    if kind == "vm":
        return (f"gcloud compute instances start {node['VM_NAME']} --project={config['GCP_PROJECT_ID']} "
                f"--zone={node['GCP_ZONE']} --quiet")
    directory = "/srv/nexoruta/releases/" + release
    return (f"gcloud compute ssh {node['VM_NAME']} --project={config['GCP_PROJECT_ID']} "
            f"--zone={node['GCP_ZONE']} --tunnel-through-iap --command="
            + shlex.quote("sudo docker compose --project-name nexoruta-demo --env-file "
                          + shlex.quote(directory + "/.env") + " -f "
                          + shlex.quote(directory + "/compose.yaml")
                          + " up -d --no-deps --force-recreate --wait --wait-timeout=300 api"))


def write_report(report, path):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--project", default=None)
    root.add_argument("--state-bucket", default=None)
    root.add_argument("--zone-a", default=None)
    root.add_argument("--zone-b", default=None)
    commands = root.add_subparsers(dest="command")
    read = commands.add_parser("inspect", help="Read the registered demo inventory and current health")
    read.add_argument("--output", help="Write the sanitized read-only report to a local JSON file")
    for kind in ("api-container", "vm"):
        fault = commands.add_parser(kind, help="Run one controlled failover scenario and restore its target")
        fault.add_argument("--node", choices=("a", "b"), required=True)
        fault.add_argument("--release", required=True)
        fault.add_argument("--api-origin", required=True)
        fault.add_argument("--confirm-fault", required=True)
        fault.add_argument("--output", help="Write the sanitized scenario report to a local JSON file")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    config = configuration(args.project, args.state_bucket, args.zone_a, args.zone_b)
    if args.command in (None, "inspect"):
        report = inspect(config)
    else:
        report = execute_fault(
            config, kind=args.command, node_id=args.node,
            expected_release=args.release, origin=args.api_origin,
            confirmation=args.confirm_fault,
        )
    if getattr(args, "output", None):
        write_report(report, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    if report.get("status") not in (None, "passed"):
        return 1
    return report


if __name__ == "__main__":
    try:
        result = main()
        if result == 1:
            raise SystemExit(1)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"NFR-13 verification failed: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from None
