#!/usr/bin/env python3
"""Disposable Linux development runtime. Never reads workshop .env or restores a backup."""
import argparse, base64, json, os, pathlib, pwd, secrets, signal, socket, subprocess, time, urllib.request, uuid
ROOT = pathlib.Path(__file__).resolve().parents[2]
STATE = ROOT / ".local" / "codex-cloud"
LOCAL_HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
DOCKER = os.environ.get("NEXORUTA_CLOUD_POSTGRES_MODE") == "docker"
CONTAINER = os.environ.get("NEXORUTA_CLOUD_CONTAINER", "nexoruta-checkpoint-cloud")
IMAGE = "postgis/postgis:18-3.6-alpine"
PG = pathlib.Path("/usr/lib/postgresql/18/bin")

def run(args, **kw):
    return subprocess.run([str(a) for a in args], check=True, **kw)

def pg(args, **kw):
    if os.geteuid() == 0:
        args = ["runuser", "-u", "postgres", "--", *map(str, args)]
    return run(args, **kw)

def load():
    s = json.loads((STATE / "private.json").read_text())
    if s.get("purpose") != "nexoruta-disposable-cloud" or not s["database"].startswith("nexoruta_cloud_"):
        raise RuntimeError("Not an owned disposable database; no operation permitted")
    if "evidences" not in s:
        s["evidences"] = base64.b64encode(secrets.token_bytes(32)).decode()
        (STATE / "private.json").write_text(json.dumps(s)); (STATE / "private.json").chmod(0o600)
    if "webhookSigning" not in s:
        s["webhookSigning"] = "whsec_" + base64.b64encode(secrets.token_bytes(32)).decode()
        s["webhookAdmin"] = secrets.token_hex(24)
        (STATE / "private.json").write_text(json.dumps(s)); (STATE / "private.json").chmod(0o600)
    return s

def env(s, role="api"):
    conn = f"Host=127.0.0.1;Port={s['pgPort']};Database={s['database']};Username={s[role+'User']};Password={s[role+'Password']}"
    values = dict(os.environ, ASPNETCORE_ENVIRONMENT="Development", DOTNET_ENVIRONMENT="Development",
        ConnectionStrings__Postgres=conn, ConnectionStrings__RateLimits=conn,
        Jwt__SigningKeyBase64=s["jwt"], Seguimiento__EncryptionKey=s["tracking"], Reparto__EvidenciasEncryptionKey=s["evidences"],
        DatabaseInitialization__ApplyMigrations="false", DatabaseInitialization__SeedData="false",
        PlatformInitialization__Enabled="false", OpenTelemetry__Enabled="false",
        DataProtection__KeysDirectory=str(STATE / "keys"),
        Geocoding__MapboxTemporal__Habilitado="false", Mapbox__PublicAccessToken="",
        Geocoding__Geoapify__PermitirLlamadasReales="false", RoutingGeoapify__PermitirLlamadasReales="false",
        RoutingGeoapify__ApiKey="", Geocoding__Geoapify__ApiKey="",
        Api__BaseAddress="http://127.0.0.1:5000/", FleetTransition__StageOnly="false")
    if os.environ.get("NEXORUTA_CLOUD_WEBHOOK_DEMO") == "1":
        values.update(Tracking__BaseAddress="http://localhost:5103/", CommerceDemo__Enabled="true", CommerceDemo__AdminPassword=s["webhookAdmin"],
            CommerceDemo__SigningSecrets__0=s["webhookSigning"], CommerceDemo__DatabasePath=str(STATE / "receiver" / "inbox.db"),
            Webhooks__DevelopmentReceiverUrl="http://127.0.0.1:5103/comercio/webhook",
            Webhooks__MaxAttempts="3", Webhooks__RetryBaseSeconds="2", Webhooks__RetryMaxSeconds="10", Webhooks__TimeoutSeconds="3")
    return values

def psql(s, sql=None, file=None, database=None):
    args = [PG / "psql", "-X", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", str(s["pgPort"]), "-U", s["ownerUser"], "-d", database or s["database"]]
    if DOCKER:
        args = ["docker", "exec", "-i", "-e", "PGPASSWORD", "-e", "NEXORUTA_API_DB_PASSWORD", "-e", "NEXORUTA_WORKER_DB_PASSWORD", "-e", "NEXORUTA_BOOTSTRAP_DB_PASSWORD", CONTAINER,
                "psql", "-X", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-U", s["ownerUser"], "-d", database or s["database"]]
        if file: sql = pathlib.Path(file).read_text()
    elif file: args += ["-f", file]
    e = dict(os.environ, PGPASSWORD=s["ownerPassword"], NEXORUTA_API_DB_PASSWORD=s["apiPassword"],
        NEXORUTA_WORKER_DB_PASSWORD=s["workerPassword"], NEXORUTA_BOOTSTRAP_DB_PASSWORD=s["bootstrapPassword"])
    return run(args, env=e, input=sql, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

def provision_limits(s):
    hosting=(ROOT / "deploy/gcp/sql/hosting.sql").read_text()
    rate=hosting.split("-- BEGIN RATE LIMIT",1)[1].split("-- END RATE LIMIT",1)[0]
    # Reuse the existing hosting contract, without unrelated Grafana/monitor services.
    psql(s,"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='nexoruta_hosting_owner') THEN CREATE ROLE nexoruta_hosting_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS; END IF; END $$;"+rate)

def build():
    for project in ["backend/src/NexoRuta.Api", "frontend/src/NexoRuta.Backoffice", "frontend/src/NexoRuta.Commerce", "frontend/src/NexoRuta.Tracking"]:
        run(["dotnet", "build", ROOT / project, "--artifacts-path", STATE / "artifacts", "--nologo"], cwd=ROOT)
    if os.environ.get("NEXORUTA_CLOUD_WEBHOOK_DEMO") == "1":
        run(["dotnet", "build", ROOT / "backend/src/NexoRuta.Worker", "--artifacts-path", STATE / "artifacts", "--nologo"], cwd=ROOT)

def launch(s, name, project, port):
    pidfile = STATE / (name + ".pid")
    if pidfile.exists():
        pid = int(pidfile.read_text())
        try:
            os.kill(pid, 0)
            command = pathlib.Path(f"/proc/{pid}/cmdline").read_text()
            if not command: raise ProcessLookupError()
            if (STATE / (name+".identity")).read_text() not in command:
                raise RuntimeError("PID no longer belongs to this runtime")
            return
        except ProcessLookupError: pass
    dll = STATE / "artifacts" / "bin" / project / "debug" / (project + ".dll")
    e = env(s, "worker" if name == "webhooks" else "api"); e["ASPNETCORE_URLS"] = f"http://0.0.0.0:{port}"
    if name == "webhooks": e["Messaging__Transport"] = "HttpWebhooks"
    content = ROOT / ("backend" if name in ("api", "webhooks") else "frontend") / "src" / project
    with (STATE / (name + ".log")).open("ab") as log:
        process = subprocess.Popen(["dotnet", dll], cwd=content, env=e, stdout=log, stderr=log, start_new_session=True)
    pidfile.write_text(str(process.pid)); (STATE / (name+".identity")).write_text(str(dll))

def start():
    if os.name != "posix" or (not DOCKER and not PG.exists()): raise RuntimeError("Run install.sh in Linux first")
    STATE.mkdir(parents=True, exist_ok=True); STATE.chmod(0o711)
    fresh = not (STATE / "private.json").exists()
    if fresh:
        s = dict(purpose="nexoruta-disposable-cloud", database="nexoruta_cloud_"+secrets.token_hex(5), pgPort=15432,
            ownerUser="cloud_owner", apiUser="nexoruta_api_runtime", workerUser="nexoruta_worker_runtime", bootstrapUser="nexoruta_bootstrap_runtime",
            evidences=base64.b64encode(secrets.token_bytes(32)).decode(), jwt=base64.b64encode(secrets.token_bytes(32)).decode(), tracking=base64.b64encode(secrets.token_bytes(32)).decode(),
            operatorId=str(uuid.uuid4()), commerceId=str(uuid.uuid4()), operatorEmail="operator@cloud.example.test", commerceEmail="commerce@cloud.example.test", adminEmail="admin@cloud.example.test")
        for r in ["owner", "api", "worker", "bootstrap", "operator", "commerce", "admin"]: s[r+"Password"] = secrets.token_hex(24)
        with socket.socket() as probe: probe.bind(("127.0.0.1", s["pgPort"]))
        (STATE / "private.json").write_text(json.dumps(s)); (STATE / "private.json").chmod(0o600)
    s = load()
    if DOCKER:
        found = subprocess.run(["docker", "container", "inspect", CONTAINER], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if found.returncode:
            e = dict(os.environ, POSTGRES_USER=s["ownerUser"], POSTGRES_PASSWORD=s["ownerPassword"], POSTGRES_DB="postgres")
            run(["docker", "run", "-d", "--name", CONTAINER, "--label", "nexoruta.checkpoint="+s["database"],
                 "-e", "POSTGRES_USER", "-e", "POSTGRES_PASSWORD", "-e", "POSTGRES_DB",
                 "-p", f"127.0.0.1:{s['pgPort']}:5432", IMAGE], env=e, stdout=subprocess.DEVNULL)
            # Filesystem snapshots can retain the marker while Docker state is new.
            (STATE / "seeded").unlink(missing_ok=True)
        else:
            info=json.loads(found.stdout)[0]
            if info["Config"]["Labels"].get("nexoruta.checkpoint") != s["database"]:
                raise RuntimeError("Container does not belong to this synthetic database")
            run(["docker", "start", CONTAINER], stdout=subprocess.DEVNULL)
        for _ in range(60):
            ready=subprocess.run(["docker","exec",CONTAINER,"pg_isready","-h","127.0.0.1","-U",s["ownerUser"]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if ready.returncode == 0:
                try:
                    psql(s,"SELECT 1",database="postgres")
                    break
                except subprocess.CalledProcessError: pass
            time.sleep(1)
        else: raise RuntimeError("Owned Docker database did not become ready")
    else:
        pgdir = STATE / "postgres"; pgdir.mkdir(exist_ok=True); pgdir.chmod(0o700)
        if os.geteuid() == 0:
            user = pwd.getpwnam("postgres"); os.chown(pgdir, user.pw_uid, user.pw_gid)
        if not (pgdir / "data" / "PG_VERSION").exists():
            password = pgdir / "initial-password"; password.write_text(s["ownerPassword"]); password.chmod(0o600)
            if os.geteuid() == 0: os.chown(password, user.pw_uid, user.pw_gid)
            try: pg([PG / "initdb", "-D", pgdir / "data", "--username", s["ownerUser"], "--pwfile", password, "--auth-host=scram-sha-256", "--auth-local=trust"], stdout=subprocess.DEVNULL)
            finally: password.unlink()
        status = subprocess.run((["runuser", "-u", "postgres", "--"] if os.geteuid()==0 else [])+[str(PG / "pg_ctl"), "-D", str(pgdir / "data"), "status"], stdout=subprocess.DEVNULL)
        if status.returncode: pg([PG / "pg_ctl", "-D", pgdir / "data", "-l", pgdir / "server.log", "-o", f"-h 127.0.0.1 -p {s['pgPort']} -k {pgdir}", "-w", "start"])
    existing = psql(s, "SELECT datname FROM pg_database WHERE datname='"+s["database"]+"';", database="postgres")
    if s["database"] not in existing: psql(s, 'CREATE DATABASE "'+s["database"]+'";', database="postgres")
    # Never rebuild files mapped by a running web process. Stop this runtime first.
    for name in ["api", "backoffice", "commerce", "tracking", "webhooks"]:
        pidfile=STATE/(name+".pid")
        if pidfile.exists():
            pid=int(pidfile.read_text())
            if pathlib.Path(f"/proc/{pid}/cmdline").exists() and pathlib.Path(f"/proc/{pid}/cmdline").read_bytes():
                raise RuntimeError("Runtime already started; use stop before start/rebuild")
    build()
    dll = STATE / "artifacts/bin/NexoRuta.Api/debug/NexoRuta.Api.dll"
    # Explicit migration only on our generated, marker-checked synthetic database; never workshop services.
    run(["dotnet", dll, "database-migrate"], cwd=ROOT / "backend/src/NexoRuta.Api", env=env(s, "owner"))
    psql(s, file=ROOT / "backend/scripts/provision-rls-runtime-roles.sql")
    provision_limits(s)
    seeded = STATE / "seeded"
    if not seeded.exists():
        e=env(s,"bootstrap"); e.update(PlatformInitialization__Email=s["adminEmail"], PlatformInitialization__Password=s["adminPassword"],
            AccesoInicial__OperadorId=s["operatorId"], AccesoInicial__ComercioId=s["commerceId"],
            AccesoInicial__UsuarioEmail=s["commerceEmail"], AccesoInicial__UsuarioPassword=s["commercePassword"],
            AccesoInicial__OperadorUsuarioEmail=s["operatorEmail"], AccesoInicial__OperadorUsuarioPassword=s["operatorPassword"],
            AccesoInicial__OperadorNombre="Cloud synthetic operator", AccesoInicial__ComercioNombre="Cloud synthetic commerce",
            AccesoInicial__OperadorRolCodigo="administrador_operador", AccesoInicial__ComercioRolCodigo="propietario_comercio",
            Bootstrap__Roles__0__Codigo="administrador_operador", Bootstrap__Roles__0__Nombre="Cloud operator administrator", Bootstrap__Roles__0__OperadorId=s["operatorId"],
            Bootstrap__Roles__1__Codigo="propietario_comercio", Bootstrap__Roles__1__Nombre="Cloud commerce owner", Bootstrap__Roles__1__ComercioId=s["commerceId"])
        run(["dotnet", dll, "local-bootstrap"], cwd=ROOT / "backend/src/NexoRuta.Api", env=e); seeded.touch()
    for name,project,port in [("api","NexoRuta.Api",5000),("backoffice","NexoRuta.Backoffice",5101),("commerce","NexoRuta.Commerce",5102),("tracking","NexoRuta.Tracking",5103)]: launch(s,name,project,port)
    if os.environ.get("NEXORUTA_CLOUD_WEBHOOK_DEMO") == "1": launch(s,"webhooks","NexoRuta.Worker",0)
    for port in [5000,5101,5102,5103]:
        for _ in range(90):
            try:
                LOCAL_HTTP.open(f"http://127.0.0.1:{port}/health/ready",timeout=2);break
            except Exception: time.sleep(1)
        else: raise RuntimeError(f"Service {port} failed; inspect private logs in {STATE}")
    if os.environ.get("NEXORUTA_CLOUD_WEBHOOK_DEMO") == "1":
        pid=int((STATE/"webhooks.pid").read_text())
        command=pathlib.Path(f"/proc/{pid}/cmdline")
        if not command.exists() or not command.read_bytes(): raise RuntimeError("HTTP worker exited; inspect its private log")
    print("Synthetic Cloud runtime ready: API5000 Backoffice5101 Commerce5102 Tracking5103. Run verify next.")

def stop():
    s=load()
    for name in ["webhooks","tracking","commerce","backoffice","api"]:
        p=STATE/(name+".pid")
        if not p.exists(): continue
        pid=int(p.read_text())
        try:
            command = pathlib.Path(f"/proc/{pid}/cmdline").read_text()
            if not command: raise ProcessLookupError()
            if (STATE/(name+".identity")).read_text() not in command: raise RuntimeError("Refusing to stop an unrelated PID")
            os.killpg(pid,signal.SIGTERM)
            for _ in range(100):
                command_path=pathlib.Path(f"/proc/{pid}/cmdline")
                if not command_path.exists() or not command_path.read_bytes(): break
                time.sleep(0.1)
            else: raise RuntimeError("Owned process did not stop; refusing to rebuild loaded files")
        except (ProcessLookupError,FileNotFoundError): pass
        p.unlink()
    if DOCKER:
        label=run(["docker","inspect","-f",'{{index .Config.Labels "nexoruta.checkpoint"}}',CONTAINER],stdout=subprocess.PIPE,text=True).stdout.strip()
        if label != s["database"]: raise RuntimeError("Refusing to stop unrelated container")
        run(["docker","stop",CONTAINER],stdout=subprocess.DEVNULL)
    else:
        pg([PG/"pg_ctl","-D",STATE/"postgres/data","-w","stop"])
    print("Owned Cloud runtime stopped; data retained")

def verify():
    s=load()
    def http(path,data=None,token=None):
        headers={"Content-Type":"application/json"}
        if token:headers["Authorization"]="Bearer "+token
        req=urllib.request.Request("http://127.0.0.1:5000/"+path,data=None if data is None else json.dumps(data).encode(),headers=headers)
        with LOCAL_HTTP.open(req) as r:return json.load(r)
    token=http("api/auth/login",dict(email=s["operatorEmail"],password=s["operatorPassword"]))["accessToken"]
    for path in ["api/envios","api/reparto/flota","api/reparto/perfiles-viales"]: http(path,token=token);print(path,"200 authenticated")
    checks=psql(s,"SELECT rolname,rolsuper,rolbypassrls FROM pg_roles WHERE rolname='nexoruta_api_runtime'; SELECT postgis_full_version(); SELECT count(*) FROM public.\"__EFMigrationsHistory\";")
    safe=psql(s,"SELECT CASE WHEN NOT rolsuper AND NOT rolbypassrls AND NOT rolcreatedb AND NOT rolcreaterole THEN 'cloud_role_safe' ELSE 'unsafe' END FROM pg_roles WHERE rolname='nexoruta_api_runtime';")
    if "cloud_role_safe" not in safe or "unsafe" in safe:raise RuntimeError("Unsafe or missing runtime RLS login")
    activity=psql(s,"SELECT count(*) FROM pg_stat_activity WHERE datname='"+s["database"]+"' AND usename='nexoruta_api_runtime';")
    count=int(activity.splitlines()[2].strip())
    if count < 1: raise RuntimeError("API runtime connection not observed")
    rls=psql(s,"SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relrowsecurity AND relforcerowsecurity;")
    if int(rls.splitlines()[2].strip()) < 1: raise RuntimeError("Forced RLS not observed")
    if os.environ.get("NEXORUTA_CLOUD_WEBHOOK_DEMO") == "1":
        response=LOCAL_HTTP.open("http://127.0.0.1:5103/comercio")
        if urllib.parse.urlsplit(response.url).path != "/comercio/ingresar": raise RuntimeError("Demo receiver must require its controls login")
        commerce=http("api/auth/login",dict(email=s["commerceEmail"],password=s["commercePassword"]))["accessToken"]
        http("api/webhooks/suscripciones",token=commerce)
        print("HTTP webhook API and protected /comercio verified")
    print("API connections use restricted runtime role; forced RLS tables verified")
    print("PostgreSQL/PostGIS and runtime RLS role verified; credentials remain in ignored private.json")
    print(checks)

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("command",choices=["start","verify","stop"])
    globals()[parser.parse_args().command]()
