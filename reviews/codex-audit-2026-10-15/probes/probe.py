import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'src'))
sys.path.insert(0,'/tmp/minecraft-audit-20261015')
import audit_batch as a
from seed_search.realm.native_batch import Prototype
from seed_search.realm.config import dynamic_blueprint_config
p=Prototype('runs/dynamic-baseline-1664/native',dynamic_blueprint_config())
policy=a.ffi.new('NBPolicy *');a.ffi.buffer(policy)[:]=bytes(p.ffi.buffer(p.policy));policy.retention=1;policy.max_misses=2
policy.max_buffer_bytes=int(sys.argv[1]) if len(sys.argv)>1 else 1400000
n=int(sys.argv[3]) if len(sys.argv)>3 else 1
seeds=a.ffi.new('uint64_t[]',[123]*n);fixtures=a.ffi.new('NBFixture[]',[(0,0,-1,0,1)]*n)
a.lib.audit_reset(int(sys.argv[2]) if len(sys.argv)>2 else 0)
b=a.lib.nb_fixture_sweep(seeds,fixtures,n,policy,1)
print(json.dumps({'cap':policy.max_buffer_bytes,'count':n,'peak_requested_bytes':a.lib.audit_peak(),'live_after_sweep':a.lib.audit_live(),'malloc_calls':a.lib.audit_calls(),'null':b==a.ffi.NULL,'error':b.error if b!=a.ffi.NULL else None,'retained':b.result_count if b!=a.ffi.NULL else None}),flush=True)
if b!=a.ffi.NULL:a.lib.nb_free(b)
print('live after free',a.lib.audit_live())
