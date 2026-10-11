from collections import namedtuple
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
