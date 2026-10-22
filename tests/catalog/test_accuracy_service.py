import copy
import pytest
from seed_search.catalog.models import identity,empty_observation
from seed_search.catalog.summaries import summarize
from seed_search.catalog.anchors import make_anchor,derive_anchor_layouts
from seed_search.catalog.accuracy_store import write_bundle,read_bundle,REVISION
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.service import CatalogService


def setup(tmp_path):
    ident=identity(17,model_id='26.50',native_sha256='a'*64,source_sha256='b'*64)
    obs=empty_observation(ident)
    with SegmentedCatalog(tmp_path) as s:sid=s.publish([obs],summarize(obs))
    ctx=dict(identity=ident,dimension='overworld',provider='estimated_world_spawn_v1',observed_build=None,evidence_sha256='c'*64)
    entry=derive_anchor_layouts(obs,make_anchor(ctx,[7,13]))
    bundle=dict(revision=REVISION,snapshot_id=sid,anchors=[entry],tiles=[],metadata={})
    gen=write_bundle(tmp_path,bundle)
    req=dict(request_revision='catalog-query-accuracy-v1',edition='bedrock',dimension='overworld',
        game_build_id=ident['game_build_id'],world_settings_id='default',catalog_snapshot_id=sid,
        evidence_policy='predicted_plus_refined_witnesses_v1',fallback_profile='balanced_survival',border_side=2048,
        anchor_mode='world_spawn_estimated',rows=[],accuracy_generation=gen)
    return bundle,req


def test_bundle_spawn_query_and_detail_preserve_v1(tmp_path):
    bundle,req=setup(tmp_path);service=CatalogService(tmp_path)
    generation,read=read_bundle(tmp_path,req['catalog_snapshot_id'],req['accuracy_generation'])
    assert read==bundle
    results=service.query({'request':req})['results'];assert len(results)==1
    result=results[0];assert result['anchor']==[7,13] and result['anchor_evidence']['y'] is None
    detail=service.detail(req['catalog_snapshot_id'],result['world_id'],result['layout_id'])
    assert detail['layout']['anchor']==[7,13] and detail['anchor_evidence']['mode']=='world_spawn_estimated'
    old=dict(req,request_revision='catalog-query-v1',evidence_policy='predicted_observations_v1',anchor_mode='origin');old.pop('accuracy_generation')
    assert service.query({'request':old})['results'][0]['anchor']==[0,0]
    assert service.snapshots()['snapshots'][0]['accuracy_generation']==generation


def test_generation_and_snapshot_membership_fail_closed(tmp_path):
    bundle,req=setup(tmp_path);service=CatalogService(tmp_path)
    wrong=dict(req,accuracy_generation='f'*64)
    with pytest.raises(__import__('seed_search.catalog.service',fromlist=['ServiceError']).ServiceError,match='unavailable'):service.query({'request':wrong})
    bad=copy.deepcopy(bundle);bad['anchors'][0]['observation_id']='f'*64
    for row in bad['anchors'][0]['layouts']:
        from seed_search.catalog.registry import digest
        row['observation_id']='f'*64;row['layout_id']=digest([row['revision'],'f'*64,row['anchor'],row['border_side']])
    with pytest.raises(ValueError,match='pinned snapshot'):write_bundle(tmp_path,bad)


def test_published_anchor_removal_cannot_break_old_share_links(tmp_path):
    bundle,req=setup(tmp_path)
    empty=dict(bundle,anchors=[])
    with pytest.raises(ValueError,match='removed or replaced'):write_bundle(tmp_path,empty)
    assert read_bundle(tmp_path,req['catalog_snapshot_id'])[1]==bundle


def test_sparse_missing_biome_witness_stays_an_unresolved_retained_world(tmp_path):
    bundle,req=setup(tmp_path);req['rows']=[dict(kind='biome_witness',rule='required',any_of=['biome.mushroom_fields'],scope={'kind':'inside_border'})]
    result=CatalogService(tmp_path).query({'request':req})
    assert result['results']==[] and result['unresolved_worlds']==1
    assert result['unresolved_candidates'][0]['seed']=='17'


def test_positive_or_witness_does_not_require_unknown_unused_alternative(tmp_path):
    from seed_search.catalog.refinement import make_tile
    bundle,req=setup(tmp_path)
    ident=bundle['anchors'][0]['anchor']['context']['identity']
    context=dict(identity=ident,dimension='overworld',provider='procedural_model_v1',observed_build=None,evidence_sha256='d'*64)
    bundle['tiles']=[make_tile(context,[1,1,2,2],63,[77],biome_names={'77':'mushroom_fields'})]
    req['accuracy_generation']=write_bundle(tmp_path,bundle)
    req['rows']=[dict(kind='biome_witness',rule='required',any_of=['biome.mushroom_fields','biome.mangrove_swamp'],scope={'kind':'near_base','radius':256})]
    service=CatalogService(tmp_path);result=service.query({'request':req})
    assert len(result['results'])==1 and result['unresolved_worlds']==0
    assert result['results'][0]['refined_biome_witnesses'][0]['x']==1
    # Cached response does not permit mutated nested data to alter later results.
    result['results'][0]['counts'][0][0]=999
    repeated=service.query({'request':req});assert repeated['stats']['result_cache_hit'] is True
    assert repeated['results'][0]['counts'][0][0]==0


def test_expired_accuracy_cursor_is_rejected_by_shared_decoder(tmp_path):
    import time
    from seed_search.catalog.registry import digest
    from seed_search.catalog.service import ServiceError
    bundle,req=setup(tmp_path);service=CatalogService(tmp_path)
    service.query({'request':req})
    cursor=service._token(dict(snapshot=req['catalog_snapshot_id'],request=digest(req),size=20,last=[],expires=0))
    with pytest.raises(ServiceError,match='expired'):service.query({'request':req,'cursor':cursor})


def test_corrupt_accuracy_artifact_is_rejected_even_with_warm_result_cache(tmp_path):
    import json
    from seed_search.catalog.service import ServiceError
    bundle,req=setup(tmp_path);service=CatalogService(tmp_path)
    service.query({'request':req});assert service.query({'request':req})['stats']['result_cache_hit']
    binding=json.loads((tmp_path/'accuracy'/(req['accuracy_generation']+'.json')).read_text())
    artifact=tmp_path/'accuracy/objects'/binding['artifact']['relative_key']
    raw=artifact.read_bytes();artifact.write_bytes(raw[:-1])
    with pytest.raises(ServiceError)as failed:service.query({'request':req})
    assert failed.value.status==503 and failed.value.code=='integrity_error'


def test_colocated_spawn_roles_share_geometry_without_losing_evidence(tmp_path):
    bundle,req=setup(tmp_path)
    first=bundle['anchors'][0]
    context=dict(first['anchor']['context'],provider='observed_world_spawn_v1',observed_build='1.26.52.3',evidence_sha256='e'*64)
    anchor=make_anchor(context,first['anchor']['coordinate'])
    second=dict(first,anchor=anchor)
    bundle['anchors'].append(second);generation=write_bundle(tmp_path,bundle)
    service=CatalogService(tmp_path)
    row=service.query({'request':dict(req,accuracy_generation=generation,anchor_mode='world_spawn_observed')})['results'][0]
    assert row['anchor_evidence']['mode']=='world_spawn_observed'
    detail=service.detail(req['catalog_snapshot_id'],row['world_id'],row['layout_id'])
    assert detail['anchor_evidence'] is None
    assert {a['mode']for a in detail['anchor_roles']}=={'world_spawn_estimated','world_spawn_observed'}
