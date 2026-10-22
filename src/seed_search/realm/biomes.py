"""Five custom wooded families and once-per-family/variant surface rewards."""
from ..backend import biome_name
import numpy as np

ALIASES={
    # Bedrock string identifiers from Mojang's vanilla biome definitions.
    # Numeric IDs are never inferred from this name/family projection.
    'forest_hills':'forest','birch_forest_mutated':'old_growth_birch_forest',
    'birch_forest_hills_mutated':'old_growth_birch_forest',
    'roofed_forest':'dark_forest','roofed_forest_mutated':'dark_forest',
    'cold_taiga':'snowy_taiga','cold_taiga_hills':'snowy_taiga','cold_taiga_mutated':'snowy_taiga',
    'mega_taiga':'old_growth_pine_taiga','mega_taiga_hills':'old_growth_pine_taiga',
    'mega_spruce_taiga':'old_growth_spruce_taiga','mega_spruce_taiga_mutated':'old_growth_spruce_taiga',
    'mega_taiga_mutated':'taiga','taiga_mutated':'taiga',
    # Mojang's mega + mutated + forest + taiga tags identify Old Growth Spruce
    # Taiga (also explicit in vanilla wolf's chestnut variant filter).
    'redwood_taiga_mutated':'old_growth_spruce_taiga',
    'redwood_taiga_hills_mutated':'old_growth_spruce_taiga',
    'jungle_mutated':'jungle','jungle_edge_mutated':'sparse_jungle',
    'extreme_hills_plus_trees':'windswept_forest','extreme_hills_plus_trees_mutated':'windswept_forest',
    'extreme_hills':'windswept_hills','extreme_hills_mutated':'windswept_gravelly_hills',
    'extreme_hills_edge':'mountain_edge','swampland':'swamp','swampland_mutated':'swamp',
    'ice_plains':'snowy_plains','ice_plains_spikes':'ice_spikes','ice_mountains':'snowy_mountains',
    'stone_beach':'stony_shore','cold_beach':'snowy_beach','mushroom_island':'mushroom_fields',
    'mushroom_island_shore':'mushroom_field_shore','legacy_frozen_ocean':'frozen_ocean',
    'savanna_mutated':'windswept_savanna','savanna_plateau_mutated':'windswept_savanna',
    'mesa':'badlands','mesa_bryce':'eroded_badlands','mesa_mutated':'badlands',
    'mesa_plateau':'badlands_plateau','mesa_plateau_mutated':'modified_badlands_plateau',
    'mesa_plateau_stone':'wooded_badlands','mesa_plateau_stone_mutated':'wooded_badlands',
    'desert_mutated':'desert_lakes',
    'wooded_hills':'forest','birch_forest_hills':'birch_forest','tall_birch_forest':'old_growth_birch_forest',
    'tall_birch_hills':'old_growth_birch_forest','wooded_mountains':'windswept_forest',
    'taiga_hills':'taiga','taiga_mountains':'taiga','snowy_taiga_hills':'snowy_taiga',
    'snowy_taiga_mountains':'snowy_taiga','giant_tree_taiga':'old_growth_pine_taiga',
    'giant_tree_taiga_hills':'old_growth_pine_taiga','giant_spruce_taiga':'old_growth_spruce_taiga',
    'giant_spruce_taiga_hills':'old_growth_spruce_taiga','jungle_hills':'jungle',
    'modified_jungle':'jungle','jungle_edge':'sparse_jungle','modified_jungle_edge':'sparse_jungle',
    'bamboo_jungle_hills':'bamboo_jungle','dark_forest_hills':'dark_forest',
    'snowy_tundra':'snowy_plains','stone_shore':'stony_shore','shattered_savanna':'windswept_savanna',
    'shattered_savanna_plateau':'windswept_savanna',
}
WOOD={
    'forest':set('forest birch_forest flower_forest old_growth_birch_forest windswept_forest dappled_forest'.split()),
    'taiga':set('taiga snowy_taiga old_growth_pine_taiga old_growth_spruce_taiga'.split()),
    'jungle':set('jungle bamboo_jungle sparse_jungle'.split()),
    'dark_pale':{'dark_forest','pale_garden'},'cherry':{'cherry_grove'},
}
FAMILIES={
    'desert':set('desert desert_hills desert_lakes'.split()),
    'swamp':set('swamp swamp_hills mangrove_swamp'.split()),
    'snowy_ice':set('snowy_plains snowy_mountains ice_spikes snowy_slopes'.split()),
    'badlands':set('badlands badlands_plateau wooded_badlands_plateau eroded_badlands modified_badlands_plateau modified_wooded_badlands_plateau wooded_badlands'.split()),
    'mushroom':{'mushroom_fields','mushroom_field_shore'},
    'plains_meadow':{'plains','sunflower_plains','meadow'},
    'mountains':set('mountains mountain_edge gravelly_mountains modified_gravelly_mountains windswept_hills windswept_gravelly_hills jagged_peaks frozen_peaks stony_peaks grove'.split()),
    'ocean':set('ocean deep_ocean warm_ocean deep_warm_ocean lukewarm_ocean deep_lukewarm_ocean cold_ocean deep_cold_ocean frozen_ocean deep_frozen_ocean'.split()),
    'rivers_shores':{'river','frozen_river','beach','stony_shore','snowy_beach'},
}
PRIMARY={name:family for family,names in WOOD.items() for name in names}
PRIMARY.update({name:family for family,names in FAMILIES.items() for name in names})
SAVANNA={'savanna','savanna_plateau','windswept_savanna'}


def canonical(name):
    name=name.removeprefix('minecraft:').lower().replace(' ','_')
    return ALIASES.get(name,name)


def classify(names, policy, complete=False, verified=False):
    names=sorted(set(canonical(n) for n in names))
    wooded=sorted(family for family,members in WOOD.items() if members.intersection(names))
    primary=sorted({PRIMARY[n] for n in names if n in PRIMARY})
    family_rewards={f:policy['family_bonuses'][f] for f in primary if f in policy['family_bonuses']}
    variant_rewards={n:v for n,v in policy['variant_bonuses'].items() if n in names}
    wood_bonus=5*max(0,len(wooded)-2)
    mapping_complete=all(n in PRIMARY or n in SAVANNA for n in names)
    status=('VERIFIED' if verified else 'PREDICTED') if len(wooded)>=2 else 'FAILED' if complete and verified and mapping_complete else 'PENDING'
    # Prediction detections are not lower bounds on actual generated coverage.
    # A verified positive sample can establish presence, but only exhaustive
    # verified coverage establishes absence of unseen families and variants.
    exhaustive=bool(complete and verified and mapping_complete)
    upper_wood=len(wooded) if exhaustive else len(WOOD)
    upper_surface=(sum(family_rewards.values())+sum(variant_rewards.values()) if exhaustive else
                   sum(policy['family_bonuses'].values())+sum(policy['variant_bonuses'].values()))
    observed_score=wood_bonus+sum(family_rewards.values())+sum(variant_rewards.values())
    upper_score=5*max(0,upper_wood-2)+upper_surface
    uncertainty={'domain':'actual_generated_surface' if verified else 'prediction_model_only',
                 'observed_wooded_family_count':len(wooded),
                 'possible_wooded_families':wooded if exhaustive else sorted(WOOD),
                 'wooded_family_count_interval':[len(wooded),upper_wood],
                 'wooded_bonus_interval':[wood_bonus,5*max(0,upper_wood-2)],
                 'surface_bonus_interval':[sum(family_rewards.values())+sum(variant_rewards.values()),upper_surface],
                 'score_interval':[observed_score,upper_score],
                 'exhaustive_verified':exhaustive,
                 'mapping_complete':mapping_complete,
                 'actual_generation_score_interval':[observed_score,upper_score] if verified else
                    [0,15+sum(policy['family_bonuses'].values())+sum(policy['variant_bonuses'].values())],
                 'interpretation':'Presence is observed; unseen families remain possible unless exhaustive verified surface coverage. Prediction intervals do not certify actual eligibility.'}
    return {'raw_names':names,'wooded_families':wooded,'wooded_family_count':len(wooded),
            'wooded_family_bitset':sum(1<<i for i,f in enumerate(WOOD) if f in wooded),
            'wooded_bonus':wood_bonus,'primary_families':primary,'family_bonuses':family_rewards,
            'variant_bonuses':variant_rewards,'surface_bonus':sum(family_rewards.values())+sum(variant_rewards.values()),
            'score':observed_score,'uncertainty':uncertainty,
            'qualification':status,'coverage':'exhaustive' if exhaustive else 'sampled or unmapped; unseen families not absent',
            'unmapped_names':[n for n in names if n not in PRIMARY and n not in SAVANNA],
            'savanna_policy':'neutral; no query, bonus, penalty or diversity credit'}


def classify_ids(ids, policy, **kwargs):
    return classify([biome_name(i) for i in sorted({int(value) for value in ids})],policy,**kwargs)


def postprocess_ids(ids, points, policy):
    """Classify unique sampled IDs and retain counts plus first observed coordinates."""
    ids=np.asarray(ids)
    if ids.ndim!=1 or len(ids)!=len(points):
        raise ValueError('Biome IDs and sample points must have equal length')
    unique,first,counts=np.unique(ids,return_index=True,return_counts=True)
    result=classify_ids(unique,policy)
    result['raw_detections']={str(int(value)):{'samples':int(count),'coordinate':points[int(index)].tolist()}
                              for value,index,count in zip(unique,first,counts)}
    return result


def variant_fit(names, variant):
    names={canonical(n) for n in names}
    # Fixed set denominator; adding Savanna cannot dilute the score.
    preferred={'forest','taiga','cherry','jungle','ocean','rivers_shores'} if variant=='v1' else {'forest','taiga','cherry','mountains','plains_meadow'}
    found={PRIMARY[n] for n in names if n in PRIMARY}
    return 100*len(found.intersection(preferred))/len(preferred)


def raster_variant_fit(raster, variant, *, target_version='26.52'):
    """Fit from actual string observations without guessing Bedrock numeric IDs.

    Sparse actual positives provide an estimate; complete verified fit requires
    every surface cell, known mapping and a one-block horizontal lattice.
    """
    metadata=raster.metadata
    observations=metadata.get('surface_biome_observations')
    if observations is not None:
        observed={};conflicts=[]
        for row in observations:
            if not isinstance(row,dict) or row.get('status')!='OBSERVED' or not isinstance(row.get('name'),str) or not row['name'].strip():
                continue
            x,z=row.get('x'),row.get('z')
            if any(isinstance(v,bool) or not isinstance(v,int) for v in (x,z)):
                continue
            if (raster.index((x,z)) is None or (x-raster.bounds[0])%raster.resolution or
                (z-raster.bounds[1])%raster.resolution):
                continue
            name=canonical(row['name'])
            if (x,z) in observed and observed[(x,z)]!=name:
                conflicts.append([x,z]);continue
            observed[(x,z)]=name
        names=sorted(set(observed.values()))
        unmapped=sorted(set(names)-set(PRIMARY)-SAVANNA)
        complete=(len(observed)==raster.height.size and not conflicts and not unmapped and
                  metadata.get('surface_biome_coverage_complete') is True)
        actual=metadata.get('source')=='actual' and metadata.get('surface_biome_evidence')=='actual_api_string_names'
        stable=metadata.get('stable_sampled_observations') is True
        status=('VERIFIED' if complete and stable and raster.resolution==1 else 'PARTIAL') if actual and names else 'UNKNOWN'
        return variant_fit(names,variant) if actual else 0.,status,{
            'source':metadata.get('surface_biome_evidence','not supplied'),'status':status,
            'raw_names':names,'unmapped_names':unmapped,'observed_cells':len(observed),
            'expected_cells':int(raster.height.size),'complete_sample_lattice':complete,
            'conflicting_coordinates':conflicts,'resolution':raster.resolution,
            'query_policy':metadata.get('surface_biome_query_policy'),'canopy_rule':metadata.get('surface_biome_canopy_rule')}
    if raster.biomes is None:
        return 0.,'UNKNOWN',{'source':'not supplied','status':'UNKNOWN'}
    names=sorted({canonical(biome_name(int(b))) for b in np.unique(raster.biomes[raster.known])})
    mapping_known=all(n in PRIMARY or n in SAVANNA for n in names)
    actual=metadata.get('source')=='actual' and metadata.get('biome_evidence')=='actual_generated'
    complete=(actual and raster.resolution==1 and raster.known.all() and mapping_known and
              metadata.get('biome_mapping_version')==target_version)
    status=('VERIFIED' if complete else 'PARTIAL') if actual and names else 'PREDICTED' if names else 'UNKNOWN'
    return variant_fit(names,variant),status,{'source':metadata.get('biome_evidence','numeric prediction IDs'),
                                          'status':status,'raw_names':names,'mapping_version':metadata.get('biome_mapping_version')}
