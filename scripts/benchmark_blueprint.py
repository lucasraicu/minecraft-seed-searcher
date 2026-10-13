"""Bounded, reproducible Master Blueprint measurements; never invent rare-event yield.

Run phases separately so builds/tests do not compete with performance trials.
Reference comparisons keep the same blueprint requirements and full64 inputs.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import time

for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[_name] = '1'

ROOT = Path(__file__).resolve().parents[1]
KEYS = (120260001000, 120261001000, 120262001000)


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def identity():
    from seed_search.realm.capabilities import identity as backend_identity
    paths = [*ROOT.glob('src/seed_search/realm/*.py'), *ROOT.glob('native/*'),
             ROOT/'src/seed_search/backend.py', ROOT/'config/realm.yaml', Path(__file__)]
    return {'platform': platform.platform(), 'backend': backend_identity(),
            'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in paths if p.is_file()}}


def qualification(rows):
    return [(r['seed'], [(a['id'], a['qualification']) for a in r['anchors']]) for r in rows]


def serial(out, count, trials):
    from seed_search.realm.baseline import evaluate_seed
    from seed_search.realm.config import blueprint_config
    from seed_search.seeds import seed_from_index
    cfg = blueprint_config()
    seeds = [seed_from_index(i, KEYS[0]) for i in range(count)]
    result = {'scope': 'Single process, same blueprint constraints; includes full64 discovery, '
              'all discovered anchors, count checks, applicable biome gate and result construction. '
              'Reference inventories all requirements without short-circuit; no IPC/SQLite/terrain/BDS.',
              'identity': identity(), 'count': count, 'seeds': list(map(str, seeds)), 'trials': []}
    expected = None
    for trial in range(trials):
        order = ('reference', 'optimized') if trial % 2 == 0 else ('optimized', 'reference')
        for arm in order:
            start = time.perf_counter()
            rows = [evaluate_seed(i, s, cfg, combined=arm != 'reference',
                                  short_circuit=arm != 'reference') for i, s in enumerate(seeds)]
            elapsed = time.perf_counter() - start
            answers = qualification(rows)
            if expected is None:
                expected = answers
            assert answers == expected, 'Blueprint qualification differs from exhaustive reference'
            stages = Counter()
            for row in rows:
                stages.update(row['stage_seconds'])
            result['trials'].append({'trial': trial, 'arm': arm, 'seconds': elapsed,
                                     'input_seeds_per_second': count/elapsed, 'stages': dict(stages),
                                     'anchors': sum(len(r['anchors']) for r in rows)})
            print(json.dumps(result['trials'][-1]), flush=True)
            write(out/'serial.json', result)
    med = {arm: statistics.median(r['seconds'] for r in result['trials'] if r['arm'] == arm)
           for arm in ('reference', 'optimized')}
    result.update(median_seconds=med, speedup=med['reference']/med['optimized'],
                  wall_time_saved_percent=100*(1-med['optimized']/med['reference']),
                  qualification_comparisons=count*trials*2, differences=0)
    write(out/'serial.json', result)


def summarize_results(rows, cfg):
    stages, counts, passed, entered = Counter(), Counter(), Counter(), Counter()
    seeds = anchors = positives = positive_seeds = 0
    qualified_ids = []
    for result in rows:
        seeds += 1
        stages.update(result.get('stage_seconds', {}))
        counts.update(result.get('counts', {}))
        any_positive = False
        for a in result['anchors']:
            anchors += 1
            for name, observation in a['required_structures'].items():
                if name == 'stronghold' or observation.get('verification') == 'DEFERRED':
                    continue
                entered[name] += 1
                passed[name] += int(observation['floor_status'] == 'PREDICTED')
            for name, observation in a['required_nether_structures'].items():
                entered[name] += 1
                passed[name] += int(bool(observation['predicted_viable']))
            if a['biomes'] is not None:
                entered['biome_palette_4y'] += 1
                passed['biome_palette_4y'] += int(a['biomes']['qualification'] == 'PREDICTED')
            if a['qualification'] == 'PREDICTED':
                positives += 1
                any_positive = True
                qualified_ids.append(a['id'])
        positive_seeds += int(any_positive)
    steps = []
    for name in [*cfg['search']['structure_order'], 'fortress', 'bastion', 'biome_palette_4y']:
        key = ('biome_palette_4y' if name == 'biome_palette_4y' else
               'final_'+name if name in ('fortress', 'bastion') else 'structure_'+name)
        elapsed = stages[key]
        steps.append({'stage': name, 'entered_anchor_queries': entered[name],
                      'passed_anchor_queries': passed[name],
                      'conditional_pass_percent': 100*passed[name]/entered[name] if entered[name] else None,
                      'summed_worker_seconds': elapsed,
                      'seconds_per_entered_query': elapsed/entered[name] if entered[name] else None,
                      'serial_equivalent_queries_per_second': entered[name]/elapsed if elapsed else None})
    return {'input_seeds': seeds, 'anchors': anchors, 'predicted_qualifying_anchors': positives,
            'predicted_qualifying_seeds': positive_seeds, 'stages': dict(stages), 'counts': dict(counts),
            'funnel': steps, 'qualified_ids': sorted(qualified_ids),
            'stage_cost_note': 'Stage sums are inclusive worker elapsed costs, not aggregate CPU throughput. '
              'final_fortress/bastion wrappers exclude shared final_nether_pair generation cost. '
              'Unentered downstream stages have null conditional rates, never zero-percent probability.',
            'zero_success_one_sided_95_upper_bound': 1-math.pow(.05, 1/seeds) if not positive_seeds and seeds else None}


def scan(out, count, workers, trials):
    from seed_search.realm.config import blueprint_config, validate_config
    from seed_search.realm.capabilities import report
    from seed_search.realm.runner import run_scan
    from seed_search.realm.store import RealmStore
    cfg = blueprint_config()
    cfg['search']['workers'] = workers
    cfg['search']['native_threads_per_worker'] = 1
    validate_config(cfg)
    result = {'scope': 'Persisted production blueprint baseline: full64 discovery, all discovered '
              'anchors, short-circuit count and applicable four-Y gates, process startup, IPC, '
              'SQLite checkpoints and resource monitoring. Coastal terrain/BDS are separate.',
              'identity': identity(), 'workers': workers, 'native_threads_per_worker': 1,
              'cohorts': [], 'note': 'Three disjoint permutation-index intervals; independent full64 '
              'seed inputs, no high-bit sibling selection. Repeated trials do not add distinct seeds.'}
    for cohort, key in enumerate(KEYS):
        cfg['search']['run_key'] = str(key)
        cohort_result = {'cohort': cohort, 'run_key': str(key), 'input_count': count, 'trials': []}
        for trial in range(trials):
            run = out/f'scan-{workers}-c{cohort}-t{trial}'
            if run.exists():
                raise ValueError(f'Fresh benchmark path required: {run}')
            run.mkdir(parents=True)
            write(run/'compatibility.json', report(cfg))
            started = time.perf_counter()
            status = run_scan(cfg, run, count, workers=workers,
                              identity={'config': cfg, 'benchmark_identity': result['identity'],
                                        'count': count, 'cohort': cohort}, allow_prediction_scale=True)
            elapsed = time.perf_counter() - started
            assert status['completed_seeds'] == count and not status.get('interrupted')
            with RealmStore(run, resume=True) as store:
                summary = summarize_results(store.iter_results(), cfg)
            summary.update(trial=trial, wall_seconds=elapsed, input_seeds_per_second=count/elapsed,
                           storage_bytes=sum(p.stat().st_size for p in run.glob('realm.sqlite*')),
                           memory=status['memory'], worker_statistics=status['worker_statistics'])
            if cohort_result['trials']:
                assert summary['qualified_ids'] == cohort_result['trials'][0]['qualified_ids']
                assert summary['counts'] == cohort_result['trials'][0]['counts']
            cohort_result['trials'].append(summary)
            print(json.dumps({'cohort': cohort, 'trial': trial, 'workers': workers, 'wall_seconds': elapsed,
                              'input_seeds_per_second': count/elapsed, 'anchors': summary['anchors'],
                              'predicted_qualifying_seeds': summary['predicted_qualifying_seeds']}), flush=True)
            write(out/f'scan-{workers}.json', {**result, 'cohorts': result['cohorts']+[cohort_result]})
        result['cohorts'].append(cohort_result)
    result['distinct_full64_inputs'] = count*len(KEYS)
    result['total_evaluations'] = count*len(KEYS)*trials
    medians = [statistics.median(t['wall_seconds'] for t in c['trials']) for c in result['cohorts']]
    result['median_aggregate_input_seeds_per_second'] = count*len(KEYS)/sum(medians)
    write(out/f'scan-{workers}.json', result)


def diagnostic(out, count, trials):
    import numpy as np
    from seed_search.backend import Backend, configure_native_threads
    from seed_search.realm.blueprint import biome_palette
    from seed_search.realm.config import blueprint_config
    from seed_search.realm.bounds import square, native_bounds
    from seed_search.realm.sampling import BiomeSampler
    cfg = blueprint_config()
    centers = []
    for cohort in ('tuning', 'holdout'):
        path = ROOT/f'runs/locked-stronghold-2026-10-11/{cohort}/centers.json'
        centers += [{**r, 'cohort': cohort} for r in json.loads(path.read_text()) if r['first_center']][:count]
    result = {'identity': identity(), 'scope': 'Unconditional diagnostic queries at retained selected '
              'centers; correlated sibling cohorts, NOT conditional on passing blueprint structures.',
              'layouts': len(centers), 'biome_trials': [], 'raw_trials': [], 'count_trials': []}
    expected_biomes = None
    configure_native_threads(1)
    for trial in range(trials):
        for arm in (('full_inventory', 'capped') if trial % 2 == 0 else ('capped', 'full_inventory')):
            with_handles = [Backend(r['seed']) for r in centers]
            answers, queries = [], 0
            start = time.perf_counter()
            try:
                for b, r in zip(with_handles, centers):
                    data = biome_palette(BiomeSampler(b), square(r['center'],1536), cfg['biomes'],
                                         complete=arm == 'full_inventory')
                    answers.append(data['qualification'])
                    queries += data['sample_count']
            finally:
                elapsed = time.perf_counter()-start
                for b in with_handles:
                    b.close()
            if expected_biomes is None:
                expected_biomes = answers
            assert expected_biomes == answers
            result['biome_trials'].append({'trial':trial,'arm':arm,'seconds':elapsed,
                'layouts_per_second':len(centers)/elapsed,'points':queries,
                'passed':sum(a=='PREDICTED' for a in answers)})
        # Keep identical cheap-first predicate order for isolated first-N versus full-count benefit.
        for arm in (('full_inventory', 'capped') if trial % 2 == 0 else ('capped', 'full_inventory')):
            handles = [Backend(r['seed']) for r in centers]
            answers=[]; calls=0
            start=time.perf_counter()
            try:
                for b,r in zip(handles,centers):
                    good=True
                    for name in cfg['search']['structure_order']:
                        goal=cfg['structures']['minimum_counts'][name]
                        bounds=native_bounds(square(r['center'],1536))
                        points=(b.structure_count(name,bounds,goal) if arm=='capped' else b.structures(name,bounds,True))
                        calls+=1
                        if len(points)<goal:
                            good=False
                            break
                    answers.append(good)
            finally:
                elapsed=time.perf_counter()-start
                for b in handles:b.close()
            if arm=='full_inventory': full_answers=answers
            else: capped_answers=answers
            result['count_trials'].append({'trial':trial,'arm':arm,'seconds':elapsed,
                'layouts_per_second':len(centers)/elapsed,'calls':calls,'passed':sum(answers)})
        assert full_answers==capped_answers
        handles=[Backend(r['seed']) for r in centers]; calls=0; answers=[]
        start=time.perf_counter()
        try:
            for b,r in zip(handles,centers):
                good=True
                for name in cfg['search']['structure_order']:
                    if name=='mineshaft':continue  # no generator-free raw count semantics
                    calls+=1
                    if len(b.structures(name,native_bounds(square(r['center'],1536)),False)) < cfg['structures']['minimum_counts'][name]:
                        good=False;break
                answers.append(good)
        finally:
            elapsed=time.perf_counter()-start
            for b in handles:b.close()
        result['raw_trials'].append({'trial':trial,'seconds':elapsed,'layouts_per_second':len(centers)/elapsed,
              'passed':sum(answers),'calls':calls,'scope':'Overworld necessary raw capacity only; includes Trial Chamber '
              'full48 placement, excludes Mineshaft/Stronghold discovery/Nether and all viability.'})
        write(out/'diagnostics.json', result)
        print(json.dumps({'diagnostic_trial':trial,'biome':result['biome_trials'][-1],
                          'counts':result['count_trials'][-1],'raw':result['raw_trials'][-1]}),flush=True)
    write(out/'diagnostics.json',result)


def per_type_counts(out, count, trials):
    from contextlib import ExitStack
    from seed_search.backend import Backend, configure_native_threads
    from seed_search.realm.config import blueprint_config
    from seed_search.realm.bounds import square, native_bounds, nether_square
    cfg=blueprint_config();configure_native_threads(1)
    path=ROOT/'runs/locked-stronghold-2026-10-11/holdout/centers.json'
    rows=[r for r in json.loads(path.read_text()) if r['first_center']][:count]
    goals={**cfg['structures']['minimum_counts'],**cfg['structures']['nether_minimum_counts']}
    goals.pop('stronghold')
    result={'identity':identity(),'scope':'Unconditional native per-type capped-vs-full viable-start '
        'queries at retained held-out selected centers; setup excluded. Mansion here is the native '
        'viable predicate before the separate fixed-Y Dark Forest policy. Serial, correlated cohorts; '
        'these rates are per entered query, not final-world yield or full search input throughput.',
        'layouts':len(rows),'trials':[],'comparisons':0,'differences':0}
    with ExitStack() as stack:
        handles=[stack.enter_context(Backend(r['seed'])) for r in rows]
        for name,goal in goals.items():
            bounds=[native_bounds(nether_square(r['center'],896) if name in ('fortress','bastion')
                                  else square(r['center'],1536)) for r in rows]
            expected=[b.structures(name,nb,True) for b,nb in zip(handles,bounds)]
            for trial in range(trials):
                for arm in (('full_inventory','first_n') if trial%2==0 else ('first_n','full_inventory')):
                    start=time.perf_counter()
                    answers=[b.structure_count(name,nb,goal) if arm=='first_n' else b.structures(name,nb,True)
                             for b,nb in zip(handles,bounds)]
                    elapsed=time.perf_counter()-start
                    for answer,full in zip(answers,expected):
                        assert (len(answer)>=goal)==(len(full)>=goal)
                        assert set(answer).issubset(full)
                        result['comparisons']+=1
                    result['trials'].append({'name':name,'goal':goal,'arm':arm,'trial':trial,
                        'seconds':elapsed,'entered_queries_per_second':len(rows)/elapsed,
                        'individual_floor_positives':sum(len(x)>=goal for x in answers)})
    result['per_type']={}
    for name,goal in goals.items():
        med={arm:statistics.median(t['seconds'] for t in result['trials'] if t['name']==name and t['arm']==arm)
             for arm in ('full_inventory','first_n')}
        result['per_type'][name]={'goal':goal,'median_seconds':med,
            'queries_per_second':{arm:len(rows)/v for arm,v in med.items()},
            'speedup':med['full_inventory']/med['first_n'],
            'wall_time_saved_percent':100*(1-med['first_n']/med['full_inventory'])}
    write(out/'per-type-counts.json',result)
    print(json.dumps({'per_type':result['per_type'],'comparisons':result['comparisons'],'differences':0}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['serial','scan','diagnostic','counts'])
    parser.add_argument('--output',type=Path,default=ROOT/'runs/blueprint-audit-2026-10-12')
    parser.add_argument('--count',type=int,default=64)
    parser.add_argument('--trials',type=int,default=3)
    parser.add_argument('--workers',type=int,default=30)
    args=parser.parse_args()
    if not 1<=args.count<=10000 or not 1<=args.trials<=5 or not 1<=args.workers<=36:
        parser.error('Use 1–10000 inputs, 1–5 trials and 1–36 workers')
    args.output.mkdir(parents=True,exist_ok=True)
    if args.phase=='scan':scan(args.output,args.count,args.workers,args.trials)
    elif args.phase=='serial':serial(args.output,args.count,args.trials)
    elif args.phase=='diagnostic':diagnostic(args.output,args.count,args.trials)
    else:per_type_counts(args.output,args.count,args.trials)


if __name__=='__main__':main()
