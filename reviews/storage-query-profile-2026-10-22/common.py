from pathlib import Path
import json,sys,time
from decimal import Decimal
ROOT=Path('/Users/lucasraicu/Downloads/minecraft-seed-searcher');sys.path.insert(0,str(ROOT/'src'))
B=Path(__file__).parent;DATA=B/'catalog-copy';SID='cd76367cbd7a679322048d534821f3017e98c9d7f57e7569568f65183074109d'
REG=json.loads((B/'source-registry.json').read_text())
def structure(feature,radius=1024,at_least=1,rule='required'):
 return dict(rule=rule,kind='structure_count',feature=feature,at_least=at_least,scope=dict(kind='near_base',radius=radius),**(dict(importance=3) if rule=='preferred' else {}))
def request(mode='recommended',side=8192,rows=None):
 return dict(request_revision='catalog-query-v3',evidence_policy='predicted_observations_v3',edition='bedrock',game_build_id='research:26.50',catalog_snapshot_id=SID,world_settings_id='default',dimension='overworld',anchor_mode=mode,border_side=side,fallback_profile='balanced_survival',rows=rows or [])
def cases():
 return [
  ('origin',request('origin',2048)),
  ('broad-recommended',request()),
  ('mixed-variants',request(rows=[structure('structure.igloo_with_basement'),structure('structure.bastion_treasure',256)])),
  ('biome-or',request(rows=[dict(rule='required',kind='biome_witness',any_of=['biome.exact.forest','biome.exact.cherry_grove'],scope=dict(kind='near_base',radius=1024)),structure('structure.village',1024,rule='preferred')])),
  ('selective',request(rows=[structure('structure.village',256,at_least=3),structure('structure.bastion_treasure',64)]))]
def timed(f):
 t=time.perf_counter();c=time.process_time();out=f();return out,dict(wall_seconds=time.perf_counter()-t,cpu_seconds=time.process_time()-c)
def canonical_result(d):
 return {k:v for k,v in d.items() if k not in ['stats','next_cursor']}
def save(name,value):
 (B/name).write_text(json.dumps(value,indent=2,default=lambda x:{'__decimal_exact__':str(x)} if isinstance(x,Decimal) else (_ for _ in ()).throw(TypeError(type(x).__name__)))+'\n')
