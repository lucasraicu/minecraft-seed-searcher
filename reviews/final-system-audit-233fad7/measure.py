"""Bounded current-build timing and durability checks; no production runs."""
from pathlib import Path
import hashlib,json,statistics,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from seed_search.realm.config import dynamic_v2_blueprint_config
from seed_search.realm.native_batch import Prototype,Batch,seeds_np,persist_pipeline
from seed_search.realm.store import RealmStore
started=time.monotonic()
p=Prototype(ROOT/'runs/dynamic-baseline-1664/native',dynamic_v2_blueprint_config())
report={'commit':'233fad7','build':p.identity,'inputs_per_trial':100000,'start_index':50000000,'run_key':2026101401,'threads':34,'batch_size':16384,'trials':[],'runtime_limit_seconds':120}
for trial in range(5):
    if time.monotonic()-started>120:raise RuntimeError('Audit timing budget exceeded')
    with tempfile.TemporaryDirectory(prefix='audit-233fad7-natural-') as run:
        r=persist_pipeline(p,run,100000,run_key=2026101401,threads=34,batch_size=16384,start_index=50000000,retention='survivors',max_misses=3)
        with RealmStore(run,resume=True) as store:
            r['saved_candidates']=store.db.execute('SELECT count(*) FROM candidates').fetchone()[0]
            r['retention_receipts']=store.db.execute('SELECT count(*) FROM retention_receipts').fetchone()[0]
            r['no_pending_ranges']=store.db.execute("SELECT count(*) FROM ranges WHERE status!='complete'").fetchone()[0]==0
        report['trials'].append(r)
report['median']={k:statistics.median(r.get(k,0) for r in report['trials']) for k in ['wall_seconds','native_seconds','input_seeds_per_second','seed_preparation_seconds','commit_seconds','record_seconds','prepare_seconds','sql_seconds','shutdown_seconds']}
report['median_native_service_over_wall']=statistics.median(r['native_seconds']/r['wall_seconds'] for r in report['trials'])
# Synthetic positive data travels through the real batch/prepare/commit/resume path.
original=p.sweep
def fixtures(seeds,threads=1,**kwargs):return original(seeds,threads,fixtures=[(0,0,-1)]*len(seeds),**kwargs)
p.sweep=fixtures
with tempfile.TemporaryDirectory(prefix='audit-233fad7-positive-') as run:
    first=persist_pipeline(p,run,8,run_key=0,threads=1,batch_size=2,retention='survivors',max_misses=3,stop_after=3)
    second=persist_pipeline(p,run,8,run_key=0,threads=1,batch_size=2,retention='survivors',max_misses=3,resume=True)
    with RealmStore(run,resume=True) as store:
        report['positive_resume']={'provenance':'synthetic coordinate/biome fixture, actual native code and durable pipeline','first_completed':first['newly_committed'],'resume_completed':second['newly_committed'],'total':store.status()['completed_seeds'],'saved_candidates':store.db.execute('SELECT count(*) FROM candidates').fetchone()[0],'terrain_tasks':store.db.execute('SELECT count(*) FROM variant_tasks').fetchone()[0],'native_seconds':first['native_seconds']+second['native_seconds'],'record_seconds':first['record_seconds']+second['record_seconds'],'prepare_seconds':first.get('prepare_seconds',0)+second.get('prepare_seconds',0),'commit_seconds':first['commit_seconds']+second['commit_seconds']}
(OUT/'measurements.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('build','trials')},indent=2))
