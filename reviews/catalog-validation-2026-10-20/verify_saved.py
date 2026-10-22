"""Bounded saved-data verification; refuses to dispatch any extraction command."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from seed_search.catalog.ingestion import ingest,atomic_json,tree_bytes,verify_no_symlinks
from seed_search.catalog.store import CatalogStore
from seed_search.catalog.view import SnapshotView
from seed_search.catalog.evaluation import bind
from seed_search.catalog.validation_contracts import MAX_JOB_SECONDS,MAX_RSS_BYTES,MAX_OUTPUT_BYTES
from seed_search.realm.runner import process_tree_resources


def verify(root):
    root=verify_no_symlinks(root)
    def load(name):return json.loads((root/name).read_text())
    controls=load('controls.json');summary=load('report.json')
    for relative,expected in controls['build']['source_sha256'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=expected:raise ValueError('Source drift')
    with (root/'job.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        charged=load('job-budget.json')['charged_seconds'];reservation=min(120,MAX_JOB_SECONDS-charged)
        if reservation<=0:raise ValueError('Original job budget exhausted')
        atomic_json(root/'job-budget.json',{'charged_seconds':charged+reservation})
        stopped=threading.Event();reasons=[];samples=[]
        def interrupt(*_):raise TimeoutError(reasons[-1] if reasons else 'Saved verification time budget exhausted')
        old=signal.signal(signal.SIGALRM,interrupt);signal.setitimer(signal.ITIMER_REAL,reservation)
        def monitor():
            while not stopped.is_set():
                sample=process_tree_resources()
                if not sample['available']:reasons.append('Aggregate monitoring unavailable')
                else:
                    samples.append(sample['rss_bytes'])
                    if sample['rss_bytes']>MAX_RSS_BYTES:reasons.append('Aggregate RSS cap')
                if tree_bytes(root)>MAX_OUTPUT_BYTES:reasons.append('Output cap')
                if reasons:os.kill(os.getpid(),signal.SIGALRM);return
                stopped.wait(.25)
        watcher=threading.Thread(target=monitor,daemon=True);watcher.start();start=time.monotonic();successful=False
        try:
            ledger=root/'ingestion/ledger.json';before=hashlib.sha256(ledger.read_bytes()).hexdigest()
            def forbidden(*_):raise AssertionError('A completed seed was dispatched again')
            resume_start=time.monotonic()
            receipts=ingest(root/'ingestion',controls,resume=True,stop_after=100,command_factory=forbidden)
            resume_seconds=time.monotonic()-resume_start
            if hashlib.sha256(ledger.read_bytes()).hexdigest()!=before:raise ValueError('Zero-extraction resume changed durable ledger')
            read_start=time.monotonic()
            with CatalogStore(root/'catalog') as store:data=store.snapshot(summary['snapshot_id'])
            reconstruction_seconds=time.monotonic()-read_start
            view_start=time.monotonic();view=SnapshotView.from_snapshot(data);view_seconds=time.monotonic()-view_start
            del data
            corpus=load('heldout.json');expected=load('defaults-evaluation.json')['rows']
            for index in (0,8):
                result=view.search(bind(corpus['cases'][index],view),limit=10)
                if [r['world_id'] for r in result]!=expected[index]['reference_world_ids']:
                    raise ValueError('Reconstructed query result differs')
            result=dict(passed=True,completed_worlds=receipts['summary']['completed'],new_extraction_dispatches=0,
                ledger_sha256=before,ledger_unchanged=True,zero_extraction_resume_seconds=resume_seconds,
                verified_reconstruction_seconds=reconstruction_seconds,verified_view_build_seconds=view_seconds,
                rebuilt_view_query_cases=[0,8],snapshot_id=view.snapshot_id,
                polled_peak_rss_bytes=max(samples,default=0),scope='Saved observations only; no native calls or new seed inputs')
            atomic_json(root/'saved-verification.json',result);successful=True
            return result
        finally:
            stopped.set();watcher.join(timeout=6);signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
            if successful:
                atomic_json(root/'job-budget.json',{'charged_seconds':charged+min(reservation,time.monotonic()-start)})


if __name__=='__main__':print(json.dumps(verify(Path(sys.argv[1])),indent=2,allow_nan=False))
