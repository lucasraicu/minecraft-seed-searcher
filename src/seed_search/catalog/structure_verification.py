"""Pinned positive reference methods. Never infers absence or physical totals."""
import copy
from .accuracy import validate_context,context_id,integer
from ..realm.structure_coordinates import project_navigation_reference
from ..realm.predictor_diagnostics import COMMANDS

TYPES=('trial_chamber','stronghold','mineshaft','ancient_city','village','ruined_portal',
       'shipwreck','monument','outpost','fortress','bastion','desert_pyramid',
       'jungle_temple','swamp_hut','igloo','ocean_ruin','mansion','buried_treasure',
       'trail_ruins','abandoned_camp','ruined_portal_nether')
TEMPLES=frozenset(('desert_pyramid','jungle_temple','swamp_hut','igloo'))
# Exact tokens actually observed in retained Beta copied-world reports.
MEMBERSHIP={
 'trial_chamber':('minecraft:trial_chambers',),'mineshaft':('minecraft:mineshaft',),
 'ancient_city':('minecraft:ancient_city',),'village':('minecraft:village',),
 'ruined_portal':('minecraft:ruined_portal',),'shipwreck':('minecraft:shipwreck',),
 'monument':('minecraft:monument',),'outpost':('minecraft:pillager_outpost',),
 'desert_pyramid':('minecraft:desert_pyramid',),'jungle_temple':('minecraft:jungle_pyramid',),
 'swamp_hut':('minecraft:swamp_hut',),'igloo':('minecraft:igloo',),
 'ocean_ruin':('minecraft:ruins',),'buried_treasure':('minecraft:buried_treasure',),
 'trail_ruins':('minecraft:trail_ruins',),'fortress':('minecraft:fortress',),
 'bastion':('minecraft:bastion_remnant',),'ruined_portal_nether':('minecraft:ruined_portal',),
 'mansion':('minecraft:mansion',),
}
# Pinned BDS vanilla1.26.50 structure-set JSON: camp is a SET, not a locatable
# jigsaw structure ID. Actual default-world taiga/forest locates and Beta taiga
# membership discriminate this from the old unsupported-registration hypothesis.
CAMP_VARIANTS=tuple('minecraft:abandoned_camp_'+name for name in (
 'bamboo_jungle','birch_forest','cherry_grove','dappled_forest','flower_forest','forest',
 'meadow','birch_forest_mutated','mega_taiga','redwood_taiga_mutated','pale_garden',
 'savanna','cold_taiga','jungle_edge','swampland','taiga','extreme_hills_plus_trees','mesa_plateau_stone'))
MEMBERSHIP['abandoned_camp']=CAMP_VARIANTS
VARIABLE_REFERENCES=frozenset(('stronghold','trial_chamber','trail_ruins','abandoned_camp'))



def _dimension(name):return 'nether' if name in ('fortress','bastion','ruined_portal_nether') else 'overworld'


def _point(value,n):
    if not isinstance(value,list) or len(value)!=n:raise ValueError('Invalid reference coordinate')
    return [integer(v) for v in value]


def verification_matrix():
    return [dict(structure_type=t,dimension=_dimension(t),locate_command=None if t=='abandoned_camp' else COMMANDS.get(t,t),
        locate_commands=list(CAMP_VARIANTS) if t=='abandoned_camp' else ['minecraft:'+COMMANDS.get(t,t)],
        locate_scope='grouped_temple_reference' if t in TEMPLES else 'type_navigation_reference',
        positive_route=('observed_type_membership' if t in MEMBERSHIP else
                        'subtype_piece_witness_required' if t in TEMPLES else 'game_located_reference'),
        membership_tokens=list(MEMBERSHIP.get(t,())),membership_scope='2.11.0-beta gametest-enabled disposable copy; not default-world certification',physical_instance_count_supported=False,
        reference_mapping=('audited_navigation_offset' if t in ('outpost','mineshaft','fortress') else
                           'piece_dependent_unresolved' if t in VARIABLE_REFERENCES else 'direct_reference'),
        unresolved=('variant_piece_reference_mapping_not_fixed_offset' if t=='abandoned_camp' else
                    'grouped_locate_requires_independent_subtype_witness' if t in TEMPLES else
                    'instance_identity_not_available')) for t in TYPES]


def assess_structure_evidence(structure_type,predicted,*,context,reported=None,membership=None,subtype=None,reported_type=None):
    if structure_type not in TYPES:raise ValueError('Unsupported structure type')
    ctx=validate_context(context)
    if ctx['dimension']!=_dimension(structure_type):raise ValueError('Wrong structure dimension')
    if ctx['provider'] not in ('bds_locate_v1','bds_feature_membership_v1'):raise ValueError('Unsupported structure evidence provider')
    raw=None if predicted is None else _point(predicted,2)
    actual=None if reported is None else _point(reported,2)
    projection=None if raw is None else project_navigation_reference(structure_type,*raw,
        dimension=ctx['dimension'],prediction_revision='cubiomes-bedrock-26.50' if ctx['identity']['model_id'] in ('26.50','MC_26_50') else None,
        bds_build=ctx['observed_build'])
    expected=None if raw is None or structure_type in VARIABLE_REFERENCES else ([projection.navigation_x,projection.navigation_z] if projection else list(raw))
    result=dict(status='unknown',raw_start=raw,expected_reference=expected,reported_reference=actual,
        reported_reference_type=reported_type,method_scope='experimental_beta_copy' if ctx['provider']=='bds_feature_membership_v1' else 'default_game_locate_reference',point_evidence=None,positive_type=False,physical_count=None,context_id=context_id(ctx),
        reason='Missing or inconclusive evidence; no absence inference')
    if actual is not None:
        if ctx['provider']!='bds_locate_v1':raise ValueError('Locate evidence requires locate provider')
        if structure_type=='abandoned_camp' and reported_type not in CAMP_VARIANTS:
            result.update(reason='Camp requires an exact biome-specific structure identifier; generic set ID is not a positive route')
            return result
        if reported_type is not None and structure_type!='abandoned_camp' and reported_type!='minecraft:'+COMMANDS.get(structure_type,structure_type):
            raise ValueError('Reported structure identifier differs')
        if structure_type in TEMPLES:
            result.update(status='located_group_reference',reason='Grouped temple locate cannot establish subtype')
        else:
            result.update(status='located_reference',positive_type=True,
                reason='Game located this type; not a physical census or confirmation of a different predicted start')
            if expected is not None and actual==expected:
                result.update(status='reference_exact',reason='Exact agreement under pinned reference convention; physical count unverified')
    if subtype is not None:
        # A caller-supplied subtype label without a scoped piece/block oracle is
        # not evidence. Keep it out of positive admission until that method exists.
        if subtype not in TEMPLES:raise ValueError('Invalid temple subtype')
    if membership is not None:
        if ctx['provider']!='bds_feature_membership_v1':raise ValueError('Membership requires its own provider')
        if not isinstance(membership,dict) or set(membership)!={'coordinate','types'}:raise ValueError('Invalid membership evidence')
        coordinate=_point(membership['coordinate'],3);types=membership['types']
        integer(coordinate[1],*((-64,319) if ctx['dimension']=='overworld' else (0,127)))
        if not isinstance(types,list) or len(types)>64 or any(not isinstance(t,str) or len(t)>128 for t in types):raise ValueError('Invalid membership tokens')
        result['point_evidence']=copy.deepcopy(membership)
        if set(MEMBERSHIP.get(structure_type,())) & set(types):
            result.update(status='observed_at_point',positive_type=True,
                reason='Type membership at this exact point; association to a predicted instance and physical total remain unknown')
    return result
