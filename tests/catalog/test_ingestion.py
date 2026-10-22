"""Tests for catalog ingestion coordinator and validation contracts."""
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import pytest

from seed_search.catalog.coverage import BIOME_METHOD, STRUCTURE_METHOD
from seed_search.catalog.models import empty_observation, validate_observation
from seed_search.catalog.registry import BIOMES, ENVELOPE, REGISTRY_REVISION, STRUCTURES
from seed_search.catalog.validation_contracts import controls as make_controls, validate_controls
from seed_search.catalog.ingestion import (
    _flock_root,
    _get_process_creation_meta,
    _validate_child_observation,
    atomic_json,
    ingest,
    strict_json_dumps,
    strict_json_loads,
    verify_no_symlinks,
)


def make_test_build(model_id: str = 'cpu-catalog-reference-v1', source_sha: str = '1' * 64) -> dict:
    """Codex build controls dict shape."""
    return {
        'identity': {
            'edition': 'bedrock',
            'game_build_id': 'research:' + model_id,
            'world_settings_id': 'default',
            'model_id': model_id,
            'native_sha256': '0' * 64,
            'source_sha256': source_sha,
            'registry_revision': REGISTRY_REVISION,
            'extractor_revision': 'cpu-catalog-reference-v1',
        },
        'source_sha256': {
            'src/ref.c': '2' * 64,
        },
    }


def make_complete_observation(seed: str, build_identity: dict) -> dict:
    """Construct a full valid 23-feature observation with valid lattice samples."""
    obs = empty_observation(dict(build_identity, seed=str(seed)))
    for st in STRUCTURES:
        obs['structures'][st['id']] = []
        obs['coverage'][st['id']] = {
            'status': 'complete',
            'bounds': list(ENVELOPE),
            'method_id': STRUCTURE_METHOD,
        }
    obs['biome_names'] = {'1': 'plains'}
    obs['biomes'] = [
        [x, 63, z, 1]
        for x in range(-5120, 5120, 64)
        for z in range(-5120, 5120, 64)
    ]
    for bm in BIOMES:
        obs['coverage'][bm['id']] = {
            'status': 'complete',
            'bounds': list(ENVELOPE),
            'method_id': BIOME_METHOD,
        }
    validate_observation(obs)
    return obs


def test_atomic_json_success_and_symlinks_and_nonfinite(tmp_path):
    target = tmp_path / "valid.json"
    atomic_json(target, {"alpha": 1, "beta": [2, 3]})
    loaded = strict_json_loads(target.read_text(encoding="utf-8"))
    assert loaded == {"alpha": 1, "beta": [2, 3]}

    # Reject non-finite floats
    with pytest.raises(ValueError):
        atomic_json(tmp_path / "nan.json", {"bad": math.nan})
    with pytest.raises(ValueError):
        atomic_json(tmp_path / "inf.json", {"bad": math.inf})
    with pytest.raises(ValueError, match="Strict finite JSON"):
        strict_json_loads('{"bad": NaN}')
    with pytest.raises(ValueError, match="Strict finite JSON"):
        strict_json_loads('{"bad": Infinity}')

    # Reject symlinks
    sym = tmp_path / "sym_target.json"
    sym.symlink_to(target)
    with pytest.raises(ValueError, match="Symlink rejected"):
        atomic_json(sym, {"new": 1})


def test_root_locking_and_concurrency(tmp_path):
    with _flock_root(tmp_path):
        with pytest.raises(RuntimeError, match="Coordinator already active"):
            with _flock_root(tmp_path):
                pass
    with _flock_root(tmp_path):
        pass


def test_controls_validation_and_mismatch(tmp_path):
    build1 = make_test_build()
    ctrls1 = make_controls(build1)
    validated = validate_controls(ctrls1)
    assert validated == ctrls1

    # Invalid controls missing build
    with pytest.raises(ValueError):
        validate_controls({"schema": "bad"})

    # Mismatch on resume
    def noop_factory(idx, seed, ckpt):
        return [sys.executable, "-c", "import sys; sys.exit(0)"]

    ingest(tmp_path, ctrls1, stop_after=0, command_factory=noop_factory)
    build2 = make_test_build(source_sha="9" * 64)
    ctrls2 = make_controls(build2)
    with pytest.raises(ValueError, match="Controls mismatch on resume"):
        ingest(tmp_path, ctrls2, resume=True, stop_after=0, command_factory=noop_factory)


def test_symlink_paths_rejected(tmp_path):
    build = make_test_build()
    ctrls = make_controls(build)

    real_root = tmp_path / "real_dir"
    real_root.mkdir()
    sym_root = tmp_path / "sym_dir"
    sym_root.symlink_to(real_root)

    def noop_factory(idx, seed, ckpt):
        return [sys.executable, "-c", "import sys; sys.exit(0)"]

    with pytest.raises(ValueError, match="Symlink rejected"):
        ingest(sym_root, ctrls, stop_after=1, command_factory=noop_factory)


def test_observation_validation_complete_vs_partial(tmp_path):
    build = make_test_build()
    seed = "12345"
    obs_identity = dict(build['identity'], seed=seed)

    # 1. Tiny valid empty observation -> partial
    obs_empty = empty_observation(obs_identity)
    ckpt_empty = tmp_path / "ckpt_empty.json"
    atomic_json(ckpt_empty, obs_empty)
    status, reason, progress = _validate_child_observation(ckpt_empty, seed, build['identity'])
    assert status == 'partial'
    assert reason == 'incomplete_features'
    assert all(progress[f] == 'unknown' for f in progress)

    # 2. Complete observation with all 23 features -> complete
    obs_comp = make_complete_observation(seed, build['identity'])
    ckpt_comp = tmp_path / "ckpt_comp.json"
    atomic_json(ckpt_comp, obs_comp)
    status2, reason2, progress2 = _validate_child_observation(ckpt_comp, seed, build['identity'])
    assert status2 == 'complete'
    assert reason2 is None
    assert all(progress2[f] == 'complete' for f in progress2)

    # 3. Seed mismatch -> error
    with pytest.raises(ValueError, match="Seed mismatch"):
        _validate_child_observation(ckpt_comp, "99999", build['identity'])

    # 4. Build identity mismatch -> error
    bad_build = dict(build['identity'], model_id='unknown-model')
    with pytest.raises(ValueError, match="Build identity mismatch"):
        _validate_child_observation(ckpt_comp, seed, bad_build)


def test_ingest_synthetic_stubs_accounting(tmp_path):
    root = tmp_path / "stubs_run"
    build = make_test_build()
    ctrls = make_controls(build)

    def stub_factory(index, seed, checkpoint_path):
        if index == 0:
            # Complete world
            script = (
                f"from tests.catalog.test_ingestion import make_complete_observation\n"
                f"from seed_search.catalog.ingestion import atomic_json\n"
                f"build_id = {build['identity']}\n"
                f"obs = make_complete_observation('{seed}', build_id)\n"
                f"atomic_json('{checkpoint_path}', obs)\n"
            )
            return [sys.executable, "-c", script]
        elif index == 1:
            # Partial world (empty obs)
            script = (
                f"from seed_search.catalog.ingestion import atomic_json\n"
                f"from seed_search.catalog.models import empty_observation\n"
                f"build_id = {build['identity']}\n"
                f"obs = empty_observation(dict(build_id, seed='{seed}'))\n"
                f"atomic_json('{checkpoint_path}', obs)\n"
            )
            return [sys.executable, "-c", script]
        elif index == 2:
            # Process failure
            return [sys.executable, "-c", "import sys; sys.exit(7)"]
        else:
            return [sys.executable, "-c", "import sys; sys.exit(0)"]

    report = ingest(root, ctrls, stop_after=3, command_factory=stub_factory)
    assert report['summary']['total_seeds'] == 100
    assert report['summary']['completed'] == 1
    assert report['summary']['partial'] == 1
    assert report['summary']['failed'] == 1
    assert report['summary']['pending'] == 97
    assert len(report['receipts']) == 100

    r0 = report['receipts'][0]
    assert r0['status'] == 'complete'
    assert r0['exit'] == 0
    assert r0['stopreason'] is None
    assert r0['wall'] > 0
    assert r0['peak_rss'] > 0

    r1 = report['receipts'][1]
    assert r1['status'] == 'partial'
    assert r1['exit'] == 0
    assert r1['stopreason'] == 'incomplete_features'

    r2 = report['receipts'][2]
    assert r2['status'] == 'failed'
    assert r2['exit'] == 7
    assert r2['stopreason'] == 'exit_7'

    r3 = report['receipts'][3]
    assert r3['status'] == 'pending'
    assert r3['attempts'] == 0


def test_preflight_10_and_resume_budget_idempotence(tmp_path):
    root = tmp_path / "preflight_run"
    build = make_test_build()
    ctrls = make_controls(build)

    def stub_factory(index, seed, checkpoint_path):
        script = (
            f"from seed_search.catalog.ingestion import atomic_json\n"
            f"from seed_search.catalog.models import empty_observation\n"
            f"build_id = {build['identity']}\n"
            f"obs = empty_observation(dict(build_id, seed='{seed}'))\n"
            f"atomic_json('{checkpoint_path}', obs)\n"
        )
        return [sys.executable, "-c", script]

    # Preflight: stop_after=10
    rep1 = ingest(root, ctrls, stop_after=10, command_factory=stub_factory)
    assert rep1['summary']['partial'] == 10
    assert rep1['summary']['pending'] == 90
    assert rep1['summary']['stopped_reason'] == 'stop_after'
    spent1 = rep1['summary']['cumulative_extract_seconds']
    assert spent1 > 0

    # Resume: stop_after=12 on same ledger
    rep2 = ingest(root, ctrls, resume=True, stop_after=12, command_factory=stub_factory)
    assert rep2['summary']['partial'] == 12
    assert rep2['summary']['pending'] == 88
    spent2 = rep2['summary']['cumulative_extract_seconds']
    assert spent2 >= spent1


def test_conservative_budget_prediction(tmp_path):
    root = tmp_path / "budget_pred_run"
    build = make_test_build()
    ctrls = make_controls(build)

    def stub_factory(index, seed, checkpoint_path):
        script = (
            f"import time\n"
            f"from seed_search.catalog.ingestion import atomic_json\n"
            f"from seed_search.catalog.models import empty_observation\n"
            f"build_id = {build['identity']}\n"
            f"time.sleep(0.04)\n"
            f"obs = empty_observation(dict(build_id, seed='{seed}'))\n"
            f"atomic_json('{checkpoint_path}', obs)\n"
        )
        return [sys.executable, "-c", script]

    # 10 worlds complete
    rep1 = ingest(root, ctrls, stop_after=10, command_factory=stub_factory)
    assert rep1['summary']['partial'] == 10

    # Simulate near-cap cumulative budget before resume
    ledger_path = root / "ledger.json"
    ledger = strict_json_loads(ledger_path.read_text())
    ledger['cumulative_extract_seconds'] = 898.0
    atomic_json(ledger_path, ledger)

    rep2 = ingest(root, ctrls, resume=True, stop_after=100, command_factory=stub_factory)
    assert rep2['summary']['stopped_reason'] == 'budget_predicted'
    assert rep2['receipts'][10]['status'] == 'pending'


def test_resource_limits_wall_timeout_memory_output(tmp_path, monkeypatch):
    build = make_test_build()
    ctrls = make_controls(build)

    def stub_sleep(idx, seed, ckpt):
        return [sys.executable, "-c", "import time; time.sleep(10)"]

    # 1. Wall timeout
    real_monotonic = time.monotonic
    calls = 0
    t0 = real_monotonic()
    def fake_monotonic():
        nonlocal calls
        calls += 1
        if calls > 2:
            return t0 + 35.0
        return t0

    monkeypatch.setattr(time, "monotonic", fake_monotonic)
    rep_wall = ingest(tmp_path / "wall", ctrls, stop_after=1, command_factory=stub_sleep, poll_seconds=0.01)
    assert rep_wall['receipts'][0]['status'] == 'failed'
    assert rep_wall['receipts'][0]['stopreason'] == 'wall_timeout'

    # 2. Memory limit
    monkeypatch.undo()
    monkeypatch.setattr("seed_search.catalog.ingestion._get_aggregate_rss", lambda pid: (5 << 30))
    rep_mem = ingest(tmp_path / "mem", ctrls, stop_after=1, command_factory=stub_sleep, poll_seconds=0.01)
    assert rep_mem['receipts'][0]['status'] == 'failed'
    assert rep_mem['receipts'][0]['stopreason'] == 'memory_limit'

    # 3. Output limit
    monkeypatch.undo()
    monkeypatch.setattr("seed_search.catalog.ingestion._get_checkpoint_size", lambda p: (3 << 30))
    rep_out = ingest(tmp_path / "out", ctrls, stop_after=1, command_factory=stub_sleep, poll_seconds=0.01)
    assert rep_out['receipts'][0]['status'] == 'failed'
    assert rep_out['receipts'][0]['stopreason'] == 'output_limit'


def test_bounded_retries_and_checkpoint_reuse(tmp_path):
    root = tmp_path / "reuse_run"
    build = make_test_build()
    ctrls = make_controls(build)

    def stub_factory(idx, seed, ckpt):
        # On attempt 1: only structures -> partial
        # On attempt 2: reuse checkpoint, add biomes -> complete!
        script = (
            f"import os\n"
            f"from seed_search.catalog.ingestion import atomic_json, strict_json_loads\n"
            f"from seed_search.catalog.models import empty_observation\n"
            f"from seed_search.catalog.registry import STRUCTURES, BIOMES, ENVELOPE\n"
            f"from seed_search.catalog.coverage import STRUCTURE_METHOD, BIOME_METHOD\n"
            f"build_id = {build['identity']}\n"
            f"if not os.path.exists('{ckpt}'):\n"
            f"    obs = empty_observation(dict(build_id, seed='{seed}'))\n"
            f"    for st in STRUCTURES:\n"
            f"        obs['structures'][st['id']] = []\n"
            f"        obs['coverage'][st['id']] = {{'status': 'complete', 'bounds': list(ENVELOPE), 'method_id': STRUCTURE_METHOD}}\n"
            f"    atomic_json('{ckpt}', obs)\n"
            f"else:\n"
            f"    with open('{ckpt}', 'r') as f: obs = strict_json_loads(f.read())\n"
            f"    obs['biome_names'] = {{'1': 'plains'}}\n"
            f"    obs['biomes'] = [[x, 63, z, 1] for x in range(-5120, 5120, 64) for z in range(-5120, 5120, 64)]\n"
            f"    for bm in BIOMES:\n"
            f"        obs['coverage'][bm['id']] = {{'status': 'complete', 'bounds': list(ENVELOPE), 'method_id': BIOME_METHOD}}\n"
            f"    atomic_json('{ckpt}', obs)\n"
        )
        return [sys.executable, "-c", script]

    # Attempt 1 -> partial
    rep1 = ingest(root, ctrls, stop_after=1, command_factory=stub_factory)
    assert rep1['receipts'][0]['status'] == 'partial'
    assert rep1['receipts'][0]['attempts'] == 1

    # Attempt 2 -> child reuses checkpoint and completes -> complete!
    rep2 = ingest(root, ctrls, resume=True, stop_after=1, command_factory=stub_factory)
    assert rep2['receipts'][0]['status'] == 'complete'
    assert rep2['receipts'][0]['attempts'] == 2

    # Attempt 3 -> complete world skipped
    rep3 = ingest(root, ctrls, resume=True, stop_after=1, command_factory=stub_factory)
    assert rep3['receipts'][0]['status'] == 'complete'
    assert rep3['receipts'][0]['attempts'] == 2


def test_stale_pid_safety_on_resume(tmp_path):
    root = tmp_path / "stale_run"
    build = make_test_build()
    ctrls = make_controls(build)

    def noop_factory(idx, seed, ckpt):
        return [sys.executable, "-c", "import sys; sys.exit(0)"]

    ingest(root, ctrls, stop_after=0, command_factory=noop_factory)
    ledger_path = root / "ledger.json"
    ledger = strict_json_loads(ledger_path.read_text())

    # Dead PID
    ledger["active_lease"] = {
        "index": 0,
        "seed": ctrls["cohort"][0],
        "pid": 999999,
        "pgid": 999999,
        "cmd": ["python3"],
        "start_time": time.time(),
        "create_time": 1000.0,
        "reserved": 30.0,
    }
    atomic_json(ledger_path, ledger)
    rep_a = ingest(root, ctrls, resume=True, stop_after=0, command_factory=noop_factory)
    assert rep_a["receipts"][0]["status"] == "failed"

    # Live PID with mismatching creation metadata
    ledger = strict_json_loads(ledger_path.read_text())
    ledger["active_lease"] = {
        "index": 1,
        "seed": ctrls["cohort"][1],
        "pid": os.getpid(),
        "pgid": os.getpid() + 10000,
        "cmd": ["other_cmd"],
        "start_time": time.time(),
        "create_time": 123.0,
        "reserved": 30.0,
    }
    atomic_json(ledger_path, ledger)
    with pytest.raises(RuntimeError, match="refusing to kill"):
        ingest(root, ctrls, resume=True, stop_after=0, command_factory=noop_factory)

    # Live PID with matching owned process group -> terminated cleanly
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"], start_new_session=True)
    child_meta = _get_process_creation_meta(child.pid)
    ledger = strict_json_loads(ledger_path.read_text())
    ledger["active_lease"] = {
        "index": 1,
        "seed": ctrls["cohort"][1],
        "pid": child.pid,
        "pgid": os.getpgid(child.pid),
        "cmd": [sys.executable],
        "start_time": time.time(),
        "create_time": child_meta.get("create_time"),
        "reserved": 30.0,
    }
    atomic_json(ledger_path, ledger)
    rep_c = ingest(root, ctrls, resume=True, stop_after=0, command_factory=noop_factory)
    ret = child.wait(timeout=2)
    assert ret == -signal.SIGKILL
    assert rep_c["receipts"][1]["status"] == "failed"


def test_sigkill_parent_recovery_at_checkpoint_boundary(tmp_path):
    root = tmp_path / "sigkill_parent_run"
    build = make_test_build()
    ctrls = make_controls(build)

    coordinator_code = (
        f"import sys, os, signal\n"
        f"from seed_search.catalog.ingestion import ingest\n"
        f"from seed_search.catalog.validation_contracts import controls as make_controls\n"
        f"build = {build}\n"
        f"ctrls = make_controls(build)\n"
        f"parent_pid = os.getpid()\n"
        f"def stub_factory(idx, seed, ckpt):\n"
        f"    script = (\n"
        f"        'import os, signal\\n'\n"
        f"        'from seed_search.catalog.ingestion import atomic_json\\n'\n"
        f"        'from seed_search.catalog.models import empty_observation\\n'\n"
        f"        f'build_id = {{build[\"identity\"]}}\\n'\n"
        f"        f'obs = empty_observation(dict(build_id, seed=\"{{seed}}\"))\\n'\n"
        f"        f'atomic_json(\"{{ckpt}}\", obs)\\n'\n"
        f"        f'os.kill({{parent_pid}}, signal.SIGKILL)\\n'\n"
        f"    )\n"
        f"    return [sys.executable, '-c', script]\n"
        f"ingest('{root}', ctrls, stop_after=1, command_factory=stub_factory, poll_seconds=0.01)\n"
    )

    parent_proc = subprocess.Popen([sys.executable, "-c", coordinator_code])
    ret = parent_proc.wait(timeout=10)
    assert ret == -signal.SIGKILL

    ledger = strict_json_loads((root / "ledger.json").read_text())
    assert ledger["active_lease"] is not None
    assert ledger["active_lease"]["index"] == 0
    reserved_spent = ledger["cumulative_extract_seconds"]
    assert reserved_spent >= 30.0

    def normal_stub_factory(idx, seed, ckpt):
        script = (
            f"from seed_search.catalog.ingestion import atomic_json\n"
            f"from seed_search.catalog.models import empty_observation\n"
            f"build_id = {build['identity']}\n"
            f"obs = empty_observation(dict(build_id, seed='{seed}'))\n"
            f"atomic_json('{ckpt}', obs)\n"
        )
        return [sys.executable, "-c", script]

    report = ingest(root, ctrls, resume=True, stop_after=2, command_factory=normal_stub_factory, poll_seconds=0.01)
    assert report['summary']['cumulative_extract_seconds'] >= reserved_spent
    assert report['receipts'][0]['status'] == 'partial'
    recovered_ledger = strict_json_loads((root / "ledger.json").read_text())
    assert recovered_ledger["active_lease"] is None
