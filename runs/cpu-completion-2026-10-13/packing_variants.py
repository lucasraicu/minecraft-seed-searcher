"""Measure equivalent uint64 input packing on three 16,384-input batches."""
import array, hashlib, json, statistics, time
from pathlib import Path
from seed_search.realm.native_batch import Prototype
from seed_search.realm.config import two_group_blueprint_config
from seed_search.seeds import seed_from_index,MASK64

root=Path(__file__).resolve().parent
proto=Prototype(root/'final-portable',two_group_blueprint_config())
ledger_path=root/'timing_budget.json';ledger=json.loads(ledger_path.read_text())
if ledger['total_measured_seconds']+60>ledger['hard_cap_seconds']:
    raise RuntimeError('Insufficient shared budget')
results=[]; started=time.monotonic()
for n in range(3):
    seeds=[seed_from_index(i) for i in range(3000000+n*16384,3000000+(n+1)*16384)]
    variants=['list','array'] if n%2==0 else ['array','list']
    expected=None
    for variant in variants:
        t=time.perf_counter()
        if variant=='list': values=proto.ffi.new('uint64_t[]',[s&MASK64 for s in seeds])
        else:
            owned=array.array('Q',(s&MASK64 for s in seeds))
            values=proto.ffi.from_buffer('uint64_t[]',owned)
        seconds=time.perf_counter()-t
        digest=hashlib.sha256(bytes(proto.ffi.buffer(values,len(seeds)*8))).hexdigest()
        if expected is not None and digest!=expected:raise RuntimeError('Packing differs')
        expected=digest
        results.append({'batch':n,'variant':variant,'inputs':len(seeds),'seconds':seconds,'uint64_bytes_sha256':digest})
wall=time.monotonic()-started
ledger['measured_profile_seconds']+=wall
ledger['total_measured_seconds']=ledger['measured_profile_seconds']+ledger['measured_cli_seconds']
ledger['events'].append({'kind':'packing_trial','wall_seconds':wall,'inputs_per_variant':49152})
ledger_path.write_text(json.dumps(ledger,indent=2)+'\n')
(root/'packing-results.json').write_text(json.dumps({'results':results,'wall_seconds':wall,
    'medians':{v:statistics.median(r['seconds'] for r in results if r['variant']==v) for v in ('list','array')},
    'all_uint64_bytes_equal':True},indent=2)+'\n')
