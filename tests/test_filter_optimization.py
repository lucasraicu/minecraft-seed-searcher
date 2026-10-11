import copy
import numpy as np
import pytest
from seed_search.backend import Backend, STRUCTURES, RAW_MT_TYPES, _RAW_LAYOUTS
from seed_search.config import load_config
from seed_search.landscapes import (analyze_landscapes, flat_metrics, build_centers,
    ring_metrics, raster_intermediates, basin_necessary_bound, xy_raster)
from seed_search.terrain import raster
from seed_search.structures import possible_required_centers


@pytest.mark.parametrize('seed',[-1,0,12345,4294979641])
def test_combined_scan_preserves_every_supported_family(seed):
    with Backend(seed) as b:
        for name in STRUCTURES:
            bounds=(-6504,-6504,6504,6504) if name=='stronghold' else (-900,-1100,1000,1200)
            assert b.structure_pair(name,bounds)==(b.structures(name,bounds,False),b.structures(name,bounds))


def test_raw_cache_reuses_only_verified_mt_layouts_and_full_seed_viability():
    _RAW_LAYOUTS.clear();bounds=(-1024,-1024,1024,1024)
    for name in RAW_MT_TYPES:
        with Backend(-1,2) as b:raw,_=b.structure_pair(name,bounds)
        with Backend(4294967295,2) as other:
            expected=other.structures(name,bounds)
            # If the second raw enumeration happens, this experiment fails.
            other.structures=lambda *_:pytest.fail('Expected exact raw layout cache hit')
            assert other.structure_pair(name,bounds)==(raw,expected)
    with Backend(12345,2) as b:
        first=b.structure_pair('trial_chamber',bounds)[0]
    with Backend(12345+(1<<32),2) as b:
        assert b.structure_pair('trial_chamber',bounds)[0]!=first
    assert len(_RAW_LAYOUTS)<=2
    with pytest.raises(RuntimeError):b.structure_pair('village',bounds)


def test_joint_required_center_intersection_and_exact_negative_border():
    cfg,_=load_config();scans={'stronghold':{'raw':[(-5000,0)]},'fortress':{'raw':[(800,0)]}}
    assert not possible_required_centers(scans,cfg,(-5000,-5000,5000,5000))
    half=cfg['deployment']['overworld_side_blocks']//2;nh=cfg['deployment']['nether_side_blocks']//2
    scans={'stronghold':{'raw':[(-half,-half)]},'fortress':{'raw':[(-nh,-nh)]}}
    assert possible_required_centers(scans,cfg,(0,0,0,0))
    scans['stronghold']['raw']=[(-half-1,-half)]
    assert not possible_required_centers(scans,cfg,(0,0,0,0))
    # Integer ranges can overlap while containing no allowed eight-block center.
    scans['stronghold']['raw']=[(half+1,half+1)]
    assert not possible_required_centers(scans,cfg,(1,1,7,7))


def test_missing_stronghold_fast_path_defers_before_any_terrain(monkeypatch):
    cfg,_=load_config();cfg['optimization']['exact_per_seed_cache']=False
    class EmptyBackend:
        def __init__(self,*_):pass
        def __enter__(self):return self
        def __exit__(self,*_):pass
        def structure_pair(self,name,bounds):assert name=='stronghold';return [],[]
        def grid(self,*_):pytest.fail('Fast deferred seed must not generate terrain')
    monkeypatch.setattr('seed_search.landscapes.Backend',EmptyBackend)
    r=analyze_landscapes((3,12345,cfg))
    assert r['candidates']==[] and r['counts']['discovery_points']==0
    assert r['near_misses'][0]['reason']=='deferred_seed_no_joint_required_prediction'
    assert r['near_misses'][0]['stronghold_completeness']=='unknown'


class Ground:
    def __init__(self,kind):self.kind=kind
    def heights(self,points,vertical_step=8):
        p=np.asarray(points);x,z=p[:,0],p[:,1];r=np.hypot(x,z)
        h=np.full(len(p),72,dtype=np.int32)
        if self.kind=='water':h[:]=50
        if self.kind=='ring':h[(r>=300)&(r<=400)]=160
        if self.kind=='recenter':
            h=72+(x%64).astype(np.int32)
            h[np.hypot(x-192,z)<=112]=72
            h[(np.hypot(x-192,z)>=300)&(np.hypot(x-192,z)<=400)]=160
            h[r<=64]=50
        return h,np.ones(len(p),np.int32)


@pytest.mark.parametrize('kind',['water','plain','ring','recenter'])
def test_basin_impossibility_bound_never_vetoes_reference_survivor(kind):
    cfg,_=load_config();cfg['landscapes']['ring_radius_blocks']=500
    backend=Ground(kind);center=[0,0];s=cfg['landscapes']
    full=raster(backend,(-1504,-1504,1504,1504),16);context=raster_intermediates(full)
    x,z=xy_raster(full)
    centers=[center]+[site['center'] for site in build_centers(full,np.hypot(x,z)<=256,[-5000,5000],8,context)]
    passes=[]
    for c in centers:
        f,_,connected=flat_metrics(full,c,s,context)
        rr=ring_metrics(full,c,s,connected,f['inner_height_median'])
        passes.append(f['flat_ground_preference_met'] and rr['dry_mountain_basin_preference_met'])
    bound=basin_necessary_bound(backend,center,cfg)
    if kind in ('ring','recenter'):assert any(passes), 'Positive control must actually survive the reference'
    if any(passes):assert not bound['impossible']
    if kind=='water':assert bound['impossible'] and bound['reason']=='dry_or_gentle_upper_bound'
    assert bound['points']<full['points']


def test_shared_raster_intermediates_preserve_negative_off_lattice_recenters():
    cfg,_=load_config();terrain=raster(Ground('recenter'),(-1512,-1480,1496,1528),16)
    context=raster_intermediates(terrain)
    for c in [(-8,24),(184,24),(-256,-200)]:
        fresh=flat_metrics(terrain,c,cfg['landscapes']);shared=flat_metrics(terrain,c,cfg['landscapes'],context)
        assert fresh[0]==shared[0]
        assert all(np.array_equal(a,b) for a,b in zip(fresh[1:],shared[1:]))
    allowed=np.hypot(context['x']+8,context['z']-24)<=256
    assert build_centers(terrain,allowed,[-5000,5000],8)==build_centers(terrain,allowed,[-5000,5000],8,context)


def test_rejected_rounding_patch_is_not_installed():
    with Backend(9) as b:
        assert b.structures('stronghold',(-920,630,-890,660))==[(-908,644)]
