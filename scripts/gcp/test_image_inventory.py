"""Fail closed when the release has mutable or unrecorded image inputs."""

import json
from pathlib import Path
import tempfile
import unittest

import image_inventory


ROOT = Path(__file__).resolve().parents[2]


class ImageInventoryTests(unittest.TestCase):
    def test_current_runtime_and_build_images_are_all_pinned_for_amd64(self):
        inventory = image_inventory.collect(ROOT)
        self.assertEqual(inventory["platform"], "linux/amd64")
        self.assertEqual(sum(item["kind"] == "runtime" for item in inventory["images"]), 17)
        self.assertEqual(sum(item["kind"] == "build" for item in inventory["images"]), 2)
        self.assertTrue(all(item["platform"] == "linux/amd64" for item in inventory["images"]))
        self.assertTrue(all(image_inventory.IMAGE_REF.fullmatch(item["image"])
                            for item in inventory["images"]))
        self.assertEqual({item["name"] for item in inventory["images"] if item["kind"] == "build"},
                         {"build", "runtime"})

    def test_pinned_digests_match_the_recorded_official_registry_platform_checks(self):
        report = json.loads((ROOT / "docs/auditorias/nfr-14/evidencia/image-platforms-2026-11-14.json")
                            .read_text(encoding="utf-8"))
        otel_report = json.loads((ROOT / "docs/auditorias/nfr-14/evidencia/otel-collector-platforms-2026-11-15.json")
                                 .read_text(encoding="utf-8"))
        inventory = image_inventory.collect(ROOT)
        expected = {(item["kind"], item["name"], item["image"]) for item in inventory["images"]}
        recorded = {(item["kind"], item["name"], item["image"]) for item in report["images"]
                    if item["name"] != "otel-collector"}
        recorded.add((otel_report["kind"], otel_report["name"], otel_report["image"]))
        self.assertEqual(report["required_platform"], "linux/amd64")
        self.assertEqual(len(report["images"]), 19)
        self.assertEqual(recorded, expected)
        self.assertTrue(all(item["linux_amd64"] for item in report["images"]))
        self.assertEqual(otel_report["required_platform"], "linux/amd64")
        self.assertTrue(otel_report["linux_amd64"])
        self.assertEqual(otel_report["manifest_digest"], otel_report["image"].split("@", 1)[1])

    def test_manifest_inventory_rejects_mutable_image_or_wrong_platform(self):
        inventory = image_inventory.collect(ROOT)
        mutable = json.loads(json.dumps(inventory))
        mutable["images"][0]["image"] = "grafana/grafana:latest"
        with self.assertRaisesRegex(ValueError, "tag and immutable"):
            image_inventory.validate_inventory(mutable)

        foreign_arch = json.loads(json.dumps(inventory))
        foreign_arch["images"][0]["platform"] = "linux/arm64"
        with self.assertRaisesRegex(ValueError, "unsupported platform"):
            image_inventory.validate_inventory(foreign_arch)

    def test_bundle_inventory_is_canonical_and_hashable(self):
        inventory = image_inventory.collect(ROOT)
        with tempfile.TemporaryDirectory() as temp:
            path = image_inventory.write_bundle(temp, inventory)
            payload = path.read_bytes()
            restored = json.loads(payload)
        self.assertEqual(restored, inventory)
        self.assertEqual(payload[:-1], image_inventory.canonical_bytes(inventory))
        self.assertEqual(image_inventory.checksum(restored), image_inventory.checksum(inventory))

    def test_delivery_lifecycle_only_expires_temporary_build_sources(self):
        source = (ROOT / "infra/gcp/bootstrap/delivery.tf").read_text(encoding="utf-8")
        lifecycle = source.split("lifecycle_rule {", 1)[1].split("\n  }", 1)[0]
        self.assertIn("age            = 30", lifecycle)
        self.assertIn('matches_prefix = ["sources/"]', lifecycle)
        self.assertNotIn("channels/", lifecycle)
        self.assertNotIn("releases/", lifecycle)


if __name__ == "__main__":
    unittest.main()
