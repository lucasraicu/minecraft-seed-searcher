"""Repeatable diagnostic stage workload, not a seed-search throughput claim."""
import argparse
import json
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[name] = '1'
import platform
import resource
import sqlite3
import statistics
import time
import tracemalloc
from pathlib import Path
import numpy as np
from seed_search.backend import Backend, model_metadata
from seed_search.seeds import seed_from_index


def profile(count, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    names = ('stronghold','fortress','village','ancient_city','trial_chamber','mineshaft')
    tracemalloc.start()
    started = time.perf_counter()
    cpu = time.process_time()
    for index in range(count):
        seed = seed_from_index(index + 1)
        row = {'index':index+1,'seed':str(seed),'stages':{},'structures':{}}
        t = time.perf_counter()
        b = Backend(seed)
        row['stages']['generator_setup'] = time.perf_counter()-t
        with b:
            anchor = (0,0)
            for name in names:
                bounds = (-2500,-2500,2499,2499) if name in ('stronghold','fortress') else (anchor[0]-1344,anchor[1]-1344,anchor[0]+1343,anchor[1]+1343)
                t = time.perf_counter(); raw = b.structures(name,bounds,False)
                row['stages'][name+'_raw'] = time.perf_counter()-t
                t = time.perf_counter(); viable = b.structures(name,bounds,True)
                row['stages'][name+'_viable_repeats_raw'] = time.perf_counter()-t
                row['structures'][name] = {'raw':len(raw),'viable':len(viable),'bounds':list(bounds)}
                if name=='stronghold' and viable:anchor=viable[0]
            row['diagnostic_anchor'] = list(anchor)
            axis = np.arange(-1344,1344,64,dtype=np.int32)
            xx,zz=np.meshgrid(axis+anchor[0],axis+anchor[1])
            pts=np.column_stack((xx.ravel(),zz.ravel()))
            t=time.perf_counter(); ids=b.biome_points(np.column_stack((pts[:,0],np.full(len(pts),63),pts[:,1])))
            row['stages']['surface_biome_batch'] = time.perf_counter()-t
            t=time.perf_counter(); b.grid(anchor[0]-1344,anchor[1]-1344,42,42,64)
            row['stages']['biome_climate_2d_batch'] = time.perf_counter()-t
            t=time.perf_counter(); heights,_=b.heights(pts,8)
            row['stages']['raw_density_height_batch'] = time.perf_counter()-t
            row['sample_points']=len(pts)
            row['height_range']=[int(heights.min()),int(heights.max())]
            row['biome_ids']=sorted(map(int,np.unique(ids)))
        t=time.perf_counter(); encoded=json.dumps(row,allow_nan=False)
        row['stages']['serialization']=time.perf_counter()-t
        with sqlite3.connect(output/'stage-profile.sqlite') as db:
            db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
            db.execute('CREATE TABLE IF NOT EXISTS rows (idx INTEGER PRIMARY KEY,payload TEXT)')
            t=time.perf_counter()
            with db:db.execute('INSERT INTO rows VALUES (?,?)',(index,encoded))
            row['stages']['sqlite_single_commit']=time.perf_counter()-t
        rows.append(row)
        print(json.dumps({'completed':index+1,'count':count,'seed':str(seed),'seconds':sum(row['stages'].values())}),flush=True)
    wall=time.perf_counter()-started; cpu=time.process_time()-cpu
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    stats={key:{'median_seconds':statistics.median(r['stages'][key] for r in rows),'total_seconds':sum(r['stages'][key] for r in rows),'min_seconds':min(r['stages'][key] for r in rows),'max_seconds':max(r['stages'][key] for r in rows)} for key in rows[0]['stages']}
    result={'workload':'unconditional diagnostic stages; not full scan; origin fallback when no predicted stronghold','count':count,'distinct_full64_seeds':count,'backend':model_metadata(),'platform':platform.platform(),'numeric_threads':1,'wall_seconds':wall,'cpu_seconds':cpu,'single_process_cpu_utilization_percent':100*cpu/wall,'diagnostic_inputs_per_second':count/wall,'python_traced_peak_bytes':peak,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024),'stages':stats,'rows':rows,'five_largest_measured_stages':sorted(stats,key=lambda k:stats[k]['total_seconds'],reverse=True)[:5]}
    (output/'stage-profile.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--count',type=int,default=8);p.add_argument('--output',required=True)
    args=p.parse_args()
    if not 1<=args.count<=128:p.error('Diagnostic sample must contain 1–128 inputs')
    print(json.dumps(profile(args.count,args.output),indent=2),flush=True)
