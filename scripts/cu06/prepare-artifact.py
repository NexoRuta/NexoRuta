"""Snapshot current dirty sources and publish an explicit Stage maintenance-capable artifact. No git mutation."""
import argparse,hashlib,json,pathlib,shutil,subprocess
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',required=True,type=pathlib.Path);a=p.parse_args();w=a.work.resolve();root=pathlib.Path.cwd();source=w/'source';source.mkdir(exist_ok=False)
def call(args,cwd=None):return subprocess.check_output(args,cwd=cwd or root).decode().strip()
manifest={"sdk":call(['dotnet','--version']),"repositories":{},"files":{}}
for repo in ['backend','frontend']:
 base=root/repo
 manifest['repositories'][repo]={"head":call(['git','rev-parse','HEAD'],base),"branch":call(['git','branch','--show-current'],base),"status":call(['git','status','--porcelain=v1'],base)}
 names=call(['git','ls-files','--cached','--others','--exclude-standard'],base).splitlines()
 for name in sorted(set(names)):
  f=base/name
  if not f.is_file() or any(x in f.parts for x in ['.git','bin','obj','node_modules']):continue
  if f.name=='.env' or f.suffix.lower() in ['.pfx','.p12','.key']:raise RuntimeError('Secret-shaped source file requires explicit review')
  target=source/repo/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target);manifest['files'][repo+'/'+name]=hashlib.sha256(target.read_bytes()).hexdigest()
(w/'source-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
for repo,project,output in [('backend','src/NexoRuta.Api','api'),('frontend','src/NexoRuta.Backoffice','backoffice')]:
 with (w/(output+'-publish.log')).open('wb') as log:
  subprocess.run(['dotnet','publish',project,'-c','Release','-o',str(w/output),'-p:ContinuousIntegrationBuild=true','-p:PathMap='+str(source)+'=/_/source'],cwd=source/repo,stdout=log,stderr=subprocess.STDOUT,check=True)
 artifacts={str(f.relative_to(w/output)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in (w/output).rglob('*') if f.is_file()}
 (w/(output+'-manifest.json')).write_text(json.dumps(artifacts,indent=2),encoding='utf-8')
print('Dirty source capsule and current API/Backoffice published with SHA256 provenance; no historical artifact claim.')
