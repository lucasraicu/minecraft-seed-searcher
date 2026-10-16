import sys,json,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'));base=Path(__file__).resolve().parent
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import run_native_scan
cfg=dynamic_v3_blueprint_config();cfg['biomes']['required_families']=[];cfg['search']['sequence']='manifest';cfg['search']['manifest_seeds']=['-3336796033057908633','0']
run=base/'recovery-run';kw=dict(count=2,native_threads=1,native_batch_size=1,retention='survivors',top_k=1,native_build=base/'baseline')
a=run_native_scan(cfg,run,stop_after=1,**kw);before=json.loads((run/'top50.json').read_text())
(run/'top50.json').write_text('{interrupted-checkpoint')
b=run_native_scan(cfg,run,resume=True,**kw);after=json.loads((run/'top50.json').read_text())
conn=sqlite3.connect(run/'realm.sqlite');tables=conn.execute("select name from sqlite_master where type='table'").fetchall()
print(json.dumps({'before_completed':a['completed_seeds'],'after_completed':b['completed_seeds'],'before_top_count':len(before),'after_top_count':len(after),'after_sqlite_top_count':conn.execute('select count(*) from top_candidates').fetchone()[0],'saved_seed_rows':b.get('saved_seed_rows'),'tables':tables},indent=2))
