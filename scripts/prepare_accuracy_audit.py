"""Deterministic coverage plan; external observations are collected separately."""
import ctypes
import json
import random
from pathlib import Path
import numpy as np
from seed_search.backend import Backend, biome_name, lib
import seed_search._native as native

OUT = Path('runs/accuracy-audit')
SEEDS = ['12345', '0', '-1', '4294979641']
dll = ctypes.CDLL(native.__file__)
dll.biomeExists.argtypes = [ctypes.c_int, ctypes.c_int]
dll.biomeExists.restype = ctypes.c_int
inventory = [dict(id=i, name=biome_name(i)) for i in range(256) if dll.biomeExists(lib.ss_model(), i)]
nether_ids = {8, 170, 171, 172, 173}
end_ids = {9, 40, 41, 42, 43}
for b in inventory:
    b['dimension'] = -1 if b['id'] in nether_ids else 1 if b['id'] in end_ids else 0
points = []
covered = set()
grid_coverage = {}
for seed in SEEDS:
    with Backend(seed) as b:
        candidates = {}
        for y in (63, -51):
            g = b.grid(-32768, -32768, 256, 256, 256, y=y)['biomes']
            grid_coverage[f'{seed}:{y}'] = [biome_name(int(i)) for i in np.unique(g)]
            for bid in np.unique(g):
                indices = np.argwhere(g == bid).tolist()
                rng = random.Random(f'{seed}:{y}:{bid}')
                rng.shuffle(indices)
                candidates[(int(bid), y)] = [(int(x)*256-32768, int(z)*256-32768) for z,x in indices[:8]]
        flat = [xz for (bid,y),cs in candidates.items() if y==63 for xz in cs]
        hs,bs = b.heights(flat, vertical_step=1)
        surface_candidates = {}
        for xz,h,bid in zip(flat,hs,bs):
            surface_candidates.setdefault(int(bid),[]).append((xz,int(h)))
        for bid,cs in sorted(surface_candidates.items()):
            key=(0,'surface',bid)
            # Two seeds per biome where possible; three for common terrain types.
            limit=2
            prior=sum(p['biome_id']==bid and p['mode']=='surface' for p in points)
            if prior>=limit: continue
            (x,z),h=cs[0]
            points.append(dict(seed=seed,dimension=0,mode='surface',x=x,z=z,local_height=h,biome_id=bid,local_biome=biome_name(bid)))
            covered.add(key)
        for bid in (174,175,183,187):
            key=(0,'bottom',bid)
            if key in covered or (bid,-51) not in candidates: continue
            x,z=candidates[(bid,-51)][0]
            points.append(dict(seed=seed,dimension=0,mode='bottom',sample_y=-51,x=x,z=z,biome_id=bid,local_biome=biome_name(bid)))
            covered.add(key)
        # Stratified terrain extras across water, coastline, plains and peaks.
        rng=random.Random(seed)
        extra=[(rng.randrange(-5000,5001),rng.randrange(-5000,5001)) for _ in range(10)]
        hs,bs=b.heights(extra,vertical_step=1)
        for (x,z),h,bid in zip(extra,hs,bs):
            points.append(dict(seed=seed,dimension=0,mode='surface',x=x,z=z,local_height=int(h),biome_id=int(bid),local_biome=biome_name(int(bid)),purpose='random_terrain'))
        found={}
        for z in range(-2048,2049,128):
            for x in range(-2048,2049,128):
                bid=b.biome(x,33,z,-1)
                found.setdefault(bid,(x,z))
        for bid,(x,z) in sorted(found.items()):
            points.append(dict(seed=seed,dimension=-1,mode='nether',sample_y=33,x=x,z=z,biome_id=bid,local_biome=biome_name(bid)))
(OUT/'plan.json').write_text(json.dumps(dict(schema_version=1,seeds=SEEDS,inventory=inventory,grid_coverage=grid_coverage,points=points),indent=2)+'\n')
print(json.dumps(dict(points=len(points),surface_types=sorted({p['local_biome'] for p in points if p['mode']=='surface'}),missing_inventory=[v for v in inventory if v['dimension']!=1 and v['id'] not in {p['biome_id'] for p in points}]),indent=2))
