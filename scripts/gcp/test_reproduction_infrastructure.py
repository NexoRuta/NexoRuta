"""Static contract checks for the disposable project ownership module."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "infra/gcp/reproduction-project"


class ReproductionInfrastructureTests(unittest.TestCase):
    def test_project_deletion_policy_is_explicit_and_scoped_to_the_disposable_project(self):
        source = (MODULE / "main.tf").read_text(encoding="utf-8")
        project = re.search(r'resource "google_project" "reproduction" \{(.*?)\n\}', source, re.S)
        self.assertIsNotNone(project)
        self.assertRegex(project.group(1), r'deletion_policy\s*=\s*"DELETE"')
        self.assertRegex(project.group(1), r'project_id\s*=\s*var\.project_id')
        self.assertIn('nfr14_owner = "nfr-14"', project.group(1))
        self.assertNotIn("prevent_destroy", project.group(1))

    def test_budget_is_project_filtered_and_removed_with_the_same_external_state(self):
        source = (MODULE / "main.tf").read_text(encoding="utf-8")
        budget = re.search(r'resource "google_billing_budget" "reproduction" \{(.*?)\n\}', source, re.S)
        self.assertIsNotNone(budget)
        for required in (
            'billing_account = var.billing_account_id',
            'projects               = ["projects/${data.google_project.reproduction.number}"]',
            'credit_types_treatment = "EXCLUDE_ALL_CREDITS"',
            'currency_code = "USD"',
            "depends_on = [google_project.reproduction]",
            "threshold_percent = 0.5", "threshold_percent = 0.8", "threshold_percent = 1.0",
        ):
            self.assertIn(required, budget.group(1))

    def test_module_pins_provider_and_uses_no_implicit_default_project_or_billing_account(self):
        source = (MODULE / "main.tf").read_text(encoding="utf-8")
        self.assertIn('required_version = "= 1.13.1"', source)
        self.assertIn('version = "= 7.46.1"', source)
        self.assertIn("billing_project       = var.control_project_id", source)
        self.assertIn("user_project_override = true", source)
        self.assertRegex(source, r'project_id\s*=\s*var\.project_id')
        self.assertIn('regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.control_project_id)', source)
        self.assertIn("billing_account = var.billing_account_id", source)
        self.assertIn('regex("^(organizations|folders)/[0-9]+$", var.parent)', source)
        self.assertIn('regex("^[A-Z0-9-]{6,30}$", var.billing_account_id)', source)
        self.assertNotIn("data.google_client_config", source)
        lock = (MODULE / ".terraform.lock.hcl").read_text(encoding="utf-8")
        self.assertIn('version     = "7.46.1"', lock)
        self.assertIn('registry.opentofu.org/hashicorp/google"', lock)
        self.assertNotIn('registry.opentofu.org/hashicorp/google-beta"', lock)


if __name__ == "__main__":
    unittest.main()
