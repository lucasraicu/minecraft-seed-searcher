"""Independent boundary and validation checks for the frozen reference contract."""
import copy
import json
import pytest
from seed_search.catalog.registry import ENVELOPE, FEATURE_IDS, SIDES
from seed_search.catalog.models import identity, empty_observation, validate_observation, world_id
from seed_search.catalog.geometry import eligible, tile, anchors
from seed_search.catalog.request import load_request, validate_request


def test_seed_and_identity_roundtrip():
    for seed in (-(1 << 63), -1, 0, (1 << 63)-1):
        i = identity(seed, model_id='MC_26_50', native_sha256='a'*64, source_sha256='b'*64)
        obs = empty_observation(i)
        assert validate_observation(json.loads(json.dumps(obs))) == obs
        assert isinstance(i['seed'], str)
        assert len(world_id(i)) == 64
    with pytest.raises(ValueError):
        identity(0, model_id='MC_26_50', native_sha256='a'*64, source_sha256='b'*64, game_build_id='1.26.52.3')


def test_geometry_and_catalog_scope():
    assert len(FEATURE_IDS) == 23 and len(anchors()) == 81
    assert SIDES == (2048, 4096, 8192)
    assert tile(-1, -257) == (-1, -2)
    assert eligible(-1024, 0, (0, 0), 2048, 1024)
    assert not eligible(1024, 0, (0, 0), 2048, 1024)
    assert eligible(1024, 0, (0, 0), 4096, 1024)
    assert not eligible(512, 1, (0, 0), 8192, 512)


def request():
    return dict(request_revision='catalog-query-v1', edition='bedrock', game_build_id='research:MC_26_50',
        catalog_snapshot_id='snapshot', world_settings_id='default', dimension='overworld',
        anchor_mode='recommended', border_side=2048, evidence_policy='predicted_observations_v1',
        fallback_profile='balanced_survival', rows=[])


@pytest.mark.parametrize('patch', [dict(border_side=True), dict(border_side=16384), dict(anchor_mode='spawn'),
    dict(unknown=0), dict(game_build_id='1.26.52.3'), dict(rows=[{'rule':'required','kind':'structure_count',
    'feature':'structure.village','at_least':True,'scope':{'kind':'near_base','radius':512}}])])
def test_reject_bad_queries(patch):
    with pytest.raises(ValueError):
        validate_request(dict(request(), **patch))


def test_request_copy_and_strict_json():
    q = request(); parsed = validate_request(q, snapshot_id='snapshot')
    q['rows'].append('mutation')
    assert parsed['rows'] == []
    for text in ('{"rows":[],"rows":[]}', '{"rows":NaN}'):
        with pytest.raises(ValueError):
            load_request(text)


def test_corrupt_observation_cannot_be_complete():
    obs = empty_observation(identity(0, model_id='MC_26_50', native_sha256='a'*64, source_sha256='b'*64))
    obs['coverage']['biome.cherry_grove'] = {'status':'complete', 'bounds':list(ENVELOPE),
        'method_id':'predictor_world_lattice_y63_stride64_v1'}
    with pytest.raises(ValueError): validate_observation(obs)
    obs['coverage'] = {}
    obs['structures']['structure.village'] = [[5120, 0]]
    with pytest.raises(ValueError): validate_observation(obs)
