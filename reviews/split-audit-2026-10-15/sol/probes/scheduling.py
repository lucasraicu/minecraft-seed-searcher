"""Small staged scheduling screen and paired confirmation, isolated kernels."""
import argparse
import hashlib
import json
import resource
import statistics
import time
from experiment import OUT, WORK, write_json
from seed_search.realm.native_batch import Prototype
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.seeds import seed_from_index

parser=argparse.ArgumentParser()
parser.add_argument('--allow-heavy',action='store_true')
parser.add_argument('--confirm',action='store_true')
args=parser.parse_args()
if not args.allow_heavy: parser.error('Requires explicit heavy-work release')
prototypes={k:Prototype(WORK/'lazy-no-surface-init'/f'chunk-{k}'/'optimized',dynamic_blueprint_config())
            for k in (16,64,128)}
rows=[]

def compare(name,configs,count=200000,trials=3,start=80000000):
    seeds=[seed_from_index(i,2026101401) for i in range(start,start+count)]
    for trial in range(trials):
        reference=None
        for threads,chunk,bsize in (configs if trial%2==0 else configs[::-1]):
            p=prototypes[chunk];kernel=0.;times=[];digest=hashlib.sha256()
            cpu=time.process_time();wall=time.perf_counter()
            for first in range(0,count,bsize):
                with p.sweep(seeds[first:first+bsize],threads,retention='survivors') as batch:
                    kernel+=batch.native_seconds;times.append(batch.native_seconds)
                    if batch.pointer.result_count: raise RuntimeError('Unexpected survivor: add full semantic receipt')
                    digest.update(p.ffi.buffer(batch.pointer.verdicts,batch.pointer.count*p.ffi.sizeof('NBVerdict')))
            elapsed=time.perf_counter()-wall;used=time.process_time()-cpu
            fp=digest.hexdigest()
            if reference is not None and reference!=fp: raise RuntimeError('Receipt mismatch')
            reference=fp
            row=dict(stage=name,trial=trial,count=count,start_index=start,run_key=2026101401,
                     threads=threads,chunk=chunk,batch=bsize,native_seconds=kernel,
                     kernel_rate=count/kernel,batch_seconds=times,wall_seconds=elapsed,
                     cpu_seconds=used,process_cpu_percent=100*used/elapsed,
                     receipt_fingerprint=fp,build_sha256=p.identity['extension_sha256'],
                     peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            rows.append(row);write_json(OUT/'scheduling.json',rows);print(json.dumps(row),flush=True)
    recent=[r for r in rows if r['stage']==name]
    return max(configs,key=lambda c:statistics.median(r['kernel_rate'] for r in recent
               if (r['threads'],r['chunk'],r['batch'])==c))

if args.confirm:
    previous=json.loads((OUT/'scheduling.json').read_text());rows.extend(previous)
    last=[r for r in previous if r['stage']=='batches']
    configs=list(dict.fromkeys((r['threads'],r['chunk'],r['batch']) for r in last))
    winner=max(configs,key=lambda c:statistics.median(r['kernel_rate'] for r in last
                  if (r['threads'],r['chunk'],r['batch'])==c))
    if winner==(34,16,16384):
        # Recheck the closest screen contender once; do not benchmark indefinitely.
        winner=sorted(configs,key=lambda c:statistics.median(r['kernel_rate'] for r in last
                  if (r['threads'],r['chunk'],r['batch'])==c),reverse=True)[1]
    compare('confirmation',[(34,16,16384),winner],count=1500000,trials=5,start=82000000)
else:
    t,_,_=compare('threads',[(t,16,16384) for t in (16,18,24,30,34)])
    t,k,b=compare('chunks',[(t,k,16384) for k in (16,64,128)])
    compare('batches',[(t,k,b) for b in (4096,8192,16384)])
