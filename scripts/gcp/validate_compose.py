"""Validate the production Compose model without real credentials or a daemon."""
from pathlib import Path
import re
import tempfile

import demo_session as session

compose = session.ROOT / "deploy/gcp/compose.yaml"
required = set(re.findall(r"\$\{([A-Z_]+):\?", compose.read_text()))
with tempfile.TemporaryDirectory(prefix="nexoruta-compose-") as temp:
    path = Path(temp) / "test.env"
    values = {key: "validation-only" for key in required}
    values.update({key: "example.invalid/test:validation" for key in required if key.endswith("_IMAGE")})
    values["SMTP_PORT"] = "1025"
    values["SMTP_SSL"] = "false"
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
    session.command("docker", "compose", "--env-file", str(path), "-f", str(compose), "config", "--quiet")
print("Production Compose configuration is valid.")
