from types import SimpleNamespace

import pytest

from seed_search.realm.resources import check_projected_capacity, disk_policy, WorkspaceCapacityError
from seed_search.web import server


def test_compact_preview_accepts_billions_before_launch(monkeypatch):
    monkeypatch.setattr(server.shutil, 'disk_usage', lambda _: SimpleNamespace(free=636 << 30))
    manager = server.SweepManager()
    assert manager.preview_sweep(count=10_000_000)['ok']
    for count in (5_000_000_000, 100_000_000_000):
        result = manager.preview_sweep(count=count)
        assert result['ok'], result
        command = result['launch']['command']
        assert command[command.index('--retention') + 1] == 'survivors'
        assert command[command.index('--count') + 1] == str(count)


def test_free_space_and_existing_run_bytes_reduce_capacity():
    policy = disk_policy({'projected_bytes_per_seed':32}, retention='full')
    with pytest.raises(WorkspaceCapacityError, match='available disk space') as error:
        check_projected_capacity(policy, used=1 << 30, free=17 << 30,
                                 remaining_seeds=100_000_000, estimate=32)
    assert '33,554,432 additional seeds' in str(error.value)
    with pytest.raises(WorkspaceCapacityError, match='per-run budget') as error:
        check_projected_capacity(policy, used=127 << 30, free=636 << 30,
                                 remaining_seeds=100_000_000, estimate=32)
    assert '33,554,432 additional seeds' in str(error.value)


def test_exact_projection_boundary_is_allowed():
    check_projected_capacity(disk_policy({'projected_bytes_per_seed':32}, retention='full'),
                             used=0, free=144 << 30,
                             remaining_seeds=4_294_967_296, estimate=32)


def test_compact_projection_is_advisory_but_writes_remain_bounded(tmp_path, monkeypatch):
    from seed_search.realm.resources import disk_status
    monkeypatch.setattr(server.shutil, 'disk_usage', lambda _: SimpleNamespace(free=636 << 30))
    policy = disk_policy({}, retention='survivors')
    result = disk_status(tmp_path, policy, remaining_seeds=100_000_000_000)
    assert result['projected_run_bytes'] > policy['run_disk_limit_bytes']
    assert result['projection_enforced'] is False
    with pytest.raises(WorkspaceCapacityError, match='disk cap'):
        disk_status(tmp_path, policy, additional_bytes=129 << 30)
    monkeypatch.setattr(server.shutil, 'disk_usage', lambda _: SimpleNamespace(free=16 << 30))
    with pytest.raises(WorkspaceCapacityError, match='reserve'):
        disk_status(tmp_path, policy, additional_bytes=1)
    assert not server.SweepManager().preview_sweep(count=5_000_000_000)['ok']


def test_billion_seed_compact_cli_checkpoints_and_resumes(tmp_path):
    import subprocess
    import yaml
    from seed_search.realm.store import RealmStore
    cfg, _ = server.SweepManager._resolve_sweep()
    policy = tmp_path / 'policy.yaml'
    policy.write_text(yaml.safe_dump(cfg))
    run = tmp_path / 'run'
    command = server.SweepManager._scan_command(policy, run, 5_000_000_000, 0, 1, 2, 3)
    for resume in (False, True):
        args = (command[:3] + ['resume', '--run', str(run), '--native-build', str(server.DEFAULT_NATIVE_BUILD), '--prediction-scale'] if resume else command) + ['--stop-after', '2']
        result = subprocess.run(args, cwd=server.PROJECT_ROOT, env=server.SweepManager._launch_environment(),
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        with RealmStore(run, resume=True) as store:
            assert store.identity['retention']['mode'] == 'survivors'
            assert store.identity['count'] == 5_000_000_000
            assert store.status()['completed_seeds'] == (4 if resume else 2)
