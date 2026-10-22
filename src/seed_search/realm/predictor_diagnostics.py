"""Read-only replay of pinned predictor/BDS regressions.

This module evaluates saved API observations, not physical structure completeness,
surface coverage or population accuracy. It never imports or calls native search.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

REVISION = 'predictor-regressions-v1'
BUILD = '1.26.52.3'
IMAGE = 'sha256:cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8'
LOCATE = re.compile(r'The nearest minecraft:([a-z_]+) is at block (-?\d+), \(y\?\), (-?\d+)')
MAX_FILE = 2 << 20
MAX_BUNDLE = 8 << 20
COMMANDS = {
    'trial_chamber': 'trial_chambers', 'outpost': 'pillager_outpost',
    'desert_pyramid': 'temple', 'jungle_temple': 'temple', 'swamp_hut': 'temple',
    'igloo': 'temple', 'ruined_portal_nether': 'ruined_portal',
    'bastion': 'bastion_remnant', 'ocean_ruin': 'ruins',
}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def _json(data):
    def bad_constant(_):
        raise ValueError('Nonfinite JSON')
    return json.loads(data, object_pairs_hook=_pairs, parse_constant=bad_constant)


def _read(root, name):
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(p in ('.', '..') for p in path.parts) or '\\' in name:
        raise ValueError('Invalid fixture path')
    target = root
    for part in path.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError('Fixture symlinks are not supported')
    with target.open('rb') as handle:
        data = handle.read(MAX_FILE + 1)
    if len(data) > MAX_FILE:
        raise ValueError('Oversized fixture file')
    return data


def load_bundle(directory):
    """Validate bytes and game identity; checksums do not authenticate the source."""
    root = Path(directory)
    if root.is_symlink():
        raise ValueError('Fixture root cannot be a symlink')
    manifest = _json(_read(root, 'manifest.json'))
    if (manifest['revision'] != REVISION or manifest['game_build'] != BUILD or
            manifest['script_api'] != '2.10.0' or 'sha256:' + manifest['image_sha256'] != IMAGE or
            manifest['prediction_revision'] != 'cubiomes-bedrock-26.50'):
        raise ValueError('Unsupported fixture identity')
    files = manifest['files']
    if not isinstance(files, dict) or not 1 <= len(files) <= 64:
        raise ValueError('Invalid fixture inventory')
    data = {}
    total = 0
    for name, expected in files.items():
        raw = _read(root, name)
        total += len(raw)
        if total > MAX_BUNDLE:
            raise ValueError('Oversized fixture bundle')
        if len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
            raise ValueError('Fixture checksum mismatch: ' + name)
        data[name] = raw
    reports = []
    for name in manifest['reports']:
        report = _json(data[name + '/report.json'])
        settings = data[name + '/server.properties']
        controls = report['controls']
        seed = controls['seed']
        if (not isinstance(seed, str) or not re.fullmatch(r'-?\d+', seed) or
                not -(1 << 63) <= int(seed) < (1 << 63)):
            raise ValueError('Invalid signed seed')
        if (report['status'] != 'observed' or report['clean_shutdown'] is not True or
                report['owned_container_removed'] is not True or controls['image_id'] != IMAGE or
                report['world_identity']['seed'] != seed or report['world_identity']['api'] != '2.10.0' or
                controls['prediction']['seed'] != seed):
            raise ValueError('Report identity/cleanup mismatch')
        if ('level-seed=' + seed).encode() not in settings.splitlines():
            raise ValueError('Settings seed mismatch')
        if controls.get('settings_sha256', hashlib.sha256(settings).hexdigest()) != hashlib.sha256(settings).hexdigest():
            raise ValueError('Settings hash mismatch')
        if not re.search(rb'\bVersion: 1\.26\.52\.3(?:\s|$)', data[name + '/console.log']):
            raise ValueError('Missing observed game build')
        if any(batch['chunksAfterUnload'] != 0 for batch in report['biome_batches']):
            raise ValueError('Biome batch cleanup failure')
        reports.append(report)
    return manifest, data, reports


def comparison_rows(manifest, data, reports):
    """Bind every derived sampler row to its unchanged original API observation."""
    original = {}
    for report in reports:
        seed = report['controls']['seed']
        for batch in report['biome_batches']:
            for row in batch['rows']:
                key = (seed, row.get('dimension', 'overworld'), row['x'], row['y'], row['z'])
                original.setdefault(key, []).append(row)
    result = {}
    # Pilot and vertical files predate embedding the seed in every comparison row.
    pilot_seed = '-3509659830737203357'
    for label, name in manifest['comparisons'].items():
        doc = _json(data[name])
        rows = doc if isinstance(doc, list) else doc['rows']
        result[label] = []
        for row in rows:
            row = dict(row)
            row.setdefault('seed', pilot_seed)
            row.setdefault('dimension', 'overworld')
            key = (row['seed'], row['dimension'], row['x'], row['y'], row['z'])
            fields = ('id', 'predicted', 'loaded')
            if not any(all(raw.get(f) == row.get(f) for f in fields) for raw in original.get(key, [])):
                raise ValueError('Comparison row is not bound to an original observation')
            if 'error' in row or not isinstance(row.get('id'), str):
                raise ValueError('Comparison must retain a successful API observation')
            if any(not isinstance(row.get(f), str) for f in ('direct_quart', 'vendor_block')):
                raise ValueError('Missing sampler result')
            result[label].append(row)
    return result


def _canonical(name, aliases):
    name = name.removeprefix('minecraft:').lower().replace(' ', '_')
    return aliases.get(name, name)


def summarize_biomes(rows, aliases):
    matches = Counter()
    differences = []
    for row in rows:
        observed = _canonical(row['id'], aliases)
        for mode in ('direct_quart', 'vendor_block'):
            matches[mode] += _canonical(row[mode], aliases) == observed
        if _canonical(row['direct_quart'], aliases) != observed:
            differences.append(dict(row, observed_under_frozen_aliases=observed))
    return dict(points=len(rows), matches=dict(matches),
                harness_created_ticking_area=sum(r['loaded'] is True for r in rows),
                api_returned_without_harness_ticking_area=sum(r['loaded'] is False for r in rows),
                raw_quart_differences=differences)


def structure_rows(reports):
    """Parse exact references, preserving errors and discovery query roles."""
    rows = []
    for report in reports:
        for query in report['queries']:
            feature = query['kind'].split('.')[-1]
            command = COMMANDS.get(feature, feature)
            if query.get('command_id', command) != command:
                raise ValueError('Requested feature/command mismatch')
            found = [m for line in query['output'] if (m := LOCATE.search(line))]
            if len(found) > 1:
                raise ValueError('Ambiguous locate output')
            match = found[0] if found else None
            if match and match[1] != query.get('command_id', command):
                raise ValueError('Locate command mismatch')
            reported = [int(match[2]), int(match[3])] if match else None
            kind = query['kind']
            outcome = ('located_exact' if reported == query['query'] else 'coordinate_difference') if match else (
                'no_location' if any('No valid structure found' in s or 'Could not find' in s for s in query['output']) else 'error')
            rows.append(dict(seed=report['controls']['seed'], kind=kind,
                             dimension=query.get('dimension', 'overworld'),
                             query=query['query'], reported=reported, outcome=outcome,
                             raw_output=query['output']))
    return rows


def diagnostic_report(directory):
    manifest, data, reports = load_bundle(directory)
    comparisons = comparison_rows(manifest, data, reports)
    structures = structure_rows(reports)
    return dict(revision='predictor-diagnostic-report-v1', game_build=BUILD,
                prediction_revision=manifest['prediction_revision'],
                raw_structure_outcomes=dict(Counter(r['outcome'] for r in structures)),
                structure_roles={role: dict(Counter(r['outcome'] for r in structures
                                      if r['kind'].startswith(prefix)))
                                 for role, prefix in [('candidate_directed', 'structure.'),
                                                      ('independent_discovery', 'discovery.')]},
                coordinate_projections=summarize_projections(manifest, data, structures),
                biome_comparisons={name: summarize_biomes(rows, manifest['aliases'])
                                   for name, rows in comparisons.items()},
                loaded_field_semantics=manifest['loaded_field_semantics'],
                limitations=manifest['limitations'],
                verdict='No global sampler replacement justified; saved API comparisons only.')


def summarize_projections(manifest, data, structures):
    """Compare secondary navigation coordinates without altering raw outcomes."""
    from .structure_coordinates import project_navigation_reference
    candidates = Counter()
    matches = Counter()
    differences = []
    for row in structures:
        if not row['kind'].startswith('structure.'):
            continue
        feature = row['kind'].removeprefix('structure.')
        projected = project_navigation_reference(feature, *row['query'],
            prediction_revision=manifest['prediction_revision'], bds_build=manifest['game_build'],
            dimension=row['dimension'])
        if projected is None:
            continue
        candidates[feature] += 1
        navigation = [projected.navigation_x, projected.navigation_z]
        matches[feature] += navigation == row['reported']
        if navigation != row['reported']:
            differences.append(dict(seed=row['seed'], feature=feature, candidate=row['query'],
                                    projected_reference=navigation, reported=row['reported'],
                                    raw_outcome=row['outcome']))
    observations = _json(data['discovery-predictor-points.json'])['rows']
    discovery = []
    for obs in observations:
        feature, seed = obs['feature'], obs['seed']
        dimension = 'nether' if feature == 'fortress' else 'overworld'
        projected = [project_navigation_reference(feature, *point,
            prediction_revision=manifest['prediction_revision'], bds_build=manifest['game_build'],
            dimension=dimension) for point in obs['points']]
        if not projected or projected[0] is None:
            continue  # Stronghold stays unsupported, even where a -2 pattern fits.
        expected = {(p.navigation_x, p.navigation_z) for p in projected}
        actual = {tuple(r['reported']) for r in structures if r['seed'] == seed and
                  r['kind'] == 'discovery.structure.' + feature and r['reported'] is not None}
        discovery.append(dict(seed=seed, feature=feature, distinct_located=len(actual),
                              exact_projected_membership=len(actual & expected),
                              unmatched=[list(p) for p in sorted(actual - expected)]))
    return dict(candidate_directed={feature: dict(tested=n, exact_projected_reference=matches[feature])
                                    for feature, n in sorted(candidates.items())},
                independent_discovery=discovery,
                projected_differences=differences,
                scope='Navigation reference only; raw mismatch outcomes and prediction counts retained.')


def replay_probe(directory, executable):
    """Bounded isolated-helper replay; do not invoke native search or a game server."""
    manifest, data, reports = load_bundle(directory)
    groups = comparison_rows(manifest, data, reports)
    rows = [row for group in groups.values() for row in group]
    if not 1 <= len(rows) <= 4096:
        raise ValueError('Diagnostic probe input cap exceeded')
    text = ''.join(f"{r['seed']} {r['x']} {r['y']} {r['z']}\n" for r in rows)
    path = Path(executable).resolve(strict=True)
    process = subprocess.run([str(path)], input=text, capture_output=True, text=True,
                             timeout=30, check=True)
    lines = process.stdout.splitlines()
    if len(process.stdout) > 1 << 20 or len(lines) != len(rows):
        raise ValueError('Unexpected diagnostic probe output size')
    mismatches = []
    for index, (line, row) in enumerate(zip(lines, rows)):
        names = line.split()
        if len(names) != 2 or any(not re.fullmatch('[a-z_]+', n) for n in names):
            raise ValueError('Invalid diagnostic probe output')
        expected = [row['direct_quart'], row['vendor_block']]
        if names != expected:
            mismatches.append(dict(index=index, seed=row['seed'], xyz=[row['x'], row['y'], row['z']],
                                   expected=expected, actual=names))
    return dict(points=len(rows), identical_to_saved=not mismatches, differences=mismatches,
                binary_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                stdout_sha256=hashlib.sha256(process.stdout.encode()).hexdigest())
