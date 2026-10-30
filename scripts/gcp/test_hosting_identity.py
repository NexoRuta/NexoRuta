import base64
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import hosting_identity as hosting


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL is required to validate PKCS#12 identities")
class HostingIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = hosting.generate_identity()

    def test_existing_identity_is_reused_without_generation_or_secret_write(self):
        output = io.StringIO()
        with (
            patch.object(hosting.session, "command", side_effect=["versions/1\n", json.dumps(self.identity)]) as command,
            patch.object(hosting, "generate_identity") as generate,
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(output),
        ):
            self.assertEqual(hosting.ensure("demo-project"), self.identity)
        generate.assert_not_called()
        self.assertEqual(command.call_count, 2)
        self.assertIn("--filter=state=ENABLED", command.call_args_list[0].args)
        self.assertEqual(command.call_args_list[1].args[3:5], ("access", "latest"))
        self.assertNotIn("--format=default", command.call_args_list[1].args)
        self.assertEqual(output.getvalue(), "")

    def test_malformed_existing_identity_never_replaces_credentials(self):
        malformed = [
            "not-json",
            "{}",
            json.dumps({**self.identity, "certificate_pfx": "invalid-base64!"}),
            json.dumps({**self.identity, "certificate_password": ""}),
            json.dumps({**self.identity, "certificate_password": "incorrect-password-that-is-long-enough"}),
            json.dumps({**self.identity, "grafana_secret_key": "short"}),
        ]
        for payload in malformed:
            with (
                self.subTest(case=malformed.index(payload)),
                patch.object(hosting.session, "command", side_effect=["versions/1", payload]) as command,
                patch.object(hosting, "generate_identity") as generate,
            ):
                with self.assertRaisesRegex(ValueError, "repair.*explicitly") as failure:
                    hosting.ensure("demo-project")
                self.assertNotIn(self.identity["certificate_password"], str(failure.exception))
                self.assertEqual(command.call_count, 2)
                generate.assert_not_called()

    def test_first_identity_is_uploaded_from_private_file_and_removed(self):
        files = []

        def command(*arguments, **kwargs):
            self.assertTrue(kwargs.get("capture"))
            if arguments[3] == "list":
                return ""
            self.assertEqual(arguments[3:5], ("add", hosting.SECRET))
            for secret in self.identity.values():
                self.assertNotIn(secret, " ".join(arguments))
            path = Path(next(argument.split("=", 1)[1] for argument in arguments if argument.startswith("--data-file=")))
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(json.loads(path.read_text()), self.identity)
            files.append(path)
            return ""

        previous = os.umask(0o022)
        try:
            with patch.object(hosting.session, "command", side_effect=command), patch.object(hosting, "generate_identity", return_value=self.identity):
                self.assertEqual(hosting.ensure("demo-project"), self.identity)
            current = os.umask(0o022)
            self.assertEqual(current, 0o022)
        finally:
            os.umask(previous)
        self.assertTrue(files)
        self.assertTrue(all(not path.exists() for path in files))

    def test_generated_pkcs12_contains_certificate_and_matching_private_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "certificate.pfx"
            path.write_bytes(base64.b64decode(self.identity["certificate_pfx"], validate=True))
            result = subprocess.run(
                [shutil.which("openssl"), "pkcs12", "-in", str(path), "-nodes", "-passin", "env:NEXORUTA_TEST_PFX_PASSWORD"],
                env={**os.environ, "NEXORUTA_TEST_PFX_PASSWORD": self.identity["certificate_password"]},
                capture_output=True, check=True,
            )
        self.assertIn(b"-----BEGIN CERTIFICATE-----", result.stdout)
        self.assertIn(b"-----BEGIN PRIVATE KEY-----", result.stdout)
        self.assertGreaterEqual(len(self.identity["grafana_secret_key"]), 48)
        self.assertNotEqual(self.identity["certificate_password"], self.identity["grafana_secret_key"])


if __name__ == "__main__":
    unittest.main()
