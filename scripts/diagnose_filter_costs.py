"""Bounded, isolated Mineshaft/biome/lower32 diagnostics; never installs a build.

Run build, micro, baseline, raw, then audit. Outputs are additive under OUT.
The prototypes prove predictor parity only, not actual Bedrock generation.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/filter-cost-investigation-2026-10-10'
DECL = '''
int diag_mt_parity(const uint32_t *,int);
int diag_mineshaft(SeedContext *,int,int,int,int,int,int *,int,int *);
int diag_biomes(SeedContext *,const int *,int,int *,int,int);
int diag_region_size(int);
int diag_guaranteed_count(int,const int *);
int diag_raw_sweep(uint64_t,uint64_t,const int *,const int *,int,int,int *,uint64_t,int);
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, data):
    path = OUT / name
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


def probe():
    record = json.loads((OUT / 'build.json').read_text())
    spec = importlib.util.spec_from_file_location(record['module'], record['path'])
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def build():
    from cffi import FFI
    from seed_search.backend import lib, ffi
    number = 1
    while (OUT / ('native' if number == 1 else f'native-v{number}')).exists():
        number += 1
    folder = OUT / ('native' if number == 1 else f'native-v{number}')
    folder.mkdir(exist_ok=False)
    code = (ROOT / 'native/bridge.c').read_text() + '\n' + (ROOT / 'scripts/filter_cost_probe.c').read_text()
    header = (ROOT / 'native/bridge.h').read_text()
    (folder / 'bridge.c').write_text(code)
    (folder / 'bridge.h').write_text(header + '\n' + DECL)
    runtime = Path(ffi.string(lib.ss_openmp_library()).decode())
    os.environ['ARCHFLAGS'] = '-arch ' + platform.machine()
    flags = ['-O3', '-std=c11', '-fwrapv', '-Xpreprocessor', '-fopenmp']
    builder = FFI()
    builder.cdef('\n'.join(line for line in header.splitlines() if not line.startswith('#')) + DECL)
    name = '_filter_cost_private' + (f'_v{number}' if number > 1 else '')
    units = ['noise', 'biomes', 'layers', 'biomenoise', 'cave', 'generator', 'finders', 'util', 'quadbase', 'mt']
    builder.set_source(name, '#include "bridge.h"',
                       sources=[str(folder / 'bridge.c')] + [str(ROOT / f'vendor/cubiomes-bedrock/{u}.c') for u in units],
                       include_dirs=[str(folder), str(ROOT / 'vendor/cubiomes-bedrock'), str(runtime.parent.parent / 'include')],
                       extra_compile_args=flags, libraries=['m', 'omp'], library_dirs=[str(runtime.parent)],
                       extra_link_args=['-Wl,-rpath,' + str(runtime.parent)])
    begin = time.perf_counter()
    path = builder.compile(tmpdir=str(folder), verbose=False)
    record = {'path': path, 'module': name, 'flags': flags, 'architecture': platform.machine(),
                        'runtime': str(runtime), 'sha256': sha(path), 'bridge_sha256': sha(folder / 'bridge.c'),
                        'seconds': time.perf_counter() - begin, 'installed': False}
    if (OUT / 'build.json').exists():
        old = json.loads((OUT / 'build.json').read_text())
        save(f'build-v{number-1}.json', old)
    save('build.json', record)
    print('Private diagnostic build complete.', flush=True)


def points(center, side):
    from seed_search.realm.bounds import square
    bounds = square(center, side)
    x, z = np.meshgrid(np.arange(bounds[0], bounds[2], 64, dtype=np.int32),
                       np.arange(bounds[1], bounds[3], 64, dtype=np.int32))
    return np.ascontiguousarray(np.column_stack((x.ravel(), np.full(x.size, 63), z.ravel())), dtype=np.int32)


def mines(module, ctx, bounds, mode=None):
    cap = ((bounds[2] - bounds[0]) // 16 + 3) * ((bounds[3] - bounds[1]) // 16 + 3) + 20
    out = np.empty((cap, 2), dtype=np.int32)
    visited = module.ffi.new('int[1]')
    if mode is None:
        typ = module.lib.ss_structure_type(b'mineshaft')
        n = module.lib.ss_scan(ctx, typ, *bounds, 0, module.ffi.from_buffer('int[]', out), cap)
    else:
        n = module.lib.diag_mineshaft(ctx, *bounds, mode, module.ffi.from_buffer('int[]', out), cap, visited)
    assert n >= 0
    return out[:n].copy(), int(visited[0])


def biomes(module, ctx, pts, mode=0, threads=1):
    out = np.empty(len(pts), np.int32)
    assert module.lib.diag_biomes(ctx, module.ffi.from_buffer('int[]', pts), len(pts),
                                  module.ffi.from_buffer('int[]', out), mode, threads) == 0
    return out


def micro():
    from seed_search import _native as installed
    from seed_search.backend import biome_name
    from seed_search.realm.bounds import square, native_bounds
    from seed_search.realm.biomes import WOOD, canonical
    m = probe()
    rng = np.random.default_rng(20261010)
    mt_seeds = np.concatenate((np.array([0, 1, 2**31, 2**32-1], dtype=np.uint32),
                               rng.integers(0, 2**32, 4096, dtype=np.uint32)))
    assert m.lib.diag_mt_parity(m.ffi.from_buffer('uint32_t[]', mt_seeds), len(mt_seeds)) == 0
    seeds = [-1, 0, 1, 12345, 4294979641, -2**63, 2**63-1, -9048740180577658153]
    centers = [(0, 0), (-17, -9), (772, -1996), (2401, -2463)]
    sides = [32, 512, 1024, 1280, 1536, 2380, 2688]
    mine_rows, biome_rows, mismatches, early_rows, thread_rows = [], [], [], [], []
    count_parity = 0
    wood_ids = {}
    for seed in seeds:
        ctx = m.lib.ss_create(seed & (2**64-1))
        old = installed.lib.ss_create(seed & (2**64-1))
        try:
            for k, side in enumerate(sides):
                center = centers[k % len(centers)]
                bounds = native_bounds(square(center, side))
                reference, _ = mines(installed, old, bounds)
                row = {'seed': str(seed), 'side': side, 'center': center, 'starts': len(reference), 'timings': {}}
                for trial in range(3):
                    for label, module, handle, mode in ((
                        ('installed', installed, old, None), ('tight_scalar', m, ctx, 0),
                        ('vector4_full', m, ctx, 2), ('existence_only', m, ctx, 1)
                    ) if trial % 2 == 0 else (
                        ('existence_only', m, ctx, 1), ('vector4_full', m, ctx, 2),
                        ('tight_scalar', m, ctx, 0), ('installed', installed, old, None)
                    )):
                        begin = time.perf_counter()
                        values, visited = mines(module, handle, bounds, mode)
                        elapsed = time.perf_counter() - begin
                        if mode == 1:
                            assert bool(len(values)) == bool(len(reference))
                            assert not len(values) or np.array_equal(values, reference[:1])
                        else:
                            assert np.array_equal(reference, values), (seed, side, label)
                        count_parity += 1
                        row['timings'].setdefault(label, []).append(elapsed)
                        if mode is not None:
                            row.setdefault('chunks_visited', {})[label] = visited
                mine_rows.append(row)
            for side in (1280, 2380, 2688):
                pts = points(centers[seeds.index(seed) % len(centers)], side)
                ref = np.empty(len(pts), np.int32)
                assert installed.lib.ss_biome_points(old, 0, installed.ffi.from_buffer('int[]', pts),
                                                     len(pts), installed.ffi.from_buffer('int[]', ref)) == 0
                row = {'seed': str(seed), 'side': side, 'points': len(pts), 'timings': {}}
                for trial in range(3):
                    for label, mode in (('private_reference', 0), ('direct_exact', 1), ('climate_hint_untrusted', 2)):
                        begin = time.perf_counter()
                        values = biomes(m, ctx, pts, mode)
                        elapsed = time.perf_counter() - begin
                        if mode < 2:
                            assert np.array_equal(ref, values)
                        else:
                            bad = np.flatnonzero(ref != values)
                            row['hint_mismatches'] = len(bad)
                            if trial == 0:
                                mismatches.extend({'seed': str(seed), 'point': pts[i].tolist(),
                                                   'reference': int(ref[i]), 'hint': int(values[i])} for i in bad[:5])
                        row['timings'].setdefault(label, []).append(elapsed)
                biome_rows.append(row)
                for value in np.unique(ref):
                    wood_ids[int(value)] = next((f for f, names in WOOD.items()
                                                if canonical(biome_name(int(value))) in names), None)
                for order in ('row_major', 'spread'):
                    permutation = np.arange(len(pts)) if order == 'row_major' else np.random.default_rng(7).permutation(len(pts))
                    observed = set()
                    visited = 0
                    begin = time.perf_counter()
                    for at in range(0, len(pts), 16):
                        chunk = np.ascontiguousarray(pts[permutation[at:at+16]])
                        found = biomes(m, ctx, chunk, 1)
                        visited += len(chunk)
                        observed.update(wood_ids[int(v)] for v in found if wood_ids[int(v)] is not None)
                        if len(observed) >= 2:
                            break
                    elapsed = time.perf_counter() - begin
                    all_wood = {wood_ids[int(v)] for v in ref if wood_ids[int(v)] is not None}
                    assert (len(observed) >= 2) == (len(all_wood) >= 2)
                    early_rows.append({'seed': str(seed), 'side': side, 'order': order,
                                       'points': len(pts), 'points_visited': visited,
                                       'positive': len(observed) >= 2, 'seconds': elapsed})
                if side == 2688:
                    for trial in range(3):
                        for threads in (1, 4, 18):
                            begin = time.perf_counter()
                            values = biomes(m, ctx, pts, 1, threads)
                            elapsed = time.perf_counter() - begin
                            assert np.array_equal(ref, values)
                            thread_rows.append({'seed': str(seed), 'trial': trial, 'threads': threads, 'seconds': elapsed})
        finally:
            m.lib.ss_destroy(ctx)
            installed.lib.ss_destroy(old)
    # Same-low32 sibling checks are predictor diagnostics, not a new allowlist.
    sibling_rows = []
    for low in [0, 1, 12345, 2**32-1, *map(int, rng.integers(0, 2**32, 12, dtype=np.uint32))]:
        reference = None
        for high in (0, 1, 2**31, 2**32-1):
            ctx = installed.lib.ss_create((high << 32) | low)
            try:
                values, _ = mines(installed, ctx, (-649, -641, 630, 638))
                if reference is None:
                    reference = values
                assert np.array_equal(reference, values)
                sibling_rows.append({'low32': low, 'high32': high, 'starts': len(values)})
            finally:
                installed.lib.ss_destroy(ctx)
    save('micro.json', {'mt_first3_cases': len(mt_seeds), 'mineshaft_comparisons': count_parity,
                        'mineshaft': mine_rows, 'biomes': biome_rows, 'climate_hint_mismatch_examples': mismatches,
                        'early_wooded_gate': early_rows, 'biome_threads': thread_rows,
                        'mineshaft_siblings': sibling_rows, 'all_exact_arms_match': True,
                        'scope': 'Isolated predictor microbenchmarks; complete enumeration and existence are different output contracts.'})
    print('Micro diagnostics: exact arms matched; hint mismatches:', sum(r['hint_mismatches'] for r in biome_rows), flush=True)


def clean(result):
    excluded = {'stage_seconds', 'total_seconds', 'native_work', 'worker_peak_rss_bytes', 'worker_pid'}
    return {k: v for k, v in result.items() if k not in excluded}


def baseline():
    import seed_search.backend as backend
    from seed_search.realm.baseline import evaluate_seed
    from seed_search.realm.cli import load
    from seed_search.realm.runner import _seed
    from seed_search import _native as installed
    m = probe()
    production = load(str(ROOT / 'config/realm.yaml'))
    rows = []

    class FastBackend(backend.Backend):
        def structures(self, name, bounds, viable=True):
            if name != 'mineshaft':
                return super().structures(name, bounds, viable)
            values, _ = mines(m, self._handle(), bounds, 2)
            return sorted({tuple(map(int, p)) for p in values})

        def biome_points(self, pts, dimension=0):
            assert dimension == 0
            return biomes(m, self._handle(), np.ascontiguousarray(pts, dtype=np.int32), 1)

    # First reference the installed module, then compare identical complete
    # candidate payloads. The faster arms retain all coordinates and sampled IDs.
    for ow, nether, discovery in ((2688, 1024, 5000), (1280, 896, 4000)):
        cfg = copy.deepcopy(production)
        cfg['deployment'] = {'overworld_side_blocks': ow, 'nether_side_blocks': nether}
        cfg['discovery'] = {name: [-discovery//2, -discovery//2, discovery//2, discovery//2]
                            for name in ('overworld_bounds', 'nether_bounds')}
        references = {}
        for trial in range(3):
            arms = ('installed', 'private_reference', 'vector4_direct')
            if trial % 2:
                arms = tuple(reversed(arms))
            for arm in arms:
                module = installed if arm == 'installed' else m
                backend.ffi, backend.lib = module.ffi, module.lib
                factory = FastBackend if arm == 'vector4_direct' else backend.Backend
                outputs, exact_points, all_points = [], 0, 0
                by_seed_points = {}
                stage = {}
                cpu = time.process_time()
                begin = time.perf_counter()
                for index in range(96):
                    result = evaluate_seed(index, _seed(index, cfg['search']), cfg, backend_factory=factory)
                    payload = clean(result)
                    if index in references:
                        assert payload == references[index], (arm, ow, index)
                    else:
                        references[index] = payload
                    outputs.append(hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest())
                    for key, value in result['stage_seconds'].items():
                        stage[key] = stage.get(key, 0) + value
                    for candidate in result['anchors']:
                        if candidate['biomes'] is not None:
                            pts = points(candidate['stronghold'], ow)
                            cache = by_seed_points.setdefault(result['seed'], set())
                            all_points += len(pts)
                            for p in pts:
                                key = tuple(map(int, p))
                                exact_points += key in cache
                                cache.add(key)
                seconds = time.perf_counter() - begin
                cpu_seconds = time.process_time() - cpu
                # Python set instrumentation is deliberately identical in every
                # arm, and separately reported. This is not a production rate.
                rows.append({'overworld_side': ow, 'nether_side': nether, 'discovery_side': discovery,
                             'trial': trial, 'arm': arm, 'inputs': len(outputs), 'seconds': seconds,
                             'cpu_seconds': cpu_seconds, 'stage_seconds': stage,
                             'payload_sha256': hashlib.sha256('\n'.join(outputs).encode()).hexdigest(),
                             'biome_points': all_points, 'exact_repeated_biome_points': exact_points})
                print('Baseline', ow, trial, arm, round(seconds, 3), flush=True)
        assert len({r['payload_sha256'] for r in rows if r['overworld_side'] == ow}) == 1
    backend.ffi, backend.lib = installed.ffi, installed.lib
    save('baseline.json', {'rows': rows, 'all_payloads_match': True,
                           'scope': '96 identical inputs per geometry, three serial trials; includes identical cache instrumentation, no persistence/terrain/BDS.'})


def families(discovery, ow, nether):
    """Inclusive integer envelopes for any permitted integer Stronghold center."""
    lo, hi = -discovery//2, discovery//2-1
    overworld = (lo-ow//2, lo-ow//2, hi+ow//2-1, hi+ow//2-1)
    # A point p belongs when center is in (8*p-4*N, 8*p+4*N].
    nether_lo = -((-(lo-4*nether))//8)
    nether_hi = (hi+4*nether-1)//8
    nether_bounds = (nether_lo, nether_lo, nether_hi, nether_hi)
    return (('village', overworld), ('ancient_city', overworld),
            ('fortress', nether_bounds), ('bastion', nether_bounds), ('fortress', (lo, lo, hi, hi)))


def joint(layouts, discovery, ow, nether, include_overworld=True):
    lo, hi = -discovery//2, discovery//2-1
    groups = []
    for i, values in enumerate(layouts):
        if i < 2 and not include_overworld:
            continue
        half, scale = (ow//2, 1) if i < 2 else (4*nether, 8)
        group = []
        for x, z in values:
            rectangle = (max(lo, scale*x-half+1), max(lo, scale*z-half+1),
                         min(hi, scale*x+half), min(hi, scale*z+half))
            if rectangle[0] <= rectangle[2] and rectangle[1] <= rectangle[3]:
                group.append(rectangle)
        if not group:
            return None
        groups.append(group)
    events = sorted({r[0] for group in groups for r in group} | {r[2]+1 for group in groups for r in group})

    def merged(intervals):
        result = []
        for a, b in sorted(intervals):
            if result and a <= result[-1][1]+1:
                result[-1] = (result[-1][0], max(b, result[-1][1]))
            else:
                result.append((a, b))
        return result

    def intersect(a, b):
        i = j = 0
        result = []
        while i < len(a) and j < len(b):
            lower, upper = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
            if lower <= upper:
                result.append((lower, upper))
            if a[i][1] < b[j][1]:
                i += 1
            else:
                j += 1
        return result

    for x in events:
        if x > hi:
            break
        common = [(lo, hi)]
        for group in groups:
            common = intersect(common, merged((r[1], r[3]) for r in group if r[0] <= x <= r[2]))
            if not common:
                break
        if common:
            return [x, common[0][0]]
    return None


def raw():
    from seed_search.backend import sweep_raw, raw_layout, structure_type
    from seed_search.realm.raw import FAMILIES, joint_center_witness
    from seed_search.realm.bounds import contains, square, nether_square
    m = probe()
    rng = np.random.default_rng(320261010)
    starts = [0, 2**32-512, *map(int, rng.integers(8192, 2**32-8192, 6, dtype=np.uint32))]
    low32 = [v for start in starts for v in range(start, start+512)]
    geometries = [(5000, 2688, 1024), (4000, 1280, 768), (4000, 1280, 896), (4000, 1536, 896)]
    rows, witnesses = [], []
    for discovery, ow, nether in geometries:
        fs = families(discovery, ow, nether)
        if discovery == 5000:
            assert fs == FAMILIES
            fs = FAMILIES
        types = np.array([structure_type(name) for name, b in fs], np.int32)
        bounds = np.array([b for name, b in fs], np.int32)
        times = []
        reference = None
        for trial in range(3):
            for mode in ((0, 1, 2) if trial % 2 == 0 else (2, 1, 0)):
                values = []
                begin = time.perf_counter()
                for start in starts:
                    out = np.empty((512, 5), np.int32)
                    assert m.lib.diag_raw_sweep(start, 512, m.ffi.from_buffer('int[]', types),
                                                m.ffi.from_buffer('int[]', bounds), 5, 18,
                                                m.ffi.from_buffer('int[]', out), out.size, mode) == 0
                    values.append(out)
                elapsed = time.perf_counter()-begin
                values = np.concatenate(values)
                if reference is None:
                    reference = values
                    control = np.concatenate([sweep_raw(start, 512, fs, 18) for start in starts])
                    assert np.array_equal(reference, control)
                assert np.array_equal(reference, values), (ow, mode)
                times.append({'trial': trial, 'mode': mode, 'seconds': elapsed})
        begin = time.perf_counter()
        missing = 0
        for i, low in enumerate(low32):
            layouts = [raw_layout(low, name, b) for name, b in fs[:4]]
            assert [len(v) for v in layouts] == reference[i, :4].tolist()
            witness = joint(layouts, discovery, ow, nether)
            if discovery == 5000:
                assert witness == joint_center_witness(layouts)
            if witness is not None:
                assert all(any(contains(p, square(witness, ow) if j < 2 else nether_square(witness, nether))
                               for p in v) for j, v in enumerate(layouts))
            else:
                missing += 1
            witnesses.append({'discovery': discovery, 'ow': ow, 'nether': nether,
                              'low32': low, 'joint_center': witness})
        joint_seconds = time.perf_counter()-begin
        row = {'discovery': discovery, 'ow': ow, 'nether': nether, 'inputs': len(low32),
               'families': fs, 'timings': times, 'joint_seconds': joint_seconds,
               'necessary_missing': int((reference == 0).any(axis=1).sum()), 'joint_missing': missing,
               'family_count_summary': [{'name': name, 'bounds': b,
                                          'min': int(reference[:, j].min()), 'median': float(np.median(reference[:, j])),
                                          'max': int(reference[:, j].max()), 'zeros': int((reference[:, j] == 0).sum()),
                                          'reference_regions': (b[2]//m.lib.diag_region_size(types[j])-b[0]//m.lib.diag_region_size(types[j])+3)
                                              * (b[3]//m.lib.diag_region_size(types[j])-b[1]//m.lib.diag_region_size(types[j])+3),
                                          'tight_regions': (b[2]//m.lib.diag_region_size(types[j])-b[0]//m.lib.diag_region_size(types[j])+1)
                                              * (b[3]//m.lib.diag_region_size(types[j])-b[1]//m.lib.diag_region_size(types[j])+1)}
                                         for j, (name, b) in enumerate(fs)]}
        rows.append(row)
        print('Raw', ow, nether, 'zero-family:', row['necessary_missing'], 'no joint witness:', missing, flush=True)
        save('raw-progress.json', {'rows': rows})
    save('raw-witnesses.json', witnesses)
    save('raw.json', {'rows': rows, 'starts': starts, 'block_size': 512,
                      'all_count_arms_match': True, 'witness_membership_checked': True,
                      'scope': '4096 low32 values in eight dispersed 512-value blocks; unknown actual Stronghold centers and full64 viability remain outside raw filtering.'})


def raw_thresholds():
    from seed_search.backend import structure_type, sweep_raw
    from seed_search.realm.raw import FAMILIES
    m = probe()
    original = json.loads((OUT / 'raw.json').read_text())
    rows = []
    for source in original['rows']:
        fs = families(source['discovery'], source['ow'], source['nether'])
        if source['discovery'] == 5000:
            assert fs == FAMILIES
        types = np.array([structure_type(name) for name, b in fs], np.int32)
        bounds = np.array([b for name, b in fs], np.int32)
        ref = np.concatenate([sweep_raw(start, 512, fs, 18) for start in original['starts']])
        guarantees = [m.lib.diag_guaranteed_count(int(t), m.ffi.from_buffer('int[]', np.ascontiguousarray(b)))
                      for t, b in zip(types, bounds)]
        assert all(np.all(ref[:, j] >= guarantee) for j, guarantee in enumerate(guarantees))
        timings = []
        for trial in range(5):
            for mode in ((0, 3, 4) if trial % 2 == 0 else (4, 3, 0)):
                values = []
                begin = time.perf_counter()
                for start in original['starts']:
                    out = np.empty((512, 5), np.int32)
                    assert m.lib.diag_raw_sweep(start, 512, m.ffi.from_buffer('int[]', types),
                                                m.ffi.from_buffer('int[]', bounds), 5, 18,
                                                m.ffi.from_buffer('int[]', out), out.size, mode) == 0
                    values.append(out)
                seconds = time.perf_counter()-begin
                actual = np.concatenate(values)
                expected = ref if mode == 0 else np.minimum(ref, 1 if mode == 3 else 32)
                assert np.array_equal(expected, actual), (mode, source['ow'])
                timings.append({'trial': trial, 'mode': mode, 'seconds': seconds})
        rows.append({'discovery': source['discovery'], 'ow': source['ow'], 'nether': source['nether'],
                     'inputs': len(ref), 'guaranteed_placement_counts': guarantees,
                     'native_timings': timings, 'count_sha256': hashlib.sha256(ref.tobytes()).hexdigest(),
                     'ranking_score_unique_values': sorted(set(np.minimum(ref, 32).sum(axis=1).tolist())),
                     'village_and_city_rank_contribution': sorted(set(np.minimum(ref[:, :2], 32).sum(axis=1).tolist()))})
        np.save(OUT / f'raw-counts-{source["ow"]}-{source["nether"]}.npy', ref)
    save('raw-thresholds.json', {'rows': rows, 'presence_parity': True, 'capped_score_parity': True,
                                'native_build': json.loads((OUT / 'build.json').read_text()),
                                'output_contracts': {'0': 'full placement counts', '3': 'existence flags',
                                                     '4': 'counts capped at 32; exact original ranking scores'},
                                'scope': 'Same 4096 dispersed inputs, five counterbalanced trials, 18 threads. Different output contracts; no persistence, joint-center or full64 evaluation.'})
    print('Raw threshold/existence arms matched their stated contracts.', flush=True)


def gate():
    """Prototype eligibility first; full inventories and scores are deferred."""
    import seed_search.backend as backend
    from seed_search import _native as installed
    from seed_search.realm.baseline import evaluate_seed, structure_observation
    from seed_search.realm.cli import load
    from seed_search.realm.runner import _seed
    from seed_search.realm.biomes import WOOD, canonical
    from seed_search.realm.bounds import square, native_bounds, nether_square
    m = probe()
    production = load(str(ROOT / 'config/realm.yaml'))
    wood = {i: next((f for f, names in WOOD.items() if canonical(backend.biome_name(i)) in names), None)
            for i in range(256)}

    def first_gate(seed, cfg):
        decisions = {}
        visits = []
        mine_visits = []
        with backend.Backend(seed) as b:
            discovery = structure_observation(b, 'stronghold', cfg['discovery']['overworld_bounds'])
            initial = structure_observation(b, 'fortress', cfg['discovery']['nether_bounds'])
            for anchor in discovery['predicted_viable']:
                pending = []
                if not initial['predicted_viable']:
                    pending.append('initial_fortress')
                n_bounds = nether_square(anchor, cfg['deployment']['nether_side_blocks'])
                ow = cfg['deployment']['overworld_side_blocks']
                o_bounds = square(anchor, ow)
                for name in ('fortress', 'bastion'):
                    found = structure_observation(b, name, n_bounds)
                    if not found['predicted_viable']:
                        pending.append('final_'+name)
                for name in cfg['search']['structure_order']:
                    if pending:
                        continue
                    if name == 'mineshaft':
                        found, visited = mines(m, b._handle(), native_bounds(o_bounds), 1)
                        mine_visits.append(visited)
                        positive = bool(len(found))
                    else:
                        positive = bool(structure_observation(b, name, o_bounds)['predicted_viable'])
                    if not positive:
                        pending.append(name)
                if not pending:
                    pts = points(anchor, ow)
                    order = np.random.default_rng(7).permutation(len(pts))
                    observed = set()
                    visited = 0
                    for at in range(0, len(pts), 16):
                        ids = biomes(m, b._handle(), np.ascontiguousarray(pts[order[at:at+16]]), 1)
                        visited += len(ids)
                        observed.update(wood.get(int(i)) for i in ids if wood.get(int(i)) is not None)
                        if len(observed) >= 2:
                            break
                    visits.append({'visited': visited, 'full': len(pts), 'positive': len(observed) >= 2})
                    if len(observed) < 2:
                        pending.append('wooded_family_coverage')
                decisions[f'{seed}:{anchor[0]}:{anchor[1]}'] = {'qualification': 'PENDING' if pending else 'PREDICTED',
                                                               'pending_reasons': pending}
        return decisions, visits, mine_visits

    rows = []
    for ow, nether, discovery in ((2688, 1024, 5000), (1280, 896, 4000)):
        cfg = copy.deepcopy(production)
        cfg['deployment'] = {'overworld_side_blocks': ow, 'nether_side_blocks': nether}
        cfg['discovery'] = {name: [-discovery//2, -discovery//2, discovery//2, discovery//2]
                            for name in ('overworld_bounds', 'nether_bounds')}
        references = {}
        for trial in range(3):
            for arm in (('full_baseline', 'eligibility_first') if trial % 2 == 0 else ('eligibility_first', 'full_baseline')):
                module = installed if arm == 'full_baseline' else m
                backend.ffi, backend.lib = module.ffi, module.lib
                all_visits = []
                mine_visits = []
                decision_hash = []
                cpu = time.process_time()
                begin = time.perf_counter()
                for index in range(96):
                    seed = _seed(index, cfg['search'])
                    if arm == 'full_baseline':
                        result = evaluate_seed(index, seed, cfg)
                        decisions = {c['id']: {'qualification': c['qualification'], 'pending_reasons': c['pending_reasons']}
                                     for c in result['anchors']}
                        all_visits.extend({'visited': c['biomes']['sample_count'], 'full': c['biomes']['sample_count'],
                                           'positive': c['biomes']['wooded_family_count'] >= 2}
                                          for c in result['anchors'] if c['biomes'])
                    else:
                        decisions, visits, visited = first_gate(seed, cfg)
                        all_visits.extend(visits)
                        mine_visits.extend(visited)
                    if index in references:
                        assert decisions == references[index], (ow, arm, index)
                    else:
                        references[index] = decisions
                    decision_hash.append(hashlib.sha256(json.dumps(decisions, sort_keys=True).encode()).hexdigest())
                elapsed = time.perf_counter()-begin
                cpu_seconds = time.process_time()-cpu
                rows.append({'ow': ow, 'nether': nether, 'discovery': discovery, 'arm': arm, 'trial': trial,
                             'inputs': 96, 'seconds': elapsed, 'cpu_seconds': cpu_seconds,
                             'decision_sha256': hashlib.sha256('\n'.join(decision_hash).encode()).hexdigest(),
                             'wooded_points': sum(v['visited'] for v in all_visits),
                             'full_wooded_points': sum(v['full'] for v in all_visits),
                             'wooded_checks': len(all_visits), 'wooded_negatives': sum(not v['positive'] for v in all_visits),
                             'mineshaft_chunks_visited': sum(mine_visits),
                             'deferred': [] if arm == 'full_baseline' else ['full Mineshaft start inventory', 'full biome inventory/bonuses', 'optional structure inventories/bonuses']})
                print('Eligibility gate', ow, trial, arm, round(elapsed, 3), flush=True)
        assert len({r['decision_sha256'] for r in rows if r['ow'] == ow}) == 1
    backend.ffi, backend.lib = installed.ffi, installed.lib
    save('gate.json', {'rows': rows, 'qualification_and_pending_reasons_match': True,
                       'native_build': json.loads((OUT / 'build.json').read_text()),
                       'scope': '96 distinct full64 inputs shared across two geometries (192 input/geometry cases), three trials. Decision parity only; inventories/scores deferred, no persistence/terrain/BDS. Prototype is not a drop-in payload replacement.'})


def raw_presence_scale():
    """Confirm the small existence timings with longer batches and two budgets."""
    from seed_search.backend import structure_type, sweep_raw
    m = probe()
    original = json.loads((OUT / 'raw.json').read_text())
    block = 32768
    starts = [min(int(s), 2**32-block) for s in original['starts']]
    ordered = sorted(starts)
    assert all(a+block <= b for a, b in zip(ordered, ordered[1:]))
    rows = []
    for discovery, ow, nether in ((5000, 2688, 1024), (4000, 1280, 768), (4000, 1280, 896)):
        fs = families(discovery, ow, nether)
        types = np.array([structure_type(name) for name, b in fs], np.int32)
        bounds = np.array([b for name, b in fs], np.int32)
        reference = None
        trials = []
        for trial in range(3):
            for threads in ((18, 36) if trial % 2 == 0 else (36, 18)):
                values = []
                cpu = time.process_time()
                begin = time.perf_counter()
                for start in starts:
                    out = np.empty((block, 5), np.int32)
                    assert m.lib.diag_raw_sweep(start, block, m.ffi.from_buffer('int[]', types),
                                                m.ffi.from_buffer('int[]', bounds), 5, threads,
                                                m.ffi.from_buffer('int[]', out), out.size, 3) == 0
                    values.append(out)
                seconds = time.perf_counter()-begin
                cpu_seconds = time.process_time()-cpu
                actual = np.concatenate(values)
                if reference is None:
                    reference = actual
                    # Full-count boundary controls for every longer block.
                    for i, start in enumerate(starts):
                        for offset in (0, 1, block//2, block-1):
                            full = sweep_raw(start+offset, 1, fs, 1)[0]
                            assert np.array_equal(full > 0, reference[i*block+offset])
                assert np.array_equal(reference, actual)
                trials.append({'trial': trial, 'threads': threads, 'seconds': seconds, 'cpu_seconds': cpu_seconds})
        rows.append({'discovery': discovery, 'ow': ow, 'nether': nether, 'inputs': len(reference),
                     'necessary_missing': int((reference == 0).any(axis=1).sum()), 'timings': trials,
                     'presence_sha256': hashlib.sha256(reference.tobytes()).hexdigest()})
        print('Larger presence batch', ow, nether, 'checked', len(reference), flush=True)
    save('raw-presence-scale.json', {'rows': rows, 'starts': starts, 'block_size': block,
                                    'boundary_full_count_controls': 32*len(rows), 'thread_outputs_match': True,
                                    'native_build': json.loads((OUT / 'build.json').read_text()),
                                    'scope': '262144 low32 values in eight dispersed blocks; existence flags only, no ranking, joint witnesses, persistence or full64 validation.'})


def audit():
    before = json.loads((OUT / 'source-before.json').read_text())['sha256']
    changed = [name for name, expected in before.items() if sha(name) != expected]
    assert not changed, changed
    m = json.loads((OUT / 'micro.json').read_text())
    b = json.loads((OUT / 'baseline.json').read_text())
    r = json.loads((OUT / 'raw.json').read_text())
    assert m['all_exact_arms_match'] and b['all_payloads_match'] and r['all_count_arms_match']
    thresholds = json.loads((OUT / 'raw-thresholds.json').read_text())
    gate_data = json.loads((OUT / 'gate.json').read_text())
    scale = json.loads((OUT / 'raw-presence-scale.json').read_text())
    assert thresholds['presence_parity'] and thresholds['capped_score_parity']
    assert gate_data['qualification_and_pending_reasons_match'] and scale['thread_outputs_match']
    # Every tested OW square has at least one guaranteed Village/City raw
    # attempt at every integer center. Exhaust the coordinate phase modulo the
    # region width; X and Z factors then form a fully contained region box.
    phase_cases = 0
    square_guarantees = []
    for side in (1024, 1280, 1536, 1792, 2048, 2304, 2380, 2688):
        counts = {}
        for name, region, chunk_range in (('village', 34, 26), ('ancient_city', 24, 16)):
            size, first, last = region*16, 8, (chunk_range-1)*16+8
            intervals = []
            for center in range(size):
                lo, hi = center-side//2, center+side//2-1
                regions = (hi-last)//size - (-((-(lo-first))//size)) + 1
                assert regions >= 1
                intervals.append(regions)
                phase_cases += 1
            counts[name] = min(intervals)**2
        square_guarantees.append({'ow': side, 'guaranteed_raw_starts_in_every_anchor_square': counts})
    # Check removing those universal clauses from the joint test against every
    # saved four-family result, including all negative witnesses.
    from seed_search.backend import raw_layout
    contracts = {(r['discovery'], r['ow'], r['nether']): r for r in json.loads((OUT / 'raw.json').read_text())['rows']}
    nether_cache = {}
    joint_cases = 0
    for row in json.loads((OUT / 'raw-witnesses.json').read_text()):
        config = contracts[row['discovery'], row['ow'], row['nether']]
        bounds = tuple(config['families'][2][1])
        key = row['low32'], bounds
        if key not in nether_cache:
            nether_cache[key] = [raw_layout(row['low32'], name, bounds) for name in ('fortress', 'bastion')]
        reduced = joint([[], [], *nether_cache[key]], row['discovery'], row['ow'], row['nether'], include_overworld=False)
        assert (reduced is not None) == (row['joint_center'] is not None)
        joint_cases += 1
    # Verify the new compact geometry against independent, exhaustive small
    # domains, including fractional Nether borders and empty family groups.
    from seed_search.realm.bounds import contains, square, nether_square
    rng = np.random.default_rng(483297)
    geometry_cases = 0
    for discovery, ow, nether in ((8, 4, 2), (12, 8, 4), (16, 12, 2)):
        centers = [(x, z) for x in range(-discovery//2, discovery//2)
                   for z in range(-discovery//2, discovery//2)]
        fs = families(discovery, ow, nether)
        for dim in (0, 1):
            samples = {p for center in centers for p in range(-32, 33)
                       if contains((p, 0), square(center, ow) if dim == 0 else nether_square(center, nether))}
            actual = fs[dim*2][1]
            assert (min(samples), max(samples)) == (actual[0], actual[2])
        for trial in range(120):
            layouts = [rng.integers(-12, 13, (int(rng.integers(0, 6)), 2)).tolist() for _ in range(4)]
            actual = joint(layouts, discovery, ow, nether)
            expected = any(all(any(contains(p, square(center, ow) if i < 2 else nether_square(center, nether))
                                   for p in group) for i, group in enumerate(layouts)) for center in centers)
            assert (actual is not None) == expected, (discovery, layouts)
            geometry_cases += 1
    builds = [json.loads((OUT / name).read_text()) for name in ('build-v1.json', 'build.json')]
    assert all(sha(record['path']) == record['sha256'] for record in builds)
    names = ('build-v1.json', 'build.json', 'micro.json', 'baseline.json', 'raw.json', 'raw-witnesses.json',
             'raw-thresholds.json', 'raw-presence-scale.json', 'gate.json')
    save('audit.json', {'preserved_original_files': len(before), 'changed_original_files': changed,
                        'micro_parity': True, 'baseline_full_payload_parity': True, 'raw_counts_parity': True,
                        'eligibility_gate_decision_parity': True, 'raw_presence_and_rank_score_parity': True,
                        'exhaustive_geometry_oracle_cases': geometry_cases,
                        'overworld_region_phase_cases': phase_cases,
                        'per_anchor_raw_presence_guarantees': square_guarantees,
                        'reduced_nether_only_joint_cases': joint_cases,
                        'native_libraries_match_recorded_builds': True,
                        'production_installation_changed': False,
                        'artifact_sha256': {name: sha(OUT / name) for name in names},
                        'actual_generation_certified': False})
    print('Audit passed:', len(before), 'original hashes preserved.', flush=True)


def report():
    micro_data = json.loads((OUT / 'micro.json').read_text())
    baseline_data = json.loads((OUT / 'baseline.json').read_text())
    gate_data = json.loads((OUT / 'gate.json').read_text())
    raw_data = json.loads((OUT / 'raw.json').read_text())
    thresholds = json.loads((OUT / 'raw-thresholds.json').read_text())
    scale = json.loads((OUT / 'raw-presence-scale.json').read_text())
    million = json.loads((ROOT / 'runs/master-implementation-2026-10-10/million/benchmark.json').read_text())['rows'][0]
    stage = million['worker_statistics']['stage_seconds']
    inventory_calls = million['counts']['biome_samples']//1764
    shares = {name: 100*stage[name]/sum(stage.values()) for name in ('mineshaft', 'wooded_biomes')}
    mine_table, biome_table, baseline_table, gate_table, raw_table, threshold_table, scale_table = [], [], [], [], [], [], []
    derived = {'scope': 'Predictor diagnosis and proposals; no production modifications or real-game certification.',
               'million': {'mineshaft_ms_per_check': 1000*stage['mineshaft']/inventory_calls,
                           'biome_ms_per_inventory': 1000*stage['wooded_biomes']/inventory_calls,
                           'timed_stage_shares_percent': shares, 'inventory_calls': inventory_calls,
                           'mineshaft_pending': million['counts'].get('pending_mineshaft', 0)}}
    derived['mineshaft'] = []
    for side in (1280, 2380, 2688):
        rows = [r for r in micro_data['mineshaft'] if r['side'] == side]
        times = {key: statistics.median(statistics.median(r['timings'][key]) for r in rows)
                 for key in ('installed', 'vector4_full', 'existence_only')}
        derived['mineshaft'].append({'side': side, 'seconds': times})
        mine_table.append(f"| {side} | {times['installed']*1000:.3f} | {times['vector4_full']*1000:.3f} | {times['existence_only']*1000:.3f} |")
        rows = [r for r in micro_data['biomes'] if r['side'] == side]
        times = {key: statistics.median(statistics.median(r['timings'][key]) for r in rows)
                 for key in ('private_reference', 'direct_exact')}
        biome_table.append(f"| {side} | {rows[0]['points']} | {times['private_reference']*1000:.3f} | {times['direct_exact']*1000:.3f} |")
    derived['baseline'] = []
    derived['eligibility_first'] = []
    for ow in (2688, 1280):
        rows = [r for r in baseline_data['rows'] if r['overworld_side'] == ow]
        normal = statistics.median(r['seconds'] for r in rows if r['arm'] == 'installed')
        fast = statistics.median(r['seconds'] for r in rows if r['arm'] == 'vector4_direct')
        reference = rows[0]
        reduction = 100*(1-fast/normal)
        baseline_table.append(f'| {ow}/{reference["nether_side"]} | {normal:.3f} | {fast:.3f} | {reduction:.1f}% |')
        derived['baseline'].append({'ow': ow, 'nether': reference['nether_side'], 'reference_seconds': normal,
                                    'prototype_seconds': fast, 'seconds_reduction_percent': reduction,
                                    'exact_biome_repeat_percent': 100*reference['exact_repeated_biome_points']/reference['biome_points']})
        rows = [r for r in gate_data['rows'] if r['ow'] == ow]
        normal = statistics.median(r['seconds'] for r in rows if r['arm'] == 'full_baseline')
        fast = statistics.median(r['seconds'] for r in rows if r['arm'] == 'eligibility_first')
        r = next(r for r in rows if r['arm'] == 'eligibility_first')
        gate_table.append(f'| {ow}/{r["nether"]} | {normal:.3f} | {fast:.3f} | {normal/fast:.2f}× | {r["wooded_points"]:,}/{r["full_wooded_points"]:,} |')
        derived['eligibility_first'].append({'ow': ow, 'nether': r['nether'], 'reference_seconds': normal,
                                             'prototype_seconds': fast, 'ratio': normal/fast,
                                             'biome_samples': r['wooded_points'], 'full_biome_samples': r['full_wooded_points'],
                                             'deferred': r['deferred']})
    derived['raw'] = []
    for row, capped in zip(raw_data['rows'], thresholds['rows']):
        percent = 100*row['joint_missing']/row['inputs']
        original = statistics.median(r['seconds'] for r in row['timings'] if r['mode'] == 0)
        trimmed = statistics.median(r['seconds'] for r in row['timings'] if r['mode'] == 2)
        rank = statistics.median(r['seconds'] for r in capped['native_timings'] if r['mode'] == 4)
        raw_table.append(f'| {row["discovery"]} | {row["ow"]}/{row["nether"]} | {row["necessary_missing"]}/{row["inputs"]} | {row["joint_missing"]}/{row["inputs"]} ({percent:.2f}%) |')
        threshold_table.append(f'| {row["ow"]}/{row["nether"]} | {original/row["inputs"]*2**32/3600:.2f} h | {trimmed/row["inputs"]*2**32/3600:.2f} h | {rank/row["inputs"]*2**32/3600:.2f} h |')
        derived['raw'].append({'discovery': row['discovery'], 'ow': row['ow'], 'nether': row['nether'],
                               'joint_missing_percent': percent, 'guaranteed_counts': capped['guaranteed_placement_counts'],
                               'capped_ranking_seconds': rank, 'original_count_seconds': original})
    derived['raw_presence_scale'] = []
    for row in scale['rows']:
        medians = {n: statistics.median(r['seconds'] for r in row['timings'] if r['threads'] == n) for n in (18, 36)}
        percent = 100*row['necessary_missing']/row['inputs']
        fastest = medians[36]
        scale_table.append(f'| {row["ow"]}/{row["nether"]} | {percent:.2f}% | {row["inputs"]/medians[18]:,.0f} | {row["inputs"]/fastest:,.0f} | {fastest/row["inputs"]*2**32/60:.1f} min |')
        derived['raw_presence_scale'].append({'ow': row['ow'], 'nether': row['nether'], 'inputs': row['inputs'],
                                              'necessary_missing_percent': percent, 'seconds': medians,
                                              '36_thread_full32_compute_only_minutes': fastest/row['inputs']*2**32/60})
    save('summary.json', derived)
    text = f'''# Mineshaft, biome inventory and lower32 investigation — 10 October 2026

The dominant cost is complete inventory work executed at the baseline gate. A phased gate can preserve the current eligibility decisions while doing much less work; a native enumeration prototype also accelerates the current complete payload. The 99.9% lower32 rejection aspiration is unsupported by the filter's logic, even with compact borders.

## Evidence and scope

The million-input benchmark used 5000-square discovery, 2688 Overworld and 1024 Nether. It measured {derived['million']['mineshaft_ms_per_check']:.2f} ms per Mineshaft check and {derived['million']['biome_ms_per_inventory']:.2f} ms per 1764-point biome inventory. Mineshaft and biome calls consumed {shares['mineshaft']:.2f}% and {shares['wooded_biomes']:.2f}% of summed timed filtering calls. There were {inventory_calls:,} checks of each, zero recorded Mineshaft prediction misses, and {million['counts']['biome_samples']:,} biome points. These are summed worker call durations, not pipeline wall-clock shares. The run's end-to-end rate remained {million['seeds_per_second']:.2f} full64 inputs/sec, including persistence.

New experiments used eight boundary/control seeds for native microbenchmarks, 96 distinct full64 seeds shared across two border contracts, 4096 distinct low32 values shared across four contracts in eight dispersed blocks, and 262,144 low32 values shared across three contracts for longer existence timing. All timings are local diagnostic workloads; repetitions do not increase unique coverage.

The 96-input complete-payload comparisons used three counterbalanced trials of installed, private-reference and exact-prototype arms. The gate comparison used three counterbalanced trials of full baseline and eligibility first. Production source/config/native binary and prior evidence retain their original hashes. Private builds and logs are under this directory.

## 1. Why Mineshaft takes so long

`native/bridge.c:ss_scan` dispatches to `finders.c:getMineshafts`, which visits every candidate chunk. Each chunk calls `setCarverSeed`, restarting MT19937, skips the first random value and tests the second. `mt_seed` initializes 397 state terms even though a usual chunk needs only two outputs. A 2688 square covers roughly 28,000 chunks: approximately 11 million dependent initialization recurrences per check. This work predicts start positions; `getMineshaftPieces` is not on this path.

The combined wrapper already scans placement once and applies a trivial Mineshaft viability mask. A duplicate raw/viable scan and buffer overflow/retry are not the current cause. The remaining waste is enumerating every start when baseline eligibility needs one. Original chunk rounding can also visit an outside edge row, but tightening the start-center bounds saved little by itself.

Isolated median times in milliseconds, three trials per seed/border case:

| Overworld side | Installed complete scan | Vector4 complete scan | First-start existence |
|---|---:|---:|---:|
{chr(10).join(mine_table)}

The four-lane prototype evaluates exact MT outputs for four chunk seeds together. Complete-scan arms matched every start coordinate; all {micro_data['mineshaft_comparisons']} comparisons passed their full-array or first-witness contracts, including control repetitions. The first three MT outputs also match on {micro_data['mt_first3_cases']} seeds, including unsigned boundaries. The existence arm stops at the first in-border start and matches the full scan's presence and first coordinate; a negative scans the complete relevant domain.

Concrete change: add a native Mineshaft existence API with exact half-open/start-center bounds, return one witness and label the full start inventory deferred. Complete enumeration can run when a candidate is nominated. If the complete baseline payload must be retained immediately, use the reviewed vector kernel with scalar fallback and versioned native identity; it reduces this stage by about half without dropping starts.

The pinned carver code truncates the world seed to uint32 for MT initialization and chunk mixing. All 64 tests of 16 low32 layouts × four high32 siblings matched their start arrays. This supports reviewing Mineshaft raw placement for a version-bound cache, but does not change the existing allowlist or certify real-world generation. Independent full64 enumeration has little useful sibling reuse; prioritize existence first.

## 2. Why biome inventory takes so long, and logic problems

`baseline.py` builds a 64-block grid anchored at each border's lower corner: 1764 points at 2688, 400 at 1280. It samples all points even after two wooded families are known because the same result supplies the entire biome inventory and bonus score. The CFFI call is batched once; it is not one Python/native crossing per point. Each native point calls `getBiomeAt`, which allocates and frees a small cache, then evaluates Voronoi access, climate noise, splines and the biome tree. Seeds are initialized once per context, not per point.

| Side | Points | Original native batch ms | Exact direct sampler ms |
|---|---:|---:|---:|
{chr(10).join(biome_table)}

Removing the allocation while preserving Voronoi coordinates, flags, rounding and a NULL climate hint saved only about 1–3%. The primary cost is noise and lookup at every point. Exact point reuse across overlapping anchors was only 0.39% at the old borders and zero at compact borders in the 96-seed cohort, so merely enabling a point cache would not solve it.

The existing `ss_biome_points` loop also has no OpenMP loop even when the handle's native thread count is increased. A private direct loop produced identical IDs at 1/4/18 threads; at 2688 its medians were about 11.13/3.03/0.96 ms. That is useful for an isolated inventory or differently partitioned process/thread budget. The baseline already runs 30 processes × one native thread; adding 18 threads to each would exceed the measured CPU budget. A new combined schedule needs its own benchmark.

Two correctness findings affect proposed optimizations:

* The current sample lattice moves when the border size changes. The saved pilot already shows seed `7980124511283784280`, Stronghold `(772,-1996)`, detecting forest+jungle at 2304 but only jungle at 2380. Replaying the old witness coordinates within the larger border restores both. Use a world-aligned lattice and retain existing in-border witnesses; version the sampling contract and re-score candidates. Refine unresolved sparse negatives instead of treating them as absence. Changing the lattice does not preserve the old inventory payload automatically.
* Reusing the previous climate-tree leaf is unsafe for exact sampling. The source tree uses strict distance comparisons, so a cached leaf can win a tie differently. The experimental hint arm changed four IDs, including seed `12345` at `(3041,63,-1183)` from beach to forest. Exclude this shortcut. Preserve NULL hints unless a canonical, reference-equivalent tie rule is proved.

The inventory samples fixed Y=63, so it predicts biomes at that height rather than actual generated surface coverage. Keep that status explicit. For final inventory, reuse surface observations/terrain raster work already available in later stages instead of adding a surface-height scan to every baseline input.

Concrete change: sample a dispersed ordering of the same lattice in small batches, stopping once two wooded families have positive witnesses. If two are not found, finish that lattice and retain PENDING. Defer full family/variant counts and optional bonus inventories, with explicit score intervals and deferred status, then complete them for the shortlist. Future prioritization must account for those unknown scores and retain fair exploration; incomplete scores cannot silently become zero or prove a candidate is worse.

## 3. Complete-payload improvement versus a phased gate

The exact vector Mineshaft scan plus direct biome sampler preserves every compared candidate payload, including all start coordinates, detections, counts, bonuses, statuses and uncertainties. These timings include the same Python cache instrumentation in each arm and exclude persistence/terrain/BDS.

| OW/Nether | Installed seconds / 96 inputs | Exact prototype seconds | Time reduction |
|---|---:|---:|---:|
{chr(10).join(baseline_table)}

A second prototype checks Mineshaft existence and wooded witnesses, deferring full Mineshaft inventory, full biome inventory/bonuses and all optional structure inventories/bonuses. All qualification and pending-reason maps match the full baseline across the same 96 seeds and both geometries. This arm produces a different, incomplete payload and requires a staged contract before adoption.

| OW/Nether | Full baseline seconds | Eligibility-first seconds | Ratio | Biome points visited/full |
|---|---:|---:|---:|---:|
{chr(10).join(gate_table)}

The old-border cohort had no wooded negative; the compact cohort had one, exercising the full-grid negative fallback. These decision results certify the current sampled predictor only. Deferred work must be paid later if it is needed. These ratios do not establish a new persisted pipeline rate or a verified-world rate.

## 4. Why the lower32 99.9% aspiration fails

`realm/raw.py:FAMILIES` and `center_rectangle` hardcode 5000 discovery / 2688 OW / 1024 Nether. The raw scan searches an envelope containing every possible Stronghold-centered border. A common-center witness can lie anywhere in that domain; it does not need to be an actual Stronghold. Raw Village and Ancient City attempts exist at very high density, while their full64 biome viability, Stronghold discovery, wooded families, Trial Chamber and terrain are outside this filter.

This is a logical selectivity limit. For the old envelopes, there are at least 196 raw Village and 400 raw Ancient City attempts for every low32 value. At the 1280 compact envelopes the guaranteed counts are still 81 and 169. Those families cannot reject a layout via zero raw counts. The genuine raw absence test is almost entirely the small-envelope Fortress/Bastion placement split. The broad initial Fortress condition adds no eligibility rejection when a required final Fortress exists inside its contained envelope.

The stronger result applies inside every individual anchor square: Village raw attempts are guaranteed when the side is at least 944, and Ancient City raw attempts when it is at least 624. Their offsets lie in bounded intervals inside each region, and any square this wide contains a complete allowed-offset region box. Therefore both raw-presence clauses hold at every possible center for all requested OW sizes (1024–2380). Exhaustive integer phase checks verify this, and a two-family Nether-only joint solver matches all 16,384 saved four-family feasibility results. Village/City raw layouts need not be enumerated even for the joint-placement predicate. Full64 biome viability remains essential.

The saved 1280/896 compact baseline already produced qualifying prediction anchors for 215 of 1000 distinct full64 inputs. A necessary prefilter discarding 99.9% before these same structure/wooded checks would discard known positive predictions under the same contract. Final terrain formations may be rare; their rarity cannot be inferred from these common raw placements.

The original saved contiguous test rejected 30/4096 (0.73%). New dispersed results:

| Discovery side | OW/Nether | A family has zero starts | No common allowed center |
|---|---|---:|---:|
{chr(10).join(raw_table)}

The joint test added only one rejection, at 1280/768. A much larger necessary-existence cohort confirms the low rejection rates:

| OW/Nether | Necessary rejection % / 262,144 | 18-thread layouts/sec | 36-thread layouts/sec | Full32 forecast at 36 threads |
|---|---:|---:|---:|---:|
{chr(10).join(scale_table)}

The last column is an existence-only compute forecast. It excludes complete counts, ranking, joint-center witnesses, checkpoints, full64 evaluation and all world verification. Even this much lighter prototype remains above the 45-minute aspiration on the measured host. Rejecting 99.9% by keeping only a fixed top quota would be a sampling decision, not a proof that the discarded layouts cannot qualify.

## 5. Lower32 implementation waste and concrete fixes

The current native adapter enumerates all regional attempts to get exact counts and scans a one-region halo. That halo is useful for displaced Stronghold starts but unnecessary for the reviewed regional raw start families here. Fortress and Bastion share candidate coordinates and a complementary type draw; scanning both separately repeats placement work. The broad Fortress scan also overlaps the final envelope.

The current ranking is `sum(min(count,32))`. Village and Ancient City therefore contribute the same 64 points to every layout, universally under these envelopes. Their full counts cost most of the raw sweep and do not distinguish the ranking. Adding Fortress and Bastion counts also mostly rewards total regional attempts, rather than a feasible, viable Stronghold combination. The saved staged comparison yielded 209 predicted anchors versus 199 independent anchors, but cost 7.60+4.73 CPU seconds versus 7.25, and measured no verified yield advantage.

Exact-count prototypes trimmed the halo and reused the shared Nether scan. A separate threshold prototype proves guaranteed counts from fully covered regions, skips constant terms, and stops once 32 hits are found. It preserves capped ranking scores and every zero/nonzero decision; its output counts are capped and must be labeled as such.

18-thread compute-only forecasts, based on the 4096-layout trials:

| OW/Nether | Original full counts | Trim/shared full counts | Exact capped-ranking counts |
|---|---:|---:|---:|
{chr(10).join(threshold_table)}

Concrete changes, in implementation order:

1. Derive and version raw envelopes and center rectangles from the active discovery/OW/Nether contract, preserving fractional Stronghold/8 Nether centers and half-open bounds.
2. Split native APIs for existence, capped ranking metrics and complete layout inventory. Prove region-presence constants and avoid scans for saturated terms. Trim only reviewed region types; retain the displaced-Stronghold adapter.
3. Reduce joint raw feasibility to Fortress/Bastion for the proved OW-size range, and reuse their placement and contained-envelope work. Preserve their complementary type selection and full64 viability.
4. Replace flat raw-density hints with measured geometry metrics, such as feasible-center coverage and Fortress/Bastion coexistence; validate actual Stronghold/biome viability on a bounded high32 cohort. These are ranking experiments until useful yield and recall are established.
5. Keep independent full64 search primary. Measure total CPU time, persistence and verified yield for any sibling strategy; the current evidence does not support a universal 99.9% front-door rejection target.

## Recommended next work

Implement the Mineshaft existence API and a separate baseline eligibility/deferred-inventory contract first. Use dispersed positive-only wooded sampling with explicit pending negatives. Keep the exact vector complete scan as the option when full payloads are needed immediately. Correct the moving lattice under a new sampling identity. Then make the raw adapter contract-aware and remove constant/capped count work. Do not spend a full32 sweep budget before the ranking strategy demonstrates useful yield.

Verification: 63 targeted regression tests passed ([test record](regression-tests.json)). [audit.json](audit.json), [summary.json](summary.json), [micro.json](micro.json), [baseline.json](baseline.json), [gate.json](gate.json), [raw.json](raw.json), [raw-thresholds.json](raw-thresholds.json), [raw-presence-scale.json](raw-presence-scale.json) retain detailed evidence. Run `scripts/diagnose_filter_costs.py` commands with the local `.venv/bin/python`; the script and `scripts/filter_cost_probe.c` reproduce the isolated prototypes. The original 46 sealed source/evidence files and both private binary hashes were checked. Independent verification covers 360 small-domain exhaustive center-intersection cases, 7424 integer region-phase cases, and 16,384 reduced joint-predicate cases. Real-game accuracy and a new persisted end-to-end throughput remain unmeasured by these experiments.
'''
    (OUT / 'REPORT.md').write_text(text)
    print('Report and derived summary saved.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'micro', 'baseline', 'raw', 'raw_thresholds', 'raw_presence_scale', 'gate', 'audit', 'report'])
    args = parser.parse_args()
    globals()[args.command]()
