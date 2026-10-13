"""Diagnostic timings survive discard and never alter semantic decisions."""
import pytest
from scripts.build_blueprint_batch import build
from scripts.profile_native_stages import measured,merge,summarize
from seed_search.realm.native_batch import Prototype
from seed_search.realm.config import blueprint_config
from test_blueprint_batch_prototype import prototype


@pytest.fixture(scope='module')
def profiled(tmp_path_factory):
    path=tmp_path_factory.mktemp('profiled-native')
    build(path,profile=True)
    return Prototype(path,blueprint_config())


@pytest.mark.parametrize('complete',[False,True])
def test_profiles_keep_full64_and_all_evidence_parity(prototype,profiled,complete):
    seeds=[0,-1,-2**63,12345+(1<<32)]
    plain=measured(prototype,seeds,1,complete=complete)
    timing=measured(profiled,seeds,1,complete=complete,profile=True)
    assert timing['fingerprint']==plain['fingerprint']
    assert timing['raw_timings']['stages']['stronghold']['count']==len(seeds)
    assert timing['raw_timings']['stages']['structure_mansion']['count']>0
    for values in timing['raw_timings'].values():
        for stats in values.values():
            assert sum(stats['bins'])==stats['count']
            assert stats['max_seconds']>=stats['min_seconds']>=0
    if complete:
        assert timing['raw_timings']['stages']['isolated_inventory_fortress']['count']>0
        assert timing['raw_timings']['stages']['ranking_inventory_outpost']['count']>0
        assert len(timing['raw_timings']['biome_y'])==4
        assert timing['logical_palette_samples']>=timing['unique_palette_coordinates_within_seed']
    else:
        assert timing['retained_inputs']==0


def test_profile_capacity_and_error_cleanup(profiled):
    ffi=profiled.ffi;lib=profiled.lib
    values=ffi.new('uint64_t[]',[0]*513)
    assert lib.nb_profile_sweep(values,513,profiled.policy,1)==ffi.NULL
    calls=[]
    class Corrupt:
        def nb_profile_sweep(self,*args):
            result=lib.nb_profile_sweep(*args);result.samples[0].seed^=1;return result
        def nb_profile_free(self,handle):calls.append(1);lib.nb_profile_free(handle)
    profiled.lib=Corrupt()
    try:
        with pytest.raises(RuntimeError,match='identity'):measured(profiled,[0],1,profile=True)
        assert calls==[1]
    finally:profiled.lib=lib


def test_histogram_merging_counts_entered_calls_only():
    values={'count':100,'bins':[0]*32,'total_seconds':.0000004,'min_seconds':4e-9,'max_seconds':4e-9,'max_seed':'0','max_coordinate':[1,63,2]}
    values['bins'][2]=100
    target={};merge(target,values);merge(target,values)
    summary=summarize(target)
    assert summary['count']==200
    assert summary['p99_seconds_bounds']==[4e-9,8e-9]
    assert summary['mean_seconds']==pytest.approx(4e-9)
    assert summarize({})['status']=='not reached'


def test_locked_natural_near_miss_profile_uses_existing_semantic_metric_exclusions(prototype,profiled):
    from seed_search.realm.config import locked_blueprint_config
    normal=Prototype(prototype.directory,locked_blueprint_config())
    timing=Prototype(profiled.directory,locked_blueprint_config())
    seeds=[4778609107263059373]
    plain=measured(normal,seeds,1)
    instrumented=measured(timing,seeds,1,profile=True)
    assert plain['retained_inputs']==instrumented['retained_inputs']==1
    assert plain['fingerprint']==instrumented['fingerprint']
