#!/usr/bin/env python3
"""Explicit, bounded two-world predictor audit; never starts a seed search.

Requires --execute and a frozen case manifest. Creates fresh owned worlds only.
No catalog evidence, serving process, source world or personal checkpoint is edited.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'sha256:cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8'
SEEDS = {'-3509659830737203357', '-9103892851552028103'}
MAX_BYTES = 4 << 30


def validate_cases(cases):
    if not isinstance(cases, list) or len(cases) != 2 or {c['seed'] for c in cases} != SEEDS:
        raise ValueError('Exactly the two approved signed seeds are required')
    biome = blocks = commands = 0
    for case in cases:
        points, columns, structures = case['points'], case['columns'], case['structures']
        if len(points) > 64 or len(columns) > 10:
            raise ValueError('Per-world point cap')
        biome += len(points) + len(columns)
        blocks += len(points) + len(columns) * 385 + 10
        commands += len(structures)
        chunks = set()
        for x, y, z in points:
            if any(type(v) is not int for v in (x, y, z)) or not -64 <= y <= 319 or max(abs(x), abs(z)) > 5120:
                raise ValueError('Invalid block XYZ')
            chunks.add((x // 16, z // 16))
        for x, z in columns:
            if any(type(v) is not int for v in (x, z)) or max(abs(x), abs(z)) > 5120:
                raise ValueError('Invalid column')
            chunks.add((x // 16, z // 16))
        if len(chunks) > 10:
            raise ValueError('Ticking-area cap')
        for row in structures:
            feature = row['feature']
            expected = {'structure.village': 'village', 'structure.outpost': 'pillager_outpost', 'structure.stronghold': 'stronghold'}
            if feature not in expected or row['command_id'] != expected[feature]:
                raise ValueError('Unsupported targeted structure command')
            if len(row['point']) != 2 or any(type(v) is not int or abs(v) > 5120 for v in row['point']):
                raise ValueError('Invalid locate position')
    if biome > 128 or blocks > 8192 or commands > 32:
        raise ValueError('Cumulative observation caps exceeded')
    return dict(max_biome_reads=biome, max_block_reads=blocks, locate_commands=commands)


def owned_size(path):
    return sum(p.stat().st_size for p in path.rglob('*') if not p.is_symlink() and p.is_file())


def run_world(case, directory, wall, docker, manifest_sha, output_root,
              *, observer_path=None, observer_options=None, post_generation_locates=False,
              copied_world=None, script_api='2.10.0', prepare_copy=None):
    directory.mkdir(exist_ok=False)
    observer = Path(observer_path) if observer_path is not None else ROOT / 'scripts/predictor_targeted_observer.js'
    shutil.copyfile(observer, directory / 'observer.js')
    spec = importlib.util.spec_from_file_location('saved_audit_setup', ROOT / 'reviews/spawn-validation-2026-10-17/bds_runner.py')
    setup_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(setup_module)
    setup_module.BASE = directory
    work = setup_module.prepare(case['seed'], 'world')
    if script_api != '2.10.0' and (script_api != '2.11.0-beta' or copied_world is None or prepare_copy is None):
        raise ValueError('Experimental API requires an explicitly prepared disposable world copy')
    copy_provenance = None
    if copied_world is not None:
        try:
            from .predictor_storage_probe import tree_hashes
        except ImportError:  # Direct script invocation.
            from predictor_storage_probe import tree_hashes
        copied_world = Path(copied_world).resolve(strict=True)
        before = tree_hashes(copied_world)
        target = work / 'worlds/spawn_audit'
        shutil.copytree(copied_world, target, dirs_exist_ok=True)
        if before != tree_hashes(copied_world):
            raise ValueError('Copied source world changed')
        copy_provenance = dict(source=str(copied_world), source_hashes=before,
                               source_unchanged=True)
        if prepare_copy is not None:
            prepare_copy(target)
    manifest_path = work / 'behavior_packs/spawn_observer/manifest.json'
    pack = json.loads(manifest_path.read_text())
    pack['dependencies'][0]['version'] = script_api
    manifest_path.write_text(json.dumps(pack, indent=2) + '\n')
    token = uuid.uuid4().hex[:12]
    name = 'codex-targeted-' + token
    settings = (work / 'server.properties').read_bytes()
    controls = dict(seed=case['seed'], image_id=IMAGE, script_api=script_api,
        cpus=2, memory_gib=2, wall_seconds=wall, output_bytes=MAX_BYTES,
        manifest_sha256=manifest_sha, observer_sha256=hashlib.sha256(observer.read_bytes()).hexdigest(),
        harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        settings_sha256=hashlib.sha256(settings).hexdigest(), container=name,
        prediction=case['prediction'], role='Targeted API/storage observations; not an exhaustive or physical structure census')
    report = dict(controls=controls, status='starting', queries=[], biome_batches=[])
    if copy_provenance is not None:
        report['copied_world'] = copy_provenance
    script = '''set -eu
for p in /opt/bds/*; do
 b=$(basename "$p")
 case "$b" in worlds|server.properties|behavior_packs|config) continue;; esac
 [ -e "/audit/$b" ] || ln -s "$p" "/audit/$b"
done
for p in /opt/bds/behavior_packs/*; do
 [ -e "$p" ] || continue
 b=$(basename "$p")
 [ -e "/audit/behavior_packs/$b" ] || ln -s "$p" "/audit/behavior_packs/$b"
done
if [ -d /opt/bds/config ]; then cp -a /opt/bds/config /audit/config; fi
cd /audit
export LD_LIBRARY_PATH=/opt/bds
exec /usr/bin/timeout --signal=TERM --kill-after=10 ''' + str(wall) + ''' /opt/bds/bedrock_server'''
    args = [docker, 'run', '--rm', '-i', '--pull=never', '--name', name,
        '--label', 'seed-search.targeted=' + token, '--cpus', '2', '--memory', '2g',
        '--pids-limit', '256', '--ulimit', 'core=0', '--network', 'bridge',
        '--read-only', '--tmpfs', '/tmp:rw,size=128m', '--log-opt', 'max-size=4m',
        '--mount', f'type=bind,src={work},dst=/audit', '--workdir', '/audit',
        '--entrypoint', '/bin/sh', IMAGE, '-c', script]
    process = None
    events = queue.Queue()
    started = time.monotonic()
    deadline = started + wall
    log = (directory / 'console.log').open('w', buffering=1)
    reader = None

    def receive():
        for line in process.stdout:
            log.write(line)
            events.put(line)

    def command(value):
        if time.monotonic() >= deadline or owned_size(output_root) > MAX_BYTES:
            raise TimeoutError('Time/output budget reached')
        log.write('AUDIT_INPUT ' + value + '\n')
        process.stdin.write(value + '\n')
        process.stdin.flush()

    def wait_for(predicate, seconds=60):
        until = min(deadline, time.monotonic() + seconds)
        while time.monotonic() < until:
            if owned_size(output_root) > MAX_BYTES:
                raise OSError('Owned output cap')
            try:
                line = events.get(timeout=.25)
            except queue.Empty:
                if process.poll() is not None:
                    raise RuntimeError('BDS process exited')
                continue
            if predicate(line):
                return line
        raise TimeoutError('BDS response deadline')

    try:
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1)
        reader = threading.Thread(target=receive, daemon=True)
        reader.start()
        identity = json.loads(wait_for(lambda s: 'TARGET_IDENTITY ' in s, 90).split('TARGET_IDENTITY ', 1)[1])
        if identity['seed'] != case['seed'] or identity['api'] != script_api or identity['players'] != 0:
            raise ValueError('Unexpected game identity')
        report['world_identity'] = identity
        for index, query in enumerate(case['structures']):
            x, z = query['point']
            command(f'execute in overworld positioned {x} 100 {z} run locate structure minecraft:{query["command_id"]} false')
            response = wait_for(lambda s: any(t in s for t in ('The nearest minecraft:', 'Syntax error', 'No valid structure', 'Could not find', 'Unknown command')), 25)
            report['queries'].append(dict(index=index, kind=query['feature'], dimension='overworld',
                command_id=query['command_id'], query=[x, z], output=[response.rstrip()]))
        payload_data = dict(points=case['points'], columns=case['columns'])
        if observer_options is not None:
            if (set(observer_options) != {'persistence_mode', 'dwell_ticks'} or
                    observer_options['persistence_mode'] not in ('read_only', 'dirty_restore') or
                    type(observer_options['dwell_ticks']) is not int or
                    not 0 <= observer_options['dwell_ticks'] <= 200):
                raise ValueError('Invalid lifecycle observer options')
            payload_data.update(observer_options)
        payload = json.dumps(payload_data, separators=(',', ':'))
        if len(payload) > 2000:
            raise ValueError('Script event payload cap')
        command('scriptevent predictor_audit:observe ' + payload)
        response = wait_for(lambda s: 'TARGET_RESULT ' in s or 'TARGET_ERROR ' in s, max(1, deadline - time.monotonic() - 35))
        if 'TARGET_ERROR ' in response:
            raise RuntimeError(response.strip())
        observation = json.loads(response.split('TARGET_RESULT ', 1)[1])
        if [[r['x'], r['y'], r['z']] for r in observation['rows']] != case['points']:
            raise ValueError('Observed coordinates differ from frozen request')
        if any('error' in r for r in observation['rows']) or observation['biomeReads'] > 128 or observation['blockReads'] > 8192:
            raise ValueError('Observation failure or read cap')
        report['target_result'] = observation
        report['biome_batches'] = [dict(id='target', rows=observation['rows'], ticking_areas_held=observation['tickingAreas'])]
        if post_generation_locates:
            report['post_generation_queries'] = []
            for index, query in enumerate(case['structures']):
                x, z = query['point']
                command(f'execute in overworld positioned {x} 100 {z} run locate structure minecraft:{query["command_id"]} false')
                response = wait_for(lambda s: any(t in s for t in ('The nearest minecraft:', 'Syntax error', 'No valid structure', 'Could not find', 'Unknown command')), 25)
                report['post_generation_queries'].append(dict(index=index, kind=query['feature'],
                    query=[x, z], output=[response.rstrip()]))
        command('save hold')
        saved = False
        for _ in range(10):
            command('save query')
            try:
                wait_for(lambda s: 'Files are now ready' in s, 2)
                saved = True
                break
            except TimeoutError:
                pass
        command('save resume')
        report['save_confirmed'] = saved
        if not saved:
            raise RuntimeError('Save confirmation missing')
        report['status'] = 'observed'
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        if process is not None and process.poll() is None:
            try:
                process.stdin.write('stop\n')
                process.stdin.flush()
                process.wait(timeout=25)
            except (OSError, subprocess.TimeoutExpired):
                pass
        report['clean_shutdown'] = process is not None and process.poll() == 0
        report['owned_container_removed'] = False
        try:
            inspected = subprocess.run([docker, 'inspect', name], capture_output=True, text=True, timeout=10)
            if inspected.returncode == 0:
                info = json.loads(inspected.stdout)[0]
                if (info['Config'].get('Labels') or {}).get('seed-search.targeted') != token:
                    raise RuntimeError('Owned container identity mismatch')
                subprocess.run([docker, 'rm', '--force', name], capture_output=True, check=True, timeout=20)
            report['owned_container_removed'] = subprocess.run([docker, 'inspect', name], capture_output=True, timeout=10).returncode != 0
        except Exception as error:
            report['cleanup_error'] = type(error).__name__ + ': ' + str(error)
        if process is not None:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
            reader.join(timeout=3)
        log.close()
        report['wall_seconds'] = time.monotonic() - started
        (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    raw = args.manifest.read_bytes()
    if len(raw) > 65536:
        parser.error('Manifest too large')
    cases = json.loads(raw)
    budget = validate_cases(cases)
    if not args.execute:
        print(json.dumps(dict(dry_run=True, budget=budget)))
        return 0
    output = args.output.resolve()
    if output.is_relative_to(ROOT) or any(c in str(output) for c in ',\n'):
        parser.error('Use a new output directory outside the repository')
    output.mkdir(parents=True, exist_ok=False)
    docker = shutil.which('docker')
    if not docker or subprocess.check_output([docker, 'image', 'inspect', IMAGE, '--format', '{{.Id}}'], text=True, timeout=20).strip() != IMAGE:
        raise RuntimeError('Pinned image unavailable')
    reports = []
    for index, case in enumerate(cases):
        remaining = 600 - sum(r['wall_seconds'] for r in reports)
        if remaining < 30:
            raise RuntimeError('Cumulative game budget exhausted')
        report = run_world(case, output / ('world-' + str(index)), min(300, int(remaining)), docker,
                           hashlib.sha256(raw).hexdigest(), output)
        reports.append(report)
        print(json.dumps(dict(world=index, status=report['status'], wall=report['wall_seconds'], error=report.get('error'))), flush=True)
        if report['status'] != 'observed' or not report['clean_shutdown'] or not report['owned_container_removed']:
            break
    (output / 'summary.json').write_text(json.dumps(dict(budget=budget, reports=[dict(status=r['status'], seed=r['controls']['seed'], wall=r['wall_seconds']) for r in reports]), indent=2) + '\n')
    return 0 if len(reports) == 2 and all(r['status'] == 'observed' and r['clean_shutdown'] for r in reports) else 2


if __name__ == '__main__':
    raise SystemExit(main())
