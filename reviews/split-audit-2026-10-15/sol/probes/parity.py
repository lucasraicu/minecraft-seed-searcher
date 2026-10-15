"""Prepared before/after parity checks; do not run while heavy work is paused.

Positive native Mansion calls are checked separately because NBFixture bypasses
the vendor viability implementation that the experimental arm changes.
"""
import argparse
import ctypes as ct
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
WORK = Path('/tmp/minecraft-sol-audit-20261015')
OUT = ROOT / 'reviews/split-audit-2026-10-15/sol'


class Component:
    def __init__(self, prototype):
        self.lib = ct.CDLL(prototype.identity['extension'])
        declarations = {
            'ss_create': (ct.c_void_p, [ct.c_uint64]),
            'ss_destroy': (None, [ct.c_void_p]),
            'ss_scan': (ct.c_int, [ct.c_void_p, *([ct.c_int] * 6), ct.POINTER(ct.c_int), ct.c_int]),
            'ss_filter_starts': (ct.c_int, [ct.c_void_p, ct.c_int, ct.POINTER(ct.c_int),
                                          ct.c_int, ct.POINTER(ct.c_int)]),
            'ss_biome': (ct.c_int, [ct.c_void_p, *([ct.c_int] * 4)]),
        }
        for name, (result, arguments) in declarations.items():
            function = getattr(self.lib, name)
            function.restype = result
            function.argtypes = arguments

    def inspect(self, seed, types):
        ctx = self.lib.ss_create(seed & ((1 << 64) - 1))
        if not ctx:
            raise MemoryError('Component context creation failed')
        try:
            output = {}
            # This order deliberately puts fresh RNG consumers after Mansion checks.
            for name in ('mansion', 'stronghold', 'outpost', 'fortress', 'bastion'):
                bounds = (-562, -562, 561, 561) if name in ('fortress', 'bastion') else (-2000, -2000, 1999, 1999)
                points = (ct.c_int * 8192)()
                n = self.lib.ss_scan(ctx, types[name], *bounds, 0, points, 4096)
                if n < 0:
                    raise RuntimeError(f'{name} component scan returned {n}')
                flags = (ct.c_int * max(1, n))()
                code = self.lib.ss_filter_starts(ctx, types[name], points, n, flags)
                if code:
                    raise RuntimeError(f'{name} component filter returned {code}')
                starts = [(points[2*i], points[2*i+1]) for i in range(n)]
                row = {'raw': starts, 'viable': [p for i,p in enumerate(starts) if flags[i]]}
                if name == 'mansion':
                    row['y63_biomes'] = [self.lib.ss_biome(ctx, 0, x, 63, z)
                                          for x,z in row['viable']]
                output[name] = row
            return output
        finally:
            self.lib.ss_destroy(ctx)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-heavy', action='store_true')
    parser.add_argument('--arms', nargs='+', default=['control', 'no-surface-init'])
    parser.add_argument('--chunk', type=int, default=16)
    parser.add_argument('--natural-count', type=int, default=256)
    parser.add_argument('--component-count', type=int, default=2000)
    args = parser.parse_args()
    if not args.allow_heavy:
        parser.error('Heavy work is paused pending user release')
    if len(args.arms) < 2 or not (1 <= args.natural_count <= 16384
                                 and 1 <= args.component_count <= 10000):
        parser.error('Use at least two arms and bounded positive cohort counts')
    from seed_search.realm.native_batch import Prototype, semantic_record
    from seed_search.realm.config import dynamic_blueprint_config
    from seed_search.backend import structure_type
    from seed_search.seeds import seed_from_index
    prototypes = {arm: Prototype(WORK / arm / f'chunk-{args.chunk}' / 'optimized',
                                  dynamic_blueprint_config()) for arm in args.arms}
    seeds = [seed_from_index(i, 2026101401) for i in range(60000000, 60000000+args.natural_count)]
    rows = []
    for retention in ('full', 'survivors'):
        for fixtures in (False, True):
            inputs = list(range(40)) if fixtures else seeds
            kwargs = dict(fixtures=[(0, 0, k % 35 - 1) for k in inputs]) if fixtures else {}
            fingerprints = []
            for arm, p in prototypes.items():
                with p.sweep(inputs, 4, retention=retention, **kwargs) as batch:
                    start_index = 0 if fixtures else 60000000
                    records = (batch.records(start_index) if retention == 'full'
                               else batch.retained_records(start_index))
                    semantic = [semantic_record(r) for r in records]
                    fp = fingerprint(semantic)
                    fingerprints.append(fp)
                    rows.append(dict(arm=arm, retention=retention, synthetic=fixtures,
                                     count=len(inputs), fingerprint=fp,
                                     retained_anchors=sum(len(r['anchors']) for r in records)))
            if len(set(fingerprints)) != 1:
                raise RuntimeError(f'Record parity mismatch: {retention}, fixtures={fixtures}')
    components = {arm: Component(p) for arm,p in prototypes.items()}
    types = {name: structure_type(name) for name in
             ('mansion', 'stronghold', 'outpost', 'fortress', 'bastion')}
    positive = 0
    positives = []
    hashes = {arm: hashlib.sha256() for arm in prototypes}
    for index in range(61000000, 61000000+args.component_count):
        seed = seed_from_index(index, 2026101401)
        reference = None
        for arm, component in components.items():
            result = component.inspect(seed, types)
            if reference is None:
                reference = result
                if result['mansion']['viable']:
                    positive += 1
                    positives.append({'index': index, 'seed': str(seed),
                                      'mansion': result['mansion']})
            elif result != reference:
                raise RuntimeError(f'Native component/interleaving mismatch: {arm}, index={index}, seed={seed}')
            hashes[arm].update(fingerprint(result).encode())
    report = dict(status='record and component comparisons passed', arms=args.arms,
                  record_checks=rows, component_count=args.component_count,
                  component_fingerprints={arm:h.hexdigest() for arm,h in hashes.items()},
                  positive_native_mansion_seeds=positive, positive_mansion_inputs=positives,
                  coverage_gap=None if positive else 'No positive natural Mansion check observed; positive coverage remains required',
                  limitations=['NBFixture bypasses vendor viability',
                               'before/after parity does not certify baseline correctness',
                               'public post-call MT state is not compared or promised identical'])
    path = OUT / ('parity-' + '-vs-'.join(args.arms) + '.json')
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'positive_mansion_inputs'}, indent=2))


if __name__ == '__main__':
    main()
