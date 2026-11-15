import io
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import delivery
import integration
import demo_session as session
import bootstrap_setup
import image_inventory
import github_environment
import load_tests as load_test_control
import monitor_agent
import vm_deploy
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


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict("os.environ", {"GITHUB_ACTIONS": "false"})
        environment.start()
        self.addCleanup(environment.stop)

    def test_isolated_project_builds_every_image_without_mutating_the_tested_ci_plan(self):
        plan = {"images": ["api"], "publish_required": True}
        self.assertEqual(delivery.selected_build_services(plan), ["api"])
        self.assertEqual(delivery.selected_build_services(plan, reproduction=True), list(delivery.SERVICES))
        self.assertEqual(plan["images"], ["api"])
        for invalid in ({"images": "api"}, {"images": ["api", "api"]},
                        {"images": ["unknown"]}, {"images": [{"name": "api"}]}):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "invalid image selection"):
                delivery.selected_build_services(invalid, reproduction=True)

    def test_load_balancer_health_wait_has_wall_clock_limit(self):
        with (patch.object(delivery.time, "monotonic", side_effect=[0, 0, 0, 301]),
              patch.object(delivery.time, "time", return_value=1000),
              patch.object(delivery.time, "sleep") as sleep):
            with self.assertRaisesRegex(RuntimeError, "not admitted"):
                delivery.wait_for_load_balancer_health({"NODE_ID": "a"}, 2000, lambda node: False)
        sleep.assert_called_once_with(5)

    def test_load_balancer_health_retries_transient_query_errors(self):
        health = Mock(side_effect=[subprocess.CalledProcessError(1, "gcloud"), False, True])
        with (patch.object(delivery.time, "monotonic", side_effect=[0, 0, 0, 5, 5, 10]),
              patch.object(delivery.time, "time", return_value=1000),
              patch.object(delivery.time, "sleep") as sleep):
            delivery.wait_for_load_balancer_health({"NODE_ID": "b"}, 2000, health)

        self.assertEqual(health.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_cache_bypass_skips_redis_smokes_and_requires_both_nodes_to_agree(self):
        inventory = [{"NODE_ID": "a"}, {"NODE_ID": "b"}]
        stage = Mock(side_effect=AssertionError("Redis must not be probed in bypass mode"))
        measure = Mock(side_effect=lambda _name, operation, **_kwargs: operation())

        self.assertFalse(delivery.prepared_cache_mode([
            {"cache_enabled": False}, {"cache_enabled": False}]))
        nodes = [{"NODE_ID": "a"}, {"NODE_ID": "b"}]
        host_record = valid_host_versions()
        host_map = delivery.prepared_host_versions(nodes, [
            {"host_versions": host_record}, {"host_versions": host_record},
        ])
        self.assertEqual(host_map, {"a": host_record, "b": host_record})
        with self.assertRaisesRegex(ValueError, "host version record"):
            delivery.prepared_host_versions(nodes, [{}, {"host_versions": host_record}])
        self.assertEqual(delivery.redis_smoke_clients_if_enabled(False, inventory, stage, measure), [])
        stage.assert_not_called()
        measure.assert_not_called()
        with self.assertRaisesRegex(RuntimeError, "same cache mode"):
            delivery.prepared_cache_mode([{"cache_enabled": False}, {"cache_enabled": True}])
        with self.assertRaisesRegex(RuntimeError, "same cache mode"):
            delivery.prepared_cache_mode([{"cache_enabled": False}, {}])

    def test_bootstrap_stops_after_one_profile_limit_error_without_sleeping(self):
        config = {"GCP_PROJECT_ID": "demo-project", "GCP_STATE_BUCKET": "demo-state",
                  "GCP_ZONE": "southamerica-west1-a"}
        ssh_calls = []

        def command(*args, capture=False):
            if args[:3] == ("gcloud", "storage", "cat"):
                return json.dumps({"expires_at": 2000})
            if args[:3] == ("gcloud", "compute", "ssh"):
                ssh_calls.append(args)
                self.assertTrue(capture)
                raise subprocess.CalledProcessError(1, "gcloud", stderr="Login profile size exceeds 32 KiB")
            raise AssertionError(args)

        with (patch.object(session, "command", side_effect=command),
              patch.object(delivery.time, "time", return_value=1000),
              patch.object(delivery.time, "sleep") as sleep):
            with self.assertRaisesRegex(RuntimeError, "OS Login SSH profile"):
                delivery.deploy(config, "release-" + "a" * 32)
        self.assertEqual(len(ssh_calls), 1)
        sleep.assert_not_called()

    def test_release_extraction_rejects_path_traversal_and_links(self):
        for name, kind in (("../outside", tarfile.REGTYPE), ("link", tarfile.SYMTYPE)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                data = io.BytesIO()
                with tarfile.open(fileobj=data, mode="w:gz") as archive:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    archive.addfile(member)
                with self.assertRaises(ValueError):
                    vm_deploy.extract(data.getvalue(), Path(temp))

    def test_local_and_gcp_grafana_use_the_shared_prometheus_dashboard(self):
        root = Path(__file__).parents[2]
        canonical_alerts = root / "deploy/observability/prometheus/alerts.yaml"
        gcp_alerts = root / "deploy/gcp/monitoring/alerts.yaml"
        self.assertEqual(canonical_alerts.read_bytes(), gcp_alerts.read_bytes())

        canonical = root / "deploy/observability/grafana/nexoruta.json"
        gcp_copy = root / "deploy/gcp/grafana/provisioning/dashboards/nexoruta.json"
        self.assertEqual(canonical.read_bytes(), gcp_copy.read_bytes())

        dashboard = json.loads(canonical.read_text(encoding="utf-8"))
        self.assertEqual(dashboard["uid"], "nexoruta-demo")

        panels = []

        def collect(items):
            for panel in items:
                if panel["type"] != "row":
                    panels.append(panel)
                collect(panel.get("panels", []))

        collect(dashboard["panels"])
        datasource_types = {
            datasource["type"]
            for panel in panels
            for datasource in [panel.get("datasource", {})]
            + [target.get("datasource", {}) for target in panel.get("targets", [])]
            if datasource.get("type")
        }
        self.assertEqual(datasource_types, {"prometheus", "loki"})

        by_title = {panel.get("title"): panel for panel in panels}
        self.assertIn("Porcentaje total ponderado", by_title)
        self.assertIn("Hits y misses en el rango", by_title)
        self.assertIn("Series de telemetría de caché", by_title)
        self.assertIn("$__range", by_title["Hits y misses en el rango"]["targets"][0]["expr"])
        self.assertIn("hit|miss", by_title["Porcentaje total ponderado"]["targets"][0]["expr"])
        self.assertEqual(by_title["Series de telemetría de caché"]["fieldConfig"]["defaults"]["noValue"],
                         "Sin telemetría")
        self.assertIn("Redis B: salud TLS/AUTH", by_title)
        rabbit_queue = by_title["Mensajes pendientes por cola RabbitMQ"]
        rabbit_query = rabbit_queue["targets"][0]["expr"]
        self.assertIn("rabbitmq_detailed_queue_messages", rabbit_query)
        self.assertIn("nexoruta_gcp_rabbit_queue_pending", rabbit_query)
        self.assertIn("label_replace", rabbit_query)
        queue_depth = by_title["Profundidad de cola · RabbitMQ y Kafka"]
        self.assertIn("nexoruta_gcp_kafka_lag", queue_depth["targets"][1]["expr"])
        offset_status = by_title["Kafka recovery · offset confirmado"]
        self.assertIn("nexoruta_gcp_kafka_group_offset_committed", offset_status["targets"][0]["expr"])
        self.assertIn("Sin commit", str(offset_status["fieldConfig"]["defaults"]["mappings"]))
        gcp_metrics = (root / "deploy/gcp/monitoring/gcp-metrics-collector.yaml").read_text(encoding="utf-8")
        self.assertIn("custom.googleapis.com/nexoruta/kafka_group_offset_committed", gcp_metrics)
        self.assertIn("nexoruta_gcp_kafka_group_offset_committed", gcp_metrics)

        gcp_row = next(panel for panel in dashboard["panels"]
                       if panel.get("title") == "Infraestructura GCP · Prometheus")
        self.assertTrue(gcp_row["collapsed"])
        datasource_config = (root / "deploy/gcp/grafana/provisioning/datasources/observability.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("deleteDatasources:", datasource_config)
        self.assertIn("name: Google Cloud Monitoring", datasource_config)

    def test_remote_telemetry_bounds_backlog_memory_and_retry_time(self):
        root = Path(__file__).parents[2]
        prometheus = (root / "deploy/gcp/monitoring/prometheus.yaml").read_text(encoding="utf-8")
        collector = (root / "deploy/gcp/monitoring/otel-collector.yaml").read_text(encoding="utf-8")
        compose = (root / "deploy/gcp/compose.yaml").read_text(encoding="utf-8")
        local = (root / "compose.override.yaml").read_text(encoding="utf-8")
        self.assertIn("storage:\n  tsdb:\n    out_of_order_time_window: 6h", prometheus)
        self.assertIn("max_elapsed_time: 5m", collector)
        self.assertIn("processors: [memory_limiter, filter/drop_stale_metrics, resource/node, batch]", collector)
        self.assertIn("limit_mib: 384", collector)
        self.assertIn("spike_limit_mib: 64", collector)
        self.assertIn("directory: /var/lib/otelcol/prometheusremotewrite-v2", collector)
        collector_image = "otel/opentelemetry-collector-contrib:0.165.0"
        self.assertIn(f"  otel-collector:\n    image: {collector_image}", compose)
        self.assertIn(f"  otel-collector:\n    image: {collector_image}", local)
        self.assertIn("GOMEMLIMIT: 300MiB", compose)
        self.assertRegex(compose, r"otel-collector:\n(?:[^\n]*\n){0,5}\s+mem_limit: 512m")
        self.assertIn("- otelcol:/var/lib/otelcol", compose)
        self.assertIn("redis:7.2.16-alpine3.21@sha256:f2c5eb3d970536f4bd6538875f650cc8482284fc828d7de20fd25a5f16fa7fdc", compose)
        self.assertIn("mem_limit: 512m", compose)
        self.assertIn("memswap_limit: 512m", compose)
        self.assertIn("cpus: 1.0", compose)
        self.assertIn("- cache-b", compose)
        redis_config = (root / "deploy/gcp/redis/redis.conf").read_text(encoding="utf-8")
        self.assertIn("port 0", redis_config)
        self.assertIn("tls-port 6378", redis_config)
        self.assertIn('save ""', redis_config)
        self.assertIn("maxmemory 256mb", redis_config)

    def test_http_webhook_worker_is_wired_into_local_and_remote_lifecycle(self):
        root = Path(__file__).parents[2]
        base_local = (root / "compose.yaml").read_text(encoding="utf-8")
        local = (root / "compose.override.yaml").read_text(encoding="utf-8")
        local_demo = (root / "compose.webhooks-demo.yaml").read_text(encoding="utf-8")
        remote = (root / "deploy/gcp/compose.yaml").read_text(encoding="utf-8")
        alerts = (root / "deploy/observability/prometheus/alerts.yaml").read_text(encoding="utf-8")

        self.assertIn("worker-webhooks:", local)
        self.assertRegex(local, r"worker-webhooks:\n\s+environment:\n\s+<<: \*otel-settings")
        self.assertRegex(local, r"worker-webhooks:[\s\S]{0,240}rls-role-provisioner:")
        self.assertRegex(base_local, r"worker-webhooks:[\s\S]{0,1000}healthcheck:")
        self.assertIn("Webhooks__AllowedOrigins: ${NEXORUTA_WEBHOOK_ALLOWED_ORIGINS:-}", base_local)
        self.assertIn("Webhooks__AllowAnyPublicHttpsOrigin: ${NEXORUTA_WEBHOOK_ALLOW_ANY_PUBLIC_HTTPS_ORIGIN:-false}", base_local)
        self.assertIn("Webhooks__AllowAnyPublicHttpsOrigin: ${NEXORUTA_WEBHOOK_ALLOW_ANY_PUBLIC_HTTPS_ORIGIN:-true}", local)
        self.assertIn("Webhooks__DevelopmentReceiverUrl", local_demo)
        self.assertIn("worker-webhooks:", remote)
        self.assertIn("Webhooks__AllowedOrigins: ${WEBHOOK_ALLOWED_ORIGINS:-}", remote)
        self.assertIn("Webhooks__AllowAnyPublicHttpsOrigin: ${WEBHOOK_ALLOW_ANY_PUBLIC_HTTPS_ORIGIN:-false}", remote)
        self.assertIn("Messaging__Transport: HttpWebhooks", remote)
        self.assertIn("worker-webhooks", vm_deploy.APPS)
        self.assertIn("worker-webhooks", monitor_agent.APPLICATIONS)
        self.assertIn('"worker-webhooks"', (root / "scripts/gcp/load_tests.py").read_text(encoding="utf-8"))
        self.assertIn("worker-webhooks", alerts)
        self.assertIn("NexoRutaCommerceWebhookTerminalFailures", alerts)
        self.assertIn("NexoRutaMobileSyncSnapshotUnavailable", alerts)

    def test_webhook_origins_are_exact_https_origins_and_flow_to_compose(self):
        self.assertEqual(github_environment.parse_webhook_allowed_origins(
            "https://merchant.example.test:443; https://events.example.test:8443/"),
            ["https://events.example.test:8443", "https://merchant.example.test"])
        self.assertEqual(github_environment.parse_webhook_allowed_origins(""), [])
        self.assertTrue(github_environment.parse_allow_any_public_https_origin("true"))
        self.assertFalse(github_environment.parse_allow_any_public_https_origin("false"))
        with self.assertRaises(ValueError):
            github_environment.parse_allow_any_public_https_origin("sometimes")
        for invalid in (
            "http://merchant.example.test", "https://merchant.example.test/hooks",
            "https://user@merchant.example.test", "https://merchant.example.test?token=x",
            "https://merchant.example.test:", "https://*.example.test", "https://[broken-ipv6",
            "https://merchant..example.test", "https://-merchant.example.test",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                github_environment.parse_webhook_allowed_origins(invalid)

    def test_load_test_dashboard_is_in_the_gcp_delivery_bundle(self):
        root = Path(__file__).parents[2]
        canonical_alerts = root / "deploy/observability/prometheus/alerts.yaml"
        dashboard_path = root / "deploy/observability/grafana/load-tests.json"
        dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
        self.assertEqual(dashboard["uid"], "nexoruta-load-tests")
        self.assertIn("run_id", {item["name"] for item in dashboard["templating"]["list"]})
        titles = {panel.get("title") for panel in dashboard["panels"]}
        self.assertIn("CPU del generador k6", titles)
        self.assertIn("Memoria del generador k6", titles)

        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp) / "source"
            shutil.copytree(root / "deploy/gcp", fixture / "deploy/gcp")
            (fixture / "deploy/observability/grafana").mkdir(parents=True)
            shutil.copyfile(root / "deploy/observability/grafana/nexoruta.json",
                            fixture / "deploy/observability/grafana/nexoruta.json")
            shutil.copyfile(dashboard_path, fixture / "deploy/observability/grafana/load-tests.json")
            runtime_roles = fixture / "backend/scripts/provision-rls-runtime-roles.sql"
            runtime_roles.parent.mkdir(parents=True)
            runtime_roles.write_text("-- Test fixture; runtime roles are supplied by migrations.\n")
            migrations = fixture / "backend/src/NexoRuta.Infrastructure/Persistence/Migrations"
            migrations.mkdir(parents=True)
            (migrations / "0001_TestRoles.cs").write_text(
                "CREATE ROLE nexoruta_schema_owner NOLOGIN; CREATE ROLE nexoruta_api NOLOGIN;\n"
            )
            monitor_agent = fixture / "scripts/gcp/monitor_agent.py"
            monitor_agent.parent.mkdir(parents=True)
            shutil.copyfile(root / "scripts/gcp/monitor_agent.py", monitor_agent)
            redis_identity = fixture / "scripts/gcp/redis_identity.py"
            shutil.copyfile(root / "scripts/gcp/redis_identity.py", redis_identity)

            with patch.object(delivery, "ROOT", fixture):
                bundle = delivery.create_bundle(Path(temp) / "output")
            with tarfile.open(bundle, "r:gz") as archive:
                packaged = archive.extractfile("grafana/provisioning/dashboards/load-tests.json")
                self.assertIsNotNone(packaged)
                self.assertEqual(packaged.read(), dashboard_path.read_bytes())
                packaged_alerts = archive.extractfile("monitoring/alerts.yaml")
                self.assertIsNotNone(packaged_alerts)
                self.assertEqual(packaged_alerts.read(), canonical_alerts.read_bytes())
                packaged_identity = archive.extractfile("redis_identity.py")
                self.assertIsNotNone(packaged_identity)
                self.assertEqual(packaged_identity.read(), redis_identity.read_bytes())
                self.assertIsNotNone(archive.extractfile("image-inventory.json"))
                self.assertIsNotNone(archive.extractfile("image_inventory.py"))
                self.assertIsNotNone(archive.extractfile("ci_evidence.py"))
                self.assertIsNotNone(archive.extractfile("host_versions.py"))
                self.assertIsNotNone(archive.extractfile("deployment_health.py"))
                self.assertIsNotNone(archive.extractfile("integration.py"))
                packaged_mongo_users = archive.extractfile("mongo/create-operational-users.js")
                self.assertIsNotNone(packaged_mongo_users)
                self.assertEqual(packaged_mongo_users.read(),
                                 (root / "deploy/gcp/mongo/create-operational-users.js").read_bytes())

    def test_environment_cannot_inject_additional_lines(self):
        with self.assertRaises(ValueError):
            vm_deploy.env_line("SMTP_PASSWORD", "value\nAPI_IMAGE=attacker/image")
        self.assertEqual(vm_deploy.env_line("PASSWORD", "a'b$cd"), "PASSWORD='a\\'b$cd'\n")

    def test_remote_stage_error_reports_only_the_structured_error_type(self):
        output = '\n'.join([
            '{"node":"a","stage":"prepare","status":"failed","error_type":"PermissionError","error":"sensitive"}',
            '{"node":"a","stage":"prepare","status":"failed","error_type":"invalid type; leak"}',
        ])
        self.assertEqual(
            delivery.remote_stage_error(output, "a", "prepare"),
            "Node a stage prepare failed (PermissionError)",
        )
        self.assertEqual(
            delivery.remote_stage_error('{"node":"b","stage":"apply","status":"failed"}', "a", "prepare"),
            "Node a stage prepare failed without a structured report",
        )

    def test_remote_stage_error_can_read_stderr_report(self):
        output = '{"node":"a","stage":"prepare","status":"failed","error_type":"PermissionError"}'
        self.assertEqual(
            delivery.remote_stage_error(output, "a", "prepare"),
            "Node a stage prepare failed (PermissionError)",
        )

    def test_remote_stage_error_reports_python_exception_class_only(self):
        self.assertEqual(
            delivery.remote_stage_error("Traceback:\nPermissionError: private detail", "a", "prepare"),
            "Node a stage prepare failed (PermissionError)",
        )

    def test_remote_stage_error_reports_exit_code_without_output(self):
        self.assertEqual(
            delivery.remote_stage_error("__NEXORUTA_STAGE_EXIT__=1", "a", "prepare"),
            "Node a stage prepare exited (1) without a report",
        )

    def test_remote_stage_error_reads_report_before_exit_marker(self):
        output = '\n'.join([
            '{"node":"a","stage":"prepare","status":"failed","error_type":"PermissionError"}',
            "__NEXORUTA_STAGE_EXIT__=1",
        ])
        self.assertEqual(
            delivery.remote_stage_error(output, "a", "prepare"),
            "Node a stage prepare failed (PermissionError)",
        )

    def test_remote_stage_error_reports_safe_source_location(self):
        output = '{"node":"a","stage":"prepare","status":"failed","error_type":"TypeError","error_location":"environment:177","error":"sensitive"}'
        self.assertEqual(
            delivery.remote_stage_error(output, "a", "prepare"),
            "Node a stage prepare failed (TypeError at environment:177)",
        )

    def test_vm_error_location_contains_only_function_and_line(self):
        try:
            raise TypeError("secret detail")
        except TypeError as error:
            location = vm_deploy.error_location(error)
        self.assertRegex(location, r"^test_vm_error_location_contains_only_function_and_line:[0-9]+$")

    def test_vm_main_reports_errors_before_service_setup_with_safe_location(self):
        args = vm_deploy.argparse.Namespace(release="release-" + "a" * 32, node="a", stage="prepare")

        def fail(_args, _timings=None):
            raise TypeError("private detail")

        with (patch.object(vm_deploy.argparse.ArgumentParser, "parse_args", return_value=args),
              patch.object(vm_deploy, "run_stage", side_effect=fail),
              patch("builtins.print") as print_mock):
            with self.assertRaises(SystemExit):
                vm_deploy.main()
        report = json.loads(print_mock.call_args.args[0])
        self.assertEqual(report["error_type"], "TypeError")
        self.assertRegex(report["error_location"], r"^fail:[0-9]+$")
        self.assertNotIn("private detail", print_mock.call_args.args[0])

    def test_remote_stage_error_reports_qualified_exception_class_only(self):
        self.assertEqual(
            delivery.remote_stage_error("urllib.error.HTTPError: private detail", "a", "prepare"),
            "Node a stage prepare failed (HTTPError)",
        )

    def test_drain_skips_node_already_absent_from_its_load_balancer_group(self):
        node = {"NODE_ID": "a", "VM_NAME": "nexoruta-demo"}
        with patch.object(session, "gcloud", return_value="[]") as gcloud:
            self.assertFalse(delivery.drain_node_from_group(node))
        self.assertEqual(gcloud.call_count, 1)
        self.assertEqual(gcloud.call_args.args[:5],
                         (node, "compute", "instance-groups", "unmanaged", "list-instances"))
        self.assertIn("nexoruta-demo-a", gcloud.call_args.args)
        self.assertTrue(gcloud.call_args.kwargs["capture"])

    def test_deployment_drains_and_stops_both_nodes_before_migrating(self):
        release = "release-" + "a" * 32
        nodes = [
            {"NODE_ID": "a", "VM_NAME": "nexoruta-a"},
            {"NODE_ID": "b", "VM_NAME": "nexoruta-b"},
        ]
        events = []
        bootstrap_attempts = 0

        def gcloud(node, *args, capture=False):
            nonlocal bootstrap_attempts
            if args[:2] == ("compute", "scp"):
                return ""
            if args[:3] == ("compute", "ssh", node["VM_NAME"]):
                command = args[-1]
                if "bootstrap-ready" in command and node["NODE_ID"] == "a":
                    bootstrap_attempts += 1
                    if bootstrap_attempts == 1:
                        raise subprocess.CalledProcessError(255, "gcloud", stderr="Connection refused")
                if "--stage" in command:
                    stage = command.split("--stage", 1)[1].split()[0]
                    events.append(("stage", node["NODE_ID"], stage))
                    result = {"release": release, "node": node["NODE_ID"], "stage": stage,
                              "status": "healthy", "cache_enabled": True}
                    if stage == "prepare":
                        result["host_versions"] = valid_host_versions()
                    if stage == "apply":
                        result["compose_health"] = valid_compose_health(node["NODE_ID"], True)
                    if stage == "redis-smoke":
                        result.update({"redis_node": "b", "redis_client_node": node["NODE_ID"],
                                       "redis_probe": "tls-auth-set-get-delete-passed"})
                    if stage == "verify":
                        result["endpoints"] = {"api": "https://api.example.test"}
                        result["authenticated_reads"] = [
                            {"role": role, "login": "passed", "actor_read": "passed",
                             "email": f"{role}@example.test"}
                            for role in ("admin", "operator", "commerce")
                        ]
                    return json.dumps(result)
                return ""
            if args[:4] == ("compute", "instance-groups", "unmanaged", "list-instances"):
                return json.dumps([{"instance": f"/zones/test/instances/{node['VM_NAME']}"}])
            operation = next((item for item in args if item in ("remove-instances", "add-instances")), None)
            if operation:
                events.append((operation, node["NODE_ID"]))
                return ""
            raise AssertionError(args)

        def command(*args, capture=False, timeout=None):
            if args[1:3] == ("storage", "cat"):
                return json.dumps({"expires_at": 2000})
            if args[1:3] == ("sql", "backups"):
                return ""
            if args[1:4] == ("compute", "backend-services", "get-health"):
                return json.dumps([{"status": {"healthStatus": [
                    {"instance": "/zones/test/instances/nexoruta-a", "healthState": "HEALTHY"},
                    {"instance": "/zones/test/instances/nexoruta-b", "healthState": "HEALTHY"},
                ]}}])
            raise AssertionError(args)

        config = {"GCP_PROJECT_ID": "demo-project", "GCP_STATE_BUCKET": "demo-state"}
        with (
            patch.object(session, "node_configs", return_value=nodes),
            patch.object(session, "command", side_effect=command),
            patch.object(session, "gcloud", side_effect=gcloud),
            patch.object(delivery.time, "time", return_value=1000),
            patch.object(delivery.time, "sleep", side_effect=lambda seconds: events.append(("sleep", seconds))),
        ):
            result = delivery.deploy(config, release)
        self.assertTrue(all(set(item) == {"role", "login", "actor_read"}
                            for item in result["authenticated_reads"]))

        operations = [event for event in events if event[0] in ("remove-instances", "add-instances", "stage")]
        self.assertCountEqual(operations[:2], [("stage", "a", "prepare"), ("stage", "b", "prepare")])
        self.assertEqual(operations[2:4], [("stage", "a", "redis-smoke"), ("stage", "b", "redis-smoke")])
        self.assertCountEqual(operations[4:6], [("remove-instances", "a"), ("remove-instances", "b")])
        self.assertEqual(operations[6:], [
            ("stage", "a", "stop"), ("stage", "b", "stop"), ("stage", "a", "migrate"),
            ("stage", "b", "apply"), ("add-instances", "b"),
            ("stage", "a", "apply"), ("add-instances", "a"), ("stage", "a", "verify"),
        ])
        self.assertIn(("sleep", 35), events)
        self.assertIn(("sleep", 5), events)
        self.assertEqual(bootstrap_attempts, 2)
        self.assertEqual(result["endpoints"]["api"], "https://api.example.test")
        self.assertEqual(result["redis_node"], "b")
        self.assertEqual(result["redis_smoke_clients"], ["a", "b"])
        self.assertEqual(result["host_versions"], {"a": valid_host_versions(), "b": valid_host_versions()})
        self.assertEqual(result["compose_health"], {
            "a": valid_compose_health("a"), "b": valid_compose_health("b"),
        })

    def test_invalid_release_manifest_fails_during_prepare_before_load_balancer_drain(self):
        release = "release-" + "a" * 32
        nodes = [
            {"NODE_ID": "a", "VM_NAME": "nexoruta-a"},
            {"NODE_ID": "b", "VM_NAME": "nexoruta-b"},
        ]
        events = []

        def gcloud(node, *args, capture=False):
            if args[:2] == ("compute", "scp"):
                return ""
            if args[:3] == ("compute", "ssh", node["VM_NAME"]):
                command = args[-1]
                if "bootstrap-ready" in command:
                    return ""
                if "--stage" in command:
                    operation = command.split("--stage", 1)[1].split()[0]
                    events.append(("stage", node["NODE_ID"], operation))
                    if operation == "prepare":
                        return json.dumps({
                            "release": release, "node": node["NODE_ID"], "stage": operation,
                            "status": "failed", "failed_phase": "release_manifest_validation",
                            "error_type": "ValueError",
                        })
                return ""
            operation = next((item for item in args if item in ("remove-instances", "add-instances")), None)
            if operation:
                events.append((operation, node["NODE_ID"]))
                return ""
            raise AssertionError(args)

        def command(*args, capture=False, timeout=None):
            if args[1:3] == ("storage", "cat"):
                return json.dumps({"expires_at": 2000})
            if args[1:4] == ("sql", "backups"):
                return ""
            raise AssertionError(args)

        with (
            patch.object(session, "node_configs", return_value=nodes),
            patch.object(session, "command", side_effect=command),
            patch.object(session, "gcloud", side_effect=gcloud),
            patch.object(delivery.time, "time", return_value=1000),
        ):
            with self.assertRaisesRegex(RuntimeError, "Node a stage prepare failed"):
                delivery.deploy({"GCP_PROJECT_ID": "demo-project", "GCP_STATE_BUCKET": "demo-state"}, release)

        self.assertIn(("stage", "a", "prepare"), events)
        self.assertFalse(any(event[0] in ("remove-instances", "add-instances") for event in events))
        self.assertFalse(any(event[0] == "stage" and event[2] in ("stop", "migrate", "apply") for event in events))

    def test_remote_error_reports_safe_http_status(self):
        output = json.dumps({"node": "a", "stage": "verify", "status": "failed",
                             "error_type": "MailSmokeError", "error_location": "smoke:520", "http_status": 503})
        self.assertEqual(delivery.remote_stage_error(output, "a", "verify"),
                         "Node a stage verify failed (MailSmokeError at smoke:520, HTTP 503)")

    def test_offline_update_does_not_provision_or_start_anything(self):
        config = {"DEMO_OPERATION": "update"}
        with patch.object(session, "instance", return_value=None), patch.object(session, "command") as command:
            session.run(config)
            command.assert_not_called()

    def test_active_update_preserves_the_lease_and_does_not_apply_infrastructure(self):
        vm = {
            "status": "RUNNING", "lastStartTimestamp": "fixed-start",
            "labels": {"application": "nexoruta", "managed_by": "opentofu"},
        }
        with (
            patch.dict("os.environ", {"DEMO_RELEASE": "release-" + "a" * 32}),
            patch.object(load_test_control, "assert_no_active"),
            patch.object(session, "instance", return_value=vm),
            patch.object(session, "check_deadline"),
            patch.object(bootstrap_setup, "validate_runtime_target"),
            patch.object(session, "publish_endpoints"),
            patch.object(session, "command") as command,
            patch.object(session, "write_lease") as lease,
            patch.object(delivery, "latest_release", return_value="release-" + "b" * 32) as latest,
            patch.object(delivery, "deploy") as deploy,
        ):
            config = {"DEMO_OPERATION": "update", "GCP_PROJECT_ID": "demo-project",
                      "GCP_STATE_BUCKET": "demo-state", "NEXORUTA_EXECUTION_PROFILE": "demo"}
            session.run(config)
            command.assert_not_called()
            lease.assert_not_called()
            latest.assert_called_once()
            deploy.assert_called_once_with(config, "release-" + "b" * 32)

    def test_automatic_events_cannot_operate_the_vm_even_if_a_job_is_misconfigured(self):
        for event in ("push", "repository_dispatch", "pull_request"):
            for operation in ("start", "update", "stop"):
                with (
                    self.subTest(event=event, operation=operation),
                    patch.dict("os.environ", {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": event}),
                    patch.object(session, "instance") as instance,
                    patch.object(session, "command") as command,
                ):
                    with self.assertRaisesRegex(RuntimeError, "manual workflow_dispatch"):
                        session.run({"DEMO_OPERATION": operation})
                    instance.assert_not_called()
                    command.assert_not_called()

    def test_source_resolution_defaults_to_remote_main_for_all_three_repos(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch.object(delivery, "ROOT", Path(temp)),
            patch.dict("os.environ", {}, clear=True),
            patch.object(session, "command", return_value="a" * 40 + "\n") as command,
        ):
            result = delivery.sources()
            self.assertEqual(set(result), {"backend", "frontend", "mobile"})
            fetches = [call.args for call in command.call_args_list if "fetch" in call.args]
            self.assertEqual(len(fetches), 3)
            self.assertTrue(all(call[-1] == "main" for call in fetches))

    def test_staged_frontend_receives_map_from_the_pinned_backend_archive(self):
        def archive(*args, **kwargs):
            data = io.BytesIO()
            with tarfile.open(fileobj=data, mode="w") as output:
                directory = tarfile.TarInfo(".")
                directory.type = tarfile.DIRTYPE
                directory.mode = 0o755
                output.addfile(directory)
                if args[0][2].endswith("backend"):
                    payload = b'{"type":"FeatureCollection","features":[]}'
                    member = tarfile.TarInfo("src/ZonasCobertura/Data/departamentos-uruguay.geojson")
                    member.size = len(payload)
                    output.addfile(member, io.BytesIO(payload))
                else:
                    for name, payload in (
                        ("src/NexoRuta.Commerce/NexoRuta.Commerce.csproj", b"<Project />"),
                        ("src/NexoRuta.Commerce/Pages/Inicio.razor", b"@page \"/\""),
                    ):
                        member = tarfile.TarInfo(name)
                        member.size = len(payload)
                        output.addfile(member, io.BytesIO(payload))
            return data.getvalue()

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)
            with patch.object(delivery.subprocess, "check_output", side_effect=archive):
                delivery.stage_sources(destination)
            canonical = destination / "backend/src/ZonasCobertura/Data/departamentos-uruguay.geojson"
            bundled = destination / "frontend/.build/departamentos-uruguay.geojson"
            restore_marker = destination / "frontend/.restore/src/NexoRuta.Commerce/__nexoruta_restore_shape.razor"
            self.assertEqual(canonical.read_bytes(), bundled.read_bytes())
            self.assertTrue((destination / "frontend/Dockerfile.deploy").is_file())
            self.assertTrue(restore_marker.is_file())
            self.assertTrue((destination / "frontend/src/NexoRuta.Commerce/Pages/Inicio.razor").is_file())

    def release_manifest(self):
        release = "release-" + "a" * 32
        sources = {name: char * 40 for name, char in zip(integration.COMPONENTS, "bcd")}
        inventory = image_inventory.collect(Path(__file__).parents[2])
        proof = {
            "schema_version": 1,
            "android_input_sha256": "f" * 64,
            "mobile_sha": sources["mobile"],
            "verified_by": {
                "repository_id": "123", "workflow_path": ".github/workflows/ci.yml",
                "run_id": 7, "run_attempt": 1, "event": "pull_request",
                "pull_request": 11, "base_branch": "main", "head_branch": "develop",
                "head_repository_id": "123", "root_sha": "8" * 40,
                "root_tree": "9" * 40, "sources": dict(sources),
                "artifact": {"id": 31, "name": "nfr14-ci-evidence-1",
                             "digest": "sha256:" + "a" * 64},
            },
            "origin_release": release,
        }
        ci = {
            "schema_version": 1, "repository_id": "123", "workflow_path": ".github/workflows/ci.yml",
            "run_id": 7, "run_attempt": 1, "run_number": 20, "event": "pull_request",
            "pull_request": 11, "base_branch": "main", "head_branch": "develop",
            "root_sha": "8" * 40, "release_root_sha": "c" * 40,
            "root_tree": "9" * 40, "sources": dict(sources), "android_job": "success",
            "artifact": {"id": 31, "name": "nfr14-ci-evidence-1", "digest": "sha256:" + "a" * 64},
            "plan_sha256": "f" * 64,
        }
        return {
            "manifest_version": 2,
            "project_id": "demo-project", "region": session.REGION,
            "channel": "main", "release": release,
            "images": {name: f"{session.REGION}-docker.pkg.dev/demo-project/nexoruta/{name}@sha256:" + "b" * 64
                       for name in delivery.SERVICES},
            "deployment_images": inventory,
            "deployment_images_sha256": image_inventory.checksum(inventory),
            "root_sha": "c" * 40, "sources": sources,
            "ci_evidence": ci,
            "ci_plan": {"android_input_sha256": proof["android_input_sha256"],
                        "components": {"mobile_android": {"run": True}}},
            "android_input_sha256": proof["android_input_sha256"],
            "android_verified_mobile_sha": proof["mobile_sha"],
            "android_verification": proof,
            "bundle_sha256": "e" * 64,
            "bundle_source": {"root_sha": "c" * 40, "backend_sha": sources["backend"]},
            "image_sources": {name: sources["backend"] if name in ("api", "worker") else sources["frontend"]
                              for name in delivery.SERVICES},
            "reused_images": {},
            "built_images": list(delivery.SERVICES),
            "bundle_rebuilt": True,
            "publication_order": [20, 1],
            "integration_tag": "integration-20-1",
        }

    def test_build_requires_the_pinned_tag_before_any_cloud_build(self):
        with patch.object(session, "configuration", return_value={}), patch.dict("os.environ", {
            "RELEASE_CHANNEL": "main", "INTEGRATION_TAG": "integration-123-1",
            "TESTED_CI_PLAN": "{}",
        }), patch.object(integration, "verify_checkout", side_effect=ValueError("wrong snapshot")), patch.object(session, "command") as command:
            with self.assertRaisesRegex(ValueError, "wrong snapshot"):
                delivery.build()
            command.assert_not_called()

    def test_build_manifest_and_channel_use_the_tested_integration(self):
        snapshot = {"integration_tag": "integration-123-1", "root_sha": "a" * 40,
                    "sources": {name: "b" * 40 for name in integration.COMPONENTS}}
        registry = f"{session.REGION}-docker.pkg.dev/demo-project/nexoruta"
        expected_inventory = image_inventory.collect(Path(__file__).parents[2])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / "bundle.tar.gz"
            bundle.write_bytes(b"bundle")
            outputs = root / "outputs"
            build_id_file = root / "cloud-build-id"
            step_summary = root / "summary"

            def command(*args, **kwargs):
                if args[1:3] == ("builds", "submit"):
                    config = json.loads(Path(next(a.split("=", 1)[1] for a in args if a.startswith("--config="))).read_text())
                    self.images = config["images"]
                    return json.dumps({"id": "build-123"})
                if args[1:3] == ("builds", "describe"):
                    return json.dumps({"status": "SUCCESS", "results": {"images": [
                        {"name": image, "digest": "sha256:" + "c" * 64} for image in self.images]}})
                if args[:3] == ("gcloud", "storage", "cp"):
                    self.assertIn("--if-generation-match=0", args)
                return ""

            with (patch.object(session, "configuration", return_value={"GCP_PROJECT_ID": "demo-project"}),
                  patch.object(delivery, "ROOT", root), patch.object(delivery, "stage_sources"),
                  patch.object(delivery, "create_bundle", return_value=bundle),
                  patch.object(delivery, "latest_manifest", return_value=None),
                  patch.object(image_inventory, "collect", return_value=expected_inventory),
                  patch.object(delivery.ci_evidence, "bind_for_release", side_effect=lambda *args, release, **kwargs: (
                      {"schema_version": 1}, {"schema_version": 1, "origin_release": release,
                       "android_input_sha256": "f" * 64, "mobile_sha": snapshot["sources"]["mobile"]})),
                  patch.object(integration, "verify_checkout", return_value=snapshot),
                  patch.object(session, "command", side_effect=command) as calls,
                  patch.object(delivery.publication, "promote", return_value=True) as promote,
                  patch.dict("os.environ", {"RELEASE_CHANNEL": "main", "INTEGRATION_TAG": snapshot["integration_tag"],
                                            "TESTED_CI_PLAN": json.dumps({"version": 1, "current": {"sources": snapshot["sources"]},
                                                                           "publish_required": True, "images": list(delivery.SERVICES),
                                                                           "bundle_required": True,
                                                                           "android_input_sha256": "f" * 64,
                                                                           "components": {"mobile_android": {"run": True}}}),
                                            "NEXORUTA_CI_EVIDENCE_FILE": str(root / "evidence.json"),
                                            "GITHUB_RUN_NUMBER": "20", "GITHUB_RUN_ATTEMPT": "2",
                                            "GITHUB_OUTPUT": str(outputs),
                                            "GITHUB_STEP_SUMMARY": str(step_summary),
                                            "NEXORUTA_CLOUD_BUILD_ID_FILE": str(build_id_file)})):
                delivery.build()
                manifest = json.loads((root / "release.json").read_text())
                self.assertEqual(manifest["root_sha"], snapshot["root_sha"])
                self.assertEqual(manifest["sources"], snapshot["sources"])
                self.assertEqual(manifest["integration_tag"], snapshot["integration_tag"])
                self.assertEqual(manifest["publication_order"], [20, 2])
                self.assertEqual(manifest["manifest_version"], 2)
                self.assertEqual(manifest["ci_evidence"]["schema_version"], 1)
                self.assertEqual(manifest["android_verification"]["mobile_sha"], snapshot["sources"]["mobile"])
                self.assertEqual(manifest["deployment_images_sha256"], image_inventory.checksum(expected_inventory))
                self.assertTrue(manifest["bundle_rebuilt"])
                self.assertTrue(all(image.startswith(registry) and "@sha256:" in image for image in manifest["images"].values()))
                self.assertEqual(promote.call_args.args[1]["integration_tag"], snapshot["integration_tag"])
                self.assertFalse(any(call.args[0] == "git" for call in calls.call_args_list))
                self.assertIn("manifest=", outputs.read_text())
                self.assertEqual(build_id_file.read_text().strip(), "build-123")
                self.assertIn("Cloud Build submitted: `build-123`", step_summary.read_text())

    def test_develop_build_publishes_a_full_unverified_release_to_its_own_channel(self):
        snapshot = {"root_sha": "a" * 40,
                    "sources": {name: "b" * 40 for name in integration.COMPONENTS},
                    "source_ref": "refs/heads/develop"}
        expected_inventory = image_inventory.collect(Path(__file__).parents[2])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / "bundle.tar.gz"
            bundle.write_bytes(b"develop bundle")

            def command(*args, **kwargs):
                if args[1:3] == ("builds", "submit"):
                    config_path = next(arg.split("=", 1)[1] for arg in args if arg.startswith("--config="))
                    self.images = json.loads(Path(config_path).read_text())["images"]
                    return json.dumps({"id": "develop-build"})
                if args[1:3] == ("builds", "describe"):
                    return json.dumps({"status": "SUCCESS", "results": {"images": [
                        {"name": image, "digest": "sha256:" + "c" * 64} for image in self.images]}})
                return ""

            with (patch.object(session, "configuration", return_value={"GCP_PROJECT_ID": "demo-project"}),
                  patch.object(delivery, "ROOT", root), patch.object(delivery, "stage_sources"),
                  patch.object(delivery, "create_bundle", return_value=bundle),
                  patch.object(delivery, "latest_manifest", return_value=None),
                  patch.object(image_inventory, "collect", return_value=expected_inventory),
                  patch.object(integration, "verify_develop_checkout", return_value=snapshot) as verify,
                  patch.object(session, "command", side_effect=command),
                  patch.object(delivery.publication, "promote", return_value=True) as promote,
                  patch.dict("os.environ", {"RELEASE_CHANNEL": "develop", "GITHUB_REF": "refs/heads/develop",
                                            "GITHUB_SHA": snapshot["root_sha"], "GITHUB_RUN_NUMBER": "30",
                                            "GITHUB_RUN_ATTEMPT": "1"})):
                delivery.build()

            manifest = json.loads((root / "release.json").read_text())
            self.assertEqual(verify.call_args.args, (snapshot["root_sha"],))
            self.assertEqual(len(self.images), len(delivery.SERVICES))
            self.assertEqual(manifest["channel"], "develop")
            self.assertEqual(manifest["source_ref"], "refs/heads/develop")
            self.assertNotIn("integration_tag", manifest)
            self.assertIsNone(manifest["ci_evidence"])
            self.assertIsNone(manifest["android_verification"])
            self.assertIsNone(manifest["android_input_sha256"])
            self.assertIsNone(manifest["android_verified_mobile_sha"])
            self.assertEqual(promote.call_args.args[1]["channel"], "develop")
            self.assertNotIn("integration_tag", promote.call_args.args[1])

    def test_cloud_build_cancellation_uses_the_tracked_project_and_region(self):
        with patch.object(session, "command") as command:
            delivery.cancel_cloud_build("build-to-cancel", "demo-project")
        command.assert_called_once_with("gcloud", "builds", "cancel", "build-to-cancel",
                                        "--project=demo-project", f"--region={session.REGION}", "--quiet")

    def test_build_reuses_unchanged_images_and_bundle_with_a_complete_manifest(self):
        sources = {name: char * 40 for name, char in zip(integration.COMPONENTS, "bcd")}
        snapshot = {"integration_tag": "integration-123-1", "root_sha": "a" * 40, "sources": sources}
        previous = self.release_manifest()
        previous.update(sources=sources, bundle_sha256=hashlib.sha256(b"old bundle").hexdigest(),
                        bundle_source={"root_sha": "e" * 40, "backend_sha": sources["backend"]})
        plan = {
            "version": 1, "current": {"root_sha": "f" * 40, "sources": sources},
            "publish_required": True, "bundle_required": False, "images": ["api", "worker"],
            "android_input_sha256": "1" * 64,
            "components": {"mobile_android": {"run": False}},
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            outputs = root / "outputs"
            seen = {}

            def command(*args, **kwargs):
                if args[1:3] == ("builds", "submit"):
                    config = json.loads(Path(next(a.split("=", 1)[1] for a in args if a.startswith("--config="))).read_text())
                    seen["config"] = config
                    return json.dumps({"id": "build-selective"})
                if args[1:3] == ("builds", "describe"):
                    return json.dumps({"status": "SUCCESS", "results": {"images": [
                        {"name": image, "digest": "sha256:" + "c" * 64} for image in seen["config"]["images"]]}})
                if args[1:3] == ("storage", "cp"):
                    if str(args[3]).startswith("gs://"):
                        Path(args[4]).write_bytes(b"old bundle")
                    else:
                        self.assertIn("--if-generation-match=0", args)
                return ""

            with (patch.object(session, "configuration", return_value={"GCP_PROJECT_ID": "demo-project"}),
                  patch.object(delivery, "ROOT", root), patch.object(delivery, "stage_sources"),
                  patch.object(delivery, "create_bundle") as create_bundle,
                  patch.object(delivery, "latest_manifest", return_value=previous),
                  patch.object(delivery.ci_evidence, "bind_for_release", side_effect=lambda *args, release, **kwargs: (
                      {"schema_version": 1}, {"schema_version": 1, "origin_release": release,
                       "android_input_sha256": "1" * 64, "mobile_sha": sources["mobile"]})),
                  patch.object(integration, "verify_checkout", return_value=snapshot),
                  patch.object(session, "command", side_effect=command),
                  patch.object(delivery.publication, "promote", return_value=True),
                  patch.dict("os.environ", {"RELEASE_CHANNEL": "main", "INTEGRATION_TAG": snapshot["integration_tag"],
                                            "GITHUB_RUN_NUMBER": "21", "GITHUB_RUN_ATTEMPT": "1",
                                            "NEXORUTA_CI_EVIDENCE_FILE": str(root / "evidence.json"),
                                            "TESTED_CI_PLAN": json.dumps(plan), "GITHUB_OUTPUT": str(outputs)})):
                delivery.build()

            manifest = json.loads((root / "release.json").read_text())
            self.assertEqual([step["id"] for step in seen["config"]["steps"]], ["api", "worker"])
            self.assertEqual(seen["config"]["steps"][0]["waitFor"], ["-"])
            self.assertEqual(seen["config"]["steps"][1]["waitFor"], ["api"])
            for step in seen["config"]["steps"]:
                self.assertIn("--cache-from", step["args"])
                self.assertIn("BUILDKIT_INLINE_CACHE=1", step["args"])
            self.assertEqual(manifest["images"]["admin"], previous["images"]["admin"])
            self.assertEqual(manifest["images"]["api"], f"{session.REGION}-docker.pkg.dev/demo-project/nexoruta/api@sha256:" + "c" * 64)
            self.assertEqual(set(manifest["reused_images"]), {"admin", "backoffice", "commerce", "tracking"})
            self.assertEqual(manifest["bundle_sha256"], previous["bundle_sha256"])
            create_bundle.assert_not_called()

    def test_channel_tag_and_manifest_must_match(self):
        manifest = self.release_manifest()
        manifest.update(integration_tag="integration-123-1", root_sha="a" * 40,
                        sources={name: "b" * 40 for name in integration.COMPONENTS}, publication_order=[20, 1])
        pointer = {"channel": "main", "release": manifest["release"],
                   "integration_tag": "integration-123-2", "publication_order": [20, 1]}
        with patch.object(session, "command", side_effect=[json.dumps(pointer), json.dumps(manifest)]):
            with self.assertRaisesRegex(ValueError, "snapshot"):
                delivery.latest_release({"GCP_PROJECT_ID": "demo-project"})

    def test_legacy_manifest_is_not_deployable_or_reusable(self):
        manifest = {"channel": "main", "release": "release-" + "a" * 32}
        pointer = {"channel": "main", "release": manifest["release"]}
        with patch.object(session, "command", side_effect=[json.dumps(pointer), json.dumps(manifest)]):
            with self.assertRaisesRegex(RuntimeError, "version 2 publication"):
                delivery.latest_manifest({"GCP_PROJECT_ID": "demo-project"})

    def test_update_resolves_one_complete_main_release_without_building(self):
        manifest = self.release_manifest()
        pointer = {"channel": "main", "release": manifest["release"],
                   "integration_tag": manifest["integration_tag"], "publication_order": [20, 1]}
        with patch.dict("os.environ", {"GCP_DELIVERY_BUCKET": "demo-delivery"}), patch.object(
            session, "command", side_effect=[json.dumps(pointer), json.dumps(manifest)],
        ) as command:
            self.assertEqual(delivery.latest_release({"GCP_PROJECT_ID": "demo-project"}), manifest["release"])
            self.assertEqual(command.call_count, 2)
            self.assertTrue(all(call.args[:3] == ("gcloud", "storage", "cat") for call in command.call_args_list))

    def test_update_resolves_the_isolated_develop_release_channel(self):
        manifest = self.release_manifest()
        manifest.update(channel="develop", source_ref="refs/heads/develop", root_sha="c" * 40,
                        sources={name: "d" * 40 for name in integration.COMPONENTS},
                        publication_order=[21, 1])
        manifest.update(ci_evidence=None, android_verification=None,
                        android_input_sha256=None, android_verified_mobile_sha=None,
                        image_sources={name: "d" * 40 for name in delivery.SERVICES},
                        bundle_source={"root_sha": "c" * 40, "backend_sha": "d" * 40})
        pointer = {"channel": "develop", "release": manifest["release"], "publication_order": [21, 1]}
        with (patch.dict("os.environ", {"RELEASE_CHANNEL": "develop", "GCP_DELIVERY_BUCKET": "demo-delivery"}),
              patch.object(session, "command", side_effect=[json.dumps(pointer), json.dumps(manifest)]) as command):
            self.assertEqual(delivery.latest_release({"GCP_PROJECT_ID": "demo-project"}), manifest["release"])
        self.assertIn("channels/develop.json", command.call_args_list[0].args[3])

    def test_update_rejects_partial_or_mixed_registry_releases(self):
        for fault in ("missing_image", "foreign_registry", "mutable_tag", "different_release", "different_channel"):
            manifest = self.release_manifest()
            pointer = {"channel": "main", "release": manifest["release"]}
            if fault == "missing_image":
                del manifest["images"]["api"]
            elif fault == "foreign_registry":
                manifest["images"]["api"] = "attacker.invalid/api@sha256:" + "b" * 64
            elif fault == "mutable_tag":
                manifest["images"]["api"] = f"{session.REGION}-docker.pkg.dev/demo-project/nexoruta/api:latest"
            elif fault == "different_release":
                manifest["release"] = "release-" + "c" * 32
            else:
                manifest["channel"] = "develop"
            with self.subTest(fault=fault), patch.object(session, "command", side_effect=[json.dumps(pointer), json.dumps(manifest)]):
                with self.assertRaises(ValueError):
                    delivery.latest_release({"GCP_PROJECT_ID": "demo-project"})

    def test_update_rejects_a_pointer_outside_the_main_channel(self):
        with patch.object(session, "command", return_value=json.dumps({"channel": "develop", "release": "release-" + "a" * 32})) as command:
            with self.assertRaisesRegex(ValueError, "pointer"):
                delivery.latest_release({"GCP_PROJECT_ID": "demo-project"})
            self.assertEqual(command.call_count, 1)

    def test_stop_cannot_recreate_deleted_resources(self):
        with self.assertRaisesRegex(RuntimeError, "must not create"):
            session.check_plan({"resource_changes": [{"address": "database", "change": {"actions": ["create"]}}]}, "stop")

    def test_region_is_not_silently_deployed_in_the_us(self):
        with patch.dict("os.environ", {
            "GCP_PROJECT_ID": "demo-project", "GCP_ZONE": "us-central1-a",
            "GCP_STATE_BUCKET": "demo-state", "DEMO_OPERATION": "start",
        }):
            with self.assertRaisesRegex(ValueError, "Santiago"):
                session.configuration()


if __name__ == "__main__":
    unittest.main()
