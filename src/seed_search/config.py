"""Validate the implemented Bedrock contract before any expensive work."""
from pathlib import Path
import hashlib
import math
import yaml
from . import BACKEND_COMMIT

METHODS = {
    ('island','score_method'): 'preferred_interval_ratio',
    ('water','score_method'): 'enclosure_times_gap_fit',
    ('mountains','score_method'): 'coverage_to_target',
    ('wood','score_method'): 'surrounding_fraction_only',
    ('nether','score_method'): 'mean_capped_inverse_distance',
    ('structures','per_type_score'): 'nearest_viable_in_border',
    ('structures','secondary_aggregation'): 'mean_including_known_absences',
    ('structures','core_policy'): 'strong_preferences_not_hard_requirements',
    ('output','unknown_score_policy'): 'interval_and_separate_review_list',
}

def positive_int(v, name):
    if isinstance(v,bool) or not isinstance(v,int) or v < 1:
        raise ValueError(f'{name} must be a positive integer')

def validate_config(cfg):
    if not isinstance(cfg,dict) or cfg.get('schema_version') != 3:
        raise ValueError('Expected configuration schema_version 3')
    g=cfg['game']; s=cfg['search']
    if (g['edition'],g['target_version'],g['backend_model']) != ('bedrock','26.52','MC_26_50'):
        raise ValueError('Supported target is Bedrock 26.52 mapped explicitly to MC_26_50')
    if g['backend_commit'] != BACKEND_COMMIT or g['backend_repository'] != 'https://github.com/FragrantResult186/cubiomes-bedrock':
        raise ValueError('Configured backend identity differs from pinned source')
    if not g['require_validated_capabilities_before_large_search']:
        raise ValueError('Capability readiness gate cannot be disabled')
    if s['large_search_enabled']:
        raise ValueError('large_search_enabled cannot bypass the evidence readiness gate; leave false')
    if s['lower_bit_optimization_enabled'] or s['mode'] != 'full_64_bit_reference' or s['deterministic_mixer'] != 'splitmix64_finalizer':
        raise ValueError('Only deterministic full-64-bit reference enumeration is supported')
    if s['raster_boundary_policy'] != 'mark_unknown':
        raise ValueError('Finite raster boundaries must remain unknown')
    if not isinstance(s['run_key'],str) or not s['run_key'].isdigit() or not 0<=int(s['run_key'])<2**64:
        raise ValueError('run_key must be unsigned 64-bit decimal text')
    weights=cfg['score_weights']
    if set(weights) != {'island_size','island_openness','water','mountains','wood','overworld_structures','nether_proximity'}:
        raise ValueError('Require all seven implemented score categories')
    if any(isinstance(w,bool) or not isinstance(w,(int,float)) or not math.isfinite(w) or w<0 for w in weights.values()) or sum(weights.values())!=100:
        raise ValueError('Score weights must total 100 and be finite/nonnegative')
    if (cfg['deployment']['overworld_side_blocks'],cfg['deployment']['nether_side_blocks']) != (3008,992):
        raise ValueError('Fixed playable squares are 3008 Overworld and 992 Nether blocks')
    if cfg['overworld']['border_center_snap_blocks']!=8 or cfg['island']['conservative_land_connectivity']!=8:
        raise ValueError('Require eight-block centers and conservative eight-neighbor connectivity')
    required=cfg['structures'].get('required_overworld_types',[])
    if required not in ([],['stronghold']):raise ValueError('Supported required Overworld type is Stronghold')
    if cfg['nether']['fortress_required'] is not True:
        raise ValueError('Fortress is required')
    if cfg['nether']['bastion_required'] is not True:
        if cfg['nether']['bastion_required'] is not False or required!=['stronghold']:
            raise ValueError('Optional Bastion requires the Fortress and Stronghold policy')
        v=cfg['nether'].get('optional_bastion_proximity_weight')
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not 0<=v<=.25:
            raise ValueError('Optional Bastion proximity weight must be in 0..0.25')
    if cfg['verification']['initial_method'] != 'chunkbase_matching_version_terrain':
        raise ValueError('Initial review requires matching-version Chunkbase with Terrain')
    if cfg['wood']['fraction_denominator']!='land_area' or cfg['wood']['island']['openness_score_method']!='one_minus_wooded_fraction' or cfg['wood']['island']['abundance_required'] or cfg['wood']['island']['preference']!='less_wooded_more_open':
        raise ValueError('Require separate island openness and surrounding land woodland')
    for keys,value in METHODS.items():
        if cfg[keys[0]][keys[1]] != value:
            raise ValueError(f'Unsupported method {keys}: expected {value}')
    fractions=cfg['structures']['category_budget_fractions']
    if set(fractions) != {'trial_chamber','stronghold','mineshaft','ancient_city','secondary_combined'} or any(not 0<=v<=1 for v in fractions.values()) or abs(sum(fractions.values())-1)>1e-9:
        raise ValueError('Structure category fractions must total one')
    secondary=cfg['structures']['secondary_types']
    if set(secondary)!= {'village','ruined_portal','shipwreck','monument','outpost'} or len(secondary)!=5:
        raise ValueError('Require the five supported secondary structure types')
    low,high=s['center_axis_bounds_blocks']
    if any(isinstance(v,bool) or not isinstance(v,int) for v in (low,high)) or low>=high or high-low+3008>14000:
        raise ValueError('Analysis envelope must fit within 14,000 blocks per axis')
    for key in ('workers','numeric_threads_per_worker','report_top_distinct_seeds','preflight_maximum_seeds','maximum_preliminary_components_per_seed','maximum_refined_centers_per_seed','maximum_refinement_patch_side_blocks'):
        positive_int(s[key],key)
    if not 1<=s['workers']<=12 or s['numeric_threads_per_worker']!=1:
        raise ValueError('Support 1–12 process workers with one numeric thread each')
    for k in ('discovery_spacing_blocks','refinement_spacing_blocks','shoreline_spacing_blocks'):
        if s[k] not in (4,8,16,32,64):
            raise ValueError('Sampling spacing must be 4, 8, 16, 32 or 64')
    if not s['discovery_spacing_blocks']>=s['refinement_spacing_blocks']>=s['shoreline_spacing_blocks']:
        raise ValueError('Sampling must become finer at each stage')
    for section,key in (('overworld','distance_score_scale_blocks'),('overworld','surrounding_range_from_shore_blocks'),('nether','full_credit_distance_blocks'),('water','angular_samples'),('mountains','minimum_height_above_water_blocks')):
        positive_int(cfg[section][key],key)
    for section,key in (('water','preferred_gap_blocks'),('island','preferred_equivalent_diameter_blocks')):
        lo,hi=cfg[section][key]
        if not 0<lo<=hi: raise ValueError(f'Invalid interval {key}')
    for section,key in (('water','preferred_enclosure_fraction'),('water','full_credit_enclosure_fraction'),('mountains','preferred_directional_fraction')):
        if not 0<cfg[section][key]<=1: raise ValueError(f'Invalid fraction {key}')
    for key in ('preferred_wooded_fraction','full_credit_wooded_fraction'):
        if not 0<cfg['wood']['surrounding_land'][key]<=1: raise ValueError(f'Invalid fraction {key}')
    if cfg['search']['maximum_refinement_patch_side_blocks']>3008: raise ValueError('Refinement patch must fit the Overworld square')
    if set(cfg['output']['candidate_files'])-{'candidate.json','overworld.png','nether.png','inspection.md'}: raise ValueError('Unsupported candidate artifact')
    if set(cfg['output']['summary_formats'])-{'json','csv'}: raise ValueError('Unsupported summary format')
    if 'optimization' in cfg:
        opt=cfg['optimization']
        original={'exact_per_seed_cache','cache_mb_per_worker','persist_report_terrain','reuse_unchanged_maps'}
        additions={'stronghold_prefilter','early_basin_bounds','reuse_raster_intermediates','combined_structure_scan','lazy_coverage_bounds','raw_mt_cache_entries'}
        if not original<=set(opt) or set(opt)-original-additions:
            raise ValueError('Unsupported optimization settings')
        if any(not isinstance(opt[k],bool) for k in ('exact_per_seed_cache','persist_report_terrain','reuse_unchanged_maps')):
            raise ValueError('Optimization flags must be booleans')
        positive_int(opt['cache_mb_per_worker'],'cache_mb_per_worker')
        if opt['cache_mb_per_worker']>128:raise ValueError('Cache is capped at 128 MiB per worker')
        if opt.get('stronghold_prefilter','review_all') not in ('review_all','defer_unpredicted'):
            raise ValueError('Stronghold prefilter must review_all or defer_unpredicted')
        if opt.get('stronghold_prefilter')=='defer_unpredicted' and required!=['stronghold']:
            raise ValueError('Fast Stronghold filtering requires Stronghold as a required structure')
        for key in ('early_basin_bounds','reuse_raster_intermediates','combined_structure_scan','lazy_coverage_bounds'):
            if key in opt and not isinstance(opt[key],bool):raise ValueError('Optimization flags must be booleans')
        entries=opt.get('raw_mt_cache_entries',0)
        if isinstance(entries,bool) or not isinstance(entries,int) or not 0<=entries<=256:raise ValueError('Raw layout cache must contain 0–256 entries')
    if 'landscapes' in cfg:
        from .landscapes import validate_landscapes
        validate_landscapes(cfg['landscapes'])
    return cfg

def load_config(path='search.example.yaml'):
    raw=Path(path).read_bytes()
    return validate_config(yaml.safe_load(raw)),hashlib.sha256(raw).hexdigest()

def discovery_grid(cfg):
    low,high=cfg['search']['center_axis_bounds_blocks']
    half=cfg['deployment']['overworld_side_blocks']//2
    step=cfg['search']['discovery_spacing_blocks']
    start=((low-half)//step)*step
    end=-((-(high+half))//step)*step
    n=(end-start)//step+1
    if n*n>100_000:
        raise ValueError('Configured discovery map exceeds 100,000 point budget')
    return start,start,n,n,step
