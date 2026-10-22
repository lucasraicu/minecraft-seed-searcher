"""Offline replay of persistence and explicit structure-membership evidence.

Locate equality and generated structure presence are independent observations.
Empty point membership is unknown presence, never an absence certificate.
"""
import hashlib
from pathlib import Path, PurePosixPath
import re

from .predictor_diagnostics import _json, IMAGE, BUILD, LOCATE


REVISION = 'predictor-resolution-regressions-v1'
MAX_FILE = 4 << 20
MAX_BUNDLE = 8 << 20


def load_resolution(directory):
    root = Path(directory)
    if root.is_symlink():
        raise ValueError('Fixture root cannot be a symlink')
    manifest_path = root / 'manifest.json'
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 65536:
        raise ValueError('Invalid fixture manifest')
    manifest = _json(manifest_path.read_bytes())
    if (manifest['revision'] != REVISION or manifest['build'] != BUILD or
            manifest['stable_api'] != '2.10.0' or manifest['membership_api'] != '2.11.0-beta'):
        raise ValueError('Unsupported resolution fixture identity')
    files = manifest['files']
    if not isinstance(files, dict) or not 1 <= len(files) <= 64:
        raise ValueError('Invalid fixture inventory')
    data = {}
    total = 0
    for name, expected in files.items():
        path = PurePosixPath(name)
        if (path.is_absolute() or '..' in path.parts or '\\' in name or
                not path.parts or str(path) != name):
            raise ValueError('Invalid fixture path')
        target = root
        for part in path.parts:
            target /= part
            if target.is_symlink():
                raise ValueError('Fixture symlink')
        if target.stat().st_size > MAX_FILE:
            raise ValueError('Oversized fixture file')
        raw = target.read_bytes()
        total += len(raw)
        if (total > MAX_BUNDLE or len(raw) != expected['bytes'] or
                hashlib.sha256(raw).hexdigest() != expected['sha256']):
            raise ValueError('Fixture size/hash mismatch')
        data[name] = raw
    return manifest, data


def resolution_report(directory):
    manifest, data = load_resolution(directory)
    cases = _json(data['membership/frozen.json'])
    if (not isinstance(cases, list) or len(cases) != 2 or
            {c['seed'] for c in cases} != {'-3509659830737203357', '-9103892851552028103'}):
        raise ValueError('Expected the two frozen diagnostic worlds')
    membership = []
    for world, case in enumerate(cases):
        prefix = f'membership/world-{world}/'
        report = _json(data[prefix + 'report.json'])
        controls = report['controls']
        if (report['status'] != 'observed' or report['clean_shutdown'] is not True or
                report['owned_container_removed'] is not True or report['save_confirmed'] is not True or
                controls['image_id'] != IMAGE or controls['script_api'] != '2.11.0-beta' or
                controls['seed'] != case['seed'] or
                controls['manifest_sha256'] != hashlib.sha256(data['membership/frozen.json']).hexdigest() or
                controls['observer_sha256'] != hashlib.sha256(data['observer/predictor_structure_membership_observer.js']).hexdigest() or
                report['world_identity'] != dict(seed=case['seed'], api='2.11.0-beta', players=0)):
            raise ValueError('Incomplete/incorrect membership report identity')
        if report['copied_world']['source_unchanged'] is not True:
            raise ValueError('Source copy provenance missing')
        settings = data[prefix + 'server.properties']
        if (hashlib.sha256(settings).hexdigest() != controls['settings_sha256'] or
                ('level-seed=' + case['seed']).encode() not in settings.splitlines()):
            raise ValueError('Membership world settings mismatch')
        pack = _json(data[prefix + 'pack-manifest.json'])
        if pack['dependencies'] != [{'module_name': '@minecraft/server', 'version': '2.11.0-beta'}]:
            raise ValueError('Membership API dependency mismatch')
        log = data[prefix + 'console.log'].decode()
        if not re.search(r'\bVersion: ' + re.escape(BUILD) + r'(?:\s|$)', log):
            raise ValueError('Actual membership build line missing')
        emitted = [_json(line.split('TARGET_RESULT ', 1)[1]) for line in log.splitlines()
                   if 'TARGET_RESULT ' in line]
        if emitted != [report['target_result']]:
            raise ValueError('Membership report differs from raw console result')
        rows = report['target_result']['rows']
        if [[r['x'], r['y'], r['z']] for r in rows] != case['points']:
            raise ValueError('Membership coordinates differ from frozen input')
        for row in rows:
            if ('error' in row or not isinstance(row['structures'], list) or
                    any(not isinstance(name, str) or not name for name in row['structures'])):
                raise ValueError('Invalid structure membership observation')
            membership.append(dict(seed=case['seed'], position=[row['x'], row['y'], row['z']],
                structures=row['structures'], block=row['block'],
                status='present' if row['structures'] else 'unconfirmed_at_point',
                method='BDS getGeneratedStructures in disposable beta-API copy'))
    # Preserve locate outcome instead of overwriting it with a physical-presence label.
    locate_disagreements = []
    for world in range(len(cases)):
        report = _json(data[f'lifecycle/dirty_restore-{world}/report.json'])
        for query in report['post_generation_queries']:
            matches = [LOCATE.search(line) for line in query['output'] if LOCATE.search(line)]
            if len(matches) != 1:
                raise ValueError('Expected one post-generation locate response')
            match = matches[0]
            point = [int(match[2]), int(match[3])]
            if point != query['query']:
                locate_disagreements.append(dict(seed=report['world_identity']['seed'],
                    feature=query['kind'], query=query['query'], reported=point,
                    interpretation='Locate coordinate disagreement; not proof of physical absence'))
    coverage = _json(data['coverage-summary.json'])
    columns = []
    column_cases = _json(data['membership-columns/frozen.json'])
    if [c['seed'] for c in column_cases] != [c['seed'] for c in cases]:
        raise ValueError('Column world identity differs')
    for world, case in enumerate(column_cases):
        prefix = f'membership-columns/world-{world}/'
        report = _json(data[prefix + 'report.json'])
        controls = report['controls']
        if (report['status'] != 'observed' or report['clean_shutdown'] is not True or
                report['owned_container_removed'] is not True or report['save_confirmed'] is not True or
                report['world_identity'] != dict(seed=case['seed'], api='2.11.0-beta', players=0) or
                controls['image_id'] != IMAGE or controls['script_api'] != '2.11.0-beta' or
                controls['seed'] != case['seed'] or
                controls['manifest_sha256'] != hashlib.sha256(data['membership-columns/frozen.json']).hexdigest() or
                controls['observer_sha256'] != hashlib.sha256(data['observer/membership-columns-observer.js']).hexdigest() or
                report['copied_world']['source_unchanged'] is not True):
            raise ValueError('Invalid column audit identity')
        if (hashlib.sha256(data[prefix + 'server.properties']).hexdigest() != controls['settings_sha256'] or
                not re.search(rb'\bVersion: 1\.26\.52\.3(?:\s|$)', data[prefix + 'console.log'])):
            raise ValueError('Column settings/build mismatch')
        emitted = [_json(line.split(b'TARGET_RESULT ', 1)[1])
                   for line in data[prefix + 'console.log'].splitlines() if b'TARGET_RESULT ' in line]
        if emitted != [report['target_result']]:
            raise ValueError('Column report differs from raw console result')
        observed = report['target_result']['membershipColumns']
        if [[c['x'], c['z']] for c in observed] != case['columns']:
            raise ValueError('Observed columns differ from frozen input')
        for column in observed:
            last = -65
            for interval in column['intervals']:
                if (type(interval['from']) is not int or type(interval['to']) is not int or
                        interval['from'] != last + 1 or not last < interval['to'] <= 319 or
                        not isinstance(interval['structures'], list) or
                        any(not isinstance(name, str) for name in interval['structures'])):
                    raise ValueError('Invalid/incomplete membership interval')
                last = interval['to']
            if last != 319:
                raise ValueError('Incomplete vertical membership coverage')
            columns.append(dict(seed=case['seed'], **column,
                interpretation='Complete Y column only; not an exhaustive horizontal structure footprint'))
    prefix = 'membership-volumes/world-0/'
    volume_case = _json(data['membership-volumes/frozen.json'])[0]
    volume_report = _json(data[prefix + 'report.json'])
    controls = volume_report['controls']
    if (volume_report['status'] != 'observed' or volume_report['clean_shutdown'] is not True or
            volume_report['owned_container_removed'] is not True or volume_report['save_confirmed'] is not True or
            volume_report['world_identity'] != dict(seed=volume_case['seed'], api='2.11.0-beta', players=0) or
            controls['image_id'] != IMAGE or controls['script_api'] != '2.11.0-beta' or
            controls['manifest_sha256'] != hashlib.sha256(data['membership-volumes/frozen.json']).hexdigest() or
            controls['observer_sha256'] != hashlib.sha256(data['observer/membership-volume-observer.js']).hexdigest() or
            hashlib.sha256(data[prefix + 'server.properties']).hexdigest() != controls['settings_sha256'] or
            volume_report['copied_world']['source_unchanged'] is not True):
        raise ValueError('Invalid full-chunk membership identity')
    log = data[prefix + 'console.log']
    if not re.search(rb'\bVersion: 1\.26\.52\.3(?:\s|$)', log):
        raise ValueError('Missing volume build line')
    emitted = [_json(line.split(b'TARGET_RESULT ', 1)[1]) for line in log.splitlines() if b'TARGET_RESULT ' in line]
    if emitted != [volume_report['target_result']]:
        raise ValueError('Volume report differs from raw console result')
    volumes = volume_report['target_result']['membershipVolumes']
    expected_bounds = [[x // 16 * 16, -64, z // 16 * 16, x // 16 * 16 + 16, 320, z // 16 * 16 + 16]
                       for x, z in volume_case['columns']]
    if ([v['bounds'] for v in volumes] != expected_bounds or
            volume_report['target_result']['volumeReads'] != len(volumes) * 98304):
        raise ValueError('Volume bounds/read budget differ')
    for volume in volumes:
        if (volume['evaluatedPositions'] != 98304 or not isinstance(volume['counts'], dict) or
                any(not isinstance(k, str) or type(v) is not int or not 1 <= v <= 98304
                    for k, v in volume['counts'].items())):
            raise ValueError('Invalid membership volume counts')
    return dict(revision='predictor-resolution-report-v1', game_build=BUILD,
        persistence=coverage, structure_membership=membership,
        structure_presence=[row for row in membership if row['status'] == 'present'],
        structure_membership_columns=columns,
        structure_membership_volumes=dict(seed=volume_case['seed'], volumes=volumes,
            interpretation='Exhaustive membership queries in these four chunks only; member-block totals are not structure counts.'),
        locate_disagreements=locate_disagreements,
        limitations=manifest['limitations'],
        cave_verdict='Name alias corrected; native full-block cave interpolation remains unresolved.',
        catalog_refresh='Exact-count promotion remains gated; no unsupported counts changed.')
