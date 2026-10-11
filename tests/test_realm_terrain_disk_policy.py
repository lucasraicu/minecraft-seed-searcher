from types import SimpleNamespace
import threading

import pytest

from seed_search.realm import store as module
from seed_search.realm.store import RealmStore, TerrainCapacityError, canonical


def setup(path):
    store = RealmStore(path, {'config': {}})
    store.configure_range(0, 1, 1); store.claim_range('scanner')
    anchor = {'id': '0:1:2', 'seed': '0', 'stronghold': [1, 2], 'qualification': 'PREDICTED'}
    store.complete_range(0, 1, [{'index': 0, 'seed': '0', 'anchors': [anchor], 'counts': {}}])
    revision = store.ensure_terrain_pool({'provider': 'synthetic'})
    return store, revision


def unit(store, revision, resolution=64):
    payload = {'stage': 'height', 'coarse_center': [1, 2], 'resolution': resolution, 'halo_level': 0,
               'raster_bounds': [-64, -64, 64, 64], 'lattice': {'step': resolution}}
    uid = store.ensure_terrain_work(revision, '0:1:2', 'v1', payload)
    return store.claim_terrain_work(uid, 'owner')


def raw(unit):
    payload = unit['payload']
    return {'id': unit['sampling_key'], 'kind': 'terrain_raster', 'bounds': payload['raster_bounds'],
            'resolution': payload['resolution'], 'lattice': payload['lattice'],
            'channels': {'height': [1, 2, 3, 4], 'known': [True] * 4}, 'metadata': {'source': 'prediction'}}


def test_cap_rejects_atomically_preserves_evidence_and_allows_explicit_increase(tmp_path, monkeypatch):
    monkeypatch.setattr(module.shutil, 'disk_usage', lambda path: SimpleNamespace(free=1 << 30))
    store, revision = setup(tmp_path)
    with store:
        current = unit(store, revision); observation = raw(current)
        size = len(canonical(observation).encode())
        store.configure_terrain_disk_policy(limit_bytes=size - 1, free_reserve_bytes=0)
        with pytest.raises(TerrainCapacityError, match='cap reached') as error:
            store.complete_terrain_work(current['unit_id'], observation=observation, result={'geometry_score': 90})
        assert store.get_observation(observation['id']) is None
        assert store.get_terrain_work(current['unit_id'])['status'] == 'leased'
        assert store.terrain_disk_status()['accounted_raster_bytes'] == 0
        store.defer_terrain_work(current['unit_id'], result={'pending': True}, state={'capacity_failure': str(error.value)},
                                 expected_attempt=1, worker='owner')
        assert not store.terrain_work_complete(revision, '0:1:2', 'v1')
        assert 'cap reached' in store.terrain_disk_status()['last_capacity_failure']['reason']
        store.configure_terrain_disk_policy(limit_bytes=size, free_reserve_bytes=0)
        store.claim_terrain_work(current['unit_id'], 'owner')
        assert store.complete_terrain_work(current['unit_id'], observation=observation)
        assert not store.complete_terrain_work(current['unit_id'], observation=observation)
        assert store.terrain_disk_status()['accounted_raster_bytes'] == size
        store.configure_terrain_disk_policy(limit_bytes=0, free_reserve_bytes=0)
        assert store.get_observation(observation['id']) == observation
        assert store.status()['completed_seeds'] == 1


@pytest.mark.parametrize('available', [False, True])
def test_disk_monitor_unavailable_or_reserve_low_fails_closed(tmp_path, monkeypatch, available):
    store, revision = setup(tmp_path)
    with store:
        current = unit(store, revision)
        store.configure_terrain_disk_policy(limit_bytes=1 << 20, free_reserve_bytes=1 << 20)
        def disk(path):
            if not available:
                raise OSError('monitor unavailable')
            return SimpleNamespace(free=100)
        monkeypatch.setattr(module.shutil, 'disk_usage', disk)
        with pytest.raises(TerrainCapacityError, match='reserve reached' if available else 'monitoring unavailable'):
            store.complete_terrain_work(current['unit_id'], observation=raw(current))
        assert store.get_terrain_work(current['unit_id'])['status'] == 'leased'
        assert store.get_observation(current['sampling_key']) is None
        assert store.terrain_disk_status()['accounted_raster_bytes'] == 0


def test_concurrent_projected_bytes_cannot_overcommit_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(module.shutil, 'disk_usage', lambda path: SimpleNamespace(free=1 << 30))
    store, revision = setup(tmp_path)
    units = [unit(store, revision, resolution) for resolution in (64, 32)]
    observations = [raw(current) for current in units]
    cap = max(len(canonical(observation).encode()) for observation in observations)
    store.configure_terrain_disk_policy(cap, 0); store.close()
    start = threading.Barrier(2)
    outcomes = []
    def complete(current, observation):
        try:
            with RealmStore(tmp_path, resume=True) as store:
                start.wait(timeout=5)
                outcomes.append(store.complete_terrain_work(current['unit_id'], observation=observation))
        except BaseException as exc:
            outcomes.append(exc)
    threads = [threading.Thread(target=complete, args=pair) for pair in zip(units, observations)]
    for thread in threads: thread.start()
    for thread in threads: thread.join(5)
    assert all(not thread.is_alive() for thread in threads)
    assert sum(outcome is True for outcome in outcomes) == 1
    assert sum(isinstance(outcome, TerrainCapacityError) for outcome in outcomes) == 1
    with RealmStore(tmp_path, resume=True) as store:
        assert 0 < store.terrain_disk_status()['accounted_raster_bytes'] <= cap
        assert store.terrain_work_counts(revision) == {'complete': 1, 'leased': 1}


def test_legacy_raw_bytes_counted_without_deleting_or_double_counting(tmp_path, monkeypatch):
    monkeypatch.setattr(module.shutil, 'disk_usage', lambda path: SimpleNamespace(free=1 << 30))
    store, revision = setup(tmp_path)
    with store:
        data = {'id': 'historic', 'kind': 'terrain_raster', 'channels': {'data': 'é'}, 'metadata': {'old': True}}
        store.db.execute('INSERT INTO observations VALUES (?,NULL,?)', (data['id'], canonical(data)))
        store.db.commit()
        size = len(canonical(data).encode('utf-8'))
        assert store.configure_terrain_disk_policy(0, 0)['accounted_raster_bytes'] == size
        assert store.configure_terrain_disk_policy(0, 0)['accounted_raster_bytes'] == size
        assert store.get_observation('historic') == data
        for value in (-1, 1.0, True, float('inf')):
            with pytest.raises(ValueError, match='nonnegative integer'):
                store.configure_terrain_disk_policy(value, 0)
        store.db.execute("INSERT INTO meta VALUES ('caller','true')")
        with pytest.raises(ValueError, match='caller transaction'):
            store.configure_terrain_disk_policy(0, 0)
        assert store.db.in_transaction
        store.db.rollback()
