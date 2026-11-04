#!/usr/bin/env python3
"""Review-only disposable runtime. Never opens the normal .local/codex-cloud state."""
import argparse,base64,json,os,pathlib,re,secrets,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/cloud'))
import dev
import portals
p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['start','stop','verify']);p.add_argument('--run-id',required=True);a=p.parse_args()
if not re.fullmatch('[a-z0-9]{1,24}',a.run_id):raise SystemExit('run-id: 1..24 lowercase letters/digits')
if not dev.DOCKER:raise SystemExit('Load env-agent.sh first; review runtime requires Docker')
dev.STATE=ROOT/'.local/review/runtimes'/a.run_id
dev.CONTAINER='nexoruta-review-'+a.run_id
key=dev.STATE/'evidence-key.json'
if a.command=='start':
    dev.STATE.mkdir(parents=True,exist_ok=True)
    if not key.exists():
        if (dev.STATE/'private.json').exists():raise SystemExit('Existing state without review key: stop and inspect, do not regenerate')
        key.write_text(json.dumps({'key':base64.b64encode(secrets.token_bytes(32)).decode()}));key.chmod(0o600)
elif not key.exists():raise SystemExit('No owned review runtime at this run-id')
original_env=dev.env
def environment(state,role='api'):
    result=original_env(state,role);result['Reparto__EvidenciasEncryptionKey']=json.loads(key.read_text())['key'];return result
dev.env=environment
if a.command=='start':dev.start();portals.start()
elif a.command=='stop':portals.stop();dev.stop()
else:dev.verify()
print('Review-only runtime:',dev.STATE,'container:',dev.CONTAINER)
