"""Repeatable, bounded Pillar 3 timing with a pinned current native build."""
import json
import os
from pathlib import Path
import runpy
import statistics
import time

os.environ.setdefault('KMP_BLOCKTIME','0')
ROOT=Path(__file__).resolve().parents[2]
REPORT=Path(__file__).resolve().parent
BUILD=ROOT/'runs/dynamic-baseline-2048/native-refinement-2026-10-16'


def main():
    from seed_search.realm.config import dynamic_v3_blueprint_config
    from seed_search.realm.native_batch import Prototype,seeds_np,persist_pipeline
    helpers=runpy.run_path(str(ROOT/'tests/test_native_refinement_parity.py'))
    grids=[]
    for witness in (True,False):
        p,inp,owned,*_=helpers['make_case'](BUILD,witness=witness)
        for step in (16,0,8):
            controls=[]
            for threads in (1,8):
                samples=[]
                for trial in range(7):
                    out=p.ffi.new('NBRefinementResult *');before=time.perf_counter()
                    assert p.lib.nb_dynamic_v3_refine_center(inp,step,threads,out)==0
                    samples.append((time.perf_counter()-before)*1000)
                row=dict(witness=witness,grid_step=step,threads=threads,
                         median_ms=statistics.median(samples),samples_ms=samples,
                         center=[out.x,out.z],score=out.score,radial_key=out.radial_key,
                         coarse_points=out.coarse_points,fine_points=out.fine_points)
                controls.append((row['center'],row['score'],row['radial_key']))
                grids.append(row);print(json.dumps(row),flush=True)
            assert controls[0]==controls[1]
    p=Prototype(BUILD,dynamic_v3_blueprint_config())
    count=65536;kernel=[]
    with p.sweep(seeds_np(0,4096,2026101630),34,retention='survivors',refine_centers=True):pass
    for trial in range(3):
        cohort=seeds_np(trial*count,(trial+1)*count,2026101630)
        for refine in ((False,True) if trial%2==0 else (True,False)):
            before=time.perf_counter();retained=0
            for first in range(0,count,16384):
                with p.sweep(cohort[first:first+16384],34,retention='survivors',refine_centers=refine) as batch:
                    retained+=batch.pointer.result_count
            seconds=time.perf_counter()-before
            row=dict(trial=trial,refine_centers=refine,count=count,seconds=seconds,
                     seeds_per_second=count/seconds,retained=retained)
            kernel.append(row);print(json.dumps(row),flush=True)
    durable=[]
    for trial in range(3):
        # Runs are outside tracked evidence; never overwrite earlier receipts.
        run=ROOT/'runs'/f'pillar3-benchmark-{time.time_ns()}-{trial}'
        result=persist_pipeline(p,run,count,run_key=2026101630,start_index=trial*count,
                                threads=34,batch_size=16384,retention='survivors',top_k=50)
        row={key:result[key] for key in ('wall_seconds','input_seeds_per_second','newly_committed')}
        row['run']=str(run);durable.append(row);print(json.dumps(row),flush=True)
    report={'scope':'cached synthetic grid timings include raster allocation, exclude macro generation; matched compact screening cohorts predominantly reject; tests may be concurrent; not accepted-world throughput',
            'identity':p.identity,'grid':grids,'kernel':kernel,'durable':durable,
            'kernel_median_seeds_per_second':{str(refine):statistics.median(r['seeds_per_second'] for r in kernel if r['refine_centers']==refine) for refine in (False,True)},
            'durable_median_seeds_per_second':statistics.median(r['input_seeds_per_second'] for r in durable)}
    (REPORT/'benchmark.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
