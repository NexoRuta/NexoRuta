"""Inventory and validate all fixed runtime and Docker build images."""

import hashlib
import json
from pathlib import Path
import re

PLATFORM = "linux/amd64"
IMAGE_REF = re.compile(
    r"(?P<repository>[A-Za-z0-9][A-Za-z0-9._/-]*):(?P<tag>[A-Za-z0-9_][A-Za-z0-9_.-]*)"
    r"@(?P<digest>sha256:[a-f0-9]{64})\Z"
)
DYNAMIC_IMAGE = re.compile(r"\$\{[A-Z][A-Z0-9_]*:\?\}\Z")


def _pinned(image, name):
    if not isinstance(image, str) or not IMAGE_REF.fullmatch(image):
        raise ValueError(f"Image {name} must include a readable tag and immutable SHA-256 digest")
    return image


def collect(root):
    root = Path(root)
    compose = (root / "deploy/gcp/compose.yaml").read_text(encoding="utf-8")
    images = []
    service = None
    in_services = False
    lines = compose.splitlines()
    for index, line in enumerate(lines):
        if line == "services:":
            in_services = True
            continue
        if in_services and line and not line.startswith(" "):
            in_services = False
        service_match = re.fullmatch(r"  ([A-Za-z0-9_-]+):", line)
        if in_services and service_match:
            service = service_match.group(1)
            continue
        image_match = re.fullmatch(r"    image: (.+)", line)
        if not (in_services and service and image_match):
            continue
        image = image_match.group(1)
        platform = None
        for following in lines[index + 1:]:
            if following.startswith("    ") and not following.startswith("      "):
                if following.startswith("    platform: "):
                    platform = following.split(":", 1)[1].strip()
                break
        if DYNAMIC_IMAGE.fullmatch(image):
            if platform != PLATFORM:
                raise ValueError(f"Application image for {service} must declare {PLATFORM}")
            continue
        _pinned(image, service)
        if platform != PLATFORM:
            raise ValueError(f"Runtime image for {service} must declare {PLATFORM}")
        images.append({"kind": "runtime", "name": service, "image": image, "platform": platform})

    dockerfile = (root / "deploy/gcp/Dockerfile").read_text(encoding="utf-8")
    for line in dockerfile.splitlines():
        if not line.startswith("FROM "):
            continue
        match = re.fullmatch(r"FROM --platform=(linux/[a-z0-9_]+) (\S+) AS ([A-Za-z0-9_-]+)", line)
        if not match:
            raise ValueError("Every Docker build base must pin a digest and explicit platform")
        platform, image, stage = match.groups()
        if platform != PLATFORM:
            raise ValueError(f"Docker build stage {stage} must target {PLATFORM}")
        _pinned(image, stage)
        images.append({"kind": "build", "name": stage, "image": image, "platform": platform})

    inventory = {"schema_version": 1, "platform": PLATFORM,
                 "images": sorted(images, key=lambda item: (item["kind"], item["name"]))}
    validate_inventory(inventory)
    return inventory


def validate_inventory(inventory):
    if (not isinstance(inventory, dict) or inventory.get("schema_version") != 1
            or inventory.get("platform") != PLATFORM or not isinstance(inventory.get("images"), list)):
        raise ValueError("Release image inventory is missing or has an unsupported schema")
    seen = set()
    kinds = set()
    for item in inventory["images"]:
        if not isinstance(item, dict) or set(item) != {"kind", "name", "image", "platform"}:
            raise ValueError("Release image inventory contains an invalid record")
        if item["kind"] not in ("runtime", "build") or not isinstance(item["name"], str) or not item["name"]:
            raise ValueError("Release image inventory contains an invalid image identity")
        identity = (item["kind"], item["name"])
        if identity in seen:
            raise ValueError("Release image inventory contains a duplicate image identity")
        seen.add(identity)
        kinds.add(item["kind"])
        if item["platform"] != PLATFORM:
            raise ValueError(f"Release image {item['name']} has an unsupported platform")
        _pinned(item["image"], item["name"])
    if not {"runtime", "build"}.issubset(kinds) or sum(item["kind"] == "build" for item in inventory["images"]) != 2:
        raise ValueError("Release image inventory must contain runtime images and both build stages")
    return inventory


def canonical_bytes(inventory):
    validate_inventory(inventory)
    return json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode("utf-8")


def checksum(inventory):
    return hashlib.sha256(canonical_bytes(inventory)).hexdigest()


def write_bundle(asset_directory, inventory):
    destination = Path(asset_directory) / "image-inventory.json"
    destination.write_bytes(canonical_bytes(inventory) + b"\n")
    return destination
