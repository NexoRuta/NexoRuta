from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
import urllib.error
from unittest.mock import Mock, patch

import vm_deploy


class VmDeploymentTests(unittest.TestCase):
    def test_public_smoke_checks_monitor_health_and_requires_auth_for_grafana_and_mail(self):
        endpoints = {name: f"https://{name}.34-0-0-1.sslip.io" for name in
                    ("api", "admin", "backoffice", "commerce", "tracking", "monitor", "mail")}
        response = Mock()
        response.__enter__ = Mock(return_value=SimpleNamespace(status=200))
        response.__exit__ = Mock(return_value=False)
        requests = []

        def open_url(url, timeout):
            requests.append(url)
            if url.endswith("/api/search?query=nexoruta") or url.endswith("/mail.34-0-0-1.sslip.io/"):
                raise urllib.error.HTTPError(url, 401, "unauthorized", {}, None)
            return response

        with patch.object(vm_deploy.urllib.request, "urlopen", side_effect=open_url):
            vm_deploy.smoke({"endpoints": endpoints}, check_accounts=False)
        self.assertIn(endpoints["monitor"] + "/api/health", requests)
        self.assertIn(endpoints["monitor"] + "/api/search?query=nexoruta", requests)
        self.assertIn(endpoints["mail"] + "/", requests)

    def test_release_extraction_makes_only_grafana_provisioning_readable_by_its_container_user(self):
        archive_data = io.BytesIO()
        with tarfile.open(fileobj=archive_data, mode="w:gz") as archive:
            for name, contents in (
                ("compose.yaml", b"services: {}\n"),
                ("grafana/provisioning/dashboards/provider.yaml", b"apiVersion: 1\n"),
            ):
                info = tarfile.TarInfo(name)
                info.size = len(contents)
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(contents))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vm_deploy.extract(archive_data.getvalue(), root)
            self.assertEqual((root / "compose.yaml").stat().st_mode & 0o777, 0o644)
            self.assertEqual((root / "grafana/provisioning/dashboards/provider.yaml").stat().st_mode & 0o777, 0o644)
            self.assertEqual((root / "grafana/provisioning/dashboards").stat().st_mode & 0o777, 0o755)

    def configuration(self):
        registry = "southamerica-west1-docker.pkg.dev/demo-project/nexoruta"
        passwords = {name: "private-" + name for name in (
            "migrator", "api", "worker", "bootstrap", "rabbit", "mongo", "mail", "monitor", "grafana",
            "keys_api", "keys_admin", "keys_backoffice", "keys_commerce", "keys_tracking", "admin", "operator", "commerce")}
        runtime = {"project_id": "demo-project", "sql_connection": "demo-project:region:sql", "registry": registry,
                   "services_host": "10.0.0.1", "frontend_ip": "34.0.0.1",
                   "passwords": passwords, "keys": {name: "key" for name in ("jwt", "tracking", "push", "evidence")},
                   "endpoints": {name: f"https://{name}.34-0-0-1.sslip.io" for name in (
                       "api", "admin", "backoffice", "commerce", "tracking", "mail", "monitor")},
                   "organization_ids": {"operator": "operator-id", "commerce": "commerce-id"}}
        integrations = {"smtp_host": "mailpit", "smtp_port": 1025, "smtp_ssl": False,
                        "smtp_from": "demo@example.test", "monitor_google_client_id": "oauth-client",
                        "monitor_google_client_secret": "private-oauth", "monitor_allowed_emails": ["reader@example.test"]}
        hosting = {"grafana_secret_key": "private-grafana-key", "certificate_password": "private-pfx",
                   "certificate_pfx": "cGZ4"}
        images = {name: registry + "/" + name + "@sha256:" + "a" * 64 for name in (
            "api", "worker", "admin", "backoffice", "commerce", "tracking")}
        return runtime, integrations, hosting, images

    def test_shared_environment_preserves_identity_and_restricts_keys_and_google_access(self):
        runtime, integrations, hosting, images = self.configuration()
        values = vm_deploy.environment(runtime, integrations, images, "hash", hosting, "b", "10.0.0.2",
                                       "release-" + "a" * 32, ("172.22.0.0/16",))
        self.assertEqual(values["SMTP_HOST"], "10.0.0.1")
        self.assertEqual(values["TRUSTED_NETWORKS"], "34.0.0.1/32,35.191.0.0/16,130.211.0.0/22,172.22.0.0/16")
        allowed_hosts = values["ALLOWED_HOSTS"].split(";")
        self.assertIn("api.34-0-0-1.sslip.io", allowed_hosts)
        self.assertNotIn("api.34-0-0-2.sslip.io", allowed_hosts)
        self.assertFalse(any(key.startswith("LEGACY_") for key in values))
        for ring in vm_deploy.RINGS:
            self.assertIn("Username=nexoruta_keys_" + ring + ";", values["KEYS_" + ring.upper() + "_CONNECTION"])
        self.assertEqual(values["MONITOR_ROLE_EXPRESSION"], "contains(['reader@example.test'], email) && 'Viewer' || 'None'")
        self.assertEqual(values["JWT_KEY"], runtime["keys"]["jwt"])

    def test_shared_environment_rejects_open_google_access_and_default_proxy_routes(self):
        runtime, integrations, hosting, images = self.configuration()
        for emails, subnets in (([], ()), (["*@example.test"], ()), (["reader@example.test"], ("0.0.0.0/0",))):
            with self.subTest(emails=emails, subnets=subnets):
                integrations["monitor_allowed_emails"] = emails
                with self.assertRaises(ValueError):
                    vm_deploy.environment(runtime, integrations, images, "hash", hosting, "a", "10.0.0.1",
                                          "release-" + "a" * 32, subnets)

    def test_migrations_provision_hosting_before_catalog_and_bootstrap(self):
        deployment = vm_deploy.Deploy(Path("unused"), io.StringIO())
        events = []

        class Lock:
            def __enter__(self):
                events.append("lock")

            def __exit__(self, *args):
                events.append("unlock")

        deployment.wait_sql = Mock()
        deployment.migration_lock = Mock(return_value=Lock())
        deployment.compose = Mock(side_effect=lambda *args, **kwargs: events.append(args[-1]))
        deployment.migrate(12345)
        self.assertEqual(events, ["lock", "/deploy/sql/preflight.sql", "migrate",
                                 "/deploy/sql/runtime-roles.sql", "/deploy/sql/hosting.sql",
                                 "/deploy/sql/postflight.sql", "department-catalog-import", "bootstrap", "unlock"])

    def test_lost_sql_lock_blocks_the_next_compose_mutation(self):
        deployment = vm_deploy.Deploy(Path("unused"), io.StringIO())
        deployment.lock_process = Mock()
        deployment.lock_process.poll.return_value = 1
        deployment.execute = Mock()
        with self.assertRaisesRegex(RuntimeError, "lock connection was lost"):
            deployment.compose("run", "migrate")
        deployment.execute.assert_not_called()

    def test_failed_node_update_does_not_restart_previous_release_or_brokers(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(vm_deploy, "BASE", Path(directory)):
            root = Path(directory)
            target = "release-" + "b" * 32
            target_directory = root / "releases" / target
            target_directory.mkdir(parents=True)
            deployment = vm_deploy.Deploy(target_directory, io.StringIO())
            args = SimpleNamespace(release=target, node="b")
            with patch.object(vm_deploy.Deploy, "compose") as compose, patch.object(vm_deploy, "direct_health", side_effect=RuntimeError("new node unhealthy")), redirect_stdout(io.StringIO()) as output:
                with self.assertRaises(RuntimeError):
                    vm_deploy.apply(args, deployment, "10.0.0.2")
            self.assertFalse((root / "current-release").exists())
            self.assertEqual(json.loads(output.getvalue())["status"], "failed")
            self.assertEqual(compose.call_count, 1)
            for call in compose.call_args_list:
                self.assertFalse(set(vm_deploy.SHARED).intersection(call.args))

    def test_prepare_of_existing_session_preserves_brokers_and_keeps_password_out_of_arguments(self):
        runtime, integrations, hosting, images = self.configuration()
        with tempfile.TemporaryDirectory() as directory, patch.object(vm_deploy, "BASE", Path(directory)):
            root = Path(directory)
            release = root / "release"
            release.mkdir()
            (release / "monitor_agent.py").write_text("# collector")
            (release / "monitoring").mkdir()
            (release / "monitoring/ops-agent.yaml").write_text("metrics: {}")
            deployment = vm_deploy.Deploy(release, io.StringIO())
            services = vm_deploy.SHARED
            identifiers = [f"container-{index}" for index in range(len(services))]
            def execute(*args, **kwargs):
                if args[:2] == ("docker", "run"):
                    return "hash"
                if args[:2] == ("docker", "ps"):
                    return "\n".join(identifiers)
                if args[:2] == ("docker", "inspect"):
                    return services[identifiers.index(args[-1])]
                return ""
            deployment.execute = Mock(side_effect=execute)
            deployment.compose = Mock()
            args = SimpleNamespace(node="a", release="release-" + "a" * 32, deadline=12345)
            with patch.object(vm_deploy, "token", return_value="token"), patch.object(vm_deploy, "bridge_subnets", return_value=["172.22.0.0/16"]), patch.object(vm_deploy, "OPS_AGENT_CONFIG", root / "ops-agent.yaml"):
                result = vm_deploy.prepare(args, deployment, runtime, integrations, hosting, {"images": images}, "10.0.0.1")
            self.assertEqual(result, {})
            up_calls = [call.args for call in deployment.compose.call_args_list if "up" in call.args]
            self.assertEqual(len(up_calls), 1)
            self.assertEqual(up_calls[0][-1], "sql-proxy")
            started = [call.args[-1] for call in deployment.execute.call_args_list if call.args[:2] == ("docker", "start")]
            self.assertEqual(set(started), set(identifiers))
            for call in deployment.execute.call_args_list:
                self.assertNotIn(runtime["passwords"]["mail"], call.args)
            config = json.loads((root / "monitor.json").read_text())
            self.assertEqual(config["expires_at"], args.deadline)
            self.assertEqual((release / "hosting.pfx").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
