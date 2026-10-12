"""Source-backed candidate-center superset pilot, subordinate to raw-model accuracy.

MC_26_50 ss_scan emits regional Strongholds plus three nextVillageStronghold
results. The latter always use a raw Village candidate shifted by (-4,-4),
selected through full64 biome viability. Regional positions and Village raw
positions use uint32 MT seeds. This superset retains every such raw Village,
including ones unreachable by the three-Stronghold iteration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import time

from seed_search.backend import Backend
from seed_search import _native
from seed_search.realm.raw import CENTER_BOUNDS, OW_ENVELOPE, NETHER_ENVELOPE
from scripts.pilot_common_centers import GROUPS, NETHER, PROFILES, placement_groups


def possible_centers(backend, villages):
    x0, z0, x1, z1 = CENTER_BOUNDS
    centers = {(x - 4, z - 4) for x, z in villages
               if x0 <= x - 4 <= x1 and z0 <= z - 4 <= z1}
    # Same regional halo as ss_scan, followed by exact discovery membership.
    for rx in range(x0 // 3200 - 1, x1 // 3200 + 2):
        for rz in range(z0 // 3200 - 1, z1 // 3200 + 2):
            point = backend.attempt('stronghold', rx, rz)
            if point is not None and x0 <= point[0] <= x1 and z0 <= point[1] <= z1:
                centers.add(point)
    return sorted(centers)


def candidate_profiles(groups, centers):
    maximum = {name: max(p.get(name, 0) for p in PROFILES.values()) for name in GROUPS}
    passing = dict.fromkeys(PROFILES, 0)
    witnesses = dict.fromkeys(PROFILES)
    for center in centers:
        counts = {}
        for name, rectangles in groups.items():
            count = 0
            for a, b, c, d in rectangles:
                if a <= center[0] <= c and b <= center[1] <= d:
                    count += 1
                    if count >= maximum[name]:
                        break
            counts[name] = count
        for name, requirements in PROFILES.items():
            if all(counts[n] >= capacity for n, capacity in requirements.items()):
                passing[name] += 1
                if witnesses[name] is None:
                    witnesses[name] = list(center)
    return {name: {'candidate_centers_pass': count, 'witness': witnesses[name]}
            for name, count in passing.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--count', type=int, default=2048)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    identity = json.loads((args.input / 'identity.json').read_text())
    main_report = json.loads((args.input / 'report.json').read_text())
    assert identity['native_sha256'] == hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest()
    for source, digest in identity['source_sha256'].items():
        assert hashlib.sha256((Path(__file__).resolve().parents[1] / source).read_bytes()).hexdigest() == digest
    all_centers = {r['low32']: r for r in map(json.loads, (args.input / 'layouts.jsonl').read_text().splitlines())}
    items = identity['manifest'][:args.count]
    if not 1 <= args.count <= len(identity['manifest']):
        parser.error('Count must fit the completed common-center pilot')
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    anchor_checks = 0
    t = time.perf_counter()
    for i, item in enumerate(items):
        low = item['low32']
        with Backend(low) as backend:
            layouts = {n: backend.structures(n, NETHER_ENVELOPE if n in NETHER else OW_ENVELOPE, False)
                       for n in GROUPS}
            candidates = possible_centers(backend, layouts['village'])
        profile = candidate_profiles(placement_groups(layouts), candidates)
        for name, result in profile.items():
            assert not result['candidate_centers_pass'] or all_centers[low]['common'][name]['area']
        if i < 128:
            for upper in (1, 0x12345678, 0x89abcdef, 0xffffffff):
                unsigned = (upper << 32) | low
                signed = unsigned if unsigned < 1 << 63 else unsigned - (1 << 64)
                with Backend(signed) as backend:
                    actual = backend.structures('stronghold', CENTER_BOUNDS, True)
                assert set(actual).issubset(candidates), (low, upper, actual, candidates)
                anchor_checks += len(actual)
        rows.append({**item, 'possible_centers': len(candidates), 'profiles': profile})
        if (i + 1) % 256 == 0:
            print(json.dumps({'completed': i + 1, 'count': len(items), 'seconds': time.perf_counter() - t}), flush=True)
    seconds = time.perf_counter() - t
    summary = {}
    for name in PROFILES:
        envelope_pass = sum(all_centers[r['low32']]['envelope'][name] for r in rows)
        continuous_pass = sum(bool(all_centers[r['low32']]['common'][name]['area']) for r in rows)
        candidate_pass = sum(bool(r['profiles'][name]['candidate_centers_pass']) for r in rows)
        summary[name] = {'envelope_pass': envelope_pass, 'unrestricted_integer_center_pass': continuous_pass,
                         'possible_stronghold_center_pass': candidate_pass,
                         'additional_rejections_vs_unrestricted': continuous_pass - candidate_pass,
                         'possible_center_reject_percent': 100 * (1 - candidate_pass / len(rows)),
                         'mean_fraction_of_candidate_centers_passing': sum(
                              r['profiles'][name]['candidate_centers_pass'] / r['possible_centers']
                              if r['possible_centers'] else 0 for r in rows) / len(rows)}
    report = {'count': len(rows), 'profiles': summary, 'seconds': seconds,
              'candidate_count_min': min(r['possible_centers'] for r in rows),
              'candidate_count_max': max(r['possible_centers'] for r in rows),
              'candidate_count_mean': sum(r['possible_centers'] for r in rows) / len(rows),
              'full64_superset_parity_inputs': min(len(rows), 128) * 4,
              'full64_predicted_anchors_checked': anchor_checks,
              'native_sha256': main_report['identity']['native_sha256'],
              'parent_report_sha256': hashlib.sha256((args.input / 'report.json').read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'limits': __doc__ + '\nThis is a predictor superset, not full64 eligibility or actual-world recall.'}
    (args.output / 'layouts.json').write_text(json.dumps(rows, indent=2) + '\n')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
