"""Kill a disposable native scan after a durable checkpoint and compare resume."""
import json,os,sqlite3,subprocess,time
from pathlib import Path
from seed_search.realm.store import RealmStore
HERE=Path(__file__).resolve().parent
LEDGER=HERE/'timing_budget.json'
BASE=['.venv/bin/python','-m','seed_search','--config','config/realm.yaml']
ENV={**os.environ,'PYTHONPATH':'.'}
OPTIONS=['--executor','native','--native-build','runs/cpu-completion-2026-10-13/final-portable','--native-threads','1','--native-batch-size','512','--retention','survivors','--max-misses','2','--prediction-scale']

def timed(args,log,kill=False):
 ledger=json.loads(LEDGER.read_text());left=ledger['hard_cap_seconds']-ledger['total_measured_seconds']
 if left<60:raise RuntimeError('Insufficient bounded budget')
 started=time.monotonic();checkpoint=None
 with log.open('w') as out:
  proc=subprocess.Popen(BASE+args,env=ENV,stdout=out,stderr=subprocess.STDOUT)
  try:
   if kill:
    db=HERE/'crashed'/'realm.sqlite'
    while proc.poll() is None:
     if time.monotonic()-started>min(30,left):raise RuntimeError('No checkpoint before deadline')
     if db.exists():
      try:
       with sqlite3.connect(f'file:{db}?mode=ro',uri=True,timeout=.05) as conn:
        rows=conn.execute("SELECT start,end FROM ranges WHERE status='complete'").fetchall()
       if rows:checkpoint=rows;proc.kill();break
      except sqlite3.OperationalError:pass
     time.sleep(.02)
   code=proc.wait(timeout=min(50,left))
  finally:
   if proc.poll() is None:proc.kill();proc.wait()
   wall=time.monotonic()-started
   ledger['measured_profile_seconds']+=wall;ledger['total_measured_seconds']=ledger['measured_cli_seconds']+ledger['measured_profile_seconds']
   ledger['events'].append({'kind':'crash_resume_operational_check','command':BASE+args,'wall_seconds':wall,'returncode':proc.returncode,'killed_after_checkpoint':checkpoint})
   LEDGER.write_text(json.dumps(ledger,indent=2)+'\n')
 if kill:
  assert checkpoint and code!=0
 else:assert code==0,log.read_text()
 return checkpoint

def receipt(run):
 with RealmStore(run,resume=True) as store:
  status=store.status();assert status['completed_seeds']==50000,status
  rows=sorted((int(a),int(b)) for a,b in store.db.execute('SELECT start,end FROM retention_receipts'))
  assert rows[0][0]==2020000 and rows[-1][1]==2070000
  assert all(a[1]==b[0] for a,b in zip(rows,rows[1:]))
  assert sum(b-a for a,b in rows)==50000
  assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  records=list(store.iter_results());assert records
  return {'status':status,'ranges':rows,'records':records}

def main():
 for name in ('control','crashed'):
  assert not (HERE/name).exists(),'Disposable run must be fresh'
 scan=['scan','--start-index','2020000','--count','50000']
 timed(scan+['--output',str(HERE/'control')]+OPTIONS,HERE/'control.log')
 checkpoint=timed(scan+['--output',str(HERE/'crashed')]+OPTIONS,HERE/'kill.log',True)
 timed(['resume','--run',str(HERE/'crashed')]+OPTIONS,HERE/'resume.log')
 c=receipt(HERE/'control');r=receipt(HERE/'crashed')
 # Timing/progress counters may differ after replay; candidate evidence must agree.
 from seed_search.realm.native_batch import semantic_record
 assert [semantic_record(x) for x in c['records']]==[semantic_record(x) for x in r['records']], 'Candidate evidence differs after restart'
 (HERE/'crash-resume.json').write_text(json.dumps({'control':c['status'],'resumed':r['status'],'killed_checkpoints':checkpoint,'sqlite_integrity':'ok','candidate_semantics_equal':True,'retained_inputs':len(r['records'])},indent=2)+'\n')
 print('PASS: crash/resume coverage, candidate semantic equality and SQLite integrity',flush=True)
if __name__=='__main__':main()
