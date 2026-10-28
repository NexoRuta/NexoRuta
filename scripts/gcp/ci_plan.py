"""Fail-closed component selection for integrated validation and image builds."""

import json
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

import integration

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ("backend", "frontend", "mobile")
SERVICES = ("api", "worker", "admin", "backoffice", "commerce", "tracking")
DISPATCH_REPOSITORIES = {
    "NexoRuta/NexoRuta-Backend": "backend",
    "NexoRuta/NexoRuta-Frontend": "frontend",
    "NexoRuta/NexoRuta-Mobile": "mobile",
}
SHA = re.compile(r"[a-f0-9]{40}\Z")


def git(repo, *args, check=True):
    result = subprocess.run(["git", "-C", str(repo), *args], text=True,
                            capture_output=True, check=False)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result


def ensure_commit(repo, sha):
    if not SHA.fullmatch(sha):
        raise ValueError("Expected a full lowercase commit SHA")
    if git(repo, "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode:
        git(repo, "fetch", "--no-tags", "--depth=1", "origin", sha)


def paths_between(repo, base, head):
    ensure_commit(repo, base)
    ensure_commit(repo, head)
    result = git(repo, "diff", "--no-ext-diff", "--name-only", base, head)
    return tuple(path for path in result.stdout.splitlines() if path)


def docs_only(paths):
    return bool(paths) and all(
        path == "README.md" or path.startswith("docs/") or
        (path.lower().endswith(".md") and not path.startswith(".github/"))
        for path in paths
    )


def is_geojson(path):
    return path.endswith("src/ZonasCobertura/Data/departamentos-uruguay.geojson")


def is_contract_change(path):
    return (
        path.startswith("src/NexoRuta.Api/") or
        path.startswith("src/NexoRuta.Domain/") or
        path.startswith("src/NexoRuta.Application/Administracion/") or
        path.startswith("src/NexoRuta.Infrastructure/Persistence/Migrations/") or
        path.startswith("src/NexoRuta.Infrastructure/Persistence/Contexts/") or
        path.endswith("openapi.json") or path.endswith("openapi.yaml") or
        path.endswith(".proto")
    )


def component_changes(name, paths):
    changed = bool(paths) and not docs_only(paths)
    build_changed = changed and any(not path.startswith("tests/") for path in paths)
    return changed, build_changed, tuple(path for path in paths if is_contract_change(path)), any(is_geojson(p) for p in paths)


def android_input_sha(repo, sha):
    tree = git(repo, "ls-tree", "-r", sha).stdout.splitlines()
    relevant = []
    for entry in tree:
        metadata, path = entry.split("\t", 1)
        if (path.startswith("src/") or path in {"global.json", "NuGet.Config", "Directory.Build.props", "Directory.Build.targets"}
                or path.startswith(".config/") or path == "tools/preparar-r8.py"):
            relevant.append(metadata + "\t" + path)
    if not relevant:
        raise ValueError("Could not find mobile Android build inputs in the source tree")
    return hashlib.sha256(("\n".join(relevant) + "\n").encode()).hexdigest()


def release_baseline():
    """Read only the latest complete integration release, never a running job."""
    releases = integration.github("releases?per_page=100")
    for release in releases:
        tag = release.get("tag_name", "")
        if release.get("draft") or not release.get("prerelease") or not re.fullmatch(integration.TAG, tag):
            continue
        match = re.search(r"```json\s*(\{.*?\})\s*```", release.get("body", ""), re.DOTALL)
        if not match:
            continue
        manifest = json.loads(match.group(1))
        if manifest.get("integration_tag") != tag:
            raise ValueError("Latest integration release manifest has a mismatched tag")
        integration.validate_sources(manifest.get("sources", {}))
        if not SHA.fullmatch(manifest.get("root_sha", "")):
            raise ValueError("Latest integration release has an invalid root SHA")
        images = manifest.get("images", {})
        if set(images) != set(SERVICES) or any(not re.search(r"@sha256:[a-f0-9]{64}\Z", images[name]) for name in SERVICES):
            raise ValueError("Latest integration release is missing a complete image manifest")
        return manifest
    return None


def validate_dispatch(event, sources):
    if os.environ.get("GITHUB_EVENT_NAME") != "repository_dispatch":
        return
    payload = event.get("client_payload")
    if not isinstance(payload, dict):
        raise ValueError("repository_dispatch must include a client_payload")
    repository, sha = payload.get("repository"), payload.get("sha")
    component = DISPATCH_REPOSITORIES.get(repository)
    if component is None or not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise ValueError("repository_dispatch source is not an allowed main-branch commit")
    if sources.get(component) != sha:
        raise ValueError("Resolved source does not match repository_dispatch SHA")
    checkout = ROOT / component
    # Prove the notified commit is reachable from that repository's main branch.
    shallow = git(checkout, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"
    args = ["fetch", "--no-tags"]
    if shallow:
        args.append("--unshallow")
    args.extend(["origin", "main"])
    git(checkout, *args)
    if git(checkout, "merge-base", "--is-ancestor", sha, "FETCH_HEAD", check=False).returncode:
        raise ValueError("repository_dispatch SHA is not reachable from the component main branch")


def make_plan(root_sha, sources, baseline, root_paths, component_paths, android_key, force_full_reason=None):
    integration.validate_sources(sources)
    unknown = force_full_reason
    if not baseline:
        unknown = unknown or "no complete integration baseline"
    elif not SHA.fullmatch(baseline.get("root_sha", "")):
        unknown = unknown or "invalid baseline root SHA"

    source_changes = {}
    build_changes = {}
    contract_changes = {}
    geojson_changed = False
    for name in COMPONENTS:
        paths = tuple(component_paths.get(name, ()))
        changed, built, contracts, geojson = component_changes(name, paths)
        source_changes[name] = changed
        build_changes[name] = built
        contract_changes[name] = contracts
        geojson_changed |= geojson

    root_code_paths = tuple(path for path in root_paths if path not in COMPONENTS and not docs_only((path,)))
    if root_code_paths:
        unknown = unknown or "root pipeline, build, or deployment inputs changed"

    if unknown:
        source_changes = {name: True for name in COMPONENTS}
        build_changes = {name: True for name in COMPONENTS}
        contract_changes = {name: () for name in COMPONENTS}
        geojson_changed = False

    backend = source_changes["backend"]
    frontend = source_changes["frontend"]
    mobile = source_changes["mobile"]
    backend_contract = bool(contract_changes["backend"])
    current_android_verified = baseline and baseline.get("android_input_sha256") == android_key
    mobile_android = build_changes["mobile"] or not current_android_verified or bool(unknown)

    components = {
        "backend": {"run": backend, "reason": "backend source changed" if backend else "backend source unchanged or docs only"},
        "frontend": {"run": frontend or backend_contract or geojson_changed,
                     "reason": "frontend source changed" if frontend else "backend contract or canonical map changed" if backend_contract or geojson_changed else "frontend inputs unchanged"},
        "mobile_portable": {"run": mobile or backend_contract,
                             "reason": "mobile source changed" if mobile else "backend contract changed" if backend_contract else "mobile inputs unchanged"},
        "mobile_android": {"run": mobile_android,
                           "reason": "mobile app build inputs changed" if build_changes["mobile"]
                           else "no Android verification for this app-input digest" if mobile_android
                           else "matching Android app-input digest was already verified"},
    }
    infrastructure = bool(root_code_paths) or bool(unknown)
    cloudsql = bool(unknown) or infrastructure or backend and any(
        "Persistence/" in path or "provision-rls" in path or "CloudSql" in path
        for path in component_paths.get("backend", ())
    )
    bundle_required = bool(unknown) or infrastructure or backend and any(
        "Persistence/Migrations/" in path or path.endswith("provision-rls-runtime-roles.sql")
        for path in component_paths.get("backend", ())
    )

    images = set()
    if unknown:
        images.update(SERVICES)
    else:
        if build_changes["backend"]:
            images.update(("api", "worker"))
        if build_changes["frontend"]:
            images.update(("admin", "backoffice", "commerce", "tracking"))
        if geojson_changed:
            images.add("backoffice")

    publish_required = bool(
        infrastructure or cloudsql or images or
        any(job["run"] for job in components.values())
    )
    return {
        "version": 1,
        "baseline": {
            "integration_tag": baseline.get("integration_tag") if baseline else None,
            "release": baseline.get("release") if baseline else None,
            "root_sha": baseline.get("root_sha") if baseline else None,
            "sources": baseline.get("sources") if baseline else None,
            "android_verified_mobile_sha": baseline.get("android_verified_mobile_sha") if baseline else None,
            "android_input_sha256": baseline.get("android_input_sha256") if baseline else None,
        },
        "current": {"root_sha": root_sha, "sources": sources},
        "android_input_sha256": android_key,
        "reason": unknown or "compared current sources with the latest complete integration",
        "root_paths": list(root_paths),
        "component_paths": {name: list(component_paths.get(name, ())) for name in COMPONENTS},
        "infrastructure": {"run": infrastructure, "reason": "root build/deploy inputs changed" if infrastructure else "root build/deploy inputs unchanged"},
        "cloudsql": {"run": bool(cloudsql), "reason": "database or infrastructure inputs changed" if cloudsql else "database inputs unchanged"},
        "bundle_required": bundle_required,
        "components": components,
        "images": [service for service in SERVICES if service in images],
        "publish_required": publish_required,
    }


def plan():
    sources = integration.validate_sources(json.loads((ROOT / "sources.json").read_text(encoding="utf-8")))
    root_sha = git(ROOT, "rev-parse", "HEAD").stdout.strip()
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event = json.loads(Path(event_path).read_text(encoding="utf-8")) if event_path else {}
    validate_dispatch(event, sources)

    baseline = None
    root_base = None
    force_full_reason = None
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name in ("workflow_dispatch", "schedule"):
        force_full_reason = f"{event_name} requested full validation"
    if event_name == "pull_request":
        root_base = event.get("pull_request", {}).get("base", {}).get("sha")
        if not isinstance(root_base, str) or not SHA.fullmatch(root_base):
            force_full_reason = "pull request base SHA is unavailable"
        else:
            try:
                ensure_commit(ROOT, root_base)
                root_base_sources = integration.pinned_sources(root_base)
                # A PR may reuse release evidence only if its base gitlinks identify
                # the same component combination as the latest complete release.
                proof = release_baseline()
                if proof and proof["sources"] == root_base_sources:
                    baseline = {**proof, "root_sha": root_base, "sources": root_base_sources}
                else:
                    baseline = {"root_sha": root_base, "sources": root_base_sources}
                    force_full_reason = "pull request base combination has no successful integrated baseline"
            except Exception as error:  # A missing baseline must never become a skip.
                force_full_reason = f"cannot establish pull request baseline: {type(error).__name__}"
    else:
        try:
            baseline = release_baseline()
        except Exception as error:  # API/history failures fail closed to full validation.
            force_full_reason = f"cannot read complete integration baseline: {type(error).__name__}"

    if not baseline and not force_full_reason:
        force_full_reason = "no complete integration baseline"

    root_paths = ()
    component_paths = {name: () for name in COMPONENTS}
    if baseline and not force_full_reason:
        try:
            root_paths = paths_between(ROOT, baseline["root_sha"], root_sha)
            for name in COMPONENTS:
                old_sha = baseline["sources"][name]
                if old_sha != sources[name]:
                    component_paths[name] = paths_between(ROOT / name, old_sha, sources[name])
        except Exception as error:
            force_full_reason = f"cannot classify complete source history: {type(error).__name__}"
            root_paths = ("<classification-failed>",)

    android_key = android_input_sha(ROOT / "mobile", sources["mobile"])
    result = make_plan(root_sha, sources, baseline, root_paths, component_paths, android_key, force_full_reason)
    rendered = json.dumps(result, separators=(",", ":"), sort_keys=True)
    print(json.dumps(result, indent=2, sort_keys=True))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write("sources=" + json.dumps(sources, separators=(",", ":")) + "\n")
            output.write("plan=" + rendered + "\n")


def main():
    if sys.argv[1:] == ["plan"]:
        plan()
    else:
        raise SystemExit("Usage: ci_plan.py plan")


if __name__ == "__main__":
    main()
