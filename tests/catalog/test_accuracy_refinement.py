import copy
import pytest
from seed_search.catalog.models import identity, empty_observation
from seed_search.catalog.accuracy import validate_context, context_id
from seed_search.catalog.anchors import make_anchor, derive_anchor_layouts, validate_anchor_summary
from seed_search.catalog.refinement import make_tile,decode_tile,evaluate_scope,sample_tile
from seed_search.catalog.registry import ENVELOPE
from seed_search.catalog.summaries import summarize
from seed_search.catalog.codec import pack_summary


def context(provider='procedural_model_v1'):
    return dict(identity=identity('-9223372036854775808',model_id='26.50',native_sha256='a'*64,source_sha256='b'*64),
        dimension='overworld',provider=provider,observed_build=None,evidence_sha256='c'*64)


def test_context_provider_seed_and_settings_are_not_interchangeable():
    c=context();key=context_id(c)
    for field,value in [('seed','9223372036854775807'),('world_settings_id','other'),('source_sha256','d'*64)]:
        other=copy.deepcopy(c);other['identity'][field]=value
        assert context_id(other)!=key
    bad=copy.deepcopy(c);bad['observed_build']='1.26.52.3'
    with pytest.raises(ValueError):validate_context(bad)
    frozen=validate_context(c);c['identity']['seed']='0';assert frozen['identity']['seed']!='0'


def test_arbitrary_spawn_and_same_inventory_all_borders():
    c=context('estimated_world_spawn_v1');a=make_anchor(c,[7,-13]);obs=empty_observation(c['identity'])
    obs['structures']={'structure.village':[[7,-13],[100,100],[500,500]]}
    obs['coverage']['structure.village']=dict(status='complete',bounds=list(ENVELOPE),method_id='predictor_viable_starts_v1')
    before=copy.deepcopy(obs);derived=derive_anchor_layouts(obs,a)
    assert obs==before and len(derived['layouts'])==3
    for row in derived['layouts']:
        assert row['anchor']==[7,-13] and row['counts'][0][:2]==[2,2]
        validate_anchor_summary(row)
        with pytest.raises(ValueError):pack_summary(row)
    assert all(pack_summary(row) for row in summarize(obs))
    bad=copy.deepcopy(a);bad['y']=32767
    with pytest.raises(ValueError):derive_anchor_layouts(obs,bad)


def test_out_of_envelope_is_partial_not_rejected():
    c=context('estimated_world_spawn_v1');obs=empty_observation(c['identity'])
    rows=derive_anchor_layouts(obs,make_anchor(c,[5000,5000]))['layouts']
    assert len(rows)==3 and not any(any(v) for r in rows for v in r['complete'])
    rows[0]['complete'][0][0]=True
    with pytest.raises(ValueError):validate_anchor_summary(rows[0])


def test_exact_patch_missed_by_coarse_grid_and_partial_absence():
    c=context();a=make_tile(c,[0,0,4,4],63,[1]*5+[2]+[1]*10)
    assert decode_tile(a)[5]==2
    assert evaluate_scope([a],c,[0,0,4,4],63,[2])['witness']==[1,63,1,2]
    assert evaluate_scope([a],c,[0,0,4,4],63,[3])['status']=='absent'
    assert evaluate_scope([a],c,[0,0,5,4],63,[3])['status']=='unknown'
    assert evaluate_scope([a],c,[0,0,5,4],63,[2])['status']=='present'
    unknown=make_tile(c,[0,0,1,1],63,[None])
    assert evaluate_scope([unknown],c,[0,0,1,1],63,[3])['status']=='unknown'


def test_circle_clipped_to_border_and_half_open_edges():
    c=context();tile=make_tile(c,[-2,-2,3,3],-64,[1]*25)
    p=evaluate_scope([tile],c,[-2,-2,3,3],-64,[2],anchor=[0,0],radius=1)
    assert p['status']=='absent' and p['total_blocks']==5
    assert evaluate_scope([tile],c,[2,2,3,3],-64,[1])['witness']==[2,-64,2,1]


def test_conflicts_build_scope_height_corruption_and_bounded_sampling():
    c=context();a=make_tile(c,[0,0,2,2],63,[1]*4);b=make_tile(c,[1,1,2,2],63,[2])
    with pytest.raises(ValueError):evaluate_scope([a,b],c,[0,0,2,2],63,[1])
    other=context();other['identity']['seed']='0'
    with pytest.raises(ValueError):evaluate_scope([a],other,[0,0,2,2],63,[1])
    with pytest.raises(ValueError):evaluate_scope([a],c,[0,0,2,2],64,[1])
    bad=copy.deepcopy(a);bad['data']=bad['data'][:-1]
    with pytest.raises(ValueError):decode_tile(bad)
    calls=[]
    with pytest.raises(ValueError):sample_tile(c,[0,0,65,65],63,lambda *p:calls.append(p))
    assert calls==[]
    with pytest.raises(ValueError):make_tile(c,[0,0,1,1],True,[1])
    assert len(a['data'])<len([1]*4096)


def test_empty_clipped_scope_is_rejected_instead_of_implying_global_absence():
    with pytest.raises(ValueError,match='no logical blocks'):
        evaluate_scope([],context(),[0,0,2,2],63,[1],anchor=[9,9],radius=0)


def test_game_observation_id_namespaces_are_not_merged_across_reports():
    from seed_search.catalog.refinement import provider_id
    c=context('bds_script_api_v1');c['observed_build']='1.26.52.3'
    other=dict(c,evidence_sha256='d'*64)
    assert provider_id(c)!=provider_id(other)
    a=make_tile(c,[0,0,1,1],63,[1],biome_names={'1':'plains'})
    b=make_tile(other,[1,0,2,1],63,[1],biome_names={'1':'forest'})
    with pytest.raises(ValueError,match='Mismatched provider'):evaluate_scope([a,b],c,[0,0,2,1],63,[2])
