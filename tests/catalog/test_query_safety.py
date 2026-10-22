import copy
import pytest
from seed_search.catalog.codec import layout_id,MISSING
from seed_search.catalog.models import SUMMARY_REVISION,empty_observation,identity,observation_id,world_id
from seed_search.catalog.query import search


def fixture():
    obs=empty_observation(identity(0,model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64))
    oid=observation_id(obs)
    row={'revision':SUMMARY_REVISION,'observation_id':oid,'world_id':world_id(obs['identity']),
        'layout_id':layout_id(oid,[0,0],2048),'seed':'0','anchor':[0,0],'border_side':2048,
        'counts':[[0]*4 for _ in range(14)],'structure_nearest_d2':[MISSING]*14,
        'biome_nearest_d2':[MISSING]*9,'biome_witness_refs':[MISSING]*9,
        'complete':[[False]*4 for _ in range(23)]}
    req={'request_revision':'catalog-query-v1','edition':'bedrock','game_build_id':'research:MC_26_50',
        'catalog_snapshot_id':'test','world_settings_id':'default','dimension':'overworld',
        'anchor_mode':'recommended','border_side':2048,'evidence_policy':'predicted_observations_v1',
        'fallback_profile':'balanced_survival','rows':[]}
    return obs,row,req


def test_partial_positive_cannot_pass_required():
    _,row,req=fixture();row['counts'][0]=[3]*4;row['structure_nearest_d2'][0]=0
    req['rows']=[{'rule':'required','kind':'structure_count','feature':'structure.village',
        'at_least':3,'scope':{'kind':'near_base','radius':512}}]
    assert search([row],req,snapshot_id='test')==[]


def test_unknown_preferred_has_zero_observed_utility():
    _,row,req=fixture();row['counts'][0]=[3]*4;row['structure_nearest_d2'][0]=0
    req['rows']=[{'rule':'preferred','importance':5,'kind':'structure_count','feature':'structure.village',
        'at_least':3,'scope':{'kind':'near_base','radius':512}}]
    result=search([row],req,snapshot_id='test')
    assert result[0]['score']==0
    assert result[0]['contributions'][0]['status']=='unknown'


def test_unknown_biome_witness_cannot_pass_required():
    _,row,req=fixture();row['biome_nearest_d2'][0]=0;row['biome_witness_refs'][0]=0
    req['rows']=[{'rule':'required','kind':'biome_witness','any_of':['biome.cherry_grove'],
        'scope':{'kind':'near_base','radius':256}}]
    assert search([row],req,snapshot_id='test')==[]


def test_limit_and_build_identity_must_be_checked():
    obs,row,req=fixture()
    for bad in (True,-1,1.5,1000000):
        with pytest.raises(ValueError): search([row],req,snapshot_id='test',limit=bad)
    bad=copy.deepcopy(obs);bad['identity']['model_id']='different'
    with pytest.raises(ValueError): search([row],req,snapshot_id='test',observations=[bad])


def test_layout_seed_must_match_observation_identity():
    obs,row,req=fixture();row['seed']='1'
    with pytest.raises(ValueError): search([row],req,snapshot_id='test',observations=[obs])
