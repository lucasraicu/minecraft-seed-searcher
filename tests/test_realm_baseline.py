import copy
import pytest
from seed_search.realm.config import default_config, validate_config
from seed_search.realm.bounds import square, contains, native_bounds, nether_square, border_fit
from seed_search.realm.biomes import classify, variant_fit
from seed_search.realm.baseline import evaluate_seed


def test_half_open_unclipped_and_fractional_nether():
    assert square((0,0),4000)==(-2000,-2000,2000,2000)
    anchor=(1999,-1999);b=square(anchor,1536)
    assert b==(1231,-2767,2767,-1231)
    assert contains((b[0],b[1]),b) and not contains((b[2],b[1]),b)
    for anchor in ((-1,-9),(7,15),(1999,-1999)):
        n=nether_square(anchor)
        assert n[2]-n[0]==896 and n[3]-n[1]==896
        nb=native_bounds(n)
        for x in (nb[0]-1,nb[0],nb[2],nb[2]+1):
            assert contains((x,nb[1]),n)==(anchor[0]-3584<=8*x<anchor[0]+3584)


def test_families_bonuses_and_neutral_savanna():
    p=default_config()['biomes']
    a=classify(['forest','birch_forest','flower_forest'],p)
    assert a['wooded_family_count']==1 and a['qualification']=='PENDING'
    names=['forest','taiga','jungle','pale_garden','cherry_grove']
    for count in (2,3,4,5):
        r=classify(names[:count],p)
        assert r['wooded_bonus']==5*(count-2) and r['qualification']=='PREDICTED'
        neutral=classify(names[:count]+['savanna','savanna_plateau','windswept_savanna'],p)
        assert r['score']==neutral['score'] and r['qualification']==neutral['qualification']
        for v in ('v1','v2'):assert variant_fit(names[:count],v)==variant_fit(neutral['raw_names'],v)
    r=classify(['forest','taiga','swamp','mangrove_swamp','warm_ocean','ocean'],p)
    assert r['family_bonuses']=={'ocean':2,'swamp':3}
    assert r['variant_bonuses']=={'mangrove_swamp':3,'warm_ocean':3}
    assert classify(['forest','taiga'],p)['qualification']=='PREDICTED'
    assert classify(['forest'],p,complete=True,verified=True)['qualification']=='FAILED'


class FakeBackend:
    def __init__(self,seed):self.seed=seed;self.native_work={}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def structure_pair(self,name,bounds):
        if name=='stronghold':p=[[-1999,-1999],[1999,1999]]
        else:p=[[bounds[0],bounds[1]]]
        return p,p
    def biome_points(self,points):
        from seed_search.backend import biome_name
        import numpy as np
        ids={biome_name(i):i for i in range(256)}
        return np.resize([ids['forest'],ids['taiga']],len(points))


def test_independent_anchors_required_and_optional_unsupported():
    cfg=default_config();cfg['search']['inventory_mode']='complete'
    r=evaluate_seed(0,-2**63,cfg,backend_factory=FakeBackend)
    assert len(r['anchors'])==2 and r['counts']['baseline_predicted']==2
    assert len({a['id'] for a in r['anchors']})==2
    for a in r['anchors']:
        assert set(a['required_structures'])==set(cfg['structures']['required'])
        assert a['optional_structures']['monster_room']['data_status']=='UNSUPPORTED'
        assert a['optional_structures']['monster_room']['bonus']==0
        assert a['qualification']=='PREDICTED'


def test_unknown_not_absent_and_no_cave_queries():
    class Missing(FakeBackend):
        def structure_pair(self,name,bounds):
            if name=='ancient_city':return [],[]
            return super().structure_pair(name,bounds)
        def biome_points(self,points):
            assert all(p[1]==63 for p in points)
            return super().biome_points(points)
    r=evaluate_seed(1,1,default_config(),backend_factory=Missing)
    assert r['counts']['confirmed_rejections']==0
    for a in r['anchors']:
        assert a['qualification']=='PENDING'
        assert not a['required_structures']['ancient_city']['confirmed_absent']


def test_border_overflow_retained():
    assert border_fit((-100,-100,100,100),(1,1))['status']=='within'
    r=border_fit((-1400,-100,100,100),(0,0))
    assert r['status']=='outside' and r['minimum_side_blocks']==2800 and r['overflow']['west']==632
    assert border_fit((-100,-100,100,100),(0,0),complete=False)['status']=='unknown'


@pytest.mark.parametrize('section,key,value',[
    ('deployment','overworld_side_blocks',2304),('search','workers',37),
    ('caves','automatic',True),('game','backend_model','MC_26_52'),('terrain','variants',['v1','v2','v3'])])
def test_config_rejects_silent_contract_changes(section,key,value):
    cfg=default_config();cfg[section][key]=value
    with pytest.raises(ValueError):validate_config(cfg)
