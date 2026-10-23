"""Create immutable integration snapshots without updating a branch or opening a PR."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ("backend", "frontend", "mobile")
SHA = r"[a-f0-9]{40}"
TAG = r"integration-[1-9][0-9]*-[1-9][0-9]*"


def git(*args, env=None):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], env=env, text=True).strip()


def validate_sources(sources):
    if set(sources) != set(COMPONENTS) or any(not isinstance(v, str) or not re.fullmatch(SHA, v)
                                             for v in sources.values()):
        raise ValueError("Expected exactly three full component commit SHAs")
    return sources


def pinned_sources(commit):
    result = {}
    for name in COMPONENTS:
        entry = git("ls-tree", commit, "--", name).split()
        if len(entry) != 4 or entry[:2] != ["160000", "commit"] or entry[3] != name:
            raise ValueError(f"Missing submodule gitlink: {name}")
        result[name] = entry[2]
    return validate_sources(result)


def snapshot(base, sources):
    """Use a private Git index: never stage or overwrite files from the checkout."""
    if not re.fullmatch(SHA, base):
        raise ValueError("The root base must be a full commit SHA")
    validate_sources(sources)
    pinned_sources(base)
    with tempfile.TemporaryDirectory(prefix="nexoruta-index-") as temp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(temp) / "index"),
               "GIT_AUTHOR_NAME": "NexoRuta integration", "GIT_COMMITTER_NAME": "NexoRuta integration",
               "GIT_AUTHOR_EMAIL": "integration@nexoruta.invalid",
               "GIT_COMMITTER_EMAIL": "integration@nexoruta.invalid"}
        # Fixed metadata makes retrying the same snapshot produce the same commit.
        date = git("show", "-s", "--format=%cI", base)
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        git("read-tree", base, env=env)
        for name, sha in sorted(sources.items()):
            git("update-index", "--cacheinfo", f"160000,{sha},{name}", env=env)
        tree = git("write-tree", env=env)
        message = "Integration snapshot\n\n" + json.dumps(sources, sort_keys=True)
        return git("commit-tree", tree, "-p", base, "-m", message, env=env)


def publish_tag(tag, commit):
    if not re.fullmatch(TAG, tag) or not re.fullmatch(SHA, commit):
        raise ValueError("Invalid integration tag or commit")
    ref = f"refs/tags/{tag}"
    remote = subprocess.run(["git", "-C", str(ROOT), "ls-remote", "--exit-code", "origin", ref],
                            capture_output=True, text=True)
    if remote.returncode == 0:
        git("fetch", "--no-tags", "origin", ref)
        if git("cat-file", "-t", "FETCH_HEAD") != "tag" or git("rev-parse", "FETCH_HEAD^{commit}") != commit:
            raise ValueError("Integration tag already identifies another snapshot; it will not be moved")
        return
    if remote.returncode != 2:
        raise RuntimeError("Could not check the remote integration tag")
    local = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", ref],
                           capture_output=True, text=True)
    if local.returncode == 0:
        if git("cat-file", "-t", ref) != "tag" or git("rev-parse", ref + "^{commit}") != commit:
            raise ValueError("Conflicting local integration tag")
    else:
        git("-c", "user.name=NexoRuta integration", "-c", "user.email=integration@nexoruta.invalid",
            "tag", "-a", tag, commit, "-m", f"Tested NexoRuta snapshot {commit}")
    # No force push and no branch ref: the only remote mutation is this new tag.
    git("push", "origin", f"{ref}:{ref}")


def verify_checkout(tag, expected_commit=None):
    if not re.fullmatch(TAG, tag):
        raise ValueError("Invalid integration tag")
    commit = git("rev-parse", "HEAD")
    if git("rev-parse", f"refs/tags/{tag}^{{commit}}") != commit or (expected_commit and commit != expected_commit):
        raise ValueError("Checkout does not match the immutable integration tag")
    sources = pinned_sources(commit)
    for name, sha in sources.items():
        if git("-C", str(ROOT / name), "rev-parse", "HEAD") != sha:
            raise ValueError(f"Checkout does not match the pinned {name} SHA")
    return {"integration_tag": tag, "root_sha": commit, "sources": sources}


def github(path, payload=None):
    repository = os.environ["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid GitHub repository")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/{path}",
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                 "Accept": "application/vnd.github+json", "Content-Type": "application/json",
                 "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def github_release(manifest):
    tag = manifest["integration_tag"]
    if not re.fullmatch(TAG, tag) or not re.fullmatch(SHA, manifest["root_sha"]):
        raise ValueError("Invalid release snapshot")
    validate_sources(manifest["sources"])
    # Release creation must never implicitly create a tag that did not pass our tag job.
    reference = github(f"git/ref/tags/{tag}")["object"]
    if reference.get("type") != "tag":
        raise ValueError("Expected the tested annotated integration tag")
    target = github(f"git/tags/{reference['sha']}")["object"]
    if target.get("type") != "commit" or target.get("sha") != manifest["root_sha"]:
        raise ValueError("GitHub tag and published root snapshot differ")
    # The same manifest is visible in GitHub and in the private immutable delivery bundle.
    body = "Tested integration; VM operations remain manual.\n\n```json\n" + json.dumps(manifest, indent=2, sort_keys=True) + "\n```"
    try:
        previous = github(f"releases/tags/{tag}")
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    else:
        if previous.get("body") != body or previous.get("draft"):
            raise ValueError("Existing GitHub Release does not match this publication")
        return
    github("releases", {"tag_name": tag, "name": tag, "body": body,
                        "draft": False, "prerelease": True, "make_latest": "false"})


def output(values):
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            for key, value in values.items():
                stream.write(f"{key}={value}\n")


def main():
    if sys.argv[1:] == ["tag"]:
        sources = validate_sources(json.loads(os.environ["TESTED_SOURCES"]))
        run, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
        tag = f"integration-{run}-{attempt}"
        if not re.fullmatch(TAG, tag):
            raise ValueError("Invalid Actions execution identity")
        commit = snapshot(os.environ["GITHUB_SHA"], sources)
        publish_tag(tag, commit)
        output({"tag": tag, "commit": commit})
    elif sys.argv[1:] == ["check"]:
        manifest = verify_checkout(os.environ["INTEGRATION_TAG"], os.environ.get("INTEGRATION_COMMIT"))
        (ROOT / "sources.json").write_text(json.dumps(manifest["sources"]), encoding="utf-8")
        print(json.dumps(manifest))
    elif sys.argv[1:] == ["release"]:
        github_release(json.loads(os.environ["RELEASE_MANIFEST"]))
    else:
        raise SystemExit("Usage: integration.py tag|check|release")


if __name__ == "__main__":
    main()
