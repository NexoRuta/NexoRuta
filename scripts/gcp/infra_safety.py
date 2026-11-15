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


def _retired_load_preparer_secret_cleanup(resource, actions):
    """Allow only the explicitly retired synthetic-admin credential secret and its access grants."""
    if actions != ["delete"]:
        return False
    address = resource.get("address")
    resource_type = resource.get("type")
    before = (resource.get("change") or {}).get("before") or {}
    if (address == 'google_secret_manager_secret.config["nexoruta-load-preparer-credentials"]'
            and resource_type == "google_secret_manager_secret"):
        return True
    if (address == "google_secret_manager_secret_version.load_preparer_credentials"
            and resource_type == "google_secret_manager_secret_version"):
        secret = before.get("secret", "")
        return (before.get("deletion_policy") == "ABANDON" and isinstance(secret, str)
                and secret.endswith("/secrets/nexoruta-load-preparer-credentials"))
    if (address == "google_secret_manager_secret_iam_member.load_preparer_credentials"
            and resource_type == "google_secret_manager_secret_iam_member"):
        secret_id = before.get("secret_id", "")
        return (isinstance(secret_id, str)
                and secret_id.endswith("/secrets/nexoruta-load-preparer-credentials"))
    return False


def check_plan(plan, operation):
    """Reject destructive actions except the explicitly retired demo credential secret."""
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
        if operation in ("bootstrap", "start", "update") and _abandoned_secret_version_replacement(resource, actions):
            continue
        if operation in ("bootstrap", "start", "update") and _retired_load_preparer_secret_cleanup(resource, actions):
            continue
        if operation == "bootstrap":
            raise RuntimeError(f"Bootstrap plan deletes/replaces resources: {address}")
        raise RuntimeError(
            f"Plan would delete or replace {address}. "
            "This session workflow does not destroy resources; review locally."
        )
