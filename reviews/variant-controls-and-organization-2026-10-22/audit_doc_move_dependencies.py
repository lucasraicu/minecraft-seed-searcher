"""Bounded read-only dependency report; does not authorize or perform any moves."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time

ROOT=Path(__file__).resolve().parents[2]
SKIP={'.git','.venv','node_modules','__pycache__','.pytest_cache','vendor','native','runs','dist','build','.next'}
def audit():
    plan=(ROOT/'REPO_ORGANIZATION_PLAN.md').read_text();section=plan.split('### Phase B',1)[1].split('### Phase C',1)[0]
    rows={m.group(1):dict(source=m.group(1),destination=m.group(2)+m.group(1),references=[],links=[],hash_pins=[])for m in re.finditer(r'^\| ([\w.]+\.md) \| (docs/[\w/]+/) \|',section,re.M)}
    for name,row in rows.items():
        p=ROOT/name;raw=p.read_bytes();row.update(sha256=hashlib.sha256(raw).hexdigest(),mode=oct(p.stat().st_mode&0o777),bytes=len(raw),destination_exists=(ROOT/row['destination']).exists())
        row['outgoing_links']=re.findall(r'\]\(([^)]+)\)',raw.decode())
    total=0;scanned=0;skipped=[];started=time.monotonic()
    for directory,dirs,files in os.walk(ROOT):
        dirs[:]=sorted(d for d in dirs if d not in SKIP and not(Path(directory)/d).is_symlink())
        for name in sorted(files):
            p=Path(directory)/name
            if p.is_symlink()or p.suffix.lower()not in {'.md','.json','.jsonl','.py','.js','.cjs','.ts','.tsx','.toml','.txt','.yaml','.yml','.sh'}:continue
            if p.stat().st_size>2<<20:skipped.append(str(p.relative_to(ROOT)));continue
            if scanned>=10000 or total+p.stat().st_size>150<<20 or time.monotonic()-started>30:raise RuntimeError('Audit bound reached; no incomplete approval report')
            raw=p.read_bytes();total+=len(raw);scanned+=1
            try:text=raw.decode('utf-8')
            except UnicodeDecodeError:continue
            rel=str(p.relative_to(ROOT))
            for target,row in rows.items():
                token=re.compile(r'(?<![\w.])'+re.escape(target)+r'(?![\w.])')
                if target==rel or not token.search(text):continue
                if row['sha256']in text:row['hash_pins'].append(rel)
                for n,line in enumerate(text.splitlines(),1):
                    if not token.search(line):continue
                    kind='mention'
                    for dest in re.findall(r'\]\(([^)]+)\)',line):
                        if dest.startswith(('https:','http:','#')):continue
                        if (p.parent/dest.split('#')[0].split(':')[0]).resolve()==ROOT/target:
                            kind='relative_link';row['links'].append(dict(path=rel,line=n));break
                    row['references'].append(dict(path=rel,line=n,kind=kind,text=line[:220]))
    for row in rows.values():
        row['frozen_links']=[r for r in row['links']if r['path'].startswith(('reviews/','docs/archive/'))]
        row['source_references']=[r for r in row['references']if r['path'].startswith(('src/','scripts/','tests/'))and r['kind']=='mention']
        row['baseline_only_hash_records']=[p for p in row['hash_pins']if p.startswith('reviews/variant-controls-and-organization-2026-10-22/')]
        row['historical_hash_pins']=[p for p in row['hash_pins']if p not in row['baseline_only_hash_records']]
        row['disposition']='defer_for_dependency_review'if row['frozen_links']or row['historical_hash_pins']or row['source_references']or row['destination_exists']else'candidate_with_active_link_updates'
    return dict(status='planning_only_no_moves',scanned_files=scanned,scanned_bytes=total,skipped_large=skipped,seconds=time.monotonic()-started,candidates=list(rows.values()))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);a=parser.parse_args();result=audit();text=json.dumps(result,indent=2)+'\n'
    if a.output:
        if a.output.exists():raise FileExistsError(a.output)
        a.output.write_text(text)
    else:print(text,end='')
