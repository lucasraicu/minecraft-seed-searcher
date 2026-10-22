"""
Contract tests for lightweight truthful backend telemetry and candidate pagination.

Verified requirements:
1. GET /api/sweep/status returns statusSchemaVersion=2, runtimeIdentity immutable per-process dict,
   generation numeric, candidatePageUrl='/api/candidates', and candidates=[] as deprecated compatibility field.
2. status does NOT compute candidate payloads or scan/parse candidate rows.
3. Accurate candidate count via lightweight DB progress/count query.
4. Read-only candidate pagination runs outside manager control lock.
5. Concurrent run switch during candidate page read returns snapshot identity and prevents stale publication.
"""

import json
import os
import sqlite3
import threading
from pathlib import Path

import pytest

import seed_search.web.server as server
from seed_search.web.server import SweepManager, RUNTIME_IDENTITY


@pytest.fixture(autouse=True)
def isolated_saved_runs(tmp_path, monkeypatch):
    # Never bind a developer's live checkpoint while testing status contracts.
    monkeypatch.setattr(server, 'RUNS_DIR', tmp_path / 'saved-runs')


def _create_mock_run(tmp_path: Path, run_id: str, completed: int = 25000, num_candidates: int = 5) -> Path:
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    db_path = run_dir / "realm.sqlite"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("INSERT INTO meta (key, value) VALUES ('completed_seeds', ?)", (str(completed),))
    identity = {
        "count": 100000,
        "start_index": 0,
        "execution": "native",
        "config": {"search": {"max_misses": 0}}
    }
    cur.execute("INSERT INTO meta (key, value) VALUES ('identity', ?)", (json.dumps(identity),))

    cur.execute("""
        CREATE TABLE candidates (
            id TEXT PRIMARY KEY,
            seed TEXT,
            score REAL,
            result TEXT
        )
    """)

    cur.execute("""
        CREATE VIEW candidate_leaderboard_view AS
        SELECT id, seed, score AS smart_score, result, 0 AS ranking_tier, 0 AS unmet_requirements
        FROM candidates
    """)

    for i in range(num_candidates):
        cand_payload = {
            "id": f"cand-{i}",
            "seed": str(1000000 + i),
            "combined_score": round(95.0 - i, 1),
            "evaluation_center": [0, 0],
            "required_structures": {},
            "qualification": "PREDICTED",
        }
        cur.execute(
            "INSERT INTO candidates (id, seed, score, result) VALUES (?, ?, ?, ?)",
            (f"cand-{i}", str(1000000 + i), round(95.0 - i, 1), json.dumps(cand_payload))
        )

    conn.commit()
    conn.close()
    return run_dir


def test_bounded_v2_payload_and_immutable_identity():
    manager = SweepManager()
    status = manager.get_status()

    # Schema version 2
    assert status["statusSchemaVersion"] == 2
    assert isinstance(status["generation"], int)
    assert status["candidatePageUrl"] == "/api/candidates"
    assert status["candidates"] == []

    # Runtime identity
    runtime_id = status["runtimeIdentity"]
    assert isinstance(runtime_id, dict)
    assert isinstance(runtime_id["processStartedAt"], (int, float))
    assert runtime_id["processStartedAt"] > 0
    assert runtime_id["pid"] == os.getpid()
    assert isinstance(runtime_id["loadedServerSourceSha256"], str)
    assert len(runtime_id["loadedServerSourceSha256"]) == 64

    # Native build identity truthful attribution
    native_build = runtime_id["nativeBuild"]
    assert isinstance(native_build, dict)
    assert native_build["source"] == "selected_on_disk"
    assert "path" in native_build

    # Bounded payload check
    raw_status = json.dumps(status)
    assert len(raw_status) < 4096

    # Immutability check
    runtime_id["pid"] = -999
    runtime_id["nativeBuild"]["source"] = "mutated"
    fresh_status = manager.get_status()
    assert fresh_status["runtimeIdentity"]["pid"] == os.getpid()
    assert fresh_status["runtimeIdentity"]["nativeBuild"]["source"] == "selected_on_disk"
    assert RUNTIME_IDENTITY["pid"] == os.getpid()


def test_status_does_not_invoke_candidate_parser(tmp_path, monkeypatch):
    run_dir = _create_mock_run(tmp_path, "web-sweep-20261020-000001-11111111", completed=12000, num_candidates=8)

    manager = SweepManager()
    manager.run_dir = run_dir
    manager.run_id = run_dir.name
    manager.status = "running"
    manager.start_time = 1.0

    parse_call_count = 0
    original_parser = server.parse_candidate_row

    def tracking_parser(*args, **kwargs):
        nonlocal parse_call_count
        parse_call_count += 1
        return original_parser(*args, **kwargs)

    monkeypatch.setattr(server, "parse_candidate_row", tracking_parser)

    # Calling get_status MUST NOT parse candidate rows
    status = manager.get_status()
    assert parse_call_count == 0
    assert status["candidates"] == []
    assert status["candidatesFound"] == 8

    # Explicit opt-in invokes parser on-demand
    status_opt_in = manager.get_status(include_candidates=True)
    assert parse_call_count == 8
    assert len(status_opt_in["candidates"]) == 8


def test_candidate_count_accuracy_without_scanning(tmp_path, monkeypatch):
    run_dir = _create_mock_run(tmp_path, "web-sweep-20261020-000002-22222222", completed=45000, num_candidates=14)

    manager = SweepManager()
    manager.run_dir = run_dir
    manager.run_id = run_dir.name

    parse_call_count = 0
    original_parser = server.parse_candidate_row

    def tracking_parser(*args, **kwargs):
        nonlocal parse_call_count
        parse_call_count += 1
        return original_parser(*args, **kwargs)

    monkeypatch.setattr(server, "parse_candidate_row", tracking_parser)

    # Refresh via progress query
    manager._query_sqlite_progress()
    assert manager.scanned_count == 45000
    assert manager.candidate_total == 14
    assert parse_call_count == 0

    # Dedicated lightweight count query
    manager.candidate_total = 0
    manager._query_sqlite_candidate_count()
    assert manager.candidate_total == 14
    assert parse_call_count == 0

    # Status matches count accurately
    status = manager.get_status()
    assert status["totalScanned"] == 45000
    assert status["candidatesFound"] == 14
    assert status["candidates"] == []
    assert parse_call_count == 0


def test_read_does_not_block_control_lock(tmp_path, monkeypatch):
    run_dir = _create_mock_run(tmp_path, "web-sweep-20261020-000003-33333333", completed=5000, num_candidates=4)

    manager = SweepManager()
    manager.run_dir = run_dir
    manager.run_id = run_dir.name

    lock_acquired_concurrently = False
    original_read_page = manager._read_candidate_page

    def delayed_read(*args, **kwargs):
        nonlocal lock_acquired_concurrently
        # Attempt non-blocking acquire on manager.lock while read is executing
        acquired = manager.lock.acquire(blocking=False)
        if acquired:
            lock_acquired_concurrently = True
            manager.lock.release()
        return original_read_page(*args, **kwargs)

    monkeypatch.setattr(manager, "_read_candidate_page", delayed_read)

    page = manager.candidate_page(limit=10, offset=0)
    assert lock_acquired_concurrently is True
    assert page["total"] == 4
    assert len(page["candidates"]) == 4


def test_switch_run_during_page_read_returns_snapshot_identity_and_no_stale_publish(tmp_path, monkeypatch):
    run_a = _create_mock_run(tmp_path, "web-sweep-20261020-000004-aaaaaaaa", completed=1000, num_candidates=3)
    run_b = _create_mock_run(tmp_path, "web-sweep-20261020-000005-bbbbbbbb", completed=9000, num_candidates=25)

    manager = SweepManager()
    manager.run_dir = run_a
    manager.run_id = run_a.name
    manager.generation = 1
    manager.candidate_total = 3

    original_read_page = manager._read_candidate_page

    def read_with_run_switch(run_dir, run_id, generation, limit=100, offset=0):
        # When reading Run A, simulate a concurrent run switch to Run B
        if run_id == run_a.name:
            with manager.lock:
                manager.run_dir = run_b
                manager.run_id = run_b.name
                manager.generation = 2
                manager.candidate_total = 25
        return original_read_page(run_dir, run_id, generation, limit, offset)

    monkeypatch.setattr(manager, "_read_candidate_page", read_with_run_switch)

    # Trigger pagination on Run A
    page = manager.candidate_page(limit=10, offset=0)

    # 1. Returned page contains Run A's captured snapshot identity and generation
    assert page["runId"] == run_a.name
    assert page["generation"] == 1
    assert page["total"] == 3
    assert len(page["candidates"]) == 3

    # 2. Manager state on Run B was NOT overwritten with Run A's stale candidate count
    assert manager.run_id == run_b.name
    assert manager.generation == 2
    assert manager.candidate_total == 25


def test_query_sqlite_candidates_compat(tmp_path):
    run_dir = _create_mock_run(tmp_path, "web-sweep-20261020-000006-cccccc", completed=8000, num_candidates=6)
    manager = SweepManager()
    manager.run_dir = run_dir
    manager.run_id = run_dir.name

    # publish=True updates manager.candidates and manager.candidate_total
    res = manager._query_sqlite_candidates(limit=10, offset=0, publish=True)
    assert res["total"] == 6
    assert len(res["candidates"]) == 6
    assert manager.candidate_total == 6
    assert len(manager.candidates) == 6

    # publish=False does not mutate manager.candidates
    manager.candidates = []
    res2 = manager._query_sqlite_candidates(limit=2, offset=0, publish=False)
    assert res2["total"] == 6
    assert len(res2["candidates"]) == 2
    assert manager.candidates == []


def test_http_endpoint_contracts(tmp_path, monkeypatch):
    run_dir = _create_mock_run(tmp_path, "web-sweep-20261020-000007-dddddd", completed=3000, num_candidates=5)
    server.MANAGER.run_dir = run_dir
    server.MANAGER.run_id = run_dir.name
    server.MANAGER.candidate_total = 5

    from io import BytesIO
    from unittest.mock import MagicMock

    handler = server.WebSearchHandler.__new__(server.WebSearchHandler)
    handler.headers = {"Origin": "http://localhost:3000"}
    handler.server = MagicMock()
    handler.server.server_port = 3000

    # 1. Default status GET
    handler.path = "/api/sweep/status"
    handler.wfile = BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_GET()
    payload = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert payload["statusSchemaVersion"] == 2
    assert payload["candidates"] == []
    assert payload["candidatePageUrl"] == "/api/candidates"
    assert payload["candidatesFound"] == 5
    assert payload["runtimeIdentity"]["source"] if "source" in payload["runtimeIdentity"] else payload["runtimeIdentity"]["nativeBuild"]["source"] == "selected_on_disk"

    # 2. Candidate pagination GET
    handler.path = "/api/candidates?limit=2&offset=1"
    handler.wfile = BytesIO()
    handler.do_GET()
    page = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert page["total"] == 5
    assert len(page["candidates"]) == 2
    assert page["offset"] == 1
    assert page["limit"] == 2
    assert page["runId"] == run_dir.name


def test_http_preview_passes_catalog_controls_and_rejects_unknown_fields(monkeypatch):
    from io import BytesIO
    from unittest.mock import MagicMock
    received=[]
    def preview(**kwargs):received.append(kwargs);return {'ok':True}
    monkeypatch.setattr(server.MANAGER,'preview_sweep',preview)
    handler=server.WebSearchHandler.__new__(server.WebSearchHandler)
    handler.server=MagicMock();handler.server.server_port=3000
    handler.path='/api/sweep/preview'
    handler.send_response=MagicMock();handler.send_header=MagicMock();handler.end_headers=MagicMock()
    body={'count':10,'threads':1,'catalogEnabled':True,'catalogRoot':'/configured/catalog'}
    for payload in (body,dict(body,unexpected=True)):
        raw=json.dumps(payload).encode();handler.rfile=BytesIO(raw);handler.wfile=BytesIO()
        handler.headers={'Host':'127.0.0.1:3000','Content-Length':str(len(raw)),'Content-Type':'application/json'}
        handler.do_POST();response=json.loads(handler.wfile.getvalue())
        assert response['ok'] is ('unexpected' not in payload)
    assert len(received)==1 and received[0]['catalog_enabled'] is True
    assert received[0]['catalog_root']=='/configured/catalog'



def test_database_failure_marks_values_stale_without_clearing_them(tmp_path):
    manager = SweepManager()
    manager.run_dir = tmp_path / 'missing-checkpoint'
    manager.run_id = 'missing'
    manager.scanned_count = 123
    manager.candidate_total = 7
    status = manager.get_status()
    assert status['totalScanned'] == 123
    assert status['candidatesFound'] == 7
    assert status['progressReadError']
    assert status['progressUpdatedAt'] is None


def test_runtime_metadata_does_not_embed_unbounded_input_manifest():
    assert 'identity' not in RUNTIME_IDENTITY['nativeBuild']
    assert RUNTIME_IDENTITY['nativeBuild']['loaded'] is False
    assert RUNTIME_IDENTITY['processStartedAtSource'] == 'server_module_initialization'
