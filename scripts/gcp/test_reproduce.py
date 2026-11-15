"""Safety checks for isolated NFR-14 reproduction targets and CI evidence inputs."""

from contextlib import nullcontext
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import reproduce


class ReproductionTargetTests(unittest.TestCase):
    def setUp(self):
        self.run_id = "0123456789abcdef0123456789abcdef"
        self.project_id = reproduce.project_id_for_run(self.run_id)
        self.project_number = "1234567890123"
        self.tag = "integration-100-2"
        self.environment = {
            "NFR14_REPRO_RUN_ID": self.run_id,
            "NFR14_REPRO_INTEGRATION_TAG": self.tag,
            "NFR14_REPRO_PROJECT_ID": self.project_id,
            "NFR14_REPRO_PROJECT_NUMBER": self.project_number,
            "NFR14_REPRO_STATE_BUCKET": f"{self.project_id}-tofu-state",
            "NFR14_REPRO_DELIVERY_BUCKET": f"{self.project_id}-nexoruta-delivery",
            "NFR14_REPRO_WORKLOAD_IDENTITY_PROVIDER": (
                f"projects/{self.project_number}/locations/global/workloadIdentityPools/"
                "nexoruta-github/providers/demo-vm"
            ),
            "NFR14_REPRO_DEPLOY_SERVICE_ACCOUNT": (
                f"nexoruta-demo-deployer@{self.project_id}.iam.gserviceaccount.com"
            ),
            "NFR14_MAIN_PROJECT_ID": "nexoruta-demo-20261022",
            "NFR14_MAIN_STATE_BUCKET": "nexoruta-demo-20261022-tofu-state",
            "NFR14_MAIN_DELIVERY_BUCKET": "nexoruta-demo-20261022-nexoruta-delivery",
            "NFR14_MAIN_WORKLOAD_IDENTITY_PROVIDER": (
                "projects/1090571196455/locations/global/workloadIdentityPools/"
                "nexoruta-github/providers/demo-vm"
            ),
            "NFR14_MAIN_DEPLOY_SERVICE_ACCOUNT": (
                "nexoruta-demo-deployer@nexoruta-demo-20261022.iam.gserviceaccount.com"
            ),
            "NEXORUTA_EXECUTION_PROFILE": "reproduction",
            "BOOTSTRAP_WIF_PROFILE": "reproduction",
            "GCP_PROJECT_ID": self.project_id,
            "GCP_REGION": reproduce.REGION,
            "GCP_ZONE": reproduce.ZONE,
            "GCP_SECONDARY_ZONE": reproduce.SECONDARY_ZONE,
            "GCP_STATE_BUCKET": f"{self.project_id}-tofu-state",
            "GCP_DELIVERY_BUCKET": f"{self.project_id}-nexoruta-delivery",
            "GCP_WORKLOAD_IDENTITY_PROVIDER": (
                f"projects/{self.project_number}/locations/global/workloadIdentityPools/"
                "nexoruta-github/providers/demo-vm"
            ),
            "GCP_DEPLOY_SERVICE_ACCOUNT": (
                f"nexoruta-demo-deployer@{self.project_id}.iam.gserviceaccount.com"
            ),
            "GCP_BASE_DOMAIN": "",
            "GCP_MANAGE_DNS": "false",
        }

    def test_target_is_derived_from_run_and_all_mapped_values_match(self):
        target = reproduce.validate_runtime_environment(
            self.environment, input_run_id=self.run_id, input_tag=self.tag,
        )
        self.assertEqual(target["project_id"], self.project_id)
        self.assertEqual(target["state_bucket"], self.project_id + "-tofu-state")
        self.assertEqual(target["delivery_bucket"], self.project_id + "-nexoruta-delivery")

    def test_github_dispatch_context_is_limited_to_main_reproduction_workflow(self):
        self.environment.update({
            "GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": reproduce.REPOSITORY,
            "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_WORKFLOW_REF": reproduce.WORKFLOW_REF,
        })
        reproduce.validate_runtime_environment(self.environment, input_run_id=self.run_id, input_tag=self.tag)
        for key, value in (
            ("GITHUB_REF", "refs/heads/develop"),
            ("GITHUB_EVENT_NAME", "push"),
            ("GITHUB_WORKFLOW_REF", "NexoRuta/NexoRuta/.github/workflows/vm-controls.yml@refs/heads/main"),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "only valid"):
                changed = {**self.environment, key: value}
                reproduce.validate_runtime_environment(changed, input_run_id=self.run_id, input_tag=self.tag)

    def test_rejects_wrong_run_or_tag_and_nonreproduction_profile(self):
        cases = (
            (self.environment, "f" * 32, self.tag),
            (self.environment, self.run_id, "integration-100-3"),
            ({**self.environment, "NEXORUTA_EXECUTION_PROFILE": "demo"}, self.run_id, self.tag),
            ({**self.environment, "BOOTSTRAP_WIF_PROFILE": "demo"}, self.run_id, self.tag),
        )
        for environment, run_id, tag in cases:
            with self.subTest(run_id=run_id, tag=tag), self.assertRaises(ValueError):
                reproduce.validate_runtime_environment(environment, input_run_id=run_id, input_tag=tag)

    def test_rejects_any_mixed_or_main_project_resource_identity(self):
        altered_values = (
            ("NFR14_REPRO_PROJECT_ID", self.environment["NFR14_MAIN_PROJECT_ID"]),
            ("NFR14_REPRO_STATE_BUCKET", self.environment["NFR14_MAIN_STATE_BUCKET"]),
            ("NFR14_REPRO_DELIVERY_BUCKET", self.environment["NFR14_MAIN_DELIVERY_BUCKET"]),
            ("NFR14_REPRO_WORKLOAD_IDENTITY_PROVIDER", self.environment["NFR14_MAIN_WORKLOAD_IDENTITY_PROVIDER"]),
            ("NFR14_REPRO_DEPLOY_SERVICE_ACCOUNT", self.environment["NFR14_MAIN_DEPLOY_SERVICE_ACCOUNT"]),
            ("GCP_PROJECT_ID", self.environment["NFR14_MAIN_PROJECT_ID"]),
            ("GCP_STATE_BUCKET", self.environment["NFR14_MAIN_STATE_BUCKET"]),
            ("GCP_DELIVERY_BUCKET", self.environment["NFR14_MAIN_DELIVERY_BUCKET"]),
        )
        for key, value in altered_values:
            with self.subTest(key=key), self.assertRaises(ValueError):
                reproduce.validate_runtime_environment({**self.environment, key: value})

    def test_rejects_dns_reuse_wrong_region_and_non_main_channel(self):
        for key, value in (
            ("GCP_BASE_DOMAIN", "demo.example.invalid"),
            ("GCP_MANAGE_DNS", "true"),
            ("GCP_REGION", "us-central1"),
            ("GCP_ZONE", "southamerica-west1-b"),
            ("RELEASE_CHANNEL", "develop"),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                reproduce.validate_runtime_environment({**self.environment, key: value})

    def test_project_derivation_accepts_only_full_unique_ids(self):
        self.assertEqual(reproduce.project_id_for_run(self.run_id), self.project_id)
        for invalid in ("", "short", "A" * 32, "0" * 31, "0" * 33):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                reproduce.project_id_for_run(invalid)

    def test_evidence_directory_must_be_empty_and_outside_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary) / "evidence"
            self.assertEqual(reproduce._prepare_evidence_directory(evidence), evidence.resolve())
            (evidence / "existing.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be empty"):
                reproduce._prepare_evidence_directory(evidence)
            (evidence / "existing.json").unlink()
            evidence.rmdir()

        repository = Path(reproduce.__file__).resolve().parents[2]
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            reproduce._prepare_evidence_directory(repository / "local-evidence")


class ReproductionCleanupTests(unittest.TestCase):
    def test_github_variables_are_deleted_with_github_token_after_project_deletion(self):
        run_id = "0123456789abcdef0123456789abcdef"
        project_id = reproduce.project_id_for_run(run_id)
        tag = "integration-100-2"
        project = {"project_id": project_id}
        profile = {"project_id": project_id}
        inventory = {
            "run_id": run_id, "project_id": project_id, "integration_tag": tag,
            "status": "project_deletion_requested", "project": project,
        }
        objects = object()
        lock = Mock()
        expected_variables = {name: f"value-{index}"
                              for index, name in enumerate(reproduce.VARIABLE_NAMES)}
        delete_variables = Mock()
        with (
            patch.object(reproduce, "_load_inventory_context",
                         return_value=("gcp-access-token", objects, "1", inventory, profile)),
            patch.object(reproduce, "_locked_control", return_value=nullcontext(lock)),
            patch.object(reproduce, "_read_inventory", return_value=("1", inventory)),
            patch.object(reproduce, "_inventory_profile", return_value=profile),
            patch.object(reproduce, "_verify_deletion_requested"),
            patch.object(reproduce, "_github_token", return_value="github-access-token"),
            patch.object(reproduce, "_reproduction_variables", return_value=expected_variables),
            patch.object(reproduce, "_delete_reproduction_variables", delete_variables),
            patch.object(reproduce, "_inventory_update", return_value=("2", inventory)),
        ):
            result = reproduce.destroy(
                run_id=run_id, control_project_id="control-project",
                control_bucket="control-bucket", confirm_project=project_id,
            )

        self.assertEqual(result["status"], "destroyed")
        delete_variables.assert_called_once_with("github-access-token", expected_variables)


if __name__ == "__main__":
    unittest.main()
