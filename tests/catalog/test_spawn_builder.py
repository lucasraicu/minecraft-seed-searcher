"""Tests for build_spawn_estimator and mock subprocess builder behavior."""
import hashlib
import json
from pathlib import Path
import pytest
from scripts.build_spawn_estimator import ROOT, C_SOURCE, build_spawn_estimator, main
from seed_search.realm.native_identity import native_source_fingerprint
from seed_search.catalog.spawn_estimator import SpawnEstimator
from seed_search.catalog.models import identity


def _mock_res(row):
    return type('Res', (), {'stdout': json.dumps(row), 'stderr': ''})()


def test_builder_refuses_repo_existing_and_symlinks(tmp_path):
    repo_target = ROOT / 'spawn_estimator_forbidden'
    with pytest.raises(ValueError, match='outside the repository'):
        build_spawn_estimator(repo_target)
    with pytest.raises(SystemExit):
        main(['--output', str(repo_target)])

    existing = tmp_path / 'existing_bin'
    existing.write_bytes(b'binary')
    with pytest.raises(ValueError, match='already exists'):
        build_spawn_estimator(existing)

    manifest_conflict = tmp_path / 'conflict_bin'
    Path(str(manifest_conflict) + '.build.json').write_text('{}')
    with pytest.raises(ValueError, match='manifest already exists'):
        build_spawn_estimator(manifest_conflict)

    sym_out = tmp_path / 'sym_target'
    sym_out.symlink_to(tmp_path / 'nonexistent')
    with pytest.raises(ValueError, match='cannot be a symlink'):
        build_spawn_estimator(sym_out)

    real_dir = tmp_path / 'real_dir'
    real_dir.mkdir()
    link_dir = tmp_path / 'link_dir'
    link_dir.symlink_to(real_dir)
    with pytest.raises(ValueError, match='symlink traversal'):
        build_spawn_estimator(link_dir / 'estimator')


def test_builder_manifest_and_spawn_estimator_config(tmp_path, monkeypatch):
    out = tmp_path / 'estimator'
    fake_bin = b'spawn-estimator-binary-content'
    captured = []

    def mock_run(cmd, check=True, timeout=None):
        assert timeout == 60
        captured.append(cmd)
        Path(out).write_bytes(fake_bin)

    monkeypatch.setattr('scripts.build_spawn_estimator.subprocess.run', mock_run)
    monkeypatch.setattr('scripts.build_spawn_estimator.subprocess.check_output',
                        lambda cmd, text=True, timeout=None: 'mock-cc 14.2\n' if timeout == 10 else '')

    result_path = build_spawn_estimator(out)
    assert result_path == out.resolve() and len(captured) == 1
    assert captured[0][0] == 'cc' and '-O2' in captured[0] and str(out) in captured[0]

    manifest = json.loads(Path(str(out) + '.build.json').read_text())
    expected_bin_sha = hashlib.sha256(fake_bin).hexdigest()
    expected_src_sha = native_source_fingerprint()
    assert manifest['binary_sha256'] == expected_bin_sha
    assert manifest['source_sha256'] == expected_src_sha
    assert manifest['compiler'] == 'mock-cc 14.2'
    assert 'embedded:spawn_estimator.c' in manifest['input_source_hashes']

    estimator = SpawnEstimator(out, binary_sha256=manifest['binary_sha256'],
                               source_sha256=manifest['source_sha256'])
    ident = identity('-9223372036854775808', model_id='26.50',
                     native_sha256='a' * 64, source_sha256=expected_src_sha)
    row = dict(seed=ident['seed'], estimate=[16, 32], repeat_estimate=[16, 32])
    monkeypatch.setattr('seed_search.catalog.spawn_estimator.subprocess.run', lambda *a, **k: _mock_res(row))
    anchor = estimator.estimate(ident)
    assert anchor['coordinate'] == [16, 32] and anchor['context']['provider'] == 'estimated_world_spawn_v1'


def test_spawn_estimator_rejects_repeat_mismatch(tmp_path, monkeypatch):
    out = tmp_path / 'estimator_mismatch'
    monkeypatch.setattr('scripts.build_spawn_estimator.subprocess.run', lambda cmd, **k: out.write_bytes(b'bin'))
    monkeypatch.setattr('scripts.build_spawn_estimator.subprocess.check_output', lambda cmd, **k: 'cc 1.0\n')
    build_spawn_estimator(out)
    manifest = json.loads(Path(str(out) + '.build.json').read_text())
    est = SpawnEstimator(out, binary_sha256=manifest['binary_sha256'], source_sha256=manifest['source_sha256'])
    ident = identity('-12345', model_id='26.50', native_sha256='a' * 64, source_sha256=manifest['source_sha256'])
    mismatch = dict(seed=ident['seed'], estimate=[16, 32], repeat_estimate=[16, 33])
    monkeypatch.setattr('seed_search.catalog.spawn_estimator.subprocess.run', lambda *a, **k: _mock_res(mismatch))
    with pytest.raises(ValueError, match='Spawn estimate identity/repeat mismatch'):
        est.estimate(ident)


def test_c_source_contract_and_signed64_preservation():
    assert 'estimateSpawn' in C_SOURCE and 'getSpawn' not in C_SOURCE
    assert 'MC_26_50' in C_SOURCE and 'DIM_OVERWORLD' in C_SOURCE and 'repeat_estimate' in C_SOURCE
    assert ('strtoimax' in C_SOURCE or 'strtoll' in C_SOURCE) and 'terrain' not in C_SOURCE.lower()


def test_main_cli_success(tmp_path, monkeypatch, capsys):
    out = tmp_path / 'cli_bin'
    monkeypatch.setattr('scripts.build_spawn_estimator.subprocess.run', lambda cmd, **k: out.write_bytes(b'cli'))
    monkeypatch.setattr('scripts.build_spawn_estimator.subprocess.check_output', lambda cmd, **k: 'cc 1.0\n')
    assert main(['--output', str(out)]) == 0
    assert str(out.resolve()) in capsys.readouterr().out
    assert Path(str(out) + '.build.json').is_file()
