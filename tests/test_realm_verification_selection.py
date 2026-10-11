import json
from seed_search.realm.cli import select_verification
from seed_search.realm.config import default_config
from seed_search.realm.store import RealmStore, canonical


def pool(tmp_path):
    cfg=default_config();cfg['bds']['verification_budget']=8
    store=RealmStore(tmp_path,{'config':cfg})
    for index in range(12):
        cid=f'1:{index}:0';qualification='PENDING' if index==11 else 'PREDICTED'
        candidate={'id':cid,'seed':'1','stronghold':[index,0],'qualification':qualification}
        store.db.execute('INSERT INTO candidates VALUES (?,?,?,?,?)',(cid,str(index),'1',qualification,canonical(candidate)))
        result={'evidence':'PREDICTED','geometry_pass':True,'geometry_score':80,'score':100-index,
                'metrics':{'diameter':400},'border_fit':{'state':'within'}}
        if index==2:result['metrics']['diameter']=250
        if index==3:result['border_fit']['state']='outside'
        if index==11:result['score']=999;result['metrics']['diameter']=250;result['border_fit']['state']='outside'
        store.upsert_variant(cid,'v1',[index,0],result)
    return store,cfg


def test_categories_deduplicate_and_random_conditional_probability(tmp_path):
    store,cfg=pool(tmp_path)
    try:
        picks,policy=select_verification(store,'v1',cfg,top=1,borderline=1,unusual=1,random_count=2,sampling_key=42)
        assert [r for _,r,_ in picks[:3]]==['top','borderline','unusual']
        assert [w['candidate_id'] for w,_,_ in picks[:3]]==['1:0:0','1:2:0','1:3:0']
        assert len({w['candidate_id'] for w,_,_ in picks})==5
        assert all(w['candidate_id']!='1:11:0' for w,_,_ in picks)
        assert policy['random_unselected_population']==8
        assert [p for _,r,p in picks if r=='random_low_rank']==[.25,.25]
        again,_=select_verification(store,'v1',cfg,top=1,borderline=1,unusual=1,random_count=2,sampling_key=42)
        assert picks==again
    finally:store.close()


def test_remaining_budget_caps_every_selection(tmp_path):
    store,cfg=pool(tmp_path)
    try:
        store.set_state('bds_verification_used',6)
        picks,policy=select_verification(store,'v1',cfg,top=1,borderline=5,unusual=8,random_count=20)
        assert len(picks)==2 and [r for _,r,_ in picks]==['top','borderline']
        store.set_state('bds_verification_used',8)
        assert select_verification(store,'v1',cfg,random_count=3)[0]==[]
    finally:store.close()


def test_cli_persists_selection_reasons_without_generation(tmp_path,monkeypatch,capsys):
    from seed_search.realm.cli import main
    from seed_search.realm.verification import VerificationAdapter
    store,cfg=pool(tmp_path)
    store.close()
    def forbidden(*args,**kwargs):
        raise AssertionError('No footprint must not launch generation')
    monkeypatch.setattr(VerificationAdapter,'verify_candidate',forbidden)
    result=main(['verify-terrain','--run',str(tmp_path),'--variant','v1','--top','0',
                 '--borderline','1','--unusual','1','--random','2','--sampling-key','7'])
    # Missing analysis footprints cannot use new-attempt selection slots or
    # prevent a later measurable candidate from advancing through the backlog.
    assert result['selected']==0
    assert result['selection_policy']['eligibility_scan_visits']['missing_footprint_visits']>0
    with RealmStore(tmp_path,resume=True) as saved:
        selections=[r for r in saved.iter_observations() if r.get('kind')=='verification_selection']
        assert selections==[]
        assert saved.get_state('bds_verification_used') is None


def test_invalid_selection_counts_rejected(tmp_path):
    import pytest
    store,cfg=pool(tmp_path)
    try:
        for values in ({'top':-1},{'borderline':True},{'unusual':1.5},{'random_count':-1}):
            with pytest.raises(ValueError,match='nonnegative integers'):
                select_verification(store,'v1',cfg,**values)
    finally:store.close()
