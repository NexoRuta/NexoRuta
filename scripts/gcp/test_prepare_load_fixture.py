import base64
import hashlib
import json
import os
import unittest
from contextlib import nullcontext
from unittest.mock import patch

import prepare_load_fixture as prepare


class PrepareLoadFixtureTests(unittest.TestCase):
    def test_secret_read_returns_existing_version_without_listing_versions(self):
        fixture = {"fixtureStatus": "ready", "accounts": []}
        body = json.dumps({
            "name": "projects/demo-project/secrets/nexoruta-load-fixtures/versions/12",
            "payload": {"data": base64.b64encode(json.dumps(fixture).encode()).decode()},
        }).encode()
        with patch.object(prepare, "google_request", return_value=(200, body)) as request:
            actual = prepare.secret_version("token", "demo-project")

        self.assertEqual((fixture, json.dumps(fixture).encode(), "12"), actual)
        self.assertEqual("GET", request.call_args.args[1])

    def test_secret_read_accepts_gcp_canonical_project_number(self):
        fixture = {"fixtureStatus": "ready", "accounts": []}
        body = json.dumps({
            "name": "projects/1090571196455/secrets/nexoruta-load-fixtures/versions/12",
            "payload": {"data": base64.b64encode(json.dumps(fixture).encode()).decode()},
        }).encode()
        with patch.object(prepare, "google_request", return_value=(200, body)):
            actual = prepare.secret_version("token", "demo-project")

        self.assertEqual((fixture, json.dumps(fixture).encode(), "12"), actual)

    def test_secret_read_rejects_a_different_project_id(self):
        body = json.dumps({
            "name": "projects/other-project/secrets/nexoruta-load-fixtures/versions/12",
            "payload": {"data": base64.b64encode(b"{}").decode()},
        }).encode()
        with patch.object(prepare, "google_request", return_value=(200, body)):
            with self.assertRaisesRegex(RuntimeError, "invalid version name"):
                prepare.secret_version("token", "demo-project")

    def test_preparation_guard_requires_the_matching_active_session_lease(self):
        now = 1_000
        run_id = "00000000-0000-4000-8000-000000000099"
        config = {"GCP_PROJECT_ID": "demo-project", "GCP_STATE_BUCKET": "state",
                  "GCP_LOAD_CONTROL_BUCKET": "control"}
        stores = {}

        class Store:
            def __init__(self, value):
                self.value = value

            def read(self, _name):
                return "1", self.value

        lease = {"run_id": run_id, "owner": "workflow-9", "status": "preparing_fixture",
                 "profile": "baseline", "expires_at": now + 100,
                 "session_expires_at": now + 10_000}
        session = {"expires_at": now + 10_000}
        stores["state"] = Store(session)
        stores["control"] = Store(lease)

        with patch.object(prepare.load_tests, "Storage", side_effect=lambda bucket, _token: stores[bucket]), \
                patch.object(prepare.load_tests, "demo_control_lock", return_value=nullcontext()), \
                patch.object(prepare.time, "time", return_value=now), \
                patch.dict(os.environ, {"GITHUB_RUN_ID": "workflow-9"}):
            prepare.assert_preparation_active(config, "token", run_id)

        lease["status"] = "cancelled"
        with patch.object(prepare.load_tests, "Storage", side_effect=lambda bucket, _token: stores[bucket]), \
                patch.object(prepare.load_tests, "demo_control_lock", return_value=nullcontext()), \
                patch.object(prepare.time, "time", return_value=now), \
                patch.dict(os.environ, {"GITHUB_RUN_ID": "workflow-9"}):
            with self.assertRaisesRegex(RuntimeError, "cancelled, expired or replaced"):
                prepare.assert_preparation_active(config, "token", run_id)

    def test_application_preparation_uses_only_the_dedicated_load_fixture_route(self):
        calls = []
        accounts = [{"email": f"opt06-load-{number:03d}@nexoruta.test", "password": "synthetic-password"}
                    for number in range(1, 7)]

        def request(_origin, _bearer, method, path, payload=None):
            calls.append((method, path, payload))
            if path == "/api/auth/login":
                return 200, {"accessToken": "ephemeral"}
            return 200, {"cuentas": payload["cuentas"]}

        with patch.object(prepare, "api_request", side_effect=request):
            seeded = prepare.prepare_application("https://api.example.test", "admin@nexoruta.test",
                                                 "admin-password", accounts)

        self.assertEqual(accounts, seeded)
        self.assertEqual(["/api/auth/login", "/api/admin/demo-data/load-fixture",
                          "/api/admin/demo-data/load-fixture"], [call[1] for call in calls])
        self.assertTrue(all(len(call[2]["cuentas"]) <= prepare.MAX_BATCH
                            for call in calls[1:]))

    def test_missing_fixture_persists_all_credentials_before_api_seed(self):
        with patch.object(prepare, "add_secret_version", return_value="2") as persist:
            accounts = prepare.fixture_accounts(None, "token", "demo-project")
        self.assertEqual(50, len(accounts))
        self.assertEqual([f"opt06-load-{number:03d}@nexoruta.test" for number in range(1, 51)],
                         [account["email"] for account in accounts])
        self.assertTrue(all(len(account["password"]) >= 12 for account in accounts))
        pending = persist.call_args.args[2]
        self.assertEqual("preparing", pending["fixtureStatus"])
        self.assertEqual(accounts, pending["accounts"])

    def test_existing_credentials_survive_a_sql_reset(self):
        accounts = [{"email": f"opt06-load-{number:03d}@nexoruta.test", "password": f"stored-{number:03d}-password"}
                    for number in range(1, 51)]
        with patch.object(prepare, "add_secret_version") as persist:
            actual = prepare.fixture_accounts({"fixtureStatus": "ready", "accounts": accounts}, "token", "demo-project")
        self.assertEqual(accounts, actual)
        persist.assert_not_called()

    def test_expanding_a_smoke_fixture_preserves_existing_passwords(self):
        existing = [{"email": f"opt06-load-{number:03d}@nexoruta.test", "password": f"stored-{number:03d}-password"}
                    for number in range(1, 6)]
        with patch.object(prepare, "add_secret_version") as persist:
            actual = prepare.fixture_accounts({"fixtureStatus": "ready", "accounts": existing},
                                              "token", "demo-project")
        self.assertEqual(existing, actual[:5])
        self.assertEqual(50, len(actual))
        self.assertTrue(all(len(account["password"]) >= 12 for account in actual))
        pending = persist.call_args.args[2]
        self.assertEqual("preparing", pending["fixtureStatus"])
        self.assertEqual(actual, pending["accounts"])

    def test_retrying_pending_fixture_reuses_the_persisted_credentials(self):
        accounts = [{"email": f"opt06-load-{number:03d}@nexoruta.test", "password": f"stored-{number:03d}-password"}
                    for number in range(1, 51)]
        with patch.object(prepare, "add_secret_version") as persist:
            actual = prepare.fixture_accounts({"fixtureStatus": "preparing", "accounts": accounts},
                                              "token", "demo-project")
        self.assertEqual(accounts, actual)
        persist.assert_not_called()

    def test_pins_only_unique_position_sequences_and_uses_content_hash_path(self):
        journey = "00000000-0000-4000-8000-000000000001"
        events = [{"id": f"10000000-0000-4000-8000-{number:012d}", "secuencia": number,
                   "tipo": "Posicion", "envioId": None, "versionEnvio": None,
                   "ocurridaEn": "2026-11-05T12:00:00+00:00", "datos": {"latitud": -34.9}}
                  for number in range(2, 52)]
        stored = {}

        def gcp_request(_token, method, url, body=None, content_type="application/json"):
            self.assertEqual("POST", method)
            self.assertEqual("application/json", content_type)
            stored["body"] = body
            stored["url"] = url
            return 200, b"{}"

        with patch.object(prepare, "google_request", side_effect=gcp_request):
            accounts, object_name, digest = prepare.pin_operations("token", "demo-project", [
                {"email": "opt06-load-001@nexoruta.test", "jornadaId": journey, "operaciones": events}])

        self.assertEqual([{"email": "opt06-load-001@nexoruta.test", "jornadaId": journey}], accounts)
        self.assertEqual(hashlib.sha256(stored["body"]).hexdigest(), digest)
        self.assertEqual(f"fixtures/opt06-{digest[:32]}/operations.json", object_name)
        self.assertIn("ifGenerationMatch=0", stored["url"])
        self.assertEqual(50, len(json.loads(stored["body"])[journey]))

    def test_rejects_a_non_position_or_duplicate_sequence(self):
        events = [{"id": f"10000000-0000-4000-8000-{number:012d}", "secuencia": number,
                   "tipo": "Posicion", "envioId": None, "versionEnvio": None,
                   "ocurridaEn": "2026-11-05T12:00:00+00:00"}
                  for number in range(2, 52)]
        events[3]["secuencia"] = 3
        with self.assertRaisesRegex(RuntimeError, "invalid position replay sequence"):
            prepare.pin_operations("token", "demo-project", [{
                "email": "opt06-load-001@nexoruta.test",
                "jornadaId": "00000000-0000-4000-8000-000000000001",
                "operaciones": events,
            }])


if __name__ == "__main__":
    unittest.main()
