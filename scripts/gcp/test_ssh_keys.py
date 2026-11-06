import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ssh_keys


class SSHKeyLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.project = "demo-project"
        self.identity = f"nexoruta-demo-deployer@{self.project}.iam.gserviceaccount.com"
        self.enterContext(patch.dict(os.environ, {
            "GITHUB_ACTIONS": "true", "GCP_DEPLOY_SERVICE_ACCOUNT": self.identity,
        }))

    def test_cleanup_without_a_local_key_does_not_require_cloud_credentials(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(ssh_keys.session, "command") as command:
            ssh_keys.cleanup(self.project, Path(temp) / "missing.pub")
        command.assert_not_called()

    def test_cleanup_removes_only_this_runners_key_even_if_its_comment_changed(self):
        keys = {
            "own": {"key": "ssh-rsa own-material server-comment"},
            "other": {"key": "ssh-rsa another-material runner@runnervmother"},
        }
        with tempfile.TemporaryDirectory() as temp:
            key = Path(temp) / "runner.pub"
            key.write_text("ssh-rsa own-material runner@runnervmcurrent\n")
            with patch.object(ssh_keys.session, "command", return_value=json.dumps({"sshPublicKeys": keys})) as command:
                ssh_keys.cleanup(self.project, key)
        removals = [c.args for c in command.call_args_list if "remove" in c.args]
        self.assertEqual(len(removals), 1)
        self.assertIn("--key=own", removals[0])
        self.assertIn("--project=demo-project", removals[0])

    def test_cleanup_after_a_failed_key_import_preserves_every_registered_key(self):
        with tempfile.TemporaryDirectory() as temp:
            key = Path(temp) / "runner.pub"
            key.write_text("ssh-rsa not-imported runner@runnervmcurrent\n")
            with (patch.object(ssh_keys, "profile", return_value={
                    "other": {"key": "ssh-rsa other-material admin@laptop"},
                  }), patch.object(ssh_keys, "remove") as remove):
                ssh_keys.cleanup(self.project, key)
        remove.assert_not_called()

    def test_repair_removes_only_unbounded_legacy_hosted_runner_keys(self):
        keys = {
            "old": {"key": "ssh-rsa old runner@runnervmnwato"},
            "old-zero": {"key": "ssh-rsa old2 runner@fv-az123-456", "expirationTimeUsec": "0"},
            "bounded": {"key": "ssh-rsa bounded runner@runnervmcurrent", "expirationTimeUsec": "9999999999999999"},
            "personal": {"key": "ssh-rsa personal user@laptop"},
            "unknown": {"key": "ssh-rsa unknown runner@custom-machine"},
            "no-comment": {"key": "ssh-rsa no-comment"},
        }
        with (patch.object(ssh_keys.session, "command", return_value=self.identity),
              patch.object(ssh_keys, "profile", return_value=keys),
              patch.object(ssh_keys, "remove") as remove):
            ssh_keys.repair(self.project)
        self.assertEqual([c.args for c in remove.call_args_list], [
            (self.project, "old"), (self.project, "old-zero"),
        ])

    def test_repair_rejects_human_or_mismatched_identities_before_reading_profile(self):
        for identity in ("user@example.test", "another@demo-project.iam.gserviceaccount.com"):
            with (self.subTest(identity=identity),
                  patch.object(ssh_keys.session, "command", return_value=identity),
                  patch.object(ssh_keys, "profile") as profile):
                with self.assertRaisesRegex(ValueError, "active gcloud identity"):
                    ssh_keys.repair(self.project)
                profile.assert_not_called()
        with (patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}),
              patch.object(ssh_keys.session, "command") as command):
            with self.assertRaisesRegex(ValueError, "restricted"):
                ssh_keys.repair(self.project)
            command.assert_not_called()
