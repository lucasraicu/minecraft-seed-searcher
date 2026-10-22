import pytest
from seed_search.catalog.structure_verification import TYPES,verification_matrix,assess_structure_evidence
from seed_search.catalog.models import identity


def context(provider='bds_locate_v1',dimension='overworld'):
    return dict(identity=identity(1,model_id='26.50',native_sha256='a'*64,source_sha256='b'*64),
        dimension=dimension,provider=provider,observed_build='1.26.52.3',evidence_sha256='c'*64)


def test_all_21_types_have_explicit_route_without_physical_census():
    rows=verification_matrix();assert len(rows)==21 and {r['structure_type'] for r in rows}==set(TYPES)
    assert not any(r['physical_instance_count_supported'] for r in rows)
    for row in rows:
        c=context(dimension=row['dimension']);r=assess_structure_evidence(row['structure_type'],[-24,-24],context=c)
        assert r['status']=='unknown' and r['physical_count'] is None
    rows[0]['dimension']='other';assert verification_matrix()[0]['dimension']=='overworld'


def test_reference_offsets_negative_coordinates_and_different_reference():
    r=assess_structure_evidence('outpost',[-24,-24],context=context(),reported=[-16,-16])
    assert r['status']=='reference_exact' and r['raw_start']==[-24,-24]
    r=assess_structure_evidence('stronghold',[-24,-24],context=context(),reported=[-26,-26])
    assert r['status']=='located_reference' and r['raw_start']==[-24,-24] and r['reported_reference']==[-26,-26]
    assert r['physical_count'] is None


def test_grouped_temple_and_no_locate_never_prove_subtype_or_absence():
    for t in ('desert_pyramid','jungle_temple','swamp_hut','igloo'):
        r=assess_structure_evidence(t,[8,8],context=context(),reported=[8,8],subtype=t)
        assert not r['positive_type'] and r['status']=='located_group_reference'
    assert assess_structure_evidence('village',[8,8],context=context())['status']=='unknown'


def test_point_membership_is_not_predicted_instance_verification():
    c=context('bds_feature_membership_v1')
    r=assess_structure_evidence('village',[8,8],context=c,membership=dict(coordinate=[900,77,900],types=['minecraft:village']))
    assert r['status']=='observed_at_point' and r['raw_start']==[8,8] and r['physical_count'] is None
    assert not assess_structure_evidence('village',[8,8],context=c,membership=dict(coordinate=[8,77,8],types=['village']))['positive_type']
    for bad in (dict(c,dimension='nether'),dict(c,observed_build='other'),dict(c,provider='procedural_model_v1',observed_build=None)):
        with pytest.raises(ValueError):assess_structure_evidence('village',[8,8],context=bad)
    with pytest.raises(ValueError):assess_structure_evidence('village',[True,8],context=c)


def test_camp_structure_set_is_not_a_locatable_variant():
    from seed_search.catalog.structure_verification import CAMP_VARIANTS
    assert len(CAMP_VARIANTS)==18
    c=context()
    ambiguous=assess_structure_evidence('abandoned_camp',[224,208],context=c,reported=[221,212])
    assert not ambiguous['positive_type']
    actual=assess_structure_evidence('abandoned_camp',[224,208],context=c,reported=[221,212],reported_type='minecraft:abandoned_camp_taiga')
    assert actual['positive_type'] and actual['status']=='located_reference' and actual['expected_reference'] is None
    positive=assess_structure_evidence('abandoned_camp',[224,208],context=context('bds_feature_membership_v1'),membership=dict(coordinate=[221,68,212],types=['minecraft:abandoned_camp_taiga']))
    assert positive['positive_type'] and positive['physical_count'] is None


def test_temple_subtype_requires_exact_observed_token_not_nearby_other_type():
    c=context('bds_feature_membership_v1')
    for t,token in [('desert_pyramid','desert_pyramid'),('jungle_temple','jungle_pyramid'),('swamp_hut','swamp_hut'),('igloo','igloo')]:
        result=assess_structure_evidence(t,None,context=c,membership=dict(coordinate=[-1736,68,2824],types=['minecraft:'+token]))
        assert result['positive_type'] and result['status']=='observed_at_point'
