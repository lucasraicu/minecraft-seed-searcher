from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.cwd()/'src'))
from seed_search.realm.dynamic import candidate_centers,overworld_bounds,nether_bounds,hub_bonus,OPTIONAL_NAMES
from seed_search.realm.blueprint import dynamic_score
from seed_search.realm.bounds import contains
from seed_search.realm.config import dynamic_blueprint_config
c=dynamic_blueprint_config()
invs={n:[(0,i*16) for i in range(g)] for n,g in {**c['structures']['minimum_counts'],**c['structures']['nether_minimum_counts']}.items()}
invs['swamp_hut']=[(840,0)]
strict={'stronghold','mansion','monument','outpost','fortress','bastion'}
ideals={n:g for n,g in c['structures']['minimum_counts'].items() if n not in strict}
rows=candidate_centers(invs,c['structures']['hard_floors'],ideals,c['search']['density_weights'])
def key(r,correct):
 counts=dict(r.counts)
 if correct:
  for name in OPTIONAL_NAMES:counts[name]=sum(contains(p,overworld_bounds(r.center)) for p in invs.get(name,[]))
 return (len(r.deficits),-dynamic_score(counts,[],hub_bonus(invs,r.center)),round(r.radial,6),sum(x*x for x in r.center),*r.center)
for correct in (False,True):
 r=min(rows,key=lambda r:key(r,correct));print(json.dumps(dict(correct_counts=correct,center=r.center,key=key(r,correct),counts=r.counts)))
r=next(r for r in rows if r.center==(16,48));print('candidate16,48',r,'actual hut',contains((840,0),overworld_bounds(r.center)))
# Exhaustively check 1D structure and lattice membership in every integer interval.
from seed_search.realm.dynamic import _LAT,_axis_events
for nether,half,points in [(False,832,range(-1984,1985,64)),(True,416,range(-512,513,64))]:
 events=_axis_events(points,half,nether)
 for lo,hi in zip(events,events[1:]):
  ref=None
  for x in range(lo,hi):
   bounds=nether_bounds((x,0)) if nether else overworld_bounds((x,0))
   members=tuple(p for p in points if bounds[0]<=p<bounds[2])
   if ref is None:ref=members
   assert ref==members
print('all integer lattice intervals invariant; unique clipped events',len(_LAT))
