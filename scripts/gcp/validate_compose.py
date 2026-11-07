"""Validate the production Compose model without real credentials or a daemon."""
from pathlib import Path
import re
import tempfile

import demo_session as session

compose = session.ROOT / "deploy/gcp/compose.yaml"
required = set(re.findall(r"\$\{([A-Z0-9_]+):\?", compose.read_text()))
with tempfile.TemporaryDirectory(prefix="nexoruta-compose-") as temp:
    path = Path(temp) / "test.env"
    redis_config = Path(temp) / "redis"
    redis_config.mkdir()
    for name in ("redis.conf", "ca.crt", "server.crt", "server.key", "users.acl", "redis-auth"):
        (redis_config / name).write_text("validation-only\n", encoding="ascii")
    values = {key: "validation-only" for key in required}
    values.update({key: "example.invalid/test:validation" for key in required if key.endswith("_IMAGE")})
    values["SMTP_PORT"] = "1025"
    values["SMTP_SSL"] = "false"
    values["NODE_PRIVATE_IP"] = "127.0.0.1"
    values["NODE_NAME"] = "node-a"
    values["RELEASE_ID"] = "release-validation"
    values["NEXORUTA_CACHE_ENABLED"] = "true"
    values["REDIS_CONFIG_DIR"] = str(redis_config)
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
    session.command("docker", "compose", "--env-file", str(path), "-f", str(compose), "config", "--quiet")
print("Production Compose configuration is valid.")
