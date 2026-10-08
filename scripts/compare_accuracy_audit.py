"""Compare recorded UI predictions to local starts; never infer absence from lists."""
import json, math
from pathlib import Path
from collections import defaultdict
from seed_search.backend import Backend
D=Path('runs/accuracy-audit')
records=[]
for query in json.loads((D/'chunkbase-structures.compact.json').read_text()):
 with Backend(query['seed']) as b:
  for index,x,z in query['results']:
   bounds=(x-160,z-160,x+160,z+160)
   viable=b.structures(query['type'],bounds)
   raw=b.structures(query['type'],bounds,viable=False)
   nearest=lambda ps:min(ps,key=lambda p:math.hypot(p[0]-x,p[1]-z)) if ps else None
   vp,rp=nearest(viable),nearest(raw)
   dist=lambda p:round(math.hypot(p[0]-x,p[1]-z),4) if p else None
   records.append(dict(seed=query['seed'],type=query['type'],chunkbase_index=index,chunkbase_xz=[x,z],local_viable_start=vp,local_raw_start=rp,viable_offset=dist(vp),raw_offset=dist(rp),matched_within_64=vp is not None and dist(vp)<=64))
groups=defaultdict(list)
for r in records:groups[r['type']].append(r)
stats={k:dict(samples=len(rs),matched=sum(r['matched_within_64'] for r in rs),exact=sum(r['viable_offset']==0 for r in rs),max_matched_offset=max((r['viable_offset'] for r in rs if r['matched_within_64']),default=None),raw_only=sum(r['local_viable_start'] is None and r['local_raw_start'] is not None for r in rs)) for k,rs in groups.items()}
(D/'structure-comparison.json').write_text(json.dumps(dict(source_kind='third_party_UI_predictions_not_in_game',version='Bedrock 26.50 - 26.52',source_url='https://www.chunkbase.com/apps/seed-map',matching_rule='nearest local viable start within 64 blocks; diagnostic window ±160 blocks; offsets do not prove identity',statistics=stats,records=records),indent=2)+'\n')
print(json.dumps(stats,indent=2));print('DISAGREEMENTS',json.dumps([r for r in records if not r['matched_within_64']],indent=2))
