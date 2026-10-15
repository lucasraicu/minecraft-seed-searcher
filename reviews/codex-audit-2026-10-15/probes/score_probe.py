import sys,random
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'src'))
from seed_search.realm.native_batch import Prototype,NAMES
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.realm.blueprint import dynamic_score,DYNAMIC_LUXURIES
p=Prototype('runs/dynamic-baseline-1664/native',dynamic_blueprint_config())
cases=0
for mask in [0,1023,*[1<<k for k in range(10)],*[random.Random(i).randrange(1024) for i in range(32)]]:
 for i in range(256):p.policy.bonus_biome_members[i]=mask
 with p.sweep([123],fixtures=[(0,0,-1)],retention='survivors') as b:
  a=b.pointer.results[0].anchors[0]
  counts={n:a.observations[k].viable.n for k,n in enumerate(NAMES)}
  counts['mansion']=sum(a.observations[0].mansion_ids[k]==p.policy.dark_id for k in range(a.observations[0].viable.n));counts['stronghold']=a.stronghold_count
  names=[members[0] for k,(_,members) in enumerate(DYNAMIC_LUXURIES) if mask&(1<<k)]
  assert a.score==dynamic_score(counts,names,a.hub_bonus),(mask,a.score,dynamic_score(counts,names,a.hub_bonus));cases+=1
for i in range(256):p.policy.bonus_biome_members[i]=0
for n in range(1,7):
 p.policy.goals[3]=n
 with p.sweep([123],fixtures=[(0,0,3)],fixture_deltas=[1],retention='survivors') as b:
  # Monument is strict: lowering below target rejects; use goal+2 fixtures instead.
  assert b.pointer.result_count==0
print('native/Python luxury-mask score agreement',cases,'cases; strict monument rejection',6,'cases')
