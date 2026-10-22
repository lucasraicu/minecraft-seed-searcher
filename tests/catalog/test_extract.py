import copy
import pytest
from seed_search.catalog.models import identity
from seed_search.catalog.extract import extract_observation
from seed_search.catalog.coverage import complete_for
from seed_search.catalog.registry import ENVELOPE, STRUCTURES, BIOMES


def ident(seed=0):
    return identity(seed, model_id='MC_26_50', native_sha256='a'*64, source_sha256='b'*64)


class Stub:
    def __init__(self, fail=None):
        self.calls=[]; self.batches=0; self.fail=fail
    def structures(self, name, bounds, viable=True):
        self.calls.append((name, bounds, viable))
        if self.fail == name: raise RuntimeError('inventory failed')
        return [(-5120, -5120), (5119, 5119), (0, 0), (0, 0)]
    def biome_points(self, xyz):
        self.batches += 1
        if self.fail == 'biomes' and self.batches == 3: raise RuntimeError('batch failed')
        return [1]*len(xyz)


def test_one_envelope_full_plane_and_resume():
    backend=Stub(); observations=[]
    obs=extract_observation(ident(), backend, name_for_id=lambda _: 'plains', on_progress=observations.append)
    assert len(backend.calls)==14 and backend.batches==25
    assert all(bounds==(-5120,-5120,5119,5119) for _,bounds,_ in backend.calls)
    assert len(obs['biomes'])==25600 and len(obs['structures']['structure.village'])==3
    assert all(v['status']=='complete' for v in obs['coverage'].values())
    assert complete_for(obs,'structure.village',(976,-976),8192,512)
    backend2=Stub()
    assert extract_observation(ident(),backend2,name_for_id=lambda _: 'plains',previous=obs)==obs
    assert backend2.calls==[] and backend2.batches==0
    assert observations[0]['coverage'] != observations[-1]['coverage']


def test_failure_is_not_completed_zero_and_retry():
    backend=Stub('village')
    obs=extract_observation(ident(), backend,name_for_id=lambda _: 'plains')
    assert obs['coverage']['structure.village']['status']=='failed'
    assert 'structure.village' not in obs['structures']
    assert not complete_for(obs,'structure.village',(0,0),2048)
    retry=Stub(); done=extract_observation(ident(),retry,name_for_id=lambda _: 'plains',previous=obs)
    assert [c[0] for c in retry.calls]==['village'] and not retry.batches
    assert done['coverage']['structure.village']['status']=='complete'
    with pytest.raises(ValueError): extract_observation(ident(1),Stub(),name_for_id=lambda _: 'plains',previous=done)


def test_partial_biome_resume_and_unmapped():
    obs=extract_observation(ident(), Stub('biomes'),name_for_id=lambda _: 'plains')
    assert len(obs['biomes'])==2048
    assert all(obs['coverage'][f['id']]['status']=='failed' for f in BIOMES)
    retry=Stub(); done=extract_observation(ident(),retry,name_for_id=lambda _: 'plains',previous=obs)
    assert retry.batches==25 and retry.calls==[] and len(done['biomes'])==25600
    unknown=extract_observation(ident(),Stub(),name_for_id=lambda _: 'unknown_1')
    assert len(unknown['biomes'])==25600
    assert not complete_for(unknown,'biome.plains',(0,0),8192)


def test_output_failure_propagates_and_bad_coordinates_fail():
    def fail(_): raise OSError('disk full')
    with pytest.raises(OSError): extract_observation(ident(),Stub(),name_for_id=lambda _: 'plains',on_progress=fail)
    class Outside(Stub):
        def structures(self,*a,**kw): return [(5120,0)]
    obs=extract_observation(ident(),Outside(),name_for_id=lambda _: 'plains')
    assert all(obs['coverage'][f['id']]['status']=='failed' for f in STRUCTURES)


def test_count_not_clipped_to_user_limit():
    class Many(Stub):
        def structures(self,*a,**kw): return [(x,0) for x in range(300)]
    obs=extract_observation(ident(),Many(),name_for_id=lambda _: 'plains')
    assert len(obs['structures']['structure.village'])==300
