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
