"""Positive-path checks for raw bounds, split initialization, and durable Top-K."""
import json
import sqlite3

import pytest

from scripts.build_blueprint_batch import build
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype, run_native_scan, seeds_np


SURVIVOR = -3336796033057908633


@pytest.fixture(scope='module')
def native_build(tmp_path_factory):
    path = tmp_path_factory.mktemp('mansion-bound-native')
    build(path)
    return path


def _policy():
    cfg = dynamic_v3_blueprint_config()
    cfg['biomes']['required_families'] = []
    return cfg


def _anchors(prototype, seeds, retention):
    with prototype.sweep(seeds, threads=1, retention=retention) as batch:
        records = batch.records() if retention == 'full' else list(batch.retained_records())
    return {str(record['seed']): [
        (a['evaluation_center'], a['baseline_score'], a['ranking']['components'])
        for a in record['anchors']
    ] for record in records if record['anchors']}


def test_optimized_bounds_preserve_natural_survivors_and_compact_decisions(native_build):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    optimized = Prototype(native_build, _policy())
    seeds = [SURVIVOR, *seeds_np(0, 4096, 2026101601)]
    expected = _anchors(optimized, seeds, 'full')
    assert str(SURVIVOR) in expected
    assert _anchors(optimized, seeds, 'survivors') == expected
    assert _anchors(optimized, [SURVIVOR], 'full') == {str(SURVIVOR): expected[str(SURVIVOR)]}


def test_disabled_preflight_still_initializes_phase_one(tmp_path):
    build(tmp_path/'disabled', dynamic_preflight=False)
    prototype = Prototype(tmp_path/'disabled', _policy())
    assert _anchors(prototype, [SURVIVOR], 'survivors') == _anchors(prototype, [SURVIVOR], 'full')


@pytest.mark.parametrize('checkpoint', ['missing', 'corrupt', 'stale', 'valid'])
def test_top_k_resume_rebuilds_from_committed_candidates(tmp_path, checkpoint, native_build):
    cfg = _policy()
    cfg['search']['sequence'] = 'manifest'
    cfg['search']['manifest_seeds'] = [str(SURVIVOR), '0']
    run = tmp_path/'run'
    options = dict(count=2, native_threads=1, native_batch_size=1,
                   retention='survivors', top_k=1,
                   native_build=native_build)
    first = run_native_scan(cfg, run, stop_after=1, **options)
    assert first['completed_seeds'] == 1
    committed_leaders = json.loads((run/'top50.json').read_text())
    assert len(committed_leaders) == 1
    if checkpoint == 'missing':
        (run/'top50.json').unlink()
    elif checkpoint == 'corrupt':
        (run/'top50.json').write_text('{broken')
    elif checkpoint == 'stale':
        (run/'top50.json').write_text('[]')
    second = run_native_scan(cfg, run, resume=True, **options)
    assert second['completed_seeds'] == 2
    leaders = json.loads((run/'top50.json').read_text())
    assert leaders == committed_leaders
    assert leaders[0]['seed'] == str(SURVIVOR)
    with sqlite3.connect(run/'realm.sqlite') as db:
        assert db.execute('SELECT seed,score FROM top_candidates').fetchone() == (str(SURVIVOR), 311)
        assert db.execute('SELECT count(*) FROM candidates').fetchone()[0] == 1


def test_uncommitted_candidate_never_enters_top_k(tmp_path, monkeypatch, native_build):
    from seed_search.realm.store import RealmStore
    cfg = _policy()
    cfg['search']['sequence'] = 'manifest'
    cfg['search']['manifest_seeds'] = [str(SURVIVOR)]
    run = tmp_path/'run'
    options = dict(count=1, native_threads=1, native_batch_size=1,
                   retention='survivors', top_k=1,
                   native_build=native_build)
    original = RealmStore.complete_prepared
    def fail_before_commit(self, *args, **kwargs):
        raise RuntimeError('injected pre-commit failure')
    monkeypatch.setattr(RealmStore, 'complete_prepared', fail_before_commit)
    with pytest.raises(RuntimeError, match='injected pre-commit failure'):
        run_native_scan(cfg, run, **options)
    assert json.loads((run/'top50.json').read_text()) == []
    monkeypatch.setattr(RealmStore, 'complete_prepared', original)
    resumed = run_native_scan(cfg, run, resume=True, **options)
    assert resumed['completed_seeds'] == 1
    assert json.loads((run/'top50.json').read_text())[0]['seed'] == str(SURVIVOR)


def test_web_saved_run_keeps_its_original_native_build(tmp_path, monkeypatch, native_build):
    from pathlib import Path
    from seed_search.realm.cli import make_identity
    from seed_search.web import server
    root = Path(__file__).resolve().parents[1]
    import shutil
    monkeypatch.setattr(server,'PROJECT_ROOT',tmp_path)
    old=tmp_path/'runs/dynamic-baseline-2048/original-native'
    shutil.copytree(native_build,old)
    metadata=json.loads((old/'identity.json').read_text())
    metadata['extension']=str(old/Path(metadata['extension']).name)
    (old/'identity.json').write_text(json.dumps(metadata))
    cfg = _policy()
    cfg['search']['sequence'] = 'manifest'
    cfg['search']['manifest_seeds'] = [str(SURVIVOR)]
    monkeypatch.setattr(server, 'RUNS_DIR', tmp_path)
    run = tmp_path/'web-sweep-20261016-000000-12345678'
    run_native_scan(cfg, run, count=1, native_threads=1, native_batch_size=1,
                    retention='survivors', native_build=old,
                    identity=make_identity(cfg, 1, 0))
    monkeypatch.setattr(server, 'DEFAULT_NATIVE_BUILD', native_build)
    directory, identity, completed, _ = server.SweepManager()._saved_run(run.name)
    assert directory == run
    assert Path(identity['native_build']).resolve() == old.resolve()
    assert completed == 1
