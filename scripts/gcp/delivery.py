"""Resolve/tested sources, publish immutable images, and deploy by digest."""

import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

import demo_session as session
import integration
import publication

ROOT = session.ROOT
SERVICES = ("api", "worker", "admin", "backoffice", "commerce", "tracking")


def sources():
    result = {}
    for name in ("backend", "frontend", "mobile"):
        ref = os.environ.get(f"{name.upper()}_REF", "main")
        if not re.fullmatch(r"(?:develop|main|[a-f0-9]{40})", ref):
            raise ValueError(f"{name}: use main, develop or a full commit SHA")
        session.command("git", "-C", str(ROOT / name), "fetch", "--depth=1", "origin", ref)
        sha = session.command("git", "-C", str(ROOT / name), "rev-parse", "FETCH_HEAD", capture=True).strip()
        session.command("git", "-C", str(ROOT / name), "checkout", "--detach", sha)
        result[name] = sha
    (ROOT / "sources.json").write_text(json.dumps(result), encoding="utf-8")
    return result


def extract_archive(archive, destination):
    destination = Path(destination).resolve()
    for member in archive.getmembers():
        if not (member.isfile() or member.isdir()):
            raise ValueError("Release archives may contain only files and directories")
        if not (destination / member.name).resolve().is_relative_to(destination):
            raise ValueError("Unsafe archive member")
    archive.extractall(destination)


def stage_sources(destination):
    for name in ("backend", "frontend"):
        archive = subprocess.check_output([shutil.which("git"), "-C", str(ROOT / name), "archive", "HEAD"])
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            extract_archive(source, destination / name)
        shutil.copyfile(ROOT / "deploy/gcp/Dockerfile", destination / name / "Dockerfile.deploy")


def create_bundle(destination):
    assets = destination / "assets"
    shutil.copytree(ROOT / "deploy/gcp", assets)
    sql = assets / "sql"
    shutil.copyfile(ROOT / "backend/scripts/provision-rls-runtime-roles.sql", sql / "runtime-roles.sql")
    migrations = ROOT / "backend/src/NexoRuta.Infrastructure/Persistence/Migrations"
    roles = set()
    for path in migrations.glob("*.cs"):
        roles.update(re.findall(r"CREATE ROLE (nexoruta_[a-z_]+)", path.read_text(encoding="utf-8-sig")))
    if "nexoruta_schema_owner" not in roles:
        raise ValueError("Could not discover the database ownership roles from migrations")
    statements = ["CREATE EXTENSION IF NOT EXISTS postgis;", "CREATE EXTENSION IF NOT EXISTS pgcrypto;"]
    for role in sorted(roles):
        statements.append(
            f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='{role}') "
            f"THEN CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS; END IF; END $$;"
        )
        # CREATEROLE already grants ADMIN to the creator. Regranting ADMIN to
        # yourself is rejected by PostgreSQL 18; only enable object privileges.
        statements.append(f"GRANT {role} TO postgres WITH INHERIT TRUE, SET TRUE;")
    statements.append("GRANT CREATE ON DATABASE nexoruta TO nexoruta_schema_owner;")
    statements.append("CREATE SCHEMA IF NOT EXISTS nexoruta_app AUTHORIZATION nexoruta_schema_owner;")
    statements.append(f"GRANT CREATE ON SCHEMA public, nexoruta_app TO {', '.join(sorted(roles))};")
    (sql / "preflight.sql").write_text("\n".join(statements) + "\n", encoding="utf-8")
    with open(sql / "postflight.sql", "a", encoding="utf-8") as output:
        restricted = sorted(roles - {"nexoruta_schema_owner"})
        output.write(f"\nREVOKE CREATE ON SCHEMA public, nexoruta_app FROM {', '.join(restricted)};\n")
    bundle = destination / "bundle.tar.gz"
    with tarfile.open(bundle, "w:gz") as archive:
        for path in sorted(assets.rglob("*")):
            if path.is_file():
                archive.add(path, arcname=path.relative_to(assets).as_posix(), recursive=False)
    return bundle


def build():
    config = session.configuration()
    if os.environ.get("RELEASE_CHANNEL") != "main":
        raise ValueError("Builds must explicitly target RELEASE_CHANNEL=main after CI tests main commits")
    # Publication uses the already-tested tag, never resolves component branches again.
    snapshot = integration.verify_checkout(os.environ["INTEGRATION_TAG"], os.environ.get("INTEGRATION_COMMIT"))
    project, region = config["GCP_PROJECT_ID"], session.REGION
    bucket = os.environ.get("GCP_DELIVERY_BUCKET", f"{project}-nexoruta-delivery")
    registry = f"{region}-docker.pkg.dev/{project}/nexoruta"
    release = f"release-{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory(prefix="nexoruta-build-") as temp:
        work = Path(temp)
        stage_sources(work)
        build_config = {
            "steps": [], "images": [], "timeout": "2400s",
            "options": {"logging": "CLOUD_LOGGING_ONLY", "machineType": "E2_HIGHCPU_8"},
        }
        for name in SERVICES:
            context = "backend" if name in ("api", "worker") else "frontend"
            assembly = "NexoRuta." + name.capitalize() if context == "backend" else "NexoRuta." + {"admin": "Admin", "backoffice": "Backoffice", "commerce": "Commerce", "tracking": "Tracking"}[name]
            tag = f"{registry}/{name}:{release}"
            build_config["steps"].append({
                "name": "gcr.io/cloud-builders/docker",
                "args": ["build", "-t", tag, "--build-arg", f"PROJECT=src/{assembly}/{assembly}.csproj", "--build-arg", f"ASSEMBLY={assembly}", "-f", f"{context}/Dockerfile.deploy", context],
            })
            build_config["images"].append(tag)
        config_file = work / "cloudbuild.json"
        config_file.write_text(json.dumps(build_config), encoding="utf-8")
        submitted = json.loads(session.command(
            "gcloud", "builds", "submit", str(work), f"--config={config_file}",
            f"--project={project}", f"--region={region}", "--async", "--quiet", "--format=json",
            f"--service-account=projects/{project}/serviceAccounts/nexoruta-demo-builder@{project}.iam.gserviceaccount.com",
            f"--gcs-source-staging-dir=gs://{bucket}/sources", capture=True,
        ))
        build_id = submitted["id"]
        until = time.monotonic() + 2700
        while time.monotonic() < until:
            info = json.loads(session.command(
                "gcloud", "builds", "describe", build_id, f"--project={project}",
                f"--region={region}", "--format=json", capture=True,
            ))
            if info["status"] == "SUCCESS":
                break
            if info["status"] not in ("QUEUED", "PENDING", "WORKING"):
                raise RuntimeError(f"Cloud Build {build_id} failed: {info['status']}")
            time.sleep(10)
        else:
            raise RuntimeError(f"Cloud Build {build_id} exceeded its deadline")
        bundle = create_bundle(work)
        published = {image["name"]: image["digest"] for image in info["results"]["images"]}
        images = {name: f"{registry}/{name}@{published[f'{registry}/{name}:{release}']}" for name in SERVICES}
        manifest = {
            "release": release, "build_id": build_id, "images": images,
            "channel": "main",
            **snapshot,
            "publication_order": [int(os.environ["GITHUB_RUN_NUMBER"]), int(os.environ["GITHUB_RUN_ATTEMPT"])],
            "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        }
        manifest_file = work / "manifest.json"
        manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
        for path in (bundle, manifest_file):
            session.command("gcloud", "storage", "cp", str(path), f"gs://{bucket}/releases/{release}/{path.name}", "--if-generation-match=0", "--quiet")
        # Advance only after all immutable assets exist. CAS prevents lost updates,
        # and execution ordering prevents an old, slow build replacing a newer one.
        publication.promote(bucket, {"channel": "main", "release": release,
                                    "integration_tag": snapshot["integration_tag"],
                                    "publication_order": manifest["publication_order"]})
        (ROOT / "release.json").write_text(json.dumps(manifest), encoding="utf-8")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write(f"release={release}\n")
                output.write("manifest=" + json.dumps(manifest, separators=(",", ":")) + "\n")
        print(f"Published {release} using immutable image digests.")


def latest_release(config):
    project = config["GCP_PROJECT_ID"]
    bucket = os.environ.get("GCP_DELIVERY_BUCKET", f"{project}-nexoruta-delivery")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", bucket):
        raise ValueError("Invalid delivery bucket")
    try:
        pointer = json.loads(session.command("gcloud", "storage", "cat",
                            f"gs://{bucket}/channels/main.json", capture=True))
    except subprocess.CalledProcessError as error:
        raise RuntimeError("No published main release is available. Push main or run start before updating.") from error
    release = pointer.get("release", "")
    if pointer.get("channel") != "main" or not re.fullmatch(r"release-[a-f0-9]{32}", release):
        raise ValueError("Invalid published main release pointer")
    manifest = json.loads(session.command("gcloud", "storage", "cat",
                         f"gs://{bucket}/releases/{release}/manifest.json", capture=True))
    if manifest.get("release") != release or manifest.get("channel") != "main":
        raise ValueError("Published main manifest does not match its pointer")
    if "integration_tag" in pointer:
        if (not re.fullmatch(integration.TAG, pointer["integration_tag"])
                or manifest.get("integration_tag") != pointer["integration_tag"]
                or manifest.get("publication_order") != pointer.get("publication_order")
                or not re.fullmatch(integration.SHA, manifest.get("root_sha", ""))):
            raise ValueError("Published integration snapshot does not match its channel")
        integration.validate_sources(manifest.get("sources", {}))
    images = manifest.get("images", {})
    registry = f"{session.REGION}-docker.pkg.dev/{project}/nexoruta"
    if set(images) != set(SERVICES) or any(
        not re.fullmatch(re.escape(f"{registry}/{name}@sha256:") + r"[a-f0-9]{64}", images[name])
        for name in SERVICES
    ):
        raise ValueError("Published release must contain all six registry images pinned by digest")
    print(f"Selected latest published main release: {release}")
    return release


def deploy(config, release):
    if not re.fullmatch(r"release-[a-f0-9]{32}", release):
        raise ValueError("Invalid release identifier")
    project = config["GCP_PROJECT_ID"]
    bucket = os.environ.get("GCP_DELIVERY_BUCKET", f"{project}-nexoruta-delivery")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", bucket):
        raise ValueError("Invalid delivery bucket")
    session.command("gcloud", "sql", "backups", "create", "--instance=nexoruta-demo-db", f"--project={project}", "--quiet")
    for attempt in range(80):
        try:
            session.gcloud(config, "compute", "ssh", session.VM_NAME, "--tunnel-through-iap", "--command=sudo test -f /srv/nexoruta/bootstrap-ready")
            break
        except subprocess.CalledProcessError:
            time.sleep(5)
    else:
        raise RuntimeError("VM bootstrap did not finish before deployment")
    session.gcloud(config, "compute", "scp", str(ROOT / "scripts/gcp/vm_deploy.py"), f"{session.VM_NAME}:/tmp/nexoruta-vm-deploy.py", "--tunnel-through-iap")
    output = session.gcloud(
        config, "compute", "ssh", session.VM_NAME, "--tunnel-through-iap",
        "--command=" + shlex.join(["sudo", "python3", "/tmp/nexoruta-vm-deploy.py", "--bucket", bucket, "--release", release]),
        capture=True,
    )
    for line in reversed(output.splitlines()):
        if line.startswith("{"):
            result = json.loads(line)
            if result.get("release") == release and result.get("status") == "healthy":
                print(line)
                return result
    raise RuntimeError("The VM did not report a healthy release")


if __name__ == "__main__":
    if sys.argv[1:] == ["sources"]:
        sources()
    elif sys.argv[1:] == ["build"]:
        build()
    else:
        raise SystemExit("Usage: delivery.py sources|build")
