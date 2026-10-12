"""Experimental count caps and fused continuation equal the complete predictor."""
import pytest
from seed_search.backend import Backend,STRUCTURES
from scripts.count_pilot_api import CountBackend,lib,TYPES
from scripts.pilot_locked_stronghold import exact_bounds

@pytest.mark.parametrize('seed,center',[(12345,(4,-4)),(-1,(-1536,768)),(4318555775,(1924,1540))])
def test_direct_and_fused_count_requirements_match_full_inventory(seed,center):
    bounds=exact_bounds(center)
    with Backend(seed) as ref,CountBackend(seed) as counted:
        for name in STRUCTURES:
            b=bounds['nether' if name in ('fortress','bastion','ruined_portal_nether') else 'overworld']
            expected=ref.structures(name,b,True)
            for n in (1,2,3,4):
                for bits in (0,32,48):
                    actual,_,_=counted.count(name,b,n,gate_bits=bits)
                    assert actual==(len(expected)>=n),(seed,name,n,bits)
                if name!='stronghold':
                    raw=ref.structures(name,b,False)
                    assert counted.count(name,b,n,raw_only=True)[0]==(len(raw)>=n)


def test_fused_raw_negative_avoids_viability_work():
    with CountBackend(12345) as b:
        direct=b.count('village',(0,0,0,0),2)
        fused=b.count('village',(0,0,0,0),2,gate_bits=32)
        assert not direct[0] and not fused[0]
        assert fused[1][1]==0 and fused[1][3]==1


def test_fused_positive_reuses_prefix_without_extra_placement_calls():
    with CountBackend(12345) as b:
        for name in ('village','shipwreck','buried_treasure','trial_chamber'):
            direct=b.count(name,(-768,-768,767,767),3)
            fused=b.count(name,(-768,-768,767,767),3,gate_bits=48)
            assert fused[0]==direct[0]
            if fused[0]:
                assert fused[1][0]==direct[1][0]
                assert fused[1][1]==direct[1][1]


def test_shared_feature_capacity_is_a_safe_native_raw_rejection():
    row={'bounds':{'overworld':(0,0,511,511),'nether':(0,0,511,511)}}
    names=('desert_pyramid','jungle_temple','swamp_hut','igloo')
    with CountBackend(12345) as b:
        prepared=b.prepare_combo(row,names,1)
        answer,stats=b.combo_prepared(prepared,32,False)
        assert not answer and stats[3]>0 and stats[1]==0
        assert not b.combo_prepared(prepared,0,False)[0]


def test_family_restricted_counts_match_explicit_full_start_classification():
    with Backend(12345) as ref,CountBackend(12345) as counted:
        for name,y in [('village',63),('mineshaft',0),('stronghold',63),('trial_chamber',0)]:
            bounds=(-768,-768,767,767)
            starts=ref.structures(name,bounds,True)
            ids=[ref.biome(x,y,z) for x,z in starts]
            allowed=set(ids[:2])
            expected=sum(v in allowed for v in ids)
            for n in (1,2,4):
                assert counted.count(name,bounds,n,allow=allowed,y=y)[0]==(expected>=n)
                assert counted.count(name,bounds,n,gate_bits=48,allow=allowed,y=y)[0]==(expected>=n)


def test_invalid_goals_orders_bounds_and_closed_handles_are_rejected():
    with CountBackend(12345) as b:
        for n in (0,33,True):
            with pytest.raises(ValueError):b.count('village',(0,0,1,1),n)
        with pytest.raises(ValueError):b.count('village',(1,0,0,1),1)
        with pytest.raises(ValueError):b.prepare_combo({'bounds':exact_bounds((4,4))},('village','village'),1)
    with pytest.raises(RuntimeError):b.count('village',(0,0,1,1),1)


def test_cached_raw_prefix_keeps_full64_viability_fresh_and_bounds_in_key():
    from scripts.count_pilot_api import lib
    seeds=(12345,(0x1234<<48)|12345)
    bounds=(-768,-768,767,767)
    lib.pc_cache_reset(1)
    try:
        for index,seed in enumerate(seeds):
            with Backend(seed) as ref,CountBackend(seed) as b:
                expected=len(ref.structures('village',bounds,True))>=2
                answer,stats,_=b.count('village',bounds,2,gate_bits=32)
                assert answer==expected
                assert stats[6]==int(index==1)
                shifted=(-767,-768,767,767)
                expected_shift=len(ref.structures('village',shifted,True))>=2
                assert b.count('village',shifted,2,gate_bits=32)[0]==expected_shift
    finally:lib.pc_cache_reset(0)
