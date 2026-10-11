import copy
import sqlite3

import pytest

from seed_search.realm.store import RealmStore


def candidate(index):
    return {'id': f'{index}:1:2', 'seed': str(index), 'stronghold': [1, 2], 'qualification': 'PREDICTED'}


def commit_seed(store, index):
    assert store.claim_range('scanner') == (index, index + 1)
    store.complete_range(index, index + 1, [{'index': index, 'seed': str(index), 'anchors': [candidate(index)], 'counts': {}}])


def setup_store(path):
    store = RealmStore(path, {'config': {}})
    store.configure_range(0, 3, 1)
    commit_seed(store, 0)
    revision = store.ensure_terrain_pool({'provider': 'synthetic-v1'})
    return store, revision


def payload(resolution=64, center=(1, 2), priority=0):
    return {'stage': 'height', 'coarse_center': list(center), 'center': list(center),
            'resolution': resolution, 'halo_level': 0, 'raster_bounds': [-64, -64, 64, 64],
            'lattice': {'x0': -64, 'z0': -64, 'step': resolution, 'shape': [2, 2]},
            'priority': priority, 'nearby_centers': [list(center)]}


def observation(unit):
    p = unit['payload']
    return {'id': unit['sampling_key'], 'bounds': p['raster_bounds'], 'resolution': p['resolution'],
            'lattice': p['lattice'], 'channels': {'encoding': 'synthetic', 'height': [1, 2, 3, 4], 'known': [True] * 4},
            'metadata': {'source': 'prediction'}}


def test_shared_pool_is_fixed_until_explicit_refresh(tmp_path):
    store, revision = setup_store(tmp_path)
    with store:
        commit_seed(store, 1)
        assert store.ensure_terrain_pool({'provider': 'synthetic-v1'}) == revision
        assert [r['id'] for r in store.iter_terrain_pool_candidates(revision, batch_size=1)] == ['0:1:2']
        assert store.get_terrain_pool(revision)['members'] == 1
        assert store.terrain_pool_uninitialized_counts(revision) == {'v1': 1, 'v2': 1}
        store.ensure_terrain_work(revision, '0:1:2', 'v1', payload())
        store.ensure_terrain_work(revision, '0:1:2', 'v1', payload(32))
        assert store.terrain_pool_uninitialized_counts(revision) == {'v1': 0, 'v2': 1}
        plan = ' '.join(str(r) for r in store.db.execute('EXPLAIN QUERY PLAN SELECT count(DISTINCT candidate_id) FROM terrain_work WHERE revision=? AND variant=?', (revision, 'v1')))
        assert 'COVERING INDEX terrain_work_pool_variant' in plan
        assert 'TEMP B-TREE' not in plan
        refreshed = store.ensure_terrain_pool({'provider': 'synthetic-v1'}, new_revision=True)
        assert refreshed != revision
        assert store.terrain_pool_uninitialized_counts(refreshed) == {'v1': 2, 'v2': 2}
        assert [r['id'] for r in store.iter_terrain_pool_candidates(refreshed)] == ['0:1:2', '1:1:2']
        assert [r['id'] for r in store.iter_terrain_pool_candidates(revision)] == ['0:1:2']
        with pytest.raises(ValueError, match='provider/algorithm'):
            store.ensure_terrain_pool({'provider': 'stale-v0'}, new_revision=True)


def test_work_keys_share_sampling_but_preserve_independent_variants(tmp_path):
    store, revision = setup_store(tmp_path)
    with store:
        first = store.ensure_terrain_work(revision, '0:1:2', 'v1', payload(priority=5))
        second = store.ensure_terrain_work(revision, '0:1:2', 'v2', payload(priority=1))
        assert first != second
        assert store.get_terrain_work(first)['sampling_key'] == store.get_terrain_work(second)['sampling_key']
        assert store.ensure_terrain_work(revision, '0:1:2', 'v1', payload(priority=5)) == first
        scoped_payload = {**payload(priority=1), 'sampling_scope': 'actual:v2:height'}
        scoped = store.ensure_terrain_work(revision, '0:1:2', 'v2', scoped_payload)
        assert store.get_terrain_work(scoped)['sampling_key'] != store.get_terrain_work(second)['sampling_key']
        with pytest.raises(ValueError, match='immutable payload'):
            store.ensure_terrain_work(revision, '0:1:2', 'v1', payload(priority=6))
        assert [u['unit_id'] for u in store.iter_terrain_work(revision, variant='v1', batch_size=1)] == [first]
        assert {u['unit_id'] for u in store.iter_terrain_work(revision, variant='v2', batch_size=1)} == {second, scoped}
        with pytest.raises(ValueError, match='frozen pool'):
            store.ensure_terrain_work(revision, 'missing', 'v1', payload())


def test_checkpoint_commits_observation_result_state_and_successors_atomically(tmp_path):
    store, revision = setup_store(tmp_path)
    uid = store.ensure_terrain_work(revision, '0:1:2', 'v1', payload())
    unit = store.claim_terrain_work(uid, 'first-owner')
    data = observation(unit)
    successor = {'payload': payload(32), 'status': 'deferred'}
    variant = {'candidate_id': '0:1:2', 'variant': 'v1', 'center': [1, 2], 'result': {'geometry_score': 80}}
    args = {'result': {'center': [1, 2]}, 'observation': data, 'state': {'next_resolution': 32},
            'successor_units': [successor], 'variant_results': [variant]}
    store.db.execute("CREATE TRIGGER reject_result BEFORE INSERT ON variants BEGIN SELECT RAISE(ABORT,'injected'); END")
    with pytest.raises(sqlite3.IntegrityError, match='injected'):
        store.complete_terrain_work(uid, **args)
    assert store.get_observation(unit['sampling_key']) is None
    assert store.terrain_work_counts(revision) == {'leased': 1}
    assert store.get_terrain_work(uid)['result'] is None
    store.db.execute('DROP TRIGGER reject_result')
    assert store.complete_terrain_work(uid, **args)
    assert not store.complete_terrain_work(uid, **args)
    with pytest.raises(ValueError, match='differs'):
        store.complete_terrain_work(uid, **{**args, 'state': {'next_resolution': 16}})
    assert store.get_terrain_work(uid)['result']['state'] == {'next_resolution': 32}
    assert store.get_variant('0:1:2', 'v1', [1, 2])['result'] == variant['result']
    assert store.terrain_work_counts(revision) == {'complete': 1, 'deferred': 1}
    assert not store.terrain_work_complete(revision, '0:1:2', 'v1')
    with pytest.raises(ValueError, match='aggregate completion'):
        store.set_variant_task_status('0:1:2', 'v1', 'complete')
    pending = next(store.iter_terrain_work(revision, status='deferred'))
    store.claim_terrain_work(pending['unit_id'], 'abandoned-owner')
    store.close()
    with RealmStore(tmp_path, resume=True) as store:
        assert store.recover_terrain_work(revision) == 1
        assert store.terrain_work_counts(revision) == {'complete': 1, 'pending': 1}
        retried = store.claim_terrain_work(pending['unit_id'], 'new-owner')
        assert retried['attempts'] == 2
        store.complete_terrain_work(retried['unit_id'], result={'geometry_score': 90}, observation=observation(retried))
        assert store.terrain_work_complete(revision, '0:1:2', 'v1')
        store.set_variant_task_status('0:1:2', 'v1', 'complete')


def test_shared_raw_observation_is_required_and_immutable(tmp_path):
    store, revision = setup_store(tmp_path)
    with store:
        uid = store.ensure_terrain_work(revision, '0:1:2', 'v1', payload())
        unit = store.claim_terrain_work(uid, 'owner')
        with pytest.raises(ValueError, match='durable raw'):
            store.complete_terrain_work(uid, result={})
        data = observation(unit)
        store.complete_terrain_work(uid, observation=data)
        other = store.ensure_terrain_work(revision, '0:1:2', 'v2', payload())
        store.claim_terrain_work(other, 'owner')
        changed = copy.deepcopy(data)
        changed['channels']['height'] = [4, 3, 2, 1]
        with pytest.raises(ValueError, match='immutable'):
            store.complete_terrain_work(other, observation=changed)
        assert store.get_terrain_work(other)['status'] == 'leased'
        assert store.complete_terrain_work(other, result={})  # matching shared observation already durable


def test_historical_results_not_adopted_and_caller_transaction_not_committed(tmp_path):
    store = RealmStore(tmp_path, {'config': {}})
    with store:
        store.configure_range(0, 1, 1)
        commit_seed(store, 0)
        store.upsert_variant('0:1:2', 'v1', [1, 2], {'provider': 'old'})
        with pytest.raises(ValueError, match='Historical terrain'):
            store.ensure_terrain_pool({'provider': 'new'})
        assert store.get_variant('0:1:2', 'v1', [1, 2])['result'] == {'provider': 'old'}
        store.db.execute("INSERT INTO meta VALUES ('caller','true')")
        with pytest.raises(ValueError, match='caller transaction'):
            store.ensure_terrain_pool({'provider': 'new'})
        assert store.db.in_transaction
        store.db.rollback()
        assert store.get_state('caller') is None


def test_completion_and_enqueue_reject_caller_transaction(tmp_path):
    store, revision = setup_store(tmp_path)
    with store:
        uid = store.ensure_terrain_work(revision, '0:1:2', 'v1', payload())
        unit = store.claim_terrain_work(uid, 'owner')
        store.db.execute("INSERT INTO meta VALUES ('caller','true')")
        calls = [lambda: store.ensure_terrain_work(revision, '0:1:2', 'v2', payload()),
                 lambda: store.claim_terrain_work(uid, 'another-owner'),
                 lambda: store.recover_terrain_work(revision),
                 lambda: store.complete_terrain_work(uid, observation=observation(unit))]
        for call in calls:
            with pytest.raises(ValueError, match='caller transaction'):
                call()
            assert store.db.in_transaction
        store.db.rollback()
        assert store.get_terrain_work(uid)['status'] == 'leased'
        assert store.get_observation(unit['sampling_key']) is None


def failed_observation(unit):
    data = observation(unit)
    data['sampling_key'] = unit['sampling_key']
    data['id'] = f"{unit['sampling_key']}:unit:{unit['unit_id']}:attempt:{unit['attempts']}"
    data['metadata']['failed'] = True
    return data


def test_failed_attempt_deferral_is_atomic_idempotent_and_retryable(tmp_path):
    store, revision = setup_store(tmp_path)
    uid = store.ensure_terrain_work(revision, '0:1:2', 'v1', payload())
    unit = store.claim_terrain_work(uid, 'first-owner')
    raw = failed_observation(unit)
    variant = {'candidate_id': '0:1:2', 'variant': 'v1', 'center': [1, 2],
               'result': {'geometry_score': 40, 'qualification': 'PENDING', 'metrics': {'closest': 3}}}
    args = {'result': {'best': variant['result']}, 'state': {'retry': True}, 'observation': raw,
            'variant_results': [variant], 'expected_attempt': 1, 'worker': 'first-owner'}
    store.db.execute("CREATE TRIGGER reject_deferred BEFORE UPDATE ON terrain_work WHEN NEW.status='deferred' BEGIN SELECT RAISE(ABORT,'injected'); END")
    with pytest.raises(sqlite3.IntegrityError, match='injected'):
        store.defer_terrain_work(uid, **args)
    assert store.get_terrain_work(uid)['status'] == 'leased'
    assert store.get_observation(raw['id']) is None
    assert store.get_variant('0:1:2', 'v1', [1, 2]) is None
    assert store.db.execute('SELECT count(*) FROM terrain_work_attempts').fetchone()[0] == 0
    store.db.execute('DROP TRIGGER reject_deferred')
    assert store.defer_terrain_work(uid, **args)
    assert not store.defer_terrain_work(uid, **args)
    with pytest.raises(ValueError, match='differs'):
        store.defer_terrain_work(uid, **{**args, 'state': {'retry': False}})
    assert store.get_observation(unit['sampling_key']) is None
    assert store.get_observation(raw['id']) == raw
    assert store.get_variant('0:1:2', 'v1', [1, 2])['result']['metrics'] == {'closest': 3}
    assert not store.terrain_work_complete(revision, '0:1:2', 'v1')
    store.close()
    with RealmStore(tmp_path, resume=True) as store:
        retried = store.claim_terrain_work(uid, 'second-owner')
        assert retried['attempts'] == 2
        with pytest.raises(ValueError, match='ownership changed'):
            store.defer_terrain_work(uid, **args)
        with pytest.raises(ValueError, match='current terrain attempt'):
            store.defer_terrain_work(uid, expected_attempt=2, worker='first-owner')
        store.complete_terrain_work(uid, result={'geometry_score': 90}, observation=observation(retried))
        assert store.terrain_work_complete(revision, '0:1:2', 'v1')
        assert store.get_observation(raw['id']) == raw
        assert store.db.execute('SELECT count(*) FROM terrain_work_attempts').fetchone()[0] == 1


def test_deferral_rejects_shared_key_stale_attempt_and_caller_transaction(tmp_path):
    store, revision = setup_store(tmp_path)
    with store:
        uid = store.ensure_terrain_work(revision, '0:1:2', 'v1', payload())
        unit = store.claim_terrain_work(uid, 'owner')
        with pytest.raises(ValueError, match='ownership changed'):
            store.defer_terrain_work(uid, expected_attempt=1.0)
        for raw in [observation(unit), {**failed_observation(unit), 'id': unit['sampling_key'] + ':attempt:0'}]:
            with pytest.raises(ValueError, match='current attempt'):
                store.defer_terrain_work(uid, observation=raw)
            assert not store.db.in_transaction
            assert store.get_terrain_work(uid)['status'] == 'leased'
        store.db.execute("INSERT INTO meta VALUES ('caller','true')")
        with pytest.raises(ValueError, match='caller transaction'):
            store.defer_terrain_work(uid, result={})
        assert store.db.in_transaction
        store.db.rollback()
        assert store.defer_terrain_work(uid, result={'failure': 'no raster returned'}, worker='owner', expected_attempt=1)


def test_pool_rotation_bounds_are_applied_before_decoding(tmp_path):
    store, revision = setup_store(tmp_path)
    with store:
        commit_seed(store, 1)
        commit_seed(store, 2)
        revision = store.ensure_terrain_pool({'provider': 'synthetic-v1'}, new_revision=True)
        assert [r['id'] for r in store.iter_terrain_pool_candidates(revision, start_after='0:1:2', stop_at='1:1:2', batch_size=1)] == ['1:1:2']
        store.db.execute("UPDATE candidates SET result='malformed excluded payload' WHERE id='0:1:2'")
        store.db.commit()
        assert [r['id'] for r in store.iter_terrain_pool_candidates(revision, start_after='1:1:2')] == ['2:1:2']
