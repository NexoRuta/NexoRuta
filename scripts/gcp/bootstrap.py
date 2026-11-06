"""Apply the existing remote foundation before a manual demo deployment."""

import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "infra/gcp/bootstrap"


def command(*args, capture=False):
    return subprocess.run(args, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def resources(module):
    yield from module.get("resources", [])
    for child in module.get("child_modules", []):
        yield from resources(child)


def settings(environment, state):
    # Preserve the optional budget chosen during initial setup. Never infer a
    # billing account from the current user's machine or silently remove it.
    budgets = [r for r in resources(state.get("values", {}).get("root_module", {}))
               if r.get("type") == "google_billing_budget"]
    result = {
        "project_id": environment["GCP_PROJECT_ID"],
        "region": environment["GCP_REGION"],
        "github_repository": environment["GITHUB_REPOSITORY"],
        "github_repository_id": environment["BOOTSTRAP_REPOSITORY_ID"],
        "github_owner_id": environment["BOOTSTRAP_OWNER_ID"],
        "billing_account_id": budgets[0]["values"]["billing_account"] if budgets else "",
    }
    for name in ("github_repository_id", "github_owner_id"):
        if not result[name].isdigit():
            raise ValueError(f"Invalid {name}")
    return result


def check_plan(plan):
    deletions = [r["address"] for r in plan.get("resource_changes", [])
                 if "delete" in r["change"]["actions"]]
    if deletions:
        raise RuntimeError("Bootstrap plan deletes/replaces resources: " + ", ".join(deletions))


def write_backend_file(module=MODULE):
    path = module / "backend.generated.tf"
    path.write_text('terraform {\n  backend "gcs" {}\n}\n', encoding="utf-8")
    return path


def main():
    bucket = os.environ["GCP_STATE_BUCKET"]
    # The first setup must create the bucket, remote state and WIF identity.
    # Refuse an empty/wrong state rather than re-creating a second foundation.
    command("gcloud", "storage", "objects", "describe",
            f"gs://{bucket}/foundation/default.tfstate", capture=True)
    write_backend_file()
    tofu = ("tofu", f"-chdir={MODULE}")
    command(*tofu, "init", "-input=false", "-lockfile=readonly",
            f"-backend-config=bucket={bucket}", "-backend-config=prefix=foundation")
    command(*tofu, "validate")
    state = json.loads(command(*tofu, "show", "-json", capture=True))
    with tempfile.TemporaryDirectory(prefix="nexoruta-bootstrap-") as directory:
        inputs = Path(directory) / "inputs.tfvars.json"
        inputs.write_text(json.dumps(settings(os.environ, state)), encoding="utf-8")
        plan_file = Path(directory) / "bootstrap.tfplan"
        command(*tofu, "plan", "-input=false", "-lock-timeout=5m",
                f"-var-file={inputs}", f"-out={plan_file}")
        plan = json.loads(command(*tofu, "show", "-json", str(plan_file), capture=True))
        check_plan(plan)
        command(*tofu, "apply", "-input=false", "-lock-timeout=5m", str(plan_file))


if __name__ == "__main__":
    main()
