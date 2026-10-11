"""Bounded, matched border diagnostics; never change the production profile.

Baseline: the same 1,000 full64 inputs, three rotated trials for each border pair.
Terrain: hash-selected union anchors plus separate common matched controls, real
durable nomination/refinement, two centers per variant, resolutions through four.
Nether changes baseline eligibility, not Overworld geometry: reuse geometry only
for pairs whose own baseline qualified the anchor. No BDS or production sweep.
"""
import argparse
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
SAMPLE_KEY = 'joint-borders-2026-10-10-union-v1:'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def read_db(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)


def key(ow, nether):
    return f'ow-{ow}-nether-{nether}'


def config(production, ow, nether, terrain=False):
    cfg = copy.deepcopy(production)
    cfg['discovery'] = {'overworld_bounds': [-2000, -2000, 2000, 2000],
                        'nether_bounds': [-2000, -2000, 2000, 2000]}
    cfg['deployment']['overworld_side_blocks'] = ow
    cfg['deployment']['nether_side_blocks'] = nether
    if terrain:
        cfg['terrain']['maximum_refinements_per_anchor'] = 2
    unchanged = copy.deepcopy(cfg)
    unchanged['discovery'] = copy.deepcopy(production['discovery'])
    unchanged['deployment'] = copy.deepcopy(production['deployment'])
    unchanged['terrain'] = copy.deepcopy(production['terrain'])
    assert unchanged == production
    return cfg


def assert_unchanged(root, production):
    identity = json.loads((root / 'production-identity.json').read_text())
    assert make_identity(production, 1000, 0) == identity
    seal = json.loads((ROOT / 'runs/master-implementation-2026-10-10/readiness.json').read_text())
    for relative, expected in seal['source_sha256'].items():
        assert sha(ROOT / relative) == expected, f'Sealed source changed: {relative}'
    return len(seal['source_sha256'])


def baseline(root, plan, production):
    target = root / 'baseline.json'
    if target.exists():
        return json.loads(target.read_text())
    assert not (root / 'baseline-progress.json').exists(), 'Preserve interrupted trials; use a fresh run'
    save(root / 'production-identity.json', make_identity(production, 1000, 0))
    pairs = [(ow, n) for ow in plan['overworld_sides'] for n in plan['nether_sides']]
    rows, members, all_ids, inputs = [], {}, None, set()
    for trial in range(3):
        # Rotate and reverse the matrix to distribute run-order effects.
        order = pairs[trial * 4:] + pairs[:trial * 4]
        if trial == 1:
            order = list(reversed(order))
        for ow, nether in order:
            label = key(ow, nether)
            cfg = config(production, ow, nether)
            folder = root / 'baseline' / f'trial-{trial}-{label}'
            folder.mkdir(parents=True)
            save(folder / 'config.json', cfg)
            run_benchmark(cfg, folder, 1000, [30])
            row = json.loads((folder / 'benchmark.json').read_text())['rows'][0]
            db = read_db(folder / 'workers-30/realm.sqlite')
            try:
                digest = hashlib.sha256()
                sequence = list(db.execute('SELECT idx,seed FROM seeds ORDER BY idx'))
                assert len(sequence) == 1000 and len({r[1] for r in sequence}) == 1000
                assert [int(r[0]) for r in sequence] == list(range(1000))
                for index, seed in sequence:
                    digest.update(f'{index}:{seed}\n'.encode())
                discovered = {r[0] for r in db.execute('SELECT id FROM candidates')}
                qualified = {r[0] for r in db.execute("SELECT id FROM candidates WHERE qualification='PREDICTED'")}
                assert db.execute('SELECT count(*) FROM variants').fetchone()[0] == 0
                assert not db.execute("SELECT 1 FROM candidates WHERE qualification='VERIFIED' LIMIT 1").fetchone()
            finally:
                db.close()
            inputs.add(digest.hexdigest())
            if all_ids is None:
                all_ids = discovered
            assert all_ids == discovered, 'Fixed discovery produced different anchors'
            if label in members:
                assert members[label] == qualified, 'Repeated eligibility changed'
            members[label] = qualified
            rows.append({**row, 'trial': trial, 'overworld_side_blocks': ow,
                         'nether_side_blocks': nether, 'input_sequence_sha256': digest.hexdigest(),
                         'predicted_qualifying_anchors': len(qualified),
                         'predicted_qualifying_seeds': len({cid.rsplit(':', 2)[0] for cid in qualified})})
            save(root / 'baseline-progress.json', rows)
    assert len(inputs) == 1
    for ow, n in pairs:
        for larger_ow, larger_n in pairs:
            if ow <= larger_ow and n <= larger_n:
                assert members[key(ow, n)] <= members[key(larger_ow, larger_n)], 'Nested eligibility failed'
    # Match the previously measured discovery cohort, not just repeated new trials.
    db = read_db(ROOT / 'runs/discovery-size-comparison-2026-10-10/trial-0-side-4000/workers-30/realm.sqlite')
    try:
        prior = hashlib.sha256()
        for idx, seed in db.execute('SELECT idx,seed FROM seeds WHERE idx<? ORDER BY idx', (f'{1000:020d}',)):
            prior.update(f'{idx}:{seed}\n'.encode())
        assert prior.hexdigest() == next(iter(inputs))
        old = {r[0] for r in db.execute("SELECT id FROM candidates WHERE idx<? AND qualification='PREDICTED'", (f'{1000:020d}',))}
        assert old == members[key(2688, 1024)]
    finally:
        db.close()
    source_count = assert_unchanged(root, production)
    summary = []
    for ow, n in pairs:
        selected = [r for r in rows if r['overworld_side_blocks'] == ow and r['nether_side_blocks'] == n]
        rates = [r['seeds_per_second'] for r in selected]
        ids = members[key(ow, n)]
        median = statistics.median(rates)
        summary.append({'pair': key(ow, n), 'overworld_side_blocks': ow, 'nether_side_blocks': n,
                        'median_seeds_per_second': median, 'range_seeds_per_second': [min(rates), max(rates)],
                        'predicted_qualifying_anchors': len(ids),
                        'predicted_qualifying_seeds': len({cid.rsplit(':', 2)[0] for cid in ids}),
                        'predicted_qualifying_anchors_per_second': len(ids) / 1000 * median})
    result = {'summary': summary, 'trials': rows, 'memberships': {k: sorted(v) for k, v in members.items()},
              'input_sequence_sha256': next(iter(inputs)), 'distinct_full64_inputs': 1000,
              'total_evaluations': 36000, 'discovered_anchors': len(all_ids), 'repeated_memberships_equal': True,
              'nested_memberships': True, 'matches_prior_discovery_cohort': True,
              'sealed_sources_unchanged': source_count, 'production_unchanged': True,
              'timing_scope': 'Includes process startup, baseline, IPC and durable checkpoint; fresh 1,000-input runs, not sustained sweep throughput.'}
    save(target, result)
    return result


def strict_pass(result):
    fit = result.get('border_fit', {})
    return (result.get('geometry_pass') is True and result.get('qualification') == 'PREDICTED'
            and fit.get('state') == 'within' and fit.get('complete') is True
            and result.get('sampling_schedule', {}).get('last_height_resolution') == 4)


def terrain(root, plan, production, base):
    # Keep scipy/numpy terrain imports out of spawned baseline worker startup.
    from seed_search.realm.terrain import run_terrain
    memberships = {k: set(v) for k, v in base['memberships'].items()}
    union = set.union(*memberships.values())
    common = set.intersection(*memberships.values())
    ranked = lambda ids: sorted(ids, key=lambda cid: (hashlib.sha256((SAMPLE_KEY + cid).encode()).hexdigest(), cid))
    random_ids = ranked(union)[:plan['terrain_random_union_sample_target']]
    common_ids = ranked(common - set(random_ids))[:plan['terrain_common_control_target']]
    assert len(random_ids) == 12 and len(common_ids) == 4
    selection = {'sample_key': SAMPLE_KEY, 'union_anchors': len(union), 'intersection_anchors': len(common),
                 'random_union_sample': random_ids, 'additional_common_controls': common_ids,
                 'membership': {cid: [k for k, ids in memberships.items() if cid in ids] for cid in random_ids + common_ids},
                 'scope': 'Uniform hash selection over anchors, not independent seeds; common controls are reported separately.'}
    selected_path = root / 'selection.json'
    if selected_path.exists():
        assert json.loads(selected_path.read_text()) == selection
    else:
        save(selected_path, selection)
    measurements = []
    for position, cid in enumerate(random_ids + common_ids):
        # Rotate border order for each anchor; no concurrent baseline/terrain timing.
        sides = list(plan['overworld_sides'])
        rotate = position % len(sides)
        sides = sides[rotate:] + sides[:rotate]
        for ow in sides:
            if cid not in memberships[key(ow, 1280)]:
                continue
            folder = root / 'terrain' / f'anchor-{position:02d}-ow-{ow}'
            result_path = folder / 'measurement.json'
            if result_path.exists():
                measurements.append(json.loads(result_path.read_text()))
                continue
            assert not folder.exists(), 'Retain interrupted terrain checkpoint; do not silently restart'
            folder.mkdir(parents=True)
            source = root / 'baseline' / f'trial-0-{key(ow, 1280)}' / 'workers-30/realm.sqlite'
            db = read_db(source)
            try:
                idx, seed, payload = db.execute('SELECT idx,seed,result FROM candidates WHERE id=?', (cid,)).fetchone()
                candidate = json.loads(payload)
            finally:
                db.close()
            assert candidate['qualification'] == 'PREDICTED'
            assert candidate['index'] == int(idx)
            assert candidate['bounds']['overworld'][2] - candidate['bounds']['overworld'][0] == ow
            cfg = config(production, ow, 1280, terrain=True)
            save(folder / 'config.json', cfg)
            save(folder / 'imported-candidate.json', candidate)
            identity = {**make_identity(cfg, 1, int(idx)), 'diagnostic_import': {
                'source': str(source.relative_to(ROOT)), 'candidate_id': cid,
                'candidate_sha256': hashlib.sha256(canonical(candidate).encode()).hexdigest()}}
            with RealmStore(folder, identity=identity) as store:
                store.configure_range(int(idx), int(idx) + 1, 1)
                assert store.claim_range('diagnostic-import') == (int(idx), int(idx) + 1)
                store.complete_range(int(idx), int(idx) + 1,
                                     [{'index': int(idx), 'seed': seed, 'anchors': [candidate]}])
                started = time.perf_counter()
                run_summary = run_terrain(store, cfg)
                seconds = time.perf_counter() - started
                variants = list(store.iter_variants())
                assert store.db.execute('SELECT count(*) FROM candidates').fetchone()[0] == 1
                assert all(v['result']['evidence'] in {'PREDICTED', 'PARTIAL'} for v in variants)
                assert all(v['result']['qualification'] in {'PREDICTED', 'PREDICTED_NEAR_MATCH', 'PENDING'} for v in variants)
            result = {'candidate_id': cid, 'sample_group': 'random_union' if cid in random_ids else 'common_control',
                      'overworld_side_blocks': ow, 'source_baseline_nether_side_blocks': 1280,
                      'eligible_pairs': selection['membership'][cid], 'elapsed_seconds': seconds,
                      'summary': run_summary, 'variants': variants,
                      'strict_pass': {v: any(r['variant'] == v and strict_pass(r['result']) for r in variants) for v in ('v1', 'v2')},
                      'any_finest_complete_within': any(r['result'].get('sampling_schedule', {}).get('last_height_resolution') == 4
                           and r['result'].get('border_fit', {}).get('state') == 'within'
                           and r['result'].get('border_fit', {}).get('complete') is True for r in variants)}
            save(result_path, result)
            measurements.append(result)
            save(root / 'terrain-progress.json', measurements)
            print(json.dumps({'terrain_step': len(measurements), 'anchor_position': position,
                              'ow': ow, 'seconds': seconds, 'passes': result['strict_pass']}), flush=True)
    return selection, measurements


def summarize(root, plan, base, selection, measurements, production):
    rows = []
    for row in base['summary']:
        label, ow = row['pair'], row['overworld_side_blocks']
        groups = {}
        for group, ids in [('random_union', selection['random_union_sample']), ('common_control', selection['additional_common_controls'])]:
            eligible = [cid for cid in ids if label in selection['membership'][cid]]
            measured = [m for m in measurements if m['sample_group'] == group and m['overworld_side_blocks'] == ow
                        and m['candidate_id'] in eligible]
            assert {m['candidate_id'] for m in measured} == set(eligible)
            durations = [m['elapsed_seconds'] for m in measured]
            groups[group] = {'sample_denominator': len(ids), 'baseline_eligible_anchors': len(eligible),
                'terrain_evaluated_anchors': len(measured),
                'strict_v1_pass_anchors': sum(m['strict_pass']['v1'] for m in measured),
                'strict_v2_pass_anchors': sum(m['strict_pass']['v2'] for m in measured),
                'strict_either_pass_anchors': sum(any(m['strict_pass'].values()) for m in measured),
                'finest_complete_within_anchors': sum(m['any_finest_complete_within'] for m in measured),
                'median_terrain_seconds_per_eligible_anchor': statistics.median(durations) if durations else None,
                'mean_terrain_seconds_per_eligible_anchor': statistics.mean(durations) if durations else None,
                'total_pending_work': sum(m['summary']['pending_work'] for m in measured),
                'total_deferred_work': sum(m['summary']['deferred_work'] for m in measured)}
        rows.append({**row, 'terrain_samples': groups})
    verified = assert_unchanged(root, production)
    result = {'plan': plan, 'summary': rows, 'selection': selection,
              'baseline_total_evaluations': base['total_evaluations'], 'distinct_baseline_full64_inputs': 1000,
              'terrain_anchor_border_evaluations': len(measurements),
              'terrain_seconds': sum(m['elapsed_seconds'] for m in measurements),
              'script_sha256': sha(Path(__file__)), 'sealed_sources_unchanged': verified,
              'production_config_unchanged': True, 'actual_generation_verified': False,
              'geometry_reuse': 'Same seed, Stronghold and Overworld border; Nether eligibility taken from each pair independently. Overall score includes source-arm baseline bonuses and is not compared across Nether arms.',
              'pass_definition': 'PREDICTED + geometry_pass + complete footprint within border + finest height resolution 4.',
              'limitations': ['12 hash-selected union anchors; 4 additional common controls reported separately.',
                  'Two centers per variant instead of production eight; thousands of pending centers retained.',
                  'A nonpass means no qualifying terrain found within this budget, not no suitable terrain exists.',
                  'Native density/biome prediction only; no authoritative Bedrock/BDS or actual liquid/ground validation.',
                  'Short baseline trials include startup; speed is not a sustained billion-seed forecast.']}
    save(root / 'report.json', result)
    save(root / 'verification.json', {'passed': True, 'input_sequence_sha256': base['input_sequence_sha256'],
        'repeated_baseline_memberships_equal': True, 'nested_baseline_memberships': True,
        'matches_prior_discovery_cohort': True, 'all_eligible_sample_border_pairs_evaluated': True,
        'production_identity_unchanged': True, 'sealed_source_hashes_unchanged': verified,
        'script_sha256': result['script_sha256'], 'no_bds_or_actual_evidence': True})
    print(json.dumps({'complete': True, 'evaluations': len(measurements), 'terrain_seconds': result['terrain_seconds'],
                      'summary': rows}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--stage', choices=['baseline', 'terrain', 'all'], default='all')
    args = parser.parse_args()
    root = Path(args.output).resolve()
    plan = json.loads((root / 'plan.json').read_text())
    production = load(str(ROOT / 'config/realm.yaml'))
    base = baseline(root, plan, production)
    if args.stage != 'baseline':
        selection, measurements = terrain(root, plan, production, base)
        summarize(root, plan, base, selection, measurements, production)
