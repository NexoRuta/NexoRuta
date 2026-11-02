"""CU06 rehearsal only: source backup is read-only; every restore/apply targets a labelled private clone."""
import argparse,datetime,hashlib,json,os,pathlib,secrets,subprocess,sys,uuid
P=pathlib.Path
WORK_CONTEXT=None
BASE="20261030120000_ListImportedShipmentReferences"
STAGE="20261101184716_StageFleetOccupations"
ENFORCE="20261101185119_EnforceFleetOccupationExclusivity"
B3="20261101203256_AddOperationalBaseAndTemporalPlan"
B4="20261101213104_AddRoadEstimationHistory"
def run(args,**kw):
    r=subprocess.run(args,capture_output=True,**kw)
    if r.returncode:
        if WORK_CONTEXT is not None:(WORK_CONTEXT/("command-failure-"+uuid.uuid4().hex[:8]+".log")).write_bytes(r.stdout+r.stderr)
        raise RuntimeError("Command failed: "+args[0]+" (protected details retained, no secrets printed)")
    return r.stdout

def save(w,name,data):
    (w/name).write_text(json.dumps(data,indent=2),encoding="utf-8")
def meta(w):return json.loads((w/"private.json").read_text(encoding="utf-8"))
def inspect(name):return json.loads(run(["docker","inspect",name]))[0]
def protect(src,dst,decrypt=False):
    env=os.environ.copy();env["NR_IN"]=str(src);env["NR_OUT"]=str(dst)
    operation="Unprotect" if decrypt else "Protect"
    script="Add-Type -AssemblyName System.Security; $b=[IO.File]::ReadAllBytes($env:NR_IN); $v=[Security.Cryptography.ProtectedData]::"+operation+"($b,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser); [IO.File]::WriteAllBytes($env:NR_OUT,$v)"
    run(["powershell.exe","-NoProfile","-NonInteractive","-Command",script],env=env)
def seal(w,name):
    src=w/name;dst=w/(name+".dpapi");digest=hashlib.sha256(src.read_bytes()).hexdigest();protect(src,dst)
    check=w/(name+".verify");protect(dst,check,True);assert hashlib.sha256(check.read_bytes()).hexdigest()==digest
    check.unlink();src.unlink();return {"plaintextSha256":digest,"encryptedSha256":hashlib.sha256(dst.read_bytes()).hexdigest(),"bytes":dst.stat().st_size}
def clone(w):
    m=meta(w);d=inspect(m["clone"])
    if d["Config"]["Labels"].get("nexoruta.cu06.rehearsal")!=m["runId"]:raise RuntimeError("Refusing a non-owned rehearsal target")
    if d["Id"]!=m["cloneId"]:raise RuntimeError("Clone identity mismatch")
    return m

def sql(w,text,db=None):
    m=clone(w);return run(["docker","exec","-i",m["clone"],"psql","-X","-v","ON_ERROR_STOP=1","-U",m["admin"],"-d",db or m["database"],"-tA"],input=text.encode()).decode().strip()
def source_sql(text):
    return run(["docker","exec","-i","nexoruta-postgres","sh","-c",'exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA'],input=text.encode()).decode().strip()
def history(w,db=None):return sql(w,'SELECT "MigrationId" FROM "__EFMigrationsHistory" ORDER BY "MigrationId";',db).splitlines()
def backup(expected=BASE):
    rid=uuid.uuid4().hex[:12];w=P(os.environ["LOCALAPPDATA"])/"NexoRuta"/"cu06-transition"/rid;w.mkdir(parents=True,exist_ok=False)
    account=os.environ["USERDOMAIN"]+"\\"+os.environ["USERNAME"]
    run(["icacls",str(w),"/inheritance:r","/grant:r",account+":(OI)(CI)F","*S-1-5-18:(OI)(CI)F"])
    d=inspect("nexoruta-postgres");source_db=source_sql("SELECT current_database();");h=source_sql('SELECT "MigrationId" FROM "__EFMigrationsHistory" ORDER BY "MigrationId";').splitlines()
    if h[-1]!=expected:raise RuntimeError("Source schema differs from the explicit backup stage; stop and review")
    with (w/"baseline.dump").open("wb") as f:
        r=subprocess.run(["docker","exec","nexoruta-postgres","sh","-c",'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --create'],stdout=f,stderr=subprocess.PIPE)
        if r.returncode:raise RuntimeError("pg_dump failed")
    (w/"roles.sql").write_bytes(run(["docker","exec","nexoruta-postgres","sh","-c",'exec pg_dumpall -U "$POSTGRES_USER" --globals-only --no-role-passwords']))
    # The local environment snapshot is encrypted, never exported into the repository.
    (w/"local.env").write_bytes(P(".env").read_bytes())
    manifests={name:seal(w,name) for name in ["baseline.dump","roles.sql","local.env"]}
    save(w,"private.json",{"runId":rid,"sourceContainerId":d["Id"],"sourceImage":d["Image"],"database":source_db,"sourceHistory":h,"snapshotUtc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"backups":manifests})
    print(str(w));return w

def restore(w):
    m=meta(w)
    if not m.get("cloneId"):
        name="nexoruta-cu06-rehearsal-"+m["runId"];admin="rehearsal_"+m["runId"];password=secrets.token_hex(32)
        env=w/"clone.env";env.write_text("POSTGRES_USER="+admin+"\nPOSTGRES_PASSWORD="+password+"\nPOSTGRES_DB=postgres\n",encoding="utf-8")
        network="cu06-private-"+m["runId"];run(["docker","network","create","--label","nexoruta.cu06.rehearsal="+m["runId"],network])
        cid=run(["docker","run","-d","--name",name,"--network",network,"--label","nexoruta.cu06.rehearsal="+m["runId"],"--env-file",str(env),"-p","127.0.0.1::5432","--tmpfs","/var/lib/postgresql:rw,size=1073741824",m["sourceImage"]]).decode().strip()
        m.update(clone=name,cloneId=cid,admin=admin,network=network);save(w,"private.json",m)
    else:
        clone(w);name=m["clone"];admin=m["admin"]
        env_values=dict(x.split("=",1) for x in (w/"clone.env").read_text(encoding="utf-8").splitlines())
        password=env_values["POSTGRES_PASSWORD"]
    import time
    for i in range(100):
        r=subprocess.run(["docker","exec",name,"pg_isready","-h","127.0.0.1","-U",admin],capture_output=True)
        if r.returncode==0:break
        time.sleep(.2)
    else:raise RuntimeError("Owned clone not ready")
    roles=w/"roles.restore";dump=w/"baseline.restore";protect(w/"roles.sql.dpapi",roles,True);protect(w/"baseline.dump.dpapi",dump,True)
    try:
        if sql(w,"SELECT count(*) FROM pg_roles WHERE rolname='nexoruta_schema_owner';",db="postgres")=="0":
            run(["docker","exec","-i",name,"psql","-X","-v","ON_ERROR_STOP=1","-U",admin,"-d","postgres"],input=roles.read_bytes().replace(b" GRANTED BY nexoruta;",b";"))
        databases=sql(w,"SELECT datname FROM pg_database;",db="postgres").splitlines()
        if m["database"] not in databases:
            run(["docker","exec","-i",name,"pg_restore","--exit-on-error","--create","-U",admin,"-d","postgres"],input=dump.read_bytes())
        else:assert history(w)==m["sourceHistory"],"Partial/different restore must be inspected, not overwritten"
        if "cu06_restorecheck" not in databases:
            sql(w,"CREATE DATABASE cu06_restorecheck;",db="postgres")
            run(["docker","exec","-i",name,"pg_restore","--exit-on-error","-U",admin,"-d","cu06_restorecheck"],input=dump.read_bytes())
        assert history(w)==m["sourceHistory"] and history(w,"cu06_restorecheck")==m["sourceHistory"]
    finally:roles.unlink();dump.unlink()
    # Clone credentials are new, not borrowed from the habitual instance.
    api_password=secrets.token_hex(32);sql(w,"ALTER ROLE nexoruta_api LOGIN PASSWORD '"+api_password+"';")
    port=inspect(name)["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostPort"]
    m.update(port=int(port),apiConnection=f"Host=127.0.0.1;Port={port};Database={m['database']};Username=nexoruta_api;Password={api_password};Pooling=false",adminConnection=f"Host=127.0.0.1;Port={port};Database={m['database']};Username={admin};Password={password};Pooling=false")
    save(w,"private.json",m);seal(w,"clone.env");print("Restored owned clone; two restores and migration histories verified")

def fingerprints(w,db=None,columns=None):
    if columns is None:
        columns=json.loads(sql(w,"SELECT coalesce(jsonb_object_agg(t.name,t.cols),'{}'::jsonb) FROM (SELECT c.table_name name,jsonb_agg(c.column_name ORDER BY c.ordinal_position) cols FROM information_schema.columns c JOIN information_schema.tables t ON t.table_schema=c.table_schema AND t.table_name=c.table_name WHERE c.table_schema='public' AND t.table_type='BASE TABLE' GROUP BY c.table_name) t;",db))
    def q(x):return '"'+x.replace('"','""')+'"'
    queries=[]
    for table,cols in columns.items():
        queries.append("SELECT '"+table.replace("'","''")+"' name,jsonb_build_object('count',count(*),'sha',md5(coalesce(string_agg(md5(to_jsonb(x)::text),'' ORDER BY md5(to_jsonb(x)::text)),''))) value FROM (SELECT "+','.join(map(q,cols))+" FROM public."+q(table)+") x")
    data=json.loads(sql(w,"SELECT jsonb_object_agg(name,value) FROM ("+" UNION ALL ".join(queries)+") all_tables;",db))
    return columns,data

def checkpoint(w,name):
    if not name.replace('-','').isalnum():raise RuntimeError("Invalid checkpoint name")
    m=clone(w);f=w/(name+".dump")
    with f.open("wb") as out:
        r=subprocess.run(["docker","exec",m["clone"],"pg_dump","-U",m["admin"],"-d",m["database"],"-Fc","--create"],stdout=out,stderr=subprocess.PIPE)
        if r.returncode:raise RuntimeError("Checkpoint failed")
    result=seal(w,f.name);cols,data=fingerprints(w);save(w,name+".checkpoint.json",{"history":history(w),"dump":result,"columns":cols,"data":data,"schemaSha256":schema_hash(w)});print("Checkpoint "+name+" encrypted")

def verify_checkpoint(w,name):
    if not name or not name.replace('-','').isalnum():raise RuntimeError("Invalid checkpoint name")
    m=clone(w);target="cu06_recovery_"+name.replace('-','_')
    existing=sql(w,"SELECT datname FROM pg_database;",db="postgres").splitlines()
    if target in existing:raise RuntimeError("Recovery target already exists; never overwrite a previous recovery")
    source=w/(name+".restore");protect(w/(name+".dump.dpapi"),source,True)
    try:
        sql(w,"CREATE DATABASE "+target+";",db="postgres")
        run(["docker","exec","-i",m["clone"],"pg_restore","--exit-on-error","-U",m["admin"],"-d",target],input=source.read_bytes())
    finally:source.unlink()
    expected=json.loads((w/(name+".checkpoint.json")).read_text())
    if history(w,target)!=expected["history"]:raise RuntimeError("Recovered checkpoint history mismatch")
    _,actual=fingerprints(w,target,expected["columns"])
    if actual!=expected["data"]:raise RuntimeError("Recovered checkpoint data mismatch")
    if schema_hash(w,target)!=expected["schemaSha256"]:raise RuntimeError("Recovered checkpoint schema/owners/ACL/RLS mismatch")
    print("Recovered "+name+" into separate "+target+"; history, data and schema/owners/ACL/RLS match")

def schema_hash(w,db=None):
    m=clone(w);raw=run(["docker","exec",m["clone"],"pg_dump","--schema-only","--no-comments","-U",m["admin"],"-d",db or m["database"]]).decode()
    # PostgreSQL emits a fresh client-side restrict nonce for every dump; it is not schema data.
    normalized="\n".join(l for l in raw.splitlines() if not l.startswith(('\\restrict ','\\unrestrict ')))
    return hashlib.sha256(normalized.encode()).hexdigest()

def apply(w,step):
    previous={"stage":BASE,"enforce":STAGE,"b3":ENFORCE,"b4":B3};target={"stage":STAGE,"enforce":ENFORCE,"b3":B3,"b4":B4}
    if history(w)[-1]!=previous[step]:raise RuntimeError("Unexpected stage; refusing unbounded or replayed migration")
    text=(w/"sql"/(step+".sql")).read_bytes();m=clone(w)
    r=subprocess.run(["docker","exec","-i",m["clone"],"psql","-X","-v","ON_ERROR_STOP=1","-U",m["admin"],"-d",m["database"]],input=text,capture_output=True)
    (w/(step+".apply.log")).write_bytes(r.stdout+r.stderr)
    if r.returncode:print("Stage "+step+" refused; no bypass. Protected log retained.");return 2
    assert history(w)[-1]==target[step];print("Applied exactly "+target[step]);return 0

def main():
    global WORK_CONTEXT
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("action",choices=["backup","restore","verify-restore","checkpoint","apply","inspect","verify-checkpoint"]);p.add_argument("--work",type=P);p.add_argument("--step",choices=["stage","enforce","b3","b4"]);p.add_argument("--name");p.add_argument("--expected-migration",choices=[BASE,STAGE,ENFORCE,B3,B4],default=BASE);a=p.parse_args()
    if a.action=="backup":backup(a.expected_migration);return 0
    if a.work is None:p.error("--work is required")
    w=a.work.resolve();WORK_CONTEXT=w
    if a.action=="restore":restore(w)
    elif a.action=="verify-restore":
        cols,first=fingerprints(w);_,second=fingerprints(w,"cu06_restorecheck",cols);assert first==second;save(w,"baseline-fingerprints.json",{"columns":cols,"data":first});print("Two independent restores match all "+str(len(first))+" physical table fingerprints")
    elif a.action=="apply":
        if not a.step:p.error("--step is required")
        return apply(w,a.step)
    elif a.action=="verify-checkpoint":
        verify_checkpoint(w,a.name)
    elif a.action=="checkpoint":
        if not a.name:p.error("--name is required")
        checkpoint(w,a.name)
    elif a.action=="inspect":print(json.dumps({"migration":history(w)[-1],"activeLegacy":sql(w,'SELECT count(*) FROM "HojasRuta" WHERE "Estado" IN (\'Despachada\',\'EnCurso\');')}))
    return 0
if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:print(type(e).__name__+": "+str(e),file=sys.stderr);sys.exit(1)
