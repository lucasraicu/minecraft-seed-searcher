"""High16 sibling controls at individually discovered, exact Stronghold borders."""
from collections import Counter
from contextlib import ExitStack
import hashlib,json,statistics,time
from pathlib import Path
from seed_search.backend import Backend
from seed_search.realm.baseline import structure_observation
from seed_search.realm.config import default_config
from scripts.pilot_locked_stronghold import exact_bounds
from scripts.count_pilot_api import CountBackend,lib
from scripts.pilot_count_bits_structures import OUT,ROOT,greedy,PROFILES

LCG=('trial_chamber','trail_ruins','abandoned_camp')
ARMS={'full64_direct':(0,False),'fused_lower32':(32,False),'fused_lower48':(48,False),'cached_lower32':(32,True),'cached_lower48':(48,True)}

def main():
    results={};all_rows=[];compared=0
    for cohort in ('tuning','holdout'):
        candidates=[r for r in json.loads((ROOT/f'runs/locked-stronghold-2026-10-11/{cohort}/centers.json').read_text()) if r['first_center']]
        bases=[];lows=set()
        for r in candidates:
            if r['low32'] not in lows:bases.append(r);lows.add(r['low32'])
            if len(bases)==16:break
        rows=[];discovery=0.;setup=0.;unresolved=0
        for base in bases:
            low48=int(base['seed'])&0xffffffffffff
            for high in (0,0x1234,0x89ab,0xffff):
                unsigned=(high<<48)|low48;seed=unsigned if unsigned<1<<63 else unsigned-(1<<64)
                t=time.perf_counter();backend=Backend(seed);setup+=time.perf_counter()-t
                with backend:
                    t=time.perf_counter();centers=structure_observation(backend,'stronghold',default_config()['discovery']['overworld_bounds'],combined=True)['predicted_viable'];discovery+=time.perf_counter()-t
                    if not centers:unresolved+=1;continue
                    row={'seed':str(seed),'low48':low48,'high16':high,'center':centers[0],'bounds':exact_bounds(centers[0])}
                    raw={};viable={}
                    with Backend(low48) as lower:
                        for name in LCG:
                            raw[name]=backend.structures(name,row['bounds']['overworld'],False)
                            assert raw[name]==lower.structures(name,row['bounds']['overworld'],False)
                            compared+=1
                            viable[name]=len(backend.structures(name,row['bounds']['overworld'],True))
                    row['raw_counts']={k:len(v) for k,v in raw.items()};row['viable_counts']=viable;rows.append(row)
        all_rows.extend({**r,'cohort':cohort} for r in rows)
        keys=[(r['low48'],tuple(r['bounds']['overworld'])) for r in rows]
        results[cohort]={'full64_inputs':64,'locked_centers':len(rows),'unresolved_without_center':unresolved,
                         'unique_lower48_border_keys':len(set(keys)),'repeated_border_queries':len(keys)-len(set(keys)),
                         'discovery_seconds':discovery,'context_setup_seconds':setup,'counts':{}}
        with ExitStack() as stack:
            handles=[stack.enter_context(CountBackend(r['seed'])) for r in rows]
            for n in (1,2,3,4):
                prepared=[b.prepare_combo(r,LCG,n,LCG) for b,r in zip(handles,rows)]
                expected=[all(r['viable_counts'][k]>=n for k in LCG) for r in rows]
                trials=[]
                for trial in range(5):
                    arms=tuple(ARMS);order=arms[trial:]+arms[:trial]
                    for arm in order:
                        bits,cached=ARMS[arm];t=time.perf_counter()
                        for repeat in range(8):
                            lib.pc_cache_reset(cached)
                            assert [b.combo_prepared(p,bits)[0] for b,p in zip(handles,prepared)]==expected
                        trials.append({'trial':trial,'arm':arm,'seconds':time.perf_counter()-t})
                med={a:statistics.median(t['seconds'] for t in trials if t['arm']==a) for a in ARMS}
                results[cohort]['counts'][str(n)]={'viable_positive':sum(expected),'raw_missing_lower48':sum(any(r['raw_counts'][k]<n for k in LCG) for r in rows),
                                                'layouts_per_second':{a:len(rows)*8/v for a,v in med.items()},
                                                'time_change_percent':{a:100*(v/med['full64_direct']-1) for a,v in med.items()},'trials':trials}
                print(json.dumps({'high16_siblings':cohort,'n':n,'result':results[cohort]['counts'][str(n)]['time_change_percent']}),flush=True)
    report={'cohorts':results,'lower48_raw_layout_comparisons':compared,'differences':0,
            'scope':'16 disjoint lower48 groups per cohort, four highest16 choices, independently discovered first Stronghold; LCG-three combination only, not whole-pipeline timing. Native raw-prefix cache is reset and charged per repetition.'}
    (OUT/'lower48-sibling-rows.json').write_text(json.dumps(all_rows,indent=2)+'\n')
    (OUT/'lower48-siblings-report.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
