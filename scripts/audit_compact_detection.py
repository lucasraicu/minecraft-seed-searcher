"""All exposed structure families and version-active biomes: exact local oracles."""
import argparse
import importlib.util
import json
from pathlib import Path
import statistics
import time

import numpy as np
from seed_search.backend import Backend,STRUCTURES,biome_name,biome_catalog,structure_type,configure_native_threads
from seed_search.realm.config import default_config
from seed_search.realm.runner import _seed
from seed_search.realm.sampling import grid_points

OUT=Path('runs/compact-implementation-2026-10-10')


def main():
    p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,default=64);args=p.parse_args()
    # Load current wrapper first. A frozen binary is used only in this isolated
    # audit process; never import it into a live scheduler/benchmark process.
    path=(OUT/'reference/src/seed_search/_native.abi3.so').resolve()
    spec=importlib.util.spec_from_file_location('frozen._native',path)
    reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
    cfg=default_config();seeds=list(dict.fromkeys([-1,0,1,12345,2**32-1,-2**63]+[_seed(200000+i,cfg['search']) for i in range(args.seeds-6)]))
    data={'seed_manifest':list(map(str,seeds)),'structures':{},'biomes':{},'catalog':biome_catalog(),'checks':0,'differences':[]}
    controls=[(-777,-779,758,756),(-2000,-2000,1999,1999),(-1,-9,7,15),(8,8,8,8)]
    observed={}; biome_times={}; original_points=[]
    for seed in seeds:
        ctx=reference.lib.ss_create(seed&((1<<64)-1))
        with Backend(seed) as backend:
            for name in STRUCTURES:
                row=data['structures'].setdefault(name,{'reference_ms':[],'complete_ms':[],'witness_ms':[],'positive_cases':0,'raw_starts':0,'viable_starts':0,'witnesses':[]})
                for bounds in controls:
                    typ=structure_type(name)
                    cap=((bounds[2]-bounds[0])//16+3)*((bounds[3]-bounds[1])//16+3)+20
                    if name=='stronghold':cap=max(cap,64)
                    result=np.empty((cap,2),np.int32)
                    started=time.perf_counter()
                    n=reference.lib.ss_scan(ctx,typ,*bounds,0 if name=='end_city' else 1,reference.ffi.from_buffer('int[]',result),cap)
                    row['reference_ms'].append(1000*(time.perf_counter()-started))
                    if n<0:raise RuntimeError((name,seed,n))
                    expected=sorted(set(map(tuple,result[:n].tolist())))
                    started=time.perf_counter();full=backend.structures(name,bounds,name!='end_city')
                    row['complete_ms'].append(1000*(time.perf_counter()-started))
                    data['checks']+=1
                    if full!=expected:data['differences'].append({'kind':'full_starts','seed':str(seed),'name':name,'bounds':bounds,'expected':expected,'actual':full})
                    raw=backend.structures(name,bounds,False)
                    viable=backend.structures(name,bounds,True)
                    row['raw_starts']+=len(raw);row['viable_starts']+=len(viable);row['positive_cases']+=bool(viable)
                    if name!='stronghold':
                        started=time.perf_counter();point=backend.structure_first(name,bounds)
                        row['witness_ms'].append(1000*(time.perf_counter()-started));data['checks']+=1
                        if bool(point)!=bool(viable) or (point is not None and point not in viable):
                            data['differences'].append({'kind':'witness','seed':str(seed),'name':name})
                        if point and len(row['witnesses'])<8:row['witnesses'].append({'seed':str(seed),'coordinate':point,'bounds':bounds})
            # Dense bounded observation sweep with surface and cave layers.
            surface=grid_points((-2000,-2000,2000,2000),64,63,'world')
            for dimension,ys in ((0,(-48,-16,63,128)),(-1,(33,)),(1,(63,))):
                for y in ys:
                    points=surface.copy();points[:,1]=y
                    started=time.perf_counter();actual=backend.biome_points(points,dimension);elapsed=time.perf_counter()-started
                    if dimension in (0,-1):
                        ref=np.empty(len(points),np.int32)
                        reference.lib.ss_biome_points(ctx,dimension,reference.ffi.from_buffer('int[]',points),len(points),reference.ffi.from_buffer('int[]',ref))
                        data['checks']+=len(points)
                        mismatch=np.flatnonzero(ref!=actual)
                        if len(mismatch):data['differences'].append({'kind':'biome_ids','seed':str(seed),'dimension':dimension,'y':y,'mismatches':len(mismatch),'first':points[int(mismatch[0])].tolist()})
                    for value in np.unique(actual):
                        value=int(value); index=int(np.flatnonzero(actual==value)[0]);point=points[index]
                        item=observed.setdefault(str(value),{'name':biome_name(value),'samples':0,'witnesses':[]})
                        item['samples']+=int(np.count_nonzero(actual==value))
                        if len(item['witnesses'])<4:item['witnesses'].append({'seed':str(seed),'coordinate':point.tolist(),'dimension':dimension})
                        trials=[]
                        for _ in range(8):
                            start=time.perf_counter();backend.biome(*map(int,point),dimension);trials.append(1e6*(time.perf_counter()-start))
                        biome_times.setdefault(str(value),[]).append(statistics.median(trials))
                    data['biomes'].setdefault(str(dimension),[]).append({'seed':str(seed),'y':y,'points':len(points),'seconds':elapsed})
        reference.lib.ss_destroy(ctx)
    for name,row in data['structures'].items():
        for field in ('reference_ms','complete_ms','witness_ms'):
            values=row[field];row[field.replace('_ms','_median_ms')]=statistics.median(values) if values else None
    for value,row in observed.items():row['median_scalar_us']=statistics.median(biome_times[value])
    data['observed_biomes']=observed
    data['active_unobserved']=[item for item in data['catalog'] if item['generates'] and str(item['id']) not in observed]
    data['unsupported_inventory_features']={
        'monster_room':'Native Dungeon requires separate cave/terrain simulation and per-chunk allocation; no reviewed bounded adapter or actual-generation parity. Not inferred from raw region starts.',
        'end_gateway':'Special decorator/return-portal semantics; not a regional structure-start adapter.',
        'ravine_lava_lake_geode_desert_well':'Terrain/decorator features; outside the regular structure inventory. No absence claim.'}
    data['accuracy_scope']='Exact pinned-predictor parity for tested starts and biome points; End viability tested against current full scan, not old incorrect dimension adapter; real Bedrock generation remains unverified.'
    (OUT/'detection-audit.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({'checks':data['checks'],'differences':len(data['differences']),'structure_families':len(data['structures']),'observed_biomes':len(observed),'unobserved_active':[r['name'] for r in data['active_unobserved']]}),flush=True)
    if data['differences']:raise SystemExit(1)


if __name__=='__main__':main()
