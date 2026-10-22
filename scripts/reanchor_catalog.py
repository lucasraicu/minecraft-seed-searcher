#!/usr/bin/env python3
"""Re-anchor an immutable catalog into a separate policy workspace; no extraction."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import sqlite3
import sys
import threading
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[name]='1'
from seed_search.catalog import automation
from seed_search.catalog.anchors import validate_anchor
from seed_search.catalog.harvest import HarvestQueue,AutomationLedger
from seed_search.catalog.ingestion import atomic_json,strict_json_loads,tree_bytes,verify_no_symlinks
from seed_search.catalog.models import validate_observation_v2,world_id
from seed_search.catalog.product_evaluation import evaluate_products
from seed_search.catalog.registry import digest
from seed_search.catalog.retention import automation_objectives,automation_offers
from seed_search.catalog.spawn_estimator import SpawnEstimator
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.summaries import summarize_v2


def reanchor_observation(original,anchor):
    validate_observation_v2(original);anchor=validate_anchor(anchor)
    if anchor['context']['identity']!=original['identity'] or anchor['mode']!='world_spawn_estimated':
        raise ValueError('Expected a predicted world anchor for this exact world identity')
    indices=[i for i,a in enumerate(original['anchors']) if a['mode']=='world_spawn_estimated']
    if len(indices)!=1:raise ValueError('Expected exactly one original estimated anchor')
    changed=copy.deepcopy(original)
    changed['anchors'][indices[0]]=dict(mode=anchor['mode'],coordinate=anchor['coordinate'],source_id=anchor['anchor_id'])
    validate_observation_v2(changed)
    return changed


def reanchor_summaries(before,after,previous):
    """Reuse unchanged grid facts; derive only spawn/refined-center rows.

    This CLI is single-threaded. Temporarily suppress only the fixed-grid iterator
    in its private process; the existing implementation still derives every new
    numeric row. No serving/extraction module or policy fingerprint changes.
    """
    from seed_search.catalog import summaries as module
    if {k:v for k,v in before.items() if k!='anchors'}!={k:v for k,v in after.items() if k!='anchors'}:
        raise ValueError('Legacy raw facts changed; grid reuse is not valid')
    required={(tuple(c),s) for c in module.anchors() for s in (2048,4096,8192)}
    available={(tuple(r['anchor']),r['border_side']) for r in previous if 'recommended' in r['anchor_modes']}
    if not required<=available:raise ValueError('Missing fixed-grid summaries')
    oid=digest(after);rows={}
    for old in previous:
        if 'recommended' not in old['anchor_modes']:continue
        row=copy.deepcopy(old);row['source_observation_id']=oid
        row['layout_id']=digest(['catalog-summary-v2',oid,row['anchor'],row['anchor_modes'],row['border_side']])
        rows[row['layout_id']]=row
    by_geometry={(tuple(r['anchor']),r['border_side']):r for r in previous}
    all_cached=True
    for anchor in after['anchors']:
        if anchor['mode'] not in ('world_spawn_estimated','world_spawn_observed'):continue
        for side in (2048,4096,8192):
            old=by_geometry.get((tuple(anchor['coordinate']),side))
            if old is None:
                all_cached=False;continue
            row=copy.deepcopy(old);row['source_observation_id']=oid;row['anchor_modes']=[anchor['mode']]
            row['layout_id']=digest(['catalog-summary-v2',oid,row['anchor'],row['anchor_modes'],side])
            rows[row['layout_id']]=row
    if all_cached:return list(rows.values())
    with patch.object(module,'anchors',lambda:()):
        fresh=module.summarize_v2(after)
    for row in fresh:
        old=rows.get(row['layout_id'])
        if old is not None and old!=row:raise ValueError('Recomputed center differs from reused grid')
        rows[row['layout_id']]=row
    return list(rows.values())


def committed_migration(store,ledger,wid,oid,pin,observation):
    """Recover a COMMIT-before-cursor interruption without re-offering a world."""
    committed=ledger.receipt(wid)
    if committed is not None:
        if committed['observation_id']!=oid or committed['replay'].get('migration_pin')!=pin:
            raise ValueError('Conflicting previously committed migration receipt')
        if store._bundle(store.artifacts.get_json(committed['artifact']))['observation']!=observation:
            raise ValueError('Committed world differs from re-anchored source')
    return committed


def copy_history(source,destination):
    """Copy immutable history, not the old mutable queue/config/current pointer."""
    for name in ('artifacts','accuracy','evidence','product-previews'):
        if (source/name).exists():shutil.copytree(source/name,destination/name)
    if (source/'pilot.sqlite').exists():
        with sqlite3.connect((source/'pilot.sqlite').as_uri()+'?mode=ro',uri=True) as old:
            with sqlite3.connect(destination/'pilot.sqlite') as new:old.backup(new)
    for name in ('objects','snapshots','generations'):
        if (source/'automation'/name).exists():
            shutil.copytree(source/'automation'/name,destination/'automation'/name)
    if (source/'automation/pins.json').exists():
        shutil.copy2(source/'automation/pins.json',destination/'automation/pins.json')


def run(source,destination,estimator_path,*,seconds=600,resume=False):
    if type(seconds)is not int or not 10<=seconds<=600:raise ValueError('Allocation10..600seconds')
    source=verify_no_symlinks(source.absolute());destination=verify_no_symlinks(destination.absolute())
    if source==destination or source in destination.parents or destination in source.parents:
        raise ValueError('Migration requires disjoint roots')
    old_store=AutomationStore(source);manifest=old_store.snapshot();source_sid=digest(manifest)
    if len(manifest['worlds'])!=222 or len({r['world_id'] for r in manifest['worlds']})!=222:
        raise ValueError('Expected the approved222 unique source worlds')
    build=strict_json_loads(Path(str(estimator_path)+'.build.json').read_bytes())
    original=automation.configuration(source)
    options=copy.deepcopy(original['options']);options['spawn']=dict(executable=str(estimator_path.absolute()),
        binary_sha256=build['binary_sha256'],source_sha256=build['source_sha256'])
    estimator=SpawnEstimator(**options['spawn'])
    pin=digest([source_sid,original,options])
    started=time.monotonic();deadline=started+seconds
    if not resume:
        destination.mkdir(parents=True,exist_ok=False)
        copy_history(source,destination)
        automation.configure(destination,original['identity'],options)
        automation.control(destination,'pause')
        atomic_json(destination/'automation/reanchor-progress.json',dict(revision='catalog-reanchor-v1',pin=pin,
            source_root=str(source),source_snapshot_id=source_sid,worlds=[],allocations=[]))
    config=automation.configuration(destination)
    if config['options']!=options:raise ValueError('Migration estimator/native options changed')
    path=destination/'automation/reanchor-progress.json'
    state=strict_json_loads(path.read_bytes())
    if state['pin']!=pin:raise ValueError('Migration input or helper changed')
    state['allocations'].append(dict(seconds=seconds,started_utc=time.time(),resume=resume))
    atomic_json(path,state)
    resource.setrlimit(resource.RLIMIT_CPU,(seconds+5,seconds+10));os.nice(10)
    done=threading.Event()
    def watchdog():
        while not done.wait(.2):
            rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)
            if time.monotonic()>=deadline or rss>4<<30:os._exit(124)
    threading.Thread(target=watchdog,daemon=True).start()
    store=AutomationStore(destination)
    try:
        with HarvestQueue(destination) as queue,queue.supervisor() as acquired,queue.ownership():
            if not acquired:raise ValueError('Migration workspace already has a supervisor')
            ledger=AutomationLedger(queue,policy_revision=config['policy_revision'],objectives=automation_objectives())
            for i,row in enumerate(state['worlds']):
                receipt=ledger.receipt(row['world_id'])
                if row['world_id']!=manifest['worlds'][i]['world_id'] or receipt is None or receipt['observation_id']!=row['new_observation_id']:
                    raise ValueError('Progress cursor does not match committed input receipts')
            for entry in manifest['worlds'][len(state['worlds']):]:
                if time.monotonic()>=deadline-30 or tree_bytes(destination)>=2<<30:break
                bundle=old_store._bundle(old_store.artifacts.get_json(entry['artifact']),entry)
                before=bundle['observation'];anchor=estimator.estimate(before['identity'])
                after=reanchor_observation(before,anchor);oid=digest(after);wid=world_id(after['identity'])
                assert {k:v for k,v in before.items() if k!='anchors'}=={k:v for k,v in after.items() if k!='anchors'}
                committed=committed_migration(store,ledger,wid,oid,pin,after)
                if committed is not None:
                    summaries=None
                else:
                    summaries=reanchor_summaries(before,after,bundle['summaries']);evaluations=evaluate_products(after)
                old_grid={(tuple(s['anchor']),s['border_side']):s for s in bundle['summaries'] if 'recommended' in s['anchor_modes']}
                for summary in summaries or []:
                    if 'recommended' in summary['anchor_modes']:
                        old=old_grid[(tuple(summary['anchor']),summary['border_side'])]
                        assert {k:v for k,v in old.items() if k not in ('layout_id','source_observation_id')}=={k:v for k,v in summary.items() if k not in ('layout_id','source_observation_id')}
                if committed is None:
                    artifact=store.stage(after,summaries)
                    receipt=dict(world_id=wid,identity=after['identity'],observation_id=oid,artifact=artifact,
                        evaluations=evaluations,replay=dict(resumable=False,migration_pin=pin,
                            source_snapshot_id=source_sid,source_observation_id=entry['observation_id'],anchor_evidence=anchor))
                    ledger.offer(receipt,automation_offers(after,summaries,evaluations))
                state['worlds'].append(dict(world_id=wid,seed=after['identity']['seed'],
                    old_observation_id=entry['observation_id'],new_observation_id=oid,
                    old_anchor=next(a for a in before['anchors'] if a['mode']=='world_spawn_estimated'),
                    new_anchor=anchor['coordinate'],new_anchor_id=anchor['anchor_id']))
                atomic_json(path,state)
                if len(state['worlds'])%20==0:
                    print(json.dumps(dict(worlds=len(state['worlds']),seconds=time.monotonic()-started)),flush=True)
            if len(state['worlds'])!=222:
                raise TimeoutError('Migration allocation exhausted; durable receipts/progress preserved')
            assert ledger.population()==222 and ledger.generation()==222
            sid=store.publish(ledger)
            state.update(complete=True,snapshot_id=sid,seconds=time.monotonic()-started,
                policy_revision=config['policy_revision'],published_worlds=len(store.snapshot(sid)['worlds']))
            assert state['published_worlds']==222
            atomic_json(path,state)
            print(json.dumps({k:v for k,v in state.items() if k!='worlds'},indent=2),flush=True)
            return state
    finally:done.set()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--estimator',type=Path,required=True);parser.add_argument('--seconds',type=int,default=600)
    parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    run(args.source,args.destination,args.estimator,seconds=args.seconds,resume=args.resume)
