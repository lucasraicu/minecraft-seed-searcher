"""One isolated bounded trial; original control imports the retained source tree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import statistics
import sys
import threading
import subprocess
import yaml
import time

for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
METRICS={'stage_seconds','native_work','worker_cpu_seconds','total_seconds','worker_pid','worker_peak_rss_bytes','prototype'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--arm',choices=['python-original','python30','python','native','native-strict','native-near'],required=True)
    p.add_argument('--source',type=Path,default=ROOT);p.add_argument('--native',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('--count',type=int,required=True);p.add_argument('--key',type=int,required=True)
    p.add_argument('--threads',type=int,default=16);p.add_argument('--batch',type=int,default=4096)
    p.add_argument('--workers',type=int,default=30)
    p.add_argument('--locked',action='store_true',help='Use the earlier locked 2048/1024 policy')
    p.add_argument('--river',action='store_true',help='Use the active river revision')
    p.add_argument('--policy-config',type=Path,help='Explicit versioned policy for same-policy order comparisons')
    p.add_argument('--max-misses',type=int)
    p.add_argument('--entrypoint',action='store_true',help='Time the actual production CLI subprocess including startup')
    args=p.parse_args()
    if not 1<=args.count<=100000:p.error('One bounded cohort, at most 100,000')
    sys.path.insert(0,str(args.source/'src'));sys.path.insert(0,str(args.source))
    from seed_search.realm.config import blueprint_config,locked_blueprint_config,river_blueprint_config
    from seed_search.realm.capabilities import report,identity
    from seed_search.realm.runner import run_scan,process_tree_resources
    from seed_search.realm.store import RealmStore,canonical
    cfg=yaml.safe_load(args.policy_config.read_text()) if args.policy_config else river_blueprint_config() if args.river else locked_blueprint_config() if args.locked else blueprint_config();cfg['search']['run_key']=str(args.key)
    if args.run.exists():raise ValueError('Fresh trial path required')
    args.run.mkdir(parents=True);(args.run/'compatibility.json').write_text(json.dumps(report(cfg),indent=2))
    stop=threading.Event();samples=[]
    def sample():
        while not stop.is_set():
            r=process_tree_resources();r['wal_bytes']=sum(f.stat().st_size for f in args.run.glob('*-wal') if f.exists())
            samples.append(r);stop.wait(.1)
    compact=args.arm in ('native-strict','native-near')
    misses=args.max_misses if args.max_misses is not None else (1 if args.locked or args.river else 2) if args.arm=='native-near' else 0
    if args.entrypoint:
        config_path=args.receipt.with_suffix('.yaml');config_path.write_text(yaml.safe_dump(cfg))
    before_identity=identity();cpu=resource.getrusage(resource.RUSAGE_SELF);child=resource.getrusage(resource.RUSAGE_CHILDREN)
    watcher=threading.Thread(target=sample,daemon=True);watcher.start();start=time.perf_counter()
    try:
        if args.entrypoint:
            command=[sys.executable,'-m','seed_search','--config',str(config_path),'baseline','--count',str(args.count),'--output',str(args.run),'--prediction-scale']
            if args.arm.startswith('native'):
                command+=['--executor','native','--native-build',str(args.native),'--native-threads',str(args.threads),'--native-batch-size',str(args.batch)]
                if compact:command+=['--retention','survivors','--max-misses',str(misses)]
            else:command+=['--workers',str(args.workers)]
            # An editable install can otherwise resolve the live workspace even
            # when cwd points at a retained control checkout.
            environment=dict(os.environ)
            environment['PYTHONPATH']=os.pathsep.join((str(args.source.resolve()/'src'),str(args.source.resolve())))
            result=subprocess.run(command,cwd=args.source,env=environment,text=True,capture_output=True)
            args.receipt.with_suffix('.cli.log').write_text(result.stdout+result.stderr)
            result.check_returncode();row={'status':json.loads(result.stdout),'command':command};native_identity=None
        elif args.arm.startswith('native'):
            from scripts.blueprint_batch_prototype import Prototype,persist_pipeline
            prototype=Prototype(args.native,cfg)
            row=persist_pipeline(prototype,args.run,args.count,run_key=args.key,threads=args.threads,batch_size=args.batch,retention="survivors" if compact else "full",max_misses=misses)
            native_identity=prototype.identity
        else:
            status=run_scan(cfg,args.run,args.count,workers=args.workers,identity={'config':cfg,'backend':before_identity,'benchmark':'throughput-control-v1','count':args.count},allow_prediction_scale=True)
            row={'status':status};native_identity=None
        seconds=time.perf_counter()-start
    finally:
        stop.set();watcher.join()
    after=resource.getrusage(resource.RUSAGE_SELF);after_child=resource.getrusage(resource.RUSAGE_CHILDREN)
    row.update(arm=args.arm,count=args.count,key=args.key,wall_seconds=seconds,input_seeds_per_second=args.count/seconds,
        cpu_seconds=after.ru_utime+after.ru_stime-cpu.ru_utime-cpu.ru_stime+after_child.ru_utime+after_child.ru_stime-child.ru_utime-child.ru_stime,
        peak_process_tree_rss_bytes=max((s.get('rss_bytes',0) for s in samples),default=0),
        peak_wal_bytes=max((s['wal_bytes'] for s in samples),default=0),source_identity=before_identity,native_identity=native_identity)
    assert row['status']['completed_seeds']==args.count
    # All semantic evidence and durable work contents, outside timing for all arms.
    with RealmStore(args.run,resume=True) as store:
        digest=hashlib.sha256();anchors=survivors=inputs=0
        for record in store.iter_results():
            inputs+=1;anchors+=len(record['anchors']);survivors+=sum(a['qualification']=='PREDICTED' for a in record['anchors'])
            digest.update(canonical({k:v for k,v in record.items() if k not in METRICS}).encode())
        task_digests={};table_rows={}
        for name in ('seeds','candidates','discovery_tasks','inventory_work','variant_tasks'):
            table_rows[name]=store.db.execute(f'SELECT count(*) FROM {name}').fetchone()[0]
        for name in ('discovery_tasks','inventory_work','variant_tasks'):
            h=hashlib.sha256()
            for task in store.db.execute(f'SELECT * FROM {name} ORDER BY 1,2'):h.update(canonical(task).encode())
            task_digests[name]=h.hexdigest()
        cursor=0
        for first,end,status in store.db.execute('SELECT start,end,status FROM ranges ORDER BY start'):
            assert status=='complete' and int(first)==cursor;cursor=int(end)
        assert cursor==args.count and inputs==(store.status()['saved_seed_rows'] if compact else args.count)
        if compact:
            assert sum(json.loads(r[0])['inputs'] for r in store.db.execute('SELECT receipt FROM retention_receipts'))==args.count
            assert store.get_state('counts')['retained_inputs']==inputs
        if args.entrypoint and args.arm.startswith('native'):
            row['native_identity']=store.identity['native'];row['pipeline']=store.get_state('native_pipeline')
        assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert store.db.execute('PRAGMA synchronous').fetchone()[0]==2
        row['fingerprint']={'records_sha256':digest.hexdigest(),'task_sha256':task_digests,'table_rows':table_rows,
                            'inputs':inputs,'anchors':anchors,'baseline_survivors':survivors,'counts':store.get_state('counts')}
        row['durability']={'journal_mode':store.db.execute('PRAGMA journal_mode').fetchone()[0],'synchronous':2}
    row['sqlite_bytes']=sum(f.stat().st_size for f in args.run.glob('realm.sqlite*'))
    row['bytes_per_input']=row['sqlite_bytes']/args.count
    latencies=row.get('batch_latencies_seconds',[])
    if latencies:row['batch_latency_p50_seconds']=statistics.median(latencies);row['batch_latency_p95_seconds']=sorted(latencies)[min(len(latencies)-1,int(.95*len(latencies)))]
    args.receipt.write_text(json.dumps(row,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:row[k] for k in ('arm','count','wall_seconds','input_seeds_per_second','peak_process_tree_rss_bytes','sqlite_bytes')}),flush=True)


if __name__=='__main__':main()
