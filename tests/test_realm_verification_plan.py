"""Actual coverage and cached verification scheduling, without generation."""
import numpy as np
import pytest

from seed_search.realm.cli import select_verification
from seed_search.realm.verification import VerificationAdapter
from seed_search.realm.verification_plan import verification_region
from seed_search.realm.raster import Raster
from seed_search.realm.terrain import evaluate_v2
from test_realm_verification_selection import pool


def prepared(tmp_path):
    store,cfg=pool(tmp_path)
    for row in list(store.iter_variants()):
        result=row['result'];x,z=row['center']
        result['center']=row['center']
        result['border_fit']['footprint']=[x-100,z-100,x+101,z+101]
        store.upsert_variant(row['candidate_id'],'v1',row['center'],result)
    return store,cfg,VerificationAdapter(cfg,store,runtime=lambda *a:pytest.fail('No generation during selection'))


def save_cached(store,cfg,adapter,center,status='PARTIAL'):
    row=store.get_variant(f'1:{center}:0','v1',[center,0])
    bounds=verification_region(row['result'],'v1',cfg,16)
    key=adapter.observation_id('1',bounds,16)
    store.upsert_observation(row['candidate_id'],{'id':key,'status':status,'seed':'1','bounds':list(bounds)})
    return key


def test_full_v2_halo_can_complete_geometry_when_measured_footprint_cannot():
    cfg={'terrain':{}}
    prediction={'center':[0,0],'border_fit':{'footprint':[-628,-628,629,629]}}
    bounds=verification_region(prediction,'v2',cfg,8)
    assert bounds==(-1122,-1122,1123,1123)
    def raster(b):
        xx,zz=np.meshgrid(np.arange(b[0],b[2],8),np.arange(b[1],b[3],8))
        radius=np.hypot(xx,zz)
        height=np.where((radius>=500)&(radius<=620),250.,180.)
        return Raster(b,8,height,water=np.zeros(height.shape,bool))
    before=evaluate_v2(raster((-636,-636,637,637)),(0,0))
    after=evaluate_v2(raster(bounds),(0,0))
    assert not before['border_fit']['complete']
    assert after['geometry_pass'] and after['border_fit']['complete']


def test_region_includes_oversized_footprint_and_can_cross_realm_boundary():
    r={'center':[1340,-1340],'border_fit':{'footprint':[1200,-1400,3100,-1100]}}
    b=verification_region(r,'v1',{'terrain':{}},16)
    assert b[2]>=3116 and b[1]<-1344
    assert b[2]>1344  # Analysis coverage does not alter mandatory membership.
    assert verification_region({'center':[0,0]},'v1',{},16) is None
    with pytest.raises(ValueError):verification_region(r,'v2',{},True)


def test_default_selection_advances_past_cached_top_without_budget_charge(tmp_path):
    store,cfg,adapter=prepared(tmp_path)
    try:
        save_cached(store,cfg,adapter,0)
        store.set_state('bds_verification_used',1)
        selected,policy=select_verification(store,'v1',cfg,top=2,adapter=adapter,require_footprint=True)
        assert [w['candidate_id'] for w,_,_ in selected]==['1:1:0','1:2:0']
        assert policy['new_attempt_selections']==2 and policy['cached_reviews']==0
        assert store.get_state('bds_verification_used')==1
    finally:store.close()


def test_exhausted_budget_still_allows_explicit_cached_review(tmp_path):
    store,cfg,adapter=prepared(tmp_path)
    try:
        save_cached(store,cfg,adapter,0)
        store.set_state('bds_verification_used',8)
        assert select_verification(store,'v1',cfg,adapter=adapter)[0]==[]
        selected,policy=select_verification(store,'v1',cfg,adapter=adapter,include_cached=True)
        assert len(selected)==1 and selected[0][0]['verification_cached']
        assert policy['new_attempt_selections']==0 and policy['cached_reviews']==1
        assert store.get_state('bds_verification_used')==8
    finally:store.close()


def test_failed_observation_retries_only_when_requested_and_budget_available(tmp_path):
    store,cfg,adapter=prepared(tmp_path)
    try:
        save_cached(store,cfg,adapter,0,'FAILED')
        store.set_state('bds_verification_used',1)
        assert select_verification(store,'v1',cfg,adapter=adapter)[0][0][0]['candidate_id']=='1:1:0'
        selected,_=select_verification(store,'v1',cfg,adapter=adapter,retry_failed=True)
        assert selected[0][0]['candidate_id']=='1:0:0'
        assert selected[0][0]['verification_retry'] and not selected[0][0]['verification_cached']
    finally:store.close()


def test_random_new_and_cached_strata_keep_correct_inclusion_probabilities(tmp_path):
    store,cfg,adapter=prepared(tmp_path)
    try:
        save_cached(store,cfg,adapter,0);save_cached(store,cfg,adapter,1)
        store.set_state('bds_verification_used',7)
        selected,policy=select_verification(store,'v1',cfg,adapter=adapter,top=0,random_count=3,
                                            include_cached=True,sampling_key=17)
        assert len(selected)==3
        assert policy['new_attempt_selections']==1 and policy['cached_reviews']==2
        assert policy['random_unselected_population']==9 and policy['random_cached_population']==2
        assert [p for w,_,p in selected if not w['verification_cached']]==[1/9]
        assert [p for w,_,p in selected if w['verification_cached']]==[1.,1.]
    finally:store.close()


def test_cli_retry_flag_and_full_planned_bounds_reach_adapter(tmp_path,monkeypatch,capsys):
    from seed_search.realm.cli import main
    store,cfg,adapter=prepared(tmp_path)
    save_cached(store,cfg,adapter,0,'FAILED')
    store.set_state('bds_verification_used',1);store.close()
    calls=[]
    def fake_verify(self,candidate,**kwargs):
        calls.append((candidate['id'],kwargs))
        return {'id':'mock-retry','status':'FAILED','reason':'Injected test failure'}
    monkeypatch.setattr(VerificationAdapter,'verify_candidate',fake_verify)
    result=main(['verify-terrain','--run',str(tmp_path),'--variant','v1','--retry-failed'])
    assert result['selected']==1 and calls[0][0]=='1:0:0'
    assert calls[0][1]['retry_failed'] is True
    assert calls[0][1]['bounds']==[-1432,-1432,1433,1433]


def test_cli_can_review_cached_failures_with_exhausted_budget(tmp_path,monkeypatch,capsys):
    from seed_search.realm.cli import main
    store,cfg,adapter=prepared(tmp_path)
    save_cached(store,cfg,adapter,0,'FAILED')
    store.set_state('bds_verification_used',8);store.close()
    monkeypatch.setattr(VerificationAdapter,'_extract',lambda *a:pytest.fail('Cached review launched BDS'))
    result=main(['verify-terrain','--run',str(tmp_path),'--variant','v1','--include-cached'])
    assert result['selected']==1
    assert result['observations'][0]['status']=='FAILED'
    assert result['selection_policy']['new_attempt_selections']==0


def test_missing_top_footprint_does_not_block_later_measurable_result(tmp_path):
    store,cfg,adapter=prepared(tmp_path)
    try:
        row=store.get_variant('1:0:0','v1',[0,0]);row['result']['border_fit'].pop('footprint')
        store.upsert_variant('1:0:0','v1',[0,0],row['result'])
        selected,_=select_verification(store,'v1',cfg,adapter=adapter,require_footprint=True)
        assert selected[0][0]['candidate_id']=='1:1:0'
    finally:store.close()


def test_coastal_2048_footprint_supported():
    cfg = {'terrain': {'variants': ['v1'], 'v1': {'mode': 'coastal_continent', 'square_side_blocks': 2048}}}
    prediction = {'center': [100, -200], 'border_fit': {'footprint': [-924, -1224, 1124, 824]}}
    bounds = verification_region(prediction, 'v1', cfg, 16)
    assert bounds == (-924, -1224, 1124, 824)
    # Also works when derived from candidate bounds
    cand = {'center': [100, -200], 'bounds': {'overworld': [-924, -1224, 1124, 824]}}
    assert verification_region(cand, 'v1', {'terrain': {'variants': ['v1'], 'v1': {'mode': 'coastal_continent'}}}, 16) == (-924, -1224, 1124, 824)
