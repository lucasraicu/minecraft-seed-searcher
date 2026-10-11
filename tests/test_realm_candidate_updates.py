import sqlite3
import threading

import pytest

from seed_search.realm.store import RealmStore


def checkpoint(path):
    store = RealmStore(path, {'config': {}})
    store.configure_range(0, 1, 1)
    store.claim_range('scanner')
    candidate = {'id': '0:1:2', 'seed': '0', 'stronghold': [1, 2], 'qualification': 'PREDICTED'}
    store.complete_range(0, 1, [{'index': 0, 'seed': '0', 'anchors': [candidate], 'counts': {}}])
    return store, candidate


def test_competing_independent_evidence_patches_both_survive(tmp_path):
    store, candidate = checkpoint(tmp_path)
    store.close()
    first_read = threading.Event()
    second_begin = threading.Event()
    second_read = threading.Event()
    release = threading.Event()
    outcomes = {}

    def patch(name, evidence):
        try:
            with RealmStore(tmp_path, resume=True) as store:
                get_candidate = store.get_candidate
                def read(cid):
                    assert store.db.in_transaction
                    if name == 'first':
                        first_read.set()
                        assert release.wait(5)
                    else:
                        second_read.set()
                    return get_candidate(cid)
                store.get_candidate = read
                if name == 'second':
                    store.db.set_trace_callback(lambda sql: second_begin.set() if sql == 'BEGIN IMMEDIATE' else None)
                outcomes[name] = store.upsert_candidate({'id': candidate['id'], **evidence})
        except BaseException as exc:
            outcomes[name] = exc

    first = threading.Thread(target=patch, args=('first', {'surface_biome_verification': {'status': 'VERIFIED'}}))
    second = threading.Thread(target=patch, args=('second', {'nether_verification': {'status': 'PARTIAL'}}))
    first.start()
    try:
        assert first_read.wait(5)
        second.start()
        assert second_begin.wait(5)
        assert not second_read.is_set()
    finally:
        release.set()
        first.join(5)
        if second.ident is not None:
            second.join(5)
    assert not first.is_alive() and not second.is_alive()
    assert all(isinstance(outcomes[name], dict) for name in ('first', 'second')), outcomes
    with RealmStore(tmp_path, resume=True) as store:
        saved = store.get_candidate(candidate['id'])
        assert saved['surface_biome_verification'] == {'status': 'VERIFIED'}
        assert saved['nether_verification'] == {'status': 'PARTIAL'}
        assert saved['qualification'] == 'PREDICTED'
        assert store.status()['completed_seeds'] == 1


def test_candidate_patch_validation_and_failure_roll_back(tmp_path):
    store, candidate = checkpoint(tmp_path)
    with store:
        for patch, error in [({'seed': '1'}, 'immutable'), ({'qualification': 'VERIFIED'}, 'authorization')]:
            with pytest.raises(ValueError, match=error):
                store.upsert_candidate({'id': candidate['id'], **patch})
            assert not store.db.in_transaction
            assert store.get_candidate(candidate['id']) == candidate
        store.db.execute("CREATE TRIGGER reject_patch BEFORE UPDATE ON candidates BEGIN SELECT RAISE(ABORT,'injected'); END")
        with pytest.raises(sqlite3.IntegrityError, match='injected'):
            store.upsert_candidate({'id': candidate['id'], 'surface_biome_verification': {'status': 'PARTIAL'}})
        assert not store.db.in_transaction
        assert store.get_candidate(candidate['id']) == candidate
        store.db.execute('DROP TRIGGER reject_patch')
        store.db.execute("INSERT INTO meta VALUES ('caller','true')")
        with pytest.raises(ValueError, match='caller transaction'):
            store.upsert_candidate({'id': candidate['id'], 'surface_biome_verification': {}})
        assert store.db.in_transaction
        assert store.get_state('caller') is True
        store.db.rollback()
        assert store.get_candidate(candidate['id']) == candidate
