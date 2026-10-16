"""Matched cohorts for current optimized build versus the prior private build."""
import json,random,statistics,time
from pathlib import Path
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype,seeds_np
root=Path(__file__).resolve().parents[2]
paths={'previous':root/'runs/dynamic-baseline-2048/native',
       'optimized':root/'runs/dynamic-baseline-2048/native-mansion-bound-2026-10-16'}
prototypes={name:Prototype(path,dynamic_v3_blueprint_config()) for name,path in paths.items()}
for prototype in prototypes.values():
    with prototype.sweep(seeds_np(90_000_000,90_001_024,2026101601),34,retention='survivors'):pass
jobs=[(name,start) for start in (40_000_000,40_131_072,40_262_144) for name in paths]
random.Random(41).shuffle(jobs)
rows=[]
for name,start in jobs:
    prototype=prototypes[name]
    began=time.perf_counter()
    for first in range(start,start+131_072,16_384):
        with prototype.sweep(seeds_np(first,first+16_384,2026101601),34,retention='survivors') as batch:
            assert batch.pointer.retained_anchors==0
    elapsed=time.perf_counter()-began
    rows.append({'arm':name,'first':start,'seconds':elapsed,'seeds_per_second':131_072/elapsed,
                 'extension_sha256':prototype.identity['extension_sha256']})
result={'rows':rows,'median_seeds_per_second':{name:statistics.median(row['seeds_per_second'] for row in rows if row['arm']==name) for name in paths}}
print(json.dumps(result,indent=2))
