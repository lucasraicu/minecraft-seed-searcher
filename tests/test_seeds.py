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
