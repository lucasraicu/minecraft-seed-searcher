"""Archive exact disposable control evidence; no BDS or extraction commands."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'src'))
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.registry import canonical_json

BASE=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/variant-controls-approved-20261022')
OUT=ROOT/'fixtures/bedrock-26.52/variant-controls'

def main():
    OUT.mkdir(parents=True,exist_ok=True);files={}
    def add(path,name):
        path=Path(path)
        if path.is_symlink():raise ValueError('Fixture links prohibited')
        files[name]=path.read_bytes()
    for name in['CONTROL_RESULTS.json','IGLOO_CONTROL_RESULTS.json','FROZEN_PROTOCOL.json','IGLOO_FOLLOWUP_PROTOCOL.json','IGLOO_REQUEST_AMENDMENT_APPROVAL.json','TEMPLATE_SIGNATURES.json']:
        add(HERE/name,'protocols/'+name)
    for name in['variant_observer.js','igloo_followup_observer.js','run_variant_controls.py','run_igloo_followup.py','read_variant_entities.py','recognize_variants.py']:
        add(HERE/name,'source/'+name)
    add(BASE/'BDS_BUDGET.json','budget/BDS_BUDGET.json')
    for idx in range(8):
        directory=BASE/f'case-{idx}'
        for name in['report.json','console.log','observer.js','entities.json','expanded-entities-diagnostic.json','recognition.json']:
            if(directory/name).exists():add(directory/name,f'cases/{idx}/'+name)
        add(directory/'worlds/world/server.properties',f'cases/{idx}/server.properties')
        add(directory/'worlds/world/behavior_packs/spawn_observer/manifest.json',f'cases/{idx}/manifest.json')
        if idx in(1,2,5,6,7):
            world=directory/'worlds/world/worlds/spawn_audit'
            for path in world.rglob('*'):
                if path.is_file():add(path,f'worlds/{idx}/'+str(path.relative_to(world)))
    for idx in(0,3,4):
        directory=BASE/f'followup-case-{idx}'
        for name in['report.json','console.log','observer.js','recognition.json']:add(directory/name,f'followups/{idx}/'+name)
        add(BASE/f'case-{idx}-before-followup.tar.gz',f'prior-worlds/case-{idx}.tar.gz')
    for name in['report.json','entities.json','recognition.json']:add(BASE/'case-2-basement-proof'/name,'saved-basement-proof/'+name)
    templates=[r for r in json.loads((BASE/'templates.json').read_text())if r['path'].startswith('igloo/')]
    files['templates/IGLOO_TEMPLATES.json']=canonical_json(templates)
    for row in templates:
        path=BASE/row['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'];add(path,'templates/'+row['path'])
    protocol=json.loads((HERE/'FROZEN_PROTOCOL.json').read_text());store=AutomationStore('/Users/lucasraicu/.local/share/antigravity-worker-mcp/biome-expansion-approved-20261022/catalog-corrected');entries={e['world_id']:e for e in store.snapshot()['worlds']}
    for case in protocol['cases']:
        observation=store.artifacts.get_json(entries[case['world_id']]['artifact'])['observation'];raw=canonical_json(observation)
        assert hashlib.sha256(raw).hexdigest()==case['observation_id'];files['observations/'+str(case['id'])+'.json']=raw
    if len(files)>512 or sum(map(len,files.values()))>128<<20:raise ValueError('Portable evidence cap')
    archive=OUT/'variant-controls.tar.gz'
    if archive.exists():raise FileExistsError(archive)
    with tarfile.open(archive,'w:gz',compresslevel=6)as tar:
        for name,raw in sorted(files.items()):
            info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(raw))
    manifest=dict(revision='variant-control-fixture-v1',archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),archive_bytes=archive.stat().st_size,total_uncompressed_bytes=sum(map(len,files.values())),members={name:dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))for name,raw in sorted(files.items())})
    (OUT/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in manifest.items()if k!='members'}));print('members',len(files))

if __name__=='__main__':main()
