"""Controlled HTTPS peer and GCS doubles for the real, isolated runner image.

This file is mounted only by the CI verifier; it is not copied into the image.
"""

from collections import deque
import datetime as dt
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import ssl
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid

sys.path.insert(0, "/suite")
import runner


ORIGIN = "https://controlled.invalid"
OUTPUT = Path("/tmp/controlled-results")
JOURNEY = str(uuid.UUID(int=1))
RUN_ID = str(uuid.uuid4())
PASSWORD = "controlled-only-password"
OPERATIONS = [{"id": str(uuid.UUID(int=100 + index)), "secuencia": index + 1,
    "tipo": "Posicion", "envioId": None, "versionEnvio": None,
    "ocurridaEn": "2026-11-04T00:00:00Z", "datos": {"latitud": -34.9, "longitud": -56.1,
        "precisionMetros": 12, "posicionEnUtc": "2026-11-04T00:00:00Z"}}
    for index in range(50)]
DATASET = json.dumps({JOURNEY: OPERATIONS}).encode()
STARTED_AT = time.monotonic()


class Peer:
    def __init__(self):
        self.lock = threading.Lock()
        self.login_window, self.refresh_window = deque(), deque()
        self.refresh = None
        self.access = {}
        self.session_id = str(uuid.uuid4())
        self.serial = self.replays = self.rate_rejections = 0
        self.login_at_seconds = []
        self.used_access = set()
        self.measured_access = set()

    def allowed(self, action):
        window, limit = (self.login_window, 5) if action == "login" else (self.refresh_window, 30)
        now = time.time()
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= limit:
            self.rate_rejections += 1
            return False
        window.append(now)
        return True

    def issue(self):
        self.serial += 1
        token = f"fixture-access-{self.serial}"
        self.refresh = "r" + str(self.serial).zfill(42)
        # Accelerate rotation without changing any production runner timers.
        expiry = time.time() + 183
        self.access[token] = expiry
        iso = lambda value: dt.datetime.fromtimestamp(value, dt.timezone.utc).isoformat()
        return {"accessToken": token, "refreshToken": self.refresh, "sesionId": self.session_id,
                "expiresAtUtc": iso(expiry), "refreshExpiresAtUtc": iso(time.time() + 86400)}

    def authenticate(self, header):
        token = header.removeprefix("Bearer ")
        if self.access.get(token, 0) <= time.time():
            return False
        self.used_access.add(token)
        return True


PEER = Peer()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        pass

    def respond(self, status, value=None):
        data = json.dumps(value or {}).encode() if status != 204 else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health/ready":
            self.respond(200)
            return
        with PEER.lock:
            allowed = self.path == "/api/mobile/perfil" and PEER.authenticate(self.headers.get("Authorization", ""))
            if allowed and PEER.replays == 50:
                PEER.measured_access.add(self.headers.get("Authorization", "").removeprefix("Bearer "))
        if not allowed:
            self.respond(403)
            return
        time.sleep(0.05)
        self.respond(200, {"fixture": True})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 <= length <= 32768:
            self.respond(413)
            return
        body = json.loads(self.rfile.read(length))
        with PEER.lock:
            if self.path.startswith("/api/auth/mobile/"):
                action = self.path.rsplit("/", 1)[-1]
                if action not in ("login", "refresh", "logout"):
                    self.respond(404)
                elif not PEER.allowed(action):
                    self.respond(429)
                elif action == "login":
                    PEER.login_at_seconds.append(round(time.monotonic() - STARTED_AT, 3))
                    if body != {"email": "load-01@nexoruta.test", "password": PASSWORD}:
                        self.respond(401)
                    else:
                        self.respond(200, PEER.issue())
                elif body.get("refreshToken") != PEER.refresh:
                    self.respond(401)
                elif action == "refresh":
                    self.respond(200, PEER.issue())
                else:
                    PEER.refresh = None
                    PEER.access.clear()
                    self.respond(204)
                return
            if (self.path != f"/api/mobile/jornadas/{JOURNEY}/operaciones"
                    or not PEER.authenticate(self.headers.get("Authorization", ""))):
                self.respond(403)
                return
            index = body.get("secuencia", 0) - 1
            if not 0 <= index < 50 or body != OPERATIONS[index]:
                self.respond(200, {"resultado": "Conflicto"})
                return
            PEER.replays += 1
        self.respond(200, {"resultado": "Aplicada"})


def upload(bucket, name, data):
    if bucket != "synthetic-results":
        raise ValueError("Controlled results bucket expected")
    target = OUTPUT / name
    if not target.resolve().is_relative_to(OUTPUT.resolve()):
        raise ValueError("Invalid controlled result path")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(data)


def verify_prometheus(origin):
    query = urllib.parse.urlencode({"match[]": '{run_id="' + RUN_ID + '"}'})
    with urllib.request.urlopen(origin + "/api/v1/series?" + query, timeout=10) as response:
        series = json.load(response)["data"]
    if not series or any("url" in labels for labels in series):
        raise RuntimeError("Remote write series are missing or have unbounded URL labels")
    for labels in series:
        for value in labels.values():
            if PASSWORD in value or "fixture-access-" in value or "@nexoruta.test" in value or JOURNEY in value:
                raise RuntimeError("Private fixture information was exported as a label")
    names = sorted({labels["__name__"] for labels in series})
    for marker in ("k6_nexoruta_load_window_started", "k6_nexoruta_load_window_finished"):
        if marker not in names:
            raise RuntimeError(f"Remote write did not publish Grafana run annotation {marker}")
    client_latency = next((name for name in names
        if name == "k6_http_req_duration_p95"), None)
    if not client_latency:
        raise RuntimeError("Remote write did not publish client latency percentiles")
    observed = {}
    checks = ((client_latency, 'phase="measured",kind="read"', 0.025, 2.0),
              ("k6_nexoruta_load_sync_drain_duration_p95", 'phase="measured"', 1, 60000),
              ("k6_nexoruta_load_generator_cpu_utilization", 'phase="control",kind="generator"', 0, 1.05),
              ("k6_nexoruta_load_generator_memory_utilization", 'phase="control",kind="generator"', 0, 1))
    for name, selectors, lower, upper in checks:
        if name not in names:
            raise RuntimeError(f"Remote write did not publish required measurement {name}")
        promql = f'last_over_time({name}{{run_id="{RUN_ID}",{selectors}}}[5m])'
        query = urllib.parse.urlencode({"query": promql})
        with urllib.request.urlopen(origin + "/api/v1/query?" + query, timeout=10) as response:
            values = json.load(response)["data"]["result"]
        numbers = [float(value["value"][1]) for value in values]
        if not numbers or any(not math.isfinite(value) or not lower <= value <= upper for value in numbers):
            raise RuntimeError(f"Remote write has no valid measured value and unit for {name}")
        observed[name] = max(numbers)
    return {"metric_names": names, "measured_and_generator_values": observed,
            "units": {client_latency: "seconds", checks[1][0]: "milliseconds",
                checks[2][0]: "ratio", checks[3][0]: "ratio"}}


def main():
    OUTPUT.mkdir(mode=0o755, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 443), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("/controlled/ca.pem", "/controlled/key.pem")
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Only binding the controlled peer's TLS port needs root. Run the actual
    # suite and its broker with the image's production uid/gid afterwards.
    os.chown(OUTPUT, 10001, 10001)
    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)
    prom = os.environ["CONTROLLED_PROMETHEUS_ORIGIN"]
    write_url = os.environ.get("NEXORUTA_PROMETHEUS_WRITE_URL", "")
    if not re.fullmatch(r"http://10(?:\.\d{1,3}){3}:9091/api/v1/write", write_url):
        raise RuntimeError("Controlled remote-write gateway address is invalid")
    suite_hash = hashlib.sha256()
    for name in ("Dockerfile", "profiles.json", "scenario.js", "runner.py", "supervision.py", "sessions.py"):
        suite_hash.update((Path("/suite") / name).read_bytes())
    configuration = json.loads(Path("/suite/profiles.json").read_text())
    manifest = {"run_id": RUN_ID, "profile": "smoke", "fixture_version": "1", "release": "controlled-fixture",
                "api_origin": ORIGIN, "suite_sha256": suite_hash.hexdigest(), "thresholds_version": configuration["version"]}
    lease = {"run_id": RUN_ID, "status": "running", "expires_at": time.time() + 600}
    fixture = {"readPath": "/api/mobile/perfil", "operationsObject": "fixtures/runtime-v1/operations.json",
               "operationsSha256": hashlib.sha256(DATASET).hexdigest(), "accounts": [
                   {"email": "load-01@nexoruta.test", "password": PASSWORD, "jornadaId": JOURNEY}]}
    os.environ.update(NEXORUTA_LOAD_PROFILE_NAME="smoke", NEXORUTA_RUN_ID=RUN_ID,
        NEXORUTA_RESULTS_BUCKET="synthetic-results", NEXORUTA_LOAD_CONTROL_BUCKET="synthetic-control",
        NEXORUTA_LOAD_FIXTURES_BUCKET="synthetic-fixtures", NEXORUTA_LOAD_FIXTURE_VERSION="1",
        NEXORUTA_LOAD_FIXTURE=json.dumps(fixture), NEXORUTA_API_ORIGIN=ORIGIN,
        NEXORUTA_PROMETHEUS_WRITE_URL=write_url, NO_PROXY="*", SSL_CERT_FILE="/controlled/ca.pem")

    def read_json(bucket, name, max_bytes=1048576):
        if bucket == "synthetic-control" and name == f"runs/{RUN_ID}/manifest.json":
            return dict(manifest)
        if bucket == "synthetic-control" and name == "leases/load-test.json":
            return dict(lease)
        raise RuntimeError("Unexpected cloud access from the controlled fixture")

    def read_object(bucket, name, max_bytes):
        if bucket != "synthetic-fixtures" or name != fixture["operationsObject"] or len(DATASET) > max_bytes:
            raise RuntimeError("Unexpected fixture object access")
        return DATASET

    runner.read_json, runner.read_object, runner.upload = read_json, read_object, upload
    evidence = {"context": "controlled-no-cloud", "run_id": RUN_ID, "status": "running"}
    try:
        runner.main()
        result = json.loads((OUTPUT / f"runs/{RUN_ID}/summary.json").read_text())
        if result["status"] != "passed" or not result["evidence"]["measurement_report"]["complete"]:
            raise RuntimeError("The actual runner did not produce a complete passing smoke")
        if PEER.replays != 50 or PEER.rate_rejections or len(PEER.measured_access) < 2:
            raise RuntimeError("Controlled replay, quota or access-token rotation was not verified")
        if not result["session_cleanup"]["complete"] or PEER.refresh is not None:
            raise RuntimeError("Controlled mobile session was not revoked")
        evidence.update(status="passed", suite_sha256=manifest["suite_sha256"], replays=PEER.replays,
            measured_access_tokens=len(PEER.measured_access), authentication=result["authentication"],
            prometheus=verify_prometheus(prom))
    except BaseException as error:
        evidence.update(status="failed", failure_type=type(error).__name__)
        evidence["fixture_authentication"] = {"login_attempts": len(PEER.login_window),
            "refresh_attempts": len(PEER.refresh_window), "issued_tokens": PEER.serial,
            "login_at_seconds": PEER.login_at_seconds,
            "rate_rejections": PEER.rate_rejections, "replays": PEER.replays,
            "measured_access_tokens": len(PEER.measured_access)}
        try:
            summary = json.loads((OUTPUT / f"runs/{RUN_ID}/summary.json").read_text())
            evidence["runner_authentication"] = summary.get("authentication")
            evidence["runner_classification"] = summary.get("classification")
            evidence["runner_stop_reason"] = summary.get("stop_reason")
            evidence["runner_measured_requests"] = summary.get("evidence", {}).get("measured_requests")
        except (OSError, ValueError):
            pass
        # This peer issues only generated test tokens. Never copy the raw log;
        # print a bounded, redacted diagnostic if k6 fails before its summary.
        log = Path("/tmp/nexoruta-load/k6.log")
        if log.exists():
            tail = log.read_text(errors="replace")[-8000:]
            tail = re.sub(r"[A-Za-z0-9_-]{32,}|fixture-access-[0-9]+|controlled-only-password|load-01@nexoruta\.test",
                          "[redacted]", tail)
            print(tail, file=sys.stderr)
        raise
    finally:
        (OUTPUT / "verification.json").write_text(json.dumps(evidence, indent=2))
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()
