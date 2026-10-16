import sys,json,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype,semantic_record
from seed_search.realm.blueprint import evaluate_dynamic_seed
seeds=[-3336796033057908633,7468236279383609753]
for palette in ('default','empty'):
 cfg=dynamic_v3_blueprint_config()
 if palette=='empty':cfg['biomes']['required_families']=[]
 p=Prototype(None,cfg)
 for seed in seeds:
  row={'seed':str(seed),'palette':palette};t=time.perf_counter()
  for mode in ('full','survivors'):
   try:
    with p.sweep([seed],retention=mode) as b:
     native=[{'center':[a.x,a.z],'score':a.score,'hub':a.hub_bonus,'spread':a.village_spread_bonus,'scenic':a.scenic_bonus,'treasure':a.treasure_bastion} for i in range(b.pointer.result_count) for a in [b.pointer.results[i].anchors[j] for j in range(b.pointer.results[i].nanchors)]]
     row[mode]={'native':native}
     records=b.records() if mode=='full' else list(b.retained_records())
     row[mode]['records']=[{'anchors':[{'center':a['evaluation_center'],'score':a['baseline_score'],'components':a['ranking']['components']} for a in r['anchors']]} for r in records]
   except Exception as exc:row[mode]={'error':str(exc)}
  try:
   rec=evaluate_dynamic_seed(0,seed,cfg)
   row['independent']=[{'center':a['evaluation_center'],'score':a['baseline_score'],'components':a['ranking']['components']} for a in rec['anchors']]
  except Exception as exc:row['independent_error']=str(exc)
  row['seconds']=time.perf_counter()-t
  print(json.dumps(row),flush=True)
