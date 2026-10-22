"""Approved bounded registry/layout rebind from saved facts; no extraction."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import resource
import sqlite3
import subprocess
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
from seed_search.catalog import automation
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.registry import digest,canonical_json
from seed_search.catalog.ingestion import atomic_json,tree_bytes
from seed_search.catalog.codec import validate_summary_v3
from seed_search.catalog.harvest import HarvestQueue,_validate_rank
from scripts.reanchor_catalog import copy_history
from scripts.reindex_catalog_biomes import process_tree_rss

SOURCE=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/biome-expansion-approved-20261022/catalog-corrected')
BASE=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/treasure-activation-approved-20261022')
TARGET=BASE/'catalog';PIN='9637bc21753fa249775f0b11e84ec7a9a92d3872d7982f8e3dfd9a2be4859421'
FID='structure.bastion_treasure'

def oracle(observation,row,feature=FID):
    igloo=feature=='structure.igloo_with_basement';key='igloo_basement'if igloo else'bastion_variant';parent_key='structure.igloo'if igloo else'structure.bastion'
    inventory=observation['realm']['inventory'][key];parent=observation['coverage'][parent_key]
    parents={tuple(p)for p in observation['structures'][parent_key]}
    points=sorted({tuple(p[:2])for p in inventory['points']if(igloo or p[2]==2)and tuple(p[:2])in parents})
    cx,cz=row['anchor']if igloo else row['nether_anchor'];half=row['border_side']//2 if igloo else 512
    window=(cx-half,cz-half,cx+half,cz+half);radii=(256,512,1024)if igloo else(64,128,256)
    captured=[p for p in points if window[0]<=p[0]<window[2]and window[1]<=p[1]<window[3]]
    distance=lambda p:(p[0]-cx)**2+(p[1]-cz)**2
    nearest=min(captured,key=lambda p:(distance(p),p),default=None)
    counts=[sum(distance(p)<=r*r for p in captured)for r in radii]+[len(captured)]
    complete=[]
    for r in (*radii,None):
        box=window if r is None else(max(window[0],cx-r),max(window[1],cz-r),min(window[2],cx+r+1),min(window[3],cz+r+1))
        b=inventory.get('bounds',[])
        complete.append(bool(inventory.get('status')=='complete'and parent.get('status')=='complete'and len(b)==4 and b[0]<=box[0]and b[1]<=box[1]and b[2]>=box[2]and b[3]>=box[3]))
    return dict(dimension='overworld'if igloo else'nether',counts=counts,complete=complete,nearest_d2=distance(nearest)if nearest is not None else None,witness=[nearest[0],None,nearest[1]]if nearest is not None else None)

def prepare(entry,definition,deadline,include_igloo=False):
    if time.monotonic()>deadline:raise TimeoutError('Rebuild deadline')
    source=AutomationStore(SOURCE);target=AutomationStore(TARGET)
    bundle=source.artifacts.get_json(entry['artifact']);observation=bundle['observation']
    if digest(observation)!=entry['observation_id']:raise ValueError('Original observation identity')
    revision=digest(definition);mapping={};offers={};rows=[];old_row_digests=[]
    for old in bundle['summaries']:
        features=[FID]+(['structure.igloo_with_basement']if include_igloo else[])
        for fid in features:
            if old['features'][fid]!=oracle(observation,old,fid):raise ValueError('Saved variant feature differs from independent oracle')
        row=dict(old,registry_revision=revision)
        row['layout_id']=digest(['catalog-summary-v3',row['source_observation_id'],row['source_extension_id'],row['sampling_profile_revision'],revision,row['anchor'],row['anchor_modes'],row['border_side']])
        validate_summary_v3(row,registry=definition);mapping[old['layout_id']]=row['layout_id'];rows.append(row)
        old_row_digests.append(digest({k:v for k,v in old.items()if k not in ('registry_revision','layout_id')}))
        # Same definition/rank as automation_offers_v3; independently replay later.
        modes=[]
        if'origin'in row['anchor_modes']:modes.append('origin')
        if'recommended'in row['anchor_modes']:modes.append('recommended')
        if'world_spawn_estimated'in row['anchor_modes']and any(a['mode']=='world_spawn_estimated'and a['coordinate']==row['anchor']for a in observation['anchors']):modes.append('spawn')
        for fid in features:
            igloo=fid=='structure.igloo_with_basement'
            if not igloo and row['border_side']!=2048:continue
            value=row['features'][fid]
            if value['nearest_d2']is None:continue
            x,y,z=value['witness'];ax,az=row['anchor'];rank=[value['nearest_d2'],entry['world_id'],ax,az,x,0 if y is None else y,z]
            nx,nz=row['anchor']if igloo else row['nether_anchor'];half=row['border_side']//2 if igloo else 512
            if not nx-half<=x<nx+half or not nz-half<=z<nz+half:raise ValueError('Variant witness border')
            for mode in modes:
                oid=f'v3.near:{fid}:'+((str(row['border_side'])+':')if igloo else'')+mode
                member=dict(world_id=entry['world_id'],layout_id=row['layout_id'],anchor=row['anchor'],source_observation_id=entry['observation_id'],witness=value['witness'],feature_id=fid,rank=rank)
                if oid not in offers or rank<offers[oid]['rank']:offers[oid]=dict(objective_id=oid,rank=rank,member=member,world_id=entry['world_id'])
    if len(mapping)!=len(rows):raise ValueError('Duplicate source layout')
    if old_row_digests!=[digest({k:v for k,v in r.items()if k not in ('registry_revision','layout_id')})for r in rows]:raise ValueError('Numeric/legacy facts changed')
    value=dict(bundle,registry=definition,summaries=rows)
    target._bundle(value)
    artifact=target.artifacts.put_json(value,compression_level=1)
    refs={}
    for side in (2048,4096,8192):
        old=source.artifacts.get_json(entry['summary_artifacts'][str(side)])
        if old['revision']!='catalog-query-projection-v5':raise ValueError('Expected source packed V5')
        packed=[]
        for p in old['rows']:
            if p[0]not in mapping:raise ValueError('Projection source layout differs')
            packed.append([mapping[p[0]],*p[1:]])
        projected=dict(old,registry=definition,bundle_sha256=artifact['sha256'],rows=packed)
        refs[str(side)]=target.artifacts.put_json(projected,compression_level=1)
    updated=dict(entry,artifact=artifact,registry_revision=revision,summary_artifacts=refs)
    # Verify actual immutable packed projections against full rebound bundle rows.
    for side in(2048,4096,8192):
        if target._projection(updated,side)!=[r for r in rows if r['border_side']==side]:raise ValueError('Projection roundtrip mismatch')
    return dict(entry=updated,mapping=mapping,offers=list(offers.values()),rows=len(rows),observation_sha256=digest(observation),realm_sha256=digest(observation['realm']),feature_payload_sha256=digest(old_row_digests))

def run(*,include_igloo=False):
    prior=None;initial=0.
    if include_igloo:
        prior=json.loads((BASE/'STATE.json').read_text())
        if not prior['complete']or prior['total_seconds']!=600 or prior.get('stage')=='both-variants':raise ValueError('Expected completed private treasure stage')
        initial=prior['charged_seconds']
        if initial>=600:raise ValueError('No remaining derived rebuild allocation')
        igloo_controls=json.loads((HERE/'IGLOO_CONTROL_RESULTS.json').read_text())
        if igloo_controls.get('status')!='pass'or any(len({c['case']['world_id']for c in igloo_controls['controls']if c['actual']is label})<2 for label in(True,False)):raise ValueError('Igloo independent controls missing')
    elif BASE.exists():raise FileExistsError('Fresh allocation only; never reset an existing journal')
    controls=json.loads((HERE/'CONTROL_RESULTS.json').read_text())
    passed=[c for c in controls['controls']if c['case']['feature']=='bastion_treasure'and c['status']=='observed'and c['build_verified']and c['clean_shutdown']and c['removed']and c['locate_matches']and c['actual']is c['case']['predicted']]
    if any(len({c['case']['world_id']for c in passed if c['actual']is label})<2 for label in(True,False)):raise ValueError('Actual controls incomplete')
    source=AutomationStore(SOURCE);current=source.snapshot()
    if digest(current)!=PIN or len(current['worlds'])!=222:raise ValueError('Source snapshot changed')
    definition=copy.deepcopy(current['registry'])
    f=next(f for f in definition['features']if f['id']==FID)
    if f['available']:raise ValueError('Source gate already open')
    f.update(available=True,unavailable_reason='')
    if include_igloo:
        next(f for f in definition['features']if f['id']=='structure.igloo_with_basement').update(available=True,unavailable_reason='')
        definition['activation_evidence']['variant_control_artifacts']={name:hashlib.sha256((HERE/file).read_bytes()).hexdigest()for name,file in[('bastion_treasure','CONTROL_RESULTS.json'),('igloo_basement','IGLOO_CONTROL_RESULTS.json')]}
    expected=(tree_bytes(BASE)+222*(3<<20)+(20<<20))if include_igloo else 2*tree_bytes(SOURCE)+(100<<20)
    import shutil
    if expected>2<<30 or shutil.disk_usage(SOURCE).free<expected:raise ValueError('Preflight bytes/free disk')
    if not include_igloo:BASE.mkdir()
    started=time.monotonic();deadline=started+(600-initial);state=dict(revision='treasure-activation-budget-v1',stage='both-variants'if include_igloo else'treasure-only',source_snapshot=PIN,registry_revision=digest(definition),total_seconds=600,prior_consumed_seconds=initial,charged_seconds=600,complete=False,worlds=[],preflight_bytes=expected)
    if prior:atomic_json(BASE/'STATE-treasure.json',prior)
    if prior:shutil.copy2(BASE/'registry.json',BASE/'registry-treasure.json')
    path=BASE/'STATE.json';atomic_json(path,state);atomic_json(BASE/'registry.json',definition)
    errors=[];stop=threading.Event();peak_tree_rss=[0]
    def guard():
        rss=process_tree_rss();peak_tree_rss[0]=max(peak_tree_rss[0],rss)
        if time.monotonic()>=deadline or tree_bytes(BASE)>2<<30 or rss>4<<30:raise TimeoutError('Activation time/output/RSS cap')
        if errors:raise TimeoutError(errors[0])
    def watch():
        while not stop.wait(1):
            try:guard()
            except Exception as e:errors.append(str(e));return
    monitor=threading.Thread(target=watch,daemon=True);monitor.start();pool=None
    try:
        if include_igloo:
            # Retire only this task's unadopted draft mutable state; all CAS/history
            # stays in the same separate root, with exact old metadata archived.
            running=subprocess.check_output(['/bin/ps','-axo','pid=,command='],text=True)
            if any('seed_search.catalog.http_server'in line and str(TARGET)in line for line in running.splitlines()):raise ValueError('Close owned private preview before retiring draft metadata')
            if any((TARGET/name).exists()for name in['harvest.sqlite-wal','harvest.sqlite-shm']):raise ValueError('Mutable SQLite was not drained')
            import fcntl
            for name in('harvest.lock','harvest-drain.lock'):
                with(TARGET/name).open('a')as handle:
                    fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(handle,fcntl.LOCK_UN)
            archive=BASE/'treasure-stage-mutable-archive';archive.mkdir(exist_ok=False)
            archived=[]
            for relative in['harvest.sqlite','automation/configuration.json','automation/current.json']:
                source_path=TARGET/relative
                if source_path.exists():
                    sha=hashlib.sha256(source_path.read_bytes()).hexdigest();dest=archive/relative;dest.parent.mkdir(parents=True,exist_ok=True);source_path.rename(dest)
                    if hashlib.sha256(dest.read_bytes()).hexdigest()!=sha:raise ValueError('Private metadata archive differs')
                    archived.append(dict(original=relative,archive=str(dest.relative_to(BASE)),sha256=sha))
            atomic_json(BASE/'TREASURE_STAGE_METADATA_ARCHIVE.json',dict(files=archived,private_never_adopted=True))
        else:TARGET.mkdir();copy_history(SOURCE,TARGET)
        guard()
        old_config=automation.configuration(SOURCE)
        automation.configure(TARGET,old_config['identity'],old_config['options'],catalog_registry=definition)
        config=automation.configuration(TARGET)
        automation.control(TARGET,'pause')
        target=AutomationStore(TARGET)
        receipts=sqlite3.connect((SOURCE/'harvest.sqlite').as_uri()+'?mode=ro',uri=True)
        members=copy.deepcopy(current['memberships']);by_world={e['world_id']:[]for e in current['worlds']}
        for m in members:by_world[m['world_id']].append(m)
        new_entries=[];new_offers={};pool=ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn'))
        futures=[pool.submit(prepare,e,definition,deadline-25,include_igloo)for e in current['worlds']]
        with HarvestQueue(TARGET)as queue,queue.supervisor()as acquired,queue.ownership():
            if not acquired:raise ValueError('Destination ownership')
            ledger=automation._ledger(queue,config)
            for i,(entry,future)in enumerate(zip(current['worlds'],futures)):
                guard();result=future.result(timeout=max(.1,deadline-time.monotonic()-20));updated=result['entry'];new_entries.append(updated)
                for m in by_world[entry['world_id']]:
                    old=m['member'].get('layout_id')
                    if old in result['mapping']:m['member']['layout_id']=result['mapping'][old]
                for off in result['offers']:new_offers.setdefault(off['objective_id'],[]).append(off)
                evaluation,replay=receipts.execute('SELECT evaluations,replay FROM automation_receipts WHERE world_id=?',(entry['world_id'],)).fetchone()
                replay=dict(json.loads(replay),treasure_activation_source=PIN)
                values=(entry['world_id'],canonical_json(entry['identity']).decode(),entry['observation_id'],canonical_json(updated['artifact']).decode(),evaluation,canonical_json(replay).decode())
                with queue.transaction():queue.conn.execute('INSERT INTO automation_receipts VALUES(?,?,?,?,?,?)',values)
                state['worlds'].append({k:v for k,v in result.items()if k not in('mapping','offers')})
                state['elapsed_seconds']=initial+time.monotonic()-started;atomic_json(path,state)
                if(i+1)%25==0:print(json.dumps(dict(worlds=i+1,seconds=state['elapsed_seconds'])),flush=True)
            receipts.close();pool.shutdown(wait=True);pool=None;guard()
            for oid,offers in sorted(new_offers.items()):
                cap=ledger.objectives[oid];chosen=sorted(offers,key=lambda o:(_validate_rank(o['rank']),o['world_id']))[:cap]
                if len({o['world_id']for o in chosen})!=len(chosen):raise ValueError('Duplicate treasure world')
                members.extend(chosen)
            if not include_igloo and any(m['objective_id'].startswith('v3.near:structure.igloo_with_basement')for m in members):raise ValueError('Igloo gate unexpectedly populated')
            members.sort(key=lambda m:(m['objective_id'],_validate_rank(m['rank']),m['world_id']))
            for m in members:
                if m['objective_id']not in ledger.objectives:raise ValueError('Unknown retained objective')
                _validate_rank(m['rank'])
            with queue.transaction():
                queue.conn.executemany('INSERT INTO automation_members VALUES(?,?,?,?)',((m['objective_id'],m['world_id'],canonical_json(m['rank']).decode(),canonical_json(m['member']).decode())for m in members))
                queue.conn.execute("UPDATE automation_meta SET value='1' WHERE key='generation'")
            manifest=dict(current,policy_revision=config['policy_revision'],policy_contract=ledger.policy_contract,registry=definition,generation=ledger.generation(),worlds=new_entries,memberships=members)
            target._manifest(manifest);guard();sid=digest(manifest)
            artifact=target._write_manifest(manifest,compression_level=1);binding=dict(revision='catalog-snapshot-binding-v2',snapshot_id=sid,generation=manifest['generation'],artifact=artifact)
            guard();atomic_json(target.generations_dir/(manifest['policy_revision']+'-'+str(manifest['generation'])+'.json'),binding);atomic_json(target.snapshots_dir/(sid+'.json'),binding);atomic_json(target.current_path,binding)
            if digest(source.snapshot())!=PIN or digest(target.snapshot())!=sid:raise ValueError('Publication/source pin')
            guard();state.update(complete=True,snapshot_id=sid,policy_revision=config['policy_revision'],memberships=len(members),treasure_memberships=sum(m['objective_id'].startswith('v3.near:'+FID+':')for m in members))
    finally:
        if pool:pool.shutdown(wait=True,cancel_futures=True)
        stop.set();monitor.join(timeout=2);state['charged_seconds']=initial+time.monotonic()-started;state['bytes']=tree_bytes(BASE);state['peak_rss_main_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;state['peak_tree_rss_sampled_bytes']=peak_tree_rss[0];state['errors']=errors;atomic_json(path,state)
    print(json.dumps({k:v for k,v in state.items()if k!='worlds'}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');parser.add_argument('--include-igloo',action='store_true');a=parser.parse_args()
    if a.execute:run(include_igloo=a.include_igloo)
    else:print(json.dumps(dict(dry_run=True,source=str(SOURCE),destination=str(TARGET),seconds=600,output_bytes=2<<30,memory_bytes=4<<30)))
