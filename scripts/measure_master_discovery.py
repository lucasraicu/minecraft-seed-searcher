"""Matched discovery-size diagnostics with fixed final Realm borders.

Copy the validated production profile and change only its initial Overworld and
Nether discovery squares. The fixed-profile public validator intentionally does
not accept these hypothetical sizes; production configuration is never edited.
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

ROOT = Path(__file__).resolve().parents[1]
ORDERS = ((5000, 4000, 3000), (3000, 5000, 4000), (4000, 3000, 5000))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def center(candidate_id):
    _, x, z = candidate_id.rsplit(':', 2)
    return int(x), int(z)


def in_discovery(candidate_id, side):
    x, z = center(candidate_id)
    half = side // 2
    return -half <= x < half and -half <= z < half


def measure(output, count):
    if not 1000 <= count <= 10000:
        raise ValueError('Use 1,000–10,000 inputs per diagnostic trial')
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    production_path = ROOT / 'config/realm.yaml'
    production_hash = sha256(production_path)
    production = load(str(production_path))
    production_identity = make_identity(production, count, 0)
    (root / 'production-identity.json').write_text(json.dumps(production_identity, indent=2) + '\n')
    rows, memberships, inputs = [], {}, set()
    for trial, sides in enumerate(ORDERS):
        for side in sides:
            cfg = copy.deepcopy(production)
            half = side // 2
            bounds = [-half, -half, half, half]
            cfg['discovery'] = {'overworld_bounds': bounds.copy(), 'nether_bounds': bounds.copy()}
            unchanged = copy.deepcopy(cfg)
            unchanged['discovery'] = copy.deepcopy(production['discovery'])
            assert unchanged == production
            folder = root / f'trial-{trial}-side-{side}'
            folder.mkdir()
            (folder / 'config.json').write_text(json.dumps(cfg, indent=2) + '\n')
            run_benchmark(cfg, folder, count, [30])
            row = json.loads((folder / 'benchmark.json').read_text())['rows'][0]
            db_path = folder / 'workers-30/realm.sqlite'
            with sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True) as db:
                digest = hashlib.sha256()
                for index, seed in db.execute('SELECT idx,seed FROM seeds ORDER BY idx'):
                    digest.update(f'{index}:{seed}\n'.encode())
                assert db.execute('SELECT count(DISTINCT seed) FROM seeds').fetchone()[0] == count
                assert db.execute('SELECT count(*) FROM variants').fetchone()[0] == 0
                assert not db.execute("SELECT 1 FROM candidates WHERE qualification='VERIFIED' LIMIT 1").fetchone()
                all_ids = set()
                qualified = set()
                for cid, qualification in db.execute('SELECT id,qualification FROM candidates'):
                    assert in_discovery(cid, side)
                    all_ids.add(cid)
                    if qualification == 'PREDICTED':
                        qualified.add(cid)
            inputs.add(digest.hexdigest())
            member = {'all': all_ids, 'qualified': qualified}
            if side in memberships:
                assert memberships[side] == member, 'Repeat trial membership changed'
            else:
                memberships[side] = member
            summary_row = {**row, 'trial': trial, 'discovery_side_blocks': side,
                           'input_sequence_sha256': digest.hexdigest(),
                           'predicted_qualifying_seeds': len({cid.rsplit(':', 2)[0] for cid in qualified})}
            rows.append(summary_row)
            (root / 'progress.json').write_text(json.dumps(rows, indent=2) + '\n')
    assert len(inputs) == 1
    assert sha256(production_path) == production_hash
    assert make_identity(production, count, 0) == production_identity
    reference = memberships[5000]
    summaries = []
    for side in (5000, 4000, 3000):
        member = memberships[side]
        expected_all = {cid for cid in reference['all'] if in_discovery(cid, side)}
        expected_qualified = {cid for cid in reference['qualified'] if in_discovery(cid, side)}
        assert member['all'] == expected_all, 'Retained-anchor discovery changed'
        assert member['qualified'] == expected_qualified, 'Retained-anchor qualification changed'
        selected = [r for r in rows if r['discovery_side_blocks'] == side]
        rates = [r['seeds_per_second'] for r in selected]
        median = statistics.median(rates)
        seeds = {cid.rsplit(':', 2)[0] for cid in member['qualified']}
        summaries.append({'discovery_side_blocks': side,
                          'median_seeds_per_second': median,
                          'range_seeds_per_second': [min(rates), max(rates)],
                          'discovered_anchors': len(member['all']),
                          'predicted_qualifying_anchors': len(member['qualified']),
                          'predicted_qualifying_seeds': len(seeds),
                          'predicted_qualifying_seeds_percent': len(seeds) / count * 100,
                          'predicted_qualifying_anchors_per_second': len(member['qualified']) / count * median,
                          'predicted_qualifying_seeds_per_second': len(seeds) / count * median,
                          'retained_reference_qualifying_anchors_percent': len(member['qualified']) / len(reference['qualified']) * 100,
                          'excluded_reference_qualifying_anchors': len(reference['qualified'] - member['qualified']),
                          'median_database_bytes': statistics.median(r['storage_bytes'] for r in selected)})
    result = {'schema': 1, 'recorded_at_unix': time.time(), 'count_per_trial': count,
              'distinct_full64_inputs': count, 'total_evaluations': count * len(rows),
              'workers': 30, 'native_threads_per_worker': 1,
              'resized_discovery_dimensions': ['overworld', 'nether'],
              'final_overworld_side_blocks': production['deployment']['overworld_side_blocks'],
              'final_nether_side_blocks': production['deployment']['nether_side_blocks'],
              'summary': summaries, 'trials': rows, 'input_sequence_sha256': inputs.pop(),
              'repeated_membership_equal': True, 'retained_anchor_membership_equal': True,
              'production_config_sha256': production_hash, 'production_config_unchanged': True,
              'production_backend_identity_unchanged': True, 'production_profile_changed': False,
              'actual_generation_verified': False,
              'script_sha256': sha256(Path(__file__)),
              'scope': 'Baseline-only prediction with startup/IPC/checkpoint. Both initial discovery squares resize; final borders and all required structures stay fixed. No terrain/BDS. Fresh small databases do not establish sustained million-input throughput or actual-game recall.'}
    (root / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('summary', 'count_per_trial', 'production_config_unchanged', 'scope')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--count', type=int, default=5000)
    args = parser.parse_args()
    measure(args.output, args.count)
