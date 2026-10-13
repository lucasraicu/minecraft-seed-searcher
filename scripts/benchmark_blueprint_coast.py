"""Paired coastal raster replay: same coordinates, exact cache reuse, no yield claim."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import statistics
import time

for _name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[_name]='1'

import numpy as np
from seed_search.backend import Backend,configure_native_threads
from seed_search.realm.store import canonical
from seed_search.realm.config import blueprint_config
from seed_search.realm.bounds import square
from seed_search.realm.raster import RasterCache
from seed_search.realm.coastal import evaluate_coastal

ROOT=Path(__file__).resolve().parents[1]


def decision_evidence(value):
    # The existing timing exclusion applies at the nested coastal metrics too.
    if isinstance(value,dict):return {k:decision_evidence(v) for k,v in value.items() if k!='stage_seconds'}
    if isinstance(value,list):return [decision_evidence(v) for v in value]
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'runs/blueprint-audit-2026-10-12/coastal-timing.json')
    p.add_argument('--trials',type=int,default=3)
    p.add_argument('--layouts',type=int,default=3)
    p.add_argument('--threads',type=int,default=18)
    p.add_argument('--resolutions',type=int,nargs='+',default=[128,64,32,16])
    args=p.parse_args()
    if not 1<=args.trials<=5 or not 1<=args.layouts<=8 or any(r not in (4,8,16,32,64,128) for r in args.resolutions):
        p.error('Use 1–5 trials, 1–8 layouts and supported resolutions')
    cfg=blueprint_config()
    selected=[r for r in json.loads((ROOT/'runs/locked-stronghold-2026-10-11/holdout/centers.json').read_text()) if r['first_center']]
    # Spread controls across different low32 groups, not consecutive siblings.
    selected=selected[::max(1,len(selected)//args.layouts)][:args.layouts]
    result={'scope':'Unconditional natural-terrain diagnostic at retained selected centers; '
            'NOT structure/biome survivors. Same fixed1536 bounds and resolutions in both arms. '
            'Raster model/predicted monument envelope is not actual generation.',
            'threads':args.threads,'resolutions':args.resolutions,'layouts':selected,
            'trials':[],'parity_checks':0,'differences':0}
    configure_native_threads(args.threads)
    expected={};reuse_plan={}
    # Independent coordinate accounting happens outside the arm timers.
    for i,row in enumerate(selected):
        bounds=square(row['center'],1536);seen=set()
        for spacing in args.resolutions:
            coordinates={(x,z) for x in range(bounds[0],bounds[2],spacing) for z in range(bounds[1],bounds[3],spacing)}
            reused=len(coordinates&seen);reuse_plan[(i,spacing)]=(len(coordinates)-reused,reused)
            seen.update(coordinates)
    for trial in range(args.trials):
        for arm in (('fresh_each_resolution','reuse_exact_points') if trial%2==0 else ('reuse_exact_points','fresh_each_resolution')):
            wall=time.perf_counter(); stages=[];queried=reused=0
            for i,row in enumerate(selected):
                cache=RasterCache(); bounds=square(row['center'],1536)
                with Backend(row['seed']) as b:
                    monuments=b.structures('monument',(bounds[0],bounds[1],bounds[2]-1,bounds[3]-1),True)
                    for spacing in args.resolutions:
                        if arm=='fresh_each_resolution':cache=RasterCache()
                        before_queries,before_reuse=cache.queried_points,cache.reused_points
                        start=time.perf_counter()
                        raster=cache.sample(b,row['seed'],bounds,spacing,stage='height')
                        sample_seconds=time.perf_counter()-start
                        start=time.perf_counter()
                        coastal=evaluate_coastal(raster,stronghold=tuple(row['center']),bounds=bounds,
                                                  thresholds=cfg['terrain']['v1'],monuments=monuments)
                        evaluate_seconds=time.perf_counter()-start
                        q=cache.queried_points-before_queries;r=cache.reused_points-before_reuse
                        expected_counts=(int(raster.height.size),0) if arm=='fresh_each_resolution' else reuse_plan[(i,spacing)]
                        assert (q,r)==expected_counts, 'Independent cache coordinate accounting differs'
                        parity_decision=copy.deepcopy(coastal)
                        accounting=parity_decision['provider']['sampling_reuse']
                        assert accounting=={'points_queried':q,'exact_points_reused':r}
                        # Validate the expected per-arm resource counters above,
                        # then express both as total defined samples for hashing.
                        # Raw decisions/counters remain retained below.
                        accounting.update(points_queried=q+r,exact_points_reused=0)
                        payload=(raster.height.tobytes()+raster.biomes.tobytes()+raster.water_mask().tobytes()+raster.known.tobytes()+
                                 canonical(decision_evidence(parity_decision)).encode())
                        digest=hashlib.sha256(payload).hexdigest();key=(i,spacing)
                        if key in expected:assert expected[key]==digest, 'Exact raster/geometry parity failed'
                        else:expected[key]=digest
                        result['parity_checks']+=1
                        q=cache.queried_points-before_queries;r=cache.reused_points-before_reuse
                        queried+=q;reused+=r
                        stages.append({'layout':i,'spacing':spacing,'points':int(raster.height.size),
                            'sample_seconds':sample_seconds,'evaluate_seconds':evaluate_seconds,
                            'new_queries':q,'exact_points_reused':r,'geometry_pass':bool(coastal['geometry_pass']),
                            'mainland_fraction':coastal['metrics']['mainland_fraction'],
                            'ocean_edges':coastal['metrics']['ocean_edges'],
                            'monument_coastal_model_pass':coastal['metrics']['monument_coastal_model_pass'],
                            'raster_and_decision_sha256':digest,'decision':coastal})
            entry={'trial':trial,'arm':arm,'seconds':time.perf_counter()-wall,
                   'queried_points':queried,'reused_points':reused,'stages':stages}
            result['trials'].append(entry)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps({k:v for k,v in entry.items() if k!='stages'}),flush=True)
    med={arm:statistics.median(t['seconds'] for t in result['trials'] if t['arm']==arm)
         for arm in ('fresh_each_resolution','reuse_exact_points')}
    result.update(median_seconds=med,speedup=med['fresh_each_resolution']/med['reuse_exact_points'],
                  wall_time_saved_percent=100*(1-med['reuse_exact_points']/med['fresh_each_resolution']))
    result['coastal_sources']={str(q.relative_to(ROOT)):hashlib.sha256(q.read_bytes()).hexdigest() for q in
        [ROOT/'src/seed_search/realm/coastal.py',ROOT/'src/seed_search/realm/raster.py',ROOT/'config/realm.yaml',Path(__file__)]}
    args.output.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
