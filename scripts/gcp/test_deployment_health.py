from pathlib import Path
import re
import unittest

import deployment_health
import vm_deploy


def snapshot(node, cache_enabled):
    services = []
    for name in deployment_health.expected_services(node, cache_enabled):
        services.append({
            "service": name,
            "state": "running",
            "health": "healthy" if name in deployment_health.HEALTHCHECK_SERVICES else "not-configured",
        })
    return {"node": node, "services": services}


class DeploymentHealthTests(unittest.TestCase):
    def test_expected_services_match_the_vm_deployment_topology(self):
        expected_a = set(vm_deploy.APPS + ("sql-proxy",) + vm_deploy.SHARED)
        expected_b = set(vm_deploy.APPS + ("sql-proxy",))
        self.assertEqual(set(deployment_health.expected_services("a", True)), expected_a)
        self.assertEqual(set(deployment_health.expected_services("b", True)), expected_b | {"redis"})
        self.assertEqual(set(deployment_health.expected_services("b", False)), expected_b)

    def test_healthcheck_allowlist_matches_compose_services(self):
        compose_path = Path(__file__).resolve().parents[2] / "deploy/gcp/compose.yaml"
        text = compose_path.read_text(encoding="utf-8")
        services_text = text.split("services:\n", 1)[1].split("\nvolumes:", 1)[0]
        starts = list(re.finditer(r"^  ([a-z0-9-]+):\n", services_text, re.MULTILINE))
        healthchecked = set()
        for index, match in enumerate(starts):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(services_text)
            block = services_text[match.start():end]
            if re.search(r"^    healthcheck:", block, re.MULTILINE):
                healthchecked.add(match.group(1))
        # The pinned Mailpit image supplies its own Docker healthcheck.
        self.assertEqual(healthchecked | {"mailpit"}, set(deployment_health.HEALTHCHECK_SERVICES))

    def test_exact_running_service_snapshot_is_sanitized_and_sorted(self):
        value = snapshot("a", True)
        value["services"].reverse()
        result = deployment_health.sanitize_node_snapshot(value, "a", True)
        self.assertEqual(result["services"], snapshot("a", True)["services"])

    def test_snapshot_rejects_missing_duplicate_unexpected_stopped_or_unhealthy_services(self):
        valid = snapshot("a", True)
        cases = []
        missing = snapshot("a", True)
        missing["services"].pop()
        cases.append(missing)
        duplicate = snapshot("a", True)
        duplicate["services"][-1] = dict(duplicate["services"][0])
        cases.append(duplicate)
        unexpected = snapshot("a", True)
        unexpected["services"][0]["service"] = "unknown"
        cases.append(unexpected)
        stopped = snapshot("a", True)
        stopped["services"][0]["state"] = "exited"
        cases.append(stopped)
        unhealthy = snapshot("a", True)
        checked = next(item for item in unhealthy["services"]
                       if item["service"] in deployment_health.HEALTHCHECK_SERVICES)
        checked["health"] = "starting"
        cases.append(unhealthy)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                deployment_health.sanitize_node_snapshot(value, "a", True)
        self.assertEqual(len(valid["services"]), len(deployment_health.expected_services("a", True)))

    def test_node_map_requires_both_nodes_and_cache_controls_redis(self):
        values = {"a": snapshot("a", False), "b": snapshot("b", False)}
        result = deployment_health.sanitize_node_map(values, False)
        self.assertNotIn("redis", {item["service"] for item in result["b"]["services"]})
        values["b"] = snapshot("b", True)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            deployment_health.sanitize_node_map(values, False)
        with self.assertRaisesRegex(ValueError, "exactly nodes A and B"):
            deployment_health.sanitize_node_map({"a": values["a"]}, False)


if __name__ == "__main__":
    unittest.main()
