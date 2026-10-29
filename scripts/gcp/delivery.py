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
import integration
import publication

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
    shutil.copyfile(ROOT / "scripts/gcp/monitor_agent.py", assets / "monitor_agent.py")
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
    if os.environ.get("TESTED_CI_PLAN"):
        plan = json.loads(os.environ["TESTED_CI_PLAN"])
        if plan.get("current", {}).get("sources") != snapshot["sources"] or not plan.get("publish_required"):
            raise ValueError("The CI change plan does not authorize this integration snapshot")
        build_services = plan.get("images")
        if (not isinstance(build_services, list) or len(build_services) != len(set(build_services))
                or any(name not in SERVICES for name in build_services)):
            raise ValueError("The CI change plan contains an invalid image selection")
    else:
        # Local use without a plan is conservative and always creates a full release.
        plan = {"version": 0, "images": list(SERVICES), "publish_required": True, "bundle_required": True,
                "android_input_sha256": None, "components": {"mobile_android": {"run": True}}}
        build_services = list(SERVICES)
    project, region = config["GCP_PROJECT_ID"], session.REGION
    bucket = os.environ.get("GCP_DELIVERY_BUCKET", f"{project}-nexoruta-delivery")
    registry = f"{region}-docker.pkg.dev/{project}/nexoruta"
    release = f"release-{uuid.uuid4().hex}"
    previous = None
    try:
        previous = latest_manifest(config)
    except RuntimeError as error:
        if "No published main release is available" not in str(error):
            raise
    if set(build_services) != set(SERVICES) and previous is None:
        raise RuntimeError("A complete prior manifest is required before reusing images")

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
        if plan.get("bundle_required") or previous is None:
            bundle = create_bundle(work)
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
            "release": release, "build_id": build_id, "images": images,
            "image_sources": image_sources, "reused_images": reused,
            "channel": "main",
            **snapshot,
            "ci_plan": plan_summary,
            "android_input_sha256": plan.get("android_input_sha256"),
            "android_verified_mobile_sha": snapshot["sources"]["mobile"] if plan.get("components", {}).get("mobile_android", {}).get("run") else (previous or {}).get("android_verified_mobile_sha"),
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
        publication.promote(bucket, {"channel": "main", "release": release,
                                    "integration_tag": snapshot["integration_tag"],
                                    "publication_order": manifest["publication_order"]})
        (ROOT / "release.json").write_text(json.dumps(manifest), encoding="utf-8")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write(f"release={release}\n")
                output.write("manifest=" + json.dumps(manifest, separators=(",", ":")) + "\n")
        print(f"Published {release}: built {len(built_images)} images and reused {len(reused)} verified digests.")


def latest_manifest(config):
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
    return manifest


def latest_release(config):
    manifest = latest_manifest(config)
    print(f"Selected latest published main release: {manifest['release']}")
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
            return f"Node {node} stage {operation} failed ({error_type}{suffix})"
    if exit_code is not None:
        return f"Node {node} stage {operation} exited ({exit_code}) without a report"
    return f"Node {node} stage {operation} failed without a structured report"


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
                    "--command=sudo test -f /srv/nexoruta/bootstrap-ready")
                return
            except subprocess.CalledProcessError:
                time.sleep(5)
        raise RuntimeError(f"Node {node['NODE_ID']} bootstrap did not finish")

    def prepare_node(node, bootstrap_ready=False):
        def prepare_node_access():
            if not bootstrap_ready:
                wait_for_bootstrap(node)
            session.gcloud(node, "compute", "scp", str(ROOT / "scripts/gcp/vm_deploy.py"),
                f"{node['VM_NAME']}:/tmp/nexoruta-vm-deploy.py", "--tunnel-through-iap")
            session.gcloud(node, "compute", "ssh", node["VM_NAME"], "--tunnel-through-iap",
                "--command=sudo install -D -m 0700 /tmp/nexoruta-vm-deploy.py /srv/nexoruta/deploy/vm_deploy.py")
        measure("bootstrap_and_script_install", prepare_node_access, node=node["NODE_ID"])
        # This stage mutates only this VM's local configuration, containers, and
        # monitoring agent. It does not touch database schema or load-balancer state.
        return measure("prepare_node", lambda: stage(node, "prepare"), node=node["NODE_ID"])

    # Let gcloud create its default SSH key before any concurrent SSH/SCP calls.
    measure("initial_ssh_bootstrap", lambda: wait_for_bootstrap(inventory[0]), node=inventory[0]["NODE_ID"])
    with ThreadPoolExecutor(max_workers=2) as executor:
        pending = [executor.submit(prepare_node, node, index == 0) for index, node in enumerate(inventory)]
        for future in pending:
            future.result()
    def health(node):
        services = ("api", "admin", "backoffice", "commerce", "tracking", "monitor")
        if node["NODE_ID"] == "a":
            services += ("mail",)
        def service_healthy(service):
            output = session.command("gcloud", "compute", "backend-services", "get-health", f"nexoruta-demo-{service}",
                "--global", f"--project={project}", "--format=json", capture=True)
            states = [status for backend in json.loads(output) for status in backend.get("status", {}).get("healthStatus", [])
                      if status.get("instance", "").endswith("/" + node["VM_NAME"])]
            return bool(states) and all(state.get("healthState") == "HEALTHY" for state in states)
        with ThreadPoolExecutor(max_workers=len(services)) as executor:
            return all(executor.map(service_healthy, services))

    # Schema changes may break the previous application release. Drain both
    # nodes and stop their apps before applying migrations or either new image.
    groups = {node["NODE_ID"]: f"nexoruta-demo-{node['NODE_ID']}" for node in inventory}
    def drain_nodes():
        def remove(node):
            session.gcloud(node, "compute", "instance-groups", "unmanaged", "remove-instances", groups[node["NODE_ID"]],
                f"--instances={node['VM_NAME']}")
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

    for node in reversed(inventory):
        group = groups[node["NODE_ID"]]
        stage(node, "apply")
        measure("load_balancer_admit", lambda: session.gcloud(
            node, "compute", "instance-groups", "unmanaged", "add-instances", group,
            f"--instances={node['VM_NAME']}"), node=node["NODE_ID"])
        healthy = False
        def await_load_balancer_health():
            nonlocal healthy
            for attempt in range(60):
                if health(node):
                    healthy = True
                    break
                if time.time() >= deadline:
                    break
                time.sleep(5)
        measure("load_balancer_health", await_load_balancer_health, node=node["NODE_ID"])
        if not healthy:
            session.gcloud(node, "compute", "instance-groups", "unmanaged", "remove-instances", group,
                f"--instances={node['VM_NAME']}")
            if time.time() >= deadline:
                raise RuntimeError("Session expired while waiting for load balancer health")
            raise RuntimeError(f"Node {node['NODE_ID']} was not admitted by the load balancer")
    result = stage(inventory[0], "verify")
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    if sys.argv[1:] == ["sources"]:
        sources()
    elif sys.argv[1:] == ["build"]:
        build()
    else:
        raise SystemExit("Usage: delivery.py sources|build")
