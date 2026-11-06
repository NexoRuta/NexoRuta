"""Remove this runner's OS Login key or repair legacy deployer key accumulation."""

import json
import os
from pathlib import Path
import re
import sys

import demo_session as session


def profile(project):
    return json.loads(session.command(
        "gcloud", "compute", "os-login", "describe-profile",
        f"--project={project}", "--format=json", capture=True,
    )).get("sshPublicKeys", {})


def remove(project, fingerprint):
    session.command(
        "gcloud", "compute", "os-login", "ssh-keys", "remove",
        f"--key={fingerprint}", f"--project={project}", "--quiet", capture=True,
    )


def cleanup(project, public_key=None):
    public_key = public_key or Path.home() / ".ssh" / "google_compute_engine.pub"
    if not public_key.is_file():
        print("No runner SSH key was generated.")
        return
    material = public_key.read_text(encoding="utf-8").split()[:2]
    if len(material) != 2:
        raise ValueError("Invalid runner SSH public key")
    removed = 0
    for fingerprint, key in profile(project).items():
        if key.get("key", "").split()[:2] == material:
            remove(project, fingerprint)
            removed += 1
    print(f"Removed {removed} OS Login keys belonging to this runner.")


def repair(project):
    expected = os.environ.get("GCP_DEPLOY_SERVICE_ACCOUNT", "")
    if os.environ.get("GITHUB_ACTIONS") != "true" or not re.fullmatch(
        rf"nexoruta-demo-deployer@{re.escape(project)}\.iam\.gserviceaccount\.com", expected,
    ):
        raise ValueError("SSH repair is restricted to the dedicated deployer in GitHub Actions")
    active = session.command("gcloud", "config", "get-value", "account", capture=True).strip()
    if active != expected:
        raise ValueError("The active gcloud identity is not the expected deployer")
    removed = 0
    for fingerprint, key in profile(project).items():
        fields = key.get("key", "").split()
        # VM-control runs are serialized; these unbounded hosted-runner keys are obsolete.
        legacy = len(fields) == 3 and re.fullmatch(
            r"runner@(?:runnervm[a-zA-Z0-9-]+|fv-az[a-zA-Z0-9-]+)", fields[2],
        )
        if legacy and not int(key.get("expirationTimeUsec", 0)):
            remove(project, fingerprint)
            removed += 1
    print(f"Removed {removed} legacy runner keys; POSIX accounts and other keys were preserved.")


def main():
    project = os.environ.get("GCP_PROJECT_ID", "")
    if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project):
        raise ValueError("Missing or invalid GCP_PROJECT_ID")
    if sys.argv[1:] == ["cleanup"]:
        cleanup(project)
    elif sys.argv[1:] == ["repair"]:
        repair(project)
    else:
        raise ValueError("Usage: ssh_keys.py cleanup|repair")


if __name__ == "__main__":
    main()
