import tempfile
import unittest
from pathlib import Path

import bootstrap


class BootstrapTests(unittest.TestCase):
    def test_generated_gcs_backend_uses_valid_nested_block_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            path = bootstrap.write_backend_file(Path(directory))
            self.assertEqual(
                'terraform {\n  backend "gcs" {}\n}\n',
                path.read_text(encoding="utf-8"),
            )

    def test_existing_optional_budget_is_preserved(self):
        env = dict(GCP_PROJECT_ID="demo-project", GCP_REGION="southamerica-west1",
                   GITHUB_REPOSITORY="NexoRuta/NexoRuta", BOOTSTRAP_REPOSITORY_ID="123",
                   BOOTSTRAP_OWNER_ID="456")
        budget = {"type": "google_billing_budget", "values": {"billing_account": "existing-account"}}
        state = {"values": {"root_module": {"resources": [budget]}}}
        self.assertEqual(bootstrap.settings(env, state)["billing_account_id"], "existing-account")
        self.assertEqual(bootstrap.settings(env, {})["billing_account_id"], "")

    def test_delete_and_replacement_are_rejected_before_apply(self):
        for actions in (["delete"], ["delete", "create"], ["create", "delete"]):
            with self.subTest(actions=actions), self.assertRaises(RuntimeError):
                bootstrap.check_plan({"resource_changes": [
                    {"address": "foundation.resource", "change": {"actions": actions}}]})
        bootstrap.check_plan({"resource_changes": [
            {"address": "foundation.resource", "change": {"actions": ["create"]}}]})

    def test_missing_remote_state_stops_before_initialization(self):
        from unittest.mock import patch
        with patch.dict(bootstrap.os.environ, {"GCP_STATE_BUCKET": "existing-bucket"}), \
             patch.object(bootstrap, "command", side_effect=RuntimeError("missing state")) as command:
            with self.assertRaisesRegex(RuntimeError, "missing state"):
                bootstrap.main()
        self.assertEqual(command.call_count, 1)


if __name__ == "__main__":
    unittest.main()
