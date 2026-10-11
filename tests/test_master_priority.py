import copy
from seed_search.realm.store import RealmStore
from seed_search.realm.terrain import run_terrain
from test_realm_terrain_work_store import setup_store,payload,observation
from test_realm_terrain_work import checkpoint,controls,Provider,CFG,IDENTITY


def test_ranked_oldest_cycle_variant_alternation_and_restart(tmp_path):
    store,revision=setup_store(tmp_path)
    try:
        ids={v:[] for v in ('v1','v2')}
        for v in ids:
            for i in range(6):
                p={**payload(center=(i,2),priority=i),'coarse_score':i*20}
                ids[v].append(store.ensure_terrain_work(revision,'0:1:2',v,p))
        selected=[]
        for slot in range(8):
            u=store.claim_priority_terrain(revision,('v1','v2'),'owner',str(slot))
            selected.append((u['variant'],u['unit_id']))
            store.complete_terrain_work(u['unit_id'],observation=observation(u))
            if slot==3:
                store.close();store=RealmStore(tmp_path,resume=True)
        assert [v for v,uid in selected]==['v1','v2']*4
        assert [uid for v,uid in selected if v=='v1']==[ids['v1'][i] for i in (5,4,3,0)]
        assert [uid for v,uid in selected if v=='v2']==[ids['v2'][i] for i in (5,4,3,0)]
        assert store.get_state(f'terrain_priority_cycle:{revision}')['dispatches']==8
    finally:store.close()


def test_claim_cycle_rolls_back_with_failed_lease_and_failed_units_are_retained(tmp_path):
    import sqlite3
    import pytest
    store,revision=setup_store(tmp_path)
    with store:
        uid=store.ensure_terrain_work(revision,'0:1:2','v1',payload())
        store.db.execute("CREATE TRIGGER reject_lease BEFORE UPDATE ON terrain_work BEGIN SELECT RAISE(ABORT,'injected'); END")
        with pytest.raises(sqlite3.IntegrityError):store.claim_priority_terrain(revision,('v1',),'owner','first')
        assert store.get_state(f'terrain_priority_cycle:{revision}') is None
        assert store.get_terrain_work(uid)['status']=='pending'
        store.db.execute('DROP TRIGGER reject_lease')
        for n in range(3):
            u=store.claim_priority_terrain(revision,('v1',),'owner',str(n))
            store.defer_terrain_work(uid,result={'sampling_failure':'test'},expected_attempt=u['attempts'],worker='owner')
            assert store.claim_priority_terrain(revision,('v1',),'owner',str(n)) is None
        assert store.claim_priority_terrain(revision,('v1',),'owner','next') is None
        assert store.get_terrain_work(uid)['status']=='deferred'
        assert store.claim_priority_terrain(revision,('v1',),'owner','manual',continue_manual=True)['attempts']==4


def test_priority_terrain_stages_and_resume_match_rotation(tmp_path,monkeypatch):
    controls(monkeypatch,centers=((0,0),(64,0),(128,0)))
    outputs=[]
    for mode in ('rotation','priority'):
        store,candidate=checkpoint(tmp_path/mode,count=2);provider=Provider()
        cfg=copy.deepcopy(CFG);cfg['terrain']['scheduler']=mode
        try:
            if mode=='priority':
                first=run_terrain(store,cfg,('v1','v2'),limit=1,provider_factory=lambda seed:provider,provider_identity=IDENTITY)
                assert first['work_completed']==1
                revision=first['pool_revision']
                assert store.terrain_work_counts(revision).get('leased',0)==0
            first=run_terrain(store,cfg,('v1','v2'),provider_factory=lambda seed:provider,provider_identity=IDENTITY)
            revision=first['pool_revision']
            assert store.terrain_work_counts(revision).get('pending',0)==8
            for _ in range(2):run_terrain(store,cfg,('v1','v2'),provider_factory=lambda seed:provider,provider_identity=IDENTITY)
            rows=list(store.iter_variants())
            for row in rows:
                row['result'].pop('sampling_schedule',None)
            outputs.append(rows)
            revision=store.get_state('terrain_pool_revision')
            assert store.terrain_work_counts(revision).get('pending',0)==0
            assert store.terrain_work_counts(revision).get('leased',0)==0
        finally:store.close()
    assert outputs[0]==outputs[1]
