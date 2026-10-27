import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import delivery
import integration
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

    def test_remote_stage_error_reports_only_the_structured_error_type(self):
        output = '\n'.join([
            '{"node":"a","stage":"prepare","status":"failed","error_type":"PermissionError","error":"sensitive"}',
            '{"node":"a","stage":"prepare","status":"failed","error_type":"invalid type; leak"}',
        ])
        self.assertEqual(
            delivery.remote_stage_error(output, "a", "prepare"),
            "Node a stage prepare failed (PermissionError)",
        )
        self.assertEqual(
            delivery.remote_stage_error('{"node":"b","stage":"apply","status":"failed"}', "a", "prepare"),
            "Node a stage prepare failed without a structured report",
        )

    def test_remote_stage_error_can_read_stderr_report(self):
        output = '{"node":"a","stage":"prepare","status":"failed","error_type":"PermissionError"}'
        self.assertEqual(
            delivery.remote_stage_error(output, "a", "prepare"),
            "Node a stage prepare failed (PermissionError)",
        )

    def test_remote_stage_error_reports_python_exception_class_only(self):
        self.assertEqual(
            delivery.remote_stage_error("Traceback:\nPermissionError: private detail", "a", "prepare"),
            "Node a stage prepare failed (PermissionError)",
        )

    def test_remote_stage_error_reports_exit_code_without_output(self):
        self.assertEqual(
            delivery.remote_stage_error("__NEXORUTA_STAGE_EXIT__=1", "a", "prepare"),
            "Node a stage prepare exited (1) without a report",
        )

    def test_remote_stage_error_reports_qualified_exception_class_only(self):
        self.assertEqual(
            delivery.remote_stage_error("urllib.error.HTTPError: private detail", "a", "prepare"),
            "Node a stage prepare failed (HTTPError)",
        )

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

    def test_staged_frontend_receives_map_from_the_pinned_backend_archive(self):
        def archive(*args, **kwargs):
            data = io.BytesIO()
            with tarfile.open(fileobj=data, mode="w") as output:
                directory = tarfile.TarInfo(".")
                directory.type = tarfile.DIRTYPE
                directory.mode = 0o755
                output.addfile(directory)
                if args[0][2].endswith("backend"):
                    payload = b'{"type":"FeatureCollection","features":[]}'
                    member = tarfile.TarInfo("src/ZonasCobertura/Data/departamentos-uruguay.geojson")
                    member.size = len(payload)
                    output.addfile(member, io.BytesIO(payload))
            return data.getvalue()

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)
            with patch.object(delivery.subprocess, "check_output", side_effect=archive):
                delivery.stage_sources(destination)
            canonical = destination / "backend/src/ZonasCobertura/Data/departamentos-uruguay.geojson"
            bundled = destination / "frontend/.build/departamentos-uruguay.geojson"
            self.assertEqual(canonical.read_bytes(), bundled.read_bytes())
            self.assertTrue((destination / "frontend/Dockerfile.deploy").is_file())

    def release_manifest(self):
        release = "release-" + "a" * 32
        return {
            "channel": "main", "release": release,
            "images": {name: f"{session.REGION}-docker.pkg.dev/demo-project/nexoruta/{name}@sha256:" + "b" * 64
                       for name in delivery.SERVICES},
        }

    def test_build_requires_the_pinned_tag_before_any_cloud_build(self):
        with patch.object(session, "configuration", return_value={}), patch.dict("os.environ", {
            "RELEASE_CHANNEL": "main", "INTEGRATION_TAG": "integration-123-1",
        }), patch.object(integration, "verify_checkout", side_effect=ValueError("wrong snapshot")), patch.object(session, "command") as command:
            with self.assertRaisesRegex(ValueError, "wrong snapshot"):
                delivery.build()
            command.assert_not_called()

    def test_build_manifest_and_channel_use_the_tested_integration(self):
        snapshot = {"integration_tag": "integration-123-1", "root_sha": "a" * 40,
                    "sources": {name: "b" * 40 for name in integration.COMPONENTS}}
        registry = f"{session.REGION}-docker.pkg.dev/demo-project/nexoruta"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / "bundle.tar.gz"
            bundle.write_bytes(b"bundle")
            outputs = root / "outputs"

            def command(*args, **kwargs):
                if args[1:3] == ("builds", "submit"):
                    config = json.loads(Path(next(a.split("=", 1)[1] for a in args if a.startswith("--config="))).read_text())
                    self.images = config["images"]
                    return json.dumps({"id": "build-123"})
                if args[1:3] == ("builds", "describe"):
                    return json.dumps({"status": "SUCCESS", "results": {"images": [
                        {"name": image, "digest": "sha256:" + "c" * 64} for image in self.images]}})
                if args[:3] == ("gcloud", "storage", "cp"):
                    self.assertIn("--if-generation-match=0", args)
                return ""

            with (patch.object(session, "configuration", return_value={"GCP_PROJECT_ID": "demo-project"}),
                  patch.object(delivery, "ROOT", root), patch.object(delivery, "stage_sources"),
                  patch.object(delivery, "create_bundle", return_value=bundle),
                  patch.object(integration, "verify_checkout", return_value=snapshot),
                  patch.object(session, "command", side_effect=command) as calls,
                  patch.object(delivery.publication, "promote", return_value=True) as promote,
                  patch.dict("os.environ", {"RELEASE_CHANNEL": "main", "INTEGRATION_TAG": snapshot["integration_tag"],
                                            "GITHUB_RUN_NUMBER": "20", "GITHUB_RUN_ATTEMPT": "2",
                                            "GITHUB_OUTPUT": str(outputs)})):
                delivery.build()
                manifest = json.loads((root / "release.json").read_text())
                self.assertEqual(manifest["root_sha"], snapshot["root_sha"])
                self.assertEqual(manifest["sources"], snapshot["sources"])
                self.assertEqual(manifest["integration_tag"], snapshot["integration_tag"])
                self.assertEqual(manifest["publication_order"], [20, 2])
                self.assertTrue(all(image.startswith(registry) and "@sha256:" in image for image in manifest["images"].values()))
                self.assertEqual(promote.call_args.args[1]["integration_tag"], snapshot["integration_tag"])
                self.assertFalse(any(call.args[0] == "git" for call in calls.call_args_list))
                self.assertIn("manifest=", outputs.read_text())

    def test_channel_tag_and_manifest_must_match(self):
        manifest = self.release_manifest()
        manifest.update(integration_tag="integration-123-1", root_sha="a" * 40,
                        sources={name: "b" * 40 for name in integration.COMPONENTS}, publication_order=[20, 1])
        pointer = {"channel": "main", "release": manifest["release"],
                   "integration_tag": "integration-123-2", "publication_order": [20, 1]}
        with patch.object(session, "command", side_effect=[json.dumps(pointer), json.dumps(manifest)]):
            with self.assertRaisesRegex(ValueError, "snapshot"):
                delivery.latest_release({"GCP_PROJECT_ID": "demo-project"})

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
