"""Tests for the isolated real-binary load runner verifier."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import verify_load_runtime


class LoadRuntimeVerifierTests(unittest.TestCase):
    def test_gateway_uses_the_same_digest_pinned_python_base_as_the_runner(self):
        self.assertEqual(verify_load_runtime.python_image(),
            "python:3.13-slim-bookworm@sha256:281d39ff02e3b389401586134ff9e6572954687822a58055ec07a60ded4e0b7f")

    def test_python_base_requires_a_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests/load").mkdir(parents=True)
            (root / "tests/load/Dockerfile").write_text("FROM python:latest\n")
            with self.assertRaises(ValueError):
                verify_load_runtime.python_image(root)

    def test_network_creation_retries_only_overlapping_private_pools(self):
        with patch.object(verify_load_runtime.secrets, "randbelow", return_value=0), \
                patch.object(verify_load_runtime, "invoke", side_effect=[
                    type("Result", (), {"returncode": 1, "stderr": "Pool overlaps with other one", "stdout": ""})(),
                    type("Result", (), {"returncode": 0, "stderr": "", "stdout": "network-id"})(),
                ]) as invoke:
            subnet = verify_load_runtime.create_network("test-network")
        self.assertEqual(subnet, "10.10.0.0/29")
        self.assertEqual(invoke.call_count, 2)

    def test_readiness_probe_runs_inside_the_private_container_network(self):
        with patch.object(verify_load_runtime, "invoke", return_value=
                type("Result", (), {"stdout": "", "returncode": 0})()) as invoke:
            verify_load_runtime.wait_container_ready("gateway", "/-/ready")
        args = invoke.call_args.args[0]
        self.assertEqual(args[:4], ["docker", "exec", "gateway", "python3"])
        self.assertNotIn("docker", args[1:])

    def test_container_options_are_before_the_image_and_entrypoint_arguments_after_it(self):
        with patch.object(verify_load_runtime, "invoke", return_value=
                type("Result", (), {"stdout": "a" * 64, "returncode": 0})()) as invoke:
            verify_load_runtime.start("runner", "image", ("--network", "internal"), ("--verify",))
        args = invoke.call_args.args[0]
        self.assertLess(args.index("--network"), args.index("image"))
        self.assertGreater(args.index("--verify"), args.index("image"))


if __name__ == "__main__":
    unittest.main()
