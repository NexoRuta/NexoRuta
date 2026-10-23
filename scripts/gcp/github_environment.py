"""Read public app settings from Compose and credentials from GitHub Secrets."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import demo_session as session

APP_COMPOSE_FILE = session.ROOT / "compose.yaml"
APP_VARIABLES = {"SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_FROM", "MAPBOX_PUBLIC_TOKEN"}


def compose_model():
    # Let Compose parse its own YAML, including anchors and quoted values.
    # No Docker daemon is needed. Preserve literal dollar signs in public tokens.
    return json.loads(session.command(
        "docker", "compose", "-f", str(APP_COMPOSE_FILE),
        "config", "--no-interpolate", "--format=json", capture=True,
    ))


def app_environment():
    source = compose_model().get("x-app-settings", {})
    if not isinstance(source, dict) or APP_VARIABLES - source.keys():
        raise ValueError("Configure all public app variables in compose.yaml > x-app-settings")
    values = {}
    # Never export GCP configuration or credentials from the public Compose block.
    for name in sorted(APP_VARIABLES):
        value = source[name]
        if not isinstance(value, (str, int, bool)):
            raise ValueError(f"Invalid Compose setting: {name}")
        value = str(value).lower() if isinstance(value, bool) else str(value)
        if any(character in value for character in ("\r", "\n", "\x00")):
            raise ValueError(f"Invalid multiline Compose setting: {name}")
        values[name] = value
    if not values["SMTP_HOST"] or not values["SMTP_FROM"]:
        raise ValueError("SMTP_HOST and SMTP_FROM must be set in compose.yaml")
    if not values["SMTP_PORT"].isdigit() or not 1 <= int(values["SMTP_PORT"]) <= 65535:
        raise ValueError("SMTP_PORT in compose.yaml must be between 1 and 65535")
    if values["SMTP_SSL"].lower() not in ("true", "false"):
        raise ValueError("SMTP_SSL in compose.yaml must be true or false")
    return values


def load_app_environment():
    values = app_environment()
    if os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as output:
            for name, value in values.items():
                output.write(f"{name}={value}\n")
    print("Public application settings loaded from compose.yaml > x-app-settings.")


def validate(job):
    patterns = {
        "GCP_PROJECT_ID": r"[a-z][a-z0-9-]{4,28}[a-z0-9]",
        "GCP_REGION": re.escape(session.REGION),
        "GCP_WORKLOAD_IDENTITY_PROVIDER": r"projects/[0-9]+/locations/global/workloadIdentityPools/[a-z0-9-]+/providers/[a-z0-9-]+",
        "GCP_DEPLOY_SERVICE_ACCOUNT": r"[a-z][a-z0-9-]*@[a-z][a-z0-9-]*\.iam\.gserviceaccount\.com",
    }
    if job in ("publish", "deploy"):
        patterns.update({
            "GCP_ZONE": re.escape(session.REGION + "-a"),
            "GCP_STATE_BUCKET": r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]",
            "GCP_DELIVERY_BUCKET": r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]",
        })
    errors = [name for name, pattern in patterns.items() if not re.fullmatch(pattern, os.environ.get(name, ""))]
    if job == "deploy":
        manage_dns = os.environ.get("GCP_MANAGE_DNS", "").lower()
        domain = os.environ.get("GCP_BASE_DOMAIN", "")
        if manage_dns not in ("", "true", "false"):
            errors.append("GCP_MANAGE_DNS")
        if (domain and not re.fullmatch(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", domain)) or (manage_dns == "true" and not domain):
            errors.append("GCP_BASE_DOMAIN")
    if errors:
        raise ValueError("Configure valid Variables in GitHub environment nexoruta-demo: " + ", ".join(errors))
    print(f"GitHub environment configuration is valid for {job}.")


def integrations():
    public = app_environment()
    result = {
        "smtp_host": public["SMTP_HOST"],
        "smtp_port": public["SMTP_PORT"],
        "smtp_ssl": public["SMTP_SSL"],
        "smtp_from": public["SMTP_FROM"],
        "smtp_username": os.environ.get("SMTP_USERNAME", ""),
        "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
        "geoapify_api_key": os.environ.get("GEOAPIFY_API_KEY", ""),
        "mapbox_public_token": public["MAPBOX_PUBLIC_TOKEN"],
    }
    for name, value in result.items():
        if any(character in value for character in ("\r", "\n", "\x00")):
            raise ValueError(f"Invalid multiline application configuration: {name.upper()}")
    if bool(result["smtp_username"]) != bool(result["smtp_password"]):
        raise ValueError("Configure both SMTP_USERNAME and SMTP_PASSWORD secrets, or neither")
    result["smtp_port"] = int(result["smtp_port"])
    result["smtp_ssl"] = result["smtp_ssl"].lower() == "true"
    return result


def sync_integrations():
    validate("deploy")
    settings = integrations()
    # The VM reads this private secret with its own identity. No GitHub token or
    # GCP runner credential is copied to the VM or application containers.
    with tempfile.TemporaryDirectory(prefix="nexoruta-integrations-") as temp:
        path = Path(temp) / "integrations.json"
        path.write_text(json.dumps(settings), encoding="utf-8")
        path.chmod(0o600)
        session.command("gcloud", "secrets", "versions", "add", "nexoruta-demo-integrations",
                        f"--project={os.environ['GCP_PROJECT_ID']}", f"--data-file={path}", "--quiet")
    print("Application integrations synchronized from Compose and GitHub Secrets; values omitted.")


if __name__ == "__main__":
    try:
        if len(sys.argv) == 3 and sys.argv[1] == "validate" and sys.argv[2] in ("publish", "deploy", "android"):
            validate(sys.argv[2])
        elif sys.argv[1:] == ["sync-integrations"]:
            sync_integrations()
        elif sys.argv[1:] == ["load-app-config"]:
            load_app_environment()
        else:
            raise ValueError("Usage: github_environment.py validate publish|deploy|android OR sync-integrations OR load-app-config")
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
