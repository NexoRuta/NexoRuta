"""Focused safety checks for remote load-test lease recovery."""

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


if __name__ == "__main__":
    unittest.main()
