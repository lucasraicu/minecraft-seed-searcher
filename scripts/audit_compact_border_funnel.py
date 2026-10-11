"""Independent read-only audit of the finite compact-border pilots."""
import collections
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from fractions import Fraction

from seed_search.seeds import seed_from_index

ROOT = Path(__file__).resolve().parents[1]


def read_db(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)


def inside(point, bounds):
    return bounds[0] <= point[0] < bounds[2] and bounds[1] <= point[1] < bounds[3]


def audit(root):
    plan = json.loads((root / 'plan.json').read_text())
    report = json.loads((root / 'report.json').read_text())
    base = json.loads((root / 'baseline.json').read_text())
    identities = json.loads((root / 'source-identity.json').read_text())
    for relative, expected in identities['source_sha256'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    selection = json.loads((root / 'selection.json').read_text())
    measurements = json.loads((root / 'terrain.json').read_text())
    all_members, structure_members, coverage_hashes, candidate_checks = {}, {}, set(), 0
    range_checks = 0
    stage_names = ['discovered_stronghold', 'initial_fortress', 'final_fortress', 'final_bastion',
                   'ancient_city', 'village', 'trial_chamber', 'mineshaft', 'wooded_families']
    for trial in range(2):
        for ow in plan['overworld_sides']:
            for nether in plan['nether_sides']:
                label = f'ow-{ow}-nether-{nether}'
                folder = root / 'baseline' / f'trial-{trial}-{label}'
                measurement = json.loads((folder / 'measurement.json').read_text())
                cfg = json.loads((folder / 'config.json').read_text())
                control = dict(cfg)
                control['deployment'] = identities['production_identity']['config']['deployment']
                control['discovery'] = identities['production_identity']['config']['discovery']
                assert control == identities['production_identity']['config']
                db = read_db(folder / 'workers-30/realm.sqlite')
                counts = collections.Counter()
                stage_seeds = {name: set() for name in stage_names}
                live_ids = set()
                structure_ids = set()
                try:
                    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                    digest = hashlib.sha256()
                    sequence = list(db.execute('SELECT idx,seed FROM seeds ORDER BY idx'))
                    assert len(sequence) == 1000
                    for index, (idx, seed) in enumerate(sequence):
                        assert int(idx) == index and seed == str(seed_from_index(index))
                        digest.update(f'{idx}:{seed}\n'.encode())
                    coverage_hashes.add(digest.hexdigest())
                    cursor = 0
                    for start, end, status in db.execute('SELECT start,end,status FROM ranges ORDER BY start'):
                        assert int(start) == cursor and status == 'complete'
                        cursor = int(end)
                        range_checks += 1
                    assert cursor == 1000
                    for cid, qualification, encoded in db.execute('SELECT id,qualification,result FROM candidates'):
                        c = json.loads(encoded)
                        sx, sz = c['stronghold']
                        assert -2000 <= sx < 2000 and -2000 <= sz < 2000
                        expected_ow = [sx-ow//2, sz-ow//2, sx+ow//2, sz+ow//2]
                        exact_nether = [Fraction(sx, 8)-nether//2, Fraction(sz, 8)-nether//2,
                                        Fraction(sx, 8)+nether//2, Fraction(sz, 8)+nether//2]
                        assert c['bounds']['overworld'] == expected_ow
                        assert c['bounds']['final_nether'] == exact_nether
                        assert c['bounds']['initial_overworld'] == [-2000, -2000, 2000, 2000]
                        observations = [c['initial_fortress'], c['required_nether_structures']['fortress'],
                                        c['required_nether_structures']['bastion']]
                        flags = [True] + [bool(o['predicted_viable']) for o in observations]
                        for name in ('ancient_city', 'village', 'trial_chamber', 'mineshaft'):
                            observation = c['required_structures'][name]
                            flags.append(bool(observation['predicted_viable']))
                            assert all(inside(p, expected_ow) for p in observation['predicted_viable'])
                        for name in ('fortress', 'bastion'):
                            assert all(inside(p, exact_nether) for p in c['required_nether_structures'][name]['predicted_viable'])
                        flags.append(bool(c['biomes'] and c['biomes']['qualification'] != 'PENDING'))
                        if all(flags[:-1]):
                            structure_ids.add(cid)
                        live = True
                        for name, flag in zip(stage_names, flags):
                            live = live and flag
                            if live:
                                counts[name] += 1
                                stage_seeds[name].add(c['seed'])
                        assert live == (qualification == 'PREDICTED')
                        assert qualification in ('PREDICTED', 'PENDING')
                        if live:
                            live_ids.add(cid)
                        candidate_checks += 1
                    for stage in measurement['stages']:
                        name = stage['stage']
                        assert counts[name] == stage['surviving_anchors']
                        assert len(stage_seeds[name]) == stage['surviving_seeds']
                finally:
                    db.close()
                assert live_ids == set(base['memberships'][label])
                if label in all_members:
                    assert all_members[label] == live_ids
                all_members[label] = live_ids
                if label in structure_members:
                    assert structure_members[label] == structure_ids
                structure_members[label] = structure_ids
    assert coverage_hashes == {base['input_sequence_sha256']}
    for ow in plan['overworld_sides']:
        for nether in plan['nether_sides']:
            for bigger_ow in plan['overworld_sides']:
                for bigger_nether in plan['nether_sides']:
                    if ow <= bigger_ow and nether <= bigger_nether:
                        smaller = f'ow-{ow}-nether-{nether}'
                        larger = f'ow-{bigger_ow}-nether-{bigger_nether}'
                        assert structure_members[smaller] <= structure_members[larger]
                        missing = all_members[smaller]-all_members[larger]
                        expected = {e['candidate_id'] for e in base['full_baseline_nesting_exceptions']
                                    if e['smaller_pair'] == smaller and e['larger_pair'] == larger}
                        assert missing == expected
    assert len(measurements) == 42
    def select_unique(pool, count, exclusions=()):
        chosen, seen = [], {cid.rsplit(':', 2)[0] for cid in exclusions}
        for cid in sorted(pool, key=lambda value: (hashlib.sha256((selection['sample_key']+value).encode()).hexdigest(), value)):
            seed = cid.rsplit(':', 2)[0]
            if seed in seen:
                continue
            seen.add(seed)
            chosen.append(cid)
            if len(chosen) == count:
                return chosen
        raise AssertionError('Sample pool too small')
    assert selection['common_controls'] == select_unique(all_members['ow-1024-nether-512'], 2)
    for ow in plan['overworld_sides']:
        expected = select_unique(all_members[f'ow-{ow}-nether-1024']-set(selection['common_controls']),
                                 4, selection['common_controls'])
        assert selection['random_eligible_per_overworld'][str(ow)] == expected
    finest_observations = collections.Counter()
    strict_counts = collections.Counter()
    for item in measurements:
        ow, cid = item['overworld_side'], item['candidate_id']
        assert cid in all_members[f'ow-{ow}-nether-1024']
        expected_nether = [n for n in plan['nether_sides'] if cid in all_members[f'ow-{ow}-nether-{n}']]
        assert item['eligible_nether_sides'] == expected_nether
        if item['sample_group'] == 'common_control':
            position = selection['common_controls'].index(cid)
        else:
            position = selection['random_eligible_per_overworld'][str(ow)].index(cid)+2
        folder = root / 'terrain' / f'ow-{ow}-sample-{position}'
        cfg = json.loads((folder / 'config.json').read_text())
        assert cfg['terrain']['maximum_refinements_per_anchor'] == 8
        db = read_db(folder / 'realm.sqlite')
        try:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            observations = collections.Counter()
            selected_centers = {'v1': set(), 'v2': set()}
            for variant, payload, encoded in db.execute('SELECT variant,payload,result FROM terrain_work WHERE result IS NOT NULL'):
                task = json.loads(payload)
                result = json.loads(encoded)['result']
                entries = result.get('proposals', []) if task['stage'] == 'nomination' else result.get('evaluated_centers', [])
                name = f"{variant}:resolution-{task['resolution']}"
                observations[name] += len(entries)
                if task['stage'] != 'nomination':
                    selected_centers[variant].add(tuple(task['coarse_center']))
                if task['resolution'] == 4:
                    finest_observations[str(ow)] += len(entries)
            assert all(len(centers) <= 8 for centers in selected_centers.values())
            for name, count in observations.items():
                assert item['stage_observations'][name]['evaluated_center_observations'] == count
            passes = {}
            for variant in ('v1', 'v2'):
                passes[variant] = False
                for encoded, in db.execute('SELECT result FROM variants WHERE variant=?', (variant,)):
                    r = json.loads(encoded)['result']
                    fit = r['border_fit']
                    passed = (r['qualification'] == 'PREDICTED' and r['geometry_pass'] and
                              fit['complete'] and fit['state'] == 'within' and
                              r.get('sampling_schedule', {}).get('last_height_resolution') == 4)
                    passes[variant] |= passed
                assert passes[variant] == item['strict_pass'][variant]
            strict_counts[str(ow)] += int(any(passes.values()))
        finally:
            db.close()
    # Public evaluator controls replay saved seeds without reading their predictions.
    from seed_search.realm.baseline import evaluate_seed
    replay_count = 0
    for ow, nether in ((1024, 512), (1280, 768), (1280, 896), (1536, 896), (2380, 1024)):
        folder = root / 'baseline' / f'trial-0-ow-{ow}-nether-{nether}'
        cfg = json.loads((folder / 'config.json').read_text())
        db = read_db(folder / 'workers-30/realm.sqlite')
        try:
            for idx in (0, 37, 999):
                result = evaluate_seed(idx, seed_from_index(idx), cfg)
                saved = {cid: json.loads(payload) for cid, payload in db.execute('SELECT id,result FROM candidates WHERE idx=?', (f'{idx:020d}',))}
                for c in result['anchors']:
                    assert c == saved[c['id']]
                assert set(saved) == {c['id'] for c in result['anchors']}
                replay_count += 1
        finally:
            db.close()
    # Replay previously observed in-border wooded-family coordinates for the
    # nonaligned 2380 lattice. This diagnoses coverage without changing a run.
    import numpy as np
    from seed_search.backend import Backend
    from seed_search.realm.biomes import postprocess_ids
    biome_controls = []
    for exception in base['full_baseline_nesting_exceptions']:
        observations = {}
        for name in ('smaller_pair', 'larger_pair'):
            db = read_db(root / 'baseline' / f"trial-0-{exception[name]}" / 'workers-30/realm.sqlite')
            try:
                observations[name] = json.loads(db.execute('SELECT result FROM candidates WHERE id=?', (exception['candidate_id'],)).fetchone()[0])
            finally:
                db.close()
        smaller = observations['smaller_pair']
        larger = observations['larger_pair']
        points = np.array([v['coordinate'] for v in smaller['biomes']['raw_detections'].values()], dtype=np.int32)
        assert all(inside((int(p[0]), int(p[2])), larger['bounds']['overworld']) for p in points)
        with Backend(int(smaller['seed'])) as backend:
            ids = backend.biome_points(points)
        policy = json.loads((root / 'baseline' / f"trial-0-{exception['larger_pair']}" / 'config.json').read_text())['biomes']
        replay = postprocess_ids(ids, points, policy)
        assert replay['qualification'] == 'PREDICTED'
        assert replay['wooded_families'] == smaller['biomes']['wooded_families']
        biome_controls.append({'candidate_id': smaller['id'],
            'smaller_sampled_wooded_families': smaller['biomes']['wooded_families'],
            'larger_sampled_wooded_families': larger['biomes']['wooded_families'],
            'replayed_in_larger_border_wooded_families': replay['wooded_families'],
            'replayed_sample_coordinates': points.tolist(),
            'production_memberships_unchanged': True, 'actual_generation_verified': False})
    (root / 'biome-lattice-replay.json').write_text(json.dumps(biome_controls, indent=2)+'\n')
    output = {'passed': True, 'distinct_signed_full64_inputs': 1000,
              'baseline_trials_audited': 70, 'candidate_bound_and_filter_checks': candidate_checks,
              'contiguous_completed_ranges_audited': range_checks,
              'unaltered_eligibility_and_geometry_thresholds': True,
              'deterministic_terrain_sample_selection': True,
              'terrain_databases_audited': 42, 'eight_center_budget_verified': True,
              'finest_resolution_center_observations': dict(finest_observations),
              'strict_pass_anchors_by_overworld': dict(strict_counts),
              'public_evaluator_replayed_seeds': replay_count,
              'matched_seed_sequence': True, 'repeated_memberships': True,
              'required_structure_memberships_nested': True,
              'full_baseline_nesting_exceptions': base['full_baseline_nesting_exceptions'],
              'biome_lattice_coordinate_replays': len(biome_controls),
              'exact_fractional_nether_bounds': True, 'stage_funnels_recomputed': True,
              'production_source_files_unchanged': len(identities['source_sha256']),
              'actual_generation_verified': False,
              'artifact_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                  (root/'report.json', root/'baseline.json', root/'selection.json', root/'terrain.json')},
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (root / 'independent-audit.json').write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    audit(Path(sys.argv[1]).resolve())
