import sys,time,json,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import run_native_scan
from seed_search.realm.capabilities import report
for i in range(3):
 cfg=dynamic_v3_blueprint_config();cfg['search']['run_key']='2026101601'
 run=BASE/f'durable-measured-{i}'
 run.mkdir(exist_ok=True)
 (run/'compatibility.json').write_text(json.dumps(report(cfg)))
 t=time.perf_counter()
 result=run_native_scan(cfg,run,262144,start_index=10000000+i*262144,native_build=ROOT/'runs/dynamic-baseline-2048/native',native_threads=34,native_batch_size=16384,retention='survivors',allow_prediction_scale=True)
 elapsed=time.perf_counter()-t
 db=sqlite3.connect(f'file:{run}/realm.sqlite?mode=ro',uri=True)
 names=[r[0] for r in db.execute("select name from sqlite_master where type='table'")]
 row={'repetition':i,'count':262144,'wall_seconds':elapsed,'rate':262144/elapsed,'status':result,'receipts':db.execute('select count(*) from retention_receipts').fetchone()[0],'integrity':db.execute('pragma integrity_check').fetchone()[0]}
 db.close();row['disk_bytes']=sum(p.stat().st_size for p in run.rglob('*') if p.is_file());print(json.dumps(row),flush=True)
