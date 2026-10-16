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
    monkeypatch.setattr(server,'DEFAULT_NATIVE_BUILD',server.PROJECT_ROOT/'runs/dynamic-baseline-1664/native')
    captured=[]
    monkeypatch.setattr(server.subprocess,'Popen',lambda cmd,**kwargs:(captured.append(cmd),FakeProcess())[1])
    manager=server.SweepManager()
    result=manager.start_sweep(count=3,threads=2,batch_size=16,max_misses=2,
                               counts={'trial_chamber':8,'fortress':2},
                               profile='dynamic1664')
    assert result['ok']
    manager.monitor_thread.join(timeout=5)
    assert manager.status=='completed'
    assert manager.scanned_count==0  # stdout cannot invent durable coverage
    cfg=yaml.safe_load((tmp_path/result['runId']/'policy.yaml').read_text())
    assert cfg['structures']['minimum_counts']['trial_chamber']==8
    assert cfg['structures']['nether_minimum_counts']['fortress']==2
    assert cfg['search']['max_misses']==2
    assert captured[0][captured[0].index('--config')+1]==str(tmp_path/result['runId']/'policy.yaml')
    assert captured[0][captured[0].index('--max-misses')+1]=='2'
    for invalid in ({'counts':{'outpost':0}}, {'counts':{'trial_chamber':6}},
                    {'counts':{'unknown':1}}, {'count':True}, {'threads':0}):
        before=len(list(tmp_path.iterdir()))
        assert not manager.start_sweep(**invalid, profile='dynamic1664')['ok']
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
    assert command[command.index('--max-misses')+1]=='0'


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


def test_large_range_preserves_exact_start_and_rejects_invalid_bounds(monkeypatch,tmp_path):
    monkeypatch.setattr(server,'RUNS_DIR',tmp_path)
    calls=[]
    monkeypatch.setattr(server.subprocess,'Popen',lambda cmd,**kwargs:(calls.append(cmd),FakeProcess())[1])
    manager=server.SweepManager()
    result=manager.start_sweep(count=100001,start_index='18446744073709451615')
    assert result['ok']
    manager.monitor_thread.join(timeout=5)
    assert calls[0][calls[0].index('--start-index')+1]=='18446744073709451615'
    assert calls[0][calls[0].index('--count')+1]=='100001'
    assert manager.get_status()['startIndex']=='18446744073709451615'
    for controls in ({'start_index':'18446744073709551616'}, {'start_index':'-1'},
                     {'start_index':True}, {'start_index':'1.0'}, {'count':2**53},
                     {'start_index':str(2**64-1),'count':2}, {'threads':35}):
        assert not manager.start_sweep(**controls)['ok']
    assert len(calls)==1


def make_saved_web_run(tmp_path):
    import sqlite3
    from seed_search.realm.cli import make_identity
    from seed_search.realm.config import two_group_blueprint_config
    from seed_search.realm.native_batch import Prototype
    name='web-sweep-20261013-120000-12345678'
    directory=tmp_path/name;directory.mkdir()
    cfg=two_group_blueprint_config()
    identity=make_identity(cfg,10,9007199254740993)
    identity.update(execution='native',native=Prototype(server.DEFAULT_NATIVE_BUILD,cfg).identity,
                    native_build=str(server.DEFAULT_NATIVE_BUILD.resolve()),
                    evaluator='seed_search.realm.native_batch:run_native_scan',
                    retention={'mode':'survivors','max_misses':2})
    with sqlite3.connect(directory/'realm.sqlite') as conn:
        conn.execute('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT)')
        conn.executemany('INSERT INTO meta VALUES (?,?)',[(k,json.dumps(v)) for k,v in
            {'identity':identity,'completed_seeds':4,'native_pipeline':{'threads':34}}.items()])
    return name,directory


def test_resume_uses_saved_identity_and_new_durable_rate(monkeypatch,tmp_path):
    monkeypatch.setattr(server,'RUNS_DIR',tmp_path)
    name,directory=make_saved_web_run(tmp_path)
    calls=[]
    monkeypatch.setattr(server.subprocess,'Popen',lambda cmd,**kwargs:(calls.append(cmd),FakeProcess())[1])
    manager=server.SweepManager()
    assert manager.list_runs()=={'runs':[{'runId':name,'completedSeeds':4,'targetCount':10,
        'startIndex':'9007199254740993','resumable':True}]}
    result=manager.resume_sweep(name)
    assert result['ok']
    manager.monitor_thread.join(timeout=5)
    assert 'resume' in calls[0] and '--count' not in calls[0] and '--start-index' not in calls[0]
    assert calls[0][calls[0].index('--run')+1]==str(directory)
    assert manager.scanned_count==4 and manager.resume_baseline==4
    assert manager.seeds_per_sec==0


def test_resume_rejects_traversal_symlinks_and_identity_drift(monkeypatch,tmp_path):
    import sqlite3
    monkeypatch.setattr(server,'RUNS_DIR',tmp_path)
    name,directory=make_saved_web_run(tmp_path)
    calls=[]
    monkeypatch.setattr(server.subprocess,'Popen',lambda *args,**kwargs:calls.append(args))
    manager=server.SweepManager()
    for value in ('../'+name,str(directory),None,'../../etc/passwd'):
        assert not manager.resume_sweep(value)['ok']
    alias=tmp_path/'web-sweep-20261013-120001-12345678';alias.symlink_to(directory,target_is_directory=True)
    assert not manager.resume_sweep(alias.name)['ok']
    with sqlite3.connect(directory/'realm.sqlite') as conn:
        identity=json.loads(conn.execute("SELECT value FROM meta WHERE key='identity'").fetchone()[0])
        identity['native']['extension_sha256']='changed'
        conn.execute("UPDATE meta SET value=? WHERE key='identity'",(json.dumps(identity),))
    assert not manager.resume_sweep(name)['ok']
    assert manager.list_runs()=={'runs':[]}
    assert calls==[]


def test_resume_refuses_running_process(monkeypatch,tmp_path):
    monkeypatch.setattr(server,'RUNS_DIR',tmp_path)
    manager=server.SweepManager()
    class ActiveProcess:
        def poll(self):return None
    manager.process=ActiveProcess();manager.run_id='active'
    result=manager.resume_sweep('web-sweep-20261013-120000-12345678')
    assert not result['ok'] and result['runId']=='active'


def test_start_disk_gate_rejects_low_free_space_without_spawning(monkeypatch,tmp_path):
    monkeypatch.setattr(server,'RUNS_DIR',tmp_path)
    calls=[]
    monkeypatch.setattr(server.subprocess,'Popen',lambda *args,**kwargs:calls.append(args))
    manager=server.SweepManager()
    from types import SimpleNamespace
    monkeypatch.setattr(server.shutil,'disk_usage',lambda _:SimpleNamespace(free=1))
    result=manager.start_sweep(count=2**53-1)
    assert not result['ok'] and 'reserve' in result['error']
    assert not calls and not list(tmp_path.iterdir())
