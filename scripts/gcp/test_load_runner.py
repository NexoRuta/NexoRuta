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

    def test_fixture_capacity_fails_with_profile_requirements_before_cloud_calls(self):
        fixture = {"fixtureStatus": "ready", "accounts": [{"email": "a@nexoruta.test"}]}
        with self.assertRaisesRegex(ValueError, "Profile stress requires 50.*fixture contains 1"):
            runner.validate_fixture_accounts("stress", fixture, {"vus": 50})

    def test_preparing_fixture_is_rejected_before_any_load_traffic(self):
        fixture = {"fixtureStatus": "preparing", "accounts": [{"email": "a@nexoruta.test"}]}
        with self.assertRaisesRegex(ValueError, "fixture is not ready"):
            runner.validate_fixture_accounts("smoke", fixture, {"vus": 1})

    def test_sync_dataset_validates_only_active_journeys_and_allows_unused_prepared_rows(self):
        accounts = [{"jornadaId": "00000000-0000-4000-8000-000000000001"}]
        events = [{"id": f"10000000-0000-4000-8000-{index + 1:012x}",
                   "secuencia": index + 2, "tipo": "Posicion", "ocurridaEn": "2026-11-05T00:00:00Z",
                   "envioId": None, "versionEnvio": None} for index in range(50)]
        operations = {accounts[0]["jornadaId"]: events,
                      "00000000-0000-4000-8000-000000000002": events}

        runner.validate_sync_dataset(accounts, operations)

    def test_sync_dataset_rejects_a_missing_active_journey_before_traffic(self):
        with self.assertRaisesRegex(ValueError, "missing an active VU journey"):
            runner.validate_sync_dataset(
                [{"jornadaId": "00000000-0000-4000-8000-000000000001"}], {})

    def test_sync_dataset_rejects_replayed_ids_shared_between_active_journeys(self):
        first = "00000000-0000-4000-8000-000000000001"
        second = "00000000-0000-4000-8000-000000000002"
        events = [{"id": f"10000000-0000-4000-8000-{index + 1:012x}",
                   "secuencia": index + 2, "tipo": "Posicion", "ocurridaEn": "2026-11-05T00:00:00Z",
                   "envioId": None, "versionEnvio": None} for index in range(50)]
        with self.assertRaisesRegex(ValueError, "invalid position sequence"):
            runner.validate_sync_dataset([{"jornadaId": first}, {"jornadaId": second}],
                                         {first: events, second: events})


if __name__ == "__main__":
    unittest.main()
