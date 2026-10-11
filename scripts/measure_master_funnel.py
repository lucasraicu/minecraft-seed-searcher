"""Bounded raw-layout feasibility and independent full64 comparison; no sweep."""
import argparse
import json
from pathlib import Path
import statistics
import time

from seed_search.backend import raw_layout,sweep_raw
from seed_search.realm.raw import FAMILIES,joint_center_witness,run_raw,evaluate_siblings
from seed_search.realm.baseline import evaluate_seed
from seed_search.realm.cli import load
from seed_search.realm.runner import _seed
from seed_search.realm.store import RealmStore
from seed_search.realm.resources import disk_policy,disk_status


def measure(output):
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    trials=[];reference=None
    for trial in range(3):
        for threads in ((1,18) if trial%2==0 else (18,1)):
            start=time.perf_counter();values=sweep_raw(0,4096,FAMILIES,threads)
            elapsed=time.perf_counter()-start
            if reference is None:reference=values.copy()
            assert (reference==values).all()
            trials.append({'trial':trial,'threads':threads,'seconds':elapsed})
    begin=time.perf_counter();cpu_start=time.process_time()
    selection=run_raw(root/'raw',0,4096,threads=18,chunk_size=512,top=64,exploration=16)
    durable_seconds=time.perf_counter()-begin;durable_cpu=time.process_time()-cpu_start
    # Exact intersection on every layout in this declared contiguous interval.
    # Counts and witnesses remain prediction-only.
    sample=range(4096)
    witnesses=[];begin=time.perf_counter()
    for low in sample:
        layouts=[raw_layout(low,name,bounds) for name,bounds in FAMILIES]
        assert [len(v) for v in layouts]==reference[low].tolist()
        witnesses.append({'low32':low,'joint_center':joint_center_witness(layouts[:4])})
    joint_seconds=time.perf_counter()-begin
    cfg=load('config/realm.yaml')
    begin=time.perf_counter();cpu_start=time.process_time()
    sibling=evaluate_siblings(cfg,root/'siblings',selection,high32=(0,1),limit=160)
    sibling_seconds=time.perf_counter()-begin;sibling_cpu=time.process_time()-cpu_start
    begin=time.perf_counter();cpu_start=time.process_time();controls=[]
    inputs=[str(_seed(i,cfg['search'])) for i in range(160)]
    with RealmStore(root/'independent',{'config':cfg,'inputs':inputs,'policy':'bounded-independent-control'}) as store:
        store.configure_range(0,len(inputs),1)
        while (lease:=store.claim_range('control')) is not None:
            first,end=lease
            disk_status(store.run,disk_policy(cfg['search']),remaining_seeds=len(inputs)-first)
            result=evaluate_seed(first,inputs[first],cfg)
            store.complete_range(first,end,[result])
            controls.append({'index':first,'seed':result['seed'],'counts':result['counts']})
    control_seconds=time.perf_counter()-begin;control_cpu=time.process_time()-cpu_start
    (root/'independent-controls.json').write_text(json.dumps(controls,indent=2)+'\n')
    medians={str(n):statistics.median(r['seconds'] for r in trials if r['threads']==n) for n in (1,18)}
    report={'lower32_range':[0,4096],'raw_trials':trials,'raw_median_seconds':medians,
            'necessary_missing':int((reference==0).any(axis=1).sum()),
            'joint_sample_size':len(sample),'joint_no_witness':sum(r['joint_center'] is None for r in witnesses),
            'joint_seconds':joint_seconds,'joint_witnesses':witnesses,
            'raw_full32_compute_only_forecast_hours':medians['18']/4096*2**32/3600,
            'durable_raw_native_seconds':selection['invocation_raw_seconds'],
            'durable_raw_wall_seconds':durable_seconds,'durable_raw_cpu_seconds':durable_cpu,
            'siblings':{'count':sibling['completed_seeds'],'seconds':sibling_seconds,'cpu_seconds':sibling_cpu,'counts':sibling['counts'],'candidate_counts':sibling['candidate_counts']},
            'independent':{'count':160,'seconds':control_seconds,'cpu_seconds':control_cpu,'predicted_anchors':sum(r['counts']['baseline_predicted'] for r in controls)},
            'interpretation':'Finite contiguous lower32 cohort and selected high32 siblings; not world recall or universal rate. Both full64 arms are serial with per-input baseline/checkpoint/disk guards. Raw+selection cost is additional; joint diagnostic excluded from raw timing. No terrain or actual verified yield. Independent full64 benchmark remains primary.'}
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='joint_witnesses'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    measure(parser.parse_args().output)
