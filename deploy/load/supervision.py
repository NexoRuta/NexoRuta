"""Bounded, payload-free evidence and verdicts for the pinned k6 runner."""

from collections import defaultdict
from array import array
import datetime as dt
import json
import math
import os
import re
from pathlib import Path
import select
import threading
import time


def seconds(value):
    match = re.fullmatch(r"([1-9][0-9]*)([sm])", value)
    if not match:
        raise ValueError("Invalid measured duration")
    return int(match[1]) * (60 if match[2] == "m" else 1)


def percentile(values, fraction):
    ordered = sorted(values)
    rank = (len(ordered) - 1) * fraction
    lower = int(rank)
    return ordered[lower] + (ordered[min(lower + 1, len(ordered) - 1)] - ordered[lower]) * (rank - lower)


class StageMeasurements:
    """Exact per-stage percentiles with a hard, run-wide sample bound."""

    SAMPLE_LIMIT = 1_000_000

    def __init__(self, profile, thresholds):
        self.start = None
        self.sample_count = 0
        self.samples = defaultdict(lambda: array("d"))
        self.counts = defaultdict(lambda: defaultdict(int))
        self.throughput = defaultdict(int)
        self.limits = {}
        self.error_limit = None
        for expression in thresholds.get("http_req_failed{phase:measured}", []):
            match = re.fullmatch(r"rate<([0-9.]+)", expression)
            if match and 0 < float(match[1]) <= 1:
                self.error_limit = float(match[1])
        for kind in ("read", "sync", "drain"):
            key = "nexoruta_load_sync_drain_duration" if kind == "drain" else f"http_req_duration{{phase:measured,kind:{kind}}}"
            expressions = thresholds.get(key, [])
            limits = {}
            for expression in expressions:
                match = re.fullmatch(r"p\((95|99)\)<([0-9.]+)", expression)
                if match:
                    limits[int(match[1])] = float(match[2])
            if set(limits) == {95, 99}:
                self.limits[kind] = limits
        self.schedule = []
        boundary = 0
        if profile.get("rate"):
            stages = profile["stages"]
            if not 1 <= len(stages) <= 16:
                raise ValueError("Invalid stage count")
            for index, stage in enumerate(stages):
                end = boundary + seconds(stage["duration"])
                self.schedule.append((str(index + 1), boundary, end, stage["target"]))
                boundary = end
        else:
            duration = seconds(profile["duration"]) + seconds(profile["ramp"]) if profile else 0
            self.schedule.append(("nominal", 0, duration, None))

    def consume(self, metric, data):
        value = data.get("value")
        tags = data.get("tags", {})
        if metric == "nexoruta_load_window_started":
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid measurement start")
            if self.start is not None and abs(self.start - value / 1000) > 0.001:
                raise ValueError("Conflicting scenario start markers")
            self.start = value / 1000
            return
        if metric == "dropped_iterations" and self.start is not None:
            timestamp = dt.datetime.fromisoformat(data["time"].replace("Z", "+00:00")).timestamp()
            stage = next((key for key, begin, end, _ in self.schedule
                          if begin <= timestamp - self.start < end), self.schedule[-1][0])
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid dropped iteration sample")
            self.counts[stage]["dropped_iterations"] += value
            return
        fields = {"http_req_failed", "http_req_duration", "nexoruta_load_unexpected_results",
                  "nexoruta_load_sync_batches_started", "nexoruta_load_sync_batches_completed",
                  "nexoruta_load_sync_drain_duration"}
        if tags.get("phase") != "measured" or metric not in fields:
            return
        stage = tags.get("stage")
        if stage not in {key for key, _, _, _ in self.schedule}:
            raise ValueError("Unknown measurement stage")
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("Invalid stage sample")
        counts = self.counts[stage]
        if metric in ("http_req_duration", "nexoruta_load_sync_drain_duration"):
            kind = "drain" if metric == "nexoruta_load_sync_drain_duration" else tags.get("kind")
            if kind not in ("read", "sync", "drain") or self.sample_count >= self.SAMPLE_LIMIT:
                raise ValueError("Invalid or oversized latency evidence")
            self.samples[(stage, kind)].append(value)
            self.sample_count += 1
        elif metric == "http_req_failed":
            counts["requests"] += 1
            counts["errors"] += value
            if self.start is not None:
                timestamp = dt.datetime.fromisoformat(data["time"].replace("Z", "+00:00")).timestamp()
                bucket = int((timestamp - self.start) // 10)
                if not 0 <= bucket < 600:
                    raise ValueError("Measured timestamp exceeds the bounded run")
                self.throughput[bucket] += 1
        else:
            counts[metric.removeprefix("nexoruta_load_")] += value

    def report(self, ended):
        rows = []
        valid = self.start is not None and bool(self.limits) and self.error_limit is not None
        for stage, begin, end, target in self.schedule:
            counts = self.counts[stage]
            requests = counts["requests"]
            elapsed = max(0, min(ended - self.start, end) - begin) if self.start is not None else 0
            row = {"stage": stage, "target_iterations_per_second": target,
                   "observed_seconds": elapsed, "complete": elapsed >= end - begin and requests > 0,
                   "requests": requests, "errors": counts["errors"],
                   "error_rate": counts["errors"] / requests if requests else None,
                   "http_rps": requests / elapsed if elapsed else None,
                   "dropped_iterations": counts["dropped_iterations"],
                   "sync_batches_started": counts["sync_batches_started"],
                   "sync_batches_completed": counts["sync_batches_completed"],
                   "latency": {}, "breaches": []}
            latency_count = 0
            for kind in ("read", "sync", "drain"):
                values = self.samples.get((stage, kind), ())
                if kind != "drain":
                    latency_count += len(values)
                if values:
                    p95, p99 = percentile(values, 0.95), percentile(values, 0.99)
                    row["latency"][kind] = {"count": len(values), "p95_ms": p95, "p99_ms": p99}
                    limits = self.limits.get(kind, {})
                    if not limits:
                        valid = False
                    for quantile, observed in ((95, p95), (99, p99)):
                        if quantile in limits and observed >= limits[quantile]:
                            row["breaches"].append(f"{kind}_p{quantile}")
            if latency_count != requests:
                valid = False
            if (row["error_rate"] is not None and self.error_limit is not None
                    and row["error_rate"] >= self.error_limit):
                row["breaches"].append("http_error_rate")
            if counts["unexpected_results"]:
                row["breaches"].append("unexpected_results")
            if counts["dropped_iterations"]:
                row["breaches"].append("dropped_iterations")
            if counts["sync_batches_started"] != counts["sync_batches_completed"]:
                row["breaches"].append("incomplete_sync_batches")
            rows.append(row)
        windows = [count / 10 for bucket, count in self.throughput.items()
                   if self.start is not None and ended >= self.start + (bucket + 1) * 10]
        return {"valid": valid and any(row["requests"] for row in rows),
                "complete": all(row["complete"] for row in rows), "stages": rows,
                "first_breached_stage": next((row["stage"] for row in rows if row["breaches"]), None),
                "maximum_observed_http_rps": max(windows) if windows else None,
                "throughput_window_seconds": 10,
                "sync_batches_started": sum(row["sync_batches_started"] for row in rows),
                "sync_batches_completed": sum(row["sync_batches_completed"] for row in rows)}


class Evidence:
    def __init__(self, profile=None, thresholds=None):
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
        self.measurements = StageMeasurements(profile or {}, thresholds or {})

    def consume(self, point):
        if not isinstance(point, dict):
            raise ValueError("Invalid metric record")
        if point.get("type") != "Point":
            return
        metric, data = point.get("metric"), point.get("data", {})
        if not isinstance(data, dict) or not isinstance(data.get("tags", {}), dict):
            raise ValueError("Invalid metric data")
        with self.lock:
            self.measurements.consume(metric, data)
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

    def snapshot(self, final=False):
        with self.lock:
            return {"measured_requests": self.requests, "measured_errors": self.errors,
                    "unexpected_results": self.unexpected, "dropped_iterations": self.dropped,
                    "first_measured_at": self.first_sample, "last_measured_at": self.last_sample,
                    "severe_errors": self.severe, "stream_error": self.fault,
                    "measurement_report": self.measurements.report(time.time()) if final else None}


class MetricStream:
    """Continuously drain a FIFO; retain aggregates, never the raw stream."""

    def __init__(self, path, profile=None, thresholds=None):
        os.mkfifo(path, mode=0o600)
        self.fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        self.evidence = Evidence(profile, thresholds)
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
    if stop_reason == "authentication_unavailable":
        return "failed", "invalid_authentication"
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
    measurement = evidence.get("measurement_report") or {}
    if not measurement.get("valid"):
        return "failed", "incomplete_evidence"
    if (stop_reason == "sustained_http_errors" or evidence.get("severe_errors") or exit_code == 99
            or measurement.get("first_breached_stage")):
        if (profile == "stress" and not evidence.get("unexpected_results") and not evidence.get("dropped_iterations")
                and measurement.get("sync_batches_started") == measurement.get("sync_batches_completed")):
            return "failed", "capacity_limit_found"
        return "failed", "slo_failed"
    if evidence.get("unexpected_results") or evidence.get("dropped_iterations"):
        return "failed", "slo_failed"
    if not measurement.get("complete"):
        return "failed", "incomplete_evidence"
    return "passed", "passed"
