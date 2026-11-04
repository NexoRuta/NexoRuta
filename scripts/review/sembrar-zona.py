#!/usr/bin/env python3
"""Create only a NEW synthetic zone/slots and admission CSVs in the review-owned runtime.
No shipment, route, receipt, load, departure, delivery, return or release is posted.
"""
import argparse,json,pathlib,re,subprocess,sys,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);a=p.parse_args()
if not re.fullmatch('[a-z0-9]{1,24}',a.run_id):raise SystemExit('Invalid run-id')
state=ROOT/'.local/review/runtimes'/a.run_id
s=json.loads((state/'private.json').read_text())
if s.get('purpose')!='nexoruta-disposable-cloud' or not (state/'evidence-key.json').exists():raise SystemExit('Not a review-owned runtime')
marker=state/'manual-preparation.json'
if marker.exists():raise SystemExit('Already prepared; inspect existing marker, do not reseed')
http=urllib.request.build_opener(urllib.request.ProxyHandler({}));token=None
def request(path,method='GET',data=None):
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request('http://127.0.0.1:5000/'+path,data=None if data is None else json.dumps(data).encode(),headers=headers,method=method)
    with http.open(req,timeout=30) as r:return json.load(r) if r.status!=204 else None
token=request('api/auth/login','POST',{'email':s['operatorEmail'],'password':s['operatorPassword']})['accessToken']
marker.write_text(json.dumps({'run':a.run_id,'stage':'creating-zone; inspect before any retry'})+'\n')
zone=request('api/configuracion/zonas','POST',{'nombre':'AUDIT '+a.run_id+' zona sintética',
    'codigoDepartamento':'UY-MO'})
id=zone['id']
marker.write_text(json.dumps({'run':a.run_id,'zonaId':id,'stage':'slots-pending'})+'\n')
for day in range(1,8):
    current=request('api/configuracion/zonas/'+id)
    request('api/configuracion/zonas/'+id+'/franjas','POST',{'diaSemanaIso':day,'horaInicio':'09:00:00','horaFin':'18:00:00','versionZona':current['version']})
marker.write_text(json.dumps({'run':a.run_id,'zonaId':id,'stage':'slots-completed'})+'\n')
current=request('api/configuracion/zonas/'+id)
if current['estado']!='Activa':request('api/configuracion/zonas/'+id+'/estado','PUT',{'estado':'Activa','version':current['version']})
marker.write_text(json.dumps({'run':a.run_id,'operadorId':s['operatorId'],'zonaId':id,
    'state':'Synthetic configuration only. Human configuration/validation and all physical actions remain pending.',
    'tariff':'Not created: complete CU-03 manually with explicit synthetic amounts and independent calculations.',
    'rules':'Not created: complete CU-04 manually.'},indent=2)+'\n')
subprocess.run([sys.executable,ROOT/'scripts/review/preparar-datos.py','--operador-id',s['operatorId'],'--zona-id',id,'--run-id',a.run_id],check=True)
print('New synthetic zone and CSVs prepared; no shipments/routes/physical operations created.')
