"""Read-only probes of the published Stage artifact against the owned restored copy. No physical confirmations."""
import argparse,base64,json,os,pathlib,secrets,socket,subprocess,time,urllib.request,urllib.error
import transition as t
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',required=True,type=pathlib.Path);a=p.parse_args();w=a.work.resolve();m=t.clone(w);assert t.history(w)[-1]==t.STAGE
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
url='http://127.0.0.1:'+str(port());env=os.environ.copy()
for k in list(env):
 if k.startswith(('ConnectionStrings__','Jwt__','RoutingGeoapify__')):del env[k]
env.update({'ASPNETCORE_URLS':url,'ASPNETCORE_ENVIRONMENT':'Development','ConnectionStrings__Postgres':m['apiConnection'],'Jwt__SigningKeyBase64':base64.b64encode(secrets.token_bytes(32)).decode(),'FleetTransition__StageOnly':'true','DatabaseInitialization__ApplyMigrations':'false','DatabaseInitialization__SeedData':'false','PlatformInitialization__Enabled':'false','RoutingGeoapify__PermitirLlamadasReales':'false','RoutingGeoapify__ApiKey':'','OpenTelemetry__Enabled':'false','DataProtection__KeysDirectory':str(w/'stage-keys'),'Logging__LogLevel__Default':'Warning'})
report={'artifact':'api/NexoRuta.Api.dll','schema':t.STAGE,'source':'restored local backup; no physical commands','queries':[]}
def req(path,data=None,token=None):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 r=urllib.request.Request(url+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
 try:
  with urllib.request.urlopen(r,timeout=15) as response:status=response.status;body=response.read()
 except urllib.error.HTTPError as e:status=e.code;body=e.read()
 report['queries'].append({'method':'POST' if data is not None else 'GET','path':path,'status':status});return status,body
with (w/'stage-host.log').open('wb') as log:
 process=subprocess.Popen(['dotnet',str(w/'api/NexoRuta.Api.dll')],cwd=w/'api',env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 try:
  for i in range(150):
   try:
    if req('/health/live')[0]==200:break
   except OSError:pass
   if process.poll() is not None:raise RuntimeError('Stage host failed; protected stage-host.log contains diagnostics')
   time.sleep(.2)
  else:raise RuntimeError('Stage host readiness timeout')
  assert req('/api/reparto/flota')[0]==401
  plain=w/'credentials.probe';t.protect(w/'local.env.dpapi',plain,True)
  try:values=dict(l.split('=',1) for l in plain.read_text(encoding='utf-8-sig').splitlines() if '=' in l and not l.startswith('#'))
  finally:plain.unlink()
  status,body=req('/api/auth/login',{'email':values['NEXORUTA_OPERADOR_MAIL'].strip('"'), 'password':values['NEXORUTA_OPERADOR_PASSWORD'].strip('"')})
  if status!=200:raise RuntimeError('Copied operator login did not succeed; no account/password changed')
  login=json.loads(body);report['loginContext']=login.get('contexto');token=login['accessToken'];status,permissions=req('/api/usuarios/actual/permisos',token=token);report['permissionCodes']=json.loads(permissions) if status==200 else [];status,body=req('/api/reparto/flota',token=token)
  if status==403:
   report['fleetRead']='blocked by existing operational-authority policy; no role or account changed'
  else:
   assert status==200
   fleet=json.loads(body);report['vehicles']=len(fleet);report['occupations']=sum(len(v['ocupaciones']) for v in fleet)
  for path in ['/api/usuarios/actual','/api/usuarios/actual/permisos']:assert req(path,token=token)[0]==200
  assert req('/api/rutas',{},token)[0]==503;assert req('/api/reparto/perfiles-viales',token=token)[0]==503
  assert t.history(w)[-1]==t.STAGE
  report['hostAndSafetyChecksPassed']=True
  report['authenticatedFleetReadPassed']=status==200 if 'fleetRead' not in report else False
 finally:
  process.terminate();process.wait(timeout=15);(w/'stage-probes.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Published Stage host and safety probes complete. See explicit authenticatedFleetReadPassed/blocker in stage-probes.json; no physical facts recorded.')
