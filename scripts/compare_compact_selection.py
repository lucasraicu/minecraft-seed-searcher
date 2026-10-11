"""Bounded four-arm lower32 experiment with charged CPU and disjoint pools."""
import copy
import hashlib
import json
from pathlib import Path
import time
import numpy as np

from seed_search.backend import raw_layout, sweep_raw
from seed_search.realm.config import default_config
from seed_search.realm.capabilities import identity, report
from seed_search.realm.raw import FAMILIES, NETHER_ENVELOPE, nether_center_coverage, _score
from seed_search.realm.runner import run_scan, _seed
from seed_search.realm.siblings import run_adaptive
from seed_search.realm.store import RealmStore

OUT=Path('runs/compact-implementation-2026-10-10/selection')
POOLS={'tuning':[0x01230000,0x23450000,0x45670000,0x67890000,0x89AB0000,0xABCD0000,0xCDEF0000,0xEF010000],
       'holdout':[0x13570000,0x35790000,0x579B0000,0x79BD0000,0x9BDF0000,0xBDF10000,0xDF130000,0xF1350000]}

def h(key,low):return hashlib.sha256(f'{key}:{low}'.encode()).digest()

def observations(path,parent_cpu):
 with RealmStore(path,resume=True) as store:
  values=list(store.iter_results())
 overhead=parent_cpu/max(1,len(values))
 return [{'seed':r['seed'],'low32':int(r['seed'])&0xffffffff,
          'anchors':sum(a['qualification']=='PREDICTED' for a in r['anchors']),
          'qualified':int(any(a['qualification']=='PREDICTED' for a in r['anchors'])),
          'cpu':r['worker_cpu_seconds']+overhead,'run':str(path)} for r in values]

def main():
 OUT.mkdir(parents=True,exist_ok=True);cfg=default_config();records=[];pools={}
 for pool,starts in POOLS.items():
  lows=[start+i for start in starts for i in range(512)]
  begin=time.perf_counter();cpu=time.process_time()
  counts=np.concatenate([sweep_raw(start,512,FAMILIES,18,mode='capped') for start in starts])
  raw_cpu=time.process_time()-cpu;raw_wall=time.perf_counter()-begin
  begin=time.perf_counter();cpu=time.process_time()
  coverage=[nether_center_coverage([raw_layout(low,t,NETHER_ENVELOPE) for t in ('fortress','bastion')]) for low in lows]
  feature_cpu=time.process_time()-cpu;feature_wall=time.perf_counter()-begin
  pool_record={'lows':lows,'raw_counts':counts.tolist(),'coverage':coverage,'raw_cpu':raw_cpu,'raw_wall':raw_wall,
               'feature_cpu':feature_cpu,'feature_wall':feature_wall,'presence_missing':int((counts==0).any(axis=1).sum())}
  pools[pool]=pool_record;(OUT/f'{pool}-pool.json').write_text(json.dumps(pool_record)+'\n')
  for key in ('allocation-0','allocation-1','allocation-2'):
   random=sorted(lows,key=lambda low:h(key,low))
   ranked=sorted(range(len(lows)),key=lambda i:(-_score(counts[i]),lows[i]))
   geo=sorted(range(len(lows)),key=lambda i:(-coverage[i]['fraction'],lows[i]))
   def chosen(order):
    reserve=random[:52];return reserve+[lows[i] for i in order if lows[i] not in set(reserve)][:204]
   arms={'uniform':random[:256],'legacy':chosen(ranked),'geometry':chosen(geo)}
   # Counterbalance the order across allocation keys.
   order=['independent','uniform','legacy','geometry'];shift=int(key[-1]);order=order[shift:]+order[:shift]
   for arm in order:
    root=OUT/f'{pool}-{key}-{arm}';begin=time.perf_counter();cpu=time.process_time()
    if arm=='independent':
     manifest=[str(_seed((1000000 if pool=='tuning' else 2000000)+int(key[-1])*10000+i,cfg['search'])) for i in range(1408)]
     run_cfg=copy.deepcopy(cfg);run_cfg['search'].update(sequence='manifest',manifest_seeds=manifest)
     root.mkdir(parents=True,exist_ok=True);(root/'compatibility.json').write_text(json.dumps(report(run_cfg))+'\n')
     status=run_scan(run_cfg,root,len(manifest),workers=30,identity={'config':run_cfg,'backend':identity(),'policy':'independent-control'},allow_prediction_scale=True)
     parent=time.process_time()-cpu;rows=observations(root,parent);rounds=[];selection_cpu=0.
    else:
     allocation_start=time.process_time()
     summary=run_adaptive(cfg,root,arms[arm],budget=4096,key=f'{pool}:{key}',workers=30)
     allocation_cpu=time.process_time()-allocation_start
     rows=[]
     for r in summary['rounds']:rows+=observations(Path(r['run']),r['parent_cpu_seconds'])
     parent=allocation_cpu
     child_parent=sum(r['parent_cpu_seconds'] for r in summary['rounds'])
     selection_cpu=max(0.,parent-child_parent)+(raw_cpu if arm in ('legacy','geometry') else 0)+(feature_cpu if arm=='geometry' else 0)
     rounds=summary['rounds']
    record={'pool':pool,'key':key,'arm':arm,'seconds':time.perf_counter()-begin,
            'inputs':len(rows),'upfront_cpu':selection_cpu,'total_cpu':sum(r['cpu'] for r in rows)+selection_cpu,
            'qualified_seeds':sum(r['qualified'] for r in rows),'qualifying_anchors':sum(r['anchors'] for r in rows),
            'rows':rows,'rounds':rounds,'raw_feature_charge':'entire bounded pool charged to each ranked arm and allocation key; no amortization'}
    records.append(record);(OUT/'experiment.json').write_text(json.dumps({'backend':identity(),'records':records},indent=2)+'\n')
    print(json.dumps({k:v for k,v in record.items() if k not in ('rows','rounds')}),flush=True)
 analysis=[];rng=np.random.default_rng(20261010)
 for pool in POOLS:
  for key in ('allocation-0','allocation-1','allocation-2'):
   cohort=[r for r in records if r['pool']==pool and r['key']==key];budget=min(r['total_cpu'] for r in cohort)
   selected={}
   for arm in cohort:
    spent=arm['upfront_cpu'];rows=[]
    for row in arm['rows']:
     if spent+row['cpu']>budget:break
     rows.append(row);spent+=row['cpu']
    clusters={}
    for row in rows:clusters[row['low32']]=clusters.get(row['low32'],0)+row['anchors']
    selected[arm['arm']]={'inputs':len(rows),'cpu_budget':budget,'charged_cpu':spent,'qualifying_anchors':sum(r['anchors'] for r in rows),
                          'qualified_seeds':sum(r['qualified'] for r in rows),'clusters':list(clusters.values())}
   ref=selected['independent'];ratios={}
   for name in ('uniform','legacy','geometry'):
    a=np.array(selected[name]['clusters']);b=np.array(ref['clusters']);draw=[]
    for _ in range(2000):
     denominator=rng.choice(b,len(b)).sum() if len(b) else 0
     if denominator:draw.append((rng.choice(a,len(a)).sum() if len(a) else 0)/denominator)
    ratios[name]={'ratio':selected[name]['qualifying_anchors']/max(1,ref['qualifying_anchors']),
                  'layout_cluster_bootstrap_95':np.quantile(draw,[.025,.975]).tolist() if draw else None}
   analysis.append({'pool':pool,'key':key,'common_cpu_budget':budget,'arms':selected,'ratios':ratios})
 result={'backend':identity(),'records':records,'analysis':analysis,
         'accounting':'Ordered full64 prefixes at common measured CPU budget; parent CPU apportioned equally per input; entire raw/feature CPU upfront. Prefix accounting is an analysis truncation of bounded completed runs, not a live CPU stop.',
         'adoption':'Independent default retained unless heldout >=20% advantage, interval excludes no advantage and matched terrain supports it; no verified-world advantage without actual BDS outcomes.'}
 (OUT/'experiment.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
