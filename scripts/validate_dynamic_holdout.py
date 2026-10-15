"""Validate frozen builds on disjoint inputs using durable decision receipts.

Same batch boundaries permit comparison of every input decision without running
the kernel twice. Earlier tuning time counts toward the total 20-minute budget.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time

from seed_search.realm.capabilities import report
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.realm.native_batch import run_native_scan
from seed_search.realm.store import RealmStore, canonical


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior', type=Path, required=True)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Fresh output directory required')
    prior = json.loads(args.prior.read_text())
    prior_seconds = prior['cumulative_benchmark_seconds']
    selected = prior['selected']
    # seed_from_index permutes index + key: adjacent keys do NOT isolate cohorts.
    run_key = 2027101403
    assert run_key > 2026101403 + 500000
    args.output.mkdir(parents=True)
    started = time.perf_counter()
    result = {'status': 'running', 'prior': str(args.prior.resolve()),
              'prior_seconds': prior_seconds, 'run_key': str(run_key),
              'inputs_per_trial': 100000, 'budget_seconds': 1200,
              'selected': selected, 'durable_pairs': []}

    def save():
        result['cumulative_benchmark_seconds'] = prior_seconds + time.perf_counter() - started
        (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')

    for trial in range(5):
        expected = None
        for arm in (('control', 'selected') if trial % 2 == 0 else ('selected', 'control')):
            if prior_seconds + time.perf_counter() - started >= 1200:
                result['status'] = 'budget_exhausted'
                save()
                raise RuntimeError('Cumulative benchmark budget exhausted')
            policy = dynamic_blueprint_config()
            policy['search']['run_key'] = str(run_key)
            run = args.output / f'pair-{trial}-{arm}'
            before = time.perf_counter()
            run.mkdir()
            (run / 'compatibility.json').write_text(json.dumps(report(policy), indent=2) + '\n')
            status = run_native_scan(policy, run, 100000, start_index=trial * 100000,
                native_build=args.control if arm == 'control' else Path(selected['path']),
                native_threads=16 if arm == 'control' else selected['threads'],
                native_batch_size=16384, retention='survivors', allow_prediction_scale=True)
            elapsed = time.perf_counter() - before
            with RealmStore(run, resume=True) as store:
                assert store.status()['completed_seeds'] == 100000
                receipts = []
                covered = 0
                for first, end, payload in store.db.execute(
                        'SELECT start,end,receipt FROM retention_receipts ORDER BY start'):
                    receipt = json.loads(payload)
                    assert int(first) == trial * 100000 + covered
                    assert int(end) - int(first) == receipt['inputs']
                    covered += receipt['inputs']
                    receipts.append((first, end, receipt))
                assert covered == 100000
                digest = hashlib.sha256()
                for candidate in store.iter_candidates():
                    digest.update(canonical(candidate).encode())
                fingerprint = (receipts, digest.hexdigest())
            if expected is None:
                expected = fingerprint
            elif expected != fingerprint:
                raise RuntimeError('Durable decision receipt or candidate mismatch')
            row = {'trial': trial, 'arm': arm, 'wall_seconds': elapsed,
                   'durable_inputs_per_second': 100000 / elapsed,
                   'candidate_fingerprint': fingerprint[1],
                   'receipt_fingerprint': hashlib.sha256(canonical(receipts).encode()).hexdigest(),
                   'execution': status['execution']}
            result['durable_pairs'].append(row)
            save()
            print(json.dumps(row), flush=True)
    result['median_durable_inputs_per_second'] = {
        arm: statistics.median(row['durable_inputs_per_second']
             for row in result['durable_pairs'] if row['arm'] == arm)
        for arm in ('control', 'selected')}
    result['status'] = 'complete'
    save()


if __name__ == '__main__':
    main()
