import copy
import sqlite3
import threading

import pytest

from seed_search.realm.baseline import evaluate_seed
from seed_search.realm.baseline import baseline_score_uncertainty
from seed_search.realm.biomes import classify
from seed_search.realm.config import default_config
from seed_search.realm.store import RealmStore


class DiscoveryBackend:
    strongholds = []
    def __init__(self, seed):
        self.native_work = {}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def structure_pair(self, name, bounds):
        if name == 'stronghold':
            return [[1, 2], [3, 4]], self.strongholds
        if name == 'fortress':
            return [[10, 20]], []
        return [], []


def seed_result(backend=DiscoveryBackend):
    return evaluate_seed(0, 42, default_config(), backend_factory=backend)


def open_run(path):
    store = RealmStore(path, {'config': default_config()})
    store.configure_range(0, 1, 1)
    store.claim_range('scanner')
    return store


def actual_evidence(task, cfg):
    return {'seed': task['seed'], 'structure': task['structure'],
            'source': {'kind': 'actual_generation', 'provider': 'bds',
                       'target_version': cfg['game']['target_version'], 'version': cfg['game']['bds_version']},
            'settings': copy.deepcopy(cfg['discovery']),
            'bounds': cfg['discovery']['overworld_bounds' if task['structure'] == 'stronghold' else 'nether_bounds'],
            'coordinates': [], 'confirmed_absent': True, 'complete': True,
            'coverage_complete': True, 'verification': 'VERIFIED'}


def test_no_anchor_seed_preserves_raw_and_viable_discovery(tmp_path):
    result = seed_result()
    assert result['anchors'] == []
    assert result['discovery']['stronghold']['raw'] == [[1, 2], [3, 4]]
    assert result['discovery']['fortress']['raw'] == [[10, 20]]
    assert result['discovery']['stronghold']['predicted_viable'] == []
    assert result['counts']['unresolved_discovery'] == 1
    assert result['counts']['unresolved_stronghold_coverage'] == 1
    assert result['counts']['unresolved_fortress_coverage'] == 1
    with open_run(tmp_path) as store:
        assert store.complete_range(0, 1, [result])
        assert not store.complete_range(0, 1, [result])
        assert list(store.iter_results()) == [result]
        tasks = list(store.iter_discovery_tasks(batch_size=1))
        assert len(tasks) == 2
        assert all(t['coverage_status'] == 'UNRESOLVED' and t['evidence_status'] == 'SAVED_PREDICTION' for t in tasks)
        assert store.status()['discovery_tasks'] == {'pending': 2}
        assert store.status()['completed_seeds'] == 1


def test_positive_anchor_does_not_close_recall(tmp_path):
    class Positive(DiscoveryBackend):
        strongholds = [[1, 2]]
    result = seed_result(Positive)
    assert len(result['anchors']) == 1
    assert result['counts']['unresolved_discovery'] == 0  # historical zero-anchor metric
    assert result['counts']['unresolved_stronghold_coverage'] == 1
    assert result['discovery']['coverage']['complete'] is False
    anchor = result['anchors'][0]
    uncertainty = anchor['baseline_score_uncertainty']
    assert anchor['biomes'] is None and uncertainty['biome_prediction_interval'][0] == 0
    assert uncertainty['actual_generation_score_interval'][0] == 0
    assert uncertainty['pending_prediction_requirements'] == ['initial_fortress','final_fortress','final_bastion']
    assert 'stronghold' in uncertainty['unresolved_required_eligibility']
    assert uncertainty['eligibility_verified'] is False
    with open_run(tmp_path) as store:
        store.complete_range(0, 1, [result])
        task = store.claim_discovery_task('recovery')
        with pytest.raises(ValueError, match='actual source'):
            store.complete_discovery_task(0, task['structure'], result['discovery'][task['structure']])
        assert store.get_discovery_task(0, task['structure'])['coverage_status'] == 'UNRESOLVED'


def test_task_insert_failure_rolls_back_coverage_and_seed_evidence(tmp_path):
    with open_run(tmp_path) as store:
        store.db.execute("CREATE TRIGGER reject_discovery BEFORE INSERT ON discovery_tasks WHEN NEW.structure='stronghold' BEGIN SELECT RAISE(ABORT,'injected'); END")
        with pytest.raises(sqlite3.IntegrityError, match='injected'):
            store.complete_range(0, 1, [seed_result()])
        assert list(store.iter_results()) == []
        assert list(store.iter_discovery_tasks()) == []
        assert store.status()['completed_seeds'] == 0
        assert store.status()['counts'] == {}
        assert store.status()['ranges'] == {'in_progress': 1}
        store.db.execute('DROP TRIGGER reject_discovery')
        store.complete_range(0, 1, [seed_result()])


def test_recovery_restart_and_complete_evidence_is_independent(tmp_path):
    store = open_run(tmp_path)
    original = seed_result()
    store.complete_range(0, 1, [original])
    task = store.claim_discovery_task('old-owner')
    store.close()
    with RealmStore(tmp_path, resume=True) as store:
        assert store.recover_discovery_assignments() == 1
        task = store.claim_discovery_task('new-owner')
        assert task['attempts'] == 2
        evidence = actual_evidence(task, default_config())
        for field, value in [('coverage_complete', False), ('bounds', [0, 0, 1, 1]),
                             ('settings', {}), ('seed', '43'), ('confirmed_absent', False),
                             ('coordinates', [[1000000, 1000000]])]:
            invalid = {**evidence, field: value}
            with pytest.raises(ValueError, match='coverage evidence'):
                store.complete_discovery_task(0, task['structure'], invalid)
        invalid = copy.deepcopy(evidence)
        invalid['source']['version'] = 'wrong'
        with pytest.raises(ValueError, match='coverage evidence'):
            store.complete_discovery_task(0, task['structure'], invalid)
        assert store.complete_discovery_task(0, task['structure'], evidence)
        assert not store.complete_discovery_task(0, task['structure'], evidence)
        changed = copy.deepcopy(evidence)
        changed['coordinates'] = [[1, 2]]
        changed['confirmed_absent'] = False
        with pytest.raises(ValueError, match='immutable'):
            store.complete_discovery_task(0, task['structure'], changed)
        resolved = store.get_discovery_task(0, task['structure'])
        assert resolved['coverage_status'] == 'RESOLVED'
        assert resolved['discovery_observation']['confirmed_absent'] is False
        assert resolved['recovery_evidence']['confirmed_absent'] is True
        assert list(store.iter_results()) == [original]
        assert store.status()['completed_seeds'] == 1
        assert list(store.iter_candidates()) == []


def test_legacy_backfill_is_explicit_bounded_and_does_not_fabricate(tmp_path):
    store = RealmStore(tmp_path, {'config': default_config()})
    store.configure_range(0, 3, 3)
    store.claim_range('scanner')
    results = [{'index': i, 'seed': str(i), 'anchors': [], 'counts': {}} for i in range(3)]
    store.complete_range(0, 3, results)
    store.db.execute('DELETE FROM discovery_tasks')
    store.db.commit()
    store.close()
    with RealmStore(tmp_path, resume=True) as store:
        assert list(store.iter_discovery_tasks()) == []
        page = store.backfill_discovery_tasks(batch_size=1)
        assert page == {'visited_seeds': 1, 'inserted_tasks': 2, 'next_after_index': 0}
        assert len(list(store.iter_discovery_tasks())) == 2
        page = store.backfill_discovery_tasks(after_index=page['next_after_index'], batch_size=2)
        assert page['inserted_tasks'] == 4
        assert store.backfill_discovery_tasks(batch_size=3)['inserted_tasks'] == 0
        assert all(t['evidence_status'] == 'LEGACY_EVIDENCE_UNAVAILABLE' and t['coverage_status'] == 'UNRESOLVED' for t in store.iter_discovery_tasks())
        assert list(store.iter_results()) == results


def test_bonus_intervals_keep_predictor_presence_separate_from_actual():
    cfg = default_config()
    biomes = classify(['forest', 'taiga', 'jungle', 'pale_garden'], cfg['biomes'])
    optional = {'monument': {'bonus': cfg['structures']['optional_bonuses']['monument']}}
    uncertainty = baseline_score_uncertainty(biomes, optional, cfg, [])
    assert uncertainty['prediction_score_interval'][0] == biomes['score'] + 5
    assert uncertainty['actual_generation_score_interval'][0] == 0
    assert uncertainty['optional_prediction_interval'][0] == 5
    assert uncertainty['optional_actual_generation_interval'][0] == 0
    assert uncertainty['prediction_score_interval'][1] >= uncertainty['prediction_score_interval'][0]
    assert uncertainty['actual_generation_score_interval'][1] == uncertainty['prediction_score_interval'][1]
    assert uncertainty['pending_prediction_requirements'] == []
    assert uncertainty['unresolved_required_eligibility']
    assert uncertainty['eligibility_verified'] is False


def test_competing_completion_connections_cannot_overwrite_evidence(tmp_path):
    with open_run(tmp_path) as store:
        store.complete_range(0, 1, [seed_result()])
        task = store.claim_discovery_task('owner')
    first_read = threading.Event()
    second_begin = threading.Event()
    release = threading.Event()
    second_read = threading.Event()
    outcomes = {}
    evidence = actual_evidence(task, default_config())
    conflicting = copy.deepcopy(evidence)
    conflicting['coordinates'] = [[1, 2]]
    conflicting['confirmed_absent'] = False

    def run(name, payload):
        try:
            with RealmStore(tmp_path, resume=True) as store:
                get_task = store.get_discovery_task
                def read(index, structure):
                    assert store.db.in_transaction  # status must be read under the write lock
                    if name == 'first':
                        first_read.set()
                        assert release.wait(5)
                    else:
                        second_read.set()
                    return get_task(index, structure)
                store.get_discovery_task = read
                if name == 'second':
                    store.db.set_trace_callback(lambda sql: second_begin.set() if sql == 'BEGIN IMMEDIATE' else None)
                outcomes[name] = store.complete_discovery_task(0, task['structure'], payload)
        except BaseException as exc:
            outcomes[name] = exc

    first = threading.Thread(target=run, args=('first', evidence))
    second = threading.Thread(target=run, args=('second', conflicting))
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
    assert outcomes['first'] is True
    assert isinstance(outcomes['second'], ValueError) and 'immutable' in str(outcomes['second'])
    with RealmStore(tmp_path, resume=True) as store:
        assert store.get_discovery_task(0, task['structure'])['recovery_evidence'] == evidence


def test_completion_validation_rolls_back_and_preserves_caller_transaction(tmp_path):
    with open_run(tmp_path) as store:
        store.complete_range(0, 1, [seed_result()])
        task = store.claim_discovery_task('owner')
        evidence = actual_evidence(task, default_config())
        for field, value in [('provider', {'truthy': True}), ('provider', ' '), ('version', ['truthy']), ('version', '')]:
            invalid = copy.deepcopy(evidence)
            invalid['source'][field] = value
            with pytest.raises(ValueError, match='coverage evidence'):
                store.complete_discovery_task(0, task['structure'], invalid)
            assert not store.db.in_transaction
            assert store.get_discovery_task(0, task['structure'])['status'] == 'in_progress'
        store.db.execute("INSERT INTO meta VALUES ('uncommitted','true')")
        with pytest.raises(ValueError, match='caller transaction'):
            store.complete_discovery_task(0, task['structure'], evidence)
        assert store.db.in_transaction and store.get_state('uncommitted') is True
        store.db.rollback()
        assert store.get_state('uncommitted') is None
        assert store.complete_discovery_task(0, task['structure'], evidence)
