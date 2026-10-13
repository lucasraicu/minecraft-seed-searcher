"""Owned direct evidence from the audited native blueprint result buffers.

No generation or evaluator replay occurs here. The Python evaluator and replay
adapter remain independent record oracles. All values returned own Python data.
"""
import os
import platform
import resource
import time

from ..backend import biome_catalog, biome_name
from .biomes import canonical
from .blueprint import smart_score, score_uncertainty
from .config import BLUEPRINT_CONTRACT, locked_policy, origin_policy, two_group_policy

NAMES = ('mansion','jungle_temple','desert_pyramid','monument','ancient_city','village',
         'trial_chamber','ruined_portal','shipwreck','mineshaft','fortress','bastion','outpost')
BIOME_NAMES = {r['id']: canonical(r['name']) for r in biome_catalog()}


def points(value):
    return [[int(value.xz[2*i]), int(value.xz[2*i+1])] for i in range(value.n)]


def full_observation(name, bounds, raw, viable):
    return {'type':name,'bounds':bounds,'raw':raw,'predicted_viable':viable,'coordinates':viable,
            'data_status':'PREDICTED' if viable else 'PARTIAL','verification':'UNVERIFIED',
            'confirmed_absent':False,'complete':False,'inventory_status':'COMPLETE',
            'detection_method':'complete_predictor_starts','evidence_scope':'bounded predictor domain',
            'negative_meaning':'not found by unvalidated predictor; not confirmed absent'}


def observation(c, name, bounds, goal=None):
    if not c.evaluated:
        return {'type':name,'bounds':bounds,'raw':[],'coordinates':[],'predicted_viable':[],
                'minimum_count':goal,'data_status':'PARTIAL','verification':'DEFERRED',
                'confirmed_absent':False,'complete':False,'inventory_status':'DEFERRED','floor_status':'PENDING'}
    if c.full:
        viable = points(c.viable)
        result = full_observation(name,bounds,points(c.raw),viable)
        if name == 'mansion' and viable:
            names = [BIOME_NAMES.get(int(c.mansion_ids[i]), canonical(biome_name(int(c.mansion_ids[i])))) for i in range(c.viable.n)]
            result['unfiltered_predicted_viable'] = viable
            result['anchor_biome_witnesses'] = [{'coordinate':[p[0],63,p[1]],'biome':n} for p,n in zip(viable,names)]
            viable = [p for p,n in zip(viable,names) if n == 'dark_forest']
            result['predicted_viable'] = result['coordinates'] = viable
            result['anchor_biome_policy'] = 'Dark Forest at start Y=63; fixed-Y predictor witness, actual surface unresolved'
    else:
        viable = points(c.floor)
        result = {'type':name,'bounds':bounds,'raw':[],'coordinates':viable,'predicted_viable':viable,
                  'data_status':'PREDICTED' if viable else 'PARTIAL','verification':'UNVERIFIED',
                  'complete':False,'confirmed_absent':False,
                  'inventory_status':'FLOOR_WITNESSES' if len(viable)>=goal else 'COMPLETE',
                  'detection_method':'native_count_floor','raw_inventory_status':'NOT_RECORDED',
                  'negative_meaning':'predictor count below floor; not confirmed actual absence'}
    if goal is not None:
        result.update(minimum_count=goal,predicted_count=len(viable))
        if name not in ('fortress','bastion'):
            result.update(count_is_complete=result['inventory_status']=='COMPLETE',
                          floor_status='PREDICTED' if len(viable)>=goal else 'PENDING')
    return result


def palette(c, bounds, policy, cache):
    samples=[];names=set()
    # Match BiomeSampler's query-batch accounting and bounded cache eviction,
    # including overlapping anchor lattices and batch-local duplicate points.
    queried=hits=0;batch_size=policy.get('gate_batch_size',16)*4
    for offset in range(0,c.biome_n,batch_size):
        xyz=[tuple(int(c.biome_xyz[3*i+t]) for t in range(3)) for i in range(offset,min(c.biome_n,offset+batch_size))]
        missing=dict.fromkeys(p for p in xyz if p not in cache)
        queried+=len(missing);hits+=len(xyz)-len(missing)
        cache.update(missing)
        while len(cache)>65536:cache.pop(next(iter(cache)))
        for i,p in enumerate(xyz,offset):
            value=int(c.biome_ids[i]);name=BIOME_NAMES.get(value)
            if name is None:name=canonical(biome_name(value))
            names.add(name);samples.append({'coordinate':list(p),'id':value,'biome':name})
    expected=list(policy['required_families'])
    from .sampling import grid_points
    expected_points=len(grid_points(bounds,policy['spacing'],policy['sample_y_levels'][0],'world'))*4
    found={expected[f]:samples[i] for i,f in sorted((int(c.first_witness[f]),f) for f in range(13) if c.first_witness[f]>=0)}
    missing=[f for f in expected if f not in found]
    result={'qualification':'PENDING' if missing else 'PREDICTED','data_status':'PREDICTED',
            'raw_names':sorted(names),'required_families':expected,'observed_families':list(found),
            'missing_families':missing,'witnesses':found,'sample_count':len(samples),
            'bounds':bounds,'spacing':policy['spacing'],'sample_y_levels':list(policy['sample_y_levels']),
            'sampling':{'version':'blueprint-four-y-v1','lattice':'world','expected_points':expected_points,
                        'samples':samples,'complete_defined_lattice':len(samples)==expected_points},
            'inventory_status':'COMPLETE' if len(samples)==expected_points else 'POSITIVE_WITNESSES',
            'surface_generation_verified':False,'cave_generation_verified':False,
            'source':'MC_26_50 3D biome prediction at four fixed Y planes; not actual surface/cave generation',
            'negative_meaning':'unseen families remain unknown; no exhaustive absence claim',
            'score':0,'uncertainty':{'domain':'prediction_model_only','score_interval':[0,0],
                                   'actual_generation_score_interval':[0,0],'exhaustive_verified':False}}
    return result,queried,hits


def build_record(native,index,seed,cfg):
    wall=time.perf_counter();cpu=time.process_time();seed=str(seed)
    discovery_bounds=list(cfg['discovery']['overworld_bounds'])
    strongholds=full_observation('stronghold',discovery_bounds,points(native.discovery),points(native.discovery))
    fortress={'type':'fortress','bounds':list(cfg['discovery']['nether_bounds']),
              'raw':[],'predicted_viable':[],'coordinates':[],'data_status':'NOT_REQUESTED',
              'verification':'UNVERIFIED','confirmed_absent':False,'complete':False}
    origin=origin_policy(cfg)
    counts={'stronghold_anchors':native.discovery.n if origin else native.nanchors};anchors=[];cache={};cache_hits=0
    if origin:counts['evaluation_centers']=native.nanchors
    locked=locked_policy(cfg);h=cfg['deployment']['overworld_side_blocks']//2;nh=cfg['deployment']['nether_side_blocks']//2
    def increment(name,n=1):counts[name]=counts.get(name,0)+n
    for j in range(native.nanchors):
        c=native.anchors[j];x=int(c.x);z=int(c.z);anchor=[x,z]
        bounds=[x-h,z-h,x+h,z+h]
        nb=[x/8-nh,z/8-nh,x/8+nh,z/8+nh]
        nb=[int(v) if int(v)==v else v for v in nb]
        required={'stronghold':{**strongholds,'bounds':bounds,
                  'coordinates':strongholds['predicted_viable'] if origin else [anchor],
                  'raw':strongholds['raw'] if origin else [anchor],
                  'predicted_viable':strongholds['predicted_viable'] if origin else [anchor],
                  'minimum_count':1,'predicted_count':native.discovery.n if origin else 1,
                  **({'count_is_complete':True} if origin else {}),
                  'floor_status':'PREDICTED' if (not origin or native.discovery.n) else 'PENDING'}}
        pending=[];nether={};optional={};biomes=None
        increment('structure_stage_entered')
        for name in cfg['search']['structure_order']:
            k=NAMES.index(name)
            o=c.observations[k];required[name]=observation(o,name,bounds,cfg['structures']['minimum_counts'][name])
            if o.evaluated:
                increment('checked_'+name)
                if c.count_missing & (1<<k):pending.append('count_'+name);increment('pending_'+name)
        if c.observations[10].evaluated:
            increment('nether_stage_entered')
            for k,name in enumerate(('fortress','bastion'),10):
                nether[name]=observation(c.observations[k],name,nb,cfg['structures']['nether_minimum_counts'][name])
                if c.count_missing & (1<<k):pending.append('count_'+name)
        if origin and native.discovery.n==0:pending.append('count_stronghold')
        if locked:
            order=['fortress','bastion',*cfg['search']['structure_order']]
            if origin:order.insert(4,'stronghold')
            pending=[p for name in order for p in pending if p=='count_'+name]
        if ((not c.fatal_missing and int(c.count_missing).bit_count()<=cfg['search']['max_misses']) if two_group_policy(cfg) else not pending):
            increment('structure_stage_passed')
        if c.biome_evaluated:
            increment('biome_stage_entered')
            biomes,queried,hits=palette(c,bounds,cfg['biomes'],cache)
            increment('biome_samples',queried);cache_hits+=hits
            if biomes['missing_families']:pending.extend('biome_'+f for f in biomes['missing_families'])
            else:increment('biome_stage_passed')
        two_group=two_group_policy(cfg)
        deficit_categories=[NAMES[k] for k in (0,4,5,6,7,9,10,11) if c.count_missing&(1<<k)] if two_group else []
        fatal_reasons=(['floor_'+NAMES[k] for k in range(13) if c.fatal_missing&(1<<k)]+
                       (['floor_stronghold'] if c.fatal_missing&(1<<13) else [])) if two_group else []
        biome_failures=['biome_'+f for f in biomes['missing_families']] if biomes else []
        complete=(not fatal_reasons and len(deficit_categories)<=cfg['search']['max_misses'] and not biome_failures and c.biome_evaluated) if two_group else not pending
        if complete and not locked:optional['outpost']=observation(c.observations[12],'outpost',bounds)
        from .config import river_policy
        ranking=smart_score(required,nether,optional,locked=locked,river=river_policy(cfg),origin=origin,two_group=two_group,
                            biome_names=(s['biome'] for s in biomes['sampling']['samples'] if s['coordinate'][1]==63) if biomes else ());score=ranking['score']
        if score!=c.score:raise RuntimeError('Native/direct score parity failure')
        anchors.append({'id':f'{seed}:{x}:{z}','index':index,'seed':seed,'stronghold':anchor,
            'contract':BLUEPRINT_CONTRACT,'game_version':cfg['game']['target_version'],
            **({'evaluation_center':[0,0],'center_kind':'world_origin','predicted_strongholds':strongholds['predicted_viable']} if origin else {}),
            'bds_version':cfg['game']['bds_version'],'backend_model':cfg['game']['backend_model'],
            'backend_commit':cfg['game']['backend_commit'],
            'bounds':{'overworld':bounds,'initial_overworld':discovery_bounds,
                      'initial_nether':list(cfg['discovery']['nether_bounds']),'final_nether':nb},
            'required_structures':required,'required_nether_structures':nether,'optional_structures':optional,
            'initial_fortress':fortress,'biomes':biomes,'ranking':ranking,
            'final_nether_prediction':{'required':['fortress','bastion'],'status':'PREDICTED' if len(nether)==2 and all(len(v['predicted_viable'])>=cfg['structures']['nether_minimum_counts'][name] for name,v in nether.items()) else 'PENDING','bounds':nb,'actual_generation_verified':False},
            'baseline_score':score if complete else None,'baseline_score_observed':score,
            'baseline_score_complete':complete,'baseline_score_status':'PREDICTED count bonuses' if complete else 'PARTIAL; baseline unresolved',
            'baseline_score_uncertainty':score_uncertainty(score,fatal_reasons+biome_failures if two_group else pending,complete),
            'inventory':{'version':'blueprint-count-inventory-v1','status':'COMPLETE' if complete else 'UNRESOLVED',
                'tasks':[],'completion_scope':'complete required predictor counts for survivors; actual generation unverified'},
            'qualification':'PREDICTED' if complete else 'PENDING','data_status':'PREDICTED','pending_reasons':pending,
            **({'deficit_categories':deficit_categories,'fatal_reasons':fatal_reasons,'biome_failures':biome_failures,
                'deficit_budget':cfg['search']['max_misses'],'baseline_qualification':'PREDICTED' if complete else 'PENDING'} if two_group else {}),
            'processing_status':'baseline_complete' if complete else 'baseline_pending',
            'final_nether_status':'UNVERIFIED','terrain_status':{'v1':'not_evaluated'}})
        if two_group:
            from .spawn import classify_spawn
            anchors[-1]['spawn_stage']=classify_spawn(anchors[-1],cfg)
    if locked:
        for a in anchors:
            a.update(screening_revision=cfg['screening_revision'],deferred_requirements=['count_monument','count_shipwreck']+([] if 'outpost' in cfg['structures']['minimum_counts'] else ['optional_outpost']),
                     marine_stage={'status':'DEFERRED','required_counts':{n:cfg['structures']['minimum_counts'][n] for n in ('monument','shipwreck')},'trigger':'complete coastal ocean/water/land footprint'},full_blueprint_certification=False)
    counts.update(baseline_predicted=sum(a['qualification']=='PREDICTED' for a in anchors),
                  baseline_pending=sum(a['qualification']=='PENDING' for a in anchors),confirmed_rejections=0,
                  unresolved_discovery=int(not strongholds['predicted_viable'] if origin else not anchors),unresolved_stronghold_coverage=1)
    return {'index':index,'seed':seed,'contract':BLUEPRINT_CONTRACT,'anchors':anchors,'counts':counts,
            'stage_seconds':{},'native_work':{},'worker_cpu_seconds':time.process_time()-cpu,
            'total_seconds':time.perf_counter()-wall,'worker_pid':os.getpid(),
            'worker_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024),
            'biome_cache_hits':cache_hits,'discovery_status':'PREDICTED' if (strongholds['predicted_viable'] if origin else anchors) else 'PENDING',
            'discovery':{'stronghold':strongholds,'fortress':fortress,'seed':seed,'settings':dict(cfg['discovery']),
                         'coverage':{'status':'UNRESOLVED','stronghold_recall':'UNVALIDATED','authoritative_absence':False,'complete':False}},
            'effective_seed_bits':{'viability':64,'raw_MT_placement':32}}
