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
from concurrent.futures import ThreadPoolExecutor

import demo_session as session
import ci_evidence
import image_inventory
import integration
import publication
import host_versions
import deployment_health

ROOT = session.ROOT
SERVICES = ("api", "worker", "admin", "backoffice", "commerce", "tracking")


def report_timing(phase, duration_ms, status="passed", **dimensions):
    print("NEXORUTA_DEPLOY_TIMING " + json.dumps({
        "phase": phase, "duration_ms": duration_ms, "status": status, **dimensions,
    }, sort_keys=True), flush=True)


def measure(phase, operation, **dimensions):
    started = time.perf_counter()
    status = "passed"
    try:
        return operation()
    except Exception:
        status = "failed"
        raise
    finally:
        report_timing(phase, round((time.perf_counter() - started) * 1000), status, **dimensions)


def record_cloud_build_id(build_id):
    """Persist the async build ID so workflow cancellation can clean it up."""
    id_file = os.environ.get("NEXORUTA_CLOUD_BUILD_ID_FILE")
    if id_file:
        path = Path(id_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(build_id + "\n", encoding="utf-8")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write(f"cloud_build_id={build_id}\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(f"\nCloud Build submitted: `{build_id}`.\n")


def cancel_cloud_build(build_id, project):
    """Cancel an asynchronous Cloud Build and retain its ID if cleanup fails."""
    try:
        session.command("gcloud", "builds", "cancel", build_id,
                        f"--project={project}", f"--region={session.REGION}", "--quiet")
    except Exception as error:
        raise RuntimeError(
            f"Could not cancel Cloud Build {build_id}; it may still be running. "
            f"Cancel it with gcloud builds cancel {build_id} --project={project} --region={session.REGION}."
        ) from error
    report_timing("cloud_build_cancel", 0, build_id=build_id)


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
        context = destination / name
        for excluded in ("docs", "tests", ".github"):
            shutil.rmtree(context / excluded, ignore_errors=True)
        (context / "README.md").unlink(missing_ok=True)
        restore_inputs = context / ".restore"
        razor_projects = set()
        for path in context.rglob("*"):
            if not path.is_file() or restore_inputs in path.parents:
                continue
            if (path.name.endswith((".csproj", ".props", ".targets")) or
                    path.name in {"packages.lock.json", "global.json", "NuGet.Config"}):
                target = restore_inputs / path.relative_to(context)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
            if path.suffix == ".razor":
                project = next((parent for parent in path.parents if any(parent.glob("*.csproj"))), None)
                if project is not None:
                    razor_projects.add(project.relative_to(context))
        for project in razor_projects:
            marker = restore_inputs / project / "__nexoruta_restore_shape.razor"
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("@* Preserves implicit Razor dependencies during locked restore. *@\n", encoding="utf-8")
        shutil.copyfile(ROOT / "deploy/gcp/Dockerfile", context / "Dockerfile.deploy")

    # Docker builds each archived repository in isolation. Package the canonical
    # asset from the tested backend archive instead of fetching mutable branches.
    map_source = destination / "backend/src/ZonasCobertura/Data/departamentos-uruguay.geojson"
    frontend_inputs = destination / "frontend/.build"
    frontend_inputs.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(map_source, frontend_inputs / map_source.name)


def create_bundle(destination, deployment_images=None):
    assets = destination / "assets"
    shutil.copytree(ROOT / "deploy/gcp", assets)
    deployment_images = deployment_images or image_inventory.collect(ROOT)
    image_inventory.write_bundle(assets, deployment_images)
    shutil.copyfile(Path(__file__).with_name("image_inventory.py"), assets / "image_inventory.py")
    shutil.copyfile(Path(__file__).with_name("ci_evidence.py"), assets / "ci_evidence.py")
    shutil.copyfile(Path(__file__).with_name("host_versions.py"), assets / "host_versions.py")
    shutil.copyfile(Path(__file__).with_name("deployment_health.py"), assets / "deployment_health.py")
    shutil.copyfile(Path(__file__).with_name("integration.py"), assets / "integration.py")
    shutil.copyfile(ROOT / "deploy/observability/grafana/nexoruta.json",
                    assets / "grafana/provisioning/dashboards/nexoruta.json")
    shutil.copyfile(ROOT / "deploy/observability/grafana/load-tests.json",
                    assets / "grafana/provisioning/dashboards/load-tests.json")
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
            f"THEN CREATE ROLE {role} NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; END IF; END $$;"
        )
        # CREATEROLE already grants ADMIN to the creator. Regranting ADMIN to
        # yourself is rejected by PostgreSQL 18; only enable object privileges.
        inherit = "FALSE" if role in {"nexoruta_api", "nexoruta_worker", "nexoruta_bootstrap"} else "TRUE"
        statements.append(f"GRANT {role} TO postgres WITH INHERIT {inherit}, SET TRUE;")
    statements.append("GRANT CREATE ON DATABASE nexoruta TO nexoruta_schema_owner;")
    statements.append("CREATE SCHEMA IF NOT EXISTS nexoruta_app AUTHORIZATION nexoruta_schema_owner;")
    statements.append(f"GRANT CREATE ON SCHEMA public, nexoruta_app TO {', '.join(sorted(roles))};")
    # Existing managed databases need the same owner-only validator privilege as fresh migrations.
    statements.append("""DO $owner_execute$
    DECLARE item record;
    BEGIN
        FOR item IN SELECT p.oid::regprocedure AS signature,r.rolname AS owner_name
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            JOIN pg_roles r ON r.oid=p.proowner
            WHERE n.nspname='nexoruta_app' AND NOT r.rolcanlogin
        LOOP
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO %I',item.signature,item.owner_name);
        END LOOP;
    END $owner_execute$;""")
    (sql / "preflight.sql").write_text("\n".join(statements) + "\n", encoding="utf-8")
    with open(sql / "postflight.sql", "a", encoding="utf-8") as output:
        restricted = sorted(roles - {"nexoruta_schema_owner"})
        output.write(f"\nREVOKE CREATE ON SCHEMA public, nexoruta_app FROM {', '.join(restricted)};\n")
    shutil.copyfile(ROOT / "scripts/gcp/monitor_agent.py", assets / "monitor_agent.py")
    shutil.copyfile(ROOT / "scripts/gcp/redis_identity.py", assets / "redis_identity.py")
    bundle = destination / "bundle.tar.gz"
    with tarfile.open(bundle, "w:gz") as archive:
        for path in sorted(assets.rglob("*")):
            if path.is_file():
                archive.add(path, arcname=path.relative_to(assets).as_posix(), recursive=False)
    return bundle


def selected_build_services(plan, *, reproduction=False):
    build_services = plan.get("images")
    if not isinstance(build_services, list) or any(
        not isinstance(name, str) or name not in SERVICES for name in build_services
    ):
        raise ValueError("The CI change plan contains an invalid image selection")
    if len(build_services) != len(set(build_services)):
        raise ValueError("The CI change plan contains an invalid image selection")
    # An isolated project's registry has no trusted previous manifest. Rebuild
    # every service while retaining the protected CI evidence for Android.
    return list(SERVICES) if reproduction else build_services


def build():
    config = session.configuration()
    channel = os.environ.get("RELEASE_CHANNEL", "")
    reproduction = config.get("NEXORUTA_EXECUTION_PROFILE") == "reproduction"
    if channel not in ("main", "develop"):
        raise ValueError("Builds must explicitly target RELEASE_CHANNEL=main or develop")
    if reproduction and channel != "main":
        raise ValueError("The reproduction project only accepts its isolated main release channel")
    if channel == "main" and not os.environ.get("TESTED_CI_PLAN"):
        raise ValueError("Main publications require the exact plan and successful protected CI evidence")
    if channel == "main":
        # Main publication uses the already-tested tag and its exact submodule gitlinks.
        snapshot = integration.verify_checkout(os.environ["INTEGRATION_TAG"], os.environ.get("INTEGRATION_COMMIT"))
        if reproduction:
            import reproduce
            target = reproduce.validate_runtime_environment(os.environ)
            if os.environ.get("INTEGRATION_TAG") != target["integration_tag"]:
                raise ValueError("The publication tag differs from the reproduction environment identity")
            reproduce._release_manifest(target["integration_tag"], os.environ.get("GITHUB_REPOSITORY_ID"))
    else:
        if os.environ.get("TESTED_CI_PLAN"):
            raise ValueError("Develop builds use a complete release and do not consume the main CI plan")
        snapshot = integration.verify_develop_checkout(os.environ.get("GITHUB_SHA"))
    if os.environ.get("TESTED_CI_PLAN"):
        plan = json.loads(os.environ["TESTED_CI_PLAN"])
        if plan.get("current", {}).get("sources") != snapshot["sources"] or not plan.get("publish_required"):
            raise ValueError("The CI change plan does not authorize this integration snapshot")
        build_services = selected_build_services(plan, reproduction=reproduction)
    else:
        # Local use without a plan is conservative and always creates a full release.
        plan = {"version": 0, "images": list(SERVICES), "publish_required": True, "bundle_required": True,
                "android_input_sha256": None, "components": {"mobile_android": {"run": True}}}
        build_services = list(SERVICES)
    ci_identity = None
    android_verification = None
    release = f"release-{uuid.uuid4().hex}"
    if channel == "main":
        evidence_file = os.environ.get("NEXORUTA_CI_EVIDENCE_FILE", "")
        if not evidence_file:
            raise ValueError("Main publications require verified Integrated CI evidence")
        ci_identity, android_verification = ci_evidence.bind_for_release(
            evidence_file, snapshot=snapshot, plan=plan, release=release)
    project, region = config["GCP_PROJECT_ID"], session.REGION
    bucket = os.environ.get("GCP_DELIVERY_BUCKET", f"{project}-nexoruta-delivery")
    registry = f"{region}-docker.pkg.dev/{project}/nexoruta"
    previous = None
    try:
        previous = latest_manifest(config)
    except RuntimeError as error:
        if (f"No published {channel} release is available" not in str(error)
                and f"No reusable {channel} release is available" not in str(error)):
            raise
    if previous:
        previous_image_sources = previous.get("image_sources", {})
        for name in SERVICES:
            source = "backend" if name in ("api", "worker") else "frontend"
            if previous_image_sources.get(name) != snapshot["sources"][source]:
                if name not in build_services:
                    build_services.append(name)
    effective_bundle_required = bool(plan.get("bundle_required") or previous is None)
    if set(build_services) != set(SERVICES) and previous is None:
        raise RuntimeError("A complete prior manifest is required before reusing images")
    if effective_bundle_required:
        deployment_images = image_inventory.collect(ROOT)
    else:
        deployment_images = image_inventory.validate_inventory(previous.get("deployment_images"))
        if image_inventory.checksum(deployment_images) != previous.get("deployment_images_sha256"):
            raise ValueError("Previous deployment image inventory checksum does not match its manifest")
    deployment_images_sha256 = image_inventory.checksum(deployment_images)

    with tempfile.TemporaryDirectory(prefix="nexoruta-build-") as temp:
        work = Path(temp)
        build_config = {
            "steps": [], "images": [], "timeout": "2400s",
            "options": {"logging": "CLOUD_LOGGING_ONLY", "machineType": "E2_HIGHCPU_8", "env": ["DOCKER_BUILDKIT=1"]},
        }
        previous_images = previous["images"] if previous else {}
        chains = {"api": "-", "worker": "api", "admin": "-", "backoffice": "admin",
                  "commerce": "backoffice", "tracking": "commerce"}
        selected = set(build_services)
        for name in SERVICES:
            if name not in selected:
                continue
            context = "backend" if name in ("api", "worker") else "frontend"
            assembly = "NexoRuta." + name.capitalize() if context == "backend" else "NexoRuta." + {"admin": "Admin", "backoffice": "Backoffice", "commerce": "Commerce", "tracking": "Tracking"}[name]
            tag = f"{registry}/{name}:{release}"
            args = ["build", "-t", tag]
            if name in previous_images:
                args.extend(["--cache-from", previous_images[name]])
            args.extend(["--build-arg", "BUILDKIT_INLINE_CACHE=1", "--build-arg", f"PROJECT=src/{assembly}/{assembly}.csproj",
                         "--build-arg", f"ASSEMBLY={assembly}", "-f", f"{context}/Dockerfile.deploy", context])
            predecessor = chains[name]
            build_config["steps"].append({
                "id": name,
                "name": "gcr.io/cloud-builders/docker",
                "waitFor": [predecessor] if predecessor in selected else ["-"],
                "args": args,
            })
            build_config["images"].append(tag)
        build_id = None
        built_images = {}
        if selected:
            stage_sources(work)
            config_file = work / "cloudbuild.json"
            config_file.write_text(json.dumps(build_config), encoding="utf-8")
            submitted = json.loads(session.command(
                "gcloud", "builds", "submit", str(work), f"--config={config_file}",
                f"--project={project}", f"--region={region}", "--async", "--quiet", "--format=json",
                f"--service-account=projects/{project}/serviceAccounts/nexoruta-demo-builder@{project}.iam.gserviceaccount.com",
                f"--gcs-source-staging-dir=gs://{bucket}/sources", capture=True,
            ))
            build_id = submitted["id"]
            record_cloud_build_id(build_id)
            until = time.monotonic() + 2700
            try:
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
                    cancel_cloud_build(build_id, project)
                    raise RuntimeError(f"Cloud Build {build_id} exceeded its deadline and was cancelled")
            except KeyboardInterrupt:
                cancel_cloud_build(build_id, project)
                raise
            published = {image["name"]: image["digest"] for image in info["results"]["images"]}
            for name in build_services:
                image_tag = f"{registry}/{name}:{release}"
                if image_tag not in published:
                    raise RuntimeError(f"Cloud Build did not produce required image {name}")
                built_images[name] = f"{registry}/{name}@{published[image_tag]}"

        images = {name: built_images.get(name, previous_images.get(name)) for name in SERVICES}
        if any(value is None for value in images.values()):
            raise RuntimeError("The complete integration manifest has missing images")
        if effective_bundle_required:
            bundle = create_bundle(work, deployment_images)
            bundle_source = {"root_sha": snapshot["root_sha"], "backend_sha": snapshot["sources"]["backend"]}
        else:
            bundle = work / "bundle.tar.gz"
            session.command("gcloud", "storage", "cp",
                            f"gs://{bucket}/releases/{previous['release']}/bundle.tar.gz",
                            str(bundle), "--quiet")
            bundle_source = previous.get("bundle_source")
        bundle_sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
        if previous and not plan.get("bundle_required") and previous.get("bundle_sha256") != bundle_sha:
            raise ValueError("Reused deployment bundle checksum does not match its previous manifest")
        image_sources = dict((previous or {}).get("image_sources", {}))
        reused = {}
        for name in SERVICES:
            if name in built_images:
                source = "backend" if name in ("api", "worker") else "frontend"
                image_sources[name] = snapshot["sources"][source]
            else:
                reused[name] = previous["release"]
                image_sources.setdefault(name, previous["sources"]["backend" if name in ("api", "worker") else "frontend"])
        plan_summary = {key: plan[key] for key in (
            "version", "baseline", "current", "reason", "infrastructure", "cloudsql", "components",
            "images", "bundle_required", "publish_required", "android_input_sha256",
        ) if key in plan}
        manifest = {
            "manifest_version": 2,
            "release": release, "project_id": project, "region": region,
            "build_id": build_id, "images": images,
            "image_sources": image_sources, "reused_images": reused,
            "deployment_images": deployment_images,
            "deployment_images_sha256": deployment_images_sha256,
            "channel": channel,
            **snapshot,
            "ci_plan": plan_summary,
            "built_images": [name for name in SERVICES if name in built_images],
            "bundle_rebuilt": effective_bundle_required,
            "ci_evidence": ci_identity,
            "android_input_sha256": android_verification.get("android_input_sha256") if android_verification else None,
            "android_verified_mobile_sha": android_verification.get("mobile_sha") if android_verification else None,
            "android_verification": android_verification,
            "bundle_source": bundle_source,
            "publication_order": [int(os.environ["GITHUB_RUN_NUMBER"]), int(os.environ["GITHUB_RUN_ATTEMPT"])],
            "bundle_sha256": bundle_sha,
        }
        manifest_file = work / "manifest.json"
        manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
        for path in (bundle, manifest_file):
            session.command("gcloud", "storage", "cp", str(path), f"gs://{bucket}/releases/{release}/{path.name}", "--if-generation-match=0", "--quiet")
        # Advance only after all immutable assets exist. CAS prevents lost updates,
        # and execution ordering prevents an old, slow build replacing a newer one.
        pointer = {"channel": channel, "release": release,
                   "publication_order": manifest["publication_order"]}
        if snapshot.get("integration_tag"):
            pointer["integration_tag"] = snapshot["integration_tag"]
        publication.promote(bucket, pointer)
        (ROOT / "release.json").write_text(json.dumps(manifest), encoding="utf-8")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write(f"release={release}\n")
                output.write("manifest=" + json.dumps(manifest, separators=(",", ":")) + "\n")
        print(f"Published {release}: built {len(built_images)} images and reused {len(reused)} verified digests.")


def latest_manifest(config):
    channel = os.environ.get("RELEASE_CHANNEL", "main")
    if channel not in ("main", "develop"):
        raise ValueError("RELEASE_CHANNEL must be main or develop")
    project = config["GCP_PROJECT_ID"]
    bucket = os.environ.get("GCP_DELIVERY_BUCKET", f"{project}-nexoruta-delivery")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", bucket):
        raise ValueError("Invalid delivery bucket")
    try:
        pointer = json.loads(session.command("gcloud", "storage", "cat",
                            f"gs://{bucket}/channels/{channel}.json", capture=True))
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"No published {channel} release is available. Publish that channel before updating.") from error
    release = pointer.get("release", "")
    if pointer.get("channel") != channel or not re.fullmatch(r"release-[a-f0-9]{32}", release):
        raise ValueError(f"Invalid published {channel} release pointer")
    manifest = json.loads(session.command("gcloud", "storage", "cat",
                         f"gs://{bucket}/releases/{release}/manifest.json", capture=True))
    if manifest.get("release") != release or manifest.get("channel") != channel:
        raise ValueError(f"Published {channel} manifest does not match its pointer")
    if manifest.get("manifest_version") != 2:
        raise RuntimeError(f"No reusable {channel} release is available; a complete version 2 publication is required")
    if manifest.get("project_id") != project or manifest.get("region") != session.REGION:
        raise ValueError("Published release belongs to a different project or region")
    if (not re.fullmatch(r"[a-f0-9]{64}", manifest.get("bundle_sha256", ""))
            or not isinstance(manifest.get("bundle_source"), dict)
            or not re.fullmatch(integration.SHA, manifest["bundle_source"].get("root_sha", ""))
            or not re.fullmatch(integration.SHA, manifest["bundle_source"].get("backend_sha", ""))
            or manifest.get("publication_order") != pointer.get("publication_order")):
        raise ValueError("Published release has incomplete bundle or publication provenance")
    inventory = image_inventory.validate_inventory(manifest.get("deployment_images"))
    if (not re.fullmatch(r"[a-f0-9]{64}", manifest.get("deployment_images_sha256", ""))
            or image_inventory.checksum(inventory) != manifest["deployment_images_sha256"]):
        raise ValueError("Published release has an incomplete or altered deployment image inventory")
    if channel == "main":
        if "integration_tag" not in pointer:
            raise ValueError("Published main channel is missing its tested integration identity")
        if (not re.fullmatch(integration.TAG, pointer["integration_tag"])
                or manifest.get("integration_tag") != pointer["integration_tag"]
                or manifest.get("publication_order") != pointer.get("publication_order")
                or not re.fullmatch(integration.SHA, manifest.get("root_sha", ""))):
            raise ValueError("Published integration snapshot does not match its channel")
        integration.validate_sources(manifest.get("sources", {}))
        ci_evidence.validate_manifest_android(manifest)
    else:
        if (manifest.get("source_ref") != "refs/heads/develop"
                or not re.fullmatch(integration.SHA, manifest.get("root_sha", ""))
                or manifest.get("publication_order") != pointer.get("publication_order")):
            raise ValueError("Published develop snapshot does not match its channel")
        integration.validate_sources(manifest.get("sources", {}))
        if (manifest.get("ci_evidence") is not None
                or manifest.get("android_verification") is not None
                or manifest.get("android_input_sha256") is not None
                or manifest.get("android_verified_mobile_sha") is not None):
            raise ValueError("Develop release cannot claim Android CI evidence")
    images = manifest.get("images", {})
    registry = f"{session.REGION}-docker.pkg.dev/{project}/nexoruta"
    if set(images) != set(SERVICES) or any(
        not re.fullmatch(re.escape(f"{registry}/{name}@sha256:") + r"[a-f0-9]{64}", images[name])
        for name in SERVICES
    ):
        raise ValueError("Published release must contain all six registry images pinned by digest")
    integration.validate_sources(manifest.get("sources", {}))
    image_sources = manifest.get("image_sources", {})
    if set(image_sources) != set(SERVICES) or any(
        image_sources[name] != manifest["sources"]["backend" if name in ("api", "worker") else "frontend"]
        for name in SERVICES
    ):
        raise ValueError("Published application images do not match the recorded source gitlinks")
    built_images = manifest.get("built_images")
    reused_images = manifest.get("reused_images")
    if (not isinstance(built_images, list)
            or any(not isinstance(name, str) or name not in SERVICES for name in built_images)
            or len(built_images) != len(set(built_images))
            or not isinstance(reused_images, dict)
            or set(built_images).intersection(reused_images)
            or set(built_images).union(reused_images) != set(SERVICES)
            or any(not isinstance(value, str) or not re.fullmatch(r"release-[a-f0-9]{32}", value)
                   for value in reused_images.values())):
        raise ValueError("Published release has incomplete application image build provenance")
    order = manifest.get("publication_order")
    if (not isinstance(order, list) or len(order) != 2
            or any(type(value) is not int or value < 1 for value in order)):
        raise ValueError("Published release has an invalid publication order")
    if type(manifest.get("bundle_rebuilt")) is not bool:
        raise ValueError("Published release is missing bundle build provenance")
    if manifest["bundle_rebuilt"] and (
        manifest["bundle_source"]["root_sha"] != manifest["root_sha"]
        or manifest["bundle_source"]["backend_sha"] != manifest["sources"]["backend"]
    ):
        raise ValueError("Rebuilt bundle does not match its recorded source snapshot")
    return manifest


def latest_release(config):
    manifest = latest_manifest(config)
    print(f"Selected latest published {manifest['channel']} release: {manifest['release']}")
    return manifest["release"]


def remote_stage_error(output, node, operation):
    exit_code = None
    for line in reversed(output.splitlines()):
        exit_match = re.fullmatch(r"__NEXORUTA_STAGE_EXIT__=([0-9]{1,3})", line.strip())
        if exit_match:
            exit_code = exit_match.group(1)
            continue
        try:
            result = json.loads(line)
        except json.JSONDecodeError:
            match = re.match(r"^([A-Za-z][A-Za-z0-9_.]*(?:Error|Exception)):", line.strip())
            if match:
                return f"Node {node} stage {operation} failed ({match.group(1).rsplit('.', 1)[-1]})"
            continue
        if not isinstance(result, dict):
            continue
        error_type = result.get("error_type", "")
        if (result.get("node") == node and result.get("stage") == operation
                and result.get("status") == "failed" and re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", error_type)):
            location = result.get("error_location", "")
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*:[0-9]{1,5}", location):
                location = ""
            suffix = f" at {location}" if location else ""
            http_status = result.get("http_status")
            if type(http_status) is int and 100 <= http_status <= 599:
                suffix += f", HTTP {http_status}"
            phase = result.get("failed_phase", "")
            if isinstance(phase, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", phase):
                suffix += f", phase {phase}"
            diagnostic = result.get("safe_diagnostic", "")
            if isinstance(diagnostic, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,63}", diagnostic):
                suffix += f", diagnostic {diagnostic}"
            return f"Node {node} stage {operation} failed ({error_type}{suffix})"
    if exit_code is not None:
        return f"Node {node} stage {operation} exited ({exit_code}) without a report"
    return f"Node {node} stage {operation} failed without a structured report"


def drain_node_from_group(node):
    group = f"nexoruta-demo-{node['NODE_ID']}"
    members = json.loads(session.gcloud(node, "compute", "instance-groups", "unmanaged", "list-instances",
                                        group, "--format=json", capture=True))
    if not isinstance(members, list):
        raise RuntimeError(f"Could not verify node {node['NODE_ID']} load-balancer membership")
    if not any(isinstance(member, dict) and isinstance(member.get("instance"), str)
               and member["instance"].endswith("/" + node["VM_NAME"]) for member in members):
        print("NEXORUTA_LB_DRAIN " + json.dumps({
            "node": node["NODE_ID"], "status": "already_absent",
        }), flush=True)
        return False
    session.gcloud(node, "compute", "instance-groups", "unmanaged", "remove-instances", group,
                   f"--instances={node['VM_NAME']}")
    return True


def wait_for_load_balancer_health(node, deadline, health):
    until = time.monotonic() + 300
    while time.monotonic() < until and time.time() < deadline:
        try:
            if health(node):
                return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
            print("NEXORUTA_LB_HEALTH_QUERY_ERROR " + json.dumps({
                "node": node["NODE_ID"], "error_type": type(error).__name__,
            }, sort_keys=True), flush=True)
        time.sleep(min(5, max(0, until - time.monotonic())))
    if time.time() >= deadline:
        raise RuntimeError("Session expired while waiting for load balancer health")
    raise RuntimeError(f"Node {node['NODE_ID']} was not admitted by the load balancer")


def prepared_cache_mode(reports):
    modes = [report.get("cache_enabled") for report in reports]
    if len(modes) != 2 or any(type(mode) is not bool for mode in modes) or modes[0] != modes[1]:
        raise RuntimeError("Both nodes must confirm the same cache mode before deployment")
    return modes[0]


def prepared_host_versions(inventory, reports):
    if len(inventory) != 2 or len(reports) != 2:
        raise RuntimeError("Both VM preparation stages must return host version evidence")
    result = {}
    for node, report in zip(inventory, reports):
        node_id = node.get("NODE_ID")
        if node_id not in ("a", "b") or node_id in result:
            raise RuntimeError("The VM inventory has an invalid host version identity")
        result[node_id] = host_versions.sanitize_host_versions(report.get("host_versions"))
    return host_versions.sanitize_node_map(result)


def redis_smoke_clients_if_enabled(cache_enabled, inventory, stage, measure):
    if not cache_enabled:
        return []
    clients = []
    for node in inventory:
        report = measure("redis_tls_auth_smoke", lambda node=node: stage(node, "redis-smoke"),
                         node=node["NODE_ID"])
        if (report.get("redis_node") != "b"
                or report.get("redis_client_node") != node["NODE_ID"]
                or report.get("redis_probe") != "tls-auth-set-get-delete-passed"):
            raise RuntimeError(f"Redis TLS/AUTH smoke failed from node {node['NODE_ID']}")
        clients.append(node["NODE_ID"])
    return clients


def deploy(config, release):
    if not re.fullmatch(r"release-[a-f0-9]{32}", release):
        raise ValueError("Invalid release identifier")
    project = config["GCP_PROJECT_ID"]
    bucket = os.environ.get("GCP_DELIVERY_BUCKET", f"{project}-nexoruta-delivery")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", bucket):
        raise ValueError("Invalid delivery bucket")
    inventory = session.node_configs(config)
    lease = json.loads(session.command("gcloud", "storage", "cat",
        f"gs://{config['GCP_STATE_BUCKET']}/leases/demo.json", capture=True))
    deadline = lease["expires_at"]
    if deadline <= time.time():
        raise RuntimeError("The common session deadline has expired")
    def stage(node, operation):
        started = time.perf_counter()
        status = "failed"
        try:
            if time.time() >= deadline:
                raise RuntimeError("The deployment cannot extend the common session deadline")
            command = ["sudo", "python3", "/srv/nexoruta/deploy/vm_deploy.py",
                "--bucket", bucket, "--release", release, "--node", node["NODE_ID"],
                "--deadline", str(deadline), "--stage", operation]
            invocation = shlex.join(command)
            script = invocation + " 2>&1; code=$?; printf '\\n__NEXORUTA_STAGE_EXIT__=%s\\n' \"$code\"; exit 0"
            remote = "bash -lc " + shlex.quote(script)
            try:
                output = session.gcloud(node, "compute", "ssh", node["VM_NAME"], "--tunnel-through-iap",
                    "--command=" + remote, capture=True)
            except subprocess.CalledProcessError as error:
                output = (error.stdout or "") + "\n" + (error.stderr or "")
                raise RuntimeError(remote_stage_error(output, node["NODE_ID"], operation)) from None
            for line in reversed(output.splitlines()):
                try:
                    result = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (not isinstance(result, dict) or result.get("release") != release
                        or result.get("node") != node["NODE_ID"]
                        or result.get("stage") != operation):
                    continue
                for phase, duration in result.get("timings_ms", {}).items():
                    failed = result.get("status") == "failed" and phase in (result.get("failed_phase"), "stage_total")
                    report_timing("vm_" + operation + "_" + phase, duration,
                                  status="failed" if failed else "passed", node=node["NODE_ID"])
                if result.get("status") == "healthy":
                    status = "passed"
                    return result
                if result.get("status") == "failed":
                    raise RuntimeError(remote_stage_error(line, node["NODE_ID"], operation))
            raise RuntimeError(remote_stage_error(output, node["NODE_ID"], operation))
        finally:
            print("NEXORUTA_DEPLOY_TIMING " + json.dumps({
                "phase": "remote_stage_call", "operation": operation, "node": node["NODE_ID"],
                "duration_ms": round((time.perf_counter() - started) * 1000), "status": status,
            }, sort_keys=True), flush=True)

    def wait_for_bootstrap(node):
        for attempt in range(80):
            try:
                session.gcloud(node, "compute", "ssh", node["VM_NAME"], "--tunnel-through-iap",
                    "--command=sudo test -f /srv/nexoruta/bootstrap-ready", capture=True)
                return
            except subprocess.CalledProcessError as error:
                print(error.stderr or str(error), file=sys.stderr)
                time.sleep(5)
        raise RuntimeError(f"Node {node['NODE_ID']} bootstrap did not finish")

    def prepare_node_access(node, bootstrap_ready=False):
        if not bootstrap_ready:
            wait_for_bootstrap(node)
        session.gcloud(node, "compute", "scp", str(ROOT / "scripts/gcp/vm_deploy.py"),
            f"{node['VM_NAME']}:/tmp/nexoruta-vm-deploy.py", "--tunnel-through-iap")
        session.gcloud(node, "compute", "ssh", node["VM_NAME"], "--tunnel-through-iap",
            "--command=sudo install -D -m 0700 /tmp/nexoruta-vm-deploy.py /srv/nexoruta/deploy/vm_deploy.py")

    def prepare_node(node, bootstrap_ready=False):
        measure("bootstrap_and_script_install",
                lambda: prepare_node_access(node, bootstrap_ready), node=node["NODE_ID"])
        # This stage mutates only this VM's local configuration, containers, and
        # monitoring agent. It does not touch database schema or load-balancer state.
        return measure("prepare_node", lambda: stage(node, "prepare"), node=node["NODE_ID"])

    # Let gcloud create its default SSH key before SSH/SCP calls.
    measure("initial_ssh_bootstrap", lambda: wait_for_bootstrap(inventory[0]), node=inventory[0]["NODE_ID"])
    # OS Login updates the deployer's shared SSH profile; concurrent connections
    # can fail with ABORTED: Multiple concurrent mutations.
    prepared = []
    for index, node in enumerate(inventory):
        prepared.append(prepare_node(node, bootstrap_ready=index == 0))

    # New APIs stay drained until both independent VM processes prove that the
    # same Redis B endpoint accepts the configured CA, hostname and AUTH. A
    # deliberate PostgreSQL bypass must remain deployable during a Redis outage.
    cache_enabled = prepared_cache_mode(prepared)
    host_version_evidence = prepared_host_versions(inventory, prepared)
    redis_smoke_clients = redis_smoke_clients_if_enabled(cache_enabled, inventory, stage, measure)
    last_health_report = {}
    def health(node):
        services = ("api", "admin", "backoffice", "commerce", "tracking", "monitor")
        if node["NODE_ID"] == "a":
            services += ("mail",)
        def service_health_states(service):
            output = session.command("gcloud", "compute", "backend-services", "get-health", f"nexoruta-demo-{service}",
                "--global", f"--project={project}", "--format=json", capture=True, timeout=15)
            states = [status for backend in json.loads(output) for status in backend.get("status", {}).get("healthStatus", [])
                      if status.get("instance", "").endswith("/" + node["VM_NAME"])]
            return service, [state.get("healthState", "UNKNOWN") for state in states]
        with ThreadPoolExecutor(max_workers=len(services)) as executor:
            states_by_service = dict(executor.map(service_health_states, services))
        unhealthy = {service: states for service, states in states_by_service.items()
                     if not states or any(state != "HEALTHY" for state in states)}
        signature = json.dumps(unhealthy, sort_keys=True)
        if unhealthy and last_health_report.get(node["NODE_ID"]) != signature:
            print("NEXORUTA_LB_HEALTH " + json.dumps({
                "node": node["NODE_ID"], "unhealthy_services": unhealthy,
            }, sort_keys=True), flush=True)
        last_health_report[node["NODE_ID"]] = signature
        return not unhealthy

    # Schema changes may break the previous application release. Drain both
    # nodes and stop their apps before applying migrations or either new image.
    groups = {node["NODE_ID"]: f"nexoruta-demo-{node['NODE_ID']}" for node in inventory}
    def drain_nodes():
        def remove(node):
            drain_node_from_group(node)
        with ThreadPoolExecutor(max_workers=len(inventory)) as executor:
            pending = [executor.submit(remove, node) for node in inventory]
            for future in pending:
                future.result()
        # Preserve the configured load-balancer drain interval.
        time.sleep(35)
    measure("load_balancer_drain", drain_nodes)
    for node in inventory:
        stage(node, "stop")

    stage(inventory[0], "migrate")

    compose_health = {}
    for node in reversed(inventory):
        group = groups[node["NODE_ID"]]
        apply_report = stage(node, "apply")
        node_id = node["NODE_ID"]
        compose_health[node_id] = deployment_health.sanitize_node_snapshot(
            apply_report.get("compose_health"), node_id, cache_enabled,
        )
        measure("load_balancer_admit", lambda: session.gcloud(
            node, "compute", "instance-groups", "unmanaged", "add-instances", group,
            f"--instances={node['VM_NAME']}"), node=node["NODE_ID"])
        try:
            measure("load_balancer_health", lambda: wait_for_load_balancer_health(node, deadline, health), node=node["NODE_ID"])
        except Exception:
            session.gcloud(node, "compute", "instance-groups", "unmanaged", "remove-instances", group,
                f"--instances={node['VM_NAME']}")
            raise
    result = stage(inventory[0], "verify")
    expected_roles = {"admin", "operator", "commerce"}
    authenticated_reads = result.get("authenticated_reads")
    if (not isinstance(authenticated_reads, list) or len(authenticated_reads) != len(expected_roles)
            or any(not isinstance(item, dict) or item.get("role") not in expected_roles
                   for item in authenticated_reads)
            or {item["role"] for item in authenticated_reads} != expected_roles
            or any(not isinstance(item, dict) or item.get("login") != "passed"
                   or item.get("actor_read") != "passed" for item in authenticated_reads)):
        raise RuntimeError("Synthetic role login and authenticated actor-read smoke did not complete")
    result["authenticated_reads"] = sorted(
        ({"role": item["role"], "login": "passed", "actor_read": "passed"}
         for item in authenticated_reads),
        key=lambda item: item["role"],
    )
    result["redis_node"] = "b"
    result["cache_enabled"] = cache_enabled
    result["redis_smoke_clients"] = redis_smoke_clients
    result["host_versions"] = host_version_evidence
    result["compose_health"] = deployment_health.sanitize_node_map(compose_health, cache_enabled)
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    if sys.argv[1:] == ["sources"]:
        sources()
    elif sys.argv[1:] == ["build"]:
        build()
    else:
        raise SystemExit("Usage: delivery.py sources|build")
