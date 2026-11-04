"""Rebuild the frozen dirty-source capsule and compare every published artifact byte."""
import argparse,hashlib,json,pathlib,subprocess
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=pathlib.Path,required=True);a=p.parse_args();w=a.work.resolve();result={}
for repo,project,output in [('backend','src/NexoRuta.Api','api'),('frontend','src/NexoRuta.Backoffice','backoffice')]:
 properties=['-p:ContinuousIntegrationBuild=true','-p:PathMap='+str(w/'source')+'=/_/source']
 with (w/(output+'-rebuild.log')).open('wb') as log:
  subprocess.run(['dotnet','build',project,'-c','Release','--no-restore','--no-incremental',*properties],cwd=w/'source'/repo,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['dotnet','publish',project,'-c','Release','--no-restore','--no-build','-o',str(w/(output+'-repeat')),*properties],cwd=w/'source'/repo,stdout=log,stderr=subprocess.STDOUT,check=True)
 expected=json.loads((w/(output+'-manifest.json')).read_text());actual={str(f.relative_to(w/(output+'-repeat'))).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in (w/(output+'-repeat')).rglob('*') if f.is_file()}
 differences=[k for k in expected.keys()|actual.keys() if expected.get(k)!=actual.get(k)];result[output]={'files':len(expected),'byteDifferences':differences}
 if differences==['NexoRuta.Backoffice.staticwebassets.endpoints.json']:
  def normalized(folder):
   document=json.loads((folder/differences[0]).read_text())
   for endpoint in document['Endpoints']:
    endpoint['ResponseHeaders']=[h for h in endpoint['ResponseHeaders'] if h['Name'].lower()!='last-modified']
   return document
  result[output]['onlyGeneratedLastModifiedDiffers']=normalized(w/output)==normalized(w/(output+'-repeat'))
(w/'reproducibility.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
if any(r['byteDifferences'] and not r.get('onlyGeneratedLastModifiedDiffers') for r in result.values()):raise RuntimeError('Unexpected published bytes differ; inspect reproducibility.json.')
print('Rebuild checked: API byte-identical; Backoffice comparison reports generated Last-Modified metadata separately. See reproducibility.json.')
