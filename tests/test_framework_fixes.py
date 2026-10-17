"""Regression coverage for source compatibility, seed domains and finalist search."""
import copy
import json
import random

import pytest

from seed_search.seeds import seed_strided, seeds_strided, validate_sequence_range
from seed_search.realm.native_batch import Prototype, seeds_strided_np, run_native_scan
from seed_search.realm.native_identity import compatible_native_build, native_source_fingerprint
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.dynamic import (grid_candidate_centers, candidate_centers,
    DYNAMIC_V3_CENTROID_WEIGHTS, NETHER_NAMES, overworld_bounds, nether_bounds,
    hub_bonus_v3, nether_core_bonus_v3, weighted_radial_v3)
from seed_search.realm.bounds import contains
from seed_search.realm.blueprint import dynamic_v3_score, evaluate_dynamic_seed


@pytest.mark.parametrize('first,count',[(2**32,1),(2**32-1,2),(-1,1),(0,-1),(True,1)])
def test_strided_range_rejected_at_every_entry(first,count,tmp_path):
    with pytest.raises(ValueError):validate_sequence_range(first,count,'strided')
    with pytest.raises(ValueError):seeds_strided(first,count,12345)
    with pytest.raises(ValueError):seeds_strided_np(first,first+count,12345)
    cfg=dynamic_v3_blueprint_config();cfg['search'].update(sequence='strided',low32=12345)
    with pytest.raises(ValueError):run_native_scan(cfg,tmp_path/'run',count,start_index=first,native_threads=1)
    assert not (tmp_path/'run').exists()


def test_last_strided_sibling_and_empty_end_boundary():
    assert seed_strided(2**32-1,-1)==-1
    with pytest.raises(ValueError):seed_strided(2**32,12345)
    assert seeds_strided(2**32,0,12345)==[]
    assert seeds_strided_np(2**32,2**32,12345).tolist()==[]
    validate_sequence_range(2**32,1,'permutation')


def test_merge_rejects_wrapped_strided_coverage(tmp_path):
    from seed_search.realm.store import RealmStore, index_key
    from scripts.merge_runs import merge_runs
    cfg=dynamic_v3_blueprint_config();cfg['search'].update(sequence='strided',low32=12345)
    source=tmp_path/'source'
    with RealmStore(source,identity={'config':cfg,'native_build':'test-source'}) as store:
        store.configure_range(2**32,2**32+1,1)
        store.claim_range('fixture')
        store.db.execute("UPDATE ranges SET status='complete'")
        store.db.commit()
    with pytest.raises(ValueError,match='32-bit seed domain'):
        merge_runs([source],tmp_path/'merged')


def test_stale_native_rejected_before_loading(current_native_build,tmp_path):
    import shutil
    path=tmp_path/'stale';shutil.copytree(current_native_build,path)
    identity=json.loads((path/'identity.json').read_text())
    identity['extension']=str(path/current_native_build.joinpath(identity['extension']).name)
    identity['inputs']['native/blueprint_dynamic.inc']='0'*64
    (path/'identity.json').write_text(json.dumps(identity))
    assert not compatible_native_build(path)
    with pytest.raises(ValueError,match='Stale native source'):
        Prototype(path,dynamic_v3_blueprint_config())
    p=Prototype(None,dynamic_v3_blueprint_config())
    assert p.ffi.string(p.lib.ss_source_fingerprint()).decode()==native_source_fingerprint()


def test_v3_default_top50_reaches_durable_pipeline(tmp_path):
    cfg=dynamic_v3_blueprint_config()
    cfg['biomes']['required_families']=[]
    cfg['search'].update(sequence='manifest',manifest_seeds=['-3336796033057908633'])
    result=run_native_scan(cfg,tmp_path/'run',1,native_threads=1,retention='survivors')
    assert result['top_k']==50 and result['top_candidates_count']==1
    result_off=run_native_scan(cfg,tmp_path/'off',1,native_threads=1,retention='survivors',top_k=0)
    assert 'top_k' not in result_off
    assert not (tmp_path/'off'/'top50.json').exists()
    with pytest.raises(ValueError,match='capacity cannot change'):
        run_native_scan(cfg,tmp_path/'run',1,native_threads=1,retention='survivors',resume=True,top_k=1)


def test_grid_counts_match_half_open_bruteforce():
    rng=random.Random(20261016)
    inventory={name:[(rng.randrange(-1300,1301),rng.randrange(-1300,1301)) for _ in range(5)]
               for name in ['village','swamp_hut','fortress','bastion']}
    rows=grid_candidate_centers(inventory,{}, {},{},step=16)
    assert len(rows)==15129
    for row in rng.sample(rows,64):
        for name,points in inventory.items():
            bounds=nether_bounds(row.center,512) if name in NETHER_NAMES else overworld_bounds(row.center,1024)
            assert row.counts[name]==sum(contains(p,bounds) for p in points)
    assert len(grid_candidate_centers({}, {}, {},{},step=8))==60025


def test_finalist_grid_recovers_missed_optional_bonus():
    cfg=dynamic_v3_blueprint_config();floors=cfg['structures']['hard_floors']
    inventory={name:[(32,8*(2*i-(n-1))) for i in range(n)] for name,n in floors.items()
               if name not in ('stronghold','fortress','bastion')}
    inventory.update(stronghold=[(992,0)],fortress=[(0,0)],bastion=[(-32,0),(32,0)],
                     swamp_hut=[(-992,0),(1040,0)])
    def key(row):
        structures={name:[p for p in points if contains(p,overworld_bounds(row.center,1024))]
                    for name,points in inventory.items() if name not in NETHER_NAMES}
        score=dynamic_v3_score(row.counts,hub=hub_bonus_v3(structures,row.center),
                               nether_core=nether_core_bonus_v3(inventory,row.center))[0]
        return (-score,weighted_radial_v3(structures,row.center,overworld_half=1024),
                sum(v*v for v in row.center),*row.center)
    reps=candidate_centers(inventory,floors,{},cfg['search']['density_weights'],0,
                          DYNAMIC_V3_CENTROID_WEIGHTS,1024,512)
    full=grid_candidate_centers(inventory,floors,{},cfg['search']['density_weights'])
    best=min(full,key=key)
    assert best.center==(32,0) and -key(best)[0]==105
    assert -key(min(reps,key=key))[0]==90


def test_refinement_rejects_replay_evidence():
    class Replay:
        dynamic_center=(0,0)
        def __enter__(self):return self
        def __exit__(self,*args):pass
    # Bad grid modes reject before any generation or partial evidence is used.
    with pytest.raises(ValueError,match='grid step'):
        evaluate_dynamic_seed(0,0,dynamic_v3_blueprint_config(),center_grid_step=4)
    with pytest.raises(ValueError,match='not native replay'):
        evaluate_dynamic_seed(0,0,dynamic_v3_blueprint_config(),backend_factory=lambda _:Replay(),center_grid_step=16)
