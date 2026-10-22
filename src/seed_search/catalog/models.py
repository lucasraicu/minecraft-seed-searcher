"""Frozen JSON records shared by reference extractor, storage and query adapters.

Observation: revision, identity, bounds, structures, biomes, biome_names, coverage,
metrics, errors. Structures map feature ID to distinct [x,z] starts. Biomes are
[x,y,z,raw_id] records. Names map raw ID strings to canonical names. Coverage maps
feature ID to {status,bounds,method_id}; a completed biome plane covers all nine
family features. Missing features are UNKNOWN, never completed zero counts.
"""
from .registry import FEATURE_IDS, STRUCTURES, ENVELOPE, REGISTRY_REVISION, digest
from .geometry import integer, inside
from ..seeds import parse_seed

REVISION = 'catalog-observation-v1'
GEOMETRY_REVISION = 'half_open_square_and_closed_circle_intersection_v1'
EXTRACTOR_REVISION = 'cpu-catalog-reference-v1'
SUMMARY_REVISION = 'catalog-summary-v1'
IDENTITY_FIELDS = ('edition', 'game_build_id', 'world_settings_id', 'seed', 'model_id',
                   'native_sha256', 'source_sha256', 'registry_revision', 'extractor_revision')
STATES = ('unknown', 'partial', 'complete', 'failed')


def identity(seed, *, model_id, native_sha256, source_sha256,
             world_settings_id='default', game_build_id=None):
    """Research identity; no accepted public game-build compatibility mapping yet."""
    if game_build_id is not None and game_build_id != 'research:' + model_id:
        raise ValueError('Public game-build acceptance is not enabled')
    return dict(edition='bedrock', game_build_id='research:' + model_id,
                world_settings_id=world_settings_id, seed=str(parse_seed(seed)), model_id=model_id,
                native_sha256=native_sha256, source_sha256=source_sha256,
                registry_revision=REGISTRY_REVISION, extractor_revision=EXTRACTOR_REVISION)


def validate_identity(value):
    if not isinstance(value, dict) or set(value) != set(IDENTITY_FIELDS):
        raise ValueError('Invalid observation identity')
    if any(not isinstance(v, str) or not v or len(v) > 256 for v in value.values()):
        raise ValueError('Identity values must be bounded strings')
    if value['seed'] != str(parse_seed(value['seed'])) or value['edition'] != 'bedrock':
        raise ValueError('Invalid canonical seed/edition')
    if value['registry_revision'] != REGISTRY_REVISION or value['extractor_revision'] != EXTRACTOR_REVISION:
        raise ValueError('Incompatible registry/extractor')
    if value['game_build_id'] != 'research:' + value['model_id']:
        raise ValueError('Only explicitly labeled research identities are supported')
    for field in ('source_sha256', 'native_sha256'):
        if len(value[field]) != 64 or any(c not in '0123456789abcdef' for c in value[field]):
            raise ValueError('Invalid build digest')
    return value


def world_id(value):
    validate_identity(value)
    return digest({k: value[k] for k in ('edition', 'game_build_id', 'world_settings_id', 'seed')})


def observation_id(observation):
    return digest(observation)


def validate_observation(obs):
    required = {'revision', 'identity', 'bounds', 'structures', 'biomes', 'biome_names', 'coverage', 'metrics', 'errors'}
    if not isinstance(obs, dict) or set(obs) != required or obs['revision'] != REVISION:
        raise ValueError('Invalid observation schema')
    validate_identity(obs['identity'])
    if obs['bounds'] != list(ENVELOPE):
        raise ValueError('Unsupported observation envelope')
    for key in ('structures', 'biome_names', 'coverage', 'metrics', 'errors'):
        if not isinstance(obs[key], dict):
            raise ValueError('Expected observation mapping')
    structure_ids = {f['id'] for f in STRUCTURES}
    if not set(obs['structures']) <= structure_ids or not set(obs['coverage']) <= set(FEATURE_IDS):
        raise ValueError('Unknown feature')
    for key, points in obs['structures'].items():
        if not isinstance(points, list) or len(points) > 200000:
            raise ValueError('Structure inventory too large')
        seen = set()
        for p in points:
            if not isinstance(p, list) or len(p) != 2:
                raise ValueError('Invalid structure start')
            x, z = (integer(n) for n in p)
            if not inside(x, z, ENVELOPE) or (x, z) in seen:
                raise ValueError('Out-of-bounds or duplicate start')
            seen.add((x, z))
    if not isinstance(obs['biomes'], list) or len(obs['biomes']) > 25600:
        raise ValueError('Invalid biome inventory')
    positions = set()
    for point in obs['biomes']:
        if not isinstance(point, list) or len(point) != 4:
            raise ValueError('Invalid biome sample')
        x, y, z, bid = point
        integer(x); integer(y); integer(z); integer(bid, 0, 65535)
        if y != 63 or x % 64 or z % 64 or not inside(x, z, ENVELOPE) or (x, z) in positions:
            raise ValueError('Invalid/duplicate lattice sample')
        positions.add((x, z))
    for bid, name in obs['biome_names'].items():
        if not isinstance(bid, str) or not bid.isascii() or not bid.isdigit() or str(int(bid)) != bid:
            raise ValueError('Invalid biome name key')
        integer(int(bid), 0, 65535)
        if not isinstance(name, str) or not name or len(name) > 128:
            raise ValueError('Invalid biome name')
    for feature, coverage in obs['coverage'].items():
        if not isinstance(coverage, dict) or set(coverage) != {'status', 'bounds', 'method_id'}:
            raise ValueError('Invalid coverage schema')
        if coverage['status'] not in STATES or coverage['bounds'] != list(ENVELOPE):
            raise ValueError('Invalid coverage state/bounds')
        if not isinstance(coverage['method_id'], str) or not coverage['method_id']:
            raise ValueError('Missing coverage method')
        if coverage['status'] == 'complete' and feature in structure_ids and feature not in obs['structures']:
            raise ValueError('Complete inventory missing')
        if coverage['status'] == 'complete' and feature.startswith('biome.') and len(positions) != 25600:
            raise ValueError('Complete plane missing samples')
        if coverage['status'] == 'complete' and feature.startswith('biome.'):
            ids = {str(point[3]) for point in obs['biomes']}
            if any(bid not in obs['biome_names'] or obs['biome_names'][bid].startswith('unknown_') for bid in ids):
                raise ValueError('Complete family mapping is missing or unknown')
    # Also reject nonfinite numbers and non-JSON payloads in metrics/errors.
    if isinstance(obs.get('realm'),dict) and 'inventory' in obs['realm']:
        from .realm_observations import validate_realm_inventory
        validate_realm_inventory(obs)
    digest(obs)
    return obs


def empty_observation(value):
    validate_identity(value)
    return dict(revision=REVISION, identity=dict(value), bounds=list(ENVELOPE),
                structures={}, biomes=[], biome_names={}, coverage={}, metrics={}, errors={})


def empty_observation_v2(value):
    from .registry import REGISTRY_REVISION_V2
    validate_identity(value)
    return dict(revision='catalog-observation-v2',registry_revision=REGISTRY_REVISION_V2,
        identity=dict(value),bounds=dict(overworld=list(ENVELOPE),nether=[-640,-640,640,640]),
        structures={},biomes=dict(overworld=[],nether=[]),biome_names={},coverage={},
        anchors=[],realm=None,metrics={},errors={})


def validate_observation_v2(obs):
    """Additive typed observations; partial features never become completed zeros."""
    from .registry import FEATURE_BY_ID_V2,REGISTRY_REVISION_V2
    from .geometry import contains
    fields={'revision','registry_revision','identity','bounds','structures','biomes',
            'biome_names','coverage','anchors','realm','metrics','errors'}
    if not isinstance(obs,dict) or set(obs)!=fields or obs['revision']!='catalog-observation-v2':
        raise ValueError('Invalid v2 observation schema')
    if obs['registry_revision']!=REGISTRY_REVISION_V2:raise ValueError('V2 registry differs')
    validate_identity(obs['identity'])
    for key in ('bounds','structures','biomes','biome_names','coverage','metrics','errors'):
        if not isinstance(obs[key],dict):raise ValueError('Expected v2 mapping')
    if set(obs['bounds'])!={'overworld','nether'} or set(obs['biomes'])!={'overworld','nether'}:
        raise ValueError('Expected both dimension namespaces')
    def box(value):
        if not isinstance(value,list) or len(value)!=4:raise ValueError('Invalid bounds')
        for n in value:integer(n,-30_000_000,30_000_001)
        if value[0]>=value[2] or value[1]>=value[3]:raise ValueError('Empty bounds')
        return value
    for b in obs['bounds'].values():box(b)
    for fid,points in obs['structures'].items():
        f=FEATURE_BY_ID_V2.get(fid)
        if not f or f['kind']!='structure_count':raise ValueError('Unknown v2 structure')
        if not isinstance(points,list) or len(points)>200000:raise ValueError('Structure cap')
        seen=set()
        for pt in points:
            if not isinstance(pt,list) or len(pt)!=2:raise ValueError('Invalid v2 start')
            x,z=[integer(v,-30_000_000,30_000_000) for v in pt]
            if not inside(x,z,obs['bounds'][f['dimension']]) or (x,z) in seen:raise ValueError('Duplicate/outside start')
            seen.add((x,z))
    for bid,name in obs['biome_names'].items():
        if not isinstance(bid,str) or not bid.isascii() or not bid.isdecimal() or str(int(bid))!=bid:
            raise ValueError('Invalid raw ID')
        integer(int(bid),0,65535)
        if not isinstance(name,str) or not name or len(name)>128:raise ValueError('Invalid biome name')
    sampled_ids={};sampled_positions={}
    for dimension,points in obs['biomes'].items():
        if not isinstance(points,list) or len(points)>200000:raise ValueError('Biome point cap')
        seen=set();sampled_ids[dimension]=set()
        for pt in points:
            if not isinstance(pt,list) or len(pt)!=4:raise ValueError('Invalid biome point')
            x,y,z,bid=pt
            integer(x,-30_000_000,30_000_000);integer(z,-30_000_000,30_000_000)
            integer(y,*((-64,319) if dimension=='overworld' else (0,127)));integer(bid,0,65535)
            if not inside(x,z,obs['bounds'][dimension]) or (x,y,z) in seen:raise ValueError('Duplicate/outside biome point')
            seen.add((x,y,z));sampled_ids[dimension].add(str(bid))
        sampled_positions[dimension]=seen
    for fid,cov in obs['coverage'].items():
        f=FEATURE_BY_ID_V2.get(fid)
        if not f or not isinstance(cov,dict) or set(cov)!={'status','bounds','method_id'}:raise ValueError('Invalid v2 coverage')
        if cov['status'] not in STATES or not contains(obs['bounds'][f['dimension']],box(cov['bounds'])):
            raise ValueError('Invalid coverage bounds/state')
        if not isinstance(cov['method_id'],str) or not 1<=len(cov['method_id'])<=256:raise ValueError('Missing method')
        if cov['status']=='complete':
            if f['kind']=='structure_count' and fid not in obs['structures']:raise ValueError('Complete inventory missing')
            if f['kind']=='biome_witness':
                dimension=f['dimension'];y=63 if dimension=='overworld' else 64
                method=f'predictor_world_lattice_y{y}_stride64_v2'
                # The legacy method remains readable for migrated observations.
                if cov['method_id'] not in (method,'predictor_world_lattice_y63_stride64_v1'):
                    raise ValueError('Unknown completed biome survey method')
                b=cov['bounds'];points=sampled_positions[dimension]
                expected=((x,y,z) for z in range(-(-b[1]//64)*64,b[3],64)
                          for x in range(-(-b[0]//64)*64,b[2],64))
                if any(p not in points for p in expected):raise ValueError('Completed biome lattice missing samples')
            if f['kind']=='biome_witness' and any(i not in obs['biome_names'] or obs['biome_names'][i].startswith('unknown') for i in sampled_ids[f['dimension']]):
                raise ValueError('Complete mapping missing')
    if not isinstance(obs['anchors'],list) or len(obs['anchors'])>100:raise ValueError('Invalid anchors')
    seen=set()
    for a in obs['anchors']:
        if not isinstance(a,dict) or set(a)!={'mode','coordinate','source_id'}:raise ValueError('Invalid anchor schema')
        if a['mode'] not in ('origin','recommended','world_spawn_estimated','world_spawn_observed'):raise ValueError('Unknown anchor mode')
        if not isinstance(a['coordinate'],list) or len(a['coordinate'])!=2:raise ValueError('Invalid anchor coordinate')
        for n in a['coordinate']:integer(n,-30_000_000,30_000_000)
        source=a['source_id']
        if not isinstance(source,str) or len(source)!=64 or any(c not in '0123456789abcdef' for c in source):raise ValueError('Invalid anchor source')
        key=(a['mode'],tuple(a['coordinate']))
        if key in seen:raise ValueError('Duplicate anchor')
        seen.add(key)
    for mode in ('world_spawn_estimated','world_spawn_observed'):
        if sum(a['mode']==mode for a in obs['anchors'])>1:raise ValueError('Ambiguous spawn')
    if obs['realm'] is not None and not isinstance(obs['realm'],dict):raise ValueError('Invalid Realm evidence')
    if isinstance(obs.get('realm'),dict) and 'inventory' in obs['realm']:
        from .realm_observations import validate_realm_inventory
        validate_realm_inventory(obs)
    digest(obs)
    return obs
