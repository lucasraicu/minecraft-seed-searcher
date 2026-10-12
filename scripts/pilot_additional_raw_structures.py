"""Bounded diagnostic: extra raw families across an envelope versus one center.

This changes no eligibility requirements. A fixed-center failure cannot reject
an entire lower32 family when other Stronghold centers remain possible.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

from seed_search.backend import raw_layout
from seed_search.realm.raw import FAMILIES, OW_ENVELOPE, NETHER_ENVELOPE
from seed_search.realm.bounds import native_bounds, square, nether_square
from seed_search.seeds import seed_from_index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=2048)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.count <= 10000:
        parser.error('Use a bounded 1–10000 layout pilot')
    lows = []
    index = 100000
    while len(lows) < args.count:
        low = seed_from_index(index, 1102026) & 0xffffffff
        if low not in lows:
            lows.append(low)
        index += 1
    extras = ('monument', 'outpost', 'shipwreck', 'ruined_portal')
    counts = {scope: {'base_pass': 0, 'all_extra_pass': 0,
                     'extra_pass': {name: 0 for name in extras},
                     'base_and_extra_pass': {name: 0 for name in extras}}
              for scope in ('conservative_envelope', 'fixed_center_origin')}
    start = time.perf_counter()
    for low in lows:
        envelope_base = all(bool(raw_layout(low, name, bounds)) for name, bounds in FAMILIES)
        # This diagnostic deliberately uses an arbitrary center, without
        # asserting that a Stronghold exists there for any upper32 sibling.
        ow, nether = native_bounds(square((0, 0), 1536)), native_bounds(nether_square((0, 0), 896))
        fixed_base = all(bool(raw_layout(low, name, bounds)) for name, bounds in
                         (('village', ow), ('ancient_city', ow),
                          ('fortress', nether), ('bastion', nether), FAMILIES[-1]))
        for scope, bounds, base in (('conservative_envelope', OW_ENVELOPE, envelope_base),
                                    ('fixed_center_origin', ow, fixed_base)):
            positives = {name: bool(raw_layout(low, name, bounds)) for name in extras}
            row = counts[scope]
            row['base_pass'] += base
            row['all_extra_pass'] += base and all(positives.values())
            for name, positive in positives.items():
                row['extra_pass'][name] += positive
                row['base_and_extra_pass'][name] += base and positive
    for row in counts.values():
        row['base_reject_percent'] = 100 * (1 - row['base_pass'] / args.count)
        row['all_extra_reject_percent'] = 100 * (1 - row['all_extra_pass'] / args.count)
        row['additional_rejected_layouts'] = row['base_pass'] - row['all_extra_pass']
    result = {'version': 'additional-raw-family-pilot-v1', 'distinct_lower32': len(lows),
              'low32_manifest': lows, 'manifest_sha256': hashlib.sha256(json.dumps(lows).encode()).hexdigest(),
              'seconds': time.perf_counter() - start, 'extra_families': list(extras),
              'bounds': {'ow_envelope': OW_ENVELOPE, 'nether_envelope': NETHER_ENVELOPE,
                         'fixed_ow': ow, 'fixed_nether': nether}, 'results': counts,
              'interpretation': 'Raw candidate presence only. No biome viability, upper32, '
                                'Stronghold anchor, joint-center coverage or verified-world yield measured.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'low32_manifest'}, indent=2))


if __name__ == '__main__':
    main()
