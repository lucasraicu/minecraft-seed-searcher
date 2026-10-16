from types import SimpleNamespace

import pytest

from seed_search.realm.resources import check_projected_capacity, disk_policy, WorkspaceCapacityError
from seed_search.web import server


def test_billion_seed_compact_cli_checkpoints_and_resumes(tmp_path):
    import subprocess
    import yaml
    from seed_search.realm.store import RealmStore
    cfg, _ = server.SweepManager._resolve_sweep()
    policy = tmp_path / 'policy.yaml'
    policy.write_text(yaml.safe_dump(cfg))
    run = tmp_path / 'run'
    command = server.SweepManager._scan_command(policy, run, 5_000_000_000, 0, 1, 2, 0)
    for resume in (False, True):
        args = (command[:3] + ['resume', '--run', str(run), '--native-build', str(server.DEFAULT_NATIVE_BUILD), '--prediction-scale'] if resume else command) + ['--stop-after', '2']
        result = subprocess.run(args, cwd=server.PROJECT_ROOT, env=server.SweepManager._launch_environment(),
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        with RealmStore(run, resume=True) as store:
            assert store.identity['retention']['mode'] == 'survivors'
            assert store.identity['count'] == 5_000_000_000
            assert store.status()['completed_seeds'] == (4 if resume else 2)
