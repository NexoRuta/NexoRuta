"""Publish the load runner from an explicit, credential-free build context."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

import load_tests


ROOT = Path(__file__).resolve().parents[2]


def stage_sources(root, destination):
    root = root.resolve()
    for relative in load_tests.SUITE_SOURCES:
        source = root / relative
        if not source.is_file() or source.is_symlink() or not source.resolve().is_relative_to(root):
            raise ValueError("Load runner build inputs must be regular repository files")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def configuration(image):
    return {"steps": [{"name": "gcr.io/cloud-builders/docker",
                       "args": ["build", "-t", image, "-f", "tests/load/Dockerfile", "."]}],
            "images": [image], "timeout": "600s",
            "options": {"logging": "CLOUD_LOGGING_ONLY", "env": ["DOCKER_BUILDKIT=1"]}}


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=30).stdout.strip()


def build(environment, root=ROOT):
    project, region, bucket = (environment.get(name, "") for name in
                              ("GCP_PROJECT_ID", "GCP_REGION", "GCP_DELIVERY_BUCKET"))
    sha, run_id, attempt = (environment.get(name, "") for name in
                            ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"))
    if (not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", project) or region != load_tests.REGION
            or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]", bucket)
            or not re.fullmatch(r"[a-f0-9]{40}", sha)
            or not re.fullmatch(r"[1-9][0-9]{0,19}", run_id)
            or not re.fullmatch(r"[1-9][0-9]{0,9}", attempt)):
        raise ValueError("Invalid reviewed load runner build configuration")
    image = f"{region}-docker.pkg.dev/{project}/nexoruta/load-tests:{sha}-{run_id}-{attempt}"
    build_id = None
    with tempfile.TemporaryDirectory(prefix="nexoruta-load-build-") as directory:
        work = Path(directory)
        stage_sources(root, work)
        config = work / "cloudbuild.json"
        config.write_text(json.dumps(configuration(image)), encoding="utf-8")
        try:
            submitted = json.loads(command("gcloud", "builds", "submit", str(work), f"--config={config}",
                f"--project={project}", f"--region={region}", "--async", "--quiet", "--format=json",
                f"--service-account=projects/{project}/serviceAccounts/nexoruta-demo-builder@{project}.iam.gserviceaccount.com",
                f"--gcs-source-staging-dir=gs://{bucket}/sources"))
            build_id = submitted["id"]
            if not isinstance(build_id, str) or not re.fullmatch(r"[a-f0-9-]{36}", build_id):
                raise ValueError("Cloud Build returned an invalid build identifier")
            print(f"Load runner Cloud Build: {build_id}", file=sys.stderr)
            deadline = time.monotonic() + 660
            while time.monotonic() < deadline:
                info = json.loads(command("gcloud", "builds", "describe", build_id,
                    f"--project={project}", f"--region={region}", "--format=json"))
                if info["status"] == "SUCCESS":
                    images = {item["name"]: item["digest"] for item in info["results"]["images"]}
                    digest = images.get(image, "")
                    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
                        raise ValueError("Cloud Build did not publish the requested image digest")
                    return image.rsplit(":", 1)[0] + "@" + digest
                if info["status"] not in ("QUEUED", "PENDING", "WORKING"):
                    raise RuntimeError("Load runner Cloud Build did not succeed")
                time.sleep(5)
            raise RuntimeError("Load runner Cloud Build exceeded its bounded deadline")
        except BaseException:
            if isinstance(build_id, str) and re.fullmatch(r"[a-f0-9-]{36}", build_id):
                try:
                    command("gcloud", "builds", "cancel", build_id,
                            f"--project={project}", f"--region={region}", "--quiet")
                except (OSError, subprocess.SubprocessError):
                    pass  # The server-side 600-second timeout is also enforced.
            raise


if __name__ == "__main__":
    try:
        print(build(os.environ))
    except (ValueError, RuntimeError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"Load runner image failed: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1) from error
