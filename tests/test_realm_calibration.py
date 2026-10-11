import copy

import pytest

from seed_search.realm.calibration import summarize_pairs, summarize_store
from seed_search.realm.reports import rescore
from test_realm_report_recovery import populated, weight_change


def pair(index, predicted, actual, variant='v1'):
    center=[index,0]
    return {'seed':'1','stronghold':[0,0],'center':center,'variant':variant,
            'game_version':'26.52','bds_version':'1.26.52.3','observation_id':str(index),
            'prediction':{'center':center,'geometry_pass':predicted,'geometry_score':90 if predicted else 20},
            'actual':{'center':center,'geometry_pass':actual,'geometry_score':80 if actual else 10,
                      'evidence':'VERIFIED','border_fit':{'complete':True}}}


def summarize(rows):
    return summarize_pairs(rows,target_version='26.52',backend_version='1.26.52.3')


def test_complete_cohort_confusion_and_variants_are_independent():
    rows=[pair(0,True,True),pair(1,True,False),pair(2,False,True),pair(3,False,False),pair(0,False,True,'v2')]
    result=summarize(rows)
    v1=result['variants']['v1']
    assert v1['confusion']==dict(true_positive=1,false_positive=1,true_negative=1,false_negative=1)
    assert v1['cohort_precision']==v1['cohort_recall']==v1['cohort_false_negative_rate']==.5
    assert result['variants']['v2']['confusion']['false_negative']==1
    assert not result['population_estimate']


@pytest.mark.parametrize('change',[
    lambda p:p['actual'].update(evidence='PARTIAL'),
    lambda p:p['actual']['border_fit'].update(complete=False),
    lambda p:p.update(bds_version='1.26.50.1'),
    lambda p:p.update(observation_id=None),
    lambda p:p['actual'].update(center=[100,0]),
    lambda p:p['actual'].update(geometry_score=float('nan')),
    lambda p:p['actual'].update(geometry_pass=None),
])
def test_partial_missing_mismatched_truth_never_becomes_negative(change):
    p=pair(0,True,False);change(p)
    result=summarize([p])
    assert result['status']=='UNSUPPORTED'
    assert result['variants']['v1']['pairs']==0
    assert len(result['excluded'])==1
    assert result['variants']['v1']['cohort_recall'] is None


def test_duplicate_pairs_fail_instead_of_inflating_sample_size():
    p=pair(0,True,True)
    with pytest.raises(ValueError,match='Duplicate'):summarize([p,copy.deepcopy(p)])


def test_constant_scores_have_no_defined_rank_correlation():
    rows=[pair(i,True,True) for i in range(3)]
    assert summarize(rows)['variants']['v1']['geometry_rank_spearman'] is None


def test_store_rejects_verified_label_without_actual_raster_provenance(tmp_path):
    store,cfg=populated(tmp_path)
    try:
        result=summarize_store(store)
        assert result['status']=='UNSUPPORTED'
        assert len(result['excluded'])==6
        assert all(v['pairs']==0 for v in result['variants'].values())
    finally:store.close()


def test_rescore_recomputes_bonus_uncertainty(tmp_path):
    store,cfg=populated(tmp_path)
    try:
        rescore(store,weight_change(cfg))
        candidate=store.get_candidate('0:1:2')
        uncertainty=candidate['baseline_score_uncertainty']
        assert uncertainty['optional_prediction_interval'][0]==15
        assert uncertainty['actual_generation_score_interval'][0]==0
        assert candidate['biomes']['uncertainty']['score_interval'][0]==candidate['biomes']['score']
    finally:store.close()
