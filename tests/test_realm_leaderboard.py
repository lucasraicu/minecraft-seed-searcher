"""Indexed live ranking, honest near-miss scores and atomic legacy migration."""
import csv
import json
import sqlite3
import pytest
from seed_search.realm.store import RealmStore,canonical
from seed_search.realm.reports import ranked,export
from seed_search.realm.leaderboard import ORDER
from test_realm_store import result


def populate(path):
    s=RealmStore(path,{'retention':{'mode':'full','max_misses':0}})
    s.configure_range(0,4,4);s.claim_range('test')
    records=[result(i) for i in range(4)]
    for i,r in enumerate(records):
        for j,a in enumerate(r['anchors']):
            a.update(baseline_score_complete=j==0,baseline_score=20+i if j==0 else None,
                     baseline_score_observed=400+i,baseline_score_uncertainty={'prediction_score_interval':[10,30]})
            if j:
                a['retention']={'classification':'NEAR_MISS','unmet_requirements':1+i%2}
    s.complete_range(0,4,records)
    return s,records


def test_complete_candidates_then_misses_then_score_and_index(tmp_path):
    s,records=populate(tmp_path)
    try:
        rows=ranked(s)
        assert [r['smart_score'] for r in rows]==[23,22,21,20,402,400,403,401]
        assert all(r['qualification']=='PREDICTED' for r in rows[:4])
        assert [r['unmet_requirements'] for r in rows[4:]]==[1,1,2,2]
        assert all(r['baseline_score'] is None and 'partial' in r['ranking_view'] for r in rows[4:])
        plan=[r[3] for r in s.db.execute(f'EXPLAIN QUERY PLAN SELECT result,smart_score FROM candidate_leaderboard_view ORDER BY {ORDER} LIMIT 20')]
        assert any('candidate_leaderboard' in r for r in plan)
        assert not any('TEMP B-TREE' in r for r in plan)
        # Live score changes update the index without changing coverage/digests.
        digest=s.db.execute('SELECT digest FROM ranges').fetchone()[0]
        c=rows[3];s.upsert_candidate({'id':c['id'],'baseline_score':100})
        assert ranked(s)[0]['id']==c['id']
        assert s.db.execute('SELECT digest FROM ranges').fetchone()[0]==digest
        assert not s.complete_range(0,4,records)
        assert ranked(s,limit=1)[0]['smart_score']==100
    finally:s.close()


def test_legacy_migration_exports_snapshot_and_rollback(tmp_path):
    s,_=populate(tmp_path/'run')
    before=list(s.db.execute('SELECT id,result FROM candidates ORDER BY id'))
    s.db.executescript('DROP VIEW candidate_leaderboard_view; DROP INDEX candidate_leaderboard;')
    s.close()
    with RealmStore(tmp_path/'run',resume=True) as s:
        assert list(s.db.execute('SELECT id,result FROM candidates ORDER BY id'))==before
        first=ranked(s)[0]
        other=sqlite3.connect(s.run/'realm.sqlite');other.execute('BEGIN IMMEDIATE')
        changed={**first,'baseline_score':999};other.execute('UPDATE candidates SET result=? WHERE id=?',(canonical(changed),first['id']))
        assert ranked(s)[0]['smart_score']==23
        # Opening a live reader must not acquire the scanner's write lock once
        # the additive schema is installed.
        with RealmStore(tmp_path/'run',resume=True) as live:
            assert ranked(live)[0]['smart_score']==23
        other.rollback();other.close()
        export(s)
        saved=[json.loads(line) for line in (s.run/'results/baseline.jsonl').read_text().splitlines()]
        assert len(saved)==8 and all('smart_score' in r for r in saved)
        with (s.run/'results/baseline.csv').open() as f:
            assert all(r['smart_score'] for r in csv.DictReader(f))
        assert s.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def test_sql_leaderboard_hides_incomplete_rescore_revision(tmp_path):
    s,_=populate(tmp_path)
    try:
        s.set_state('rescore_revision',{'status':'in_progress'})
        assert s.db.execute('SELECT count(*) FROM candidate_leaderboard_view').fetchone()[0]==0
        with pytest.raises(ValueError,match='Incomplete score revision'):ranked(s)
        s.set_state('rescore_revision',{'status':'complete'})
        assert len(ranked(s))==8
    finally:s.close()


@pytest.mark.parametrize('limit',[0,-1,True,10001])
def test_leaderboard_rejects_unbounded_limits(tmp_path,limit):
    with RealmStore(tmp_path) as s:
        with pytest.raises(ValueError,match='limit'):ranked(s,limit=limit)


def test_dynamic_tiers_precede_combined_score_and_score_fallbacks():
    from seed_search.realm import leaderboard
    db=sqlite3.connect(':memory:')
    db.executescript('CREATE TABLE candidates(id TEXT,idx INTEGER,seed TEXT,qualification TEXT,result TEXT);CREATE TABLE meta(key TEXT,value TEXT);')
    cases=[('zero',0,{'combined_score':0,'baseline_score':100}),
           ('combined',1,{'combined_score':9999,'baseline_score':1}),
           ('baseline',0,{'combined_score':None,'baseline_score':30}),
           ('midpoint',0,{'baseline_score_uncertainty':{'prediction_score_interval':[10,30]}}),
           ('observed',0,{'baseline_score_observed':15}),
           ('near',2,{'combined_score':999,'baseline_score_observed':5,
                      'retention':{'classification':'NEAR_MISS','unmet_requirements':1}})]
    for name,tier,fields in cases:
        record={'screening_revision':'dynamic-envelope-1664-v1',
                'deficit_categories':['village']*tier,**fields}
        db.execute('INSERT INTO candidates VALUES(?,0,?,\'PREDICTED\',?)',(name,'1',json.dumps(record)))
    db.commit();leaderboard.install(db)
    assert db.execute(f'SELECT id,ranking_tier,smart_score FROM candidate_leaderboard_view ORDER BY {ORDER}').fetchall()==[
        ('baseline',0,30),('midpoint',0,20),('observed',0,15),('zero',0,0),('combined',1,9999),('near',2,5)]
    db.close()
