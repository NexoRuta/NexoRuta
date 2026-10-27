"""Exercise Cloud SQL-style ownership, runtime isolation and shared hosting SQL.

The disposable local PostgreSQL instance approximates Cloud SQL permissions;
this harness never connects to the managed database or changes GCP resources.
"""
from concurrent.futures import ThreadPoolExecutor
import json
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
    password, root_password = secrets.token_hex(24), secrets.token_hex(24)
    runtime_passwords = {role: secrets.token_hex(24) for role in ("API", "WORKER", "BOOTSTRAP")}
    hosting_passwords = {
        **{f"KEYS_{portal}_PASSWORD": secrets.token_hex(24)
           for portal in ("API", "ADMIN", "BACKOFFICE", "COMMERCE", "TRACKING")},
        "MONITOR_DB_PASSWORD": secrets.token_hex(24),
        "GRAFANA_DB_PASSWORD": secrets.token_hex(24),
    }
    redactions = [password, root_password, *runtime_passwords.values(), *hosting_passwords.values()]

    def run(args, *, env=None, input=None, cwd=None, check=True):
        # Capture command output and never include argv in errors: provisioning
        # SQL and application diagnostics can contain generated credentials.
        result = subprocess.run(args, env=env, input=input, cwd=cwd, text=True, capture_output=True)
        if check and result.returncode:
            detail = result.stderr or result.stdout
            for secret in redactions:
                detail = detail.replace(secret, "***")
            raise RuntimeError(f"{args[0]} failed ({result.returncode}): {detail[-5000:]}")
        return result

    provision_env = os.environ.copy()
    provision_env.update(hosting_passwords)
    provision_env.update({f"NEXORUTA_{role}_DB_PASSWORD": secret
                          for role, secret in runtime_passwords.items()})
    provision_names = ["--env", "PGPASSWORD"]
    for variable in (*hosting_passwords, *(f"NEXORUTA_{role}_DB_PASSWORD" for role in runtime_passwords)):
        provision_names.extend(["--env", variable])

    def psql(sql, login="postgres", secret=password, database="nexoruta", check=True):
        process_env = provision_env.copy()
        process_env["PGPASSWORD"] = secret
        return run(["docker", "exec", "-i", *provision_names, name, "psql", "-X", "-A", "-t", "-q",
                    "-h", "127.0.0.1", "-U", login, "-d", database, "-v", "ON_ERROR_STOP=1"],
                   input=sql, env=process_env, check=check)

    def denied(sql, login, secret):
        result = psql("\\set VERBOSITY sqlstate\n" + sql, login, secret, check=False)
        if not result.returncode or "42501" not in result.stderr:
            raise RuntimeError(f"Expected insufficient privilege for {login} was not enforced")

    try:
        docker_env = os.environ.copy()
        docker_env["POSTGRES_PASSWORD"] = root_password
        run(["docker", "run", "--detach", "--rm", "--name", name,
             "--publish", "127.0.0.1::5432", "--env", "POSTGRES_USER=cloud_root",
             "--env", "POSTGRES_DB=nexoruta", "--env", "POSTGRES_PASSWORD",
             "postgis/postgis:18-3.6-alpine"], env=docker_env)
        for _ in range(60):
            result = run(["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "cloud_root",
                          "-d", "nexoruta"], check=False)
            if result.returncode == 0:
                break
            time.sleep(2)
        else:
            raise RuntimeError("Compatibility database did not start")
        psql(
            "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS pgcrypto; "
            "CREATE ROLE cloudsqlsuperuser NOLOGIN; "
            f"CREATE ROLE postgres LOGIN CREATEROLE CREATEDB INHERIT NOSUPERUSER NOBYPASSRLS PASSWORD '{password}'; "
            "GRANT cloudsqlsuperuser TO postgres; ALTER DATABASE nexoruta OWNER TO postgres; "
            "GRANT ALL ON SCHEMA public TO postgres;", "cloud_root", root_password)
        port = run(["docker", "port", name, "5432"]).stdout.strip().rsplit(":", 1)[1]
        with tempfile.TemporaryDirectory(prefix="nexoruta-compat-") as temp:
            directory = Path(temp)
            delivery.create_bundle(directory)
            psql((directory / "assets/sql/preflight.sql").read_text())
            env = os.environ.copy()
            env.update({
                "ASPNETCORE_ENVIRONMENT": "Production",
                "ConnectionStrings__Postgres": f"Host=127.0.0.1;Port={port};Database=nexoruta;Username=postgres;Password={password};Include Error Detail=true",
            })
            api = str(session.ROOT / "backend/src/NexoRuta.Api/bin/Release/net10.0/NexoRuta.Api.dll")
            run(["dotnet", api, "database-migrate"], env=env)
            print("Migration chain passed with NOSUPERUSER/CREATEROLE/CREATEDB postgres.")
            # Repeat all role/schema provisioning, including hosting, to exercise
            # ALTER OWNER and CREATE OR REPLACE against their final owners.
            for sql in ("runtime-roles.sql", "postflight.sql", "hosting.sql", "preflight.sql",
                        "runtime-roles.sql", "postflight.sql", "hosting.sql"):
                psql((directory / "assets/sql" / sql).read_text())
            print("Runtime roles and hosting.sql provisioned twice.")
            for _ in range(2):
                run(["dotnet", api, "department-catalog-import"], env=env)
            runtime = {
                "passwords": {role: secrets.token_hex(24) for role in ("admin", "operator", "commerce")},
                "organization_ids": {role: str(uuid.uuid4()) for role in ("operator", "commerce")},
            }
            redactions.extend(runtime["passwords"].values())
            settings = directory / "appsettings.Production.json"
            settings.write_text(json.dumps(vm_deploy.bootstrap_config(runtime)), encoding="utf-8")
            settings.chmod(0o600)
            bootstrap_env = env.copy()
            bootstrap_env["ConnectionStrings__Postgres"] = (
                f"Host=127.0.0.1;Port={port};Database=nexoruta;Username=nexoruta_bootstrap_runtime;"
                f"Password={runtime_passwords['BOOTSTRAP']};Include Error Detail=true")
            for _ in range(2):
                run(["dotnet", api, "local-bootstrap"], env=bootstrap_env, cwd=directory)
            psql((directory / "assets/sql/postflight.sql").read_text())
            print("Catalog import and runtime bootstrap repeated; forced RLS preserved.")

            # Inspect attributes and direct memberships without emitting secrets.
            technical = [*(f"nexoruta_keys_{portal}" for portal in
                            ("api", "admin", "backoffice", "commerce", "tracking")),
                         "nexoruta_monitor_runtime", "nexoruta_grafana_runtime"]
            logins = technical + ["nexoruta_api_runtime", "nexoruta_worker_runtime", "nexoruta_bootstrap_runtime"]
            role_sql = ",".join("'" + role + "'" for role in logins)
            unsafe = psql(f"SELECT count(*) FROM pg_roles WHERE rolname IN ({role_sql}) "
                          "AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication);").stdout.strip()
            if unsafe != "0":
                raise RuntimeError("Unsafe runtime role attributes")
            technical_sql = ",".join("'" + role + "'" for role in technical)
            inherited = psql("SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member "
                             f"WHERE r.rolname IN ({technical_sql});").stdout.strip()
            if inherited != "0":
                raise RuntimeError("A technical login inherited another role")
            print("Runtime role attributes and technical membership isolation passed.")

            # Each portal can persist its own keys but cannot read another ring
            # or business data. An ordinary API login cannot access key material.
            for portal in ("api", "admin", "backoffice", "commerce", "tracking"):
                role = "nexoruta_keys_" + portal
                secret = hosting_passwords[f"KEYS_{portal.upper()}_PASSWORD"]
                psql(f'INSERT INTO {role}."DataProtectionKeys" ("FriendlyName", "Xml") '
                     "VALUES ('compat-key', '<key/>');", role, secret)
                found = psql(f'SELECT count(*) FROM {role}."DataProtectionKeys" '
                             'WHERE "FriendlyName"=\'compat-key\';', role, secret).stdout.strip()
                if found != "1":
                    raise RuntimeError("Portal key storage failed")
                other = "nexoruta_keys_admin" if portal == "api" else "nexoruta_keys_api"
                denied(f'SELECT "Xml" FROM {other}."DataProtectionKeys";', role, secret)
                denied('SELECT "Payload" FROM public."OutboxMessages";', role, secret)
                denied("CREATE ROLE compat_forbidden;", role, secret)
            denied('SELECT "Xml" FROM nexoruta_keys_api."DataProtectionKeys";',
                   "nexoruta_api_runtime", runtime_passwords["API"])
            print("Five key rings: own write/read allowed, cross-ring/business/role creation denied.")

            # Seed only this isolated test instance; no row-level bypass is ever
            # granted to a runtime login. Verify aggregate output over real rows.
            psql('INSERT INTO public."OutboxMessages" '
                 '("Id","Ambito","ClaveAmbito","Tipo","VersionContrato","Destino","Prioridad","Estado",'
                 '"Payload","Intentos","CreadoEnUtc","ProximoIntentoEnUtc") VALUES '
                 "(gen_random_uuid(),'Identidad',gen_random_uuid(),'PasswordRecoveryRequested',1,'Kafka','Normal','Pendiente',"
                 "'{\"secret\":\"must-not-be-visible\"}',0,now()-interval '5 minutes',now());",
                 "cloud_root", root_password)
            monitor_secret = hosting_passwords["MONITOR_DB_PASSWORD"]
            aggregate = psql("SELECT transport,state,messages,oldest_age_seconds>=250 "
                             "FROM nexoruta_hosting.outbox_metrics() WHERE transport='Kafka' AND state='Pendiente';",
                             "nexoruta_monitor_runtime", monitor_secret).stdout.strip()
            if aggregate != "Kafka|Pendiente|1|t":
                raise RuntimeError("Outbox aggregate omitted or exposed incorrect data")
            denied('SELECT "Payload" FROM public."OutboxMessages";', "nexoruta_monitor_runtime", monitor_secret)
            denied("SET ROLE nexoruta_monitor_fn;", "nexoruta_monitor_runtime", monitor_secret)
            denied("SELECT * FROM nexoruta_hosting.rate_limits;", "nexoruta_monitor_runtime", monitor_secret)
            print("Monitor aggregate sees seeded outbox; raw data/function-owner/counters denied.")

            # Start well inside one window so the twelve independent sessions
            # exercise the same quota. This wait is at most fifteen seconds.
            seconds = time.time() % 60
            if seconds > 45:
                time.sleep(60 - seconds + 0.1)
            key = secrets.token_hex(32)
            def take(_):
                return psql(f"SELECT nexoruta_hosting.take_rate_limit('{key}',5);",
                            "nexoruta_api_runtime", runtime_passwords["API"]).stdout.strip()
            with ThreadPoolExecutor(max_workers=12) as pool:
                result = list(pool.map(take, range(12)))
            if result.count("t") != 5 or result.count("f") != 7:
                raise RuntimeError("Shared atomic rate limit failed: expected 5 accepts / 7 rejects")
            denied("SELECT * FROM nexoruta_hosting.rate_limits;", "nexoruta_api_runtime", runtime_passwords["API"])
            denied("SELECT nexoruta_hosting.take_rate_limit('" + key + "',5);", "nexoruta_monitor_runtime", monitor_secret)
            print("Atomic shared quota: twelve concurrent connections, exactly five allowed / seven denied.")

            grafana_secret = hosting_passwords["GRAFANA_DB_PASSWORD"]
            psql("CREATE TABLE compat_grafana (id integer PRIMARY KEY); INSERT INTO compat_grafana VALUES (1);",
                 "nexoruta_grafana_runtime", grafana_secret, database="grafana")
            denied('SELECT "Payload" FROM public."OutboxMessages";', "nexoruta_grafana_runtime", grafana_secret)
            print("Grafana owns its database; business data remains inaccessible.")
        print("Managed PostgreSQL compatibility and hosting isolation checks passed.")
    finally:
        subprocess.run(["docker", "rm", "--force", name], capture_output=True)


if __name__ == "__main__":
    main()
