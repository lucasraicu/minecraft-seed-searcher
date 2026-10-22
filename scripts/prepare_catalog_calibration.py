#!/usr/bin/env python3
"""Add missing Realm facts to the same fixed calibration cohort, serially."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[name] = '1'

from seed_search.catalog.artifacts import ArtifactStore
from seed_search.catalog.ingestion import atomic_json, strict_json_loads, verify_no_symlinks
from seed_search.catalog.models import validate_observation_v2, world_id
from seed_search.catalog.realm_observations import extract_realm_inventory
from seed_search.catalog.registry import digest
from seed_search.catalog.spawn_estimator import SpawnEstimator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--spawn', type=Path, required=True)
    parser.add_argument('--native-build', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=600)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if not 10 <= args.seconds <= 600:
        raise ValueError('Explicit allocation must be10..600seconds')
    from seed_search import _native
    from seed_search.backend import Backend, configure_native_threads
    from seed_search.realm.config import dynamic_v3_blueprint_config
    from seed_search.realm.native_batch import Prototype
    source_root = verify_no_symlinks(args.input.absolute())
    source = strict_json_loads((source_root / 'progress.json').read_bytes())
    if source.get('complete') is not True or not 1 <= len(source['worlds']) <= 200:
        raise ValueError('Require completed fixed cohort, maximum200 worlds')
    if hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest() != source['identity']['native_sha256']:
        raise ValueError('Current native binary differs from source cohort')
    spawn_manifest = strict_json_loads(Path(str(args.spawn) + '.build.json').read_bytes())
    estimator = SpawnEstimator(args.spawn, binary_sha256=spawn_manifest['binary_sha256'],
                               source_sha256=spawn_manifest['source_sha256'])
    cfg = dynamic_v3_blueprint_config()
    prototype = Prototype(args.native_build, cfg)
    pin = {k: prototype.identity[k] for k in ('extension_sha256', 'runtime_sha256',
            'record_adapter_sha256', 'record_sources_sha256', 'policy_sha256')}
    root = verify_no_symlinks(args.output.absolute())
    progress = root / 'progress.json'
    if root.exists() and not args.resume:
        raise ValueError('Existing output requires explicit --resume')
    root.mkdir(parents=True, exist_ok=True)
    objects = ArtifactStore(root / 'objects')
    inputs = ArtifactStore(source_root / 'objects')
    state = strict_json_loads(progress.read_bytes()) if progress.exists() else dict(
        revision='catalog-calibration-ready-v1', cohort_id=source['cohort_id'],
        identity=source['identity'], native_realm_pin=pin, worlds=[], allocations=[])
    if state['cohort_id'] != source['cohort_id'] or state['identity'] != source['identity'] or state['native_realm_pin'] != pin:
        raise ValueError('Calibration cohort/runtime changed')
    started = time.monotonic()
    deadline = started + args.seconds
    stop = threading.Event()
    resource.setrlimit(resource.RLIMIT_CPU, (args.seconds + 5, args.seconds + 10))
    os.nice(10)
    configure_native_threads(1)
    def watchdog():
        while not stop.wait(.2):
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
            if rss > 4 << 30 or time.monotonic() > deadline + 2:
                os._exit(124)
    threading.Thread(target=watchdog, daemon=True).start()
    state['allocations'].append(dict(seconds=args.seconds, started_utc=time.time(), explicit_resume=args.resume))
    atomic_json(progress, state)
    try:
        for row in source['worlds'][len(state['worlds']):]:
            if time.monotonic() >= deadline - 5:
                break
            obs = validate_observation_v2(inputs.get_json(row['artifact']))
            if digest(obs) != row['observation_id'] or obs['identity']['seed'] != row['seed']:
                raise ValueError('Input artifact differs')
            with Backend(row['seed']) as backend:
                extract_realm_inventory(obs, backend)
            estimated = estimator.estimate(obs['identity'])
            obs['anchors'].append(dict(mode=estimated['mode'], coordinate=estimated['coordinate'], source_id=estimated['anchor_id']))
            with prototype.sweep([int(row['seed'])], threads=1, retention='survivors', max_misses=0, refine_centers=True) as batch:
                records = batch.retained_records()
            evaluation = records[0] if records else dict(anchors=[])
            evaluation['execution_complete'] = True
            obs['realm'].update(config_digest=digest(cfg), evaluation=evaluation, native_pin=pin)
            for anchor in evaluation.get('anchors', []):
                if anchor.get('qualification') == 'PREDICTED' and anchor.get('baseline_score_complete') is True:
                    coordinate = list(anchor['evaluation_center'])
                    obs['anchors'].append(dict(mode='recommended', coordinate=coordinate,
                        source_id=digest(['realm-refined-center-v2', obs['identity'], digest(cfg), coordinate])))
            validate_observation_v2(obs)
            artifact = objects.put_json(obs)
            state['worlds'].append(dict(world_id=world_id(obs['identity']), legacy_world_id=row['world_id'],
                seed=row['seed'], split=row['split'], observation_id=digest(obs), artifact=artifact))
            atomic_json(progress, state)
            if len(state['worlds']) % 10 == 0:
                print(json.dumps(dict(completed=len(state['worlds']), elapsed=round(time.monotonic()-started, 2))), flush=True)
        state.update(complete=len(state['worlds']) == len(source['worlds']), last_elapsed_seconds=time.monotonic()-started)
        atomic_json(progress, state)
        print(json.dumps(dict(completed=len(state['worlds']), complete=state['complete'], elapsed=state['last_elapsed_seconds'])), flush=True)
    finally:
        stop.set()


if __name__ == '__main__':
    main()
