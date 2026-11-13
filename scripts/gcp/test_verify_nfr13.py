import unittest
from unittest.mock import patch

import demo_session
import verify_nfr13 as verifier


class VerifyNfr13SafetyTests(unittest.TestCase):
    def test_import_and_help_do_not_call_google_cloud(self):
        with patch.object(demo_session, "command", side_effect=AssertionError("unexpected cloud call")):
            with self.assertRaises(SystemExit) as raised:
                verifier.main(["--help"])
        self.assertEqual(raised.exception.code, 0)

    def test_configuration_is_locked_to_demo_project_bucket_and_zones(self):
        config = verifier.configuration()
        self.assertEqual(config["GCP_PROJECT_ID"], verifier.PROJECT)
        self.assertEqual(config["GCP_STATE_BUCKET"], verifier.STATE_BUCKET)
        for values in (
            {"project": "nexoruta-production"},
            {"state_bucket": "other-state"},
            {"zone_a": "us-central1-a"},
            {"zone_b": "southamerica-west1-c"},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                verifier.configuration(**values)

    def test_api_origin_requires_https_and_demo_host(self):
        self.assertEqual(verifier.validate_origin(
            verifier.configuration(), "https://api.34-120-10-20.sslip.io/"),
            "https://api.34-120-10-20.sslip.io")
        for origin in (
            "http://api.34-120-10-20.sslip.io",
            "https://attacker.example.test",
            "https://api.34-120-10-20.sslip.io/other",
            "https://user:secret@api.34-120-10-20.sslip.io",
        ):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                verifier.validate_origin(verifier.configuration(), origin)

    def test_configured_domain_must_match_exact_api_host(self):
        def resolver(host, port, *, type):
            return [(2, 1, 6, "", ("34.120.10.20", port))]

        with patch.dict("os.environ", {"GCP_BASE_DOMAIN": "demo.nexoruta.test"}):
            self.assertEqual(verifier.validate_origin(
                verifier.configuration(), "https://api.demo.nexoruta.test",
                expected_address="34.120.10.20", resolver=resolver),
                "https://api.demo.nexoruta.test")
            with self.assertRaises(ValueError):
                verifier.validate_origin(verifier.configuration(), "https://api.other.test")

    def test_ip_based_api_origin_must_match_registered_frontend_ip(self):
        origin = "https://api.34-120-10-20.sslip.io"
        self.assertEqual(verifier.validate_origin(
            verifier.configuration(), origin, expected_address="34.120.10.20"), origin)
        with self.assertRaises(ValueError):
            verifier.validate_origin(verifier.configuration(), origin, expected_address="34.120.10.21")

    def test_instance_inventory_rejects_wrong_owner_zone_or_machine(self):
        node = verifier.demo_session.node_configs(verifier.configuration())[0]
        vm = {
            "name": node["VM_NAME"], "zone": "zones/" + node["GCP_ZONE"],
            "status": "RUNNING", "machineType": "zones/z1/machineTypes/n4-custom-6-16384",
            "labels": dict(verifier.EXPECTED_LABELS),
            "disks": [{"boot": True, "source": "zones/z1/disks/nexoruta-demo"}],
        }
        self.assertEqual(verifier.instance_summary({}, node, vm)["boot_disk"], "nexoruta-demo")
        vm["labels"].pop("managed_by")
        with self.assertRaises(RuntimeError):
            verifier.instance_summary({}, node, vm)

    def test_http_recovery_requires_ten_consecutive_successes_and_counts_samples(self):
        now = [0.0]
        statuses = iter([503, 502, 200, *([200] * 9)])
        result = verifier.wait_stable(
            "https://api.34-120-10-20.sslip.io", since=0,
            request=lambda _: {"status": next(statuses)},
            clock=lambda: now[0], sleeper=lambda seconds: now.__setitem__(0, now[0] + seconds),
        )
        self.assertEqual(len(result["samples"]), 12)
        self.assertEqual(result["stable_successes"], 10)
        self.assertEqual(result["recovery_seconds"], 2.0)

    def test_http_recovery_timeout_preserves_every_completed_probe(self):
        now = [0.0]
        with self.assertRaises(verifier.ObservationError) as raised:
            verifier.wait_stable(
                "https://api.34-120-10-20.sslip.io", observation_limit=4,
                request=lambda _: {"status": 503},
                clock=lambda: now[0], sleeper=lambda seconds: now.__setitem__(0, now[0] + seconds),
            )
        self.assertEqual(len(raised.exception.samples), 4)

    def test_backend_transition_requires_survivor_healthy_and_target_out(self):
        now = [0.0]
        states = iter([
            [{"instance": "nexoruta-demo", "health": "HEALTHY"},
             {"instance": "nexoruta-demo-b", "health": "HEALTHY"}],
            [{"instance": "nexoruta-demo", "health": "UNHEALTHY"},
             {"instance": "nexoruta-demo-b", "health": "HEALTHY"}],
        ])
        result = verifier.wait_backend_transition(
            verifier.configuration(), "a", read_health=lambda _: next(states),
            clock=lambda: now[0], sleeper=lambda seconds: now.__setitem__(0, now[0] + seconds),
        )
        self.assertEqual(result["target_health"], "UNHEALTHY")
        self.assertEqual(result["survivor"], "nexoruta-demo-b")

    def test_wrong_fault_confirmation_fails_before_lock_or_cloud_access(self):
        with patch.object(verifier.control_lock, "control_lock", side_effect=AssertionError("unexpected lock")):
            with self.assertRaises(ValueError):
                verifier.execute_fault(
                    verifier.configuration(), kind="vm", node_id="a",
                    expected_release="release-" + "a" * 32,
                    origin="https://api.34-120-10-20.sslip.io", confirmation="wrong",
                )

    def test_api_container_fault_disables_restart_before_kill(self):
        node = verifier.demo_session.node_configs(verifier.configuration())[0]
        with patch.object(verifier, "remote_command") as remote:
            verifier.kill_api(node, "a" * 12)
        self.assertIn("docker update --restart=no", remote.call_args.args[1])
        self.assertIn("docker kill --signal KILL", remote.call_args.args[1])

    def test_api_recovery_recreates_from_the_exact_release_without_migrations(self):
        node = verifier.demo_session.node_configs(verifier.configuration())[1]
        release = "release-" + "b" * 32
        with patch.object(verifier, "remote_command") as remote:
            verifier.restore_api(node, release)
        command = remote.call_args.args[1]
        self.assertIn("/srv/nexoruta/releases/" + release, command)
        self.assertIn("--force-recreate", command)
        self.assertTrue(command.endswith("api"))
        self.assertNotIn("migrate", command)

    def test_running_vm_recovery_never_restarts_or_changes_the_session(self):
        node = verifier.demo_session.node_configs(verifier.configuration())[0]
        vm = {"name": node["VM_NAME"], "zone": "zones/" + node["GCP_ZONE"],
              "status": "RUNNING", "machineType": "zones/z1/machineTypes/" + verifier.EXPECTED_MACHINE_TYPE,
              "labels": dict(verifier.EXPECTED_LABELS)}
        with (patch.object(verifier.demo_session, "instance", return_value=vm),
              patch.object(verifier.demo_session, "gcloud") as gcloud):
            verifier.start_vm(node)
        gcloud.assert_not_called()

    def test_reports_contain_only_the_sanitized_report_payload(self):
        self.assertEqual(verifier.OBSERVATION_SECONDS, 90)
        self.assertEqual(verifier.STABLE_SUCCESSES, 10)
        self.assertEqual(verifier.MIN_FAULT_WINDOW_SECONDS, 5400)


if __name__ == "__main__":
    unittest.main()
