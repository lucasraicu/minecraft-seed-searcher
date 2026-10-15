"""Declared prediction/actual-generation capabilities; no implied fallback."""
import hashlib
import platform
from pathlib import Path
from ..backend import model_metadata, STRUCTURES, RAW_MT_TYPES, biome_name


ROOT=Path(__file__).resolve().parents[3]


def report(cfg):
    blueprint=cfg.get('contract')=='master_seed_blueprint_v1'
    known={biome_name(i):i for i in range(256) if not biome_name(i).startswith('unknown_')}
    features={name:{'candidate_placement':'PREDICTED','generation':'UNVERIFIED',
                    'complete_negative_evidence':False,'effective_placement_seed_bits':32 if name in RAW_MT_TYPES else 64,
                    'viability_seed_bits':64} for name in STRUCTURES}
    for name in ('monster_room',):
        features[name]={'candidate_placement':'UNSUPPORTED','generation':'UNVERIFIED','complete_negative_evidence':False}
    features['stronghold']['enumerator_completeness']='incomplete; known reference misses'
    for name in ('ancient_city','bastion'):
        features[name]['known_disagreement']='candidate/viability disagreement in frozen reference fixture'
    for name in ('dappled_forest','sulfur_caves'):
        features[name]={'biome_id':known.get(name),'prediction':'PREDICTED' if name in known else 'UNSUPPORTED',
                        'generation':'UNVERIFIED','complete_negative_evidence':False}
    features['terrain']={'prediction':'MC_26_50 raw density without actual liquids/aquifers/decoration',
                         'bds_actual_blocks':'supported in bounded isolated tests',
                         'natural_ground_provenance':'PARTIAL; structures/waterlogging/ice not fully validated',
                         'exact_variant_qualification':'UNVERIFIED'}
    return {'target_version':cfg['game']['target_version'],'bds_version':cfg['game']['bds_version'],
            'prediction_model':cfg['game']['backend_model'],'backend':model_metadata(),
            'features':features,'large_search_ready':False,'prediction_scale_available':True,
            'edition':'bedrock','silent_fallback':False,
            'baseline_execution':{'default':'python','native':'explicit opt-in, audited blueprint eligibility profile only; selected runtime is validated'},
            'remaining_gates':['version-matched required structure validation','complete stronghold recall',
                               'surface-biome coverage','actual natural-ground and water geometry calibration'],
            'missing_support_policy':'unknown or unsupported, never confirmed absent',
            'contract':cfg.get('contract','historical_realm_schema5'),
            'geometry_scope':'coastal_geometry_subset; full blueprint terrain certification pending' if blueprint else 'historical island and mountain variants',
            'full_blueprint_certification':False,
            'caves':'automatic four-Y predictor biome witnesses; actual cave verification remains explicit' if blueprint else 'manual invocation only',
            'variants':list(cfg.get('terrain',{}).get('variants',['v1','v2'])),
            'platform':platform.platform()}


def identity():
    from .. import _native
    from ..backend import native_runtime
    paths=[Path(_native.__file__),ROOT/'vendor/backend.json',ROOT/'native/bridge.c',ROOT/'native/bridge.h',ROOT/'native/filters.inc',ROOT/'native/blueprint_batch.h',ROOT/'native/blueprint_batch.inc',ROOT/'native/blueprint_dynamic.inc']
    # Freeze computational implementation independently from historical report rendering.
    paths += [ROOT/f'src/seed_search/{name}.py' for name in ('backend','seeds')]
    paths += [ROOT/f'src/seed_search/realm/{name}.py' for name in ('baseline','blueprint','dynamic','coastal','marine','spawn','bounds','biomes','sampling','inventory','raw','siblings','config','runner','store','resources','native_batch','native_records','native_encoding')]
    return {'model':model_metadata(),'native_runtime':native_runtime(),
            'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
