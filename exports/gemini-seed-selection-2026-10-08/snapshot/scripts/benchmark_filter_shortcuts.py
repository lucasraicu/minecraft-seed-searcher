"""Controlled basin/native-layout experiments; never starts the broad sweep."""
import json
import math
import sqlite3
import time
from pathlib import Path
import numpy as np
from seed_search.backend import Backend,STRUCTURES
from seed_search.cache import CachedBackend
from seed_search.config import load_config
from seed_search.landscapes import (basin_necessary_bound,raster_intermediates,flat_metrics,
                                   ring_metrics,build_centers,xy_raster)
from seed_search.terrain import raster


def reference_basin(seed,center,cfg):
    with CachedBackend(seed,64) as b:
        terrain=raster(b,(center[0]-1504,center[1]-1504,center[0]+1504,center[1]+1504),16)
        context=raster_intermediates(terrain);x,z=xy_raster(terrain);s=cfg['landscapes']
        sites=build_centers(terrain,np.hypot(x-center[0],z-center[1])<=256,[-5000,5000],8,context)
        passes=[]
        for c in [center]+[v['center'] for v in sites]:
            f,_,connected=flat_metrics(terrain,c,s,context)
            if f['flat_ground_preference_met']:
                passes.append(ring_metrics(terrain,c,s,connected,f['inner_height_median'])['dry_mountain_basin_preference_met'])
        return {'passed':any(passes),'points':terrain['points']+terrain['sea_level_stride1_points'],
                'computed_points':sum(v['computed_points'] for v in b.cache_statistics()['operations'].values())}


if __name__=='__main__':
    cfg,_=load_config('runs/filter-optimization/config/sweep.yaml');out=Path('runs/filter-optimization')
    old=[json.loads(r[0]) for r in sqlite3.connect('runs/landscape-expansion/pilot-20-verified/checkpoint.sqlite').execute('select result from seeds')]
    cases=[(int(r['seed']),n['center']) for r in old for n in r['near_misses'] if n['reason']=='density_not_dry_flat_mountain_basin'][:4]
    results=[]
    for index,(seed,center) in enumerate(cases):
        row={'seed':str(seed),'center':center}
        for variant in (('reference','bound') if index%2==0 else ('bound','reference')):
            started=time.perf_counter()
            if variant=='reference':value=reference_basin(seed,center,cfg)
            else:
                with CachedBackend(seed,64) as b:
                    value=basin_necessary_bound(b,center,cfg)
                    value['computed_points']=sum(v['computed_points'] for v in b.cache_statistics()['operations'].values())
            row[variant]={'seconds':time.perf_counter()-started,**value}
        assert not row['bound']['impossible'] or not row['reference']['passed']
        results.append(row);print(json.dumps(row),flush=True)
    # Same full seeds/bounds, alternating combined versus duplicate scans.
    timings={k:[] for k in ('duplicate','combined')};bounds=(-2048,-2048,2048,2048)
    for seed in (-1,12345,12853964,4294979641):
        observed={}
        for variant in ('duplicate','combined') if seed%2 else ('combined','duplicate'):
            started=time.perf_counter()
            with Backend(seed) as b:
                observed[variant]={name:b.structure_pair(name,bounds) if variant=='combined' else
                                   (b.structures(name,bounds,False),b.structures(name,bounds)) for name in STRUCTURES}
            timings[variant].append(time.perf_counter()-started)
        assert observed['duplicate']==observed['combined']
    proof={'basins':results,'native_structure_scan_seconds':timings,
           'reference_basin_seconds':sum(v['reference']['seconds'] for v in results),
           'bound_basin_seconds':sum(v['bound']['seconds'] for v in results),
           'computed_columns_reference':sum(v['reference']['computed_points'] for v in results),
           'computed_columns_bound':sum(v['bound']['computed_points'] for v in results),
           'all_bound_rejections_reference_failed':True,'limits':'Four saved negative nominations, isolated alternating-order cold per-seed cache A/B. Native structure parity covers all supported types and four full seeds. Not a universal yield/timing guarantee.'}
    (out/'shortcuts-ab.json').write_text(json.dumps(proof,indent=2)+'\n')
