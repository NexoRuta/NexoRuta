"""Safe diagnostics for remote load-runner failures."""

from pathlib import Path
import sys
import unittest
import urllib.error


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deploy" / "load"))
import runner


class LoadRunnerDiagnosticTests(unittest.TestCase):
    def test_http_error_includes_status_and_endpoint_but_not_query_parameters(self):
        error = urllib.error.HTTPError(
            "https://api.example.test/health/ready?access_token=private",
            403, "Forbidden", {}, None,
        )

        message = runner.safe_http_error(error)

        self.assertEqual(
            "Load test failed safely: HTTPError status=403 endpoint=api.example.test/health/ready",
            message,
        )
        self.assertNotIn("access_token", message)
        self.assertNotIn("private", message)


if __name__ == "__main__":
    unittest.main()
