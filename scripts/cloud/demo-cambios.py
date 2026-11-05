#!/usr/bin/env python3
"""Synthetic demo only. Requires dev.py start. Never uses Windows or shared data."""
import datetime as dt,json,pathlib,sys,urllib.request,urllib.error,uuid,os
ROOT=pathlib.Path(__file__).resolve().parents[2]
STATE=ROOT/'.local/codex-cloud'; private=json.loads((STATE/'private.json').read_text())
if private.get('purpose')!='nexoruta-disposable-cloud':raise RuntimeError('Not an owned disposable runtime')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def call(method,path,data=None,token=None):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 try:
  with opener.open(urllib.request.Request('http://127.0.0.1:5000'+path,data=json.dumps(data).encode() if data is not None else None,headers=headers,method=method),timeout=60) as r:
   content=r.read();return json.loads(content) if content else None
 except urllib.error.HTTPError as e:raise RuntimeError(f'{method} {path}: {e.code}: {e.read().decode()[:1500]}') from None
def login(prefix):return call('POST','/api/auth/login',{'email':private[prefix+'Email'],'password':private[prefix+'Password']})['accessToken']
def uid():return str(uuid.uuid4())
def iso(t):return t.isoformat().replace('+00:00','Z')
def setup():
 operator=login('operator');commerce=login('commerce');op=private['operatorId']
 actor=call('GET','/api/usuarios/actual',token=operator);access=actor['accesoId']
 rules=call('POST','/api/configuracion/reglas-operativas/borrador',{},operator)
 request={'versionConcurrencia':rules['versionConcurrencia'],'maxIntentosEntrega':3,'intervaloEntreIntentosMinutos':1,'politicaDevolucionAlAgotarIntentos':'DecisionOperativa','plazoEstandarMinutos':2880,'plazoUrgenteMinutos':1440,'plazoValidacionPruebaMinutos':60,'requisitosPrueba':['Fotografia','NombreReceptor'],'motivos':[{'codigo':'AUSENTE','descripcion':'Destinatario ausente','disponible':True}],'permiteEntregaParcial':True,'politicaPendientesParcial':'NuevaVisitaConRecargo','recargoNuevaVisitaUyu':25}
 draft=call('PUT','/api/configuracion/reglas-operativas/borrador',request,operator)
 call('POST','/api/configuracion/reglas-operativas/borrador/publicar',{'versionConcurrencia':draft['versionConcurrencia']},operator)
 zone=call('POST','/api/configuracion/zonas',{'nombre':'Demo 31–41 '+uid()[:8],'codigoDepartamento':'UY-MO'},operator)
 zid=zone['id'];version=zone['version']
 for day in range(1,8):
  slot=call('POST',f'/api/configuracion/zonas/{zid}/franjas',{'diaSemanaIso':day,'horaInicio':'00:00:00','horaFin':'23:59:59','versionZona':version},operator);version=slot['versionZona']
  slotid=slot['franja']['id'];update=call('PUT',f'/api/configuracion/zonas/{zid}/franjas/{slotid}',{'diaSemanaIso':day,'horaInicio':'00:00:00','horaFin':'23:59:59','estado':'Activa','versionZona':version},operator);version=update['versionZona']
 call('PUT',f'/api/configuracion/zonas/{zid}/estado',{'estado':'Activa','version':version},operator)
 try: tariff=call('GET','/api/configuracion/tarifas/borrador',token=operator)
 except RuntimeError as e:
  if ': 404:' not in str(e):raise
  tariff=call('POST','/api/configuracion/tarifas/borrador',{},operator)
 tariff=call('PUT','/api/configuracion/tarifas/borrador/tarifas',{'versionConcurrencia':tariff['versionConcurrencia'],'tarifas':[{'zonaId':zid,'modalidad':m,'importeBaseUyu':base,'precioPorKilogramoUyu':5,'precioPorMetroCubicoUyu':10,'ajustes':[]} for m,base in [('Estandar',100),('Retiro',70)]]},operator)
 call('POST','/api/configuracion/tarifas/borrador/publicar',{'versionConcurrencia':tariff['versionConcurrencia']},operator)
 conf=None
 # Fresh demo runtime initially has no reparto configuration. A configured one is kept/versioned.
 try: conf=call('GET','/api/reparto/configuracion',token=operator)
 except RuntimeError as e:
  if ': 404:' not in str(e):raise
 call('PUT','/api/reparto/configuracion',{'version':conf['version'] if conf else 0,'zonaHoraria':'America/Montevideo','maximoParadas':30,'bloquearDiscrepanciasCarga':True},operator)
 call('PUT',f'/api/repartidores/{access}',{'nombre':'Repartidor sintético 31–41','activo':True},operator)
 vehicle=call('PUT','/api/reparto/vehiculos',{'matricula':'DEMO-'+uid()[:6],'pesoMaximoGramos':3500,'volumenMaximoCm3':3500,'activo':True},operator)
 call('POST',f'/api/reparto/flota/{vehicle["id"]}/verificar-inicial',{'comandoId':uid(),'version':vehicle['version'],'motivo':'Verificación física sintética; vehículo vacío.'},operator)
 def create(count,pickup=False):
  req={'operadorId':op,'destinatarioNombre':'Comprador sintético 31–41','destinatarioEmail':'demo@example.test','direccion':'Domicilio de demostración 123','servicio':{'zonaId':zid,'latitud':-34.9,'longitud':-56.2,'modalidad':'Retiro' if pickup else 'Estandar'},'bultos':[{'codigo':'DEMO-'+uid()[:8],'pesoGramos':1000,'largoCentimetros':10,'anchoCentimetros':10,'altoCentimetros':10} for _ in range(count)]}
  if pickup:req['retiro']={'solicitudId':uid(),'motivo':'Cambio de producto','desdeUtc':iso(dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=1)),'hastaUtc':iso(dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=1))}
  created=call('POST','/api/retiros' if pickup else '/api/envios',req,commerce)
  if not pickup:
   for b in req['bultos']:
    scan=call('GET','/api/deposito/consulta?codigo='+b['codigo'],token=operator)
    parcel=next(x for x in scan['bultos'] if x['codigo']==b['codigo'])
    call('POST',f'/api/deposito/bultos/{parcel["id"]}/recepcion',{'comandoId':uid(),'versionEnvio':scan['versionEnvio'],'versionBulto':parcel['version'],'conforme':True,'pesoObservado':1000,'largoObservado':10,'anchoObservado':10,'altoObservado':10,'observaciones':''},operator)
  return created['id']
 partial=create(3);pickup=create(1,True)
 now=dt.datetime.now(dt.timezone.utc);date=(now-dt.timedelta(hours=3)).date().isoformat()
 route=call('POST','/api/rutas',{'repartidorAccesoId':access,'vehiculoId':vehicle['id'],'fecha':date,'paradas':[{'envioId':partial,'llegadaEstimadaUtc':iso(now+dt.timedelta(minutes=20))},{'envioId':pickup,'llegadaEstimadaUtc':iso(now+dt.timedelta(minutes=40))}]},operator)
 route=call('POST',f'/api/rutas/{route["id"]}/despacho',{'version':route['version']},operator)
 state={'rutaId':route['id'],'jornadaId':route['jornadaId'],'entregaId':partial,'retiroId':pickup}
 (STATE/'demo-cambios.json').write_text(json.dumps(state));print('Demo sintética creada. Ruta mixta lista para el cliente portátil.')
def verify_and_finish():
 operator=login('operator');commerce=login('commerce');d=json.loads((STATE/'demo-cambios.json').read_text())
 envios=call('GET','/api/envios',token=operator);partial=next(e for e in envios if e['id']==d['entregaId']);pickup=next(e for e in envios if e['id']==d['retiroId'])
 assert partial['estado']=='EntregadoParcialmente' and sum(b['resultado']=='Entregado' for b in partial['bultos'])==2
 # Links are generated by the real RabbitMQ worker. Public output never contains parcel/tenant IDs.
 links={}
 for key in ['entregaId','retiroId']:
  link=call('GET',f"/api/envios/{d[key]}/seguimiento",token=commerce)
  if not link:raise RuntimeError('Tracking worker has not generated the public link yet')
  links[key]=link
  url=link['url'];token=url.rstrip('/').split('/')[-1]
  progress=call('GET','/api/public/seguimiento/'+token)
  assert progress['totalBultos']==(3 if key=='entregaId' else 1)
  assert 'bultoId' not in json.dumps(progress) and 'operadorId' not in json.dumps(progress)
  if key=='entregaId':assert progress['bultosEntregados']==2
 notices=call('GET','/api/avisos-comercio',token=commerce)
 assert any(a['envioId']==d['entregaId'] and a['tipo']=='BultoActualizado' for a in notices),'Kafka commerce inbox not populated'
 call('POST',f"/api/deposito/envios/{pickup['id']}/recepcion",{'version':pickup['version']},operator)
 pickup=next(e for e in call('GET','/api/envios',token=operator) if e['id']==d['retiroId'])
 assert pickup['estado']=='RetiroEnDeposito'
 call('POST',f"/api/deposito/retiros/{pickup['id']}/entrega-comercio",{'version':pickup['version']},operator)
 # Explicit physical return and release are separate from closing the route.
 fleet=call('GET','/api/reparto/flota',token=operator)
 vehicle=next(v for v in fleet if any(o['rutaId']==d['rutaId'] for o in v['ocupaciones']))
 occupation=next(o for o in vehicle['ocupaciones'] if o['rutaId']==d['rutaId'])
 returned=call('POST',f"/api/reparto/flota/{vehicle['id']}/retorno",{'comandoId':uid(),'ocupacionId':occupation['id'],'version':occupation['version'],'motivo':'Constatación sintética del retorno físico.'},operator)
 call('POST',f"/api/reparto/flota/{vehicle['id']}/liberar",{'comandoId':uid(),'ocupacionId':occupation['id'],'version':returned['version'],'motivo':'Inspección sintética de vehículo sin carga.'},operator)
 d['links']=links;(STATE/'demo-cambios.json').write_text(json.dumps(d))
 print('Verificado: parcial 2/3, enlaces públicos sin IDs internos, avisos Kafka v2, recepción y entrega al comercio, retorno y liberación explícitos.')
def revisit():
 operator=login('operator');d=json.loads((STATE/'demo-cambios.json').read_text());now=dt.datetime.now(dt.timezone.utc)
 if 'revisitaId' in d:raise RuntimeError('This demo already prepared its next visit; use the recorded route')
 old=next(r for r in call('GET','/api/rutas?fecha='+(now-dt.timedelta(hours=3)).date().isoformat(),token=operator) if r['id']==d['rutaId'])
 envio=next(e for e in call('GET','/api/envios',token=operator) if e['id']==d['entregaId']);before=envio['tarifa']['totalFinalUyu']
 pendientes=[b['codigo'] for b in envio['bultos'] if b['resultado']=='Pendiente'];assert len(pendientes)==1
 h=call('POST','/api/rutas',{'repartidorAccesoId':old['repartidorAccesoId'],'vehiculoId':old['vehiculoId'],'fecha':old['fecha'],'paradas':[{'envioId':envio['id'],'llegadaEstimadaUtc':iso(now+dt.timedelta(minutes=30))}]},operator)
 assert [b['codigo'] for b in h['paradas'][0]['bultos']]==pendientes,'Completed parcels leaked into new visit'
 h=call('POST',f"/api/rutas/{h['id']}/despacho",{'version':h['version']},operator)
 after=call('GET',f"/api/envios/{envio['id']}/tarifa",token=operator)['totalFinalUyu'];assert round(after-before,2)==25
 d['revisitaId']=h['id'];(STATE/'demo-cambios.json').write_text(json.dumps(d))
 print('Nueva visita contiene solo el pendiente; despacho aplica una única versión acumulada con recargo UYU 25.')
if __name__=='__main__':
 if sys.argv[1:]==['setup']:setup()
 elif sys.argv[1:]==['finish']:verify_and_finish()
 elif sys.argv[1:]==['revisit']:revisit()
 else:raise SystemExit('Uso: demo-cambios.py setup | finish | revisit')
