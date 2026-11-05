"""Own and renew synthetic mobile sessions within one disposable load Job."""

import datetime as dt
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re
import secrets
import threading
import time
import urllib.error
import urllib.request
import uuid


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(origin, action, payload, timeout=10):
    req = urllib.request.Request(origin + "/api/auth/mobile/" + action,
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    # Never forward credentials through a redirect. Use the platform CA store.
    with urllib.request.build_opener(NoRedirects()).open(req, timeout=timeout) as response:
        body = response.read(65537)
        if len(body) > 65536:
            raise ValueError("Oversized authentication response")
        if action == "logout":
            if response.status != 204:
                raise ValueError("Invalid logout response")
            return None
        if response.status != 200:
            raise ValueError("Invalid authentication response")
        return json.loads(body)


def expires(value):
    if not isinstance(value, str):
        raise ValueError("Invalid session expiry")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("An explicit UTC session expiry is required")
    return parsed.timestamp()


class Sessions:
    LOGIN_INTERVAL = 12.1  # Pause after responses: safe even with variable RTT.
    REFRESH_INTERVAL = 2.1  # Below 30/min, shared by refresh and logout.
    RENEW_AHEAD = 180

    def __init__(self, origin, fixture, count, transport=request, wall=time.time, monotonic=time.monotonic):
        accounts = fixture.get("accounts")
        if (fixture.get("readPath") != "/api/mobile/perfil" or not isinstance(accounts, list)
                or not isinstance(count, int) or not 1 <= count <= 50 or not count <= len(accounts) <= 50):
            raise ValueError("A bounded synthetic mobile fixture is required")
        for account in accounts:
            if (not isinstance(account, dict) or not isinstance(account.get("email"), str)
                    or not account["email"].endswith("@nexoruta.test")
                    or not isinstance(account.get("password"), str) or not account["password"]
                    or not isinstance(account.get("jornadaId"), str)):
                raise ValueError("Invalid synthetic account")
            if str(uuid.UUID(account["jornadaId"])) != account["jornadaId"].lower():
                raise ValueError("A canonical journey identifier is required")
        if (len({a["email"] for a in accounts}) != len(accounts)
                or len({a["jornadaId"].lower() for a in accounts}) != len(accounts)):
            raise ValueError("Synthetic identities and journeys must be distinct")
        self.accounts = [dict(a) for a in accounts[:count]]
        # k6 needs only the identities assigned to active VUs. Keep the other
        # fixture journey IDs private to this wrapper for smaller profiles.
        self.public_fixture = {"readPath": fixture["readPath"],
                               "accounts": [{"jornadaId": a["jornadaId"]} for a in self.accounts]}
        self.origin, self.transport, self.wall, self.monotonic = origin, transport, wall, monotonic
        self.values = [None] * count
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        self.prepared = threading.Event()
        self.thread = None
        self.next_login = self.next_refresh = 0
        self.login_requests = self.refresh_requests = 0
        self.fault = None
        self.unknown_session_state = False
        self.uncertain_indexes = []

    def _validated(self, body, previous=None):
        if not isinstance(body, dict):
            raise ValueError("Invalid session response")
        token, refresh = body.get("accessToken"), body.get("refreshToken")
        expiry, refresh_expiry = expires(body["expiresAtUtc"]), expires(body["refreshExpiresAtUtc"])
        if not isinstance(body.get("sesionId"), str):
            raise ValueError("Invalid session identifier")
        session_id = str(uuid.UUID(body["sesionId"]))
        if (not isinstance(token, str) or not 1 <= len(token) <= 32768 or not re.fullmatch(r"[A-Za-z0-9_.-]+", token)
                or not isinstance(refresh, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", refresh)
                or expiry <= self.wall() + self.RENEW_AHEAD or refresh_expiry <= expiry
                or (previous and (session_id != previous["session_id"] or refresh == previous["refresh"]))):
            raise ValueError("Invalid session response")
        return {"access": token, "refresh": refresh, "expiry": expiry,
                "expires_at_utc": body["expiresAtUtc"], "session_id": session_id}

    def tick(self):
        """Perform at most one serialized request; return an interruptible wait."""
        now, mono = self.wall(), self.monotonic()
        with self.lock:
            if self.fault or self.stopped.is_set():
                return 1
            due = next((i for i, value in sorted(enumerate(self.values),
                key=lambda pair: pair[1]["expiry"] if pair[1] else float("inf"))
                if value and value["expiry"] - now <= self.RENEW_AHEAD), None)
            if due is not None:
                if mono < self.next_refresh:
                    return min(1, self.next_refresh - mono)
                index, action = due, "refresh"
                previous = self.values[index]
                payload = {"refreshToken": previous["refresh"]}
                self.next_refresh = mono + self.REFRESH_INTERVAL
                self.refresh_requests += 1
            else:
                index = next((i for i, value in enumerate(self.values) if value is None), None)
                if index is None or mono < self.next_login:
                    return min(1, max(0.01, self.next_login - mono)) if index is not None else 1
                action, previous = "login", None
                payload = {"email": self.accounts[index]["email"], "password": self.accounts[index]["password"]}
                self.next_login = mono + self.LOGIN_INTERVAL
                self.login_requests += 1
        try:
            body = self.transport(self.origin, action, payload, timeout=10)
            value = self._validated(body, previous)
        except urllib.error.HTTPError as error:
            self.fail(f"{action}_http_{error.code}")
            return 1
        except (OSError, ValueError, KeyError, TypeError):
            # A POST may have succeeded remotely. Never retry a lost rotation.
            self.fail(f"{action}_response_unavailable", ambiguous=True, index=index)
            return 1
        finally:
            with self.lock:
                if action == "login":
                    self.next_login = self.monotonic() + self.LOGIN_INTERVAL
                else:
                    self.next_refresh = self.monotonic() + self.REFRESH_INTERVAL
        with self.lock:
            self.values[index] = value
            if action == "login":
                self.accounts[index] = {}  # Passwords are not needed after login.
            if all(self.values):
                self.prepared.set()
        return 0

    def fail(self, code, ambiguous=False, index=None):
        with self.lock:
            self.fault = code
            self.unknown_session_state |= ambiguous
            if ambiguous and index is not None and index not in self.uncertain_indexes:
                self.uncertain_indexes.append(index)
        self.prepared.set()

    def snapshot(self):
        with self.lock:
            return {"ready": all(self.values) and not self.fault, "accounts": len(self.values),
                    "login_requests": self.login_requests, "refresh_requests": self.refresh_requests,
                    "fault": self.fault, "unknown_session_state": self.unknown_session_state,
                    "unresolved_account_indexes": list(self.uncertain_indexes)}

    def session(self, index):
        with self.lock:
            value = self.values[index] if 0 <= index < len(self.values) else None
            if value and value["expiry"] <= self.wall() + 30:
                self.fault = "session_expiry_too_close"
            if self.fault or not value:
                return None
            return {"accessToken": value["access"], "expiresAtUtc": value["expires_at_utc"]}

    def _work(self):
        try:
            while not self.stopped.is_set():
                self.stopped.wait(self.tick())
        except Exception:
            self.fail("authentication_internal_error", ambiguous=True)

    def start(self):
        self.thread = threading.Thread(target=self._work, daemon=True)
        self.thread.start()

    def close(self, budget=120):
        deadline = self.monotonic() + max(0, budget)
        self.stopped.set()
        self.prepared.set()
        if self.thread and self.thread.ident is not None:
            self.thread.join(timeout=min(12, max(0, deadline - self.monotonic())))
        if self.thread and self.thread.is_alive():
            return {"complete": False, "reason": "authentication_worker_did_not_stop",
                    "unknown_session_state": True}
        known = sum(value is not None for value in self.values)
        pending = [value["session_id"] for value in self.values if value is not None]
        revoked = 0
        reason = None
        for value in self.values:
            if value is None:
                continue
            wait = max(0, self.next_refresh - self.monotonic())
            if self.monotonic() + wait + 1 >= deadline:
                reason = "cleanup_budget_exhausted"
                break
            if wait:
                time.sleep(wait)
            self.next_refresh = self.monotonic() + self.REFRESH_INTERVAL
            timeout = min(10, deadline - self.monotonic())
            outcome = {"revoked": False}

            def revoke(token=value["refresh"]):
                try:
                    self.transport(self.origin, "logout", {"refreshToken": token}, timeout=timeout)
                    outcome["revoked"] = True
                except (OSError, ValueError, KeyError, TypeError):
                    pass
                finally:
                    self.next_refresh = self.monotonic() + self.REFRESH_INTERVAL

            # A socket timeout does not bound DNS resolution. The daemon thread
            # also bounds the whole request; no second request follows a timeout.
            worker = threading.Thread(target=revoke, daemon=True)
            try:
                worker.start()
            except RuntimeError:
                reason = "logout_worker_unavailable"
                break
            worker.join(timeout=timeout)
            if worker.is_alive():
                reason = "logout_response_unavailable"
                break
            revoked += int(outcome["revoked"])
            if outcome["revoked"]:
                pending.remove(value["session_id"])
            elif reason is None:
                reason = "logout_rejected_or_unavailable"
        # Logout preserves domain history; it revokes only this run's sessions.
        return {"complete": revoked == known and not self.unknown_session_state,
                "known_sessions": known, "revoked_sessions": revoked,
                "pending_session_ids": pending,
                "unknown_session_state": self.unknown_session_state, "reason": reason}


class SessionBroker:
    def __init__(self, sessions, generator_metrics):
        self.sessions = sessions
        self.generator_metrics = generator_metrics
        self.capability = secrets.token_urlsafe(32)
        broker = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass  # Never log a token endpoint or authorization header.

            def do_GET(self):
                if not hmac.compare_digest(self.headers.get("Authorization", "").encode("utf-8"),
                                           ("Bearer " + broker.capability).encode("utf-8")):
                    self.respond(403, {})
                    return
                if self.path == "/ready":
                    sessions.prepared.wait(timeout=10)
                    state = sessions.snapshot()
                    self.respond(503 if state["fault"] or sessions.stopped.is_set() else (200 if state["ready"] else 202), {})
                    return
                if self.path == "/generator":
                    sample = broker.generator_metrics()
                    if not isinstance(sample, dict) or not sample.get("available"):
                        self.respond(503, {})
                        return
                    cpu = sample.get("cpu_utilization")
                    memory = sample.get("memory_bytes")
                    memory_limit = sample.get("memory_limit_bytes")
                    if cpu is None:
                        self.respond(202, {})
                        return
                    if (not isinstance(cpu, (int, float)) or not 0 <= cpu <= 1.05
                            or not isinstance(memory, int) or memory < 0
                            or not isinstance(memory_limit, int) or memory_limit <= 0 or memory > memory_limit):
                        self.respond(503, {})
                        return
                    self.respond(200, {"cpu_utilization": cpu,
                        "memory_utilization": memory / memory_limit})
                    return
                match = re.fullmatch(r"/sessions/([0-9]{1,2})", self.path)
                if not match:
                    self.respond(404, {})
                    return
                value = sessions.session(int(match[1]))
                self.respond(200 if value else 503, value or {})

            def respond(self, code, value):
                data = json.dumps(value).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        class Server(HTTPServer):
            request_queue_size = 64

            def handle_error(self, *_args):
                pass  # HTTP failures must not dump request headers or tokens.

        self.server = Server(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        self.sessions.start()

    def close(self, budget=120):
        self.sessions.stopped.set()
        self.sessions.prepared.set()
        if self.thread.is_alive():
            self.server.shutdown()
        self.server.server_close()
        if self.thread.ident is not None:
            self.thread.join(timeout=2)
        return self.sessions.close(budget)
