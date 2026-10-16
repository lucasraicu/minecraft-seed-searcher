import json,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'));b=Path(__file__).resolve().parent
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype
out=[]
for arm in ('baseline','stream','tight','exhaustive'):
 cfg=dynamic_v3_blueprint_config();cfg['biomes']['required_families']=[];p=Prototype(b/arm,cfg)
 for fixture in (False,True):
  kw=dict(fixtures=[(0,0,-1)]) if fixture else {};t=time.perf_counter()
  with p.sweep([-3336796033057908633],retention='survivors',**kw) as batch:
   rows=[dict(center=[a.x,a.z],score=a.score) for i in range(batch.pointer.result_count) for a in [batch.pointer.results[i].anchors[j] for j in range(batch.pointer.results[i].nanchors)]]
  out.append(dict(arm=arm,fixture=fixture,rows=rows,seconds=time.perf_counter()-t))
(b/'survivors.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
