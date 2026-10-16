"""Attribute worker elapsed time in an isolated instrumented build, not production throughput."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
sys.path[:0]=[str(ROOT/'src')]
from seed_search.realm.config import dynamic_v2_blueprint_config
from seed_search.realm.native_batch import Prototype,seeds_np
p=Prototype('/tmp/final-audit-233fad7-diagnostic/build',dynamic_v2_blueprint_config())
control=Prototype(ROOT/'runs/dynamic-baseline-1664/native',dynamic_v2_blueprint_config())
names=['raw_preflight','overworld_apply_seed','raw_dark_gate','mansion_inventory','stronghold_discovery','outpost_inventory','nether_initialization_inventory','remaining_overworld_inventories','center_search','winning_evidence']
rows=[{'stage':n,'inputs':0,'calls':0,'worker_elapsed_seconds':0.0} for n in names]
policy=p.ffi.new('NBPolicy *');p.ffi.memmove(policy,p.policy,p.ffi.sizeof('NBPolicy'));policy.retention=1;policy.max_misses=3
elapsed=0.;retained=0;total_eval=0.;offset=50000000;end=offset+100000
while offset<end:
    seeds=seeds_np(offset,min(offset+16384,end),2026101401)
    samples=p.ffi.new('AuditSample[]',len(seeds));values=p.ffi.from_buffer('uint64_t[]',seeds)
    start=time.perf_counter();b=p.lib.audit_sweep(values,len(seeds),policy,34,samples);elapsed+=time.perf_counter()-start
    assert b!=p.ffi.NULL
    try:
        assert b.error==0 and b.count==len(seeds)
        for i,s in enumerate(samples):
            assert s.seed==int(seeds[i])&((1<<64)-1)
            total_eval+=s.eval_seconds
            for k,row in enumerate(rows):
                row['inputs']+=int(s.calls[k]>0);row['calls']+=s.calls[k];row['worker_elapsed_seconds']+=s.seconds[k]
        actual=[(int(b.results[i].seed),int(b.results[i].nanchors)) for i in range(b.result_count)]
        with control.sweep(seeds,34,retention='survivors',max_misses=3) as c:
            expected=[(int(c.pointer.results[i].seed),int(c.pointer.results[i].nanchors)) for i in range(c.pointer.result_count)]
            assert actual==expected
        retained+=b.result_count
    finally:p.lib.nb_free(b)
    offset+=len(seeds)
for r in rows:
    r['percent_input']=r['inputs']/1000;r['percent_worker_elapsed']=100*r['worker_elapsed_seconds']/total_eval
report={'inputs':100000,'start_index':50000000,'run_key':2026101401,'threads':34,'retained':retained,'control_retention_equal':True,'wall_native_calls_seconds':elapsed,'sum_worker_eval_seconds':total_eval,'unattributed_worker_seconds':total_eval-sum(r['worker_elapsed_seconds'] for r in rows),'stages':rows,'caveats':['Instrumented build has no PGO; stage timers perturb timing.','Worker elapsed time includes descheduling; it is not wall-time attribution or hardware CPU cycles.','Natural all-reject cohort cannot establish scoring or retained-candidate throughput.'],'build':p.identity}
(OUT/'profile-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='build'},indent=2))
