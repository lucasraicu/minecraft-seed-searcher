"""Current corrected personal screening and independent catalog handoff costs."""
from pathlib import Path
import copy,hashlib,json,os,signal,sqlite3,statistics,sys,time
ROOT=Path('/Users/lucasraicu/Downloads/minecraft-seed-searcher');sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('KMP_BLOCKTIME','0')
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype,seeds_np,run_native_scan,semantic_record
from seed_search.realm.store import RealmStore
from seed_search.realm.capabilities import report as compatibility_report

P=Path(__file__).parent;BUILD=ROOT/'runs/dynamic-baseline-2048/native-corrected-openmp-2026-10-21'
COUNT=262144;KEY=2026101630

def fingerprint(run,expected):
 with RealmStore(run,resume=True)as store:
  assert store.status()['completed_seeds']==expected
  assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert store.db.execute('PRAGMA synchronous').fetchone()[0]==2
  records=[semantic_record(row)for row in store.iter_results()]
  ranges=store.db.execute('SELECT start,end,status FROM ranges ORDER BY start').fetchall()
  assert all(row[2]=='complete'for row in ranges)
  assert sum(json.loads(row[0])['inputs']for row in store.db.execute('SELECT receipt FROM retention_receipts'))==expected
  return dict(completed=expected,ranges=ranges,counts=store.get_state('counts'),records=len(records),records_sha256=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest())

def one_run(trial,arm,count=COUNT,start=None,public=None):
 cfg=dynamic_v3_blueprint_config();cfg['search']['run_key']=str(KEY)
 run=P/f'personal-{trial}-{arm}';assert not run.exists()
 run.mkdir();(run/'compatibility.json').write_text(json.dumps(compatibility_report(cfg),indent=2)+'\n')
 options=dict(start_index=trial*COUNT if start is None else start,native_build=BUILD,native_threads=34,native_batch_size=16384,retention='survivors',max_misses=0,top_k=50,allow_prediction_scale=True)
 if public is not None:options.update(catalog_root=public,catalog_sample_cap=2)
 started=time.monotonic();cpu=time.process_time()
 result=run_native_scan(cfg,run,count,**options)
 elapsed=time.monotonic()-started
 assert result['completed_seeds']==count
 assert result['candidate_policy']['candidate_capacity']==100, result['candidate_policy']
 row=dict(trial=trial,arm=arm,count=count,start=options['start_index'],wall_seconds=elapsed,input_seeds_per_second=count/elapsed,cpu_seconds=time.process_time()-cpu,execution=result['execution'],candidate_policy=result['candidate_policy'],fingerprint=fingerprint(run,count),run=str(run))
 if public is not None:
  assert result['catalog_harvest']['state']=='registered';row['handoff']=result['catalog_harvest']
 print(json.dumps({k:row[k]for k in ('trial','arm','count','wall_seconds','input_seeds_per_second')}),flush=True)
 return row

def main():
 signal.alarm(150)
 cfg=dynamic_v3_blueprint_config();prototype=Prototype(BUILD,cfg)
 assert prototype.identity['openmp']
 with prototype.sweep(seeds_np(0,4096,KEY),34,retention='survivors',refine_centers=True)as batch:assert batch.pointer.effective_threads==34
 kernels=[];rows=[]
 for trial in range(3):
  cohort=seeds_np(trial*COUNT,(trial+1)*COUNT,KEY);before=time.monotonic();retained=0
  for offset in range(0,COUNT,16384):
   with prototype.sweep(cohort[offset:offset+16384],34,retention='survivors',refine_centers=True)as batch:
    assert batch.pointer.effective_threads==34;retained+=int(batch.pointer.result_count)
  elapsed=time.monotonic()-before;kernels.append(dict(trial=trial,count=COUNT,seconds=elapsed,seeds_per_second=COUNT/elapsed,retained=retained))
  pair=[]
  for arm in (('personal_only','catalog_handoff')if trial%2==0 else('catalog_handoff','personal_only')):
   public=P/f'queue-only-{trial}'if arm=='catalog_handoff'else None
   row=one_run(trial,arm,public=public);rows.append(row);pair.append(row)
  assert pair[0]['fingerprint']==pair[1]['fingerprint'],('Personal semantic/receipt differences',trial)
  (P/'personal-results.json').write_text(json.dumps(dict(identity=prototype.identity,kernel=kernels,rows=rows),indent=2)+'\n')
 report=json.loads((P/'personal-results.json').read_text())
 report['median_rates']={arm:statistics.median(row['input_seeds_per_second']for row in rows if row['arm']==arm)for arm in ('personal_only','catalog_handoff')}
 report['kernel_median_rate']=statistics.median(row['seeds_per_second']for row in kernels)
 report['paired_wall_ratios']=[next(row['wall_seconds']for row in rows if row['trial']==i and row['arm']=='catalog_handoff')/next(row['wall_seconds']for row in rows if row['trial']==i and row['arm']=='personal_only')for i in range(3)]
 report['scope']='3counterbalanced pairs;262144inputs each, same current build/config/cohort,34OMPthreads,batch16384,strictsurvivorTop50;API wall includes preflight/handoff/pipeline, excludes interpreter startup. Query service idle; no extractor is run by handoff.'
 (P/'personal-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['median_rates']),flush=True)

if __name__=='__main__':main()
