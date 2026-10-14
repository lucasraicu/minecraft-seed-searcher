"""Versioned resource-family preferences and explicitly sampled biome evidence."""
import math
import numpy as np
from .backend import biome_name

VERSION='resource-families-v1'
# Explicit mapping: variants share credit, distinct wood/material families do not.
GROUPS={
 'oak':(3,'forest wooded_hills flower_forest'),
 'birch':(3,'birch_forest birch_forest_hills tall_birch_forest tall_birch_hills old_growth_birch_forest'),
 'spruce':(3,'taiga taiga_hills taiga_mountains snowy_taiga snowy_taiga_hills snowy_taiga_mountains giant_tree_taiga giant_tree_taiga_hills giant_spruce_taiga giant_spruce_taiga_hills old_growth_pine_taiga old_growth_spruce_taiga grove'),
 'dark_oak':(3,'dark_forest dark_forest_hills'),
 'jungle':(3,'jungle jungle_hills jungle_edge modified_jungle modified_jungle_edge sparse_jungle bamboo_jungle bamboo_jungle_hills'),
 'mangrove':(3,'mangrove_swamp'),
 'badlands':(3,'badlands badlands_plateau wooded_badlands_plateau eroded_badlands modified_badlands_plateau modified_wooded_badlands_plateau wooded_badlands'),
 'desert':(2,'desert desert_hills desert_lakes'),
 'coral':(2,'warm_ocean deep_warm_ocean'),
 'acacia':(2,'savanna savanna_plateau shattered_savanna shattered_savanna_plateau windswept_savanna'),
 'cherry':(2,'cherry_grove'),
 'pale_oak':(2,'pale_garden'),
 'plains':(1,'plains sunflower_plains meadow'),
 'wetland':(1,'swamp swamp_hills'),
 'mushroom':(1,'mushroom_fields mushroom_field_shore'),
 'shore':(1,'beach stone_shore snowy_beach stony_shore'),
 'river':(1,'river frozen_river'),
 'snow':(1,'snowy_tundra snowy_mountains ice_spikes snowy_plains snowy_slopes'),
 'mountain':(1,'mountains wooded_mountains mountain_edge gravelly_mountains modified_gravelly_mountains windswept_hills windswept_forest windswept_gravelly_hills jagged_peaks frozen_peaks stony_peaks'),
 'ocean':(1,'ocean deep_ocean'),
 'cool_ocean':(1,'lukewarm_ocean cold_ocean deep_lukewarm_ocean deep_cold_ocean'),
 'frozen_ocean':(1,'frozen_ocean deep_frozen_ocean'),
 'lush_caves':(2,'lush_caves'),
 'dripstone_caves':(2,'dripstone_caves'),
 'deep_dark':(1,'deep_dark'),
 'nether_wastes':(1,'nether_wastes'),
 'soul_sand':(2,'soul_sand_valley'),
 'crimson':(3,'crimson_forest'),
 'warped':(3,'warped_forest'),
 'basalt':(2,'basalt_deltas'),
}
FAMILIES={name:family for family,(_,names) in GROUPS.items() for name in names.split()}
DEFAULT_WEIGHTS={family:w for family,(w,_) in GROUPS.items()}
MANUAL_CAVE_FAMILIES=frozenset(('lush_caves','dripstone_caves','deep_dark'))

def validate_policy(p):
    if p.get('version')!=VERSION or p.get('scope') not in ('structure_qualified','all_evaluated'):
        raise ValueError('Unsupported biome diversity version or scope')
    weights=p.get('family_weights',{})
    if set(weights)!=set(DEFAULT_WEIGHTS) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in weights.values()) or sum(weights.values())<=0:
        raise ValueError('Biome weights must cover every configured family with finite nonnegative values')
    for name in ('extent_blocks2','support_cells','structures_surface_spacing','nether_spacing'):
        if isinstance(p.get(name),bool) or not isinstance(p.get(name),int) or p[name]<=0:raise ValueError(f'Invalid biome policy {name}')
    if p['structures_surface_spacing'] not in (16,32,64) or p['nether_spacing'] not in (16,32,64):raise ValueError('Biome sampling must have a finite supported spacing')
    bonus=p.get('bonus_points')
    if isinstance(bonus,bool) or not isinstance(bonus,(int,float)) or not math.isfinite(bonus) or not 0<=bonus<=5:raise ValueError('Biome bonus must be in 0..5')

def inventory(ids,points,step,bounds,policy,grade,y=None):
    ids=np.asarray(ids).reshape(-1);points=np.asarray(points).reshape(-1,2)
    if len(ids)!=len(points):raise ValueError('Biome IDs and coordinates differ in length')
    # Clip then deduplicate coordinates, so overlapping rasters cannot inflate support.
    keep=(points[:,0]>=bounds[0])&(points[:,0]<=bounds[2])&(points[:,1]>=bounds[1])&(points[:,1]<=bounds[3])
    pts=points[keep];values=ids[keep]
    pts,first=np.unique(pts,axis=0,return_index=True);values=values[first]
    rows={};raw={}
    # Cell-footprint area clipped to square; endpoints receive half-cell widths.
    area=np.maximum(0,np.minimum(pts[:,0]+step/2,bounds[2])-np.maximum(pts[:,0]-step/2,bounds[0]))*np.maximum(0,np.minimum(pts[:,1]+step/2,bounds[3])-np.maximum(pts[:,1]-step/2,bounds[1]))
    center=np.array([(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2])
    for ident in sorted(np.unique(values)):
        name=biome_name(int(ident));mask=values==ident;family=FAMILIES.get(name)
        raw[str(int(ident))]={'name':name,'samples':int(mask.sum()),'family':family}
        if family is None:continue
        row=rows.setdefault(family,{'samples':0,'estimated_area_blocks2':0.,'nearest_sample_distance':None,'nearest_sample':None})
        row['samples']+=int(mask.sum());row['estimated_area_blocks2']+=float(area[mask].sum())
        matching=pts[mask];dist=np.linalg.norm(matching-center,axis=1);i=int(np.argmin(dist))
        if row['nearest_sample_distance'] is None or dist[i]<row['nearest_sample_distance']:
            row['nearest_sample_distance']=float(dist[i]);row['nearest_sample']=matching[i].tolist()
    for family,row in rows.items():
        row['weight']=policy['family_weights'][family]
        row['extent_factor']=min(1.,row['estimated_area_blocks2']/policy['extent_blocks2'],row['samples']/policy['support_cells'])
    numerator=sum(row['weight']*row['extent_factor'] for family,row in sorted(rows.items()) if family not in MANUAL_CAVE_FAMILIES)
    denominator=sum(v for family,v in sorted(policy['family_weights'].items()) if family not in MANUAL_CAVE_FAMILIES)
    return {'policy_version':policy['version'],'grade':grade,'spacing':step,'y':y,'bounds':list(bounds),
            'unique_samples':len(pts),'raw_id_count':len(raw),'family_count':len(rows),'raw_ids':raw,'families':rows,
            'weighted_utility':numerator/denominator,'unmapped_ids':[k for k,v in raw.items() if v['family'] is None],
            'coverage':'sampled_estimate; unseen biomes are not proved absent; resources and access unverified'}

def grid_points(bounds,step):
    x,z=np.meshgrid(np.arange(bounds[0],bounds[2]+1,step),np.arange(bounds[1],bounds[3]+1,step))
    return np.column_stack((x.ravel(),z.ravel())).astype(np.int32)

def terrain_inventory(terrain,bounds,policy):
    return inventory(terrain['biomes'],grid_points(terrain['bounds'],terrain['step']),terrain['step'],bounds,policy,'surface_sampled')

def candidate_diversity(backend,terrain,center,cfg,coarse=None,grid=None):
    from .structures import square,nether_center
    policy=cfg['biome_diversity'];ob=square(center,cfg['deployment']['overworld_side_blocks']);nb=square(nether_center(center),cfg['deployment']['nether_side_blocks'])
    surface=terrain_inventory(terrain,ob,policy)
    step=policy['nether_spacing'];points=grid_points(nb,step)
    ids=backend.biome_points(np.column_stack((points[:,0],np.full(len(points),33),points[:,1])), -1)
    nether=inventory(ids,points,step,nb,policy,'nether_fixed_y',33)
    coarse_inv=None
    if coarse is not None:
        x0,z0,nx,nz,spacing=grid
        coarse_inv=inventory(coarse['biomes'],grid_points((x0,z0,x0+(nx-1)*spacing,z0+(nz-1)*spacing),spacing),spacing,ob,policy,'coarse_fixed_y',63)
    # Shared denominator: resource families across dimensions each credited once.
    ext={}
    for inv in (surface,nether):
        for family,row in inv['families'].items():
            if family not in MANUAL_CAVE_FAMILIES:ext[family]=max(ext.get(family,0),row['extent_factor'])
    utility=sum(policy['family_weights'][g]*q for g,q in sorted(ext.items()))/sum(v for family,v in sorted(policy['family_weights'].items()) if family not in MANUAL_CAVE_FAMILIES)
    return {'surface':surface,'nether':nether,'underground':{'grade':'not_sampled','layers':[]},'coarse':coarse_inv,
            'grade':'surface_sampled','weighted_utility':utility,'bonus':utility*policy['bonus_points'],
            'bonus_maximum':policy['bonus_points'],'unmapped_ids':sorted(set(surface['unmapped_ids']+nether['unmapped_ids'])),
            'additional_biome_query_points':len(points),'measurement':'estimated_sample_score; not exhaustive biome presence or resource verification'}

def add_bonus(score,diversity,base_maximum=100):
    import copy
    s=copy.deepcopy(score);bonus=diversity['bonus']
    s['base_total']=score['total'];s['base_interval']=list(score['interval']);s['base_maximum']=base_maximum
    maximum=diversity.get('bonus_maximum',5)
    uncertain=bool(diversity.get('unmapped_ids')) or diversity['grade']!='surface_sampled'
    s['biome_bonus']=bonus;s['biome_evidence_grade']=diversity['grade'];s['maximum']=base_maximum+maximum
    s['biome_surface_spacing']=diversity.get('surface',{}).get('spacing')
    s['biome_bonus_interval']=[bonus,maximum] if uncertain else [bonus,bonus]
    s['interval']=[score['interval'][i]+s['biome_bonus_interval'][i] for i in (0,1)]
    s['total']=None if score['total'] is None or uncertain else score['total']+bonus
    if uncertain:s['unknown_components'].append('biome_diversity')
    return s
