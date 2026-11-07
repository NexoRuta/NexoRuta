from contextlib import redirect_stdout
import io
import sys
import json
import os
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
import urllib.error
from unittest.mock import Mock, patch

import vm_deploy
import monitor_agent


class VmDeploymentTests(unittest.TestCase):
    def test_redis_dns_is_exactly_bound_to_vm_b_and_private_subnet(self):
        runtime, _, _, _ = self.configuration()
        with patch.object(vm_deploy.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("10.0.0.3", 6378))]):
            self.assertEqual(vm_deploy.redis_addresses(runtime), {vm_deploy.ipaddress.ip_address("10.0.0.3")})
        with patch.object(vm_deploy.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("8.8.8.8", 6378))]):
            with self.assertRaisesRegex(ValueError, "outside the configured private subnet"):
                vm_deploy.redis_addresses(runtime)
        runtime["redis"]["host"] = "redis.attacker.example"
        with self.assertRaisesRegex(ValueError, "VM B identity"):
            vm_deploy.redis_dns_name(runtime)

    def test_monitor_redis_info_and_docker_units_are_bounded_and_numeric(self):
        values = monitor_agent.redis_info_fields(
            b"# Memory\r\nused_memory:100\r\nused_memory_rss:200\r\nmaxmemory:268435456\r\n"
            b"# Stats\r\nevicted_keys:4\r\n# Clients\r\nconnected_clients:3\r\n")
        self.assertEqual(values, {"used_memory": 100, "used_memory_rss": 200,
                                  "maxmemory": 268435456, "evicted_keys": 4, "connected_clients": 3})
        self.assertEqual(monitor_agent.docker_bytes("128.5MiB"), 134_742_016)
        for payload in (b"used_memory:not-a-number\n", b"# Memory\nused_memory:1\n"):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                monitor_agent.redis_info_fields(payload)
        with self.assertRaises(ValueError):
            monitor_agent.docker_bytes("999MB-or-more")

    def test_redis_material_keeps_the_server_key_only_on_b_and_acl_restricts_namespace(self):
        runtime, _, _, _ = self.configuration()
        identity = runtime["redis_identity_fixture"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            release = root / "release"
            (release / "redis").mkdir(parents=True)
            (release / "redis/redis.conf").write_text("maxmemory 256mb\n", encoding="ascii")
            with (patch.object(vm_deploy, "BASE", root / "base"),
                  patch.object(vm_deploy.os, "chown", create=True)):
                directory, a_fingerprint = vm_deploy.configure_redis_files(release, identity, "a")
                self.assertFalse((directory / "server.key").exists())
                self.assertFalse((directory / "server.crt").exists())
                acl = (directory / "users.acl").read_text(encoding="ascii")
                self.assertIn("~nexoruta:nexoruta-gcp-demo:cache:v1:*", acl)
                self.assertIn("-@all", acl)
                self.assertNotIn(identity["password"], acl)
                self.assertNotIn("flushdb", acl.lower())

                directory, b_fingerprint = vm_deploy.configure_redis_files(release, identity, "b")
                self.assertTrue((directory / "server.key").is_file())
                self.assertTrue((directory / "server.crt").is_file())
                self.assertEqual(a_fingerprint, b_fingerprint)
                if os.name == "posix":
                    self.assertEqual((directory / "server.key").stat().st_mode & 0o777, 0o440)

    def test_prepare_acquires_lock_before_downloading_manifest(self):
        args = SimpleNamespace(release="release-" + "a" * 32, deadline=2000, stage="prepare", node="a", bucket="demo")
        lock = Mock()
        with (tempfile.TemporaryDirectory() as temp,
            patch.object(vm_deploy, "BASE", Path(temp)),
            patch.object(vm_deploy.time, "time", return_value=1000),
            patch.object(vm_deploy.os, "umask"),
            patch("builtins.open", unittest.mock.mock_open()),
            patch.dict(sys.modules, {"fcntl": SimpleNamespace(flock=lock, LOCK_EX=2)}),
            patch.object(vm_deploy, "object_bytes", side_effect=RuntimeError("reached download")),
        ):
            with self.assertRaisesRegex(RuntimeError, "reached download"):
                vm_deploy.run_stage(args)
            lock.assert_called_once()

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

    def test_mail_smoke_retries_transient_error_but_requires_401(self):
        endpoints = {name: f"https://{name}.example.test" for name in
                     ("api", "admin", "backoffice", "commerce", "tracking", "monitor", "mail")}
        response = Mock()
        response.__enter__ = Mock(return_value=SimpleNamespace(status=200))
        response.__exit__ = Mock(return_value=False)
        mail_statuses = iter((503, 401))

        def open_url(url, timeout):
            if url == endpoints["mail"] + "/":
                raise urllib.error.HTTPError(url, next(mail_statuses), "error", {}, None)
            if "/api/search?" in url:
                raise urllib.error.HTTPError(url, 401, "unauthorized", {}, None)
            return response

        with (patch.object(vm_deploy.urllib.request, "urlopen", side_effect=open_url),
              patch.object(vm_deploy.time, "sleep") as sleep):
            vm_deploy.smoke({"endpoints": endpoints}, check_accounts=False)
        sleep.assert_called_once_with(5)

    def test_failed_measure_records_phase(self):
        timings = {}
        with self.assertRaises(RuntimeError) as caught:
            vm_deploy.measure(timings, "public_https_and_login_smoke", lambda: (_ for _ in ()).throw(RuntimeError()))
        self.assertEqual(caught.exception.nexoruta_phase, "public_https_and_login_smoke")
        self.assertIn("public_https_and_login_smoke", timings)

    def test_mail_smoke_rejects_public_access_and_reports_http_status(self):
        endpoints = {name: f"https://{name}.example.test" for name in
                     ("api", "admin", "backoffice", "commerce", "tracking", "monitor", "mail")}
        response = Mock()
        response.__enter__ = Mock(return_value=SimpleNamespace(status=200))
        response.__exit__ = Mock(return_value=False)

        def open_url(url, timeout):
            if "/api/search?" in url:
                raise urllib.error.HTTPError(url, 401, "unauthorized", {}, None)
            return response

        with patch.object(vm_deploy.urllib.request, "urlopen", side_effect=open_url):
            with self.assertRaises(vm_deploy.MailSmokeError) as caught:
                vm_deploy.smoke({"endpoints": endpoints}, check_accounts=False)
        self.assertEqual(caught.exception.http_status, 200)

    def test_release_extraction_makes_only_grafana_provisioning_readable_by_its_container_user(self):
        if os.name != "posix":
            self.skipTest("The runtime permission-bit contract is enforced on the Linux deployment host")
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

    def test_release_extraction_rejects_paths_and_links(self):
        for member in (
            ("../escape.txt", tarfile.REGTYPE, None),
            ("link", tarfile.SYMTYPE, "../../escape.txt"),
        ):
            archive_data = io.BytesIO()
            with tarfile.open(fileobj=archive_data, mode="w:gz") as archive:
                info = tarfile.TarInfo(member[0])
                info.type = member[1]
                info.linkname = member[2] or ""
                info.size = 1 if info.type == tarfile.REGTYPE else 0
                archive.addfile(info, io.BytesIO(b"x") if info.size else None)
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "release"
                root.mkdir()
                with self.assertRaisesRegex(ValueError, "Unsafe release archive"):
                    vm_deploy.extract(archive_data.getvalue(), root)
                self.assertFalse((Path(directory) / "escape.txt").exists())

    def configuration(self):
        registry = "southamerica-west1-docker.pkg.dev/demo-project/nexoruta"
        passwords = {name: "private-" + name for name in (
            "migrator", "api", "worker", "bootstrap", "rabbit", "mongo", "mail", "monitor", "grafana",
            "keys_api", "keys_admin", "keys_backoffice", "keys_commerce", "keys_tracking", "admin", "operator", "commerce")}
        runtime = {"project_id": "demo-project", "sql_connection": "demo-project:region:sql", "registry": registry,
                   "services_host": "10.0.0.1", "frontend_ip": "34.0.0.1", "subnet_cidr": "10.0.0.0/24",
                   "nodes": {"a": {"name": "nexoruta-demo", "zone": "southamerica-west1-a"},
                             "b": {"name": "nexoruta-demo-b", "zone": "southamerica-west1-b"}},
                   "redis": {"host": "nexoruta-demo-b.southamerica-west1-b.c.demo-project.internal", "port": 6378},
                   "passwords": passwords, "keys": {name: "key" for name in ("jwt", "tracking", "push", "evidence")},
                   "endpoints": {name: f"https://{name}.34-0-0-1.sslip.io" for name in (
                       "api", "admin", "backoffice", "commerce", "tracking", "mail", "monitor")},
                   "organization_ids": {"operator": "operator-id", "commerce": "commerce-id"}}
        integrations = {"smtp_host": "mailpit", "smtp_port": 1025, "smtp_ssl": False,
                        "smtp_from": "demo@example.test", "monitor_google_client_id": "oauth-client",
                        "monitor_google_client_secret": "private-oauth", "monitor_allowed_emails": ["reader@example.test"],
                        "cache_enabled": "true"}
        hosting = {"grafana_secret_key": "private-grafana-key", "certificate_password": "private-pfx",
                   "certificate_pfx": "cGZ4"}
        images = {name: registry + "/" + name + "@sha256:" + "a" * 64 for name in (
            "api", "worker", "admin", "backoffice", "commerce", "tracking")}
        runtime["redis_identity_fixture"] = {
            "dns_name": runtime["redis"]["host"],
            "password": "private-redis-auth-" + "x" * 48,
            "ca_certificate": "-----BEGIN CERTIFICATE-----\nfixture\n-----END CERTIFICATE-----\n",
            "server_certificate": "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n",
            "server_private_key": "-----BEGIN PRIVATE KEY-----\nprivate\n-----END PRIVATE KEY-----\n",
        }
        return runtime, integrations, hosting, images

    def test_shared_environment_preserves_identity_and_restricts_keys_and_google_access(self):
        runtime, integrations, hosting, images = self.configuration()
        values = vm_deploy.environment(runtime, integrations, images, "hash", hosting, "b", "10.0.0.2",
                                       "release-" + "a" * 32, ("172.22.0.0/16",), runtime["redis_identity_fixture"])
        self.assertEqual(values["SMTP_HOST"], "10.0.0.1")
        self.assertEqual(values["REDIS_HOST"], runtime["redis"]["host"])
        self.assertEqual(values["REDIS_AUTH"], runtime["redis_identity_fixture"]["password"])
        self.assertEqual(values["REDIS_PORT"], 6378)
        import base64
        expected_ca = base64.b64encode(runtime["redis_identity_fixture"]["ca_certificate"].encode()).decode()
        self.assertEqual(json.loads(values["REDIS_CA_CERTIFICATES_BASE64_JSON"]), [expected_ca])
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
                                          "release-" + "a" * 32, subnets, runtime["redis_identity_fixture"])

    def test_shared_environment_requires_private_authenticated_tls_redis(self):
        runtime, integrations, hosting, images = self.configuration()
        original = runtime["redis"]
        invalid = (
            ({**original, "host": "redis.attacker.example"}, runtime["redis_identity_fixture"]),
            ({**original, "port": 6379}, runtime["redis_identity_fixture"]),
            (original, {**runtime["redis_identity_fixture"], "password": "short"}),
            (original, {**runtime["redis_identity_fixture"], "dns_name": "redis.attacker.example"}),
        )
        for redis, identity in invalid:
            with self.subTest(redis=redis):
                runtime["redis"] = redis
                with self.assertRaises(ValueError):
                    vm_deploy.environment(runtime, integrations, images, "hash", hosting, "a", "10.0.0.1",
                                          "release-" + "a" * 32, redis_identity=identity)
        runtime["redis"] = original

    def test_shared_environment_allows_empty_redis_credentials_only_in_explicit_bypass(self):
        runtime, integrations, hosting, images = self.configuration()
        integrations["cache_enabled"] = "false"
        values = vm_deploy.environment(runtime, integrations, images, "hash", hosting, "a", "10.0.0.1",
                                       "release-" + "a" * 32, ("172.22.0.0/16",), redis_identity=None)
        self.assertEqual(values["REDIS_AUTH"], "")
        self.assertEqual(json.loads(values["REDIS_CA_CERTIFICATES_BASE64_JSON"]), [])
        self.assertEqual(values["NEXORUTA_CACHE_ENABLED"], "false")

        integrations["cache_enabled"] = "true"
        with self.assertRaisesRegex(ValueError, "Enabled Redis requires"):
            vm_deploy.environment(runtime, integrations, images, "hash", hosting, "a", "10.0.0.1",
                                  "release-" + "a" * 32, ("172.22.0.0/16",), redis_identity=None)

    def test_cache_bypass_configuration_is_strict(self):
        self.assertTrue(vm_deploy.caching_enabled({}))
        self.assertTrue(vm_deploy.caching_enabled({"cache_enabled": "TRUE"}))
        self.assertFalse(vm_deploy.caching_enabled({"cache_enabled": "false"}))
        for value in (True, "yes", "", None):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "true or false"):
                vm_deploy.caching_enabled({"cache_enabled": value})

    def test_monitor_config_accepts_only_private_vm_b_tls_endpoint(self):
        config = {"node": "a", "project_id": "demo-project", "private_ip": "10.0.0.2",
                  "services_host": "10.0.0.1",
                  "redis_host": "nexoruta-demo-b.southamerica-west1-b.c.demo-project.internal",
                  "redis_port": 6378, "redis_zone": "southamerica-west1-b", "redis_subnet_cidr": "10.0.0.0/24"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "monitor.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            resolved = [(2, 1, 6, "", ("10.0.0.3", 6378))]
            with patch.object(monitor_agent.socket, "getaddrinfo", return_value=resolved):
                self.assertEqual(monitor_agent.read_config(path), config)
            for invalid in ({**config, "redis_port": 6379}, {**config, "redis_host": "redis.attacker.example"},
                            {**config, "redis_subnet_cidr": "192.168.0.0/24"}):
                path.write_text(json.dumps(invalid), encoding="utf-8")
                with (self.subTest(invalid=invalid), patch.object(monitor_agent.socket, "getaddrinfo", return_value=resolved),
                      self.assertRaises(ValueError)):
                    monitor_agent.read_config(path)

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
        self.assertIn("prometheus-write-gateway", vm_deploy.SHARED)
        self.assertIn("prometheus-write-gateway", vm_deploy.OBSERVABILITY_CORE)
        runtime, integrations, hosting, images = self.configuration()
        with tempfile.TemporaryDirectory() as directory, patch.object(vm_deploy, "BASE", Path(directory)):
            root = Path(directory)
            release = root / "release"
            release.mkdir()
            (release / "monitor_agent.py").write_text("# collector")
            (release / "monitoring").mkdir()
            (release / "monitoring/ops-agent.yaml").write_text("metrics: {}")
            (release / "redis").mkdir()
            (release / "redis/redis.conf").write_text("maxmemory 256mb\n")
            deployment = vm_deploy.Deploy(release, io.StringIO())
            services = vm_deploy.SHARED
            identifiers = [f"container-{index}" for index in range(len(services))]
            events = []
            def execute(*args, **kwargs):
                if args[:2] == ("docker", "run"):
                    return "hash"
                if args[:2] == ("docker", "ps"):
                    return "\n".join(identifiers)
                if args[:2] == ("docker", "inspect"):
                    return services[identifiers.index(args[-1])]
                if args[:3] == ("systemctl", "restart", "google-cloud-ops-agent"):
                    self.assertEqual((root / "ops-agent.yaml").read_text(), "metrics: {}")
                    events.append("restart_ops_agent")
                return ""
            deployment.execute = Mock(side_effect=execute)
            deployment.compose = Mock(side_effect=lambda *args, **kwargs: events.append(("compose", *args)))
            args = SimpleNamespace(node="a", release="release-" + "a" * 32, deadline=12345)
            response = Mock()
            response.__enter__ = Mock(return_value=SimpleNamespace(status=200))
            response.__exit__ = Mock(return_value=False)
            with (patch.object(vm_deploy, "token", return_value="token"),
                  patch.object(vm_deploy, "bridge_subnets", return_value=["172.22.0.0/16"]),
                  patch.object(vm_deploy, "redis_addresses", return_value={"10.0.0.3"}),
                  patch.object(vm_deploy, "configure_redis_files", return_value=(root / "redis", "fingerprint")),
                  patch.object(vm_deploy, "OPS_AGENT_CONFIG", root / "ops-agent.yaml"),
                  patch.object(vm_deploy.urllib.request, "urlopen", return_value=response) as urlopen):
                result = vm_deploy.prepare(args, deployment, runtime, integrations, hosting,
                                           runtime["redis_identity_fixture"], {"images": images}, "10.0.0.1")
            self.assertEqual(result, {"cache_enabled": True, "redis_node": "b", "redis_port": 6378,
                                      "redis_server_reconciled": False})
            up_calls = [call.args for call in deployment.compose.call_args_list if "up" in call.args]
            self.assertIn(("up", "-d", "--wait", "--wait-timeout", "300", "sql-proxy"), up_calls)
            self.assertIn(("--profile", "shared", "up", "-d", "--no-deps", "--force-recreate",
                           "--wait", "--wait-timeout", "300", "proxy"), up_calls)
            started = [call.args[-1] for call in deployment.execute.call_args_list if call.args[:2] == ("docker", "start")]
            retained = {identifier for service, identifier in zip(services, identifiers)
                        if service not in ("proxy", *vm_deploy.OBSERVABILITY_CORE)}
            self.assertEqual(set(started), retained)
            self.assertIn(("--profile", "shared", "up", "-d", "--no-deps", "--force-recreate",
                           "--wait", "--wait-timeout", "300", *vm_deploy.OBSERVABILITY_CORE), up_calls)
            observability_reconcile = ("compose", "--profile", "shared", "up", "-d", "--no-deps",
                                       "--force-recreate", "--wait", "--wait-timeout", "300",
                                       *vm_deploy.OBSERVABILITY_CORE)
            self.assertLess(events.index("restart_ops_agent"), events.index(observability_reconcile))
            request = urlopen.call_args.args[0]
            self.assertEqual(request.full_url, "http://10.0.0.1:18025/healthz")
            self.assertEqual(request.get_header("Host"), "mail.34-0-0-1.sslip.io")
            for call in deployment.execute.call_args_list:
                self.assertNotIn(runtime["passwords"]["mail"], call.args)
            config = json.loads((root / "monitor.json").read_text())
            self.assertEqual(config["expires_at"], args.deadline)
            self.assertEqual(config["redis_host"], runtime["redis"]["host"])
            self.assertEqual(config["redis_port"], runtime["redis"]["port"])
            self.assertEqual(config["redis_zone"], runtime["nodes"]["b"]["zone"])
            self.assertEqual(config["redis_subnet_cidr"], runtime["subnet_cidr"])
            if os.name == "posix":
                self.assertEqual((release / "hosting.pfx").stat().st_mode & 0o777, 0o600)

    def test_prepare_with_cache_bypass_does_not_require_or_start_redis_on_b(self):
        runtime, integrations, hosting, images = self.configuration()
        integrations["cache_enabled"] = "false"
        with tempfile.TemporaryDirectory() as directory, patch.object(vm_deploy, "BASE", Path(directory)):
            root = Path(directory)
            release = root / "release"
            release.mkdir()
            (release / "monitor_agent.py").write_text("# collector")
            (release / "monitoring").mkdir()
            (release / "monitoring/ops-agent.yaml").write_text("metrics: {}")
            (release / "redis").mkdir()
            (release / "redis/redis.conf").write_text("maxmemory 256mb\n")
            deployment = vm_deploy.Deploy(release, io.StringIO())
            deployment.execute = Mock(side_effect=lambda *args, **kwargs: "hash" if args[:2] == ("docker", "run") else "")
            deployment.compose = Mock()
            args = SimpleNamespace(node="b", release="release-" + "a" * 32, deadline=12345)

            with (patch.object(vm_deploy, "token", return_value="token"),
                  patch.object(vm_deploy, "bridge_subnets", return_value=["172.22.0.0/16"]),
                  patch.object(vm_deploy, "redis_addresses") as redis_addresses,
                  patch.object(vm_deploy, "configure_redis_files") as configure_redis_files,
                  patch.object(vm_deploy, "OPS_AGENT_CONFIG", root / "ops-agent.yaml"),
                  patch.object(vm_deploy.socket, "gethostbyname", return_value="10.0.0.1")):
                result = vm_deploy.prepare(args, deployment, runtime, integrations, hosting,
                                           runtime["redis_identity_fixture"], {"images": images}, "10.0.0.2")

            redis_addresses.assert_not_called()
            self.assertFalse(result["cache_enabled"])
            self.assertFalse(result["redis_server_reconciled"])
            configure_redis_files.assert_not_called()
            calls = [call.args for call in deployment.compose.call_args_list]
            self.assertNotIn(("--profile", "cache-b", "pull", "redis"), calls)
            self.assertNotIn(("--profile", "cache-b", "config", "--quiet"), calls)
            self.assertFalse(any("up" in call and "redis" in call for call in calls))
            self.assertTrue(any("up" in call and "sql-proxy" in call for call in calls))


if __name__ == "__main__":
    unittest.main()
