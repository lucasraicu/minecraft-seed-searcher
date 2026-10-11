"""Matched hypothetical Overworld-border trials; leave the Realm contract intact.

Run after the sole million-input benchmark. These diagnostic config copies bypass
the fixed-border public profile validator deliberately, never its production file.
All trials retain discovery bounds, required structures, Nether bounds and seeds.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import statistics
import time

from seed_search.realm.cli import load, run_benchmark
from seed_search.realm.store import RealmStore, canonical


def measure(output, count):
    if not 1000 <= count <= 10000:
        raise ValueError('Use a bounded 1,000–10,000 input comparison')
    root = Path(output)
    if root.exists():
        raise ValueError('Use a fresh comparison directory')
    root.mkdir(parents=True)
    production_path = Path('config/realm.yaml')
    production_hash = hashlib.sha256(production_path.read_bytes()).hexdigest()
    production = load(str(production_path))
    rows = []
    inputs = set()
    memberships = {}
    # Every size appears once in each position to reduce run-order effects.
    for trial, sizes in enumerate(((2688, 1500, 1200), (1200, 2688, 1500), (1500, 1200, 2688))):
        for side in sizes:
            cfg = copy.deepcopy(production)
            cfg['deployment']['overworld_side_blocks'] = side
            folder = root / f'trial-{trial}-side-{side}'
            run_benchmark(cfg, folder, count, [30])
            row = json.loads((folder / 'benchmark.json').read_text())['rows'][0]
            with RealmStore(folder / 'workers-30', resume=True) as store:
                digest = hashlib.sha256()
                for index, seed in store.db.execute('SELECT idx,seed FROM seeds ORDER BY idx'):
                    digest.update(f'{index}:{seed}\n'.encode())
                inputs.add(digest.hexdigest())
                qualified = {r[0] for r in store.db.execute("SELECT id FROM candidates WHERE qualification='PREDICTED'")}
                memberships.setdefault(side, []).append(qualified)
            rows.append({**row, 'trial': trial, 'overworld_side_blocks': side,
                         'input_sequence_sha256': digest.hexdigest(),
                         'config_sha256': hashlib.sha256(canonical(cfg).encode()).hexdigest()})
            (root / 'progress.json').write_text(json.dumps(rows, indent=2) + '\n')
    assert len(inputs) == 1
    assert hashlib.sha256(production_path.read_bytes()).hexdigest() == production_hash
    assert all(all(s == sets[0] for s in sets) for sets in memberships.values())
    summary = []
    for side in (2688, 1500, 1200):
        selected = [r for r in rows if r['overworld_side_blocks'] == side]
        rates = [r['seeds_per_second'] for r in selected]
        qualified = memberships[side][0]
        reference = memberships[2688][0]
        summary.append({'overworld_side_blocks': side,
                        'median_seeds_per_second': statistics.median(rates),
                        'range_seeds_per_second': [min(rates), max(rates)],
                        'predicted_anchors': len(qualified),
                        'predicted_anchors_per_input': len(qualified) / count,
                        'predicted_anchors_per_second': len(qualified) / count * statistics.median(rates),
                        'retained_reference_predicted_anchors': len(reference & qualified),
                        'reference_predicted_anchors_not_qualified': len(reference - qualified),
                        'newly_predicted_anchors': len(qualified - reference),
                        'median_database_bytes': statistics.median(r['storage_bytes'] for r in selected)})
    result = {'recorded_at_unix': time.time(), 'count_per_trial': count,
              'total_evaluations': count * len(rows), 'distinct_full64_inputs': count,
              'workers': 30, 'native_threads_per_worker': 1,
              'discovery': production['discovery'],
              'nether_side_blocks': production['deployment']['nether_side_blocks'],
              'production_config_sha256': production_hash,
              'production_config_unchanged': True, 'summary': summary, 'trials': rows,
              'actual_generation_verified': False, 'production_profile_changed': False,
              'scope': 'Hypothetical border sizes; baseline with startup/IPC/checkpoint, no terrain/BDS. A small fresh database does not establish sustained million-input speed. Candidate yield is predictor-only, not verified worlds.'}
    (root / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('summary', 'count_per_trial', 'production_config_unchanged', 'scope')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--count', type=int, default=5000)
    args = parser.parse_args()
    measure(args.output, args.count)
