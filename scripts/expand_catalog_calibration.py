#!/usr/bin/env python3
"""Bounded positive-control prioritization from verified completed sweep inputs.

This diagnostic never refits thresholds, rejects public worlds or estimates seed
prevalence from the selectively enriched cases. All outputs stay outside the UI.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sqlite3
import sys
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
from seed_search.catalog.artifacts import ArtifactStore
from seed_search.catalog.geometry import anchors,inside,bounds_for
from seed_search.catalog.ingestion import atomic_json,strict_json_loads,verify_no_symlinks,tree_bytes
from seed_search.catalog.models import empty_observation_v2,validate_observation_v2
from seed_search.catalog.registry import digest


def validate_inputs(manifest):
    from seed_search.realm.runner import _seed
    if manifest.get('revision')!='catalog-expanded-calibration-inputs-v1' or len(manifest.get('rows',[]))>2000:
        raise ValueError('Invalid bounded completed-input manifest')
    if manifest.get('manifest_id')!=digest({k:v for k,v in manifest.items() if k!='manifest_id'}):
        raise ValueError('Input manifest digest differs')
    source=verify_no_symlinks(Path(manifest['source']))
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as conn:
        conn.execute('PRAGMA query_only=ON');conn.execute('BEGIN')
        original=json.loads(conn.execute("SELECT value FROM meta WHERE key='identity'").fetchone()[0])
        if digest(original)!=manifest['source_identity_id']:raise ValueError('Completed sweep identity changed')
        for row in manifest['rows']:
            index=int(row['index'])
            receipt=conn.execute('SELECT start,end,status,digest FROM ranges WHERE start<=? ORDER BY start DESC LIMIT 1',
                (f'{index:020d}',)).fetchone()
            if (receipt is None or receipt!=(row['range_start'],row['range_end'],'complete',row['range_digest'])
                    or not int(receipt[0])<=index<int(receipt[1]) or str(_seed(index,original['config']['search']))!=row['seed']):
                raise ValueError('Unverified completed input')


def triage(obs,backend,calibration):
    """Grid-only positive-control prioritization; no global absence conclusion."""
    sizes={side:list(anchors()) for side in (4096,8192)}
    order=('mansion','village','desert_pyramid','ancient_city','trial_chamber','ruined_portal',
           'shipwreck','monument','outpost','stronghold','mineshaft','fortress','bastion')
    for name in order:
        dimension='nether' if name in ('fortress','bastion') else 'overworld'
        box=obs['bounds'][dimension]
        points=backend.structures(name,(box[0],box[1],box[2]-1,box[3]-1),viable=True)
        obs['structures']['structure.'+name]=[list(p) for p in points]
        obs['coverage']['structure.'+name]=dict(status='partial' if name=='stronghold' else 'complete',
            bounds=list(box),method_id='predictor_bounded_strongholds_v2' if name=='stronghold' else 'predictor_viable_starts_v1')
        for side,centers in sizes.items():
            floor=1 if name=='fortress' else 2 if name=='bastion' else calibration['thresholds']['sizes'][str(side)][name]['thresholds'][0]
            kept=[]
            for center in centers:
                scope=bounds_for(center,side) if dimension=='overworld' else None
                # Nether has its own fixed1024-square contract.
                if dimension=='nether':
                    x,z=[n//8 for n in center];scope=[x-512,z-512,x+512,z+512]
                if sum(inside(x,z,scope) for x,z in points)>=floor:kept.append(center)
            sizes[side]=kept
        if not any(sizes.values()):return []
    return [side for side,centers in sizes.items() if centers]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--calibration',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    if not 10<=args.seconds<=600:raise ValueError('Explicit allocation10..600seconds')
    manifest=strict_json_loads(args.inputs.read_bytes());validate_inputs(manifest)
    calibration=strict_json_loads(args.calibration.read_bytes())
    from seed_search import _native
    from seed_search.backend import Backend,configure_native_threads,biome_name,native_runtime
    from seed_search.realm.biomes import canonical
    from seed_search.realm.native_identity import native_source_fingerprint
    from seed_search.catalog.extract import extract_observation_v2
    from seed_search.catalog.realm_observations import extract_realm_inventory
    from seed_search.catalog.harvest_native import _realm_layers_v2,save_checkpoint,checkpoint_observation
    from seed_search.catalog import realm_evaluation
    native_runtime();configure_native_threads(1)
    template=calibration['source_identity']
    if (hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest()!=template['native_sha256']
            or native_source_fingerprint()!=template['source_sha256']):raise ValueError('Current predictor differs')
    pin=dict(manifest_id=manifest['manifest_id'],calibration_id=digest(calibration),identity=template,
        evaluator_sha256=hashlib.sha256(Path(realm_evaluation.__file__).read_bytes()).hexdigest(),
        diagnostic_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    root=verify_no_symlinks(args.output.absolute());progress=root/'progress.json'
    if root.exists() and not args.resume:raise ValueError('Existing diagnostic requires explicit --resume')
    root.mkdir(parents=True,exist_ok=True);objects=ArtifactStore(root/'selected-control-objects')
    state=strict_json_loads(progress.read_bytes()) if progress.exists() else dict(
        revision='catalog-expanded-validation-v1',pin=pin,rows=[],controls=[],allocations=[],inflight=None)
    if state['pin']!=pin:raise ValueError('Input/predictor/frozen policy/diagnostic changed')
    started=time.monotonic();deadline=started+args.seconds;stop=threading.Event();active={'started':None}
    resource.setrlimit(resource.RLIMIT_CPU,(args.seconds+5,args.seconds+10));os.nice(10)
    def watchdog():
        while not stop.wait(.2):
            rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
            now=time.monotonic()
            if rss>4<<30 or now>deadline+2 or (active['started'] is not None and now-active['started']>122):os._exit(124)
    threading.Thread(target=watchdog,daemon=True).start()
    state['allocations'].append(dict(seconds=args.seconds,started_utc=time.time(),explicit_resume=args.resume));atomic_json(progress,state)
    checkpoint=root/'partial-control.json';enriched=0
    try:
        for row in manifest['rows'][len(state['rows']):]:
            if time.monotonic()>deadline-5 or enriched>=20 or tree_bytes(root)>=2<<30:break
            active['started']=time.monotonic();ident=dict(template,seed=row['seed']);observation=empty_observation_v2(ident)
            with Backend(row['seed']) as backend:
                sides=triage(observation,backend,calibration)
                record=dict(index=row['index'],seed=row['seed'],status='positive_control_unprioritized',grid_structure_sides=sides)
                if sides:
                    state['inflight']=dict(index=row['index'],seed=row['seed']);atomic_json(progress,state)
                    previous=checkpoint_observation(checkpoint,protocol=2) if checkpoint.exists() else observation
                    if previous['identity']!=ident:raise ValueError('Partial control identity differs')
                    previous['metrics'].pop('resource_stop',None)
                    observation=extract_observation_v2(ident,backend,previous=previous,name_for_id=lambda bid:canonical(biome_name(bid)))
                    save_checkpoint(checkpoint,observation)
                    extract_realm_inventory(observation,backend)
                    _realm_layers_v2(observation,backend,min(deadline,active['started']+120),lambda value:save_checkpoint(checkpoint,value))
                    if observation['metrics'].get('resource_stop'):atomic_json(progress,state);break
                    observation['realm']['native_pin']=calibration['native_realm_pin']
                    result=realm_evaluation.evaluate_large_realms(observation,calibration,seconds=5)
                    artifact=objects.put_json(validate_observation_v2(observation))
                    state['controls'].append(dict(index=row['index'],seed=row['seed'],observation_id=digest(observation),
                        artifact=artifact,evaluation=result,selection='structure-grid-prioritized positive control; not a prevalence sample'))
                    record['status']='selected_control_evaluated';enriched+=1
            state['rows'].append(record);state['inflight']=None;atomic_json(progress,state)
            checkpoint.unlink(missing_ok=True);active['started']=None
            if len(state['rows'])%100==0:print(json.dumps(dict(processed=len(state['rows']),controls=len(state['controls']),elapsed=round(time.monotonic()-started,2))),flush=True)
        state.update(complete=len(state['rows'])==len(manifest['rows']),last_elapsed_seconds=time.monotonic()-started)
        state['positive_controls']={side:sum(c['evaluation']['sizes'][side]['status']=='match' for c in state['controls']) for side in ('4096','8192')}
        atomic_json(progress,state)
        print(json.dumps(dict(processed=len(state['rows']),controls=len(state['controls']),complete=state['complete'],positive_controls=state['positive_controls'])),flush=True)
    finally:stop.set()


if __name__=='__main__':main()
