"""Actual spawn/IPC/lifecycle checks on tiny saved catalog fixtures, no MC jobs."""
import concurrent.futures
import copy
import json
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import sys
import time
import urllib.request
import pytest
from seed_search.catalog import query_workers
from seed_search.catalog.service import CatalogService, ServiceError
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.evaluation import heldout_cases
from tests.catalog.test_integrated_pilot import sample, bind


def process_state(pid):
    result=subprocess.run(['ps','-p',str(pid),'-o','stat=','-o','lstart='],capture_output=True,text=True,timeout=1)
    return result.stdout.strip()


def live(pid):
    state=process_state(pid)
    return bool(state)and not state.startswith('Z')


@pytest.fixture
def catalog(tmp_path):
    observations=[];layouts=[]
    for seed in (-1,0,1):
        obs,rows=sample(seed);observations.append(obs);layouts.extend(rows)
    with SegmentedCatalog(tmp_path)as store:
        sid=store.publish(observations,layouts);req=bind(heldout_cases()['cases'][0]['template'],store.info(sid))
    return tmp_path,req


def wait_ready(pool,count,seconds=4):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if pool.status()['ready']==count:return
        time.sleep(.01)
    raise AssertionError(pool.status())


@pytest.mark.parametrize('workers',[1,2])
def test_real_workers_exact_cache_cursor_and_error_contracts(catalog,workers):
    root,req=catalog;service=CatalogService(root,query_processes=workers,secret=b'fixed-worker-test')
    try:
        expected=CatalogService(root).query(dict(request=req,page_size=1))
        first=service.query(dict(request=req,page_size=1));assert first['results']==expected['results']
        assert not first['stats']['result_cache_hit']
        warm=service.query(dict(request=req,page_size=1));assert warm['stats']['result_cache_hit']
        first['results'][0]['counts'][0][0]=999
        assert service.query(dict(request=req,page_size=1))['results']==expected['results']
        next_page=service.query(dict(request=req,page_size=1,cursor=first['next_cursor']))
        assert next_page['results'][0]['world_id']!=warm['results'][0]['world_id']
        # A different worker/cold cache must accept the same secret-bound cursor.
        key=next(iter(service.query_workers._affinity))
        if workers==2:service.query_workers._affinity[key]=1-service.query_workers._affinity[key]
        assert service.query(dict(request=req,page_size=1,cursor=first['next_cursor']))['results']==next_page['results']
        for body in ({'request':req,'page_size':0},{'request':dict(req,border_side=3)},[]):
            with pytest.raises(ServiceError)as failed:service.query(body)
            assert failed.value.status==400
        expired=service._token(dict(snapshot=req['catalog_snapshot_id'],request='0'*64,size=1,last=[],expires=0))
        with pytest.raises(ServiceError)as error:service.query(dict(request=req,cursor=expired,page_size=1))
        assert error.value.status==410
        pids=service.query_workers.status()['pids'];assert len(pids)==workers
    finally:service.close()
    assert all(not live(pid)for pid in pids)


def test_deadline_bounds_blocked_ipc_write_and_replacement(catalog):
    root,req=catalog;service=CatalogService(root,query_processes=1,query_seconds=.15)
    try:
        old=service.query_workers._workers[0];os.kill(old.process.pid,signal.SIGSTOP)
        start=time.monotonic()
        with pytest.raises(ServiceError)as error:
            service.query({'request':{'padding':'x'*(query_workers.MAX_REQUEST//2)}})
        assert error.value.code=='query_timeout'and time.monotonic()-start<1.5
        assert not old.process.is_alive()
        wait_ready(service.query_workers,1)
        assert service.query({'request':req})['matched_worlds']==3
    finally:service.close()


def test_worker_crash_has_no_replay_and_recovers_cursor(catalog):
    root,req=catalog;service=CatalogService(root,query_processes=1)
    try:
        first=service.query(dict(request=req,page_size=1));old=service.query_workers._workers[0]
        os.kill(old.process.pid,signal.SIGSTOP)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1)as executor:
            future=executor.submit(service.query,dict(request=req,page_size=1,cursor=first['next_cursor']))
            limit=time.monotonic()+1
            while not service.query_workers.status()['busy']and time.monotonic()<limit:time.sleep(.005)
            os.kill(old.process.pid,signal.SIGKILL)
            with pytest.raises(ServiceError)as error:future.result(timeout=2)
            assert error.value.code=='query_worker_failed'
        wait_ready(service.query_workers,1)
        second=service.query(dict(request=req,page_size=1,cursor=first['next_cursor']))
        assert second['results'][0]['world_id']!=first['results'][0]['world_id']
        assert not second['stats']['result_cache_hit']
    finally:service.close()


def test_busy_affinity_owner_never_blocks_an_idle_worker(catalog):
    root,req=catalog;service=CatalogService(root,query_processes=2,query_seconds=1)
    try:
        baseline=service.query({'request':req});owner=service.query_workers._workers[0]
        os.kill(owner.process.pid,signal.SIGSTOP)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1)as executor:
            blocked=executor.submit(service.query,{'request':req})
            deadline=time.monotonic()+.5
            while not owner.busy and time.monotonic()<deadline:time.sleep(.005)
            assert owner.busy
            start=time.monotonic();other=service.query({'request':req})
            assert other['results']==baseline['results']and time.monotonic()-start<.8
            os.kill(owner.process.pid,signal.SIGKILL)
            with pytest.raises(ServiceError):blocked.result(timeout=2)
    finally:service.close()


def test_one_healthy_worker_cannot_receive_two_leases(catalog):
    root,req=catalog;service=CatalogService(root,query_processes=2)
    try:
        pool=service.query_workers
        # Inject exhausted recovery with one surviving worker, then block it.
        with pool._condition:pool._exhausted=True
        pool._retire(pool._workers[1]);worker=pool._workers[0]
        os.kill(worker.process.pid,signal.SIGSTOP)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1)as executor:
            blocked=executor.submit(pool.query,{'request':req},deadline=time.monotonic()+1,acquire_deadline=time.monotonic()+.5)
            limit=time.monotonic()+.5
            while not worker.busy and time.monotonic()<limit:time.sleep(.005)
            assert pool.status()['busy']==1
            with pytest.raises(ServiceError)as error:pool.query({'request':req},deadline=time.monotonic()+.5,acquire_deadline=time.monotonic()+.05)
            assert error.value.code=='busy'and pool.status()['busy']==1
            os.kill(worker.process.pid,signal.SIGKILL)
            with pytest.raises(ServiceError):blocked.result(timeout=2)
    finally:service.close()


def test_restart_budget_stops_dispatch_without_orphans(catalog):
    root,req=catalog;service=CatalogService(root,query_processes=1,query_seconds=.1)
    try:
        for attempt in range(3):
            wait_ready(service.query_workers,1);worker=service.query_workers._workers[0]
            os.kill(worker.process.pid,signal.SIGSTOP)
            with pytest.raises(ServiceError):service.query({'request':req})
            assert not worker.process.is_alive()
        status=service.query_workers.status();assert status['restart_exhausted']and status['ready']==0
        with pytest.raises(ServiceError)as error:service.query({'request':req})
        assert error.value.code=='query_workers_unavailable'
    finally:service.close()


def malformed_reply(channel,config):
    query_workers._send(channel,dict(protocol=query_workers.PROTOCOL,kind='ready',generation=config['generation']),config['startup_deadline'],query_workers.MAX_REPLY)
    job=query_workers._receive(channel,None,query_workers.MAX_REQUEST)
    query_workers._send(channel,dict(protocol=query_workers.PROTOCOL,kind='result',generation=config['generation'],id='wrong-id',payload={}),job['deadline'],query_workers.MAX_REPLY)
    channel.close()


def test_wrong_job_reply_is_rejected(catalog,monkeypatch):
    root,req=catalog;monkeypatch.setattr(query_workers,'_worker_main',malformed_reply)
    service=CatalogService(root,query_processes=1)
    try:
        with pytest.raises(ServiceError)as error:service.query({'request':req})
        assert error.value.code=='query_worker_failed'
    finally:service.close()


def test_warm_membership_corruption_is_rejected(catalog):
    root,req=catalog;service=CatalogService(root,query_processes=1)
    try:
        service.query({'request':req});assert service.query({'request':req})['stats']['result_cache_hit']
        with SegmentedCatalog(root)as store:store.conn.execute('UPDATE observation_ref SET observation_id=? WHERE snapshot_id=?',('f'*64,req['catalog_snapshot_id']))
        with pytest.raises(ServiceError)as error:service.query({'request':req})
        assert error.value.code=='integrity_error'
    finally:service.close()


def test_ipc_frame_and_duplicate_keys_are_bounded():
    a,b=socket.socketpair()
    try:
        a.sendall(struct.pack('!I',query_workers.MAX_REPLY+1))
        with pytest.raises(ValueError):query_workers._receive(b,time.monotonic()+1,query_workers.MAX_REPLY)
        raw=b'{"kind":1,"kind":2}';a.sendall(struct.pack('!I',len(raw))+raw)
        with pytest.raises(ValueError):query_workers._receive(b,time.monotonic()+1,query_workers.MAX_REPLY)
    finally:a.close();b.close()


def test_process_accuracy_fine_or_unknown_expiry_and_warm_corruption(tmp_path):
    from tests.catalog.test_accuracy_service import setup
    from seed_search.catalog.accuracy_store import write_bundle
    from seed_search.catalog.refinement import make_tile
    from seed_search.catalog.registry import digest
    bundle,req=setup(tmp_path)
    ident=bundle['anchors'][0]['anchor']['context']['identity']
    context=dict(identity=ident,dimension='overworld',provider='procedural_model_v1',observed_build=None,evidence_sha256='d'*64)
    bundle['tiles']=[make_tile(context,[1,1,2,2],63,[77],biome_names={'77':'mushroom_fields'})]
    req['accuracy_generation']=write_bundle(tmp_path,bundle)
    req['rows']=[dict(kind='biome_witness',rule='required',any_of=['biome.mushroom_fields','biome.mangrove_swamp'],scope={'kind':'near_base','radius':256})]
    service=CatalogService(tmp_path,query_processes=2)
    try:
        expected=CatalogService(tmp_path).query({'request':req})
        result=service.query({'request':req})
        assert result['results']==expected['results'] and result['unresolved_worlds']==0
        assert result['results'][0]['refined_biome_witnesses'][0]['x']==1
        result['results'][0]['refined_biome_witnesses'][0]['x']=999
        warm=service.query({'request':req})
        assert warm['stats']['result_cache_hit'] and warm['results']==expected['results']
        unknown=copy.deepcopy(req);unknown['rows'][0]['any_of']=['biome.mangrove_swamp']
        unresolved=service.query({'request':unknown})
        assert unresolved['results']==[] and unresolved['unresolved_worlds']==1
        assert unresolved['unresolved_candidates'][0]['seed']=='17'
        cursor=service._token(dict(snapshot=req['catalog_snapshot_id'],request=digest(req),size=20,last=[],expires=0))
        with pytest.raises(ServiceError)as expired:service.query({'request':req,'cursor':cursor})
        assert expired.value.code=='cursor_expired'
        binding=json.loads((tmp_path/'accuracy'/(req['accuracy_generation']+'.json')).read_text())
        artifact=tmp_path/'accuracy/objects'/binding['artifact']['relative_key']
        artifact.write_bytes(artifact.read_bytes()[:-1])
        with pytest.raises(ServiceError)as corrupt:service.query({'request':req})
        assert corrupt.value.code=='integrity_error' and corrupt.value.status==503
    finally:service.close()


@pytest.mark.parametrize('termination',[signal.SIGTERM,signal.SIGKILL])
def test_standalone_parent_death_leaves_no_live_worker(catalog,termination):
    root,_=catalog;repo=Path(__file__).resolve().parents[2]
    parent=subprocess.Popen([sys.executable,'-m','seed_search.catalog.http_server','--root',str(root),'--port','0','--query-processes','1'],cwd=repo,env=dict(os.environ,PYTHONPATH=str(repo/'src')),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    identities=[]
    try:
        line=parent.stdout.readline().strip();assert line.startswith('Private Catalog backend '),line
        with urllib.request.urlopen(line.split()[-1]+'/api/catalog/status',timeout=5)as response:status=json.load(response)
        identities=[(pid,process_state(pid).split(maxsplit=1)[1])for pid in status['query_workers']['pids']]
        os.kill(parent.pid,termination);parent.wait(timeout=3)
        deadline=time.monotonic()+2
        while any(live(pid)for pid,_ in identities)and time.monotonic()<deadline:time.sleep(.02)
        assert not any(live(pid)for pid,_ in identities)
    finally:
        if parent.poll()is None:parent.kill();parent.wait(timeout=3)
        for pid,started in identities:
            state=process_state(pid)
            if state and not state.startswith('Z')and state.split(maxsplit=1)[1]==started:os.kill(pid,signal.SIGKILL)
        parent.stdout.close();parent.stderr.close()


def busy_query_worker(channel,config):
    from seed_search.catalog.service import CatalogService
    def blocked(self,body):
        time.sleep(30)
        raise AssertionError('Owned test parent should have exited first')
    CatalogService.query=blocked
    query_workers._worker_main(channel,config)


def test_abrupt_parent_death_cleans_busy_worker(catalog):
    root,req=catalog;repo=Path(__file__).resolve().parents[2]
    code="from seed_search.catalog import query_workers; from tests.catalog.test_query_workers import busy_query_worker; query_workers._worker_main=busy_query_worker; from seed_search.catalog.http_server import main; main()"
    parent=subprocess.Popen([sys.executable,'-c',code,'--root',str(root),'--port','0','--query-processes','1'],cwd=repo,env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(repo/'src'),str(repo)])),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    child=None;child_birth=None;executor=concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        line=parent.stdout.readline().strip();assert line.startswith('Private Catalog backend '),line
        base=line.split()[-1]+'/api/catalog'
        with urllib.request.urlopen(base+'/status',timeout=3)as response:child=json.load(response)['query_workers']['pids'][0]
        child_birth=process_state(child).split(maxsplit=1)[1]
        def request():
            try:
                with urllib.request.urlopen(urllib.request.Request(base+'/query',data=json.dumps({'request':req}).encode(),headers={'Content-Type':'application/json'}),timeout=4)as response:response.read()
            except OSError:pass
        future=executor.submit(request);deadline=time.monotonic()+2
        while True:
            with urllib.request.urlopen(base+'/status',timeout=1)as response:status=json.load(response)
            if status['query_workers']['busy']==1:break
            assert time.monotonic()<deadline
            time.sleep(.01)
        os.kill(parent.pid,signal.SIGKILL);parent.wait(timeout=2)
        deadline=time.monotonic()+2
        while live(child)and time.monotonic()<deadline:time.sleep(.02)
        assert not live(child)
        future.result(timeout=4)
    finally:
        if parent.poll()is None:parent.kill();parent.wait(timeout=2)
        executor.shutdown(wait=True)
        if child and live(child)and process_state(child).split(maxsplit=1)[1]==child_birth:os.kill(child,signal.SIGKILL)
        parent.stdout.close();parent.stderr.close()


def test_startup_failure_does_not_leave_owned_children(tmp_path):
    import multiprocessing
    before={p.pid for p in multiprocessing.active_children()}
    with pytest.raises((EOFError,OSError)):
        CatalogService(tmp_path/'absent',query_processes=2)
    assert {p.pid for p in multiprocessing.active_children()}==before
