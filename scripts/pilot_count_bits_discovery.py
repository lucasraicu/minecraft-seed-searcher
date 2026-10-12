"""Charge full64 Stronghold discovery/setup before count-N filtering."""
import argparse,hashlib,json,statistics,time
from pathlib import Path
from seed_search.backend import Backend
from seed_search.realm.baseline import structure_observation
from seed_search.realm.config import default_config
from scripts.count_pilot_api import CountBackend,lib
from scripts.pilot_locked_stronghold import exact_bounds
from scripts.pilot_count_bits_structures import ROOT,OUT,ARMS


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inputs',type=int,default=128);args=parser.parse_args()
    primary=json.loads((OUT/'structures-report.json').read_text());results={};comparisons=0
    for cohort in ('tuning','holdout'):
        manifest=json.loads((ROOT/f'runs/locked-stronghold-2026-10-11/{cohort}/identity.json').read_text())['manifest'][:args.inputs]
        centers=[r for r in json.loads((ROOT/f'runs/locked-stronghold-2026-10-11/{cohort}/centers.json').read_text()) if r['first_center']]
        observations=json.loads((OUT/f'{cohort}-structure-observations.json').read_text())
        known={r['seed']:(r,o) for r,o in zip(centers,observations)}
        cohort_results={}
        for n in (1,2,3,4):
            parent=primary['cohorts'][cohort]['all_21_ow_nether'][str(n)]
            order=parent['direct_order'];expected=[all(known[item['seed']][1][k]['viable_count']>=n for k in order) if item['seed'] in known else None for item in manifest]
            # Freeze the discovery cohort and truth before any timings.
            def run(arm):
                bits,cached=ARMS[arm];lib.pc_cache_reset(cached);answers=[];discovery=0.;setup=0.;filtering=0.
                for item in manifest:
                    t=time.perf_counter();backend=Backend(item['seed']);setup+=time.perf_counter()-t
                    with backend:
                        t=time.perf_counter();discovered=structure_observation(backend,'stronghold',default_config()['discovery']['overworld_bounds'],combined=True)['predicted_viable'];discovery+=time.perf_counter()-t
                    if not discovered:answers.append(None);continue
                    assert item['seed'] in known and list(discovered[0])==known[item['seed']][0]['center']
                    row={'bounds':exact_bounds(discovered[0])}
                    t=time.perf_counter();counter=CountBackend(item['seed']);setup+=time.perf_counter()-t
                    with counter:
                        t=time.perf_counter();prepared=counter.prepare_combo(row,order,n,parent['raw_order'][str(bits or 32)]);answer=counter.combo_prepared(prepared,bits)[0];filtering+=time.perf_counter()-t
                        answers.append(answer)
                assert answers==expected
                return {'discovery_seconds':discovery,'setup_seconds':setup,'count_and_prepare_seconds':filtering}
            for arm in ARMS:run(arm)
            trials=[];arms=tuple(ARMS)
            for trial in range(3):
                rotation=arms[trial:]+arms[:trial]
                if trial%2:rotation=tuple(reversed(rotation))
                for arm in rotation:
                    t,cpu=time.perf_counter(),time.process_time();parts=run(arm)
                    trials.append({'arm':arm,'trial':trial,'seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-cpu,**parts})
                    comparisons+=len(manifest)
            med={a:statistics.median(t['seconds'] for t in trials if t['arm']==a) for a in ARMS}
            cohort_results[str(n)]={'full64_inputs':len(manifest),'without_discovered_center':sum(x is None for x in expected),'viable_positive':sum(x is True for x in expected),
                                     'seeds_per_second':{a:len(manifest)/v for a,v in med.items()},'time_change_percent':{a:100*(v/med['full64_direct']-1) for a,v in med.items()},'trials':trials}
            print(json.dumps({'discovery_included':cohort,'n':n,'time_change':cohort_results[str(n)]['time_change_percent']}),flush=True)
        results[cohort]=cohort_results
    report={'cohorts':results,'comparisons':comparisons,'differences':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'scope':'Three counterbalanced trials on 128 full64 inputs/cohort by default. Includes native full64 Stronghold discovery, both diagnostic contexts, bound/FFI preparation, count filtering and charged raw-cache reset. Excludes biome inventory, terrain, persistence, IPC and game generation. Missing Strongholds stay unresolved rather than actual-world rejections; extra diagnostic context setup is common to every arm.'}
    (OUT/'discovery-included-report.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
