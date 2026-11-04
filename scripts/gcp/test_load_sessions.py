"""Verify session rotation, shared quotas and the private k6 token boundary."""

import datetime as dt
import importlib.util
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
import uuid


spec = importlib.util.spec_from_file_location("load_sessions",
    Path(__file__).resolve().parents[2] / "deploy/load/sessions.py")
sessions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sessions)


class Clock:
    def __init__(self):
        self.value = 0

    def wall(self):
        return 1_700_000_000 + self.value

    def monotonic(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def fixture(count):
    return {"readPath": "/api/mobile/perfil", "accounts": [
        {"email": f"load-{index}@nexoruta.test", "password": "private-test-password",
         "jornadaId": str(uuid.UUID(int=index + 1))} for index in range(count)]}


class Transport:
    def __init__(self, clock):
        self.clock, self.calls, self.tokens = clock, [], {}
        self.serial = 0
        self.login_id = 0
        self.fail_action = None

    def __call__(self, origin, action, payload, timeout):
        self.calls.append((self.clock.monotonic(), action, dict(payload)))
        if self.fail_action == action:
            raise urllib.error.HTTPError(origin, 429, "controlled rejection", {}, None)
        if action == "logout":
            self.tokens.pop(payload["refreshToken"], None)
            return None
        if action == "login":
            self.login_id += 1
            session_id = str(uuid.UUID(int=self.login_id))
        else:
            session_id = self.tokens.pop(payload["refreshToken"])
        self.serial += 1
        refresh = "r" + str(self.serial).zfill(42)
        self.tokens[refresh] = session_id
        iso = lambda seconds: dt.datetime.fromtimestamp(self.clock.wall() + seconds, dt.timezone.utc).isoformat()
        return {"accessToken": f"access-{self.serial}", "refreshToken": refresh,
                "expiresAtUtc": iso(900), "refreshExpiresAtUtc": iso(86400), "sesionId": session_id}


class SessionTests(unittest.TestCase):
    def manager(self, count):
        clock = Clock()
        transport = Transport(clock)
        manager = sessions.Sessions("https://controlled.invalid", fixture(count), count,
            transport=transport, wall=clock.wall, monotonic=clock.monotonic)
        return manager, clock, transport

    def prepare(self, manager, clock):
        for _ in range(3000):
            clock.advance(max(0.001, manager.tick()))
            if manager.snapshot()["ready"]:
                return
        self.fail("Controlled authentication did not prepare its identities")

    def test_fifty_logins_and_inactive_identity_renewals_obey_shared_quotas(self):
        manager, clock, transport = self.manager(50)
        self.prepare(manager, clock)
        initial = [value["refresh"] for value in manager.values]
        end = clock.monotonic() + 3600
        while clock.monotonic() < end:
            clock.advance(max(0.001, manager.tick()))
        self.assertTrue(manager.snapshot()["ready"])
        for value, previous in zip(manager.values, initial):
            self.assertNotEqual(value["refresh"], previous)
            self.assertGreater(value["expiry"], clock.wall() + 30)
        with patch.object(sessions.time, "sleep", side_effect=clock.advance):
            self.assertTrue(manager.close()["complete"])
        for actions, limit in (({"login"}, 5), ({"refresh", "logout"}, 30)):
            starts = [stamp for stamp, action, _ in transport.calls if action in actions]
            for stamp in starts:
                self.assertLessEqual(sum(stamp <= other < stamp + 60 for other in starts), limit)

    def test_refresh_uses_the_rotated_token_and_preserves_session_identity(self):
        manager, clock, transport = self.manager(1)
        self.prepare(manager, clock)
        identity = manager.values[0]["session_id"]
        original = manager.values[0]["refresh"]
        clock.advance(730)
        manager.tick()
        rotated = manager.values[0]["refresh"]
        clock.advance(730)
        manager.tick()
        used = [payload["refreshToken"] for _, action, payload in transport.calls if action == "refresh"]
        self.assertEqual(used, [original, rotated])
        self.assertEqual(manager.values[0]["session_id"], identity)

    def test_variable_rtt_does_not_compress_the_login_quota_at_the_server(self):
        manager, clock, transport = self.manager(5)
        windows = []

        def delayed(origin, action, payload, timeout):
            started = clock.monotonic()
            clock.advance(10 if not windows else 0.1)
            result = transport(origin, action, payload, timeout)
            windows.append((started, clock.monotonic()))
            return result

        manager.transport = delayed
        self.prepare(manager, clock)
        for previous, following in zip(windows, windows[1:]):
            self.assertGreaterEqual(following[0] - previous[1], manager.LOGIN_INTERVAL - 0.001)

    def test_rotation_response_lost_is_not_retried_and_remains_explicitly_unresolved(self):
        manager, clock, transport = self.manager(1)
        self.prepare(manager, clock)
        clock.advance(730)

        def lost(origin, action, payload, timeout):
            transport(origin, action, payload, timeout)
            if action == "refresh":
                raise OSError("controlled lost POST response")

        manager.transport = lost
        manager.tick()
        for _ in range(10):
            clock.advance(1)
            manager.tick()
        self.assertEqual(manager.snapshot()["refresh_requests"], 1)
        self.assertTrue(manager.snapshot()["unknown_session_state"])
        self.assertEqual(manager.snapshot()["unresolved_account_indexes"], [0])
        self.assertFalse(manager.close()["complete"])

    def test_refresh_quota_rejection_is_an_authentication_fault_without_retry_burst(self):
        manager, clock, transport = self.manager(1)
        self.prepare(manager, clock)
        clock.advance(730)
        transport.fail_action = "refresh"
        manager.tick()
        manager.tick()
        self.assertEqual(manager.snapshot()["fault"], "refresh_http_429")
        self.assertEqual(manager.snapshot()["refresh_requests"], 1)
        self.assertIsNone(manager.session(0))

    def test_refresh_cannot_switch_the_owned_mobile_session(self):
        manager, clock, transport = self.manager(1)
        self.prepare(manager, clock)
        owned = manager.values[0]["session_id"]
        clock.advance(730)

        def switched(origin, action, payload, timeout):
            body = transport(origin, action, payload, timeout)
            body["sesionId"] = str(uuid.UUID(int=999))
            return body

        manager.transport = switched
        manager.tick()
        self.assertEqual(manager.values[0]["session_id"], owned)
        self.assertTrue(manager.snapshot()["unknown_session_state"])
        self.assertIsNone(manager.session(0))

    def test_public_fixture_and_status_do_not_expose_private_credentials(self):
        manager, clock, _ = self.manager(1)
        self.prepare(manager, clock)
        public = json.dumps({"fixture": manager.public_fixture, "status": manager.snapshot(),
                             "session": manager.session(0)})
        self.assertNotIn("private-test-password", public)
        self.assertNotIn("refreshToken", public)
        self.assertNotIn("@nexoruta.test", public)
        self.assertEqual(set(manager.session(0)), {"accessToken", "expiresAtUtc"})

    def test_cleanup_revokes_only_created_sessions_and_respects_a_bounded_deadline(self):
        manager, clock, transport = self.manager(2)
        self.prepare(manager, clock)
        cleanup = manager.close(budget=2)
        self.assertFalse(cleanup["complete"])
        self.assertEqual(cleanup["known_sessions"], 2)
        self.assertEqual(cleanup["revoked_sessions"], 1)
        self.assertEqual(cleanup["pending_session_ids"], [manager.values[1]["session_id"]])
        self.assertEqual(cleanup["reason"], "cleanup_budget_exhausted")
        self.assertEqual(len([action for _, action, _ in transport.calls if action == "logout"]), 1)

    def test_cleanup_deadline_also_bounds_a_transport_that_ignores_its_socket_timeout(self):
        manager, clock, transport = self.manager(1)
        self.prepare(manager, clock)
        release = threading.Event()
        result = []

        def blocked(origin, action, payload, timeout):
            if action == "logout":
                release.wait(timeout=10)
            return transport(origin, action, payload, timeout)

        manager.transport = blocked
        manager.monotonic = time.monotonic
        caller = threading.Thread(target=lambda: result.append(manager.close(budget=1.1)), daemon=True)
        caller.start()
        try:
            caller.join(timeout=3)
            self.assertFalse(caller.is_alive())
            self.assertFalse(result[0]["complete"])
            self.assertEqual(result[0]["reason"], "logout_response_unavailable")
        finally:
            release.set()
            caller.join(timeout=2)

    def test_expired_access_token_is_never_returned(self):
        manager, clock, _ = self.manager(1)
        self.prepare(manager, clock)
        clock.advance(900)
        self.assertIsNone(manager.session(0))
        self.assertEqual(manager.snapshot()["fault"], "session_expiry_too_close")

    def test_fixture_rejects_non_synthetic_or_duplicate_identities(self):
        for invalid in (fixture(2), fixture(1)):
            if len(invalid["accounts"]) == 2:
                invalid["accounts"][1]["jornadaId"] = invalid["accounts"][0]["jornadaId"]
            else:
                invalid["accounts"][0]["email"] = "real@example.org"
            with self.assertRaises(ValueError):
                sessions.Sessions("https://controlled.invalid", invalid, 1)


class BrokerHttpTests(unittest.TestCase):
    def test_real_loopback_server_requires_capability_and_never_returns_refresh_tokens(self):
        clock = Clock()
        transport = Transport(clock)
        manager = sessions.Sessions("https://controlled.invalid", fixture(1), 1,
            transport=transport, wall=clock.wall, monotonic=clock.monotonic)
        broker = sessions.SessionBroker(manager)
        broker.start()
        try:
            self.assertTrue(manager.prepared.wait(timeout=2))
            self.assertEqual(broker.server.server_address[0], "127.0.0.1")
            with self.assertRaises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(broker.url + "/sessions/0", timeout=2)
            self.assertEqual(denied.exception.code, 403)
            req = urllib.request.Request(broker.url + "/sessions/0",
                headers={"Authorization": "Bearer " + broker.capability})
            with urllib.request.urlopen(req, timeout=2) as response:
                value = json.load(response)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(set(value), {"accessToken", "expiresAtUtc"})
        finally:
            self.assertTrue(broker.close()["complete"])

    def test_authentication_post_never_follows_a_redirect_with_credentials(self):
        calls = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                calls.append(self.path)
                self.rfile.read(int(self.headers.get("Content-Length", "0")))
                self.send_response(307)
                self.send_header("Location", "/unexpected-credential-target")
                self.end_headers()

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(urllib.error.HTTPError) as rejected:
                sessions.request(f"http://127.0.0.1:{server.server_port}", "login",
                    {"email": "load@nexoruta.test", "password": "controlled-fixture"})
            self.assertEqual(rejected.exception.code, 307)
            self.assertEqual(calls, ["/api/auth/mobile/login"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
