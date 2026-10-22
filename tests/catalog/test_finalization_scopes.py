import copy
import pytest
from seed_search.catalog.finalization import advance_finalization,evidence_identity,make_evidence_receipt


def candidate(i,**changes):
    return dict(world_id=f'{i:064x}',seed=str(i),anchor=[0,0],border_side=2048,dimension='overworld',profile='presence-v3',
        build_id='1.26.52.3',world_settings_id='default',source_observation_id='b'*64,provider_id='c'*64,
        evidence_policy='actual_scoped_conditions_v1',requirements={'feature':'biome.exact.forest'},**changes)


def scope(c):
    return evidence_identity(c['seed'],anchor=c['anchor'],border=c['border_side'],dimension=c['dimension'],profile=c['profile'],build_id=c['build_id'],requirements=c['requirements'],world_settings_id=c['world_settings_id'],source_observation_id=c['source_observation_id'],provider_id=c['provider_id'],evidence_policy=c['evidence_policy'])[1]


def receipt(c,eid,status='pass'):
    return make_evidence_receipt(eid,c['world_id'],c['seed'],status,details=dict(actual=True,source='actual',provider='official BDS 1.26.52.3',scope=scope(c),requirements_complete=True,evidence_artifacts=['d'*64]))


def test_promotion_frozen_order_and_cached_actual_evidence():
    rows=[candidate(i) for i in range(1,5)]
    def verify(c,eid):return receipt(c,eid,'fail' if c['seed']=='1' else 'pass')
    r=advance_finalization('obj',rows,2,{},verifier=verify,budget=4)
    assert r['verified_count']==2 and [c['seed'] for c in r['promoted']]==['3']
    assert r['checks_performed']==3
    reused=advance_finalization('obj',rows,2,r['receipts'],budget=0,previous=r['progress'])
    assert reused['verified_count']==2 and reused['checks_performed']==0
    with pytest.raises(ValueError,match='Frozen'):advance_finalization('obj',list(reversed(rows)),2,r['receipts'],previous=r['progress'])


def test_scoped_failure_does_not_blacklist_and_bare_prediction_never_verifies():
    a=candidate(1);a['requirements']={'feature':'biome.exact.desert'}
    failed=advance_finalization('a',[a],1,{},verifier=lambda c,e:receipt(c,e,'fail'),budget=1)
    b=candidate(1)
    good=advance_finalization('b',[b],1,failed['receipts'],verifier=receipt,budget=1)
    assert good['verified_count']==1 and good['checks_performed']==1
    fake=advance_finalization('b',[b],1,{},verifier=lambda c,e:'pass',budget=1)
    assert fake['verified_count']==0 and len(fake['pending'])==1


def test_wrong_identity_incomplete_scope_and_prediction_proof_rejected():
    c=candidate(1);bad=receipt(c,'f'*64)
    r=advance_finalization('a',[c],1,{},verifier=lambda c,e:bad,budget=1)
    assert r['verified_count']==0
    for field in ('provider_id','source_observation_id','requirements','build_id'):
        partial=dict(c);partial.pop(field)
        r=advance_finalization('a',[partial],1,{},verifier=lambda c,e:'pass',budget=1)
        assert r['checks_performed']==0 and r['verified_count']==0
    def predicted(c,e):
        r=receipt(c,e);r['details']['actual']=False;return r
    assert advance_finalization('a',[c],1,{},verifier=predicted,budget=1)['verified_count']==0


def test_distinct_seed_and_error_budget_retry():
    c=candidate(1);rows=[c,copy.deepcopy(c),candidate(2),candidate(3)]
    r=advance_finalization('a',rows,2,{},verifier=receipt,budget=2)
    assert r['verified_count']==2 and r['checks_performed']==2
    def raises(c,e):raise RuntimeError('inconclusive')
    r=advance_finalization('a',[c,candidate(2)],1,{},verifier=raises,budget=1)
    assert r['checks_performed']==1 and r['verified_count']==0
    retried=advance_finalization('a',[c,candidate(2)],1,r['receipts'],verifier=receipt,budget=1,retry_pending=True)
    assert retried['verified_count']==1 and retried['checks_performed']==1
    for budget in (-1,True,None):
        with pytest.raises(ValueError):advance_finalization('a',[c],1,{},verifier=receipt,budget=budget)
