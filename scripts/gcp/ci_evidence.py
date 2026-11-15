"""Create and resolve immutable evidence from the required Integrated CI run."""

import hashlib
import io
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile

import integration

WORKFLOW_PATH = ".github/workflows/ci.yml"
ARTIFACT_FILE = "nfr14-ci-evidence.json"
ARTIFACT_PREFIX = "nfr14-ci-evidence-"
SHA = re.compile(r"[a-f0-9]{40}\Z")
HEX_256 = re.compile(r"[a-f0-9]{64}\Z")
ARTIFACT_DIGEST = re.compile(r"sha256:[a-f0-9]{64}\Z")
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024
MAX_EVIDENCE_BYTES = 128 * 1024


def _positive_int(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(f"Invalid {name} in CI evidence")
    return value


def _matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _api(path, token):
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid GitHub repository context")
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    request = urllib.request.Request(
        f"{base}/repos/{repository}/{path}",
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError("Could not read the required GitHub CI evidence") from error


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _download_artifact(artifact_id, token, expected_digest):
    if not _matches(ARTIFACT_DIGEST, expected_digest):
        raise ValueError("GitHub did not provide a SHA-256 identity for the CI artifact")
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    repository = os.environ["GITHUB_REPOSITORY"]
    request = urllib.request.Request(
        f"{base}/repos/{repository}/actions/artifacts/{artifact_id}/zip",
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        opener.open(request, timeout=30)
        raise RuntimeError("GitHub returned an unexpected CI artifact response")
    except urllib.error.HTTPError as response:
        if response.code not in (301, 302, 303, 307, 308):
            raise RuntimeError("Could not download the required GitHub CI artifact") from response
        location = response.headers.get("Location", "")
    if not location:
        raise RuntimeError("GitHub CI artifact is missing its signed download location")
    parsed = urllib.parse.urlsplit(location)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("GitHub returned an invalid CI artifact download location")
    # The bearer token is never sent to the signed artifact host.
    try:
        with urllib.request.urlopen(location, timeout=60) as response:
            archive = response.read(MAX_ARCHIVE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError("Could not download the required GitHub CI artifact") from error
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("GitHub CI artifact exceeds the allowed size")
    actual_digest = "sha256:" + hashlib.sha256(archive).hexdigest()
    if actual_digest != expected_digest:
        raise ValueError("GitHub CI artifact checksum does not match its API identity")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            files = [item for item in zipped.infolist() if not item.is_dir()]
            if len(files) != 1 or files[0].filename != ARTIFACT_FILE or files[0].file_size > MAX_EVIDENCE_BYTES:
                raise ValueError("GitHub CI artifact has an unexpected file layout")
            payload = zipped.read(files[0])
    except zipfile.BadZipFile as error:
        raise ValueError("GitHub CI artifact is not a valid archive") from error
    return json.loads(payload)


def _validate_sources(sources):
    try:
        return integration.validate_sources(sources)
    except (TypeError, ValueError) as error:
        raise ValueError("CI evidence must identify exactly three full source gitlinks") from error


def validate_ci_identity(identity, *, root_sha=None, sources=None):
    if (not isinstance(identity, dict) or type(identity.get("schema_version")) is not int
            or identity.get("schema_version") != 1):
        raise ValueError("Published CI evidence is missing or has an unsupported schema")
    if (not isinstance(identity.get("repository_id"), str)
            or not identity["repository_id"].isdigit()
            or identity.get("workflow_path") != WORKFLOW_PATH
            or identity.get("event") != "pull_request"
            or identity.get("base_branch") != "main"
            or identity.get("head_branch") != "develop"
            or type(identity.get("pull_request")) is not int
            or identity["pull_request"] < 1
            or not _matches(SHA, identity.get("root_sha"))
            or not _matches(SHA, identity.get("release_root_sha"))
            or not _matches(SHA, identity.get("root_tree"))
            or identity.get("android_job") not in ("success", "skipped")
            or not _matches(HEX_256, identity.get("plan_sha256"))):
        raise ValueError("Published CI evidence has an invalid identity")
    _positive_int(identity.get("run_id"), "run ID")
    _positive_int(identity.get("run_attempt"), "run attempt")
    _positive_int(identity.get("run_number"), "run number")
    resolved_sources = _validate_sources(identity.get("sources", {}))
    artifact = identity.get("artifact")
    if (not isinstance(artifact, dict)
            or type(artifact.get("id")) is not int or artifact["id"] < 1
            or artifact.get("name") != f"{ARTIFACT_PREFIX}{identity['run_attempt']}"
            or not _matches(ARTIFACT_DIGEST, artifact.get("digest"))):
        raise ValueError("Published CI evidence has no immutable artifact identity")
    if root_sha is not None and identity["release_root_sha"] != root_sha:
        raise ValueError("Published CI evidence does not match the release root SHA")
    if sources is not None and resolved_sources != sources:
        raise ValueError("Published CI evidence does not match the release gitlinks")
    return identity


def validate_proof(proof, *, require_artifact=True):
    if not isinstance(proof, dict) or type(proof.get("schema_version")) is not int or proof.get("schema_version") != 1:
        raise ValueError("Android verification evidence is missing or has an unsupported schema")
    if not _matches(HEX_256, proof.get("android_input_sha256")):
        raise ValueError("Android verification evidence has an invalid input digest")
    if not _matches(SHA, proof.get("mobile_sha")):
        raise ValueError("Android verification evidence has an invalid mobile SHA")
    verified_by = proof.get("verified_by")
    if not isinstance(verified_by, dict):
        raise ValueError("Android verification evidence has no CI identity")
    if (not isinstance(verified_by.get("repository_id"), str)
            or not verified_by["repository_id"].isdigit()
            or verified_by.get("workflow_path") != WORKFLOW_PATH
            or verified_by.get("event") != "pull_request"
            or verified_by.get("base_branch") != "main"
            or verified_by.get("head_branch") != "develop"
            or verified_by.get("head_repository_id") != verified_by.get("repository_id")
            or type(verified_by.get("pull_request")) is not int
            or verified_by["pull_request"] < 1
            or not _matches(SHA, verified_by.get("root_sha"))
            or not _matches(SHA, verified_by.get("root_tree"))):
        raise ValueError("Android verification evidence has an invalid CI identity")
    _positive_int(verified_by.get("run_id"), "run ID")
    _positive_int(verified_by.get("run_attempt"), "run attempt")
    sources = _validate_sources(verified_by.get("sources", {}))
    if sources["mobile"] != proof["mobile_sha"]:
        raise ValueError("Android verification evidence does not match its mobile source")
    if require_artifact:
        artifact = verified_by.get("artifact")
        if (not isinstance(artifact, dict)
                or type(artifact.get("id")) is not int or artifact["id"] < 1
                or artifact.get("name") != f"{ARTIFACT_PREFIX}{verified_by['run_attempt']}"
                or not _matches(ARTIFACT_DIGEST, artifact.get("digest"))):
            raise ValueError("Android verification evidence has no immutable artifact identity")
        if not isinstance(proof.get("origin_release"), str) or not re.fullmatch(r"release-[a-f0-9]{32}", proof["origin_release"]):
            raise ValueError("Android verification evidence has no originating release")
        reused = proof.get("reused_from_release")
        if reused is not None and (not isinstance(reused, str)
                                   or not re.fullmatch(r"release-[a-f0-9]{32}", reused)):
            raise ValueError("Android verification evidence has an invalid reuse reference")
    return proof


def validate_manifest_android(manifest):
    """Validate that a main release's Android claim follows its CI plan decision."""
    if not isinstance(manifest, dict) or manifest.get("channel") != "main":
        raise ValueError("Android verification evidence is only valid on main releases")
    sources = _validate_sources(manifest.get("sources", {}))
    ci = validate_ci_identity(manifest.get("ci_evidence"), root_sha=manifest.get("root_sha"), sources=sources)
    proof = validate_proof(manifest.get("android_verification"))
    if (proof["android_input_sha256"] != manifest.get("android_input_sha256")
            or proof["mobile_sha"] != manifest.get("android_verified_mobile_sha")):
        raise ValueError("Main release Android verification fields are inconsistent")
    plan = manifest.get("ci_plan")
    if not isinstance(plan, dict) or plan.get("android_input_sha256") != proof["android_input_sha256"]:
        raise ValueError("Main release CI plan does not identify the verified Android inputs")
    components = plan.get("components")
    if not isinstance(components, dict):
        raise ValueError("Main release CI plan has no component decisions")
    android_job = components.get("mobile_android")
    if not isinstance(android_job, dict):
        raise ValueError("Main release CI plan has no Android job decision")
    if type(android_job.get("run")) is not bool:
        raise ValueError("Main release CI plan has no Android job decision")
    if ci["android_job"] == "success":
        verified_by = proof["verified_by"]
        if (android_job["run"] is not True
                or proof.get("origin_release") != manifest.get("release")
                or proof.get("reused_from_release") is not None
                or proof["mobile_sha"] != sources["mobile"]
                or verified_by.get("repository_id") != ci["repository_id"]
                or verified_by.get("run_id") != ci["run_id"]
                or verified_by.get("run_attempt") != ci["run_attempt"]
                or verified_by.get("artifact") != ci["artifact"]):
            raise ValueError("Main release claims Android success without evidence from its CI run")
        return proof
    if ci["android_job"] != "skipped" or android_job["run"] is not False:
        raise ValueError("Main release Android job result does not match its CI plan")
    baseline = plan.get("baseline")
    if not isinstance(baseline, dict):
        raise ValueError("Main release CI plan has no Android proof baseline")
    baseline_proof = validate_proof(baseline.get("android_verification"))
    current_proof = dict(proof)
    baseline_copy = dict(baseline_proof)
    current_proof.pop("reused_from_release", None)
    baseline_copy.pop("reused_from_release", None)
    if (baseline.get("release") != proof.get("reused_from_release")
            or not isinstance(baseline.get("release"), str)
            or not re.fullmatch(r"release-[a-f0-9]{32}", baseline["release"])
            or baseline_copy != current_proof
            or baseline_proof["android_input_sha256"] != plan["android_input_sha256"]):
        raise ValueError("Main release reuses Android proof without an exact baseline release reference")
    return proof


def make_ci_evidence(plan, root_tree, event, job_results):
    if not isinstance(plan, dict) or plan.get("version") != 1:
        raise ValueError("The integrated CI plan is missing or unsupported")
    current = plan.get("current", {})
    sources = _validate_sources(current.get("sources", {}))
    root_sha = current.get("root_sha", "")
    if not _matches(SHA, root_sha) or not _matches(SHA, root_tree):
        raise ValueError("The integrated CI root identity is invalid")
    pull = event.get("pull_request", {})
    base = pull.get("base", {})
    head = pull.get("head", {})
    base_repo = base.get("repo", {}) or {}
    head_repo = head.get("repo", {}) or {}
    repository_id = os.environ.get("GITHUB_REPOSITORY_ID", "")
    pr_number = event.get("number")
    run_id = int(os.environ.get("GITHUB_RUN_ID", "0"))
    run_attempt = int(os.environ.get("GITHUB_RUN_ATTEMPT", "0"))
    run_number = int(os.environ.get("GITHUB_RUN_NUMBER", "0"))
    if (event.get("action") not in ("opened", "edited", "reopened", "synchronize")
            or base.get("ref") != "main" or head.get("ref") != "develop"
            or not repository_id.isdigit() or base_repo.get("id") != int(repository_id)
            or head_repo.get("id") != int(repository_id)
            or type(pr_number) is not int or pr_number < 1):
        raise ValueError("CI evidence is only issued for a same-repository develop-to-main pull request")
    if not _matches(HEX_256, plan.get("android_input_sha256")):
        raise ValueError("The integrated CI plan has an invalid Android input digest")
    android = plan.get("components", {}).get("mobile_android", {})
    android_ran = android.get("run")
    if type(android_ran) is not bool:
        raise ValueError("The integrated CI plan has no Android job decision")
    if android_ran:
        if job_results.get("mobile_android") != "success":
            raise ValueError("Android verification was required but did not succeed")
        verified = {
            "schema_version": 1,
            "android_input_sha256": plan["android_input_sha256"],
            "mobile_sha": sources["mobile"],
            "verified_by": {
                "repository_id": repository_id,
                "workflow_path": WORKFLOW_PATH,
                "run_id": run_id,
                "run_attempt": run_attempt,
                "event": "pull_request",
                "pull_request": pr_number,
                "base_branch": "main",
                "head_branch": "develop",
                "head_repository_id": repository_id,
                "root_sha": root_sha,
                "root_tree": root_tree,
                "sources": sources,
            },
        }
        reuse_release = None
    else:
        if job_results.get("mobile_android") != "skipped":
            raise ValueError("The Android job was skipped inconsistently with the integrated CI plan")
        baseline = plan.get("baseline", {})
        verified = baseline.get("android_verification")
        validate_proof(verified)
        if verified["android_input_sha256"] != plan["android_input_sha256"]:
            raise ValueError("Skipped Android verification has no proof for the current input digest")
        reuse_release = baseline.get("release")
        if not isinstance(reuse_release, str) or not re.fullmatch(r"release-[a-f0-9]{32}", reuse_release):
            raise ValueError("Skipped Android verification has no source release identity")
    return {
        "schema_version": 1,
        "repository_id": repository_id,
        "workflow_path": WORKFLOW_PATH,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "run_number": run_number,
        "event": "pull_request",
        "pull_request": pr_number,
        "base_branch": "main",
        "head_branch": "develop",
        "head_repository_id": repository_id,
        "root_sha": root_sha,
        "root_tree": root_tree,
        "sources": sources,
        "plan": plan,
        "android_job": "success" if android_ran else "skipped",
        "android_verification": verified,
        "android_reused_from_release": reuse_release,
    }


def write(path):
    plan = json.loads(os.environ["NFR14_CI_PLAN"])
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    results = json.loads(os.environ["NFR14_JOB_RESULTS"])
    evidence = make_ci_evidence(plan, os.environ.get("NFR14_ROOT_TREE", ""), event, results)
    Path(path).write_text(json.dumps(evidence, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def _run_pull_requests(run, token):
    pulls = run.get("pull_requests")
    if not pulls:
        detail = _api(f"actions/runs/{run['id']}", token)
        pulls = detail.get("pull_requests", [])
    return pulls


def _pull_request_is_merged(pull, token):
    """Handle both merged_at list responses and canonical PR response fields."""
    if type(pull.get("merged")) is bool:
        return pull["merged"]
    if "merged_at" in pull:
        return isinstance(pull["merged_at"], str) and bool(pull["merged_at"])
    number = pull.get("number")
    if type(number) is not int or number < 1:
        return False
    detail = _api(f"pulls/{number}", token)
    if detail.get("number") != number:
        return False
    if type(detail.get("merged")) is bool:
        return detail["merged"]
    return isinstance(detail.get("merged_at"), str) and bool(detail["merged_at"])


def _artifact_candidates(run, token):
    items = _api(f"actions/runs/{run['id']}/artifacts?per_page=100", token).get("artifacts", [])
    attempt = run.get("run_attempt")
    expected_name = f"{ARTIFACT_PREFIX}{attempt}"
    return [item for item in items if item.get("name") == expected_name and not item.get("expired")]


def _validate_resolved(evidence, artifact, run, pull, expected):
    if (not isinstance(evidence, dict) or type(evidence.get("schema_version")) is not int
            or evidence.get("schema_version") != 1
            or evidence.get("repository_id") != expected["repository_id"]
            or evidence.get("workflow_path") != WORKFLOW_PATH
            or evidence.get("run_id") != run.get("id")
            or evidence.get("run_attempt") != run.get("run_attempt")
            or evidence.get("run_number") != run.get("run_number")
            or evidence.get("event") != "pull_request"
            or evidence.get("pull_request") != pull.get("number")
            or evidence.get("base_branch") != "main"
            or evidence.get("head_branch") != "develop"
            or evidence.get("head_repository_id") != expected["repository_id"]
            or not _matches(SHA, evidence.get("root_sha"))
            or evidence.get("root_tree") != expected["root_tree"]
            or evidence.get("sources") != expected["sources"]):
        raise ValueError("The successful CI artifact does not match the integrated source tree")
    plan = evidence.get("plan")
    if not isinstance(plan, dict):
        raise ValueError("The successful CI artifact has no integrated plan")
    current = plan.get("current")
    components = plan.get("components")
    if (not isinstance(current, dict) or not isinstance(components, dict)
            or current.get("root_sha") != evidence.get("root_sha")
            or current.get("sources") != expected["sources"]
            or plan.get("android_input_sha256") != expected["android_input_sha256"]):
        raise ValueError("The successful CI artifact does not match the release plan")
    android_job = components.get("mobile_android")
    if not isinstance(android_job, dict) or type(android_job.get("run")) is not bool:
        raise ValueError("The successful CI artifact has no Android job decision")
    if android_job["run"]:
        proof = evidence.get("android_verification")
        if (evidence.get("android_job") != "success" or not isinstance(proof, dict)
                or proof.get("mobile_sha") != expected["sources"]["mobile"]):
            raise ValueError("The successful CI artifact has no passing Android verification")
        verified_by = proof.get("verified_by")
        if not isinstance(verified_by, dict):
            raise ValueError("The Android proof does not belong to the selected CI run")
        if (proof.get("android_input_sha256") != expected["android_input_sha256"]
                or verified_by.get("run_id") != run.get("id")
                or verified_by.get("run_attempt") != run.get("run_attempt")
                or verified_by.get("artifact") is not None):
            raise ValueError("The Android proof does not belong to the selected CI run")
    else:
        if evidence.get("android_job") != "skipped":
            raise ValueError("The successful CI artifact has an inconsistent Android job result")
        proof = validate_proof(evidence.get("android_verification"))
        baseline = plan.get("baseline")
        if not isinstance(baseline, dict):
            raise ValueError("Skipped Android verification has no validated baseline")
        if (proof != baseline.get("android_verification")
                or proof.get("android_input_sha256") != expected["android_input_sha256"]
                or evidence.get("android_reused_from_release") != baseline.get("release")):
            raise ValueError("Skipped Android verification does not reference the exact validated baseline proof")
    if (type(artifact.get("id")) is not int or artifact["id"] < 1
            or artifact.get("name") != f"{ARTIFACT_PREFIX}{run.get('run_attempt')}"
            or not _matches(ARTIFACT_DIGEST, artifact.get("digest"))):
        raise ValueError("The selected CI artifact identity is invalid")
    artifact_identity = {
        "id": artifact["id"], "name": artifact["name"], "digest": artifact["digest"],
    }
    return {"artifact": artifact_identity, "evidence": evidence}


def resolve(output_path, root_sha, root_tree, sources, plan):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("A GitHub token with Actions and pull request read access is required")
    sources = _validate_sources(sources)
    if not _matches(SHA, root_sha) or not _matches(SHA, root_tree):
        raise ValueError("The publication root identity is invalid")
    expected = {
        "repository_id": os.environ.get("GITHUB_REPOSITORY_ID", ""),
        "root_sha": root_sha, "root_tree": root_tree, "sources": sources,
        "android_input_sha256": plan.get("android_input_sha256"),
    }
    if (not expected["repository_id"].isdigit()
            or not _matches(HEX_256, expected["android_input_sha256"])):
        raise ValueError("The publication context does not identify the candidate CI inputs")
    associated = _api(f"commits/{root_sha}/pulls?per_page=100", token)
    repository = os.environ["GITHUB_REPOSITORY"].casefold()
    pull_requests = []
    for pull in associated:
        base_repo = pull.get("base", {}).get("repo", {}) or {}
        head_repo = pull.get("head", {}).get("repo", {}) or {}
        if (pull.get("base", {}).get("ref") == "main"
                and pull.get("head", {}).get("ref") == "develop"
                and base_repo.get("id") == int(expected["repository_id"])
                and head_repo.get("id") == int(expected["repository_id"])
                and (head_repo.get("full_name", "").casefold() == repository)
                and _pull_request_is_merged(pull, token)):
            pull_requests.append(pull)
    if len(pull_requests) != 1:
        raise ValueError("The main commit must map to exactly one merged same-repository develop pull request")
    pull = pull_requests[0]
    runs = []
    for page in range(1, 11):
        query = urllib.parse.urlencode({"event": "pull_request", "branch": "develop", "per_page": 100, "page": page})
        batch = _api(f"actions/workflows/ci.yml/runs?{query}", token).get("workflow_runs", [])
        runs.extend(batch)
        if len(batch) < 100:
            break
    runs = sorted(runs, key=lambda item: (item.get("run_number", 0), item.get("run_attempt", 0)), reverse=True)
    for run in runs:
        path = run.get("path", "").split("@", 1)[0]
        if (path != WORKFLOW_PATH or run.get("event") != "pull_request"
                or run.get("status") != "completed" or run.get("conclusion") != "success"):
            continue
        run_pulls = _run_pull_requests(run, token)
        if not any(item.get("number") == pull.get("number")
                   and item.get("base", {}).get("ref") == "main"
                   and item.get("head", {}).get("ref") == "develop"
                   and (item.get("head", {}).get("repo", {}) or {}).get("id") == int(expected["repository_id"])
                   and (item.get("base", {}).get("repo", {}) or {}).get("id") == int(expected["repository_id"])
                   for item in run_pulls):
            continue
        for artifact in _artifact_candidates(run, token):
            if (type(artifact.get("id")) is not int or artifact["id"] < 1
                    or not _matches(ARTIFACT_DIGEST, artifact.get("digest"))):
                continue
            try:
                evidence = _download_artifact(artifact["id"], token, artifact["digest"])
                resolved = _validate_resolved(evidence, artifact, run, pull, expected)
            except (ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile):
                continue
            jobs = _api(f"actions/runs/{run['id']}/jobs?filter=latest&per_page=100", token).get("jobs", [])
            final_jobs = [job for job in jobs if job.get("name") == "Integrated CI / result"]
            if len(final_jobs) != 1 or final_jobs[0].get("conclusion") != "success":
                continue
            resolved["run"] = {
                "id": run["id"], "attempt": run["run_attempt"], "number": run["run_number"],
                "workflow_path": WORKFLOW_PATH,
            }
            Path(output_path).write_text(json.dumps(resolved, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            return resolved
    raise ValueError("No successful Integrated CI evidence matches the exact main source tree")


def bind_for_release(resolved_path, *, snapshot, plan, release):
    resolved = json.loads(Path(resolved_path).read_text(encoding="utf-8"))
    evidence = resolved.get("evidence")
    artifact = resolved.get("artifact")
    run = resolved.get("run")
    if not isinstance(evidence, dict) or not isinstance(artifact, dict) or not isinstance(run, dict):
        raise ValueError("Resolved CI evidence is incomplete")
    if ((snapshot.get("source_ref") or "refs/heads/main") != "refs/heads/main"
            or evidence.get("root_tree") != integration.git("rev-parse", f"{snapshot['root_sha']}^{{tree}}")
            or evidence.get("sources") != snapshot.get("sources")
            or evidence.get("plan") != plan
            or run.get("id") != evidence.get("run_id")
            or run.get("attempt") != evidence.get("run_attempt")):
        raise ValueError("Resolved CI evidence does not match the immutable integration snapshot")
    identity = {
        "schema_version": 1,
        "repository_id": evidence["repository_id"], "workflow_path": WORKFLOW_PATH,
        "run_id": evidence["run_id"], "run_attempt": evidence["run_attempt"],
        "run_number": evidence["run_number"], "event": evidence["event"],
        "pull_request": evidence["pull_request"], "root_sha": evidence["root_sha"],
        "release_root_sha": snapshot["root_sha"],
        "root_tree": evidence["root_tree"], "sources": evidence["sources"],
        "base_branch": evidence["base_branch"], "head_branch": evidence["head_branch"],
        "android_job": evidence["android_job"], "artifact": artifact,
        "plan_sha256": hashlib.sha256(json.dumps(evidence["plan"], sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
    proof = evidence["android_verification"]
    if evidence["android_job"] == "success":
        proof = dict(proof)
        verified_by = dict(proof["verified_by"])
        verified_by["artifact"] = dict(artifact)
        proof["verified_by"] = verified_by
        proof["origin_release"] = release
    else:
        baseline = plan.get("baseline", {})
        if (proof != baseline.get("android_verification")
                or evidence.get("android_reused_from_release") != baseline.get("release")
                or proof.get("android_input_sha256") != plan.get("android_input_sha256")):
            raise ValueError("CI reused Android proof does not match the validated publication baseline")
        proof = dict(proof)
        proof["reused_from_release"] = baseline["release"]
    validate_proof(proof)
    return identity, proof


def main():
    if len(os.sys.argv) >= 2 and os.sys.argv[1] == "write" and len(os.sys.argv) == 3:
        write(os.sys.argv[2])
        return
    if len(os.sys.argv) >= 2 and os.sys.argv[1] == "resolve" and len(os.sys.argv) == 3:
        inputs = json.loads(os.environ["NFR14_CI_RESOLVE_INPUTS"])
        resolved = resolve(os.sys.argv[2], inputs["root_sha"], inputs["root_tree"], inputs["sources"], inputs["plan"])
        if os.environ.get("GITHUB_OUTPUT"):
            rendered = json.dumps(resolved["evidence"]["plan"], sort_keys=True, separators=(",", ":"))
            delimiter = "NFR14_PLAN_" + os.urandom(12).hex()
            with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
                stream.write(f"plan<<{delimiter}\n{rendered}\n{delimiter}\n")
        return
    raise SystemExit("Usage: ci_evidence.py write OUTPUT | resolve OUTPUT")


if __name__ == "__main__":
    main()
