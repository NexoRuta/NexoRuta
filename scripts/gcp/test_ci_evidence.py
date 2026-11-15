"""Validation of the protected CI evidence carried by published releases."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ci_evidence


class CiEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.sources = {name: char * 40 for name, char in zip(("backend", "frontend", "mobile"), "bcd")}
        self.plan = {
            "version": 1,
            "current": {"root_sha": "e" * 40, "sources": dict(self.sources)},
            "baseline": {
                "release": "release-" + "f" * 32,
                "android_input_sha256": "a" * 64,
                "android_verified_mobile_sha": self.sources["mobile"],
                "android_verification": self.baseline_proof(),
            },
            "android_input_sha256": "a" * 64,
            "components": {"mobile_android": {"run": True}},
            "images": ["api", "worker"],
            "publish_required": True,
        }
        self.event = {
            "action": "synchronize", "number": 11,
            "pull_request": {
                "base": {"ref": "main", "repo": {"id": 123}},
                "head": {"ref": "develop", "repo": {"id": 123}},
            },
        }

    def baseline_proof(self):
        release = "release-" + "f" * 32
        return {
            "schema_version": 1,
            "android_input_sha256": "a" * 64,
            "mobile_sha": self.sources["mobile"],
            "verified_by": {
                "repository_id": "123", "workflow_path": ci_evidence.WORKFLOW_PATH,
                "run_id": 6, "run_attempt": 1, "event": "pull_request",
                "pull_request": 10, "base_branch": "main", "head_branch": "develop",
                "head_repository_id": "123", "root_sha": "8" * 40,
                "root_tree": "9" * 40, "sources": dict(self.sources),
                "artifact": {"id": 31, "name": "nfr14-ci-evidence-1",
                             "digest": "sha256:" + "c" * 64},
            },
            "origin_release": release,
        }

    def ci_env(self):
        return patch.dict(os.environ, {
            "GITHUB_REPOSITORY_ID": "123", "GITHUB_RUN_ID": "7",
            "GITHUB_RUN_ATTEMPT": "2", "GITHUB_RUN_NUMBER": "20",
        })

    def test_android_job_success_creates_bound_evidence(self):
        with self.ci_env():
            evidence = ci_evidence.make_ci_evidence(self.plan, "9" * 40, self.event,
                                                   {"mobile_android": "success"})
        self.assertEqual(evidence["android_job"], "success")
        self.assertEqual(evidence["android_verification"]["mobile_sha"], self.sources["mobile"])
        self.assertEqual(evidence["android_verification"]["verified_by"]["run_id"], 7)
        self.assertEqual(evidence["android_verification"]["verified_by"]["root_tree"], "9" * 40)

    def test_android_required_but_failed_does_not_issue_evidence(self):
        with self.ci_env(), self.assertRaisesRegex(ValueError, "did not succeed"):
            ci_evidence.make_ci_evidence(self.plan, "9" * 40, self.event,
                                         {"mobile_android": "failure"})

    def test_skipped_android_reuses_only_the_same_validated_release_proof(self):
        self.plan["components"]["mobile_android"]["run"] = False
        with self.ci_env():
            evidence = ci_evidence.make_ci_evidence(self.plan, "9" * 40, self.event,
                                                   {"mobile_android": "skipped"})
        self.assertEqual(evidence["android_job"], "skipped")
        self.assertEqual(evidence["android_verification"], self.plan["baseline"]["android_verification"])
        self.assertEqual(evidence["android_reused_from_release"], self.plan["baseline"]["release"])

        self.plan["android_input_sha256"] = "b" * 64
        with self.ci_env(), self.assertRaisesRegex(ValueError, "current input digest"):
            ci_evidence.make_ci_evidence(self.plan, "9" * 40, self.event,
                                         {"mobile_android": "skipped"})

    def release_manifest(self, android_ran):
        self.plan["components"]["mobile_android"]["run"] = android_ran
        with self.ci_env():
            evidence = ci_evidence.make_ci_evidence(
                self.plan, "9" * 40, self.event,
                {"mobile_android": "success" if android_ran else "skipped"},
            )
        release = "release-" + "a" * 32
        # The PR merge commit and the protected main commit can have different
        # SHAs while resolving to the same integrated source tree.
        snapshot = {"source_ref": "refs/heads/main", "root_sha": "0" * 40,
                    "sources": self.sources}
        resolved = {
            "evidence": evidence,
            "artifact": {"id": 31, "name": "nfr14-ci-evidence-2", "digest": "sha256:" + "c" * 64},
            "run": {"id": 7, "attempt": 2},
        }
        with tempfile.TemporaryDirectory() as temp:
            resolved_path = Path(temp) / "resolved.json"
            resolved_path.write_text(json.dumps(resolved), encoding="utf-8")
            with patch.object(ci_evidence.integration, "git", return_value="9" * 40):
                identity, proof = ci_evidence.bind_for_release(
                    str(resolved_path), snapshot=snapshot, plan=self.plan, release=release,
                )
        return {
            "channel": "main", "release": release, "root_sha": snapshot["root_sha"],
            "sources": self.sources, "ci_evidence": identity, "android_verification": proof,
            "android_input_sha256": proof["android_input_sha256"],
            "android_verified_mobile_sha": proof["mobile_sha"], "ci_plan": self.plan,
        }

    def test_main_manifest_validates_android_success_against_ci_plan(self):
        manifest = self.release_manifest(android_ran=True)
        self.assertNotEqual(manifest["ci_evidence"]["root_sha"], manifest["root_sha"])
        self.assertEqual(manifest["ci_evidence"]["root_tree"], "9" * 40)
        self.assertEqual(ci_evidence.validate_manifest_android(manifest), manifest["android_verification"])

    def test_main_manifest_validates_reused_android_proof_against_exact_baseline(self):
        manifest = self.release_manifest(android_ran=False)
        self.assertEqual(ci_evidence.validate_manifest_android(manifest), manifest["android_verification"])

    def test_main_manifest_rejects_malformed_android_plan_before_using_it(self):
        manifest = self.release_manifest(android_ran=True)
        manifest["ci_plan"]["components"] = None
        with self.assertRaisesRegex(ValueError, "component decisions"):
            ci_evidence.validate_manifest_android(manifest)

    def test_only_same_repository_develop_to_main_ci_can_issue_evidence(self):
        self.event["pull_request"]["head"]["repo"]["id"] = 456
        with self.ci_env(), self.assertRaisesRegex(ValueError, "same-repository"):
            ci_evidence.make_ci_evidence(self.plan, "9" * 40, self.event,
                                         {"mobile_android": "success"})

    def test_resolver_selects_only_successful_ci_for_exact_pr_tree(self):
        with self.ci_env(), patch.dict(os.environ, {
            "GITHUB_REPOSITORY": "acme/nexoruta", "GH_TOKEN": "non-secret-test-token",
        }):
            with self.ci_env():
                evidence = ci_evidence.make_ci_evidence(self.plan, "9" * 40, self.event,
                                                       {"mobile_android": "success"})
            pull = {
                "number": 11, "merged_at": "2026-11-14T20:00:00Z",
                "base": {"ref": "main", "repo": {"id": 123, "full_name": "acme/nexoruta"}},
                "head": {"ref": "develop", "sha": "b" * 40,
                         "repo": {"id": 123, "full_name": "acme/nexoruta"}},
            }
            run = {
                "id": 7, "run_attempt": 2, "run_number": 20,
                "path": ".github/workflows/ci.yml@refs/pull/11/merge",
                "event": "pull_request", "status": "completed", "conclusion": "success",
                "pull_requests": [{
                    "number": 11,
                    "base": {"ref": "main", "repo": {"id": 123}},
                    "head": {"ref": "develop", "repo": {"id": 123}},
                }],
            }
            artifact = {"id": 31, "name": "nfr14-ci-evidence-2", "expired": False,
                        "digest": "sha256:" + "c" * 64}
            responses = [
                [pull],
                {"workflow_runs": [run]},
                {"artifacts": [artifact]},
                {"jobs": [{"name": "Integrated CI / result", "conclusion": "success"}]},
            ]
            with tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / "resolved.json"
                with (patch.object(ci_evidence, "_api", side_effect=responses),
                      patch.object(ci_evidence, "_download_artifact", return_value=evidence)):
                    resolved = ci_evidence.resolve(str(destination), "c" * 40, "9" * 40,
                                                   self.sources, self.plan)
                stored = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(stored, resolved)
        self.assertEqual(resolved["run"]["id"], 7)
        self.assertEqual(resolved["artifact"]["id"], 31)

    def test_resolver_confirms_merge_when_associated_pull_omits_merge_fields(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "acme/nexoruta", "GITHUB_REPOSITORY_ID": "123",
                                     "GH_TOKEN": "test"}):
            pull = {
                "number": 11,
                "base": {"ref": "main", "repo": {"id": 123, "full_name": "acme/nexoruta"}},
                "head": {"ref": "develop", "repo": {"id": 123, "full_name": "acme/nexoruta"}},
            }
            detail = {"number": 11, "merged": True}
            with (patch.object(ci_evidence, "_api", side_effect=[[pull], detail, {"workflow_runs": []}]) as api,
                  tempfile.TemporaryDirectory() as temp):
                with self.assertRaisesRegex(ValueError, "No successful Integrated CI evidence"):
                    ci_evidence.resolve(str(Path(temp) / "resolved.json"), "c" * 40, "9" * 40,
                                        self.sources, self.plan)
        self.assertEqual(api.call_args_list[1].args[0], "pulls/11")

    def test_resolver_rejects_a_different_tree_even_when_ci_passed(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "acme/nexoruta", "GH_TOKEN": "test",
                                     "GITHUB_REPOSITORY_ID": "123"}):
            evidence = {
                "schema_version": 1, "repository_id": "123", "workflow_path": ci_evidence.WORKFLOW_PATH,
                "run_id": 7, "run_attempt": 1, "run_number": 20, "event": "pull_request",
                "pull_request": 11, "base_branch": "main", "head_branch": "develop",
                "head_repository_id": "123", "root_sha": "e" * 40,
                "root_tree": "8" * 40, "sources": self.sources,
                "plan": {**self.plan, "current": {"root_sha": "e" * 40, "sources": self.sources}},
            }
            pull = {"number": 11, "merged": True, "base": {"ref": "main", "repo": {"id": 123, "full_name": "acme/nexoruta"}},
                    "head": {"ref": "develop", "sha": "b" * 40, "repo": {"id": 123, "full_name": "acme/nexoruta"}}}
            run = {"id": 7, "run_attempt": 1, "run_number": 20, "path": ".github/workflows/ci.yml@refs/pull/11/merge",
                   "event": "pull_request", "status": "completed", "conclusion": "success",
                   "pull_requests": [{"number": 11, "base": {"ref": "main", "repo": {"id": 123}},
                                      "head": {"ref": "develop", "repo": {"id": 123}}}]}
            artifact = {"id": 31, "name": "nfr14-ci-evidence-1", "expired": False,
                        "digest": "sha256:" + "c" * 64}
            with (patch.object(ci_evidence, "_api", side_effect=[[pull], {"workflow_runs": [run]},
                                                                  {"artifacts": [artifact]}]),
                  patch.object(ci_evidence, "_download_artifact", return_value=evidence),
                  tempfile.TemporaryDirectory() as temp):
                with self.assertRaisesRegex(ValueError, "No successful Integrated CI evidence"):
                    ci_evidence.resolve(str(Path(temp) / "resolved.json"), "c" * 40, "9" * 40,
                                        self.sources, self.plan)


if __name__ == "__main__":
    unittest.main()
