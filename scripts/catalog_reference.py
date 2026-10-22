#!/usr/bin/env python3
"""Bounded CPU catalog reference. Does not expose a public service or certify worlds."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import resource
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
MAX_BYTES = 1 << 30
MAX_RSS_KB = 4 * 1024 * 1024


def validate_budget(threads, seconds):
    if type(threads) is not int or not 1 <= threads <= 4:
        raise ValueError('Reference thread cap is 1..4')
    if type(seconds) is not int or not 1 <= seconds <= 300:
        raise ValueError('Total extraction wall cap is 1..300 seconds')


def atomic_json(path, value):
    from seed_search.catalog.registry import canonical_json
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.checkpoint-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(canonical_json(value)); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def tree_bytes(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def _extract(args):
    # Only parent-approved fixed cohort jobs call this internal subprocess entry.
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[key] = '1'
    resource.setrlimit(resource.RLIMIT_CPU, (1200, 1200))
    from seed_search import _native
    from seed_search.backend import Backend, configure_native_threads, model_metadata, biome_name, native_runtime
    from seed_search.realm.native_identity import native_source_fingerprint
    from seed_search.realm.biomes import canonical
    from seed_search.catalog.models import identity
    from seed_search.catalog.extract import extract_observation
    native_runtime()  # Fail closed on source/binary drift; never rebuild implicitly.
    configure_native_threads(args.threads)
    value = identity(args.seed, model_id=model_metadata()['model'],
        source_sha256=native_source_fingerprint(),
        native_sha256=hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest())
    checkpoint = args.output
    previous = json.loads(checkpoint.read_text()) if checkpoint.exists() else None
    with Backend(args.seed) as backend:
        extract_observation(value, backend, name_for_id=lambda bid: canonical(biome_name(bid)),
            previous=previous, on_progress=lambda obs: atomic_json(checkpoint, obs))
    return 0


def _stop(process):
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            process.wait(timeout=5)
            return
        try: process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait(timeout=5)


def build(args):
    validate_budget(args.threads, args.seconds)
    from seed_search.seeds import seed_from_index
    from seed_search.catalog.registry import digest, REGISTRY_REVISION
    from seed_search.catalog.store import CatalogStore
    from seed_search.catalog.summaries import summarize
    from seed_search.catalog.models import validate_observation
    from seed_search.catalog.registry import FEATURE_IDS
    from seed_search.catalog.coverage import STRUCTURE_METHOD, BIOME_METHOD
    from seed_search import _native
    from seed_search.backend import native_runtime
    from seed_search.realm.native_identity import native_source_fingerprint
    native_runtime()
    if args.output.is_symlink():
        raise ValueError('Symlink output root is not allowed')
    seeds = [str(seed_from_index(i, 0xCA7A10)) for i in range(2)]
    controls = {'schema': 'catalog-reference-run-v1', 'seeds': seeds, 'threads': args.threads,
                'total_extraction_wall_cap_seconds': args.seconds, 'output_cap_bytes': MAX_BYTES,
                'child_rss_cap_bytes': MAX_RSS_KB * 1024, 'registry_revision': REGISTRY_REVISION,
                'native_sha256': hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest(),
                'native_source_sha256': native_source_fingerprint(),
                'reference_source_sha256': {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in [Path(__file__).resolve(), *sorted((ROOT/'src/seed_search/catalog').glob('*.py'))]},
                'selection': 'fixed seed_from_index before relevance evaluation; no personal gate'}
    if args.resume:
        if args.output.is_symlink() or not args.output.is_dir():
            raise ValueError('No safe reference run to resume')
        old = json.loads((args.output / 'controls.json').read_text())
        if old != controls:
            raise ValueError('Resume controls mismatch')
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        atomic_json(args.output / 'controls.json', controls)
        atomic_json(args.output / 'budget.json', {'spent_seconds': 0.0})
    spent = json.loads((args.output / 'budget.json').read_text())['spent_seconds']
    if type(spent) not in (int,float) or not math.isfinite(spent) or not 0 <= spent <= args.seconds:
        raise ValueError('Invalid durable extraction budget')
    initial_spent = spent
    observations = []; layouts = []; jobs = []
    started = time.monotonic()
    for index, seed in enumerate(seeds):
        checkpoint = args.output / f'observation-{index}.json'
        if checkpoint.is_symlink(): raise ValueError('Unsafe checkpoint')
        previous = validate_observation(json.loads(checkpoint.read_text())) if checkpoint.exists() else None
        if previous and previous['identity']['seed'] != seed:
            raise ValueError('Checkpoint seed mismatch')
        finished = previous is not None and all(
            previous['coverage'].get(fid, {}).get('status') == 'complete' and
            previous['coverage'][fid]['method_id'] == (BIOME_METHOD if fid.startswith('biome.') else STRUCTURE_METHOD)
            for fid in FEATURE_IDS)
        remaining = args.seconds - spent
        if finished or remaining <= 0:
            jobs.append({'seed':seed,'resumed_without_extraction':True,'stop_reason':None if finished else 'budget_exhausted'})
            if previous:
                observations.append(previous)
                t=time.monotonic();derived=summarize(previous);layouts.extend(derived)
                jobs[-1].update(summary_seconds=time.monotonic()-t,layouts=len(derived))
            continue
        command = [sys.executable, str(Path(__file__).resolve()), '_extract', '--output', str(checkpoint),
                   '--seed', seed, '--threads', str(args.threads)]
        before = time.monotonic(); reason = None; peak_rss_kb = 0
        # Reserve the entire remaining budget before starting. A parent crash
        # consumes that reservation; a healthy exit refunds unused wall time.
        atomic_json(args.output / 'budget.json', {'spent_seconds': float(args.seconds)})
        with (args.output / f'extract-{index}.log').open('ab') as log:
            process = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            try:
                while process.poll() is None:
                    elapsed = time.monotonic()-before
                    rss = subprocess.run(['ps', '-o', 'rss=', '-p', str(process.pid)],
                        capture_output=True, text=True, check=False).stdout.strip()
                    if rss: peak_rss_kb = max(peak_rss_kb, int(rss))
                    if elapsed > remaining: reason = 'wall_timeout'
                    elif peak_rss_kb > MAX_RSS_KB: reason = 'memory_cap'
                    elif tree_bytes(args.output) > MAX_BYTES: reason = 'output_cap'
                    if reason: _stop(process); break
                    time.sleep(0.1)
            finally:
                _stop(process)
        spent = min(float(args.seconds), spent+time.monotonic()-before)
        atomic_json(args.output / 'budget.json', {'spent_seconds': spent})
        jobs.append({'seed': seed, 'exit_status': process.returncode, 'stop_reason': reason,
                     'wall_seconds': time.monotonic()-before, 'peak_rss_bytes': peak_rss_kb*1024})
        if checkpoint.exists():
            obs = validate_observation(json.loads(checkpoint.read_text()))
            if obs['identity']['seed'] != seed:
                raise ValueError('Checkpoint seed mismatch')
            observations.append(obs)
            t = time.monotonic(); derived = summarize(obs); layouts.extend(derived)
            jobs[-1]['summary_seconds'] = time.monotonic()-t
            jobs[-1]['layouts'] = len(derived)
        if reason in ('memory_cap', 'output_cap'): break
    if not observations:
        report = {'controls': controls, 'jobs': jobs, 'status': 'failed_no_observations'}
        atomic_json(args.output / 'report.json', report)
        return 1
    t = time.monotonic()
    with CatalogStore(args.output / 'catalog') as store:
        snapshot_id = store.publish_snapshot(observations, layouts)
        loaded = store.snapshot(snapshot_id)
        if len(loaded['layouts']) != len(layouts): raise ValueError('Snapshot layout mismatch')
    complete = sum(all(obs['coverage'].get(fid, {}).get('status') == 'complete'
        for fid in FEATURE_IDS)
        for obs in observations)
    report = {'schema': 'catalog-reference-report-v1', 'status': 'complete' if complete == 2 else 'partial',
        'scope': 'Research predictor only; no game certification, public activation or retention recall claim',
        'controls': controls, 'jobs': jobs, 'snapshot_id': snapshot_id,
        'worlds': len(observations), 'complete_worlds': complete, 'partial_or_failed_worlds': len(observations)-complete,
        'layouts': len(layouts), 'publication_seconds': time.monotonic()-t,
        'total_wall_seconds': time.monotonic()-started, 'extraction_wall_seconds': spent,
        'new_extraction_wall_seconds': spent-initial_spent,
        'output_bytes': tree_bytes(args.output),
        'observation_bytes_uncompressed': [len(json.dumps(o).encode()) for o in observations]}
    atomic_json(args.output / 'report.json', report)
    print(json.dumps(report, indent=2))
    return 0 if complete == 2 else 2


def query(args):
    from seed_search.catalog.store import CatalogStore
    from seed_search.catalog.request import load_request
    from seed_search.catalog.query import search
    request = load_request(args.request.read_text())
    with CatalogStore(args.catalog) as store:
        data = store.snapshot(request['catalog_snapshot_id'])
    result = search(data['layouts'], request, snapshot_id=data['snapshot_id'], limit=args.limit,
                    observations=data['observations'])
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    b = commands.add_parser('build')
    b.add_argument('--output', type=Path, required=True); b.add_argument('--threads', type=int, default=1)
    b.add_argument('--seconds', type=int, default=300); b.add_argument('--resume', action='store_true')
    q = commands.add_parser('query')
    q.add_argument('--catalog', type=Path, required=True); q.add_argument('--request', type=Path, required=True)
    q.add_argument('--limit', type=int, default=5)
    child = commands.add_parser('_extract', help=argparse.SUPPRESS)
    child.add_argument('--output', type=Path, required=True); child.add_argument('--seed', required=True)
    child.add_argument('--threads', type=int, required=True)
    args = parser.parse_args(argv)
    if args.command == '_extract':
        validate_budget(args.threads, 300)
        return _extract(args)
    return build(args) if args.command == 'build' else query(args)


if __name__ == '__main__':
    raise SystemExit(main())
