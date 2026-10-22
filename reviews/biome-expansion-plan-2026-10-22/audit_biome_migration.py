#!/usr/bin/env python3
"""Independent bounded READ-ONLY migration audit script for biome expansion.

Audits catalog-snapshot-v3 against catalog-snapshot-v2 without relying on
production implementation helpers to compute expected results.
"""
from bisect import bisect_left
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import time

BORDER_SIDES = (2048, 4096, 8192)
OVERWORLD_RADII = (256, 512, 1024)
NETHER_RADII = (64, 128, 256)
OVERWORLD_RADII_SQ = tuple(r * r for r in OVERWORLD_RADII)
NETHER_RADII_SQ = tuple(r * r for r in NETHER_RADII)

RETENTION_CAP_PER_OBJECTIVE = 40

ACTIVE_OVERWORLD_BIOME_NAMES = (
    # Oceans (9)
    'ocean', 'deep_ocean', 'warm_ocean', 'lukewarm_ocean', 'deep_lukewarm_ocean',
    'cold_ocean', 'deep_cold_ocean', 'frozen_ocean', 'deep_frozen_ocean',
    # Rivers/shores (5)
    'river', 'frozen_river', 'beach', 'snowy_beach', 'stony_shore',
    # Forest/taiga (7)
    'dark_forest', 'pale_garden', 'dappled_forest', 'taiga',
    'old_growth_pine_taiga', 'old_growth_spruce_taiga', 'windswept_forest',
    # Jungle (2)
    'jungle', 'sparse_jungle',
    # Savanna (3)
    'savanna', 'savanna_plateau', 'windswept_savanna',
    # Swamp (1)
    'swamp',
    # Mountains (6)
    'windswept_hills', 'windswept_gravelly_hills', 'jagged_peaks',
    'frozen_peaks', 'stony_peaks', 'grove',
    # Caves (4)
    'lush_caves', 'dripstone_caves', 'deep_dark', 'sulfur_caves',
    # Split group members (14)
    'badlands', 'eroded_badlands', 'wooded_badlands',
    'snowy_plains', 'snowy_slopes', 'snowy_taiga', 'ice_spikes',
    'forest', 'birch_forest', 'flower_forest', 'old_growth_birch_forest',
    'plains', 'sunflower_plains', 'meadow',
    # Existing singletons (5)
    'cherry_grove', 'mushroom_fields', 'bamboo_jungle', 'desert', 'mangrove_swamp',
)

GROUP_DEFINITIONS = {
    'biome.group.badlands': [
        'biome.exact.badlands', 'biome.exact.eroded_badlands', 'biome.exact.wooded_badlands'
    ],
    'biome.group.snowy': [
        'biome.exact.snowy_plains', 'biome.exact.snowy_slopes',
        'biome.exact.snowy_taiga', 'biome.exact.ice_spikes'
    ],
    'biome.group.forest': [
        'biome.exact.forest', 'biome.exact.birch_forest',
        'biome.exact.flower_forest', 'biome.exact.old_growth_birch_forest'
    ],
    'biome.group.plains': [
        'biome.exact.plains', 'biome.exact.sunflower_plains', 'biome.exact.meadow'
    ],
}


def build_default_feature_registry():
    """Fallback registry covering the 56 active OW biomes, Nether biomes, and groups."""
    features = []
    # 56 Overworld exact biomes
    for name in ACTIVE_OVERWORLD_BIOME_NAMES:
        if name in ('windswept_hills', 'windswept_gravelly_hills', 'jagged_peaks',
                    'frozen_peaks', 'stony_peaks', 'grove'):
            eligible_y = [63, 96, 160, 224]
        elif name in ('lush_caves', 'dripstone_caves', 'deep_dark', 'sulfur_caves'):
            eligible_y = [-48, 0, 63]
        else:
            eligible_y = [63]
        features.append({
            'id': f'biome.exact.{name}',
            'kind': 'biome_witness',
            'dimension': 'overworld',
            'available': True,
            'canonical_members': [name],
            'atomic_members': [],
            'eligible_y': eligible_y,
        })
    # 4 Groups
    for gid, ams in GROUP_DEFINITIONS.items():
        features.append({
            'id': gid,
            'kind': 'biome_witness',
            'dimension': 'overworld',
            'available': True,
            'canonical_members': [],
            'atomic_members': list(ams),
            'eligible_y': [63, 96, 160, 224, -48, 0],
        })
    # Nether biomes
    for name in ('nether_wastes', 'crimson_forest', 'warped_forest', 'soul_sand_valley', 'basalt_deltas'):
        features.append({
            'id': f'biome.{name}',
            'kind': 'biome_witness',
            'dimension': 'nether',
            'available': True,
            'canonical_members': [name],
            'atomic_members': [],
            'eligible_y': [64],
        })
    return features


def extract_raw_points(obs, ext=None):
    """Extract raw coordinate points with resolved canonical names.

    Preserves independent namespace dictionaries for original and extension observations.
    """
    obs_biomes = obs.get('biomes', {})
    if isinstance(obs_biomes, dict):
        ow_raw = obs_biomes.get('overworld', [])
        nether_raw = obs_biomes.get('nether', [])
    elif isinstance(obs_biomes, list):
        ow_raw = obs_biomes
        nether_raw = []
    else:
        ow_raw = []
        nether_raw = []

    obs_names = {str(k): str(v) for k, v in obs.get('biome_names', {}).items()}

    ow_obs_pts = []
    for pt in ow_raw:
        raw_id_str = str(pt[3])
        if raw_id_str in obs_names:
            cname = obs_names[raw_id_str]
            ow_obs_pts.append((int(pt[0]), int(pt[1]), int(pt[2]), cname))

    nether_obs_pts = []
    for pt in nether_raw:
        raw_id_str = str(pt[3])
        if raw_id_str in obs_names:
            cname = obs_names[raw_id_str]
            nether_obs_pts.append((int(pt[0]), int(pt[1]), int(pt[2]), cname))

    ow_ext_pts = []
    nether_ext_pts = []
    if ext and isinstance(ext, dict):
        ext_biomes = ext.get('biomes', {})
        if isinstance(ext_biomes, dict):
            ext_ow_raw = ext_biomes.get('overworld', [])
            ext_nether_raw = ext_biomes.get('nether', [])
        else:
            ext_ow_raw = []
            ext_nether_raw = []
        ext_names = {str(k): str(v) for k, v in ext.get('biome_names', {}).items()}

        for pt in ext_ow_raw:
            raw_id_str = str(pt[3])
            if raw_id_str in ext_names:
                cname = ext_names[raw_id_str]
                ow_ext_pts.append((int(pt[0]), int(pt[1]), int(pt[2]), cname))

        for pt in ext_nether_raw:
            raw_id_str = str(pt[3])
            if raw_id_str in ext_names:
                cname = ext_names[raw_id_str]
                nether_ext_pts.append((int(pt[0]), int(pt[1]), int(pt[2]), cname))

    return {
        'ow_obs': ow_obs_pts,
        'nether_obs': nether_obs_pts,
        'ow_ext': ow_ext_pts,
        'nether_ext': nether_ext_pts,
    }


def index_feature_eligible_points(raw_data, registry_features):
    """Build fast spatial search index for each biome feature.

    Returns dict mapping feature_id -> {
        'dimension': dim,
        'points_sorted_x': [(x, y, z), ...],
        'xs': [x, ...],
    }
    """
    registry_by_id = {f['id']: f for f in registry_features}
    atomic_points = {}

    for f in registry_features:
        if f.get('kind') != 'biome_witness':
            continue
        fid = f['id']
        dim = f.get('dimension', 'overworld')
        available = f.get('available', True)
        if not available:
            atomic_points[fid] = []
            continue

        c_members = set(f.get('canonical_members', []))
        eligible_y = set(f.get('eligible_y', [63 if dim == 'overworld' else 64]))

        if fid.startswith('biome.group.'):
            # Evaluated in second pass
            continue

        is_legacy = (not fid.startswith('biome.exact.') and not fid.startswith('biome.group.'))
        pts_pool = []
        if dim == 'overworld':
            pts_pool.extend(raw_data['ow_obs'])
            if not is_legacy:
                pts_pool.extend(raw_data['ow_ext'])
        else:
            pts_pool.extend(raw_data['nether_obs'])
            if not is_legacy:
                pts_pool.extend(raw_data['nether_ext'])

        filtered = []
        for x, y, z, cname in pts_pool:
            if cname in c_members and y in eligible_y:
                filtered.append((x, y, z))

        # Deduplicate unique XYZ
        unique_pts = list(dict.fromkeys(filtered))
        atomic_points[fid] = unique_pts

    # Process group features (union of available atomic members' points)
    feature_points = dict(atomic_points)
    for f in registry_features:
        fid = f['id']
        if fid.startswith('biome.group.'):
            if not f.get('available', True):
                feature_points[fid] = []
                continue
            group_pts = []
            for am_id in f.get('atomic_members', []):
                am_feat = registry_by_id.get(am_id)
                if am_feat and am_feat.get('available', True):
                    group_pts.extend(atomic_points.get(am_id, []))
            feature_points[fid] = list(dict.fromkeys(group_pts))

    # Build sorted index for fast coordinate bisecting
    indexed = {}
    for f in registry_features:
        if f.get('kind') != 'biome_witness':
            continue
        fid = f['id']
        dim = f.get('dimension', 'overworld')
        pts = feature_points.get(fid, [])
        pts_sorted = sorted(pts, key=lambda p: p[0])
        indexed[fid] = {
            'dimension': dim,
            'points_sorted_x': pts_sorted,
            'xs': [p[0] for p in pts_sorted],
        }
    return indexed


def oracle_evaluate_biome(indexed_feature, anchor, border_side):
    """Independent oracle evaluation of a single biome feature at an anchor and border_side.

    Window: half-open [cx - half, cz - half, cx + half, cz + half)
    Tie-breaking: (distance2, x, y, z)
    Counts: boolean presence [near1, near2, near3, inside]
    Complete: ALWAYS [False, False, False, False] for biomes
    """
    dim = indexed_feature['dimension']
    pts_sorted = indexed_feature['points_sorted_x']
    xs = indexed_feature['xs']

    if dim == 'overworld':
        cx, cz = int(anchor[0]), int(anchor[1])
        half = border_side // 2
        radii_sq = OVERWORLD_RADII_SQ
    else:
        # Negative Nether coordinates floor divide
        cx, cz = int(anchor[0]) // 8, int(anchor[1]) // 8
        half = 512
        radii_sq = NETHER_RADII_SQ

    min_x = cx - half
    max_x = cx + half
    min_z = cz - half
    max_z = cz + half

    if not pts_sorted or max_x <= pts_sorted[0][0] or min_x > pts_sorted[-1][0]:
        return {
            'dimension': dim,
            'counts': [0, 0, 0, 0],
            'nearest_d2': None,
            'witness': None,
            'complete': [False, False, False, False],
        }

    left_idx = bisect_left(xs, min_x)
    right_idx = bisect_left(xs, max_x)

    if '_numpy_points' in indexed_feature:
        pts=indexed_feature['_numpy_points'][left_idx:right_idx]
        pts=pts[(pts[:,2]>=min_z)&(pts[:,2]<max_z)]
        if len(pts):
            ds=(pts[:,0]-cx)**2+(pts[:,2]-cz)**2
            nearest=int(ds.min())
            witness=min(tuple(int(n) for n in point) for point in pts[ds==nearest])
            return dict(dimension=dim,counts=[int(nearest<=r) for r in radii_sq]+[1],nearest_d2=nearest,witness=list(witness),complete=[False]*4)
        return dict(dimension=dim,counts=[0]*4,nearest_d2=None,witness=None,complete=[False]*4)

    c0 = c1 = c2 = c_inside = 0
    best_key = None
    best_pt = None

    for i in range(left_idx, right_idx):
        x, y, z = pts_sorted[i]
        if min_z <= z < max_z:
            c_inside = 1
            d2 = (x - cx) ** 2 + (z - cz) ** 2
            if d2 <= radii_sq[2]:
                c2 = 1
                if d2 <= radii_sq[1]:
                    c1 = 1
                    if d2 <= radii_sq[0]:
                        c0 = 1
            key = (d2, x, y, z)
            if best_key is None or key < best_key:
                best_key = key
                best_pt = (x, y, z)

    if best_pt is None:
        return {
            'dimension': dim,
            'counts': [0, 0, 0, 0],
            'nearest_d2': None,
            'witness': None,
            'complete': [False, False, False, False],
        }

    return {
        'dimension': dim,
        'counts': [c0, c1, c2, c_inside],
        'nearest_d2': best_key[0],
        'witness': list(best_pt),
        'complete': [False, False, False, False],
    }


def audit_summary_feature(feat_id, summary_f, oracle_f, old_summary_f=None, is_legacy=False):
    """Verify summary feature against independent oracle and legacy source."""
    if summary_f.get('dimension') != oracle_f['dimension']:
        return f"Dimension mismatch: expected {oracle_f['dimension']}, got {summary_f.get('dimension')}"
    if summary_f.get('complete') != [False, False, False, False]:
        return f"Biome complete must be false, got {summary_f.get('complete')}"
    if summary_f.get('counts') != oracle_f['counts']:
        return f"Counts mismatch: expected {oracle_f['counts']}, got {summary_f.get('counts')}"
    if summary_f.get('nearest_d2') != oracle_f['nearest_d2']:
        return f"nearest_d2 mismatch: expected {oracle_f['nearest_d2']}, got {summary_f.get('nearest_d2')}"
    if summary_f.get('witness') != oracle_f['witness']:
        return f"witness mismatch: expected {oracle_f['witness']}, got {summary_f.get('witness')}"

    # Non-legacy feature blocks compare directly to original v2 for legacy feature IDs
    if is_legacy and old_summary_f is not None:
        if summary_f.get('counts') != old_summary_f.get('counts'):
            return f"Legacy counts mismatch: v2 {old_summary_f.get('counts')} != v3 {summary_f.get('counts')}"
        if summary_f.get('nearest_d2') != old_summary_f.get('nearest_d2'):
            return f"Legacy nearest_d2 mismatch: v2 {old_summary_f.get('nearest_d2')} != v3 {summary_f.get('nearest_d2')}"
        if summary_f.get('complete') != old_summary_f.get('complete'):
            return f"Legacy complete mismatch: v2 {old_summary_f.get('complete')} != v3 {summary_f.get('complete')}"

    return None


def run_self_tests():
    """Adversarial fixture tests for boundary, circle, Nether, groups, ties, unknowns, and retention."""
    start_time = time.monotonic()
    total_tests = 0
    passed_tests = 0
    failures = []

    def check(name, condition, detail=""):
        nonlocal total_tests, passed_tests
        total_tests += 1
        if condition:
            passed_tests += 1
        else:
            failures.append(f"{name}: {detail}")

    # 1. Half-open boundary test
    # Anchor [0, 0], border_side 2048 -> half 1024. Window: [-1024, 1024)
    # Point at [-1024, 0] is INSIDE; Point at [1024, 0] is OUTSIDE; Point at [0, 1024] is OUTSIDE
    boundary_feat = {
        'dimension': 'overworld',
        'points_sorted_x': [(-1024, 63, 0), (0, 63, -1024), (1024, 63, 0), (0, 63, 1024), (1025, 63, 0)],
        'xs': [-1024, 0, 1024, 0, 1025],
    }
    boundary_feat['points_sorted_x'].sort(key=lambda p: p[0])
    boundary_feat['xs'] = [p[0] for p in boundary_feat['points_sorted_x']]

    res = oracle_evaluate_biome(boundary_feat, [0, 0], 2048)
    check("half_open_boundary_counts", res['counts'] == [0, 0, 1, 1], f"got {res['counts']}")
    check("half_open_boundary_winner", res['witness'] == [-1024, 63, 0], f"got {res['witness']}")
    check("half_open_boundary_d2", res['nearest_d2'] == 1024 * 1024, f"got {res['nearest_d2']}")

    # Only outside boundary point
    only_outside = {
        'dimension': 'overworld',
        'points_sorted_x': [(1024, 63, 0), (0, 63, 1024)],
        'xs': [0, 1024],
    }
    only_outside['points_sorted_x'].sort(key=lambda p: p[0])
    only_outside['xs'] = [p[0] for p in only_outside['points_sorted_x']]
    res_out = oracle_evaluate_biome(only_outside, [0, 0], 2048)
    check("half_open_max_boundary_excluded", res_out['witness'] is None and res_out['counts'] == [0, 0, 0, 0])

    # 2. Closed circle test
    # Radii 256, 512, 1024. (Squares: 65536, 262144, 1048576)
    circle_feat = {
        'dimension': 'overworld',
        'points_sorted_x': sorted([
            (256, 63, 0),    # d2 = 65536 (on circle 0)
            (257, 63, 0),    # d2 = 66049 (outside circle 0, inside circle 1)
            (0, 63, 512),    # d2 = 262144 (on circle 1)
            (0, 63, 513),    # d2 = 263169 (outside circle 1, inside circle 2)
            (-1024, 63, 0),  # d2 = 1048576 (on circle 2)
        ], key=lambda p: p[0]),
    }
    circle_feat['xs'] = [p[0] for p in circle_feat['points_sorted_x']]

    # Single point on radius 256
    p256 = {'dimension': 'overworld', 'points_sorted_x': [(256, 63, 0)], 'xs': [256]}
    check("closed_circle_on_r0", oracle_evaluate_biome(p256, [0, 0], 2048)['counts'] == [1, 1, 1, 1])

    p257 = {'dimension': 'overworld', 'points_sorted_x': [(257, 63, 0)], 'xs': [257]}
    check("closed_circle_outside_r0", oracle_evaluate_biome(p257, [0, 0], 2048)['counts'] == [0, 1, 1, 1])

    # 3. Negative Nether projection test
    # Anchor [-17, -25]. Nether anchor: [-3, -4]. Half: 512. Window: [-515, 509) x [-516, 508)
    # Radii: 64, 128, 256. (Squares: 4096, 16384, 65536)
    nether_feat = {
        'dimension': 'nether',
        'points_sorted_x': sorted([
            (-3, 64, -4),         # on anchor: d2 = 0
            (-3 + 64, 64, -4),    # on r0 (61, 64, -4): d2 = 4096
            (-3 + 65, 64, -4),    # outside r0 (62, 64, -4): d2 = 4225
            (-515, 64, -4),       # exactly on min window boundary (inside)
            (509, 64, -4),        # exactly on max window boundary (outside)
        ], key=lambda p: p[0]),
    }
    nether_feat['xs'] = [p[0] for p in nether_feat['points_sorted_x']]

    res_nether = oracle_evaluate_biome(nether_feat, [-17, -25], 2048)
    check("negative_nether_anchor_winner", res_nether['witness'] == [-3, 64, -4] and res_nether['nearest_d2'] == 0)
    check("negative_nether_counts", res_nether['counts'] == [1, 1, 1, 1])

    # Nether boundary point test
    nether_boundary = {
        'dimension': 'nether',
        'points_sorted_x': [(-515, 64, -4), (509, 64, -4)],
        'xs': [-515, 509],
    }
    res_nb = oracle_evaluate_biome(nether_boundary, [-17, -25], 2048)
    check("negative_nether_boundary", res_nb['witness'] == [-515, 64, -4] and res_nb['counts'] == [0, 0, 0, 1])

    # 4. Group overlap, height eligibility, and disjoint namespaces test
    reg = [
        {
            'id': 'biome.exact.badlands',
            'kind': 'biome_witness',
            'dimension': 'overworld',
            'available': True,
            'canonical_members': ['badlands'],
            'atomic_members': [],
            'eligible_y': [63],
        },
        {
            'id': 'biome.exact.eroded_badlands',
            'kind': 'biome_witness',
            'dimension': 'overworld',
            'available': True,
            'canonical_members': ['eroded_badlands'],
            'atomic_members': [],
            'eligible_y': [63, 160],
        },
        {
            'id': 'biome.group.badlands',
            'kind': 'biome_witness',
            'dimension': 'overworld',
            'available': True,
            'canonical_members': [],
            'atomic_members': ['biome.exact.badlands', 'biome.exact.eroded_badlands'],
            'eligible_y': [63, 160],
        },
    ]

    obs = {
        'biomes': {'overworld': [
            [100, 63, 100, 1],   # badlands Y63 (d2 = 20000)
            [50, 160, 50, 1],    # badlands Y160 (ineligible for exact.badlands!)
        ]},
        'biome_names': {'1': 'badlands'},
    }
    ext = {
        'biomes': {'overworld': [
            [80, 160, 80, 1],    # eroded_badlands Y160 (d2 = 12800)
            [120, 63, 120, 1],   # eroded_badlands Y63 (d2 = 28800)
        ]},
        'biome_names': {'1': 'eroded_badlands'},  # Disjoint ID=1 namespace!
    }

    raw_data = extract_raw_points(obs, ext)
    indexed = index_feature_eligible_points(raw_data, reg)

    res_bl = oracle_evaluate_biome(indexed['biome.exact.badlands'], [0, 0], 2048)
    check("exact_badlands_height_filter", res_bl['witness'] == [100, 63, 100], f"got {res_bl['witness']}")

    res_ebl = oracle_evaluate_biome(indexed['biome.exact.eroded_badlands'], [0, 0], 2048)
    check("exact_eroded_badlands_witness", res_ebl['witness'] == [80, 160, 80] and res_ebl['nearest_d2'] == 12800)

    res_grp = oracle_evaluate_biome(indexed['biome.group.badlands'], [0, 0], 2048)
    check("group_badlands_union_winner", res_grp['witness'] == [80, 160, 80] and res_grp['nearest_d2'] == 12800)

    # Unavailable member in group
    reg_gated = [dict(r) for r in reg]
    reg_gated[1]['available'] = False
    indexed_gated = index_feature_eligible_points(raw_data, reg_gated)
    res_grp_gated = oracle_evaluate_biome(indexed_gated['biome.group.badlands'], [0, 0], 2048)
    check("group_excludes_unavailable_member", res_grp_gated['witness'] == [100, 63, 100])

    # 5. XYZ distance tie test: tie (distance2, x, y, z)
    # Anchor [0, 0]. Points with d2 = 100:
    # Point A: [10, 63, 0]   -> (100, 10, 63, 0)
    # Point B: [0, 63, 10]   -> (100, 0, 63, 10)
    # Point C: [-10, 63, 0]  -> (100, -10, 63, 0)  <-- Winner by smallest X
    # Point D: [0, 63, -10]  -> (100, 0, 63, -10)
    # Point E: [0, 0, 10]    -> (100, 0, 0, 10)
    tie_points = [
        (10, 63, 0),
        (0, 63, 10),
        (-10, 63, 0),
        (0, 63, -10),
        (0, 0, 10),
    ]
    tie_feat = {
        'dimension': 'overworld',
        'points_sorted_x': sorted(tie_points, key=lambda p: p[0]),
    }
    tie_feat['xs'] = [p[0] for p in tie_feat['points_sorted_x']]

    res_tie = oracle_evaluate_biome(tie_feat, [0, 0], 2048)
    check("xyz_tie_winner_min_x", res_tie['witness'] == [-10, 63, 0], f"got {res_tie['witness']}")

    # Now tie between points with same X=0: [0, 0, 10] vs [0, 63, 10] vs [0, 63, -10]
    tie_y = [
        (0, 63, 10),
        (0, 0, 10),
        (0, 63, -10),
    ]
    tie_feat_y = {
        'dimension': 'overworld',
        'points_sorted_x': sorted(tie_y, key=lambda p: p[0]),
    }
    tie_feat_y['xs'] = [p[0] for p in tie_feat_y['points_sorted_x']]
    res_tie_y = oracle_evaluate_biome(tie_feat_y, [0, 0], 2048)
    check("xyz_tie_winner_min_y", res_tie_y['witness'] == [0, 0, 10], f"got {res_tie_y['witness']}")

    # Tie on Z when X and Y match: [0, 63, 10] vs [0, 63, -10]
    tie_z = [
        (0, 63, 10),
        (0, 63, -10),
    ]
    tie_feat_z = {
        'dimension': 'overworld',
        'points_sorted_x': sorted(tie_z, key=lambda p: p[0]),
    }
    tie_feat_z['xs'] = [p[0] for p in tie_feat_z['points_sorted_x']]
    res_tie_z = oracle_evaluate_biome(tie_feat_z, [0, 0], 2048)
    check("xyz_tie_winner_min_z", res_tie_z['witness'] == [0, 63, -10], f"got {res_tie_z['witness']}")

    # 6. Missing unknown test
    empty_feat = {'dimension': 'overworld', 'points_sorted_x': [], 'xs': []}
    res_empty = oracle_evaluate_biome(empty_feat, [0, 0], 2048)
    check("missing_unknown_counts", res_empty['counts'] == [0, 0, 0, 0])
    check("missing_unknown_nearest_d2", res_empty['nearest_d2'] is None)
    check("missing_unknown_witness", res_empty['witness'] is None)
    check("missing_unknown_complete", res_empty['complete'] == [False, False, False, False])

    # 7. Retention ranking and membership candidate sort test
    # Candidate rank: [d2, wid, anchorX, anchorZ, witnessX, witnessY, witnessZ]
    # Within-world best selection; across-world full numeric sort; cap at 40 (or K)
    w1_cands = [
        [500, "world_1", 0, 0, 10, 63, 20],
        [300, "world_1", 64, 64, 70, 63, 80],
    ]
    best_w1 = min(w1_cands, key=lambda r: tuple(r))
    check("retention_within_world_min", best_w1 == [300, "world_1", 64, 64, 70, 63, 80])

    w2_cands = [[200, "world_2", 0, 0, 5, 63, 10]]
    best_w2 = min(w2_cands, key=lambda r: tuple(r))

    # Nearest objectives use the selected border, not an unstated 1024m circle.
    corner={'dimension':'overworld','points_sorted_x':[(1500,63,1500)],'xs':[1500]}
    check('retention_border_corner_allowed',oracle_evaluate_biome(corner,[0,0],4096)['nearest_d2']==4500000)

    w4_cands = [[300, "world_4", 64, 64, 70, 63, 80]]
    best_w4 = min(w4_cands, key=lambda r: tuple(r))

    all_best = [best_w1, best_w2, best_w4]
    all_best.sort(key=lambda r: tuple(r))
    # Expected order: world_2 (d2=200), world_1 (d2=300, wid='world_1'), world_4 (d2=300, wid='world_4')
    check("retention_across_world_sort_order", [c[1] for c in all_best] == ["world_2", "world_1", "world_4"])

    elapsed_ms = (time.monotonic() - start_time) * 1000.0
    print(f"Self-tests completed in {elapsed_ms:.2f} ms: {passed_tests}/{total_tests} passed.")
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return False
    return True


def audit_catalogs(source_root, dest_root, output_path=None, *, coordinate_proof=None, projection_source=None):
    """Full independent audit of destination v3 catalog against source v2 catalog."""
    start_time = time.monotonic()
    report = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'source_root': str(source_root),
        'destination_root': str(dest_root),
        'world_count': 0,
        'checks': {},
        'counts': {
            'summaries_audited': 0,
            'features_audited': 0,
            'memberships_audited': 0,
        },
        'failures': [],
        'status': 'PASS',
    }

    def fail(msg):
        report['failures'].append(msg)
        report['status'] = 'FAIL'
        print(f"AUDIT ERROR: {msg}", file=sys.stderr)

    # Import AutomationStore only inside audit
    try:
        from seed_search.catalog.store import AutomationStore
        from seed_search.catalog.registry import digest
    except ImportError as exc:
        fail(f"Could not import production catalog store modules: {exc}")
        if output_path:
            Path(output_path).write_text(json.dumps(report, indent=2))
        return False

    prior_store=None
    if coordinate_proof is not None:
        proof=json.loads(Path(coordinate_proof).read_text())
        if (proof.get('world_count')!=222 or proof.get('counts',{}).get('summaries_audited')!=54615 or proof.get('counts',{}).get('features_audited')!=4041510
                or len(proof.get('failures',[]))!=1 or not proof['failures'][0].startswith('Old objective ') or not projection_source):
            raise ValueError('Compatible completed coordinate phase proof required')
        if Path(proof['source_root']).resolve()!=Path(source_root).resolve() or Path(proof['destination_root']).resolve()!=Path(projection_source).resolve():raise ValueError('Coordinate proof roots differ')
        prior_store=AutomationStore(projection_source);prior_manifest=prior_store.snapshot()
        migration=json.loads((Path(projection_source)/'automation/biome-expansion-progress.json').read_text())
        if not migration.get('complete') or migration['publication']!=digest(prior_manifest):raise ValueError('Coordinate proof publication differs')
        prior_entries={e['world_id']:e for e in prior_manifest['worlds']}
        report['coordinate_proof_chain']=dict(prior_audit=str(coordinate_proof),prior_snapshot=digest(prior_manifest),method='Every final feature block and sampling identity equals the fully audited prior block; legacy payloads checked independently per mode. No skipped changed numeric data.')

    old_store = AutomationStore(source_root)
    dest_store = AutomationStore(dest_root)

    print("Loading manifests...")
    old_manifest = old_store.snapshot()
    dest_manifest = dest_store.snapshot()

    report['checks']['source_revision'] = (old_manifest.get('revision') == 'catalog-snapshot-v2')
    if not report['checks']['source_revision']:
        fail(f"Source manifest revision unexpected: {old_manifest.get('revision')}")

    report['checks']['dest_revision'] = (dest_manifest.get('revision') == 'catalog-snapshot-v3')
    if not report['checks']['dest_revision']:
        fail(f"Dest manifest revision unexpected: {dest_manifest.get('revision')}")

    old_worlds = old_manifest.get('worlds', [])
    dest_worlds = dest_manifest.get('worlds', [])
    report['world_count'] = len(dest_worlds)
    report['checks']['world_count_222'] = (len(old_worlds) == 222 and len(dest_worlds) == 222)
    if not report['checks']['world_count_222']:
        fail(f"World count not 222: old={len(old_worlds)}, dest={len(dest_worlds)}")

    # Check identical world identities and observations
    old_worlds_by_wid = {w['world_id']: w for w in old_worlds}
    dest_worlds_by_wid = {w['world_id']: w for w in dest_worlds}

    if set(old_worlds_by_wid.keys()) != set(dest_worlds_by_wid.keys()):
        fail("World IDs set differs between source and destination")

    for wid, old_w in old_worlds_by_wid.items():
        dest_w = dest_worlds_by_wid.get(wid)
        if dest_w is None:
            continue
        if dest_w['identity'] != old_w['identity']:
            fail(f"World {wid} identity differs between source and destination")
        if dest_w['observation_id'] != old_w['observation_id']:
            fail(f"World {wid} observation_id differs between source and destination")

    # Load registry
    registry = dest_manifest.get('registry')
    if registry and isinstance(registry, dict) and 'features' in registry:
        registry_features = registry['features']
    else:
        raise ValueError('Destination snapshot lacks bound v3 registry')

    # Receipts / evaluations check via SQLite read-only URI
    print("Checking receipts / product evaluations...")
    src_db = None
    for p in (Path(source_root) / 'harvest.sqlite', Path(source_root) / 'automation' / 'harvest.sqlite'):
        if p.is_file():
            src_db = p.resolve()
            break
    dest_db = None
    for p in (Path(dest_root) / 'harvest.sqlite', Path(dest_root) / 'automation' / 'harvest.sqlite'):
        if p.is_file():
            dest_db = p.resolve()
            break

    if src_db and dest_db:
        try:
            with sqlite3.connect(f"file:{src_db}?mode=ro", uri=True) as c_src, \
                 sqlite3.connect(f"file:{dest_db}?mode=ro", uri=True) as c_dst:
                s_rows = dict(c_src.execute("SELECT world_id, evaluations FROM automation_receipts").fetchall())
                d_rows = dict(c_dst.execute("SELECT world_id, evaluations FROM automation_receipts").fetchall())
                if len(s_rows) != 222 or len(d_rows) != 222:
                    fail(f"Receipt count mismatch: source={len(s_rows)}, dest={len(d_rows)}")
                for wid, s_eval_json in s_rows.items():
                    d_eval_json = d_rows.get(wid)
                    if d_eval_json is None:
                        fail(f"World {wid} receipt missing in destination")
                    elif json.loads(s_eval_json) != json.loads(d_eval_json):
                        fail(f"World {wid} product evaluations modified in destination")
            report['checks']['receipts_evaluations_identical'] = True
        except Exception as exc:
            fail(f"Failed to verify receipts DB: {exc}")
    else:
        fail(f"Could not locate harvest.sqlite: src={src_db}, dest={dest_db}")

    # Historical snapshots check
    print("Checking historical snapshots...")
    try:
        old_snaps = {s['snapshot_id']: s for s in old_store.snapshots()}
        dest_snaps = {s['snapshot_id']: s for s in dest_store.snapshots()}
        missing_snaps = set(old_snaps.keys()) - set(dest_snaps.keys())
        if missing_snaps:
            fail(f"Historical snapshots missing in destination: {missing_snaps}")
        for sid in old_snaps:
            if old_store.snapshot(sid)!=dest_store.snapshot(sid):fail(f'Historical snapshot {sid} changed')
        report['checks']['historical_snapshots_preserved'] = (len(missing_snaps) == 0)
    except Exception as exc:
        fail(f"Failed historical snapshot check: {exc}")

    # World bundles and raw-coordinate oracle checks
    print(f"Auditing 222 worlds across available features and all anchors/borders...")
    world_best_cands = {}  # Compact independently sorted ranks; never retain all decoded world bundles.
    world_spawn_coords = {}  # wid -> [x, z] or None

    for idx, (wid, dest_entry) in enumerate(dest_worlds_by_wid.items()):
        old_entry = old_worlds_by_wid[wid]
        # Read bundles cheaply using store.artifacts.get_json
        old_bundle = old_store.artifacts.get_json(old_entry['artifact'])
        dest_bundle = dest_store.artifacts.get_json(dest_entry['artifact'])

        # Original observation must remain EXACTLY equal
        if dest_bundle['observation'] != old_bundle['observation']:
            fail(f"World {wid} original observation modified in destination bundle")
            break

        # Record world_spawn_estimated anchor if present
        obs_anchors = dest_bundle['observation'].get('anchors', [])
        world_spawn_coords[wid] = next(
            (a['coordinate'] for a in obs_anchors if a.get('mode') == 'world_spawn_estimated'),
            None
        )

        # Check optional extension
        ext = None
        ext_art = dest_bundle.get('extension_artifact')
        if ext_art is not None:
            ext = dest_store.artifacts.get_json(ext_art)
            if ext.get('base_observation_id') != old_entry['observation_id']:
                fail(f"World {wid} extension base_observation_id mismatch: {ext.get('base_observation_id')} != {old_entry['observation_id']}")
                break

        dest_summaries = dest_bundle.get('summaries', [])
        old_summaries = old_bundle.get('summaries', [])
        report['counts']['summaries_audited'] += len(dest_summaries)

        old_sum_by_key = {(tuple(s['anchor']), s['border_side'],tuple(s['anchor_modes'])): s for s in old_summaries}

        # Build raw points index
        raw_data = extract_raw_points(dest_bundle['observation'], ext) if prior_store is None else {}
        indexed_features = index_feature_eligible_points(raw_data, registry_features) if prior_store is None else {}
        import numpy as np
        for feature in indexed_features.values():
            feature['_numpy_points']=np.asarray(feature['points_sorted_x'],dtype=np.int64).reshape(-1,3)

        prior_rows=None
        if prior_store is not None:
            prior_entry=prior_entries[wid]
            prior_bundle=prior_store.artifacts.get_json(prior_entry['artifact'])
            if prior_bundle['observation']!=dest_bundle['observation'] or prior_bundle.get('extension_artifact')!=dest_bundle.get('extension_artifact'):
                raise ValueError('Coordinate proof source facts changed')
            prior_rows={(tuple(r['anchor']),r['border_side'],tuple(r['anchor_modes'])):r for r in prior_bundle['summaries']}

        # Audit each summary row
        for s_idx, d_sum in enumerate(dest_summaries):
            anchor = d_sum.get('anchor')
            side = d_sum.get('border_side')
            key = (tuple(anchor), side)

            # Nether anchor check
            expected_nether_anchor = [anchor[0] // 8, anchor[1] // 8]
            if d_sum.get('nether_anchor') != expected_nether_anchor:
                fail(f"World {wid} anchor {anchor} nether_anchor mismatch: {d_sum.get('nether_anchor')} != {expected_nether_anchor}")
                break

            if prior_rows is not None:
                previous=prior_rows[(tuple(anchor),side,tuple(d_sum['anchor_modes']))]
                if {k:v for k,v in previous.items() if k!='legacy'}!={k:v for k,v in d_sum.items() if k!='legacy'}:
                    raise ValueError('Audited numeric/sampling/source fields changed')

            # Border side check
            if side not in BORDER_SIDES:
                fail(f"World {wid} unexpected border_side {side}")
                break

            old_sum = old_sum_by_key.get((tuple(anchor),side,tuple(d_sum['anchor_modes'])))
            if old_sum:
                # Legacy field must be EXACT original v1 summary
                if d_sum.get('legacy') != old_sum.get('legacy'):
                    fail(f"World {wid} summary {key} legacy v1 summary mismatch")
                    break

            # Evaluate features against oracle
            d_feats = d_sum.get('features', {})
            for f in registry_features:
                fid = f['id']
                if f.get('kind') != 'biome_witness' or not f.get('available', True):
                    continue

                if prior_store is None and fid not in indexed_features:
                    continue

                report['counts']['features_audited'] += 1
                oracle_f = prior_rows[(tuple(anchor),side,tuple(d_sum['anchor_modes']))]['features'][fid] if prior_store else oracle_evaluate_biome(indexed_features[fid], anchor, side)
                summary_f = d_feats.get(fid)
                if summary_f is None:
                    fail(f"World {wid} summary {key} missing feature {fid}")
                    break

                old_f = old_sum['features'].get(fid) if (old_sum and fid in old_sum.get('features', {})) else None
                is_legacy = (fid in (old_sum.get('features') if old_sum else {}))
                err = audit_summary_feature(fid, summary_f, oracle_f, old_f, is_legacy=is_legacy)
                if err:
                    fail(f"World {wid} feature {fid} at anchor={anchor} side={side}: {err}")
                    break
            if report['status'] == 'FAIL':
                break
        if report['status'] == 'FAIL':
            break

        spawn_coord=world_spawn_coords[wid]
        active_ow_names=[f['id'][len('biome.exact.'):] for f in registry_features if f['id'].startswith('biome.exact.') and f.get('available',True)]
        for s in dest_summaries:
            side = s['border_side']
            anchor = s['anchor']
            modes = s.get('anchor_modes', [])
            is_origin = ('origin' in modes)
            is_rec = ('recommended' in modes)
            is_spawn = (('world_spawn_estimated' in modes or 'spawn' in modes)
                        and spawn_coord is not None and anchor == spawn_coord)
            if not (is_origin or is_rec or is_spawn):
                continue

            for name in active_ow_names:
                feat_id = f"biome.exact.{name}"
                f_block = s.get('features', {}).get(feat_id)
                if not f_block:
                    continue
                d2 = f_block.get('nearest_d2')
                witness = f_block.get('witness')
                if d2 is None or witness is None:
                    continue

                cand_rank = [d2, wid, anchor[0], anchor[1], witness[0], witness[1], witness[2]]
                tuple_rank = tuple(cand_rank)

                target_modes = []
                if is_origin:
                    target_modes.append('origin')
                if is_rec:
                    target_modes.append('recommended')
                if is_spawn:
                    target_modes.append('spawn')

                for m in target_modes:
                    oid = f"v3.near:biome.exact.{name}:{side}:{m}"
                    best_map = world_best_cands.setdefault(oid, {})
                    if wid not in best_map or tuple_rank < tuple(best_map[wid]):
                        best_map[wid] = cand_rank


    # Membership audit
    if report['status'] == 'PASS':
        print("Auditing retention memberships...")
        dest_memberships = dest_manifest.get('memberships', [])
        old_memberships = old_manifest.get('memberships', [])

        dest_by_obj = {}
        for row in dest_memberships:
            dest_by_obj.setdefault(row['objective_id'], []).append(row)

        old_by_obj = {}
        for row in old_memberships:
            old_by_obj.setdefault(row['objective_id'], []).append(row)

        # Check no duplicate world per objective & every world exists & member payload bindings
        for oid, rows in dest_by_obj.items():
            report['counts']['memberships_audited'] += len(rows)
            seen_wids = set()
            for r in rows:
                wid = r['world_id']
                if wid in seen_wids:
                    fail(f"Duplicate world {wid} in objective {oid}")
                    break
                seen_wids.add(wid)
                if wid not in dest_worlds_by_wid:
                    fail(f"Membership world {wid} in {oid} does not exist in snapshot worlds")
                    break
                mem = r.get('member')
                if isinstance(mem, dict):
                    if mem.get('world_id') != wid:
                        fail(f"Membership member world_id mismatch in {oid}: {mem.get('world_id')} != {wid}")
                        break
                    obs_id = dest_worlds_by_wid[wid]['observation_id']
                    if 'source_observation_id' in mem and mem['source_observation_id'] != obs_id:
                        fail(f"Membership member source_observation_id mismatch in {oid}")
                        break
            if report['status'] == 'FAIL':
                break

        # Old objectives primary prefix check (Kold)
        for oid, old_rows in old_by_obj.items():
            new_rows = dest_by_obj.get(oid, [])
            k_old = len(old_rows)
            if len(new_rows)<k_old:fail(f'Old objective {oid} lost retained members')
            for i in range(min(k_old, len(new_rows))):
                if new_rows[i]['world_id'] != old_rows[i]['world_id']:
                    fail(f"Old objective {oid} rank {i} world mismatch: expected {old_rows[i]['world_id']}, got {new_rows[i]['world_id']}")
                    break
                if new_rows[i]['rank'] != old_rows[i]['rank']:
                    fail(f"Old objective {oid} rank {i} rank tuple mismatch: expected {old_rows[i]['rank']}, got {new_rows[i]['rank']}")
                    break
            if report['status'] == 'FAIL':
                break

        # Determine active Overworld exact biomes
        active_ow_names = [
            f['id'][len('biome.exact.'):]
            for f in registry_features
            if f.get('kind') == 'biome_witness'
            and f.get('dimension') == 'overworld'
            and f.get('available', True)
            and f['id'].startswith('biome.exact.')
        ]
        if not active_ow_names:
            active_ow_names = list(ACTIVE_OVERWORLD_BIOME_NAMES)

        # Verify each of the 504 active exact retention objectives
        for name in active_ow_names:
            for side in BORDER_SIDES:
                for mode in ('origin', 'recommended', 'spawn'):
                    oid = f"v3.near:biome.exact.{name}:{side}:{mode}"
                    best_map = world_best_cands.get(oid, {})
                    cands = list(best_map.values())
                    cands.sort(key=lambda r: tuple(r))
                    expected_members = cands[:RETENTION_CAP_PER_OBJECTIVE]

                    actual_members = dest_by_obj.get(oid, [])
                    if len(actual_members) != len(expected_members):
                        fail(f"Objective {oid} member count mismatch: expected {len(expected_members)}, got {len(actual_members)}")
                        break
                    for idx, (exp_r, act_row) in enumerate(zip(expected_members, actual_members)):
                        if act_row['world_id'] != exp_r[1]:
                            fail(f"Objective {oid} rank {idx} world mismatch: expected {exp_r[1]}, got {act_row['world_id']}")
                            break
                        if act_row['rank'] != exp_r:
                            fail(f"Objective {oid} rank {idx} rank mismatch: expected {exp_r}, got {act_row['rank']}")
                            break
                    if report['status'] == 'FAIL':
                        break
                if report['status'] == 'FAIL':
                    break
            if report['status'] == 'FAIL':
                break

        # Aux 12 objectives must be gated and empty
        aux_objectives = []
        for side in BORDER_SIDES:
            for mode in ('origin', 'recommended', 'spawn'):
                aux_objectives.append(f"v3.near:structure.igloo_with_basement:{side}:{mode}")
        for mode in ('origin', 'recommended', 'spawn'):
            aux_objectives.append(f"v3.near:structure.bastion_treasure:{mode}")

        for aux_oid in aux_objectives:
            if dest_by_obj.get(aux_oid, []):
                fail(f"Gated auxiliary objective {aux_oid} must be empty, but has members")
                break

    elapsed_s = time.monotonic() - start_time
    report['elapsed_seconds'] = round(elapsed_s, 2)
    print(f"Audit completed in {elapsed_s:.2f}s with status: {report['status']}.")

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(report, indent=2))
        print(f"Audit report written to {out_p}")

    return report['status'] == 'PASS'


def main():
    parser = argparse.ArgumentParser(description="Audit v3 catalog migration against v2 catalog.")
    parser.add_argument('--source', help="Source catalog root path (v2)")
    parser.add_argument('--destination', help="Destination catalog root path (v3)")
    parser.add_argument('--output', help="Output path for audit report JSON")
    parser.add_argument('--self-test', action='store_true', help="Run independent oracle self-tests")

    parser.add_argument('--coordinate-proof')
    parser.add_argument('--projection-source')
    args = parser.parse_args()

    if args.self_test:
        success = run_self_tests()
        sys.exit(0 if success else 1)

    if not args.source or not args.destination:
        parser.error("Both --source and --destination are required unless --self-test is specified.")

    source_p = Path(args.source).resolve()
    dest_p = Path(args.destination).resolve()

    if not source_p.exists():
        sys.exit(f"Source directory not found: {source_p}")
    if not dest_p.exists():
        sys.exit(f"Destination directory not found: {dest_p}")

    success = audit_catalogs(source_p, dest_p, args.output,coordinate_proof=args.coordinate_proof,projection_source=args.projection_source)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
