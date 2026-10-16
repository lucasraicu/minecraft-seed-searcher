import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype,seeds_np
p=Prototype(None,dynamic_v3_blueprint_config());out={}
for palette in ('default','empty'):
 cfg=dynamic_v3_blueprint_config()
 if palette=='empty':cfg['biomes']['required_families']=[]
 p=Prototype(None,cfg);seeds=list(range(35));fixtures=[(0,0,m) for m in range(-1,34)]
 results={}
 for mode in ('full','survivors'):
  with p.sweep(seeds,fixtures=fixtures,retention=mode) as b:
   results[mode]={str(int(b.pointer.results[i].seed)):int(b.pointer.results[i].nanchors) for i in range(b.pointer.result_count) if b.pointer.results[i].nanchors}
 out[palette]={'full_equals_compact':results['full']==results['survivors'],'accepted_missing_slots':[int(s)-1 for s in results['survivors']]}
p=Prototype(None,dynamic_v3_blueprint_config());seeds=seeds_np(0,4096,2026101601);results={}
for mode in ('full','survivors'):
 with p.sweep(seeds,threads=1,retention=mode) as b:
  results[mode]={str(int(b.pointer.results[i].seed)):int(b.pointer.results[i].nanchors) for i in range(b.pointer.result_count) if b.pointer.results[i].nanchors}
out['natural4096']={'full_equals_compact':results['full']==results['survivors'],'survivors':len(results['survivors']),'limitations':'Mostly rejection-path coverage; not proof of zero false rejects'}
print(json.dumps(out,indent=2))
