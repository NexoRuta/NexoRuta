"""Check exact build inputs, supported gcloud arguments and bounded cancellation."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import load_image


ENVIRONMENT = {"GCP_PROJECT_ID": "demo-project", "GCP_REGION": "southamerica-west1",
               "GCP_DELIVERY_BUCKET": "demo-delivery", "GITHUB_SHA": "a" * 40,
               "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}
BUILD_ID = "00000000-0000-4000-8000-000000000001"


class LoadImageTests(unittest.TestCase):
    def inputs(self, root):
        for name in load_image.load_tests.SUITE_SOURCES:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
        (root / ".env").write_text("private-test-credentials")
        (root / ".dockerignore").write_text("**\n")

    def test_context_has_exactly_the_reviewed_sources_and_no_root_ignore_or_credentials(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as staged:
            self.inputs(Path(source))
            load_image.stage_sources(Path(source), Path(staged))
            files = {path.relative_to(staged).as_posix() for path in Path(staged).rglob("*") if path.is_file()}
            self.assertEqual(files, set(load_image.load_tests.SUITE_SOURCES))

    @unittest.skipIf(os.name == "nt", "Symlink creation needs an explicit Windows privilege")
    def test_context_rejects_a_symlink_outside_the_reviewed_sources(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as staged:
            root = Path(source)
            self.inputs(root)
            entry = root / load_image.load_tests.SUITE_SOURCES[0]
            entry.unlink()
            entry.symlink_to(root / ".env")
            with self.assertRaises(ValueError):
                load_image.stage_sources(root, Path(staged))

    def test_cloud_build_uses_config_and_pins_the_published_digest(self):
        with tempfile.TemporaryDirectory() as source:
            self.inputs(Path(source))
            image = None

            def command(*args):
                nonlocal image
                if args[1:3] == ("builds", "submit"):
                    config = Path(next(arg.split("=", 1)[1] for arg in args if arg.startswith("--config=")))
                    value = json.loads(config.read_text())
                    image = value["images"][0]
                    self.assertEqual(value["steps"][0]["args"],
                        ["build", "-t", image, "-f", "tests/load/Dockerfile", "."])
                    self.assertEqual(value["timeout"], "600s")
                    self.assertNotIn("--file", args)
                    return json.dumps({"id": BUILD_ID})
                self.assertEqual(args[1:4], ("builds", "describe", BUILD_ID))
                return json.dumps({"status": "SUCCESS", "results": {"images": [
                    {"name": image, "digest": "sha256:" + "b" * 64}]}})

            with patch.object(load_image, "command", side_effect=command):
                result = load_image.build(ENVIRONMENT, root=Path(source))
            self.assertEqual(result, "southamerica-west1-docker.pkg.dev/demo-project/nexoruta/load-tests@sha256:" + "b" * 64)

    def test_failed_observation_cancels_the_exact_build_instead_of_submitting_another(self):
        with tempfile.TemporaryDirectory() as source:
            self.inputs(Path(source))
            with patch.object(load_image, "command", side_effect=[json.dumps({"id": BUILD_ID}),
                    RuntimeError("controlled status failure"), ""]) as command:
                with self.assertRaises(RuntimeError):
                    load_image.build(ENVIRONMENT, root=Path(source))
            self.assertEqual(command.call_count, 3)
            self.assertEqual(command.call_args.args[1:4], ("builds", "cancel", BUILD_ID))

    def test_build_deadline_cancels_the_remote_build(self):
        with tempfile.TemporaryDirectory() as source:
            self.inputs(Path(source))
            with patch.object(load_image, "command", side_effect=[json.dumps({"id": BUILD_ID}), ""]) as command, \
                    patch.object(load_image.time, "monotonic", side_effect=[0, 661]):
                with self.assertRaisesRegex(RuntimeError, "bounded deadline"):
                    load_image.build(ENVIRONMENT, root=Path(source))
            self.assertEqual(command.call_args.args[1:4], ("builds", "cancel", BUILD_ID))

    def test_invalid_build_inputs_are_rejected_before_any_cloud_request(self):
        with patch.object(load_image, "command") as command:
            with self.assertRaises(ValueError):
                load_image.build({**ENVIRONMENT, "GCP_REGION": "unreviewed-region"})
        command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
