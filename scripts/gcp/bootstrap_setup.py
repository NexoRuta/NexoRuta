"""First-bootstrap runner for the single supported NexoRuta demo profile."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from infra_safety import check_plan

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "infra/gcp/bootstrap"
REPOSITORY = "NexoRuta/NexoRuta"
ENVIRONMENT = "nexoruta-demo"
REGION = "southamerica-west1"
ZONES = (REGION + "-a", REGION + "-b")
MACHINE_TYPE = "n4-custom-6-16384"
REQUIRED_CPUS = 12
WIF_WORKFLOWS = (
    f"{REPOSITORY}/.github/workflows/publish.yml@refs/heads/main",
    f"{REPOSITORY}/.github/workflows/vm-controls.yml@refs/heads/main",
    f"{REPOSITORY}/.github/workflows/vm-controls.yml@refs/heads/develop",
    f"{REPOSITORY}/.github/workflows/load-tests.yml@refs/heads/main",
    f"{REPOSITORY}/.github/workflows/load-tests.yml@refs/heads/develop",
)
WIF_PROFILES = {
    "demo": {
        "environment": ENVIRONMENT,
        "refs": ("refs/heads/main", "refs/heads/develop"),
        "events": ("workflow_dispatch", "push"),
        "workflows": WIF_WORKFLOWS,
    },
    "reproduction": {
        "environment": ENVIRONMENT,
        "refs": ("refs/heads/main",),
        "events": ("workflow_dispatch",),
        "workflows": (f"{REPOSITORY}/.github/workflows/reproduce.yml@refs/heads/main",),
    },
}


def validate_profile(project_id, repository, environment, region, state_bucket, state_prefix):
    if not isinstance(project_id, str) or not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project_id):
        raise ValueError("Invalid project ID")
    if (repository != REPOSITORY or environment != ENVIRONMENT
            or region != REGION or state_bucket != f"{project_id}-tofu-state"
            or state_prefix != "foundation"):
        raise ValueError("Bootstrap target is outside the supported NexoRuta demo profile")


def validate_destination(project, bucket, repository, *, project_id, repository_id, owner_id,
                         region=REGION, bucket_name=None):
    project_number = validate_project_and_bucket(
        project, bucket, project_id=project_id, region=region,
        bucket_name=bucket_name or f"{project_id}-tofu-state",
    )
    validate_repository_identity(repository, repository_id, owner_id)
    return project_number


def validate_repository_identity(repository, repository_id, owner_id):
    owner = repository.get("owner") or {}
    if (repository.get("full_name", "") != REPOSITORY
            or str(repository.get("id", "")) != str(repository_id)
            or str(owner.get("id", "")) != str(owner_id)
            or owner.get("login", "") != "NexoRuta"):
        raise ValueError("GitHub repository or owner identity does not match the bootstrap profile")


def validate_project_and_bucket(project, bucket, *, project_id, region=REGION, bucket_name=None):
    project_number = str(project.get("projectNumber", ""))
    if (project.get("projectId") != project_id or project.get("lifecycleState") != "ACTIVE"
            or not project_number.isdigit()):
        raise ValueError("The explicit Google Cloud project identity is invalid or inactive")
    bucket_name = bucket_name or f"{project_id}-tofu-state"
    if (bucket.get("name") != bucket_name or str(bucket.get("projectNumber", "")) != project_number
            or str(bucket.get("location", "")).upper() != region.upper()):
        raise ValueError("The OpenTofu state bucket does not belong to the explicit project and region")
    return project_number


def validate_quota(quotas, required_cpus=REQUIRED_CPUS):
    if not isinstance(quotas, list):
        raise ValueError("Could not inspect regional Compute Engine quotas")
    cpu = [item for item in quotas if isinstance(item, dict) and item.get("metric") == "CPUS"]
    if len(cpu) != 1:
        raise ValueError("The regional CPUS quota is missing or ambiguous")
    try:
        available = float(cpu[0]["limit"]) - float(cpu[0]["usage"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("The regional CPUS quota response is invalid") from error
    if available < required_cpus:
        raise ValueError(f"The demo requires {required_cpus} available regional CPUs")
    return available


def _run(*args, capture=False, allow_not_found=False):
    result = subprocess.run(args, text=True, capture_output=True, check=False)
    if result.returncode:
        diagnostic = (result.stdout or "") + "\n" + (result.stderr or "")
        if allow_not_found and re.search(r"(?i)(\b404\b|\bNOT_FOUND\b)", diagnostic):
            return None
        raise RuntimeError(f"{Path(args[0]).name} failed with exit code {result.returncode}")
    return result.stdout if capture else None


def _json_command(*args, allow_not_found=False):
    output = _run(*args, capture=True, allow_not_found=allow_not_found)
    return None if output is None else json.loads(output)


def _storage_bucket_info(bucket_name, *, allow_not_found=False):
    token = _run("gcloud", "auth", "print-access-token", capture=True)
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("Could not obtain credentials to inspect the state bucket")
    url = "https://storage.googleapis.com/storage/v1/b/" + urllib.parse.quote(bucket_name, safe="")
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token.strip()})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        if allow_not_found and error.code == 404:
            return None
        raise RuntimeError(f"Could not inspect the state bucket (HTTP {error.code})") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise RuntimeError("Could not inspect the state bucket") from None


def _resources(module):
    if not isinstance(module, dict):
        return
    yield from module.get("resources", [])
    for child in module.get("child_modules", []):
        yield from _resources(child)


def expected_wif_condition(repository_id, owner_id, repository, *, immutable_subject=True,
                           profile="demo"):
    try:
        wif = WIF_PROFILES[profile]
    except KeyError as error:
        raise ValueError("Unsupported bootstrap WIF profile") from error
    owner, name = repository.split("/", 1)
    subject = f"repo:{owner}@{owner_id}/{name}@{repository_id}:environment:{wif['environment']}"
    subject_condition = (
        f"assertion.sub == '{subject}'" if immutable_subject else
        f"assertion.sub in ['repo:{repository}:environment:{wif['environment']}', '{subject}']"
    )
    refs = ", ".join(f"'{ref}'" for ref in wif["refs"])
    events = ", ".join(f"'{event}'" for event in wif["events"])
    workflows = ", ".join(f"'{workflow}'" for workflow in wif["workflows"])
    return " && ".join((
        f"assertion.repository_id == '{repository_id}'",
        f"assertion.repository_owner_id == '{owner_id}'",
        f"assertion.repository == '{repository}'",
        f"assertion.ref in [{refs}]",
        subject_condition,
        f"assertion.workflow_ref in [{workflows}]",
        f"assertion.event_name in [{events}]",
    ))


def validate_state_identity(state, *, project_id, bucket_name, repository, repository_id, owner_id,
                            project_number=None, require_complete=False, require_current_subject=False,
                            wif_profile="demo", firebase_project_id="nexoruta-mobile"):
    try:
        wif = WIF_PROFILES[wif_profile]
    except KeyError as error:
        raise ValueError("Unsupported bootstrap WIF profile") from error
    if not isinstance(state, dict) or not isinstance(state.get("values"), dict):
        raise ValueError("OpenTofu state is missing or unreadable")
    values = state["values"]
    outputs = values.get("outputs") or {}
    configuration = (outputs.get("bootstrap_configuration") or {}).get("value")
    variables = (outputs.get("github_variables") or {}).get("value")
    if (isinstance(configuration, dict) and configuration.get("project_id") is not None
            and configuration.get("project_id") != project_id):
        raise ValueError("Bootstrap configuration output belongs to a different project")
    if project_number is not None and not str(project_number).isdigit():
        raise ValueError("Invalid explicit Google Cloud project number")
    if (isinstance(configuration, dict) and configuration.get("project_number") is not None
            and project_number is not None
            and str(configuration.get("project_number")) != str(project_number)):
        raise ValueError("Bootstrap configuration output belongs to a different project number")
    if isinstance(configuration, dict):
        recorded_profile = configuration.get("wif_profile")
        if recorded_profile is not None and recorded_profile != wif_profile:
            raise ValueError("Bootstrap configuration output belongs to a different WIF profile")
        recorded_environment = configuration.get("github_environment")
        if recorded_environment is not None and recorded_environment != wif["environment"]:
            raise ValueError("Bootstrap configuration output belongs to a different GitHub environment")
    if (isinstance(variables, dict) and variables.get("GCP_PROJECT_ID") is not None
            and variables.get("GCP_PROJECT_ID") != project_id):
        raise ValueError("Bootstrap GitHub output belongs to a different project")
    if require_complete:
        if (not isinstance(configuration, dict) or configuration.get("project_id") != project_id
                or str(configuration.get("project_number", "")) != str(project_number or "")
                or configuration.get("state_bucket") != bucket_name
                or configuration.get("github_repository") != repository
                or configuration.get("github_repository_id") != str(repository_id)
                or configuration.get("github_owner_id") != str(owner_id)
                or configuration.get("wif_profile") != wif_profile
                or configuration.get("github_environment") != wif["environment"]):
            raise ValueError("Bootstrap state outputs do not match the explicit destination")
        if not isinstance(variables, dict) or variables.get("GCP_PROJECT_ID") != project_id:
            raise ValueError("Bootstrap state has no matching public GitHub configuration")

    resources = list(_resources(values.get("root_module") or {}))
    project_ids = set()
    for item in resources:
        if not isinstance(item, dict):
            continue
        resource_project = item.get("values", {}).get("project")
        if resource_project is None or str(resource_project) == project_id:
            if resource_project is not None:
                project_ids.add(str(resource_project))
            continue
        external_firebase_config = (
            item.get("mode") == "data"
            and item.get("address") == "data.google_firebase_android_app_config.mobile"
            and item.get("type") == "google_firebase_android_app_config"
            and str(resource_project) == firebase_project_id
        )
        if not external_firebase_config:
            raise ValueError("OpenTofu state contains resources from a different project")
    project_marked = (project_id in project_ids
                      or (isinstance(configuration, dict) and configuration.get("project_id") == project_id)
                      or (isinstance(variables, dict) and variables.get("GCP_PROJECT_ID") == project_id))
    if resources and not project_marked:
        raise ValueError("OpenTofu state does not prove its project identity")
    buckets = [item for item in resources if isinstance(item, dict)
               and item.get("type") == "google_storage_bucket" and item.get("name") == "state"]
    if len(buckets) > 1 or (buckets and buckets[0].get("values", {}).get("name") != bucket_name):
        raise ValueError("OpenTofu state contains a different foundation state bucket")
    if require_complete and not buckets:
        raise ValueError("Bootstrap state does not own the expected foundation state bucket")

    providers = [item for item in resources if isinstance(item, dict)
                 and item.get("type") == "google_iam_workload_identity_pool_provider"
                 and item.get("name") == "github"]
    if len(providers) > 1:
        raise ValueError("Bootstrap state contains ambiguous GitHub identity providers")
    if providers:
        provider_values = providers[0].get("values", {})
        condition = provider_values.get("attribute_condition", "")
        provider_name = provider_values.get("name", "")
        expected_name = (f"projects/{project_number}/locations/global/workloadIdentityPools/"
                         "nexoruta-github/providers/demo-vm")
        if project_number is not None and provider_name and provider_name != expected_name:
            raise ValueError("Bootstrap state WIF provider belongs to a different project number")
        if require_complete and (not project_number or provider_name != expected_name):
            raise ValueError("Bootstrap state does not contain the expected project WIF provider identity")
        expected_conditions = {expected_wif_condition(
            repository_id, owner_id, repository, immutable_subject=True, profile=wif_profile,
        )}
        if not require_current_subject:
            expected_conditions.add(expected_wif_condition(
                repository_id, owner_id, repository, immutable_subject=False, profile=wif_profile,
            ))
        if condition not in expected_conditions:
            raise ValueError("OpenTofu state has a different GitHub WIF trust profile")
    elif require_complete:
        raise ValueError("Bootstrap state does not contain the expected GitHub identity provider")

    if not resources and not require_complete:
        raise ValueError("Local OpenTofu state contains no resources for the explicit destination")
    return state


def _write_inputs(path, project_id, repository, repository_id, owner_id, billing_account_id,
                  wif_profile="demo"):
    wif = WIF_PROFILES[wif_profile]
    path.write_text(json.dumps({
        "project_id": project_id,
        "region": REGION,
        "github_repository": repository,
        "github_repository_id": str(repository_id),
        "github_owner_id": str(owner_id),
        "github_environment": wif["environment"],
        "github_refs": list(wif["refs"]),
        "github_events": list(wif["events"]),
        "github_workflows": list(wif["workflows"]),
        "wif_profile": wif_profile,
        "billing_account_id": billing_account_id,
    }), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _verify_capacity(project_id):
    for zone in ZONES:
        machine = _json_command("gcloud", "compute", "machine-types", "describe", MACHINE_TYPE,
                                f"--zone={zone}", f"--project={project_id}", "--format=json")
        if (machine.get("name") != MACHINE_TYPE or machine.get("zone", "").rsplit("/", 1)[-1] != zone
                or int(machine.get("guestCpus", 0)) != 6 or int(machine.get("memoryMb", 0)) != 16384):
            raise ValueError(f"The required demo machine type is unavailable or changed in {zone}")
    region = _json_command("gcloud", "compute", "regions", "describe", REGION,
                           f"--project={project_id}", "--format=json(quotas)")
    return validate_quota(region.get("quotas"))


def validate_runtime_target(project_id, region, state_bucket, state_prefix, *, wif_profile="demo"):
    if wif_profile not in WIF_PROFILES:
        raise ValueError("Unsupported bootstrap WIF profile")
    validate_profile(project_id, REPOSITORY, ENVIRONMENT, region, state_bucket, "foundation")
    if state_prefix != "demo/vm":
        raise ValueError("Demo state prefix does not match the supported runtime profile")
    project = _json_command("gcloud", "projects", "describe", project_id, "--format=json")
    bucket = _storage_bucket_info(state_bucket)
    project_number = validate_project_and_bucket(project, bucket, project_id=project_id,
                                                 region=region, bucket_name=state_bucket)
    if (wif_profile == "reproduction"
            and str(project_number) != os.environ.get("NFR14_REPRO_PROJECT_NUMBER")):
        raise ValueError("The active project number differs from the locked NFR-14 reproduction identity")
    state_uri = f"gs://{state_bucket}/foundation/default.tfstate"
    _json_command("gcloud", "storage", "objects", "describe", state_uri,
                  f"--project={project_id}", "--format=json")
    return project_number


def run_setup(project_id, repository=REPOSITORY, environment=ENVIRONMENT, region=REGION,
              *, skip_budget=False, wif_profile="demo"):
    import bootstrap

    bucket_name = f"{project_id}-tofu-state"
    if wif_profile not in WIF_PROFILES:
        raise ValueError("Unsupported bootstrap WIF profile")
    validate_profile(project_id, repository, environment, region, bucket_name, "foundation")

    project = _json_command("gcloud", "projects", "describe", project_id, "--format=json")
    billing = _json_command("gcloud", "billing", "projects", "describe", project_id, "--format=json")
    if billing.get("billingEnabled") is not True:
        raise ValueError("The explicit project needs an active billing account before bootstrap")
    repo = _json_command("gh", "api", f"repos/{repository}")
    repository_id = repo.get("id")
    owner_id = (repo.get("owner") or {}).get("id")
    if type(repository_id) is not int or type(owner_id) is not int:
        raise ValueError("GitHub did not return stable numeric repository and owner IDs")
    validate_repository_identity(repo, repository_id, owner_id)
    machine_project_number = str(project.get("projectNumber", ""))
    if not machine_project_number.isdigit() or project.get("lifecycleState") != "ACTIVE":
        raise ValueError("The explicit Google Cloud project identity is invalid or inactive")
    _verify_capacity(project_id)

    module = MODULE
    remote_uri = f"gs://{bucket_name}/foundation/default.tfstate"
    bucket = _storage_bucket_info(bucket_name, allow_not_found=True)
    remote_exists = _json_command("gcloud", "storage", "objects", "describe", remote_uri,
                                  f"--project={project_id}", "--format=json", allow_not_found=True) is not None
    local_state = module / "terraform.tfstate"
    backend_file = module / "backend.generated.tf"
    if bucket is not None:
        machine_project_number = validate_destination(
            project, bucket, repo, project_id=project_id, repository_id=repository_id,
            owner_id=owner_id, region=region, bucket_name=bucket_name,
        )
    if remote_exists and bucket is None:
        raise ValueError("Remote foundation state exists but its bucket could not be verified")
    if not remote_exists and bucket is not None and not local_state.is_file():
        raise ValueError("A state bucket exists without foundation state; refusing to adopt or overwrite it")
    if backend_file.exists() and not remote_exists and not local_state.is_file():
        raise ValueError("A generated remote backend exists but neither remote nor verified local state is available")

    tofu = ("tofu", f"-chdir={module}")
    if remote_exists:
        bootstrap.write_backend_file(module)
        _run(*tofu, "init", "-reconfigure", "-input=false", "-lockfile=readonly",
             f"-backend-config=bucket={bucket_name}", "-backend-config=prefix=foundation")
    else:
        _run(*tofu, "init", "-reconfigure", "-backend=false", "-input=false", "-lockfile=readonly")
    _run(*tofu, "validate")

    state = None
    if remote_exists or local_state.is_file():
        state = json.loads(_run(*tofu, "show", "-json", capture=True))
        validate_state_identity(state, project_id=project_id, bucket_name=bucket_name,
                                repository=repository, repository_id=repository_id, owner_id=owner_id,
                                project_number=machine_project_number, wif_profile=wif_profile,
                                firebase_project_id=os.environ.get(
                                    "NEXORUTA_FIREBASE_ANDROID_PROJECT_ID", "nexoruta-mobile"))
        if not remote_exists and bucket is not None:
            resources = list(_resources(state.get("values", {}).get("root_module") or {}))
            owned = [item for item in resources if item.get("type") == "google_storage_bucket"
                     and item.get("name") == "state"
                     and item.get("values", {}).get("name") == bucket_name]
            if len(owned) != 1:
                raise ValueError("An existing state bucket is not owned by the verified local state")

    from bootstrap import settings
    environment_data = {
        "GCP_PROJECT_ID": project_id,
        "GCP_REGION": region,
        "GITHUB_REPOSITORY": repository,
        "BOOTSTRAP_REPOSITORY_ID": str(repository_id),
        "BOOTSTRAP_OWNER_ID": str(owner_id),
        "BOOTSTRAP_WIF_PROFILE": wif_profile,
    }
    billing_account_name = billing.get("billingAccountName")
    if not skip_budget and (not isinstance(billing_account_name, str)
                            or not re.fullmatch(r"billingAccounts/[A-Z0-9-]{6,30}", billing_account_name)):
        raise ValueError("The active billing account has an invalid identity")
    billing_account = "" if skip_budget else billing_account_name.removeprefix("billingAccounts/")
    inputs_data = settings(environment_data, state or {}, default_billing_account_id=billing_account)
    with tempfile.TemporaryDirectory(prefix="nexoruta-bootstrap-") as directory:
        try:
            Path(directory).chmod(0o700)
        except OSError:
            pass
        inputs = Path(directory) / "inputs.tfvars.json"
        _write_inputs(inputs, project_id, repository, repository_id, owner_id,
                      inputs_data["billing_account_id"], wif_profile)
        plan_file = Path(directory) / "bootstrap.tfplan"
        _run(*tofu, "plan", "-input=false", "-lock-timeout=5m",
             f"-var-file={inputs}", f"-out={plan_file}")
        plan = json.loads(_run(*tofu, "show", "-json", str(plan_file), capture=True))
        check_plan(plan, "bootstrap")
        _run(*tofu, "apply", "-input=false", "-lock-timeout=5m", str(plan_file))

    if not remote_exists:
        created_bucket = _storage_bucket_info(bucket_name)
        machine_project_number = validate_destination(
            project, created_bucket, repo, project_id=project_id,
            repository_id=repository_id, owner_id=owner_id,
            region=region, bucket_name=bucket_name,
        )
        bootstrap.write_backend_file(module)
        _run(*tofu, "init", "-migrate-state", "-force-copy", "-input=false", "-lockfile=readonly",
             f"-backend-config=bucket={bucket_name}", "-backend-config=prefix=foundation")

    _json_command("gcloud", "storage", "objects", "describe", remote_uri,
                  f"--project={project_id}", "--format=json")
    final_state = json.loads(_run(*tofu, "show", "-json", capture=True))
    validate_state_identity(final_state, project_id=project_id, bucket_name=bucket_name,
                            repository=repository, repository_id=repository_id, owner_id=owner_id,
                            project_number=machine_project_number,
                            require_complete=True, require_current_subject=True, wif_profile=wif_profile,
                            firebase_project_id=os.environ.get(
                                "NEXORUTA_FIREBASE_ANDROID_PROJECT_ID", "nexoruta-mobile"))
    lineage, serial = final_state.get("lineage"), final_state.get("serial")
    if (not isinstance(lineage, str) or not lineage
            or type(serial) is not int or serial < 0):
        raise ValueError("The completed foundation state has no valid lineage and serial")
    return {"project_id": project_id, "project_number": machine_project_number,
            "repository_id": repository_id, "owner_id": owner_id,
            "state_bucket": bucket_name, "state_prefix": "foundation",
            "state_lineage": lineage, "state_serial": serial}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--repository", default=REPOSITORY)
    parser.add_argument("--environment", default=ENVIRONMENT)
    parser.add_argument("--region", default=REGION)
    parser.add_argument("--skip-budget", action="store_true")
    parser.add_argument("--wif-profile", choices=tuple(WIF_PROFILES), default="demo")
    args = parser.parse_args()
    result = run_setup(args.project_id, args.repository, args.environment, args.region,
                       skip_budget=args.skip_budget, wif_profile=args.wif_profile)
    print(json.dumps({"status": "complete", **result}, sort_keys=True))


if __name__ == "__main__":
    main()
