"""Matched finite border pilots with production baseline/terrain evaluators.

Hypothetical bounds are isolated in diagnostic identities; no public profile,
geometry thresholds, or game-certification policy is changed. Spawned baseline
workers must not import the terrain/scipy stack at module import time.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import statistics
import time

from seed_search.realm.cli import load, make_identity, run_benchmark
from seed_search.realm.store import RealmStore, canonical

ROOT = Path(__file__).resolve().parents[1]
OW = [1024, 1280, 1536, 1792, 2048, 2304, 2380]
NETHER = [512, 640, 768, 896, 1024]
STAGES = ['discovered_stronghold', 'initial_fortress', 'final_fortress',
          'final_bastion', 'ancient_city', 'village', 'trial_chamber',
          'mineshaft', 'wooded_families']
SAMPLE_KEY = 'compact-border-funnel-2026-10-10-v1:'


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_db(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)


def key(ow, nether):
    return f'ow-{ow}-nether-{nether}'


def config(production, ow, nether):
    cfg = copy.deepcopy(production)
    cfg['discovery'] = {'overworld_bounds': [-2000, -2000, 2000, 2000],
                        'nether_bounds': [-2000, -2000, 2000, 2000]}
    cfg['deployment'] = {'overworld_side_blocks': ow, 'nether_side_blocks': nether}
    control = copy.deepcopy(cfg)
    control['discovery'] = copy.deepcopy(production['discovery'])
    control['deployment'] = copy.deepcopy(production['deployment'])
    assert control == production
    return cfg


def inspect_baseline(path, count):
    db = read_db(path)
    members, discovered, inputs = set(), set(), hashlib.sha256()
    retained = {name: set() for name in STAGES}
    seed_sets = {name: set() for name in STAGES}
    queries = collections.Counter()
    try:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        sequence = list(db.execute('SELECT idx,seed FROM seeds ORDER BY idx'))
        assert len(sequence) == count and len({r[1] for r in sequence}) == count
        assert [int(r[0]) for r in sequence] == list(range(count))
        for idx, seed in sequence:
            inputs.update(f'{idx}:{seed}\n'.encode())
        assert not db.execute('SELECT 1 FROM variants LIMIT 1').fetchone()
        assert not db.execute("SELECT 1 FROM candidates WHERE qualification='VERIFIED' LIMIT 1").fetchone()
        for cid, qualification, payload in db.execute('SELECT id,qualification,result FROM candidates'):
            candidate = json.loads(payload)
            discovered.add(cid)
            flags = [True, bool(candidate['initial_fortress']['predicted_viable'])]
            flags += [bool(candidate['required_nether_structures'][n]['predicted_viable'])
                      for n in ('fortress', 'bastion')]
            flags += [bool(candidate['required_structures'][n]['predicted_viable'])
                      for n in ('ancient_city', 'village', 'trial_chamber', 'mineshaft')]
            flags += [bool(candidate['biomes'] and candidate['biomes']['qualification'] != 'PENDING')]
            live = True
            for name, flag in zip(STAGES, flags):
                live = live and flag
                if live:
                    retained[name].add(cid)
                    seed_sets[name].add(candidate['seed'])
            assert (qualification == 'PREDICTED') == live
            if live:
                members.add(cid)
            for name, value in candidate['required_structures'].items():
                if name != 'stronghold' and value.get('verification') != 'DEFERRED':
                    queries[name] += 1
            queries['final_fortress'] += 1
            queries['final_bastion'] += 1
            queries['wooded_families'] += int(candidate['biomes'] is not None)
        stages = []
        previous = len(discovered)
        for name in STAGES:
            current = len(retained[name])
            stages.append({'stage': name, 'surviving_anchors': current,
                           'surviving_seeds': len(seed_sets[name]),
                           'newly_pending_anchors': previous-current,
                           'conditional_retention_percent': 100*current/previous if previous else None})
            previous = current
        ranges = list(db.execute('SELECT start,end,status FROM ranges ORDER BY start'))
        cursor = 0
        for start, end, status in ranges:
            assert int(start) == cursor and status == 'complete'
            cursor = int(end)
        assert cursor == count
    finally:
        db.close()
    return {'members': sorted(members), 'discovered': sorted(discovered),
            'input_sequence_sha256': inputs.hexdigest(), 'stages': stages,
            'anchor_query_counts': dict(queries)}


def check_sources(root, production):
    before = json.loads((root / 'source-identity.json').read_text())
    for relative, expected in before['source_sha256'].items():
        assert sha(ROOT / relative) == expected, f'Changed existing source: {relative}'
    assert sha(ROOT / 'config/realm.yaml') == before['production_config_sha256']
    assert make_identity(production, 1000, 0) == before['production_identity']
    return len(before['source_sha256'])


def baseline(root, production):
    target = root / 'baseline.json'
    if target.exists():
        return json.loads(target.read_text())
    pairs = [(ow, n) for ow in OW for n in NETHER]
    rows, members, funnels, all_ids, input_hashes = [], {}, {}, None, set()
    for trial in range(2):
        order = pairs if trial == 0 else list(reversed(pairs))
        for ow, n in order:
            label = key(ow, n)
            folder = root / 'baseline' / f'trial-{trial}-{label}'
            row_path = folder / 'measurement.json'
            if row_path.exists():
                result = json.loads(row_path.read_text())
            else:
                cfg = config(production, ow, n)
                folder.mkdir(parents=True, exist_ok=True)
                save(folder / 'config.json', cfg)
                if not (folder / 'benchmark.json').exists():
                    run_benchmark(cfg, folder, 1000, [30])
                row = json.loads((folder / 'benchmark.json').read_text())['rows'][0]
                audited = inspect_baseline(folder / 'workers-30/realm.sqlite', 1000)
                result = {'trial': trial, 'pair': label, 'ow': ow, 'nether': n,
                          'benchmark': row, **audited}
                save(row_path, result)
            input_hashes.add(result['input_sequence_sha256'])
            discovered = set(result['discovered'])
            if all_ids is None:
                all_ids = discovered
            assert all_ids == discovered
            ids = set(result['members'])
            if label in members:
                assert members[label] == ids
                assert funnels[label] == result['stages']
            members[label] = ids
            funnels[label] = result['stages']
            rows.append({k: v for k, v in result.items() if k not in ('members', 'discovered')})
            save(root / 'baseline-progress.json', rows)
            print(json.dumps({'baseline_trial': trial, 'pair': label, 'completed': len(rows),
                              'total': 70, 'qualifying_anchors': len(ids),
                              'seeds_per_second': result['benchmark']['seeds_per_second']}), flush=True)
    assert len(input_hashes) == 1
    nesting_exceptions = []
    for ow, n in pairs:
        for larger_ow, larger_n in pairs:
            if ow <= larger_ow and n <= larger_n:
                missing = members[key(ow, n)] - members[key(larger_ow, larger_n)]
                if missing:
                    # Changing a half-width by a nonmultiple of the biome step
                    # changes the sample lattice. Structure membership remains
                    # nested, while observed wooded-family coverage need not.
                    assert ((larger_ow-ow)//2) % production['biomes']['spacing'] != 0
                    folder = root / 'baseline' / f'trial-0-{key(larger_ow, larger_n)}'
                    db = read_db(folder / 'workers-30/realm.sqlite')
                    try:
                        for cid in sorted(missing):
                            c = json.loads(db.execute('SELECT result FROM candidates WHERE id=?', (cid,)).fetchone()[0])
                            assert c['pending_reasons'] == ['wooded_family_coverage']
                            nesting_exceptions.append({'smaller_pair': key(ow, n),
                                'larger_pair': key(larger_ow, larger_n), 'candidate_id': cid,
                                'pending_reasons': c['pending_reasons'],
                                'interpretation': 'Changed 64-block biome sample lattice; all required structure predictions still qualify.'})
                    finally:
                        db.close()
    prior = json.loads((ROOT / 'runs/joint-border-comparison-2026-10-10/baseline.json').read_text())
    overlaps = []
    for label in members.keys() & prior['memberships'].keys():
        assert members[label] == set(prior['memberships'][label])
        overlaps.append(label)
    assert next(iter(input_hashes)) == prior['input_sequence_sha256']
    summary = []
    for ow, n in pairs:
        label = key(ow, n)
        trials = [r['benchmark'] for r in rows if r['pair'] == label]
        rates = [r['seeds_per_second'] for r in trials]
        stages = sorted(set.union(*(set(t['worker_statistics']['stage_seconds']) for t in trials)))
        summary.append({'pair': label, 'overworld_side': ow, 'nether_side': n,
                        'median_seeds_per_second': statistics.median(rates),
                        'range_seeds_per_second': [min(rates), max(rates)],
                        'qualifying_anchors': len(members[label]),
                        'qualifying_seeds': funnels[label][-1]['surviving_seeds'],
                        'qualifying_anchors_per_second': len(members[label])/1000*statistics.median(rates),
                        'funnel': funnels[label],
                        'median_summed_stage_seconds': {s: statistics.median(t['worker_statistics']['stage_seconds'].get(s, 0) for t in trials) for s in stages},
                        'median_storage_bytes': statistics.median(t['storage_bytes'] for t in trials)})
    result = {'summary': summary, 'trials': rows,
              'memberships': {k: sorted(v) for k, v in members.items()},
              'discovered_anchors': len(all_ids), 'distinct_inputs': 1000,
              'total_evaluations': 70000, 'matched_prior_arms': sorted(overlaps),
              'full_baseline_nesting_exceptions': nesting_exceptions,
              'input_sequence_sha256': next(iter(input_hashes)),
              'source_files_unchanged': check_sources(root, production)}
    save(target, result)
    return result


def strict_pass(result):
    fit = result.get('border_fit', {})
    return (result.get('geometry_pass') is True and result.get('qualification') == 'PREDICTED'
            and fit.get('state') == 'within' and fit.get('complete') is True
            and result.get('sampling_schedule', {}).get('last_height_resolution') == 4)


def hash_order(ids):
    return sorted(ids, key=lambda cid: (hashlib.sha256((SAMPLE_KEY + cid).encode()).hexdigest(), cid))


def unique_seeds(ids, count, excluded=()):
    seeds = {cid.rsplit(':', 2)[0] for cid in excluded}
    chosen = []
    for cid in hash_order(ids):
        seed = cid.rsplit(':', 2)[0]
        if seed in seeds:
            continue
        chosen.append(cid)
        seeds.add(seed)
        if len(chosen) == count:
            break
    assert len(chosen) == count
    return chosen


def terrain_stage_counts(store):
    result = {}
    tasks = []
    for variant, payload, encoded, status in store.db.execute('SELECT variant,payload,result,status FROM terrain_work'):
        item = json.loads(payload)
        if not encoded:
            continue
        value = json.loads(encoded).get('result', {})
        results = value.get('proposals', []) if item['stage'] == 'nomination' else value.get('evaluated_centers', [])
        name = f"{variant}:resolution-{item['resolution']}"
        counts = result.setdefault(name, {'evaluated_center_observations': 0, 'geometry_pass': 0,
                                         'complete_within': 0, 'geometry_and_complete_within': 0,
                                         'strict_finest_pass': 0, 'reasons': {}})
        for r in results:
            fit = r.get('border_fit', {})
            within = fit.get('state') == 'within' and fit.get('complete') is True
            counts['evaluated_center_observations'] += 1
            counts['geometry_pass'] += int(r['geometry_pass'])
            counts['complete_within'] += int(within)
            counts['geometry_and_complete_within'] += int(r['geometry_pass'] and within)
            # Per-center records do not carry scheduling metadata; attach resolution.
            rr = {**r, 'sampling_schedule': {'last_height_resolution': item['resolution']}}
            counts['strict_finest_pass'] += int(strict_pass(rr))
            for reason in r.get('reasons', []):
                counts['reasons'][reason] = counts['reasons'].get(reason, 0)+1
        tasks.append({'variant': variant, 'stage': item['stage'], 'resolution': item['resolution'],
                      'status': status, 'coarse_center': item['coarse_center']})
    return result, tasks


def terrain(root, production, base):
    from seed_search.realm.terrain import run_terrain
    memberships = {k: set(v) for k, v in base['memberships'].items()}
    common = unique_seeds(memberships[key(1024, 512)], 2)
    per_ow = {str(ow): unique_seeds(memberships[key(ow, 1024)]-set(common), 4, common) for ow in OW}
    selection = {'sample_key': SAMPLE_KEY, 'common_controls': common,
                 'random_eligible_per_overworld': per_ow,
                 'method': 'Two shared independent-seed controls from the smallest pair; four additional independent-seed hash picks per OW from its 1024-Nether qualifying pool. Groups reported separately.'}
    save(root / 'selection.json', selection)
    rows = []
    # Interleave sizes across sample positions to distribute thermal/order effects.
    for position in range(6):
        sizes = OW[position % len(OW):] + OW[:position % len(OW)]
        for ow in sizes:
            group = 'common_control' if position < 2 else 'random_eligible'
            cid = common[position] if position < 2 else per_ow[str(ow)][position-2]
            folder = root / 'terrain' / f'ow-{ow}-sample-{position}'
            measurement = folder / 'measurement.json'
            if measurement.exists():
                rows.append(json.loads(measurement.read_text()))
                continue
            cfg = config(production, ow, 1024)
            source = root / 'baseline' / f'trial-0-{key(ow, 1024)}' / 'workers-30/realm.sqlite'
            db = read_db(source)
            try:
                idx, seed, encoded = db.execute('SELECT idx,seed,result FROM candidates WHERE id=?', (cid,)).fetchone()
                candidate = json.loads(encoded)
            finally:
                db.close()
            assert candidate['qualification'] == 'PREDICTED'
            folder.mkdir(parents=True, exist_ok=True)
            save(folder / 'config.json', cfg)
            save(folder / 'imported-candidate.json', candidate)
            identity = {**make_identity(cfg, 1, int(idx)), 'diagnostic_import': {
                'source': str(source.relative_to(ROOT)), 'candidate_id': cid,
                'candidate_sha256': hashlib.sha256(canonical(candidate).encode()).hexdigest()}}
            checkpoint = folder / 'realm.sqlite'
            with RealmStore(folder, identity=identity, resume=checkpoint.exists()) as store:
                if not checkpoint.exists() or store.db.execute('SELECT count(*) FROM seeds').fetchone()[0] == 0:
                    store.configure_range(int(idx), int(idx)+1, 1)
                    assert store.claim_range('diagnostic-import') == (int(idx), int(idx)+1)
                    store.complete_range(int(idx), int(idx)+1, [{'index': int(idx), 'seed': seed, 'anchors': [candidate]}])
                started = time.perf_counter()
                run_summary = run_terrain(store, cfg)
                seconds = time.perf_counter()-started
                assert not run_summary.get('resource_blocked')
                variants = list(store.iter_variants())
                stages, tasks = terrain_stage_counts(store)
                assert all(v['result']['evidence'] in {'PREDICTED', 'PARTIAL'} for v in variants)
            result = {'candidate_id': cid, 'sample_group': group, 'overworld_side': ow,
                      'eligible_nether_sides': [n for n in NETHER if cid in memberships[key(ow, n)]],
                      'elapsed_seconds': seconds, 'summary': run_summary, 'variants': variants,
                      'stage_observations': stages, 'completed_tasks': tasks,
                      'strict_pass': {v: any(r['variant'] == v and strict_pass(r['result']) for r in variants) for v in ('v1', 'v2')},
                      'any_finest_complete_within': any(r['result'].get('sampling_schedule', {}).get('last_height_resolution') == 4 and r['result'].get('border_fit', {}).get('state') == 'within' and r['result'].get('border_fit', {}).get('complete') is True for r in variants)}
            save(measurement, result)
            rows.append(result)
            save(root / 'terrain-progress.json', rows)
            print(json.dumps({'terrain_completed': len(rows), 'total': 42, 'overworld_side': ow,
                              'group': group, 'seconds': seconds, 'strict_pass': result['strict_pass']}), flush=True)
    save(root / 'terrain.json', rows)
    check_sources(root, production)
    return rows


def summarize(root, production, base, terrain_rows):
    rows = []
    for item in base['summary']:
        ow, n = item['overworld_side'], item['nether_side']
        evaluated = [t for t in terrain_rows if t['overworld_side'] == ow and n in t['eligible_nether_sides']]
        groups = {}
        for group in ('common_control', 'random_eligible'):
            picked = [t for t in evaluated if t['sample_group'] == group]
            groups[group] = {'evaluated_anchors': len(picked),
                             'strict_v1_passes': sum(t['strict_pass']['v1'] for t in picked),
                             'strict_v2_passes': sum(t['strict_pass']['v2'] for t in picked),
                             'strict_either_passes': sum(any(t['strict_pass'].values()) for t in picked),
                             'finest_complete_within': sum(t['any_finest_complete_within'] for t in picked)}
        rows.append({**item, 'terrain_sample': groups})
    result = {'plan': json.loads((root / 'plan.json').read_text()), 'summary': rows,
              'baseline': {k: v for k, v in base.items() if k not in ('trials', 'memberships', 'summary')},
              'terrain_evaluations': len(terrain_rows),
              'terrain_seconds': sum(t['elapsed_seconds'] for t in terrain_rows),
              'terrain_by_overworld': {str(ow): {
                  'median_seconds_per_anchor': statistics.median(t['elapsed_seconds'] for t in terrain_rows if t['overworld_side'] == ow),
                  'stage_observations': {name: {metric: sum(t['stage_observations'].get(name, {}).get(metric, 0) for t in terrain_rows if t['overworld_side'] == ow) for metric in ('evaluated_center_observations', 'geometry_pass', 'complete_within', 'geometry_and_complete_within', 'strict_finest_pass')} for name in sorted({name for t in terrain_rows if t['overworld_side'] == ow for name in t['stage_observations']})},
                  'pending_work': sum(t['summary']['pending_work'] for t in terrain_rows if t['overworld_side'] == ow),
                  'deferred_work': sum(t['summary']['deferred_work'] for t in terrain_rows if t['overworld_side'] == ow)} for ow in OW},
              'strict_pass_definition': 'PREDICTED, geometry_pass, complete footprint within exact border, last height resolution 4',
              'stage_timing_scope': 'Sum of elapsed native/Python stage call seconds across workers, not wall time or whole-run CPU attribution.',
              'source_files_unchanged': check_sources(root, production),
              'actual_generation_verified': False,
              'limitations': ['Short matched baseline timing includes startup/IPC/persistence, not sustained sweep speed.',
                  'Missing predictions remain pending, not actual-world absence.',
                  'Six independent seeds per OW, two common controls plus four separately selected eligible seeds; no population terrain-rate estimate.',
                  'Eight nominated centers per variant; deferred fine/halo tasks and other centers remain unresolved.',
                  'Nether variants reuse geometry only at their own baseline-eligible anchors; no Nether access/footprint certification.',
                  'Native MC_26_50 predictions, not actual Bedrock 26.52 certification.']}
    save(root / 'report.json', result)
    print(json.dumps({'finished': True, 'terrain_evaluations': len(terrain_rows),
                      'strict_passes': sum(any(t['strict_pass'].values()) for t in terrain_rows)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--stage', choices=['baseline', 'terrain', 'all'], default='all')
    args = parser.parse_args()
    root = Path(args.output).resolve()
    root.mkdir(parents=True, exist_ok=True)
    production = load(str(ROOT / 'config/realm.yaml'))
    plan = {'overworld_sides': OW, 'nether_sides': NETHER, 'discovery_side': 4000,
            'distinct_full64_inputs_per_arm': 1000, 'trials_per_arm': 2,
            'baseline_processes': 30, 'native_threads_per_baseline_worker': 1,
            'terrain_threads': production['terrain']['native_threads'],
            'terrain_independent_seeds_per_overworld': 6,
            'terrain_centers_per_variant': production['terrain']['maximum_refinements_per_anchor'],
            'terrain_resolutions': production['terrain']['resolutions'],
            'scope': 'Finite diagnostics only; unchanged terrain/biome/structure thresholds; no production sweep or BDS.'}
    save(root / 'plan.json', plan)
    if not (root / 'source-identity.json').exists():
        seal = json.loads((ROOT / 'runs/master-implementation-2026-10-10/readiness.json').read_text())
        before = {'production_identity': make_identity(production, 1000, 0),
                  'production_config_sha256': sha(ROOT / 'config/realm.yaml'),
                  'source_sha256': {relative: sha(ROOT / relative) for relative in seal['source_sha256']}}
        save(root / 'source-identity.json', before)
    check_sources(root, production)
    base = baseline(root, production)
    if args.stage != 'baseline':
        measurements = terrain(root, production, base)
        summarize(root, production, base, measurements)


if __name__ == '__main__':
    main()
