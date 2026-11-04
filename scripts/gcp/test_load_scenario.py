"""Execute the actual k6 scenario against controlled HTTP and clock doubles."""

from pathlib import Path
import shutil
import subprocess
import unittest


class LoadScenarioTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is required for the scenario harness")
    def test_setup_warmup_and_measurement_contract(self):
        result = subprocess.run(
            ["node", "--experimental-vm-modules", "--test",
             str(Path(__file__).with_name("load_scenario_test.mjs"))],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
