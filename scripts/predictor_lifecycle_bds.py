#!/usr/bin/env python3
"""Explicit paired persistence experiment in four fresh, disposable BDS worlds."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

try:
    from .predictor_targeted_bds import ROOT, IMAGE, owned_size, run_world, validate_cases, MAX_BYTES
except ImportError:  # Direct script invocation.
    from predictor_targeted_bds import ROOT, IMAGE, owned_size, run_world, validate_cases, MAX_BYTES


def freeze_cases(original):
    cases = json.loads(json.dumps(original))
    first = cases[0]
    points = []
    heights = [-48, 0, 16, 32, 40, 48, 52, 56, 60, 63, 64, 68, 80, 96, 112, 120, 128, 160, 192, 256, 304, 319]
    for x, z in [(-256, -256), (-448, 320)]:
        points.extend([[x, y, z] for y in heights])
    points.extend([[-64, y, 320] for y in [-48, 32, 63, 319]])
    points.extend([[x, 63, -512] for x in range(446, 453)])
    for structure in first['structures']:
        x, z = structure['point']
        points.extend([[x, y, z] for y in [63, 319]])
    first['points'] = points
    budget = validate_cases(cases)
    # Both protocols read the same points, scan columns, and wait the same dwell.
    # Dirty protocol additionally reads/restores each sky marker twice (<=10/world).
    cumulative = dict(biome_reads=2 * budget['max_biome_reads'],
        block_reads=2 * budget['max_block_reads'] + 40,
        locate_commands=4 * budget['locate_commands'], worlds=4,
        max_game_wall_seconds=4 * 240, max_output_bytes=MAX_BYTES,
        dwell_ticks=200, protocols=['read_only', 'dirty_restore'])
    if cumulative['biome_reads'] > 1024 or cumulative['block_reads'] > 16384 or cumulative['locate_commands'] > 128:
        raise ValueError('Cumulative resolution-stage budget exceeded')
    return cases, cumulative


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    raw = args.manifest.read_bytes()
    if len(raw) > 65536:
        parser.error('Manifest cap')
    cases, budget = freeze_cases(json.loads(raw))
    if not args.execute:
        print(json.dumps(dict(dry_run=True, budget=budget)))
        return 0
    output = args.output.resolve()
    if output.is_relative_to(ROOT) or any(c in str(output) for c in ',\n'):
        parser.error('Use new owned external output')
    output.mkdir(parents=True, exist_ok=False)
    docker = shutil.which('docker')
    if not docker or subprocess.check_output([docker, 'image', 'inspect', IMAGE, '--format', '{{.Id}}'], text=True, timeout=20).strip() != IMAGE:
        raise RuntimeError('Pinned image unavailable')
    frozen = json.dumps(dict(cases=cases, budget=budget), indent=2).encode()
    (output / 'frozen.json').write_bytes(frozen)
    digest = hashlib.sha256(frozen).hexdigest()
    reports = []
    started = time.monotonic()
    for mode in budget['protocols']:
        for index, case in enumerate(cases):
            if time.monotonic() - started > 1800 or owned_size(output) > MAX_BYTES:
                raise RuntimeError('Cumulative lifecycle time/output cap')
            report = run_world(case, output / f'{mode}-{index}', 240, docker, digest, output,
                observer_path=ROOT / 'scripts/predictor_lifecycle_observer.js',
                observer_options=dict(persistence_mode=mode, dwell_ticks=200),
                post_generation_locates=True)
            reports.append(dict(mode=mode, world=index, seed=case['seed'], status=report['status'],
                wall_seconds=report['wall_seconds'], clean_shutdown=report['clean_shutdown'],
                save_confirmed=report.get('save_confirmed'), owned_container_removed=report['owned_container_removed']))
            (output / 'summary.json').write_text(json.dumps(reports, indent=2) + '\n')
            if report['status'] != 'observed' or not report['clean_shutdown'] or not report.get('save_confirmed') or not report['owned_container_removed']:
                raise RuntimeError('Failed lifecycle world; inspect report before continuing')
    print(json.dumps(reports, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
