"""Recompute the audit from retained evidence; fail on missing or inconsistent observations."""
import hashlib,json,math,statistics
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
def read(name):return json.loads((BASE/name).read_text())
def distribution(values):
 a=sorted(values)
 return {'count':len(a),'p50':statistics.median(a),'p95_nearest_rank':a[math.ceil(.95*len(a))-1],'max':a[-1]}
def main():
 seeds=read('seeds.json');pred=read('predictions.json');cohort=read('bds-cohort.json');metadata=read('persisted-metadata.json');controls=read('controls.json')
 assert len(cohort)==108 and len(seeds['random'])==100 and len(seeds['edge'])==8
 assert [int(r['seed']) for r in cohort]==seeds['all']
 assert [p['seed'] for p in pred]==[r['seed'] for r in cohort]
 byseed={p['seed']:p for p in pred};bymeta={p['label']:p for p in metadata}
 for r in cohort:
  assert r['status']=='observed' and r['clean_shutdown']
  assert [x['phase'] for x in r['rows']]==['world_load','world_tick20','world_tick40']
  assert all(x['players']==0 and x['seed']==r['seed'] and x['spawnRadius']==10 for x in r['rows'])
  assert all(x['defaultSpawn']==r['rows'][0]['defaultSpawn'] for x in r['rows'])
  assert r['rows'][-1]['defaultSpawn']==bymeta[r['label']]['spawn']
  assert r['seed']==bymeta[r['label']]['seed']
  assert byseed[r['seed']]['estimate']==byseed[r['seed']]['repeat_estimate']
 for r in controls:
  assert r['clean_shutdown'] and r['status']=='started_without_observer'
  assert bymeta[r['label']]['spawn']==next(c for c in cohort if c['seed']==r['seed'])['rows'][-1]['defaultSpawn']
 identity=read('identity.json')
 for name,expected in identity['source_sha256'].items():
  local=ROOT/name
  if local.exists():assert hashlib.sha256(local.read_bytes()).hexdigest()==expected,name
 summary={'reference':'BDS 1.26.52.3 default Overworld spawn X/Z, not initial-player placement','world_count':108,'random_count':100,'edge_count':8,'stable_worlds':108,'persisted_metadata_matches':108,'no_pack_controls':len(controls),'initial_player_joins_observed':0,'methods':{}}
 for method in ['estimate','detailed']:
  per=[]
  for r in cohort:
   s=r['rows'][-1]['defaultSpawn'];v=byseed[r['seed']][method]
   per.append({'seed':r['seed'],'predicted':v,'observed_xz':[s['x'],s['z']],'displacement_blocks':math.hypot(v[0]-s['x'],v[1]-s['z'])})
  errors=[r['displacement_blocks'] for r in per]
  summary['methods'][method]={'horizontal_displacement_blocks':distribution(errors),'within_16_blocks':sum(x<=16 for x in errors),'within_64_blocks':sum(x<=64 for x in errors),'exact_xz_matches':sum(x==0 for x in errors),'applySeed_plus_routine_elapsed_ms':distribution([1000*p[method+'_seconds'] for p in pred]),'per_seed':per}
 (BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps({**summary,'methods':{k:{a:b for a,b in v.items() if a!='per_seed'} for k,v in summary['methods'].items()}},indent=2))
if __name__=='__main__':main()
