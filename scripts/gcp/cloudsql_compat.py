"""CI: exercise the entire migration chain without PostgreSQL superuser rights.

This catches ownership/membership assumptions before using Cloud SQL. It is a
local approximation of its permissions, not a substitute for the managed service.
"""
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import uuid

import delivery
import demo_session as session
import vm_deploy


def main():
    name = "nexoruta-cloudsql-compat-" + uuid.uuid4().hex[:10]
    password = secrets.token_hex(24)
    root_password = secrets.token_hex(24)
    try:
        session.command("docker", "run", "--detach", "--rm", "--name", name,
                        "--publish", "127.0.0.1::5432", "--env", "POSTGRES_USER=cloud_root",
                        "--env", "POSTGRES_DB=nexoruta", "--env", "POSTGRES_PASSWORD=" + root_password,
                        "postgis/postgis:18-3.6-alpine")
        for attempt in range(60):
            ready = subprocess.run(["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "cloud_root", "-d", "nexoruta"], capture_output=True)
            if ready.returncode == 0:
                break
            time.sleep(2)
        else:
            raise RuntimeError("Compatibility database did not start")
        setup = (
            "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS pgcrypto; "
            "CREATE ROLE cloudsqlsuperuser NOLOGIN; "
            f"CREATE ROLE postgres LOGIN CREATEROLE CREATEDB INHERIT NOSUPERUSER NOBYPASSRLS PASSWORD '{password}'; "
            "GRANT cloudsqlsuperuser TO postgres; ALTER DATABASE nexoruta OWNER TO postgres; "
            "GRANT ALL ON SCHEMA public TO postgres;"
        )
        subprocess.run(["docker", "exec", "-i", name, "psql", "-U", "cloud_root", "-d", "nexoruta", "-v", "ON_ERROR_STOP=1"], input=setup, text=True, check=True, capture_output=True)
        port = session.command("docker", "port", name, "5432", capture=True).strip().rsplit(":", 1)[1]
        with tempfile.TemporaryDirectory(prefix="nexoruta-compat-") as temp:
            directory = Path(temp)
            delivery.create_bundle(directory)
            preflight = (directory / "assets/sql/preflight.sql").read_text()
            env = os.environ.copy()
            env["PGPASSWORD"] = password
            checked = subprocess.run(["docker", "exec", "-i", "--env", "PGPASSWORD=" + password,
                                      name, "psql", "-h", "127.0.0.1", "-U", "postgres", "-d", "nexoruta", "-v", "ON_ERROR_STOP=1"],
                                     input=preflight, text=True, capture_output=True)
            if checked.returncode:
                raise RuntimeError("Database preflight failed: " + checked.stderr.replace(password, "***"))
            env.update({
                "ASPNETCORE_ENVIRONMENT": "Production",
                "ConnectionStrings__Postgres": f"Host=127.0.0.1;Port={port};Database=nexoruta;Username=postgres;Password={password};Include Error Detail=true",
            })
            subprocess.run(["dotnet", str(session.ROOT / "backend/src/NexoRuta.Api/bin/Release/net10.0/NexoRuta.Api.dll"), "database-migrate"],
                           env=env, check=True)
            runtime_env = []
            runtime_passwords = {}
            for role in ("API", "WORKER", "BOOTSTRAP"):
                runtime_passwords[role] = secrets.token_hex(24)
                runtime_env.extend(["--env", f"NEXORUTA_{role}_DB_PASSWORD=" + runtime_passwords[role]])
            # Repeat preflight/provisioning to cover the update path as well.
            for sql in ("runtime-roles.sql", "postflight.sql", "preflight.sql", "runtime-roles.sql", "postflight.sql"):
                checked = subprocess.run(
                    ["docker", "exec", "-i", "--env", "PGPASSWORD=" + password, *runtime_env,
                     name, "psql", "-h", "127.0.0.1", "-U", "postgres", "-d", "nexoruta", "-v", "ON_ERROR_STOP=1"],
                    input=(directory / "assets/sql" / sql).read_text(), text=True, capture_output=True,
                )
                if checked.returncode:
                    raise RuntimeError(f"Database {sql} failed: " + checked.stderr.replace(password, "***"))
            api = str(session.ROOT / "backend/src/NexoRuta.Api/bin/Release/net10.0/NexoRuta.Api.dll")
            for _ in range(2):
                subprocess.run(["dotnet", api, "department-catalog-import"], env=env, check=True)
            runtime = {
                "passwords": {role: secrets.token_hex(24) for role in ("admin", "operator", "commerce")},
                "organization_ids": {role: str(uuid.uuid4()) for role in ("operator", "commerce")},
            }
            settings = directory / "appsettings.Production.json"
            settings.write_text(__import__("json").dumps(vm_deploy.bootstrap_config(runtime)), encoding="utf-8")
            settings.chmod(0o600)
            bootstrap_env = env.copy()
            bootstrap_env["ConnectionStrings__Postgres"] = (
                f"Host=127.0.0.1;Port={port};Database=nexoruta;Username=nexoruta_bootstrap_runtime;"
                f"Password={runtime_passwords['BOOTSTRAP']};Include Error Detail=true"
            )
            for _ in range(2):
                subprocess.run(["dotnet", api, "local-bootstrap"], env=bootstrap_env, cwd=directory, check=True)
        print("Managed PostgreSQL migrations, repeat role provisioning, catalog import and bootstrap passed.")
    finally:
        subprocess.run(["docker", "rm", "--force", name], capture_output=True)


if __name__ == "__main__":
    main()
