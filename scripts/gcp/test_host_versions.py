import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import host_versions


def record():
    return {
        "schema_version": 1,
        "recorded_at": "2026-11-14T12:00:00+00:00",
        "os_id": "debian",
        "os_version_id": "12",
        "kernel": "6.1.0-cloud-amd64",
        "architecture": "x86_64",
        "docker_server": "29.1.3",
        "docker_compose": "2.40.3",
        "docker_buildx": "github.com/docker/buildx v0.29.1",
        "containerd": "containerd github.com/containerd/containerd v2.1.5",
        "packages": {name: "1.2.3-1" for name in host_versions.PACKAGE_NAMES},
    }


class HostVersionEvidenceTests(unittest.TestCase):
    def test_sanitizer_preserves_only_a_complete_debian_12_toolchain_record(self):
        value = record()
        result = host_versions.sanitize_host_versions(value)
        self.assertEqual(result, value)
        value["accidental_secret"] = "must not escape"
        with self.assertRaisesRegex(ValueError, "unexpected schema"):
            host_versions.sanitize_host_versions(value)

    def test_sanitizer_rejects_schema_os_timezone_and_control_character_errors(self):
        cases = (
            {**record(), "schema_version": True},
            {**record(), "os_version_id": "13"},
            {**record(), "recorded_at": "2026-11-14T12:00:00"},
            {**record(), "docker_server": "29.1.3\nsecret"},
            {**record(), "packages": {"docker-ce": "1.0"}},
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                host_versions.sanitize_host_versions(value)

    def test_node_map_requires_exactly_a_and_b_and_sanitizes_each_record(self):
        value = {"a": record(), "b": record()}
        result = host_versions.sanitize_node_map(value)
        self.assertEqual(set(result), {"a", "b"})
        for invalid in ({"a": record()}, {"a": record(), "b": record(), "c": record()}):
            with self.subTest(nodes=tuple(invalid)), self.assertRaises(ValueError):
                host_versions.sanitize_node_map(invalid)

    def test_collector_refreshes_an_allowlisted_snapshot_from_current_host_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            os_release = root / "os-release"
            os_release.write_text('ID=debian\nVERSION_ID="12"\n', encoding="utf-8")
            calls = []

            def runner(arguments, **kwargs):
                calls.append((arguments, kwargs))
                if arguments[0] == "dpkg-query":
                    output = "".join(f"{name}\t1.2.3-1\n" for name in host_versions.PACKAGE_NAMES)
                elif arguments[:3] == ["docker", "version", "--format"]:
                    output = "29.1.3\n"
                elif arguments[:3] == ["docker", "compose", "version"]:
                    output = "2.40.3\n"
                elif arguments[:3] == ["docker", "buildx", "version"]:
                    output = "github.com/docker/buildx v0.29.1\n"
                elif arguments == ["containerd", "--version"]:
                    output = "containerd github.com/containerd/containerd v2.1.5\n"
                else:
                    raise AssertionError(arguments)
                return SimpleNamespace(stdout=output)

            with (patch.object(host_versions.platform, "release", return_value="6.1.0-cloud-amd64"),
                  patch.object(host_versions.platform, "machine", return_value="x86_64")):
                path = root / "snapshot.json"
                result = host_versions.collect_host_versions(path, os_release_path=os_release, runner=runner)

            self.assertEqual(host_versions.read_host_versions(path), result)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), result)
            self.assertEqual(len(calls), 5)
            self.assertTrue(all(call[1]["check"] and call[1]["capture_output"] for call in calls))


if __name__ == "__main__":
    unittest.main()
