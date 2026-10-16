"""New profile validation; legacy schema 3/4 contracts keep their own validation."""
import copy
import math
from .. import BACKEND_COMMIT
from .resources import disk_policy

DEFAULT = {
    'schema_version':5,
    'game':{'edition':'bedrock','target_version':'26.52','backend_model':'MC_26_50',
            'backend_commit':BACKEND_COMMIT,'bds_version':'1.26.52.3'},
    'deployment':{'overworld_side_blocks':1536,'nether_side_blocks':896},
    'discovery':{'overworld_bounds':[-2000,-2000,2000,2000],
                 'nether_bounds':[-2000,-2000,2000,2000]},
    'search':{'mode':'prediction','sequence':'permutation','run_key':'0','workers':30,'max_workers':36,
              'numeric_threads_per_worker':1,'native_threads_per_worker':1,'batch_size':32,'pilot_limit':1000,'inventory_mode':'eligibility',
              'memory_target_gib':25,'memory_ceiling_gib':30,'docker_reserve_gib':8,
              'run_disk_limit_bytes':128 << 30,'free_disk_reserve_bytes':16 << 30,
              'projected_bytes_per_seed':65536,
              'structure_order':['ancient_city','village','trial_chamber','mineshaft']},
    'structures':{'required':['stronghold','village','trial_chamber','ancient_city','mineshaft'],
                  'nether_required':['fortress','bastion'],
                  'optional_bonuses':{'monument':5,'outpost':5,'shipwreck':2,'ruined_portal':2,
                                      'buried_treasure':1,'monster_room':1}},
    'biomes':{'spacing':64,'sample_y':63,'lattice':'world','gate_batch_size':16,'refinement_budget':128,'wooded_minimum_families':2,
              'family_bonuses':{'desert':3,'swamp':3,'snowy_ice':2,'badlands':2,'mushroom':3,
                                'plains_meadow':1,'mountains':2,'ocean':2,'rivers_shores':1},
              'variant_bonuses':{'pale_garden':3,'mangrove_swamp':3,'bamboo_jungle':2,
                                 'dappled_forest':2,'warm_ocean':3}},
    'scoring':{'geometry_weight':.8,'biome_fit_weight':.1,'baseline_weight':.1,'baseline_quality_cap':60},
    'terrain':{'variants':['v1','v2'],'native_threads':1,'scheduler':'rotation','resolutions':[128,64,32,16,8,4],
               'center_spacing':64,'refine_center_spacing':16,'rays':32,
               'maximum_refinements_per_anchor':8},
    'bds':{'enabled':True,'version':'1.26.52.3',
           'docker_cli':'/Applications/Docker.app/Contents/Resources/bin/docker',
           'image':'bedrock-verification-poc:1.26.52.3',
           'image_id':'sha256:cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8',
           'cpus':4,'memory_gib':6,'verification_budget':20,'persist_snapshot':False,
           'compare_reference':True,'maximum_region_side':256},
    'caves':{'automatic':False,'y_levels':[0,-16,-32,-48],'spacing':64,'maximum_samples':10000},
}


def default_config():
    cfg=copy.deepcopy(DEFAULT)
    from .terrain import SEARCH_V1, SEARCH_V2
    cfg['terrain']['v1']=dict(SEARCH_V1)
    cfg['terrain']['v2']=dict(SEARCH_V2)
    return cfg


BLUEPRINT_CONTRACT='master_seed_blueprint_v1'
BLUEPRINT_COUNTS={'stronghold':1,'mansion':1,'village':5,'trial_chamber':2,
                  'ancient_city':1,'desert_pyramid':1,'jungle_temple':1,
                  'monument':1,'ruined_portal':3,'shipwreck':2,'mineshaft':5}
BLUEPRINT_ORDER=['mansion','jungle_temple','desert_pyramid','monument','ancient_city',
                 'village','trial_chamber','ruined_portal','shipwreck','mineshaft']


def blueprint_config():
    """Historical audited blueprint policy; locked_blueprint_config is current."""
    cfg=default_config()
    cfg['contract']=BLUEPRINT_CONTRACT
    cfg['search']['structure_order']=list(BLUEPRINT_ORDER)
    cfg['structures']={'required':list(BLUEPRINT_COUNTS),
                       'minimum_counts':dict(BLUEPRINT_COUNTS),
                       'nether_required':['fortress','bastion'],
                       'nether_minimum_counts':{'fortress':1,'bastion':1},
                       'optional_bonuses':{'outpost':10}}
    cfg['biomes'].update(sample_y_levels=[63,-48,0,160],
                         required_families=['plains','desert','forest','taiga','jungle','swamp',
                                            'snowy_ice','dark_forest','peaks','stony_shore',
                                            'lush_caves','dripstone_caves','deep_dark'],
                         family_bonuses={},variant_bonuses={})
    cfg['terrain']['variants']=['v1']
    cfg['terrain']['v1']={'mode':'coastal_continent','coastal_continent':{
        'land_fraction_min':.75,'land_fraction_max':.85,'ocean_edge_min_width_blocks':250,
        'ocean_edge_preferred_max_width_blocks':400,'ocean_edge_fraction_min':.5,
        'monument_envelope_half_size_blocks':80}}
    cfg['terrain'].pop('v2',None)
    return cfg


def _integer(value, lo, hi, name):
    if isinstance(value,bool) or not isinstance(value,int) or not lo<=value<=hi:
        raise ValueError(f'{name} must be an integer in {lo}–{hi}')


def memory_budget_gib(search, *, docker_reserve_default=8):
    """Validate the combined scanner/Docker budget before checkpoint mutation."""
    values=[search.get('memory_target_gib',25),search.get('memory_ceiling_gib',30),
            search.get('docker_reserve_gib',docker_reserve_default)]
    for name,value in zip(('memory_target_gib','memory_ceiling_gib','docker_reserve_gib'),values):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or (isinstance(value,float) and not math.isfinite(value)):
            raise ValueError(f'{name} must be a finite number')
    target,ceiling,reserve=values
    if not 0<target<=ceiling<=30:
        raise ValueError('Memory target must fit the agreed 30 GiB combined ceiling')
    if not 0<=reserve<ceiling:
        raise ValueError('Docker reserve must be nonnegative and below the combined memory ceiling')
    return target,ceiling,reserve


def validate_config(cfg):
    if cfg.get('contract')==BLUEPRINT_CONTRACT:
        return validate_blueprint_config(cfg)
    if cfg.get('contract') is not None:raise ValueError('Unknown Realm contract')
    if cfg.get('schema_version')!=5:
        raise ValueError('Realm profile requires schema_version 5')
    for name in DEFAULT:
        if name not in cfg:raise ValueError(f'Missing Realm configuration section {name}')
    for key,value in DEFAULT['game'].items():
        if cfg['game'].get(key)!=value:raise ValueError(f'Unsupported or unpinned game setting {key}')
    if cfg['deployment'] != DEFAULT['deployment']:
        raise ValueError('This Realm contract uses 1536 Overworld and 896 Nether blocks')
    if cfg['discovery'] != DEFAULT['discovery']:
        raise ValueError('Discovery must use exactly half-open [-2000,2000) in each dimension')
    s=cfg['search']
    if s.get('mode')!='prediction' or s.get('sequence') not in ('permutation','sequential','manifest','strided'):
        raise ValueError('Realm scan mode must explicitly label predictions and supported seed sequence')
    if s.get('sequence')=='manifest':
        from ..seeds import parse_seed
        values=s.get('manifest_seeds')
        if not isinstance(values,list) or not 1<=len(values)<=10000 or any(not isinstance(v,str) or str(parse_seed(v))!=v for v in values):
            raise ValueError('Manifest requires 1–10000 canonical signed decimal seeds')
        if len(set(values))!=len(values):raise ValueError('Manifest seeds must be distinct')
    if s.get('sequence')=='strided':
        from ..seeds import parse_seed
        low32=s.get('low32',0)
        if isinstance(low32,str):low32=parse_seed(low32)
        elif isinstance(low32,bool) or not isinstance(low32,int):raise ValueError('low32 must be an integer')
        if not -(1<<63)<=low32<(1<<63):raise ValueError('low32 outside 64-bit range')
    if s.get('inventory_mode','complete') not in ('complete','eligibility'):raise ValueError('Invalid inventory mode')
    if cfg['biomes'].get('lattice','border') not in ('border','world'):raise ValueError('Invalid biome lattice')
    _integer(cfg['biomes'].get('gate_batch_size',16),1,256,'biome gate batch size')
    _integer(cfg['biomes'].get('refinement_budget',0),0,4096,'biome refinement budget')
    key=s.get('run_key')
    if not isinstance(key,str) or not key.isdigit() or not 0<=int(key)<2**64:
        raise ValueError('run_key must be a decimal uint64 string')
    if s['sequence']=='sequential' and int(key)!=0:raise ValueError('Sequential scans require run_key 0')
    _integer(s.get('max_workers'),1,36,'max_workers');_integer(s.get('workers'),1,s['max_workers'],'workers')
    _integer(s.get('batch_size'),1,4096,'batch_size');_integer(s.get('pilot_limit'),1,1000,'pilot_limit')
    if s.get('numeric_threads_per_worker')!=1:raise ValueError('Use exactly one numeric thread per worker')
    _integer(s.get('native_threads_per_worker',1),1,36,'native_threads_per_worker')
    if s['workers']*s.get('native_threads_per_worker',1)>36:
        raise ValueError('Process/native thread product must fit 36 logical CPUs')
    if 'memory_target_gib' not in s or 'memory_ceiling_gib' not in s:
        raise ValueError('Memory target and ceiling must be configured')
    memory_budget_gib(s)
    disk_policy(s)
    if cfg.get('terrain',{}).get('scheduler','rotation') not in ('rotation','priority'):
        raise ValueError('Terrain scheduler must be rotation or priority')
    _integer(cfg.get('terrain',{}).get('native_threads',1),1,36,'terrain.native_threads')
    order=s.get('structure_order',[])
    if len(order)!=4 or set(order)!=set(DEFAULT['search']['structure_order']):
        raise ValueError('All four mandatory non-anchor structures must be checked')
    if cfg['structures'].get('required')!=DEFAULT['structures']['required']:
        raise ValueError('Required structure eligibility cannot be relaxed')
    if cfg['structures'].get('nether_required',DEFAULT['structures']['nether_required'])!=['fortress','bastion']:
        raise ValueError('Both Fortress and Bastion are mandatory in the final Nether square')
    for section,keys in (('structures',('optional_bonuses',)),('biomes',('family_bonuses','variant_bonuses'))):
        for key in keys:
            vals=cfg[section].get(key,{})
            if set(vals)!=set(DEFAULT[section][key]) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in vals.values()):
                raise ValueError(f'Invalid configurable {key}')
    if cfg['biomes'].get('wooded_minimum_families')!=2:raise ValueError('At least two wooded families remain mandatory')
    if cfg['biomes'].get('spacing') not in (4,8,16,32,64,128):raise ValueError('Invalid biome spacing')
    if cfg['biomes'].get('sample_y')!=63:raise ValueError('Fixed-Y predictor must retain declared Y=63 provenance')
    t=cfg['terrain']
    if t.get('variants')!=['v1','v2'] or t.get('rays')!=32:raise ValueError('Only independent V1/V2 with 32 rays are supported')
    if t.get('resolutions')!=[128,64,32,16,8,4]:raise ValueError('Keep the declared adaptive terrain resolutions')
    _integer(t.get('maximum_refinements_per_anchor'),0,10000,'maximum_refinements_per_anchor')
    for key in ('center_spacing','refine_center_spacing'):_integer(t.get(key),1,256,key)
    from .terrain import V1,V2
    for name,defaults in (('v1',V1),('v2',V2)):
        if name in t:
            values=t[name]
            required=set(defaults)-({'ridge_min_arc_rays','ridge_min_arc_aspect','enclosure_policy'} if name=='v2' else set())
            if not isinstance(values,dict) or not required.issubset(values) or set(values)-set(defaults) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for k,v in values.items() if k!='enclosure_policy'):
                raise ValueError(f'Invalid configurable {name} geometry thresholds')
            if name=='v2':
                _integer(values.get('ridge_min_arc_rays',defaults['ridge_min_arc_rays']),1,t['rays'],'ridge_min_arc_rays')
                if values.get('enclosure_policy','continuous_arcs') not in ('continuous_arcs','surrounding_mountains'):
                    raise ValueError('Invalid configurable v2 enclosure_policy')
    weights=[cfg['scoring'].get(n) for n in ('geometry_weight','biome_fit_weight','baseline_weight')]
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in weights) or abs(sum(weights)-1)>1e-9:
        raise ValueError('Variant weights must be finite, nonnegative and sum to one')
    if cfg['scoring']['baseline_quality_cap']<=0:raise ValueError('Baseline quality cap must be positive')
    if cfg['caves'].get('automatic') is not False:raise ValueError('Cave inventory requires explicit manual invocation')
    if cfg['caves'].get('y_levels')!=[0,-16,-32,-48]:raise ValueError('Keep the agreed initial cave Y levels')
    _integer(cfg['caves'].get('maximum_samples'),1,1000000,'maximum_samples')
    if cfg['caves'].get('spacing') not in (4,8,16,32,64,128):raise ValueError('Invalid manual cave spacing')
    b=cfg['bds']
    for key in ('version','image_id','image'):
        if b.get(key)!=DEFAULT['bds'][key]:raise ValueError(f'BDS {key} must match the verified pin')
    from .verification import validate_bds_pins
    validate_bds_pins(cfg)
    _integer(b.get('cpus'),4,4,'BDS CPUs');_integer(b.get('verification_budget'),0,10000,'verification_budget')
    if b.get('memory_gib')!=6:raise ValueError('Tested BDS allocation requires exactly 6 GiB memory')
    return cfg


LOCKED_REVISION='locked-2048-1024-v1'
RIVER_REVISION='locked-2048-1024-river-v2'
OUTPOST_REVISION='locked-2048-1024-outpost-v3'
ORIGIN_REVISION='origin-fixed-2048-v1'
TWO_GROUP_REVISION='origin-fixed-2048-two-group-v2'
TWO_GROUP_MARINE_REVISION='origin-fixed-2048-two-group-marine-v3'
DYNAMIC_REVISION='dynamic-envelope-1664-v1'
DYNAMIC_V2_REVISION='dynamic-envelope-1664-v2'
DYNAMIC_V3_REVISION='dynamic-envelope-2048-v3'
ORIGIN_ORDER=['ruined_portal','trial_chamber','outpost','desert_pyramid','jungle_temple',
              'mansion','ancient_city','village','mineshaft']
TWO_GROUP_ORDER=['outpost','desert_pyramid','jungle_temple','ruined_portal',
                 'trial_chamber','mansion','ancient_city','village','mineshaft']
TWO_GROUP_STRONGHOLD_AFTER=4


def stronghold_after(cfg):
    """Preserve replay ordering for v2 runs created before the new filter order."""
    return cfg['search'].get('stronghold_after_structure_count',2) if two_group_policy(cfg) else 2
OUTPOST_ORDER=['ruined_portal','outpost','desert_pyramid','jungle_temple','mansion',
               'ancient_city','village','trial_chamber','mineshaft']
LOCKED_ORDER=['ruined_portal','trial_chamber','mansion','desert_pyramid',
              'jungle_temple','ancient_city','village','mineshaft']


def locked_blueprint_config():
    """Current geometry; blueprint_config retains the historical audited policy."""
    cfg=blueprint_config()
    cfg['screening_revision']=LOCKED_REVISION
    cfg['deployment']={'overworld_side_blocks':2048,'nether_side_blocks':1024}
    cfg['search']['structure_order']=list(LOCKED_ORDER)
    cfg['structures']['minimum_counts'].update(village=6,trial_chamber=5,ruined_portal=6,
                                              mineshaft=15,ancient_city=2,shipwreck=4)
    cfg['structures']['nether_minimum_counts']={'fortress':2,'bastion':2}
    cfg['structures']['deferred_until_coastal_terrain']=['monument','shipwreck','outpost']
    cfg['terrain']['v1']['square_side_blocks']=2048
    return cfg


def locked_policy(cfg):
    return cfg.get('screening_revision') in (LOCKED_REVISION,RIVER_REVISION,OUTPOST_REVISION,ORIGIN_REVISION,TWO_GROUP_REVISION,TWO_GROUP_MARINE_REVISION,DYNAMIC_REVISION,DYNAMIC_V2_REVISION,DYNAMIC_V3_REVISION)


def river_policy(cfg):
    return cfg.get('screening_revision') in (RIVER_REVISION,OUTPOST_REVISION,ORIGIN_REVISION,TWO_GROUP_REVISION,TWO_GROUP_MARINE_REVISION)


def outpost_policy(cfg):
    return cfg.get('screening_revision') in (OUTPOST_REVISION,ORIGIN_REVISION,TWO_GROUP_REVISION,TWO_GROUP_MARINE_REVISION,DYNAMIC_REVISION,DYNAMIC_V2_REVISION,DYNAMIC_V3_REVISION)


def origin_policy(cfg):
    return cfg.get('screening_revision') in (ORIGIN_REVISION,TWO_GROUP_REVISION,TWO_GROUP_MARINE_REVISION)


def baseline_requirements(cfg):
    if dynamic_v2_policy(cfg):return 19+len(cfg['biomes']['required_families'])
    return 32 if dynamic_policy(cfg) else 26 if marine_baseline_policy(cfg) else 24 if outpost_policy(cfg) else 23 if locked_policy(cfg) else 25


def river_blueprint_config():
    """Historical river profile retained for reproducible controls and checkpoints."""
    cfg=locked_blueprint_config()
    cfg['screening_revision']=RIVER_REVISION
    cfg['structures']['nether_minimum_counts']['bastion']=3
    cfg['structures']['minimum_counts']['shipwreck']=5
    cfg['terrain']['v1']['coastal_continent'].update(
        land_connectivity=8,bridge_inland_freshwater=True,
        river_corridor_min_length_blocks=600,
        river_highway_hub_radius_blocks=250,river_highway_bonus_points=20)
    return cfg


def outpost_blueprint_config():
    cfg=river_blueprint_config()
    cfg['screening_revision']=OUTPOST_REVISION
    cfg['search']['structure_order']=list(OUTPOST_ORDER)
    cfg['structures']['required'].append('outpost')
    cfg['structures']['minimum_counts']['outpost']=2
    cfg['structures']['optional_bonuses']={}
    cfg['structures']['deferred_until_coastal_terrain']=['monument','shipwreck']
    return cfg


def origin_blueprint_config():
    """Origin is an evaluation center; Strongholds remain real predicted starts."""
    cfg=outpost_blueprint_config()
    cfg['screening_revision']=ORIGIN_REVISION
    cfg['discovery']['overworld_bounds']=[-1024,-1024,1024,1024]
    cfg['discovery']['nether_bounds']=[-512,-512,512,512]
    cfg['search']['structure_order']=list(ORIGIN_ORDER)
    cfg['terrain']['v1']['coastal_continent']['river_highway_bonus_points']=35
    return cfg


def two_group_blueprint_config():
    """Versioned B=2 target categories; hard floors never consume the budget."""
    cfg=origin_blueprint_config()
    cfg['screening_revision']=TWO_GROUP_REVISION
    cfg['search']['structure_order']=list(TWO_GROUP_ORDER)
    cfg['search']['stronghold_after_structure_count']=TWO_GROUP_STRONGHOLD_AFTER
    cfg['search']['max_misses']=2
    cfg['structures']['minimum_counts'].update(
        trial_chamber=10,village=7,ruined_portal=7,mineshaft=20,outpost=1,shipwreck=3)
    cfg['structures']['hard_floors']={
        'stronghold':1,'jungle_temple':1,'desert_pyramid':1,'outpost':1,
        'mansion':0,'trial_chamber':8,'village':5,'ruined_portal':5,
        'mineshaft':17,'ancient_city':1,'fortress':1,'bastion':2}
    return cfg


def marine_baseline_blueprint_config():
    """Versioned v2 baseline with strict predicted marine start counts, no terrain gate."""
    cfg=two_group_blueprint_config()
    cfg['screening_revision']=TWO_GROUP_MARINE_REVISION
    cfg['structures']['hard_floors'].update(monument=1,shipwreck=3)
    cfg['structures']['deferred_until_coastal_terrain']=[]
    coastal=cfg['terrain']['v1']['coastal_continent']
    for key in ('river_corridor_min_length_blocks','river_highway_hub_radius_blocks','river_highway_bonus_points'):
        coastal.pop(key,None)
    return cfg


def marine_baseline_policy(cfg):
    return cfg.get('screening_revision')==TWO_GROUP_MARINE_REVISION


def dynamic_policy(cfg):
    return cfg.get('screening_revision') in (DYNAMIC_REVISION, DYNAMIC_V2_REVISION, DYNAMIC_V3_REVISION)


def dynamic_v1_policy(cfg):
    return cfg.get('screening_revision') == DYNAMIC_REVISION


def dynamic_v2_policy(cfg):
    return cfg.get('screening_revision') in (DYNAMIC_V2_REVISION, DYNAMIC_V3_REVISION)


def dynamic_v3_policy(cfg):
    return cfg.get('screening_revision') == DYNAMIC_V3_REVISION


def dynamic_blueprint_config():
    """Historical sliding-center policy (v1, 1664x1664)."""
    cfg=marine_baseline_blueprint_config()
    cfg['screening_revision']=DYNAMIC_REVISION
    cfg['deployment']={'overworld_side_blocks':1664,'nether_side_blocks':832}
    cfg['discovery']={'overworld_bounds':[-2000,-2000,2000,2000],
                      'nether_bounds':[-562,-562,562,562]}
    cfg['structures']['minimum_counts'].update(village=9,trial_chamber=8,
        ancient_city=4,desert_pyramid=3,jungle_temple=3,monument=1,
        ruined_portal=7,shipwreck=6,mineshaft=15,outpost=2,mansion=1)
    cfg['structures']['nether_minimum_counts']={'fortress':2,'bastion':2}
    cfg['structures']['hard_floors']={'stronghold':1,'mansion':1,'village':8,
        'trial_chamber':7,'ancient_city':3,'desert_pyramid':2,'jungle_temple':2,
        'monument':1,'ruined_portal':5,'shipwreck':4,'mineshaft':12,
        'outpost':2,'fortress':2,'bastion':2}
    cfg['structures']['deferred_until_coastal_terrain']=[]
    cfg['terrain']['v1']['square_side_blocks']=1664
    cfg['terrain']['v1']['coastal_continent'].update(
        land_fraction_min=.70,land_fraction_max=.80,
        ocean_edge_min_width_blocks=200,ocean_edge_preferred_max_width_blocks=300)
    cfg['search']['density_weights']={'village':3,'trial_chamber':2,'ancient_city':2,'desert_pyramid':1,'jungle_temple':1,'outpost':1}
    cfg['search']['centroid_weights']={'village':3,'trial_chamber':2,'ruined_portal':2,'ancient_city':2,'outpost':1,'desert_pyramid':1,'jungle_temple':1,'mansion':1,'monument':1,'stronghold':1,'shipwreck':1}
    cfg['biomes']['include_frozen_peaks']=True
    cfg['biomes']['nether_required']=['nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas']
    cfg['search'].pop('stronghold_after_structure_count',None)
    return cfg


def dynamic_v2_blueprint_config():
    """Historical player-envelope policy (v2, 1664x1664)."""
    cfg=dynamic_blueprint_config()
    cfg['screening_revision']=DYNAMIC_V2_REVISION
    cfg['search']['max_misses']=3
    cfg['search']['centroid_weights']={
        'village':3,'trial_chamber':2,'ruined_portal':0,'ancient_city':2,
        'outpost':1,'desert_pyramid':1,'jungle_temple':1,'mansion':1,
        'monument':1,'stronghold':1,'shipwreck':0
    }
    cfg['terrain']['variants']=[]
    cfg['terrain'].pop('v1',None)
    return cfg


def dynamic_v3_blueprint_config():
    """Active player-envelope policy (v3, 2048x2048 overworld, 1024x1024 nether)."""
    cfg=dynamic_v2_blueprint_config()
    cfg['screening_revision']=DYNAMIC_V3_REVISION
    cfg['deployment']={'overworld_side_blocks':2048,'nether_side_blocks':1024}
    cfg['discovery']={'overworld_bounds':[-2000,-2000,2000,2000],
                      'nether_bounds':[-634,-634,634,634]}
    cfg['structures']['minimum_counts'].update(
        village=6,trial_chamber=8,ancient_city=2,desert_pyramid=1,
        jungle_temple=1,monument=1,ruined_portal=8,shipwreck=4,
        mineshaft=10,outpost=1,mansion=1
    )
    cfg['structures']['nether_minimum_counts']={'fortress':1,'bastion':2}
    cfg['structures']['hard_floors']={
        'stronghold':1,'mansion':1,'village':6,'trial_chamber':8,
        'ancient_city':2,'desert_pyramid':1,'jungle_temple':1,
        'monument':1,'ruined_portal':8,'shipwreck':4,'mineshaft':10,
        'outpost':1,'fortress':1,'bastion':2
    }
    cfg['search']['centroid_weights']={
        'village':3,'trial_chamber':2,'ruined_portal':0,'ancient_city':2,
        'outpost':1,'desert_pyramid':2,'jungle_temple':2,'mansion':2,
        'monument':1,'stronghold':1,'shipwreck':0
    }
    cfg['search']['max_misses']=0
    return cfg


def two_group_policy(cfg):
    return cfg.get('screening_revision') in (TWO_GROUP_REVISION,TWO_GROUP_MARINE_REVISION,DYNAMIC_REVISION,DYNAMIC_V2_REVISION,DYNAMIC_V3_REVISION)


def validate_blueprint_config(cfg):
    """Validate common pins through legacy validation, then the explicit contract."""
    expected=(dynamic_v3_blueprint_config() if dynamic_v3_policy(cfg) else
              dynamic_v2_blueprint_config() if dynamic_v2_policy(cfg) else
              dynamic_blueprint_config() if dynamic_policy(cfg) else
              marine_baseline_blueprint_config() if marine_baseline_policy(cfg) else
              two_group_blueprint_config() if two_group_policy(cfg) else
              origin_blueprint_config() if origin_policy(cfg) else
              outpost_blueprint_config() if outpost_policy(cfg) else
              river_blueprint_config() if river_policy(cfg) else
              locked_blueprint_config() if locked_policy(cfg) else
              blueprint_config())
    if cfg.get('screening_revision') not in (None,LOCKED_REVISION,RIVER_REVISION,OUTPOST_REVISION,ORIGIN_REVISION,TWO_GROUP_REVISION,TWO_GROUP_MARINE_REVISION,DYNAMIC_REVISION,DYNAMIC_V2_REVISION,DYNAMIC_V3_REVISION):raise ValueError('Unknown blueprint screening revision')
    if cfg['deployment']!=expected['deployment']:raise ValueError('Blueprint geometry differs from its revision')
    if cfg['discovery']!=expected['discovery']:raise ValueError('Blueprint discovery bounds differ from its revision')
    legacy=copy.deepcopy(cfg)
    legacy.pop('contract',None)
    legacy['deployment']=copy.deepcopy(DEFAULT['deployment'])
    legacy['discovery']=copy.deepcopy(DEFAULT['discovery'])
    legacy['search']['structure_order']=list(DEFAULT['search']['structure_order'])
    legacy['structures']=copy.deepcopy(DEFAULT['structures'])
    legacy['biomes']['family_bonuses']=copy.deepcopy(DEFAULT['biomes']['family_bonuses'])
    legacy['biomes']['variant_bonuses']=copy.deepcopy(DEFAULT['biomes']['variant_bonuses'])
    legacy['terrain'].update(variants=['v1','v2'])
    from .terrain import SEARCH_V1,SEARCH_V2
    legacy['terrain']['v1']=dict(SEARCH_V1);legacy['terrain']['v2']=dict(SEARCH_V2)
    validate_config(legacy)
    if two_group_policy(cfg) and not dynamic_policy(cfg):
        _integer(cfg['search'].get('max_misses'),0,8,'max_misses')
        expected_after=TWO_GROUP_STRONGHOLD_AFTER if cfg['search']['structure_order']==TWO_GROUP_ORDER else 2
        if stronghold_after(cfg)!=expected_after:
            raise ValueError('Stronghold placement differs from the resolved filter order')
    if dynamic_policy(cfg):
        max_misses_limit=0 if dynamic_v3_policy(cfg) else (3 if dynamic_v2_policy(cfg) else 2)
        _integer(cfg['search'].get('max_misses'),0,max_misses_limit,'max_misses')
        weights=cfg['search'].get('density_weights')
        if not isinstance(weights,dict) or set(weights)!=set(expected['search']['density_weights']):
            raise ValueError('Dynamic density weights must name all six supported structures')
        for name,weight in weights.items():_integer(weight,0,1000,f'density_weights.{name}')
        if not any(weights.values()):raise ValueError('At least one density weight must be positive')
        if cfg['search'].get('centroid_weights')!=expected['search']['centroid_weights']:raise ValueError('Centroid weights differ from the blueprint')
        if cfg['biomes'].get('include_frozen_peaks') is not True:raise ValueError('Dynamic peak witnesses include Frozen Peaks')
        if cfg['biomes'].get('nether_required')!=expected['biomes']['nether_required']:raise ValueError('All five Nether biome families are required')
    if two_group_policy(cfg):
        actual=cfg['structures'];baseline=expected['structures']
        if set(actual)!=set(baseline) or any(actual[k]!=baseline[k] for k in baseline if k not in ('minimum_counts','nether_minimum_counts')):
            raise ValueError('Blueprint structure floors and allowed bonuses cannot be relaxed')
        if set(actual['minimum_counts'])!=set(baseline['minimum_counts']) or set(actual['nether_minimum_counts'])!=set(baseline['nether_minimum_counts']):
            raise ValueError('Blueprint structure goal keys differ from the policy')
        strict={'stronghold'} if dynamic_policy(cfg) else {'stronghold','jungle_temple','desert_pyramid','outpost'}
        if marine_baseline_policy(cfg):strict.update(('monument','shipwreck'))
        for name,goal in actual['minimum_counts'].items():
            _integer(goal,0,64,f'minimum_counts.{name}')
            floor=baseline['hard_floors'].get(name,baseline['minimum_counts'][name])
            if goal<floor or (name in strict and goal!=baseline['minimum_counts'][name]):
                raise ValueError(f'Blueprint goal below fixed floor or strict target: {name}')
        for name,goal in actual['nether_minimum_counts'].items():
            _integer(goal,0,64,f'nether_minimum_counts.{name}')
            if goal<baseline['hard_floors'][name]:raise ValueError(f'Blueprint goal below fixed floor: {name}')
    elif cfg['structures']!=expected['structures']:
        raise ValueError('Blueprint structure floors and allowed bonuses cannot be relaxed')
    order=cfg['search']['structure_order']
    if len(order)!=len(expected['search']['structure_order']) or set(order)!=set(expected['search']['structure_order']):
        raise ValueError('Blueprint must check every required non-anchor structure')
    for key in ('spacing','sample_y','sample_y_levels','lattice','required_families','family_bonuses','variant_bonuses'):
        if key=='required_families' and dynamic_v2_policy(cfg):
            selected=cfg['biomes'].get(key)
            allowed=expected['biomes'][key]
            if (not isinstance(selected,list) or not all(isinstance(f,str) for f in selected) or
                len(set(selected))!=len(selected) or not set(selected)<=set(allowed)):
                raise ValueError('Required biome families must be a unique subset of the supported v2 families')
            continue
        if cfg['biomes'].get(key)!=expected['biomes'][key]:
            raise ValueError(f'Blueprint biome policy differs: {key}')
    if dynamic_v2_policy(cfg):
        if cfg['terrain'].get('variants')!=[]:
            raise ValueError('Dynamic V2 requires empty terrain active variants')
    else:
        if cfg['terrain'].get('variants')!=['v1'] or cfg['terrain'].get('v1')!=expected['terrain']['v1'] or 'v2' in cfg['terrain']:
            raise ValueError('Blueprint requires only V1 Coastal Continent with its declared thresholds')
    return cfg
