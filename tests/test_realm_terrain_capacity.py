"""Scheduler disk-pressure deferral without native generation."""
import pytest
from test_realm_terrain_work import checkpoint, controls, Provider, CFG, IDENTITY
from seed_search.realm.terrain import run_terrain


@pytest.mark.parametrize('failed_sample',[False,True])
def test_capacity_stops_dispatch_and_retains_retryable_closest(tmp_path,monkeypatch,failed_sample):
    controls(monkeypatch)
    store,candidate=checkpoint(tmp_path,count=2)
    provider=Provider()
    if failed_sample:
        original=provider.sample_raster
        def sample(*a,**kw):
            raster=original(*a,**kw);raster.known[:]=False;return raster
        provider.sample_raster=sample
    cfg={**CFG,'terrain':{**CFG['terrain'],'durable_cache_limit_bytes':1,'free_disk_reserve_bytes':0}}
    try:
        result=run_terrain(store,cfg,provider_factory=lambda seed:provider,provider_identity=IDENTITY)
        assert result['resource_blocked'] and len(provider.calls)==1
        assert result['deferred_work']==1 and result['work_completed']==0
        rows=list(store.iter_variants());assert len(rows)==1
        assert 'disk policy' in rows[0]['result']['pending_work'][-1]
        assert list(store.iter_observations())==[]
        unit=next(store.iter_terrain_work(result['pool_revision'],status='deferred'))
        assert unit['status']=='deferred' and unit['result']['state']['capacity_failure']
        assert store.get_candidate(candidate['id'])==candidate
    finally:store.close()
