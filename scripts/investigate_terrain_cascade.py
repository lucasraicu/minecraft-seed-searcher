"""Bounded locked-border density/cascade experiment; controls are near misses."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time

for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from seed_search.backend import Backend,configure_native_threads
from seed_search.realm.config import locked_blueprint_config
from seed_search.realm.coastal import evaluate_coastal
from seed_search.realm.raster import RasterCache
from seed_search.realm.store import RealmStore,canonical


def decision_fingerprint(result):
    value=copy.deepcopy(result)
    value['metrics'].pop('stage_seconds')
    counters=value['provider'].pop('sampling_reuse')
    assert counters['exact_points_reused']+counters['points_queried']==512*512
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--trials',type=int,default=3);args=p.parse_args()
    if args.output.exists() or not 2<=args.trials<=5:p.error('Fresh output and 2–5 trials required')
    args.output.mkdir(parents=True)
    with RealmStore(args.run,resume=True) as store:controls=list(store.iter_candidates())[:3]
    if not controls:raise RuntimeError('No retained natural controls')
    cfg=locked_blueprint_config();configure_native_threads(18)
    schedules={'existing_six_levels':[128,64,32,16,8,4], 'three_levels':[128,32,4], 'fine_only':[4]}
    observations=[];expected={};expected_decisions={}
    for trial in range(args.trials):
        arms=list(schedules);arms=arms[trial%3:]+arms[:trial%3]
        for arm in arms:
            for candidate in controls:
                cache=RasterCache();stages=[];started=time.perf_counter()
                with Backend(candidate['seed']) as provider:
                    for resolution in schedules[arm]:
                        stage='nomination' if resolution==128 else 'height'
                        before=time.perf_counter()
                        raster=cache.sample(provider,candidate['seed'],candidate['bounds']['overworld'],resolution,stage=stage)
                        sample_seconds=time.perf_counter()-before
                        before=time.perf_counter()
                        decision=evaluate_coastal(raster,bounds=raster.bounds,stronghold=candidate['stronghold'],thresholds=cfg['terrain']['v1'],require_monument=False)
                        stages.append({'resolution':resolution,'stage':stage,'samples':raster.height.size,
                                       'sample_seconds':sample_seconds,'geometry_seconds':time.perf_counter()-before,
                                       'reuse':raster.metadata['sampling_reuse'],
                                       'mainland_fraction':decision['metrics']['mainland_fraction'],
                                       'coastal_model_pass':decision['model_geometry_pass']})
                elapsed=time.perf_counter()-started
                digest=hashlib.sha256(raster.height.tobytes()+raster.biomes.tobytes()+raster.known.tobytes()).hexdigest()
                cid=candidate['id'];decision_hash=decision_fingerprint(decision)
                if cid in expected:assert digest==expected[cid] and decision_hash==expected_decisions[cid],(cid,arm,'final raster/decision parity')
                else:expected[cid]=digest;expected_decisions[cid]=decision_hash
                row={'arm':arm,'trial':trial,'candidate_id':cid,'baseline_pending_reasons':candidate['pending_reasons'],
                     'wall_seconds':elapsed,'stages':stages,'raster_sha256':digest,'decision_sha256':decision_hash,
                     'final_mainland_fraction':decision['metrics']['mainland_fraction'],'final_coastal_model_pass':decision['model_geometry_pass']}
                observations.append(row);print(json.dumps(row),flush=True)
                np.savez_compressed(args.output/f'{arm}-{trial}-{controls.index(candidate)}.npz',height=raster.height,biomes=raster.biomes,known=raster.known)
    medians={arm:statistics.median(sum(r['wall_seconds'] for r in observations if r['arm']==arm and r['trial']==trial) for trial in range(args.trials)) for arm in schedules}
    result={'scope':'Three unconditional retained natural near-miss controls, not complete survivors. Timed sampling+geometry; NPZ artifact writing is outside timing. No SQL/BDS certification.',
            'native_threads':18,'schedules':schedules,'observations':observations,'median_cohort_seconds':medians,
            'raster_differences':0,'full_final_decision_differences':0,
            'three_level_speedup':medians['existing_six_levels']/medians['three_levels'],
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),ROOT/'src/seed_search/realm/raster.py',ROOT/'src/seed_search/realm/coastal.py')}}
    (args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(medians))


if __name__=='__main__':main()
