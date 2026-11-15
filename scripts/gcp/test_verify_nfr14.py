import datetime as dt
from email.message import Message
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

import verify_nfr14 as verify
import host_versions
import deployment_health


def valid_host_versions():
    return {
        "schema_version": 1, "recorded_at": "2026-11-14T12:00:00+00:00",
        "os_id": "debian", "os_version_id": "12", "kernel": "6.1.0-cloud-amd64",
        "architecture": "x86_64", "docker_server": "29.1.3", "docker_compose": "2.40.3",
        "docker_buildx": "github.com/docker/buildx v0.29.1",
        "containerd": "containerd github.com/containerd/containerd v2.1.5",
        "packages": {name: "1.2.3-1" for name in host_versions.PACKAGE_NAMES},
    }


def valid_compose_health(node="a", cache_enabled=True):
    return {
        "node": node,
        "services": [
            {"service": name, "state": "running",
             "health": "healthy" if name in deployment_health.HEALTHCHECK_SERVICES else "not-configured"}
            for name in deployment_health.expected_services(node, cache_enabled)
        ],
    }


class VerifyNfr14Tests(unittest.TestCase):
    def setUp(self):
        self.frontend_ip = "34.12.34.56"
        self.endpoints = {
            name: f"https://{name}.34-12-34-56.sslip.io"
            for name in verify.SERVICES
        }
        self.run_id = "a" * 32
        self.tag = "nexoruta-integration-20261114-abcdef"
        self.target = {
            "run_id": self.run_id, "integration_tag": self.tag,
            "project_id": "nfr14-reproduction", "project_number": "123456",
            "state_bucket": "nfr14-reproduction-tofu-state",
        }
        self.published = {"release": "release-" + "b" * 32}

    def test_endpoints_must_match_the_public_load_balancer_ip_and_exact_services(self):
        result = verify.validate_endpoints(self.endpoints, self.frontend_ip)
        self.assertEqual(result, self.endpoints)
        for endpoints, address in (
            ({**self.endpoints, "extra": "https://extra.34-12-34-56.sslip.io"}, self.frontend_ip),
            ({**self.endpoints, "api": "http://api.34-12-34-56.sslip.io"}, self.frontend_ip),
            ({**self.endpoints, "api": "https://api.10-0-0-1.sslip.io"}, self.frontend_ip),
            (self.endpoints, "10.0.0.1"),
        ):
            with self.subTest(address=address), self.assertRaises(ValueError):
                verify.validate_endpoints(endpoints, address)

    def test_tls_check_uses_system_chain_and_exact_server_hostname_and_validity(self):
        now = dt.datetime(2026, 11, 14, 12, tzinfo=dt.timezone.utc)
        raw = Mock()
        raw.__enter__ = Mock(return_value=raw)
        raw.__exit__ = Mock(return_value=False)
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        connection.getpeercert.return_value = {"notBefore": "start", "notAfter": "end"}
        context = Mock()
        context.wrap_socket.return_value = connection
        connector = Mock(return_value=raw)
        with patch.object(verify.ssl, "cert_time_to_seconds",
                           side_effect=[now.timestamp() - 60, now.timestamp() + 60]):
            result = verify.check_tls("api.34-12-34-56.sslip.io", now=now, connector=connector,
                                      context_factory=Mock(return_value=context))
        connector.assert_called_once_with(("api.34-12-34-56.sslip.io", 443), timeout=10)
        context.wrap_socket.assert_called_once_with(raw, server_hostname="api.34-12-34-56.sslip.io")
        self.assertTrue(result["chain_and_hostname_verified"])

    def test_tls_check_rejects_an_expired_certificate(self):
        now = dt.datetime(2026, 11, 14, 12, tzinfo=dt.timezone.utc)
        raw = Mock()
        raw.__enter__ = Mock(return_value=raw)
        raw.__exit__ = Mock(return_value=False)
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        connection.getpeercert.return_value = {"notBefore": "start", "notAfter": "end"}
        context = Mock()
        context.wrap_socket.return_value = connection
        with patch.object(verify.ssl, "cert_time_to_seconds",
                           side_effect=[now.timestamp() - 120, now.timestamp() - 60]):
            with self.assertRaisesRegex(ValueError, "not currently valid"):
                verify.check_tls("api.34-12-34-56.sslip.io", now=now,
                                 connector=Mock(return_value=raw),
                                 context_factory=Mock(return_value=context))

    def test_http_upgrade_accepts_only_same_hostname_https_redirects(self):
        headers = Message()
        headers["Location"] = "https://api.34-12-34-56.sslip.io/health"

        class Opener:
            def open(self, request, timeout):
                raise urllib.error.HTTPError(request.full_url, 301, "moved", headers, None)

        result = verify.check_http_upgrade(self.endpoints["api"], opener_factory=lambda *_: Opener())
        self.assertEqual(result["https_hostname"], "api.34-12-34-56.sslip.io")
        del headers["Location"]
        headers["Location"] = "https://attacker.example/health"
        with self.assertRaisesRegex(ValueError, "outside the matching validated HTTPS hostname"):
            verify.check_http_upgrade(self.endpoints["api"], opener_factory=lambda *_: Opener())

    def test_http_error_status_still_checks_the_final_redirect_hostname(self):
        expected = self.endpoints["api"] + "/live"
        headers = Message()

        def unauthorized(url, timeout):
            raise urllib.error.HTTPError(url, 401, "unauthorized", headers, None)

        self.assertEqual(verify.get_status(expected, opener=unauthorized), 401)

        def redirected(url, timeout):
            raise urllib.error.HTTPError("https://attacker.example/live", 401,
                                         "unauthorized", headers, None)

        with self.assertRaisesRegex(ValueError, "outside its validated"):
            verify.get_status(expected, opener=redirected)

    def test_authenticated_smoke_is_exact_and_report_drops_unapproved_fields(self):
        proof = {
            "schema_version": 3, "project_id": self.target["project_id"],
            "release": self.published["release"], "cache_enabled": True, "redis_node": "b",
            "redis_smoke_clients": ["a", "b"],
            "host_versions": {"a": valid_host_versions(), "b": valid_host_versions()},
            "compose_health": {"a": valid_compose_health("a"), "b": valid_compose_health("b")},
            "authenticated_reads": [
                {"role": role, "login": "passed", "actor_read": "passed"}
                for role in ("commerce", "admin", "operator")
            ],
            "accidental_secret": "must never be copied to the report",
        }
        result = verify.validate_deployment_smoke(json.dumps(proof), self.target,
                                                  self.published, cache_enabled=True)
        self.assertEqual([item["role"] for item in result["authenticated_reads"]],
                         ["admin", "commerce", "operator"])
        self.assertEqual(set(result["host_versions"]), {"a", "b"})
        self.assertEqual(set(result["compose_health"]), {"a", "b"})
        self.assertEqual(len(result["compose_health"]["b"]["services"]),
                         len(deployment_health.expected_services("b", True)))
        self.assertNotIn("accidental_secret", result)
        proof["authenticated_reads"].append(proof["authenticated_reads"][0])
        with self.assertRaisesRegex(ValueError, "all synthetic roles"):
            verify.validate_deployment_smoke(json.dumps(proof), self.target,
                                              self.published, cache_enabled=True)
        proof["authenticated_reads"].pop()
        proof.pop("host_versions")
        with self.assertRaisesRegex(ValueError, "Host version evidence"):
            verify.validate_deployment_smoke(json.dumps(proof), self.target,
                                              self.published, cache_enabled=True)
        proof["host_versions"] = {"a": valid_host_versions(), "b": valid_host_versions()}
        proof.pop("compose_health")
        with self.assertRaisesRegex(ValueError, "exactly nodes A and B"):
            verify.validate_deployment_smoke(json.dumps(proof), self.target,
                                              self.published, cache_enabled=True)

    def test_online_checks_cover_tls_http_upgrade_and_anonymous_denials(self):
        tls = Mock(side_effect=lambda host: {"hostname": host, "chain_and_hostname_verified": True})
        upgrade = Mock(side_effect=lambda origin: {"status": 301,
                                                   "https_hostname": origin.split("//", 1)[1]})

        def status(url):
            return 401 if url.endswith("/api/search?query=nexoruta") or url == self.endpoints["mail"] + "/" else 200

        result = verify._online_checks(self.endpoints, tls_checker=tls,
                                       upgrade_checker=upgrade, status_reader=status)
        self.assertEqual(tls.call_count, len(verify.SERVICES))
        self.assertEqual(upgrade.call_count, len(verify.SERVICES))
        self.assertEqual(result["https_status"]["api/live"], 200)
        self.assertEqual(result["https_status"]["monitor/api/search?query=nexoruta"], 401)
        self.assertEqual(result["https_status"]["mail/"], 401)

    def test_finalize_stop_requires_terminated_vms_inactive_lease_and_running_sql(self):
        report = {
            "schema_version": 1, "status": "passed", "run_id": self.run_id,
            "integration_tag": self.tag, "project_id": self.target["project_id"],
            "project_number": self.target["project_number"], "checks": {},
            "session_stop": "pending",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "verification.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            storage = Mock()
            storage.read.return_value = (None, None)
            factory = Mock(return_value=storage)
            target = dict(self.target)

            def google_json(*args, **kwargs):
                if args[:2] == ("compute", "instances"):
                    return None
                if args[:3] == ("sql", "instances", "describe"):
                    return {"state": "RUNNABLE"}
                raise AssertionError(args)

            with (patch.object(verify.reproduce, "validate_runtime_environment", return_value=target),
                  patch.object(verify.reproduce, "_access_token", return_value="test-token"),
                  patch.object(verify.reproduce, "_read_active_marker", return_value=False)):
                result = verify.finalize_stop(
                    run_id=self.run_id, integration_tag=self.tag, output_path=path,
                    environment={}, google_json=google_json, objects_factory=factory,
                )
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["session_stop"], "passed")
        self.assertEqual(result["checks"]["post_stop_sql"], "RUNNABLE")


if __name__ == "__main__":
    unittest.main()
