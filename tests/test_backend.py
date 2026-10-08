import numpy as np
import pytest
from seed_search.backend import Backend, biome_name, model_metadata

def test_grid_matches_scalar_at_negative_and_positive_coordinates():
    with Backend(-12345678912345) as b:
        g=b.grid(-71,-49,9,7,16,95)
        for row,col in [(0,0),(3,4),(6,8),(1,7)]:
            assert g["biomes"][row,col]==b.biome(-71+col*16,95,-49+row*16)
        assert np.isfinite(g["climate"]).all()
        assert np.array_equal(g["biomes"],b.grid(-71,-49,9,7,16,95)["biomes"])

@pytest.mark.parametrize("name",["trial_chamber","stronghold","mineshaft","fortress","bastion"])
def test_structure_scan_is_partition_independent(name):
    bounds=(-1024,-1024,1024,1024)
    with Backend(12345) as b:
        full=set(b.structures(name,bounds))
        left=set(b.structures(name,(-1024,-1024,-1,1024)))
        right=set(b.structures(name,(0,-1024,1024,1024)))
    assert full==left|right
    assert all(-1024<=x<=1024 and -1024<=z<=1024 for x,z in full)

def test_surface_density_step_is_an_approximation_not_a_claim():
    pts=np.array([[-256,-256],[-1,1],[0,0],[256,256],[900,-900]])
    with Backend(12345) as b:
        coarse,_=b.heights(pts,8)
        full,_=b.heights(pts,1)
        assert np.all(coarse<=full)  # coarse can miss thin solid layers
        assert np.all((-65<=full)&(full<=319))
        assert np.array_equal(coarse,b.heights(pts,8)[0])

def test_seed_12345_absent_fortress_is_not_promoted_from_failed_bastion():
    # Phone inspection found no Fortress around this rejected Bastion attempt.
    # A unit test of fallback behavior previously concealed this false positive.
    with Backend(12345) as b:
        assert b.attempt("bastion", -1, 0) == (-152, 120)
        assert b.structures("bastion", (-152, 120, -152, 120)) == []
        for viable in (False, True):
            assert b.structures("fortress", (-960, -80, 32, 912), viable) == []

def test_seed_12345_reported_nether_locations_remain_predicted():
    # Phone locate anchors: Fortress (64,816), Bastion (-680,-168).
    with Backend(12345) as b:
        assert b.structures("fortress", (48, 800, 96, 848)) == [(72, 824)]
        assert b.structures("bastion", (-680, -168, -680, -168)) == [(-680, -168)]

def test_trial_placement_uses_upper_32_bits():
    values=[]
    for seed in [12345,12345+(1<<32),12345+(1<<40)]:
        with Backend(seed) as b:
            values.append(b.attempt("trial_chamber",0,0))
    assert len(set(values))>1
    assert model_metadata()["structure_rng"]["trial_chamber"]==1

def test_missing_backend_biome_labels_are_mapped():
    assert [biome_name(i) for i in range(178,182)]==["grove","snowy_slopes","jagged_peaks","frozen_peaks"]

def test_closed_handle_and_bad_inputs_are_rejected():
    b=Backend(1)
    with pytest.raises(ValueError): b.grid(0,0,1000,1000)
    with pytest.raises(ValueError): b.heights([[1.5,2]])
    b.close()
    with pytest.raises(RuntimeError): b.biome(0,64,0)
