"""Focused safety checks for remote load-test lease recovery."""

import subprocess
import unittest
from unittest.mock import patch

import load_tests as load_test_control


class MemoryStorage:
    def __init__(self, value):
        self.value = value
        self.generation = 1

    def read(self, _name):
        return str(self.generation), dict(self.value) if self.value is not None else None

    def write(self, _name, generation, value):
        if str(self.generation) != generation:
            raise AssertionError("generation precondition was not preserved")
        self.value = dict(value)
        self.generation += 1
        return str(self.generation)


class LoadTestLeaseTests(unittest.TestCase):
    def test_expired_prelaunch_lease_is_closed_without_starting_cloud_run(self):
        store = MemoryStorage({"run_id": "run-1", "status": "starting", "expires_at": 1})
        with patch.object(load_test_control, "time") as clock, patch.object(load_test_control, "gcp_request") as request:
            clock.time.return_value = 2
            self.assertTrue(load_test_control.reconcile_execution(store, "demo-project", "run-1"))
        self.assertEqual(store.value["status"], "failed")
        request.assert_not_called()

    def test_lost_jobs_run_response_is_reconciled_by_exact_run_id(self):
        run_id = "00000000-0000-4000-8000-000000000001"
        execution_name = "projects/demo/locations/southamerica-west1/jobs/nexoruta-load-tests/executions/run-1"
        store = MemoryStorage({"run_id": run_id, "status": "cancelling", "launch_requested_at": 5,
                              "expires_at": 10})
        listing = {"executions": [{"name": execution_name, "template": {"containers": [{
            "env": [{"name": "NEXORUTA_RUN_ID", "value": run_id}]
        }]}}]}

        def request(_method, url, _project, body=None):
            if url.endswith("/executions?pageSize=100&orderBy=createTime+desc"):
                return listing
            if url.endswith(execution_name):
                return {"conditions": [{"type": "Completed", "state": "CONDITION_FAILED"}]}
            self.fail(f"Unexpected Cloud Run request: {url}")

        with patch.object(load_test_control, "gcp_request", side_effect=request):
            self.assertTrue(load_test_control.reconcile_execution(store, "demo-project", run_id))
        self.assertEqual(store.value["execution"], execution_name)
        self.assertEqual(store.value["status"], "failed")

    def test_multiple_executions_for_one_run_id_are_never_guessed(self):
        run_id = "00000000-0000-4000-8000-000000000001"
        item = {"template": {"containers": [{"env": [{"name": "NEXORUTA_RUN_ID", "value": run_id}]}]}}
        with patch.object(load_test_control, "gcp_request", return_value={"executions": [
            {**item, "name": "execution-1"}, {**item, "name": "execution-2"},
        ]}):
            with self.assertRaisesRegex(RuntimeError, "Multiple Cloud Run executions"):
                load_test_control.find_execution("demo-project", run_id)

    def test_running_execution_keeps_the_lease_blocking_other_controls(self):
        store = MemoryStorage({"run_id": "run-1", "status": "running", "execution": "execution-1"})
        with patch.object(load_test_control, "gcp_request", return_value={"conditions": []}):
            self.assertFalse(load_test_control.reconcile_execution(store, "demo-project", "run-1"))
        self.assertEqual(store.value["status"], "running")


class LatestFixtureVersionTests(unittest.TestCase):
    @patch("load_tests.subprocess.run")
    def test_accepts_short_version_name_from_gcloud_value_format(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout="1\n", stderr="")

        self.assertEqual("1", load_test_control.latest_fixture_version("nexoruta-demo-20261022"))
        self.assertIn("--format=value(name)", run.call_args.args[0])

    @patch("load_tests.subprocess.run")
    def test_accepts_full_secret_version_resource_name(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0,
            stdout="projects/123456789/secrets/nexoruta-load-fixtures/versions/7\n",
            stderr="",
        )

        self.assertEqual("7", load_test_control.latest_fixture_version("nexoruta-demo-20261022"))

    @patch("load_tests.subprocess.run")
    def test_rejects_unrecognized_gcloud_output(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")

        with self.assertRaisesRegex(RuntimeError, "No enabled synthetic fixture version"):
            load_test_control.latest_fixture_version("nexoruta-demo-20261022")


class DemoControlLockTests(unittest.TestCase):
    def test_uses_the_lock_store_protocol_instead_of_the_named_object_storage(self):
        config = {"GCP_PROJECT_ID": "nexoruta-demo-20261022", "GCP_STATE_BUCKET": "state-bucket"}
        lock_store = object()
        context = object()
        with patch.object(load_test_control.control_lock, "JsonStorage", return_value=lock_store) as storage, \
                patch.object(load_test_control.control_lock, "control_lock", return_value=context) as guard:
            result = load_test_control.demo_control_lock(config, "access-token")

        self.assertIs(context, result)
        storage.assert_called_once_with("state-bucket", "access-token")
        guard.assert_called_once_with(config, store=lock_store)


class ReleaseMarkerTests(unittest.TestCase):
    def test_parses_marker_when_ssh_adds_output_around_the_command(self):
        output = (
            "gcloud ssh notice\n" + load_test_control.RELEASE_MARKER_START +
            "\nrelease-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n" +
            load_test_control.RELEASE_MARKER_END + "\nremote shell notice"
        )

        self.assertEqual(
            "release-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            load_test_control.parse_release_marker(output),
        )

    def test_rejects_invalid_or_ambiguous_markers(self):
        with self.assertRaisesRegex(RuntimeError, "invalid applied release marker"):
            load_test_control.parse_release_marker(
                load_test_control.RELEASE_MARKER_START + "\ninvalid\n" +
                load_test_control.RELEASE_MARKER_END
            )
        with self.assertRaisesRegex(RuntimeError, "Could not isolate"):
            load_test_control.parse_release_marker("release-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")


if __name__ == "__main__":
    unittest.main()
