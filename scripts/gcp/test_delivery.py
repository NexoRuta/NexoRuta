import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import delivery
import demo_session as session
import vm_deploy


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict("os.environ", {"GITHUB_ACTIONS": "false"})
        environment.start()
        self.addCleanup(environment.stop)

    def test_release_extraction_rejects_path_traversal_and_links(self):
        for name, kind in (("../outside", tarfile.REGTYPE), ("link", tarfile.SYMTYPE)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                data = io.BytesIO()
                with tarfile.open(fileobj=data, mode="w:gz") as archive:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    archive.addfile(member)
                with self.assertRaises(ValueError):
                    vm_deploy.extract(data.getvalue(), Path(temp))

    def test_environment_cannot_inject_additional_lines(self):
        with self.assertRaises(ValueError):
            vm_deploy.env_line("SMTP_PASSWORD", "value\nAPI_IMAGE=attacker/image")
        self.assertEqual(vm_deploy.env_line("PASSWORD", "a'b$cd"), "PASSWORD='a\\'b$cd'\n")

    def test_offline_update_does_not_provision_or_start_anything(self):
        config = {"DEMO_OPERATION": "update"}
        with patch.object(session, "instance", return_value=None), patch.object(session, "command") as command:
            session.run(config)
            command.assert_not_called()

    def test_active_update_preserves_the_lease_and_does_not_apply_infrastructure(self):
        vm = {
            "status": "RUNNING", "lastStartTimestamp": "fixed-start",
            "labels": {"application": "nexoruta", "managed_by": "opentofu"},
        }
        with (
            patch.dict("os.environ", {"DEMO_RELEASE": "release-" + "a" * 32}),
            patch.object(session, "instance", return_value=vm),
            patch.object(session, "check_deadline"),
            patch.object(session, "publish_endpoints"),
            patch.object(session, "command") as command,
            patch.object(session, "write_lease") as lease,
            patch.object(delivery, "latest_release", return_value="release-" + "b" * 32) as latest,
            patch.object(delivery, "deploy") as deploy,
        ):
            session.run({"DEMO_OPERATION": "update"})
            command.assert_not_called()
            lease.assert_not_called()
            latest.assert_called_once()
            deploy.assert_called_once_with({"DEMO_OPERATION": "update"}, "release-" + "b" * 32)

    def test_automatic_events_cannot_operate_the_vm_even_if_a_job_is_misconfigured(self):
        for event in ("push", "repository_dispatch", "pull_request"):
            for operation in ("start", "update", "stop"):
                with (
                    self.subTest(event=event, operation=operation),
                    patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": event}),
                    patch.object(session, "instance") as instance,
                    patch.object(session, "command") as command,
                ):
                    with self.assertRaisesRegex(RuntimeError, "manual workflow_dispatch"):
                        session.run({"DEMO_OPERATION": operation})
                    instance.assert_not_called()
                    command.assert_not_called()

    def test_source_resolution_defaults_to_remote_main_for_all_three_repos(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(delivery, "ROOT", Path(temp)),
            patch.dict("os.environ", {}, clear=True),
            patch.object(session, "command", return_value="a" * 40 + "\n") as command,
        ):
            result = delivery.sources()
            self.assertEqual(set(result), {"backend", "frontend", "mobile"})
            fetches = [call.args for call in command.call_args_list if "fetch" in call.args]
            self.assertEqual(len(fetches), 3)
            self.assertTrue(all(call[-1] == "main" for call in fetches))

    def release_manifest(self):
        release = "release-" + "a" * 32
        return {
            "channel": "main", "release": release,
            "images": {name: f"{session.REGION}-docker.pkg.dev/demo-project/nexoruta/{name}@sha256:" + "b" * 64
                       for name in delivery.SERVICES},
        }

    def test_update_resolves_one_complete_main_release_without_building(self):
        manifest = self.release_manifest()
        with patch.dict("os.environ", {"GCP_DELIVERY_BUCKET": "demo-delivery"}), patch.object(
            session, "command", side_effect=[json.dumps({"channel": "main", "release": manifest["release"]}), json.dumps(manifest)],
        ) as command:
            self.assertEqual(delivery.latest_release({"GCP_PROJECT_ID": "demo-project"}), manifest["release"])
            self.assertEqual(command.call_count, 2)
            self.assertTrue(all(call.args[:3] == ("gcloud", "storage", "cat") for call in command.call_args_list))

    def test_update_rejects_partial_or_mixed_registry_releases(self):
        for fault in ("missing_image", "foreign_registry", "mutable_tag", "different_release", "different_channel"):
            manifest = self.release_manifest()
            pointer = {"channel": "main", "release": manifest["release"]}
            if fault == "missing_image":
                del manifest["images"]["api"]
            elif fault == "foreign_registry":
                manifest["images"]["api"] = "attacker.invalid/api@sha256:" + "b" * 64
            elif fault == "mutable_tag":
                manifest["images"]["api"] = f"{session.REGION}-docker.pkg.dev/demo-project/nexoruta/api:latest"
            elif fault == "different_release":
                manifest["release"] = "release-" + "c" * 32
            else:
                manifest["channel"] = "develop"
            with self.subTest(fault=fault), patch.object(session, "command", side_effect=[json.dumps(pointer), json.dumps(manifest)]):
                with self.assertRaises(ValueError):
                    delivery.latest_release({"GCP_PROJECT_ID": "demo-project"})

    def test_update_rejects_a_pointer_outside_the_main_channel(self):
        with patch.object(session, "command", return_value=json.dumps({"channel": "develop", "release": "release-" + "a" * 32})) as command:
            with self.assertRaisesRegex(ValueError, "pointer"):
                delivery.latest_release({"GCP_PROJECT_ID": "demo-project"})
            self.assertEqual(command.call_count, 1)

    def test_database_cleanup_still_runs_if_the_vm_stop_fails(self):
        with (
            patch.object(session, "instance", side_effect=RuntimeError("Compute unavailable")),
            patch.object(session, "end_lease") as lease,
            patch.object(session, "stop_database") as sql,
        ):
            session.stop_after_failure({})
            lease.assert_called_once()
            sql.assert_called_once()

    def test_unmanaged_database_cannot_be_stopped(self):
        database = [{"name": "nexoruta-demo-db", "settings": {"userLabels": {}, "activationPolicy": "ALWAYS"}}]
        with patch.object(session, "command", return_value=json.dumps(database)) as command:
            with self.assertRaisesRegex(RuntimeError, "not owned"):
                session.stop_database({"GCP_PROJECT_ID": "demo-project"})
            self.assertEqual(command.call_count, 1)

    def test_stop_with_a_missing_vm_still_stops_sql_without_provisioning(self):
        with (
            patch.object(session, "instance", return_value=None),
            patch.object(session, "end_lease"),
            patch.object(session, "stop_database") as sql,
            patch.object(session, "command") as command,
        ):
            session.run({"DEMO_OPERATION": "stop"})
            sql.assert_called_once()
            command.assert_not_called()

    def test_stop_cannot_recreate_deleted_resources(self):
        with self.assertRaisesRegex(RuntimeError, "must not create"):
            session.check_plan({"resource_changes": [{"address": "database", "change": {"actions": ["create"]}}]}, "stop")

    def test_sql_cleanup_is_independent_of_lease_write_failure(self):
        with (
            patch.object(session, "instance", return_value=None),
            patch.object(session, "end_lease", side_effect=RuntimeError("Storage unavailable")),
            patch.object(session, "stop_database") as sql,
        ):
            session.stop_after_failure({})
            sql.assert_called_once()

    def test_region_is_not_silently_deployed_in_the_us(self):
        with patch.dict("os.environ", {
            "GCP_PROJECT_ID": "demo-project", "GCP_ZONE": "us-central1-a",
            "GCP_STATE_BUCKET": "demo-state", "DEMO_OPERATION": "start",
        }):
            with self.assertRaisesRegex(ValueError, "Santiago"):
                session.configuration()


if __name__ == "__main__":
    unittest.main()
