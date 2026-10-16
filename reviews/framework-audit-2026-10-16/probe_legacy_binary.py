import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype
try:
 p=Prototype(ROOT/'runs/dynamic-baseline-1664/native',dynamic_v3_blueprint_config())
 with p.sweep([456],fixtures=[(0,0,-1)]) as b:
  a=b.pointer.results[0].anchors[0] if b.pointer.results[0].nanchors else None
  out={'accepted_v3_config':True,'center':[a.x,a.z] if a else None,'native_score':a.score if a else None}
  try:out['record_anchors']=len(b.records()[0]['anchors'])
  except Exception as exc:out['record_error']=str(exc)
except Exception as exc:out={'error':str(exc)}
print(json.dumps(out,indent=2))
