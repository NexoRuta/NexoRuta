"""Local Git remotes exercise snapshots/tags; GitHub and Storage requests are mocked."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

import integration
import publication


def http_error(code):
    return urllib.error.HTTPError("https://example.invalid", code, "simulated", {}, None)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "root"
        self.remote = Path(self.temp.name) / "remote.git"
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        subprocess.run(["git", "init", "-b", "main", str(self.root)], check=True, capture_output=True)
        self.patch = patch.object(integration, "ROOT", self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        integration.git("config", "user.name", "Test")
        integration.git("config", "user.email", "test@example.invalid")
        integration.git("remote", "add", "origin", str(self.remote))
        (self.root / "infrastructure.txt").write_text("tested settings")
        integration.git("add", "infrastructure.txt")
        for name in integration.COMPONENTS:
            integration.git("update-index", "--add", "--cacheinfo", f"160000,{'a' * 40},{name}")
        integration.git("commit", "-m", "base")
        self.base = integration.git("rev-parse", "HEAD")
        integration.git("push", "origin", "main")
        self.sources = dict(zip(integration.COMPONENTS, ("b" * 40, "c" * 40, "d" * 40)))

    def test_snapshot_changes_only_gitlinks_and_never_touches_branch_index_or_files(self):
        (self.root / "infrastructure.txt").write_text("local edits must survive")
        integration.git("add", "infrastructure.txt")
        before = integration.git("write-tree")
        commit = integration.snapshot(self.base, self.sources)
        self.assertEqual(commit, integration.snapshot(self.base, self.sources))
        self.assertEqual(integration.pinned_sources(commit), self.sources)
        self.assertEqual(integration.git("rev-parse", "HEAD"), self.base)
        self.assertEqual(integration.git("write-tree"), before)
        self.assertEqual((self.root / "infrastructure.txt").read_text(), "local edits must survive")
        self.assertEqual(integration.git("show", f"{commit}:infrastructure.txt"), "tested settings")
        self.assertEqual(set(integration.git("diff", "--name-only", self.base, commit).splitlines()), set(self.sources))

    def test_remote_tag_is_annotated_immutable_and_retryable(self):
        commit = integration.snapshot(self.base, self.sources)
        tag = "integration-123-1"
        integration.publish_tag(tag, commit)
        integration.publish_tag(tag, commit)
        self.assertEqual(integration.git("cat-file", "-t", f"refs/tags/{tag}"), "tag")
        self.assertEqual(integration.git("rev-parse", f"refs/tags/{tag}^{{commit}}"), commit)
        self.assertEqual(integration.git("ls-remote", "origin", "refs/heads/main").split()[0], self.base)
        with self.assertRaisesRegex(ValueError, "will not be moved"):
            integration.publish_tag(tag, self.base)

    def test_invalid_snapshot_input_is_rejected(self):
        for value in ({}, {**self.sources, "unexpected": "a" * 40}, {**self.sources, "mobile": "main"}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                integration.snapshot(self.base, value)
        with self.assertRaises(ValueError):
            integration.publish_tag("main", self.base)

    def test_existing_lightweight_tag_cannot_impersonate_an_integration(self):
        tag = "integration-124-1"
        integration.git("tag", tag, self.base)
        with self.assertRaisesRegex(ValueError, "local"):
            integration.publish_tag(tag, self.base)
        integration.git("push", "origin", f"refs/tags/{tag}")
        with self.assertRaisesRegex(ValueError, "will not be moved"):
            integration.publish_tag(tag, self.base)

    def test_checkout_verifies_each_component_and_tag(self):
        commit = integration.snapshot(self.base, self.sources)
        tag = "integration-123-2"
        integration.publish_tag(tag, commit)
        integration.git("checkout", "--detach", commit)
        # Root Git is real; only component HEAD queries need simulated checkouts.
        real_git = integration.git

        def query(*args, **kwargs):
            if args[0] == "-C":
                return self.sources[Path(args[1]).name]
            return real_git(*args, **kwargs)

        with patch.object(integration, "git", side_effect=query):
            self.assertEqual(integration.verify_checkout(tag, commit)["sources"], self.sources)
        with patch.object(integration, "git", side_effect=lambda *a, **k: "f" * 40 if a[0] == "-C" else real_git(*a, **k)):
            with self.assertRaisesRegex(ValueError, "pinned"):
                integration.verify_checkout(tag, commit)
        with self.assertRaises(ValueError):
            integration.verify_checkout(tag, self.base)


class GitHubReleaseTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {"integration_tag": "integration-123-1", "root_sha": "a" * 40,
                         "sources": {name: "b" * 40 for name in integration.COMPONENTS},
                         "release": "release-" + "c" * 32}
        self.reference = {"object": {"type": "tag", "sha": "d" * 40}}
        self.target = {"object": {"type": "commit", "sha": "a" * 40}}

    def test_release_created_only_after_tag_and_manifest_agree(self):
        with patch.object(integration, "github", side_effect=[self.reference, self.target, http_error(404), {}]) as github:
            integration.github_release(self.manifest)
            payload = github.call_args.args[1]
            self.assertEqual(payload["tag_name"], self.manifest["integration_tag"])
            self.assertTrue(payload["prerelease"])
            self.assertFalse(payload["draft"])
            self.assertIn(self.manifest["root_sha"], payload["body"])

    def test_missing_or_different_tag_never_creates_a_release(self):
        for responses in ([http_error(404)], [self.reference, {"object": {"type": "commit", "sha": "f" * 40}}]):
            with self.subTest(responses=responses), patch.object(integration, "github", side_effect=responses) as github:
                with self.assertRaises((ValueError, urllib.error.HTTPError)):
                    integration.github_release(self.manifest)
                self.assertTrue(all(len(call.args) == 1 for call in github.call_args_list))

    def test_release_retry_is_idempotent_and_existing_mismatch_is_rejected(self):
        body = "Tested integration; VM operations remain manual.\n\n```json\n" + json.dumps(self.manifest, indent=2, sort_keys=True) + "\n```"
        for previous in ({"body": body, "draft": False}, {"body": "different", "draft": False}):
            with patch.object(integration, "github", side_effect=[self.reference, self.target, previous]) as github:
                if previous["body"] == body:
                    integration.github_release(self.manifest)
                else:
                    with self.assertRaises(ValueError):
                        integration.github_release(self.manifest)
                self.assertEqual(github.call_count, 3)


class PublicationTests(unittest.TestCase):
    def pointer(self, run=20, attempt=1):
        return {"channel": "main", "release": "release-" + "a" * 32,
                "integration_tag": "integration-123-1", "publication_order": [run, attempt]}

    def test_first_publication_uses_create_only_precondition(self):
        with patch.object(publication, "request", side_effect=[http_error(404), {}]) as request:
            self.assertTrue(publication.promote("demo-delivery", self.pointer()))
            self.assertIn("ifGenerationMatch=0", request.call_args.args[0])

    def test_channel_without_publication_order_is_rejected(self):
        with patch.object(publication, "request", side_effect=[
            {"generation": "42"}, {"channel": "main", "release": "release-legacy"},
        ]) as request:
            with self.assertRaisesRegex(ValueError, "publication order"):
                publication.promote("demo-delivery", self.pointer())
            self.assertEqual(request.call_count, 2)

    def test_old_build_cannot_replace_newer_publication(self):
        for old in (self.pointer(19, 9), self.pointer(20, 1)):
            with patch.object(publication, "request", side_effect=[{"generation": "42"}, self.pointer(20, 2)]) as request:
                self.assertFalse(publication.promote("demo-delivery", old))
                self.assertEqual(request.call_count, 2)

    def test_publication_retry_and_collision(self):
        with patch.object(publication, "request", side_effect=[{"generation": "42"}, self.pointer()]):
            self.assertTrue(publication.promote("demo-delivery", self.pointer()))
        other = {**self.pointer(), "release": "different"}
        with patch.object(publication, "request", side_effect=[{"generation": "42"}, other]):
            with self.assertRaisesRegex(ValueError, "collision"):
                publication.promote("demo-delivery", self.pointer())

    def test_generation_race_rereads_and_keeps_newer_winner(self):
        with patch.object(publication, "request", side_effect=[{"generation": "42"}, self.pointer(19), http_error(412),
                                                              {"generation": "43"}, self.pointer(21)]) as request:
            self.assertFalse(publication.promote("demo-delivery", self.pointer(20)))
            self.assertEqual(request.call_count, 5)

    def test_storage_permission_errors_fail_closed(self):
        with patch.object(publication, "request", side_effect=http_error(403)):
            with self.assertRaises(urllib.error.HTTPError):
                publication.promote("demo-delivery", self.pointer())


if __name__ == "__main__":
    unittest.main()
