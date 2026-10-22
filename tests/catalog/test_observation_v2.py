"""Typed survey regressions with small deterministic backends, no world generation."""
import copy
import pytest
from seed_search.catalog.models import identity, empty_observation_v2,validate_observation_v2
from seed_search.catalog.extract import extract_observation_v2
from seed_search.catalog.registry import FEATURES_V2


class Backend:
    def __init__(self):self.calls=[];self.fail=False
    def structures(self,key,bounds,viable):
        self.calls.append(('structure',key,bounds))
        if self.fail and key=='village':raise RuntimeError('stub failure')
        return [[0,0],[0,0]]
    def biome_points(self,points,dimension):
        self.calls.append(('biome',dimension,len(points)))
        return [1 if dimension==0 else 8]*len(points)


def ident():return identity('123',model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64)
def extract(backend,**kwargs):
    return extract_observation_v2(ident(),backend,name_for_id=lambda i:'plains' if i==1 else 'nether_wastes',
        bounds={'overworld':[-64,-64,65,65],'nether':[-64,-64,65,65]},**kwargs)


def test_survey_calls_each_feature_once_and_separates_dimension_planes():
    backend=Backend();obs=extract(backend)
    assert len([x for x in backend.calls if x[0]=='structure'])==17
    assert [x for x in backend.calls if x[0]=='biome']==[('biome',0,9),('biome',-1,9)]
    assert all(points==[[0,0]] for points in obs['structures'].values())
    assert obs['coverage']['structure.stronghold']['status']=='partial'
    for f in FEATURES_V2:
        if f['kind']=='biome_witness':assert obs['coverage'][f['id']]['status']=='complete'
    assert validate_observation_v2(obs)==obs


def test_completed_plane_cannot_omit_sample_or_claim_unknown_mapping():
    obs=extract(Backend());bad=copy.deepcopy(obs);bad['biomes']['nether'].pop()
    with pytest.raises(ValueError,match='missing samples'):validate_observation_v2(bad)
    bad=copy.deepcopy(obs);bad['biome_names']['8']='unknown_8'
    with pytest.raises(ValueError,match='mapping'):validate_observation_v2(bad)


def test_resume_skips_completed_features_and_bounded_strongholds_remain_partial():
    obs=extract(Backend());backend=Backend();resumed=extract(backend,previous=obs)
    assert len(backend.calls)==1
    assert resumed['coverage']['structure.stronghold']['status']=='partial'
    bad=copy.deepcopy(obs);bad['identity']['seed']='124'
    with pytest.raises(ValueError,match='identity'):extract(Backend(),previous=bad)


def test_failure_is_not_a_completed_zero_and_does_not_drop_other_features():
    backend=Backend();backend.fail=True;obs=extract(backend)
    assert 'structure.village' not in obs['structures']
    assert obs['coverage']['structure.village']['status']=='failed'
    assert obs['structures']['structure.monument']==[[0,0]]
    assert obs['biomes']['nether']
