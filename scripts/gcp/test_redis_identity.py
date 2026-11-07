import json
import shutil
import unittest
from unittest.mock import patch

import demo_session
import redis_identity


PROJECT = "nexoruta-demo-20261022"
ZONE = "southamerica-west1-b"
DNS = f"nexoruta-demo-b.{ZONE}.c.{PROJECT}.internal"


class RedisIdentityTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("openssl"), "OpenSSL is available on the deployment runner")
    def test_generated_identity_is_persistable_and_bound_to_vm_b_hostname(self):
        identity = redis_identity.generate_identity(DNS)

        self.assertEqual(identity["dns_name"], DNS)
        self.assertGreaterEqual(len(identity["password"]), 48)
        self.assertTrue(identity["expires_at"].endswith("Z"))
        self.assertEqual(redis_identity.validate_identity(identity, DNS), identity)
        with self.assertRaisesRegex(ValueError, "invalid or near expiry"):
            redis_identity.validate_identity(identity, f"nexoruta-demo-b.{ZONE}.c.attacker.internal")

    def test_dns_and_zone_are_derived_from_the_configured_secondary_zone(self):
        with patch.object(demo_session, "command") as command:
            with self.assertRaisesRegex(ValueError, "secondary zone"):
                redis_identity.ensure(PROJECT, "southamerica-west1-a")
            command.assert_not_called()
        with patch.object(demo_session, "command") as command:
            with self.assertRaisesRegex(ValueError, "DNS name"):
                redis_identity.generate_identity("redis.attacker.example")
            command.assert_not_called()

    def test_existing_invalid_identity_fails_closed_without_generating_a_replacement(self):
        with (
            patch.object(demo_session, "command", side_effect=["1\n", "not-json"]),
            patch.object(redis_identity, "generate_identity") as generate,
        ):
            with self.assertRaisesRegex(ValueError, "existing Redis identity is invalid"):
                redis_identity.ensure(PROJECT, ZONE)
            generate.assert_not_called()

    def test_absent_identity_is_added_without_exposing_its_payload_in_arguments(self):
        identity = {
            "password": "private-redis-password-" + "x" * 48,
            "dns_name": DNS,
            "ca_certificate": "-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----\n",
            "server_certificate": "-----BEGIN CERTIFICATE-----\nserver\n-----END CERTIFICATE-----\n",
            "server_private_key": "-----BEGIN PRIVATE KEY-----\nprivate\n-----END PRIVATE KEY-----\n",
        }
        commands = []

        def command(*arguments, capture=False):
            commands.append(arguments)
            if arguments[:4] == ("gcloud", "secrets", "versions", "list"):
                return ""
            if arguments[:4] == ("gcloud", "secrets", "versions", "add"):
                file_argument = next(item for item in arguments if item.startswith("--data-file="))
                payload = json.loads(__import__("pathlib").Path(file_argument.split("=", 1)[1]).read_text())
                self.assertEqual(payload, identity)
                return ""
            raise AssertionError(arguments)

        with (patch.object(demo_session, "command", side_effect=command),
              patch.object(redis_identity, "generate_identity", return_value=identity)):
            result = redis_identity.ensure(PROJECT, ZONE)

        self.assertEqual(result["dns_name"], DNS)
        self.assertEqual(len(commands), 2)
        self.assertNotIn(identity["password"], " ".join(" ".join(call) for call in commands))
        self.assertNotIn(identity["server_private_key"], " ".join(" ".join(call) for call in commands))


if __name__ == "__main__":
    unittest.main()
