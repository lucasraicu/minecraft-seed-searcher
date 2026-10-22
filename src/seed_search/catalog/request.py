"""Strict request vocabulary for the source-tree research reference CLI."""
import json
from .registry import REQUEST_SCHEMA, STRUCTURES, BIOMES, PROFILES, SIDES, RADII
from .geometry import integer


class UnsupportedFeatureError(ValueError):
    pass


class GatedFeatureError(UnsupportedFeatureError):
    pass



def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def load_request(text, **expected):
    return validate_request(json.loads(text, object_pairs_hook=_unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON'))), **expected)


def validate_request(payload, *, snapshot_id=None, game_build_id=None, world_settings_id=None):
    if not isinstance(payload, dict) or set(payload) != set(REQUEST_SCHEMA['required']):
        raise ValueError('Missing or unknown request field')
    for key in ('game_build_id', 'catalog_snapshot_id', 'world_settings_id'):
        if not isinstance(payload[key], str) or not 1 <= len(payload[key]) <= 256:
            raise ValueError('Invalid request identity')
    for key, value in (('edition', 'bedrock'), ('dimension', 'overworld'),
                       ('request_revision', 'catalog-query-v1'),
                       ('evidence_policy', 'predicted_observations_v1')):
        if payload[key] != value:
            raise UnsupportedFeatureError('Unsupported ' + key)
    if not payload['game_build_id'].startswith('research:'):
        raise UnsupportedFeatureError('Public game-build acceptance is not enabled')
    for key, value in (('catalog_snapshot_id', snapshot_id), ('game_build_id', game_build_id),
                       ('world_settings_id', world_settings_id)):
        if value is not None and payload[key] != value:
            raise ValueError('Request identity mismatch: ' + key)
    if payload['anchor_mode'] not in ('origin', 'recommended'):
        raise UnsupportedFeatureError('Anchor mode is gated or unsupported')
    if type(payload['border_side']) is not int or payload['border_side'] not in SIDES:
        raise UnsupportedFeatureError('Unsupported border size')
    if not isinstance(payload['fallback_profile'], str) or payload['fallback_profile'] not in PROFILES:
        raise UnsupportedFeatureError('Unknown fallback profile')
    if not isinstance(payload['rows'], list) or len(payload['rows']) > 12:
        raise ValueError('At most twelve rows')
    structure_ids = {f['id'] for f in STRUCTURES}
    biome_ids = {f['id'] for f in BIOMES}
    for row in payload['rows']:
        if not isinstance(row, dict) or row.get('rule') not in ('required', 'preferred'):
            raise ValueError('Invalid rule')
        keys = {'rule', 'kind', 'scope'}
        if row['rule'] == 'preferred':
            keys.add('importance')
            if type(row.get('importance')) is not int or row['importance'] not in (1, 3, 5):
                raise ValueError('Invalid importance')
        if row.get('kind') == 'structure_count':
            keys |= {'feature', 'at_least'}
            if not isinstance(row.get('feature'), str) or row['feature'] not in structure_ids:
                raise UnsupportedFeatureError('Unsupported structure')
            integer(row.get('at_least'), 1, 16)
        elif row.get('kind') == 'biome_witness':
            keys.add('any_of')
            alternatives = row.get('any_of')
            if not isinstance(alternatives, list) or not 1 <= len(alternatives) <= 9:
                raise ValueError('Invalid biome alternatives')
            if any(not isinstance(a, str) or a not in biome_ids for a in alternatives):
                raise UnsupportedFeatureError('Unsupported biome')
            if len(set(alternatives)) != len(alternatives):
                raise ValueError('Duplicate biome alternative')
        else:
            raise UnsupportedFeatureError('Unsupported condition kind')
        if set(row) != keys:
            raise ValueError('Missing or unknown row field')
        scope = row['scope']
        if not isinstance(scope, dict):
            raise ValueError('Invalid scope')
        if scope.get('kind') == 'near_base':
            if set(scope) != {'kind', 'radius'} or type(scope['radius']) is not int or scope['radius'] not in RADII:
                raise UnsupportedFeatureError('Unsupported radius')
        elif scope != {'kind': 'inside_border'}:
            raise UnsupportedFeatureError('Unsupported scope')
    # Defensive copy: caller mutation cannot change a validated query in flight.
    return json.loads(json.dumps(payload, allow_nan=False))


def load_request_v2(text, **expected):
    return validate_request_v2(json.loads(text, object_pairs_hook=_unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON'))), **expected)


def validate_request_v2(payload, *, snapshot_id=None, game_build_id=None, world_settings_id=None):
    if not isinstance(payload, dict) or set(payload) != set(REQUEST_SCHEMA['required']):
        raise ValueError('Missing or unknown request field')
    for key in ('game_build_id', 'catalog_snapshot_id', 'world_settings_id'):
        if not isinstance(payload[key], str) or not 1 <= len(payload[key]) <= 256:
            raise ValueError('Invalid request identity')
    for key, value in (('edition', 'bedrock'), ('dimension', 'overworld'),
                       ('request_revision', 'catalog-query-v2'),
                       ('evidence_policy', 'predicted_observations_v2')):
        if payload[key] != value:
            raise UnsupportedFeatureError('Unsupported ' + key)
    if not payload['game_build_id'].startswith('research:'):
        raise UnsupportedFeatureError('Public game-build acceptance is not enabled')
    for key, value in (('catalog_snapshot_id', snapshot_id), ('game_build_id', game_build_id),
                       ('world_settings_id', world_settings_id)):
        if value is not None and payload[key] != value:
            raise ValueError('Request identity mismatch: ' + key)
    if payload['anchor_mode'] not in ('origin', 'recommended', 'world_spawn_estimated', 'world_spawn_observed'):
        raise UnsupportedFeatureError('Anchor mode is gated or unsupported')
    if type(payload['border_side']) is not int or payload['border_side'] not in SIDES:
        raise UnsupportedFeatureError('Unsupported border size')
    if not isinstance(payload['fallback_profile'], str) or payload['fallback_profile'] not in PROFILES:
        raise UnsupportedFeatureError('Unknown fallback profile')
    if not isinstance(payload['rows'], list) or len(payload['rows']) > 12:
        raise ValueError('At most twelve rows')

    from .registry import FEATURES_V2, FEATURE_BY_ID_V2, REGISTRY_V2
    structure_ids = {f['id'] for f in FEATURES_V2 if f['kind'] == 'structure_count'}
    biome_ids = {f['id'] for f in FEATURES_V2 if f['kind'] == 'biome_witness'}
    ow_radii = tuple(REGISTRY_V2['overworld_radii'])
    nether_radii = tuple(REGISTRY_V2['nether_radii'])

    for row in payload['rows']:
        if not isinstance(row, dict) or row.get('rule') not in ('required', 'preferred'):
            raise ValueError('Invalid rule')
        keys = {'rule', 'kind', 'scope'}
        if row['rule'] == 'preferred':
            keys.add('importance')
            if type(row.get('importance')) is not int or row['importance'] not in (1, 3, 5):
                raise ValueError('Invalid importance')
        if row.get('kind') == 'structure_count':
            keys |= {'feature', 'at_least'}
            feature = row.get('feature')
            if not isinstance(feature, str) or feature not in structure_ids:
                raise UnsupportedFeatureError('Unsupported structure')
            at_least = row.get('at_least')
            if type(at_least) is not int:
                raise ValueError('Invalid at_least')
            integer(at_least, 1, 16)
            dim = FEATURE_BY_ID_V2[feature]['dimension']
        elif row.get('kind') == 'biome_witness':
            keys.add('any_of')
            alternatives = row.get('any_of')
            if not isinstance(alternatives, list) or len(alternatives) == 0:
                raise ValueError('Invalid biome alternatives')
            if any(not isinstance(a, str) or a not in biome_ids for a in alternatives):
                raise UnsupportedFeatureError('Unsupported biome')
            if len(set(alternatives)) != len(alternatives):
                raise ValueError('Duplicate biome alternative')
            dims = {FEATURE_BY_ID_V2[a]['dimension'] for a in alternatives}
            if len(dims) != 1:
                raise UnsupportedFeatureError('Mixed biome dimensions')
            dim = next(iter(dims))
            if dim == 'overworld' and not (1 <= len(alternatives) <= 9):
                raise ValueError('Invalid biome alternatives')
            if dim == 'nether' and not (1 <= len(alternatives) <= 5):
                raise ValueError('Invalid biome alternatives')
        else:
            raise UnsupportedFeatureError('Unsupported condition kind')

        if set(row) != keys:
            raise ValueError('Missing or unknown row field')
        scope = row['scope']
        if not isinstance(scope, dict):
            raise ValueError('Invalid scope')
        if scope.get('kind') == 'near_base':
            if set(scope) != {'kind', 'radius'}:
                raise ValueError('Invalid scope')
            radius = scope.get('radius')
            if type(radius) is not int:
                raise UnsupportedFeatureError('Unsupported radius')
            valid_radii = ow_radii if dim == 'overworld' else nether_radii
            if radius not in valid_radii:
                raise UnsupportedFeatureError('Unsupported radius')
        elif scope == {'kind': 'inside_border'}:
            pass
        else:
            raise UnsupportedFeatureError('Unsupported scope')

    # Defensive copy: caller mutation cannot change a validated query in flight.
    return json.loads(json.dumps(payload, allow_nan=False))


def load_request_v3(text, *, registry=None, **expected):
    return validate_request_v3(
        json.loads(text, object_pairs_hook=_unique,
                   parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON'))),
        registry=registry,
        **expected
    )


def validate_request_v3(payload, *, registry=None, snapshot_id=None, game_build_id=None, world_settings_id=None):
    if not isinstance(payload, dict) or set(payload) != set(REQUEST_SCHEMA['required']):
        raise ValueError('Missing or unknown request field')
    for key in ('game_build_id', 'catalog_snapshot_id', 'world_settings_id'):
        if not isinstance(payload[key], str) or not 1 <= len(payload[key]) <= 256:
            raise ValueError('Invalid request identity')
    for key, value in (('edition', 'bedrock'), ('dimension', 'overworld'),
                       ('request_revision', 'catalog-query-v3'),
                       ('evidence_policy', 'predicted_observations_v3')):
        if payload[key] != value:
            raise UnsupportedFeatureError('Unsupported ' + key)
    if not payload['game_build_id'].startswith('research:'):
        raise UnsupportedFeatureError('Public game-build acceptance is not enabled')
    for key, value in (('catalog_snapshot_id', snapshot_id), ('game_build_id', game_build_id),
                       ('world_settings_id', world_settings_id)):
        if value is not None and payload[key] != value:
            raise ValueError('Request identity mismatch: ' + key)
    if payload['anchor_mode'] not in ('origin', 'recommended', 'world_spawn_estimated', 'world_spawn_observed'):
        raise UnsupportedFeatureError('Anchor mode is gated or unsupported')
    if type(payload['border_side']) is not int or payload['border_side'] not in SIDES:
        raise UnsupportedFeatureError('Unsupported border size')
    if not isinstance(payload['fallback_profile'], str) or payload['fallback_profile'] not in PROFILES:
        raise UnsupportedFeatureError('Unknown fallback profile')
    if not isinstance(payload['rows'], list) or len(payload['rows']) > 12:
        raise ValueError('At most twelve rows')

    from .registry import REGISTRY_V3
    active_registry = registry if registry is not None else REGISTRY_V3
    feature_by_id = {f['id']: f for f in active_registry['features']}
    structure_ids = {f['id']: f for f in active_registry['features'] if f['kind'] == 'structure_count'}
    biome_ids = {f['id']: f for f in active_registry['features'] if f['kind'] == 'biome_witness'}
    ow_radii = tuple(active_registry.get('overworld_radii', (256, 512, 1024)))
    nether_radii = tuple(active_registry.get('nether_radii', (64, 128, 256)))

    for row in payload['rows']:
        if not isinstance(row, dict) or row.get('rule') not in ('required', 'preferred'):
            raise ValueError('Invalid rule')
        keys = {'rule', 'kind', 'scope'}
        if row['rule'] == 'preferred':
            keys.add('importance')
            if type(row.get('importance')) is not int or row['importance'] not in (1, 3, 5):
                raise ValueError('Invalid importance')
        if row.get('kind') == 'structure_count':
            keys |= {'feature', 'at_least'}
            feature = row.get('feature')
            if not isinstance(feature, str) or feature not in structure_ids:
                raise UnsupportedFeatureError('Unsupported structure')
            fdef = feature_by_id[feature]
            if fdef.get('available') is False:
                raise GatedFeatureError(f"Gated structure feature: {feature} ({fdef.get('unavailable_reason')})")
            at_least = row.get('at_least')
            if type(at_least) is not int:
                raise ValueError('Invalid at_least')
            integer(at_least, 1, 16)
            dim = fdef['dimension']
        elif row.get('kind') == 'biome_witness':
            keys.add('any_of')
            alternatives = row.get('any_of')
            if not isinstance(alternatives, list) or not (1 <= len(alternatives) <= 16):
                raise ValueError('Invalid biome alternatives (must be 1..16)')
            for a in alternatives:
                if not isinstance(a, str) or a not in biome_ids:
                    raise UnsupportedFeatureError('Unsupported biome: ' + str(a))
                fdef = feature_by_id[a]
                if fdef.get('available') is False:
                    raise GatedFeatureError(f"Gated biome feature: {a} ({fdef.get('unavailable_reason')})")
            if len(set(alternatives)) != len(alternatives):
                raise ValueError('Duplicate biome alternative')
            dims = {feature_by_id[a]['dimension'] for a in alternatives}
            if len(dims) != 1:
                raise UnsupportedFeatureError('Mixed biome dimensions')
            dim = next(iter(dims))
        else:
            raise UnsupportedFeatureError('Unsupported condition kind')

        if set(row) != keys:
            raise ValueError('Missing or unknown row field')
        scope = row['scope']
        if not isinstance(scope, dict):
            raise ValueError('Invalid scope')
        if scope.get('kind') == 'near_base':
            if set(scope) != {'kind', 'radius'}:
                raise ValueError('Invalid scope')
            radius = scope.get('radius')
            if type(radius) is not int:
                raise UnsupportedFeatureError('Unsupported radius')
            valid_radii = ow_radii if dim == 'overworld' else nether_radii
            if radius not in valid_radii:
                raise UnsupportedFeatureError('Unsupported radius')
        elif scope == {'kind': 'inside_border'}:
            pass
        else:
            raise UnsupportedFeatureError('Unsupported scope')

    return json.loads(json.dumps(payload, allow_nan=False))


