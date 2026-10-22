"""Replay all saved summary facts through typed masks, plus stratified derivation."""
from pathlib import Path
import json,sys,time,copy,collections
R=Path(__file__).resolve().parents[2];E=Path(__file__).parent;B=Path.home()/'.local/share/antigravity-worker-mcp/pre-gpu-readiness-approved-20261022';sys.path.insert(0,str(R/'src'))
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.read_views import pack_masks,candidate_layouts
from seed_search.catalog.summaries import summarize_v3
from seed_search.catalog.summaries_fast import summarize_v3 as fast
from seed_search.catalog.registry import digest
store=AutomationStore(B/'catalog-copy');m=store.snapshot();counts=collections.Counter();cohort=[];started=time.monotonic();world_meta=[]
for entry in m['worlds']:
 bundle=store._bundle(store.artifacts.get_json(entry['artifact']),entry);obs=bundle['observation'];summaries=bundle['summaries'];reg=bundle.get('registry',m['registry'])
 assert digest(obs)==entry['observation_id']
 structures=[f['id']for f in reg['features']if f['kind']=='structure_count']
 for side in (2048,4096,8192):
  rows=[r for r in summaries if r['border_side']==side];header,columns=pack_masks(rows,reg)
  for fi,fid in enumerate(structures):
   for scope in range(4):
    for minimum in (1,3,32):
     expected={r['layout_id']for r in rows if r['features'][fid]['counts'][scope]>=minimum or not r['features'][fid]['complete'][scope]}
     assert candidate_layouts(header,columns,[(fid,scope,minimum)])==expected
     counts['mask_comparisons']+=1
  counts['summary_rows']+=len(rows)
 counts['worlds']+=1
 world_meta.append(dict(entry=entry,points=sum(len(v)for v in obs['biomes'].values()),anchors=len(obs['anchors']),variants=sum(len(obs['structures'].get(f,[]))for f in ('structure.igloo','structure.bastion'))))
 if counts['worlds']%50==0:print('all-fact masks',counts['worlds'],flush=True)
# Deterministic strata include source-sorted coverage plus density/spawn/variant extremes.
chosen={v['entry']['world_id']:v for v in world_meta[::max(1,len(world_meta)//20)]}
for key in ('points','anchors','variants'):
 for v in sorted(world_meta,key=lambda v:v[key])[:2]+sorted(world_meta,key=lambda v:v[key])[-2:]:chosen[v['entry']['world_id']]=v
for v in chosen.values():
 entry=v['entry'];bundle=store._bundle(store.artifacts.get_json(entry['artifact']),entry);obs=bundle['observation'];reg=bundle.get('registry',m['registry']);ext=store.artifacts.get_json(bundle['extension_artifact'])if bundle.get('extension_artifact')else None
 a=summarize_v3(obs,extension=ext,registry=reg);b=fast(obs,extension=ext,registry=reg);assert a==b,entry['world_id']
 cohort.append(dict(world_id=entry['world_id'],points=v['points'],anchors=v['anchors'],variants=v['variants'],rows=len(a),exact_digest=digest(a)))
 print('derivation strata',len(cohort),len(chosen),flush=True)
report=dict(status='PASS',all_saved_facts=dict(counts),derivation_cohort=cohort,seconds=time.monotonic()-started,snapshot_id=digest(m),scope='All222currentworlds/fullsourceboundsummaryfacts;allstructuremasks/scopes/thresholds;deterministicstratifiedoriginal-vs-fastfullsummaryreplay;no base extraction/new search')
(E/'SAVED_FACT_REPLAY.json').write_text(json.dumps(report,indent=2)+'\n');print('saved facts PASS',flush=True)
