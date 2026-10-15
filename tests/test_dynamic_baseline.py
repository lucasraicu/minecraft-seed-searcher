"""Exact dynamic-center policy and native/reference decision agreement."""
from fractions import Fraction

import numpy as np
import pytest

from scripts.build_blueprint_batch import build
from seed_search.backend import biome_catalog
from seed_search.realm.blueprint import dynamic_score, evaluate_seed
from seed_search.realm.config import dynamic_blueprint_config, validate_config
from seed_search.realm.dynamic import candidate_centers, nether_bounds, overworld_bounds
from seed_search.realm.native_batch import NAMES, Prototype, semantic_record

IDS={row['name']:row['id'] for row in biome_catalog()}


class DynamicFixtureBackend:
    surface=('plains','desert','forest','taiga','jungle','swamp','snowy_plains',
             'dark_forest','jagged_peaks','stony_shore')
    caves=('lush_caves','dripstone_caves','deep_dark')
    def __init__(self,missing=-1,extra_mask=0,depth=1,x=0,z=0,cfg=None):
        self.missing=missing;self.extra_mask=extra_mask;self.depth=depth
        self.x=x;self.z=z;self.cfg=cfg or dynamic_blueprint_config();self.native_work={}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def absent(self,slot):return self.missing==slot or bool(self.extra_mask&(1<<slot))
    def structure_pair(self,name,bounds):
        if name=='stronghold':
            points=[] if self.absent(28) else [(16,0),(32,0)]
            return points,points
        if name in ('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure'):return [],[]
        cfg=self.cfg;slot=NAMES.index(name)
        goal=(cfg['structures']['minimum_counts'].get(name) or
              cfg['structures']['nether_minimum_counts'].get(name))
        n=max(0,goal-self.depth) if self.absent(slot) else goal+2
        points=[(bounds[0]+800+i*16+self.x,bounds[1]+800+self.z) for i in range(n)]
        return points,points
    def igloo_basement(self,x,z):return False
    def nether_structure_pairs(self,bounds):
        return {name:self.structure_pair(name,bounds) for name in ('fortress','bastion')}
    def biome_points(self,points,dimension=0):
        values=[]
        if dimension==-1:
            names=('nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas')
            return np.array([-1 if self.missing==29+(int(x)//64+int(z)//64)%5 else IDS[names[(int(x)//64+int(z)//64)%5]] for x,y,z in points],dtype=np.int32)
        for x,y,z in points:
            if x%64 or z%64:
                name='pale_garden' if self.absent(27) or x==self.x+32 else 'dark_forest'
            else:
                cave=y in (-48,0)
                if self.absent(26):name='dark_forest' if cave else 'lush_caves'
                else:
                    choices=self.caves if cave else self.surface
                    k=(int(x)//64+int(z)//64)%len(choices)
                    family=k+10 if cave else k
                    if self.absent(family+13):values.append(-1);continue
                    name=choices[k]
            values.append(IDS[name])
        return np.array(values,dtype=np.int32)


@pytest.fixture(scope='module')
def native(tmp_path_factory):
    path=tmp_path_factory.mktemp('dynamic-native')
    build(path)
    return Prototype(path,dynamic_blueprint_config())


def test_configurable_ideals_and_fixed_hard_floors():
    cfg=dynamic_blueprint_config();validate_config(cfg)
    assert cfg['deployment']=={'overworld_side_blocks':1664,'nether_side_blocks':832}
    assert cfg['structures']['hard_floors']['mansion']==1
    cfg['structures']['minimum_counts']['village']=8
    cfg['structures']['minimum_counts']['outpost']=3
    cfg['structures']['nether_minimum_counts']['fortress']=3
    validate_config(cfg)
    cfg['structures']['minimum_counts']['village']=7
    with pytest.raises(ValueError,match='floor'):validate_config(cfg)


@pytest.mark.parametrize('center',[(0,0),(1,-1),(-7,7),(-1168,1168)])
def test_fractional_nether_square_contains_exact_integer_blocks(center):
    bounds=nether_bounds(center)
    for axis in (0,1):
        lo=Fraction(center[axis],8)-416
        hi=Fraction(center[axis],8)+416
        assert bounds[axis]==-(-lo.numerator//lo.denominator)
        assert bounds[axis+2]==-(-hi.numerator//hi.denominator)
        assert all((bounds[axis]<=v<bounds[axis+2])==(lo<=v<hi)
                   for v in range(bounds[axis]-1,bounds[axis+2]+1))


def test_critical_cells_choose_nearest_origin_at_equal_density():
    inventories={'stronghold':[(0,0)],'mansion':[(0,0)],'fortress':[(0,0)],
                 'outpost':[(0,0)],'village':[(0,0)]}
    floors={name:1 for name in inventories}
    weights={name:int(name=='village') for name in
             ('village','trial_chamber','ancient_city','desert_pyramid','jungle_temple','outpost')}
    result=candidate_centers(inventories,floors,{},weights)
    assert result[0].center==(0,0)
    assert result[0].density==1
    assert overworld_bounds((1168,1168))== (336,336,2000,2000)


def test_luxury_bonus_matrix_has_no_river_score():
    assert dynamic_score({},('cherry_grove','pale_garden','mangrove_swamp',
                             'badlands','flower_forest','bamboo_jungle','mushroom_fields'))==150
    assert dynamic_score({},('river',))==0


@pytest.mark.parametrize('missing,mask,expected',[
    (-1,0,[]),(0,0,None),(12,0,None),(10,0,None),
    (5,0,['village']),(5,1<<6,['village','trial_chamber']),
    (5,(1<<6)|(1<<4),None),
])
def test_native_python_dynamic_fixture_agreement(native,missing,mask,expected):
    cfg=dynamic_blueprint_config()
    with native.sweep([123],fixtures=[(0,0,missing)],fixture_masks=[mask]) as batch:
        direct=batch.records()[0]
        replay=batch.records(adapter='replay')[0]
        assert semantic_record(direct)==semantic_record(replay)
    reference=evaluate_seed(0,123,cfg,backend_factory=lambda _:DynamicFixtureBackend(missing,mask))
    assert semantic_record(direct)==semantic_record(reference)
    assert len(direct['anchors'])==len(reference['anchors'])==int(expected is not None)
    if expected is not None:
        anchor=direct['anchors'][0];oracle=reference['anchors'][0]
        assert anchor['evaluation_center']==oracle['evaluation_center']==oracle['evaluation_center']
        assert all(value%8==0 for value in anchor['evaluation_center'])
        assert anchor['deficit_categories']==oracle['deficit_categories']==expected
        assert anchor['baseline_score_observed']==oracle['baseline_score_observed']
        assert anchor['bounds']==oracle['bounds']
        assert anchor['predicted_strongholds']==oracle['predicted_strongholds']


def test_strict_ideal_above_floor_never_spends_deficit_budget(native):
    cfg=dynamic_blueprint_config()
    cfg['structures']['minimum_counts']['outpost']=3
    validate_config(cfg)
    strict=Prototype(native.directory,cfg)
    with strict.sweep([1],fixtures=[(0,0,12)],retention='survivors') as batch:
        assert batch.pointer.result_count==0
    reference=evaluate_seed(0,1,cfg,backend_factory=lambda _:DynamicFixtureBackend(12,cfg=cfg))
    assert reference['anchors']==[]


def test_fractional_native_center_and_reference_bounds(native):
    cfg=dynamic_blueprint_config()
    with native.sweep([321],fixtures=[(1,-1,-1)]) as batch:
        direct=batch.records()[0]
    reference=evaluate_seed(0,321,cfg,
        backend_factory=lambda _:DynamicFixtureBackend(x=1,z=-1))
    assert semantic_record(direct)==semantic_record(reference)
    center=direct['anchors'][0]['evaluation_center']
    assert all(value%8==0 for value in center)
    assert direct['anchors'][0]['bounds']['final_nether']==list(nether_bounds(center))
    assert direct['anchors'][0]['bounds']['nether_center_exact']=={
        'x':[center[0],8],'z':[center[1],8]}


@pytest.mark.parametrize('missing',range(29,34))
def test_every_nether_biome_is_required(native,missing):
    with native.sweep([123],fixtures=[(0,0,missing)]) as batch:
        direct=batch.records()[0]
    reference=evaluate_seed(0,123,dynamic_blueprint_config(),backend_factory=lambda _:DynamicFixtureBackend(missing))
    assert direct['anchors']==reference['anchors']==[]


def test_raw_nether_bounds_match_exhaustive_aligned_center_union(native):
    rng=np.random.default_rng(20261014)
    coordinates=np.arange(-1168,1169,8,dtype=np.int32)
    gx,gz=np.meshgrid(coordinates,coordinates)
    for case in range(24):
        fort=rng.integers(-562,562,size=(6,2),dtype=np.int32)
        bast=rng.integers(-562,562,size=(6,2),dtype=np.int32)
        fg=2+case%2;bg=2+(case//2)%2
        def count(points):
            return sum((8*(x-416)<gx)&(gx<=8*(x+416))&(8*(z-416)<gz)&(gz<=8*(z+416)) for x,z in points)
        mask=(count(fort)>=fg)&(count(bast)>=bg)
        f=native.ffi.new('int[]',fort.ravel().tolist());b=native.ffi.new('int[]',bast.ravel().tolist())
        output=native.ffi.new('int[4]')
        status=native.lib.nb_dynamic_raw_bounds(f,6,b,6,fg,bg,output)
        assert status==int(bool(mask.any()))
        if mask.any():assert list(output)==[int(gx[mask].min())-832,int(gz[mask].min())-832,int(gx[mask].max())+831,int(gz[mask].max())+831]


def test_dynamic_rescore_preserves_score_and_rank(native):
    from seed_search.realm.reports import _candidate_rescore
    from copy import deepcopy
    cfg=dynamic_blueprint_config()
    with native.sweep([123],fixtures=[(0,0,-1)]) as batch:original=batch.records()[0]['anchors'][0]
    updated=_candidate_rescore(deepcopy(original),cfg,'test-revision')
    assert updated['baseline_score']==original['baseline_score']
    assert updated['weighted_radial_dist']==original['weighted_radial_dist']
    assert updated['ranking']==original['ranking']


def test_optional_recount_after_snapping():
    from seed_search.realm.blueprint import evaluate_dynamic_seed
    class OptionalBoundaryBackend(DynamicFixtureBackend):
        def structure_pair(self, name, bounds):
            if name == 'swamp_hut': return [(56, -800)], [(56, -800)]
            return super().structure_pair(name, bounds)
    res = evaluate_dynamic_seed(0, 123, dynamic_blueprint_config(),
                                backend_factory=lambda _: OptionalBoundaryBackend())['anchors'][0]
    assert res['evaluation_center'] == [-752, -816]
    assert res['baseline_score'] == 434
    assert res['optional_structures']['swamp_hut']['predicted_viable'] == [[56, -800]]

