"""Lower32 diagnostics at explicit full64-discovered Stronghold borders only.

No envelope or possible-center solver. The one-center diagnostic fixes the first
discovered center in the pipeline's sorted order before any placement screening.
Production still evaluates all discovered centers and its selection is unchanged.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import time

from seed_search import _native
from seed_search.backend import Backend, RAW_MT_TYPES, raw_layout, sweep_raw
from seed_search.realm.bounds import contains, native_bounds, nether_square, square
from seed_search.realm.config import default_config
from seed_search.realm.baseline import structure_observation
from scripts.pilot_common_centers import BASE, FEATURES, GROUPS, NETHER, PROFILES


def exact_bounds(center):
    return {'overworld': native_bounds(square(center, 1536)),
            'nether': native_bounds(nether_square(center, 896))}


def raw_presence(low, bounds):
    ow, nether = bounds['overworld'], bounds['nether']
    # Existing optimized mode has a fixed five-family signature. The fifth
    # Fortress is redundant here: give it the same exact deployment bound.
    # There is no discovery/envelope query in this gate.
    result = sweep_raw(low, 1, (('village', ow), ('ancient_city', ow),
                               ('fortress', nether), ('bastion', nether),
                               ('fortress', nether)), mode='presence')[0]
    return bool(result.all())


def current_viability(backend, bounds):
    pair = backend.nether_structure_pairs(bounds['nether'])
    if not all(pair[n][1] for n in ('fortress', 'bastion')):
        return False
    if backend.structure_first('ancient_city', bounds['overworld']) is None:
        return False
    return backend.structure_first('village', bounds['overworld']) is not None


def gated_viability(backend, bounds):
    if not raw_presence(backend.seed & 0xffffffff, bounds):
        return False
    return current_viability(backend, bounds)


def summarize(rows):
    return {name: {'centers': len(rows), 'raw_positive': sum(r['profiles'][name] for r in rows),
                   'raw_missing': sum(not r['profiles'][name] for r in rows),
                   'raw_missing_percent': 100 * sum(not r['profiles'][name] for r in rows) / len(rows) if rows else None}
            for name in PROFILES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--low-count', type=int, default=128)
    args = parser.parse_args()
    parent = json.loads((args.input / 'identity.json').read_text())
    if not 1 <= args.low_count <= len(parent['manifest']):
        parser.error('Low-count must fit input manifest')
    args.output.mkdir(parents=True, exist_ok=True)
    cfg = default_config()
    discovery = cfg['discovery']['overworld_bounds']
    manifest = []
    for item in parent['manifest'][:args.low_count]:
        for upper in (1, 0x12345678, 0x89abcdef, 0xffffffff):
            unsigned = (upper << 32) | item['low32']
            manifest.append({'low32': item['low32'], 'upper32': upper,
                             'seed': str(unsigned if unsigned < 1 << 63 else unsigned - (1 << 64))})
    identity = {'version': 'locked-stronghold-pilot-v1', 'manifest': manifest,
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'native_sha256': hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest(),
                'parent_manifest_sha256': hashlib.sha256((args.input / 'identity.json').read_bytes()).hexdigest(),
                'geometry': cfg['deployment'], 'one_center_policy': 'first discovered sorted center, fixed before raw screening; diagnostic only',
                'limits': __doc__}
    assert identity['native_sha256'] == parent['native_sha256']
    (args.output / 'identity.json').write_text(json.dumps(identity, indent=2)+'\n')
    seeds = []
    rows = []
    comparisons = 0
    discovery_seconds = 0.
    start = time.perf_counter()
    for i, item in enumerate(manifest):
        with Backend(item['seed']) as full, Backend(item['low32']) as lower:
            t = time.perf_counter()
            centers = structure_observation(full, 'stronghold', discovery, combined=True)['predicted_viable']
            discovery_seconds += time.perf_counter() - t
            seed_row = {**item, 'centers': centers}
            seeds.append(seed_row)
            for number, center in enumerate(centers):
                bounds = exact_bounds(center)
                native_raw = {}
                for name in GROUPS:
                    b = bounds['nether' if name in NETHER else 'overworld']
                    native_raw[name] = full.structures(name, b, viable=False)
                    values = raw_layout(item['low32'], name, b) if name in RAW_MT_TYPES else lower.structures(name, b, viable=False)
                    assert values == native_raw[name], (item, center, name)
                    comparisons += 1
                # Check all four shared types directly in the locked bounds.
                for name in FEATURES[1:]:
                    reference = full.structures(name, bounds['overworld'], False)
                    values = lower.structures(name, bounds['overworld'], False)
                    assert values == reference == native_raw['desert_pyramid']
                    comparisons += 1
                profiles = {name: all(len(native_raw[n]) >= required for n, required in requirements.items())
                            for name, requirements in PROFILES.items()}
                assert raw_presence(item['low32'], bounds) == profiles['current_four']
                rows.append({**item, 'center': center, 'first_center': number == 0,
                             'bounds': bounds, 'profiles': profiles,
                             'family_raw_counts': {n: len(v) for n, v in native_raw.items()}})
        if (i + 1) % 128 == 0:
            print(json.dumps({'completed_full64': i + 1, 'centers': len(rows), 'seconds': time.perf_counter() - start}), flush=True)
    parity_seconds = time.perf_counter() - start
    first = [r for r in rows if r['first_center']]

    # Same explicit centers and cached query inputs for both arms. Stronghold
    # discovery is charged separately, not repeated inside this stage benchmark.
    trials = []
    reference = None
    for trial in range(3):
        for arm in (('direct', 'lower32_gate') if trial % 2 == 0 else ('lower32_gate', 'direct')):
            fn = current_viability if arm == 'direct' else gated_viability
            answers = []
            t, cpu = time.perf_counter(), time.process_time()
            for seed_row in seeds:
                with Backend(seed_row['seed']) as backend:
                    for center in seed_row['centers']:
                        answers.append(fn(backend, exact_bounds(center)))
            seconds = time.perf_counter() - t
            if reference is None:
                reference = answers
            assert answers == reference
            trials.append({'trial': trial, 'arm': arm, 'seconds': seconds,
                           'cpu_seconds': time.process_time() - cpu, 'viability_positive_centers': sum(answers)})
    medians = {arm: statistics.median(r['seconds'] for r in trials if r['arm'] == arm)
               for arm in ('direct', 'lower32_gate')}
    by_low = defaultdict(list)
    for r in seeds:
        by_low[r['low32']].append(r)
    changed = sum(len({tuple(map(tuple, r['centers'])) for r in family}) > 1 for family in by_low.values())
    first_by_low = defaultdict(list)
    for r in first:
        first_by_low[r['low32']].append(r)
    example = next((family for family in first_by_low.values()
                    if len({r['profiles']['current_four'] for r in family}) > 1), None)
    report = {'full64_inputs': len(seeds), 'distinct_lower32': args.low_count,
              'without_discovered_center': sum(not r['centers'] for r in seeds),
              'all_discovered_centers': summarize(rows), 'one_locked_center_per_seed': summarize(first),
              'raw_layout_comparisons': comparisons, 'raw_layout_differences': 0,
              'center_lists_changed_with_upper32_families': changed,
              'same_lower32_different_locked_center_example': example,
              'stronghold_discovery_seconds': discovery_seconds, 'parity_invocation_seconds': parity_seconds,
              'current_four_viability_stage': {'trials': trials, 'median_seconds': medians,
                   'gate_time_change_percent': 100 * (medians['lower32_gate']/medians['direct'] - 1),
                   'stage_scope': 'Exact-center final Nether pair then City and Village viability only; includes handle setup/bound conversion. '
                                  'Excludes initial discovery Fortress, Trial Chamber, Mineshaft, wooded biome gate, persistence, terrain and actual generation.'},
              'limits': 'Raw-positive means only that necessary placements exist. Center discovery and biome viability are full64. '
                        'No whole-lower32 family is rejected from a single-center failure; missing Strongholds remain unresolved. '
                        'New raw families remain diagnostic, not promoted into the certified public adapter.'}
    (args.output / 'centers.json').write_text(json.dumps(rows, indent=2)+'\n')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'same_lower32_different_locked_center_example'}, indent=2))


if __name__ == '__main__':
    main()
