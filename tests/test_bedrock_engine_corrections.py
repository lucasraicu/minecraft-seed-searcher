"""Pinned game evidence plus independently compiled native correctness checks."""
import collections
import ctypes
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess

import pytest

from scripts.predictor_storage_probe import compare_points
from seed_search.realm.bedrock_biome_storage import (
    BiomeSection, Data3D, decode_data3d, sample_bedrock_runtime,
)
from seed_search.realm.biomes import canonical

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'fixtures/bedrock-26.52/predictor-engine'
PARENT = ROOT / 'fixtures/bedrock-26.52/predictor-resolution'
MECHANISM = ROOT / 'fixtures/bedrock-26.52/predictor-mechanism'


def read(path):
    return json.loads(path.read_bytes())


def reference_quart(seed, x, y, z):
    """Independent Python integer/f32 transcription; no production helper calls."""
    mask = (1 << 64) - 1
    f32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
    base = [v // 8 for v in (x, y, z)]
    fraction = [(v % 8) / 8 for v in (x, y, z)]
    best = None
    for dx, dz, dy in itertools.product((0, 1), repeat=3):
        bits = dx, dy, dz
        cx, cy, cz = [a + b for a, b in zip(base, bits)]
        a = ((cx * 3129871) ^ cy) & 0xffffffff
        signed = a - (1 << 32) if a & (1 << 31) else a
        n = (signed & mask) ^ ((cz * 116129781) & mask)
        n = (n * (n * 42317861 + 11)) & mask
        state = (n >> 16) ^ ((int(seed) & 0xffffffff) ^ 0x5deece66d)
        jitter = []
        for _ in range(3):
            state = (state * 0x5deece66d + 11) & mask
            jitter.append(f32((((state >> 24) & 0xffffff) / (1 << 24) - .5) * f32(.9)))
        v = [f32(f32(t - b) + j) for t, b, j in zip(fraction, bits, jitter)]
        distance = f32(f32(f32(v[0] * v[0]) + f32(v[1] * v[1])) + f32(v[2] * v[2]))
        if best is None or distance < best[0]:
            best = distance, (cx * 2, cy * 2, cz * 2)
    return best[1]


def test_pinned_observation_bundle_and_actual_game_identity():
    manifest = read(FIXTURE / 'manifest.json')
    assert manifest['revision'] == 'predictor-engine-regressions-v1'
    assert manifest['pinned_binary_sha256'] == '0a490c711d4a2ce075debcd979e8862b7eaba008373f9970f0edbb67f98f9207'
    assert hashlib.sha256((PARENT / 'manifest.json').read_bytes()).hexdigest() == manifest['parent_resolution_manifest_sha256']
    for name, entry in manifest['files'].items():
        assert '..' not in Path(name).parts and not Path(name).is_absolute()
        raw = (FIXTURE / name).read_bytes()
        assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256']
    observations = []
    for run in ('fresh', 'reload', 'retained_copy'):
        report = read(FIXTURE / run / 'report.json')
        assert report['status'] == 'observed'
        assert all(report[k] is True for k in ('clean_shutdown', 'owned_container_removed', 'save_confirmed'))
        assert report['world_identity'] == dict(seed='-9103892851552028103', api='2.10.0', players=0)
        assert 'Version: 1.26.52.3' in (FIXTURE / run / 'console.log').read_text()
        assert report['target_result']['biomeReads'] == 33
        assert report['target_result']['blockReads'] <= 36
        if run != 'fresh':
            assert report['copied_world']['source_unchanged'] is True
            assert report['target_result']['mutations'] == []
        else:
            assert report['target_result']['mutations'] == [dict(
                x=111, y=319, z=-2020, before='minecraft:air', after='minecraft:air', restored=True)]
        observations.append([(r['x'], r['y'], r['z'], r['id']) for r in report['target_result']['rows']])
    assert observations[0] == observations[1] == observations[2]


@pytest.mark.parametrize('run', ['fresh', 'reload', 'retained_copy'])
def test_runtime_ceiling_matches_direct_game_and_detects_old_repeat_error(run):
    report = read(FIXTURE / run / 'report.json')
    export = read(FIXTURE / run / 'export.json')
    points = read(FIXTURE / 'frozen.json')['points']
    result = compare_points(export, points, runtime_ceiling=True)
    assert result['revision'] == 'stored-biome-point-diagnostics-v3' and result['unknown'] == 0
    # Associate names only through explicit storage and exact API points in THIS world.
    names = {}
    for stored, api in zip(result['rows'], report['target_result']['rows'], strict=True):
        if stored['status'] == 'stored':
            name = canonical(api['id'])
            assert names.setdefault(stored['stored_id'], name) == name
    assert len(names) == 2
    for stored, api in zip(result['rows'], report['target_result']['rows'], strict=True):
        assert names[stored['stored_id']] == canonical(api['id'])
    legacy = compare_points(export, points, resolve_repeats=True)
    for x in (101, 106, 111):
        n = points.index([x, 80, -2020])
        assert legacy['rows'][n]['stored_id'] != result['rows'][n]['stored_id']
        assert result['rows'][n]['status'] == 'runtime_ceiling_clamped'
    with pytest.raises(ValueError, match='separate interpretations'):
        compare_points(export, points, resolve_repeats=True, runtime_ceiling=True)


def test_runtime_ceiling_does_not_invent_missing_or_interior_sections():
    uniform = BiomeSection(0, 'uniform', (7,), ())
    unknown = BiomeSection(1, 'unknown', (), ())
    heightmap = (0,) * 256
    assert sample_bedrock_runtime(Data3D(heightmap, (uniform, unknown)), 0, 16, 0) == 7
    assert sample_bedrock_runtime(Data3D(heightmap, (uniform,)), 0, 16, 0) is None
    assert sample_bedrock_runtime(Data3D(heightmap, (unknown,)), 0, 16, 0) is None
    gapped = Data3D(heightmap, (uniform, BiomeSection(2, 'unknown', (), ())))
    assert sample_bedrock_runtime(gapped, 0, 32, 0) is None
    interior = Data3D(heightmap, (uniform, unknown, BiomeSection(2, 'uniform', (8,), ())))
    assert sample_bedrock_runtime(interior, 0, 16, 0) is None
    with pytest.raises(TypeError):
        sample_bedrock_runtime(Data3D(heightmap, ()), True, 0, 0)


@pytest.fixture(scope='module')
def native(tmp_path_factory):
    out = tmp_path_factory.mktemp('bedrock-correctness')
    wrapper = out / 'wrapper.c'
    wrapper.write_text('''
#include "cave.h"
#include "finders.h"
#include <string.h>
#define main original_diagnostic_main
#include "biome_sampling_probe.c"
#undef main
const char *test_name(int id) { return name(id); }
int test_biomes(uint64_t seed, const int *xyz, int n, int *out) {
    Generator *g=calloc(1,sizeof(*g)); if(!g)return -1;
    setupGenerator(g,MC_26_50,0);applySeed(g,DIM_OVERWORLD,seed);
    for(int i=0;i<n;i++) out[i]=getBiomeAt(g,1,xyz[3*i],xyz[3*i+1],xyz[3*i+2]);
    free(g);return 0;
}
int test_structure(uint64_t seed,int x,int z,int outpost) {
    Generator *g=calloc(1,sizeof(*g));if(!g)return -1;
    setupGenerator(g,MC_26_50,0);applySeed(g,DIM_OVERWORLD,seed);
    int r=isViableStructurePos(outpost?Outpost:Village,g,x,z,0);free(g);return r;
}
int test_range(uint64_t seed,int scale,int x,int y,int z,int sx,int sy,int sz,int *out) {
    Generator *g=calloc(1,sizeof(*g));if(!g)return -1;
    setupGenerator(g,MC_26_50,0);applySeed(g,DIM_OVERWORLD,seed);
    Range r={scale,x,z,sx,sz,y,sy};
    int *cache=allocCache(g,r);if(!cache){free(g);return -1;}
    int result=genBiomes(g,cache,r);
    if(!result)memcpy(out,cache,sizeof(int)*sx*sz*(sy?sy:1));
    free(cache);free(g);return result;
}
int test_quarts(uint64_t seed,const int *xyz,int n,int *out) {
    Generator *g=calloc(1,sizeof(*g));if(!g)return -1;
    setupGenerator(g,MC_26_50,0);applySeed(g,DIM_OVERWORLD,seed);
    for(int i=0;i<n;i++)out[i]=getBiomeAt(g,4,xyz[3*i],xyz[3*i+1],xyz[3*i+2]);
    free(g);return 0;
}
''')
    vendor = ROOT / 'vendor/cubiomes-bedrock'
    library = out / 'corrections.dylib'
    units = 'noise biomes layers biomenoise cave generator finders util quadbase mt'.split()
    command = ['cc', '-shared', '-fPIC', '-O2', '-std=c11', '-fwrapv', '-ffp-contract=off',
               '-I', str(vendor), '-I', str(ROOT / 'scripts'), '-I', str(ROOT / 'native'),
               str(wrapper), str(ROOT / 'native/bridge.c'),
               *[str(vendor / (unit + '.c')) for unit in units], '-lm', '-o', str(library)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr
    lib = ctypes.CDLL(str(library))
    ptr = ctypes.POINTER(ctypes.c_int)
    lib.getBedrockBiomeQuart.argtypes = [ctypes.c_uint64, ctypes.c_int, ctypes.c_int, ctypes.c_int, ptr]
    lib.getBedrockBiomeQuart.restype = ctypes.c_int
    lib.test_biomes.argtypes = [ctypes.c_uint64, ptr, ctypes.c_int, ptr]
    lib.test_name.argtypes = [ctypes.c_int]
    lib.test_name.restype = ctypes.c_char_p
    lib.test_structure.argtypes = [ctypes.c_uint64, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    lib.test_range.argtypes = [ctypes.c_uint64, *([ctypes.c_int] * 7), ptr]
    lib.test_quarts.argtypes = [ctypes.c_uint64, ptr, ctypes.c_int, ptr]
    lib.ss_create.argtypes = [ctypes.c_uint64]
    lib.ss_create.restype = ctypes.c_void_p
    lib.ss_destroy.argtypes = [ctypes.c_void_p]
    lib.ss_biome.argtypes = [ctypes.c_void_p, *([ctypes.c_int] * 4)]
    lib.ss_biome_points.argtypes = [ctypes.c_void_p, ctypes.c_int, ptr, ctypes.c_int, ptr]
    lib.ss_grid.argtypes = [ctypes.c_void_p, *([ctypes.c_int] * 6), ptr,
                           ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_double)]
    return lib


def predict(native, seed, points):
    xyz = (ctypes.c_int * (3 * len(points)))(*(v for point in points for v in point))
    ids = (ctypes.c_int * len(points))()
    assert native.test_biomes(int(seed) % (1 << 64), xyz, len(points), ids) == 0
    return [canonical(native.test_name(i).decode()) for i in ids]


def test_native_cave_boundaries_and_spatial_seed_holdouts(native):
    domain = read(MECHANISM / 'domain.json')
    maps = read(MECHANISM / 'findings.json')['numeric_name_associations']
    totals = collections.Counter()
    for world, seed in enumerate(('-3509659830737203357', '-9103892851552028103')):
        export = read(PARENT / f'lifecycle/dirty_restore-{world}/export.json')
        records = {(r['cx'], r['cz']): decode_data3d(bytes.fromhex(r['data'])) for r in export['records']}
        points, expected = [], []
        for c in domain['chunks']:
            if c['world'] != world:
                continue
            for lx, lz, y in itertools.product(domain['local_x'], domain['local_z'], range(16, 81)):
                points.append([c['cx'] * 16 + lx, y, c['cz'] * 16 + lz])
                bid = sample_bedrock_runtime(records[c['cx'], c['cz']], lx, y, lz)
                expected.append(maps[seed][str(bid)])
                totals[c['role']] += 1
        assert predict(native, seed, points) == expected
    assert dict(totals) == dict(discovery=4160, spatial_holdout=2080, seed_holdout=2080)


def test_native_matches_all_330_heldout_cohort_game_reads(native):
    cohort = read(FIXTURE / 'heldout-biome-cohort.json')['rows']
    assert len(cohort) == 330
    for seed in {r['seed'] for r in cohort}:
        rows = [r for r in cohort if r['seed'] == seed]
        assert predict(native, seed, [r['position'] for r in rows]) == [r['observed'] for r in rows]


def test_native_bridge_points_scalar_and_grid_use_bedrock_selection(native):
    cohort = read(FIXTURE / 'heldout-biome-cohort.json')['rows']
    for seed in {r['seed'] for r in cohort}:
        rows = [r for r in cohort if r['seed'] == seed]
        ctx = native.ss_create(int(seed) % (1 << 64))
        assert ctx
        try:
            xyz = (ctypes.c_int * (3 * len(rows)))(*(v for r in rows for v in r['position']))
            ids = (ctypes.c_int * len(rows))()
            assert native.ss_biome_points(ctx, 0, xyz, len(rows), ids) == 0
            assert [canonical(native.test_name(i).decode()) for i in ids] == [r['observed'] for r in rows]
            for r in rows:
                bid = native.ss_biome(ctx, 0, *r['position'])
                assert canonical(native.test_name(bid).decode()) == r['observed']
            grid = (ctypes.c_int * 20)()
            climate = (ctypes.c_double * 120)()
            height = (ctypes.c_double * 20)()
            assert native.ss_grid(ctx, -11, -9, 5, 4, 1, 39, grid, climate, height) == 0
            expected = predict(native, seed, [[-11+x, 39, -9+z] for z in range(4) for x in range(5)])
            assert [canonical(native.test_name(i).decode()) for i in grid] == expected
        finally:
            native.ss_destroy(ctx)


def test_native_volume_indexing_and_zero_height_plane(native):
    seed = -3509659830737203357
    for sy in (0, 3):
        sx, sz = 5, 4
        out = (ctypes.c_int * (sx * sz * (sy or 1)))()
        assert native.test_range(seed % (1 << 64), 1, -11, 39, -9, sx, sy, sz, out) == 0
        points = [[-11 + x, 39 + y, -9 + z] for y in range(sy or 1)
                  for z in range(sz) for x in range(sx)]
        assert [canonical(native.test_name(i).decode()) for i in out] == predict(native, seed, points)


def test_native_quart_classification_preserves_all_3920_prior_nodes(native):
    domain = read(MECHANISM / 'domain.json')
    seeds = {0: '-3509659830737203357', 1: '-9103892851552028103'}
    keys = [(seeds[c['world']], x, y, z) for c in domain['chunks']
            for x in range(c['cx'] * 4 - 1, c['cx'] * 4 + 6)
            for y in range(3, 23) for z in range(c['cz'] * 4 - 1, c['cz'] * 4 + 6)]
    original = (MECHANISM / 'nodes.txt').read_text().splitlines()
    assert len(keys) == len(original) == 3920
    for seed in seeds.values():
        rows = [(k, l) for k, l in zip(keys, original, strict=True) if k[0] == seed]
        xyz = (ctypes.c_int * (3 * len(rows)))(*(v for k, _ in rows for v in k[1:]))
        ids = (ctypes.c_int * len(rows))()
        assert native.test_quarts(int(seed) % (1 << 64), xyz, len(rows), ids) == 0
        assert list(ids) == [int(l.split()[0]) for _, l in rows]


def test_native_cell_selection_signed_edges_and_lower32_seed_contract(native):
    points = [(x, y, z) for x in (-2147483648, -17, -16, -9, -8, -1, 0, 7, 8, 2147483647)
              for y in (-64, -1, 0, 79, 319) for z in (-2147483648, -9, -1, 0, 8, 2147483647)]
    for seed in (0, 1, 0xffffffff, 0x12345678ffffffff, (1 << 63), (1 << 64) - 1):
        for point in points:
            out = (ctypes.c_int * 3)()
            assert native.getBedrockBiomeQuart(seed, *point, out) == 0
            assert tuple(out) == reference_quart(seed, *point)
    assert native.getBedrockBiomeQuart(0, 0, 0, 0, None) == -1


def test_structure_rejections_and_independent_positive_controls(native):
    seed = -3509659830737203357
    assert native.test_structure(seed % (1 << 64), -296, -312, 0) == 0
    assert native.test_structure(seed % (1 << 64), 528, 512, 1) == 0
    villages = read(FIXTURE / 'village-preliminary-controls.json')
    assert len(villages) == 28
    for r in villages:
        x, z = r['point']
        if [x, z] != [-296, -312]:
            assert native.test_structure(seed % (1 << 64), x, z, 0) > 0
    controls = read(FIXTURE / 'heldout-structure-controls.json')
    assert len(controls) == 24 and len({r['seed'] for r in controls}) == 3
    for r in controls:
        assert native.test_structure(int(r['seed']) % (1 << 64), *r['raw'], r['feature'].endswith('outpost')) > 0
