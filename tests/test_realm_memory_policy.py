from concurrent.futures import Future
import pytest

from seed_search.realm import runner
from seed_search.realm.config import default_config, validate_config
from seed_search.realm.store import RealmStore


class ImmediatePool:
    """Completed deterministic futures exercise parent bookkeeping without generation."""
    def __init__(self, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def submit(self, function, evaluator, start, end, cfg):
        future = Future()
        results = [{"index": index, "seed": str(runner._seed(index, cfg['search'])),
                    "anchors": [], "counts": {}, "stage_seconds": {}}
                   for index in range(start, end)]
        future.set_result({"results": results, "pid": 1, "wall_seconds": 0.0,
                           "cpu_seconds": 0.0, "worker_peak_rss_bytes": 1})
        return future


def monitoring_available():
    return {'available': True, 'rss_bytes': 1 << 30, 'cpu_percent': 0, 'processes': []}


@pytest.mark.parametrize('field,value',[
    ('docker_reserve_gib', -1), ('docker_reserve_gib', float('nan')),
    ('docker_reserve_gib', float('inf')), ('docker_reserve_gib', float('-inf')),
    ('docker_reserve_gib', True), ('docker_reserve_gib', '8'),
    ('docker_reserve_gib', 30), ('memory_target_gib', float('nan')),
    ('memory_target_gib', float('inf')), ('memory_ceiling_gib', float('nan')),
    ('memory_ceiling_gib', float('inf')), ('memory_ceiling_gib', True),
])
def test_invalid_memory_settings_rejected_before_checkpoint(field, value, tmp_path):
    cfg=default_config()
    cfg['search'][field]=value
    with pytest.raises(ValueError):
        validate_config(cfg)
    with pytest.raises(ValueError):
        runner.run_scan(cfg, tmp_path / 'run', 1)
    assert not (tmp_path / 'run' / 'realm.sqlite').exists()


def test_monitor_unavailable_blocks_initial_dispatch_and_preserves_resume(tmp_path, monkeypatch):
    cfg=default_config()
    cfg['search'].update(workers=2, batch_size=1)
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', ImmediatePool)
    monkeypatch.setattr(runner, 'process_tree_resources', lambda: {'available': False, 'error': 'ps unavailable'})
    with pytest.raises(RuntimeError, match='monitoring unavailable'):
        runner.run_scan(cfg, tmp_path, 5)
    with RealmStore(tmp_path, resume=True) as store:
        assert store.status()['completed_seeds']==0
        assert store.status()['ranges']=={}
        assert store.get_state('next_index')==0
        assert store.status()['worker_statistics']['last_monitor_failure']['error']=='ps unavailable'
        assert store.status()['memory']['available'] is False
    monkeypatch.setattr(runner, 'process_tree_resources', monitoring_available)
    assert runner.run_scan(cfg, tmp_path, 5, resume=True)['completed_seeds']==5


def test_monitor_loss_stops_refill_and_keeps_committed_batches(tmp_path, monkeypatch):
    cfg=default_config()
    cfg['search'].update(workers=2, batch_size=1)
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', ImmediatePool)
    original_wait=runner.wait
    waits=[0]
    def defer_first_completion(futures, **kwargs):
        waits[0]+=1
        if waits[0]==1:
            return set(),set(futures)
        return original_wait(futures, **kwargs)
    monkeypatch.setattr(runner,'wait',defer_first_completion)
    calls=[0]
    def monitor():
        calls[0]+=1
        if calls[0]==1:
            return monitoring_available()
        return {'available': False, 'error': 'monitor lost'}
    monkeypatch.setattr(runner, 'process_tree_resources', monitor)
    with pytest.raises(RuntimeError, match='monitoring unavailable'):
        runner.run_scan(cfg, tmp_path, 5)
    with RealmStore(tmp_path, resume=True) as store:
        assert store.status()['completed_seeds']==2
        assert store.get_state('next_index')==2
        assert store.status()['ranges']=={'complete': 2}
        assert [r['index'] for r in store.iter_results()]==[0,1]
    monkeypatch.setattr(runner, 'process_tree_resources', monitoring_available)
    assert runner.run_scan(cfg, tmp_path, 5, resume=True)['completed_seeds']==5


def test_zero_docker_reserve_and_valid_default_budget(tmp_path, monkeypatch):
    cfg=default_config()
    cfg['search']['docker_reserve_gib']=0
    assert validate_config(cfg) is cfg
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', ImmediatePool)
    monkeypatch.setattr(runner, 'process_tree_resources', monitoring_available)
    state=runner.run_scan(cfg, tmp_path, 1)
    assert state['memory']['docker_reserved_bytes']==0
    assert state['completed_seeds']==1


def test_wrong_returned_seed_leaves_lease_retryable(tmp_path, monkeypatch):
    cfg=default_config()
    cfg['search'].update(workers=1, batch_size=1, sequence='sequential', run_key='0')
    class WrongSeedPool(ImmediatePool):
        def submit(self, *args):
            future=super().submit(*args)
            future.result()['results'][0]['seed']='1'
            return future
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', WrongSeedPool)
    monkeypatch.setattr(runner, 'process_tree_resources', monitoring_available)
    with pytest.raises(ValueError, match='assigned sequence'):
        runner.run_scan(cfg, tmp_path, 2)
    with RealmStore(tmp_path, resume=True) as store:
        assert store.status()['completed_seeds']==0
        assert store.status()['ranges']=={'retry':1}
        assert list(store.iter_results())==[]
        assert list(store.iter_candidates())==[]
    monkeypatch.setattr(runner, 'ProcessPoolExecutor', ImmediatePool)
    assert runner.run_scan(cfg, tmp_path, 2, resume=True)['completed_seeds']==2
