"""Explicit Master Seed Blueprint predictor contract, separate from legacy Realm V1.

Sparse biome witnesses and count floors are model evidence, never Bedrock truth.
The exhaustive reference path uses the same constraints without early exits.
"""
import os
import platform
import resource
import time

import numpy as np

from ..backend import Backend, biome_name
from ..seeds import parse_seed
from .biomes import canonical, FAMILIES, WOOD
from .bounds import square, native_bounds, nether_square, json_bounds, contains
from .config import BLUEPRINT_CONTRACT
from .sampling import BiomeSampler, grid_points, dispersed_indices

PALETTE={
    'plains':{'plains','sunflower_plains','meadow'},
    'desert':FAMILIES['desert'], 'forest':{'forest','birch_forest','flower_forest','old_growth_birch_forest'},
    'taiga':{'taiga','old_growth_pine_taiga','old_growth_spruce_taiga'},
    'jungle':{'jungle','bamboo_jungle'}, 'swamp':FAMILIES['swamp'],
    'snowy_ice':FAMILIES['snowy_ice']|{'frozen_ocean','deep_frozen_ocean','frozen_river'},
    'dark_forest':{'dark_forest'}, 'peaks':{'jagged_peaks','stony_peaks'},
    'stony_shore':{'stony_shore'}, 'lush_caves':{'lush_caves'},
    'dripstone_caves':{'dripstone_caves'}, 'deep_dark':{'deep_dark'},
}
CAVE_FAMILIES={'lush_caves','dripstone_caves','deep_dark'}


def biome_gate(backend,bounds,cfg,*,complete=False):
    """Public benchmark entry point; bounds are half-open block coordinates."""
    sampler=BiomeSampler(backend)
    result=biome_palette(sampler,bounds,cfg['biomes'],complete=complete)
    result['queried_points']=sampler.queried
    result['cache_hits']=sampler.hits
    return result


def biome_palette(sampler,bounds,policy,*,complete=False):
    """Sample all four Y planes; surface and cave witness roles stay distinct."""
    expected=list(policy['required_families'])
    grids=[grid_points(bounds,policy['spacing'],y,'world') for y in policy['sample_y_levels']]
    # Interleave Y at each dispersed XZ. This does not confuse Y with surface height.
    points=np.stack(grids,axis=1).reshape(-1,3)
    xz_order=dispersed_indices(len(grids[0]))
    order=(xz_order[:,None]*len(grids)+np.arange(len(grids))).ravel()
    found={};samples=[];names=set();batch_size=policy.get('gate_batch_size',16)*len(grids)
    for offset in range(0,len(order),batch_size):
        if len(found)==len(expected) and not complete:break
        batch=points[order[offset:offset+batch_size]]
        values=sampler.sample(batch)
        for point,value in zip(batch,values):
            name=canonical(biome_name(int(value)));names.add(name)
            row={'coordinate':point.tolist(),'id':int(value),'biome':name}
            samples.append(row)
            for family in expected:
                role_y=(-48,0) if family in CAVE_FAMILIES else (63,160)
                if family not in found and int(point[1]) in role_y and name in PALETTE[family]:
                    found[family]=row
    missing=[f for f in expected if f not in found]
    return {'qualification':'PENDING' if missing else 'PREDICTED','data_status':'PREDICTED',
            'raw_names':sorted(names),'required_families':expected,'observed_families':list(found),
            'missing_families':missing,'witnesses':found,'sample_count':len(samples),
            'bounds':json_bounds(bounds),'spacing':policy['spacing'],
            'sample_y_levels':list(policy['sample_y_levels']),
            'sampling':{'version':'blueprint-four-y-v1','lattice':'world','expected_points':len(points),
                        'samples':samples,'complete_defined_lattice':len(samples)==len(points)},
            'inventory_status':'COMPLETE' if len(samples)==len(points) else 'POSITIVE_WITNESSES',
            'surface_generation_verified':False,'cave_generation_verified':False,
            'source':'MC_26_50 3D biome prediction at four fixed Y planes; not actual surface/cave generation',
            'negative_meaning':'unseen families remain unknown; no exhaustive absence claim',
            'score':0,'uncertainty':{'domain':'prediction_model_only','score_interval':[0,0],
                                   'actual_generation_score_interval':[0,0],'exhaustive_verified':False}}


def count_observation(backend,name,bounds,minimum,*,capped=True,combined=True):
    from .baseline import structure_observation
    # The pinned Mansion predictor also permits Pale Garden. The blueprint
    # specifically asks for a Dark Forest anchor; inspect every start before
    # selecting the qualifying subset, so an early Pale Garden cannot hide one.
    if name=='mansion':capped=False
    if capped and hasattr(backend,'structure_count'):
        points=backend.structure_count(name,native_bounds(bounds),minimum)
        coords=sorted({tuple(p) for p in points if contains(p,bounds)})
        observation={'type':name,'bounds':json_bounds(bounds),'raw':[],
                     'coordinates':[list(p) for p in coords],
                     'predicted_viable':[list(p) for p in coords],
                     'data_status':'PREDICTED' if coords else 'PARTIAL',
                     'verification':'UNVERIFIED','complete':False,'confirmed_absent':False,
                     'inventory_status':'FLOOR_WITNESSES' if len(coords)>=minimum else 'COMPLETE',
                     'detection_method':'native_count_floor','raw_inventory_status':'NOT_RECORDED',
                     'negative_meaning':'predictor count below floor; not confirmed actual absence'}
    else:
        observation=structure_observation(backend,name,bounds,combined)
    if name=='mansion' and observation['predicted_viable']:
        starts=observation['predicted_viable']
        xyz=np.array([[x,63,z] for x,z in starts],dtype=np.int32)
        ids=backend.biome_points(xyz)
        names=[canonical(biome_name(int(value))) for value in ids]
        observation['unfiltered_predicted_viable']=starts
        observation['anchor_biome_witnesses']=[{'coordinate':p.tolist(),'biome':n} for p,n in zip(xyz,names)]
        observation['predicted_viable']=[p for p,n in zip(starts,names) if n=='dark_forest']
        observation['coordinates']=observation['predicted_viable']
        observation['anchor_biome_policy']='Dark Forest at start Y=63; fixed-Y predictor witness, actual surface unresolved'
    count=len(observation['predicted_viable'])
    observation.update(minimum_count=minimum,predicted_count=count,
                       count_is_complete=observation['inventory_status']=='COMPLETE',
                       floor_status='PREDICTED' if count>=minimum else 'PENDING')
    return observation


def smart_score(structures,nether,optional,*,coastal_footprint_verified=False,locked=False,river=False,metrics=None,origin=False,biome_names=()):
    """Blueprint bonuses from predictor counts; footprint bonus needs actual bounds."""
    counts={k:len(v.get('predicted_viable',[])) for k,v in {**structures,**nether,**optional}.items()}
    bonuses={}
    for name,floor,points in (('village',6 if locked else 5,5),('ruined_portal',6 if locked else 3,5),('shipwreck',5 if river else 4 if locked else 2,5),('mineshaft',15 if locked else 5,1)):
        bonuses[name]=max(0,counts.get(name,0)-floor)*points
    for name,floor,cap,points in (('trial_chamber',5,counts.get('trial_chamber',0),10),('ancient_city',2,4,15),('fortress',2,4,15),('bastion',2,4,15)) if locked else (('trial_chamber',2,4,10),('ancient_city',1,3,15),('fortress',1,3,15),('bastion',1,3,15)):
        bonuses[name]=max(0,min(cap,counts.get(name,0))-floor)*points
    for name in ('desert_pyramid','jungle_temple'):
        n=counts.get(name,0);bonuses[name]=(20 if n>=2 else 0)+(10 if n>=3 and (not locked or name=='desert_pyramid') else 0)
    bonuses['monument']=25*int(counts.get('monument',0)>=2)
    if river:
        bonuses['bastion']=max(0,counts.get('bastion',0)-3)*15
        bonuses['mansion']=50*int(counts.get('mansion',0)>=2)
        bonuses['river_highway']=20*int((metrics or {}).get('river_highway_connected') is True)
    bonuses['coastal_monument_footprint']=25*int(coastal_footprint_verified)
    bonuses['outpost']=10*counts.get('outpost',0)
    if origin:
        # The origin policy's advertised jackpots are scored from observed
        # predictor evidence; deferred marine/terrain bonuses arrive later.
        bonuses.update(stronghold=50*int(counts.get('stronghold',0)>=2),
                       ancient_city=25*max(0,min(counts.get('ancient_city',0),4)-2),
                       fortress=20*max(0,min(counts.get('fortress',0),4)-2),
                       bastion=20*max(0,counts.get('bastion',0)-3),
                       desert_pyramid=10*int(counts.get('desert_pyramid',0)>=2),
                       jungle_temple=10*int(counts.get('jungle_temple',0)>=2),
                       outpost=10*max(0,counts.get('outpost',0)-2),
                       river_highway=35*int((metrics or {}).get('river_highway_connected') is True),
                       mega_ravine_hub=35*int((metrics or {}).get('mega_ravine_hub') is True))
        observed=set(biome_names)
        bonuses.update(cherry_grove=15*int('cherry_grove' in observed),
                       badlands=15*int(bool(observed & {'badlands','wooded_badlands','eroded_badlands'})),
                       mushroom_fields=15*int('mushroom_fields' in observed))
    return {'score':sum(bonuses.values()),'bonuses':bonuses,'counts':counts,
            'source':'predictor start counts; actual generation unverified',
            'coastal_footprint_bonus_status':'VERIFIED' if coastal_footprint_verified else 'PENDING actual footprint containment'}


def score_uncertainty(score,pending,complete):
    return {'domain':'prediction_model_only','prediction_score_interval':[score,score if complete else None],
            'actual_generation_score_interval':[0,None],'pending_prediction_requirements':list(pending),
            'eligibility_verified':False,'interpretation':'Count and biome witnesses are predictions; actual counts, surface palette, cave generation and monument extent require verification.'}


def evaluate_seed(index,seed,cfg,*,backend_factory=Backend,combined=True,short_circuit=True):
    from .config import locked_policy
    if locked_policy(cfg):return evaluate_locked_seed(index,seed,cfg,backend_factory=backend_factory,combined=combined,short_circuit=short_circuit)
    from .baseline import structure_observation
    seed=parse_seed(seed);start=time.perf_counter();cpu=time.process_time();times={};counts={};anchors=[]
    def timed(name,fn):
        before=time.perf_counter()
        try:return fn()
        finally:times[name]=times.get(name,0)+time.perf_counter()-before
    # Complete/reference mode uses full scans and evaluates all constraints.
    capped=short_circuit and cfg['search'].get('inventory_mode')=='eligibility'
    with backend_factory(seed) as backend:
        sampler=BiomeSampler(backend)
        discovery_bounds=cfg['discovery']['overworld_bounds']
        strongholds=timed('stronghold',lambda:structure_observation(backend,'stronghold',discovery_bounds,combined))
        # Broad Nether discovery is irrelevant to the centered final border.
        fortress={'type':'fortress','bounds':list(cfg['discovery']['nether_bounds']),
                  'raw':[],'predicted_viable':[],'coordinates':[],'data_status':'NOT_REQUESTED',
                  'verification':'UNVERIFIED','confirmed_absent':False,'complete':False}
        counts['stronghold_anchors']=len(strongholds['predicted_viable'])
        for anchor in strongholds['predicted_viable']:
            bounds=square(anchor,1536);nb=nether_square(anchor,896)
            required={'stronghold':{**strongholds,'bounds':json_bounds(bounds),'coordinates':[anchor],
                'raw':[anchor],'predicted_viable':[anchor],'minimum_count':1,'predicted_count':1,'floor_status':'PREDICTED'}}
            pending=[];nether={};optional={};biomes=None
            counts['structure_stage_entered']=counts.get('structure_stage_entered',0)+1
            for name in cfg['search']['structure_order']:
                if pending and short_circuit:
                    required[name]={'type':name,'bounds':json_bounds(bounds),'raw':[],
                        'coordinates':[],'predicted_viable':[],'minimum_count':cfg['structures']['minimum_counts'][name],
                        'data_status':'PARTIAL','verification':'DEFERRED','confirmed_absent':False,
                        'complete':False,'inventory_status':'DEFERRED','floor_status':'PENDING'}
                    continue
                goal=cfg['structures']['minimum_counts'][name]
                observation=timed('structure_'+name,lambda n=name,g=goal:count_observation(backend,n,bounds,g,capped=capped,combined=combined))
                required[name]=observation
                counts['checked_'+name]=counts.get('checked_'+name,0)+1
                if observation['floor_status']!='PREDICTED':
                    pending.append('count_'+name);counts['pending_'+name]=counts.get('pending_'+name,0)+1
            if not pending or not short_circuit:
                counts['nether_stage_entered']=counts.get('nether_stage_entered',0)+1
                pairs=timed('final_nether_pair',lambda:backend.nether_structure_pairs(native_bounds(nb))) if combined and hasattr(backend,'nether_structure_pairs') else None
                for name in ('fortress','bastion'):
                    observation=timed('final_'+name,lambda n=name:structure_observation(backend,n,nb,combined,pair=pairs[n] if pairs else None))
                    observation.update(minimum_count=1,predicted_count=len(observation['predicted_viable']))
                    nether[name]=observation
                    if not observation['predicted_viable']:pending.append('count_'+name)
            if not pending:counts['structure_stage_passed']=counts.get('structure_stage_passed',0)+1
            if not pending or not short_circuit:
                counts['biome_stage_entered']=counts.get('biome_stage_entered',0)+1
                before=sampler.queried
                biomes=timed('biome_palette_4y',lambda:biome_palette(sampler,bounds,cfg['biomes'],complete=not short_circuit))
                counts['biome_samples']=counts.get('biome_samples',0)+sampler.queried-before
                if biomes['missing_families']:pending.extend('biome_'+f for f in biomes['missing_families'])
                else:counts['biome_stage_passed']=counts.get('biome_stage_passed',0)+1
            # All jackpot counts are inventoried only for full baseline survivors.
            # No legacy presence inventory can overwrite this count contract.
            inventory_complete=not pending
            if inventory_complete:
                for name in cfg['search']['structure_order']:
                    if not required[name].get('count_is_complete',False):
                        required[name]=timed('ranking_inventory',lambda n=name:count_observation(backend,n,bounds,cfg['structures']['minimum_counts'][n],capped=False,combined=combined))
                optional['outpost']=timed('ranking_inventory',lambda:structure_observation(backend,'outpost',bounds,combined))
            ranking=smart_score(required,nether,optional)
            score=ranking['score'];status='PENDING' if pending else 'PREDICTED'
            anchors.append({'id':f'{seed}:{anchor[0]}:{anchor[1]}','index':index,'seed':str(seed),'stronghold':anchor,
                'contract':BLUEPRINT_CONTRACT,'game_version':cfg['game']['target_version'],
                'bds_version':cfg['game']['bds_version'],'backend_model':cfg['game']['backend_model'],
                'backend_commit':cfg['game']['backend_commit'],
                'bounds':{'overworld':json_bounds(bounds),'initial_overworld':list(discovery_bounds),
                          'initial_nether':list(cfg['discovery']['nether_bounds']),'final_nether':json_bounds(nb)},
                'required_structures':required,'required_nether_structures':nether,'optional_structures':optional,
                'initial_fortress':fortress,'biomes':biomes,'ranking':ranking,
                'final_nether_prediction':{'required':['fortress','bastion'],'status':'PREDICTED' if len(nether)==2 and all(v['predicted_viable'] for v in nether.values()) else 'PENDING','bounds':json_bounds(nb),'actual_generation_verified':False},
                'baseline_score':score if inventory_complete else None,'baseline_score_observed':score,
                'baseline_score_complete':inventory_complete,'baseline_score_status':'PREDICTED count bonuses' if inventory_complete else 'PARTIAL; baseline unresolved',
                'baseline_score_uncertainty':score_uncertainty(score,pending,inventory_complete),
                'inventory':{'version':'blueprint-count-inventory-v1','status':'COMPLETE' if inventory_complete else 'UNRESOLVED',
                    'tasks':[],'completion_scope':'complete required predictor counts for survivors; actual generation unverified'},
                'qualification':status,'data_status':'PREDICTED','pending_reasons':pending,
                'processing_status':'baseline_complete' if inventory_complete else 'baseline_pending',
                'final_nether_status':'UNVERIFIED','terrain_status':{'v1':'not_evaluated'}})
        work=getattr(backend,'native_work',{})
    counts.update(baseline_predicted=sum(a['qualification']=='PREDICTED' for a in anchors),
                  baseline_pending=sum(a['qualification']=='PENDING' for a in anchors),confirmed_rejections=0,
                  unresolved_discovery=int(not anchors),unresolved_stronghold_coverage=1)
    return {'index':index,'seed':str(seed),'contract':BLUEPRINT_CONTRACT,'anchors':anchors,
            'counts':counts,'stage_seconds':times,'native_work':work,
            'worker_cpu_seconds':time.process_time()-cpu,'total_seconds':time.perf_counter()-start,
            'worker_pid':os.getpid(),'worker_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024),
            'biome_cache_hits':sampler.hits,'discovery_status':'PREDICTED' if anchors else 'PENDING',
            'discovery':{'stronghold':strongholds,'fortress':fortress,'seed':str(seed),'settings':dict(cfg['discovery']),
                         'coverage':{'status':'UNRESOLVED','stronghold_recall':'UNVALIDATED','authoritative_absence':False,'complete':False}},
            'effective_seed_bits':{'viability':64,'raw_MT_placement':32}}


def evaluate_locked_seed(index,seed,cfg,*,backend_factory=Backend,combined=True,short_circuit=True):
    from .config import river_policy, origin_policy, two_group_policy
    if two_group_policy(cfg):
        raise ValueError("Two-group screening requires Phase 2 Python hard-floor enforcement")
    from .baseline import structure_observation
    seed=parse_seed(seed);start=time.perf_counter();cpu=time.process_time();times={};counts={};anchors=[]
    def timed(name,fn):
        before=time.perf_counter()
        try:return fn()
        finally:times[name]=times.get(name,0)+time.perf_counter()-before
    # Complete/reference mode uses full scans and evaluates all constraints.
    capped=short_circuit and cfg['search'].get('inventory_mode')=='eligibility'
    origin=origin_policy(cfg)
    with backend_factory(seed) as backend:
        sampler=BiomeSampler(backend)
        discovery_bounds=cfg['discovery']['overworld_bounds']
        strongholds=timed('stronghold',lambda:structure_observation(backend,'stronghold',discovery_bounds,combined))
        # Broad Nether discovery is irrelevant to the centered final border.
        fortress={'type':'fortress','bounds':list(cfg['discovery']['nether_bounds']),
                  'raw':[],'predicted_viable':[],'coordinates':[],'data_status':'NOT_REQUESTED',
                  'verification':'UNVERIFIED','confirmed_absent':False,'complete':False}
        counts['stronghold_anchors']=len(strongholds['predicted_viable'])
        if origin:counts['evaluation_centers']=1
        for anchor in ([(0,0)] if origin else strongholds['predicted_viable']):
            if origin:anchor=[0,0]
            bounds=square(anchor,2048);nb=nether_square(anchor,1024)
            actual=strongholds['predicted_viable'] if origin else [anchor]
            required={'stronghold':{**strongholds,'bounds':json_bounds(bounds),'coordinates':actual,
                'raw':strongholds['raw'] if origin else [anchor],
                'predicted_viable':actual,'minimum_count':1,'predicted_count':len(actual),
                **({'count_is_complete':True} if origin else {}),
                'floor_status':'PREDICTED' if actual else 'PENDING'}}
            pending=[];nether={};optional={};biomes=None
            if True:
                counts['nether_stage_entered']=counts.get('nether_stage_entered',0)+1
                pairs=timed('final_nether_pair',lambda:backend.nether_structure_pairs(native_bounds(nb))) if combined and hasattr(backend,'nether_structure_pairs') else None
                for name in ('fortress','bastion'):
                    observation=timed('final_'+name,lambda n=name:structure_observation(backend,n,nb,combined,pair=pairs[n] if pairs else None))
                    minimum=cfg['structures']['nether_minimum_counts'][name]
                    observation.update(minimum_count=minimum,predicted_count=len(observation['predicted_viable']))
                    nether[name]=observation
                    if len(observation['predicted_viable'])<minimum:pending.append('count_'+name)
            counts['structure_stage_entered']=counts.get('structure_stage_entered',0)+1
            for position,name in enumerate(cfg['search']['structure_order']):
                if origin and position==2 and not actual:pending.append('count_stronghold')
                if pending and short_circuit:
                    required[name]={'type':name,'bounds':json_bounds(bounds),'raw':[],
                        'coordinates':[],'predicted_viable':[],'minimum_count':cfg['structures']['minimum_counts'][name],
                        'data_status':'PARTIAL','verification':'DEFERRED','confirmed_absent':False,
                        'complete':False,'inventory_status':'DEFERRED','floor_status':'PENDING'}
                    continue
                goal=cfg['structures']['minimum_counts'][name]
                observation=timed('structure_'+name,lambda n=name,g=goal:count_observation(backend,n,bounds,g,capped=capped,combined=combined))
                required[name]=observation
                counts['checked_'+name]=counts.get('checked_'+name,0)+1
                if observation['floor_status']!='PREDICTED':
                    pending.append('count_'+name);counts['pending_'+name]=counts.get('pending_'+name,0)+1
            if not pending:counts['structure_stage_passed']=counts.get('structure_stage_passed',0)+1
            if not pending or not short_circuit:
                counts['biome_stage_entered']=counts.get('biome_stage_entered',0)+1
                before=sampler.queried
                biomes=timed('biome_palette_4y',lambda:biome_palette(sampler,bounds,cfg['biomes'],complete=origin or not short_circuit))
                counts['biome_samples']=counts.get('biome_samples',0)+sampler.queried-before
                if biomes['missing_families']:pending.extend('biome_'+f for f in biomes['missing_families'])
                else:counts['biome_stage_passed']=counts.get('biome_stage_passed',0)+1
            # All jackpot counts are inventoried only for full baseline survivors.
            # No legacy presence inventory can overwrite this count contract.
            inventory_complete=not pending
            if inventory_complete:
                for name in cfg['search']['structure_order']:
                    if not required[name].get('count_is_complete',False):
                        required[name]=timed('ranking_inventory',lambda n=name:count_observation(backend,n,bounds,cfg['structures']['minimum_counts'][n],capped=False,combined=combined))
                pass # Optional and marine inventories belong to Stage 3.
            ranking=smart_score(required,nether,optional,locked=True,river=river_policy(cfg),origin=origin,
                                biome_names=(s['biome'] for s in biomes['sampling']['samples'] if s['coordinate'][1]==63) if biomes else ())
            score=ranking['score'];status='PENDING' if pending else 'PREDICTED'
            anchors.append({'id':f'{seed}:{anchor[0]}:{anchor[1]}','index':index,'seed':str(seed),'stronghold':anchor,
                **({'evaluation_center':[0,0],'center_kind':'world_origin','predicted_strongholds':actual} if origin else {}),
                'contract':BLUEPRINT_CONTRACT,'screening_revision':cfg['screening_revision'],
                'deferred_requirements':['count_monument','count_shipwreck']+([] if 'outpost' in cfg['structures']['minimum_counts'] else ['optional_outpost']),
                'marine_stage':{'status':'DEFERRED','required_counts':{n:cfg['structures']['minimum_counts'][n] for n in ('monument','shipwreck')},'trigger':'complete coastal ocean/water/land footprint'},
                'full_blueprint_certification':False,'game_version':cfg['game']['target_version'],
                'bds_version':cfg['game']['bds_version'],'backend_model':cfg['game']['backend_model'],
                'backend_commit':cfg['game']['backend_commit'],
                'bounds':{'overworld':json_bounds(bounds),'initial_overworld':list(discovery_bounds),
                          'initial_nether':list(cfg['discovery']['nether_bounds']),'final_nether':json_bounds(nb)},
                'required_structures':required,'required_nether_structures':nether,'optional_structures':optional,
                'initial_fortress':fortress,'biomes':biomes,'ranking':ranking,
                'final_nether_prediction':{'required':['fortress','bastion'],'status':'PREDICTED' if len(nether)==2 and all(len(v['predicted_viable'])>=cfg['structures']['nether_minimum_counts'][name] for name,v in nether.items()) else 'PENDING','bounds':json_bounds(nb),'actual_generation_verified':False},
                'baseline_score':score if inventory_complete else None,'baseline_score_observed':score,
                'baseline_score_complete':inventory_complete,'baseline_score_status':'PREDICTED count bonuses' if inventory_complete else 'PARTIAL; baseline unresolved',
                'baseline_score_uncertainty':score_uncertainty(score,pending,inventory_complete),
                'inventory':{'version':'blueprint-count-inventory-v1','status':'COMPLETE' if inventory_complete else 'UNRESOLVED',
                    'tasks':[],'completion_scope':'complete required predictor counts for survivors; actual generation unverified'},
                'qualification':status,'data_status':'PREDICTED','pending_reasons':pending,
                'processing_status':'baseline_complete' if inventory_complete else 'baseline_pending',
                'final_nether_status':'UNVERIFIED','terrain_status':{'v1':'not_evaluated'}})
        work=getattr(backend,'native_work',{})
    counts.update(baseline_predicted=sum(a['qualification']=='PREDICTED' for a in anchors),
                  baseline_pending=sum(a['qualification']=='PENDING' for a in anchors),confirmed_rejections=0,
                  unresolved_discovery=int(not strongholds['predicted_viable'] if origin else not anchors),unresolved_stronghold_coverage=1)
    return {'index':index,'seed':str(seed),'contract':BLUEPRINT_CONTRACT,'anchors':anchors,
            'counts':counts,'stage_seconds':times,'native_work':work,
            'worker_cpu_seconds':time.process_time()-cpu,'total_seconds':time.perf_counter()-start,
            'worker_pid':os.getpid(),'worker_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024),
            'biome_cache_hits':sampler.hits,'discovery_status':'PREDICTED' if (strongholds['predicted_viable'] if origin else anchors) else 'PENDING',
            'discovery':{'stronghold':strongholds,'fortress':fortress,'seed':str(seed),'settings':dict(cfg['discovery']),
                         'coverage':{'status':'UNRESOLVED','stronghold_recall':'UNVALIDATED','authoritative_absence':False,'complete':False}},
            'effective_seed_bits':{'viability':64,'raw_MT_placement':32}}
