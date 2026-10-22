import datetime as dt
import unittest
from unittest.mock import patch

import demo_session as session


class SessionSafetyTests(unittest.TestCase):
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
            patch.dict("os.environ", {"DEMO_RELEASE": "release-" + "a" * 32}),
            patch.object(session, "instance", return_value=None),
            patch.object(session, "write_lease"),
            patch.object(session, "command", return_value='{"resource_changes": []}'),
            patch.object(session, "gcloud", return_value='{"status": "RUNNING"}'),
            patch.object(session, "stop_after_failure") as stop,
        ):
            with self.assertRaisesRegex(RuntimeError, "STOP policy"):
                session.run(config)
            stop.assert_called_once_with(config)


if __name__ == "__main__":
    unittest.main()
