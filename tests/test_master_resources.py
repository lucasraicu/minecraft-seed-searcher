import pytest
from seed_search.realm.resources import disk_policy,disk_status,workspace_usage,WorkspaceCapacityError
from seed_search.realm import runner
from seed_search.realm.config import default_config
from seed_search.realm.store import RealmStore
from test_realm_memory_policy import ImmediatePool,monitoring_available


def test_workspace_counts_wal_exports_snapshots_and_not_links(tmp_path):
    for name,n in [('realm.sqlite',10),('realm.sqlite-wal',20),('export/report.json',30),('bds/snapshot',40)]:
        p=tmp_path/name;p.parent.mkdir(exist_ok=True);p.write_bytes(b'x'*n)
    (tmp_path/'external').symlink_to('/tmp')
    assert workspace_usage(tmp_path)==100


def test_physical_cap_and_projection_are_distinct(tmp_path):
    (tmp_path/'data').write_bytes(b'x'*100)
    policy={'run_disk_limit_bytes':1000,'free_disk_reserve_bytes':1,'projected_bytes_per_seed':100}
    assert disk_status(tmp_path,policy,remaining_seeds=8)['projected_run_bytes']==900
    with pytest.raises(WorkspaceCapacityError,match='Projected'):disk_status(tmp_path,policy,remaining_seeds=10)
    with pytest.raises(WorkspaceCapacityError,match='cap'):disk_status(tmp_path,policy,additional_bytes=901)


def test_disk_failure_keeps_scan_coverage_retryable(tmp_path,monkeypatch):
    cfg=default_config();cfg['search'].update(workers=1,batch_size=1,run_disk_limit_bytes=1)
    monkeypatch.setattr(runner,'ProcessPoolExecutor',ImmediatePool)
    monkeypatch.setattr(runner,'process_tree_resources',monitoring_available)
    with pytest.raises(WorkspaceCapacityError):runner.run_scan(cfg,tmp_path,5)
    with RealmStore(tmp_path,resume=True) as store:
        assert store.status()['completed_seeds']==0
        assert store.get_state('next_index')==0
        assert store.get_state('workspace_disk_failure')


def test_memory_target_stops_dispatch_after_drain(tmp_path,monkeypatch):
    cfg=default_config();cfg['search'].update(workers=1,batch_size=1)
    monkeypatch.setattr(runner,'ProcessPoolExecutor',ImmediatePool)
    monkeypatch.setattr(runner,'process_tree_resources',lambda:{**monitoring_available(),'rss_bytes':18<<30})
    with pytest.raises(RuntimeError,match='working target'):runner.run_scan(cfg,tmp_path,5)
    with RealmStore(tmp_path,resume=True) as store:assert store.status()['completed_seeds']==0


def test_startup_and_shrinking_wal_do_not_inflate_large_shard(tmp_path):
    wal=tmp_path/'realm.sqlite-wal';wal.write_bytes(b'x'*1000000)
    policy=disk_policy({'run_disk_limit_bytes':64<<20,'free_disk_reserve_bytes':1},retention='survivors')
    first=disk_status(tmp_path,policy,remaining_seeds=1000000)
    assert first['initial_completed_seeds']==0
    wal.write_bytes(b'x'*900000)
    sample=disk_status(tmp_path,policy,completed_seeds=1000,remaining_seeds=999000)
    assert sample['bytes_per_seed_estimate']==32
    assert sample['projected_run_bytes']==900000+999000*32
    # Excluding fixed bytes from marginal growth must never bypass physical caps.
    with pytest.raises(WorkspaceCapacityError,match='cap'):
        disk_status(tmp_path,policy,additional_bytes=64<<20)


def test_resume_restores_paired_baseline_and_observed_growth(tmp_path):
    data=tmp_path/'data';data.write_bytes(b'x'*1000000)
    search={'run_disk_limit_bytes':1<<30,'free_disk_reserve_bytes':1}
    initial=disk_status(tmp_path,disk_policy(search,retention='survivors'))
    data.write_bytes(b'x'*1200000)
    resumed=disk_status(tmp_path,disk_policy(search,retention='survivors'),
        completed_seeds=1000,remaining_seeds=1000,previous_sample=initial)
    assert resumed['initial_used_bytes']==1000000
    assert resumed['initial_completed_seeds']==0
    assert resumed['bytes_per_seed_estimate']==300


@pytest.mark.parametrize('previous',[None,{'initial_used_bytes':1000000},
    {'initial_used_bytes':True,'initial_completed_seeds':0},
    {'initial_used_bytes':1000000,'initial_completed_seeds':2000}])
def test_legacy_resume_starts_new_paired_observation_interval(tmp_path,previous):
    data=tmp_path/'data';data.write_bytes(b'x'*1000000)
    policy=disk_policy({'run_disk_limit_bytes':1<<30,'free_disk_reserve_bytes':1},retention='survivors')
    first=disk_status(tmp_path,policy,completed_seeds=1000,previous_sample=previous)
    assert first['bytes_per_seed_estimate']==32
    assert first['initial_completed_seeds']==1000
    data.write_bytes(b'x'*1012800)
    sample=disk_status(tmp_path,policy,completed_seeds=1128)
    assert sample['bytes_per_seed_estimate']==150  # 12,800 bytes / 128 NEW inputs × 1.5


def test_python_scan_persists_disk_baseline_across_resume(tmp_path,monkeypatch):
    cfg=default_config();cfg['search'].update(workers=1,batch_size=1)
    monkeypatch.setattr(runner,'ProcessPoolExecutor',ImmediatePool)
    monkeypatch.setattr(runner,'process_tree_resources',monitoring_available)
    runner.run_scan(cfg,tmp_path,4,stop_after=2)
    with RealmStore(tmp_path,resume=True) as store:
        first=store.get_state('workspace_disk')
        assert first['initial_completed_seeds']==0
        assert store.status()['completed_seeds']==2
    runner.run_scan(cfg,tmp_path,4,resume=True)
    with RealmStore(tmp_path,resume=True) as store:
        last=store.get_state('workspace_disk')
        assert (last['initial_used_bytes'],last['initial_completed_seeds'])==(first['initial_used_bytes'],0)
        assert store.status()['completed_seeds']==4
