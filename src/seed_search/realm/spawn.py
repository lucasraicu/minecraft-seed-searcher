"""Downstream, evidence-scoped initial-player spawn classification for v2.

No predictor x/z or world-spawn metadata establishes initial player placement.
An absent or partial observation stays pending and never changes baseline status.
"""
from ..seeds import parse_seed
from .config import two_group_policy, dynamic_policy

POLICY='v2-initial-player-spawn-radius100-y63-dry-solid-v1'
OCEAN={'ocean','deep_ocean','cold_ocean','deep_cold_ocean','frozen_ocean',
       'deep_frozen_ocean','lukewarm_ocean','deep_lukewarm_ocean','warm_ocean'}


def player_inspection_statuses(candidate):
    """Report optional inspections independently of predictive eligibility."""
    reasons = {
        'end_access': 'Predicted Stronghold starts do not establish a reachable, intact portal room.',
        'portal_links': 'Nether arrival safety and return links have not been inspected.',
        'snow_ice_resources': 'Snow/ice biome witnesses do not establish packed ice, blue ice, or powder snow quantities.',
    }
    supplied = candidate.get('player_inspections') or {}
    return {name: (supplied[name] if isinstance(supplied.get(name), dict) and supplied[name].get('source')
                   else {'status': 'UNVERIFIED', 'reason': reason, 'source': None})
            for name, reason in reasons.items()}


def classify_spawn(candidate,cfg,evidence=None):
    if not two_group_policy(cfg):raise ValueError('Spawn policy requires the v2 blueprint')
    center=candidate.get('evaluation_center')
    dynamic=dynamic_policy(cfg)
    if dynamic:
        ow_half=cfg['deployment']['overworld_side_blocks']//2
        ow_bounds=cfg['discovery']['overworld_bounds']
        min_c=ow_bounds[0]+ow_half
        max_c=ow_bounds[2]-ow_half
        if not isinstance(center,list) or len(center)!=2 or any(type(v) is not int or not min_c<=v<=max_c for v in center):
            raise ValueError('Dynamic spawn metric requires a selected center inside the envelope')
    elif center!=[0,0]:raise ValueError('V2 spawn policy requires the fixed origin center')
    base={'policy':'dynamic-initial-player-spawn-radius100-y63-dry-solid-v1' if dynamic else POLICY,'status':'PENDING','baseline_qualification':candidate.get('baseline_qualification',candidate.get('qualification')),
          'evaluation_center':list(center),'radius_blocks':100,'evidence_kind':None,'coordinates':None,
          'predicates':{'within_radius':None,'y_at_least_63':None,'non_ocean':None,
                        'dry':None,'solid_support':None,'headroom':None}}
    if evidence is None:return base
    if not isinstance(evidence,dict):raise ValueError('Spawn evidence must be an object')
    source=evidence.get('source')
    if (not isinstance(source,dict) or source.get('kind')!='actual_generation' or
        source.get('provider')!='bds' or source.get('version')!=cfg['game']['bds_version'] or
        evidence.get('placement_kind')!='initial_player' or
        str(parse_seed(evidence.get('seed')))!=candidate['seed']):
        raise ValueError('Initial-player evidence needs the pinned BDS source/version/seed')
    point=evidence.get('coordinates')
    if not isinstance(point,list) or len(point)!=3 or any(type(v) is not int for v in point):
        raise ValueError('Initial-player coordinates must be integer [x,y,z]')
    x,y,z=point
    biome=evidence.get('biome')
    if biome is not None and (not isinstance(biome,str) or not biome.strip()):
        raise ValueError('Spawn biome must be a named observation')
    biome_id=biome.strip().lower().removeprefix('minecraft:').replace(' ','_') if biome is not None else None
    predicates={'within_radius':(x-center[0])**2+(z-center[1])**2<=100*100,'y_at_least_63':y>=63,
                'non_ocean':None if biome_id is None else biome_id not in OCEAN,
                'dry':evidence.get('dry') if type(evidence.get('dry')) is bool else None,
                'solid_support':evidence.get('solid_support') if type(evidence.get('solid_support')) is bool else None,
                'headroom':evidence.get('headroom') if type(evidence.get('headroom')) is bool else None}
    status='FAILED' if False in predicates.values() else 'VERIFIED' if all(v is True for v in predicates.values()) else 'PENDING'
    return {**base,'status':status,'evidence_kind':'actual_initial_player_placement',
            'coordinates':point,'biome':biome,'predicates':predicates,'source':source}


def save_spawn_evidence(store,candidate_id,evidence):
    candidate=store.get_candidate(candidate_id)
    if candidate is None:raise ValueError('Unknown baseline candidate')
    stage=classify_spawn(candidate,store.identity['config'],evidence)
    store.upsert_candidate({'id':candidate_id,'spawn_stage':stage})
    return stage
