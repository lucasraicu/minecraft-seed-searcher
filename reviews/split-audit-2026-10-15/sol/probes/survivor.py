"""Native survivor stages and Python reconstruction measured separately."""
import argparse
import json
import statistics
import time
from experiment import ROOT, OUT, WORK, write_json
from seed_search.realm.native_batch import Prototype, Batch
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.seeds import MASK64

parser=argparse.ArgumentParser();parser.add_argument('--allow-heavy',action='store_true')
if not parser.parse_args().allow_heavy: parser.error('Heavy work requires release')
p=Prototype(WORK/'diagnostic/native-build',dynamic_blueprint_config())
ffi,lib=p.ffi,p.lib
policy=ffi.new('NBPolicy *');ffi.memmove(policy,p.policy,ffi.sizeof('NBPolicy'))
policy.retention=1;policy.max_misses=2
profile=json.loads((OUT/'profile-50000000-100000-34.json').read_text())
late=profile['late_stage_inputs']['dynamic_center_search']
labels=json.loads((OUT/'diagnostic-labels.json').read_text())['labels']
labels[35:40]=['optional_inventories','overworld_prefix','nether_prefix','event_build','argmin']
result={'build':p.identity,'synthetic_trials':[],'natural_late_stage_trials':[],
        'forced_natural_components':[],
        'limitations':['Forced components do not assert seed eligibility',
                       'Diagnostic timing is not an uninstrumented throughput claim',
                       'No compatible natural retained survivor was found in the bounded cohort',
                       'Peak allocation evidence is in codex/reproductions.json; context is excluded']}

for synthetic in (True,False):
    seeds=[123]*32 if synthetic else [int(r['seed']) for r in late]
    if not seeds: continue
    for trial in range(5):
        values=ffi.new('uint64_t[]',[s&MASK64 for s in seeds])
        samples=ffi.new('SolAuditSample[]',len(seeds))
        before=time.perf_counter()
        if synthetic:
            fixtures=ffi.new('NBFixture[]',len(seeds))
            for f in fixtures:f.missing=-1;f.deficit_depth=1
            ptr=lib.sol_diag_fixture_sweep(values,fixtures,len(seeds),policy,1,samples)
        else: ptr=lib.sol_diag_sweep(values,len(seeds),policy,1,samples)
        elapsed=time.perf_counter()-before
        if ptr==ffi.NULL or ptr.error: raise RuntimeError('Diagnostic batch failure')
        with Batch(p,ptr,seeds,elapsed,False,synthetic,'survivors',2) as batch:
            before=time.perf_counter();records=batch.retained_records(0)
            reconstruction=time.perf_counter()-before
            before=time.perf_counter();encoded=json.dumps(records,separators=(',',':')).encode()
            serialization=time.perf_counter()-before
            stages={labels[k]:sum(s.seconds[k] for s in samples) for k in range(40)
                    if sum(s.seconds[k] for s in samples)>0}
            row=dict(trial=trial,count=len(seeds),native_seconds_instrumented=elapsed,
                     retained_inputs=ptr.result_count,stage_seconds_sum=stages,
                     reconstruction_seconds=reconstruction,serialization_seconds=serialization,
                     serialized_bytes=len(encoded))
            if synthetic:
                row['native_counts']={'discovery':ptr.results[0].discovery.n,
                                      'selected_centers':ptr.results[0].nanchors,
                                      'receipt_anchors':ptr.verdicts[0].anchors,
                                      'receipt_retained':ptr.verdicts[0].retained}
            result['synthetic_trials' if synthetic else 'natural_late_stage_trials'].append(row)

for item in late[:16]:
    seconds=ffi.new('double[5]');counts=ffi.new('int[20]')
    code=lib.sol_stage_probe(int(item['seed'])&MASK64,policy,seconds,counts)
    if code: raise RuntimeError(f'Forced component error: {code}')
    result['forced_natural_components'].append(dict(input=item,
        seconds=dict(zip(['mandatory_inventories','optional_inventories','overworld_prefix',
                          'nether_prefix','final_evidence'],list(seconds))),counts=list(counts)))
result['late_stage_inputs']=late
write_json(OUT/'survivor.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ('build',)},indent=2))
