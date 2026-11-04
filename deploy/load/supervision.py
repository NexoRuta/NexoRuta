"""Bounded, payload-free evidence and verdicts for the pinned k6 runner."""

from collections import defaultdict
import datetime as dt
import json
import math
import os
from pathlib import Path
import select
import threading
import time


class Evidence:
    def __init__(self):
        self.lock = threading.Lock()
        self.first_sample = None
        self.last_sample = None
        self.requests = 0
        self.errors = 0
        self.unexpected = 0
        self.dropped = 0
        self.window = defaultdict(lambda: [0, 0])
        self.fault = None
        self.severe = False

    def consume(self, point):
        if not isinstance(point, dict):
            raise ValueError("Invalid metric record")
        if point.get("type") != "Point":
            return
        metric, data = point.get("metric"), point.get("data", {})
        if not isinstance(data, dict) or not isinstance(data.get("tags", {}), dict):
            raise ValueError("Invalid metric data")
        if metric == "dropped_iterations":
            value = data["value"]
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid dropped iteration sample")
            with self.lock:
                self.dropped += value
            return
        if data.get("tags", {}).get("phase") != "measured":
            return
        if metric not in ("http_req_failed", "nexoruta_load_unexpected_results"):
            return
        value = data["value"]
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("Invalid metric sample")
        timestamp = dt.datetime.fromisoformat(data["time"].replace("Z", "+00:00")).timestamp()
        with self.lock:
            if metric == "nexoruta_load_unexpected_results":
                self.unexpected += value
                return
            if value not in (0, 1):
                raise ValueError("Invalid HTTP failure rate sample")
            self.first_sample = timestamp if self.first_sample is None else min(self.first_sample, timestamp)
            self.last_sample = timestamp if self.last_sample is None else max(self.last_sample, timestamp)
            self.requests += 1
            self.errors += value
            second = int(timestamp)
            # k6 outputs may interleave VUs; ignore late points only for the
            # rolling window, while retaining their run-wide counts above.
            if second >= int(self.last_sample) - 60:
                self.window[second][0] += 1
                self.window[second][1] += value
            for old in list(self.window):
                if old < int(self.last_sample) - 60:
                    del self.window[old]
            # Only completed seconds: arrival order within the current second
            # must not turn an exact 5% window into a transient false alarm.
            requests = sum(item[0] for stamp, item in self.window.items() if stamp < int(self.last_sample))
            errors = sum(item[1] for stamp, item in self.window.items() if stamp < int(self.last_sample))
            if self.last_sample - self.first_sample >= 60 and requests and errors / requests > 0.05:
                self.severe = True

    def snapshot(self):
        with self.lock:
            return {"measured_requests": self.requests, "measured_errors": self.errors,
                    "unexpected_results": self.unexpected, "dropped_iterations": self.dropped,
                    "first_measured_at": self.first_sample, "last_measured_at": self.last_sample,
                    "severe_errors": self.severe, "stream_error": self.fault}


class MetricStream:
    """Continuously drain a FIFO; retain aggregates, never the raw stream."""

    def __init__(self, path):
        os.mkfifo(path, mode=0o600)
        self.fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        self.evidence = Evidence()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._read, daemon=True)

    def start(self):
        self.thread.start()

    def _read(self):
        pending = b""
        try:
            while True:
                ready, _, _ = select.select([self.fd], [], [], 0.1)
                if not ready:
                    if self.stop.is_set():
                        if pending:
                            raise ValueError("Incomplete metric record")
                        return
                    continue
                pending += os.read(self.fd, 65536)
                while b"\n" in pending:
                    line, pending = pending.split(b"\n", 1)
                    if len(line) > 65536:
                        raise ValueError("Oversized metric record")
                    if line:
                        self.evidence.consume(json.loads(line))
                if len(pending) > 65536:
                    raise ValueError("Oversized metric record")
        except (OSError, ValueError, KeyError, TypeError, OverflowError):
            with self.evidence.lock:
                self.evidence.fault = "invalid_metric_stream"

    def close(self):
        self.stop.set()
        self.thread.join(timeout=3)
        if self.thread.is_alive():
            with self.evidence.lock:
                self.evidence.fault = "metric_reader_did_not_stop"
        else:
            os.close(self.fd)


class Resources:
    """Read the Job's cgroup v2 allocation without inspecting application VMs."""

    def __init__(self, root=Path("/sys/fs/cgroup")):
        self.root = root
        self.previous = None
        self.initial_oom = None
        self.saturated_since = None
        self.latest = {}

    def sample(self, now=None):
        now = time.monotonic() if now is None else now
        try:
            cpu = dict(line.split() for line in (self.root / "cpu.stat").read_text().splitlines())
            quota, period = (self.root / "cpu.max").read_text().split()
            limit = int(quota) / int(period)
            memory = int((self.root / "memory.current").read_text())
            memory_limit = int((self.root / "memory.max").read_text())
            events = dict(line.split() for line in (self.root / "memory.events").read_text().splitlines())
            oom = int(events["oom_kill"])
            if self.initial_oom is None:
                self.initial_oom = oom
            usage = int(cpu["usage_usec"]) / 1_000_000
            utilization = None
            if self.previous and now > self.previous[0]:
                utilization = max(0, (usage - self.previous[1]) / (now - self.previous[0]) / limit)
            self.previous = (now, usage)
            saturated = memory / memory_limit >= 0.9 or (utilization is not None and utilization >= 0.9)
            self.saturated_since = (now if self.saturated_since is None else self.saturated_since) if saturated else None
            self.latest = {"cpu_utilization": utilization, "memory_bytes": memory,
                           "memory_limit_bytes": memory_limit, "oom": oom > self.initial_oom,
                           "saturated": self.saturated_since is not None and now - self.saturated_since >= 30,
                           "available": True}
        except (OSError, KeyError, ValueError, ZeroDivisionError):
            self.latest = {"available": False}
        return self.latest


def classify(profile, exit_code, stop_reason, evidence, resources, has_summary):
    if stop_reason in ("cloud_run_signal", "lease_expired", "lease_cancelled_or_expired"):
        return "cancelled", "cancelled"
    if stop_reason in ("prometheus_unavailable", "metric_stream_unavailable") or evidence.get("stream_error"):
        return "failed", "invalid_telemetry"
    if stop_reason == "generator_telemetry_unavailable":
        return "failed", "invalid_generator_telemetry"
    if (stop_reason in ("generator_saturated", "generator_oom", "local_storage_exhausted")
            or resources.get("oom") or resources.get("saturated")):
        return "failed", "invalid_generator"
    if stop_reason and stop_reason != "sustained_http_errors":
        return "failed", "infrastructure_failed"
    if exit_code not in (0, 99) and stop_reason != "sustained_http_errors":
        return "failed", "infrastructure_failed"
    if not resources.get("available"):
        return "failed", "invalid_generator_telemetry"
    if not has_summary or not evidence.get("measured_requests"):
        return "failed", "incomplete_evidence"
    if stop_reason == "sustained_http_errors" or evidence.get("severe_errors") or exit_code == 99:
        if profile == "stress" and not evidence.get("unexpected_results") and not evidence.get("dropped_iterations"):
            return "failed", "capacity_limit_found"
        return "failed", "slo_failed"
    if evidence.get("unexpected_results") or evidence.get("dropped_iterations"):
        return "failed", "slo_failed"
    return "passed", "passed"
