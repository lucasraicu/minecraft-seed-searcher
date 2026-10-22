#!/usr/bin/env python3
"""Correct per-mode legacy bindings and compact derived views within the original budget."""
import argparse
import copy
import json
import os
from pathlib import Path
import resource
import sqlite3
import sys
import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.harvest import HarvestQueue, _validate_rank
from seed_search.catalog import automation
from seed_search.catalog.registry import digest, canonical_json
from seed_search.catalog.ingestion import atomic_json,strict_json_loads,tree_bytes
from seed_search.catalog.retention import retain,objective_family
from scripts.reanchor_catalog import copy_history


def merge_offers(existing,pending,objectives):
    groups={}
    for member in existing:
        groups.setdefault(member['objective_id'],{})[member['world_id']]=member
    for wid,offers in pending:
        for off in offers:
            group=groups.setdefault(off['objective_id'],{});old=group.get(wid)
            if old is None or _validate_rank(off['rank'])<_validate_rank(old['rank']):group[wid]=dict(off,world_id=wid)
    members=[]
    for oid,group in sorted(groups.items()):
        members.extend(sorted(group.values(),key=lambda m:(_validate_rank(m['rank']),m['world_id']))[:objectives[oid]])
    return members


def process_tree_rss():
    rows=[tuple(map(int,line.split())) for line in subprocess.check_output(['/bin/ps','-axo','pid=,ppid=,rss='],text=True).splitlines()]
    owned={os.getpid()}
    for _ in range(4):owned.update(pid for pid,ppid,rss in rows if ppid in owned)
    return sum(rss*1024 for pid,ppid,rss in rows if pid in owned)


def legacy_grid_rows(rows):
    return [r['legacy'] for r in rows if 'recommended' in r['anchor_modes'] and r['legacy'].get('revision')=='catalog-summary-v1']


def prepare_world(root,source,destination,definition,entry,old_entry,kept,deadline):
    if time.monotonic()>=deadline:raise TimeoutError('Original correction deadline')
    store=AutomationStore(root);legacy_store=AutomationStore(source);target=AutomationStore(destination)
    rows=[];legacy_rows=[];changed=False
    for side in (2048,4096,8192):
        original_rows=legacy_store._projection(old_entry,side)
        by_mode={(tuple(r['anchor']),tuple(r['anchor_modes'])):r['legacy'] for r in original_rows}
        for row in store._projection(entry,side):
            value=by_mode[(tuple(row['anchor']),tuple(row['anchor_modes']))]
            changed|=row['legacy']!=value;row['legacy']=value;rows.append(row)
        legacy_rows.extend(legacy_grid_rows(original_rows))
    updated=dict(entry)
    if changed:
        bundle=store.artifacts.get_json(entry['artifact'])
        assert digest(bundle['observation'])==entry['observation_id']
        # All unchanged feature/source fields come from source-bound writer-validated V4 projections; legacy replacements were strictly validated against the original mode-specific V2 rows.
        updated['artifact']=target.artifacts.put_json(dict(bundle,summaries=rows),compression_level=1)
    refs={}
    for side in (2048,4096,8192):
        chosen=[r for r in rows if r['border_side']==side]
        value=dict(revision='catalog-query-projection-v5',registry=definition,sampling_profile_revision=entry['sampling_profile_revision'],source_extension_id=entry['source_extension_id'],world_id=entry['world_id'],identity=entry['identity'],observation_id=entry['observation_id'],bundle_sha256=updated['artifact']['sha256'],summary_validator_sha256=target._query_validator_id(),row_count=len(chosen),border_side=side,rows=target._pack_query_rows(chosen,definition))
        refs[str(side)]=target.artifacts.put_json(value,compression_level=1)
    updated['summary_artifacts']=refs
    selected=retain(legacy_rows,[entry['identity']]);grid={r['layout_id']:r for r in legacy_rows};offers=list(kept)
    for objective,members in selected['objectives'].items():
        for member in members:
            rank=list(member['rank'])
            if member.get('layout_id') is not None:
                layout=grid[member['layout_id']];rank[-1]=digest(['automation-anchor-v2',entry['world_id'],layout['anchor'],layout['border_side']])
            if objective_family(objective) in ('profiles','diversity'):rank[0]=dict(decimal=rank[0])
            offers.append(dict(objective_id=objective,rank=rank,member=dict(member,rank=rank,source_observation_id=entry['observation_id'])))

    if time.monotonic()>=deadline:raise TimeoutError('Original correction deadline')
    return updated,offers,changed


def run(root,source,destination):
    root=Path(root).absolute();source=Path(source).absolute();destination=Path(destination).absolute()
    if len({root,source,destination})!=3 or any(a in b.parents for a in (root,source,destination) for b in (root,source,destination) if a!=b):raise ValueError('Disjoint roots required')
    started=time.monotonic();store=AutomationStore(root);legacy_store=AutomationStore(source)
    migration_path=root/'automation/biome-expansion-progress.json';migration=strict_json_loads(migration_path.read_bytes())
    if not migration['complete'] or migration['total_budget_seconds']!=3600:raise ValueError('Completed bounded migration required')
    path=root/'automation/biome-projection-progress.json'
    current=store.snapshot();legacy=legacy_store.snapshot();pin=digest([migration['publication'],digest(legacy),str(destination)])
    old_config=strict_json_loads((root/'automation/configuration.json').read_bytes())
    if path.exists():state=strict_json_loads(path.read_bytes())
    else:
        state=dict(revision='catalog-biome-correction-v1',pin=pin,consumed_seconds=migration['consumed_seconds'],worlds=[],complete=False)
        atomic_json(path,state)
    if state['pin']!=pin:raise ValueError('Correction input changed')
    if state['complete']:return state
    approval_path=destination/'automation/biome-correction-budget-approval.json'
    budget=3600
    if approval_path.exists():
        approval=strict_json_loads(approval_path.read_bytes())
        if (approval.get('revision')!='catalog-biome-budget-amendment-v1' or approval.get('pin')!=pin or approval.get('original_total_seconds')!=3600 or approval.get('additional_seconds')!=180 or approval.get('total_seconds')!=3780 or approval.get('approval')!='Approve additional 180 seconds'):raise ValueError('Invalid bounded budget approval')
        budget=approval['total_seconds']
    initial=state['consumed_seconds']
    resource.setrlimit(resource.RLIMIT_CPU,(max(1,int(budget-initial)+5),max(1,int(budget-initial)+10)))
    def spent():return initial+time.monotonic()-started
    last_output_check=[0.]
    def guard():
        output_exceeded=False
        if time.monotonic()-last_output_check[0]>10:
            output_exceeded=tree_bytes(root)+(tree_bytes(destination) if destination.exists() else 0)>2<<30;last_output_check[0]=time.monotonic()
        if spent()>=budget or process_tree_rss()>4<<30 or output_exceeded:raise TimeoutError('Original migration budget/caps exhausted; no reset')
    guard()
    if not destination.exists():
        if 2*tree_bytes(root)+(100<<20)>2<<30:raise ValueError('Preserved history and correction output exceed preflight cap')
        state['consumed_seconds']=spent()+15;atomic_json(path,state)
        destination.mkdir();copy_history(root,destination)
        automation.configure(destination,old_config['identity'],old_config['options'],catalog_registry=current['registry'])
        automation.control(destination,'pause');state['consumed_seconds']=spent();atomic_json(path,state)
    target=AutomationStore(destination);config=automation.configuration(destination)
    originals={e['world_id']:e for e in legacy['worlds']};keep={e['world_id']:[] for e in current['worlds']}
    for member in current['memberships']:
        # The legacy families are rebuilt from every saved world's original grid.
        if member['objective_id'].startswith(('v2.','v3.','realm.','preset.','record.')):keep[member['world_id']].append(dict(objective_id=member['objective_id'],rank=member['rank'],member=member['member']))
    original_db=sqlite3.connect((root/'harvest.sqlite').as_uri()+'?mode=ro',uri=True)
    manifest=dict(current);manifest['policy_revision']=config['policy_revision'];manifest['worlds']=[]
    pool=ProcessPoolExecutor(max_workers=8,mp_context=multiprocessing.get_context('spawn'))
    futures={i:pool.submit(prepare_world,root,source,destination,current['registry'],entry,originals[entry['world_id']],keep[entry['world_id']],started+budget-initial-8) for i,entry in enumerate(current['worlds']) if i>=len(state['worlds'])}
    try:
        with HarvestQueue(destination) as queue,queue.supervisor() as acquired,queue.ownership():
            if not acquired:raise ValueError('Writer already active')
            ledger=automation._ledger(queue,config)
            # Destination is a pinned correction prefix, never an inherited ledger.
            allowed={e['world_id']:e for e in current['worlds'][:len(state['worlds'])+1]}
            for wid,oid in queue.conn.execute('SELECT world_id,observation_id FROM automation_receipts'):
                if wid not in allowed or oid!=allowed[wid]['observation_id']:raise ValueError('Unexpected correction receipt outside pinned prefix')
            pending=[]
            for i,entry in enumerate(current['worlds']):
                if i<len(state['worlds']):
                    saved=state['worlds'][i]
                    if saved['entry']['world_id']!=entry['world_id'] or queue.conn.execute('SELECT 1 FROM automation_receipts WHERE world_id=?',(entry['world_id'],)).fetchone() is None:raise ValueError('Correction cursor differs')
                    manifest['worlds'].append(saved['entry'])
                    if saved.get('offers_artifact'):pending.append((saved['entry']['world_id'],target.artifacts.get_json(saved['offers_artifact'])['offers']))
                    continue
                guard()
                if budget-spent()<12:raise TimeoutError('Publication allowance unavailable')
                state['consumed_seconds']=spent()+8;atomic_json(path,state);begin=time.monotonic()
                updated,offers,changed=futures[i].result(timeout=max(.01,budget-spent()-8))
                evaluations,replay=original_db.execute('SELECT evaluations,replay FROM automation_receipts WHERE world_id=?',(entry['world_id'],)).fetchone()
                receipt=dict(world_id=entry['world_id'],identity=entry['identity'],observation_id=entry['observation_id'],artifact=updated['artifact'],evaluations=strict_json_loads(evaluations),replay=dict(strict_json_loads(replay),legacy_mode_binding_corrected=True))
                # Persist one bounded, source-bound offer batch per world.  Merge each
                # objective once at publication instead of repeatedly reading/sorting
                # its entire heap for every world's offer.  Checkpoints remain replayable.
                for off in offers:
                    if off['objective_id'] not in ledger.objectives or off['member']['world_id']!=entry['world_id'] or off['member'].get('source_observation_id',entry['observation_id'])!=entry['observation_id']:raise ValueError('Unbound bulk offer')
                    _validate_rank(off['rank'])
                offer_artifact=target.artifacts.put_json(dict(revision='catalog-correction-offers-v1',offers=offers),compression_level=1)
                with queue.transaction():
                    queue.conn.execute('INSERT INTO automation_receipts VALUES(?,?,?,?,?,?) ON CONFLICT(world_id) DO UPDATE SET identity=excluded.identity,observation_id=excluded.observation_id,artifact=excluded.artifact,evaluations=excluded.evaluations,replay=excluded.replay',tuple(receipt[k] if k in ('world_id','observation_id') else canonical_json(receipt[k]).decode() for k in ('world_id','identity','observation_id','artifact','evaluations','replay')))
                pending.append((entry['world_id'],offers));manifest['worlds'].append(updated)
                if time.monotonic()-begin>8:raise TimeoutError('Bounded correction world allowance exceeded')
                state['worlds'].append(dict(entry=updated,changed_legacy=changed,offers_artifact=offer_artifact));state['consumed_seconds']=spent();atomic_json(path,state)
                if (i+1)%25==0:print(json.dumps(dict(worlds=i+1,cumulative_seconds=spent())),flush=True)
            guard();state['consumed_seconds']=budget;atomic_json(path,state)
            # All durable batches are idempotent: choose the best exact typed rank
            # per (objective,world), then take the declared 2K capacity per objective.
            members=merge_offers(ledger.members(),pending,ledger.objectives)
            with queue.transaction():
                queue.conn.execute('DELETE FROM automation_members')
                queue.conn.executemany('INSERT INTO automation_members VALUES(?,?,?,?)',((m['objective_id'],m['world_id'],canonical_json(m['rank']).decode(),canonical_json(m['member']).decode()) for m in members))
                queue.conn.execute("UPDATE automation_meta SET value=? WHERE key='generation'",(str(ledger.generation()+1),))
            manifest['memberships']=members;manifest['generation']=ledger.generation();target._manifest(manifest);sid=digest(manifest)
            artifact=target._write_manifest(manifest,compression_level=1);binding=dict(revision='catalog-snapshot-binding-v2',snapshot_id=sid,generation=manifest['generation'],artifact=artifact)
            guard();atomic_json(target.generations_dir/(manifest['policy_revision']+'-'+str(manifest['generation'])+'.json'),binding)
            atomic_json(target.snapshots_dir/(sid+'.json'),binding);atomic_json(target.current_path,binding)
            guard();state.update(complete=True,snapshot_id=sid,consumed_seconds=spent(),bytes=tree_bytes(root)+tree_bytes(destination),corrected_worlds=sum(r['changed_legacy'] for r in state['worlds']));atomic_json(path,state)
            final=dict(migration,total_budget_seconds=budget,original_total_budget_seconds=3600,additional_budget_seconds=budget-3600,publication=sid,consumed_seconds=spent(),bytes=tree_bytes(destination),original_publication=migration['publication'],correction_root=str(destination),aggregate_output_bytes=state['bytes'])
            atomic_json(destination/'automation/biome-expansion-progress.json',final)
            print(json.dumps(dict(complete=True,snapshot_id=sid,cumulative_seconds=spent(),aggregate_output_bytes=state['bytes'],corrected_worlds=state['corrected_worlds'])),flush=True)
    finally:
        pool.shutdown(wait=True,cancel_futures=True)
        original_db.close()
    return state

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--source',required=True);p.add_argument('--destination',required=True);a=p.parse_args();run(a.root,a.source,a.destination)
