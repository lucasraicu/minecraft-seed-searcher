"""Post-terrain marine predictor evidence; never actual-world certification."""
import copy
import time

import numpy as np
from scipy import ndimage

from ..backend import Backend, biome_name
from .blueprint import count_observation, smart_score, score_uncertainty
from .config import river_policy, two_group_policy, marine_baseline_policy
from .bounds import contains
from .coastal import _ocean_mask, _overlap, evaluate_coastal


def evaluate_marine_stage(candidate, cfg, raster, precheck, *, backend_factory=Backend):
    """Query only after a complete finest-resolution sampled coastal footprint.

    The caller commits this patch with the terrain work/observation transaction.
    A failed call publishes no candidate patch; retries regenerate identical
    semantic inventories. Model footprints and sampled beach witnesses remain
    explicitly unverified. Near misses keep their baseline classification.
    """
    if not cfg.get('screening_revision') or (candidate.get('marine_stage') or {}).get('status') not in ('DEFERRED','PENDING'):
        return precheck, None
    if (raster.resolution != min(cfg['terrain']['resolutions']) or
            not precheck.get('model_geometry_pass') or
            (precheck.get('metrics') or {}).get('known_fraction') != 1. or
            precheck.get('evidence') not in ('PREDICTED', 'VERIFIED')):
        return precheck, None
    bounds=candidate['bounds']['overworld']
    ocean, available, _ = _ocean_mask(raster)
    def pending(reason):
        stage={'status':'PENDING','reason':reason,'required_counts':{n:cfg['structures']['minimum_counts'][n] for n in ('monument','shipwreck')},
               'source':'sampled coastal model; actual generation unverified'}
        return {**precheck,'marine_stage':stage}, {'id':candidate['id'],'marine_stage':stage,
            'full_blueprint_certification':False}
    if not available:return pending('ocean_evidence_unavailable')
    ocean &= (_overlap(raster,bounds)>0)
    labels, _ = ndimage.label(ocean)
    coastal=np.isin(labels,(precheck.get('metrics') or {}).get('coastal_component_ids',[]))
    if not coastal.any():return pending('coastal_ocean_absent_in_sample')
    required=copy.deepcopy(candidate['required_structures'])
    optional=copy.deepcopy(candidate.get('optional_structures') or {})
    started=time.perf_counter()
    with backend_factory(candidate['seed']) as backend:
        for name in ('monument','shipwreck'):
            required[name]=count_observation(backend,name,bounds,cfg['structures']['minimum_counts'][name],capped=False)
        if 'outpost' not in required:
            optional['outpost']=count_observation(backend,'outpost',bounds,0,capped=False)
    # Keep full raw/viable inventories alongside the qualifying coastal subset.
    center=candidate.get('evaluation_center',candidate['stronghold'])
    terrain=evaluate_coastal(raster,center,bounds,center,
                             thresholds=cfg['terrain']['v1'],monuments=required['monument']['predicted_viable'],
                             biome_fit=precheck.get('biome_fit',0.),baseline_quality=precheck.get('baseline_quality',0.))
    qualified_monuments={tuple(r['position']) for r in terrain['metrics']['monument_footprints'] if r['model_pass']}
    for name in ('monument','shipwreck'):
        observation=required[name];all_viable=observation['predicted_viable'];qualified=[];witnesses=[]
        for point in all_viable:
            if name=='monument':passed=tuple(point) in qualified_monuments
            else:
                index=raster.index(point);passed=False
                if index is not None and contains(point,bounds):
                    row,col=index
                    beach=biome_name(int(raster.biomes[index])) in ('beach','snowy_beach','stony_shore') if raster.biomes is not None else False
                    adjacent=coastal[max(0,row-1):row+2,max(0,col-1):col+2].any()
                    passed=bool(coastal[index] or (beach and adjacent))
                    witnesses.append({'position':list(point),'sampled_cell':list(index),'coastal_or_beach_model_pass':passed})
            if passed:qualified.append(point)
        observation.update(unfiltered_predicted_viable=all_viable,predicted_viable=qualified,coordinates=qualified,
                           predicted_count=len(qualified),floor_status='PREDICTED' if len(qualified)>=observation['minimum_count'] else 'PENDING',
                           coastal_filter_scope='complete start inventory; sampled coastal model, actual generation unverified')
        if name=='shipwreck':observation['coastal_witnesses']=witnesses
    missing=['count_'+name for name in ('monument','shipwreck') if required[name]['floor_status']!='PREDICTED']
    from .config import origin_policy
    source=terrain.get('source') or {}
    actual=source.get('kind')=='actual_generation' if isinstance(source,dict) else False
    v2=two_group_policy(cfg)
    ranking=smart_score(required,candidate['required_nether_structures'],optional,locked=True,river=river_policy(cfg),
                        origin=origin_policy(cfg),two_group=v2,river_bonus=not marine_baseline_policy(cfg),
                        biome_names=(s['biome'] for s in ((candidate.get('biomes') or {}).get('sampling') or {}).get('samples',()) if s['coordinate'][1]==63),
                        metrics=terrain['metrics'] if not v2 or actual else None,
                        coastal_footprint_verified=actual and len(qualified_monuments)>=2)
    patch={'id':candidate['id'],'required_structures':required,'optional_structures':optional,'ranking':ranking,
           **({'combined_score':ranking['score']} if two_group_policy(cfg) else {'baseline_score_observed':ranking['score']}),
           **({'terrain_score_metrics':{k:terrain['metrics'][k] for k in ('river_highway_connected','river_evidence','river_navigability_verified')}} if river_policy(cfg) and not marine_baseline_policy(cfg) else {}),
           **({} if two_group_policy(cfg) else {
               'baseline_score_uncertainty':score_uncertainty(ranking['score'],candidate['pending_reasons'],candidate.get('baseline_score_complete',False)),
               'baseline_score':ranking['score'] if candidate.get('baseline_score_complete') else None}),
           'deferred_requirements':[],
           'marine_stage':{'status':'PENDING' if missing else 'PREDICTED','missing_requirements':missing,
                           'required_counts':{n:cfg['structures']['minimum_counts'][n] for n in ('monument','shipwreck')},
                           'resolution':raster.resolution,'bounds':list(bounds),
                           'source':'pinned predictor with sampled coastal containment; actual world unverified'},
           'full_blueprint_certification':False}
    terrain['marine_stage']=patch['marine_stage'];terrain['marine_query_seconds']=time.perf_counter()-started
    if missing:
        terrain['model_geometry_pass']=False;terrain['geometry_pass']=False
        terrain['reasons'].extend(missing)
        terrain['qualification']='PREDICTED_NEAR_MATCH' if raster.metadata.get('source')!='actual' else 'PENDING'
    return terrain,patch
