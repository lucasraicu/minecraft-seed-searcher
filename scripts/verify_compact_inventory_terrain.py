"""Matched bounded inventory/terrain follow-up of the four selection arms."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time
from seed_search.realm.store import RealmStore
from seed_search.realm.config import default_config
from seed_search.realm.capabilities import identity
from seed_search.realm.inventory import run_inventory,complete_start_audit
from seed_search.realm.terrain import run_terrain

ROOT=Path('runs/compact-implementation-2026-10-10')


def followup(record):
 cfg=default_config();candidates=[]
 paths=[Path(r['run']) for r in record['rounds']] if record['rounds'] else [ROOT/'selection'/f"holdout-{record['key']}-{record['arm']}"]
 for path in paths:
  with RealmStore(path,resume=True) as store:candidates+=list(store.iter_candidates(['PREDICTED']))
 selected=sorted(candidates,key=lambda c:hashlib.sha256(c['id'].encode()).digest())[:2]
 out=ROOT/'terrain-followup-parallel'/f"{record['key']}-{record['arm']}"
 with RealmStore(out,identity={'config':cfg,'backend':identity(),'sample':list(c['id'] for c in selected)}) as store:
  store.configure_range(0,len(selected),len(selected));lease=store.claim_range('sample')
  store.complete_range(*lease,[{'index':i,'seed':c['seed'],'anchors':[{**c,'index':i}]} for i,c in enumerate(selected)])
  begin=time.perf_counter();cpu=time.process_time();inventory=run_inventory(store,cfg)
  inventory.update(cpu_seconds=time.process_time()-cpu,seconds=time.perf_counter()-begin)
  begin=time.perf_counter();cpu=time.process_time();terrain=run_terrain(store,cfg,limit=2)
  terrain.update(cpu_seconds=time.process_time()-cpu,seconds=time.perf_counter()-begin)
  values=list(store.iter_variants());passed={v:sum(x['variant']==v and x['result'].get('geometry_pass',False) for x in values) for v in ('v1','v2')}
  observation=complete_start_audit(store,cfg,selected[0]['id']) if record['key']=='allocation-0' else None
  report={'key':record['key'],'arm':record['arm'],'anchors':list(c['id'] for c in selected),
          'inventory':inventory,'terrain':terrain,'predicted_geometry_passes':passed,
          'variant_results':values,'complete_start_audit_seconds':observation['seconds'] if observation else None,
          'verification':'UNVERIFIED; no actual worlds produced; same two-anchor/eight-refinement V1/V2 budget',
          'run':str(out),'concurrency':'four independent processes, one native thread each; process CPU charged individually'}
  (out/'followup.json').write_text(json.dumps(report,indent=2)+'\n')
  return report


def main():
 experiment=json.loads((ROOT/'selection/experiment.json').read_text());reports=json.loads((ROOT/'inventory-terrain-followup.json').read_text())
 done={(r['key'],r['arm']) for r in reports}
 pending=[r for r in experiment['records'] if r['pool']=='holdout' and (r['key'],r['arm']) not in done]
 with ProcessPoolExecutor(max_workers=4) as pool:
  for future in as_completed([pool.submit(followup,r) for r in pending]):
   report=future.result();reports.append(report)
   (ROOT/'inventory-terrain-followup.json').write_text(json.dumps(reports,indent=2)+'\n')
   print(json.dumps({k:v for k,v in report.items() if k not in ('variant_results','inventory','terrain')}),flush=True)

if __name__=='__main__':main()
