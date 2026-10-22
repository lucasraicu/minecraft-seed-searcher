"""Read-only saved-world candidate inventory; predictions are not variant controls."""
import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.registry import digest
root=Path('/Users/lucasraicu/.local/share/antigravity-worker-mcp/spawn-correction-approved-20261021/catalog')
store=AutomationStore(root);manifest=store.snapshot();started=time.monotonic();worlds=[]
for entry in manifest['worlds']:
 if time.monotonic()-started>120:raise TimeoutError('Read-only inventory exceeded120s')
 obs=store.artifacts.get_json(entry['artifact'])['observation'];inv=obs.get('realm',{}).get('inventory',{});igloo=inv.get('igloo_basement',{});bastion=inv.get('bastion_variant',{});rows=[]
 if igloo.get('status')in ('complete','partial'):
  positive={tuple(p) for p in igloo.get('points',[])}
  for point in obs['structures'].get('structure.igloo',[]):
   result=True if tuple(point)in positive else (False if igloo['status']=='complete' else None)
   if result is not None:rows.append(dict(feature='igloo_basement',dimension='overworld',start=point,predicted=result,method_id=igloo['method_id']))
 for x,z,variant in bastion.get('points',[]):rows.append(dict(feature='bastion_treasure',dimension='nether',start=[x,z],predicted=variant==2,predicted_variant=variant,method_id=bastion['method_id']))
 if rows:worlds.append(dict(world_id=entry['world_id'],seed=entry['identity']['seed'],observation_id=entry['observation_id'],candidates=rows))
counts={}
for feature in ('igloo_basement','bastion_treasure'):
 for predicted in (True,False):counts[feature+':'+str(predicted)]=sum(any(c['feature']==feature and c['predicted']==predicted for c in w['candidates']) for w in worlds)
report=dict(source_snapshot=digest(manifest),saved_worlds=len(manifest['worlds']),candidate_worlds=len(worlds),predicted_world_counts=counts,actual_independent_control_worlds=0,seconds=time.monotonic()-started,worlds=worlds)
Path(__file__).with_name('VARIANT_CANDIDATES.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='worlds'}))
