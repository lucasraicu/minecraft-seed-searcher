"""Comprehensive tests for Web Server Backend & Telemetry Hardening."""
import io
import json
import os
import resource
import shutil
import sqlite3
import subprocess
import sys
import threading
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest
import yaml

from seed_search.realm import resources, runner
from seed_search.web import server


class FakeProc:
    def __init__(self):
        self.stdout = io.StringIO('{"completed_seeds": 1000}\n')
        self.stderr = io.StringIO('')
        self.returncode = 0
        self.killed = False
        self.waited_timeout = None

    def poll(self):
        return None if not self.killed else self.returncode

    def wait(self, timeout=None):
        self.waited_timeout = timeout
        return self.returncode

    def terminate(self):
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9


def test_start_sweep_cleanup_on_popen_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(server, 'RUNS_DIR', tmp_path)

    def fail_popen(*args, **kwargs):
        raise OSError("Exec format error")

    monkeypatch.setattr(server.subprocess, 'Popen', fail_popen)

    manager = server.SweepManager()
    result = manager.start_sweep(count=1)
    assert not result['ok']
    assert "Exec format error" in result['error']
    assert manager.status == "error"
    assert manager.process is None
    # Partial directory must be cleaned up
    run_dir = tmp_path / manager.run_id
    assert not run_dir.exists()

    # Verify locks were released and manager can attempt next sweep
    monkeypatch.setattr(server.subprocess, 'Popen', lambda *a, **kw: FakeProc())
    success = manager.start_sweep(count=1)
    assert success['ok']
    assert manager.status == "running"
    manager.stop_sweep()


def test_stop_sweep_kills_and_waits_and_guards_racing_start(monkeypatch, tmp_path):
    monkeypatch.setattr(server, 'RUNS_DIR', tmp_path)
    manager = server.SweepManager()
    proc = FakeProc()
    manager.process = proc
    manager.status = "running"
    manager.run_id = "test-run"

    res = manager.stop_sweep()
    assert res['ok']
    assert res['status'] == "stopped"
    assert proc.killed is True
    assert proc.waited_timeout == 2.0
    assert manager.process is None
    assert manager.status == "stopped"

    # Verify that stopping status guards against concurrent start
    manager.status = "stopping"
    start_res = manager.start_sweep(count=1)
    assert not start_res['ok']
    assert "currently stopping" in start_res['error']


def test_dead_prng_functions_deleted():
    assert not hasattr(server, 'predict_candidate_ravines')
    assert not hasattr(server, 'predict_candidate_cave_clusters')
    assert not hasattr(server, 'get_curated_or_historical_candidates')


def test_telemetry_rss_platform_scaling(monkeypatch):
    manager = server.SweepManager()
    manager.status = "running"

    class MockProc:
        pid = 12345
        def poll(self): return None

    manager.process = MockProc()

    # Simulate process_tree_resources unavailable so it falls back to RUSAGE_SELF
    monkeypatch.setattr(server, 'process_tree_resources', lambda pid: {'available': False})

    # SELF RSS belongs to the website and cannot stand in for the scan child.
    status = manager.get_status()
    assert status['memoryRssGib'] is None


def test_candidate_canonical_ranking_and_tristate_terrain(tmp_path):
    manager = server.SweepManager()
    run_dir = tmp_path / "web-sweep-canonical"
    run_dir.mkdir()
    manager.run_dir = run_dir

    db_path = run_dir / "realm.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE candidates (id TEXT PRIMARY KEY, idx TEXT, seed TEXT, qualification TEXT, result TEXT)")
        conn.execute("CREATE TABLE variants (candidate_id TEXT, variant TEXT, center TEXT, result TEXT, PRIMARY KEY(candidate_id, variant, center))")
        conn.execute("""
            CREATE VIEW candidate_leaderboard_view AS
            SELECT id, idx, seed, qualification, result,
                   CAST(json_extract(result, '$.retention.classification') AS TEXT) AS retention_classification,
                   CAST(json_extract(result, '$.ranking_tier') AS INTEGER) AS ranking_tier,
                   CAST(json_extract(result, '$.unmet_requirements') AS INTEGER) AS unmet_requirements,
                   CAST(json_extract(result, '$.smart_score') AS REAL) AS smart_score
            FROM candidates
        """)

        # Insert 3 candidates with different ranking tiers and unmet requirements
        # Candidate 1: Tier 1, unmet 1, score 80
        cand1_result = {
            "ranking_tier": 1, "unmet_requirements": 1, "smart_score": 80.0,
            "marine_stage": {"status": "DEFERRED"}
        }
        # Candidate 2: Tier 0, unmet 0, score 95
        cand2_result = {
            "ranking_tier": 0, "unmet_requirements": 0, "smart_score": 95.0,
            "marine_stage": {"status": "PREDICTED"}
        }
        # Candidate 3: Tier 1, unmet 0, score 70
        cand3_result = {
            "ranking_tier": 1, "unmet_requirements": 0, "smart_score": 70.0,
            "marine_stage": {"status": "DEFERRED"}
        }

        conn.execute("INSERT INTO candidates VALUES ('c1', '0', '1001', 'PREDICTED', ?)", (json.dumps(cand1_result),))
        conn.execute("INSERT INTO candidates VALUES ('c2', '1', '1002', 'VERIFIED', ?)", (json.dumps(cand2_result),))
        conn.execute("INSERT INTO candidates VALUES ('c3', '2', '1003', 'PREDICTED', ?)", (json.dumps(cand3_result),))

        # Variants:
        # c2 has passed terrain (geometry_pass = 1)
        conn.execute("INSERT INTO variants VALUES ('c2', 'v1', '[0,0]', ?)",
                     (json.dumps({"result": {"geometry_pass": 1}}),))
        # c1 has failed terrain (geometry_pass = 0)
        conn.execute("INSERT INTO variants VALUES ('c1', 'v1', '[0,0]', ?)",
                     (json.dumps({"result": {"geometry_pass": 0}}),))
        # c3 has no variant row -> pending

    manager._query_sqlite_candidates()
    cands = manager.candidates
    assert len(cands) == 3

    # Canonical order: ORDER BY ranking_tier, unmet_requirements, smart_score DESC, id
    # 1st should be c2 (tier 0, unmet 0, score 95)
    # 2nd should be c3 (tier 1, unmet 0, score 70)
    # 3rd should be c1 (tier 1, unmet 1, score 80)
    assert [c['seed'] for c in cands] == ['1002', '1003', '1001']

    c2 = cands[0]
    assert c2['rankingTier'] == 0
    assert c2['unmetRequirements'] == 0
    assert c2['terrainPassed'] is True
    assert c2['terrainStatus'] == 'passed'
    # Crucial: marineStatus must NOT be automatically overwritten to EVALUATED on terrain pass
    assert c2['marineStatus'] == 'PREDICTED'

    c3 = cands[1]
    assert c3['rankingTier'] == 1
    assert c3['unmetRequirements'] == 0
    assert c3['terrainPassed'] is None
    assert c3['terrainStatus'] == 'pending'

    c1 = cands[2]
    assert c1['rankingTier'] == 1
    assert c1['unmetRequirements'] == 1
    assert c1['terrainPassed'] is False
    assert c1['terrainStatus'] == 'failed'


def test_list_runs_mtime_caching(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'RUNS_DIR', tmp_path)
    from test_web_server_evidence import make_saved_web_run

    name, directory = make_saved_web_run(tmp_path)
    manager = server.SweepManager()

    call_count = [0]
    orig_saved_run = manager._saved_run

    def tracked_saved_run(run_id):
        call_count[0] += 1
        return orig_saved_run(run_id)

    monkeypatch.setattr(manager, '_saved_run', tracked_saved_run)

    # First call must populate cache
    runs1 = manager.list_runs()
    assert len(runs1['runs']) == 1
    assert call_count[0] == 1

    # Second call should use cache
    runs2 = manager.list_runs()
    assert len(runs2['runs']) == 1
    assert call_count[0] == 1


def test_process_tree_resources_and_sample_memory_graceful_fallback(monkeypatch):
    # Simulate ps -axo failing
    def fail_ps(*args, **kwargs):
        raise OSError("ps command not permitted in sandbox")

    monkeypatch.setattr(runner.subprocess, 'run', fail_ps)

    # 1. process_tree_resources fallback
    res = runner.process_tree_resources()
    assert res['available'] is False
    assert res['fallback'] == 'rusage_self'
    assert res['rss_bytes'] > 0

    # resources.py wrapper also works
    res_mod = resources.process_tree_resources()
    assert res_mod['available'] is False
    assert res_mod['fallback'] == 'rusage_self'

    # For other PIDs, ps failure returns available: False
    res_other = runner.process_tree_resources(99999)
    assert res_other['available'] is False
    assert 'rss_bytes' not in res_other


def test_post_security_validation():
    from unittest.mock import MagicMock

    class MockHandler:
        def __init__(self, path, headers=None, body=b''):
            self.rfile = io.BytesIO(body)
            self.wfile = io.BytesIO()
            self.path = path
            self.headers = headers or {}
            self.server = MagicMock(server_port=3000)
            self.responses = []
            self.resp_headers = []

        def send_response(self, code, message=None):
            self.responses.append(code)

        def send_header(self, keyword, value):
            self.resp_headers.append((keyword, value))

        def end_headers(self):
            pass

    # 1. Sec-Fetch-Site: cross-site -> 403
    h_sec = MockHandler('/api/sweep/start', {'Sec-Fetch-Site': 'cross-site'})
    server.WebSearchHandler.do_POST(h_sec)
    assert h_sec.responses[0] == 403
    assert 'Cross-site' in json.loads(h_sec.wfile.getvalue().decode())['error']

    # 2. Disallowed Origin -> 403
    h_origin = MockHandler('/api/sweep/start', {'Origin': 'http://evil.com'})
    server.WebSearchHandler.do_POST(h_origin)
    assert h_origin.responses[0] == 403
    assert 'Origin is not allowed' in json.loads(h_origin.wfile.getvalue().decode())['error']

    # 3. Disallowed Referer -> 403
    h_ref = MockHandler('/api/sweep/start', {'Referer': 'http://evil.com/page'})
    server.WebSearchHandler.do_POST(h_ref)
    assert h_ref.responses[0] == 403
    assert 'Referer is not allowed' in json.loads(h_ref.wfile.getvalue().decode())['error']

    # 4. Allowed Origin localhost:3000 -> accepted
    h_good_orig = MockHandler('/api/sweep/stop', {'Origin': 'http://localhost:3000'})
    server.WebSearchHandler.do_POST(h_good_orig)
    assert h_good_orig.responses[0] == 200

    # 5. Bodyless /api/sweep/stop with missing Content-Length -> 200, safe handling
    h_no_cl = MockHandler('/api/sweep/stop', {})
    server.WebSearchHandler.do_POST(h_no_cl)
    assert h_no_cl.responses[0] == 200
    assert json.loads(h_no_cl.wfile.getvalue().decode())['ok'] is False  # no active sweep

    # 6. Bodyless /api/sweep/stop with Content-Length: 0 -> 200
    h_cl_zero = MockHandler('/api/sweep/stop', {'Content-Length': '0'})
    server.WebSearchHandler.do_POST(h_cl_zero)
    assert h_cl_zero.responses[0] == 200

    # The website cannot launch terrain filtering in baseline-only mode.
    h_terrain = MockHandler('/api/terrain/start', {'Content-Length': '2'}, b'{}')
    server.WebSearchHandler.do_POST(h_terrain)
    assert h_terrain.responses[0] == 404


def test_candidate_biome_grid_endpoint():
    from unittest.mock import MagicMock

    class MockGetHandler:
        def __init__(self, path):
            self.path = path
            self.wfile = io.BytesIO()
            self.headers = {}
            self.server = MagicMock(server_port=3000)
            self.responses = []

        def send_response(self, code, message=None):
            self.responses.append(code)

        def send_header(self, k, v):
            pass

        def end_headers(self):
            pass

    # 1. Missing seed -> 400
    h_bad = MockGetHandler('/api/candidate/biome-grid')
    server.WebSearchHandler.do_GET(h_bad)
    assert h_bad.responses[0] == 400

    # 2. Valid seed -> 200 with authentic grid and names
    h_good = MockGetHandler('/api/candidate/biome-grid?seed=12345&dimension=overworld')
    server.WebSearchHandler.do_GET(h_good)
    assert h_good.responses[0] == 200
    data = json.loads(h_good.wfile.getvalue().decode())
    assert data['ok'] is True
    assert data['seed'] == '12345'
    assert len(data['grid']) == 65
    assert len(data['grid'][0]) == 65
    assert 'names' in data
    assert data['approx_height'] is None


def test_biome_grid_river_prediction_never_requests_terrain(monkeypatch):
    import numpy as np
    from seed_search import backend

    class BiomeOnlyBackend:
        def __init__(self, seed):
            assert seed == 456

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def grid(self, **kwargs):
            raise AssertionError('Terrain grid must not run')

        def biome_points(self, points, dimension):
            assert dimension == 0 and len(points) == 65 * 65
            values = np.zeros(len(points), dtype=np.int32)
            values[0] = 7
            values[1] = 8
            return values

    monkeypatch.setattr(backend, 'Backend', BiomeOnlyBackend)
    monkeypatch.setattr(backend, 'biome_name', lambda value: {0: 'plains', 7: 'river', 8: 'frozen_river'}[value])
    server.MANAGER._biome_grid_cache.clear()

    class Handler:
        path = '/api/candidate/biome-grid?seed=456&dimension=overworld'
        wfile = io.BytesIO()
        responses = []
        def send_response(self, code, message=None):
            self.responses.append(code)
        def send_header(self, key, value):
            pass
        def end_headers(self):
            pass

    handler = Handler()
    server.WebSearchHandler.do_GET(handler)
    data = json.loads(handler.wfile.getvalue())
    assert handler.responses == [200]
    assert data['names']['7'] == 'river' and data['names']['8'] == 'frozen_river'
    assert data['approx_height'] is None
