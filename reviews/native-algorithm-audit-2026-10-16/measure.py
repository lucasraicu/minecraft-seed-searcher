import sys,json,time,subprocess,random,resource,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'));BASE=Path(__file__).resolve().parent
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype,seeds_np
if len(sys.argv)>1:
 arm,threads,batch,first,count=sys.argv[1:];threads,batch,first,count=map(int,(threads,batch,first,count));p=Prototype(BASE/arm,dynamic_v3_blueprint_config())
 with p.sweep(seeds_np(99000000,99001024,81271),threads,retention='survivors'):pass
 p.lib.nb_diag_reset();start=time.perf_counter();native=0;retained=0
 for i in range(first,first+count,batch):
  with p.sweep(seeds_np(i,min(i+batch,first+count),81271),threads,retention='survivors') as b:native+=b.native_seconds;retained+=b.pointer.retained_anchors
 elapsed=time.perf_counter()-start;diag=p.ffi.new('uint64_t[12]');p.lib.nb_diag_get(diag)
 print(json.dumps(dict(arm=arm,threads=threads,batch=batch,first=first,count=count,seconds=elapsed,native_seconds=native,rate=count/elapsed,retained=retained,diag=list(diag),peak_rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)))
else:
 jobs=[(a,34,16384,30000000+r*65536,65536) for r in range(3) for a in ('baseline','order','chunk64','no-preflight')];random.Random(7).shuffle(jobs)
 jobs += [('baseline',t,b,31000000,32768) for t,b in [(1,16384),(8,16384),(18,16384),(34,1024),(34,4096),(34,32768)]]
 with (BASE/'measurements.jsonl').open('w') as f:
  for job in jobs:
   p=subprocess.run([sys.executable,__file__,*map(str,job)],capture_output=True,text=True)
   if p.returncode:row=dict(job=job,error=p.stderr)
   else:row=json.loads(p.stdout.strip().splitlines()[-1])
   f.write(json.dumps(row)+'\n');f.flush();print(json.dumps(row),flush=True)
