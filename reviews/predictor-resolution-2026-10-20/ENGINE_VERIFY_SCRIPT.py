"""Independent NumPy geometry oracle for every regenerated layout and preview."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

BASE = Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/predictor-engine-20261020')
sys.path.insert(0, str(BASE / 'integrated-runtime/src'))
import numpy as np
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.registry import STRUCTURES, BIOMES
from seed_search.catalog.models import observation_id, world_id
from seed_search.catalog.product_views import read_previews
from seed_search.catalog.evidence import read_evidence, validate_evidence
from seed_search.realm.biomes import canonical
from seed_search.catalog.index import validate_index
from seed_search.catalog.query import search
from seed_search.catalog.service import CatalogService
from seed_search.catalog.evaluation import heldout_cases

MISSING = (1 << 32) - 1
START = time.monotonic()


def budget():
    if time.monotonic() - START > 900:
        raise TimeoutError('Independent validation exceeded 900 seconds')
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if rss * (1 if sys.platform == 'darwin' else 1024) > 2 << 30:
        raise MemoryError('Independent validation exceeded 2GiB RSS')


def check_numeric(observation, layouts):
    """Does not call summarize, query predicates, or shared geometry helpers."""
    structures = [np.asarray(observation['structures'][f['id']], dtype=np.int64).reshape(-1, 2) for f in STRUCTURES]
    biomes = np.asarray(observation['biomes'], dtype=np.int64)
    biome_xy = biomes[:, [0, 2]]
    families = []
    for feature in BIOMES:
        members = set(feature['canonical_members'])
        ids = [int(k) for k, name in observation['biome_names'].items() if canonical(name) in members]
        families.append(np.isin(biomes[:, 3], ids))
    # Frozen public_policy.json uses inset edge anchors +/-976, not +/-1024.
    # Keep this explicit rather than calling the production geometry helper.
    axis = (-976, -768, -512, -256, 0, 256, 512, 768, 976)
    expected_geometries = {(x, z, side) for x in axis for z in axis for side in (2048, 4096, 8192)}
    seen = set(); oid = observation_id(observation); wid = world_id(observation['identity'])
    distances = {}
    for row in layouts:
        budget(); x, z = row['anchor']; side = row['border_side']
        geometry = x, z, side
        # Exact integer half-open squares; every predicate uses this same anchor.
        assert geometry in expected_geometries and geometry not in seen
        seen.add(geometry)
        assert row['world_id'] == wid and row['observation_id'] == oid and row['seed'] == observation['identity']['seed']
        lower = np.array([x - side // 2, z - side // 2], dtype=np.int64)
        upper = np.array([x + side // 2, z + side // 2], dtype=np.int64)
        anchor = np.array([x, z], dtype=np.int64)
        counts, nearest = [], []
        for points in structures:
            selected = points[np.all((points >= lower) & (points < upper), axis=1)]
            d2 = np.sum((selected - anchor) ** 2, axis=1)
            counts.append([int(np.count_nonzero(d2 <= r * r)) for r in (256, 512, 1024)] + [len(selected)])
            nearest.append(int(d2.min()) if len(d2) else MISSING)
        assert counts == row['counts'], ('structure counts', geometry)
        assert nearest == row['structure_nearest_d2'], ('structure nearest', geometry)
        inside = np.all((biome_xy >= lower) & (biome_xy < upper), axis=1)
        if (x, z) not in distances:
            distances[x, z] = np.sum((biome_xy - anchor) ** 2, axis=1)
        d2 = distances[x, z]; nearest, witnesses = [], []
        for family in families:
            indices = np.flatnonzero(family & inside)
            if len(indices):
                # flatnonzero is ascending; argmin therefore independently gives
                # the smallest original sample index on equal distance.
                chosen = int(indices[np.argmin(d2[indices])])
                nearest.append(int(d2[chosen])); witnesses.append(chosen)
            else:
                nearest.append(MISSING); witnesses.append(MISSING)
        assert nearest == row['biome_nearest_d2'], ('biome nearest', geometry)
        assert witnesses == row['biome_witness_refs'], ('biome witnesses', geometry)
        assert row['complete'] == [[True] * 4 for _ in range(23)]
    assert seen == expected_geometries
    return len(seen)


def verify(root, sid):
    totals = dict(worlds=0, layouts=0, biome_points=0, structure_points=0, evidence_worlds=0)
    expected_previews = {}; all_rows = []
    with SegmentedCatalog(root) as store:
        info = store.info(sid); store.audit(sid)
        previews = read_previews(root, sid, expected_header=info['header'])
        assert previews is not None
        expected_previews = {k: [] for k in previews['lists']}
        checked_detection = False
        for segment in store.iter_segments(sid):
            budget(); layouts = segment['layouts']
            validate_index(segment['index'], layouts=layouts, trusted=False)
            all_rows.extend(layouts)
            assert layouts and len({r['world_id'] for r in layouts}) == 1
            wid = layouts[0]['world_id']; obs = store.observation(sid, wid)
            totals['layouts'] += check_numeric(obs, layouts)
            if not checked_detection:
                import copy
                bad = copy.deepcopy(layouts)
                bad[0]['counts'][0][3] += 1
                try:
                    check_numeric(obs, bad)
                except AssertionError:
                    checked_detection = True
                else:
                    raise AssertionError('Independent oracle failed to detect perturbed count')
            totals['worlds'] += 1; totals['biome_points'] += len(obs['biomes'])
            totals['structure_points'] += sum(len(v) for v in obs['structures'].values())
            for name in expected_previews:
                feature = 'structure.' + name.split('.')[2]
                points = sorted(p for p in obs['structures'][feature] if p[0] * p[0] + p[1] * p[1] <= 4000000)
                if points:
                    expected_previews[name].append(dict(world_id=wid, seed=obs['identity']['seed'], count=len(points), witnesses=points[:5000]))
            audit = read_evidence(root, sid, wid, observation_id(obs))
            if audit is not None:
                validate_evidence(audit, observation=obs); totals['evidence_worlds'] += 1
            if totals['worlds'] % 20 == 0:
                print(json.dumps(dict(verified=totals['worlds'], seconds=time.monotonic() - START)), flush=True)
        for name, rows in expected_previews.items():
            rows.sort(key=lambda r: (-r['count'], r['world_id'])); rows = rows[:100]
            actual = [{k: r[k] for k in ('world_id', 'seed', 'count', 'witnesses')} for r in previews['lists'][name]]
            assert rows == actual, ('preview ranking', name)
        assert checked_detection and totals['worlds'] == 200 and totals['layouts'] == 48600
        assert totals['biome_points'] == 5120000
    service = CatalogService(root, query_seconds=30)
    query_measurements = []
    for side in (2048, 4096, 8192):
        for mode in ('origin', 'recommended'):
            for scenario in ('general', 'required', 'preferred'):
                budget()
                req = dict(heldout_cases()['cases'][0]['template'], catalog_snapshot_id=sid,
                    game_build_id=info['header']['game_build_id'], world_settings_id=info['header']['world_settings_id'],
                    border_side=side, anchor_mode=mode)
                if scenario == 'required':
                    req['rows'] = [dict(rule='required', kind='structure_count', feature='structure.village',
                        at_least=3, scope=dict(kind='near_base', radius=512))]
                if scenario == 'preferred':
                    req['rows'] = [dict(rule='preferred', kind='biome_witness', importance=5,
                        any_of=['biome.badlands', 'biome.mangrove_swamp'], scope=dict(kind='inside_border'))]
                expected = search(all_rows, req, snapshot_id=sid, limit=20)
                before = time.monotonic()
                actual = service.query(dict(request=req, page_size=20))
                key = lambda rows: [(r['world_id'], r['layout_id'], r['score']) for r in rows]
                assert key(expected) == key(actual['results']), ('query parity', side, mode, scenario)
                query_measurements.append(dict(side=side, mode=mode, scenario=scenario, seconds=time.monotonic()-before))
    budget()
    return dict(snapshot_id=sid, root=str(root), verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                **totals, all_numeric_fields_match=True,
                same_anchor_and_border_scope=True, all_preview_rankings_match=True,
                query_paths_match=True, query_measurements=query_measurements,
                perturbation_detected=True, wall_seconds=time.monotonic() - START)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.root, args.snapshot)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
