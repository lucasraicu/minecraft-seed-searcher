"""Exact frozen-lattice decisions, deferred completion and thread parity."""
import json
from pathlib import Path
import time
import numpy as np
from seed_search.backend import Backend,configure_native_threads
from seed_search.realm.store import RealmStore
from seed_search.realm.config import default_config
from seed_search.realm.inventory import execute_inventory
from seed_search.realm.sampling import grid_points

ROOT=Path('runs/compact-implementation-2026-10-10')

def main():
 cfg=default_config();cfg['biomes'].update(lattice='border',refinement_budget=0);checks=0;differences=[];completion=[];changes={}
 for cohort in ('tuning','holdout'):
  def values(name):
   report=json.loads((ROOT/name/'benchmark.json').read_text())[0]
   with RealmStore(Path(report.get('path',ROOT/name/'trial-0')),resume=True) as store:
    return {a['id']:a for a in store.iter_candidates()},list(store.iter_results())
  ref,ref_rows=values(f'final-reference-border-{cohort}')
  fast,fast_rows=values(f'final-eligibility-border-{cohort}')
  world,world_rows=values(f'final-eligibility-world-{cohort}')
  assert list(r['seed'] for r in ref_rows)==list(r['seed'] for r in fast_rows)==list(r['seed'] for r in world_rows)
  assert ref.keys()==fast.keys()==world.keys()
  for key,a in ref.items():
   b=fast[key];checks+=1
   for field in ('qualification','pending_reasons','stronghold','bounds'):
    if a[field]!=b[field]:differences.append({'id':key,'field':field})
   for family,obs in b['required_structures'].items():
    if obs.get('verification')=='DEFERRED':continue
    if any(p not in a['required_structures'][family]['predicted_viable'] for p in obs['predicted_viable']):differences.append({'id':key,'family':family,'issue':'witness not in full scan'})
  changes[cohort]=[{'id':key,'from':ref[key]['qualification'],'to':world[key]['qualification'],
                   'old_reasons':ref[key]['pending_reasons'],'new_reasons':world[key]['pending_reasons']} for key in ref if ref[key]['qualification']!=world[key]['qualification']]
  selected=[a for a in ref.values() if a['qualification']=='PREDICTED'][:32]
  for a in selected:
   b=fast[a['id']];begin=time.perf_counter();cpu=time.process_time()
   with Backend(b['seed']) as backend:
    structures=execute_inventory(b,cfg,'structures',backend)
    biomes=execute_inventory(b,cfg,'biomes',backend)
   checks+=1
   for field in ('raw_detections','raw_names','primary_families','wooded_families','family_bonuses','variant_bonuses','score','sample_count'):
    if biomes['biomes'].get(field)!=a['biomes'].get(field):differences.append({'id':a['id'],'completion_field':field})
   for name,old in a['optional_structures'].items():
    if name=='buried_treasure':continue
    new=structures['optional_structures'][name]
    if bool(old['predicted_viable'])!=bool(new['predicted_viable']):differences.append({'id':a['id'],'optional':name})
   observed=biomes['biomes']['score']+sum(v['bonus'] for name,v in structures['optional_structures'].items() if name!='buried_treasure')
   if observed!=a['baseline_score']:differences.append({'id':a['id'],'score':observed,'reference':a['baseline_score']})
   completion.append({'id':a['id'],'seconds':time.perf_counter()-begin,'cpu_seconds':time.process_time()-cpu,
                      'new_treasure_bonus':structures['optional_structures']['buried_treasure']['bonus'],
                      'families':len(structures['structure_inventory']),'supplemental_dimensions':list(biomes['supplemental_biome_inventories'])})
 thread_checks=0
 for seed in (-1,0,12345,-2**63):
  points=grid_points((-2000,-2000,2000,2000),64,63,'world');expected={}
  for threads in (1,4,18):
   configure_native_threads(threads)
   with Backend(seed) as backend:
    for dimension in (0,-1,1):
     actual=backend.biome_points(points,dimension)
     if threads==1:expected[dimension]=actual
     else:assert np.array_equal(actual,expected[dimension]);thread_checks+=len(points)
 configure_native_threads(1)
 report={'decision_anchor_checks':checks,'differences':differences,'sampling_revision_changes':changes,'completion_sample':completion,
         'thread_point_checks':thread_checks,'scope':'Frozen-lattice exact decisions and canonical inventory/old score parity. New buried-treasure capability deliberately adds its configured bonus. World-lattice/refinement is a separately versioned sampling revision.'}
 (ROOT/'completion-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'checks':checks,'differences':len(differences),'completion_samples':len(completion),'thread_checks':thread_checks,'lattice_changes':{k:len(v) for k,v in changes.items()}}),flush=True)
 if differences:raise SystemExit(1)

if __name__=='__main__':main()
