"""Explicit actual surface-family checks; point samples never prove absence."""
from .biomes import classify
from ..seeds import parse_seed


def verify_surface_families(candidate, cfg, adapter, points, *, retry_failed=False):
    """Check positive family presence inside the configured candidate square."""
    sx, sz = candidate.get('evaluation_center',candidate['stronghold'])
    half = cfg['deployment']['overworld_side_blocks']//2
    points = list(points)
    if not 1 <= len(points) <= 16:
        raise ValueError('Surface verification requires 1..16 explicit points')
    for point in points:
        if (not isinstance(point, (list, tuple)) or len(point) != 2 or
                any(isinstance(v, bool) or not isinstance(v, int) for v in point)):
            raise ValueError('Surface points must be integer [x,z] pairs')
        x, z = point
        if not (sx-half <= x < sx+half and sz-half <= z < sz+half):
            raise ValueError('Surface points must lie within the candidate Realm bounds')
    result = adapter.verify_surface_points(candidate['seed'], points,
                                          candidate_id=candidate['id'], retry_failed=retry_failed)
    requested = {tuple(point) for point in points}
    trusted = (result.get('source') == 'actual' and result.get('actual') is True and
               result.get('operation') == 'surface_points_v1' and
               result.get('seed') == str(parse_seed(candidate['seed'])) and
               result.get('requested_points') == [list(point) for point in sorted(requested)] and
               isinstance(result.get('id'), str) and bool(result['id']) and
               result.get('identity') == adapter.cache_identity() and
               result.get('status') == 'PARTIAL' and
               result.get('existence_only') is True and result.get('absence_verified') is False)
    valid = {}; conflicts = set()
    for row in result.get('surface_biome_observations', []):
        if not isinstance(row, dict):
            continue
        key = (row.get('x'), row.get('z'))
        if (any(isinstance(v, bool) or not isinstance(v, int) for v in key) or
                key not in requested or row.get('status') != 'OBSERVED' or
                not isinstance(row.get('name'), str) or not row['name'].strip()):
            continue
        if key in valid and valid[key] != row['name']:
            conflicts.add(key)
        valid[key] = row['name']
    names = [name for point, name in valid.items() if point not in conflicts] if trusted else []
    classification = classify(names, cfg['biomes'], verified=trusted, complete=False)
    return {'observation_id': result.get('id'), 'observation': result,
            'classification': classification,
            'wooded_requirement': classification['qualification'],
            'status': 'PARTIAL', 'existence_only': True, 'absence_verified': False,
            'conflicting_coordinates': [list(point) for point in sorted(conflicts)],
            'realm_bounds': [sx-half, sz-half, sx+half, sz+half],
            'baseline_eligibility': 'UNCHANGED; generated structure evidence remains required',
            'score_interpretation': 'Observed surface bonus lower bound; unsampled bonuses remain possible. Prediction scores are preserved.'}


def save_surface_verification(store, candidate_id, result):
    """Publish under the current scoring revision after slow generation ends."""
    from .reports import _rescore_lock, ensure_score_revision_complete
    with _rescore_lock(store):
        ensure_score_revision_complete(store)
        policy=store.get_state('score_policy') or store.identity['config']
        detected=result['classification']
        result['classification']=classify(detected['raw_names'],policy['biomes'],complete=False,
                                           verified=detected.get('uncertainty',{}).get('domain')=='actual_generated_surface')
        result['wooded_requirement']=result['classification']['qualification']
        revision=store.get_state('rescore_revision')
        if revision:result['score_revision']=revision['id']
        return store.upsert_candidate({'id':candidate_id,'surface_biome_verification':result})
