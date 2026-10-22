"""Derived layout summaries across 81 anchors and 3 border sides.

Derived from raw observation structures and biome samples without re-extracting.
Each observation generates 243 364-byte summary payloads validated by codec.
"""
from .models import SUMMARY_REVISION, validate_observation, observation_id, world_id
from .codec import layout_id, validate_summary, validate_summary_v3, MISSING
from .registry import (
    STRUCTURES, BIOMES, FEATURE_IDS, SIDES, ENVELOPE,
    FEATURES_V2, FEATURE_BY_ID_V2, REGISTRY_REVISION_V2, REGISTRY_V2,
    FEATURES_V3, FEATURE_BY_ID_V3, REGISTRY_REVISION_V3, REGISTRY_V3,
    SAMPLING_PROFILES_V3, SAMPLING_PROFILE_REVISION_V3, digest
)
from .geometry import anchors, bounds_for, inside, contains
from ..seeds import parse_seed
from .coverage import STRUCTURE_METHODS
import json


RADII_SQUARED = (256 * 256, 512 * 512, 1024 * 1024)
STRUCTURE_METHOD = 'predictor_viable_starts_v1'
BIOME_METHOD = 'predictor_world_lattice_y63_stride64_v1'
FULL_ENVELOPE = list(ENVELOPE)


def summarize(obs):
    return _summarize(obs, anchors(), custom=False)


def summarize_at(obs, anchor):
    """Versioned arbitrary-anchor rows; world-aligned observations stay unchanged."""
    from .anchors import validate_anchor_coordinate
    return _summarize(obs, [validate_anchor_coordinate(anchor)], custom=True)


def _summarize(obs, all_anchors, *, custom):
    """Derive 243 anchor x border summaries from one validated observation."""
    validate_observation(obs)
    obs_id = observation_id(obs)
    w_id = world_id(obs['identity'])
    seed_str = str(parse_seed(obs['identity']['seed']))

    # 1. Structure coverage & points by slot (0..13)
    struct_complete = []
    struct_points = []
    for f in STRUCTURES:
        feat_id = f['id']
        cov = obs['coverage'].get(feat_id)
        is_comp = (
            cov is not None
            and cov.get('status') == 'complete'
            and cov.get('method_id') in STRUCTURE_METHODS
            and cov.get('bounds') == FULL_ENVELOPE
        )
        struct_complete.append(is_comp)
        struct_points.append(obs['structures'].get(feat_id, []))

    # 2. Biome coverage, unknown raw IDs check, & samples by slot (0..8)
    has_unknown = False
    for bid_str, bname in obs['biome_names'].items():
        if bname.startswith('unknown'):
            has_unknown = True
            break

    if not has_unknown:
        for pt in obs['biomes']:
            bid = pt[3]
            if str(bid) not in obs['biome_names']:
                has_unknown = True
                break

    all_biomes_complete = (not has_unknown) and (len(obs['biomes']) == 25600)

    biome_complete = []
    for b in BIOMES:
        feat_id = b['id']
        cov = obs['coverage'].get(feat_id)
        is_comp = (
            all_biomes_complete
            and cov is not None
            and cov.get('status') == 'complete'
            and cov.get('method_id') == BIOME_METHOD
            and cov.get('bounds') == FULL_ENVELOPE
        )
        biome_complete.append(is_comp)

    # Map raw biome IDs to family slots (0..8)
    canonical_to_slot = {
        member: b['slot']
        for b in BIOMES
        for member in b.get('canonical_members', ())
    }
    raw_id_to_slot = {}
    for bid_str, bname in obs['biome_names'].items():
        if bname in canonical_to_slot:
            raw_id_to_slot[int(bid_str)] = canonical_to_slot[bname]

    # Partition biome samples by slot
    biome_samples_by_slot = [[] for _ in range(9)]
    for idx, pt in enumerate(obs['biomes']):
        slot = raw_id_to_slot.get(pt[3])
        if slot is not None:
            biome_samples_by_slot[slot].append((pt[0], pt[2], idx))

    # Full completion matrix: 14 structures + 9 biomes = 23 rows, 4 scopes each
    completion_matrix = [
        [struct_complete[s]] * 4 for s in range(14)
    ] + [
        [biome_complete[b]] * 4 for b in range(9)
    ]

    r0_sq, r1_sq, r2_sq = RADII_SQUARED
    summaries = []

    for anchor in all_anchors:
        cx, cz = anchor
        anchor_list = [cx, cz]

        for side in SIDES:
            lo_x, lo_z, hi_x, hi_z = bounds_for(anchor_list, side)

            # Structure counts (14x4) and nearest squared distances
            counts = []
            structure_nearest_d2 = []
            for s in range(14):
                pts = struct_points[s]
                c0 = c1 = c2 = c3 = 0
                min_d2 = MISSING
                for x, z in pts:
                    if lo_x <= x < hi_x and lo_z <= z < hi_z:
                        d2 = (x - cx) ** 2 + (z - cz) ** 2
                        if d2 < min_d2:
                            min_d2 = d2
                        c3 += 1
                        if d2 <= r2_sq:
                            c2 += 1
                            if d2 <= r1_sq:
                                c1 += 1
                                if d2 <= r0_sq:
                                    c0 += 1
                counts.append([c0, c1, c2, c3])
                structure_nearest_d2.append(min_d2)

            # Biome nearest squared distances and witness refs (9 slots)
            biome_nearest_d2 = []
            biome_witness_refs = []
            for b in range(9):
                best_d2 = MISSING
                best_idx = MISSING
                for x, z, idx in biome_samples_by_slot[b]:
                    if lo_x <= x < hi_x and lo_z <= z < hi_z:
                        d2 = (x - cx) ** 2 + (z - cz) ** 2
                        if d2 < best_d2:
                            best_d2 = d2
                            best_idx = idx
                        elif d2 == best_d2 and idx < best_idx:
                            best_idx = idx
                biome_nearest_d2.append(best_d2)
                biome_witness_refs.append(best_idx)

            lid = layout_id(obs_id, anchor_list, side)
            summary = {
                'revision': SUMMARY_REVISION,
                'observation_id': obs_id,
                'world_id': w_id,
                'layout_id': lid,
                'seed': seed_str,
                'anchor': list(anchor_list),
                'border_side': side,
                'counts': counts,
                'structure_nearest_d2': structure_nearest_d2,
                'biome_nearest_d2': biome_nearest_d2,
                'biome_witness_refs': biome_witness_refs,
                'complete': [list(row) for row in completion_matrix],
            }
            if custom:
                from .anchors import SUMMARY_REVISION as anchor_revision, validate_anchor_summary
                from .registry import digest
                summary['revision'] = anchor_revision
                summary['layout_id'] = digest([anchor_revision, obs_id, anchor_list, side])
                covered = (ENVELOPE[0] <= lo_x and ENVELOPE[1] <= lo_z and
                           hi_x <= ENVELOPE[2] and hi_z <= ENVELOPE[3])
                if not covered:
                    summary['complete'] = [[False] * 4 for _ in range(23)]
                validate_anchor_summary(summary)
            else:
                validate_summary(summary)
            summaries.append(summary)

    return summaries


def _validate_obs_v2(obs):
    from .models import validate_observation_v2
    return validate_observation_v2(obs)


def legacy_observation_v2(obs):
    """Validates v2 and projects only old 14 OW structures and nine-family lattice into v1 observation."""
    _validate_obs_v2(obs)

    # Defensive copy of identity
    ident = dict(obs['identity'])

    # 1. Project 14 old OW structures
    v1_structures = {}
    raw_structs = obs.get('structures', {})
    for f in STRUCTURES:
        feat_id = f['id']
        raw_starts = raw_structs.get(feat_id, [])
        filtered = []
        seen = set()
        for p in raw_starts:
            x, z = int(p[0]), int(p[1])
            if inside(x, z, ENVELOPE) and (x, z) not in seen:
                seen.add((x, z))
                filtered.append([x, z])
        if feat_id in raw_structs:
            v1_structures[feat_id] = filtered

    # 2. Project OW biomes: Y63, stride64, ENVELOPE
    v1_biomes = []
    seen_lattice = set()
    raw_biomes = obs.get('biomes', {})
    if isinstance(raw_biomes, dict):
        ow_biomes = raw_biomes.get('overworld', [])
    elif isinstance(raw_biomes, list):
        ow_biomes = raw_biomes
    else:
        ow_biomes = []

    for pt in ow_biomes:
        x, y, z, bid = int(pt[0]), int(pt[1]), int(pt[2]), int(pt[3])
        if y == 63 and x % 64 == 0 and z % 64 == 0 and inside(x, z, ENVELOPE):
            if (x, z) not in seen_lattice:
                seen_lattice.add((x, z))
                v1_biomes.append([x, y, z, bid])

    v1_biome_names = {str(k): str(v) for k, v in obs.get('biome_names', {}).items()}

    # Biome complete criteria: full 25600 known lattice exists
    has_unknown = any(name.startswith('unknown') for name in v1_biome_names.values())
    mapped_ids = {str(pt[3]) for pt in v1_biomes}
    all_mapped = all(
        bid in v1_biome_names and not v1_biome_names[bid].startswith('unknown')
        for bid in mapped_ids
    )
    full_known_lattice = (len(v1_biomes) == 25600) and (not has_unknown) and all_mapped

    # 3. Coverage
    v1_coverage = {}
    raw_cov = obs.get('coverage', {})

    for f in STRUCTURES:
        feat_id = f['id']
        cov = raw_cov.get(feat_id)
        if cov is not None:
            status = cov.get('status')
            bounds = cov.get('bounds')
            method_id = cov.get('method_id') if cov.get('method_id') in STRUCTURE_METHODS else STRUCTURE_METHOD
            if status == 'complete' and bounds and contains(bounds, ENVELOPE):
                v1_status = 'complete'
            elif status == 'complete':
                v1_status = 'partial'
            elif status in ('unknown', 'partial', 'failed'):
                v1_status = status
            else:
                v1_status = 'unknown'
        else:
            v1_status = 'unknown'
            method_id = STRUCTURE_METHOD

        v1_coverage[feat_id] = {
            'status': v1_status,
            'bounds': list(ENVELOPE),
            'method_id': method_id,
        }
        if v1_status == 'complete' and feat_id not in v1_structures:
            v1_structures[feat_id] = []

    for b in BIOMES:
        feat_id = b['id']
        cov = raw_cov.get(feat_id)
        if cov is not None:
            status = cov.get('status')
            bounds = cov.get('bounds')
            method_id = cov.get('method_id') if cov.get('method_id') == BIOME_METHOD else BIOME_METHOD
            if full_known_lattice and status == 'complete' and bounds and contains(bounds, ENVELOPE):
                v1_status = 'complete'
            elif status == 'complete':
                v1_status = 'partial'
            elif status in ('unknown', 'partial', 'failed'):
                v1_status = status
            else:
                v1_status = 'unknown'
        else:
            v1_status = 'unknown'
            method_id = BIOME_METHOD

        v1_coverage[feat_id] = {
            'status': v1_status,
            'bounds': list(ENVELOPE),
            'method_id': method_id,
        }

    # 4. Metrics and errors (compatible JSON copies)
    v1_metrics = json.loads(json.dumps(obs.get('metrics', {})))
    v1_errors = json.loads(json.dumps(obs.get('errors', {})))

    from .models import REVISION as V1_REVISION, validate_observation
    v1_obs = {
        'revision': V1_REVISION,
        'identity': ident,
        'bounds': list(ENVELOPE),
        'structures': v1_structures,
        'biomes': v1_biomes,
        'biome_names': v1_biome_names,
        'coverage': v1_coverage,
        'metrics': v1_metrics,
        'errors': v1_errors,
    }
    return validate_observation(v1_obs)


def summarize_v2(obs):
    """Derive summaries for 81 grid anchors x 3 border sides, plus spawn anchors x 3."""
    _validate_obs_v2(obs)
    obs_id = digest(obs)
    w_id = world_id(obs['identity'])
    seed_str = str(parse_seed(obs['identity']['seed']))

    # Project to legacy v1 observation once
    legacy_obs = legacy_observation_v2(obs)

    # 1. Determine all anchors
    anchor_rows = []
    # 81 grid anchors: (0, 0) has ['origin', 'recommended'], others have ['recommended']
    for coord in anchors():
        ax, az = coord
        if ax == 0 and az == 0:
            modes = ['origin', 'recommended']
        else:
            modes = ['recommended']
        anchor_rows.append(([ax, az], modes))

    # Spawn rows: preserve source anchor type and support their own mode only
    seen_spawns = set()
    for a in obs.get('anchors', []):
        mode = a.get('mode')
        if mode in ('world_spawn_estimated', 'world_spawn_observed'):
            coord = [int(a['coordinate'][0]), int(a['coordinate'][1])]
            spawn_key = (coord[0], coord[1], mode)
            if spawn_key not in seen_spawns:
                seen_spawns.add(spawn_key)
                anchor_rows.append((coord, [mode]))

    # Public Realm evidence can supply an additional refined settlement center.
    for a in obs['anchors']:
        if a['mode']=='recommended' and not any(coord==a['coordinate'] and 'recommended' in modes for coord,modes in anchor_rows):
            anchor_rows.append((list(a['coordinate']),['recommended']))

    # Deduplicate unique anchor coordinates for legacy summarization
    unique_anchor_coords = []
    seen_coords = set()
    for coord, _ in anchor_rows:
        key = (coord[0], coord[1])
        if key not in seen_coords:
            seen_coords.add(key)
            unique_anchor_coords.append(coord)

    legacy_by_coord_side = {(tuple(row['anchor']),row['border_side']):row for row in summarize(legacy_obs)}
    for coord in unique_anchor_coords:
        if (tuple(coord),SIDES[0]) in legacy_by_coord_side:continue
        legacy_list = summarize_at(legacy_obs, coord)
        for l_sum in legacy_list:
            legacy_by_coord_side[(tuple(coord), l_sum['border_side'])] = l_sum

    # 2. Group feature points once outside anchor loop
    canonical_to_feature_id = {
        member: f['id']
        for f in FEATURES_V2
        if f['kind'] == 'biome_witness'
        for member in f.get('canonical_members', ())
    }

    struct_points_by_feature = {}
    for f in FEATURES_V2:
        if f['kind'] == 'structure_count':
            feat_id = f['id']
            starts = obs.get('structures', {}).get(feat_id, [])
            struct_points_by_feature[feat_id] = starts

    raw_biomes = obs.get('biomes', {})
    if isinstance(raw_biomes, dict):
        ow_biome_samples = raw_biomes.get('overworld', [])
        nether_biome_samples = raw_biomes.get('nether', [])
    elif isinstance(raw_biomes, list):
        ow_biome_samples = raw_biomes
        nether_biome_samples = []
    else:
        ow_biome_samples = []
        nether_biome_samples = []

    biome_names = obs.get('biome_names', {})
    biome_points_by_feature = {f['id']: [] for f in FEATURES_V2 if f['kind'] == 'biome_witness'}

    # Overworld biomes: Y63 only
    for idx, pt in enumerate(ow_biome_samples):
        x, y, z, raw_id = int(pt[0]), int(pt[1]), int(pt[2]), int(pt[3])
        if y == 63:
            bname = biome_names.get(str(raw_id))
            if bname in canonical_to_feature_id:
                target_feat = canonical_to_feature_id[bname]
                biome_points_by_feature[target_feat].append((x, y, z, idx))

    # Nether biomes: Y64 only
    for idx, pt in enumerate(nether_biome_samples):
        x, y, z, raw_id = int(pt[0]), int(pt[1]), int(pt[2]), int(pt[3])
        if y == 64:
            bname = biome_names.get(str(raw_id))
            if bname in canonical_to_feature_id:
                target_feat = canonical_to_feature_id[bname]
                biome_points_by_feature[target_feat].append((x, y, z, idx))

    ow_radii = tuple(REGISTRY_V2['overworld_radii'])
    nether_radii = tuple(REGISTRY_V2['nether_radii'])

    summaries_v2 = []
    for anchor, anchor_modes in anchor_rows:
        ax, az = anchor
        nether_anchor = [ax // 8, az // 8]
        nax, naz = nether_anchor

        for side in SIDES:
            ow_lo_x = ax - side // 2
            ow_hi_x = ax + side // 2
            ow_lo_z = az - side // 2
            ow_hi_z = az + side // 2

            n_lo_x = nax - 1024 // 2
            n_hi_x = nax + 1024 // 2
            n_lo_z = naz - 1024 // 2
            n_hi_z = naz + 1024 // 2

            row_features = {}
            for f in FEATURES_V2:
                feat_id = f['id']
                dim = f['dimension']
                kind = f['kind']

                if dim == 'overworld':
                    cx, cz = ax, az
                    lo_x, hi_x, lo_z, hi_z = ow_lo_x, ow_hi_x, ow_lo_z, ow_hi_z
                    radii = ow_radii
                else:
                    cx, cz = nax, naz
                    lo_x, hi_x, lo_z, hi_z = n_lo_x, n_hi_x, n_lo_z, n_hi_z
                    radii = nether_radii

                r0_sq = radii[0] * radii[0]
                r1_sq = radii[1] * radii[1]
                r2_sq = radii[2] * radii[2]

                if kind == 'structure_count':
                    pts = struct_points_by_feature[feat_id]
                    c0 = c1 = c2 = cInside = 0
                    min_d2 = None
                    witness = None
                    for pt in pts:
                        x, z = int(pt[0]), int(pt[1])
                        if lo_x <= x < hi_x and lo_z <= z < hi_z:
                            d2 = (x - cx) ** 2 + (z - cz) ** 2
                            cInside += 1
                            if d2 <= r2_sq:
                                c2 += 1
                                if d2 <= r1_sq:
                                    c1 += 1
                                    if d2 <= r0_sq:
                                        c0 += 1
                            if min_d2 is None or d2 < min_d2:
                                min_d2 = d2
                                if len(pt) >= 3:
                                    witness = [int(pt[0]), int(pt[1]), int(pt[2])]
                                else:
                                    witness = [x, None, z]
                    counts = [c0, c1, c2, cInside]
                    nearest_d2 = min_d2

                    cov = obs.get('coverage', {}).get(feat_id)
                    if cov and cov.get('status') == 'complete' and cov.get('bounds') and len(cov['bounds']) == 4:
                        cov_bounds = cov['bounds']
                        box3 = (lo_x, lo_z, hi_x, hi_z)
                        comp3 = contains(cov_bounds, box3)
                        box2 = (max(lo_x, cx - radii[2]), max(lo_z, cz - radii[2]),
                                min(hi_x, cx + radii[2]+1), min(hi_z, cz + radii[2]+1))
                        comp2 = contains(cov_bounds, box2)
                        box1 = (max(lo_x, cx - radii[1]), max(lo_z, cz - radii[1]),
                                min(hi_x, cx + radii[1]+1), min(hi_z, cz + radii[1]+1))
                        comp1 = contains(cov_bounds, box1)
                        box0 = (max(lo_x, cx - radii[0]), max(lo_z, cz - radii[0]),
                                min(hi_x, cx + radii[0]+1), min(hi_z, cz + radii[0]+1))
                        comp0 = contains(cov_bounds, box0)
                        complete = [comp0, comp1, comp2, comp3]
                    else:
                        complete = [False, False, False, False]

                else:
                    pts = biome_points_by_feature[feat_id]
                    c0 = c1 = c2 = cInside = 0
                    best_d2 = None
                    best_idx = None
                    witness = None
                    for x, y, z, idx in pts:
                        if lo_x <= x < hi_x and lo_z <= z < hi_z:
                            d2 = (x - cx) ** 2 + (z - cz) ** 2
                            cInside = 1
                            if d2 <= r2_sq:
                                c2 = 1
                                if d2 <= r1_sq:
                                    c1 = 1
                                    if d2 <= r0_sq:
                                        c0 = 1
                            if best_d2 is None or d2 < best_d2 or (d2 == best_d2 and idx < best_idx):
                                best_d2 = d2
                                best_idx = idx
                                witness = [x, y, z]
                    counts = [c0, c1, c2, cInside]
                    nearest_d2 = best_d2
                    complete = [False, False, False, False]

                row_features[feat_id] = {
                    'dimension': dim,
                    'counts': counts,
                    'complete': complete,
                    'nearest_d2': nearest_d2,
                    'witness': witness,
                }

            lid = digest(['catalog-summary-v2', obs_id, list(anchor), list(anchor_modes), side])
            legacy = legacy_by_coord_side[(tuple(anchor), side)]

            summary = {
                'revision': 'catalog-summary-v2',
                'registry_revision': REGISTRY_REVISION_V2,
                'source_observation_id': obs_id,
                'world_id': w_id,
                'seed': seed_str,
                'anchor': list(anchor),
                'nether_anchor': list(nether_anchor),
                'anchor_modes': list(anchor_modes),
                'border_side': side,
                'layout_id': lid,
                'features': row_features,
                'legacy': legacy,
            }
            summaries_v2.append(summary)

    return summaries_v2


BIOME_ALIASES = {
    'forest_hills': 'forest', 'birch_forest_mutated': 'old_growth_birch_forest',
    'birch_forest_hills_mutated': 'old_growth_birch_forest',
    'roofed_forest': 'dark_forest', 'roofed_forest_mutated': 'dark_forest',
    'cold_taiga': 'snowy_taiga', 'cold_taiga_hills': 'snowy_taiga', 'cold_taiga_mutated': 'snowy_taiga',
    'mega_taiga': 'old_growth_pine_taiga', 'mega_taiga_hills': 'old_growth_pine_taiga',
    'mega_spruce_taiga': 'old_growth_spruce_taiga', 'mega_spruce_taiga_mutated': 'old_growth_spruce_taiga',
    'mega_taiga_mutated': 'taiga', 'taiga_mutated': 'taiga',
    'redwood_taiga_mutated': 'old_growth_spruce_taiga',
    'redwood_taiga_hills_mutated': 'old_growth_spruce_taiga',
    'jungle_mutated': 'jungle', 'jungle_edge_mutated': 'sparse_jungle',
    'extreme_hills_plus_trees': 'windswept_forest', 'extreme_hills_plus_trees_mutated': 'windswept_forest',
    'extreme_hills': 'windswept_hills', 'extreme_hills_mutated': 'windswept_gravelly_hills',
    'extreme_hills_edge': 'mountain_edge', 'swampland': 'swamp', 'swampland_mutated': 'swamp',
    'ice_plains': 'snowy_plains', 'ice_plains_spikes': 'ice_spikes', 'ice_mountains': 'snowy_mountains',
    'stone_beach': 'stony_shore', 'cold_beach': 'snowy_beach', 'mushroom_island': 'mushroom_fields',
    'mushroom_island_shore': 'mushroom_field_shore', 'legacy_frozen_ocean': 'frozen_ocean',
    'savanna_mutated': 'windswept_savanna', 'savanna_plateau_mutated': 'windswept_savanna',
    'mesa': 'badlands', 'mesa_bryce': 'eroded_badlands', 'mesa_mutated': 'badlands',
    'mesa_plateau': 'badlands_plateau', 'mesa_plateau_mutated': 'modified_badlands_plateau',
    'mesa_plateau_stone': 'wooded_badlands', 'mesa_plateau_stone_mutated': 'wooded_badlands',
    'desert_mutated': 'desert_lakes',
    'wooded_hills': 'forest', 'birch_forest_hills': 'birch_forest', 'tall_birch_forest': 'old_growth_birch_forest',
    'tall_birch_hills': 'old_growth_birch_forest', 'wooded_mountains': 'windswept_forest',
    'taiga_hills': 'taiga', 'taiga_mountains': 'taiga', 'snowy_taiga_hills': 'snowy_taiga',
    'snowy_taiga_mountains': 'snowy_taiga', 'giant_tree_taiga': 'old_growth_pine_taiga',
    'giant_tree_taiga_hills': 'old_growth_pine_taiga', 'giant_spruce_taiga': 'old_growth_spruce_taiga',
    'giant_spruce_taiga_hills': 'old_growth_spruce_taiga', 'jungle_hills': 'jungle',
    'modified_jungle': 'jungle', 'jungle_edge': 'sparse_jungle', 'modified_jungle_edge': 'sparse_jungle',
    'bamboo_jungle_hills': 'bamboo_jungle', 'dark_forest_hills': 'dark_forest',
    'snowy_tundra': 'snowy_plains', 'stone_shore': 'stony_shore', 'shattered_savanna': 'windswept_savanna',
    'shattered_savanna_plateau': 'windswept_savanna',
}


def canonical_biome_name(name):
    name = str(name).removeprefix('minecraft:').lower().replace(' ', '_')
    return BIOME_ALIASES.get(name, name)


def summarize_v3(obs, *, extension=None, base_summaries=None, registry=None):
    """Additive summaries preserving legacy payload and anchor modes.

    Fields same as v2 plus source_extension_id (nullable), sampling_profile_revision.
    Layout ID binds revision/base/extension/profile/registry/anchor/modes/side.
    Reuses base_summaries v2 when supplied to avoid recomputation.
    """
    _validate_obs_v2(obs)
    obs_id = digest(obs)
    w_id = world_id(obs['identity'])
    seed_str = str(parse_seed(obs['identity']['seed']))

    active_registry = registry if registry is not None else REGISTRY_V3
    active_features = active_registry['features']
    active_feature_by_id = {f['id']: f for f in active_features}
    reg_rev = digest(active_registry)

    # 1. Validate extension if provided
    source_extension_id = None
    sampling_prof_rev = SAMPLING_PROFILE_REVISION_V3
    ext_ow_biomes = []
    ext_nether_biomes = []
    ext_biome_names = {}

    if extension is not None:
        from .biome_extension import validate_extension
        validate_extension(extension,obs)
        source_extension_id=digest(extension)
        ext_ow_biomes=extension['biomes']['overworld']
        ext_biome_names=extension['biome_names']

    # 2. Preserve per-mode legacy payloads when spawn overlaps a grid coordinate.
    legacy_by_modes = {}
    if base_summaries is not None:
        anchor_rows = []
        seen_anchor_keys = set()
        legacy_by_coord_side = {}
        from .codec import validate_summary_v2
        for s in base_summaries:
            validate_summary_v2(s)
            if s['source_observation_id']!=obs_id or s['world_id']!=w_id:raise ValueError('Base summary source differs')
            for mode in ('world_spawn_estimated','world_spawn_observed'):
                if mode in s['anchor_modes'] and not any(a['mode']==mode and a['coordinate']==s['anchor'] for a in obs['anchors']):raise ValueError('Base summary spawn differs')
            coord = list(s['anchor'])
            modes = list(s['anchor_modes'])
            side = s['border_side']
            key = (coord[0], coord[1], tuple(modes))
            if key not in seen_anchor_keys:
                seen_anchor_keys.add(key)
                anchor_rows.append((coord, modes))
            legacy_by_modes[(tuple(coord), side, tuple(modes))] = s['legacy']
            legacy_by_coord_side[(tuple(coord), side)] = s['legacy']
    else:
        legacy_obs = legacy_observation_v2(obs)
        anchor_rows = []
        for coord in anchors():
            ax, az = coord
            if ax == 0 and az == 0:
                modes = ['origin', 'recommended']
            else:
                modes = ['recommended']
            anchor_rows.append(([ax, az], modes))

        seen_spawns = set()
        for a in obs.get('anchors', []):
            mode = a.get('mode')
            if mode in ('world_spawn_estimated', 'world_spawn_observed'):
                coord = [int(a['coordinate'][0]), int(a['coordinate'][1])]
                spawn_key = (coord[0], coord[1], mode)
                if spawn_key not in seen_spawns:
                    seen_spawns.add(spawn_key)
                    anchor_rows.append((coord, [mode]))

        for a in obs.get('anchors', []):
            if a.get('mode') == 'recommended' and not any(coord == a.get('coordinate') and 'recommended' in modes for coord, modes in anchor_rows):
                anchor_rows.append((list(a['coordinate']), ['recommended']))

        unique_anchor_coords = []
        seen_coords = set()
        for coord, _ in anchor_rows:
            key = (coord[0], coord[1])
            if key not in seen_coords:
                seen_coords.add(key)
                unique_anchor_coords.append(coord)

        legacy_by_coord_side = {(tuple(row['anchor']), row['border_side']): row for row in summarize(legacy_obs)}
        for coord in unique_anchor_coords:
            if (tuple(coord), SIDES[0]) in legacy_by_coord_side:
                continue
            legacy_list = summarize_at(legacy_obs, coord)
            for l_sum in legacy_list:
                legacy_by_coord_side[(tuple(coord), l_sum['border_side'])] = l_sum

    # 3. Structures
    struct_points_by_feature = {}
    for f in active_features:
        if f['kind'] == 'structure_count':
            feat_id = f['id']
            ext_key = f.get('extractor_key')
            starts = obs.get('structures', {}).get(feat_id)
            if starts is None and ext_key:
                starts = obs.get('structures', {}).get(ext_key)
            struct_points_by_feature[feat_id] = starts or []
            if feat_id in ('structure.igloo_with_basement','structure.bastion_treasure'):
                inventory=(obs.get('realm') or {}).get('inventory',{})
                key='igloo_basement' if feat_id=='structure.igloo_with_basement' else 'bastion_variant'
                entry=inventory.get(key,{})
                parent='structure.igloo' if key=='igloo_basement' else 'structure.bastion'
                parents={tuple(p) for p in obs['structures'].get(parent,[])}
                struct_points_by_feature[feat_id]=sorted({tuple(p[:2]) for p in entry.get('points',[]) if (key=='igloo_basement' or p[2]==2) and tuple(p[:2]) in parents})


    # 4. Biomes with full overlap preservation across exact, group, and legacy features
    canonical = canonical_biome_name

    name_to_features = {}
    for f in active_features:
        if f['kind'] == 'biome_witness':
            feat_id = f['id']
            members = set(f.get('canonical_members', ()))
            if feat_id.startswith('biome.exact.'):
                cname = feat_id.removeprefix('biome.exact.')
                members.add(cname)
            for atom_id in f.get('atomic_members', ()):
                if atom_id.startswith('biome.exact.'):
                    members.add(atom_id.removeprefix('biome.exact.'))
                else:
                    members.add(atom_id)
            for m in members:
                c_m = canonical(m)
                name_to_features.setdefault(c_m, set()).add(feat_id)
                name_to_features.setdefault(m, set()).add(feat_id)

    raw_biomes = obs.get('biomes', {})
    if isinstance(raw_biomes, dict):
        base_ow = raw_biomes.get('overworld', [])
        base_nether = raw_biomes.get('nether', [])
    elif isinstance(raw_biomes, list):
        base_ow = raw_biomes
        base_nether = []
    else:
        base_ow = []
        base_nether = []

    all_names = dict(obs.get('biome_names', {}))
    all_names.update(ext_biome_names)

    biome_points_by_feature = {f['id']: [] for f in active_features if f['kind'] == 'biome_witness'}

    # Process Overworld samples (base Y63 + extension samples)
    all_ow_samples = list(base_ow) + list(ext_ow_biomes)
    for idx, pt in enumerate(all_ow_samples):
        x, y, z = int(pt[0]), int(pt[1]), int(pt[2])
        raw_val = pt[3]
        bname = all_names.get(str(raw_val), str(raw_val))
        cname = canonical(bname)

        matching_fids = name_to_features.get(cname, set()) | name_to_features.get(bname, set())
        for fid in matching_fids:
            fdef = active_feature_by_id[fid]
            if fdef['dimension'] != 'overworld':
                continue
            # Legacy aliases remain v2 Y63 even when exact features multi-height
            is_legacy_alias = fid.startswith('biome.') and not fid.startswith('biome.exact.') and not fid.startswith('biome.group.')
            if is_legacy_alias:
                if y != 63:
                    continue
            else:
                eligible_y = fdef.get('eligible_y')
                if eligible_y and y not in eligible_y:
                    continue
            biome_points_by_feature[fid].append((x, y, z, idx))

    # Process Nether samples (base Y64 + extension samples)
    all_nether_samples = list(base_nether) + list(ext_nether_biomes)
    for idx, pt in enumerate(all_nether_samples):
        x, y, z = int(pt[0]), int(pt[1]), int(pt[2])
        raw_val = pt[3]
        bname = all_names.get(str(raw_val), str(raw_val))
        cname = canonical(bname)

        matching_fids = name_to_features.get(cname, set()) | name_to_features.get(bname, set())
        for fid in matching_fids:
            fdef = active_feature_by_id[fid]
            if fdef['dimension'] != 'nether':
                continue
            is_legacy_alias = fid.startswith('biome.') and not fid.startswith('biome.exact.') and not fid.startswith('biome.group.')
            if is_legacy_alias:
                if y != 64:
                    continue
            else:
                eligible_y = fdef.get('eligible_y')
                if eligible_y and y not in eligible_y:
                    continue
            biome_points_by_feature[fid].append((x, y, z, idx))

    for f in active_features:
        if f['id'].startswith('biome.group.'):
            points=set()
            for member in f['atomic_members']:
                if active_feature_by_id[member].get('available',True):
                    points.update(biome_points_by_feature[member])
            biome_points_by_feature[f['id']]=sorted(points)

    ow_radii = tuple(active_registry.get('overworld_radii', (256, 512, 1024)))
    nether_radii = tuple(active_registry.get('nether_radii', (64, 128, 256)))

    summaries_v3_list = []
    for anchor, anchor_modes in anchor_rows:
        ax, az = anchor
        nether_anchor = [ax // 8, az // 8]
        nax, naz = nether_anchor

        for side in SIDES:
            ow_lo_x = ax - side // 2
            ow_hi_x = ax + side // 2
            ow_lo_z = az - side // 2
            ow_hi_z = az + side // 2

            n_lo_x = nax - 1024 // 2
            n_hi_x = nax + 1024 // 2
            n_lo_z = naz - 1024 // 2
            n_hi_z = naz + 1024 // 2

            row_features = {}
            for f in active_features:
                feat_id = f['id']
                dim = f['dimension']
                kind = f['kind']

                if dim == 'overworld':
                    cx, cz = ax, az
                    lo_x, hi_x, lo_z, hi_z = ow_lo_x, ow_hi_x, ow_lo_z, ow_hi_z
                    radii = ow_radii
                else:
                    cx, cz = nax, naz
                    lo_x, hi_x, lo_z, hi_z = n_lo_x, n_hi_x, n_lo_z, n_hi_z
                    radii = nether_radii

                r0_sq = radii[0] * radii[0]
                r1_sq = radii[1] * radii[1]
                r2_sq = radii[2] * radii[2]

                if kind == 'structure_count':
                    pts = struct_points_by_feature[feat_id]
                    c0 = c1 = c2 = cInside = 0
                    min_d2 = None
                    witness = None
                    for pt in pts:
                        x, z = int(pt[0]), int(pt[1])
                        if lo_x <= x < hi_x and lo_z <= z < hi_z:
                            d2 = (x - cx) ** 2 + (z - cz) ** 2
                            cInside += 1
                            if d2 <= r2_sq:
                                c2 += 1
                                if d2 <= r1_sq:
                                    c1 += 1
                                    if d2 <= r0_sq:
                                        c0 += 1
                            if min_d2 is None or d2 < min_d2:
                                min_d2 = d2
                                if len(pt) >= 3:
                                    witness = [int(pt[0]), int(pt[1]), int(pt[2])]
                                else:
                                    witness = [x, None, z]
                    counts = [c0, c1, c2, cInside]
                    nearest_d2 = min_d2

                    cov = obs.get('coverage', {}).get(feat_id)
                    if feat_id in ('structure.igloo_with_basement','structure.bastion_treasure'):
                        key='igloo_basement' if feat_id=='structure.igloo_with_basement' else 'bastion_variant'
                        entry=(obs.get('realm') or {}).get('inventory',{}).get(key,{})
                        parent='structure.igloo' if key=='igloo_basement' else 'structure.bastion'
                        parent_cov=obs.get('coverage',{}).get(parent,{})
                        cov=entry if entry.get('status')=='complete' and parent_cov.get('status')=='complete' else None
                    if cov and cov.get('status') == 'complete' and cov.get('bounds') and len(cov['bounds']) == 4:
                        cov_bounds = cov['bounds']
                        box3 = (lo_x, lo_z, hi_x, hi_z)
                        comp3 = contains(cov_bounds, box3)
                        box2 = (max(lo_x, cx - radii[2]), max(lo_z, cz - radii[2]),
                                min(hi_x, cx + radii[2]+1), min(hi_z, cz + radii[2]+1))
                        comp2 = contains(cov_bounds, box2)
                        box1 = (max(lo_x, cx - radii[1]), max(lo_z, cz - radii[1]),
                                min(hi_x, cx + radii[1]+1), min(hi_z, cz + radii[1]+1))
                        comp1 = contains(cov_bounds, box1)
                        box0 = (max(lo_x, cx - radii[0]), max(lo_z, cz - radii[0]),
                                min(hi_x, cx + radii[0]+1), min(hi_z, cz + radii[0]+1))
                        comp0 = contains(cov_bounds, box0)
                        complete = [comp0, comp1, comp2, comp3]
                    else:
                        complete = [False, False, False, False]

                else:
                    pts = biome_points_by_feature[feat_id]
                    c0 = c1 = c2 = cInside = 0
                    best_d2 = None
                    best_idx = None
                    witness = None
                    for x, y, z, idx in pts:
                        if lo_x <= x < hi_x and lo_z <= z < hi_z:
                            d2 = (x - cx) ** 2 + (z - cz) ** 2
                            cInside = 1
                            if d2 <= r2_sq:
                                c2 = 1
                                if d2 <= r1_sq:
                                    c1 = 1
                                    if d2 <= r0_sq:
                                        c0 = 1
                            if best_d2 is None or (d2,x,y,z) < (best_d2,*witness):
                                best_d2 = d2
                                best_idx = idx
                                witness = [x, y, z]
                    counts = [c0, c1, c2, cInside]
                    nearest_d2 = best_d2
                    complete = [False, False, False, False]

                row_features[feat_id] = {
                    'dimension': dim,
                    'counts': counts,
                    'complete': complete,
                    'nearest_d2': nearest_d2,
                    'witness': witness,
                }

            lid = digest([
                'catalog-summary-v3',
                obs_id,
                source_extension_id,
                sampling_prof_rev,
                reg_rev,
                list(anchor),
                list(anchor_modes),
                side
            ])
            legacy = legacy_by_modes.get((tuple(anchor), side, tuple(anchor_modes)), legacy_by_coord_side[(tuple(anchor), side)])

            summary = {
                'revision': 'catalog-summary-v3',
                'registry_revision': reg_rev,
                'source_observation_id': obs_id,
                'source_extension_id': source_extension_id,
                'sampling_profile_revision': sampling_prof_rev,
                'world_id': w_id,
                'seed': seed_str,
                'anchor': list(anchor),
                'nether_anchor': list(nether_anchor),
                'anchor_modes': list(anchor_modes),
                'border_side': side,
                'layout_id': lid,
                'features': row_features,
                'legacy': legacy,
            }
            validate_summary_v3(summary, registry=active_registry)
            summaries_v3_list.append(summary)

    return summaries_v3_list


