import datetime as dt
import json
import threading
from pathlib import Path
import unittest
from unittest.mock import patch

import demo_session as session
import delivery


class SessionSafetyTests(unittest.TestCase):
    def test_stop_runs_both_vms_concurrently_without_stopping_sql(self):
        barrier = threading.Barrier(2)
        calls = []
        vm = {"status": "RUNNING", "labels": {"application": "nexoruta", "managed_by": "opentofu"}}

        def stop(node, *args, **kwargs):
            calls.append(node["NODE_ID"])
            barrier.wait(timeout=3)

        with (patch.object(session, "end_lease"), patch.object(session, "instance", return_value=vm),
              patch.object(session, "gcloud", side_effect=stop), patch.object(session, "command") as command):
            self.assertEqual(session.stop_session({}), [])
            command.assert_not_called()
        self.assertCountEqual(calls, ["a", "b"])

    def test_guard_leaves_sql_running(self):
        guard = (Path(__file__).parents[2] / "infra/gcp/bootstrap/guard.yaml.tftpl").read_text()
        self.assertNotIn("sqladmin.googleapis.com", guard)
        self.assertIn("/instances/\" + node.name + \"/stop", guard)

    def test_stop_continues_if_lease_or_one_node_fails(self):
        nodes = session.node_configs({})
        def lookup(node):
            if node["NODE_ID"] == "a":
                raise RuntimeError("unavailable")
            return {"status": "RUNNING", "labels": {"application": "nexoruta", "managed_by": "opentofu"}}
        with (patch.object(session, "end_lease", side_effect=RuntimeError("lease failure")),
              patch.object(session, "instance", side_effect=lookup),
              patch.object(session, "gcloud") as gcloud):
            errors = session.stop_session({})
        self.assertEqual(len(errors), 2)
        self.assertEqual(gcloud.call_args.args[0], nodes[1])

    def test_tofu_setup_overlaps_database_start_and_both_finish_before_session(self):
        database_started = threading.Event()
        setup_started = threading.Event()
        completed = []

        def start_database(config):
            database_started.set()
            if not setup_started.wait(5):
                raise AssertionError("OpenTofu setup did not run concurrently")
            completed.append("database")

        def setup(config):
            setup_started.set()
            if not database_started.wait(5):
                raise AssertionError("database did not start concurrently")
            completed.append("tofu")

        def start(config, release):
            self.assertCountEqual(completed, ["database", "tofu"])

        with (patch.object(delivery, "latest_release", return_value="release-" + "a" * 32),
              patch.object(session, "instance", return_value=None),
              patch.object(session, "write_lease"),
              patch.object(session, "start_database", side_effect=start_database),
              patch.object(session, "initialize_tofu", side_effect=setup),
              patch.object(session, "start_session", side_effect=start)):
            session.run({"DEMO_OPERATION": "start"})

    def setUp(self):
        environment = patch.dict("os.environ", {"GITHUB_ACTIONS": "false"})
        environment.start()
        self.addCleanup(environment.stop)
        self.now = dt.datetime(2026, 10, 21, 15, tzinfo=dt.timezone.utc)
        self.vm = {
            "name": session.VM_NAME,
            "status": "RUNNING",
            "labels": {"application": "nexoruta", "managed_by": "opentofu"},
            "scheduling": {
                "maxRunDuration": {"seconds": "14400"},
                "instanceTerminationAction": "STOP",
                "automaticRestart": False,
            },
            "resourceStatus": {"scheduling": {"terminationTimestamp": "2026-10-21T19:00:00Z"}},
        }

    def test_repeated_start_cannot_extend_an_active_session(self):
        with self.assertRaisesRegex(RuntimeError, "already running"):
            session.check_existing(self.vm, "start")

    def test_stop_on_empty_project_cannot_create_a_vm(self):
        with self.assertRaisesRegex(RuntimeError, "refusing to create"):
            session.check_existing(None, "stop")

    def test_unrelated_vm_cannot_be_taken_over(self):
        self.vm["labels"] = {}
        with self.assertRaisesRegex(RuntimeError, "not labeled"):
            session.check_existing(self.vm, "stop")

    def test_restart_after_expiry_is_allowed(self):
        self.vm["status"] = "TERMINATED"
        session.check_existing(self.vm, "start")

    def test_reported_deadline_must_match_four_hour_policy(self):
        session.check_deadline(self.vm, self.now)
        self.vm["resourceStatus"]["scheduling"]["terminationTimestamp"] = "2026-10-22T19:00:00Z"
        with self.assertRaisesRegex(RuntimeError, "exceeds"):
            session.check_deadline(self.vm, self.now)

    def test_missing_or_unsafe_stop_policy_is_rejected(self):
        for key, value in (
            ("instanceTerminationAction", "DELETE"),
            ("automaticRestart", True),
            ("maxRunDuration", {"seconds": "28800"}),
        ):
            with self.subTest(key=key), patch.dict(self.vm["scheduling"], {key: value}):
                with self.assertRaises(RuntimeError):
                    session.check_deadline(self.vm, self.now)
        self.vm.pop("resourceStatus")
        with self.assertRaisesRegex(RuntimeError, "termination timestamp"):
            session.check_deadline(self.vm, self.now)

    def test_list_and_describe_use_the_correct_zone_flags(self):
        config = {"GCP_PROJECT_ID": "demo-project", "GCP_ZONE": "us-central1-a"}
        with patch.object(session, "command") as command:
            session.gcloud(config, "compute", "instances", "list")
            self.assertIn("--zones=us-central1-a", command.call_args.args)
            session.gcloud(config, "compute", "instances", "describe", session.VM_NAME)
            self.assertIn("--zone=us-central1-a", command.call_args.args)

    def test_replacing_persistent_resources_is_rejected(self):
        plan = {"resource_changes": [{
            "address": "google_compute_disk.data",
            "change": {"actions": ["delete", "create"]},
        }]}
        with self.assertRaisesRegex(RuntimeError, "delete or replace"):
            session.check_plan(plan)

    def test_start_policy_verification_failure_stops_vm(self):
        config = {
            "DEMO_OPERATION": "start", "GCP_PROJECT_ID": "demo-project",
            "GCP_ZONE": "us-central1-a", "GCP_STATE_BUCKET": "demo-state",
        }
        with (
            patch.object(delivery, "latest_release", return_value="release-" + "a" * 32),
            patch.object(session, "instance", return_value=None),
            patch.object(session, "write_lease"),
            patch.object(session, "start_database"),
            patch.object(session, "command", return_value='{"resource_changes": []}'),
            patch.object(session, "gcloud", return_value='{"status": "RUNNING"}'),
            patch.object(session, "stop_after_failure") as stop,
        ):
            with self.assertRaisesRegex(RuntimeError, "STOP policy"):
                session.run(config)
            stop.assert_called_once_with(config)

    def test_stopped_database_is_woken_before_its_users_can_be_refreshed(self):
        database = {"name": "nexoruta-demo-db", "state": "STOPPED", "settings": {
            "activationPolicy": "NEVER", "userLabels": {"managed_by": "opentofu"},
        }}
        with patch.object(session, "command", side_effect=[json.dumps([database]), None, '{"state":"RUNNABLE"}']) as command:
            session.start_database({"GCP_PROJECT_ID": "demo-project"})
            self.assertIn("--activation-policy=ALWAYS", command.call_args_list[1].args)
            self.assertEqual(command.call_args_list[2].args[:4], ("gcloud", "sql", "instances", "describe"))

    def test_unmanaged_database_is_never_started(self):
        database = {"name": "nexoruta-demo-db", "settings": {"userLabels": {}}}
        with patch.object(session, "command", return_value=json.dumps([database])) as command:
            with self.assertRaisesRegex(RuntimeError, "not owned"):
                session.start_database({"GCP_PROJECT_ID": "demo-project"})
            self.assertEqual(command.call_count, 1)

    def test_start_cleanup_also_covers_a_failed_infrastructure_refresh(self):
        events = []
        def fail_refresh(config, release):
            events.append("refresh")
            raise RuntimeError("refresh failed")
        with (
            patch.object(delivery, "latest_release", return_value="release-" + "a" * 32),
            patch.object(session, "instance", return_value=None),
            patch.object(session, "write_lease"),
            patch.object(session, "start_database", side_effect=lambda config: events.append("database")),
            patch.object(session, "initialize_tofu"),
            patch.object(session, "start_session", side_effect=fail_refresh),
            patch.object(session, "stop_after_failure") as cleanup,
        ):
            with self.assertRaisesRegex(RuntimeError, "refresh failed"):
                session.run({"DEMO_OPERATION": "start"})
            self.assertEqual(events, ["database", "refresh"])
            cleanup.assert_called_once()

    def test_stopping_an_already_stopped_vm_never_refreshes_sql_users_or_wakes_it(self):
        self.vm["status"] = "TERMINATED"
        with (
            patch.object(session, "instance", return_value=self.vm),
            patch.object(session, "end_lease"),
            patch.object(session, "command") as command,
            patch.object(session, "gcloud") as vm_command,
        ):
            session.run({"DEMO_OPERATION": "stop"})
            command.assert_not_called()
            vm_command.assert_not_called()

    def test_rejected_repeat_start_does_not_clean_up_an_active_session(self):
        with (
            patch.object(session, "instance", return_value=self.vm),
            patch.object(session, "start_database") as database,
            patch.object(session, "stop_after_failure") as cleanup,
        ):
            with self.assertRaisesRegex(RuntimeError, "already running"):
                session.run({"DEMO_OPERATION": "start"})
            database.assert_not_called()
            cleanup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
