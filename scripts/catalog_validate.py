#!/usr/bin/env python3
"""Approved bounded100-world CPU validation; no public deployment or GPU work."""
from pathlib import Path
import argparse
import fcntl
import gzip
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def atomic(path,value):
    from seed_search.catalog.ingestion import atomic_json
    atomic_json(path,value)


def load(path):
    from seed_search.catalog.ingestion import strict_json_loads,verify_no_symlinks
    return strict_json_loads(verify_no_symlinks(path).read_text())


def frozen_inputs(cohort_start=0):
    from seed_search import _native
    from seed_search.backend import native_runtime,model_metadata
    from seed_search.realm.native_identity import native_source_fingerprint
    from seed_search.catalog.models import identity
    from seed_search.catalog.validation_contracts import controls,pilot_controls
    from seed_search.catalog.evaluation import heldout_cases
    if cohort_start not in (0,100):raise ValueError('Only original0..99 or approved100..199 cohort supported')
    native_runtime();corpus=heldout_cases() if cohort_start==0 else heldout_cases(seed=2026102005,count=256)
    ident=identity(0,model_id=model_metadata()['model'],source_sha256=native_source_fingerprint(),
        native_sha256=hashlib.sha256(Path(_native.__file__).read_bytes()).hexdigest());ident.pop('seed')
    paths=[Path(__file__).resolve(),ROOT/'scripts/catalog_reference.py',ROOT/'src/seed_search/backend.py',
        ROOT/'src/seed_search/realm/biomes.py',ROOT/'src/seed_search/seeds.py',*sorted((ROOT/'src/seed_search/catalog').glob('*.py'))]
    build={'identity':ident,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
           'heldout_sha256':corpus['sha256']}
    return (controls(build) if cohort_start==0 else pilot_controls(build)),corpus


def _pipeline(output):
    from seed_search.catalog.ingestion import ingest
    from seed_search.catalog.validation_contracts import validate_controls,MAX_JOB_SECONDS
    from seed_search.catalog.registry import FEATURE_IDS
    from seed_search.catalog.models import validate_observation
    from seed_search.catalog.summaries import summarize
    from seed_search.catalog.store import CatalogStore
    from seed_search.catalog.view import SnapshotView
    from seed_search.catalog.retention import retain,merge
    from seed_search.catalog.evaluation import evaluate
    from seed_search.catalog.retention_oracle import oracle_memberships
    controls=validate_controls(load(output/'controls.json'))
    actual,_=frozen_inputs(100) if controls.get('cohort_start')==100 else frozen_inputs()
    if controls!=actual:raise ValueError('Source/build/control mismatch')
    corpus=load(output/'heldout.json');deadline=time.monotonic()+MAX_JOB_SECONDS
    checkpoint_map=load(output/'checkpoint-map.json') if (output/'checkpoint-map.json').exists() else {}
    def command(index,seed,checkpoint):
        path=Path(checkpoint)
        if not path.resolve().is_relative_to(output.resolve()):raise ValueError('Checkpoint escaped run')
        checkpoint_map[str(index)]=str(path.relative_to(output))
        atomic(output/'checkpoint-map.json',checkpoint_map)
        return [sys.executable,str(ROOT/'scripts/catalog_reference.py'),'_extract','--output',str(path),
                '--seed',seed,'--threads','1']
    before=time.monotonic();run=output/'ingestion'
    preflight=ingest(run,controls,resume=run.exists(),stop_after=10,command_factory=command)
    atomic(output/'preflight.json',preflight)
    print('10-world preflight persisted',flush=True)
    report=ingest(run,controls,resume=True,stop_after=100,command_factory=command)
    atomic(output/'ingestion-report.json',report)
    print('Ingestion stopped/completed; collecting explicit receipts',flush=True)
    observations=[];identities=[];missing=[];partial=[];invalid=[]
    for index,seed in enumerate(controls['cohort']):
        identities.append(dict(controls['build']['identity'],seed=seed))
        relative=checkpoint_map.get(str(index))
        if relative is None or not (output/relative).exists():missing.append(index);continue
        try:
            path=output/relative
            if not path.resolve().is_relative_to(output.resolve()):raise ValueError('Checkpoint escaped run')
            obs=validate_observation(load(path))
            if obs['identity']!=identities[-1]:raise ValueError('Checkpoint/cohort identity mismatch')
        except Exception as exc:
            invalid.append({'index':index,'error':type(exc).__name__+': '+str(exc)[:300]});continue
        observations.append(obs)
        if not all(obs['coverage'].get(f,{}).get('status')=='complete' for f in FEATURE_IDS):partial.append(index)
    if not observations:raise ValueError('No valid observations to publish')
    extract_wall=time.monotonic()-before
    if time.monotonic()>deadline:raise TimeoutError('Validation job wall budget exhausted')
    start=time.monotonic();layouts=[]
    for obs in observations:
        if time.monotonic()>deadline:raise TimeoutError('Summary budget exhausted')
        layouts.extend(summarize(obs))
    summaries_seconds=time.monotonic()-start
    start=time.monotonic()
    with CatalogStore(output/'catalog') as store:
        sid=store.publish_snapshot(observations,layouts);data=store.snapshot(sid)
    publication_seconds=time.monotonic()-start
    start=time.monotonic();view=SnapshotView.from_snapshot(data);view_seconds=time.monotonic()-start
    print(f'Published {len(observations)} worlds / {len(layouts)} layouts; evaluating retention',flush=True)
    experiments={};references=None;retention_seconds={};oracle=None;oracle_seconds=None
    for label,capacity in (('defaults',None),('reduced_k1',{'structure_count':1,'structure_proximity':1,'biome_proximity':1,
        'biome_landmark_pairs':1,'profiles':1,'diversity':1,'reference_sample':5}),('reduced_k2',{
        'structure_count':2,'structure_proximity':2,'biome_proximity':2,'biome_landmark_pairs':2,
        'profiles':2,'diversity':1,'reference_sample':5})):
        if time.monotonic()>deadline:raise TimeoutError('Retention budget exhausted')
        start=time.monotonic();selection=retain(layouts,identities,capacities=capacity)
        retention_seconds[label]=time.monotonic()-start
        if oracle is None:
            start=time.monotonic();oracle=oracle_memberships(layouts,identities,selection['capacities'],deadline=deadline)
            oracle_seconds=time.monotonic()-start
        expected={oid:members[:selection['capacities'][oid.split(':')[0]]] for oid,members in oracle['objectives'].items()}
        expected_worlds=sorted({m['world_id'] for members in expected.values() for m in members})
        if selection['objectives']!=expected or selection['world_ids']!=expected_worlds:
            raise ValueError('Independent retention oracle mismatch')
        compressed=gzip.compress(json.dumps(selection,sort_keys=True,separators=(',',':'),allow_nan=False).encode(),mtime=0)
        target=output/f'{label}-selection.json.gz'
        with target.open('wb') as stream:stream.write(compressed);stream.flush();os.fsync(stream.fileno())
        metrics,references=evaluate(view,selection['world_ids'],corpus,reference_results=references,deadline=deadline)
        experiments[label]=metrics
        atomic(output/f'{label}-evaluation.json',metrics)
        print(f'{label}: {len(selection["world_ids"])} retained identities; queryable={metrics["retained_queryable_worlds"]}',flush=True)
        if label=='defaults':
            partitioned=[]
            for part in range(3):
                chosen=identities[part::3];ids={__import__('seed_search.catalog.models',fromlist=['world_id']).world_id(i) for i in chosen}
                partitioned.append(retain([l for l in layouts if l['world_id'] in ids],chosen))
            if merge(partitioned)!=selection:raise ValueError('Partitioned retention merge mismatch')
    from seed_search.catalog.validation_synthetic import synthetic_snapshot
    start=time.monotonic();synthetic_data=synthetic_snapshot();synthetic_view=SnapshotView.from_snapshot(synthetic_data)
    synthetic_ids=[o['identity'] for o in synthetic_data['observations']]
    synthetic_selection=retain(synthetic_data['layouts'],synthetic_ids,capacities={
        'structure_count':1,'structure_proximity':1,'biome_proximity':1,'biome_landmark_pairs':1,
        'profiles':1,'diversity':1,'reference_sample':5})
    synthetic_oracle=oracle_memberships(synthetic_data['layouts'],synthetic_ids,synthetic_selection['capacities'],deadline=deadline)
    if synthetic_oracle['objectives']!=synthetic_selection['objectives']:raise ValueError('Synthetic oracle mismatch')
    synthetic_metrics,_=evaluate(synthetic_view,synthetic_selection['world_ids'],corpus,deadline=deadline)
    if not synthetic_metrics['discriminating']:raise ValueError('Synthetic fixture failed to oversubscribe retention')
    synthetic_metrics['fixture']='FABRICATED identical spatial facts, 64 distinct identities, 3 anchors x3 borders; not real Minecraft worlds'
    atomic(output/'synthetic-evaluation.json',synthetic_metrics)
    synthetic_seconds=time.monotonic()-start
    if time.monotonic()>deadline:raise TimeoutError('Restore budget exhausted')
    with CatalogStore(output/'catalog') as store:
        if not (output/'backup').exists():store.backup(output/'backup')
    with CatalogStore(output/'backup') as restored:
        if restored.snapshot(sid)!=data:raise ValueError('Backup/restore differs from source snapshot')
    result={'schema':'catalog100-validation-report-v1','status':'complete' if report['summary']['completed']==100 and not missing and not partial and not invalid else 'partial',
        'snapshot_id':sid,'worlds':len(observations),'missing_indices':missing,'partial_indices':partial,
        'invalid_checkpoints':invalid,'ingestion_summary':report['summary'],
        'layouts':len(layouts),'ingestion_wall_seconds':extract_wall,'summary_seconds':summaries_seconds,
        'publication_seconds':publication_seconds,'verified_view_seconds':view_seconds,
        'retention_seconds':retention_seconds,'retention_oracle_seconds':oracle_seconds,'retention_oracle_parity':True,
        'synthetic_seconds':synthetic_seconds,'synthetic':{k:v for k,v in synthetic_metrics.items() if k!='rows'},'backup_restore':True,'partition_merge_parity':True,
        'heldout_sha256':corpus['sha256'],'experiments':{k:{n:v for n,v in item.items() if n!='rows'} for k,item in experiments.items()},
        'scope':'Declared100-world predictor corpus; no four-pillar/world certification, public launch, GPU or production recall proof'}
    atomic(output/'report.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='experiments'},indent=2),flush=True)
    return 0 if result['status']=='complete' else 2


def _resources(root_pid):
    from seed_search.realm.runner import process_tree_resources
    return process_tree_resources(root_pid)


def supervise(output,resume=False,cohort_start=0):
    from seed_search.catalog.validation_contracts import MAX_JOB_SECONDS,MAX_RSS_BYTES,MAX_OUTPUT_BYTES
    from seed_search.catalog.ingestion import verify_no_symlinks,tree_bytes
    output=verify_no_symlinks(output)
    controls,corpus=frozen_inputs(100) if cohort_start==100 else frozen_inputs()
    if output.is_symlink():raise ValueError('Unsafe output root')
    if resume:
        if load(output/'controls.json')!=controls or load(output/'heldout.json')!=corpus:raise ValueError('Resume input mismatch')
    else:
        output.mkdir(parents=True,exist_ok=False);atomic(output/'controls.json',controls);atomic(output/'heldout.json',corpus)
        atomic(output/'job-budget.json',{'charged_seconds':0.})
    with (output/'job.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        charged=load(output/'job-budget.json')['charged_seconds']
        if type(charged) not in (int,float) or not 0<=charged<MAX_JOB_SECONDS:raise ValueError('Job budget exhausted/invalid')
        remaining=MAX_JOB_SECONDS-charged;reserved=min(60.,remaining);before=time.monotonic()
        atomic(output/'job-budget.json',{'charged_seconds':charged+reserved})
        read_fd,write_fd=os.pipe()
        with (output/'validation.log').open('ab') as log:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'_run','--output',str(output),
                '--lifeline-fd',str(read_fd)],stdout=log,stderr=log,start_new_session=True,pass_fds=(read_fd,),
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
                    MKL_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1'))
            os.close(read_fd);peak=0;reason=None;total=0;failure=None
            try:
                while process.poll() is None:
                    elapsed=time.monotonic()-before
                    if elapsed>=remaining:reason='job_wall_cap'
                    sampled=_resources(os.getpid())
                    if not sampled['available']:raise RuntimeError('Aggregate RSS monitoring unavailable')
                    peak=max(peak,sampled['rss_bytes'])
                    if peak>MAX_RSS_BYTES:reason='aggregate_rss_cap'
                    total=tree_bytes(output)
                    if total>MAX_OUTPUT_BYTES:reason='output_cap'
                    if reason:break
                    if elapsed>=reserved-1:
                        reserved=min(remaining,reserved+60)
                        atomic(output/'job-budget.json',{'charged_seconds':charged+reserved})
                    time.sleep(0.25)
            except BaseException as exc:
                failure=exc;reason='supervisor_error:'+type(exc).__name__
            finally:
                os.close(write_fd)  # Lifeline EOF triggers child finally/owned-process cleanup.
                if process.poll() is None:
                    try:os.killpg(process.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        try:os.killpg(process.pid,signal.SIGKILL)
                        except ProcessLookupError:pass
                        process.wait(timeout=5)
            spent=min(remaining,time.monotonic()-before)
            atomic(output/'job-budget.json',{'charged_seconds':charged+spent})
            atomic(output/'supervision.json',{'exit_status':process.returncode,'stop_reason':reason,
                'wall_seconds':spent,'polled_peak_rss_bytes':peak,'output_bytes':total})
            if failure is not None:raise failure
            return process.returncode if reason is None else 2


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['run','_run'])
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--resume',action='store_true')
    parser.add_argument('--cohort-start',type=int,choices=(0,100),default=0)
    parser.add_argument('--lifeline-fd',type=int);args=parser.parse_args(argv)
    if args.command=='run':return supervise(args.output,args.resume,args.cohort_start)
    def interrupted(*_):raise KeyboardInterrupt('Validation supervisor stopped')
    signal.signal(signal.SIGTERM,interrupted)
    if args.lifeline_fd is not None:
        def lifeline():
            try:os.read(args.lifeline_fd,1)
            finally:os.kill(os.getpid(),signal.SIGTERM)
        threading.Thread(target=lifeline,daemon=True).start()
    return _pipeline(args.output)


if __name__=='__main__':raise SystemExit(main())
