"""Exercise the PowerShell helper against a native argv receiver, without deploying."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


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
        self.shell = shutil.which("powershell.exe") or shutil.which("pwsh")
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


if __name__ == "__main__":
    unittest.main()
