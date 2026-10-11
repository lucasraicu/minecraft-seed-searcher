import sqlite3
import threading

import pytest

from seed_search.realm.baseline import evaluate_seed
from seed_search.realm.bounds import json_bounds,nether_square
from seed_search.realm.config import default_config
from seed_search.realm.recovery import import_positive
from seed_search.realm.store import RealmStore
from seed_search.realm.verification import pinned_world_settings
from test_realm_baseline import FakeBackend


class Missing(FakeBackend):
    def structure_pair(self,name,bounds):
        if name in ('stronghold','bastion'):return [],[]
        return super().structure_pair(name,bounds)


def setup(path):
    cfg=default_config();store=RealmStore(path,{'config':cfg})
    store.configure_range(0,1,1);store.claim_range('baseline')
    store.complete_range(0,1,[evaluate_seed(0,42,cfg,backend_factory=Missing)])
    return store,cfg


def evidence(cfg,kind,points,bounds):
    return {'seed':'42','structure':kind,'actual':True,'verification':'VERIFIED','confirmed_absent':False,
            'source':{'kind':'actual_generation','provider':'synthetic_control','target_version':'26.52','version':'26.52'},
            'anchor_convention':'stronghold_stairway_block_xz' if kind=='stronghold' else 'structure_start_block_xz',
            'coordinates':points,'bounds':json_bounds(bounds),'world_settings':pinned_world_settings(),
            'artifact':'synthetic:positive-import-control','artifact_sha256':'a'*64,
            'complete':False,'coverage_complete':False}


def test_partial_positive_adds_independent_anchors_without_closing_recall_or_input_coverage(tmp_path):
    store,cfg=setup(tmp_path)
    with store:
        original=list(store.iter_results());digest=store.db.execute('SELECT digest FROM ranges').fetchone()[0]
        old_pool=store.ensure_terrain_pool({'provider':'control'})
        result=import_positive(store,0,evidence(cfg,'stronghold',[[-1,-9],[1999,1999]],cfg['discovery']['overworld_bounds']),backend_factory=Missing)
        assert result['added_candidates']==['42:-1:-9','42:1999:1999']
        assert store.get_state('recovered_stronghold_anchors')==2
        assert store.status()['completed_seeds']==1 and store.status()['discovery_tasks']=={'pending':2}
        assert store.status()['variant_tasks']=={'v1:pending':2,'v2:pending':2}
        assert list(store.iter_results())==original
        assert store.db.execute('SELECT digest FROM ranges').fetchone()[0]==digest
        assert store.get_terrain_pool(old_pool)['members']==0
        first=store.get_candidate('42:-1:-9')
        assert first['bounds']['final_nether']==json_bounds(nether_square((-1,-9)))
        assert first['qualification']=='PENDING' and 'final_bastion' in first['pending_reasons']
        assert first['required_structures']['stronghold']['actual_presence']=='VERIFIED_POSITIVE'
        assert first['final_nether_status']=='UNVERIFIED' and first['actual_recovery']['discovery_recall']=='UNRESOLVED'


def test_actual_bastion_can_recover_provisional_eligibility_and_restart_is_idempotent(tmp_path):
    store,cfg=setup(tmp_path);proof=evidence(cfg,'stronghold',[[-1,-9]],cfg['discovery']['overworld_bounds'])
    with store:import_positive(store,0,proof,backend_factory=Missing)
    with RealmStore(tmp_path,resume=True) as store:
        def no_generation(seed):raise AssertionError('Repeated proof regenerated an anchor')
        assert import_positive(store,0,proof,backend_factory=no_generation)['replayed']
        c=store.get_candidate('42:-1:-9')
        result=import_positive(store,0,evidence(cfg,'bastion',[[0,0]],c['bounds']['final_nether']),candidate_id=c['id'],backend_factory=Missing)
        assert result['terrain_pool_refresh_required']
        c=store.get_candidate(c['id'])
        assert c['qualification']=='PREDICTED' and c['pending_reasons']==[]
        assert c['required_nether_structures']['bastion']['actual_presence']=='VERIFIED_POSITIVE'
        assert c['final_nether_status']=='UNVERIFIED' and not c['final_nether_prediction']['actual_generation_verified']
        assert store.db.execute("SELECT count(*) FROM observations WHERE json_extract(result,'$.kind')='pre_actual_recovery'").fetchone()[0]==1
        new_pool=store.ensure_terrain_pool({'provider':'control'},new_revision=True)
        assert store.get_terrain_pool(new_pool)['members']==1
        assert store.status()['completed_seeds']==1


@pytest.mark.parametrize('field,value',[('seed','43'),('bounds',[-1,-1,1,1]),('actual',False),
                                      ('anchor_convention','nearest_query'),('artifact_sha256','bad'),
                                      ('world_settings',{}),('coordinates',[[2000,0]])])
def test_wrong_identity_or_boundary_cannot_invent_covered_anchors(tmp_path,field,value):
    store,cfg=setup(tmp_path)
    with store:
        proof=evidence(cfg,'stronghold',[[0,0]],cfg['discovery']['overworld_bounds']);proof[field]=value
        with pytest.raises(ValueError):import_positive(store,0,proof,backend_factory=Missing)
        assert store.status()['candidate_counts']=={} and store.status()['completed_seeds']==1
        assert store.db.execute('SELECT count(*) FROM observations').fetchone()[0]==0


def test_import_failure_rolls_back_anchors_proofs_and_both_variant_tasks(tmp_path):
    store,cfg=setup(tmp_path)
    with store:
        store.db.execute("CREATE TRIGGER reject_variant BEFORE INSERT ON variant_tasks WHEN NEW.variant='v2' BEGIN SELECT RAISE(ABORT,'injected'); END")
        with pytest.raises(sqlite3.IntegrityError,match='injected'):
            import_positive(store,0,evidence(cfg,'stronghold',[[1,2]],cfg['discovery']['overworld_bounds']),backend_factory=Missing)
        assert store.status()['candidate_counts']=={} and store.status()['variant_tasks']=={}
        assert store.db.execute('SELECT count(*) FROM observations').fetchone()[0]==0
        assert store.get_state('recovered_stronghold_anchors') is None


def test_final_square_rejects_actual_start_outside_fractional_east_edge(tmp_path):
    store,cfg=setup(tmp_path)
    with store:
        import_positive(store,0,evidence(cfg,'stronghold',[[-1,-9]],cfg['discovery']['overworld_bounds']),backend_factory=Missing)
        c=store.get_candidate('42:-1:-9')
        with pytest.raises(ValueError):
            import_positive(store,0,evidence(cfg,'bastion',[[512,0]],c['bounds']['final_nether']),candidate_id=c['id'],backend_factory=Missing)
        assert store.get_candidate(c['id'])==c


def test_uncovered_index_and_caller_transaction_remain_unchanged(tmp_path):
    store,cfg=setup(tmp_path)
    with store:
        proof=evidence(cfg,'stronghold',[[0,0]],cfg['discovery']['overworld_bounds'])
        with pytest.raises(ValueError,match='completed input'):import_positive(store,1,proof,backend_factory=Missing)
        store.db.execute("INSERT INTO meta VALUES ('caller','true')")
        with pytest.raises(ValueError,match='caller transaction'):import_positive(store,0,proof,backend_factory=Missing)
        assert store.db.in_transaction and store.get_state('caller') is True
        store.db.rollback()
        assert store.get_state('caller') is None and store.status()['candidate_counts']=={}


def test_concurrent_positive_imports_preserve_both_proofs_and_actual_starts(tmp_path):
    store,cfg=setup(tmp_path)
    with store:
        import_positive(store,0,evidence(cfg,'stronghold',[[-1,-9]],cfg['discovery']['overworld_bounds']),backend_factory=Missing)
        bounds=store.get_candidate('42:-1:-9')['bounds']['overworld']
    entered=threading.Event();second_started=threading.Event();release=threading.Event();outcomes={}
    class Waiting(Missing):
        def __enter__(self):
            entered.set();assert release.wait(5);return self
    def run(kind,factory):
        try:
            with RealmStore(tmp_path,resume=True) as s:
                if kind=='ancient_city':
                    s.db.set_trace_callback(lambda sql:second_started.set() if sql=='BEGIN IMMEDIATE' else None)
                outcomes[kind]=import_positive(s,0,evidence(cfg,kind,[[0,0]],bounds),candidate_id='42:-1:-9',backend_factory=factory)
        except BaseException as exc:outcomes[kind]=exc
    first=threading.Thread(target=run,args=('village',Waiting));second=threading.Thread(target=run,args=('ancient_city',Missing))
    first.start()
    try:
        assert entered.wait(5);second.start();assert second_started.wait(5)
    finally:
        release.set();first.join(5)
        if second.ident is not None:second.join(5)
    assert not first.is_alive() and not second.is_alive()
    assert all(isinstance(r,dict) for r in outcomes.values()),outcomes
    with RealmStore(tmp_path,resume=True) as s:
        c=s.get_candidate('42:-1:-9')
        assert set(c['actual_required_structure_evidence'])=={'stronghold','village','ancient_city'}
        assert s.status()['completed_seeds']==1 and s.get_state('recovered_stronghold_anchors')==1


def test_import_blocks_stale_scores_and_resumes_the_saved_rescore_policy(tmp_path):
    from seed_search.realm.reports import rescore,ranked
    store,cfg=setup(tmp_path)
    with store:
        import_positive(store,0,evidence(cfg,'stronghold',[[-1,-9]],cfg['discovery']['overworld_bounds']),backend_factory=Missing)
        rescore(store,cfg)
        c=store.get_candidate('42:-1:-9');proof=evidence(cfg,'bastion',[[0,0]],c['bounds']['final_nether'])
        result=import_positive(store,0,proof,candidate_id=c['id'],backend_factory=Missing)
        assert result['rescore_required'] and store.get_state('rescore_revision')['status']=='running'
        with pytest.raises(ValueError,match='Incomplete score'):ranked(store)
        assert import_positive(store,0,proof,candidate_id=c['id'],backend_factory=Missing)['replayed']
        rescore(store,store.get_state('rescore_revision')['policy'])
        assert ranked(store)[0]['qualification']=='PREDICTED'
