import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from seed_search.realm.dynamic import nether_palette,nether_bounds
from seed_search.realm.bounds import contains
from seed_search.backend import biome_catalog
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype
ids={r['name']:r['id'] for r in biome_catalog()}
class Fake:
 def sample(self,points,dimension):
  # Fifth family exists ONLY at the excluded east boundary.
  names=('nether_wastes','crimson_forest','warped_forest','soul_sand_valley')
  return [ids['basalt_deltas'] if x>=512 else ids[names[(x//64+z//64)%4]] for x,y,z in points]
pal=nether_palette(Fake(),(0,0),512);bounds=nether_bounds((0,0),512)
out={'bounds':bounds,'sample_count':pal['sample_count'],'outside_samples':sum(not contains((r['coordinate'][0],r['coordinate'][2]),bounds) for r in pal['sampling']['samples']),'missing_families':pal['missing_families'],'basalt_witness':pal['witnesses']['basalt_deltas']['coordinate']}
cfg=dynamic_v3_blueprint_config();cfg['biomes']['required_families']=[];p=Prototype(None,cfg)
with p.sweep([-3336796033057908633],retention='survivors') as b:
 a=list(b.retained_records())[0]['anchors'][0]
 print('ANCHOR KEYS', [k for k in a if 'nether' in k],file=sys.stderr)
 npal=a['nether_biomes']
 bounds=nether_bounds(a['evaluation_center'],512)
 out['natural_native_record']={'bounds':bounds,'samples':npal['sample_count'],'outside_samples':sum(not contains((r['coordinate'][0],r['coordinate'][2]),bounds) for r in npal['sampling']['samples']),'outside_witnesses':{k:r['coordinate'] for k,r in npal['witnesses'].items() if not contains((r['coordinate'][0],r['coordinate'][2]),bounds)}}
print(json.dumps(out,indent=2))
