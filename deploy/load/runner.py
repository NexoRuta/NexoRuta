"""Run bounded k6 traffic with lease checks and private GCS checkpoints."""

import json
import hashlib
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from supervision import MetricStream, Resources, classify


PROFILES = {"smoke": ("2m", 1), "baseline": ("15m", 5), "sync": ("15m", 20),
            "stress": ("25m", 50), "soak": ("60m", 5)}
ROOT = Path(__file__).resolve().parent
EXIT_SIGNAL = None


def metadata(path):
    request = urllib.request.Request(
        "http://metadata.google.internal/computeMetadata/v1/" + path,
        headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def access_token():
    return metadata("instance/service-accounts/default/token")["access_token"]


def object_url(bucket, name):
    return ("https://storage.googleapis.com/storage/v1/b/" + urllib.parse.quote(bucket, safe="")
            + "/o/" + urllib.parse.quote(name, safe=""))


def read_object(bucket, name, max_bytes):
    request = urllib.request.Request(object_url(bucket, name) + "?alt=media",
        headers={"Authorization": "Bearer " + access_token()})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("A private load-test object exceeds its reviewed size limit")
    return data


def read_json(bucket, name, max_bytes=1_048_576):
    return json.loads(read_object(bucket, name, max_bytes))


def upload(bucket, name, data):
    url = "https://storage.googleapis.com/upload/storage/v1/b/" + urllib.parse.quote(bucket, safe="")
    query = urllib.parse.urlencode({"uploadType": "media", "name": name, "ifGenerationMatch": "0"})
    request = urllib.request.Request(url + "/o?" + query, method="POST", data=data,
        headers={"Authorization": "Bearer " + access_token(), "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def check_endpoint(url, timeout=15):
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError("A required remote health endpoint is not ready")


def request_stop(signum, _frame):
    global EXIT_SIGNAL
    EXIT_SIGNAL = signum


def load_thresholds(profile_name, profile, defaults):
    thresholds = dict(defaults)
    if profile.get("sync"):
        batches = profile["vus"]
        operations = batches * 50
        thresholds["nexoruta_load_sync_batches_completed"] = [f"count>={batches}"]
        thresholds["nexoruta_load_sync_operations_applied"] = [f"count>={operations}"]
        thresholds["nexoruta_load_sync_drain_duration"] = ["p(95)<60000", "p(99)<120000"]
    return thresholds


def run_process(args, env, output, result, lease, control_bucket, bucket, prom_origin):
    stream = MetricStream(output / "metrics.pipe")
    resources = Resources()
    resources.sample()
    args = [*args[:-1], "-o", f"json={output / 'metrics.pipe'}", args[-1]]
    stream.start()
    process = None
    stop_reason = None
    started = last_checkpoint = last_lease_check = last_prom_check = time.time()
    checkpoint = 0
    try:
        with (output / "k6.log").open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(args, env=env, stdout=log_file, stderr=subprocess.STDOUT)
            while process.poll() is None:
                now = time.time()
                evidence = stream.evidence.snapshot()
                resource_sample = resources.sample()
                if EXIT_SIGNAL:
                    stop_reason = "cloud_run_signal"
                elif now >= lease.get("expires_at", 0):
                    stop_reason = "lease_expired"
                elif evidence["stream_error"]:
                    stop_reason = "metric_stream_unavailable"
                elif resource_sample.get("oom"):
                    stop_reason = "generator_oom"
                elif resource_sample.get("saturated"):
                    stop_reason = "generator_saturated"
                elif not resource_sample["available"] and now - started > 30:
                    stop_reason = "generator_telemetry_unavailable"
                elif (shutil.disk_usage(output).free < 64 * 1024 * 1024
                      or (output / "k6.log").stat().st_size > 16 * 1024 * 1024):
                    stop_reason = "local_storage_exhausted"
                elif evidence["severe_errors"]:
                    stop_reason = "sustained_http_errors"
                elif evidence["last_measured_at"] and now - evidence["last_measured_at"] > 20:
                    stop_reason = "metric_stream_unavailable"
                if not stop_reason and now - last_lease_check >= 5:
                    last_lease_check = now
                    try:
                        lease = read_json(control_bucket, "leases/load-test.json")
                        if (lease.get("run_id") != result["run_id"]
                                or lease.get("status") not in ("starting", "running")
                                or lease.get("expires_at", 0) <= now):
                            stop_reason = "lease_cancelled_or_expired"
                    except (OSError, urllib.error.URLError, ValueError):
                        stop_reason = "lease_unavailable"
                if not stop_reason and now - last_prom_check >= 15:
                    last_prom_check = now
                    try:
                        check_endpoint(prom_origin + "/-/ready", timeout=5)
                    except (OSError, urllib.error.URLError, RuntimeError):
                        stop_reason = "prometheus_unavailable"
                if stop_reason:
                    process.send_signal(signal.SIGINT)
                    break
                if now - last_checkpoint >= 30:
                    checkpoint += 1
                    progress = {**result, "checkpoint": checkpoint, "observed_at": now,
                                "elapsed_seconds": round(now - started, 3),
                                "evidence": evidence, "generator": resource_sample}
                    try:
                        upload(bucket, f"runs/{result['run_id']}/progress/{checkpoint:04d}.json",
                               json.dumps(progress).encode())
                    except (OSError, urllib.error.URLError):
                        stop_reason = "report_export_unavailable"
                        process.send_signal(signal.SIGINT)
                        break
                    last_checkpoint = now
                time.sleep(1)
            try:
                exit_code = process.wait(timeout=7 if stop_reason or EXIT_SIGNAL else 15)
            except subprocess.TimeoutExpired:
                process.kill()
                exit_code = process.wait()
    finally:
        # Any unexpected control/export failure must also stop the traffic.
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        stream.close()
    return exit_code, stop_reason, stream.evidence.snapshot(), resources.latest


def main():
    profile_name = os.environ.get("NEXORUTA_LOAD_PROFILE_NAME", "")
    run_id = os.environ.get("NEXORUTA_RUN_ID", "")
    bucket = os.environ.get("NEXORUTA_RESULTS_BUCKET", "")
    control_bucket = os.environ.get("NEXORUTA_LOAD_CONTROL_BUCKET", "")
    fixtures_bucket = os.environ.get("NEXORUTA_LOAD_FIXTURES_BUCKET", "")
    fixture_version = os.environ.get("NEXORUTA_LOAD_FIXTURE_VERSION", "")
    if (profile_name not in PROFILES or not re.fullmatch(r"[a-f0-9-]{36}", run_id)
            or not re.fullmatch(r"[a-z0-9._-]{3,222}", bucket)
            or not re.fullmatch(r"[a-z0-9._-]{3,222}", control_bucket)
            or not re.fullmatch(r"[a-z0-9._-]{3,222}", fixtures_bucket)
            or not re.fullmatch(r"[1-9][0-9]*", fixture_version)):
        raise ValueError("Invalid load-test execution configuration")
    fixture = os.environ.get("NEXORUTA_LOAD_FIXTURE", "")
    if not fixture or len(fixture.encode("utf-8")) > 64 * 1024:
        raise ValueError("The bounded synthetic fixture secret is required")
    fixture_data = json.loads(fixture)
    if not isinstance(fixture_data, dict) or not isinstance(fixture_data.get("accounts"), list):
        raise ValueError("The synthetic fixture must contain a bounded account list")
    profile = json.loads((ROOT / "profiles.json").read_text(encoding="utf-8"))
    selected = profile["profiles"][profile_name]
    max_duration, max_vus = PROFILES[profile_name]
    if selected["duration"] != max_duration or selected["vus"] > max_vus:
        raise ValueError("The selected profile exceeds its reviewed execution limits")
    selected_sync = selected.get("sync") is True
    operations_sha256 = None
    operations_object = None
    if selected_sync:
        operations_object = fixture_data.get("operationsObject", "")
        operations_sha256 = fixture_data.get("operationsSha256", "")
        if (not re.fullmatch(r"fixtures/[A-Za-z0-9._-]{1,120}/operations.json", operations_object)
                or not re.fullmatch(r"[a-f0-9]{64}", operations_sha256)):
            raise ValueError("A pinned synthetic sync dataset is required for this profile")
    manifest = read_json(control_bucket, f"runs/{run_id}/manifest.json")
    lease = read_json(control_bucket, "leases/load-test.json")
    if (manifest.get("run_id") != run_id or manifest.get("profile") != profile_name
            or manifest.get("fixture_version") != fixture_version
            or lease.get("run_id") != run_id or lease.get("status") not in ("starting", "running")
            or lease.get("expires_at", 0) <= time.time()):
        raise RuntimeError("The load-test reservation was cancelled, expired, or does not match")
    operations_path = None
    if selected_sync:
        operations_data = read_object(fixtures_bucket, operations_object, 4 * 1024 * 1024)
        if hashlib.sha256(operations_data).hexdigest() != operations_sha256:
            raise ValueError("The synthetic sync dataset hash does not match the secret fixture")
        operations_path = Path("/tmp/nexoruta-load-operations.json")
        operations_path.write_bytes(operations_data)
        operations_path.chmod(0o600)
    api_origin = os.environ.get("NEXORUTA_API_ORIGIN", "").rstrip("/")
    if api_origin != manifest.get("api_origin") or not re.fullmatch(r"https://[a-z0-9.-]+", api_origin):
        raise ValueError("The configured HTTPS origin does not match the verified application release")
    prom_write = os.environ.get("NEXORUTA_PROMETHEUS_WRITE_URL", "")
    if not re.fullmatch(r"http://10(?:\.\d{1,3}){3}:9091/api/v1/write", prom_write):
        raise ValueError("The private write-only Prometheus gateway is required")
    os.environ["NEXORUTA_LOAD_FIXTURE"] = json.dumps(fixture_data)
    if operations_path:
        os.environ["NEXORUTA_LOAD_OPERATIONS_FILE"] = str(operations_path)
    # These are local, bounded probes from the isolated VPC before any user traffic.
    check_endpoint(api_origin + "/health/ready")
    prom_origin = prom_write.removesuffix("/api/v1/write")
    check_endpoint(prom_origin + "/-/ready")

    output = Path("/tmp/nexoruta-load")
    output.mkdir(mode=0o700)
    report = output / "summary.json"
    started = time.time()
    result = {"run_id": run_id, "profile": profile_name, "release": manifest["release"],
              "fixture_version": fixture_version, "suite_sha256": manifest["suite_sha256"],
              "status": "running", "started_at": started}
    if operations_sha256:
        result["operations_sha256"] = operations_sha256
    upload(bucket, f"runs/{run_id}/progress.json", json.dumps(result).encode())

    env = {**os.environ, "NEXORUTA_LOAD_PROFILE": json.dumps(selected),
           "NEXORUTA_LOAD_THRESHOLDS": json.dumps(load_thresholds(profile_name, selected, profile["thresholds"])),
           "K6_PROMETHEUS_RW_SERVER_URL": prom_write,
           "K6_PROMETHEUS_RW_PUSH_INTERVAL": "5s",
           "K6_PROMETHEUS_RW_STALE_MARKERS": "true",
           "K6_PROMETHEUS_RW_TREND_STATS": "p(95),p(99),avg",
           "K6_PROMETHEUS_RW_LABELS": f"run_id={run_id},profile={profile_name}"}
    args = ["k6", "run", "-o", "experimental-prometheus-rw", "--summary-export", str(report),
            str(ROOT / "scenario.js")]
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    exit_code, stop_reason, evidence, generator = run_process(
        args, env, output, result, lease, control_bucket, bucket, prom_origin)
    if EXIT_SIGNAL and not stop_reason:
        stop_reason = "cloud_run_signal"
    ended = time.time()
    data = None
    if report.exists() and report.stat().st_size <= 4 * 1024 * 1024:
        try:
            candidate = json.loads(report.read_text(encoding="utf-8"))
            if isinstance(candidate, dict) and isinstance(candidate.get("metrics"), dict) and candidate["metrics"]:
                data = candidate
        except (OSError, ValueError):
            pass  # An invalid or incomplete summary is never passing evidence.
    status, classification = classify(profile_name, exit_code, stop_reason, evidence, generator, data is not None)
    result.update(status=status, classification=classification, evidence=evidence, generator=generator,
                  stop_reason=stop_reason, ended_at=ended,
                  duration_seconds=round(ended - started, 3), exit_code=exit_code)
    if data is not None:
        result["metrics"] = data.get("metrics", {})
        upload(bucket, f"runs/{run_id}/k6-summary.json", json.dumps(data).encode())
    upload(bucket, f"runs/{run_id}/summary.json", json.dumps(result).encode())
    if result["status"] != "passed":
        raise SystemExit(exit_code or 1)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, urllib.error.URLError) as error:
        print(f"Load test failed safely: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1) from error
