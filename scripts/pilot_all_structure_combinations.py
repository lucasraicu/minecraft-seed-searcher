"""Matched exact-center structure-combination pilot; no production policy changes."""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import statistics
import time

from seed_search import _native
from seed_search.backend import Backend, STRUCTURES
from scripts.pilot_locked_stronghold import raw_presence, current_viability

NETHER = frozenset(('fortress', 'bastion', 'ruined_portal_nether'))
# These 16 placement families passed the preceding 30,208 exact-border
# lower/full64 layout comparisons. This does NOT certify their biome viability.
MT = ('village', 'ancient_city', 'ruined_portal', 'shipwreck', 'monument',
      'outpost', 'fortress', 'bastion', 'desert_pyramid', 'jungle_temple',
      'swamp_hut', 'igloo', 'ocean_ruin', 'mansion', 'buried_treasure',
      'ruined_portal_nether')
CURRENT = ('village', 'ancient_city', 'fortress', 'bastion')
PROFILES = {'current_four': CURRENT,
            'plus_mansion_outpost': CURRENT + ('mansion', 'outpost'),
            'all_16_mt_families': MT,
            'all_21_overworld_nether': tuple(n for n in STRUCTURES if n not in ('stronghold', 'end_city'))}


def query_bounds(row, name):
    # End control uses the same coordinate-centered 1536 square in the END.
    # It is a diagnostic window, not a new production border requirement.
    return row['bounds']['nether' if name in NETHER else 'overworld']


def direct(backend, row, order):
    return all(backend.structure_first(name, query_bounds(row, name)) is not None for name in order)


def expanded_raw(backend, row, order):
    # Current bounded raw scanner implementation, including its actual query
    # and list-allocation cost. No precomputed/free raw result is timed as work.
    return all(bool(backend.structures(name, query_bounds(row, name), viable=False)) for name in order)


def greedy_order(rows, observations, names, key='viable', time_key='seconds'):
    remaining = list(names)
    survivors = list(range(len(rows)))
    order = []
    while remaining:
        def score(name):
            rejected = sum(not observations[i][name][key] for i in survivors)
            cost = sum(observations[i][name][time_key] for i in survivors)
            return rejected / max(cost, 1e-12)
        best = max(remaining, key=score)
        order.append(best)
        survivors = [i for i in survivors if observations[i][best][key]]
        remaining.remove(best)
    return order


def benchmark(handles, rows, order, raw_order, expected, repeats, current=False):
    arms = ('direct', 'native_four_gate', 'expanded_mt_gate')
    def run(arm, backend, row):
        if arm == 'native_four_gate' and not raw_presence(backend.seed & 0xffffffff, row['bounds']):
            return False
        if arm == 'expanded_mt_gate' and not expanded_raw(backend, row, raw_order):
            return False
        return current_viability(backend, row['bounds']) if current else direct(backend, row, order)
    for arm in arms:
        assert [run(arm, b, r) for b, r in zip(handles, rows)] == expected
    trials = []
    for trial in range(6):
        rotation = arms[trial % 3:] + arms[:trial % 3]
        if trial >= 3:
            rotation = tuple(reversed(rotation))
        for arm in rotation:
            start, cpu = time.perf_counter(), time.process_time()
            for _ in range(repeats):
                answers = [run(arm, b, r) for b, r in zip(handles, rows)]
                assert answers == expected
            trials.append({'trial': trial, 'arm': arm, 'seconds': time.perf_counter()-start,
                           'cpu_seconds': time.process_time()-cpu})
    medians = {a: statistics.median(t['seconds'] for t in trials if t['arm'] == a) for a in arms}
    return {'trials': trials, 'median_seconds': medians,
            'stage_centers_per_second': {a: len(rows)*repeats/v for a, v in medians.items()},
            'time_change_percent': {a: 100*(v/medians['direct']-1) for a,v in medians.items()},
            'viable_positive_centers': sum(expected), 'center_inputs': len(rows),
            'repetitions_per_trial': repeats, 'direct_order': order, 'expanded_raw_order': raw_order}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=Path('runs/locked-stronghold-2026-10-11'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--repeats', type=int, default=8)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    inputs = {cohort: [r for r in json.loads((args.input/cohort/'centers.json').read_text()) if r['first_center']]
              for cohort in ('tuning', 'holdout')}
    assert not ({r['low32'] for r in inputs['tuning']} & {r['low32'] for r in inputs['holdout']})
    identity = {'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'native_sha256': hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest(),
                'parent_sha256': {c: hashlib.sha256((args.input/c/'centers.json').read_bytes()).hexdigest() for c in inputs},
                'center_policy': 'first discovered sorted Stronghold; frozen before any filter',
                'geometry': '4000-square discovery; 1536-square OW; 896-square Nether at exact /8 center',
                'end_control': 'End dimension, same X/Z center and 1536-square window; diagnostic only',
                'profiles': PROFILES, 'raw_mt': MT,
                'scope': 'Single-process conditional structure-existence stage. Excludes discovery, handle creation, biome inventory, terrain, persistence and game generation.'}
    for c in inputs:
        assert json.loads((args.input/c/'identity.json').read_text())['native_sha256'] == identity['native_sha256']
    (args.output/'identity.json').write_text(json.dumps(identity, indent=2)+'\n')
    observations, results, orders, raw_orders = {}, {}, {}, {}
    comparisons = 0
    for cohort, rows in inputs.items():
        with ExitStack() as stack:
            handles = [stack.enter_context(Backend(r['seed'])) for r in rows]
            obs = []
            for i, (b, row) in enumerate(zip(handles, rows)):
                item = {}
                for name in STRUCTURES:
                    if name == 'stronghold':
                        continue
                    start = time.perf_counter()
                    witness = b.structure_first(name, query_bounds(row, name))
                    seconds = time.perf_counter()-start
                    item[name] = {'viable': witness is not None, 'witness': witness, 'seconds': seconds}
                    if name in MT:
                        start = time.perf_counter()
                        raw = b.structures(name, query_bounds(row, name), viable=False)
                        item[name].update(raw=bool(raw), raw_seconds=time.perf_counter()-start)
                        assert witness is None or tuple(witness) in raw
                        assert bool(raw) == bool(row['family_raw_counts'][name if name not in ('jungle_temple','swamp_hut','igloo') else 'desert_pyramid'])
                        comparisons += 1
                    if i < 16:
                        complete = b.structures(name, query_bounds(row, name), viable=True)
                        assert bool(complete) == (witness is not None)
                        assert witness is None or tuple(witness) in complete
                        comparisons += 1
                obs.append(item)
                if (i+1) % 128 == 0:
                    print(json.dumps({'cohort': cohort, 'inventory_complete': i+1}), flush=True)
            observations[cohort] = obs
            (args.output/f'{cohort}-observations.json').write_text(json.dumps(obs, indent=2)+'\n')
            if cohort == 'tuning':
                for profile, names in PROFILES.items():
                    orders[profile] = greedy_order(rows, obs, names)
                    raw_orders[profile] = greedy_order(rows, obs, [n for n in names if n in MT], 'raw', 'raw_seconds')
            cohort_results = {}
            for profile, names in PROFILES.items():
                expected = [all(o[n]['viable'] for n in names) for o in obs]
                raw_positive = sum(all(o[n]['raw'] for n in names if n in MT) for o in obs)
                timing = benchmark(handles, rows, orders[profile], raw_orders[profile], expected, args.repeats,
                                   current=profile == 'current_four')
                timing.update(raw_missing_centers=len(rows)-raw_positive,
                              raw_missing_percent=100*(len(rows)-raw_positive)/len(rows))
                cohort_results[profile] = timing
                print(json.dumps({'cohort':cohort,'profile':profile,
                                  'timing_change_percent':timing['time_change_percent']}),flush=True)
            cohort_results['individual_structures'] = {
                n: {'positive_centers':sum(o[n]['viable'] for o in obs),
                    'mean_microseconds':1e6*statistics.mean(o[n]['seconds'] for o in obs),
                    'max_microseconds':1e6*max(o[n]['seconds'] for o in obs)}
                for n in STRUCTURES if n != 'stronghold'}
            # Increasing combinations along the tuned all-structure order.
            order = orders['all_21_overworld_nether']
            cohort_results['increasing_combinations'] = [
                {'required':order[:k], 'viable_positive_centers':sum(all(o[n]['viable'] for n in order[:k]) for o in obs),
                 'raw_missing_centers':sum(not all(o[n]['raw'] for n in order[:k] if n in MT) for o in obs)}
                for k in range(1,len(order)+1)]
            cohort_results['all_22_with_end_control_positive'] = sum(
                all(o[n]['viable'] for n in STRUCTURES if n != 'stronghold') for o in obs)
            results[cohort] = cohort_results
    keys = [(r['low32'],tuple(r['bounds']['overworld']),tuple(r['bounds']['nether'])) for rows in inputs.values() for r in rows]
    report = {'cohorts':results, 'comparisons':comparisons, 'differences':0,
              'exact_center_keys':len(keys), 'unique_exact_center_keys':len(set(keys)),
              'limits':identity['scope']+' Expanded gate times the existing complete raw scanner, not a new fused native implementation. '
                       'All-structure rarity includes full64 biome constraints that a lower32 placement gate cannot apply. '
                       'No whole lower32 family can be rejected from a failed selected border. Stronghold is the previously discovered anchor, not rechecked. '
                       'The 128 seeds with no discovered Stronghold in the parent pilot are not represented here; detector recall remains unresolved.'}
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'completed':True,'comparisons':comparisons,'differences':0}),flush=True)

if __name__ == '__main__':
    main()
