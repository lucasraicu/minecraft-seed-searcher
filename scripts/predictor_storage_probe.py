#!/usr/bin/env python3
"""Read-only stopped-world export and strict stored-biome point diagnostics.

The pinned container opens only a temporary copy of LevelDB. Stored IDs retain
their own namespace; there is no guessed mapping to predictor IDs or biome names.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'sha256:cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8'
BUILD = '1.26.52.3'
MAX_DB_BYTES = 128 << 20


def load_json(path, limit=20 << 20):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    with Path(path).open('rb') as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('JSON input cap')
    def nonfinite(_):
        raise ValueError('Nonfinite JSON')
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite), hashlib.sha256(raw).hexdigest()


def tree_hashes(world):
    """Bounded source inventory; reject links rather than following them."""
    world = Path(world)
    if world.is_symlink() or not world.is_dir() or not (world / 'db').is_dir():
        raise ValueError('Expected a real stopped-world directory')
    files = [world / 'level.dat']
    for path in (world / 'db').rglob('*'):
        if path.is_symlink():
            raise ValueError('Source DB symlinks are not allowed')
        if path.is_file():
            files.append(path)
        if len(files) > 20000:
            raise ValueError('Source file-count cap')
    if any(path.is_symlink() for path in [world / 'db', *files]):
        raise ValueError('Source symlinks are not allowed')
    if sum(path.stat().st_size for path in files) > MAX_DB_BYTES:
        raise ValueError('Source copy exceeds 128MiB')
    return {str(path.relative_to(world)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}


def validate_report(world, report_path):
    report_path = Path(report_path).resolve(strict=True)
    report, report_sha = load_json(report_path, 2 << 20)
    expected_world = report_path.parent / 'worlds/world/worlds/spawn_audit'
    if Path(world).resolve(strict=True) != expected_world.resolve(strict=True):
        raise ValueError('World is not bound to the supplied audit report')
    if (report.get('status') != 'observed' or report.get('clean_shutdown') is not True or
            report.get('owned_container_removed') is not True or report['controls']['image_id'] != IMAGE):
        raise ValueError('Expected a completed stopped audit using the pinned image')
    if 'target_result' in report and report.get('save_confirmed') is not True:
        raise ValueError('Targeted save acknowledgement missing')
    seed = report['controls']['seed']
    if report['world_identity']['seed'] != seed or report['world_identity']['api'] != '2.10.0':
        raise ValueError('Audit seed/API identity differs')
    console = report_path.parent / 'console.log'
    if console.is_symlink() or console.stat().st_size > 32 << 20 or not re.search(
            rb'\bVersion: 1\.26\.52\.3(?:\s|$)', console.read_bytes()):
        raise ValueError('Actual BDS build line unavailable')
    settings = (report_path.parent / 'worlds/world/server.properties').read_bytes()
    if ('level-seed=' + seed).encode() not in settings.splitlines():
        raise ValueError('World settings seed differs')
    digest = hashlib.sha256(settings).hexdigest()
    if report['controls'].get('settings_sha256', digest) != digest:
        raise ValueError('Settings hash differs')
    return report, dict(report_sha256=report_sha, settings_sha256=digest, build=BUILD,
                        image_sha256=IMAGE, script_api='2.10.0', seed=seed)


def compare_points(export, points, *, resolve_repeats=False, runtime_ceiling=False):
    from seed_search.realm.bedrock_biome_storage import (
        decode_data3d, resolve_repeated_sections, sample_bedrock_runtime,
    )
    if type(resolve_repeats) is not bool:
        raise TypeError('resolve_repeats must be boolean')
    if type(runtime_ceiling) is not bool:
        raise TypeError('runtime_ceiling must be boolean')
    if resolve_repeats and runtime_ceiling:
        raise ValueError('Historical inheritance and runtime ceiling are separate interpretations')
    if export.get('revision') != 'stopped-biome-export-v1':
        raise ValueError('Unknown export format')
    seed = export['world_identity']['seed']
    if not isinstance(seed, str) or not re.fullmatch(r'-?\d+', seed) or not -(1 << 63) <= int(seed) < (1 << 63):
        raise ValueError('Expected exact signed-64 seed identity')
    if not isinstance(points, list) or not 1 <= len(points) <= 4096:
        raise ValueError('Point count must be 1..4096')
    cache = {}
    records = export['records']
    if not isinstance(records, list) or len(records) > 4096:
        raise ValueError('Export record-count cap')
    total = 0
    for row in records:
        if type(row['cx']) is not int or type(row['cz']) is not int:
            raise ValueError('Chunk coordinates must be integers')
        if any(not -(1 << 31) <= row[c] < (1 << 31) for c in ('cx', 'cz')):
            raise ValueError('Chunk coordinates exceed int32')
        if row['key'] != (struct.pack('<ii', row['cx'], row['cz']) + b'\x2b').hex():
            raise ValueError('Raw record key does not bind its chunk coordinates')
        if len(row['data']) > 2 << 20:
            raise ValueError('Record-size cap')
        raw = bytes.fromhex(row['data'])
        total += len(raw)
        if total > 8 << 20 or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Record size/hash mismatch')
        key = (row['cx'], row['cz'])
        if key in cache:
            raise ValueError('Duplicate chunk record')
        decoded = decode_data3d(raw)
        repeats = {s.section_y for s in decoded.sections if s.kind == 'unknown'}
        cache[key] = (resolve_repeated_sections(decoded) if resolve_repeats else decoded,
                      row['sha256'], repeats)
    results = []
    for point in points:
        if not isinstance(point, list) or len(point) != 3 or any(type(v) is not int for v in point):
            raise ValueError('Expected integer block XYZ')
        x, y, z = point
        if not -64 <= y <= 319 or max(abs(x), abs(z)) > 5120:
            raise ValueError('Point exceeds inspected bounds')
        found = cache.get((x // 16, z // 16))
        result = dict(position=point, chunk=[x // 16, z // 16],
                      local=[x % 16, y % 16, z % 16], quart=[x // 4, y // 4, z // 4],
                      stored_id=None, status='missing_data3d_record')
        if found:
            decoded, sha, repeats = found
            value = (sample_bedrock_runtime(decoded, x % 16, y, z % 16) if runtime_ceiling
                     else decoded.sample(x % 16, y, z % 16))
            result.update(stored_id=value, record_sha256=sha,
                          status='stored' if value is not None else 'unknown_section')
            if resolve_repeats and value is not None and y // 16 in repeats:
                result['status'] = 'stored_repeated'
            if runtime_ceiling and value is not None and y // 16 in repeats:
                result['status'] = 'runtime_ceiling_clamped'
        results.append(result)
    revision = ('stored-biome-point-diagnostics-v3' if runtime_ceiling else
                'stored-biome-point-diagnostics-v2' if resolve_repeats else 'stored-biome-point-diagnostics-v1')
    return dict(revision=revision, world_identity=export['world_identity'],
                namespace='bedrock_saved_world_numeric_ids_not_predictor_ids', rows=results,
                stored=sum(r['stored_id'] is not None for r in results),
                unknown=sum(r['stored_id'] is None for r in results),
                scope='Persisted data only; no inferred biome name, generation rule or structure completeness.')


def export_world(world, report_path, output, *, dimension_aware=False):
    world = Path(world).resolve(strict=True)
    report, identity = validate_report(world, report_path)
    before = tree_hashes(world)
    docker = shutil.which('docker')
    if not docker:
        raise RuntimeError('Docker is required for the isolated stopped-world reader')
    # Refuse to inspect a source potentially mounted into a running container.
    ids = subprocess.check_output([docker, 'ps', '-q'], text=True, timeout=10).split()
    if ids:
        active = json.loads(subprocess.check_output([docker, 'inspect', *ids], text=True, timeout=10))
        for container in active:
            for mount in container.get('Mounts', []):
                source = Path(mount.get('Source', '/nonexistent')).resolve()
                if world == source or world.is_relative_to(source) or source.is_relative_to(world):
                    raise ValueError('Source world overlaps a running container mount')
    output = Path(output).resolve()
    if output.exists() or output.is_relative_to(world) or output.is_relative_to(ROOT):
        raise ValueError('Use a new export path outside source world and repository')
    if any(c in str(world) for c in ',\n'):
        raise ValueError('Unsupported mount path')
    output.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex[:12]
    name = 'codex-storage-reader-' + token
    reader = ROOT / ('src/seed_search/realm/bds_tools/accuracy_storage_reader.py' if dimension_aware else 'src/seed_search/realm/bds_tools/biome_storage_reader.py')
    command = [docker, 'run', '--rm', '--pull=never', '--name', name, '--label', 'seed-search.storage=' + token,
        '--read-only', '--network', 'none', '--cpus', '1', '--memory', '512m', '--pids-limit', '64',
        '--tmpfs', '/tmp:rw,size=256m', '--mount', f'type=bind,src={world},dst=/input,readonly',
        '--mount', f'type=bind,src={reader},dst=/biome_storage_reader.py,readonly',
        '--entrypoint', '/opt/reader/bin/python', IMAGE, '/biome_storage_reader.py']
    try:
        completed = subprocess.run(command, capture_output=True, check=True, text=True, timeout=60)
        if len(completed.stdout) > 20 << 20:
            raise ValueError('Reader output cap')
        export = json.loads(completed.stdout)
        if export['world_identity']['seed'] != identity['seed']:
            raise ValueError('Saved world seed differs from observed game seed')
        after = tree_hashes(world)
        if after != before:
            raise ValueError('Source world changed during the stopped-world read')
        export['provenance'] = dict(identity, source_hashes=before,
            reader_sha256=hashlib.sha256(reader.read_bytes()).hexdigest(), source_unchanged=True)
        with output.open('x') as handle:
            handle.write(json.dumps(export, indent=2) + '\n')
    finally:
        inspected = subprocess.run([docker, 'inspect', name], capture_output=True, text=True, timeout=10)
        if inspected.returncode == 0:
            info = json.loads(inspected.stdout)[0]
            if (info['Config'].get('Labels') or {}).get('seed-search.storage') != token:
                raise RuntimeError('Reader container ownership mismatch')
            subprocess.run([docker, 'rm', '--force', name], capture_output=True, check=True, timeout=10)
    return export


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    exp = sub.add_parser('export')
    exp.add_argument('--world', type=Path, required=True)
    exp.add_argument('--report', type=Path, required=True)
    exp.add_argument('--output', type=Path, required=True)
    replay = sub.add_parser('compare')
    replay.add_argument('--export', dest='export_path', type=Path, required=True)
    replay.add_argument('--points', type=Path, required=True, help='JSON array of block XYZ')
    interpretation = replay.add_mutually_exclusive_group()
    interpretation.add_argument('--resolve-repeats', action='store_true', help='Historical whole-section experiment; v2, not runtime lookup')
    interpretation.add_argument('--runtime-ceiling', action='store_true', help='Pinned Bedrock stored-ceiling lookup; revision v3')
    args = parser.parse_args(argv)
    if args.action == 'export':
        data = export_world(args.world, args.report, args.output)
        print(json.dumps(dict(seed=data['world_identity']['seed'], records=len(data['records']), source_unchanged=True)))
    else:
        data, _ = load_json(args.export_path)
        points, _ = load_json(args.points, 65536)
        print(json.dumps(compare_points(data, points, resolve_repeats=args.resolve_repeats,
                                        runtime_ceiling=args.runtime_ceiling), indent=2))
    return 0


if __name__ == '__main__':
    # Importing these read-only utilities must not override an explicitly chosen
    # isolated runtime. Direct CLI use retains a fallback for an uninstalled repo.
    sys.path.append(str(ROOT / 'src'))
    raise SystemExit(main())
