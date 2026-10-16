"""UI request -> HTTP preview/start -> saved YAML -> real native CLI parity."""
import http.client
import http.server
import json
import subprocess
import threading
from pathlib import Path

import pytest
import yaml

from test_dynamic_v2_scoring import native_v2
from test_web_server_evidence import FakeProcess
from seed_search.realm.store import RealmStore
from seed_search.web import server

ROOT = Path(__file__).resolve().parents[1]


def test_ui_values_reach_actual_machine_and_resume(monkeypatch, tmp_path, native_v2):
    # Generate the payload with the actual TypeScript helper used by both buttons.
    js = """
const {load,root}=require('./tests/web_test_loader.cjs');
const {INITIAL_CONFIG}=load(root+'/web-ui/src/mockData.ts');
const {buildSweepRequest}=load(root+'/web-ui/src/utils/sweep.ts');
const cfg={...INITIAL_CONFIG,sweepSeedCount:3,startIndex:'9007199254741001',
 openmpThreads:1,batchSize:2,maxMisses:1,structureFloorCounts:{...INITIAL_CONFIG.structureFloorCounts,
 village:10,trial_chamber:9,monument:2,fortress:3,bastion:3}, selectedBiomes:['forest','deep_dark']};
console.log(JSON.stringify(buildSweepRequest(cfg)));
"""
    payload = json.loads(subprocess.run(['node', '-e', js], cwd=ROOT, check=True,
                                        capture_output=True, text=True).stdout)
    runs = tmp_path / 'runs'
    monkeypatch.setattr(server, 'RUNS_DIR', runs)
    monkeypatch.setattr(server, 'DEFAULT_NATIVE_BUILD', native_v2.directory)
    manager = server.SweepManager()
    monkeypatch.setattr(server, 'MANAGER', manager)
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), server.WebSearchHandler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    captured = []
    def post(endpoint, data):
        conn = http.client.HTTPConnection(*httpd.server_address, timeout=10)
        try:
            conn.request('POST', endpoint, json.dumps(data), {'Content-Type': 'application/json'})
            response = conn.getresponse()
            return response.status, json.loads(response.read())
        finally:
            conn.close()
    def capture(command, **kwargs):
        captured.append((command, kwargs))
        return FakeProcess()
    try:
        with monkeypatch.context() as fake:
            fake.setattr(server.subprocess, 'Popen', capture)
            code, preview = post('/api/sweep/preview', payload)
            assert code == 200 and preview['ok']
            assert not runs.exists() and captured == []
            code, launched = post('/api/sweep/start', payload)
            assert code == 200 and launched['ok']
            manager.monitor_thread.join(timeout=5)
        command, kwargs = captured[0]
        assert command == launched['launch']['command'] == launched['command']
        assert preview['effectiveConfig'] == launched['effectiveConfig']
        directory = runs / launched['runId']
        policy = yaml.safe_load((directory / 'policy.yaml').read_text())
        assert policy['biomes']['required_families'] == payload['biomes'] == ['forest','deep_dark']
        assert policy == yaml.safe_load(preview['launch']['policyYaml'])
        assert policy == yaml.safe_load(launched['launch']['policyYaml'])
        targets = {**policy['structures']['minimum_counts'], **policy['structures']['nether_minimum_counts']}
        for key, count in payload['counts'].items():
            assert targets[key] == count
        assert command[command.index('--count')+1] == '3'
        assert command[command.index('--start-index')+1] == payload['startIndex']
        assert command[command.index('--native-threads')+1] == '1'
        assert command[command.index('--native-batch-size')+1] == '2'
        assert command[command.index('--max-misses')+1] == '1'
        assert kwargs['cwd'] == launched['launch']['cwd']
        assert kwargs['env']['PYTHONPATH'] == launched['launch']['environment']['PYTHONPATH']
        assert json.loads((directory/'launch.json').read_text()) == launched['launch']
        # Run the copied command from a different directory; stop after one input
        # to exercise the same saved settings on resume without a large campaign.
        actual = subprocess.run(launched['launch']['shellCommand']+' --stop-after 1', shell=True,
                                cwd=tmp_path, capture_output=True, text=True, timeout=60)
        assert actual.returncode == 0, actual.stderr
        with RealmStore(directory, resume=True) as store:
            assert store.identity['config'] == policy
            assert store.identity['start_index'] == int(payload['startIndex'])
            assert store.status()['completed_seeds'] == 1
            assert store.get_state('native_pipeline')['threads'] == 1
            assert store.get_state('native_pipeline')['batch_size'] == 2
        with monkeypatch.context() as fake:
            fake.setattr(server.subprocess, 'Popen', capture)
            code, resumed = post('/api/sweep/resume', {'runId': launched['runId']})
            assert code == 200 and resumed['ok'], resumed
            manager.monitor_thread.join(timeout=5)
        assert resumed['effectiveConfig'] == policy
        controls = resumed['launch']['controls']
        assert (controls['threads'], controls['batch_size'], controls['max_misses']) == (1, 2, 1)
        assert controls['start_index'] == payload['startIndex']
        assert resumed['launch']['command'] == captured[-1][0]
        result = subprocess.run(resumed['launch']['shellCommand'], shell=True, cwd=tmp_path,
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        with RealmStore(directory, resume=True) as store:
            assert store.status()['completed_seeds'] == 3
            assert store.identity['config'] == policy
    finally:
        httpd.shutdown()
        httpd.server_close()
        worker.join(timeout=5)


@pytest.mark.parametrize('changes', [
    {'counts': {'stronghold': 2}}, {'counts': {'village': 5}},
    {'threads': 35}, {'batchSize': 16385}, {'startIndex': str(2**64)},
])
def test_preview_and_launch_reject_the_same_invalid_settings(tmp_path, monkeypatch, changes):
    monkeypatch.setattr(server, 'RUNS_DIR', tmp_path/'runs')
    manager = server.SweepManager()
    kwargs = { {'threads':'threads','batchSize':'batch_size','startIndex':'start_index','counts':'counts'}[key]: value
               for key, value in changes.items() }
    preview = manager.preview_sweep(**kwargs)
    launched = manager.start_sweep(**kwargs)
    assert not preview['ok'] and preview['error'] == launched['error']
    assert not (tmp_path/'runs').exists()
