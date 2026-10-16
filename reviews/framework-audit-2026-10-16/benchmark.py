import sys,time,json,statistics,subprocess,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from seed_search.realm.config import dynamic_v3_blueprint_config,dynamic_v2_blueprint_config
from seed_search.realm.native_batch import Prototype,seeds_np
BASE=Path(__file__).resolve().parent
if len(sys.argv)>1:
 arm=sys.argv[1];count=int(sys.argv[2]);threads=int(sys.argv[3]);first=int(sys.argv[4])
 cfg=dynamic_v2_blueprint_config() if arm=='v2-current' else dynamic_v3_blueprint_config()
 path=BASE/'no-diag-build' if arm=='v3-no-diag' else ROOT/'runs/dynamic-baseline-2048/native'
 p=Prototype(path,cfg)
 with p.sweep(seeds_np(90000000,90001024,2026101601),threads,retention='survivors'):pass
 if hasattr(p.lib,'nb_diag_reset'):p.lib.nb_diag_reset()
 total=0.;retained=0;t=time.perf_counter()
 for start in range(first,first+count,16384):
  with p.sweep(seeds_np(start,min(start+16384,first+count),2026101601),threads,retention='survivors') as b:
   total+=b.native_seconds;retained+=b.pointer.retained_anchors
 elapsed=time.perf_counter()-t
 diag=[]
 if hasattr(p.lib,'nb_diag_get'):
  buf=p.ffi.new('uint64_t[12]');p.lib.nb_diag_get(buf);diag=list(buf)
 print(json.dumps({'arm':arm,'count':count,'first':first,'threads':threads,'batch_size':16384,'run_key':2026101601,'wall_seconds':elapsed,'native_seconds':total,'rate':count/elapsed,'retained':retained,'diagnostics':diag,'binary_sha':p.identity['extension_sha256']}))
else:
 jobs=[(arm,262144,34,10000000+r*262144) for r in range(3) for arm in ('v3-current','v3-no-diag','v2-current')]
 random.Random(42).shuffle(jobs)
 jobs += [('v3-current',32768,1,20000000),('v3-current',32768,18,20000000)]
 out=BASE/'benchmark.jsonl'
 with out.open('w') as f:
  for job in jobs:
   r=subprocess.run([sys.executable,__file__,*map(str,job)],capture_output=True,text=True,check=True)
   row=json.loads(r.stdout.strip().splitlines()[-1]);f.write(json.dumps(row)+'\n');f.flush();print(json.dumps(row),flush=True)
