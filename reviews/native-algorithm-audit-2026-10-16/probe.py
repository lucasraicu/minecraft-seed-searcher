import sys,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'));BASE=Path(__file__).resolve().parent
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype,seeds_np
from seed_search.realm.top_tracker import Top50Tracker
out={}
for palette in ('default','empty'):
 cfg=dynamic_v3_blueprint_config()
 if palette=='empty':cfg['biomes']['required_families']=[]
 for arm in ('baseline','no-preflight','order','chunk64'):
  p=Prototype(BASE/arm,cfg);runs=[]
  for threads in (1,4):
   for mode in ('full','survivors'):
    with p.sweep([-3336796033057908633,7468236279383609753],threads,retention=mode) as b:
     rows=[(int(b.pointer.results[i].seed),[(a.x,a.z,a.score) for a in [b.pointer.results[i].anchors[j] for j in range(b.pointer.results[i].nanchors)]]) for i in range(b.pointer.result_count) if b.pointer.results[i].nanchors]
     runs.append(dict(threads=threads,mode=mode,rows=rows))
  out[palette+'-'+arm]=runs
p=Prototype(BASE/'baseline',dynamic_v3_blueprint_config());cases=[]
for missing in range(-1,34):
 with p.sweep([123],fixtures=[(0,0,missing)],retention='survivors') as b:
  scores=[b.pointer.results[i].anchors[j].score for i in range(b.pointer.result_count) for j in range(b.pointer.results[i].nanchors)]
 for cutoff in sorted(set([1,400,600,1250,1251]+([scores[0],scores[0]+1] if scores else []))):
  with p.sweep([123],fixtures=[(0,0,missing)],retention='survivors',cutoff_score=cutoff) as b:
   actual=[b.pointer.results[i].anchors[j].score for i in range(b.pointer.result_count) for j in range(b.pointer.results[i].nanchors)]
  cases.append(dict(missing=missing,cutoff=cutoff,expected=[s for s in scores if s>=cutoff],actual=actual))
out['cutoff_cases']=len(cases);out['cutoff_mismatches']=[x for x in cases if x['expected']!=x['actual']]
# A documented score-only bound requires homogeneous ranking tiers.
t=Top50Tracker(1);t.observe({'seed':'1','ranking_tier':2,'baseline_score':900});out['tier_cutoff']=t.cutoff_score();out['better_tier_lower_score_admitted']=t.observe({'seed':'2','ranking_tier':0,'baseline_score':100})
# Zero identity must not turn into an empty dedup key.
t=Top50Tracker(3);t.observe({'seed':0,'baseline_score':10});t.observe({'seed':0,'baseline_score':10});out['duplicate_numeric_seed_zero_count']=len(t)
(BASE/'probes.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
