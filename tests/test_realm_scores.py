import copy
import pytest
from seed_search.realm.terrain import apply_score_policy, attach_actual_evaluation
from seed_search.realm.reports import ranked, rescore, export
from test_realm_cli_reports import populated


def result(source='prediction', evidence='PREDICTED', geometry=80, fit=40):
    return dict(geometry_score=geometry, biome_fit=fit, baseline_quality=60,
                evidence=evidence, score_generation_source=source, geometry_pass=True,
                qualification=evidence, border_fit={'complete':True,'state':'within'},
                score_component_status={'geometry':evidence,'biome_fit':evidence,'baseline_quality':evidence})


def test_custom_policy_and_actual_components_are_not_promoted():
    weights=dict(geometry_weight=.2,biome_fit_weight=.5,baseline_weight=.3)
    prediction=apply_score_policy(result(),weights)
    actual=apply_score_policy(result('actual','VERIFIED',20,0),weights,
                              component_status={'biome_fit':'UNKNOWN','baseline_quality':'PREDICTED'})
    attach_actual_evaluation(prediction,actual,weights)
    assert prediction['score']==54
    assert prediction['predicted_score']==54
    assert prediction['actual_partial_score']==22
    assert prediction['verified_score'] is None
    assert actual['score_interval']=={'low':22.,'high':72.,'policy':'unknown-components-bounds; prediction error not calibrated'}
    assert actual['score_component_status']['biome_fit']=='UNKNOWN'
    assert not actual['score_verified_complete']


def test_verified_score_requires_complete_footprint_and_active_components():
    actual=result('actual','VERIFIED')
    apply_score_policy(actual)
    assert actual['verified_score']==74
    actual['border_fit']['complete']=False
    apply_score_policy(actual)
    assert actual['verified_score'] is None
    actual['border_fit']['complete']=True
    actual['score_component_status'].update(biome_fit='UNKNOWN',baseline_quality='PREDICTED')
    apply_score_policy(actual,dict(geometry_weight=1,biome_fit_weight=0,baseline_weight=0))
    assert actual['verified_score']==80


def test_rescore_preserves_both_nested_views_and_exports(tmp_path):
    store,cfg=populated(tmp_path)
    try:
        candidate=next(store.iter_candidates())
        prediction=apply_score_policy(result())
        actual=apply_score_policy(result('actual','PARTIAL',20,0),component_status={'biome_fit':'UNKNOWN','baseline_quality':'PREDICTED'})
        attach_actual_evaluation(prediction,actual)
        store.upsert_variant(candidate['id'],'v1',[0,0],prediction)
        policy=copy.deepcopy(cfg);policy['scoring'].update(geometry_weight=.25,biome_fit_weight=.5,baseline_weight=.25)
        rescore(store,policy)
        saved=store.get_variant(candidate['id'],'v1',[0,0])['result']
        assert saved['score']==saved['predicted_score']
        assert saved['actual_partial_score']==saved['actual_evaluation']['score']
        assert saved['actual_partial_score']!=saved['predicted_score']
        assert saved['actual_evaluation']['score_component_status']['biome_fit']=='UNKNOWN'
        assert saved['verified_score'] is None
        assert saved['score_policy']['geometry_weight']==.25
        export(store)
        import csv
        with (store.run/'results/v1.csv').open() as f: row=next(csv.DictReader(f))
        assert float(row['actual_partial_score'])==saved['actual_partial_score']
        assert float(row['predicted_score'])==saved['predicted_score']
    finally:store.close()


def test_ranking_uses_complete_verified_geometry_not_prediction(tmp_path):
    store,cfg=populated(tmp_path)
    try:
        cid=next(store.iter_candidates())['id']
        for center,geometry,passed in [([0,0],99,False),([1,1],10,True)]:
            prediction=apply_score_policy(result(geometry=geometry))
            actual=result('actual','VERIFIED',geometry=100-geometry)
            actual['geometry_pass']=passed
            attach_actual_evaluation(prediction,actual)
            store.upsert_variant(cid,'v1',center,prediction)
        rows=ranked(store,'v1')
        assert rows[0]['center']==[1,1]
        assert rows[0]['ranking_view']=='verified'
        assert rows[0]['ranking_result']['geometry_score']==90
        assert rows[0]['result']['predicted_score']==18
        # Unknown actual biome evidence retains prediction ranking and raw actual view.
        for row in rows:
            prediction=row['result'];actual=prediction['actual_evaluation']
            actual['score_component_status']['biome_fit']='UNKNOWN'
            attach_actual_evaluation(prediction,actual)
            store.upsert_variant(cid,'v1',row['center'],prediction)
        rows=ranked(store,'v1')
        assert rows[0]['center']==[0,0]
        assert rows[0]['ranking_view']=='prediction'
        assert rows[0]['result']['verified_score'] is None
    finally:store.close()


@pytest.mark.parametrize('with_biomes',[False,True])
def test_actual_cli_uses_saved_policy_without_copying_prediction_biomes(tmp_path,monkeypatch,capsys,with_biomes):
    from seed_search.realm.cli import main
    from seed_search.realm.store import RealmStore
    from seed_search.realm.verification import VerificationAdapter
    import seed_search.realm.verification as verification
    import seed_search.realm.terrain as terrain
    import seed_search.backend as backend_module
    store,cfg=populated(tmp_path)
    cid=next(store.iter_candidates())['id']
    prediction=apply_score_policy(result(fit=100))
    prediction['border_fit']['footprint']=[-1,-1,1,1]
    store.upsert_variant(cid,'v1',[0,0],prediction)
    policy=copy.deepcopy(cfg);policy['scoring'].update(geometry_weight=.3,biome_fit_weight=.5,baseline_weight=.2)
    rescore(store,policy);store.close()
    calls=[]
    def evaluate(*args,**kwargs):
        calls.append(kwargs)
        actual=result('actual','VERIFIED',geometry=20,fit=kwargs['biome_fit'])
        actual['baseline_quality']=kwargs['baseline_quality']
        return actual
    monkeypatch.setattr(terrain,'evaluate_v1',evaluate)
    monkeypatch.setattr(VerificationAdapter,'verify_candidate',lambda *a,**k: {
        'id':'synthetic-generated-observation','status':'PARTIAL',
        'raster':{'bounds':[-1,-1,1,1],'resolution':2,'height':[[70]],'known':[[True]],
                  'water':[[False]],'biomes':[[4]] if with_biomes else None,
                  'metadata':{'source':'actual','biome_evidence':'actual_generated'} if with_biomes else {'source':'actual'}}})
    class NoNative:
        def __init__(self,*args):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
    monkeypatch.setattr(backend_module,'Backend',NoNative)
    monkeypatch.setattr(verification,'calibrate_prediction',lambda *a: {'synthetic':True})
    main(['verify-terrain','--run',str(tmp_path),'--variant','v1','--top','1'])
    with RealmStore(tmp_path,resume=True) as saved:
        r=saved.get_variant(cid,'v1',[0,0])['result']
        actual=r['actual_evaluation']
        assert (calls[0]['biome_fit']>0) if with_biomes else calls[0]['biome_fit']==0
        assert actual['biome_fit']==calls[0]['biome_fit']
        assert actual['score_policy']['geometry_weight']==.3
        assert actual['score_component_status']['biome_fit']==('PARTIAL' if with_biomes else 'UNKNOWN')
        assert actual['score_component_status']['baseline_quality']=='PREDICTED'
        assert actual['score']==pytest.approx(.3*20+.5*actual['biome_fit']+.2*actual['baseline_quality'])
        assert r['verified_score'] is None
        assert r['predicted_score']!=r['actual_partial_score']


def test_legacy_actual_copied_biome_value_is_not_actual_evidence():
    legacy=result('actual','VERIFIED',fit=100)
    legacy.pop('score_component_status')
    apply_score_policy(legacy)
    assert legacy['biome_fit']==0
    assert legacy['unverified_biome_fit_input']==100
    assert legacy['score_component_status']['biome_fit']=='UNKNOWN'
    assert legacy['verified_score'] is None


def test_actual_raster_biome_fit_is_reasserted_with_explicit_provenance():
    import numpy as np
    from seed_search.realm.terrain import evaluate_v1
    from test_realm_terrain import synthetic
    raster=synthetic('lake',actual=True)
    raster.biomes=np.full(raster.shape,4,dtype=int)
    actual=evaluate_v1(raster,(0,0),biome_fit=75)
    # Geometry evaluation cannot infer the provenance of a supplied numeric fit.
    assert actual['score_component_status']['biome_fit']=='UNKNOWN'
    apply_score_policy(actual,dict(geometry_weight=.5,biome_fit_weight=.5,baseline_weight=0),
                       source='actual',biome_fit=75,
                       component_status={'biome_fit':'VERIFIED'})
    assert actual['biome_fit']==75
    assert actual['score']==pytest.approx(.5*actual['geometry_score']+37.5)
    assert actual['score_component_status']['biome_fit']=='VERIFIED'


def test_provenance_assignment_alone_does_not_restore_legacy_copied_fit():
    legacy=result('actual','VERIFIED',fit=100)
    legacy.pop('score_component_status')
    apply_score_policy(legacy)
    apply_score_policy(legacy,component_status={'biome_fit':'VERIFIED'})
    assert legacy['biome_fit']==0
    assert legacy['unverified_biome_fit_input']==100
