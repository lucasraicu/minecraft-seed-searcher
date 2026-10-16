from pathlib import Path
import json,sys,tempfile,threading
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src')]
from seed_search.realm.store import RealmStore,canonical
from seed_search.realm.config import dynamic_v2_blueprint_config
from seed_search.web.server import SweepManager
with tempfile.TemporaryDirectory() as run:
    with RealmStore(run,{'config':dynamic_v2_blueprint_config()}) as st:
        base={'screening_revision':'dynamic-envelope-1664-v2','baseline_score':100,'baseline_score_complete':True,'evaluation_center':[0,0],'deficit_categories':[],'radial_key':0,'origin_distance_squared':0}
        with st.db:
            st.db.executemany('INSERT INTO candidates VALUES (?,?,?,?,?)',[(f'{i}:0:0',str(i),str(i),'PREDICTED',canonical({**base,'id':f'{i}:0:0','seed':str(i)})) for i in range(5001)])
        manager=SweepManager.__new__(SweepManager);manager.run_dir=Path(run);manager.candidates=[];manager.lock=threading.Lock();manager.logs=[]
        manager._query_sqlite_candidates()
        result={'database_count':5001,'manager_count':len(manager.candidates),'offset_5000_page':len(manager.candidates[5000:5100]),'api_reported_total':len(manager.candidates)}
Path(__file__).with_name('pagination-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(result)
