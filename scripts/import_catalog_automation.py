#!/usr/bin/env python3
"""Replay verified saved observations into the additive public automation sidecar.

No seed discovery: inputs are completed calibration artifacts. A durable cursor
follows membership commits; publication is replayed before continuing after a crash.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import resource
import sys
import time
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[key] = '1'

from seed_search.catalog import automation
from seed_search.catalog.artifacts import ArtifactStore
from seed_search.catalog.harvest import HarvestQueue, AutomationLedger
from seed_search.catalog.ingestion import atomic_json, strict_json_loads, tree_bytes
from seed_search.catalog.models import validate_observation_v2, world_id
from seed_search.catalog.product_evaluation import evaluate_products
from seed_search.catalog.realm_evaluation import load_calibration, RealmScene
from seed_search.catalog.registry import digest
from seed_search.catalog.retention import automation_objectives, automation_offers
from seed_search.catalog.spawn_estimator import SpawnEstimator
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.summaries import summarize_v2


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--seconds', type=int, default=600)
    p.add_argument('--resume', action='store_true')
    args = p.parse_args()
    if not 10 <= args.seconds <= 600:
        raise ValueError('Explicit allocation must be10..600seconds')
    base = args.evidence.absolute(); root = args.root.absolute()
    original = strict_json_loads((base/'calibration-ready/progress.json').read_bytes())
    saved = strict_json_loads((base/'calibration-optimized-validation.json').read_bytes())
    controls = strict_json_loads((base/'expanded-calibration-controls/progress.json').read_bytes())
    candidate = strict_json_loads((base/'realm-calibration-candidate.json').read_bytes())
    active = load_calibration()
    if active is None or active['thresholds'] != candidate['thresholds']:
        raise ValueError('Calibration thresholds changed after validation')
    if not all(v.get('complete') is True for v in (original, saved, controls)):
        raise ValueError('Input evidence is incomplete')
    saved_by_seed = {r['seed']:r for r in saved['worlds']}
    inputs = [(base/'calibration-ready/objects', r, saved_by_seed[r['seed']]['evaluation'],
               'existing200catalog:' + r['split']) for r in original['worlds']]
    inputs += [(base/'expanded-calibration-controls/selected-control-objects', r, r['evaluation'],
                r['selection']) for r in controls['controls']]
    # The independently replayed personal control supplies the2048 positive.
    known_store = AutomationStore(base/'native-v2-validation-r3-fast')
    known = next(known_store.iter_worlds(digest(known_store.snapshot())))['observation']
    inputs.append((None, dict(observation=known, observation_id=digest(known)), None,
                   'selected known personal control; not a prevalence sample'))
    seeds = [r.get('seed', r.get('observation', {}).get('identity', {}).get('seed')) for _,r,_,_ in inputs]
    if len(set(seeds)) != len(seeds):
        raise ValueError('Duplicate input world')
    old_config = strict_json_loads((base/'native-v2-validation-r3-fast/automation/configuration.json').read_bytes())
    if automation.configuration(root) is None:
        automation.configure(root, original['identity'], old_config['options'])
    config = automation.configuration(root)
    automation.control(root, 'pause')
    pin = digest([config, active, original, saved, controls, digest(known)])
    progress = root/'automation/import-progress.json'
    if progress.exists() and not args.resume:
        raise ValueError('Existing import requires explicit --resume')
    state = strict_json_loads(progress.read_bytes()) if progress.exists() else dict(
        revision='catalog-saved-observation-import-v1', pin=pin, worlds=[], allocations=[])
    if state['pin'] != pin:
        raise ValueError('Import policy or saved inputs changed')
    estimator = SpawnEstimator(**config['options']['spawn'])
    prototype = None
    started = time.monotonic(); deadline = started + args.seconds
    resource.setrlimit(resource.RLIMIT_CPU, (args.seconds+5, args.seconds+10))
    def watchdog():
        while time.monotonic()<deadline:
            rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform=='darwin' else 1024)
            if rss>4<<30:os._exit(124)
            time.sleep(.2)
        # Cursor and CAS/SQLite atomic publication are resumable at any window.
        os._exit(124)
    threading.Thread(target=watchdog,daemon=True).start()
    os.nice(10)
    state['allocations'].append(dict(seconds=args.seconds, started_utc=time.time(), explicit_resume=args.resume))
    atomic_json(progress, state)
    store = AutomationStore(root)
    checkpoint = root/'automation/import-current.json'
    with HarvestQueue(root) as queue, queue.supervisor() as acquired, queue.ownership():
        if not acquired:
            raise ValueError('Public worker is already active')
        ledger = AutomationLedger(queue, policy_revision=config['policy_revision'], objectives=automation_objectives())
        published_generation=None;published_snapshot=None
        if ledger.generation():
            published_snapshot=store.publish(ledger);published_generation=ledger.generation()
        for source,row,evaluation,selection in inputs[len(state['worlds']):]:
            if time.monotonic() > deadline-10 or tree_bytes(root) >= 2<<30:
                break
            obs = copy.deepcopy(row['observation']) if source is None else ArtifactStore(source).get_json(row['artifact'])
            validate_observation_v2(obs)
            if digest(obs) != row['observation_id'] or dict(obs['identity'], seed='0') != config['identity']:
                raise ValueError('Saved observation identity/checksum changed')
            if evaluation is not None and evaluation['calibration_id'] != digest(candidate):
                raise ValueError('Saved search belongs to another calibration')
            prepared = strict_json_loads(checkpoint.read_bytes()) if checkpoint.exists() else None
            if prepared is not None and prepared['index']==len(state['worlds']):
                if prepared['pin']!=pin or prepared['source_id']!=row['observation_id'] or digest(prepared['observation'])!=prepared['observation_id']:
                    raise ValueError('Import checkpoint changed')
                obs = validate_observation_v2(prepared['observation'])
            if not any(a['mode']=='world_spawn_estimated' for a in obs['anchors']):
                anchor = estimator.estimate(obs['identity'])
                obs['anchors'].append(dict(mode=anchor['mode'],coordinate=anchor['coordinate'],source_id=anchor['anchor_id']))
            if not (obs.get('realm') or {}).get('evaluation'):
                from seed_search.realm.native_batch import Prototype
                from seed_search.realm.config import dynamic_v3_blueprint_config
                cfg = dynamic_v3_blueprint_config()
                if prototype is None:
                    prototype = Prototype(config['options']['native_build'], cfg)
                with prototype.sweep([int(obs['identity']['seed'])], threads=1, retention='survivors', max_misses=0, refine_centers=True) as batch:
                    records = batch.retained_records()
                native = records[0] if records else dict(anchors=[])
                native['execution_complete'] = True
                obs.setdefault('realm', {}).update(evaluation=native,config_digest=digest(cfg),native_pin=config['options']['native_pin'])
            if evaluation is not None and not (prepared is not None and prepared['index']==len(state['worlds'])):
                scene = RealmScene(obs, active); refreshed = {}
                for side,result in evaluation['sizes'].items():
                    center = result.get('center')
                    if center is None:
                        refreshed[side] = result
                        continue
                    current = scene.evaluate(center, int(side), min(deadline, time.monotonic()+5))
                    for key in ('status','score','counts','floors','group_scores'):
                        if current.get(key) != result.get(key):
                            raise ValueError('Saved center no longer reproduces: '+key)
                    refreshed[side] = dict(current,candidates_evaluated=result['candidates_evaluated'],search_budget_exhausted=result['search_budget_exhausted'])
                obs['realm']['larger_sizes'] = dict(evaluation, calibration_id=digest(active), sizes=refreshed,
                    candidate_policy='revalidated-saved-supported-centers-v1',source_search_sha256=digest(evaluation))
            obs['metrics']['import_selection'] = selection
            obs['metrics']['import_source_observation_id'] = row['observation_id']
            validate_observation_v2(obs)
            atomic_json(checkpoint,dict(index=len(state['worlds']),pin=pin,source_id=row['observation_id'],
                observation_id=digest(obs),observation=obs))
            t = time.monotonic(); summaries = summarize_v2(obs); evaluations = evaluate_products(obs)
            artifact = store.stage(obs, summaries); wid = world_id(obs['identity'])
            receipt = dict(world_id=wid,identity=obs['identity'],observation_id=digest(obs),artifact=artifact,
                evaluations=evaluations,replay=dict(resumable=False,import_pin=pin,selection=selection))
            ledger.offer(receipt, automation_offers(obs, summaries, evaluations))
            # A committed receipt can be reoffered without double-counting after a crash.
            state['worlds'].append(dict(seed=obs['identity']['seed'],world_id=wid,observation_id=digest(obs),seconds=time.monotonic()-t))
            atomic_json(progress, state)
            checkpoint.unlink()
            if len(state['worlds'])%100 == 0:
                published_snapshot=store.publish(ledger);published_generation=ledger.generation()
                print(json.dumps(dict(imported=len(state['worlds']),seconds=time.monotonic()-started)),flush=True)
        state.update(complete=len(state['worlds'])==len(inputs),last_elapsed_seconds=time.monotonic()-started)
        state['snapshot_id'] = store.publish(ledger) if published_generation!=ledger.generation() else published_snapshot
        state['last_elapsed_seconds']=time.monotonic()-started
        state['population_worlds'] = ledger.population()
        state['memberships'] = len(ledger.members())
        atomic_json(progress,state)
        print(json.dumps({k:v for k,v in state.items() if k not in ('worlds','allocations')}),flush=True)


if __name__ == '__main__':
    main()
