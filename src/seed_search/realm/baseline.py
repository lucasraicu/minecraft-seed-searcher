"""Cheap universal baseline; predictions qualify provisionally, negatives remain pending."""
import os
import platform
import resource
import time
import numpy as np
from ..backend import Backend, STRUCTURES
from ..seeds import parse_seed
from .bounds import square, contains, native_bounds, nether_square, json_bounds
from .biomes import postprocess_ids
from .capabilities import report
from .sampling import BiomeSampler


def structure_observation(backend, name, bounds, combined=True, *, minimal=False, pair=None):
    if name not in STRUCTURES:
        return {'type':name,'bounds':json_bounds(bounds),'raw':[], 'predicted_viable':[],
                'coordinates':[],'data_status':'UNSUPPORTED','verification':'UNVERIFIED',
                'confirmed_absent':False,'complete':False}
    nb=native_bounds(bounds)
    partial=False
    if pair is not None:raw,viable=pair
    elif minimal and hasattr(backend,'structure_first') and name!='stronghold':
        point=backend.structure_first(name,nb)
        raw=viable=[point] if point is not None else []
        partial=bool(point)
    elif minimal and name=='mineshaft' and hasattr(backend,'mineshaft_first'):
        point=backend.mineshaft_first(nb)
        raw=viable=[point] if point is not None else []
        partial=bool(point)
    elif combined:raw,viable=backend.structure_pair(name,nb)
    else:raw,viable=backend.structures(name,nb,False),backend.structures(name,nb,True)
    raw=sorted({tuple(p) for p in raw if contains(p,bounds)})
    viable=sorted({tuple(p) for p in viable if contains(p,bounds)})
    return {'type':name,'bounds':json_bounds(bounds),'raw':[list(p) for p in raw],
            'predicted_viable':[list(p) for p in viable],'coordinates':[list(p) for p in viable],
            'data_status':'PREDICTED' if viable else 'PARTIAL',
            'verification':'UNVERIFIED','confirmed_absent':False,
            'complete':False,'inventory_status':'DEFERRED' if partial else 'COMPLETE',
            'detection_method':'first_viable_start' if minimal else 'complete_predictor_starts',
            'evidence_scope':'positive witness; remaining starts unqueried' if partial else 'bounded predictor domain',
            'negative_meaning':'not found by unvalidated predictor; not confirmed absent'}


def baseline_score_uncertainty(biomes, optional, cfg, pending):
    """Bonus bounds do not establish required-structure or wooded eligibility."""
    optional_max = sum(cfg['structures']['optional_bonuses'].values())
    optional_observed = sum(v.get('bonus', 0) for v in optional.values())
    biome_max = 15 + sum(cfg['biomes']['family_bonuses'].values()) + sum(cfg['biomes']['variant_bonuses'].values())
    biome_prediction = biomes.get('uncertainty', {}).get('score_interval', [biomes['score'], biome_max]) if biomes else [0, biome_max]
    biome_actual = biomes.get('uncertainty', {}).get('actual_generation_score_interval', [0, biome_max]) if biomes else [0, biome_max]
    return {'domain': 'prediction_model_only',
            'optional_prediction_interval': [optional_observed, optional_max],
            'optional_actual_generation_interval': [0, optional_max],
            'biome_prediction_interval': biome_prediction,
            'biome_actual_generation_interval': biome_actual,
            'prediction_score_interval': [biome_prediction[0] + optional_observed, biome_prediction[1] + optional_max],
            'actual_generation_score_interval': [biome_actual[0], biome_actual[1] + optional_max],
            'unresolved_required_eligibility': ['initial_fortress', *cfg['structures']['required'], 'final_fortress','final_bastion','wooded_family_coverage'],
            'pending_prediction_requirements': list(pending),
            'eligibility_verified': False,
            'interpretation': 'Observed predictor bonuses do not lower-bound actual generation; bonus intervals do not resolve required eligibility or discovery recall.'}


def evaluate_seed(index, seed, cfg, *, backend_factory=Backend, combined=True, short_circuit=True):
    if cfg.get('contract')=='master_seed_blueprint_v1':
        from .blueprint import evaluate_seed as evaluate_blueprint
        return evaluate_blueprint(index,seed,cfg,backend_factory=backend_factory,combined=combined,short_circuit=short_circuit)
    seed=parse_seed(seed);start=time.perf_counter();cpu_start=time.process_time();times={};counts={};anchors=[]
    minimal=cfg['search'].get('inventory_mode','complete')=='eligibility'
    def timed(name, fn):
        t=time.perf_counter()
        try:return fn()
        finally:times[name]=times.get(name,0)+time.perf_counter()-t
    with backend_factory(seed) as backend:
        sampler=BiomeSampler(backend)
        ob=cfg['discovery']['overworld_bounds'];nb=cfg['discovery']['nether_bounds']
        strongholds=timed('stronghold',lambda:structure_observation(backend,'stronghold',ob,combined))
        fortress=timed('initial_fortress',lambda:structure_observation(backend,'fortress',nb,combined,minimal=minimal))
        counts['stronghold_anchors']=len(strongholds['predicted_viable'])
        counts['initial_fortress_predicted']=int(bool(fortress['predicted_viable']))
        for anchor in strongholds['predicted_viable']:
            bounds=square(anchor,cfg['deployment']['overworld_side_blocks'])
            nether_bounds=nether_square(anchor,cfg['deployment']['nether_side_blocks'])
            required={'stronghold':{**strongholds,'bounds':json_bounds(bounds),
                                   'coordinates':[anchor],'predicted_viable':[anchor],'raw':[anchor]}}
            pending=[]
            if not fortress['predicted_viable']:pending.append('initial_fortress')
            nether_required={}
            pairs=timed('final_nether_pair',lambda:backend.nether_structure_pairs(native_bounds(nether_bounds))) if hasattr(backend,'nether_structure_pairs') else None
            for name in ('fortress','bastion'):
                nether_required[name]=timed('final_'+name,lambda n=name:structure_observation(backend,n,nether_bounds,combined,pair=pairs[n] if pairs else None))
                if not nether_required[name]['predicted_viable']:
                    pending.append('final_'+name)
                    counts['pending_final_'+name]=counts.get('pending_final_'+name,0)+1
            for name in cfg['search']['structure_order']:
                if pending and short_circuit:
                    required[name]={'type':name,'bounds':json_bounds(bounds),'raw':[],
                                    'coordinates':[],'predicted_viable':[], 'data_status':'PARTIAL',
                                    'verification':'DEFERRED','confirmed_absent':False,'complete':False}
                    continue
                required[name]=timed(name,lambda n=name:structure_observation(backend,n,bounds,combined,minimal=minimal))
                if not required[name]['predicted_viable']:
                    pending.append(name);counts['pending_'+name]=counts.get('pending_'+name,0)+1
            optional={};biomes=None
            if not pending or not short_circuit:
                before=sampler.queried
                biomes=timed('wooded_biomes',lambda:sampler.gate(bounds,cfg['biomes'],complete=not minimal))
                counts['biome_samples']=counts.get('biome_samples',0)+sampler.queried-before
                if biomes['qualification']=='PENDING':pending.append('wooded_family_coverage')
            if not pending and not minimal:
                for name,bonus in cfg['structures']['optional_bonuses'].items():
                    optional[name]=timed('optional_structures',lambda n=name:structure_observation(backend,n,bounds,combined))
                    optional[name]['bonus']=bonus if optional[name]['predicted_viable'] else 0
                    optional[name]['bonus_status']='PREDICTED' if optional[name]['predicted_viable'] else 'unknown; zero observed lower bound'
            status='PENDING' if pending else 'PREDICTED'
            bonus=(biomes['score'] if biomes else 0)+sum(v['bonus'] for v in optional.values())
            inventory_deferred=minimal
            tasks=['structures','biomes'] if minimal else []
            anchors.append({'id':f'{seed}:{anchor[0]}:{anchor[1]}','index':index,'seed':str(seed),'stronghold':anchor,
                            'game_version':cfg['game']['target_version'],'bds_version':cfg['game']['bds_version'],
                            'backend_model':cfg['game']['backend_model'],'backend_commit':cfg['game']['backend_commit'],
                            'bounds':{'overworld':json_bounds(bounds),'initial_overworld':list(ob),'initial_nether':list(nb),
                                      'final_nether':json_bounds(nether_bounds)},
                            'required_structures':required,'optional_structures':optional,'biomes':biomes,
                            'initial_fortress':fortress,'required_nether_structures':nether_required,
                            'final_nether_prediction':{'required':['fortress','bastion'],
                                'status':'PREDICTED' if all(v['predicted_viable'] for v in nether_required.values()) else 'PENDING',
                                'bounds':json_bounds(nether_bounds),'actual_generation_verified':False},
                            'baseline_score':None if inventory_deferred else bonus,'baseline_score_observed':bonus,
                            'baseline_score_complete':not inventory_deferred,
                            'baseline_score_status':'PARTIAL; inventory deferred' if inventory_deferred else 'PREDICTED; observed predictor score',
                            'inventory':{'version':'candidate-inventory-v1','status':'DEFERRED' if inventory_deferred else 'COMPLETE' if not pending else 'UNRESOLVED',
                                         'completion_scope':'predictor family presence and canonical biome sample; complete start counts require explicit audit; actual generation unverified',
                                         'tasks':tasks,'sampling_policy':{k:cfg['biomes'][k] for k in ('spacing','sample_y','lattice','gate_batch_size','refinement_budget') if k in cfg['biomes']}},
                            'baseline_score_uncertainty':baseline_score_uncertainty(biomes,optional,cfg,pending),
                            'qualification':status,'data_status':'PREDICTED','processing_status':'eligibility_complete_inventory_deferred' if inventory_deferred else 'baseline_complete' if not pending else 'baseline_pending',
                            'pending_reasons':pending,'final_nether_status':'UNVERIFIED',
                            'terrain_status':{'v1':'not_evaluated','v2':'not_evaluated'}})
        counts['baseline_predicted']=sum(a['qualification']=='PREDICTED' for a in anchors)
        counts['baseline_pending']=sum(a['qualification']=='PENDING' for a in anchors)
        counts['confirmed_rejections']=0
        counts['unresolved_discovery']=int(not strongholds['predicted_viable'])
        counts['unresolved_stronghold_coverage']=1
        counts['unresolved_fortress_coverage']=1
        work=getattr(backend,'native_work',{})
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
    return {'index':index,'seed':str(seed),'anchors':anchors,'counts':counts,'stage_seconds':times,
            'worker_cpu_seconds':time.process_time()-cpu_start,'biome_cache_hits':sampler.hits,
            'total_seconds':time.perf_counter()-start,'worker_pid':os.getpid(),'worker_peak_rss_bytes':rss,
            'native_work':work,'discovery_status':'PREDICTED' if anchors else 'PENDING',
            'discovery':{'stronghold':strongholds,'fortress':fortress,
                         'seed':str(seed),'settings':dict(cfg['discovery']),
                         'source':{'kind':'prediction','provider':'native',
                                   'target_version':cfg['game']['target_version'],
                                   'version':cfg['game']['backend_model'],
                                   'backend_commit':cfg['game']['backend_commit']},
                         'coverage':{'status':'UNRESOLVED','stronghold_recall':'UNVALIDATED',
                                     'fortress_recall':'UNVALIDATED','authoritative_absence':False,
                                     'complete':False}},
            'effective_seed_bits':{'viability':64,'raw_MT_placement':32}}
