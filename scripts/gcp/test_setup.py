"""Exercise the PowerShell helper against a native argv receiver, without deploying."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import bootstrap
import bootstrap_setup
import infra_safety

HARNESS = r"""
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $env:NEXORUTA_TEST_SETUP, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw 'setup.ps1 contains PowerShell syntax errors' }
$helper = $ast.Find({param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -eq 'Invoke-Tool'
}, $true)
if (!$helper) { throw 'Invoke-Tool is missing' }
. ([scriptblock]::Create($helper.Extent.Text))
$probeHelper = $ast.Find({param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -eq 'Test-Tool'
}, $true)
if ($probeHelper) { . ([scriptblock]::Create($probeHelper.Extent.Text)) }
$cases = ConvertFrom-Json $env:NEXORUTA_TEST_ARGUMENTS
foreach ($case in $cases) {
    $arguments = @($env:NEXORUTA_TEST_PROBE) + @($case.arguments)
    if ($env:NEXORUTA_TEST_MODE -eq 'probe') {
        Test-Tool -Name $env:NEXORUTA_TEST_PYTHON -Arguments $arguments -NotFoundOnly
    } else {
        Invoke-Tool -Name $env:NEXORUTA_TEST_PYTHON -Arguments $arguments
        Invoke-Tool $env:NEXORUTA_TEST_PYTHON $arguments
    }
}
"""


class SetupPowerShellTests(unittest.TestCase):
    def setUp(self):
        self.shell = shutil.which("pwsh")
        if os.name == "nt":
            self.shell = shutil.which("powershell.exe") or self.shell
        if not self.shell:
            self.skipTest("PowerShell is unavailable")
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory(prefix="nexoruta argv ")))
        self.probe = self.directory / "argv probe.py"
        self.probe.write_text(
            "import json, sys\n"
            "if sys.argv[1:] == ['--fail']: sys.exit(7)\n"
            "if sys.argv[1:] == ['--not-found']: print('Not found: 404', file=sys.stderr); sys.exit(1)\n"
            "if sys.argv[1:] == ['--denied']: print('Permission denied: 403', file=sys.stderr); sys.exit(1)\n"
            "print(json.dumps(sys.argv[1:]))\n",
            encoding="utf-8",
        )

    def invoke(self, cases, mode="invoke"):
        environment = dict(os.environ, NEXORUTA_TEST_SETUP=str(Path(__file__).with_name("setup.ps1")),
                           NEXORUTA_TEST_PROBE=str(self.probe), NEXORUTA_TEST_PYTHON=sys.executable,
                           NEXORUTA_TEST_ARGUMENTS=json.dumps([{"arguments": case} for case in cases]),
                           NEXORUTA_TEST_MODE=mode)
        return subprocess.run([self.shell, "-NoProfile", "-NonInteractive", "-Command", HARNESS],
                              env=environment, capture_output=True, text=True, timeout=30)

    def test_argument_arrays_preserve_subcommands_spaces_and_empty_option_values(self):
        cases = [
            ["config", "set", "project", "nexoruta-demo-20261022"],
            ["-chdir=C:\\Nexo Ruta\\infra", "init", "-backend-config=prefix=foundation"],
            ["variable", "set", "GCP_BASE_DOMAIN", "--body="],
        ]
        result = self.invoke(cases)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([json.loads(line) for line in result.stdout.splitlines()],
                         [case for case in cases for _ in range(2)])

    def test_failed_native_command_stops_the_script(self):
        result = self.invoke([["--fail"]])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed with exit code 7", result.stderr)

    def test_missing_remote_state_is_expected_but_permission_failure_is_not(self):
        result = self.invoke([["--not-found"], ["valid-state"]], mode="probe")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["False", "True"])
        self.assertEqual(result.stderr, "")
        denied = self.invoke([["--denied"]], mode="probe")
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("Could not inspect remote state", denied.stderr)


class BootstrapSetupValidationTests(unittest.TestCase):
    def setUp(self):
        self.project_id = "nexoruta-demo-20261022"
        self.repository = {
            "full_name": "NexoRuta/NexoRuta", "id": 1406504463,
            "owner": {"login": "NexoRuta", "id": 338352981},
        }
        self.project = {"projectId": self.project_id, "projectNumber": "123456789", "lifecycleState": "ACTIVE"}
        self.bucket = {"name": self.project_id + "-tofu-state", "projectNumber": "123456789",
                       "location": "SOUTHAMERICA-WEST1"}

    def test_bootstrap_profile_requires_explicit_project_repo_environment_and_prefix(self):
        bootstrap_setup.validate_profile(self.project_id, "NexoRuta/NexoRuta", "nexoruta-demo",
                                         "southamerica-west1", self.bucket["name"], "foundation")
        invalid = (
            (self.project_id, "NexoRuta/NexoRuta", "nexoruta-demo", "southamerica-west1",
             "unrelated-bucket", "foundation"),
            (self.project_id, "other/repo", "nexoruta-demo", "southamerica-west1", self.bucket["name"], "foundation"),
            (self.project_id, "NexoRuta/NexoRuta", "other-environment", "southamerica-west1", self.bucket["name"], "foundation"),
            (self.project_id, "NexoRuta/NexoRuta", "nexoruta-demo", "southamerica-west1", self.bucket["name"], "other-prefix"),
        )
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(ValueError):
                bootstrap_setup.validate_profile(*args)

    def test_destination_requires_project_number_bucket_owner_and_stable_github_ids(self):
        self.assertEqual(bootstrap_setup.validate_destination(
            self.project, self.bucket, self.repository, project_id=self.project_id,
            repository_id=1406504463, owner_id=338352981,
        ), "123456789")
        for bucket, repository in (
            ({**self.bucket, "projectNumber": "9"}, self.repository),
            (self.bucket, {**self.repository, "id": 9}),
            (self.bucket, {**self.repository, "owner": {"login": "other", "id": 338352981}}),
        ):
            with self.subTest(bucket=bucket, repository=repository), self.assertRaises(ValueError):
                bootstrap_setup.validate_destination(
                    self.project, bucket, repository, project_id=self.project_id,
                    repository_id=1406504463, owner_id=338352981,
                )

    def test_quota_validation_uses_available_general_region_cpus(self):
        self.assertEqual(bootstrap_setup.validate_quota([{"metric": "CPUS", "limit": 20, "usage": 2}]), 18)
        for quotas in (
            [{"metric": "CPUS", "limit": 12, "usage": 1}],
            [{"metric": "N2_CPUS", "limit": 20, "usage": 0}],
            [{"metric": "CPUS", "limit": "unknown", "usage": 0}],
        ):
            with self.subTest(quotas=quotas), self.assertRaises(ValueError):
                bootstrap_setup.validate_quota(quotas)

    def test_only_a_404_state_probe_is_treated_as_absent(self):
        import subprocess
        not_found = subprocess.CompletedProcess([], 1, "", "Not found: 404")
        denied = subprocess.CompletedProcess([], 1, "", "Permission denied: 403")
        with patch.object(bootstrap_setup.subprocess, "run", return_value=not_found):
            self.assertIsNone(bootstrap_setup._run("gcloud", "storage", "objects", "describe", "missing",
                                                   capture=True, allow_not_found=True))
        with patch.object(bootstrap_setup.subprocess, "run", return_value=denied):
            with self.assertRaisesRegex(RuntimeError, "exit code 1"):
                bootstrap_setup._run("gcloud", "storage", "objects", "describe", "private",
                                     capture=True, allow_not_found=True)

    def test_bucket_api_verifies_project_number_and_never_treats_403_as_absent(self):
        import urllib.error
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"name":"state-bucket","projectNumber":"123","location":"SOUTHAMERICA-WEST1"}'
        with (patch.object(bootstrap_setup, "_run", return_value="private-token"),
              patch.object(bootstrap_setup.urllib.request, "urlopen", return_value=response) as urlopen):
            bucket = bootstrap_setup._storage_bucket_info("state-bucket")
        self.assertEqual(bucket["projectNumber"], "123")
        self.assertEqual(urlopen.call_args.args[0].get_header("Authorization"), "Bearer private-token")
        with (patch.object(bootstrap_setup, "_run", return_value="private-token"),
              patch.object(bootstrap_setup.urllib.request, "urlopen",
                           side_effect=urllib.error.HTTPError("url", 403, "Forbidden", {}, None))):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
                bootstrap_setup._storage_bucket_info("state-bucket", allow_not_found=True)

    def test_state_identity_checks_the_exact_project_and_immutable_wif_profile(self):
        repository_id, owner_id = "1406504463", "338352981"
        subject = f"repo:NexoRuta@{owner_id}/NexoRuta@{repository_id}:environment:nexoruta-demo"
        workflows = ", ".join(f"'{workflow}'" for workflow in bootstrap_setup.WIF_WORKFLOWS)
        condition = (
            f"assertion.repository_id == '{repository_id}' && "
            f"assertion.repository_owner_id == '{owner_id}' && "
            "assertion.repository == 'NexoRuta/NexoRuta' && "
            "assertion.ref in ['refs/heads/main', 'refs/heads/develop'] && "
            f"assertion.sub == '{subject}' && assertion.workflow_ref in [{workflows}]"
            " && assertion.event_name in ['workflow_dispatch', 'push']"
        )
        state = {"values": {
            "outputs": {
                "bootstrap_configuration": {"value": {
                    "project_id": self.project_id, "project_number": "123456789",
                    "state_bucket": self.bucket["name"],
                    "github_repository": "NexoRuta/NexoRuta", "github_repository_id": repository_id,
                    "github_owner_id": owner_id, "github_environment": "nexoruta-demo",
                    "wif_profile": "demo",
                }},
                "github_variables": {"value": {"GCP_PROJECT_ID": self.project_id}},
            },
            "root_module": {"resources": [
                {"type": "google_storage_bucket", "name": "state", "values": {
                    "project": self.project_id, "name": self.bucket["name"],
                }},
                {"type": "google_iam_workload_identity_pool_provider", "name": "github", "values": {
                    "name": "projects/123456789/locations/global/workloadIdentityPools/nexoruta-github/providers/demo-vm",
                    "attribute_condition": condition,
                }},
            ]},
        }}
        identity = {"project_id": self.project_id, "project_number": "123456789",
                    "bucket_name": self.bucket["name"],
                    "repository": "NexoRuta/NexoRuta", "repository_id": repository_id, "owner_id": owner_id}
        bootstrap_setup.validate_state_identity(state, **identity, require_complete=True,
                                                require_current_subject=True)
        altered = json.loads(json.dumps(state))
        altered["values"]["root_module"]["resources"][1]["values"]["attribute_condition"] = condition.replace(
            f"assertion.sub == '{subject}'", f"assertion.sub in ['repo:NexoRuta/NexoRuta:environment:nexoruta-demo', '{subject}']",
        )
        with self.assertRaisesRegex(ValueError, "WIF trust profile"):
            bootstrap_setup.validate_state_identity(altered, **identity, require_current_subject=True)

    def test_reproduction_wif_profile_is_limited_to_main_dispatch_and_one_workflow(self):
        profile = bootstrap_setup.WIF_PROFILES["reproduction"]
        condition = bootstrap_setup.expected_wif_condition(
            "1406504463", "338352981", "NexoRuta/NexoRuta", profile="reproduction",
        )
        self.assertEqual(profile["environment"], "nexoruta-demo")
        self.assertEqual(profile["refs"], ("refs/heads/main",))
        self.assertEqual(profile["events"], ("workflow_dispatch",))
        self.assertEqual(profile["workflows"], (
            "NexoRuta/NexoRuta/.github/workflows/reproduce.yml@refs/heads/main",
        ))
        self.assertIn("assertion.ref in ['refs/heads/main']", condition)
        self.assertIn("assertion.event_name in ['workflow_dispatch']", condition)
        self.assertNotIn("vm-controls.yml", condition)
        self.assertNotIn("develop", condition)

        state = {"values": {
            "outputs": {"bootstrap_configuration": {"value": {
                "project_id": self.project_id, "state_bucket": self.bucket["name"],
            "project_number": "123456789",
                "github_repository": "NexoRuta/NexoRuta", "github_repository_id": "1406504463",
                "github_owner_id": "338352981", "github_environment": "nexoruta-demo",
                "wif_profile": "reproduction",
            }}, "github_variables": {"value": {"GCP_PROJECT_ID": self.project_id}}},
            "root_module": {"resources": [
                {"type": "google_storage_bucket", "name": "state", "values": {
                    "project": self.project_id, "name": self.bucket["name"],
                }},
                {"type": "google_iam_workload_identity_pool_provider", "name": "github", "values": {
                    "name": "projects/123456789/locations/global/workloadIdentityPools/nexoruta-github/providers/demo-vm",
                    "attribute_condition": condition,
                }},
            ]},
        }}
        bootstrap_setup.validate_state_identity(
            state, project_id=self.project_id, bucket_name=self.bucket["name"],
            project_number="123456789",
            repository="NexoRuta/NexoRuta", repository_id="1406504463", owner_id="338352981",
            require_complete=True, require_current_subject=True, wif_profile="reproduction",
        )
        with self.assertRaisesRegex(ValueError, "different WIF profile"):
            bootstrap_setup.validate_state_identity(
                state, project_id=self.project_id, bucket_name=self.bucket["name"],
                project_number="123456789",
                repository="NexoRuta/NexoRuta", repository_id="1406504463", owner_id="338352981",
                require_current_subject=True, wif_profile="demo",
            )

    def test_shared_plan_gate_rejects_destruction_and_preserves_only_abandon_rotation(self):
        create = {"resource_changes": [{"address": "service", "change": {"actions": ["create"]}}]}
        infra_safety.check_plan(create, "bootstrap")
        deletion = {"resource_changes": [{"address": "disk", "change": {"actions": ["delete"]}}]}
        for operation in ("bootstrap", "start", "update", "stop"):
            with self.subTest(operation=operation), self.assertRaisesRegex(RuntimeError, "deletes/replaces|delete or replace"):
                infra_safety.check_plan(deletion, operation)
        replacement = {"resource_changes": [{
            "address": "secret.version", "type": "google_secret_manager_secret_version",
            "change": {"actions": ["delete", "create"],
                       "before": {"deletion_policy": "ABANDON"}, "after": {"deletion_policy": "ABANDON"}},
        }]}
        infra_safety.check_plan(replacement, "start")
        infra_safety.check_plan(replacement, "bootstrap")
        with self.assertRaisesRegex(RuntimeError, "must not create"):
            infra_safety.check_plan(replacement, "stop")
        with self.assertRaisesRegex(RuntimeError, "must not create"):
            infra_safety.check_plan(create, "stop")
        with self.assertRaisesRegex(RuntimeError, "invalid plan"):
            infra_safety.check_plan(None, "update")

    def test_legacy_mobile_secret_migration_forgets_state_without_deleting_version(self):
        state = {"values": {"root_module": {"resources": [{
            "address": "google_secret_manager_secret_version.mobile",
            "type": "google_secret_manager_secret_version",
            "name": "mobile",
            "values": {
                "id": "projects/1090571196455/secrets/nexoruta-mobile-config/versions/1",
                "secret": "projects/nexoruta-demo-20261022/secrets/nexoruta-mobile-config",
                "deletion_policy": "DELETE",
            },
        }]}}}
        tofu = ("tofu", "-chdir=infra/gcp/bootstrap")
        with patch.object(bootstrap, "command") as execute:
            self.assertTrue(bootstrap.detach_legacy_mobile_config_version(tofu, state))
        execute.assert_called_once_with(
            *tofu, "state", "rm", "-lock-timeout=5m",
            "google_secret_manager_secret_version.mobile",
        )

        wrong_secret = json.loads(json.dumps(state))
        wrong_secret["values"]["root_module"]["resources"][0]["values"]["secret"] = (
            "projects/nexoruta-demo-20261022/secrets/another-secret"
        )
        with patch.object(bootstrap, "command") as execute:
            with self.assertRaisesRegex(RuntimeError, "unexpected Secret Manager"):
                bootstrap.detach_legacy_mobile_config_version(tofu, wrong_secret)
        execute.assert_not_called()

    def test_bootstrap_wif_condition_uses_only_the_verified_immutable_subject(self):
        main_tf = (Path(__file__).resolve().parents[2] / "infra/gcp/bootstrap/main.tf").read_text(encoding="utf-8")
        self.assertIn('"assertion.sub ==', main_tf)
        self.assertNotIn("assertion.sub in [", main_tf)
        self.assertNotIn("repo:${var.github_repository}:environment:nexoruta-demo", main_tf)


if __name__ == "__main__":
    unittest.main()
