import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import github_environment as settings


class GitHubEnvironmentTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {
            "GCP_PROJECT_ID": "demo-project", "GCP_REGION": "southamerica-west1",
            "GCP_ZONE": "southamerica-west1-a", "GCP_STATE_BUCKET": "demo-state",
            "GCP_DELIVERY_BUCKET": "demo-delivery",
            "GCP_WORKLOAD_IDENTITY_PROVIDER": "projects/123456/locations/global/workloadIdentityPools/nexoruta-github/providers/demo-vm",
            "GCP_DEPLOY_SERVICE_ACCOUNT": "nexoruta-demo-deployer@demo-project.iam.gserviceaccount.com",
        }, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        temp = self.enterContext(tempfile.TemporaryDirectory())
        self.work = Path(temp)
        self.public = {
            "SMTP_HOST": "mailpit", "SMTP_PORT": "1025", "SMTP_SSL": "false",
            "SMTP_FROM": "demo@nexoruta.test", "MAPBOX_PUBLIC_TOKEN": "",
        }
        self.enterContext(patch.object(settings, "compose_model", return_value={"x-app-settings": self.public}))

    def test_compose_loads_public_values_literally_without_overwriting_cloud_or_secrets(self):
        self.public.update({
            "SMTP_HOST": "smtp.example.uy", "MAPBOX_PUBLIC_TOKEN": "pk.$(literal-token)",
            "GCP_PROJECT_ID": "wrong-project", "SMTP_PASSWORD": "wrong-secret",
        })
        exported = self.work / "github-env"
        with patch.dict(os.environ, {"GITHUB_ENV": str(exported), "SMTP_PASSWORD": "actual-secret", "SMTP_HOST": "old-github-variable"}):
            settings.load_app_environment()
            self.assertEqual(os.environ["GCP_PROJECT_ID"], "demo-project")
            self.assertEqual(os.environ["SMTP_PASSWORD"], "actual-secret")
            config = settings.app_environment()
            self.assertEqual(config["SMTP_HOST"], "smtp.example.uy")
        values = dict(line.split("=", 1) for line in exported.read_text().splitlines())
        self.assertEqual(set(values), settings.APP_VARIABLES)
        self.assertEqual(values["MAPBOX_PUBLIC_TOKEN"], "pk.$(literal-token)")
        self.assertNotIn("actual-secret", exported.read_text())

    def test_invalid_public_configuration_fails_before_exporting(self):
        exported = self.work / "github-env"
        for name, value in (("SMTP_PORT", 70000), ("SMTP_SSL", "maybe"), ("MAPBOX_PUBLIC_TOKEN", "value\nSMTP_PASSWORD=injected")):
            with self.subTest(name=name), patch.dict(self.public, {name: value}), patch.dict(os.environ, {"GITHUB_ENV": str(exported)}):
                with self.assertRaises(ValueError):
                    settings.load_app_environment()
                self.assertFalse(exported.exists())

    def test_missing_compose_settings_do_not_silently_fall_back_to_other_defaults(self):
        with patch.object(settings, "compose_model", return_value={}):
            with self.assertRaisesRegex(ValueError, "compose.yaml > x-app-settings"):
                settings.app_environment()

    def test_missing_environment_variables_fail_before_authentication(self):
        for name in ("GCP_PROJECT_ID", "GCP_WORKLOAD_IDENTITY_PROVIDER", "GCP_DEPLOY_SERVICE_ACCOUNT", "GCP_DELIVERY_BUCKET"):
            with self.subTest(name=name), patch.dict(os.environ, {name: ""}):
                with self.assertRaisesRegex(ValueError, name):
                    settings.validate("publish")

    def test_environment_only_settings_validate_for_all_runner_jobs(self):
        for job in ("publish", "deploy", "android"):
            with self.subTest(job=job):
                settings.validate(job)
        with patch.dict(os.environ, {"GCP_REGION": "us-central1"}):
            with self.assertRaisesRegex(ValueError, "GCP_REGION"):
                settings.validate("android")

    def test_managed_dns_requires_an_owned_domain(self):
        with patch.dict(os.environ, {"GCP_MANAGE_DNS": "true"}):
            with self.assertRaisesRegex(ValueError, "GCP_BASE_DOMAIN"):
                settings.validate("deploy")
        with patch.dict(os.environ, {"GCP_MANAGE_DNS": "true", "GCP_BASE_DOMAIN": "demo.example.uy"}):
            settings.validate("deploy")

    def test_unconfigured_integrations_use_mailpit_and_configured_secrets_are_paired(self):
        defaults = settings.integrations()
        self.assertEqual((defaults["smtp_host"], defaults["smtp_port"], defaults["smtp_ssl"]), ("mailpit", 1025, False))
        with patch.dict(os.environ, {"SMTP_USERNAME": "demo"}):
            with self.assertRaisesRegex(ValueError, "both SMTP_USERNAME and SMTP_PASSWORD"):
                settings.integrations()

    def test_sync_delivers_private_json_without_secrets_in_arguments_or_logs(self):
        self.public["SMTP_PORT"] = 587
        output = io.StringIO()
        private_paths = []

        def upload(*args, **kwargs):
            self.assertNotIn("private-password", " ".join(args))
            self.assertNotIn("private-geo-key", " ".join(args))
            path = Path(next(arg.split("=", 1)[1] for arg in args if arg.startswith("--data-file=")))
            private_paths.append(path)
            data = json.loads(path.read_text())
            self.assertEqual(data["smtp_password"], "private-password")
            self.assertEqual(data["geoapify_api_key"], "private-geo-key")
            self.assertEqual(data["smtp_port"], 587)

        with (
            patch.dict(os.environ, {"SMTP_USERNAME": "demo", "SMTP_PASSWORD": "private-password", "GEOAPIFY_API_KEY": "private-geo-key"}),
            patch.object(settings.session, "command", side_effect=upload) as command,
            patch("hosting_identity.ensure"),
            contextlib.redirect_stdout(output),
        ):
            settings.sync_integrations()
            command.assert_called_once()
        self.assertNotIn("private-password", output.getvalue())
        self.assertNotIn("private-geo-key", output.getvalue())
        self.assertTrue(private_paths)
        self.assertTrue(all(not path.exists() for path in private_paths))


if __name__ == "__main__":
    unittest.main()
