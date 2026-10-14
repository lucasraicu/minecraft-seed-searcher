import pytest

from seed_search.realm import siblings
from seed_search.realm.config import default_config, validate_config
from seed_search.realm.runner import _seed
from seed_search.realm.store import RealmStore


def fake_scan(cfg, output, count, *, identity, resume, **kwargs):
    with RealmStore(output, identity, resume) as store:
        store.configure_range(0, count, count)
        store.recover_assignments()
        while (lease := store.claim_range('fake')) is not None:
            results = []
            for i in range(*lease):
                seed = str(_seed(i, cfg['search']))
                positive = (int(seed) & 0xffffffff) % 3 == 0
                results.append({'index': i, 'seed': seed, 'counts': {}, 'anchors': [
                    {'id': f'{seed}:0:0', 'index': i, 'seed': seed, 'stronghold': [0, 0],
                     'qualification': 'PREDICTED' if positive else 'PENDING'}]})
            store.complete_range(*lease, results)
        store.set_state('worker_statistics', {'worker_cpu_seconds': 1.})
        return store.status()


def test_adaptive_resume_after_committed_round_has_no_duplicate_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(siblings, 'run_scan', fake_scan)
    cfg = default_config(); layouts = [0, 1, 2, 3]
    def interrupt(record):
        raise RuntimeError('interrupted after committed round')
    with pytest.raises(RuntimeError, match='interrupted'):
        siblings.run_adaptive(cfg, tmp_path/'resumed', layouts, budget=20,
                              promotion=(4, 4, 4), progress=interrupt)
    resumed = siblings.run_adaptive(cfg, tmp_path/'resumed', layouts, budget=20,
                                    promotion=(4, 4, 4), resume=True)
    single = siblings.run_adaptive(cfg, tmp_path/'single', layouts, budget=20, promotion=(4, 4, 4))
    assert resumed['stats'] == single['stats']
    assert resumed['evaluated_inputs'] == single['evaluated_inputs'] == 20
    seen = []
    for path in sorted((tmp_path/'resumed').glob('round-*')):
        with RealmStore(path, resume=True) as store:
            seen.extend(r['seed'] for r in store.iter_results())
    assert len(seen) == len(set(seen)) == 20
    with pytest.raises(ValueError, match='Incompatible resume'):
        siblings.run_adaptive(cfg, tmp_path/'resumed', layouts, budget=21,
                              promotion=(4, 4, 4), resume=True)


def test_manifest_identity_requires_canonical_distinct_seeds():
    cfg = default_config()
    cfg['search'].update(sequence='manifest', manifest_seeds=['-1', '0', '12345'])
    validate_config(cfg)
    assert [_seed(i, cfg['search']) for i in range(3)] == [-1, 0, 12345]
    with pytest.raises(ValueError, match='manifest'):
        _seed(3, cfg['search'])
    cfg['search']['manifest_seeds'] = ['-1', '-1']
    with pytest.raises(ValueError, match='distinct'):
        validate_config(cfg)


def test_adaptive_interrupted_child_batch_resumes_without_skipping_seeds(tmp_path, monkeypatch):
    interrupted_once = False

    def interruptible_scan(cfg, output, count, *, identity, resume, **kwargs):
        nonlocal interrupted_once
        with RealmStore(output, identity, resume) as store:
            store.configure_range(0, count, 2)
            store.recover_assignments()
            # If this is round-1 and we have not interrupted yet, complete only 1 batch (2 seeds)
            if 'round-1' in str(output) and not interrupted_once:
                interrupted_once = True
                lease = store.claim_range('fake', max_seeds=2)
                if lease is not None:
                    results = []
                    for i in range(*lease):
                        seed = str(_seed(i, cfg['search']))
                        results.append({'index': i, 'seed': seed, 'counts': {}, 'anchors': [
                            {'id': f'{seed}:0:0', 'index': i, 'seed': seed, 'stronghold': [0, 0],
                             'qualification': 'PREDICTED'}]})
                    store.complete_range(*lease, results)
                status = store.status()
                status['interrupted'] = True
                return status
            # Otherwise normal completion
            while (lease := store.claim_range('fake')) is not None:
                results = []
                for i in range(*lease):
                    seed = str(_seed(i, cfg['search']))
                    positive = (int(seed) & 0xffffffff) % 3 == 0
                    results.append({'index': i, 'seed': seed, 'counts': {}, 'anchors': [
                        {'id': f'{seed}:0:0', 'index': i, 'seed': seed, 'stronghold': [0, 0],
                         'qualification': 'PREDICTED' if positive else 'PENDING'}]})
                store.complete_range(*lease, results)
            store.set_state('worker_statistics', {'worker_cpu_seconds': 1.})
            return store.status()

    monkeypatch.setattr(siblings, 'run_scan', interruptible_scan)
    cfg = default_config()
    layouts = [0, 1, 2, 3]

    # First run gets interrupted during round-1
    result1 = siblings.run_adaptive(cfg, tmp_path / 'adaptive_run', layouts, budget=20,
                                   promotion=(4, 4, 4))
    assert result1.get('interrupted') is True

    # Verify that parent store did NOT advance round counter by planned batch size
    with RealmStore(tmp_path / 'adaptive_run', resume=True) as parent:
        assert parent.get_state('adaptive_next_round') == 1
        partial = parent.get_state('adaptive_partial_round')
        assert partial is not None
        assert partial['round'] == 1
        # Round 0 evaluated 4 inputs, round 1 was interrupted so used is still 4
        assert result1['evaluated_inputs'] == 4

    # Resume run: should resume round 1 and finish remaining seeds
    result2 = siblings.run_adaptive(cfg, tmp_path / 'adaptive_run', layouts, budget=20,
                                   promotion=(4, 4, 4), resume=True)
    assert result2.get('interrupted') is not True
    assert result2['evaluated_inputs'] == 20

    with RealmStore(tmp_path / 'adaptive_run', resume=True) as parent:
        assert parent.get_state('adaptive_next_round') == 3
        assert parent.get_state('adaptive_partial_round') is None

    # Verify no seeds were skipped or duplicated
    seen = []
    for path in sorted((tmp_path / 'adaptive_run').glob('round-*')):
        with RealmStore(path, resume=True) as store:
            seen.extend(r['seed'] for r in store.iter_results())
    assert len(seen) == len(set(seen)) == 20
