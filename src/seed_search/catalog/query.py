"""Strict layout search and scoring engine over catalog summaries.

Evaluates request-relative satisfaction, exact utility fractions and quantized
distance ties without floating-point tie arithmetic. Deduplicates to unique-world
top-K results before truncating.
"""
import math
from decimal import Decimal, localcontext
from .request import validate_request, load_request
from .registry import STRUCTURES, BIOMES, PROFILES, RADII
from .models import observation_id, validate_observation, world_id
from .codec import validate_summary, MISSING

LCM = 720720  # math.lcm(*range(1, 17))
RADII_MAP = {r: i for i, r in enumerate(RADII)}
STRUCTURE_SLOTS = {f['id']: f['slot'] for f in STRUCTURES}
BIOME_SLOTS = {f['id']: f['slot'] for f in BIOMES}


def search(layouts, request, *, snapshot_id, limit=5, observations=None):
    """Search layouts against a validated request, returning unique-world results."""
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError('Result limit must be1..50')
    layouts = list(layouts)
    if isinstance(request, str):
        req = load_request(request, snapshot_id=snapshot_id)
    else:
        req = validate_request(request, snapshot_id=snapshot_id)

    if observations is not None:
        if isinstance(observations, dict):
            obs_list = list(observations.values())
        elif isinstance(observations, (list, tuple)):
            obs_list = list(observations)
        else:
            raise ValueError('observations must be a list or mapping')

        allowed_obs_ids = set()
        obs_by_id = {}
        build_headers = set()
        for obs in obs_list:
            if not isinstance(obs, dict) or 'identity' not in obs:
                raise ValueError('Invalid observation structure')
            ident = obs['identity']
            if ident.get('game_build_id') != req['game_build_id']:
                raise ValueError(f"Incompatible game_build_id: {ident.get('game_build_id')}")
            if ident.get('world_settings_id') != req['world_settings_id']:
                raise ValueError(f"Incompatible world_settings_id: {ident.get('world_settings_id')}")
            if ident.get('edition') != req['edition']:
                raise ValueError(f"Incompatible edition: {ident.get('edition')}")
            validate_observation(obs)
            oid = observation_id(obs)
            allowed_obs_ids.add(oid)
            obs_by_id[oid] = obs
            build_headers.add(tuple((k, v) for k, v in sorted(ident.items()) if k != 'seed'))
        if len(build_headers) > 1:
            raise ValueError('Mixed predictor/build identities in one query snapshot')

        for l in layouts:
            if l.get('observation_id') not in allowed_obs_ids:
                raise ValueError(f"Layout references unknown observation: {l.get('observation_id')}")
            obs = obs_by_id[l['observation_id']]
            if l.get('seed') != obs['identity']['seed'] or l.get('world_id') != world_id(obs['identity']):
                raise ValueError('Layout identity is not bound to its observation')

    return _rank(layouts, req, limit, validate_records=True)


def _rank(layouts, req, limit, *, validate_records, keep_keys=False, positive_witnesses=False):
    """Internal scorer; only immutable verified views skip per-record validation."""
    req_side = req['border_side']
    is_origin = (req['anchor_mode'] == 'origin')

    required_rows = [r for r in req['rows'] if r['rule'] == 'required']
    preferred_rows = [r for r in req['rows'] if r['rule'] == 'preferred']

    candidate_layouts = []

    for layout in layouts:
        if validate_records:
            validate_summary(layout)
        if layout['border_side'] != req_side:
            continue
        if is_origin and tuple(layout['anchor']) != (0, 0):
            continue

        # Evaluate Required rows: ALL must pass on this same layout
        passed_all_required = True
        for r in required_rows:
            scope_kind = r['scope']['kind']
            scope_idx = 3 if scope_kind == 'inside_border' else RADII_MAP[r['scope']['radius']]

            if r['kind'] == 'structure_count':
                s_idx = STRUCTURE_SLOTS[r['feature']]
                count = layout['counts'][s_idx][scope_idx]
                at_least = r['at_least']
                if not layout['complete'][s_idx][scope_idx] or count < at_least:
                    passed_all_required = False
                    break
            elif r['kind'] == 'biome_witness':
                any_of = r['any_of']
                if not positive_witnesses and not all(layout['complete'][14+BIOME_SLOTS[bid]][scope_idx] for bid in any_of):
                    passed_all_required = False
                    break
                radius = r['scope']['radius'] if scope_kind == 'near_base' else None
                r2 = radius ** 2 if radius is not None else None

                has_witness = False
                for b_id in any_of:
                    b_slot = BIOME_SLOTS[b_id]
                    d2 = layout['biome_nearest_d2'][b_slot]
                    if d2 != MISSING and (r2 is None or d2 <= r2):
                        has_witness = True
                        break
                if not has_witness:
                    passed_all_required = False
                    break

        if not passed_all_required:
            continue

        # Distance tie calculation across ALL selected rows in request
        distance_tie = 0
        for r in req['rows']:
            scope_kind = r['scope']['kind']
            normalizer = req_side // 2 if scope_kind == 'inside_border' else r['scope']['radius']
            scope_idx = 3 if scope_kind == 'inside_border' else RADII_MAP[r['scope']['radius']]
            radius = r['scope']['radius'] if scope_kind == 'near_base' else None
            r2 = radius ** 2 if radius is not None else None

            if r['kind'] == 'structure_count':
                s_idx = STRUCTURE_SLOTS[r['feature']]
                count = layout['counts'][s_idx][scope_idx]
                d2 = layout['structure_nearest_d2'][s_idx]
                if not layout['complete'][s_idx][scope_idx] or count == 0 or d2 == MISSING or (r2 is not None and d2 > r2):
                    term = 1_000_000
                else:
                    term = min(math.isqrt(d2 * 10**12) // normalizer, 1_000_000)
            elif r['kind'] == 'biome_witness':
                min_d2 = MISSING
                for b_id in r['any_of']:
                    b_slot = BIOME_SLOTS[b_id]
                    d2 = layout['biome_nearest_d2'][b_slot]
                    if d2 != MISSING and (r2 is None or d2 <= r2):
                        if min_d2 == MISSING or d2 < min_d2:
                            min_d2 = d2
                if not positive_witnesses and not all(layout['complete'][14+BIOME_SLOTS[bid]][scope_idx] for bid in r['any_of']):
                    min_d2 = MISSING
                if min_d2 == MISSING:
                    term = 1_000_000
                else:
                    term = min(math.isqrt(min_d2 * 10**12) // normalizer, 1_000_000)
            distance_tie += term

        # Utility scoring
        if preferred_rows:
            total_units = 0
            max_units = 0
            contributions = []
            for r in preferred_rows:
                w = r['importance']
                max_units += w * LCM
                scope_kind = r['scope']['kind']
                scope_idx = 3 if scope_kind == 'inside_border' else RADII_MAP[r['scope']['radius']]

                if r['kind'] == 'structure_count':
                    s_idx = STRUCTURE_SLOTS[r['feature']]
                    count = layout['counts'][s_idx][scope_idx]
                    is_comp = layout['complete'][s_idx][scope_idx]
                    at_least = r['at_least']
                    frac_num = min(count, at_least)
                    units = w * (frac_num * LCM // at_least) if is_comp else 0
                    status = 'known' if is_comp else 'unknown'
                    contributions.append({
                        'feature': r['feature'],
                        'rule': 'preferred',
                        'kind': 'structure_count',
                        'count': count,
                        'at_least': at_least,
                        'importance': w,
                        'utility_units': units,
                        'max_units': w * LCM,
                        'complete': is_comp,
                        'status': status,
                    })
                    total_units += units
                elif r['kind'] == 'biome_witness':
                    any_of = r['any_of']
                    radius = r['scope']['radius'] if scope_kind == 'near_base' else None
                    r2 = radius ** 2 if radius is not None else None
                    witness_found = False
                    witness_b_id = None
                    for b_id in any_of:
                        b_slot = BIOME_SLOTS[b_id]
                        d2 = layout['biome_nearest_d2'][b_slot]
                        if d2 != MISSING and (r2 is None or d2 <= r2):
                            witness_found = True
                            witness_b_id = b_id
                            break
                    all_comp = all(layout['complete'][14 + BIOME_SLOTS[b_id]][scope_idx] for b_id in any_of)
                    if witness_found and (all_comp or positive_witnesses):
                        units = w * LCM
                        status = 'known'
                    else:
                        units = 0
                        status = 'known' if all_comp and not positive_witnesses else 'unknown'
                    contributions.append({
                        'any_of': any_of,
                        'rule': 'preferred',
                        'kind': 'biome_witness',
                        'witness_found': witness_found,
                        'witness_feature': witness_b_id,
                        'importance': w,
                        'utility_units': units,
                        'max_units': w * LCM,
                        'complete': all_comp,
                        'status': status,
                    })
                    total_units += units
            score = (total_units * 100.0) / max_units
        else:
            # Fallback profile evaluation on scope 2 (near 1024)
            profile_id = req['fallback_profile']
            coefficients = PROFILES[profile_id]
            coeff_sum = sum(coefficients)

            v_count = layout['counts'][0][2]
            t_count = layout['counts'][1][2]
            a_count = layout['counts'][2][2]
            o_count = layout['counts'][4][2] + layout['counts'][12][2]
            e_count = sum(1 for s in range(14) if layout['counts'][s][2] > 0)
            b_count = sum(
                1 for b in range(9)
                if layout['biome_nearest_d2'][b] != MISSING and layout['biome_nearest_d2'][b] <= 1048576
            )
            r_count = (
                layout['counts'][7][2] + layout['counts'][8][2] +
                layout['counts'][9][2] + layout['counts'][10][2]
            )

            u_V = min(v_count, 6) * (LCM // 6)
            u_T = min(t_count, 4) * (LCM // 4)
            u_A = min(a_count, 2) * (LCM // 2)
            u_O = min(o_count, 6) * (LCM // 6)
            u_E = e_count * (LCM // 14)
            u_B = min(b_count, 8) * (LCM // 8)
            u_R = min(r_count, 4) * (LCM // 4)

            if v_count == 0:
                u_H = 0
            else:
                d2 = layout['structure_nearest_d2'][0]
                with localcontext() as context:
                    context.prec = 50
                    u_H = max(Decimal(0), Decimal(1)-Decimal(d2).sqrt()/1024)*LCM

            feature_units = [u_V, u_T, u_A, u_O, u_E, u_B, u_H, u_R]
            groups = ((0,), (1,), (2,), (4,12), tuple(range(14)),
                      tuple(range(14,23)), (0,), (7,8,9,10))
            component_known = [all(layout['complete'][slot][2] for slot in group) for group in groups]
            feature_units = [units if known else 0 for units,known in zip(feature_units,component_known)]
            with localcontext() as context:
                context.prec = 50
                total_units = sum(c * u for c, u in zip(coefficients, feature_units))
            max_units = coeff_sum * LCM
            score = float(total_units * 100 / max_units) if max_units > 0 else 0.0
            contributions = [
                {'feature': k, 'coefficient': c, 'utility_units': float(u), 'max_units': LCM,
                 'status': 'known' if known else 'unknown'}
                for k, c, u, known in zip('VTAOEBHR', coefficients, feature_units, component_known)
            ]

        unsigned_seed = int(layout['seed']) & ((1 << 64) - 1)
        sort_key = (
            -total_units,
            distance_tie,
            unsigned_seed,
            layout['anchor'][0],
            layout['anchor'][1],
            layout['layout_id'],
        )

        candidate = {
            'world_id': layout['world_id'],
            'seed': layout['seed'],
            'layout_id': layout['layout_id'],
            'anchor': list(layout['anchor']),
            'border_side': layout['border_side'],
            'score': score,
            'utility_units': int(total_units),
            'distance_tie': distance_tie,
            'contributions': contributions,
            '_sort_key': sort_key,
        }
        candidate_layouts.append(candidate)

    # Group best layout by world BEFORE applying Top-K limit
    best_by_world = {}
    for cand in candidate_layouts:
        wid = cand['world_id']
        if wid not in best_by_world or cand['_sort_key'] < best_by_world[wid]['_sort_key']:
            best_by_world[wid] = cand

    ranked = sorted(best_by_world.values(), key=lambda c: c['_sort_key'])
    results = ranked[:limit]
    if not keep_keys:
        for r in results:
            r.pop('_sort_key', None)
    return results


from .request import validate_request_v2, load_request_v2, validate_request_v3, load_request_v3
from .registry import FEATURES_V2, FEATURE_BY_ID_V2, REGISTRY_V2, REGISTRY_V3
from .geometry import bounds_for
from . import scoring

OW_RADII_MAP = {r: i for i, r in enumerate(REGISTRY_V2['overworld_radii'])}
NETHER_RADII_MAP = {r: i for i, r in enumerate(REGISTRY_V2['nether_radii'])}


def _rank_features(summaries, req, limit=1000, *, keep_keys=False, registry=None):
    if type(limit) is not int or limit < 1:
        raise ValueError('Limit must be a positive integer')

    active_registry = registry if registry is not None else REGISTRY_V2
    feature_by_id = {f['id']: f for f in active_registry['features']}
    ow_radii_map = {r: i for i, r in enumerate(active_registry.get('overworld_radii', (256, 512, 1024)))}
    nether_radii_map = {r: i for i, r in enumerate(active_registry.get('nether_radii', (64, 128, 256)))}

    req_side = req['border_side']
    req_mode = req['anchor_mode']

    required_rows = [r for r in req['rows'] if r['rule'] == 'required']
    preferred_rows = [r for r in req['rows'] if r['rule'] == 'preferred']

    best_matches_by_world = {}
    best_pending_by_world = {}

    for summary in summaries:
        if summary.get('border_side') != req_side:
            continue
        if req_mode not in summary.get('anchor_modes', []):
            continue

        # Evaluate Required rows: ALL must pass on this same summary
        has_failed_required = False
        has_pending_required = False
        pending_reasons = []

        for r in required_rows:
            scope_kind = r['scope']['kind']
            if r['kind'] == 'structure_count':
                feat_id = r['feature']
                dim = feature_by_id[feat_id]['dimension']
                scope_idx = 3 if scope_kind == 'inside_border' else (
                    ow_radii_map[r['scope']['radius']] if dim == 'overworld' else nether_radii_map[r['scope']['radius']]
                )
                feat_data = summary['features'][feat_id]
                count = feat_data['counts'][scope_idx]
                comp = feat_data['complete'][scope_idx]
                at_least = r['at_least']
                if count >= at_least:
                    pass
                else:
                    if comp:
                        has_failed_required = True
                        break
                    else:
                        has_pending_required = True
                        pending_reasons.append(f"{feat_id} count {count} < {at_least} (incomplete)")
            elif r['kind'] == 'biome_witness':
                any_of = r['any_of']
                dim = feature_by_id[any_of[0]]['dimension']
                scope_idx = 3 if scope_kind == 'inside_border' else (
                    ow_radii_map[r['scope']['radius']] if dim == 'overworld' else nether_radii_map[r['scope']['radius']]
                )
                has_witness = False
                for b_id in any_of:
                    if summary['features'][b_id]['counts'][scope_idx] > 0:
                        has_witness = True
                        break
                if has_witness:
                    pass
                else:
                    has_pending_required = True
                    pending_reasons.append(f"biome witness missing for {any_of}")

        if has_failed_required:
            continue

        # Distance tie calculation across ALL selected rows in request
        distance_tie = 0
        for r in req['rows']:
            scope_kind = r['scope']['kind']
            if r['kind'] == 'structure_count':
                feat_id = r['feature']
                dim = feature_by_id[feat_id]['dimension']
                scope_idx = 3 if scope_kind == 'inside_border' else (
                    ow_radii_map[r['scope']['radius']] if dim == 'overworld' else nether_radii_map[r['scope']['radius']]
                )
                normalizer = (req_side // 2 if dim == 'overworld' else 512) if scope_kind == 'inside_border' else r['scope']['radius']
                feat_data = summary['features'][feat_id]
                count = feat_data['counts'][scope_idx]
                d2 = feat_data['nearest_d2']
                radius = r['scope']['radius'] if scope_kind == 'near_base' else None
                r2 = radius ** 2 if radius is not None else None
                if count == 0 or d2 is None or (r2 is not None and d2 > r2):
                    term = 1_000_000
                else:
                    term = min(math.isqrt(d2 * 10**12) // normalizer, 1_000_000)
                distance_tie += term
            elif r['kind'] == 'biome_witness':
                any_of = r['any_of']
                dim = feature_by_id[any_of[0]]['dimension']
                scope_idx = 3 if scope_kind == 'inside_border' else (
                    ow_radii_map[r['scope']['radius']] if dim == 'overworld' else nether_radii_map[r['scope']['radius']]
                )
                normalizer = (req_side // 2 if dim == 'overworld' else 512) if scope_kind == 'inside_border' else r['scope']['radius']
                radius = r['scope']['radius'] if scope_kind == 'near_base' else None
                r2 = radius ** 2 if radius is not None else None
                min_d2 = None
                for b_id in any_of:
                    b_data = summary['features'][b_id]
                    if b_data['counts'][scope_idx] > 0 and b_data['nearest_d2'] is not None:
                        d2 = b_data['nearest_d2']
                        if r2 is None or d2 <= r2:
                            if min_d2 is None or d2 < min_d2:
                                min_d2 = d2
                if min_d2 is None:
                    term = 1_000_000
                else:
                    term = min(math.isqrt(min_d2 * 10**12) // normalizer, 1_000_000)
                distance_tie += term

        # Utility scoring
        if preferred_rows:
            total_units = 0
            max_units = 0
            contributions = []
            for r in preferred_rows:
                w = r['importance']
                max_units += w * LCM
                scope_kind = r['scope']['kind']
                if r['kind'] == 'structure_count':
                    feat_id = r['feature']
                    dim = feature_by_id[feat_id]['dimension']
                    scope_idx = 3 if scope_kind == 'inside_border' else (
                        ow_radii_map[r['scope']['radius']] if dim == 'overworld' else nether_radii_map[r['scope']['radius']]
                    )
                    feat_data = summary['features'][feat_id]
                    count = feat_data['counts'][scope_idx]
                    comp = feat_data['complete'][scope_idx]
                    at_least = r['at_least']
                    frac_num = min(count, at_least)
                    units = w * (frac_num * LCM // at_least)
                    status = 'known' if comp else 'unknown'
                    contributions.append({
                        'feature': feat_id,
                        'rule': 'preferred',
                        'kind': 'structure_count',
                        'count': count,
                        'at_least': at_least,
                        'importance': w,
                        'utility_units': units,
                        'max_units': w * LCM,
                        'complete': comp,
                        'status': status,
                        'positive_witness': count > 0,
                    })
                    total_units += units
                elif r['kind'] == 'biome_witness':
                    any_of = r['any_of']
                    dim = feature_by_id[any_of[0]]['dimension']
                    scope_idx = 3 if scope_kind == 'inside_border' else (
                        ow_radii_map[r['scope']['radius']] if dim == 'overworld' else nether_radii_map[r['scope']['radius']]
                    )
                    witness_found = False
                    witness_b_id = None
                    for b_id in any_of:
                        b_data = summary['features'][b_id]
                        if b_data['counts'][scope_idx] > 0:
                            witness_found = True
                            witness_b_id = b_id
                            break
                    if witness_found:
                        units = w * LCM
                        status = 'known'
                    else:
                        units = 0
                        status = 'unknown'
                    contributions.append({
                        'any_of': any_of,
                        'rule': 'preferred',
                        'kind': 'biome_witness',
                        'witness_found': witness_found,
                        'witness_feature': witness_b_id,
                        'importance': w,
                        'utility_units': units,
                        'max_units': w * LCM,
                        'complete': False,
                        'status': status,
                        'positive_witness': witness_found,
                    })
                    total_units += units
            score = (total_units * 100.0) / max_units if max_units > 0 else 0.0
        else:
            profile_id = req['fallback_profile']
            legacy = summary.get('legacy', {})
            total_units, max_units, _ = scoring.profile_units(legacy, profile_id)
            score = float(total_units * 100 / max_units) if max_units > 0 else 0.0

            coefficients = PROFILES[profile_id]
            counts = [row[2] for row in legacy.get('counts', [])]
            known = [all(legacy.get('complete', [])[slot][2] for slot in group) for group in scoring.GROUPS] if 'complete' in legacy else [False] * len(scoring.GROUPS)
            n_biomes = sum(d != MISSING and d <= 1024**2 for d in legacy.get('biome_nearest_d2', []))
            units = [
                min(counts[0], 6) * (LCM // 6) if len(counts) > 0 else 0,
                min(counts[1], 4) * (LCM // 4) if len(counts) > 1 else 0,
                min(counts[2], 2) * (LCM // 2) if len(counts) > 2 else 0,
                min(counts[4] + counts[12], 6) * (LCM // 6) if len(counts) > 12 else 0,
                sum(n > 0 for n in counts) * (LCM // 14) if counts else 0,
                min(n_biomes, 8) * (LCM // 8),
                0,
                min(sum(counts[i] for i in (7, 8, 9, 10)), 4) * (LCM // 4) if len(counts) > 10 else 0,
            ]
            if counts and counts[0] and legacy.get('structure_nearest_d2', [MISSING])[0] != MISSING:
                with localcontext() as context:
                    context.prec = 50
                    units[6] = max(Decimal(0), 1 - Decimal(legacy['structure_nearest_d2'][0]).sqrt() / 1024) * LCM
            feature_units = [u if k else 0 for u, k in zip(units, known)]
            contributions = [
                {
                    'feature': k,
                    'coefficient': c,
                    'utility_units': float(u),
                    'max_units': LCM,
                    'status': 'known' if complete_flag else 'unknown',
                }
                for k, c, u, complete_flag in zip('VTAOEBHR', coefficients, feature_units, known)
            ]

        unsigned_seed = int(summary['seed']) & ((1 << 64) - 1)
        sort_key = (
            -total_units,
            distance_tie,
            unsigned_seed,
            summary['anchor'][0],
            summary['anchor'][1],
            summary['layout_id'],
        )

        # Build complete display data only for a new best anchor.  All required
        # and preferred tests and exact sort keys have already been evaluated.
        wid=summary['world_id']
        destination=best_pending_by_world if has_pending_required else best_matches_by_world
        if wid in destination and sort_key>=destination[wid]['_sort_key']:
            continue

        legacy = summary.get('legacy', {})
        feature_counts = {fid: fdata['counts'] for fid, fdata in summary.get('features', {}).items()}
        feature_complete = {fid: fdata['complete'] for fid, fdata in summary.get('features', {}).items()}
        nether_anchor = list(summary.get('nether_anchor', [summary['anchor'][0] // 8, summary['anchor'][1] // 8]))

        candidate = {
            'world_id': summary['world_id'],
            'seed': summary['seed'],
            'layout_id': summary['layout_id'],
            'anchor': list(summary['anchor']),
            'nether_anchor': nether_anchor,
            'border_side': summary['border_side'],
            'border': summary['border_side'],
            'bounds': list(bounds_for(summary['anchor'], summary['border_side'])),
            'score': score,
            'utility_units': int(total_units),
            'distance_tie': distance_tie,
            'contributions': contributions,
            'counts': legacy.get('counts'),
            'structure_nearest_d2': legacy.get('structure_nearest_d2'),
            'biome_nearest_d2': legacy.get('biome_nearest_d2'),
            'complete': legacy.get('complete'),
            'feature_counts': feature_counts,
            'feature_complete': feature_complete,
            '_sort_key': sort_key,
        }
        if 'biome_witness_refs' in legacy:
            candidate['biome_witness_refs'] = legacy['biome_witness_refs']

        wid = summary['world_id']
        if not has_pending_required:
            if wid not in best_matches_by_world or sort_key < best_matches_by_world[wid]['_sort_key']:
                best_matches_by_world[wid] = candidate
        else:
            candidate['status'] = 'pending'
            candidate['reason'] = '; '.join(pending_reasons)
            candidate['reasons'] = pending_reasons
            if wid not in best_pending_by_world or sort_key < best_pending_by_world[wid]['_sort_key']:
                best_pending_by_world[wid] = candidate

    matched_worlds = len(best_matches_by_world)
    ranked_matches = sorted(best_matches_by_world.values(), key=lambda c: c['_sort_key'])
    results = ranked_matches[:limit]

    unresolved_by_world = {
        wid: cand for wid, cand in best_pending_by_world.items()
        if wid not in best_matches_by_world
    }
    unresolved_candidates = sorted(unresolved_by_world.values(), key=lambda c: c['_sort_key'])[:limit]

    if not keep_keys:
        for r in results:
            r.pop('_sort_key', None)
        for u in unresolved_candidates:
            u.pop('_sort_key', None)

    return {
        'results': results,
        'unresolved_candidates': unresolved_candidates,
        'matched_worlds': matched_worlds,
        'unresolved_worlds': len(unresolved_by_world),
    }


def rank_v2(summaries, request, limit=1000, *, keep_keys=False):
    """Rank v2 catalog summaries against an additive catalog-query-v2 request."""
    if isinstance(request, str):
        req = load_request_v2(request)
    else:
        req = validate_request_v2(request)
    return _rank_features(summaries, req, limit, keep_keys=keep_keys, registry=REGISTRY_V2)


def rank_v3(summaries, request, limit=1000, *, keep_keys=False, registry=None):
    """Rank v3 catalog summaries against an additive catalog-query-v3 request."""
    from .registry import REGISTRY_V3
    from .request import validate_request_v3, load_request_v3
    active_registry = registry if registry is not None else REGISTRY_V3
    if isinstance(request, str):
        req = load_request_v3(request, registry=active_registry)
    else:
        req = validate_request_v3(request, registry=active_registry)
    return _rank_features(summaries, req, limit, keep_keys=keep_keys, registry=active_registry)


