import pytest
from seed_search.seeds import parse_seed, seed_from_index
from seed_search.config import load_config, discovery_grid

@pytest.mark.parametrize("seed",[-(1<<63),-1,0,1,(1<<63)-1])
def test_exact_signed_seed_roundtrip(seed):
    assert parse_seed(str(seed))==seed

@pytest.mark.parametrize("seed",["1.5","--1",str(1<<63),str(-(1<<63)-1),True])
def test_invalid_seeds_rejected(seed):
    with pytest.raises(ValueError): parse_seed(seed)

def test_index_seeds_unique_and_reproducible():
    a=[seed_from_index(i) for i in range(1000)]
    assert len(set(a))==1000
    assert a==[seed_from_index(i) for i in range(1000)]
    assert seed_from_index(0)==0

def test_config_has_new_wood_requirement_and_bounded_grid():
    c,_=load_config("runs/sweep-readiness/config/sweep.yaml")
    assert not c["search"]["large_search_enabled"]
    assert not c["wood"]["island"]["abundance_required"]
    assert "abundant_accessible_wood_on_surrounding_land" in c["verification"]["final_required_checks"]
    assert sum(c["score_weights"].values())==100
    assert discovery_grid(c)==(-6528,-6528,205,205,64)

    assert discovery_grid(c)[0]+(discovery_grid(c)[2]-1)*64 >= 6504


def test_seed_strided_and_seeds_strided_exact_formula():
    from seed_search.seeds import seed_strided, seeds_strided
    # Basic edge cases
    assert seed_strided(0, 0) == 0
    assert seed_strided(0, 0xFFFFFFFF) == 0xFFFFFFFF
    assert seed_strided(0xFFFFFFFF, 0xFFFFFFFF) == -1
    assert seed_strided(0xFFFFFFFF, -1) == -1
    assert seed_strided(1, 0) == (1 << 32)
    assert seed_strided(6789, 12345) == (6789 << 32) | 12345

    # Signed seed negative boundary (high bit set)
    high_neg = 0x80000000
    s_neg = seed_strided(high_neg, 0x12345678)
    assert s_neg < 0
    assert (s_neg & 0xFFFFFFFFFFFFFFFF) == (high_neg << 32) | 0x12345678

    # seeds_strided sequence matches seed_strided scalar
    seeds = seeds_strided(100, 25, 0xABCDEF)
    assert len(seeds) == 25
    expected = [seed_strided(i, 0xABCDEF) for i in range(100, 125)]
    assert seeds == expected


def test_seeds_strided_np_parity():
    from seed_search.seeds import seeds_strided
    from seed_search.realm.native_batch import seeds_strided_np
    # Test parity across various low32 values and sibling ranges
    for low in (0, 1, 12345, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, -1):
        python_seeds = seeds_strided(50, 100, low)
        np_seeds = seeds_strided_np(50, 150, low).tolist()
        assert python_seeds == np_seeds


def test_seeds_strided_validation():
    from seed_search.seeds import seed_strided, seeds_strided
    with pytest.raises(ValueError):
        seed_strided(-1, 0)
    with pytest.raises(ValueError):
        seed_strided(True, 0)
    with pytest.raises(ValueError):
        seed_strided(0, True)
    with pytest.raises(ValueError):
        seeds_strided(-1, 10, 0)
    with pytest.raises(ValueError):
        seeds_strided(0, -1, 0)
    with pytest.raises(ValueError):
        seeds_strided(0, 10, True)
    with pytest.raises(ValueError):
        seeds_strided(0, 10, "not_a_number")


def test_bedrock_random_invariance_and_trial_chambers_separation():
    from seed_search.backend import Backend
    from seed_search.seeds import seed_strided
    low32 = 424242
    bounds = (-2000, -2000, 2000, 2000)

    # Siblings sharing low32 but having different high32
    seed_a = seed_strided(10, low32)
    seed_b = seed_strided(200, low32)

    with Backend(seed_a) as ba, Backend(seed_b) as bb:
        # BEDROCK_RANDOM structures are invariant across all 2^32 upper-bit siblings!
        assert ba.structures("village", bounds, False) == bb.structures("village", bounds, False)
        assert ba.structures("mansion", bounds, False) == bb.structures("mansion", bounds, False)
        assert ba.structures("ancient_city", bounds, False) == bb.structures("ancient_city", bounds, False)
        assert ba.structures("outpost", bounds, False) == bb.structures("outpost", bounds, False)

        # Trial Chambers uses Java 48-bit LCG (JAVA_RANDOM) and VARIES with upper bits!
        assert ba.structures("trial_chamber", bounds, False) != bb.structures("trial_chamber", bounds, False)
