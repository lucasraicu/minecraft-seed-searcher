"""Live web API must bind the v2 policy and publish observed evidence only."""
import io
import json
import threading

import pytest
import yaml

from seed_search.web import server


class FakeProcess:
    def __init__(self):
        self.stdout=io.StringIO('{"completed_seeds": 100000}\n')
        self.stderr=io.StringIO('diagnostic\n')
        self.returncode=0
    def wait(self,timeout=None):return self.returncode
    def poll(self):return self.returncode
    def terminate(self):self.returncode=-15
    def kill(self):self.returncode=-9


def test_start_binds_validated_counts_and_budget(monkeypatch,tmp_path):
    monkeypatch.setattr(server,'RUNS_DIR',tmp_path)
    monkeypatch.setattr(server,'DEFAULT_NATIVE_BUILD',server.PROJECT_ROOT/'runs/pre-sweep-v2-2026-10-13/control-native')
    captured=[]
    monkeypatch.setattr(server.subprocess,'Popen',lambda cmd,**kwargs:(captured.append(cmd),FakeProcess())[1])
    manager=server.SweepManager()
    result=manager.start_sweep(count=3,threads=2,batch_size=16,max_misses=2,
                               counts={'trial_chamber':8,'fortress':1})
    assert result['ok']
    manager.monitor_thread.join(timeout=5)
    assert manager.status=='completed'
    assert manager.scanned_count==0  # stdout cannot invent durable coverage
    cfg=yaml.safe_load((tmp_path/result['runId']/'policy.yaml').read_text())
    assert cfg['structures']['minimum_counts']['trial_chamber']==8
    assert cfg['structures']['nether_minimum_counts']['fortress']==1
    assert cfg['search']['max_misses']==2
    assert captured[0][captured[0].index('--config')+1]==str(tmp_path/result['runId']/'policy.yaml')
    assert captured[0][captured[0].index('--max-misses')+1]=='2'
    for invalid in ({'counts':{'outpost':0}}, {'counts':{'trial_chamber':7}},
                    {'counts':{'unknown':1}}, {'count':True}, {'threads':0}):
        before=len(list(tmp_path.iterdir()))
        assert not manager.start_sweep(**invalid)['ok']
        assert len(list(tmp_path.iterdir()))==before


def test_live_defaults_use_heldout_selected_scheduling(monkeypatch,tmp_path):
    monkeypatch.setattr(server,'RUNS_DIR',tmp_path)
    calls=[]
    monkeypatch.setattr(server.subprocess,'Popen',lambda cmd,**kwargs:(calls.append(cmd),FakeProcess())[1])
    manager=server.SweepManager()
    result=manager.start_sweep(count=1)
    assert result['ok']
    manager.monitor_thread.join(timeout=5)
    command=calls[0]
    assert command[command.index('--native-threads')+1]=='34'
    assert command[command.index('--native-batch-size')+1]=='16384'
    assert command[command.index('--max-misses')+1]=='2'


def test_candidate_serialization_does_not_invent_evidence():
    row={'evaluation_center':[0,0],'screening_revision':'origin-fixed-2048-two-group-v2',
         'required_structures':{'stronghold':{'predicted_viable':[]},
                                'village':{'predicted_viable':[[100,200]],'data_status':'PREDICTED'}},
         'required_nether_structures':{'fortress':{'predicted_viable':[[20,-40]]}},
         'qualification':'PREDICTED','marine_stage':{'status':'DEFERRED'}}
    parsed=server.parse_candidate_row('-9223372036854775808',0,json.dumps(row))
    assert parsed['score']==0
    assert parsed['seed']=='-9223372036854775808'
    assert parsed['strongholdAnchor'] is None
    assert parsed['spawnPoint'] is None and parsed['spawnDistance'] is None
    assert parsed['terrainMetrics'] is None and parsed['bdsAccuracy'] is None
    assert parsed['ravines']==[] and parsed['caveClusters']==[] and parsed['biomes']==[]
    assert parsed['chunkbaseUrl'] is None and not parsed['bdsVerified']
    assert parsed['structures'][0]['y'] is None
    assert parsed['structures'][1]['distanceUnits']=='nether horizontal blocks'


def test_old_monitor_cannot_finish_new_run(monkeypatch,tmp_path):
    manager=server.SweepManager()
    manager.generation=2;manager.run_dir=tmp_path/'new';manager.status='running'
    manager._monitor_process(FakeProcess(),tmp_path/'old',1)
    assert manager.status=='running'


def test_invalid_json_http_has_no_process_or_run(monkeypatch,tmp_path):
    import http.client
    import http.server
    monkeypatch.setattr(server,'RUNS_DIR',tmp_path)
    server.MANAGER=server.SweepManager()
    httpd=http.server.ThreadingHTTPServer(('127.0.0.1',0),server.WebSearchHandler)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    try:
        connection=http.client.HTTPConnection('127.0.0.1',httpd.server_port,timeout=5)
        connection.request('POST','/api/sweep/start',body='not json',headers={'Content-Type':'application/json'})
        response=connection.getresponse()
        assert response.status==400
        assert json.loads(response.read())['ok'] is False
        connection.request('POST','/api/sweep/stop')
        stop=connection.getresponse()
        assert stop.status==200
        assert json.loads(stop.read())['error']=='No active sweep to stop'
        assert not list(tmp_path.iterdir())
        connection.close()
    finally:
        httpd.shutdown();httpd.server_close();thread.join(timeout=5)
