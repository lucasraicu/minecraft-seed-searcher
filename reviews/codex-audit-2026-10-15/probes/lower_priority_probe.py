import sys,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'src'))
from seed_search.realm.store import RealmStore,canonical,index_key
from seed_search.web.server import SweepManager
from seed_search.realm.config import dynamic_blueprint_config
run=Path(tempfile.mkdtemp(prefix='audit-web-cache-'))
with RealmStore(run,identity={'config':dynamic_blueprint_config()}) as st:
 r={'id':'123:0:0','seed':'123','stronghold':[0,0],'evaluation_center':[0,0], 'screening_revision':'dynamic-envelope-1664-v1','qualification':'PREDICTED','baseline_score':100,'baseline_score_observed':100,'deficit_categories':[]}
 st.db.execute('INSERT INTO candidates VALUES(?,?,?,?,?)',(r['id'],index_key(0),'123','PREDICTED',canonical(r)));st.db.commit()
 m=SweepManager();m.run_dir=run;m._last_candidates_sig=None;m._query_sqlite_candidates()
 print('before',m.candidates[0]['score'])
 r['baseline_score']=r['baseline_score_observed']=130
 st.db.execute('UPDATE candidates SET result=? WHERE id=?',(canonical(r),r['id']));st.db.commit()
 m._query_sqlite_candidates();print('after score UPDATE',m.candidates[0]['score'],'DB score',st.db.execute('SELECT smart_score FROM candidate_leaderboard_view').fetchone()[0])
