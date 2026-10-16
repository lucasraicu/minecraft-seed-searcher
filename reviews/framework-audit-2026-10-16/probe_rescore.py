import sys,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype
from seed_search.realm.reports import _candidate_rescore
cfg=dynamic_v3_blueprint_config();cfg['biomes']['required_families']=[]
p=Prototype(None,cfg)
with p.sweep([-3336796033057908633],retention='survivors') as b:
 a=list(b.retained_records())[0]['anchors'][0]
 orig=copy.deepcopy(a)
 try:
  r=_candidate_rescore(a,cfg,'audit-same-policy')
  out={'before':orig['baseline_score'],'after':r['baseline_score'],'before_components':orig['ranking']['components'],'after_components':r['ranking']['components'],'screening_revision_after':r['screening_revision']}
 except Exception as exc:out={'error':str(exc)}
print(json.dumps(out,indent=2))
