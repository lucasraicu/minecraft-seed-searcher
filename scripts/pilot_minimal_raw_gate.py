"""Minimal placement-only follow-up, with paid exact-center cache construction."""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import statistics
import time
from seed_search import _native
from seed_search.backend import Backend
from scripts.pilot_all_structure_combinations import PROFILES, query_bounds, direct
from scripts.pilot_locked_stronghold import current_viability, raw_presence

# Pinned MC_26_50 source: both have 80-chunk regions, 60-chunk offset ranges,
# triangular placement offsets; Mansion adds 8 blocks, Outpost adds 0. Other audited region-MT
# families are placement-guaranteed at these deployment widths; all 16 raw
# conjunctions were checked against the reduced gate in both frozen cohorts.
SPARSE = ('outpost', 'mansion')


def sparse_raw_first(backend, row, name):
    if name not in SPARSE:
        raise ValueError('Diagnostic helper supports only source-reviewed sparse families')
    x0,z0,x1,z1 = query_bounds(row, name)
    size,offset = 80*16, 0 if name == 'outpost' else 8
    last = (60-1)*16+offset
    # Does any full possible-offset rectangle lie within the inclusive border?
    if -((offset-x0)//size) <= (x1-last)//size and -((offset-z0)//size) <= (z1-last)//size:
        return True
    for rx in range(x0//size,x1//size+1):
        for rz in range(z0//size,z1//size+1):
            p = backend.attempt(name,rx,rz)
            if p is not None and x0<=p[0]<=x1 and z0<=p[1]<=z1:
                return True
    return False


def minimal_gate(backend, row, sparse=SPARSE):
    return raw_presence(backend.seed & 0xffffffff,row['bounds']) and all(sparse_raw_first(backend,row,n) for n in sparse)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path('runs/all-structure-combinations-2026-10-11'))
    args=parser.parse_args()
    report=json.loads((args.input/'report.json').read_text())
    output={'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'native_sha256':hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest(),
            'scope':'Exact-center conditional stage only; cached arm builds a new cache each repetition, charging misses and hits; no free precomputed results.'}
    parity=0
    for cohort in ('tuning','holdout'):
        rows=[r for r in json.loads((Path('runs/locked-stronghold-2026-10-11')/cohort/'centers.json').read_text()) if r['first_center']]
        observations=json.loads((args.input/f'{cohort}-observations.json').read_text())
        with ExitStack() as stack:
            handles=[stack.enter_context(Backend(r['seed'])) for r in rows]
            for backend,row,obs in zip(handles,rows,observations):
                for name in SPARSE:
                    assert sparse_raw_first(backend,row,name) == obs[name]['raw']
                    parity+=1
                assert minimal_gate(backend,row) == all(o['raw'] for n,o in obs.items() if 'raw' in o)
                parity+=1
            cohort_results={}
            for profile in PROFILES:
                parent=report['cohorts'][cohort][profile]
                order=parent['direct_order']
                sparse=() if profile=='current_four' else SPARSE
                expected=[all(o[n]['viable'] for n in PROFILES[profile]) for o in observations]
                def replay(arm):
                    cache={}
                    answers=[]
                    for b,row in zip(handles,rows):
                        if arm!='direct':
                            if arm=='cached_minimal_gate':
                                key=(b.seed & 0xffffffff,tuple(row['bounds']['overworld']),tuple(row['bounds']['nether']))
                                if key not in cache:
                                    cache[key]=minimal_gate(b,row,sparse)
                                ok=cache[key]
                            else:
                                ok=minimal_gate(b,row,sparse)
                            if not ok:
                                answers.append(False)
                                continue
                        answers.append(current_viability(b,row['bounds']) if profile=='current_four' else direct(b,row,order))
                    return answers
                arms=('direct','minimal_gate','cached_minimal_gate')
                for arm in arms:
                    assert replay(arm)==expected
                trials=[]
                for trial in range(6):
                    rotation=arms[trial%3:]+arms[:trial%3]
                    if trial>=3: rotation=tuple(reversed(rotation))
                    for arm in rotation:
                        start,cpu=time.perf_counter(),time.process_time()
                        for _ in range(8):
                            assert replay(arm)==expected
                        trials.append({'arm':arm,'trial':trial,'seconds':time.perf_counter()-start,'cpu_seconds':time.process_time()-cpu})
                med={a:statistics.median(t['seconds'] for t in trials if t['arm']==a) for a in arms}
                cohort_results[profile]={'trials':trials,'median_seconds':med,
                    'stage_centers_per_second':{a:len(rows)*8/s for a,s in med.items()},
                    'time_change_percent':{a:100*(s/med['direct']-1) for a,s in med.items()}}
                print(json.dumps({'cohort':cohort,'profile':profile,'time_change_percent':cohort_results[profile]['time_change_percent']}),flush=True)
            output[cohort]=cohort_results
    output.update(raw_presence_comparisons=parity,differences=0)
    (args.input/'minimal-gate-timing.json').write_text(json.dumps(output,indent=2)+'\n')

if __name__=='__main__':main()
