"""Frozen-cohort BDS audit. Dry-run by default; no admission or catalog changes."""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from seed_search.realm.predictor_diagnostics import COMMANDS, IMAGE

DIMENSIONS = {'overworld', 'nether', 'the_end'}
TYPES = {'trial_chamber', 'stronghold', 'mineshaft', 'ancient_city', 'village',
    'ruined_portal', 'shipwreck', 'monument', 'outpost', 'fortress', 'bastion',
    'desert_pyramid', 'jungle_temple', 'swamp_hut', 'igloo', 'ocean_ruin', 'mansion',
    'buried_treasure', 'trail_ruins', 'abandoned_camp', 'ruined_portal_nether', 'end_city'}
TERMINAL = ('The nearest minecraft:', 'Syntax error', 'No valid structure',
            'Could not find', 'Unknown command', 'Unknown structure')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def atomic_json(path, value):
    path = Path(path); temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2); stream.write('\n'); stream.flush()
        import os
        os.fsync(stream.fileno())
    temporary.replace(path)


def size(path):
    return sum(p.stat().st_size for p in Path(path).rglob('*') if p.is_file() and not p.is_symlink())


def coordinate(point, dimension, *, xyz):
    if not isinstance(point, list) or len(point) != (3 if xyz else 2) or any(type(v) is not int for v in point):
        raise ValueError('Coordinates must be integer lists')
    x, z = (point[0], point[2]) if xyz else point
    if abs(x) > 5120 or abs(z) > 5120: raise ValueError('Coordinate envelope exceeded')
    if xyz:
        low, high = {'overworld': (-64, 319), 'nether': (0, 127), 'the_end': (0, 255)}[dimension]
        if not low <= point[1] <= high: raise ValueError('Invalid dimension Y')


def validate_manifest(value):
    if value.get('revision') != 'generalization-cohort-v1': raise ValueError('Manifest revision')
    if (value.get('image_id') != IMAGE or value.get('bds_build') != '1.26.52.3' or
            value.get('prediction_revision') != 'cubiomes-bedrock-26.50' or value.get('script_api') != '2.10.0'):
        raise ValueError('Manifest build/settings scope differs')
    worlds = value['worlds']
    if len(worlds) != 24 or len({w['seed'] for w in worlds}) != 24: raise ValueError('Frozen cohort differs')
    if [w['index'] for w in worlds] != list(range(24)): raise ValueError('Invalid world ordering')
    if [w['group'] for w in worlds] != ['blind'] * 16 + ['targeted'] * 8: raise ValueError('Cohort groups differ')
    if value['pilot_indices'] != [0, 16, 1, 17, 2]: raise ValueError('Pilot differs')
    total_points = total_queries = 0
    for world in worlds:
        if not isinstance(world['seed'], str) or str(int(world['seed'])) != world['seed'] or not -(1 << 63) <= int(world['seed']) < (1 << 63):
            raise ValueError('Seed must be exact signed64 decimal')
        seen = set(); ids = set()
        if len(world['predictions']) > 1024: raise ValueError('Per-world biome cap')
        for p in world['predictions']:
            if p['dimension'] not in DIMENSIONS or not isinstance(p['biome_name'], str) or not p['biome_name'] or not isinstance(p['sample_group'], str):
                raise ValueError('Invalid biome prediction')
            coordinate(p['position'], p['dimension'], xyz=True)
            key = p['dimension'], *p['position']
            if key in seen: raise ValueError('Duplicate biome point')
            seen.add(key)
        for q in world['structures']:
            if q['case_id'] in ids or not isinstance(q['case_id'], str): raise ValueError('Duplicate/invalid case ID')
            ids.add(q['case_id'])
            if q['structure_type'] not in TYPES or q['command_id'] != COMMANDS.get(q['structure_type'], q['structure_type']):
                raise ValueError('Unapproved locate command')
            expected = 'nether' if q['structure_type'] in ('fortress', 'bastion', 'ruined_portal_nether') else ('the_end' if q['structure_type'] == 'end_city' else 'overworld')
            if q['dimension'] != expected: raise ValueError('Wrong structure dimension')
            coordinate(q['origin'], expected, xyz=False)
            if q['disposition'] not in ('retained', 'rejected', 'discovery'): raise ValueError('Invalid disposition')
            if (q['predicted'] is None) != (q['disposition'] == 'discovery'): raise ValueError('Prediction/disposition differs')
            if q['predicted'] is not None: coordinate(q['predicted'], expected, xyz=False)
        total_points += len(world['predictions']); total_queries += len(world['structures'])
    if total_points > 24576 or total_queries > 2000: raise ValueError('Cumulative query cap')
    return dict(worlds=24, biome_reads=total_points, locates=total_queries)


def run_world(world, directory, *, docker, manifest_sha, seconds, output_root, resume_from=None, repair_observer=False):
    """One immutable fresh default-settings world, serial command/biome batches."""
    started = time.monotonic(); directory.mkdir(exist_ok=False)
    observer = ROOT / 'scripts/generalization_observer.js'
    shutil.copyfile(observer, directory / 'observer.js')
    spec = importlib.util.spec_from_file_location('generalization_bds_setup', ROOT / 'reviews/spawn-validation-2026-10-17/bds_runner.py')
    setup = importlib.util.module_from_spec(spec); spec.loader.exec_module(setup)
    previous = None
    if resume_from is None:
        setup.BASE = directory; work = setup.prepare(world['seed'], 'world')
    else:
        resume_from = Path(resume_from)
        previous = json.loads((resume_from / 'report.json').read_bytes())
        if (previous['seed'] != world['seed'] or previous['manifest_sha256'] != manifest_sha or
                previous['status'] != 'failed' or previous.get('clean_shutdown') is not True or
                previous.get('owned_container_removed') is not True or
                (previous.get('resumed_from') is not None and not repair_observer) or previous.get('observer_repaired') is True):
            raise ValueError('Only one reconciled clean stopped attempt may resume')
        work = Path(previous.get('work_directory', str(Path(previous.get('resumed_from', {}).get('directory', resume_from)) / 'worlds/world')))
        if not work.is_relative_to(output_root) or work.is_symlink() or not work.is_dir():
            raise ValueError('Resume must use the same owned campaign world')
        installed = work / 'behavior_packs/spawn_observer/scripts/main.js'
        if digest(installed.read_bytes()) != digest(observer.read_bytes()):
            if not repair_observer: raise ValueError('Cannot silently change observer during resume')
            shutil.copyfile(installed, directory / 'previous-observer.js')
            shutil.copyfile(observer, installed)
    token = uuid.uuid4().hex[:12]; name = 'codex-generalization-' + token
    report = dict(status='starting', seed=world['seed'], group=world['group'], index=world['index'],
        manifest_sha256=manifest_sha, image_id=IMAGE, script_api='2.10.0',
        settings_sha256=digest((work / 'server.properties').read_bytes()),
        observer_sha256=digest(observer.read_bytes()), harness_sha256=digest(Path(__file__).read_bytes()),
        container=name, token=token, seconds=seconds, cpus=2, memory_gib=2, work_directory=str(work),
        observer_protocol='direct-api-first-v2', observer_repaired=repair_observer,
        queries=[], biome_batches=[], interpretation='Raw default-settings observations; no physical census or admission change')
    if previous is not None:
        report.update(queries=previous['queries'], biome_batches=previous['biome_batches'],
            resumed_from=dict(report_sha256=digest((resume_from/'report.json').read_bytes()),
                console_sha256=digest((resume_from/'console.log').read_bytes()), directory=str(resume_from),
                previous_wall_seconds=previous.get('cumulative_world_wall_seconds', previous['wall_seconds']),
                reason=('Explicit direct-API-first observer repair after two loading timeouts; unfinished probes only'
                        if repair_observer else 'Outer 60s batch timeout; same world, unchanged probes, only unfinished observations')))
    atomic_json(directory / 'report.json', report)
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
if [ -d /opt/bds/config ] && [ ! -e /audit/config ]; then cp -a /opt/bds/config /audit/config; fi
cd /audit
export LD_LIBRARY_PATH=/opt/bds
exec /usr/bin/timeout --signal=TERM --kill-after=10 ''' + str(max(1, seconds - 15)) + ''' /opt/bds/bedrock_server'''
    argv = [docker, 'run', '--rm', '-i', '--pull=never', '--name', name,
        '--label', 'seed-search.generalization=' + token, '--cpus', '2', '--memory', '2g',
        '--pids-limit', '256', '--ulimit', 'core=0', '--network', 'bridge', '--read-only',
        '--tmpfs', '/tmp:rw,size=128m', '--log-opt', 'max-size=4m',
        '--mount', f'type=bind,src={work},dst=/audit', '--workdir', '/audit',
        '--entrypoint', '/bin/sh', IMAGE, '-c', script]
    process = None; reader = None; events = queue.Queue()
    deadline = started + seconds - 45
    log = (directory / 'console.log').open('w', buffering=1)
    if previous is not None:
        log.write('PRIOR_ATTEMPT_CONSOLE_BEGIN\n' + (resume_from/'console.log').read_text() + '\nPRIOR_ATTEMPT_CONSOLE_END\n')
    def check():
        if time.monotonic() >= deadline: raise TimeoutError('Per-world observation allowance exhausted')
        if size(output_root) > 8 << 30: raise OSError('Owned output cap exceeded')
    def receive():
        for line in process.stdout:
            log.write(line); events.put(line)
    def send(command):
        check(); log.write('AUDIT_INPUT ' + command + '\n'); process.stdin.write(command + '\n'); process.stdin.flush()
    def wait(predicate, allowance):
        until = min(deadline, time.monotonic() + allowance)
        while time.monotonic() < until:
            check()
            try: line = events.get(timeout=.25)
            except queue.Empty:
                if process.poll() is not None: raise RuntimeError('BDS exited')
                continue
            if predicate(line): return line
        raise TimeoutError('No matching game response before deadline')
    try:
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        reader = threading.Thread(target=receive, daemon=True); reader.start()
        line = wait(lambda s: 'GENERALIZATION_IDENTITY ' in s, 90)
        identity = json.loads(line.split('GENERALIZATION_IDENTITY ', 1)[1])
        if identity['seed'] != world['seed'] or identity['api'] != '2.10.0' or identity['players'] != 0: raise ValueError('World identity mismatch')
        report['world_identity'] = identity
        observed_cases = {q['case_id'] for q in report['queries']}
        for q in world['structures']:
            if q['case_id'] in observed_cases: continue
            x, z = q['origin']
            send(f'execute in {q["dimension"]} positioned {x} 64 {z} run locate structure minecraft:{q["command_id"]} false')
            response = wait(lambda s: any(t in s for t in TERMINAL), 30)
            report['queries'].append(dict(case_id=q['case_id'], dimension=q['dimension'], query=q['origin'], command_id=q['command_id'], output=[response.rstrip()]))
        completed_points = {(batch['dimension'], row['x'], row['y'], row['z'])
            for batch in report['biome_batches'] for row in batch['rows']}
        batch_id = max((batch['id'] for batch in report['biome_batches']), default=0)
        for dim in ('overworld', 'nether', 'the_end'):
            points = [p['position'] for p in world['predictions'] if p['dimension'] == dim and
                      (dim, *p['position']) not in completed_points]
            for start in range(0, len(points), 12):
                subset = points[start:start + 12]; batch_id += 1
                payload = dict(id=batch_id, dimension=dim, points=subset)
                encoded = json.dumps(payload, separators=(',', ':'))
                if len(encoded) > 2000: raise ValueError('Script-event payload cap')
                send('scriptevent generalization:observe ' + encoded)
                line = wait(lambda s: 'GENERALIZATION_RESULT ' in s or 'GENERALIZATION_ERROR ' in s, 120)
                if 'GENERALIZATION_ERROR ' in line: raise RuntimeError(line.strip())
                result = json.loads(line.split('GENERALIZATION_RESULT ', 1)[1])
                if result['id'] != batch_id or result['dimension'] != dim or result['chunksAfterUnload'] != 0: raise ValueError('Batch binding/cleanup differs')
                if [[r['x'], r['y'], r['z']] for r in result['rows']] != subset: raise ValueError('Observed XYZ differs')
                report['biome_batches'].append(result)
                atomic_json(directory / 'report.json', report)
        send('save hold'); saved = False
        for _ in range(10):
            send('save query')
            try: wait(lambda s: 'Files are now ready' in s, 2); saved = True; break
            except TimeoutError: pass
        send('save resume'); report['save_confirmed'] = saved
        if not saved: raise RuntimeError('Save confirmation missing')
        report['status'] = 'observed'
    except Exception as error:
        report.update(status='failed', error=type(error).__name__ + ': ' + str(error))
    finally:
        if process is not None and process.poll() is None:
            try: process.stdin.write('stop\n'); process.stdin.flush(); process.wait(timeout=25)
            except (OSError, subprocess.TimeoutExpired): pass
        report['clean_shutdown'] = process is not None and process.poll() == 0
        report['owned_container_removed'] = False
        try:
            inspected = subprocess.run([docker, 'inspect', name], capture_output=True, text=True, timeout=10)
            if inspected.returncode == 0:
                info = json.loads(inspected.stdout)[0]
                if (info['Config'].get('Labels') or {}).get('seed-search.generalization') != token: raise RuntimeError('Container ownership mismatch')
                subprocess.run([docker, 'rm', '--force', name], capture_output=True, check=True, timeout=20)
            report['owned_container_removed'] = subprocess.run([docker, 'inspect', name], capture_output=True, timeout=10).returncode != 0
        except Exception as error: report['cleanup_error'] = type(error).__name__ + ': ' + str(error)
        if process is not None:
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.terminate(); process.wait(timeout=5)
        if reader is not None: reader.join(timeout=3)
        log.close(); report['wall_seconds'] = time.monotonic() - started
        report['cumulative_world_wall_seconds'] = report['wall_seconds'] + (previous.get('cumulative_world_wall_seconds',previous['wall_seconds']) if previous is not None else 0)
        text = (directory / 'console.log').read_text()
        report['game_build_observed'] = bool(re.search(r'\bVersion: 1\.26\.52\.3(?:\s|$)', text))
        atomic_json(directory / 'report.json', report)
    return report


def run(manifest_path, output, *, phase, execute=False, resume_index=None, repair_observer=False):
    raw = Path(manifest_path).read_bytes()
    if len(raw) > 16 << 20: raise ValueError('Manifest size cap')
    manifest = json.loads(raw); budget = validate_manifest(manifest); sha = digest(raw)
    if not execute: return dict(dry_run=True, manifest_sha256=sha, budget=budget)
    output = Path(output).absolute()
    if output.is_relative_to(ROOT) or any(c in str(output) for c in ',\n'): raise ValueError('Use external owned output')
    for p in (output, *output.parents):
        if p.is_symlink(): raise ValueError('Symlink output is unsupported')
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'campaign.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        frozen = output / 'manifest.json'
        if frozen.exists() and frozen.read_bytes() != raw: raise ValueError('Campaign manifest changed')
        if not frozen.exists(): frozen.write_bytes(raw)
        ledger_path = output / 'ledger.json'
        ledger = json.loads(ledger_path.read_bytes()) if ledger_path.exists() else []
        incomplete = [r for r in ledger if r['state'] != 'complete']
        if incomplete and (len(incomplete) != 1 or incomplete[0]['index'] != resume_index or incomplete[0]['state'] != 'failed'):
            raise ValueError('Reconcile incomplete/failed attempt before any new dispatch')
        if len({r['index'] for r in ledger}) != len(ledger): raise ValueError('Duplicate attempts')
        done = {r['index'] for r in ledger if r['state'] == 'complete'}
        for row in ledger:
            prior = output / row.get('report_path', f'world-{row["index"]:02}/report.json')
            if not prior.is_file() or digest(prior.read_bytes()) != row.get('report_sha256'):
                raise ValueError('Completed report changed or is missing')
            report = json.loads(prior.read_bytes())
            if report['manifest_sha256'] != sha or report['seed'] != manifest['worlds'][row['index']]['seed']:
                raise ValueError('Completed world belongs to different manifest/seed')
            if row['state'] == 'failed' and ((report.get('resumed_from') is not None and not repair_observer) or report.get('observer_repaired') is True or
                    report.get('clean_shutdown') is not True or report.get('owned_container_removed') is not True):
                raise ValueError('Failed world cannot safely resume')
        docker = shutil.which('docker')
        if not docker or subprocess.check_output([docker, 'image', 'inspect', IMAGE, '--format', '{{.Id}}'], text=True, timeout=20).strip() != IMAGE: raise ValueError('Pinned image unavailable')
        pilot = manifest['pilot_indices']
        if phase == 'expand' and not set(pilot).issubset(done): raise ValueError('Complete pilot before expansion')
        indices = pilot if phase == 'pilot' else [w['index'] for w in manifest['worlds'] if w['index'] not in pilot]
        cap = 1800 if phase == 'pilot' else 7200
        for index in indices:
            if index in done: continue
            spent = sum(r['wall_seconds'] for r in ledger)
            if cap - spent < 90: raise TimeoutError('Remaining cumulative world allowance insufficient')
            world = manifest['worlds'][index]
            row = next((r for r in ledger if r['index'] == index), None)
            previous_seconds = row['wall_seconds'] if row is not None else 0.
            if 600 - previous_seconds < 90: raise TimeoutError('Per-world cumulative allowance insufficient for resume')
            resume_from = (output / row.get('report_path', f'world-{index:02}/report.json')).parent if row is not None else None
            if row is None:
                row = dict(index=index, state='starting', wall_seconds=0., seed=world['seed']); ledger.append(row)
            row['state'] = 'starting'; atomic_json(ledger_path, ledger)
            directory = output / (f'world-{index:02}' if resume_from is None else f'world-{index:02}-' + ('repair-1' if repair_observer else 'resume-1'))
            report = run_world(world, directory, docker=docker, manifest_sha=sha,
                seconds=min(int(600-previous_seconds), int(cap-spent)), output_root=output, resume_from=resume_from, repair_observer=repair_observer and resume_from is not None)
            row.update(state='complete' if report['status'] == 'observed' and all(report.get(k) is True for k in ('clean_shutdown', 'owned_container_removed', 'save_confirmed', 'game_build_observed')) else 'failed', wall_seconds=previous_seconds+report['wall_seconds'])
            row.update(report_path=str((directory/'report.json').relative_to(output)), report_sha256=digest((directory/'report.json').read_bytes()))
            atomic_json(ledger_path, ledger)
            print(json.dumps(dict(index=index, seed=world['seed'], state=row['state'], seconds=row['wall_seconds'], error=report.get('error'))), flush=True)
            if row['state'] != 'complete': raise RuntimeError('World failed; no new dispatch before reconciliation')
        return dict(phase=phase, completed=len(ledger), game_wall_seconds=sum(r['wall_seconds'] for r in ledger), manifest_sha256=sha)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', choices=('pilot', 'expand'), default='pilot'); parser.add_argument('--execute', action='store_true')
    parser.add_argument('--resume-index', type=int, help='One explicit reconciled resume of unfinished probes in an existing owned world')
    parser.add_argument('--repair-observer', action='store_true', help='One explicitly reconciled observer-method repair, preserving old logs and cumulative caps')
    args = parser.parse_args(); print(json.dumps(run(args.manifest, args.output, phase=args.phase, execute=args.execute, resume_index=args.resume_index, repair_observer=args.repair_observer)), flush=True)
