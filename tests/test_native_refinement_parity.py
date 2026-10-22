"""Independent inventory/grid oracle for native finalist optimization."""
import math
import random
import sqlite3

import numpy as np
import pytest

from seed_search.backend import biome_catalog
from seed_search.realm.blueprint import dynamic_v3_score, evaluate_dynamic_seed
from seed_search.realm.bounds import contains
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.dynamic import (PaletteIndex, NETHER_NAMES, OPTIONAL_NAMES,
    overworld_bounds, nether_bounds, hub_bonus_v3, nether_core_bonus_v3,
    weighted_radial_v3, village_spread_bonus_v2, treasure_bastion_bonus_v2,
    SCENIC_BIOMES, RIVER_OFFSETS)
from seed_search.realm.native_batch import Prototype, NAMES, run_native_scan


def make_case(directory=None, *, witness=False):
    """All caches derive from declared complete synthetic evidence, independently."""
    cfg=dynamic_v3_blueprint_config();cfg['biomes']['required_families']=[]
    p=Prototype(directory,cfg);ffi=p.ffi
    ids={row['name']:row['id'] for row in biome_catalog()}
    class Sampler:
        def sample(self,points,dimension=0):
            names=('plains',) if witness else ('plains','river','cherry_grove','badlands','warm_ocean','ice_spikes')
            if dimension==-1:names=tuple(cfg['biomes']['nether_required'])
            return np.array([ids[names[(int(x)//64+3*(int(z)//64))%len(names)]] for x,y,z in points])
    palette=PaletteIndex(Sampler(),cfg['biomes'],v2=True,overworld_half=1024,nether_half=512)
    rng=random.Random(3403)
    inventory={name:[(rng.randrange(-400,401),rng.randrange(-400,401)) for _ in range(n+2)]
               for name,n in cfg['structures']['hard_floors'].items()}
    inventory['fortress']=[(-100,0),(100,0)];inventory['bastion']=[(-32,0),(32,0),(0,64)]
    for name in OPTIONAL_NAMES:inventory[name]=[(rng.randrange(-1600,1601),rng.randrange(-1600,1601)) for _ in range(6)]
    # Exact inclusion/exclusion boundaries in both dimensions.
    inventory['village'] += [(-1024,0),(1024,0),(0,-1024),(0,1024)]
    if witness:
        inventory={name:[(32,8*(2*i-(n-1))) for i in range(n)]
                   for name,n in cfg['structures']['hard_floors'].items()
                   if name not in ('stronghold','fortress','bastion')}
        inventory.update(stronghold=[(992,0)],fortress=[(0,0)],bastion=[(-32,0),(32,0)],
                         swamp_hut=[(-992,0),(1040,0)])
    variants={point:0 if witness else (2 if i==0 else 0) for i,point in enumerate(inventory['bastion'])}
    owned=[]
    def ints(values,kind='int[]'):
        a=ffi.new(kind,list(map(int,values)));owned.append(a);return a
    def points(target,values):
        target.n=len(values);target.xz=ints([v for point in values for v in point]) if values else ffi.NULL
    macro=ffi.new('NBObservation[13]');optional=ffi.new('NBObservation[5]');strong=ffi.new('NBPoints *')
    for i,name in enumerate(NAMES):points(macro[i].viable,inventory.get(name,[]))
    macro[0].mansion_ids=ints([ids['dark_forest']]*macro[0].viable.n)
    for i,name in enumerate(OPTIONAL_NAMES):points(optional[i].viable,inventory.get(name,[]))
    points(strong,inventory['stronghold'])
    prefix=ints(palette.prefix.transpose(0,2,1).ravel());nether=ints(palette.nether.transpose(0,2,1).ravel())
    scenic=np.zeros((64,64),dtype=np.int32)
    for iz in range(63):
        for ix in range(63):
            if palette.surface[iz,ix] not in SCENIC_BIOMES:continue
            rivers=sorted((ix+dx,iz+dz) for dx,dz in RIVER_OFFSETS
                          if 0<=ix+dx<63 and 0<=iz+dz<63 and palette.surface[iz+dz,ix+dx]=='river')
            if rivers:
                rx,rz=rivers[0];scenic[ix+1,iz+1]=0x10000|((rx+1)<<8)|(rz+1)
    villages=inventory['village']
    sep=ints([int((x-xx)**2+(z-zz)**2>=256**2) for x,z in villages for xx,zz in villages],'unsigned char[]')
    inp=ffi.new('NBRefinementInput *');inp.policy=p.policy;inp.macro=macro;inp.optional=optional;inp.strong=strong
    inp.palette_prefix=prefix;inp.nether_prefix=nether;inp.scenic_river=ints(scenic.ravel())
    inp.village_sep=sep;inp.bastion_count=len(variants);inp.bastion_variants=ints(variants.values())
    return p,inp,(owned,macro,optional,strong),inventory,palette,variants


def python_rank(center,inventory,palette,variants,cfg):
    counts={name:sum(contains(point,nether_bounds(center,512) if name in NETHER_NAMES else overworld_bounds(center,1024))
                     for point in points) for name,points in inventory.items()}
    goals={**cfg['structures']['minimum_counts'],**cfg['structures']['nether_minimum_counts']}
    if any(counts.get(name,0)<max(floor,goals.get(name,0)) for name,floor in cfg['structures']['hard_floors'].items()) or not palette.valid(center):return None
    structures={name:[point for point in points if contains(point,overworld_bounds(center,1024))]
                for name,points in inventory.items() if name not in NETHER_NAMES}
    treasure=treasure_bastion_bonus_v2(inventory['bastion'],center,lambda x,z:variants[x,z],512)[0]
    score=dynamic_v3_score(counts,palette.luxuries(center),hub=hub_bonus_v3(structures,center),
        scenic=25 if palette.scenic_pair(center)[0] else 0,
        village_spread=25 if village_spread_bonus_v2(structures['village'],center,1024)[0] else 0,
        treasure_bastion=20 if treasure else 0,optional_counts={name:counts.get(name,0) for name in OPTIONAL_NAMES},
        nether_core=nether_core_bonus_v3(inventory,center))[0]
    radial=weighted_radial_v3(structures,center,overworld_half=1024)
    return (-score,int(math.floor(radial*1e6+0.5)),center[0]**2+center[1]**2,*center)


def native_rank(r):return (-r.score,r.radial_key,r.x*r.x+r.z*r.z,r.x,r.z) if r.found else None


def test_1000_centers_match_independent_python_exactly():
    p,inp,owned,inventory,palette,variants=make_case()
    rng=random.Random(7303)
    centers=[(rng.randrange(-122,123)*8,rng.randrange(-122,123)*8) for _ in range(1000)]
    centers[:5]=[(0,0),(-976,-976),(976,976),(-8,8),(16,-16)]
    coords=p.ffi.new('int[]',[v for center in centers for v in center]);out=p.ffi.new('NBRefinementResult[]',len(centers))
    assert p.lib.nb_dynamic_v3_score_centers(inp,coords,len(centers),out)==0
    valid=0
    for center,result in zip(centers,out):
        expected=python_rank(center,inventory,palette,variants,p.cfg)
        assert native_rank(result)==expected,center
        valid+=expected is not None
    assert valid>100


@pytest.mark.parametrize('step',[16,8,0])
def test_native_grid_recovers_optional_witness(step):
    p,inp,owned,inventory,palette,variants=make_case(witness=True)
    out=p.ffi.new('NBRefinementResult *')
    assert p.lib.nb_dynamic_v3_refine_center(inp,step,1,out)==0
    assert (out.x,out.z,out.score)==(32,0,105)
    assert native_rank(out)==python_rank((32,0),inventory,palette,variants,p.cfg)
    assert out.coarse_points==(60025 if step==8 else 15129)


def test_parallel_grid_determinism(current_native_build):
    p,inp,owned,*_=make_case(current_native_build)
    ranks=[]
    for threads in (1,4,8):
        out=p.ffi.new('NBRefinementResult *')
        assert p.lib.nb_dynamic_v3_refine_center(inp,0,threads,out)==0
        ranks.append((native_rank(out),out.coarse_points,out.fine_points))
    assert ranks[0]==ranks[1]==ranks[2]


def test_native_refinement_rejects_invalid_inputs():
    p,inp,owned,*_=make_case();out=p.ffi.new('NBRefinementResult *')
    assert p.lib.nb_dynamic_v3_refine_center(inp,4,1,out)==-1
    assert p.lib.nb_dynamic_v3_refine_center(inp,16,0,out)==-1
    inp.macro=p.ffi.NULL
    assert p.lib.nb_dynamic_v3_refine_center(inp,16,1,out)==-1


def test_production_refinement_persists_and_resumes(tmp_path):
    cfg=dynamic_v3_blueprint_config();cfg['biomes']['required_families']=[]
    seed='-3336796033057908633';cfg['search'].update(sequence='manifest',manifest_seeds=[seed])
    run=tmp_path/'refined'
    status=run_native_scan(cfg,run,1,native_threads=1,retention='survivors')
    import json
    with sqlite3.connect(run/'realm.sqlite') as db:
        a=json.loads(db.execute('select result from candidates').fetchone()[0])
    original=evaluate_dynamic_seed(0,seed,cfg)['anchors'][0]
    assert a['centroid_unrefined']==original['evaluation_center']
    assert a['sweep_centroid']['score']==original['baseline_score_observed']
    assert a['refined_center']==a['evaluation_center']
    assert a['refinement_gain']==a['baseline_score_observed']-original['baseline_score_observed']>=0
    assert a['center_selection']['coarse_points']==15129
    assert a['center_selection']['global_8_grid_optimum'] is False
    assert status['top_candidates_count']==1
    resumed=run_native_scan(cfg,run,1,native_threads=1,retention='survivors',resume=True)
    assert resumed['execution']['newly_committed']==0


def test_full_coarse_optimum_matches_independent_python():
    p,inp,owned,inventory,palette,variants=make_case(witness=True)
    # Compare the complete admissible chunk grid, including all rejected points.
    expected=min(rank for x in range(-976,977,16) for z in range(-976,977,16)
                 if (rank:=python_rank((x,z),inventory,palette,variants,p.cfg)) is not None)
    out=p.ffi.new('NBRefinementResult *')
    assert p.lib.nb_dynamic_v3_refine_center(inp,16,1,out)==0
    assert native_rank(out)==expected


def test_hierarchical_scope_is_bounded_by_complete_grids():
    p,inp,owned,*_=make_case();ranks={}
    for step in (16,0,8):
        out=p.ffi.new('NBRefinementResult *')
        assert p.lib.nb_dynamic_v3_refine_center(inp,step,1,out)==0
        ranks[step]=native_rank(out)
    assert ranks[8]<=ranks[0]<=ranks[16]


def test_floor_and_palette_failures_do_not_produce_centers():
    p,inp,owned,*_=make_case();out=p.ffi.new('NBRefinementResult *')
    inp.strong.n=0
    assert p.lib.nb_dynamic_v3_refine_center(inp,16,1,out)==0 and not out.found
    inp.strong.n=3  # make_case uses floor one plus two.
    p.policy.required_biome_mask=8191
    # Synthetic surface lacks several mandatory families, unlike empty policy.
    assert p.lib.nb_dynamic_v3_refine_center(inp,16,1,out)==0 and not out.found


def test_refined_sweep_applies_cutoff_and_retains_provenance():
    p=Prototype(None,dynamic_v3_blueprint_config())
    for cutoff,retained in ((484,1),(485,0)):
        with p.sweep([456],fixtures=[(200,200,-1)],retention='survivors',
                     refine_centers=True,cutoff_score=cutoff) as batch:
            assert batch.pointer.result_count==retained
            if retained:
                record=batch.retained_records()[0];a=record['anchors'][0]
                assert a['baseline_score_observed']==484
                assert a['centroid_unrefined']==[-768,-960]
                assert a['refined_center']==[-776,-976]
                assert a['refinement_gain']==0
                assert a['grid_step']==8
                assert a['center_selection']['fine_points']>0


def test_count_raster_respects_filtered_mansions_and_custom_goals():
    p,inp,owned,inventory,palette,variants=make_case()
    inp.macro[0].mansion_ids[0]=p.policy.pale_id
    inventory['mansion']=inventory['mansion'][1:]
    coords=p.ffi.new('int[]',[0,0,-8,8]);out=p.ffi.new('NBRefinementResult[2]')
    assert p.lib.nb_dynamic_v3_score_centers(inp,coords,2,out)==0
    assert native_rank(out[0])==python_rank((0,0),inventory,palette,variants,p.cfg)
    assert native_rank(out[1])==python_rank((-8,8),inventory,palette,variants,p.cfg)
    p.policy.goals[5]=64
    result=p.ffi.new('NBRefinementResult *')
    assert p.lib.nb_dynamic_v3_refine_center(inp,16,1,result)==0
    assert not result.found
