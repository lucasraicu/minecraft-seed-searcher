"""Bounded current-source CPU timing, kept separate from concurrent test runs."""
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype, persist_pipeline, seeds_np


def main():
    directory = Path(__file__).resolve().parent
    cfg = dynamic_v3_blueprint_config()
    p = Prototype(ROOT / 'runs/dynamic-baseline-2048/native', cfg)
    stale = [name for name, digest in p.identity['inputs'].items()
             if (ROOT / name).exists() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    assert not stale, stale
    os.environ.setdefault('KMP_BLOCKTIME', '0')
    with p.sweep(seeds_np(0, 4096, 2026101699), threads=34, retention='survivors'):
        pass
    rows = []
    count = 65536
    for trial, order in enumerate(((1, 12, 18, 24, 34), (34, 24, 18, 12, 1), (18, 1, 34, 12, 24))):
        key = 2026101630
        start_index = trial * count
        cohort = seeds_np(start_index, start_index + count, key)
        for threads in order:
            p.lib.nb_diag_reset()
            wall = time.perf_counter()
            native = 0.0
            retained = 0
            for first in range(0, count, 16384):
                with p.sweep(cohort[first:first + 16384], threads=threads, retention='survivors') as batch:
                    native += batch.native_seconds
                    retained += int(batch.pointer.result_count)
            elapsed = time.perf_counter() - wall
            diag = p.ffi.new('uint64_t[12]')
            p.lib.nb_diag_get(diag)
            row = dict(trial=trial, run_key=key, start_index=start_index, count=count, threads=threads,
                       seconds=elapsed, native_seconds=native, inputs_per_second=count / elapsed,
                       retained=retained, funnel=[int(diag[i]) for i in range(12)])
            rows.append(row)
            print(json.dumps(row), flush=True)
    durable = []
    for trial in range(3):
        run = directory / f'cpu-durable-{trial}'
        assert not run.exists(), 'Use a fresh report directory for repeated durable timing'
        result = persist_pipeline(p, run, count, run_key=2026101630, start_index=trial * count,
                                  threads=34, batch_size=16384, retention='survivors', top_k=50)
        row = {key: result[key] for key in ('wall_seconds', 'input_seeds_per_second', 'newly_committed', 'cutoff_score')}
        row['trial'] = trial
        row['top_count'] = len(result['top_tracker'])
        durable.append(row)
        print(json.dumps({'durable': row}), flush=True)
    medians = {str(threads): statistics.median(row['inputs_per_second'] for row in rows if row['threads'] == threads)
               for threads in (1, 12, 18, 24, 34)}
    result = dict(scope='Current-source compact kernel and separately checkpointed compact pipeline; three disjoint cohorts, reused across thread arms; no historical comparison or actual-generation certification',
                  source='3a83220', count_per_cohort=count, distinct_random_inputs=3 * count,
                  platform=platform.platform(), logical_cpus=os.cpu_count(), identity=p.identity,
                  rows=rows, median_inputs_per_second=medians, durable=durable,
                  durable_median_inputs_per_second=statistics.median(row['input_seeds_per_second'] for row in durable),
                  peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    (directory / 'cpu-benchmark.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'medians': medians, 'durable_median': result['durable_median_inputs_per_second']}), flush=True)


if __name__ == '__main__':
    main()
