"""Configured normalized scores and explicit intervals for missing measurements."""
import math
import numpy as np
from scipy import ndimage
from .geometry import band, angular_metrics
from .wood import wood_masks


def landscape_scores(terrain,island,component,cfg):
    h=terrain['height'];b=terrain['biomes'];step=terrain['step']
    dense,sparse=wood_masks(b);land=h>=63
    distance=ndimage.distance_transform_edt(~island,sampling=step)
    outside=land&~island&(distance<=cfg['overworld']['surrounding_range_from_shore_blocks'])
    count=int(outside.sum()); icount=int(island.sum())
    if not icount: raise ValueError('Island disappeared on landscape raster')
    island_wood=float((dense&island).sum()/icount);extwood=float((dense&outside).sum()/count) if count else 0.0
    sparse_fraction=float((sparse&outside).sum()/count) if count else 0.0
    from .backend import biome_name
    high_mask=None
    if not cfg['mountains']['snowy_summits_allowed']:
        snow=[i for i in np.unique(b) if any(v in biome_name(i) for v in ('snowy','frozen','ice_spikes'))]
        high_mask=~np.isin(b,snow)
    rays=angular_metrics(h,island,component['center'],*terrain['bounds'][:2],step,cfg,high_mask=high_mask)
    known_rays=rays['unknown_rays']==0
    gap=rays['median_gap']; enclosure=rays['enclosure_fraction_bounds'][0]
    size=band(component['equivalent_diameter'],*cfg['island']['preferred_equivalent_diameter_blocks'])
    water=min(1,enclosure/cfg['water']['full_credit_enclosure_fraction'])*band(gap,*cfg['water']['preferred_gap_blocks']) if gap is not None else 0.0
    scores={'island_size':size,'island_openness':1-island_wood,
            'water':water if known_rays else None,
            'mountains':min(1,rays['high_terrain_fraction_bounds'][0]/cfg['mountains']['preferred_directional_fraction']) if known_rays else None,
            'wood':min(1,extwood/cfg['wood']['surrounding_land']['full_credit_wooded_fraction'])}
    patches,patch_count=ndimage.label(outside&dense,np.ones((3,3),int)); forest=[]
    for sl in ndimage.find_objects(patches):
        if sl is None:continue
        zz,xx=sl
        forest.append({'x':terrain['bounds'][0]+(xx.start+xx.stop-1)//2*step,
                       'z':terrain['bounds'][1]+(zz.start+zz.stop-1)//2*step})
    rel=h[island]
    metrics={'island_woodland_fraction':island_wood,'surrounding_woodland_fraction':extwood,
             'surrounding_sparse_wood_fraction':sparse_fraction,'surrounding_land_area_blocks2':count*step**2,
             'surrounding_wooded_area_blocks2':int((dense&outside).sum())*step**2,
             'wood_preference_met':extwood>=cfg['wood']['surrounding_land']['preferred_wooded_fraction'],
             'forest_patch_coordinates':forest,'wood_evidence':'surface_biome_proxy_not_tree_counts',
             'island_height_percentiles':np.percentile(rel,[10,50,90]).tolist(),
             'island_height_range':[int(rel.min()),int(rel.max())],
             'buildability':'manual_Chunkbase_terrain_review_required',
             'island_span_blocks':[component['bounds'][2]-component['bounds'][0],component['bounds'][3]-component['bounds'][1]],
             'biome_inventory':{},**rays}
    from .backend import biome_name
    metrics['biome_inventory']={biome_name(i):int((b==i).sum()) for i in np.unique(b)}
    return scores,metrics


def structure_scores(structures,cfg):
    budget=cfg['structures']['category_budget_fractions']; scale=cfg['overworld']['distance_score_scale_blocks']
    factors={}
    for name,r in structures.items():
        if name in ('fortress','bastion'):continue
        factors[name]=math.exp(-r['distance']/scale) if r['distance'] is not None else None if r['rejected_raw_review'] or name=='stronghold' else 0.0
    known=sum(budget[t]*factors[t] for t in ('trial_chamber','stronghold','mineshaft','ancient_city') if factors[t] is not None)
    unknown=sum(budget[t] for t in ('trial_chamber','stronghold','mineshaft','ancient_city') if factors[t] is None)
    types=cfg['structures']['secondary_types']; secondary=budget['secondary_combined']/len(types)
    known+=sum(secondary*factors[t] for t in types if factors[t] is not None)
    unknown+=sum(secondary for t in types if factors[t] is None)
    ns=[]
    for t in ('fortress','bastion'):
        distance=structures[t]['distance']
        ns.append(min(1,cfg['nether']['full_credit_distance_blocks']/distance) if distance else 1 if distance==0 else None)
    if cfg['nether']['bastion_required']:
        nether=sum(ns)/2 if all(v is not None for v in ns) else None
    else:
        optional_weight=cfg['nether']['optional_bastion_proximity_weight']
        # An optional unresolved/missing Bastion must not create an unknown
        # required category or hide a Fortress/Stronghold candidate.
        nether=(1-optional_weight)*ns[0]+optional_weight*(ns[1] or 0) if ns[0] is not None else None
    return {'overworld_structures':known if unknown==0 else None,'nether_proximity':nether},factors,[known,known+unknown]


def weighted_score(scores,cfg,structure_interval=None):
    lower=upper=0.0;unknown=[]
    # SQLite persists configuration as sorted JSON; YAML insertion order must
    # not change floating-point accumulation or unknown-component ordering.
    for name,weight in sorted(cfg['score_weights'].items()):
        value=scores[name]
        if value is None:
            unknown.append(name)
            if name=='overworld_structures' and structure_interval:
                lower+=weight*structure_interval[0];upper+=weight*structure_interval[1]
            else:upper+=weight
        else:
            if not 0<=value<=1:raise ValueError(f'Invalid normalized score {name}')
            lower+=weight*value;upper+=weight*value
    return {'total':lower if not unknown else None,'interval':[lower,upper],'components':scores,'unknown_components':unknown}


def ranking_key(c):
    m=c['metrics'];s=c['score']
    return (-(s['total'] if s['total'] is not None else s['interval'][0]),
            m['largest_mountain_gap_degrees'],-(m['median_high_relative_height'] or 0),
            m['median_mountain_distance_from_shore'] if m['median_mountain_distance_from_shore'] is not None else float('inf'),
            int(c['seed']),*c['center'])


def distinct_rank(candidates,limit):
    # Never compare an interval as a known total. Each list has its own ranking.
    lists={ 'ranked':[],'review':[],'near_misses':[]}
    for c in sorted(candidates,key=ranking_key):
        group='near_misses' if c['nether_status']=='missing_required_local_prediction' else 'review' if c['score']['total'] is None or c['nether_status']=='disputed_required_review' else 'ranked'
        if len(lists[group])<limit and c['seed'] not in {v['seed'] for v in lists[group]}:lists[group].append(c)
    return lists
