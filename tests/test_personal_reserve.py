"""Independent sorting, durable resume and presentation contracts for 2K screening."""
import json
import sqlite3
from types import SimpleNamespace
import pytest
from seed_search.realm.reserve import selection_policy, resume_policy
from seed_search.realm.top_tracker import Top50Tracker


def record(seed, score, x=0):
    return dict(seed=str(seed),anchors=[dict(id=f'{seed}:{x}',seed=str(seed),ranking_tier=0,
        baseline_score_observed=score,unmet_requirements=0,radial_key=0,
        origin_distance_squared=x*x,evaluation_center=[x,0])])


def oracle(records):
    best={}
    def key(r):
        a=r['anchors'][0]
        return (-a['baseline_score_observed'],a['origin_distance_squared'],a['evaluation_center'][0],a['id'])
    for r in records:
        if r['seed'] not in best or key(r)<key(best[r['seed']]):best[r['seed']]=r
    return sorted(best.values(),key=key)


def test_tracker_reserve_fullsort_dedup_ties_and_delayed_cutoff(tmp_path):
    policy=selection_policy(5); t=Top50Tracker(capacity=10,winner_limit=5,reserve_policy=policy)
    rows=[record(i,(i*17)%41,i%3) for i in range(60)]
    rows += [record(3,90),record(3,89)]
    for i,r in enumerate(rows):
        t.observe(r)
        if i<9:assert t.cutoff_score() is None
    assert t.top_records()==oracle(rows)[:10]
    t.save_to_json(str(tmp_path/'top50.json'))
    assert json.loads((tmp_path/'top50.json').read_text())==oracle(rows)[:5]
    assert json.loads((tmp_path/'reserves.json').read_text())==oracle(rows)[5:10]
    with sqlite3.connect(tmp_path/'test.sqlite') as db:
        t.flush(db)
        assert db.execute('select count(*) from top_candidates').fetchone()[0]==10
    old=Top50Tracker(capacity=5)
    for r in rows:old.observe(r)
    assert old.top_records()==t.top_records()[:5]


def test_policy_bounds_disabled_and_legacy_resume(tmp_path):
    assert selection_policy(0)['candidate_capacity']==0
    assert selection_policy(50)['candidate_capacity']==100
    with pytest.raises(ValueError,match='bound'):selection_policy(501)
    with sqlite3.connect(tmp_path/'realm.sqlite') as db:
        db.execute('create table meta(key text primary key,value text)')
        db.executemany('insert into meta values (?,?)',[('identity','{}'),('native_pipeline',json.dumps(dict(top_k=50)))])
    policy,bind=resume_policy(tmp_path,50,True)
    assert not bind and policy['candidate_capacity']==50 and not policy['historically_complete']
    with pytest.raises(ValueError,match='change'):resume_policy(tmp_path,51,True)


def test_pipeline_synthetic_resume_rebuilds_caches(tmp_path):
    from test_blueprint_batch_prototype import FixtureBackend
    from seed_search.realm.blueprint import evaluate_seed
    from seed_search.realm.config import blueprint_config
    from seed_search.realm.native_batch import persist_pipeline
    cfg=blueprint_config();cfg['search']['sequence']='sequential'
    class Batch:
        native_seconds=0
        def __init__(self,seeds):self.seeds=seeds
        def __enter__(self):return self
        def __exit__(self,*_):pass
        def close(self):pass
        def records(self,first):
            return [evaluate_seed(first+i,s,cfg,backend_factory=lambda _,s=s:FixtureBackend((s%8*16,0,-1)),short_circuit=False) for i,s in enumerate(self.seeds)]
    class Proto:
        identity={'synthetic':True};policy=SimpleNamespace(max_buffer_bytes=1024)
        def sweep(self,seeds,threads,**kwargs):return Batch(seeds)
    proto=Proto();proto.cfg=cfg
    out=persist_pipeline(proto,tmp_path,16,threads=1,batch_size=2,encoded=False,stop_after=8,top_k=2)
    assert out['candidate_policy']['candidate_capacity']==4
    assert len(out['top_tracker'])==4
    for name in ('top50.json','reserves.json'):(tmp_path/name).write_text('corrupt')
    out=persist_pipeline(proto,tmp_path,16,threads=1,batch_size=2,encoded=False,resume=True,top_k=2)
    assert len(json.loads((tmp_path/'top50.json').read_text()))==2
    assert len(json.loads((tmp_path/'reserves.json').read_text()))==2
    with sqlite3.connect(tmp_path/'realm.sqlite') as db:
        assert json.loads(db.execute("select value from meta where key='identity'").fetchone()[0])['top_selection']['candidate_capacity']==4
        assert db.execute('select count(*) from top_candidates').fetchone()[0]==4
    from seed_search.web.server import SweepManager
    primary=SweepManager._read_candidate_page(None,tmp_path,'fixture',1,view='primary')
    reserve=SweepManager._read_candidate_page(None,tmp_path,'fixture',1,view='reserve')
    assert primary['total']==reserve['total']==2
    assert primary['primary_count']==reserve['reserve_count']==2
    assert len(primary['candidates'])==len(reserve['candidates'])==2
    assert not ({c['seed'] for c in primary['candidates']}&{c['seed'] for c in reserve['candidates']})
    with pytest.raises(ValueError,match='change'):
        persist_pipeline(proto,tmp_path,16,threads=1,batch_size=2,encoded=False,resume=True,top_k=3)


def test_pruned_pipeline_retains_two_k_against_unpruned_fullsort(tmp_path):
    from test_blueprint_batch_prototype import FixtureBackend
    from seed_search.realm.blueprint import evaluate_seed
    from seed_search.realm.config import blueprint_config
    from seed_search.realm.native_batch import persist_pipeline
    cfg=blueprint_config();cfg['search']['sequence']='sequential'
    all_rows=[];cutoffs=[]
    for i in range(32):
        r=evaluate_seed(i,i,cfg,backend_factory=lambda _,i=i:FixtureBackend((i%8*16,0,-1)),short_circuit=False)
        # Deliberate synthetic score/tie stream. Tests selection plumbing, not scoring.
        for a in r['anchors']:
            a['baseline_score_observed']=100+(i*17)%41;a['ranking_tier']=0
        all_rows.append(r)
    class Batch:
        native_seconds=0
        def __init__(self,seeds,cutoff):self.seeds=seeds;self.cutoff=cutoff
        def __enter__(self):return self
        def __exit__(self,*_):pass
        def close(self):pass
        def records(self,first):
            import copy
            rows=copy.deepcopy([all_rows[s] for s in self.seeds])
            for r in rows:
                if self.cutoff is not None:r['anchors']=[a for a in r['anchors'] if a['baseline_score_observed']>=self.cutoff]
            return rows
    class Proto:
        identity={'synthetic-pruning-fixture':True};policy=SimpleNamespace(max_buffer_bytes=1024)
        def sweep(self,seeds,threads,**kw):
            cutoff=kw.get('cutoff_score');cutoffs.append((min(seeds),cutoff));return Batch(seeds,cutoff)
    proto=Proto();proto.cfg=cfg
    result=persist_pipeline(proto,tmp_path,32,threads=1,batch_size=1,encoded=False,top_k=2)
    def key(r):
        a=r['anchors'][0]
        return (a.get('ranking_tier',0),-a['baseline_score_observed'],a.get('unmet_requirements',0),a.get('radial_key',0),a.get('origin_distance_squared',0),*a.get('evaluation_center',a['stronghold']),a['id'])
    expected=sorted(all_rows,key=key)[:4]
    assert [r['seed'] for r in result['top_tracker'].top_records()]==[r['seed'] for r in expected]
    assert len(json.loads((tmp_path/'top50.json').read_text()))==2
    assert len(json.loads((tmp_path/'reserves.json').read_text()))==2
    assert all(c is None for i,c in cutoffs if i<4)
    assert any(c is not None for _,c in cutoffs)
