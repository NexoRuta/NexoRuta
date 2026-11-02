#!/usr/bin/env python3
"""Disposable Linux development runtime. Never reads workshop .env or restores a backup."""
import argparse, base64, json, os, pathlib, pwd, secrets, signal, socket, subprocess, time, urllib.request, uuid
ROOT = pathlib.Path(__file__).resolve().parents[2]
STATE = ROOT / ".local" / "codex-cloud"
LOCAL_HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
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
    return s

def env(s, role="api"):
    conn = f"Host=127.0.0.1;Port={s['pgPort']};Database={s['database']};Username={s[role+'User']};Password={s[role+'Password']}"
    return dict(os.environ, ASPNETCORE_ENVIRONMENT="Development", DOTNET_ENVIRONMENT="Development",
        ConnectionStrings__Postgres=conn, ConnectionStrings__RateLimits=conn,
        Jwt__SigningKeyBase64=s["jwt"], Seguimiento__EncryptionKey=s["tracking"],
        DatabaseInitialization__ApplyMigrations="false", DatabaseInitialization__SeedData="false",
        PlatformInitialization__Enabled="false", OpenTelemetry__Enabled="false",
        DataProtection__KeysDirectory=str(STATE / "keys"),
        Geocoding__MapboxTemporal__Habilitado="false", Mapbox__PublicAccessToken="",
        Geocoding__Geoapify__PermitirLlamadasReales="false", RoutingGeoapify__PermitirLlamadasReales="false",
        RoutingGeoapify__ApiKey="", Geocoding__Geoapify__ApiKey="",
        Api__BaseAddress="http://127.0.0.1:5000/", FleetTransition__StageOnly="false")

def psql(s, sql=None, file=None, database=None):
    args = [PG / "psql", "-X", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", str(s["pgPort"]), "-U", s["ownerUser"], "-d", database or s["database"]]
    if file: args += ["-f", file]
    e = dict(os.environ, PGPASSWORD=s["ownerPassword"], NEXORUTA_API_DB_PASSWORD=s["apiPassword"],
        NEXORUTA_WORKER_DB_PASSWORD=s["workerPassword"], NEXORUTA_BOOTSTRAP_DB_PASSWORD=s["bootstrapPassword"])
    return run(args, env=e, input=sql, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

def provision_limits(s):
    hosting=(ROOT / "deploy/gcp/sql/hosting.sql").read_text()
    rate=hosting.split("-- BEGIN RATE LIMIT",1)[1].split("-- END RATE LIMIT",1)[0]
    # Reuse the existing hosting contract, without unrelated Grafana/monitor services.
    psql(s,"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='nexoruta_hosting_owner') THEN CREATE ROLE nexoruta_hosting_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS; END IF; END $$;"+rate)

def build():
    for project in ["backend/src/NexoRuta.Api", "frontend/src/NexoRuta.Backoffice", "frontend/src/NexoRuta.Commerce"]:
        run(["dotnet", "build", ROOT / project, "--artifacts-path", STATE / "artifacts", "--nologo"], cwd=ROOT)

def launch(s, name, project, port):
    pidfile = STATE / (name + ".pid")
    if pidfile.exists():
        pid = int(pidfile.read_text())
        try:
            os.kill(pid, 0)
            if (STATE / (name+".identity")).read_text() not in pathlib.Path(f"/proc/{pid}/cmdline").read_text():
                raise RuntimeError("PID no longer belongs to this runtime")
            return
        except ProcessLookupError: pass
    dll = STATE / "artifacts" / "bin" / project / "debug" / (project + ".dll")
    e = env(s); e["ASPNETCORE_URLS"] = f"http://0.0.0.0:{port}"
    content = ROOT / ("backend" if name == "api" else "frontend") / "src" / project
    with (STATE / (name + ".log")).open("ab") as log:
        process = subprocess.Popen(["dotnet", dll], cwd=content, env=e, stdout=log, stderr=log, start_new_session=True)
    pidfile.write_text(str(process.pid)); (STATE / (name+".identity")).write_text(str(dll))

def start():
    if os.name != "posix" or not PG.exists(): raise RuntimeError("Run install.sh in Linux first")
    STATE.mkdir(parents=True, exist_ok=True); STATE.chmod(0o711)
    fresh = not (STATE / "private.json").exists()
    if fresh:
        s = dict(purpose="nexoruta-disposable-cloud", database="nexoruta_cloud_"+secrets.token_hex(5), pgPort=15432,
            ownerUser="cloud_owner", apiUser="nexoruta_api_runtime", workerUser="nexoruta_worker_runtime", bootstrapUser="nexoruta_bootstrap_runtime",
            jwt=base64.b64encode(secrets.token_bytes(32)).decode(), tracking=base64.b64encode(secrets.token_bytes(32)).decode(),
            operatorId=str(uuid.uuid4()), commerceId=str(uuid.uuid4()), operatorEmail="operator@cloud.example.test", commerceEmail="commerce@cloud.example.test", adminEmail="admin@cloud.example.test")
        for r in ["owner", "api", "worker", "bootstrap", "operator", "commerce", "admin"]: s[r+"Password"] = secrets.token_hex(24)
        with socket.socket() as probe: probe.bind(("127.0.0.1", s["pgPort"]))
        (STATE / "private.json").write_text(json.dumps(s)); (STATE / "private.json").chmod(0o600)
    else: s = load()
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
    for name in ["api", "backoffice", "commerce"]:
        pidfile=STATE/(name+".pid")
        if pidfile.exists():
            pid=int(pidfile.read_text())
            if pathlib.Path(f"/proc/{pid}/cmdline").exists():
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
    for name,project,port in [("api","NexoRuta.Api",5000),("backoffice","NexoRuta.Backoffice",5101),("commerce","NexoRuta.Commerce",5102)]: launch(s,name,project,port)
    for port in [5000,5101,5102]:
        for _ in range(90):
            try:
                LOCAL_HTTP.open(f"http://127.0.0.1:{port}/health/ready",timeout=2);break
            except Exception: time.sleep(1)
        else: raise RuntimeError(f"Service {port} failed; inspect private logs in {STATE}")
    print("Synthetic Cloud runtime ready: API5000 Backoffice5101 Commerce5102. Run verify next.")

def stop():
    load()
    for name in ["commerce","backoffice","api"]:
        p=STATE/(name+".pid")
        if not p.exists(): continue
        pid=int(p.read_text())
        try:
            if (STATE/(name+".identity")).read_text() not in pathlib.Path(f"/proc/{pid}/cmdline").read_text(): raise RuntimeError("Refusing to stop an unrelated PID")
            os.killpg(pid,signal.SIGTERM)
        except (ProcessLookupError,FileNotFoundError): pass
        p.unlink()
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
    print("PostgreSQL/PostGIS and runtime RLS role verified; credentials remain in ignored private.json")
    print(checks)

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("command",choices=["start","verify","stop"])
    globals()[parser.parse_args().command]()
