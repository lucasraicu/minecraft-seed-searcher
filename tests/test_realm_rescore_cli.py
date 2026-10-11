"""Recover the saved score policy without the original external policy file."""
import pytest

from seed_search.realm.cli import main
from seed_search.realm.reports import rescore
from seed_search.realm.store import RealmStore
from test_realm_report_recovery import populated, weight_change


def test_cli_resumes_persisted_revision_without_policy_file(tmp_path, capsys):
    store, cfg = populated(tmp_path / 'run')
    def interrupt(_):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        rescore(store, weight_change(cfg), batch_size=1, progress=interrupt)
    revision_id = store.get_state('rescore_revision')['id']
    store.close()
    status = main(['status', '--run', str(tmp_path / 'run')])
    assert status['score_revision']['status'] == 'running'
    result = main(['rescore', '--run', str(tmp_path / 'run'), '--resume'])
    assert result['score_revision'] == revision_id
    assert result['rescored_candidates'] == 3
    assert result['rescored_variants'] == 6
    with RealmStore(tmp_path / 'run', resume=True) as saved:
        assert saved.get_state('rescore_revision')['status'] == 'complete'
        assert all(c['baseline_score'] == 15 for c in saved.iter_candidates())
    capsys.readouterr()


def test_cli_rejects_resume_without_interrupted_revision(tmp_path, capsys):
    store, cfg = populated(tmp_path / 'run')
    store.close()
    for completed in (False, True):
        if completed:
            with RealmStore(tmp_path / 'run', resume=True) as saved:
                rescore(saved, weight_change(cfg))
        with pytest.raises(SystemExit) as exc:
            main(['rescore', '--run', str(tmp_path / 'run'), '--resume'])
        assert exc.value.code == 2
        assert 'No interrupted score revision' in capsys.readouterr().err


def test_baseline_resume_uses_original_compute_config_after_rescore(tmp_path, monkeypatch, capsys):
    from seed_search.realm import runner, cli
    store, cfg = populated(tmp_path / 'run')
    rescore(store, weight_change(cfg))
    original_scoring = dict(cfg['scoring'])
    store.close()
    seen = []
    def fake_scan(config, *args, **kwargs):
        seen.append(dict(config['scoring']))
        return {'completed_seeds': 3}
    monkeypatch.setattr(runner, 'run_scan', fake_scan)
    # Compatibility reporting and identity creation remain read-only here.
    monkeypatch.setattr(cli, 'report', lambda cfg: {'test': True})
    monkeypatch.setattr(cli, 'make_identity', lambda cfg, count, first: {'config': cfg})
    main(['resume', '--run', str(tmp_path / 'run')])
    assert seen == [original_scoring]
    with RealmStore(tmp_path / 'run', resume=True) as saved:
        assert saved.get_state('score_policy')['scoring']['geometry_weight'] == .5
        assert all(c['baseline_score'] == 15 for c in saved.iter_candidates())
    capsys.readouterr()
