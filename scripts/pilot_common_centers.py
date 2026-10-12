"""Bounded shadow pilot of envelope presence versus exact common-center capacity.

No production requirements, raw adapter eligibility or ranking are changed.
All placements are predictor candidates, not actual structure existence.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from seed_search import _native
from seed_search.backend import Backend
from seed_search.realm.bounds import contains, nether_square, square
from seed_search.realm.raw import CENTER_BOUNDS, OW_ENVELOPE, NETHER_ENVELOPE, center_rectangle, joint_center_witness
from seed_search.seeds import seed_from_index

ROOT = Path(__file__).resolve().parents[1]
BASE = ('village', 'ancient_city', 'fortress', 'bastion')
FEATURES = ('desert_pyramid', 'jungle_temple', 'swamp_hut', 'igloo')
NETHER = ('fortress', 'bastion', 'ruined_portal_nether')
OW = ('village', 'ancient_city', 'ruined_portal', 'shipwreck', 'monument',
      'outpost', 'desert_pyramid', 'ocean_ruin', 'mansion', 'buried_treasure')
GROUPS = OW + NETHER
PROFILES = {
    'current_four': dict.fromkeys(BASE, 1),
    'plus_mansion_outpost': dict.fromkeys(BASE + ('mansion', 'outpost'), 1),
    'expanded_mt_presence': dict.fromkeys(GROUPS, 1),
    'expanded_mt_feature_capacity': {**dict.fromkeys(GROUPS, 1), 'desert_pyramid': 4},
}


def rectangle_profiles(groups, profiles, domain):
    """Exact inclusive integer-center area/witness using compressed event slabs.

Each rectangle contributes one unit of capacity to its group. Repeated clipped
rectangles are retained because they can represent distinct placement slots.
No center sampling, geometric approximation or downsampling is used.
"""
    x0, z0, x1, z1 = domain
    if x0 > x1 or z0 > z1:
        raise ValueError('Empty center domain')
    names = tuple(groups)
    index = {name: i for i, name in enumerate(names)}
    clipped = []
    edges = {z0, z1 + 1}
    for name in names:
        for a, b, c, d in groups[name]:
            a, b, c, d = max(a, x0), max(b, z0), min(c, x1), min(d, z1)
            if a <= c and b <= d:
                clipped.append((index[name], a, b, c, d))
                edges.update((b, d + 1))
    zs = sorted(edges)
    zi = {z: i for i, z in enumerate(zs)}
    widths = np.diff(zs).astype(np.int64)
    counts = np.zeros((len(names), len(widths)), dtype=np.int32)
    events = defaultdict(list)
    events[x0]; events[x1 + 1]
    for group, a, b, c, d in clipped:
        events[a].append((group, zi[b], zi[d + 1], 1))
        events[c + 1].append((group, zi[b], zi[d + 1], -1))
    compiled = {}
    for name, requirements in profiles.items():
        if not requirements or any(v < 1 for v in requirements.values()):
            raise ValueError('Profiles need positive capacities')
        compiled[name] = (np.array([index[n] for n in requirements]),
                          np.array(list(requirements.values()), dtype=np.int32)[:, None])
    result = {n: {'area': 0, 'witness': None} for n in profiles}
    xs = sorted(events)
    for x, next_x in zip(xs, xs[1:]):
        for group, lo, hi, delta in events[x]:
            counts[group, lo:hi] += delta
        for name, (indices, capacities) in compiled.items():
            valid = np.all(counts[indices] >= capacities, axis=0)
            length = int(np.dot(valid, widths))
            if length:
                result[name]['area'] += length * (next_x - x)
                if result[name]['witness'] is None:
                    result[name]['witness'] = [x, zs[int(np.flatnonzero(valid)[0])]]
    total = (x1 - x0 + 1) * (z1 - z0 + 1)
    for row in result.values():
        row['fraction'] = row['area'] / total
    return result


def point_feasible(groups, requirements, center):
    return all(sum(a <= center[0] <= c and b <= center[1] <= d
                   for a, b, c, d in groups[name]) >= count
               for name, count in requirements.items())


def placement_groups(layouts):
    return {name: [r for p in layouts[name]
                   if (r := center_rectangle(p, name in NETHER)) is not None]
            for name in GROUPS}


def actual_membership(layouts, requirements, center):
    return all(sum(contains(p, nether_square(center, 896) if name in NETHER else square(center, 1536))
                   for p in layouts[name]) >= count for name, count in requirements.items())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=2048)
    parser.add_argument('--anchor-low-count', type=int, default=128)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.count <= 4096 or not 0 <= args.anchor_low_count <= args.count:
        parser.error('Use 1–4096 layouts and at most count anchor layouts')
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / 'layouts.jsonl').exists():
        parser.error('Choose a fresh output directory')
    keys = (11102026, 11102027, 11102028)
    manifest = []
    seen = set()
    for i in range(args.count):
        key = keys[i % len(keys)]
        at = 300000 + i // len(keys)
        low = seed_from_index(at, key) & 0xffffffff
        while low in seen:
            at += 100000
            low = seed_from_index(at, key) & 0xffffffff
        seen.add(low)
        manifest.append({'low32': low, 'key': key, 'index': at})
    identity = {
        'version': 'common-center-pilot-v1', 'count': args.count, 'manifest': manifest,
        'native_sha256': sha(_native.__file__), 'script_sha256': sha(__file__),
        'source_sha256': {n: sha(ROOT / n) for n in
            ('native/bridge.c', 'vendor/cubiomes-bedrock/finders.c',
             'vendor/cubiomes-bedrock/finders.h', 'vendor/cubiomes-bedrock/mt.h',
             'src/seed_search/realm/raw.py', 'src/seed_search/realm/bounds.py')},
        'center_domain': CENTER_BOUNDS, 'ow_envelope': OW_ENVELOPE,
        'nether_envelope': NETHER_ENVELOPE, 'ow_side': 1536, 'nether_side': 896,
        'profiles': PROFILES,
        'limits': 'Exact candidate placement only; common center need not be a Stronghold. '
                  'Expanded profiles are shadow hypotheses, not new search requirements. '
                  'No full64 biome viability, terrain or actual-world acquisition measured.',
    }
    (args.output / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    all_rows = []
    anchor_rows = []
    timings = defaultdict(float)
    start = time.perf_counter()
    with (args.output / 'layouts.jsonl').open('w') as records:
        for i, item in enumerate(manifest):
            low = item['low32']
            t = time.perf_counter()
            with Backend(low) as backend:
                layouts = {name: backend.structures(name, NETHER_ENVELOPE if name in NETHER else OW_ENVELOPE, viable=False)
                           for name in GROUPS}
                if i < 32:
                    # Shared-slot capacity relies on identical candidate placement.
                    assert all(backend.structures(n, OW_ENVELOPE, viable=False) == layouts['desert_pyramid']
                               for n in FEATURES[1:])
            timings['raw_layout_seconds'] += time.perf_counter() - t
            t = time.perf_counter()
            groups = placement_groups(layouts)
            timings['rectangle_preparation_seconds'] += time.perf_counter() - t
            envelope = {name: all(len(layouts[n]) >= required for n, required in profile.items())
                        for name, profile in PROFILES.items()}
            fixed = {name: actual_membership(layouts, profile, (0, 0)) for name, profile in PROFILES.items()}
            t = time.perf_counter()
            common = rectangle_profiles(groups, PROFILES, CENTER_BOUNDS)
            timings['joint_solver_seconds'] += time.perf_counter() - t
            for name, profile in PROFILES.items():
                row = common[name]
                assert not row['area'] or envelope[name]
                if row['witness'] is not None:
                    assert point_feasible(groups, profile, row['witness'])
                    assert actual_membership(layouts, profile, row['witness'])
                assert not fixed[name] or row['area']
            assert common['expanded_mt_feature_capacity']['area'] <= common['expanded_mt_presence']['area']
            assert common['expanded_mt_presence']['area'] <= common['plus_mansion_outpost']['area'] <= common['current_four']['area']
            if i < 64:
                expected = joint_center_witness([layouts[n] for n in BASE])
                assert (expected is not None) == bool(common['current_four']['area'])
            row = {**item, 'envelope': envelope, 'fixed_origin': fixed, 'common': common}
            if i < args.anchor_low_count:
                t = time.perf_counter()
                for upper in (1, 0x12345678, 0x89abcdef, 0xffffffff):
                    unsigned = (upper << 32) | low
                    signed = unsigned if unsigned < 1 << 63 else unsigned - (1 << 64)
                    with Backend(signed) as backend:
                        anchors = backend.structures('stronghold', CENTER_BOUNDS, viable=True)
                    passed = {name: sum(point_feasible(groups, profile, c) for c in anchors)
                              for name, profile in PROFILES.items()}
                    for c in anchors:
                        assert all(point_feasible(groups, p, c) == actual_membership(layouts, p, c)
                                   for p in PROFILES.values())
                    anchor_rows.append({'low32': low, 'upper32': upper, 'seed': str(signed),
                                        'anchor_count': len(anchors), 'profile_raw_positive_anchors': passed})
                timings['stronghold_anchor_diagnostic_seconds'] += time.perf_counter() - t
            all_rows.append(row)
            records.write(json.dumps(row, separators=(',', ':')) + '\n')
            if (i + 1) % 64 == 0:
                records.flush()
                print(json.dumps({'completed': i + 1, 'count': args.count,
                                  'elapsed_seconds': time.perf_counter() - start}), flush=True)
    timings['wall_seconds'] = time.perf_counter() - start
    (args.output / 'anchors.json').write_text(json.dumps(anchor_rows, indent=2) + '\n')
    cohorts = {'all': all_rows, **{str(k): [r for r in all_rows if r['key'] == k] for k in keys}}
    summary = {}
    for key, rows in cohorts.items():
        if not rows:
            continue
        summary[key] = {'count': len(rows), 'profiles': {}}
        for name in PROFILES:
            fractions = [r['common'][name]['fraction'] for r in rows]
            env = sum(r['envelope'][name] for r in rows)
            joint = sum(bool(r['common'][name]['area']) for r in rows)
            summary[key]['profiles'][name] = {
                'envelope_pass': env, 'common_center_pass': joint,
                'fixed_origin_pass': sum(r['fixed_origin'][name] for r in rows),
                'additional_joint_rejections': env - joint,
                'envelope_reject_percent': 100 * (1 - env / len(rows)),
                'common_center_reject_percent': 100 * (1 - joint / len(rows)),
                'mean_center_fraction': float(np.mean(fractions)),
                'median_center_fraction': float(np.median(fractions)),
            }
    anchors = {'full64_inputs': len(anchor_rows), 'distinct_lower32': args.anchor_low_count,
               'predicted_anchors': sum(r['anchor_count'] for r in anchor_rows),
               'full64_inputs_without_predicted_anchor': sum(not r['anchor_count'] for r in anchor_rows),
               'profiles': {name: {
                    'raw_positive_anchors': sum(r['profile_raw_positive_anchors'][name] for r in anchor_rows),
                    'inputs_with_raw_positive_anchor': sum(bool(r['profile_raw_positive_anchors'][name]) for r in anchor_rows),
                } for name in PROFILES},
               'limits': 'Predicted Stronghold centers only; missing anchors are unresolved. '
                         'Extra-family viability and actual structure existence were not evaluated.'}
    report = {'identity': {k: v for k, v in identity.items() if k != 'manifest'},
              'timings': dict(timings), 'cohorts': summary, 'anchor_diagnostic': anchors,
              'integrity': {'layout_rows': len(all_rows), 'distinct_lower32': len(seen),
                            'legacy_joint_parity_layouts': min(args.count, 64),
                            'shared_feature_parity_layouts': min(args.count, 32),
                            'witness_membership_and_monotonicity': 'PASS'},
              'files': {n: sha(args.output / n) for n in ('identity.json', 'layouts.jsonl', 'anchors.json')}}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
