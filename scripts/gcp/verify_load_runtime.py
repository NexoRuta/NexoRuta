"""Run the production k6 runner against isolated, controlled CI dependencies."""

import argparse
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time
import uuid

import load_image


ROOT = Path(__file__).resolve().parents[2]
PROMETHEUS_IMAGE = "prom/prometheus:v3.15.1"
RUN_TIMEOUT = 360


def invoke(args, timeout=60, check=True):
    result = subprocess.run(args, check=False, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        detail = (result.stderr or result.stdout)[-12000:]
        raise RuntimeError(f"{args[0]} command failed ({result.returncode}):\n{detail}")
    return result


def python_image(root=ROOT):
    dockerfile = (root / "tests/load/Dockerfile").read_text(encoding="utf-8")
    images = re.findall(r"(?m)^FROM\s+(python:[^\s]+)\s*$", dockerfile)
    if len(images) != 1 or not re.fullmatch(r"python:[A-Za-z0-9._-]+@sha256:[a-f0-9]{64}", images[0]):
        raise ValueError("The pinned Python base image for the controlled gateway is missing")
    return images[0]


def wait_container_ready(name, path, timeout=60):
    deadline = time.monotonic() + timeout
    probe = ("import urllib.request; response = urllib.request.urlopen(" 
             f"'http://127.0.0.1:9091{path}', timeout=1); "
             "raise SystemExit(0 if response.status == 200 else 1)")
    while time.monotonic() < deadline:
        result = invoke(["docker", "exec", name, "python3", "-c", probe], timeout=3, check=False)
        if result.returncode == 0:
            return
        state = invoke(["docker", "inspect", "--format={{.State.Status}}", name], check=False).stdout.strip()
        if state == "exited":
            logs = invoke(["docker", "logs", "--tail", "40", name], check=False).stdout[-4000:]
            raise RuntimeError(f"A controlled service exited before readiness:\n{logs}")
        time.sleep(1)
    raise RuntimeError("A controlled CI dependency did not become ready before its deadline")


def create_network(name):
    # Docker rejects overlapping pools. Select a fresh private /29 instead of
    # assuming a developer or hosted runner has an unused fixed subnet.
    for _ in range(32):
        subnet = f"10.{secrets.randbelow(240) + 10}.{secrets.randbelow(256)}.{secrets.randbelow(32) * 8}/29"
        result = invoke(["docker", "network", "create", "--internal", "--subnet", subnet, name], check=False)
        if result.returncode == 0:
            return subnet
        if "overlap" not in (result.stderr + result.stdout).lower():
            raise RuntimeError("Docker could not create the isolated controlled-test network")
    raise RuntimeError("Docker has no available private subnet for the controlled-test network")


def start(name, image, options=(), command=()):
    result = invoke(["docker", "run", "--detach", "--name", name, *options, image, *command])
    identifier = result.stdout.strip()
    if not re.fullmatch(r"[a-f0-9]{12,64}", identifier):
        raise RuntimeError("Docker returned an invalid controlled-test container identifier")
    return identifier


def sanitize_diagnostic(value):
    value = re.sub(r"load-\d+@nexoruta\.test|controlled-only-password|fixture-access-\d+", "[redacted]", value)
    value = re.sub(r"[A-Za-z0-9_-]{32,}", "[redacted]", value)
    return re.sub(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", "[redacted]", value, flags=re.I)


def verify(evidence_path=None, root=ROOT):
    docker = invoke(["docker", "version", "--format", "{{.Server.Version}}"], timeout=15).stdout.strip()
    if not docker:
        raise RuntimeError("Docker Engine is not available")

    suffix = uuid.uuid4().hex[:12]
    prefix = f"nexoruta-load-ci-{suffix}"
    image = f"nexoruta-load-ci:{suffix}"
    network = f"{prefix}-net"
    prometheus, gateway, runner = (f"{prefix}-{role}" for role in ("prom", "gateway", "runner"))
    names = (prometheus, gateway, runner)
    created_network = False
    evidence = None
    with tempfile.TemporaryDirectory(prefix="nexoruta-load-runtime-") as temporary:
        work = Path(temporary)
        context = work / "context"
        context.mkdir()
        load_image.stage_sources(root, context)
        controlled = work / "controlled"
        controlled.mkdir(mode=0o755)
        controlled.chmod(0o755)
        controlled_results = work / "controlled-results"
        controlled_results.mkdir(mode=0o755)
        # work is private to this process (mode 0700); allow the production
        # runner uid to write evidence while preserving host cleanup access.
        controlled_results.chmod(0o777)
        (controlled / "load_runtime.py").write_bytes((root / "scripts/gcp/fixtures/load_runtime.py").read_bytes())
        gateway_source = root / "deploy/gcp/monitoring/prometheus-write-gateway.py"
        config = work / "prometheus.yml"
        config.write_text("global:\n  scrape_interval: 1s\nscrape_configs: []\n", encoding="utf-8")
        cert = controlled / "ca.pem"
        key = controlled / "key.pem"
        invoke(["openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048", "-keyout", str(key),
                "-out", str(cert), "-days", "1", "-subj", "/CN=controlled.invalid",
                "-addext", "subjectAltName=DNS:controlled.invalid"], timeout=30)
        key.chmod(0o600)
        cert.chmod(0o644)

        try:
            invoke(["docker", "build", "--file",
                str(context / "tests/load/Dockerfile"), "--tag", image, str(context)], timeout=300)
            inspected_user = invoke(["docker", "image", "inspect", "--format={{.Config.User}}", image]).stdout.strip()
            if inspected_user != "10001:10001":
                raise RuntimeError("The production runner image does not default to its restricted uid/gid")
            base = python_image(root)
            invoke(["docker", "pull", PROMETHEUS_IMAGE], timeout=180)
            subnet = create_network(network)
            created_network = True
            network_octets = subnet.split("/", 1)[0].split(".")
            prefix = ".".join(network_octets[:3])
            network_host = int(network_octets[3])
            prom_ip, gateway_ip, runner_ip = (f"{prefix}.{network_host + offset}" for offset in (2, 3, 4))

            start(prometheus, PROMETHEUS_IMAGE,
                ("--network", network, "--ip", prom_ip, "--network-alias", "prometheus",
                 "--user", "0:0",
                 "--mount", f"type=bind,src={config},dst=/etc/prometheus/prometheus.yml,readonly",
                 "--entrypoint", "/bin/prometheus"),
                ("--config.file=/etc/prometheus/prometheus.yml", "--storage.tsdb.path=/prometheus",
                 "--web.enable-remote-write-receiver", "--log.level=warn"))
            start(gateway, base,
                ("--network", network, "--ip", gateway_ip, "--network-alias", "gateway",
                 "--read-only", "--tmpfs", "/tmp:size=8m",
                 "--user", "10001:10001",
                 "--mount", f"type=bind,src={gateway_source},dst=/opt/prometheus-write-gateway.py,readonly",
                 "--entrypoint", "python3"),
                ("/opt/prometheus-write-gateway.py",))
            wait_container_ready(gateway, "/-/ready")

            start(runner, image,
                ("--network", network, "--ip", runner_ip,
                 "--add-host", "controlled.invalid:127.0.0.1", "--cpus=2", "--memory=2g",
                 "--pids-limit=256", "--user", "0:0", "--cap-drop=ALL",
                 "--cap-add=SETGID", "--cap-add=SETUID", "--cap-add=NET_BIND_SERVICE",
                 "--cap-add=DAC_OVERRIDE",
                 "--read-only", "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m",
                 "--mount", f"type=bind,src={controlled},dst=/controlled,readonly",
                 "--mount", f"type=bind,src={controlled_results},dst=/tmp/controlled-results",
                 "--env", "CONTROLLED_PROMETHEUS_ORIGIN=http://prometheus:9090",
                 "--env", f"NEXORUTA_PROMETHEUS_WRITE_URL=http://{gateway_ip}:9091/api/v1/write",
                 "--entrypoint", "python3"),
                ("/controlled/load_runtime.py",))
            exit_code = invoke(["docker", "wait", runner], timeout=RUN_TIMEOUT).stdout.strip()
            if not re.fullmatch(r"[0-9]{1,3}", exit_code):
                raise RuntimeError("Docker returned an invalid controlled-runner exit code")
            verification = controlled_results / "verification.json"
            if verification.is_file():
                evidence = json.loads(verification.read_text(encoding="utf-8"))
            else:
                summaries = list((controlled_results / "runs").glob("*/summary.json"))
                if summaries:
                    summary = json.loads(summaries[0].read_text(encoding="utf-8"))
                    evidence = {"context": "controlled-no-cloud", "status": "failed",
                        "failure_type": "verification_evidence_missing",
                        "runner_classification": summary.get("classification"),
                        "runner_authentication": summary.get("authentication"),
                        "runner_measurement": summary.get("evidence", {}).get("measurement_report")}
            if evidence_path and evidence is not None:
                path = Path(evidence_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
            if exit_code != "0" or not evidence or evidence.get("status") != "passed":
                failure = evidence.get("failure_type", "missing controlled-runner evidence") if evidence else "missing controlled-runner evidence"
                logs = invoke(["docker", "logs", "--tail", "100", runner], check=False)
                diagnostic = sanitize_diagnostic(logs.stdout + logs.stderr)[-10000:]
                raise RuntimeError(f"The production runner did not pass its controlled smoke ({failure})\n"
                    f"{json.dumps(evidence or {}, sort_keys=True)}\n{diagnostic}")
        finally:
            for name in names:
                invoke(["docker", "rm", "--force", name], timeout=20, check=False)
            if created_network:
                invoke(["docker", "network", "rm", network], timeout=20, check=False)
            invoke(["docker", "image", "rm", "--force", image], timeout=30, check=False)

    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", help="Write the sanitized verification result to this path")
    args = parser.parse_args()
    try:
        result = verify(args.evidence)
        print(json.dumps(result, indent=2))
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(f"Controlled load runner verification failed: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
