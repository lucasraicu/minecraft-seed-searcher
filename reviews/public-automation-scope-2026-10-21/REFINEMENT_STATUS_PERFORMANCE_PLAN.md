CurrentrealNativev2endtoendcontrol81.774s,64densetiles and4coarseheightplanes. Isolatedactualevaluate_products(saved102532OWpoints)0.749s/call; refinementcallsfull36productvalidation/rankingeveryrounddespiteonlyneedingpendingstatusofbiomeproducts. NativeProvidersetup0.026s, scalar4096block0.026s,batch0.019s: batchtileoptimizationwouldnotaddressmaincost, leaveitunchanged.

Routineperformancefix scopedharvest_native._refine_v2only,newstubtests: Buildindexdimension->canonicalbiomename->[(x,y,z)] once fromvalidatedobs. Determineeacheligiblebiomeproductpendingonlybypositivewitnesspresence overexactFAMILIES mapping,heightroles andinclusivecircle; structureprerequisitesremaincurrentexistingcheck. ComputeallpendingflagsONCEperroundbeforetiles, preservingoldround-robin/tileorder. Updatenamepointindexonlywhenaddingnewdensewitness (sameexistingcoordinate dedup). No metadataOID hashing/wholeobsvalidation/allrecordclusterrankinginstatus-onlyloop. Keep checkpoint/finalfullvalidation, allfinalevaluate_products/sourcebindingunchanged. No changes toscoreNative/C/geometry/budgets,tile64cap/retries. Helpers2smallfunctions(orlocalclosure), no DSL/cacheframework. Testpresenceparityvsactualbiome_points/_preset/_recordforsupportedbiomeproducts,aliases/caveY/NetherY64/inclusivecircle, sameoriginalsource/tileorder. RerunoneknownseedrealboundedNativepipelinecomparecompleteproductstatus/featurecounts/witnesses+tileIDswith81.774sbaseline;reportactualtimingandlimits,notpromisegeneral speedup. Reviewforincorrectpositive, source/height/scope, staleround/witnessupdates.
SOURCE
def _refine_v2(obs,backend,path,deadline,checkpoint):
    """Shared bounded tile queue, four-height coarse record pass, positive witnesses."""
    from .product_evaluation import evaluate_products,DEFINITIONS,spawn_reference,biome_points,structure_points
    from .geometry import inside,distance2
    from .refinement_queue import RefinementQueue
    from .refinement_worker import execute_one,NativeProvider
    from .refinement import decode_tile
    from ..backend import biome_name
    from ..realm.biomes import canonical
    anchor=spawn_reference(obs,'overworld')
    if anchor is None:return
    known={d:{tuple(p[:3]) for p in pts} for d,pts in obs['biomes'].items()}
    meta=obs['metrics'].setdefault('refinement',dict(tiles=[],coarse_done=False,reason=None))
    if not meta['coarse_done']:
        ax,az=anchor['overworld']
        coords=[[x,y,z] for y in (-48,0,160)
            for z in range(-(-(az-1000)//64)*64,az+1001,64)
            for x in range(-(-(ax-1000)//64)*64,ax+1001,64)
            if distance2(x,z,[ax,az])<=1000**2 and inside(x,z,obs['bounds']['overworld']) and (x,y,z) not in known['overworld']]
        for first in range(0,len(coords),1024):
            if time.monotonic()>=deadline:meta['reason']='world_time_budget_exhausted';checkpoint(obs);return
            points=coords[first:first+1024];values=backend.biome_points(points)
            if len(values)!=len(points):raise ValueError('Truncated record biome batch')
            for p,bid in zip(points,values):
                bid=int(bid);obs['biome_names'][str(bid)]=canonical(biome_name(bid))
                obs['biomes']['overworld'].append(p+[bid]);known['overworld'].add(tuple(p))
            checkpoint(obs)
        meta['coarse_done']=True;checkpoint(obs)
    q=RefinementQueue(path.parent.parent/'refinement')
    loaded={t['tile_id'] for t in meta['tiles']}
    definitions=sorted([p for p in DEFINITIONS['presets'] if p['biomes']]+[
        p for p in DEFINITIONS['records'] if p['kind']=='biome_sampler'],key=lambda p:p['id'])
    requests=[]
    for p in definitions:
        ref=spawn_reference(obs,p['dimension'])
        if ref is None:continue
        a=ref['coordinate'];r=p['radius']
        if any(len(structure_points(obs,feature,a,r))<n for feature,n in p.get('structures',{}).items()):continue
        layers=(-48,0,63,160) if p.get('kind')=='biome_sampler' else ((64,) if p['dimension']=='nether' else (63,))
        tiles=[]
        for y in layers:
            for z in range((a[1]-r)//64*64,a[1]+r+1,64):
                for x in range((a[0]-r)//64*64,a[0]+r+1,64):
                    nearest=(max(x,min(a[0],x+63)),max(z,min(a[1],z+63)))
                    if distance2(*nearest,a)<=r*r and inside(x,z,obs['bounds'][p['dimension']]) and inside(x+63,z+63,obs['bounds'][p['dimension']]):
                        tiles.append((distance2(x+32,z+32,a),x,z,y))
        requests.append((p,iter(sorted(tiles))))
    progress=True
    while progress and time.monotonic()<deadline:
        progress=False
        statuses={e['product_id']:e['status'] for e in evaluate_products(obs)}
        for p,tiles in requests:
            if statuses[p['id']]!='pending':continue
            try:_,x,z,y=next(tiles)
            except StopIteration:continue
            progress=True
            if time.monotonic()>=deadline:break
            dimension=p['dimension']
            context=dict(identity=obs['identity'],dimension=dimension,provider='procedural_model_v1',
                observed_build=None,evidence_sha256=digest(['catalog-procedural-model-v2',obs['identity']]))
            spec=dict(revision='catalog-refinement-job-v1',context=context,bounds=[x,z,x+64,z+64],y=y)
            key=digest(spec);existing=q._path(key).exists()
            if not existing and len(list(q.root.glob('*.json')))>=64:
                meta['reason']='tile_budget_exhausted';checkpoint(obs);return
            q.submit(context,[x,z,x+64,z+64],y)
            result=q.result(key)
            if result['status']!='complete':
                seconds=min(60,int(deadline-time.monotonic()))
                if seconds<1:meta['reason']='world_time_budget_exhausted';checkpoint(obs);return
                execute_one(q,NativeProvider,seconds=seconds)
                result=q.result(key)
            if result['status']!='complete':continue
            tile=result['tile']
            if tile['tile_id'] in loaded:continue
            values=decode_tile(tile);best={};a=spawn_reference(obs,dimension)['coordinate']
            for offset,bid in enumerate(values):
                if bid is None:continue
                px=x+offset%64;pz=z+offset//64
                candidate=(distance2(px,pz,a),px,pz)
                if bid not in best or candidate<best[bid]:best[bid]=candidate
            for bid,(_,px,pz) in best.items():
                obs['biome_names'][str(bid)]=canonical(biome_name(bid))
                if (px,y,pz) not in known[dimension]:
                    obs['biomes'][dimension].append([px,y,pz,bid]);known[dimension].add((px,y,pz))
            meta['tiles'].append(tile);loaded.add(tile['tile_id']);checkpoint(obs)
    if time.monotonic()>=deadline:meta['reason']='world_time_budget_exhausted'
    checkpoint(obs)


