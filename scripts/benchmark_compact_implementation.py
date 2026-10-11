"""Bounded persisted compact-contract benchmark, including a frozen reference."""
import argparse
import json
from pathlib import Path
import resource
import sys
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--package')
    p.add_argument('--output', required=True)
    p.add_argument('--count', type=int, default=1000)
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--trials', type=int, default=3)
    p.add_argument('--workers', type=int, default=30)
    p.add_argument('--threads', type=int, default=1)
    p.add_argument('--mode', default='complete')
    p.add_argument('--lattice', default='border')
    p.add_argument('--refinement', type=int, default=0)
    args = p.parse_args()
    if args.package:
        sys.path.insert(0, str(Path(args.package).resolve()))
    from seed_search.realm.config import default_config
    from seed_search.realm.runner import run_scan, _seed
    from seed_search.realm.store import RealmStore
    from seed_search.realm.capabilities import identity
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    cfg = default_config()
    cfg['search'].update(workers=args.workers, native_threads_per_worker=args.threads,
                         inventory_mode=args.mode)
    cfg['biomes']['lattice'] = args.lattice
    cfg['biomes']['refinement_budget'] = args.refinement
    manifest = {'config': cfg, 'backend': identity(), 'seeds': [str(_seed(i, cfg['search']))
                for i in range(args.start, args.start+args.count)]}
    (root/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    records = []
    for trial in range(args.trials):
        out = root/f'trial-{trial}'
        begin = time.perf_counter()
        before = resource.getrusage(resource.RUSAGE_SELF)
        run_scan(cfg, out, args.count, start_index=args.start, workers=args.workers,
                 identity={'config': cfg, 'backend': manifest['backend'], 'benchmark': True},
                 allow_prediction_scale=True)
        elapsed = time.perf_counter()-begin
        after = resource.getrusage(resource.RUSAGE_SELF)
        with RealmStore(out, resume=True) as store:
            stages = {}; work = {}; cpu = 0.; points = 0; anchors = 0; qualified = 0
            for result in store.iter_results():
                for key, value in result.get('stage_seconds', {}).items():
                    stages[key] = stages.get(key, 0)+value
                cpu += result.get('worker_cpu_seconds', 0)
                for key, value in result.get('native_work', {}).items():
                    row = work.setdefault(key, {'calls': 0, 'points': 0, 'seconds': 0})
                    for field in row: row[field] += value.get(field, 0)
                points += result['counts'].get('biome_samples', 0)
                anchors += len(result['anchors'])
                qualified += any(a['qualification']=='PREDICTED' for a in result['anchors'])
            status = store.status()
        record = {'trial': trial, 'seconds': elapsed, 'inputs_per_second': args.count/elapsed,
                  'parent_cpu_seconds': after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
                  'worker_cpu_seconds': (status.get('worker_statistics') or {}).get('worker_cpu_seconds',cpu), 'stages': stages, 'native_work': work,
                  'biome_points': points, 'anchors': anchors, 'qualified_seeds': qualified,
                  'status': status, 'bytes': sum(q.stat().st_size for q in out.rglob('*') if q.is_file())}
        records.append(record)
        (root/'benchmark.json').write_text(json.dumps(records, indent=2)+'\n')
        print(json.dumps({k: record[k] for k in ('trial', 'seconds', 'inputs_per_second', 'anchors', 'qualified_seeds')}), flush=True)


if __name__ == '__main__':
    main()
