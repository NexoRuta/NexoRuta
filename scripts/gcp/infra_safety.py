"""Shared fail-closed checks for OpenTofu plans that preserve the demo state."""


def _abandoned_secret_version_replacement(resource, actions):
    change = resource.get("change") or {}
    before = change.get("before") or {}
    after = change.get("after") or {}
    return (
        resource.get("type") == "google_secret_manager_secret_version"
        and set(actions) == {"create", "delete"}
        and before.get("deletion_policy") == "ABANDON"
        and after.get("deletion_policy") == "ABANDON"
    )


def check_plan(plan, operation):
    """Reject destructive actions before apply; bootstrap may create only."""
    if operation not in ("bootstrap", "start", "update", "stop"):
        raise ValueError("Unsupported infrastructure plan operation")
    if not isinstance(plan, dict) or not isinstance(plan.get("resource_changes", []), list):
        raise RuntimeError("OpenTofu returned an invalid plan; refusing to apply")

    for resource in plan.get("resource_changes", []):
        if not isinstance(resource, dict) or not isinstance(resource.get("change"), dict):
            raise RuntimeError("OpenTofu returned an invalid resource change; refusing to apply")
        address = resource.get("address")
        actions = resource["change"].get("actions")
        if (not isinstance(address, str) or not isinstance(actions, list)
                or any(action not in ("no-op", "read", "create", "update", "delete") for action in actions)):
            raise RuntimeError("OpenTofu returned an invalid action; refusing to apply")

        if operation == "stop" and "create" in actions:
            raise RuntimeError("Stopping a session must not create missing resources")
        if "delete" not in actions:
            continue
        if operation in ("start", "update") and _abandoned_secret_version_replacement(resource, actions):
            continue
        if operation == "bootstrap":
            raise RuntimeError(f"Bootstrap plan deletes/replaces resources: {address}")
        raise RuntimeError(
            f"Plan would delete or replace {address}. "
            "This session workflow does not destroy resources; review locally."
        )
