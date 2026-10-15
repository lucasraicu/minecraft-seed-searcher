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
from .config import BLUEPRINT_CONTRACT, stronghold_after
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
                if family not in found and int(point[1]) in role_y and name in (PALETTE[family]|({'frozen_peaks'} if family=='peaks' and policy.get('include_frozen_peaks') else set())):
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


def smart_score(structures,nether,optional,*,coastal_footprint_verified=False,locked=False,river=False,metrics=None,origin=False,biome_names=(),two_group=False,river_bonus=True):
    """Blueprint bonuses from predictor counts; footprint bonus needs actual bounds."""
    counts={k:len(v.get('predicted_viable',[])) for k,v in {**structures,**nether,**optional}.items()}
    if two_group:
        names=set(biome_names)
        bonuses={
            'mansion':50*min(counts.get('mansion',0),2),
            'stronghold':50*int(counts.get('stronghold',0)>=2),
            'mega_ravine_hub':35*int((metrics or {}).get('mega_ravine_hub') is True),
            'river_highway':35*int((metrics or {}).get('river_highway_connected') is True),
            'ancient_city':25*max(0,min(counts.get('ancient_city',0),4)-2),
            'fortress':20*max(0,min(counts.get('fortress',0),4)-2),
            'bastion':20*max(0,counts.get('bastion',0)-3),
            'monument':30*int(coastal_footprint_verified and counts.get('monument',0)>=2),
            'trial_chamber':10*max(0,counts.get('trial_chamber',0)-10),
            'village':5*max(0,counts.get('village',0)-7),
            'ruined_portal':5*max(0,counts.get('ruined_portal',0)-7),
            'mineshaft':max(0,counts.get('mineshaft',0)-20),
            'outpost':10*max(0,counts.get('outpost',0)-1),
            'desert_pyramid':10*int(counts.get('desert_pyramid',0)>=2),
            'jungle_temple':10*int(counts.get('jungle_temple',0)>=2),
            'shipwreck':5*max(0,counts.get('shipwreck',0)-5),
            'cherry_grove':15*int('cherry_grove' in names),
            'badlands':15*int(bool(names & {'badlands','wooded_badlands','eroded_badlands'})),
            'mushroom_fields':15*int('mushroom_fields' in names),
        }
        if not river_bonus:bonuses.pop('river_highway',None)
        return {'score':sum(bonuses.values()),'bonuses':bonuses,'counts':counts,
                'source':'v2 predictor starts and supported deferred feature evidence; actual generation unverified',
                'coastal_footprint_bonus_status':'VERIFIED' if coastal_footprint_verified else 'PENDING actual footprint containment'}
    bonuses={}
    for name,floor,points in (('village',6 if locked else 5,5),('ruined_portal',6 if locked else 3,5),('shipwreck',5 if river else 4 if locked else 2,5),('mineshaft',15 if locked else 5,1)):
        bonuses[name]=max(0,counts.get(name,0)-floor)*points
    for name,floor,cap,points in (('trial_chamber',5,counts.get('trial_chamber',0),10),('ancient_city',2,4,15),('fortress',2,4,15),('bastion',2,4,15)) if locked else (('trial_chamber',2,4,10),('ancient_city',1,3,15),('fortress',1,3,15),('bastion',1,3,15)):
        bonuses[name]=max(0,min(cap,counts.get(name,0))-floor)*points
    for name in ('desert_pyramid','jungle_temple'):
        n=counts.get(name,0);bonuses[name]=(20 if n>=2 else 0)+(10 if n>=3 and (not locked or name=='desert_pyramid') else 0)
    bonuses['monument']=30*int(counts.get('monument',0)>=2)
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
    if not river_bonus:bonuses.pop('river_highway',None)
    return {'score':sum(bonuses.values()),'bonuses':bonuses,'counts':counts,
            'source':'predictor start counts; actual generation unverified',
            'coastal_footprint_bonus_status':'VERIFIED' if coastal_footprint_verified else 'PENDING actual footprint containment'}


def score_uncertainty(score,pending,complete):
    return {'domain':'prediction_model_only','prediction_score_interval':[score,score if complete else None],
            'actual_generation_score_interval':[0,None],'pending_prediction_requirements':list(pending),
            'eligibility_verified':False,'interpretation':'Count and biome witnesses are predictions; actual counts, surface palette, cave generation and monument extent require verification.'}


def evaluate_seed(index,seed,cfg,*,backend_factory=Backend,combined=True,short_circuit=True):
    from .config import locked_policy, dynamic_policy
    if dynamic_policy(cfg):return evaluate_dynamic_seed(index,seed,cfg,backend_factory=backend_factory,combined=combined,short_circuit=short_circuit)
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
    two_group=two_group_policy(cfg)
    floors=cfg['structures'].get('hard_floors',{}) if two_group else {}
    budget=cfg['search'].get('max_misses',0) if two_group else 0
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
            pending=[];fatal=[];deficits=[];nether={};optional={};biomes=None
            if True:
                counts['nether_stage_entered']=counts.get('nether_stage_entered',0)+1
                pairs=timed('final_nether_pair',lambda:backend.nether_structure_pairs(native_bounds(nb))) if combined and hasattr(backend,'nether_structure_pairs') else None
                for name in ('fortress','bastion'):
                    observation=timed('final_'+name,lambda n=name:structure_observation(backend,n,nb,combined,pair=pairs[n] if pairs else None))
                    minimum=cfg['structures']['nether_minimum_counts'][name]
                    observation.update(minimum_count=minimum,predicted_count=len(observation['predicted_viable']))
                    nether[name]=observation
                    observed=len(observation['predicted_viable'])
                    if observed<minimum:
                        pending.append('count_'+name)
                        if two_group: deficits.append(name)
                    if two_group and observed<floors[name]:fatal.append('floor_'+name)
            counts['structure_stage_entered']=counts.get('structure_stage_entered',0)+1
            for position,name in enumerate(cfg['search']['structure_order']):
                # The full/reference provider has already inventoried Strongholds,
                # so report absence even when another predicate rejected earlier.
                if origin and position==stronghold_after(cfg) and not actual:
                    pending.append('count_stronghold')
                    if two_group:fatal.append('floor_stronghold')
                blocked=(fatal or len(deficits)>budget) if two_group else pending
                if blocked and short_circuit:
                    required[name]={'type':name,'bounds':json_bounds(bounds),'raw':[],
                        'coordinates':[],'predicted_viable':[],'minimum_count':cfg['structures']['minimum_counts'][name],
                        'data_status':'PARTIAL','verification':'DEFERRED','confirmed_absent':False,
                        'complete':False,'inventory_status':'DEFERRED','floor_status':'PENDING'}
                    continue
                goal=cfg['structures']['minimum_counts'][name]
                observation=timed('structure_'+name,lambda n=name,g=goal:count_observation(backend,n,bounds,g,capped=capped,combined=combined))
                required[name]=observation
                counts['checked_'+name]=counts.get('checked_'+name,0)+1
                observed=observation['predicted_count']
                if observed<goal:
                    pending.append('count_'+name);counts['pending_'+name]=counts.get('pending_'+name,0)+1
                    if two_group and name not in ('outpost','desert_pyramid','jungle_temple'):deficits.append(name)
                if two_group and observed<floors[name]:fatal.append('floor_'+name)
            structure_pass=(not fatal and len(deficits)<=budget) if two_group else not pending
            if structure_pass:counts['structure_stage_passed']=counts.get('structure_stage_passed',0)+1
            if structure_pass or not short_circuit:
                counts['biome_stage_entered']=counts.get('biome_stage_entered',0)+1
                before=sampler.queried
                biomes=timed('biome_palette_4y',lambda:biome_palette(sampler,bounds,cfg['biomes'],complete=origin or not short_circuit))
                counts['biome_samples']=counts.get('biome_samples',0)+sampler.queried-before
                if biomes['missing_families']:pending.extend('biome_'+f for f in biomes['missing_families'])
                else:counts['biome_stage_passed']=counts.get('biome_stage_passed',0)+1
            from .config import marine_baseline_policy
            marine_baseline=marine_baseline_policy(cfg)
            if marine_baseline and (not short_circuit or (biomes and not biomes['missing_families'] and structure_pass)):
                for name in ('monument','shipwreck'):
                    goal=cfg['structures']['minimum_counts'][name]
                    observation=timed('structure_'+name,lambda n=name,g=goal:count_observation(backend,n,bounds,g,capped=capped,combined=combined))
                    required[name]=observation
                    counts['checked_'+name]=counts.get('checked_'+name,0)+1
                    if observation['predicted_count']<goal:
                        pending.append('count_'+name)
                        fatal.append('floor_'+name)
                        counts['pending_'+name]=counts.get('pending_'+name,0)+1
                        if short_circuit:break
            if marine_baseline:
                for name in ('monument','shipwreck'):
                    if name not in required:
                        required[name]={'type':name,'bounds':json_bounds(bounds),'raw':[],
                            'coordinates':[],'predicted_viable':[],
                            'minimum_count':cfg['structures']['minimum_counts'][name],
                            'data_status':'PARTIAL','verification':'DEFERRED','confirmed_absent':False,
                            'complete':False,'inventory_status':'DEFERRED','floor_status':'PENDING'}
            # All jackpot counts are inventoried only for full baseline survivors.
            # No legacy presence inventory can overwrite this count contract.
            biome_failures=['biome_'+f for f in biomes['missing_families']] if biomes else []
            inventory_complete=structure_pass and not fatal and not biome_failures if two_group else not pending
            if inventory_complete:
                for name in cfg['search']['structure_order']:
                    if not required[name].get('count_is_complete',False) or required[name].get('raw_inventory_status')=='NOT_RECORDED':
                        required[name]=timed('ranking_inventory',lambda n=name:count_observation(backend,n,bounds,cfg['structures']['minimum_counts'][n],capped=False,combined=combined))
                if marine_baseline:
                    for name in ('monument','shipwreck'):
                        if not required[name].get('count_is_complete',False) or required[name].get('raw_inventory_status')=='NOT_RECORDED':
                            required[name]=timed('ranking_inventory',lambda n=name:count_observation(backend,n,bounds,cfg['structures']['minimum_counts'][n],capped=False,combined=combined))
            ranking=smart_score(required,nether,optional,locked=True,river=river_policy(cfg),origin=origin,two_group=two_group,river_bonus=not marine_baseline,
                                biome_names=(s['biome'] for s in biomes['sampling']['samples'] if s['coordinate'][1]==63) if biomes else ())
            score=ranking['score'];status='PREDICTED' if inventory_complete else 'PENDING'
            anchors.append({'id':f'{seed}:{anchor[0]}:{anchor[1]}','index':index,'seed':str(seed),'stronghold':anchor,
                **({'evaluation_center':[0,0],'center_kind':'world_origin','predicted_strongholds':actual} if origin else {}),
                'contract':BLUEPRINT_CONTRACT,'screening_revision':cfg['screening_revision'],
                'deferred_requirements':([] if marine_baseline else ['count_monument','count_shipwreck']+([] if 'outpost' in cfg['structures']['minimum_counts'] else ['optional_outpost'])),
                'marine_stage':({'status':'PREDICTED' if all(required.get(n,{}).get('predicted_count',0)>=cfg['structures']['minimum_counts'][n] for n in ('monument','shipwreck')) else 'PENDING',
                                 'required_counts':{n:cfg['structures']['minimum_counts'][n] for n in ('monument','shipwreck')},
                                 'predicted_counts':{n:required.get(n,{}).get('predicted_count') for n in ('monument','shipwreck')},
                                 'actual_generation_verified':False} if marine_baseline else
                                {'status':'DEFERRED','required_counts':{n:cfg['structures']['minimum_counts'][n] for n in ('monument','shipwreck')},'trigger':'complete coastal ocean/water/land footprint'}),
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
                'baseline_score_uncertainty':score_uncertainty(score,fatal+biome_failures if two_group else pending,inventory_complete),
                'inventory':{'version':'blueprint-count-inventory-v1','status':'COMPLETE' if inventory_complete else 'UNRESOLVED',
                    'tasks':[],'completion_scope':'complete required predictor counts for survivors; actual generation unverified'},
                'qualification':status,'data_status':'PREDICTED','pending_reasons':pending,
                **({'deficit_categories':deficits,'fatal_reasons':fatal,'biome_failures':biome_failures,
                    'deficit_budget':budget,'baseline_qualification':status} if two_group else {}),
                'processing_status':'baseline_complete' if inventory_complete else 'baseline_pending',
                'final_nether_status':'UNVERIFIED','terrain_status':{'v1':'not_evaluated'}})
            if two_group:
                from .spawn import classify_spawn
                anchors[-1]['spawn_stage']=classify_spawn(anchors[-1],cfg)
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


def dynamic_score(counts,biome_names,hub=0):
    """Revision 4.1 predictor score; named ordinal jackpots are awarded once."""
    n=lambda name:counts.get(name,0)
    score=50*(n('mansion')>=2)+50*(n('stronghold')>=2)+30*(n('monument')>=2)
    score+=max(0,n('village')-8)*25+max(0,n('trial_chamber')-7)*10
    score+=25*(n('ancient_city')>=4)
    score+=sum(20*(n(name)>=3) for name in ('desert_pyramid','jungle_temple','outpost','fortress','bastion'))
    score+=max(0,n('shipwreck')-6)*5+max(0,n('ruined_portal')-7)*5
    score+=max(0,n('mineshaft')-15)+min(40,max(0,hub))
    for name,first_pts in (('swamp_hut',15),('igloo',10),('trail_ruins',10),('ocean_ruin',10),('buried_treasure',10)):
        cnt=n(name);score+=(first_pts+(cnt-1)*3 if cnt>0 else 0)
    names=set(biome_names)
    for points,members in DYNAMIC_LUXURIES:
        if names.intersection(members):score+=points
    return score


DYNAMIC_LUXURIES=((30,('cherry_grove',)),(20,('badlands','wooded_badlands','eroded_badlands')),
    (25,('mushroom_fields',)),(30,('pale_garden',)),(25,('mangrove_swamp',)),
    (10,('flower_forest',)),(10,('bamboo_jungle',)),(15,('warm_ocean',)),
    (15,('ice_spikes',)),(15,('windswept_savanna','shattered_savanna')))


def evaluate_dynamic_seed(index,seed,cfg,*,backend_factory=Backend,combined=True,short_circuit=True):
    """Independent complete-inventory oracle for the exact dynamic center."""
    from .baseline import structure_observation
    from .dynamic import (candidate_centers,OVERWORLD_NAMES,NETHER_NAMES,OPTIONAL_NAMES,
                          overworld_bounds,nether_bounds,nether_palette,hub_bonus,weighted_radial,PaletteIndex)
    from .config import baseline_requirements
    seed=parse_seed(seed);started=time.perf_counter();cpu=time.process_time()
    timings={};anchors=[];counts={}
    def timed(name,fn):
        before=time.perf_counter()
        try:return fn()
        finally:timings[name]=timings.get(name,0)+time.perf_counter()-before
    ow_macro=tuple(cfg['discovery']['overworld_bounds'])
    nw_macro=tuple(cfg['discovery']['nether_bounds'])
    with backend_factory(seed) as backend:
        sampler=BiomeSampler(backend)
        strongholds=timed('stronghold',lambda:structure_observation(backend,'stronghold',ow_macro,combined))
        inventories={'stronghold':strongholds}
        replay_center=getattr(backend,'dynamic_center',None)
        if getattr(backend,'dynamic_no_anchor',False):eligible=[]
        elif replay_center is None:
            mansion=timed('structure_mansion',lambda:count_observation(backend,'mansion',ow_macro,1,capped=False,combined=combined))
            inventories['mansion']=mansion
            if mansion['predicted_viable']:
                inventories['outpost']=timed('structure_outpost',lambda:structure_observation(backend,'outpost',ow_macro,combined))
            if mansion['predicted_viable'] and len(inventories.get('outpost',{}).get('predicted_viable',[]))>=cfg['structures']['hard_floors']['outpost']:
                pairs=timed('final_nether_pair',lambda:backend.nether_structure_pairs(native_bounds(nw_macro))) if combined and hasattr(backend,'nether_structure_pairs') else None
                for name in NETHER_NAMES:
                    inventories[name]=timed('final_'+name,lambda name=name:structure_observation(backend,name,nw_macro,combined,pair=pairs[name] if pairs else None))
            if (strongholds['predicted_viable'] and mansion['predicted_viable'] and
                    len(inventories.get('outpost',{}).get('predicted_viable',[]))>=cfg['structures']['hard_floors']['outpost'] and
                    len(inventories.get('fortress',{}).get('predicted_viable',[]))>=cfg['structures']['hard_floors']['fortress'] and
                    len(inventories.get('bastion',{}).get('predicted_viable',[]))>=cfg['structures']['nether_minimum_counts']['bastion']):
                for name in OVERWORLD_NAMES:
                    if name not in inventories:
                        inventories[name]=timed('structure_'+name,lambda name=name:structure_observation(backend,name,ow_macro,combined))
                for name in OPTIONAL_NAMES:
                    ob=structure_observation(backend,name,ow_macro,combined)
                    if name=='igloo':
                        ob['predicted_viable']=[p for p in ob['predicted_viable'] if backend.igloo_basement(*p)]
                        ob['coordinates']=ob['predicted_viable']
                        ob['data_status']='PREDICTED' if ob['predicted_viable'] else 'PARTIAL'
                    inventories[name]=ob
                all_points={name:[tuple(p) for p in observation['predicted_viable']]
                            for name,observation in inventories.items()}
                all_ideals={**cfg['structures']['minimum_counts'],**cfg['structures']['nether_minimum_counts']}
                strict={'stronghold','mansion','monument','outpost','fortress','bastion'}
                ideals={name:all_ideals[name] for name in all_ideals if name not in strict}
                eligible=candidate_centers(all_points,cfg['structures']['hard_floors'],
                    ideals,cfg['search']['density_weights'],cfg['search']['max_misses'])
                # Strict categories reject below their configurable targets.
                eligible=[item for item in eligible if all(item.counts[name]>=all_ideals[name] for name in strict)]
            else:eligible=[]
        else:eligible=[type('Selected',(),{'center':tuple(replay_center)})()]
        selected=None;biomes=None;nether_biomes=None
        if replay_center is None and eligible:
            palette_index=timed('biome_palette_4y',lambda:PaletteIndex(sampler,cfg['biomes']))
            def center_key(item):
                center=item.center
                structures={name:[p for p in points if contains(p,overworld_bounds(center))]
                            for name,points in all_points.items() if name in OVERWORLD_NAMES}
                score=dynamic_score(item.counts,palette_index.luxuries(center),hub_bonus(structures,center))
                return (len(item.deficits),-score,round(item.radial,6),center[0]**2+center[1]**2,*center)
            eligible=sorted((item for item in eligible if palette_index.valid(item.center)),key=center_key)
        for item in eligible:
            center=item.center;bounds=overworld_bounds(center)
            palette=timed('biome_palette_4y',lambda:biome_palette(sampler,bounds,cfg['biomes'],complete=True))
            npalette=timed('nether_palette',lambda:nether_palette(sampler,center))
            if not palette['missing_families'] and not npalette['missing_families']:
                selected=center;biomes=palette;nether_biomes=npalette;break
        if selected is not None:
            ow=overworld_bounds(selected);nw=nether_bounds(selected)
            def trim(name,bounds):
                if replay_center is not None and name!='stronghold':
                    return count_observation(backend,name,bounds,0,capped=False,combined=combined) if name=='mansion' else structure_observation(backend,name,bounds,combined)
                source=inventories[name]
                raw=[p for p in source['raw'] if contains(p,bounds)]
                viable=[p for p in source['predicted_viable'] if contains(p,bounds)]
                ob={**source,'bounds':json_bounds(bounds),'raw':raw,
                    'predicted_viable':viable,'coordinates':viable,
                    'data_status':'PREDICTED' if viable else 'PARTIAL',
                    'inventory_status':'COMPLETE','count_is_complete':True}
                if name=='mansion':
                    ob['unfiltered_predicted_viable']=[p for p in source.get('unfiltered_predicted_viable',[]) if contains(p,bounds)]
                    ob['anchor_biome_witnesses']=[row for row in source.get('anchor_biome_witnesses',[]) if contains((row['coordinate'][0],row['coordinate'][2]),bounds)]
                return ob
            required={name:trim(name,ow) for name in OVERWORLD_NAMES}
            nether={name:trim(name,nw) for name in NETHER_NAMES}
            optional={name:trim(name,ow) for name in OPTIONAL_NAMES}
            for ob in optional.values():ob['count_is_complete']=True
            optional['igloo']['variant_policy']='Pinned MC_26_50 basement PRNG prediction; generated basement unverified'
            all_observations={**required,**nether}
            all_ideals={**cfg['structures']['minimum_counts'],**cfg['structures']['nether_minimum_counts']}
            strict={'stronghold','mansion','monument','outpost','fortress','bastion'}
            deficits=[];fatal=[]
            for name,ob in all_observations.items():
                observed=len(ob['predicted_viable']);goal=all_ideals[name]
                ob.update(minimum_count=goal,predicted_count=observed,count_is_complete=True,
                          floor_status='PREDICTED' if observed>=goal else 'PENDING')
                if observed<cfg['structures']['hard_floors'][name]:fatal.append('floor_'+name)
                elif observed<goal:
                    if name in strict:fatal.append('count_'+name)
                    else:deficits.append(name)
            actual=required['stronghold']['predicted_viable']
            surface=[row['biome'] for row in biomes['sampling']['samples'] if row['coordinate'][1]==63]
            structures={name:ob['predicted_viable'] for name,ob in required.items()}
            hub=hub_bonus(structures,selected)
            radial=weighted_radial(structures,selected)
            score=dynamic_score({name:len(ob['predicted_viable']) for name,ob in {**all_observations,**optional}.items()},surface,hub)
            density=sum(cfg['search']['density_weights'][name]*len(required[name]['predicted_viable'])
                        for name in cfg['search']['density_weights'])
            qualified=not fatal and len(deficits)<=cfg['search']['max_misses'] and not biomes['missing_families']
            if qualified:
                anchor={'id':f'{seed}:{selected[0]}:{selected[1]}','index':index,'seed':str(seed),
                    'stronghold':actual[0],'evaluation_center':list(selected),
                    'center_kind':'snapped_weighted_centroid','predicted_strongholds':actual,
                    'contract':BLUEPRINT_CONTRACT,'screening_revision':cfg['screening_revision'],
                    'full_blueprint_certification':False,'game_version':cfg['game']['target_version'],
                    'bds_version':cfg['game']['bds_version'],'backend_model':cfg['game']['backend_model'],
                    'backend_commit':cfg['game']['backend_commit'],
                    'bounds':{'overworld':json_bounds(ow),'initial_overworld':list(ow_macro),
                              'initial_nether':list(nw_macro),'final_nether':json_bounds(nw),
                              'nether_center_exact':{'x':[selected[0],8],'z':[selected[1],8]},
                              'final_nether_exact':[[selected[0]-3328,8],[selected[1]-3328,8],
                                                    [selected[0]+3328,8],[selected[1]+3328,8]]},
                    'required_structures':required,'required_nether_structures':nether,
                    'optional_structures':optional,'initial_fortress':{'type':'fortress','data_status':'NOT_REQUESTED'},
                    'biomes':biomes,'nether_biomes':nether_biomes,
                    'ranking':{'score':score,'deficit_tier':len(deficits),
                               'weighted_radial_dist':radial,'origin_distance':float(np.hypot(*selected)),
                               'components':{'dynamic_density':density,'hub_bonus':hub}},
                    'weighted_radial_dist':radial,'origin_distance':float(np.hypot(*selected)),
                    'final_nether_prediction':{'required':['fortress','bastion'],'status':'PREDICTED',
                                               'bounds':json_bounds(nw),'actual_generation_verified':False},
                    'marine_stage':{'status':'PREDICTED','required_counts':{n:all_ideals[n] for n in ('monument','shipwreck')},
                                    'predicted_counts':{n:len(required[n]['predicted_viable']) for n in ('monument','shipwreck')},
                                    'actual_generation_verified':False},
                    'deferred_requirements':[],'baseline_score':score,'baseline_score_observed':score,
                    'baseline_score_complete':True,'baseline_score_status':'PREDICTED count and palette bonuses',
                    'baseline_score_uncertainty':score_uncertainty(score,[],True),
                    'inventory':{'version':'dynamic-1664-count-inventory-v1','status':'COMPLETE','tasks':[],
                                 'completion_scope':'complete predictor counts at selected center; actual generation unverified'},
                    'qualification':'PREDICTED','data_status':'PREDICTED','pending_reasons':[],
                    'deficit_categories':deficits,'fatal_reasons':[],'biome_failures':[],
                    'deficit_budget':cfg['search']['max_misses'],'baseline_qualification':'PREDICTED',
                    'processing_status':'baseline_complete','final_nether_status':'UNVERIFIED',
                    'terrain_status':{'v1':'not_evaluated'},
                    'density_score':density}
                anchors=[anchor]
                from .spawn import classify_spawn
                anchor['spawn_stage']=classify_spawn(anchor,cfg)
        work=getattr(backend,'native_work',{})
    counts.update(stronghold_anchors=len(strongholds['predicted_viable']),evaluation_centers=len(anchors),
                  baseline_predicted=len(anchors),baseline_pending=0,confirmed_rejections=0,
                  unresolved_discovery=int(not anchors),unresolved_stronghold_coverage=1)
    return {'index':index,'seed':str(seed),'contract':BLUEPRINT_CONTRACT,'anchors':anchors,
            'counts':counts,'stage_seconds':timings,'native_work':work,
            'worker_cpu_seconds':time.process_time()-cpu,'total_seconds':time.perf_counter()-started,
            'worker_pid':os.getpid(),'worker_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024),
            'biome_cache_hits':sampler.hits,'discovery_status':'PREDICTED' if anchors else 'PENDING',
            'discovery':{'stronghold':strongholds,'fortress':{'type':'fortress','data_status':'NOT_REQUESTED'},
                         'seed':str(seed),'settings':dict(cfg['discovery']),
                         'coverage':{'status':'UNRESOLVED','stronghold_recall':'UNVALIDATED',
                                     'authoritative_absence':False,'complete':False}},
            'effective_seed_bits':{'viability':64,'raw_MT_placement':32}}
