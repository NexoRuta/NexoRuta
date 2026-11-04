#!/usr/bin/env python3
"""Generate NEW admission CSVs for human validation; performs no HTTP or DB operations."""
import argparse,csv,json,pathlib,uuid
ROOT=pathlib.Path(__file__).resolve().parents[2]
RESERVED={'01a19e23-d3a5-7a48-92f4-97fe178c87ad','01a19e71-822f-7434-9acc-2a02b89b2487'}
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--operador-id',required=True,type=uuid.UUID);p.add_argument('--zona-id',required=True,type=uuid.UUID)
p.add_argument('--run-id',default=None);a=p.parse_args()
if str(a.operador_id) in RESERVED or str(a.zona_id) in RESERVED:raise SystemExit('Reserved identifier prohibited')
run=a.run_id or uuid.uuid4().hex[:12]
if not run.isalnum() or len(run)>32:raise SystemExit('run-id: 1..32 alphanumeric characters')
out=ROOT/'.local/review/manual'/run
out.mkdir(parents=True,exist_ok=False)
header=['referenciaExterna','nombreDestinatario','emailDestinatario','direccion','codigoBulto','pesoGramos','largoCentimetros','anchoCentimetros','altoCentimetros','zonaId','latitud','longitud','modalidad']
# These are declared synthetic parcel measurements, not observations of physical receipt.
rows=[]
for case in ['MULTI','HISTORIA','CAPACIDAD','INTENTO','RETORNO','PRUEBA','CANCELACION','AISLAMIENTO']:
    for parcel in range(1,3 if case=='MULTI' else 2):
        ref=f'AUD-{run}-{case}'
        rows.append([ref,'Destinatario sintético '+case,f'{case.lower()}-{run}@example.test','Dirección sintética de validación',f'{ref}-B{parcel}',500,20,10,5,str(a.zona_id),-34.9,-56.2,'Estandar'])
def write(name,data):
    with (out/name).open('w',newline='') as f:w=csv.writer(f);w.writerow(header);w.writerows(data)
write('01-alta-v2.csv',rows)
write('02-reimportacion-parcial-v2.csv',rows[:2])
bad=rows[-1].copy();bad[0]+='-NEG';bad[5]='-1'
fresh=rows[2].copy();fresh[0]+='-ATOMICO';fresh[4]+='-ATOMICO'
write('03-lote-invalido-atomico-v2.csv',[fresh,bad])
rivera=rows[-1].copy();rivera[0]+='-RIVERA';rivera[4]+='-RIVERA';rivera[10:12]=[-30.905,-55.55]
write('04-sin-cobertura-v2.csv',[rivera])
(out/'manifest.json').write_text(json.dumps(dict(run=run,operadorId=str(a.operador_id),zonaId=str(a.zona_id),versionFormato=2,
    coordinates='Declare an operator/zone that really contains -34.9,-56.2 in this NEW synthetic environment. No coverage or tariff is created by this generator.',
    physicalActions='Pending HUMAN observation: receive, compare, load, depart, deliver, return and release. Never mark them performed from this manifest.',
    references=sorted(set(r[0] for r in rows))),indent=2)+'\n')
print(out)
