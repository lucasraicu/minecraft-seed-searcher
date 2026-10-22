"""Authoritative catalog retention engine across 7 fixed objective families.

Evaluates fixed-capacity Top-K retention objectives for public catalog candidates.
Deduplicates best eligible layout per world before Top-K truncation.
Enforces stable-hash reference sampling across the population before relevance gates.
"""
from decimal import Decimal, localcontext
from bisect import insort
import hashlib
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .codec import MISSING, validate_summary
from .models import SUMMARY_REVISION, validate_identity, world_id
from .registry import (
    AXIS,
    BIOMES,
    POLICY,
    PROFILES,
    RADII,
    REGISTRY_REVISION,
    SIDES,
    STRUCTURES,
    canonical_json,
    digest,
)
from .scoring import LCM, canonical_tail, profile_units

POLICY_REVISION: str = POLICY['policy_id'] + ':' + digest([REGISTRY_REVISION, SUMMARY_REVISION, POLICY])
REFERENCE_SALT: str = POLICY['retention']['reference_sample']['salt']
MODES: Tuple[str, ...] = tuple(POLICY['retention']['modes'])
PAIR_LANDMARKS: Tuple[str, ...] = tuple(POLICY['retention']['biome_landmark_pairs']['landmarks'])
DIVERSITY_BITS: Tuple[str, ...] = tuple(POLICY['retention']['diversity']['bits'])
DIVERSITY_PROFILES: Tuple[str, ...] = tuple(POLICY['retention']['diversity']['profiles'])

STRUCTURE_SLOTS: Dict[str, int] = {f['id']: f['slot'] for f in STRUCTURES}
BIOME_SLOTS: Dict[str, int] = {f['id']: f['slot'] for f in BIOMES}

DEFAULT_CAPACITIES: Dict[str, int] = {
    'structure_count': POLICY['retention']['structure_count']['k'],
    'structure_proximity': POLICY['retention']['structure_proximity']['k'],
    'biome_proximity': POLICY['retention']['biome_proximity']['k'],
    'biome_landmark_pairs': POLICY['retention']['biome_landmark_pairs']['k'],
    'profiles': POLICY['retention']['profiles']['k'],
    'diversity': POLICY['retention']['diversity']['k_each'],
    'reference_sample': POLICY['retention']['reference_sample']['k'],
}


def _build_objective_ids() -> Tuple[str, ...]:
    ids: List[str] = []
    # 1. structure_count: 14 * 4 * 3 * 2 = 336
    for f in STRUCTURES:
        for scope_idx in range(4):
            for side in SIDES:
                for mode in MODES:
                    ids.append(f"structure_count:{f['id']}:{scope_idx}:{side}:{mode}")
    # 2. structure_proximity: 14 * 3 * 2 = 84
    for f in STRUCTURES:
        for side in SIDES:
            for mode in MODES:
                ids.append(f"structure_proximity:{f['id']}:{side}:{mode}")
    # 3. biome_proximity: 9 * 3 * 2 = 54
    for b in BIOMES:
        for side in SIDES:
            for mode in MODES:
                ids.append(f"biome_proximity:{b['id']}:{side}:{mode}")
    # 4. biome_landmark_pairs: 9 * 4 * 3 * 2 = 216
    for b in BIOMES:
        for lmark in PAIR_LANDMARKS:
            for side in SIDES:
                for mode in MODES:
                    ids.append(f"biome_landmark_pairs:{b['id']}:{lmark}:{side}:{mode}")
    # 5. profiles: 16 * 3 * 2 = 96
    for p in POLICY['profiles']:
        for side in SIDES:
            for mode in MODES:
                ids.append(f"profiles:{p['id']}:{side}:{mode}")
    # 6. diversity: 256 * 4 * 3 * 2 = 6,144
    for cell in range(256):
        for p in DIVERSITY_PROFILES:
            for side in SIDES:
                for mode in MODES:
                    ids.append(f"diversity:{cell}:{p}:{side}:{mode}")
    # 7. reference_sample: 1
    ids.append("reference_sample")
    return tuple(ids)


ALL_OBJECTIVE_IDS: Tuple[str, ...] = _build_objective_ids()
assert len(ALL_OBJECTIVE_IDS) == 6931, f"Expected 6931 objectives, got {len(ALL_OBJECTIVE_IDS)}"


def automation_objectives():
    """Registered finite objective set; never enumerate arbitrary query subsets."""
    from .products import launch_definitions
    values={oid:DEFAULT_CAPACITIES[oid.split(':',1)[0]] for oid in ALL_OBJECTIVE_IDS}
    for mode in MODES:
        for side in SIDES:
            for scope in range(4):values[f'v2.count:structure.stronghold:{scope}:{side}:{mode}']=100
            values[f'v2.near:structure.stronghold:{side}:{mode}']=100
        for feature in ('structure.fortress','structure.bastion'):
            for scope in range(4):values[f'v2.count:{feature}:{scope}:{mode}']=100
            values[f'v2.near:{feature}:{mode}']=100
        for biome in ('nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas'):
            values[f'v2.near:biome.{biome}:{mode}']=100
    products=launch_definitions()
    for p in [products['realm'],*products.get('realm_sizes',[]),*products['presets'],*products['records']]:values[p['id']]=p['capacity']
    assert len(values)==7027 and sum(values.values())==105644
    return values


def automation_policy_revision():
    import json
    from .registry import REGISTRY_REVISION_V2,CONTRACT_ROOT
    from .products import launch_definitions
    from .product_evaluation import FAMILIES
    import hashlib
    from pathlib import Path
    module_root=Path(__file__).parent
    sources={name:hashlib.sha256((module_root/name).read_bytes()).hexdigest() for name in
             ('product_evaluation.py','realm_evaluation.py','calibration.py','realm_observations.py','models.py','extract.py','summaries.py','retention.py')}
    calibration_path=CONTRACT_ROOT.parent/'v2'/'realm_calibration.json'
    calibration=json.loads(calibration_path.read_text()) if calibration_path.is_file() else None
    # V2 semantic functions/contracts are frozen; additive v3 source must not invalidate historical policy roots.
    frozen=json.loads((CONTRACT_ROOT.parent/'v3'/'legacy_automation_policy.json').read_text())
    sources=frozen['sources']
    return digest(['catalog-automation-v2-r3',sources,calibration,POLICY_REVISION,REGISTRY_REVISION_V2,launch_definitions(),FAMILIES,
        json.loads((CONTRACT_ROOT.parent/'v2'/'realm_scoring.json').read_text()),automation_objectives()])


def automation_offers(observation, summaries, evaluations):
    """Offer a whole world's best eligible anchors into baseline + added lists."""
    from .product_evaluation import product_offers
    from .models import validate_observation_v2
    validate_observation_v2(observation)
    oid=digest(observation);wid=world_id(observation['identity'])
    if any(s['source_observation_id']!=oid or s['world_id']!=wid for s in summaries):
        raise ValueError('Retention summary source differs')
    grid={s['legacy']['layout_id']:s['legacy'] for s in summaries if 'recommended' in s['anchor_modes'] and s['legacy']['revision']=='catalog-summary-v1'}
    selected=retain(list(grid.values()),[observation['identity']])
    offers=[]
    for objective,members in selected['objectives'].items():
        for member in members:
            rank=list(member['rank'])
            if member.get('layout_id') is not None:
                layout=grid[member['layout_id']]
                # Metrics and new witnesses change source IDs, not geometric tie preference.
                rank[-1]=digest(['automation-anchor-v2',wid,layout['anchor'],layout['border_side']])
            if objective_family(objective) in ('profiles','diversity'):
                rank[0]=dict(decimal=rank[0])
            offers.append(dict(objective_id=objective,rank=rank,member=dict(member,rank=list(rank),
                source_observation_id=oid)))
    wid=world_id(observation['identity']);best={}
    def offer(oid,rank,s):
        member=dict(world_id=wid,layout_id=s['layout_id'],anchor=s['anchor'],
                    source_observation_id=s['source_observation_id'])
        key=tuple(rank)
        if oid not in best or key<best[oid][0]:best[oid]=(key,member)
    for s in summaries:
        for mode in MODES:
            if mode not in s['anchor_modes']:continue
            side=s['border_side']
            f=s['features']['structure.stronghold']
            for scope,c in enumerate(f['counts']):
                if c and f['complete'][scope]:offer(f'v2.count:structure.stronghold:{scope}:{side}:{mode}',[-c,wid,*s['anchor']],s)
            if f['nearest_d2'] is not None and f['nearest_d2']<=256**2:
                offer(f'v2.near:structure.stronghold:{side}:{mode}',[f['nearest_d2'],wid,*s['anchor']],s)
            # Identical fixed Nether windows are not triplicated by OW border.
            if side!=SIDES[0]:continue
            for feature in ('structure.fortress','structure.bastion'):
                f=s['features'][feature]
                for scope,c in enumerate(f['counts']):
                    if c and f['complete'][scope]:offer(f'v2.count:{feature}:{scope}:{mode}',[-c,wid,*s['anchor']],s)
                if f['nearest_d2'] is not None and f['nearest_d2']<=64**2:
                    offer(f'v2.near:{feature}:{mode}',[f['nearest_d2'],wid,*s['anchor']],s)
            for biome in ('nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas'):
                feature='biome.'+biome;f=s['features'][feature]
                if f['nearest_d2'] is not None and f['nearest_d2']<=256**2:
                    offer(f'v2.near:{feature}:{mode}',[f['nearest_d2'],wid,*s['anchor']],s)
    offers.extend(dict(objective_id=oid,rank=list(key),member=member) for oid,(key,member) in best.items())
    offers.extend(product_offers(evaluations))
    return offers


# ---------------------------------------------------------------------------
# Version 3 Additive Public Retention Definitions
# ---------------------------------------------------------------------------

ATOMIC_OW_BIOMES_56: Tuple[str, ...] = (
    # Oceans (9)
    'ocean', 'deep_ocean', 'warm_ocean', 'lukewarm_ocean', 'deep_lukewarm_ocean',
    'cold_ocean', 'deep_cold_ocean', 'frozen_ocean', 'deep_frozen_ocean',
    # Rivers & shores (5)
    'river', 'frozen_river', 'beach', 'snowy_beach', 'stony_shore',
    # Forest & taiga (7)
    'dark_forest', 'pale_garden', 'dappled_forest', 'taiga',
    'old_growth_pine_taiga', 'old_growth_spruce_taiga', 'windswept_forest',
    # Jungle (2)
    'jungle', 'sparse_jungle',
    # Savanna (3)
    'savanna', 'savanna_plateau', 'windswept_savanna',
    # Swamp (1)
    'swamp',
    # Mountains (6) (initially gated pending height evidence / controls)
    'windswept_hills', 'windswept_gravelly_hills', 'jagged_peaks',
    'frozen_peaks', 'stony_peaks', 'grove',
    # Caves (4) (initially gated pending height evidence / controls)
    'lush_caves', 'dripstone_caves', 'deep_dark', 'sulfur_caves',
    # Split group members (14)
    'badlands', 'eroded_badlands', 'wooded_badlands',
    'snowy_plains', 'snowy_slopes', 'snowy_taiga', 'ice_spikes',
    'forest', 'birch_forest', 'flower_forest', 'old_growth_birch_forest',
    'plains', 'sunflower_plains', 'meadow',
    # Singletons (5)
    'cherry_grove', 'mushroom_fields', 'bamboo_jungle', 'desert', 'mangrove_swamp',
)
assert len(ATOMIC_OW_BIOMES_56) == 56

MODES_V3: Tuple[str, ...] = ('origin', 'recommended', 'spawn')

GATED_V3_FEATURES_DEFAULT: Set[str] = {
    'biome.exact.windswept_hills',
    'biome.exact.windswept_gravelly_hills',
    'biome.exact.jagged_peaks',
    'biome.exact.frozen_peaks',
    'biome.exact.stony_peaks',
    'biome.exact.grove',
    'biome.exact.lush_caves',
    'biome.exact.dripstone_caves',
    'biome.exact.deep_dark',
    'biome.exact.sulfur_caves',
    'structure.igloo_with_basement',
    'structure.bastion_treasure',
}


def automation_primary_objectives_v3() -> Dict[str, int]:
    """Registered finite objective primary capacities: exactly 7,543 objectives / 115,964 slots."""
    values = dict(automation_objectives())
    # 56 atomic biomes x 3 border sides x 3 modes = 504 objectives (capacity 20 each)
    for b in ATOMIC_OW_BIOMES_56:
        for side in SIDES:
            for mode in MODES_V3:
                values[f'v3.near:biome.exact.{b}:{side}:{mode}'] = 20
    # 1 basement igloo x 3 border sides x 3 modes = 9 objectives (capacity 20 each)
    for side in SIDES:
        for mode in MODES_V3:
            values[f'v3.near:structure.igloo_with_basement:{side}:{mode}'] = 20
    # 1 treasure bastion x 3 modes = 3 objectives (capacity 20 each; Nether window is fixed 1024)
    for mode in MODES_V3:
        values[f'v3.near:structure.bastion_treasure:{mode}'] = 20

    assert len(values) == 7543, f"Expected 7543 objectives, got {len(values)}"
    assert sum(values.values()) == 115964, f"Expected 115964 primary slots, got {sum(values.values())}"
    return values


def automation_objectives_v3() -> Dict[str, int]:
    """Registered finite objective effective 2x capacities: exactly 7,543 objectives / 231,928 slots."""
    primary = automation_primary_objectives_v3()
    effective = {oid: cap * 2 for oid, cap in primary.items()}
    assert len(effective) == 7543, f"Expected 7543 objectives, got {len(effective)}"
    assert sum(effective.values()) == 231928, f"Expected 231928 effective slots, got {sum(effective.values())}"
    return effective


def objective_capacities_v3() -> Dict[str, Dict[str, int]]:
    """Mapping of each objective to its primary and 2x effective retained capacity."""
    primary = automation_primary_objectives_v3()
    return {oid: {'primary_k': cap, 'retained_k': cap * 2} for oid, cap in primary.items()}


def split_primary_reserve(members: Sequence[Any], primary_k: int) -> Tuple[List[Any], List[Any]]:
    """Partition a ranked 2K candidate sequence into primary (0..K-1) and reserve (K..2K-1)."""
    if primary_k < 0:
        raise ValueError('primary_k must be non-negative')
    primary = list(members[:primary_k])
    reserve = list(members[primary_k:2 * primary_k])
    return primary, reserve


def world_objective_roles(
    objective_members: Dict[str, Sequence[Dict[str, Any]]],
    primary_capacities: Optional[Dict[str, int]] = None,
    *,
    world_id: str,
) -> Dict[str, str]:
    """Return objective -> 'primary' | 'reserve' role mapping for a given world ID."""
    if primary_capacities is None:
        primary_capacities = automation_primary_objectives_v3()
    roles = {}
    for oid, members in objective_members.items():
        k = primary_capacities.get(oid, 0)
        for idx, m in enumerate(members):
            wid = m.get('world_id') if isinstance(m, dict) else m
            if wid == world_id:
                roles[oid] = 'primary' if idx < k else 'reserve'
                break
    return roles


def retained_union(objective_members: Dict[str, Sequence[Any]]) -> List[str]:
    """Deduplicated sorted union of all distinct world IDs across all objectives and tiers."""
    wids = set()
    for members in objective_members.values():
        for m in members:
            wid = m.get('world_id') if isinstance(m, dict) else m
            if isinstance(wid, str):
                wids.add(wid)
    return sorted(list(wids))


def automation_policy_revision_v3(*, registry=None) -> str:
    """Versioned public retention policy hash bound to frozen v3 contracts and source."""
    import json
    import hashlib
    from pathlib import Path
    from .registry import CONTRACT_ROOT, digest
    from .products import launch_definitions
    from .product_evaluation import FAMILIES

    module_root = Path(__file__).parent
    source_names = (
        'product_evaluation.py', 'realm_evaluation.py', 'calibration.py',
        'realm_observations.py', 'models.py', 'extract.py', 'summaries.py',
        'retention.py', 'finalization.py'
    )
    sources = {}
    for name in source_names:
        p = module_root / name
        if p.is_file():
            sources[name] = hashlib.sha256(p.read_bytes()).hexdigest()

    v3_root = CONTRACT_ROOT.parent / 'v3'
    v3_contracts = {}
    for cname in ('public_retention.json', 'feature_registry.json', 'sampling_profiles.json'):
        cp = v3_root / cname
        if cp.is_file():
            try:
                v3_contracts[cname] = digest(json.loads(cp.read_text()))
            except Exception:
                v3_contracts[cname] = hashlib.sha256(cp.read_bytes()).hexdigest()

    reg_rev = None
    if registry is not None:
        reg_rev = digest(registry)
    elif 'feature_registry.json' in v3_contracts:
        reg_rev = v3_contracts['feature_registry.json']
    else:
        try:
            from .registry import REGISTRY_REVISION_V3 as reg_rev
        except ImportError:
            from .registry import REGISTRY_REVISION_V2 as reg_rev

    calibration_path = CONTRACT_ROOT.parent / 'v2' / 'realm_calibration.json'
    calibration = json.loads(calibration_path.read_text()) if calibration_path.is_file() else None
    scoring_path = CONTRACT_ROOT.parent / 'v2' / 'realm_scoring.json'
    scoring = json.loads(scoring_path.read_text()) if scoring_path.is_file() else None

    return digest([
        'catalog-automation-v3-r1',
        sources,
        v3_contracts,
        calibration,
        reg_rev,
        launch_definitions(),
        FAMILIES,
        scoring,
        automation_objectives_v3(),
    ])


def automation_offers_v3(
    observation: Dict[str, Any],
    summaries: Sequence[Dict[str, Any]],
    evaluations: Sequence[Dict[str, Any]],
    *,
    registry: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Offer a world's best eligible anchors into baseline, v2 and expanded v3 objective lists.

    - Reuses legacy v1 projections from v3 summaries with careful v2 layout bindings.
    - Preserves all v2 stronghold, fortress, bastion and Nether biome objective offers.
    - Evaluates 504 atomic OW biome nearest-witness lists (56 biomes x 3 borders x 3 modes).
    - Evaluates 9 igloo-with-basement nearest-witness lists (3 borders x 3 modes).
    - Evaluates 3 treasure-bastion nearest-witness lists (3 modes).
    - Gated features offer nothing.
    - Eligible nearest-witness rank: [d2, world_id, anchor_x, anchor_z, witness_x, witness_y, witness_z].
    - No synthetic origin fallback for spawn mode.
    """
    from .product_evaluation import product_offers
    from .models import validate_identity, world_id

    # Validate identity and compute world / observation digests
    validate_identity(observation['identity'])
    oid = digest(observation)
    wid = world_id(observation['identity'])

    if any(s.get('source_observation_id') != oid or s.get('world_id') != wid for s in summaries):
        raise ValueError('Retention summary source differs')

    # 1. Feature availability resolution
    available_map: Dict[str, bool] = {}
    if registry is not None:
        if isinstance(registry, dict) and 'features' in registry:
            for f in registry['features']:
                if isinstance(f, dict) and 'id' in f:
                    available_map[f['id']] = bool(f.get('available', True))
    else:
        try:
            from .registry import REGISTRY_V3
            if isinstance(REGISTRY_V3, dict) and 'features' in REGISTRY_V3:
                for f in REGISTRY_V3['features']:
                    if isinstance(f, dict) and 'id' in f:
                        available_map[f['id']] = bool(f.get('available', True))
        except (ImportError, AttributeError):
            pass

    def is_feature_available(fid: str) -> bool:
        if fid in available_map:
            return available_map[fid]
        # Default gates if not in registry
        return fid not in GATED_V3_FEATURES_DEFAULT

    # 2. Legacy baseline offers (v1 6,931 objectives) via v2 anchor bindings
    grid = {
        s['legacy']['layout_id']: s['legacy']
        for s in summaries
        if 'legacy' in s and 'recommended' in s.get('anchor_modes', ()) and s['legacy'].get('revision') == 'catalog-summary-v1'
    }
    selected = retain(list(grid.values()), [observation['identity']])
    offers = []
    for objective, members in selected['objectives'].items():
        for member in members:
            rank = list(member['rank'])
            if member.get('layout_id') is not None:
                layout = grid[member['layout_id']]
                # Metrics and new witnesses change source IDs, not geometric tie preference.
                rank[-1] = digest(['automation-anchor-v2', wid, layout['anchor'], layout['border_side']])
            if objective_family(objective) in ('profiles', 'diversity'):
                rank[0] = dict(decimal=rank[0])
            offers.append(dict(
                objective_id=objective,
                rank=rank,
                member=dict(member, rank=list(rank), source_observation_id=oid)
            ))

    # 3. Best-per-world collector for v2 and v3 added objectives
    best: Dict[str, Tuple[Tuple[Any, ...], Dict[str, Any]]] = {}

    def offer(obj_id: str, rank_key: Sequence[Any], s: Dict[str, Any], member_extra: Optional[Dict[str, Any]] = None):
        member = dict(
            world_id=wid,
            layout_id=s['layout_id'],
            anchor=s['anchor'],
            source_observation_id=s['source_observation_id'],
        )
        if member_extra:
            member.update(member_extra)
        key = tuple(rank_key)
        if obj_id not in best or key < best[obj_id][0]:
            best[obj_id] = (key, member)

    # 4. v2 objectives evaluation across summaries
    for s in summaries:
        for mode in MODES:
            if mode not in s.get('anchor_modes', ()):
                continue
            side = s['border_side']
            s_feats = s.get('features', {})

            if 'structure.stronghold' in s_feats:
                f = s_feats['structure.stronghold']
                for scope, c in enumerate(f['counts']):
                    if c and f['complete'][scope]:
                        offer(f'v2.count:structure.stronghold:{scope}:{side}:{mode}', [-c, wid, *s['anchor']], s)
                if f['nearest_d2'] is not None and f['nearest_d2'] <= 256**2:
                    offer(f'v2.near:structure.stronghold:{side}:{mode}', [f['nearest_d2'], wid, *s['anchor']], s)

            # Nether fixed window is evaluated once (bound to SIDES[0])
            if side != SIDES[0]:
                continue

            for feature in ('structure.fortress', 'structure.bastion'):
                if feature in s_feats:
                    f = s_feats[feature]
                    for scope, c in enumerate(f['counts']):
                        if c and f['complete'][scope]:
                            offer(f'v2.count:{feature}:{scope}:{mode}', [-c, wid, *s['anchor']], s)
                    if f['nearest_d2'] is not None and f['nearest_d2'] <= 64**2:
                        offer(f'v2.near:{feature}:{mode}', [f['nearest_d2'], wid, *s['anchor']], s)

            for biome in ('nether_wastes', 'crimson_forest', 'warped_forest', 'soul_sand_valley', 'basalt_deltas'):
                feature_name = 'biome.' + biome
                if feature_name in s_feats:
                    f = s_feats[feature_name]
                    if f['nearest_d2'] is not None and f['nearest_d2'] <= 256**2:
                        offer(f'v2.near:{feature_name}:{mode}', [f['nearest_d2'], wid, *s['anchor']], s)

    # 5. v3 objectives evaluation: atomic56x9 + basement9 + treasure3
    for s in summaries:
        s_modes = s.get('anchor_modes', ())
        active_modes = []
        if 'origin' in s_modes:
            active_modes.append('origin')
        if 'recommended' in s_modes:
            active_modes.append('recommended')
        # Spawn mode requires an actual compatible spawn anchor (no origin fallback)
        if 'world_spawn_estimated' in s_modes and any(a['mode']=='world_spawn_estimated' and a['coordinate']==s['anchor'] for a in observation.get('anchors',[])):
            active_modes.append('spawn')

        if not active_modes:
            continue

        side = s['border_side']
        s_feats = s.get('features', {})
        ax, az = s['anchor']
        lo_x = ax - side // 2
        hi_x = ax + side // 2
        lo_z = az - side // 2
        hi_z = az + side // 2

        for mode in active_modes:
            # --- 56 Atomic Overworld Biomes ---
            for b in ATOMIC_OW_BIOMES_56:
                fid = f'biome.exact.{b}'
                if not is_feature_available(fid):
                    continue
                f = s_feats.get(fid) or s_feats.get(b)
                if f and f.get('nearest_d2') is not None and f.get('witness') is not None:
                    wit = f['witness']
                    # Witness must be inside the selected border
                    if lo_x <= wit[0] < hi_x and lo_z <= wit[2] < hi_z:
                        wy = 0 if wit[1] is None else int(wit[1])
                        rank_v3 = [int(f['nearest_d2']), wid, int(ax), int(az), int(wit[0]), wy, int(wit[2])]
                        oid = f'v3.near:{fid}:{side}:{mode}'
                        offer(oid, rank_v3, s, member_extra={'witness': wit, 'feature_id': fid})

            # --- Igloo with basement (Overworld, 3 sides x 3 modes) ---
            fid_igloo = 'structure.igloo_with_basement'
            if is_feature_available(fid_igloo):
                f = s_feats.get(fid_igloo)
                if f and f.get('nearest_d2') is not None and f.get('witness') is not None:
                    wit = f['witness']
                    if lo_x <= wit[0] < hi_x and lo_z <= wit[2] < hi_z:
                        wy = 0 if wit[1] is None else int(wit[1])
                        rank_v3 = [int(f['nearest_d2']), wid, int(ax), int(az), int(wit[0]), wy, int(wit[2])]
                        oid = f'v3.near:{fid_igloo}:{side}:{mode}'
                        offer(oid, rank_v3, s, member_extra={'witness': wit, 'feature_id': fid_igloo})

            # --- Bastion treasure (Nether fixed window: only for side == SIDES[0]) ---
            fid_treasure = 'structure.bastion_treasure'
            if is_feature_available(fid_treasure) and side == SIDES[0]:
                f = s_feats.get(fid_treasure)
                if f and f.get('nearest_d2') is not None and f.get('witness') is not None:
                    wit = f['witness']
                    nx,nz=s['nether_anchor']
                    if not nx-512<=wit[0]<nx+512 or not nz-512<=wit[2]<nz+512:continue
                    wy = 0 if wit[1] is None else int(wit[1])
                    rank_v3 = [int(f['nearest_d2']), wid, int(ax), int(az), int(wit[0]), wy, int(wit[2])]
                    oid = f'v3.near:{fid_treasure}:{mode}'
                    offer(oid, rank_v3, s, member_extra={'witness': wit, 'feature_id': fid_treasure})

    offers.extend(
        dict(objective_id=oid, rank=list(key), member=dict(member, rank=list(key)))
        for oid, (key, member) in best.items()
    )
    offers.extend(product_offers(evaluations))
    return offers


def objective_family(obj_id: str) -> str:
    if obj_id == 'reference_sample':
        return 'reference_sample'
    return obj_id.split(':', 1)[0]


def compare_key(obj_id: str, rank: Sequence[Any]) -> Tuple[Any, ...]:
    fam = objective_family(obj_id)
    if fam in ('profiles', 'diversity'):
        return (Decimal(str(rank[0])), *rank[1:])
    return tuple(rank)


def retain(
    layouts: Iterable[Dict[str, Any]],
    identities: Sequence[Dict[str, Any]],
    *,
    capacities: Optional[Dict[str, int]] = None,
    pins: Iterable[str] = (),
) -> Dict[str, Any]:
    """Retain catalog candidates into the frozen Top-K objective families."""
    # 1. Validate capacities
    caps = dict(DEFAULT_CAPACITIES)
    experiment = False
    if capacities is not None:
        if not isinstance(capacities, dict):
            raise ValueError('capacities must be a dict')
        unknown_keys = set(capacities) - set(DEFAULT_CAPACITIES)
        if unknown_keys:
            raise ValueError(f'Unknown capacity keys: {unknown_keys}')
        for k, v in capacities.items():
            if type(v) is not int or v < 0 or v > DEFAULT_CAPACITIES[k]:
                raise ValueError(f'Capacity for {k} must be integer in 0..{DEFAULT_CAPACITIES[k]}')
            caps[k] = v
        experiment = (caps != DEFAULT_CAPACITIES)

    # 2. Validate identities
    if not isinstance(identities, (list, tuple)):
        raise ValueError('identities must be a sequence of identity dictionaries')

    ident_by_wid: Dict[str, Dict[str, Any]] = {}
    known_seeds: Set[str] = set()
    common_header: Optional[Tuple[str, str, str, str, str]] = None

    for ident in identities:
        validate_identity(ident)
        wid = world_id(ident)
        if wid in ident_by_wid or ident['seed'] in known_seeds:
            raise ValueError(f'Duplicate identity or seed conflict: {wid}')
        ident_by_wid[wid] = ident
        known_seeds.add(ident['seed'])

        hdr = tuple(sorted((k,v) for k,v in ident.items() if k != 'seed'))
        if common_header is None:
            common_header = hdr
        elif common_header != hdr:
            raise ValueError('Mixed settings/build/revision in identities')

    # 3. Validate pins
    pinned_wids: Set[str] = set()
    for p in pins:
        if not isinstance(p, str) or p not in ident_by_wid:
            raise ValueError(f'Invalid pin not in population: {p}')
        pinned_wids.add(p)
    pins_list = sorted(list(pinned_wids))

    # 4. Validate layouts and group by world
    layouts_by_wid: Dict[str, List[Dict[str, Any]]] = {wid: [] for wid in ident_by_wid}
    layout_keys_seen: Set[Tuple[str, int, int, int]] = set()

    for l in layouts:
        validate_summary(l)
        wid = l['world_id']
        if wid not in ident_by_wid:
            raise ValueError(f'Layout references unknown world_id: {wid}')
        ident = ident_by_wid[wid]
        if l['seed'] != ident['seed']:
            raise ValueError(f'Layout seed does not match world identity seed: {l["seed"]}')

        layout_key = (wid, l['border_side'], l['anchor'][0], l['anchor'][1])
        if layout_key in layout_keys_seen:
            raise ValueError(f'Duplicate layout conflict for world {wid} at {l["anchor"]} side {l["border_side"]}')
        layout_keys_seen.add(layout_key)
        layouts_by_wid[wid].append(l)

    # 5. Evaluate stable-hash reference sample across all identities before relevance gates
    candidates_by_obj: Dict[str, List[Tuple[Tuple[Any, ...], Dict[str, Any]]]] = {
        oid: [] for oid in ALL_OBJECTIVE_IDS
    }

    def offer(oid, key, member):
        items = candidates_by_obj[oid]
        insort(items, (key, member), key=lambda item: item[0])
        del items[caps[objective_family(oid)]:]

    if caps['reference_sample'] > 0:
        for wid, ident in ident_by_wid.items():
            payload = [
                REFERENCE_SALT,
                ident['edition'],
                ident['game_build_id'],
                ident['world_settings_id'],
                ident['seed'],
            ]
            digest_hex = hashlib.sha256(canonical_json(payload)).hexdigest()
            rank_key = (digest_hex, ident['edition'], ident['game_build_id'], ident['world_settings_id'], int(ident['seed']) & ((1<<64)-1), wid)
            member = {
                'world_id': wid,
                'layout_id': None,
                'rank': list(rank_key),
            }
            offer('reference_sample', rank_key, member)

    # 6. Evaluate layout-based objectives per world
    div_bits_biomes = DIVERSITY_BITS[:4]
    div_bits_structures = DIVERSITY_BITS[4:]
    div_biome_slots = [BIOME_SLOTS[bid] for bid in div_bits_biomes]
    div_struct_slots = [STRUCTURE_SLOTS[sid] for sid in div_bits_structures]

    for wid, world_layouts in layouts_by_wid.items():
        if not world_layouts:
            continue

        # Group world layouts by border_side
        by_side: Dict[int, List[Dict[str, Any]]] = {side: [] for side in SIDES}
        for l in world_layouts:
            by_side[l['border_side']].append(l)

        for side in SIDES:
            layouts_side = by_side[side]
            if not layouts_side:
                continue

            origin_layout = next((l for l in layouts_side if l['anchor'] == [0, 0]), None)

            for mode in MODES:
                cand_layouts = [origin_layout] if mode == 'origin' else layouts_side
                if not cand_layouts or (mode == 'origin' and origin_layout is None):
                    continue

                # --- Family 1: structure_count ---
                if caps['structure_count'] > 0:
                    for f in STRUCTURES:
                        s_slot = f['slot']
                        f_id = f['id']
                        for scope_idx in range(4):
                            best_key = None
                            best_m = None
                            for l in cand_layouts:
                                if l['complete'][s_slot][scope_idx]:
                                    cnt = l['counts'][s_slot][scope_idx]
                                    if cnt >= 1:
                                        d2 = l['structure_nearest_d2'][s_slot]
                                        tail = canonical_tail(l)
                                        key = (-cnt, d2, *tail)
                                        if best_key is None or key < best_key:
                                            best_key = key
                                            best_m = {
                                                'world_id': wid,
                                                'layout_id': l['layout_id'],
                                                'rank': list(key),
                                            }
                            if best_m is not None:
                                obj_id = f"structure_count:{f_id}:{scope_idx}:{side}:{mode}"
                                offer(obj_id, best_key, best_m)

                # --- Family 2: structure_proximity ---
                if caps['structure_proximity'] > 0:
                    for f in STRUCTURES:
                        s_slot = f['slot']
                        f_id = f['id']
                        best_key = None
                        best_m = None
                        for l in cand_layouts:
                            if l['complete'][s_slot][0] and l['complete'][s_slot][3]:
                                d2 = l['structure_nearest_d2'][s_slot]
                                if d2 != MISSING and d2 <= 256 * 256:
                                    inside_cnt = l['counts'][s_slot][3]
                                    tail = canonical_tail(l)
                                    key = (d2, -inside_cnt, *tail)
                                    if best_key is None or key < best_key:
                                        best_key = key
                                        best_m = {
                                            'world_id': wid,
                                            'layout_id': l['layout_id'],
                                            'rank': list(key),
                                        }
                        if best_m is not None:
                            obj_id = f"structure_proximity:{f_id}:{side}:{mode}"
                            offer(obj_id, best_key, best_m)

                # --- Family 3: biome_proximity ---
                if caps['biome_proximity'] > 0:
                    for b in BIOMES:
                        b_slot = b['slot']
                        b_id = b['id']
                        best_key = None
                        best_m = None
                        for l in cand_layouts:
                            if l['complete'][14 + b_slot][2]:
                                d2 = l['biome_nearest_d2'][b_slot]
                                if d2 != MISSING and d2 <= 1024 * 1024:
                                    tail = canonical_tail(l)
                                    key = (d2, *tail)
                                    if best_key is None or key < best_key:
                                        best_key = key
                                        best_m = {
                                            'world_id': wid,
                                            'layout_id': l['layout_id'],
                                            'rank': list(key),
                                        }
                        if best_m is not None:
                            obj_id = f"biome_proximity:{b_id}:{side}:{mode}"
                            offer(obj_id, best_key, best_m)

                # --- Family 4: biome_landmark_pairs ---
                if caps['biome_landmark_pairs'] > 0:
                    for b in BIOMES:
                        b_slot = b['slot']
                        b_id = b['id']
                        for lmark in PAIR_LANDMARKS:
                            l_slot = STRUCTURE_SLOTS[lmark]
                            best_key = None
                            best_m = None
                            for l in cand_layouts:
                                if l['complete'][14 + b_slot][0] and l['complete'][l_slot][1]:
                                    b_d2 = l['biome_nearest_d2'][b_slot]
                                    if b_d2 != MISSING and b_d2 <= 256 * 256:
                                        l_cnt = l['counts'][l_slot][1]
                                        if l_cnt >= 1:
                                            l_d2 = l['structure_nearest_d2'][l_slot]
                                            tail = canonical_tail(l)
                                            key = (-l_cnt, b_d2, l_d2, *tail)
                                            if best_key is None or key < best_key:
                                                best_key = key
                                                best_m = {
                                                    'world_id': wid,
                                                    'layout_id': l['layout_id'],
                                                    'rank': list(key),
                                                }
                            if best_m is not None:
                                obj_id = f"biome_landmark_pairs:{b_id}:{lmark}:{side}:{mode}"
                                offer(obj_id, best_key, best_m)

                # --- Family 5: profiles ---
                if caps['profiles'] > 0:
                    for p in POLICY['profiles']:
                        p_id = p['id']
                        best_key = None
                        best_m = None
                        for l in cand_layouts:
                            tot, denom, flag = profile_units(l, p_id)
                            if flag:
                                tail = canonical_tail(l)
                                key = (-tot, *tail)
                                if best_key is None or key < best_key:
                                    best_key = key
                                    best_m = {
                                        'world_id': wid,
                                        'layout_id': l['layout_id'],
                                        'rank': [str(-tot), *tail],
                                    }
                        if best_m is not None:
                            obj_id = f"profiles:{p_id}:{side}:{mode}"
                            offer(obj_id, best_key, best_m)

                # --- Family 6: diversity ---
                if caps['diversity'] > 0:
                    # Map each eligible layout to its single 8-bit cell
                    best_div_by_cell_prof: Dict[Tuple[int, str], Tuple[Tuple[Any, ...], Dict[str, Any]]] = {}
                    for l in cand_layouts:
                        all8 = (
                            all(l['complete'][14 + b_s][2] for b_s in div_biome_slots)
                            and all(l['complete'][s_s][2] for s_s in div_struct_slots)
                        )
                        if not all8:
                            continue

                        # Compute 8-bit cell
                        b0 = l['biome_nearest_d2'][div_biome_slots[0]] <= 1024 * 1024 and l['biome_nearest_d2'][div_biome_slots[0]] != MISSING
                        b1 = l['biome_nearest_d2'][div_biome_slots[1]] <= 1024 * 1024 and l['biome_nearest_d2'][div_biome_slots[1]] != MISSING
                        b2 = l['biome_nearest_d2'][div_biome_slots[2]] <= 1024 * 1024 and l['biome_nearest_d2'][div_biome_slots[2]] != MISSING
                        b3 = l['biome_nearest_d2'][div_biome_slots[3]] <= 1024 * 1024 and l['biome_nearest_d2'][div_biome_slots[3]] != MISSING
                        b4 = l['counts'][div_struct_slots[0]][2] >= 1
                        b5 = l['counts'][div_struct_slots[1]][2] >= 1
                        b6 = l['counts'][div_struct_slots[2]][2] >= 1
                        b7 = l['counts'][div_struct_slots[3]][2] >= 1

                        cell = (
                            int(b0)
                            | (int(b1) << 1)
                            | (int(b2) << 2)
                            | (int(b3) << 3)
                            | (int(b4) << 4)
                            | (int(b5) << 5)
                            | (int(b6) << 6)
                            | (int(b7) << 7)
                        )

                        tail = canonical_tail(l)
                        for p_id in DIVERSITY_PROFILES:
                            tot, denom, flag = profile_units(l, p_id)
                            if flag:
                                key = (-tot, *tail)
                                cell_prof = (cell, p_id)
                                if cell_prof not in best_div_by_cell_prof or key < best_div_by_cell_prof[cell_prof][0]:
                                    best_div_by_cell_prof[cell_prof] = (
                                        key,
                                        {
                                            'world_id': wid,
                                            'layout_id': l['layout_id'],
                                            'rank': [str(-tot), *tail],
                                        },
                                    )

                    for (cell, p_id), (b_key, b_m) in best_div_by_cell_prof.items():
                        obj_id = f"diversity:{cell}:{p_id}:{side}:{mode}"
                        offer(obj_id, b_key, b_m)

    # 7. Finalize Top-K members for all 6,931 objectives
    final_objectives: Dict[str, List[Dict[str, Any]]] = {}
    retained_wids: Set[str] = set(pins_list)

    for obj_id in ALL_OBJECTIVE_IDS:
        fam = objective_family(obj_id)
        k = caps[fam]
        cands = candidates_by_obj[obj_id]
        if k == 0 or not cands:
            final_objectives[obj_id] = []
        else:
            if fam != 'reference_sample':
                cands.sort(key=lambda item: item[0])
            members = [item[1] for item in cands[:k]]
            final_objectives[obj_id] = members
            for m in members:
                retained_wids.add(m['world_id'])

    world_ids = sorted(list(retained_wids))

    return {
        'policy_revision': POLICY_REVISION,
        'build_revision': digest(common_header) if common_header is not None else None,
        'experiment': experiment,
        'capacities': caps,
        'objectives': final_objectives,
        'world_ids': world_ids,
        'pins': pins_list,
    }


def merge(selections: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge partition-local selections into the canonical public selection shape.

    Freezes objective IDs, capacity settings, and policy revision across partitions.
    Resolves overlapping worlds by their best anchor; identical layouts must agree.
    Deduplicates unique worlds before taking Top-K for each objective.
    """
    if not isinstance(selections, (list, tuple)) or not selections:
        raise ValueError('selections must be a non-empty sequence of selection dicts')

    s0 = selections[0]
    expected_keys = {'build_revision', 'policy_revision', 'experiment', 'capacities', 'objectives', 'world_ids', 'pins'}
    for s in selections:
        if not isinstance(s, dict) or set(s) != expected_keys:
            raise ValueError('Invalid selection dictionary shape')
        if s['policy_revision'] != POLICY_REVISION:
            raise ValueError('Unknown policy_revision')
        if s['build_revision'] != s0['build_revision']:
            raise ValueError('Conflicting build_revision across selections')
        if s['policy_revision'] != s0['policy_revision']:
            raise ValueError('Conflicting policy_revision across selections')
        if s['capacities'] != s0['capacities']:
            raise ValueError('Conflicting capacities across selections')
        if s['experiment'] != s0['experiment']:
            raise ValueError('Conflicting experiment flag across selections')
        if set(s['capacities']) != set(DEFAULT_CAPACITIES) or any(type(v) is not int or not 0<=v<=DEFAULT_CAPACITIES[k] for k,v in s['capacities'].items()):
            raise ValueError('Invalid capacities')
        if type(s['experiment']) is not bool or s['experiment'] != (s['capacities'] != DEFAULT_CAPACITIES):
            raise ValueError('Invalid experiment flag')
        if set(s['objectives']) != set(ALL_OBJECTIVE_IDS):
            raise ValueError('Conflicting objective IDs across selections')
        union=set(s['pins'])
        for oid,members in s['objectives'].items():
            if not isinstance(members,list) or len(members)>s['capacities'][objective_family(oid)]:
                raise ValueError('Invalid objective membership size')
            seen=set();keys=[]
            for member in members:
                if not isinstance(member,dict) or set(member)!={'world_id','layout_id','rank'}:
                    raise ValueError('Invalid member shape')
                wid=member['world_id'];rank=member['rank'];fam=objective_family(oid)
                if not isinstance(wid,str) or len(wid)!=64 or any(c not in '0123456789abcdef' for c in wid) or wid in seen:
                    raise ValueError('Invalid or duplicate member world')
                expected_length={'structure_count':6,'structure_proximity':6,'biome_proximity':5,
                    'biome_landmark_pairs':7,'profiles':5,'diversity':5,'reference_sample':6}[fam]
                if not isinstance(rank,list) or len(rank)!=expected_length:
                    raise ValueError('Invalid rank shape')
                if fam in ('profiles','diversity') and not Decimal(str(rank[0])).is_finite():
                    raise ValueError('Non-finite profile rank')
                if fam=='reference_sample':
                    if member['layout_id'] is not None:raise ValueError('Invalid reference layout')
                elif member['layout_id']!=rank[-1]:raise ValueError('Rank/layout mismatch')
                seen.add(wid);union.add(wid);keys.append(compare_key(oid,rank))
            if keys!=sorted(keys):raise ValueError('Objective members must be sorted')
        if s['world_ids']!=sorted(union) or s['pins']!=sorted(set(s['pins'])):
            raise ValueError('Selection union/pins mismatch')

    merged_objectives: Dict[str, List[Dict[str, Any]]] = {}
    all_pins: Set[str] = set()
    for s in selections:
        all_pins.update(s['pins'])
    merged_pins = sorted(list(all_pins))

    retained_wids: Set[str] = set(merged_pins)

    for obj_id in ALL_OBJECTIVE_IDS:
        fam = objective_family(obj_id)
        k = s0['capacities'][fam]

        world_members: Dict[str, Dict[str, Any]] = {}
        for s in selections:
            members = s['objectives'][obj_id]
            for m in members:
                wid = m['world_id']
                if wid in world_members:
                    existing = world_members[wid]
                    if existing['layout_id'] == m['layout_id'] and existing['rank'] != m['rank']:
                        raise ValueError(f'Conflicting rank/layout for world {wid} in objective {obj_id}')
                    if compare_key(obj_id,m['rank']) < compare_key(obj_id,existing['rank']):
                        world_members[wid] = m
                else:
                    world_members[wid] = m

        if k == 0 or not world_members:
            merged_objectives[obj_id] = []
        else:
            candidates = list(world_members.values())
            candidates.sort(key=lambda m: compare_key(obj_id, m['rank']))
            top_k = candidates[:k]
            merged_objectives[obj_id] = top_k
            for m in top_k:
                retained_wids.add(m['world_id'])

    merged_world_ids = sorted(list(retained_wids))

    return {
        'policy_revision': s0['policy_revision'],
        'build_revision': s0['build_revision'],
        'experiment': s0['experiment'],
        'capacities': dict(s0['capacities']),
        'objectives': merged_objectives,
        'world_ids': merged_world_ids,
        'pins': merged_pins,
    }
