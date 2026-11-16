"""Strict, secret-free evidence for the services expected on each VM."""

SERVICES_A = (
    "api", "admin", "backoffice", "commerce", "tracking", "worker-rabbit",
    "worker-kafka", "worker-push", "worker-webhooks", "grafana", "otel-collector",
    "alloy", "sql-proxy", "rabbitmq", "kafka", "mongo", "mailpit", "proxy",
    "prometheus", "prometheus-write-gateway", "gcp-metrics-collector", "loki", "tempo",
)
SERVICES_B_BASE = (
    "api", "admin", "backoffice", "commerce", "tracking", "worker-rabbit",
    "worker-kafka", "worker-push", "worker-webhooks", "grafana", "otel-collector",
    "alloy", "sql-proxy",
)
HEALTHCHECK_SERVICES = frozenset((
    "api", "admin", "backoffice", "commerce", "tracking", "worker-rabbit",
    "worker-kafka", "worker-push", "worker-webhooks", "grafana", "proxy",
    "rabbitmq", "kafka", "mongo", "redis", "mailpit",
))
NODES = ("a", "b")


def expected_services(node, cache_enabled):
    if type(cache_enabled) is not bool:
        raise ValueError("The deployment health cache mode must be boolean")
    if node == "a":
        return tuple(sorted(SERVICES_A))
    if node == "b":
        return tuple(sorted(SERVICES_B_BASE + (("redis",) if cache_enabled else ())))
    raise ValueError("The deployment health node must be A or B")


def sanitize_node_snapshot(value, node, cache_enabled):
    if node not in NODES:
        raise ValueError("The deployment health node must be A or B")
    expected = expected_services(node, cache_enabled)
    if (type(cache_enabled) is not bool or not isinstance(value, dict)
            or set(value) != {"node", "services"} or value.get("node") != node):
        raise ValueError("The Compose health snapshot has an invalid node identity")
    services = value.get("services")
    if not isinstance(services, list) or len(services) != len(expected):
        raise ValueError("The Compose health snapshot is incomplete")
    by_name = {}
    for item in services:
        if not isinstance(item, dict) or set(item) != {"service", "state", "health"}:
            raise ValueError("The Compose health snapshot has an invalid service record")
        name = item.get("service")
        if (not isinstance(name, str) or name not in expected or name in by_name
                or item.get("state") != "running"):
            raise ValueError("A required Compose service is missing, duplicated, or stopped")
        health = item.get("health")
        expected_health = "healthy" if name in HEALTHCHECK_SERVICES else "not-configured"
        if health != expected_health:
            raise ValueError("A Compose healthcheck is missing, unhealthy, or unexpected")
        by_name[name] = {"service": name, "state": "running", "health": health}
    if set(by_name) != set(expected):
        raise ValueError("The Compose health snapshot does not contain the exact service set")
    return {"node": node, "services": [by_name[name] for name in expected]}


def sanitize_node_map(value, cache_enabled):
    if not isinstance(value, dict) or set(value) != set(NODES):
        raise ValueError("Compose health evidence must cover exactly nodes A and B")
    return {node: sanitize_node_snapshot(value[node], node, cache_enabled) for node in NODES}
