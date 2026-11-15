"""Apply the existing remote foundation before a manual demo deployment."""

import json
import os
from pathlib import Path
import subprocess
import tempfile

import bootstrap_setup
from infra_safety import check_plan as _check_infra_plan

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "infra/gcp/bootstrap"


def command(*args, capture=False):
    return subprocess.run(args, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def resources(module):
    yield from module.get("resources", [])
    for child in module.get("child_modules", []):
        yield from resources(child)


def detach_legacy_mobile_config_version(tofu, state):
    """Forget the legacy DELETE-tracked version without deleting it in GCP."""
    root = state.get("values", {}).get("root_module", {})
    matches = [resource for resource in resources(root)
               if resource.get("address") == "google_secret_manager_secret_version.mobile"]
    if not matches:
        return False
    if len(matches) != 1:
        raise RuntimeError("The legacy mobile config secret has ambiguous Terraform state")

    resource = matches[0]
    values = resource.get("values") or {}
    secret = values.get("secret")
    if (resource.get("type") != "google_secret_manager_secret_version"
            or not isinstance(secret, str)
            or not secret.endswith("/secrets/nexoruta-mobile-config")):
        raise RuntimeError("Refusing to detach an unexpected Secret Manager resource")
    if values.get("deletion_policy") != "DELETE":
        return False
    version_id = values.get("id")
    if (not isinstance(version_id, str)
            or "/secrets/nexoruta-mobile-config/versions/" not in version_id):
        raise RuntimeError("Refusing to detach an unexpected mobile config version")

    address = resource["address"]
    command(*tofu, "state", "rm", "-lock-timeout=5m", address)
    print("Detached the legacy mobile config version from Terraform state; the GCP version remains.",
          flush=True)
    return True


def settings(environment, state, default_billing_account_id=""):
    # Preserve the optional budget chosen during initial setup. Never infer a
    # billing account from the current user's machine or silently remove it.
    budgets = [r for r in resources(state.get("values", {}).get("root_module", {}))
               if r.get("type") == "google_billing_budget"]
    outputs = state.get("values", {}).get("outputs", {})
    configuration = (outputs.get("bootstrap_configuration") or {}).get("value")
    if budgets:
        billing_account_id = budgets[0]["values"]["billing_account"]
    elif isinstance(configuration, dict):
        billing_account_id = configuration.get("billing_account_id", "")
    elif list(resources(state.get("values", {}).get("root_module", {}))):
        # An older completed bootstrap without the configuration output and
        # without a budget intentionally remains without a budget.
        billing_account_id = ""
    else:
        billing_account_id = default_billing_account_id
    profile = environment.get("BOOTSTRAP_WIF_PROFILE", "demo")
    try:
        wif = bootstrap_setup.WIF_PROFILES[profile]
    except KeyError as error:
        raise ValueError("Unsupported bootstrap WIF profile") from error
    result = {
        "project_id": environment["GCP_PROJECT_ID"],
        "region": environment["GCP_REGION"],
        "github_repository": environment["GITHUB_REPOSITORY"],
        "github_repository_id": environment["BOOTSTRAP_REPOSITORY_ID"],
        "github_owner_id": environment["BOOTSTRAP_OWNER_ID"],
        "github_environment": wif["environment"],
        "github_refs": list(wif["refs"]),
        "github_events": list(wif["events"]),
        "github_workflows": list(wif["workflows"]),
        "wif_profile": profile,
        "billing_account_id": billing_account_id,
    }
    for name in ("github_repository_id", "github_owner_id"):
        if not result[name].isdigit():
            raise ValueError(f"Invalid {name}")
    return result


def check_plan(plan):
    return _check_infra_plan(plan, "bootstrap")


def write_backend_file(module=MODULE):
    path = module / "backend.generated.tf"
    path.write_text('terraform {\n  backend "gcs" {}\n}\n', encoding="utf-8")
    return path


def preflight_target(environment):
    project_id = environment["GCP_PROJECT_ID"]
    region = environment["GCP_REGION"]
    bucket = environment["GCP_STATE_BUCKET"]
    repository = environment["GITHUB_REPOSITORY"]
    repository_id = environment["BOOTSTRAP_REPOSITORY_ID"]
    owner_id = environment["BOOTSTRAP_OWNER_ID"]
    profile = environment.get("BOOTSTRAP_WIF_PROFILE", "demo")
    if profile not in bootstrap_setup.WIF_PROFILES:
        raise ValueError("Unsupported bootstrap WIF profile")
    if profile == "reproduction":
        import reproduce
        reproduce.validate_runtime_environment(environment)
    bootstrap_setup.validate_profile(project_id, repository, bootstrap_setup.ENVIRONMENT,
                                     region, bucket, "foundation")
    if not repository_id.isdigit() or not owner_id.isdigit():
        raise ValueError("Invalid GitHub repository or owner identity")
    project = json.loads(command("gcloud", "projects", "describe", project_id, "--format=json", capture=True))
    bucket_info = bootstrap_setup._storage_bucket_info(bucket)
    repo = json.loads(command("gh", "api", f"repos/{repository}", capture=True))
    return bootstrap_setup.validate_destination(
        project, bucket_info, repo, project_id=project_id, repository_id=repository_id,
        owner_id=owner_id, region=region, bucket_name=bucket,
    )


def main():
    environment = os.environ
    project_id = environment["GCP_PROJECT_ID"]
    bucket = environment["GCP_STATE_BUCKET"]
    project_number = preflight_target(environment)
    # The first setup must create the bucket, remote state and WIF identity.
    # Refuse an empty/wrong state rather than re-creating a second foundation.
    command("gcloud", "storage", "objects", "describe",
            f"gs://{bucket}/foundation/default.tfstate", f"--project={project_id}", capture=True)
    write_backend_file()
    tofu = ("tofu", f"-chdir={MODULE}")
    command(*tofu, "init", "-input=false", "-lockfile=readonly",
            f"-backend-config=bucket={bucket}", "-backend-config=prefix=foundation")
    command(*tofu, "validate")
    state = json.loads(command(*tofu, "show", "-json", capture=True))
    identity = {"project_id": project_id, "bucket_name": bucket,
                "repository": environment["GITHUB_REPOSITORY"],
                "repository_id": environment["BOOTSTRAP_REPOSITORY_ID"],
                "owner_id": environment["BOOTSTRAP_OWNER_ID"], "project_number": project_number,
                "wif_profile": environment.get("BOOTSTRAP_WIF_PROFILE", "demo"),
                "firebase_project_id": environment.get(
                    "NEXORUTA_FIREBASE_ANDROID_PROJECT_ID", "nexoruta-mobile")}
    bootstrap_setup.validate_state_identity(state, **identity)
    detach_legacy_mobile_config_version(tofu, state)
    with tempfile.TemporaryDirectory(prefix="nexoruta-bootstrap-") as directory:
        inputs = Path(directory) / "inputs.tfvars.json"
        inputs.write_text(json.dumps(settings(environment, state)), encoding="utf-8")
        try:
            inputs.chmod(0o600)
        except OSError:
            pass
        plan_file = Path(directory) / "bootstrap.tfplan"
        command(*tofu, "plan", "-input=false", "-lock-timeout=5m",
                f"-var-file={inputs}", f"-out={plan_file}")
        plan = json.loads(command(*tofu, "show", "-json", str(plan_file), capture=True))
        check_plan(plan)
        command(*tofu, "apply", "-input=false", "-lock-timeout=5m", str(plan_file))
    final_state = json.loads(command(*tofu, "show", "-json", capture=True))
    bootstrap_setup.validate_state_identity(final_state, **identity,
                                            require_complete=True, require_current_subject=True)


if __name__ == "__main__":
    main()
