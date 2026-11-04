"""Exercise rolling safety gates, cgroup evidence and fail-closed verdicts."""

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import load_tests as load_test_control


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[2] / "deploy/load" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


supervision = load_module("load_supervision", "supervision.py")
with patch.dict(sys.modules, {"supervision": supervision}):
    runner = load_module("load_runner", "runner.py")


def point(second, value=0, phase="measured", metric="http_req_failed"):
    import datetime as dt
    timestamp = dt.datetime.fromtimestamp(second, dt.timezone.utc).isoformat()
    return {"type": "Point", "metric": metric,
            "data": {"value": value, "time": timestamp,
                     "tags": {"phase": phase, "stage": "nominal", "kind": "read"}}}


class StageMeasurementTests(unittest.TestCase):
    def setUp(self):
        profiles = json.loads((Path(__file__).resolve().parents[2] / "tests/load/profiles.json").read_text())
        self.profile = profiles["profiles"]["stress"]
        self.thresholds = runner.load_thresholds("stress", self.profile, profiles["thresholds"])
        self.measurements = supervision.StageMeasurements(self.profile, self.thresholds)
        self.measurements.consume("nexoruta_load_window_started", {"value": 1_000_000})

    def sample(self, second, stage, latency=100):
        failed = point(1000 + second)
        failed["data"]["tags"]["stage"] = stage
        self.measurements.consume("http_req_failed", failed["data"])
        self.measurements.consume("http_req_duration", {**failed["data"], "value": latency})

    def test_first_breach_is_reported_by_stage_even_if_global_percentile_would_hide_it(self):
        for second, stage, latency in ((1, "1", 100), (241, "2", 100), (601, "3", 2000), (961, "4", 100)):
            self.sample(second, stage, latency)
        report = self.measurements.report(2500)
        self.assertTrue(report["valid"])
        self.assertTrue(report["complete"])
        self.assertEqual(report["first_breached_stage"], "3")
        self.assertEqual(report["stages"][2]["latency"]["read"]["p95_ms"], 2000)
        verdict = supervision.classify("stress", 0, None,
            {"measured_requests": 4, "measurement_report": report}, {"available": True}, True)
        self.assertEqual(verdict, ("failed", "capacity_limit_found"))

    def test_percentiles_use_samples_not_averages_of_vu_percentiles(self):
        for second, latency in enumerate((100, 200, 300, 400)):
            self.sample(second, "1", latency)
        report = self.measurements.report(1100)
        self.assertAlmostEqual(report["stages"][0]["latency"]["read"]["p95_ms"], 385)
        self.assertFalse(report["complete"])

    def test_peak_throughput_excludes_partial_ten_second_windows(self):
        for _ in range(20):
            self.sample(1, "1")
        for _ in range(100):
            self.sample(13, "1")
        report = self.measurements.report(1015)
        self.assertEqual(report["maximum_observed_http_rps"], 2)

    def test_missing_latency_samples_invalidate_the_measurement(self):
        self.sample(1, "1")
        failed = point(1002)
        failed["data"]["tags"]["stage"] = "1"
        self.measurements.consume("http_req_failed", failed["data"])
        self.assertFalse(self.measurements.report(1015)["valid"])

    def test_conflicting_scenario_clocks_and_unknown_stages_are_rejected(self):
        with self.assertRaises(ValueError):
            self.measurements.consume("nexoruta_load_window_started", {"value": 2_000_000})
        with self.assertRaises(ValueError):
            self.sample(1, "unbounded-user-input")

    def test_exact_sample_storage_is_bounded_and_does_not_silently_truncate(self):
        self.measurements.SAMPLE_LIMIT = 1
        self.sample(1, "1")
        with self.assertRaises(ValueError):
            self.sample(2, "1")
        self.assertEqual(self.measurements.sample_count, 1)

    def test_dynamic_stress_batches_are_checked_against_starts_not_maximum_vus(self):
        self.assertEqual(self.thresholds["nexoruta_load_sync_batches_completed"], ["count>=1"])
        for metric in ("nexoruta_load_sync_batches_started", "nexoruta_load_sync_batches_completed"):
            self.measurements.consume(metric, {"value": 3, "tags": {"phase": "measured", "stage": "1"}})
        self.sample(1, "1")
        report = self.measurements.report(2500)
        self.assertEqual(report["sync_batches_started"], report["sync_batches_completed"])
        self.assertNotIn("incomplete_sync_batches", report["stages"][0]["breaches"])

    def test_incomplete_replay_is_not_classified_as_an_application_capacity_limit(self):
        self.measurements.consume("nexoruta_load_sync_batches_started",
            {"value": 1, "tags": {"phase": "measured", "stage": "1"}})
        self.sample(1, "1")
        report = self.measurements.report(2500)
        verdict = supervision.classify("stress", 99, None,
            {"measured_requests": 1, "measurement_report": report}, {"available": True}, True)
        self.assertEqual(verdict, ("failed", "slo_failed"))

    def test_nominal_sync_keeps_the_requirement_for_every_configured_vu(self):
        thresholds = runner.load_thresholds("sync", {"vus": 20, "sync": True}, {})
        self.assertEqual(thresholds["nexoruta_load_sync_batches_completed"], ["count>=20"])

    def test_error_slo_comes_from_the_pinned_thresholds(self):
        thresholds = {**self.thresholds, "http_req_failed{phase:measured}": ["rate<0.2"]}
        self.measurements = supervision.StageMeasurements(self.profile, thresholds)
        self.measurements.consume("nexoruta_load_window_started", {"value": 1_000_000})
        for index in range(20):
            failed = point(1001 + index, int(index == 0))
            failed["data"]["tags"]["stage"] = "1"
            self.measurements.consume("http_req_failed", failed["data"])
            self.measurements.consume("http_req_duration", {**failed["data"], "value": 100})
        self.assertNotIn("http_error_rate", self.measurements.report(1100)["stages"][0]["breaches"])


class EvidenceTests(unittest.TestCase):
    def test_control_exception_kills_the_traffic_process(self):
        with tempfile.TemporaryDirectory() as directory:
            process = Mock()
            process.poll.return_value = None
            stream = Mock()
            stream.evidence.snapshot.return_value = {"stream_error": None}
            with patch.object(runner, "MetricStream", return_value=stream), \
                    patch.object(runner, "Resources") as resources, \
                    patch.object(runner.subprocess, "Popen", return_value=process), \
                    patch.object(runner.shutil, "disk_usage", side_effect=OSError("controlled failure")):
                resources.return_value.sample.return_value = {"available": True}
                with self.assertRaises(OSError):
                    runner.run_process(["k6", "scenario.js"], {}, Path(directory),
                        {"run_id": "controlled"}, {"expires_at": float("inf")}, "control", "results", "unused")
            process.kill.assert_called_once()
            stream.close.assert_called_once()

    def test_setup_and_warmup_errors_do_not_trigger_measured_abort(self):
        evidence = supervision.Evidence()
        for second in range(120):
            evidence.consume(point(second, 1, "setup" if second < 60 else "warmup"))
        self.assertEqual(evidence.snapshot()["measured_requests"], 0)
        self.assertFalse(evidence.snapshot()["severe_errors"])

    def test_severe_errors_need_a_full_minute_of_measured_history(self):
        evidence = supervision.Evidence()
        for second in range(60):
            evidence.consume(point(second, 1))
        self.assertFalse(evidence.snapshot()["severe_errors"])
        evidence.consume(point(60, 1))
        evidence.consume(point(61))
        self.assertTrue(evidence.snapshot()["severe_errors"])

    def test_exactly_five_percent_does_not_cross_the_abort_limit(self):
        evidence = supervision.Evidence()
        for second in range(61):
            for request in range(20):
                evidence.consume(point(second, int(request == 0)))
        self.assertFalse(evidence.snapshot()["severe_errors"])
        evidence.consume(point(60, 1))
        evidence.consume(point(61))
        self.assertTrue(evidence.snapshot()["severe_errors"])

    def test_window_is_bounded_and_late_samples_preserve_totals(self):
        evidence = supervision.Evidence()
        for second in range(1000):
            evidence.consume(point(second))
        evidence.consume(point(1))
        self.assertLessEqual(len(evidence.window), 61)
        self.assertEqual(evidence.snapshot()["measured_requests"], 1001)

    def test_invalid_samples_are_rejected(self):
        for value in (-1, float("nan"), 2):
            with self.subTest(value=value), self.assertRaises(ValueError):
                supervision.Evidence().consume(point(0, value))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO transport requires the Linux Job runtime")
    def test_real_child_output_is_drained_before_evidence_is_finalized(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            child = output / "child.py"
            child.write_text(
                "import sys\n"
                "path = next(value[5:] for value in sys.argv if value.startswith('json='))\n"
                f"with open(path, 'w') as stream: stream.write({json.dumps(json.dumps(point(1)) + chr(10))})\n",
                encoding="utf-8",
            )
            with patch.object(runner, "Resources") as resources:
                resources.return_value.sample.return_value = {"available": True}
                resources.return_value.latest = {"available": True}
                code, reason, evidence, _ = runner.run_process(
                    [sys.executable, str(child), "scenario.js"], dict(os.environ), output,
                    {"run_id": "controlled"}, {"expires_at": float("inf")}, "control", "results", "http://unused")
            self.assertEqual(code, 0)
            self.assertIsNone(reason)
            self.assertEqual(evidence["measured_requests"], 1)
            self.assertIsNone(evidence["stream_error"])


class ResourceTests(unittest.TestCase):
    def test_cpu_saturation_requires_thirty_seconds_and_oom_uses_a_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in {"cpu.max": "200000 100000", "memory.current": "500",
                                  "memory.max": "1000", "memory.events": "oom_kill 2"}.items():
                (root / name).write_text(content)
            resources = supervision.Resources(root)
            (root / "cpu.stat").write_text("usage_usec 0")
            self.assertFalse(resources.sample(0)["oom"])
            (root / "cpu.stat").write_text("usage_usec 2000000")
            self.assertFalse(resources.sample(1)["saturated"])
            (root / "cpu.stat").write_text("usage_usec 62000000")
            self.assertTrue(resources.sample(31)["saturated"])
            (root / "memory.events").write_text("oom_kill 3")
            self.assertTrue(resources.sample(32)["oom"])

    def test_missing_resource_limits_cannot_be_reported_as_valid_measurements(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(supervision.Resources(Path(directory)).sample()["available"])


class ClassificationTests(unittest.TestCase):
    def test_controller_pass_requires_a_valid_complete_measurement(self):
        summary = {"run_id": "one", "status": "passed", "classification": "passed",
                   "evidence": {"measured_requests": 10,
                                "measurement_report": {"valid": True, "complete": True}}}
        report = load_test_control.execution_report({"run_id": "one"}, "CONDITION_SUCCEEDED", summary)
        self.assertEqual(report["status"], "passed")
        summary["evidence"]["measurement_report"]["complete"] = False
        report = load_test_control.execution_report({"run_id": "one"}, "CONDITION_SUCCEEDED", summary)
        self.assertEqual(report["status"], "failed")

    def test_wait_persists_a_failure_report_when_cloud_succeeds_without_summary(self):
        active = {"run_id": "one", "profile": "baseline", "expires_at": 999,
                  "execution": "projects/demo/locations/southamerica-west1/jobs/load/executions/one"}
        leases, results = Mock(), Mock()
        leases.read.return_value = ("1", active)
        results.read.return_value = ("0", None)
        with patch.object(load_test_control, "Storage", side_effect=[leases, results]), \
                patch.object(load_test_control, "token", return_value="controlled"), \
                patch.object(load_test_control.time, "time", return_value=1), \
                patch.object(load_test_control, "gcp_request", return_value={"conditions": [
                    {"type": "Completed", "state": "CONDITION_SUCCEEDED"}]}):
            self.assertFalse(load_test_control.wait(
                {"GCP_PROJECT_ID": "demo-project", "GCP_LOAD_RESULTS_BUCKET": "results"}, "one"))
        report = results.write.call_args.args[2]
        self.assertEqual(report["classification"], "infrastructure_failed")
        self.assertEqual(leases.write.call_args.args[2]["status"], "failed")

    def test_verdicts_do_not_confuse_cancellation_with_infrastructure_or_slos(self):
        evidence = {"measured_requests": 10, "measurement_report": {"valid": True, "complete": True}}
        for profile, code, reason, resources, has_summary, expected in (
            ("baseline", 0, None, {"available": True}, True, ("passed", "passed")),
            ("baseline", 99, None, {"available": True}, True, ("failed", "slo_failed")),
            ("stress", 99, None, {"available": True}, True, ("failed", "capacity_limit_found")),
            ("baseline", 105, "lease_expired", {}, False, ("cancelled", "cancelled")),
            ("baseline", 105, "prometheus_unavailable", {}, False, ("failed", "invalid_telemetry")),
            ("baseline", -9, None, {}, False, ("failed", "infrastructure_failed")),
            ("baseline", 0, None, {}, True, ("failed", "invalid_generator_telemetry")),
            ("baseline", 0, None, {"available": True}, False, ("failed", "incomplete_evidence")),
        ):
            with self.subTest(expected=expected):
                self.assertEqual(supervision.classify(profile, code, reason, evidence, resources, has_summary), expected)

    def test_discarded_iterations_do_not_prove_an_application_capacity_limit(self):
        verdict = supervision.classify("stress", 99, None,
            {"measured_requests": 100, "dropped_iterations": 1,
             "measurement_report": {"valid": True, "complete": True}}, {"available": True}, True)
        self.assertEqual(verdict, ("failed", "slo_failed"))

    def test_successful_execution_without_runner_evidence_is_failed(self):
        report = load_test_control.execution_report({"run_id": "one"}, "CONDITION_SUCCEEDED", None)
        self.assertEqual(report["status"], "failed")

    def test_runner_pass_cannot_override_cloud_failure_or_mismatched_run(self):
        summary = {"run_id": "one", "status": "passed", "classification": "passed",
                   "evidence": {"measured_requests": 10}}
        self.assertEqual(load_test_control.execution_report({"run_id": "one"}, "CONDITION_FAILED", summary)["status"], "failed")
        self.assertEqual(load_test_control.execution_report({"run_id": "two"}, "CONDITION_SUCCEEDED", summary)["status"], "failed")

    def test_runner_pass_requires_measured_requests(self):
        report = load_test_control.execution_report({"run_id": "one"}, "CONDITION_SUCCEEDED",
            {"run_id": "one", "status": "passed", "classification": "passed"})
        self.assertEqual(report["classification"], "incomplete_evidence")


if __name__ == "__main__":
    unittest.main()

