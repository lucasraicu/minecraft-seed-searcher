"""World-spawn anchors and arbitrary-center summaries, separate from v1 grid rows."""
from .accuracy import validate_context, context_id, integer, sha256
from .models import validate_observation, observation_id, world_id
from .registry import digest, SIDES, ENVELOPE
from .geometry import bounds_for
from .codec import validate_summary_numbers
from ..seeds import parse_seed

REVISION = 'catalog-anchor-v1'
SUMMARY_REVISION = 'catalog-anchor-summary-v1'
MODES = ('world_spawn_estimated', 'world_spawn_observed')


def validate_anchor_coordinate(value):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError('Expected absolute [x,z] anchor')
    return [integer(v, -30_000_000, 30_000_000) for v in value]


def make_anchor(context, coordinate):
    ctx = validate_context(context)
    modes = {'estimated_world_spawn_v1': MODES[0], 'observed_world_spawn_v1': MODES[1]}
    if ctx['provider'] not in modes or ctx['dimension'] != 'overworld':
        raise ValueError('World spawn requires an Overworld spawn provider')
    coordinate = validate_anchor_coordinate(coordinate)
    body = dict(revision=REVISION, context=ctx, mode=modes[ctx['provider']],
                coordinate=coordinate, y=None, semantics='world_spawn_xz_not_player_landing')
    return dict(body, anchor_id=digest(body))


def validate_anchor(value):
    if not isinstance(value, dict) or set(value) != {'revision','context','mode','coordinate',
            'y','semantics','anchor_id'}:
        raise ValueError('Invalid anchor schema')
    expected = make_anchor(value['context'], value['coordinate'])
    if value != expected:
        raise ValueError('Anchor identity/provenance mismatch')
    return expected


def validate_anchor_summary(value):
    fields = {'revision','observation_id','world_id','layout_id','seed','anchor','border_side',
              'counts','structure_nearest_d2','biome_nearest_d2','biome_witness_refs','complete'}
    if not isinstance(value, dict) or set(value) != fields or value['revision'] != SUMMARY_REVISION:
        raise ValueError('Invalid arbitrary-anchor summary')
    if not isinstance(value['seed'],str) or str(parse_seed(value['seed'])) != value['seed']:
        raise ValueError('Invalid canonical seed')
    anchor = validate_anchor_coordinate(value['anchor'])
    if type(value['border_side']) is not int or value['border_side'] not in SIDES:
        raise ValueError('Unsupported border side')
    for key in ('observation_id','world_id','layout_id'):
        sha256(value[key])
    if value['layout_id'] != digest([SUMMARY_REVISION,value['observation_id'],anchor,value['border_side']]):
        raise ValueError('Anchor layout identity mismatch')
    validate_summary_numbers(value)
    box = bounds_for(anchor,value['border_side'])
    if not (ENVELOPE[0]<=box[0] and ENVELOPE[1]<=box[1] and box[2]<=ENVELOPE[2] and box[3]<=ENVELOPE[3]):
        if any(any(row) for row in value['complete']):
            raise ValueError('Out-of-envelope layout cannot claim complete coverage')
    return value


def derive_anchor_layouts(observation, anchor):
    obs = validate_observation(observation)
    anchor = validate_anchor(anchor)
    if anchor['context']['identity'] != obs['identity']:
        raise ValueError('Anchor/observation build or seed differs')
    from .summaries import summarize_at
    layouts = summarize_at(obs, anchor['coordinate'])
    return dict(anchor=anchor, observation_id=observation_id(obs), world_id=world_id(obs['identity']),
                layouts=layouts)
