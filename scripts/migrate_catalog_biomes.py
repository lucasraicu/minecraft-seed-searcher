#!/usr/bin/env python3
"""Approved bounded v3 migration of saved worlds into a separate policy root."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import resource
import sqlite3
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[key]='1'
from seed_search.catalog import automation
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.harvest import HarvestQueue
from seed_search.catalog.registry import digest,SAMPLING_PROFILE_REVISION_V3
from seed_search.catalog.ingestion import atomic_json,strict_json_loads,tree_bytes,verify_no_symlinks
from seed_search.catalog.models import world_id
from seed_search.catalog.biome_extension import extract_extension
from seed_search.catalog.summaries import summarize_v3
from seed_search.catalog.retention import automation_offers_v3
from seed_search.backend import Backend,biome_name,configure_native_threads
from seed_search.realm.biomes import canonical
from scripts.reanchor_catalog import copy_history

OUTPUT_CAP=2<<30
TOTAL_SECONDS=3600
WORLD_SECONDS=120


def run(source,destination,registry_path,*,resume=False):
    source=verify_no_symlinks(Path(source).absolute());destination=verify_no_symlinks(Path(destination).absolute())
    if source==destination or source in destination.parents or destination in source.parents:raise ValueError('Disjoint policy roots required')
    registry_data=Path(registry_path).read_bytes()
    if len(registry_data)>16<<20:raise ValueError('Registry artifact cap')
    registry=strict_json_loads(registry_data)
    source_store=AutomationStore(source);manifest=source_store.snapshot();sid=digest(manifest)
    if len(manifest['worlds'])!=222:raise ValueError('Approved222-world source cohort required')
    old_config=automation.configuration(source)
    options=copy.deepcopy(old_config['options']);pin=digest([sid,registry,old_config])
    # Conservative measured preflight: 2MiB/world bundle+projections and twice
    # the fully expanded membership envelope at 1KiB/slot, plus copied history.
    expected=tree_bytes(source)+len(manifest['worlds'])*(2<<20)+231928*1024*2
    if expected>OUTPUT_CAP:raise ValueError('Migration preflight exceeds2GiB output cap')
    state_path=destination/'automation/biome-expansion-progress.json'
    if not resume:
        destination.mkdir(parents=True,exist_ok=False);copy_history(source,destination)
        automation.configure(destination,old_config['identity'],options,catalog_registry=registry)
        automation.control(destination,'pause')
        atomic_json(state_path,dict(revision='catalog-biome-migration-v3',pin=pin,source_snapshot_id=sid,
            total_budget_seconds=TOTAL_SECONDS,consumed_seconds=0.,worlds=[],complete=False,publication=None,
            preflight_bytes=expected,started_utc=time.time()))
    state=strict_json_loads(state_path.read_bytes())
    if state['pin']!=pin or state['total_budget_seconds']!=TOTAL_SECONDS:raise ValueError('Migration input/budget differs')
    config=automation.configuration(destination)
    if automation.policy_registry(destination,config)!=registry:raise ValueError('Destination registry differs')
    store=AutomationStore(destination);configure_native_threads(1);os.nice(10)
    started=time.monotonic();initial_spent=state['consumed_seconds'];allocation=max(0,TOTAL_SECONDS-initial_spent)
    resource.setrlimit(resource.RLIMIT_CPU,(max(1,int(allocation)+5),max(1,int(allocation)+10)))
    def guard():
        spent=initial_spent+time.monotonic()-started
        if spent>=TOTAL_SECONDS or tree_bytes(destination)>OUTPUT_CAP or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>4<<30:raise TimeoutError('Migration budget exhausted; durable cursor retained')
        return spent
    original_db=sqlite3.connect((source/'harvest.sqlite').as_uri()+'?mode=ro',uri=True)
    try:
        with HarvestQueue(destination) as queue,queue.supervisor() as acquired,queue.ownership():
            if not acquired:raise ValueError('Destination worker already running')
            ledger=automation._ledger(queue,config)
            for index,entry in enumerate(manifest['worlds']):
                wid=entry['world_id'];receipt=ledger.receipt(wid)
                if index<len(state['worlds']):
                    if state['worlds'][index]['world_id']!=wid or receipt is None or receipt['observation_id']!=entry['observation_id']:raise ValueError('Cursor differs from committed receipts')
                    continue
                spent=guard()
                if TOTAL_SECONDS-spent<150:break
                # Charge the full bounded operation before starting; a crash
                # conservatively retains this reservation instead of resetting it.
                state['consumed_seconds']=spent+WORLD_SECONDS;atomic_json(state_path,state)
                begin=time.monotonic()
                if receipt is not None:
                    if receipt['replay'].get('migration_pin')!=pin or receipt['observation_id']!=entry['observation_id']:raise ValueError('Conflicting committed receipt')
                    row=dict(world_id=wid,seed=entry['identity']['seed'],observation_id=entry['observation_id'],recovered=True)
                else:
                    bundle=source_store._bundle(source_store.artifacts.get_json(entry['artifact']),entry)
                    original=bundle['observation'];before=digest(original)
                    with Backend(original['identity']['seed']) as backend:
                        extension=extract_extension(original,backend,name_for_id=lambda n:canonical(biome_name(n)),deadline=begin+WORLD_SECONDS)
                    summaries=summarize_v3(original,extension=extension,base_summaries=bundle['summaries'],registry=registry)
                    if digest(original)!=before:raise ValueError('Frozen observation changed')
                    old=original_db.execute('SELECT evaluations FROM automation_receipts WHERE world_id=?',(wid,)).fetchone()
                    if old is None:raise ValueError('Original evaluation receipt missing')
                    evaluations=strict_json_loads(old[0])
                    artifact=store.stage(original,summaries,extension=extension,registry_v3=registry)
                    receipt=dict(world_id=wid,identity=original['identity'],observation_id=before,artifact=artifact,
                        evaluations=evaluations,replay=dict(resumable=False,migration_pin=pin,source_snapshot_id=sid,
                            source_observation_id=before,historically_complete=False))
                    offers=automation_offers_v3(original,summaries,evaluations,registry=registry)
                    if time.monotonic()-begin>WORLD_SECONDS:raise TimeoutError('Migration world cap')
                    ledger.offer(receipt,offers)
                    row=dict(world_id=wid,seed=original['identity']['seed'],observation_id=before,
                        source_extension_id=digest(extension) if extension else None,
                        extra_points=len(extension['biomes']['overworld']) if extension else 0,
                        offers=len(offers),summary_bytes=len(json.dumps(summaries,separators=(',',':'))),
                        artifact_bytes=artifact['byte_length'],realm_sha256=digest(original['realm']),
                        structures_sha256=digest(original['structures']),evaluations_sha256=digest(evaluations))
                row['wall_seconds']=time.monotonic()-begin;state['worlds'].append(row)
                state['consumed_seconds']=guard();atomic_json(state_path,state)
                print(json.dumps(dict(worlds=len(state['worlds']),total=222,consumed_seconds=state['consumed_seconds'],last_seconds=row['wall_seconds'])),flush=True)
            if len(state['worlds'])==222:
                guard();remaining=TOTAL_SECONDS-guard();state['consumed_seconds']=TOTAL_SECONDS;atomic_json(state_path,state)
                # Publication may page but never raises the existing artifact caps.
                published=automation.publish(store,ledger,config)
                state.update(consumed_seconds=guard(),complete=True,publication=published,bytes=tree_bytes(destination),finished_utc=time.time())
                atomic_json(state_path,state)
                print(json.dumps(dict(complete=True,snapshot_id=published,seconds=state['consumed_seconds'],bytes=state['bytes'])),flush=True)
    finally:original_db.close()
    return state


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--destination',required=True);p.add_argument('--registry',required=True);p.add_argument('--resume',action='store_true');a=p.parse_args()
    result=run(a.source,a.destination,a.registry,resume=a.resume)
    if not result['complete']:raise SystemExit('Migration checkpoint retained; budget or work remains')
if __name__=='__main__':main()
