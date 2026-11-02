"""Authorized local workshop-data activation. Explicit phases, no unbounded migrator, secrets never printed."""
import argparse,base64,hashlib,json,os,pathlib,secrets,subprocess,sys,time,urllib.request,urllib.error
import transition as t
P=pathlib.Path
W=P((P(os.environ['TEMP'])/'cu06-local-activation-path.txt').read_text()).resolve()
V=dict(line.split('=',1) for line in P('.env').read_text(encoding='utf-8-sig').splitlines() if '=' in line and not line.startswith('#'))
V={k:v.strip().strip('"').strip("'") for k,v in V.items()}
EMAIL='cu06.operaciones.taller@example.test';PASSWORD=V['NEXORUTA_OPERADOR_PASSWORD']
LOG=W/'requests-private.json';requests=json.loads(LOG.read_text()) if LOG.exists() else []
def save(name,data):t.save(W,name,data)
def sql(text):return t.source_sql(text)
def history():return sql('SELECT "MigrationId" FROM "__EFMigrationsHistory" ORDER BY "MigrationId";').splitlines()
def request(base,method,path,data=None,token=None,expected=(200,)):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,method=method,headers=headers,data=json.dumps(data).encode() if data is not None else None)
 try:
  with urllib.request.urlopen(req,timeout=30) as response:status=response.status;body=response.read()
 except urllib.error.HTTPError as e:status=e.code;body=e.read()
 row={'method':method,'path':path,'status':status,'syntheticWorkshopData':True}
 if data and 'comandoId' in data:row['commandId']=data['comandoId']
 requests.append(row);save(LOG.name,requests)
 if status not in expected:
  (W/'last-http-failure-private.log').write_bytes(body);raise RuntimeError(f'{method} {path}: HTTP{status}; protected details retained')
 return json.loads(body) if body else None

def login(base,email=EMAIL,password=PASSWORD):return request(base,'POST','/api/auth/login',{'email':email,'password':password})['accessToken']
def apply(step):
 previous={'stage':t.BASE,'enforce':t.STAGE,'b3':t.ENFORCE,'b4':t.B3};target={'stage':t.STAGE,'enforce':t.ENFORCE,'b3':t.B3,'b4':t.B4}
 if history()[-1]!=previous[step]:raise RuntimeError('Unexpected local schema; refusing migration')
 path=P('docs/auditorias/cu06/evidencias/transicion/sql')/(step+'.sql');manifest=json.loads(P('docs/auditorias/cu06/evidencias/transicion/provenance.json').read_text())
 if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['sqlSha256'][step]:raise RuntimeError('SQL checksum mismatch')
 r=subprocess.run(['docker','exec','-i','nexoruta-postgres','sh','-c','exec psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'],input=path.read_bytes(),capture_output=True)
 (W/(step+'-local-apply.log')).write_bytes(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError('Migration refused; protected log retained')
 if history()[-1]!=target[step]:raise RuntimeError('Migration result differs from requested stage')
 print('Applied exactly',target[step])
def prepare():
 if history()[-1]!=t.BASE:raise RuntimeError('Access preparation is baseline-only; no service was changed')
 base='http://127.0.0.1:5000';subprocess.run(['docker','start','nexoruta-api'],check=True,capture_output=True)
 try:
  for i in range(100):
   try:
    with urllib.request.urlopen(base+'/health/live',timeout=1) as r:
     if r.status==200:break
   except OSError:time.sleep(.2)
  token=login(base,V['NEXORUTA_OPERADOR_MAIL']);role=(W/'role-id.txt').read_text().strip()
  users=request(base,'GET','/api/usuarios',token=token)
  if not any(u['email']==EMAIL for u in users):request(base,'POST','/api/usuarios',{'email':EMAIL,'password':PASSWORD,'rolId':role},token,expected=(201,))
  roles=request(base,'GET','/api/roles',token=token);denied=next((r for r in roles if r['codigo']=='cu06_sin_permisos'),None)
  if denied is None:denied=request(base,'POST','/api/roles',{'codigo':'cu06_sin_permisos','nombre':'Prueba CU06 sin permisos'},token,expected=(201,))
  deniedid=denied.get('id');deniedemail='cu06.sin-permisos.taller@example.test'
  if not any(u['email']==deniedemail for u in users):request(base,'POST','/api/usuarios',{'email':deniedemail,'password':PASSWORD,'rolId':deniedid},token,expected=(201,))
  save('configured-access.json',{'email':EMAIL,'roleId':role,'roleCode':'administrador_operador','negativeEmail':deniedemail,'passwordSource':'existing local operator .env value; not printed','synthetic':True})
  print('Local workshop authorized and no-permission accounts created using existing user API.')
 finally:subprocess.run(['docker','stop','nexoruta-api'],capture_output=True,check=True)
def stage():
 if history()[-1]!=t.STAGE:raise RuntimeError('Stage required')
 sql('GRANT SELECT ON public."__EFMigrationsHistory" TO nexoruta_api;')
 artifact=P(os.environ['LOCALAPPDATA'])/'NexoRuta/cu06-transition/c83b359a6bfe/api';env=os.environ.copy()
 env.update({'ASPNETCORE_URLS':'http://127.0.0.1:5189','ASPNETCORE_ENVIRONMENT':'Development','ConnectionStrings__Postgres':'Host=127.0.0.1;Port=55433;Database=nexoruta;Username=nexoruta_api_runtime;Password='+V['NEXORUTA_API_DB_PASSWORD'],'Jwt__SigningKeyBase64':base64.b64encode(secrets.token_bytes(32)).decode(),'FleetTransition__StageOnly':'true','DatabaseInitialization__ApplyMigrations':'false','DatabaseInitialization__SeedData':'false','PlatformInitialization__Enabled':'false','RoutingGeoapify__PermitirLlamadasReales':'false','RoutingGeoapify__ApiKey':'','OpenTelemetry__Enabled':'false','DataProtection__KeysDirectory':str(W/'stage-keys'),'Logging__LogLevel__Default':'Warning'})
 with (W/'stage-local-host.log').open('wb') as log:
  child=subprocess.Popen(['dotnet',str(artifact/'NexoRuta.Api.dll')],cwd=artifact,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   base='http://127.0.0.1:5189'
   for i in range(150):
    try:
     with urllib.request.urlopen(base+'/health/live',timeout=1) as r:
      if r.status==200:break
    except OSError:time.sleep(.2)
    if child.poll() is not None:raise RuntimeError('Stage host exited; protected log retained')
   token=login(base);fleet=request(base,'GET','/api/reparto/flota',token=token);save('fleet-before-synthetic.json',fleet)
   for vehicle in fleet:
    for occupation in vehicle['ocupaciones']:
     action='anular' if occupation['estadoRuta']=='Despachada' else None
     if action:
      if not occupation['puedeAnular']:raise RuntimeError('Legacy dispatch is not eligible for cancellation; no history bypass')
      command={'comandoId':str(__import__('uuid').uuid4()),'ocupacionId':occupation['id'],'version':occupation['version'],'motivo':'Regularización SINTÉTICA autorizada CU06: datos ficticios del taller; autorización nunca iniciada ni cargada. No acredita hechos reales.'}
      receipt=request(base,'POST','/api/reparto/flota/'+vehicle['id']+'/'+action,command,token);save('receipt-'+command['comandoId']+'.json',receipt)
   fleet=request(base,'GET','/api/reparto/flota',token=token)
   for vehicle in fleet:
    for occupation in vehicle['ocupaciones']:
     if occupation['legada'] and occupation['adquiridaEnUtc'] is None:
      command={'comandoId':str(__import__('uuid').uuid4()),'ocupacionId':occupation['id'],'version':occupation['version'],'motivo':'Regularización SINTÉTICA autorizada CU06: conservar como vigente la jornada de prueba iniciada, sin acreditar retorno ni descarga real.'}
      receipt=request(base,'POST','/api/reparto/flota/'+vehicle['id']+'/conciliar',command,token);save('receipt-'+command['comandoId']+'.json',receipt)
   save('fleet-after-synthetic.json',request(base,'GET','/api/reparto/flota',token=token))
   print('Legacy synthetic regularization completed with existing commands and receipts.')
  finally:child.terminate();child.wait(timeout=15)
 sql('REVOKE SELECT ON public."__EFMigrationsHistory" FROM nexoruta_api;')
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare-access','apply','stage']);parser.add_argument('--step',choices=['stage','enforce','b3','b4']);a=parser.parse_args()
 if a.action=='prepare-access':prepare()
 elif a.action=='apply':apply(a.step)
 elif a.action=='stage':stage()
