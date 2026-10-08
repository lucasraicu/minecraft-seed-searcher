import numpy as np
from seed_search.geometry import island_components, band
from seed_search.wood import surrounding_score, openness_score

def test_diagonal_land_bridge_connects_to_boundary():
    land=np.zeros((15,15),dtype=bool)
    land[5:10,5:10]=True
    isolated=island_components(land,-448,-448,64,[-5000,5000])
    assert len(isolated)==1
    for i in range(6): land[i,i]=True
    assert island_components(land,-448,-448,64,[-5000,5000])==[]

def test_center_stays_on_land_when_centroid_is_water():
    land=np.zeros((15,15),dtype=bool)
    land[4:11,4:11]=True
    land[6:9,6:9]=False
    result=island_components(land,0,0,64,[-5000,5000])
    assert len(result)==1
    x,z=result[0]["center"]
    assert land[z//64,x//64]
    assert not result[0]["isolation_verified"]

def test_zero_island_wood_is_preferred_not_disqualified():
    assert openness_score(0)==1
    assert openness_score(1)==0
    assert surrounding_score(0)==0
    assert surrounding_score(.6)==1
    assert band(299,300,700)<band(300,300,700)==1
    assert band(701,300,700)<1
