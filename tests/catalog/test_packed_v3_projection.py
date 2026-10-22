import copy
import pytest
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.registry import REGISTRY_V3,SAMPLING_PROFILE_REVISION_V3,digest
from seed_search.catalog.models import world_id
from test_expansion_storage import observation,extension
from seed_search.catalog.summaries import summarize_v2,summarize_v3


def case(tmp_path):
    o=observation();e=extension(o);rows=summarize_v3(o,extension=e,base_summaries=summarize_v2(o))
    rows=[r for r in rows if r['border_side']==2048];store=AutomationStore(tmp_path)
    entry=dict(world_id=world_id(o['identity']),identity=o['identity'],observation_id=digest(o),registry_revision=digest(REGISTRY_V3),sampling_profile_revision=SAMPLING_PROFILE_REVISION_V3,source_extension_id=digest(e),artifact={'sha256':'d'*64})
    return store,entry,rows


def test_exact_all_field_roundtrip_and_mode_filter(tmp_path):
    store,entry,rows=case(tmp_path);packed=store._pack_query_rows(rows,REGISTRY_V3)
    assert store._unpack_query_rows(packed,entry,REGISTRY_V3,2048)==rows
    assert store._unpack_query_rows(packed,entry,REGISTRY_V3,2048,'origin')==[r for r in rows if 'origin' in r['anchor_modes']]
    for row in rows:assert row['features']['biome.exact.ocean']['witness'] is None


def test_malformed_packed_fields_rejected(tmp_path):
    store,entry,rows=case(tmp_path);packed=store._pack_query_rows(rows,REGISTRY_V3)
    for mutate in [lambda r:r.append(None),lambda r:r.__setitem__(0,'invalid'),lambda r:r.__setitem__(1,[0]),lambda r:r.__setitem__(2,['fake']),lambda r:r.__setitem__(4,[]),lambda r:r[4][0].__setitem__(1,16),lambda r:r[4][0].__setitem__(0,[-1]*4),lambda r:r[4][-1].__setitem__(0,-1),lambda r:r[4][0].__setitem__(2,-1),lambda r:r[4][0].__setitem__(3,[1,None])]:
        value=copy.deepcopy(packed);mutate(value[0])
        with pytest.raises(ValueError):store._unpack_query_rows(value,entry,REGISTRY_V3,2048)


def test_v4_and_v5_same_query_view_and_source_checks(tmp_path):
    store,entry,rows=case(tmp_path)
    header=dict(world_id=entry['world_id'],identity=entry['identity'],observation_id=entry['observation_id'],bundle_sha256=entry['artifact']['sha256'],border_side=2048,summary_validator_sha256=store._query_validator_id(),row_count=len(rows),registry=REGISTRY_V3,sampling_profile_revision=SAMPLING_PROFILE_REVISION_V3,source_extension_id=entry['source_extension_id'])
    v4=store.artifacts.put_json(dict(header,revision='catalog-query-projection-v4',rows=rows));v5=store.artifacts.put_json(dict(header,revision='catalog-query-projection-v5',rows=store._pack_query_rows(rows,REGISTRY_V3)))
    for artifact in [v4,v5]:
        bound=dict(entry,summary_artifacts={'2048':artifact})
        assert store._projection(bound,2048)==rows
        assert list(store.iter_query_summaries({'worlds':[bound]},2048,'origin'))==[r for r in rows if 'origin' in r['anchor_modes']]
        with pytest.raises(ValueError):store._projection(dict(bound,source_extension_id='f'*64),2048)
    # A stale validator takes the strict decoder path and must still round-trip.
    strict=store.artifacts.put_json(dict(header,summary_validator_sha256='f'*64,revision='catalog-query-projection-v5',rows=store._pack_query_rows(rows,REGISTRY_V3)))
    assert store._projection(dict(entry,summary_artifacts={'2048':strict}),2048)==rows


def test_standard_gzip_levels_preserve_json_and_bounds(tmp_path):
    from seed_search.catalog.artifacts import ArtifactStore
    store=ArtifactStore(tmp_path/'compressed');value={'repeated':['source-bound']*10000}
    refs=[store.put_json(value,compression_level=n) for n in (1,9)]
    assert all(store.get_json(ref)==value and ref['codec']=='gzip' for ref in refs)
    assert refs[0]['byte_length']>=refs[1]['byte_length']
    for level in (0,10,True,'1'):
        with pytest.raises(ValueError):store.put_json(value,compression_level=level)


def test_lazy_query_keeps_complete_results_and_strict_fallback(tmp_path):
    from seed_search.catalog.query import rank_v2,rank_v3
    store,entry,rows=case(tmp_path);packed=store._pack_query_rows(rows,REGISTRY_V3)
    lazy=store._unpack_query_rows(packed,entry,REGISTRY_V3,2048,validate=False,lazy_features=True)
    assert len(lazy[0]['features'].decoded)==0
    lazy[0]['features']['biome.exact.forest']
    assert len(lazy[0]['features'].decoded)==1
    header=dict(world_id=entry['world_id'],identity=entry['identity'],observation_id=entry['observation_id'],bundle_sha256=entry['artifact']['sha256'],border_side=2048,summary_validator_sha256='f'*64,row_count=len(rows),registry=REGISTRY_V3,sampling_profile_revision=SAMPLING_PROFILE_REVISION_V3,source_extension_id=entry['source_extension_id'])
    strict=store.artifacts.put_json(dict(header,revision='catalog-query-projection-v5',rows=packed))
    strict_rows=store._projection(dict(entry,summary_artifacts={'2048':strict}),2048,lazy_features=True)
    assert isinstance(strict_rows[0]['features'],dict) and strict_rows==rows
    for revision,ranker,fid in [('v2',rank_v2,'biome.forest'),('v3',rank_v3,'biome.exact.forest')]:
        for rule in ('required','preferred'):
            req=dict(request_revision='catalog-query-'+revision,evidence_policy='predicted_observations_'+revision,edition='bedrock',game_build_id=entry['identity']['game_build_id'],catalog_snapshot_id='a'*64,world_settings_id='default',dimension='overworld',anchor_mode='recommended',border_side=2048,fallback_profile='balanced_survival',rows=[dict(rule=rule,kind='biome_witness',any_of=[fid],scope={'kind':'inside_border'},**({'importance':3} if rule=='preferred' else {}))])
            full=ranker(rows,req);actual=ranker(lazy,req)
            assert actual==full
            for candidate in [*actual['results'],*actual['unresolved_candidates']]:
                assert set(candidate['feature_counts'])==set(rows[0]['features'])
