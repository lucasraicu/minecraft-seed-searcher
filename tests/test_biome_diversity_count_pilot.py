"""Distinct biome variants never count repeated points or repeated IDs."""
import numpy as np
import pytest
from seed_search.backend import Backend
from scripts.biome_diversity_pilot_api import DiversityBackend

@pytest.mark.parametrize('dimension',[-1,0,1])
def test_variant_counts_and_multi_family_stream_match_full_point_inventory(dimension):
    points=np.array([(x,63,z) for x in range(-512,1536,128) for z in range(-512,1536,128)],np.int32)
    with Backend(4318555775) as ref,DiversityBackend(4318555775) as counted:
        ids=ref.biome_points(points,dimension)
        unique=sorted(set(map(int,ids)))
        groups=[unique,unique[:2]]
        for n in (1,2,3,4):
            prepared=counted.prepare(points,dimension,[unique],[n])
            assert counted.prepared(prepared)[0]==(len(unique)>=n)
            combo=counted.prepare(points,dimension,groups,[n,1])
            assert counted.prepared(combo)[0]==(len(unique)>=n and bool(groups[1]))


def test_repeating_one_sample_cannot_satisfy_two_distinct_variants():
    points=np.array([(0,63,0)]*20,np.int32)
    with Backend(12345) as ref,DiversityBackend(12345) as counted:
        ident=ref.biome(0,63,0)
        allowed=[ident,1 if ident!=1 else 4]
        assert counted.prepared(counted.prepare(points,0,[allowed],[1]))[0]
        assert not counted.prepared(counted.prepare(points,0,[allowed],[2]))[0]


def test_insufficient_catalog_capacity_rejects_without_queries():
    with DiversityBackend(12345) as counted:
        answer,queried=counted.prepared(counted.prepare(np.array([(0,63,0)],np.int32),0,[[185]],[2]))
        assert not answer and queried==0


def test_invalid_goals_and_closed_handle_rejected():
    with DiversityBackend(12345) as counted:
        with pytest.raises(ValueError):counted.prepare(np.array([(0,63,0)],np.int32),0,[[4]],[0])
        prepared=counted.prepare(np.array([(0,63,0)],np.int32),0,[[4]],[1])
    with pytest.raises(RuntimeError):counted.prepared(prepared)
