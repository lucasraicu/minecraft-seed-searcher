"""Fault-path tests use fake Docker/console only; never launch a server."""
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import pytest

from seed_search.realm import verification as v
from seed_search.realm.bds_tools import poc_control as control, probe_tools as p
REAL_SNAPSHOT=p.snapshot
REAL_PROBE=p.Probe


@pytest.fixture
def environment(tmp_path,monkeypatch):
    state={'running':True,'exists':True,'exit_code':0,'stop_error':None,'extract_error':None,
           'startup_error':None,'docker_stop_error':None,'remove_error':None,'inspect_unknown':False}
    calls=[];snapshots=[]
    monkeypatch.setattr(v,'CLEANUP_GUARD',tmp_path/'blocked.json')
    monkeypatch.setattr(v.time,'sleep',lambda seconds:None)
    monkeypatch.setattr(p,'ROOT',tmp_path)
    monkeypatch.setattr(control,'ROOT',tmp_path)
    def docker(*args,**kwargs):
        calls.append((args,kwargs))
        if args[:2]==('image','inspect'):return SimpleNamespace(stdout=json.dumps([{'Id':v.IMAGE_ID}]))
        if args[0]=='info':return SimpleNamespace(stdout=json.dumps({'NCPU':4}))
        if args[:4]==('run','--rm','--entrypoint','/bin/df'):
            return SimpleNamespace(stdout=state.get('df_output','Filesystem 1024-blocks Used Available Capacity Mounted\n/dev/root 134217728 1 67108864 1% /srv/bds\n'))
        assert kwargs.get('timeout') is not None, 'Cleanup Docker operations must be bounded'
        if args[0]=='inspect':
            if state['inspect_unknown']:raise subprocess.TimeoutExpired(args,5)
            if not state['exists']:raise subprocess.CalledProcessError(1,args)
            return SimpleNamespace(stdout=json.dumps([{'State':{'Running':state['running'],'ExitCode':state['exit_code']}}]))
        if args[0]=='ps':
            if state['inspect_unknown']:raise subprocess.TimeoutExpired(args,5)
            name=json.loads(v.CLEANUP_GUARD.read_text())['name'] if v.CLEANUP_GUARD.exists() else 'unused'
            return SimpleNamespace(stdout=name if state['exists'] else '')
        if args[0]=='stop':
            if state['docker_stop_error']:raise state['docker_stop_error']
            state['running']=False
            return SimpleNamespace(stdout='stopped')
        if args[:2]==('rm','--force'):
            if state['remove_error']:raise state['remove_error']
            state['exists']=False;state['running']=False
            return SimpleNamespace(stdout='removed')
        raise AssertionError(args)
    monkeypatch.setattr(control,'docker',docker)
    monkeypatch.setattr(p,'create',lambda *args:None)
    class Console:
        start_seconds=.1
        def __init__(self,*args):
            if state['startup_error']:raise state['startup_error']
        def request(self,action,q):
            if state['extract_error']:raise state['extract_error']
            return {'fullyLoaded':True} if action=='load' else {'missing':0,'mismatches':0}
        def rows(self,q):return [{'x':0,'z':0,'ground':{'y':80},'waterDepth':0}]
        def save(self):return 0
        def resources(self):return {}
        def stop(self):
            if state['stop_error']:raise state['stop_error']
            state['running']=False
            return state['exit_code']
        def close_io(self):return []
    monkeypatch.setattr(p,'Probe',Console)
    def snapshot(*args):
        snapshots.append(args)
        assert not state['running'] and state['exists']
        return tmp_path/'snapshot'
    monkeypatch.setattr(p,'snapshot',snapshot)
    monkeypatch.setattr(p,'coverage',lambda *args:{'seed':'1','regions':[]})
    adapter=v.VerificationAdapter({'bds':{'evidence_dir':str(tmp_path/'evidence')}})
    def report():return json.loads(next((tmp_path/'evidence').glob('*-results.json')).read_text())
    return state,calls,snapshots,adapter,report


def run(adapter):return adapter._extract_locked('1',list(v.tiles((0,0,1,1),1)))


def test_clean_stop_confirmed_before_snapshot(environment):
    state,calls,snapshots,adapter,report=environment
    result=run(adapter)
    assert result['cleanup']['clean_shutdown'] and result['exit_code']==0
    assert len(snapshots)==1 and not v.CLEANUP_GUARD.exists()


@pytest.mark.parametrize('text',['','Filesystem blocks used available\n/dev/root 100 99 1 99% /srv/bds\n'])
def test_docker_disk_unknown_or_full_prevents_generation(environment,text):
    state,calls,snapshots,adapter,report=environment
    state['df_output']=text
    with pytest.raises(RuntimeError,match='disk monitoring|free-space reserve'):run(adapter)
    assert not snapshots and not v.CLEANUP_GUARD.exists()


@pytest.mark.parametrize('error',[RuntimeError('original extraction failed'),KeyboardInterrupt(),SystemExit(7)])
def test_original_extraction_exception_or_interrupt_preserved(environment,error):
    state,calls,snapshots,adapter,report=environment
    state['extract_error']=error;state['stop_error']=RuntimeError('secondary stop failure')
    with pytest.raises(type(error)) as caught:run(adapter)
    assert caught.value is error
    saved=report()
    assert saved['error_type']==type(error).__name__ and saved['status']=='FAILED'
    assert saved['cleanup']['stopped']
    assert saved['cleanup']['actions'][0]['error']=='secondary stop failure'
    assert not snapshots


def test_startup_failure_stops_existing_server_and_persists(environment):
    state,calls,snapshots,adapter,report=environment
    error=TimeoutError('startup timeout');state['startup_error']=error
    with pytest.raises(TimeoutError) as caught:run(adapter)
    assert caught.value is error and not state['running']
    assert report()['cleanup']['stopped'] and not snapshots
    assert any(args[0]=='stop' for args,_ in calls)


@pytest.mark.parametrize('error',[subprocess.TimeoutExpired(['logs'],20),RuntimeError('stop command failed')])
def test_failed_graceful_stop_never_snapshots_even_after_fallback(environment,error):
    state,calls,snapshots,adapter,report=environment
    state['stop_error']=error
    with pytest.raises(RuntimeError,match='snapshot forbidden'):run(adapter)
    assert not snapshots and not state['running']
    assert report()['cleanup']['stopped'] and not report()['cleanup']['clean_shutdown']


def test_stop_timeout_force_removes_possible_live_container(environment):
    state,calls,snapshots,adapter,report=environment
    state['stop_error']=TimeoutError('console timeout')
    state['docker_stop_error']=subprocess.TimeoutExpired(['stop'],15)
    with pytest.raises(RuntimeError,match='snapshot forbidden'):run(adapter)
    assert report()['cleanup']['removed'] and not state['exists'] and not snapshots
    assert any(args[:2]==('rm','--force') for args,_ in calls)


def test_fallback_timeouts_persist_guard_and_block_next_launch(environment):
    state,calls,snapshots,adapter,report=environment
    state['stop_error']=TimeoutError('console timeout')
    state['docker_stop_error']=subprocess.TimeoutExpired(['stop'],15)
    state['remove_error']=subprocess.TimeoutExpired(['rm'],15)
    state['inspect_unknown']=True
    with pytest.raises(RuntimeError,match='snapshot forbidden'):run(adapter)
    saved=report()
    assert not saved['cleanup']['stopped'] and not saved['cleanup']['removed']
    assert v.CLEANUP_GUARD.exists() and not snapshots
    calls.clear()
    with pytest.raises(RuntimeError,match='Previous BDS cleanup remains unresolved'):
        adapter._extract('1',list(v.tiles((0,0,1,1),1)))
    assert not any(args[:2]==('image','inspect') for args,_ in calls)


def test_observation_helpers_do_not_generate_or_reserve(tmp_path):
    from seed_search.realm.store import RealmStore
    with RealmStore(tmp_path,{}) as store:
        adapter=v.VerificationAdapter({},store,runtime=lambda *a:pytest.fail('No generation'))
        key=adapter.observation_id('-1',(-1,-1,7,7),4)
        assert adapter.get_cached('-1',(-1,-1,7,7),4) is None
        store.upsert_observation({'id':key,'status':'PARTIAL','seed':'-1'})
        assert adapter.get_cached('-1',(-1,-1,7,7),4)['id']==key
        assert adapter.verify('-1',(-1,-1,7,7),4)['id']==key
        assert adapter.used==0 and store.get_state('bds_verification_used') is None
        with pytest.raises(ValueError):adapter.observation_id('1',(0,0,1,1),False)


def test_original_error_preserved_when_all_fallbacks_fail(environment):
    state,calls,snapshots,adapter,report=environment
    original=RuntimeError('primary extraction error')
    state.update(extract_error=original,stop_error=TimeoutError('stop'),
                 docker_stop_error=subprocess.TimeoutExpired(['stop'],15),
                 remove_error=subprocess.TimeoutExpired(['rm'],15))
    with pytest.raises(RuntimeError) as caught:run(adapter)
    assert caught.value is original and report()['error']=='primary extraction error'
    assert v.CLEANUP_GUARD.exists() and not snapshots


@pytest.mark.parametrize('unknown',[False,True])
def test_snapshot_helper_refuses_live_or_unconfirmed_database(environment,unknown):
    state,calls,snapshots,adapter,report=environment
    state['inspect_unknown']=unknown
    with pytest.raises(RuntimeError,match='authoritative clean stopped'):
        REAL_SNAPSHOT('test-owned-container','snapshot')
    assert not any(args[0]=='cp' for args,_ in calls)


def test_snapshot_reader_failure_persisted_after_clean_shutdown(environment,monkeypatch):
    state,calls,snapshots,adapter,report=environment
    error=RuntimeError('reader decode failed')
    def broken(*args):raise error
    monkeypatch.setattr(p,'coverage',broken)
    with pytest.raises(RuntimeError) as caught:run(adapter)
    assert caught.value is error
    assert report()['status']=='FAILED' and report()['error']=='reader decode failed'
    assert report()['cleanup']['clean_shutdown'] and not state['running']


def test_probe_startup_failure_closes_partial_logging_handles(monkeypatch):
    closed=[]
    monkeypatch.setattr(control.Console,'__init__',lambda *args:None)
    monkeypatch.setattr(control.Console,'close_io',lambda self:closed.append(True))
    error=TimeoutError('ready timeout')
    def failed(*args,**kwargs):raise error
    monkeypatch.setattr(control.Console,'wait_for',failed)
    with pytest.raises(TimeoutError) as caught:REAL_PROBE('test','test')
    assert caught.value is error and closed==[True]


def test_docker_wrapper_supplies_bounded_default(monkeypatch):
    received=[]
    def fake_run(*args,**kwargs):
        received.append(kwargs)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(control.subprocess,'run',fake_run)
    control.docker('version')
    control.docker('stop','name',timeout=15)
    assert [row['timeout'] for row in received]==[60,15]


def test_nonzero_stopped_exit_is_not_snapshot_safe(environment):
    state,calls,snapshots,adapter,report=environment
    state['exit_code']=137
    with pytest.raises(RuntimeError,match='snapshot forbidden'):run(adapter)
    assert report()['cleanup']['stopped'] and not report()['cleanup']['clean_shutdown']
    assert not snapshots


def test_unwritable_diagnostics_does_not_mask_primary_error(environment,monkeypatch):
    state,calls,snapshots,adapter,report=environment
    original=RuntimeError('primary')
    state['extract_error']=original
    write_text=Path.write_text
    def fail_report(path,*args,**kwargs):
        if path.name.endswith('-results.json'):raise OSError('evidence disk failure')
        return write_text(path,*args,**kwargs)
    monkeypatch.setattr(Path,'write_text',fail_report)
    with pytest.raises(RuntimeError) as caught:run(adapter)
    assert caught.value is original and any('diagnostics also failed' in note for note in caught.value.__notes__)
    assert not state['running'] and not snapshots


def test_reported_console_success_without_stopped_confirmation_is_not_clean(environment,monkeypatch):
    state,calls,snapshots,adapter,report=environment
    monkeypatch.setattr(p.Probe,'stop',lambda self:0)
    with pytest.raises(RuntimeError,match='snapshot forbidden'):run(adapter)
    assert not state['running'] and not report()['cleanup']['clean_shutdown']
    assert not snapshots


def test_cleanup_system_exit_stops_container_and_preserves_exit_code(environment):
    state,calls,snapshots,adapter,report=environment
    state['stop_error']=SystemExit(9)
    with pytest.raises(SystemExit) as caught:run(adapter)
    assert caught.value.code==9 and not state['running']
    assert report()['cleanup']['termination']=={'type':'SystemExit','code':9}
    assert not snapshots
