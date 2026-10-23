import contextlib
import io
import json
import subprocess
import unittest
from unittest.mock import patch

import setup_integration_token as setup


class IntegrationTokenTests(unittest.TestCase):
    def test_cli_receives_token_only_on_stdin_and_all_three_secrets_are_verified(self):
        token = "github_pat_" + "test" * 20
        output = io.StringIO()

        def command(arguments, **kwargs):
            self.assertNotIn(token, " ".join(arguments))
            if arguments[1] == "secret":
                self.assertEqual(kwargs["input"], token)
                return subprocess.CompletedProcess(arguments, 0, "", "")
            return subprocess.CompletedProcess(arguments, 0, json.dumps({"name": setup.SECRET}), "")

        with (
            patch.object(setup.shutil, "which", return_value="gh"),
            patch.object(setup, "verify_token") as validate,
            patch.object(setup.subprocess, "run", side_effect=command) as execute,
            contextlib.redirect_stdout(output),
        ):
            setup.configure(token)
            validate.assert_called_once_with(token)
        self.assertEqual(execute.call_count, 6)
        for component in setup.COMPONENTS:
            self.assertIn(component, output.getvalue())
        self.assertNotIn(token, output.getvalue())

    def test_existing_cli_oauth_token_is_not_accepted_as_a_dedicated_pat(self):
        with patch.object(setup.urllib.request, "urlopen") as network:
            with self.assertRaisesRegex(ValueError, "fine-grained"):
                setup.verify_token("gho_" + "other" * 20)
            network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
