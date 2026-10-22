import copy
import struct
import pytest
from seed_search.catalog.biome_provider import StoredBiomeProvider
from seed_search.catalog.models import identity


def context(dimension='overworld'):
    return dict(identity=identity(42,model_id='26.50',native_sha256='a'*64,source_sha256='b'*64),
                dimension=dimension,provider='bds_saved_runtime_v3',observed_build='1.26.52.3',evidence_sha256='c'*64)


def payload(ids):
    return bytes(512)+b''.join(b'\xff' if n is None else b'\x01'+struct.pack('<I',n) for n in ids)


def test_per_chunk_ceilings_unknown_interior_and_negative_coordinates():
    records=[dict(chunk_x=-1,chunk_z=-1,payload=payload([7,None,None])),
             dict(chunk_x=0,chunk_z=0,payload=payload([8,9,None])),
             dict(chunk_x=1,chunk_z=0,payload=payload([7,None,8,None]))]
    p=StoredBiomeProvider(context(),records,names={7:'plains',8:'desert'})
    assert p.sample(-1,-33,-1)['raw_id']==7
    assert p.sample(0,-33,0)['raw_id']==9
    assert p.sample(0,-33,0)['name'] is None # No guessed namespace.
    assert p.sample(16,-40,0)['status']=='unknown' # Interior hole.
    assert p.sample(0,63,0)['status']=='unknown' # Outside encoded record, not global clamp.
    assert p.sample(-17,-64,-1)['reason']=='missing_chunk'
    records[0]['payload']=payload([99]);assert p.sample(-1,-64,-1)['raw_id']==7
    c=p.context;c['identity']['seed']='0';assert p.context['identity']['seed']=='42'


@pytest.mark.parametrize('dimension,y', [('overworld',-64),('overworld',319),('nether',0),('nether',127)])
def test_dimensions_and_edges(dimension,y):
    count=25 if dimension=='overworld' else 8
    p=StoredBiomeProvider(context(dimension),[dict(chunk_x=0,chunk_z=0,payload=payload([1]*count))])
    assert p.sample(0,y,0)['status']=='observed'
    assert p.sample(0,-65 if dimension=='overworld' else -1,0)['status']=='unknown'
    assert p.sample(0,320 if dimension=='overworld' else 128,0)['status']=='unknown'


def test_wrong_provider_build_malformed_payload_duplicates_and_caps():
    c=context();c['provider']='procedural_model_v1';c['observed_build']=None
    with pytest.raises(ValueError):StoredBiomeProvider(c,[])
    c=context();c['observed_build']='other'
    with pytest.raises(ValueError):StoredBiomeProvider(c,[])
    r=dict(chunk_x=0,chunk_z=0,payload=payload([1]))
    with pytest.raises(ValueError):StoredBiomeProvider(context(),[r,r])
    with pytest.raises(ValueError):StoredBiomeProvider(context(),[dict(r,payload=b'x')])
    with pytest.raises(ValueError):StoredBiomeProvider(context(),[dict(r,payload=bytes((1<<20)+1))])
    with pytest.raises(ValueError):StoredBiomeProvider(context(),[dict(r,chunk_x=True)])
    p=StoredBiomeProvider(context(),[])
    with pytest.raises(ValueError):p.sample(True,0,0)
