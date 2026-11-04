#!/usr/bin/env python3
"""Create NEW synthetic review actors through the local API; secrets stay in ignored 0600 JSON."""
import argparse,json,pathlib,re,secrets,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);a=p.parse_args()
if not re.fullmatch('[a-z0-9]{1,24}',a.run_id):raise SystemExit('Invalid run-id')
state=ROOT/'.local/review/runtimes'/a.run_id
if not(state/'evidence-key.json').exists():raise SystemExit('Review runtime required')
s=json.loads((state/'private.json').read_text())
if s.get('purpose')!='nexoruta-disposable-cloud':raise SystemExit('Wrong runtime marker')
file=state/'manual-actors.private.json'
with file.open('x') as f:json.dump({'status':'preparing'},f)
file.chmod(0o600)
actors={'status':'preparing','actors':{},'roles':{}}
def save():file.write_text(json.dumps(actors,indent=2)+'\n')
http=urllib.request.build_opener(urllib.request.ProxyHandler({}));token=None
def request(path,method='GET',data=None):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 req=urllib.request.Request('http://127.0.0.1:5000/'+path,data=None if data is None else json.dumps(data).encode(),headers=headers,method=method)
 with http.open(req,timeout=30) as r:return json.load(r) if r.status!=204 else None
def credential(label):
 account={'email':f'audit-{a.run_id}-{label.lower()}@example.test','password':secrets.token_hex(24)}
 actors['actors'][label]=account;save();return account
# A/C1/admin are the fresh bootstrap identities, never copied from another runtime.
for label,role in [('A','operator'),('C1','commerce'),('PLATAFORMA','admin')]:
 actors['actors'][label]={'email':s[role+'Email'],'password':s[role+'Password']}
save()
token=request('api/auth/login','POST',{'email':s['adminEmail'],'password':s['adminPassword']})['accessToken']
for label,path in [('B','operadores'),('C2','comercios')]:
 account=credential(label)
 result=request('api/admin/'+path,'POST',{'nombre':'AUDIT '+a.run_id+' '+label,'administrador':account})
 account['creation']=result;save()
token=request('api/auth/login','POST',{'email':s['operatorEmail'],'password':s['operatorPassword']})['accessToken']
for label,permissions,users in [('despachador',['envios.gestionar','envios.consultar'],['A1','A2']),('deposito',['envios.gestionar','envios.consultar'],['D1']),('repartidor',['reparto.ejecutar'],['R1','R2']),('sinpermiso',[],['NEGATIVO'])]:
 role=request('api/roles','POST',{'codigo':'audit_'+a.run_id+'_'+label,'nombre':'AUDIT '+a.run_id+' '+label})
 actors['roles'][label]=role;save()
 request('api/roles/'+role['id']+'/permisos','PUT',{'permisos':permissions})
 for user in users:
  account=credential(user)
  account['creation']=request('api/usuarios','POST',{'email':account['email'],'password':account['password'],'rolId':role['id']});save()
actors['status']='prepared; no physical or shipment/route operation performed';save()
print('New A1/A2/D1/R1/R2/NEGATIVO, operator B and commerce C2 prepared. Credentials remain in ignored 0600 JSON.')
