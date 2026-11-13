"""Published artifacts on a test-fixture-owned database; never accepts an operational connection argument."""
import base64,json,os,pathlib,secrets,socket,subprocess,time,urllib.request,urllib.error
w=pathlib.Path(os.environ['NEXORUTA_REHEARSAL_ARTIFACTS']).resolve()
# This variable is supplied only by the Testcontainers fixture, not by local.env.
connection=os.environ['CU06_FIXTURE_CONNECTION'];email=os.environ['CU06_FIXTURE_EMAIL'];password=os.environ['CU06_FIXTURE_PASSWORD'];route=os.environ['CU06_FIXTURE_ROUTE']
if 'database=integration_' not in connection.lower().replace(' ','') or 'username=rls_http_' not in connection.lower().replace(' ',''):
 raise RuntimeError('Only the restricted Testcontainers fixture identity is admitted')
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
api='http://127.0.0.1:'+str(port())+'/';bo='http://127.0.0.1:'+str(port())+'/'
report={'lane':'synthetic bounded migration fixture; published Release artifacts','queries':[]}
def req(path,token=None,data=None):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 try:
  with urllib.request.urlopen(urllib.request.Request(api+path,headers=headers,data=json.dumps(data).encode() if data is not None else None),timeout=15) as r:status=r.status;body=r.read()
 except urllib.error.HTTPError as e:status=e.code;body=e.read()
 report['queries'].append({'method':'POST' if data is not None else 'GET','path':'/'+path,'status':status});return status,body
processes=[];logs=[]
def start(folder,dll,env):
 log=(w/(folder+'-fixture-host.log')).open('wb');logs.append(log);child=subprocess.Popen(['dotnet',str(w/folder/dll)],cwd=w/folder,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);processes.append(child);return child
def ready(url,child):
 for i in range(150):
  try:
   with urllib.request.urlopen(url+'live',timeout=1) as r:
    if r.status==200:return
  except OSError:pass
  if child.poll() is not None:raise RuntimeError('Published fixture host failed; protected startup log retained')
  time.sleep(.2)
 raise RuntimeError('Published host readiness timeout')
try:
 env=os.environ.copy()
 for k in list(env):
  if k.startswith(('ConnectionStrings__','Jwt__','RoutingGeoapify__')):del env[k]
 env.update({'ASPNETCORE_URLS':api,'ASPNETCORE_ENVIRONMENT':'Development','ConnectionStrings__Postgres':connection,'Jwt__SigningKeyBase64':base64.b64encode(secrets.token_bytes(32)).decode(),'FleetTransition__StageOnly':'false','DatabaseInitialization__ApplyMigrations':'false','DatabaseInitialization__SeedData':'false','PlatformInitialization__Enabled':'false','RoutingGeoapify__PermitirLlamadasReales':'false','RoutingGeoapify__ApiKey':'','OpenTelemetry__Enabled':'false','DataProtection__KeysDirectory':str(w/'fixture-api-keys'),'Logging__LogLevel__Default':'Warning'})
 child=start('api','NexoRuta.Api.dll',env);ready(api,child);status,body=req('api/auth/login',data={'email':email,'password':password});assert status==200;token=json.loads(body)['accessToken']
 for path in ['api/reparto/vehiculos','api/reparto/flota','api/reparto/perfiles-viales','api/rutas/'+route+'/estimaciones']:
  assert req(path,token)[0]==200
 env.update({'ASPNETCORE_URLS':bo,'Api__BaseAddress':api,'DataProtection__KeysDirectory':str(w/'fixture-bo-keys')});child=start('backoffice','NexoRuta.Backoffice.dll',env)
 for i in range(150):
  try:
   with urllib.request.urlopen(bo+'ready',timeout=1) as r:
    if r.status==200:break
  except OSError:pass
  if child.poll() is not None:raise RuntimeError('Published Backoffice startup failed')
  time.sleep(.2)
 else:raise RuntimeError('Backoffice readiness timeout')
 browserenv=os.environ.copy();browserenv.update({'VEH_E2E_URL':bo,'VEH_E2E_EMAIL':email,'VEH_E2E_PASSWORD':password,'NEXORUTA_VEHICLES_E2E_DIR':str(w/'browser-published')})
 result=subprocess.run(['node',str(pathlib.Path.cwd()/'frontend/tests/browser/cu06-vehiculos.cjs')],env=browserenv,capture_output=True,timeout=120)
 (w/'published-browser.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
 report['passed']=True
finally:
 for process in reversed(processes):
  if process.poll() is None:process.terminate();process.wait(timeout=15)
 for log in logs:log.close()
 (w/'published-current-probes.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Published API/Backoffice and Chromium passed on bounded-migration synthetic database; all four reads HTTP200.')
