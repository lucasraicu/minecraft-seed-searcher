import sys,json,hashlib,time,statistics
from pathlib import Path
root=Path.cwd();sys.path[:0]=[str(root/'src'),'/tmp/minecraft-audit-20261015']
import audit_batch as a
from seed_search.realm.native_batch import Prototype
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.seeds import seed_from_index,MASK64
p=Prototype(root/'runs/dynamic-baseline-1664/native',dynamic_blueprint_config())
policy=a.ffi.new('NBPolicy *');a.ffi.buffer(policy)[:]=bytes(p.ffi.buffer(p.policy));policy.retention=1;policy.max_misses=2;policy.max_buffer_bytes=268435456
rows=[]
for count in [1,2,32]:
 seeds=a.ffi.new('uint64_t[]',[123]*count);fixtures=a.ffi.new('NBFixture[]',[(0,0,-1,0,1)]*count)
 a.lib.audit_reset(0);batch=a.lib.nb_fixture_sweep(seeds,fixtures,count,policy,1)
 assert batch!=a.ffi.NULL and batch.error==0
 row=dict(count=count,threads=1,synthetic=True,allocation_calls=a.lib.audit_calls(),peak_requested_live_bytes=a.lib.audit_peak(),retained_live_bytes=a.lib.audit_live())
 a.lib.nb_free(batch);row['live_after_free']=a.lib.audit_live();assert row['live_after_free']==0;rows.append(row)
# Isolate seed-array construction and verdict hashing from native computation.
seeds=[seed_from_index(i,2026101401) for i in range(110000000,110016384)]
array_times=[];hash_times=[]
for _ in range(20):
 t=time.perf_counter();array=p.ffi.new('uint64_t[]',[s&MASK64 for s in seeds]);array_times.append(time.perf_counter()-t)
 receipt=p.ffi.new('NBVerdict[]',len(seeds))
 t=time.perf_counter();hashlib.sha256(p.ffi.buffer(receipt,len(seeds)*p.ffi.sizeof('NBVerdict'))).digest();hash_times.append(time.perf_counter()-t)
out=dict(allocation_cases=rows,allocation_scope='one worker; NB allocations only, excludes SeedContext and allocator metadata; no failure injection',boundary=dict(count=16384,trials=20,array_creation_median_seconds=statistics.median(array_times),verdict_hash_median_seconds=statistics.median(hash_times),hash_input='zero-initialized verdict bytes; hashing is content-independent in cost',includes_native=False))
(root/'reviews/split-audit-2026-10-15/sol/allocation-boundary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
