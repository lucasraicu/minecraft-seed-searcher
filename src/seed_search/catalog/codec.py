"""Versioned 364-byte derived feature payload, not a custom durable engine."""
import struct
from .geometry import integer, bounds_for, anchors
from .registry import digest, FEATURE_IDS, SIDES
from .models import SUMMARY_REVISION

MISSING = (1 << 32)-1
_NUMERIC = struct.Struct('<88I')


def layout_id(observation_id, anchor, side):
    return digest([SUMMARY_REVISION, observation_id, list(anchor), side])


def validate_summary(summary):
    expected = {'revision', 'observation_id', 'world_id', 'layout_id', 'seed', 'anchor',
                'border_side', 'counts', 'structure_nearest_d2', 'biome_nearest_d2',
                'biome_witness_refs', 'complete'}
    if not isinstance(summary, dict) or set(summary) != expected or summary['revision'] != SUMMARY_REVISION:
        raise ValueError('Invalid summary schema')
    from ..seeds import parse_seed
    if not isinstance(summary['seed'], str) or summary['seed'] != str(parse_seed(summary['seed'])):
        raise ValueError('Invalid summary seed')
    if not isinstance(summary['anchor'], list) or tuple(summary['anchor']) not in anchors():
        raise ValueError('Unsupported anchor')
    bounds_for(summary['anchor'], summary['border_side'])
    for field in ('observation_id', 'world_id', 'layout_id'):
        v = summary[field]
        if not isinstance(v, str) or len(v) != 64 or any(c not in '0123456789abcdef' for c in v):
            raise ValueError('Invalid summary identity')
    if summary['layout_id'] != layout_id(summary['observation_id'], summary['anchor'], summary['border_side']):
        raise ValueError('Layout identity mismatch')
    validate_summary_numbers(summary)
    return summary


def validate_summary_numbers(summary):
    """Validate numeric payload only, independent of versioned anchor geometry."""
    if not isinstance(summary['counts'], list) or len(summary['counts']) != 14:
        raise ValueError('Invalid count matrix')
    for row in summary['counts']:
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError('Invalid count scopes')
        for v in row:
            integer(v, 0, MISSING)
        if row != sorted(row):
            raise ValueError('Counts must increase with nested scopes')
    for field, n in (('structure_nearest_d2', 14), ('biome_nearest_d2', 9), ('biome_witness_refs', 9)):
        values = summary[field]
        if not isinstance(values, list) or len(values) != n:
            raise ValueError('Invalid distance/witness vector')
        for v in values:
            integer(v, 0, MISSING)
    if not isinstance(summary['complete'], list) or len(summary['complete']) != len(FEATURE_IDS):
        raise ValueError('Invalid completion matrix')
    for row in summary['complete']:
        if not isinstance(row, list) or len(row) != 4 or any(type(v) is not bool for v in row):
            raise ValueError('Invalid completion flags')
    return summary


def pack_summary(summary):
    validate_summary(summary)
    nums = [v for row in summary['counts'] for v in row]
    for key in ('structure_nearest_d2', 'biome_nearest_d2', 'biome_witness_refs'):
        nums.extend(summary[key])
    bits = sum(int(v) << i for i, v in enumerate(v for row in summary['complete'] for v in row))
    return _NUMERIC.pack(*nums) + bits.to_bytes(12, 'little')


def summary_metadata(summary):
    validate_summary(summary)
    return {k: summary[k] for k in ('revision', 'observation_id', 'world_id', 'layout_id', 'seed', 'anchor', 'border_side')}


def unpack_summary(payload, metadata):
    if not isinstance(payload, bytes) or len(payload) != 364 or payload[-1] & 0xf0:
        raise ValueError('Invalid summary payload size/reserved bits')
    values = _NUMERIC.unpack(payload[:352])
    bits = int.from_bytes(payload[352:], 'little')
    result = dict(metadata, counts=[list(values[i:i+4]) for i in range(0, 56, 4)],
                  structure_nearest_d2=list(values[56:70]), biome_nearest_d2=list(values[70:79]),
                  biome_witness_refs=list(values[79:88]),
                  complete=[[bool(bits & (1 << (f*4+s))) for s in range(4)] for f in range(23)])
    return validate_summary(result)


def validate_summary_v2(value):
    """Validate the additive typed summary before artifact publication/querying."""
    from .registry import FEATURE_BY_ID_V2, REGISTRY_REVISION_V2, digest
    from .anchors import validate_anchor_summary
    from ..seeds import parse_seed
    fields={'revision','registry_revision','source_observation_id','world_id','seed',
            'anchor','nether_anchor','anchor_modes','border_side','layout_id','features','legacy'}
    if not isinstance(value,dict) or set(value)!=fields or value['revision']!='catalog-summary-v2':
        raise ValueError('Invalid v2 summary schema')
    if value['registry_revision']!=REGISTRY_REVISION_V2:raise ValueError('V2 registry mismatch')
    for key in ('source_observation_id','world_id','layout_id'):
        sha=value[key]
        if not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('Invalid summary digest')
    if not isinstance(value['seed'],str) or str(parse_seed(value['seed']))!=value['seed']:
        raise ValueError('Invalid canonical seed')
    for key in ('anchor','nether_anchor'):
        if not isinstance(value[key],list) or len(value[key])!=2:raise ValueError('Invalid anchor')
        for n in value[key]:integer(n,-30_000_000,30_000_000)
    if value['nether_anchor']!=[n//8 for n in value['anchor']]:raise ValueError('Nether projection mismatch')
    modes=value['anchor_modes']
    if not isinstance(modes,list) or not modes or len(set(modes))!=len(modes) or any(
        m not in ('origin','recommended','world_spawn_estimated','world_spawn_observed') for m in modes):
        raise ValueError('Invalid anchor modes')
    if 'origin' in modes and value['anchor']!=[0,0]:raise ValueError('Origin must be zero')
    if type(value['border_side']) is not int or value['border_side'] not in (2048,4096,8192):
        raise ValueError('Unsupported border')
    if value['layout_id']!=digest(['catalog-summary-v2',value['source_observation_id'],value['anchor'],modes,value['border_side']]):
        raise ValueError('V2 layout identity mismatch')
    features=value['features']
    if not isinstance(features,dict) or set(features)!=set(FEATURE_BY_ID_V2):raise ValueError('Feature registry differs')
    for fid,row in features.items():
        definition=FEATURE_BY_ID_V2[fid];biome=definition['kind']=='biome_witness'
        if not isinstance(row,dict) or set(row)!={'dimension','counts','complete','nearest_d2','witness'} or row['dimension']!=definition['dimension']:
            raise ValueError('Invalid typed feature')
        counts=row['counts'];complete=row['complete']
        if not isinstance(counts,list) or len(counts)!=4:raise ValueError('Invalid counts')
        for n in counts:integer(n,0,1 if biome else 200000)
        if counts!=sorted(counts):raise ValueError('Counts not nested')
        if not isinstance(complete,list) or len(complete)!=4 or any(type(n) is not bool for n in complete):
            raise ValueError('Invalid completion vector')
        if biome and any(complete):raise ValueError('Sampled presence cannot prove absence')
        distance=row['nearest_d2'];witness=row['witness']
        if (distance is None)!=(witness is None) or (distance is None)!=(counts[3]==0):
            raise ValueError('Witness/count/distance mismatch')
        if distance is not None:
            integer(distance,0,2*(60_000_000**2))
            if not isinstance(witness,list) or len(witness)!=3:raise ValueError('Invalid witness')
            x,y,z=witness;integer(x,-30_000_000,30_000_000);integer(z,-30_000_000,30_000_000)
            center=value['anchor'] if row['dimension']=='overworld' else value['nether_anchor']
            half=value['border_side']//2 if row['dimension']=='overworld' else 512
            if not center[0]-half<=x<center[0]+half or not center[1]-half<=z<center[1]+half:
                raise ValueError('Witness outside selected border')
            if distance!=(x-center[0])**2+(z-center[1])**2:raise ValueError('Witness distance mismatch')
            radii=(256,512,1024) if row['dimension']=='overworld' else (64,128,256)
            if any((counts[i]>0)!=(distance<=radius**2) for i,radius in enumerate(radii)):
                raise ValueError('Nearest witness contradicts radius counts')
            if biome:
                if y!=(63 if row['dimension']=='overworld' else 64):raise ValueError('Wrong query biome height')
            elif y is not None:raise ValueError('Structure start has no verified height')
    legacy=value['legacy']
    (validate_summary if legacy.get('revision')==SUMMARY_REVISION else validate_anchor_summary)(legacy)
    for key in ('world_id','seed','anchor','border_side'):
        if legacy[key]!=value[key]:raise ValueError('Legacy summary binding mismatch')
    return value


def validate_summary_v3(value, *, registry=None):
    """Validate additive v3 typed summary before artifact publication/querying."""
    from .registry import (
        FEATURE_BY_ID_V3, REGISTRY_REVISION_V3, REGISTRY_V3,
        SAMPLING_PROFILE_REVISION_V3, digest
    )
    from .anchors import validate_anchor_summary
    from ..seeds import parse_seed

    fields = {
        'revision', 'registry_revision', 'source_observation_id',
        'source_extension_id', 'sampling_profile_revision',
        'world_id', 'seed', 'anchor', 'nether_anchor', 'anchor_modes',
        'border_side', 'layout_id', 'features', 'legacy'
    }
    if not isinstance(value, dict) or set(value) != fields or value['revision'] != 'catalog-summary-v3':
        raise ValueError('Invalid v3 summary schema')

    active_registry = registry if registry is not None else REGISTRY_V3
    active_features_by_id = {f['id']: f for f in active_registry['features']}
    expected_reg_rev = digest(active_registry)

    if value['registry_revision'] != expected_reg_rev:
        raise ValueError('V3 registry mismatch')

    for key in ('source_observation_id', 'world_id', 'layout_id'):
        sha = value[key]
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('Invalid summary digest: ' + key)

    ext_id = value['source_extension_id']
    if ext_id is not None:
        if not isinstance(ext_id, str) or len(ext_id) != 64 or any(c not in '0123456789abcdef' for c in ext_id):
            raise ValueError('Invalid source_extension_id')

    prof_rev = value['sampling_profile_revision']
    if prof_rev!=SAMPLING_PROFILE_REVISION_V3:
        raise ValueError('Unknown sampling_profile_revision')

    if not isinstance(value['seed'], str) or str(parse_seed(value['seed'])) != value['seed']:
        raise ValueError('Invalid canonical seed')

    for key in ('anchor', 'nether_anchor'):
        if not isinstance(value[key], list) or len(value[key]) != 2:
            raise ValueError('Invalid anchor')
        for n in value[key]:
            integer(n, -30_000_000, 30_000_000)

    if value['nether_anchor'] != [n // 8 for n in value['anchor']]:
        raise ValueError('Nether projection mismatch')

    modes = value['anchor_modes']
    if not isinstance(modes, list) or not modes or len(set(modes)) != len(modes) or any(
        m not in ('origin', 'recommended', 'world_spawn_estimated', 'world_spawn_observed') for m in modes
    ):
        raise ValueError('Invalid anchor modes')

    if 'origin' in modes and value['anchor'] != [0, 0]:
        raise ValueError('Origin must be zero')

    if type(value['border_side']) is not int or value['border_side'] not in (2048, 4096, 8192):
        raise ValueError('Unsupported border')

    expected_lid = digest([
        'catalog-summary-v3',
        value['source_observation_id'],
        ext_id,
        prof_rev,
        expected_reg_rev,
        value['anchor'],
        modes,
        value['border_side']
    ])
    if value['layout_id'] != expected_lid:
        raise ValueError('V3 layout identity mismatch')

    features = value['features']
    if not isinstance(features, dict) or set(features) != set(active_features_by_id):
        raise ValueError('Feature registry differs')

    ow_radii = tuple(active_registry.get('overworld_radii', (256, 512, 1024)))
    nether_radii = tuple(active_registry.get('nether_radii', (64, 128, 256)))

    for fid, row in features.items():
        definition = active_features_by_id[fid]
        biome = definition['kind'] == 'biome_witness'
        if not isinstance(row, dict) or set(row) != {'dimension', 'counts', 'complete', 'nearest_d2', 'witness'} or row['dimension'] != definition['dimension']:
            raise ValueError('Invalid typed feature')

        counts = row['counts']
        complete = row['complete']
        if not isinstance(counts, list) or len(counts) != 4:
            raise ValueError('Invalid counts')
        for n in counts:
            integer(n, 0, 1 if biome else 200000)
        if counts != sorted(counts):
            raise ValueError('Counts not nested')

        if not isinstance(complete, list) or len(complete) != 4 or any(type(n) is not bool for n in complete):
            raise ValueError('Invalid completion vector')
        if biome and any(complete):
            raise ValueError('Sampled presence cannot prove absence')

        distance = row['nearest_d2']
        witness = row['witness']
        if (distance is None) != (witness is None) or (distance is None) != (counts[3] == 0):
            raise ValueError('Witness/count/distance mismatch')

        if distance is not None:
            integer(distance, 0, 2 * (60_000_000 ** 2))
            if not isinstance(witness, list) or len(witness) != 3:
                raise ValueError('Invalid witness')
            x, y, z = witness
            integer(x, -30_000_000, 30_000_000)
            integer(z, -30_000_000, 30_000_000)
            center = value['anchor'] if row['dimension'] == 'overworld' else value['nether_anchor']
            half = value['border_side'] // 2 if row['dimension'] == 'overworld' else 512
            if not (center[0] - half <= x < center[0] + half) or not (center[1] - half <= z < center[1] + half):
                raise ValueError('Witness outside selected border')
            if distance != (x - center[0]) ** 2 + (z - center[1]) ** 2:
                raise ValueError('Witness distance mismatch')

            radii = ow_radii if row['dimension'] == 'overworld' else nether_radii
            if any((counts[i] > 0) != (distance <= radius ** 2) for i, radius in enumerate(radii)):
                raise ValueError('Nearest witness contradicts radius counts')

            if biome:
                integer(y, -1000, 1000)
                # Legacy aliases remain v2 Y63 even when exact features multi-height
                if fid.startswith('biome.') and not fid.startswith('biome.exact.') and not fid.startswith('biome.group.'):
                    expected_legacy_y = 63 if row['dimension'] == 'overworld' else 64
                    if y != expected_legacy_y:
                        raise ValueError('Wrong query biome height for legacy alias')
                else:
                    eligible_y = definition.get('eligible_y')
                    if fid.startswith('biome.group.'):
                        eligible_y={y for mid in definition['atomic_members'] for y in active_features_by_id[mid]['eligible_y'] if active_features_by_id[mid].get('available',True)}
                    if eligible_y and y not in eligible_y:
                        raise ValueError(f'Wrong query biome height {y} for {fid}')
            elif y is not None:
                raise ValueError('Structure start has no verified height')

    legacy = value['legacy']
    (validate_summary if legacy.get('revision') == SUMMARY_REVISION else validate_anchor_summary)(legacy)
    for key in ('world_id', 'seed', 'anchor', 'border_side'):
        if legacy[key] != value[key]:
            raise ValueError('Legacy summary binding mismatch')

    return value

