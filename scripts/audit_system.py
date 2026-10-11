"""Bounded audit experiments; never mutate the production predictor or launch a sweep.

Run from the repository root with .venv/bin/python scripts/audit_system.py.
The experimental land cache shares only the pinned raw-density land boolean.
It must not be generalized to block-scale biome lookup or an interpolated model.
"""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[key] = '1'
import argparse
import cProfile
import io
import json
from pathlib import Path
import pstats
import time
import numpy as np
from seed_search.backend import Backend
from seed_search.cache import CachedBackend
from seed_search.config import load_config
from seed_search.storage import backend_identity
import seed_search.landscapes as landscapes

OUT = Path('runs/system-audit-2026-10-08')

def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

class QuartLandBackend(CachedBackend):
    def land(self, points):
        # _sample groups by floor(X/4), floor(Z/4), then broadcasts the result.
        out = self._sample(points, 'experimental_exact_land_quart', 4, 128, 1,
                           np.int8, -128, lambda p: Backend.land(self, p))
        return out[:, 0].astype(bool)

def micro():
    rows = []
    for seed in (-1, 0, 9, 12345, 4294979641):
        for anchor in ((-65, -33), (497, -1025)):
            x, z = np.meshgrid(np.arange(anchor[0], anchor[0]+64),
                               np.arange(anchor[1], anchor[1]+64))
            points = np.column_stack((x.ravel(), z.ravel())).astype(np.int32)
            # Include deduplication and expansion in the experimental timing.
            timings = {'reference': [], 'quart': []}
            for trial in range(3):
                answers = {}
                for mode in (('reference', 'quart') if trial % 2 == 0 else ('quart', 'reference')):
                    with Backend(seed) as b:
                        started = time.perf_counter()
                        if mode == 'reference':
                            answer = b.land(points)
                        else:
                            cells, inverse = np.unique(points // 4, axis=0, return_inverse=True)
                            answer = b.land(cells * 4)[inverse]
                        timings[mode].append(time.perf_counter()-started)
                        answers[mode] = answer
                assert np.array_equal(answers['reference'], answers['quart'])
            rows.append({'seed': str(seed), 'anchor': anchor, 'points': len(points),
                         'unique_quart_cells': len(cells), 'land_points': int(answer.sum()),
                         'equal': True, 'seconds': timings})
            print('micro', seed, anchor, timings, flush=True)
    save('land-cell-ab.json', {'scope': 'Ten fixed patches, three alternating-order trials; cold Backend instances.',
                              'rows': rows, 'backend_identity': backend_identity()})

def profile(seed):
    cfg, config_hash = load_config()
    values = {}
    for mode in ('reference', 'quart'):
        landscapes.CachedBackend = CachedBackend if mode == 'reference' else QuartLandBackend
        profiler = cProfile.Profile()
        result = profiler.runcall(landscapes.analyze_landscapes, (0, seed, cfg))
        profiler.dump_stats(str(OUT / f'profile-{seed}-{mode}.pstats'))
        stream = io.StringIO()
        pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats('cumulative').print_stats(60)
        (OUT / f'profile-{seed}-{mode}.txt').write_text(stream.getvalue())
        save(f'profile-{seed}-{mode}.json', result)
        values[mode] = result
        print(mode, result['total_seconds'], result['stage_seconds'], flush=True)
    landscapes.CachedBackend = CachedBackend
    fields = ('index', 'seed', 'candidates', 'near_misses', 'counts', 'filter_policy')
    equality = {key: values['reference'][key] == values['quart'][key] for key in fields}
    save(f'profile-{seed}-comparison.json', {'config_sha256': config_hash,
         'equal': all(equality.values()), 'compared_fields': equality,
         'reference_seconds': values['reference']['total_seconds'],
         'quart_seconds': values['quart']['total_seconds'],
         'scope': 'Single serial seed with cProfile overhead; not parallel throughput or yield.'})
    assert all(equality.values()), equality

def checks():
    """Repeat the bounded selectivity and synthetic lattice diagnostics."""
    import math
    import sqlite3
    from collections import Counter, defaultdict
    from seed_search.config import validate_config
    from seed_search.seeds import seed_from_index
    from seed_search.terrain import raster
    cfg, _ = load_config()
    cfg['search']['refinement_spacing_blocks'] = 64
    validate_config(cfg)
    class Ground:
        def heights(self, points, vertical_step=8):
            p = np.asarray(points)
            x, z = p[:, 0], p[:, 1]
            radius = np.hypot(x, z)
            h = np.where(x % 64 == 32, 72, 50).astype(np.int32)
            h[(x % 64 == 32) & (radius >= 300) & (radius <= 500)] = 160
            return h, np.ones(len(p), np.int32)
    ground = Ground()
    terrain = raster(ground, (-1504, -1504, 1504, 1504), 64)
    flat, _, connected = landscapes.flat_metrics(terrain, [0, 0], cfg['landscapes'])
    ring = landscapes.ring_metrics(terrain, [0, 0], cfg['landscapes'], connected,
                                    flat['inner_height_median'])
    bound = landscapes.basin_necessary_bound(ground, [0, 0], cfg)
    assert flat['flat_ground_preference_met'] and ring['dry_mountain_basin_preference_met']
    assert bound['impossible']
    save('basin-lattice-counterexample.json', {'configuration_accepted': True,
         'refinement_spacing': 64, 'reference_flat': flat, 'reference_ring': ring,
         'early_bound': bound, 'reference_passes': True,
         'scope': 'Synthetic terrain: accepted nondefault spacing samples different local/full lattices.'})

    def possible(groups):
        boxes = [(-5000, -5000, 5000, 5000)]
        for points, scale, half in groups:
            next_boxes = []
            for p in points:
                b = ((p[0]-half)*scale, (p[1]-half)*scale,
                     (p[0]+half)*scale, (p[1]+half)*scale)
                for a in boxes:
                    q = (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))
                    if math.ceil(q[0]/8)*8 <= q[2] and math.ceil(q[1]/8)*8 <= q[3]:
                        next_boxes.append(q)
            boxes = next_boxes
            if not boxes:
                return False
        return bool(boxes)
    rows = []
    for index in range(100, 356):
        seed = seed_from_index(index) & 0xffffffff
        started = time.perf_counter()
        with Backend(seed) as b:
            fortress = b.structures('fortress', (-945, -945, 945, 945), False)
            bastion = b.structures('bastion', (-945, -945, 945, 945), False)
            village = b.structures('village', (-6152, -6152, 6152, 6152), False)
        elapsed = time.perf_counter()-started
        rows.append({'lower32': str(seed), 'seconds': elapsed,
                     'raw_counts': {'fortress': len(fortress), 'bastion': len(bastion), 'village': len(village)},
                     'fortress_possible': possible([(fortress, 8, 320)]),
                     'village_fortress_bastion_joint_possible': possible(
                         [(fortress, 8, 320), (bastion, 8, 320), (village, 1, 1152)])})
    save('raw-layout-selectivity.json', {'count': len(rows),
         'all_lower32_unique': len({r['lower32'] for r in rows}) == len(rows),
         'fortress_survivors': sum(r['fortress_possible'] for r in rows),
         'optional_village_bastion_joint_survivors': sum(r['village_fortress_bastion_joint_possible'] for r in rows),
         'scan_seconds': sum(r['seconds'] for r in rows),
         'scope': '256 fixed layouts; 2304/640 geometry. Existing Backend allocation included. Optional structures diagnostic only. No Stronghold/terrain/yield inference.',
         'rows': rows})
    with sqlite3.connect('file:runs/filter-optimization/pilot-20/checkpoint.sqlite?mode=ro', uri=True) as db:
        results = [json.loads(row[0]) for row in db.execute('SELECT result FROM seeds')]
    operations = defaultdict(Counter)
    for r in results:
        for key, value in r['cache']['operations'].items():
            operations[key].update(value)
    save('cache-audit.json', {'seeds': len(results),
         'evictions_total': sum(r['cache']['evictions'] for r in results),
         'seeds_with_evictions': sum(r['cache']['evictions'] > 0 for r in results),
         'max_cache_bytes': max(r['cache']['peak_bytes'] for r in results),
         'operations': {key: dict(value) for key, value in operations.items()}})
    from seed_search.review import apply_review, landscape_review_fields
    from seed_search.scoring import distinct_rank
    cfg, config_hash = load_config()
    candidate = next(c for r in results for c in r['candidates'] if c['score']['total'] is not None)
    review = {'seed': candidate['seed'], 'center': candidate['center'],
              'config_sha256': config_hash, 'landscape_type': candidate['landscape_type'],
              'source_kind': 'fresh_chunkbase_browser_UI',
              'source_url': 'https://www.chunkbase.com/apps/seed-map',
              'version': 'Bedrock 26.50 - 26.52', 'recorded_at': 'synthetic-audit-only',
              'browser_evidence': ['synthetic-no-browser-review-performed'],
              'terrain_enabled': True, 'dimensions_checked': ['overworld', 'nether'],
              'structures': {'stronghold': [], 'fortress': []},
              **{key: True for key in landscape_review_fields(candidate['landscape_type'])}}
    reviewed = apply_review(candidate, [review], cfg, config_hash)
    ranked = distinct_rank([reviewed], 20)
    save('review-ranking-counterexample.json', {
        'scope': 'Synthetic in-memory review only. No review imported; no browser evidence claimed. Empty lists mean unconfirmed required markers.',
        'seed': candidate['seed'], 'center': candidate['center'],
        'selection_status': reviewed['selection_status'],
        'native_required_status': reviewed['nether_status'],
        'score_total': reviewed['score']['total'],
        'list_membership': [key for key, values in ranked.items() if values],
        'confirmed_required': [reviewed['structures'][key]['confirmed_required_eligible'] for key in ('stronghold', 'fortress')]})
    assert ranked['ranked'] and not any(reviewed['structures'][key]['confirmed_required_eligible'] for key in ('stronghold', 'fortress'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile-seed', type=int)
    parser.add_argument('--checks', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.checks:
        checks()
    elif args.profile_seed is None:
        micro()
    else:
        profile(args.profile_seed)
