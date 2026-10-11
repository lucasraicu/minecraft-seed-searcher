import numpy as np
import pytest

from seed_search.backend import biome_name
from seed_search.realm.biomes import classify, classify_ids, postprocess_ids
from seed_search.realm.config import default_config


def reference(raw, points, policy):
    ids=raw.tolist()
    result=classify([biome_name(int(value)) for value in ids],policy)
    result['raw_detections']={str(int(value)):{'samples':int(np.count_nonzero(np.asarray(ids)==value)),
                                             'coordinate':points[int(np.flatnonzero(np.asarray(ids)==value)[0])].tolist()}
                              for value in sorted(set(ids))}
    return result


def test_postprocessing_exact_parity_preserves_first_coordinates():
    policy=default_config()['biomes']
    # Includes every exposed ID, repeats, unknown IDs, and non-sorted observation order.
    ids=np.tile(np.arange(255,-1,-1,dtype=np.int32),7)
    points=np.column_stack((np.arange(len(ids))-1000,np.full(len(ids),63),np.arange(len(ids))*3-2000)).astype(np.int32)
    assert postprocess_ids(ids,points,policy)==reference(ids,points,policy)
    assert postprocess_ids(ids,points,policy)['raw_detections']['255']['coordinate']==[-1000,63,-2000]
    assert postprocess_ids(ids,points,policy)['raw_detections']['255']['samples']==7


def test_classify_ids_resolves_each_unique_id_once(monkeypatch):
    from seed_search.realm import biomes
    policy=default_config()['biomes']
    called=[]
    def lookup(value):
        called.append(value)
        return biome_name(value)
    monkeypatch.setattr(biomes,'biome_name',lookup)
    ids=np.array([4,4,5,5,4,999,999],dtype=np.int32)
    assert classify_ids(ids,policy)==classify([biome_name(int(value)) for value in ids],policy)
    assert called==[4,5,999]


def test_postprocessing_empty_and_length_validation():
    policy=default_config()['biomes']
    result=postprocess_ids(np.array([],dtype=np.int32),np.empty((0,3),dtype=np.int32),policy)
    assert result['raw_detections']=={} and result['qualification']=='PENDING'
    with pytest.raises(ValueError,match='equal length'):
        postprocess_ids(np.array([4]),np.empty((0,3)),policy)
