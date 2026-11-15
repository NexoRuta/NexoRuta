import datetime as dt
import json
import subprocess
import threading
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import demo_session as session
import delivery
import bootstrap_setup
import load_tests as load_test_control
import host_versions
import deployment_health


def valid_host_versions():
    return {
        "schema_version": 1, "recorded_at": "2026-11-14T12:00:00+00:00",
        "os_id": "debian", "os_version_id": "12", "kernel": "6.1.0-cloud-amd64",
        "architecture": "x86_64", "docker_server": "29.1.3", "docker_compose": "2.40.3",
        "docker_buildx": "github.com/docker/buildx v0.29.1",
        "containerd": "containerd github.com/containerd/containerd v2.1.5",
        "packages": {name: "1.2.3-1" for name in host_versions.PACKAGE_NAMES},
    }


def valid_compose_health(node="a", cache_enabled=True):
    return {
        "node": node,
        "services": [
            {"service": name, "state": "running",
             "health": "healthy" if name in deployment_health.HEALTHCHECK_SERVICES else "not-configured"}
            for name in deployment_health.expected_services(node, cache_enabled)
        ],
    }


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
              patch.object(load_test_control, "assert_no_active"),
              patch.object(bootstrap_setup, "validate_runtime_target"),
              patch.object(session, "instance", return_value=None),
              patch.object(session, "write_lease"),
              patch.object(session, "start_database", side_effect=start_database),
              patch.object(session, "initialize_tofu", side_effect=setup),
              patch.object(session, "start_session", side_effect=start)):
            session.run({"DEMO_OPERATION": "start", "GCP_PROJECT_ID": "demo-project",
                         "GCP_STATE_BUCKET": "demo-project-tofu-state",
                         "NEXORUTA_EXECUTION_PROFILE": "demo"})

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

    def test_new_start_normalizes_an_expired_absolute_deadline_in_place(self):
        stopped = dict(self.vm)
        stopped["status"] = "TERMINATED"
        stopped["scheduling"] = {
            "terminationTime": "2026-10-21T19:00:00Z",
            "instanceTerminationAction": "STOP",
            "automaticRestart": False,
            "onHostMaintenance": "TERMINATE",
        }
        normalized = dict(stopped)
        normalized["scheduling"] = {
            "maxRunDuration": {"seconds": "14400"},
            "instanceTerminationAction": "STOP",
            "automaticRestart": False,
            "onHostMaintenance": "TERMINATE",
        }
        node = session.node_configs({})[0]
        with (patch.object(session, "instance", return_value=stopped),
              patch.object(session, "gcloud", side_effect=[None, json.dumps(normalized)]) as gcloud):
            session.ensure_start_schedule(node)
        self.assertEqual(gcloud.call_count, 2)
        self.assertEqual(gcloud.call_args_list[0].args[1:], (
            "compute", "instances", "set-scheduling", node["VM_NAME"],
            "--clear-termination-time", "--max-run-duration=14400s",
            "--instance-termination-action=STOP", "--no-restart-on-failure",
            "--maintenance-policy=TERMINATE",
        ))
        self.assertEqual(gcloud.call_args_list[1].args[1:5], (
            "compute", "instances", "describe", node["VM_NAME"],
        ))

    def test_new_start_does_not_touch_an_already_normalized_vm(self):
        stopped = dict(self.vm)
        stopped["status"] = "TERMINATED"
        stopped["scheduling"] = {**self.vm["scheduling"], "onHostMaintenance": "TERMINATE"}
        node = session.node_configs({})[0]
        with (patch.object(session, "instance", return_value=stopped),
              patch.object(session, "gcloud") as gcloud):
            session.ensure_start_schedule(node)
        gcloud.assert_not_called()

    def test_new_start_refuses_to_reconcile_a_running_or_unmanaged_vm(self):
        node = session.node_configs({})[0]
        with patch.object(session, "instance", return_value=self.vm), patch.object(session, "gcloud") as gcloud:
            with self.assertRaisesRegex(RuntimeError, "already running"):
                session.ensure_start_schedule(node)
            gcloud.assert_not_called()
        self.vm["status"] = "TERMINATED"
        self.vm["labels"] = {}
        with patch.object(session, "instance", return_value=self.vm), patch.object(session, "gcloud") as gcloud:
            with self.assertRaisesRegex(RuntimeError, "not labeled"):
                session.ensure_start_schedule(node)
            gcloud.assert_not_called()

    def test_reported_deadline_must_match_four_hour_policy(self):
        session.check_deadline(self.vm, self.now)
        self.vm["resourceStatus"]["scheduling"]["terminationTimestamp"] = "2026-10-22T19:00:00Z"
        with self.assertRaisesRegex(RuntimeError, "exceeds"):
            session.check_deadline(self.vm, self.now)

    def test_absolute_session_deadline_is_valid_after_vm_restart(self):
        self.vm["scheduling"].pop("maxRunDuration")
        self.vm["scheduling"]["terminationTime"] = "2026-10-21T19:00:00Z"
        self.assertEqual(session.check_deadline(self.vm, self.now), "2026-10-21T19:00:00Z")

    def test_absolute_session_deadline_must_match_compute_timestamp(self):
        self.vm["scheduling"].pop("maxRunDuration")
        self.vm["scheduling"]["terminationTime"] = "2026-10-21T18:00:00Z"
        with self.assertRaisesRegex(RuntimeError, "differs"):
            session.check_deadline(self.vm, self.now)

    def test_missing_or_unsafe_stop_policy_is_rejected(self):
        for key, value in (
            ("instanceTerminationAction", "DELETE"),
            ("automaticRestart", True),
            ("maxRunDuration", {"seconds": "28800"}),
            ("terminationTime", "2026-10-21T19:00:00Z"),
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

    def test_ssh_and_scp_expire_keys_but_other_gcloud_commands_do_not(self):
        config = {"GCP_PROJECT_ID": "demo-project", "GCP_ZONE": "us-central1-a"}
        for args, expires in ((["compute", "ssh", "demo"], True),
                              (["compute", "scp", "local.py", "demo:/tmp/"], True),
                              (["compute", "instances", "describe", "demo"], False)):
            with self.subTest(args=args), patch.object(session, "command") as command:
                session.gcloud(config, *args)
                self.assertEqual("--ssh-key-expire-after=1h" in command.call_args.args, expires)

    def test_profile_limit_is_actionable_and_transient_ssh_errors_are_preserved(self):
        config = {"GCP_PROJECT_ID": "demo-project", "GCP_ZONE": "us-central1-a"}
        for operation in ("ssh", "scp"):
            error = subprocess.CalledProcessError(1, "gcloud", stderr="Login profile size exceeds 32 KiB")
            with self.subTest(operation=operation), patch.object(session, "command", side_effect=error):
                with self.assertRaisesRegex(RuntimeError, "operation=repair-ssh"):
                    session.gcloud(config, "compute", operation, "demo", capture=True)
        error = subprocess.CalledProcessError(255, "gcloud", stderr="Connection refused")
        with patch.object(session, "command", side_effect=error):
            with self.assertRaises(subprocess.CalledProcessError) as raised:
                session.gcloud(config, "compute", "ssh", "demo", capture=True)
            self.assertIs(raised.exception, error)

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
            "GCP_ZONE": "us-central1-a", "GCP_STATE_BUCKET": "demo-project-tofu-state",
            "NEXORUTA_EXECUTION_PROFILE": "demo",
        }
        with (
            patch.object(delivery, "latest_release", return_value="release-" + "a" * 32),
            patch.object(load_test_control, "assert_no_active"),
            patch.object(bootstrap_setup, "validate_runtime_target"),
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
            patch.object(load_test_control, "assert_no_active"),
            patch.object(session, "instance", return_value=None),
            patch.object(session, "write_lease"),
            patch.object(session, "start_database", side_effect=lambda config: events.append("database")),
            patch.object(bootstrap_setup, "validate_runtime_target"),
            patch.object(session, "initialize_tofu"),
            patch.object(session, "start_session", side_effect=fail_refresh),
            patch.object(session, "stop_after_failure") as cleanup,
        ):
            with self.assertRaisesRegex(RuntimeError, "refresh failed"):
                session.run({"DEMO_OPERATION": "start", "GCP_PROJECT_ID": "demo-project",
                             "GCP_STATE_BUCKET": "demo-project-tofu-state",
                             "NEXORUTA_EXECUTION_PROFILE": "demo"})
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

    def test_reproduction_smoke_output_contains_only_allowlisted_role_and_cache_results(self):
        deployment = {
            "authenticated_reads": [
                {"role": role, "login": "passed", "actor_read": "passed", "email": f"{role}@example.test"}
                for role in ("admin", "operator", "commerce")
            ],
            "redis_node": "b", "redis_smoke_clients": ["a", "b"], "cache_enabled": True,
            "endpoints": {"api": "https://private.example.test"}, "access_token": "private-token",
            "host_versions": {"a": valid_host_versions(), "b": valid_host_versions()},
            "compose_health": {"a": valid_compose_health("a"), "b": valid_compose_health("b")},
        }
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "github-output.txt"
            with patch.dict("os.environ", {"GITHUB_OUTPUT": str(output_path)}):
                session.publish_reproduction_deployment_smoke(
                    {"GCP_PROJECT_ID": "nfr14-test-project"}, "release-" + "a" * 32, deployment,
                )
            raw = output_path.read_text(encoding="utf-8")
        payload = raw.splitlines()[1]
        proof = json.loads(payload)
        self.assertEqual(proof["schema_version"], 3)
        self.assertEqual(proof["project_id"], "nfr14-test-project")
        self.assertEqual(set(proof["host_versions"]), {"a", "b"})
        self.assertEqual(set(proof["compose_health"]), {"a", "b"})
        self.assertEqual(len(proof["compose_health"]["a"]["services"]),
                         len(deployment_health.expected_services("a", True)))
        self.assertEqual([item["role"] for item in proof["authenticated_reads"]],
                         ["admin", "commerce", "operator"])
        self.assertNotIn("email", payload)
        self.assertNotIn("private.example.test", payload)
        self.assertNotIn("private-token", payload)

    def test_reproduction_smoke_rejects_duplicate_actor_roles(self):
        read = {"role": "admin", "login": "passed", "actor_read": "passed"}
        deployment = {
            "authenticated_reads": [read, read, {"role": "commerce", "login": "passed", "actor_read": "passed"}],
            "redis_node": "b", "redis_smoke_clients": ["a", "b"], "cache_enabled": True,
        }
        with self.assertRaisesRegex(RuntimeError, "every synthetic runtime role"):
            session.publish_reproduction_deployment_smoke(
                {"GCP_PROJECT_ID": "nfr14-test-project"}, "release-" + "a" * 32, deployment,
            )


if __name__ == "__main__":
    unittest.main()
