#!/usr/bin/env python3
"""Read-only OOXML/source inventory. Never executes macros or interprets styles."""
import argparse, hashlib, json, pathlib, subprocess, zipfile, xml.etree.ElementTree as E
ROOT=pathlib.Path(__file__).resolve().parents[2]
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def sheets(file):
    with zipfile.ZipFile(file) as z:
        strings=[''.join(e.itertext()) for e in E.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',NS)] if 'xl/sharedStrings.xml' in z.namelist() else []
        rel={e.get('Id'):e.get('Target') for e in E.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        result={}
        for sheet in E.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',NS):
            target=rel[sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            rows=[]
            for row in E.fromstring(z.read(target)).findall('s:sheetData/s:row',NS):
                cells={}
                for c in row:
                    v=c.find('s:v',NS);inline=c.find('s:is',NS)
                    value=(v.text or '') if v is not None else ''.join(inline.itertext()) if inline is not None else ''
                    if c.get('t')=='s' and value:value=strings[int(value)]
                    if value:cells[c.get('r')]=value
                if cells:rows.append(cells)
            result[sheet.get('name')]=rows
        return result

def inventory():
    source=ROOT/'docs/alcance/Calcs/Casos de Uso - Responsables.xlsm'
    files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'docs/alcance').rglob('*')) if p.is_file()}
    heads={p or 'principal':subprocess.check_output(['git','-C',str(ROOT/p),'rev-parse','HEAD'],text=True).strip() for p in ['', 'backend','frontend','mobile']}
    endpoints=[]
    for p in sorted((ROOT/'backend/src/NexoRuta.Api').rglob('*Controller.cs')):
        attributes=[{'line':i,'text':line.strip()} for i,line in enumerate(p.read_text().splitlines(),1) if any(x in line for x in ['[Route','[Http','[Authorize','[AllowAnonymous','[EnableRateLimiting'])]
        endpoints.append({'file':str(p.relative_to(ROOT)),'attributes':attributes})
    other={str(p.relative_to(ROOT)):sheets(p) for p in sorted((ROOT/'docs/alcance').rglob('*.xlsx'))}
    return dict(source_sha256=files,heads=heads,sheets=sheets(source),secondary_workbooks=other,controllers=endpoints,
                limits='Attribute inventory is a source index, not proof of route reachability or effective authorization. No macros/styles executed.')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(inventory(),ensure_ascii=False,indent=2)+'\n')
