"""Prepared dynamic diagnostic runner; compilation and runs remain gated.

Instrumented call timings are attribution data, not candidate throughput results.
"""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'reviews/split-audit-2026-10-15/sol'
WORK = Path('/tmp/minecraft-sol-audit-20261015')
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-heavy', action='store_true')
    parser.add_argument('--count', type=int, default=100000)
    parser.add_argument('--threads', type=int, default=34)
    parser.add_argument('--start', type=int, default=50000000)
    parser.add_argument('--build', type=Path, default=WORK / 'diagnostic/native-build')
    parser.add_argument('--output')
    args = parser.parse_args()
    if not args.allow_heavy:
        parser.error('Heavy work is paused pending user release')
    if not (1 <= args.count <= 1000000 and 1 <= args.threads <= 34 and args.start >= 0):
        parser.error('Invalid bounded cohort or worker count')
    from seed_search.realm.native_batch import Prototype, Batch
    from seed_search.realm.config import dynamic_blueprint_config
    from seed_search.seeds import seed_from_index, MASK64
    p = Prototype(args.build, dynamic_blueprint_config())
    ffi, lib = p.ffi, p.lib
    labels = json.loads((OUT / 'diagnostic-labels.json').read_text())['labels']
    if args.build.parent.name == 'diagnostic-gate':
        labels[12] = 'raw_dark_gate'
    elif args.build.parent.name == 'diagnostic-optimized':
        labels[12] = 'empty_initializer_timing_hook'
    counts = [0] * len(labels)
    seconds = [0.] * len(labels)
    policy = ffi.new('NBPolicy *')
    ffi.memmove(policy, p.policy, ffi.sizeof('NBPolicy'))
    policy.retention = 1
    policy.max_misses = 2
    workers = {}
    selected = {'mansion_inventory': [], 'outpost_inventory': [], 'nether_viability_pair': [],
                'dynamic_center_search': []}
    reached_slot = {'mansion_inventory': 9, 'outpost_inventory': 8,
                    'nether_viability_pair': 7, 'dynamic_center_search': 33}
    retained = 0
    native_seconds = 0.
    for first in range(args.start, args.start + args.count, 16384):
        end = min(args.start + args.count, first + 16384)
        seeds = [seed_from_index(i, 2026101401) for i in range(first, end)]
        values = ffi.new('uint64_t[]', [s & MASK64 for s in seeds])
        samples = ffi.new('SolAuditSample[]', len(seeds))
        before = time.perf_counter()
        pointer = lib.sol_diag_sweep(values, len(seeds), policy, args.threads, samples)
        elapsed = time.perf_counter() - before
        native_seconds += elapsed
        if pointer == ffi.NULL:
            raise RuntimeError('Diagnostic batch allocation/policy failure')
        with Batch(p, pointer, seeds, elapsed, False, False, 'survivors', 2):
            if pointer.error or pointer.effective_threads != args.threads:
                raise RuntimeError('Diagnostic batch error or worker-team mismatch')
            retained += pointer.result_count
            for i, seed in enumerate(seeds):
                sample = samples[i]
                if sample.seed != seed & MASK64:
                    raise RuntimeError('Diagnostic seed identity mismatch')
                for k in range(len(labels)):
                    counts[k] += int(sample.counts[k])
                    seconds[k] += float(sample.seconds[k])
                worker = workers.setdefault(str(sample.worker), {'seeds': 0, 'eval_seconds': 0.})
                worker['seeds'] += 1
                worker['eval_seconds'] += float(sample.eval_seconds)
                for name, slot in reached_slot.items():
                    if sample.counts[slot] and len(selected[name]) < 200:
                        selected[name].append({'index': first+i, 'seed': str(seed),
                                               'run_key': 2026101401})
    report = dict(status='instrumented attribution only', count=args.count,
        start_index=args.start, run_key=2026101401, threads=args.threads,
        build=p.identity, native_seconds_instrumented=native_seconds,
        retained_inputs=retained, workers=workers,
        counters={label: {'count': counts[k], 'seconds': seconds[k]}
                  for k, label in enumerate(labels) if not label.startswith('reserved_')},
        late_stage_inputs=selected,
        caveats=['Timing groups overlap; do not sum parent and child times',
                 'Instrumented throughput is not a production/candidate benchmark',
                 'Native stage-field counts indicate nonzero timing, not exact predicate entries',
                 'Late-stage inputs reached a stage; they are not necessarily qualified survivors'])
    path = OUT / (args.output or f'profile-{args.start}-{args.count}-{args.threads}.json')
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('build', 'late_stage_inputs')}, indent=2))


if __name__ == '__main__':
    main()
