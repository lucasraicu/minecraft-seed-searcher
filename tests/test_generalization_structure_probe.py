"""Reference agreement is separate from physical presence and seed rejection."""
import copy
import pytest
from scripts.generalization_structure_probe import assess_locates, summarize_structures


def case(feature='village', predicted=None, *, disposition='retained', dim='overworld'):
    return dict(case_id='one', structure_type=feature, dimension=dim, predicted=[-296, -312] if predicted is None else predicted,
                origin=[-296, -312], disposition=disposition)


def check(c, output, **kwargs):
    return assess_locates([c], [dict(case_id='one', output=output)],
        prediction_revision=kwargs.get('prediction_revision', 'cubiomes-bedrock-26.50'),
        bds_build=kwargs.get('bds_build', '1.26.52.3'))[0]


def line(command, x, z): return f'[2026 INFO] The nearest minecraft:{command} is at block {x}, (y?), {z} (30 blocks away)'


def test_rejected_exact_is_preserved_as_possible_false_negative():
    c = case(disposition='rejected'); before = copy.deepcopy(c)
    r = check(c, [line('village', -296, -312)])
    assert r['outcome'] == 'reference_exact' and r['disposition'] == 'rejected'
    assert 'over-rejection' in r['interpretation'] and c == before


@pytest.mark.parametrize('f,p,reported,dim', [
    ('outpost', [528, 512], [536, 520], 'overworld'),
    ('mineshaft', [-16, -16], [-24, -24], 'overworld'),
    ('fortress', [-400, -400], [-408, -408], 'nether'),
])
def test_navigation_uses_only_exact_whitelist(f,p,reported,dim):
    assert check(case(f,p,dim=dim), [line(f if f != 'outpost' else 'pillager_outpost',*reported)])['outcome'] == 'navigation_exact'


@pytest.mark.parametrize('feature,command', [('stronghold','stronghold'),('trial_chamber','trial_chambers'),('trail_ruins','trail_ruins')])
def test_unproven_offsets_never_get_fuzzy_matches(feature,command):
    r = check(case(feature,[10,10]), [line(command,8,8)])
    assert r['outcome'] == 'different_reference' and 'unresolved' in r['interpretation']


def test_wrong_version_and_dimension_do_not_apply_projection():
    c=case('outpost',[528,512])
    assert check(c,[line('pillager_outpost',536,520)],bds_build='other')['outcome']=='unknown'
    c['dimension']='nether'
    assert check(c,[line('pillager_outpost',536,520)])['outcome']=='different_reference'


def test_grouped_temple_is_not_subtype_confirmation():
    r=check(case('igloo'),[line('temple',-296,-312)])
    assert r['outcome']=='reference_exact' and r['grouped_command'] and 'does not confirm subtype' in r['interpretation']


def test_missing_and_no_location_are_not_absence():
    r=assess_locates([case()],[],prediction_revision='cubiomes-bedrock-26.50',bds_build='1.26.52.3')[0]
    assert r['outcome']=='unknown'
    r=check(case(),['No valid structure found nearby'])
    assert r['outcome']=='no_location' and 'not proof' in r['interpretation']


def test_discovery_never_manufactures_count_or_recall():
    c=case(disposition='discovery');c['predicted']=None
    r=check(c,[line('village',20,30)])
    assert r['outcome']=='discovery_location' and r['reported']==[20,30]
    s=summarize_structures([r])
    assert s==dict(total=1,by_disposition={'discovery':{'discovery_location':1}},by_type={'village':{'discovery_location':1}})


@pytest.mark.parametrize('lines,outcome', [
    (['Syntax error: abandoned_camp'],'verifier_unavailable'),
    ([line('outpost',1,2)],'error'),
    ([line('village',1,2),line('village',1,2)],'error'),
    (['unrecognized'],'error'),
])
def test_unavailable_and_ambiguous_verifiers_preserve_uncertainty(lines,outcome):
    assert check(case(),lines)['outcome']==outcome


@pytest.mark.parametrize('mutate', [
    lambda c:c['predicted'].__setitem__(0,True),
    lambda c:c.update(predicted=None),
    lambda c:c.update(dimension='moon'),
    lambda c:c.update(disposition='absent'),
])
def test_malformed_cases_fail_before_comparison(mutate):
    c=case();mutate(c)
    with pytest.raises(ValueError):check(c,[])


def test_duplicate_and_orphan_bindings_rejected():
    with pytest.raises(ValueError):assess_locates([case(),case()],[],prediction_revision='',bds_build='')
    with pytest.raises(ValueError):assess_locates([case()],[dict(case_id='other',output=[])],prediction_revision='',bds_build='')
