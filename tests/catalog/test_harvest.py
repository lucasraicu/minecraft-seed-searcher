"""Queue ownership, independent seed selection, bounded recovery and real child stop."""
import copy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest

from seed_search.catalog.harvest import HarvestQueue,make_descriptor,write_descriptor,validate_descriptor
from seed_search.catalog.models import identity
from seed_search.realm.runner import _seed
from tests.catalog.test_ingestion import make_complete_observation


def descriptor(root,search=None,*,start=0,count=5,caps=None,tag='a'):
    return make_descriptor(search or {'sequence':'sequential'},start,count,
        identity(0,model_id='test',native_sha256='b'*64,source_sha256='c'*64),tag*64,root,caps=caps)


@pytest.mark.parametrize('search,start,count',[
 ({'sequence':'sequential'},(1<<63)-1,3),
 ({'sequence':'permutation','run_key':'text key'},0,9),
 ({'sequence':'strided','low32':'123'},(1<<31)-1,3),
 ({'sequence':'manifest','manifest_seeds':['-9223372036854775808','9223372036854775807','-1']},0,3)])
def test_seed_enumeration_before_personal_rejection(tmp_path,search,start,count):
    desc=descriptor(tmp_path/'queue',search,start=start,count=count)
    with HarvestQueue(tmp_path/'queue') as queue:
        queue.register(desc);seen=[]
        while (job:=queue.claim('test')) is not None:
            seen.append(job['seed']);queue.acknowledge(job,'f'*64)
        assert sorted(seen)==sorted(str(_seed(i,search)) for i in range(start,start+count))
        # No personal policy or survivors are needed to dispatch every public sample.
        assert queue.status()['jobs']['complete']==count


def test_descriptor_immutable_caps_full64_and_symlink(tmp_path):
    desc=descriptor(tmp_path/'queue',count=1<<64)
    assert desc['count']==str(1<<64)
    path=write_descriptor(tmp_path/'spool',desc)
    assert write_descriptor(tmp_path/'spool',desc)==path
    bad=copy.deepcopy(desc);bad['count']='4'
    with pytest.raises(ValueError):validate_descriptor(bad)
    with pytest.raises(ValueError):descriptor(tmp_path/'q',caps={'sample_cap':101})
    (tmp_path/'link').symlink_to(tmp_path/'spool',target_is_directory=True)
    with pytest.raises(ValueError):write_descriptor(tmp_path/'link',desc)


def test_backpressure_duplicate_registration_and_shared_cancel(tmp_path):
    root=tmp_path/'queue'
    first=descriptor(root,count=5,caps={'pending_cap':1})
    second=descriptor(root,count=5,caps={'pending_cap':1},tag='d')
    with HarvestQueue(root) as queue:
        queue.register(first);queue.register(first);queue.register(second);queue.expand()
        status=queue.status();assert status['jobs']=={'pending':1}
        assert all(c['scheduled_samples']==1 for c in status['campaigns'])
        job=queue.claim('one')
        queue.set_campaign_state(first['campaign_id'],'cancelled')
        queue.acknowledge(job,'f'*64)  # second campaign still owns this shared world
        queue.expand();assert queue.status()['jobs']=={'complete':1,'pending':1}
        assert queue.claim('active-owner')['campaign_id']==second['campaign_id']
        with pytest.raises(ValueError):queue.set_campaign_state(first['campaign_id'],'active')


def test_lease_fencing_expiry_private_generations_pause_resume(tmp_path):
    now=[100.]
    root=tmp_path/'queue'
    with HarvestQueue(root,clock=lambda:now[0]) as one, HarvestQueue(root,clock=lambda:now[0]) as two:
        desc=descriptor(root,count=1);one.register(desc)
        old=one.claim('old',lease_seconds=1)
        assert two.claim('new') is None
        now[0]+=2;new=two.claim('new')
        assert new['generation']>old['generation'] and new['checkpoint']!=old['checkpoint']
        with pytest.raises(ValueError):one.acknowledge(old,'f'*64)
        with pytest.raises(ValueError):one.heartbeat(old)
        two.set_campaign_state(desc['campaign_id'],'paused')
        with pytest.raises(ValueError):two.acknowledge(new,'f'*64)
        assert one.claim('next') is None
        two.set_campaign_state(desc['campaign_id'],'active')
        resumed=one.claim('next');assert resumed
        with one.publication(resumed):one.acknowledge(resumed,'f'*64)


def test_busy_registration_fails_bounded_and_descriptor_replays(tmp_path):
    root=tmp_path/'queue';desc=descriptor(root)
    path=write_descriptor(tmp_path/'spool',desc)
    with HarvestQueue(root) as first, HarvestQueue(root,busy_ms=20) as second:
        first.conn.execute('BEGIN IMMEDIATE');started=time.monotonic()
        try:
            with pytest.raises(sqlite3.OperationalError):second.register(desc)
            assert time.monotonic()-started<1
        finally:first.conn.rollback()
        second.register(json.loads(path.read_text()));second.expand()
        assert second.status()['jobs']['pending']==5


def test_attempt_backoff_and_zero_survivor_public_drain(tmp_path):
    from seed_search.catalog.harvest_worker import drain
    now=[100.];root=tmp_path/'queue'
    with HarvestQueue(root,clock=lambda:now[0]) as queue:
        queue.register(descriptor(root,count=1));job=queue.claim('w')
        queue.fail(job,'fixture failure');assert queue.claim('w') is None
        now[0]+=3
        published=[]
        def extract(job,seconds):
            assert seconds<=120
            return make_complete_observation(job['seed'],{k:v for k,v in job['identity'].items() if k!='seed'})
        result=drain(queue,extract,lambda job,obs:published.append(obs['identity']['seed']) or 'f'*64)
        assert result['completed']==1 and published==['0']


def test_cancelled_world_can_belong_to_new_active_campaign_without_cap_overflow(tmp_path):
    root=tmp_path/'queue'
    with HarvestQueue(root) as queue:
        first=descriptor(root,count=1,caps={'pending_cap':1})
        queue.register(first);queue.expand();queue.set_campaign_state(first['campaign_id'],'cancelled')
        assert queue.status()['jobs']=={'cancelled':1}
        new=descriptor(root,count=1,caps={'pending_cap':1},tag='d')
        queue.register(new);job=queue.claim('new-owner')
        assert job and job['seed']=='0'
        queue.acknowledge(job,'f'*64)


def test_native_child_timeout_and_output_cap_no_orphans(tmp_path,monkeypatch):
    from seed_search.catalog import harvest_native
    real_popen=subprocess.Popen;children=[]
    def fake_popen(argv,**kwargs):
        # Harmless owned child, no native seed extraction.
        child=real_popen([sys.executable,'-c','import sys,time;sys.stdin.read();time.sleep(30)'],**kwargs)
        children.append(child);return child
    monkeypatch.setattr(harvest_native.subprocess,'Popen',fake_popen)
    monkeypatch.setattr(harvest_native,'_get_aggregate_rss',lambda pid:0)
    root=tmp_path/'queue'
    with HarvestQueue(root) as queue:
        queue.register(descriptor(root,count=1));job=queue.claim('w')
        with pytest.raises(TimeoutError):harvest_native.extract_native(job,.1)
        assert children and children[0].poll() is not None
        job['caps']['output_bytes']=1
        with pytest.raises(OSError):harvest_native.extract_native(job,1)
        assert len(children)==1


def test_single_supervisor_and_atomic_checksummed_checkpoint(tmp_path):
    from seed_search.catalog.harvest_worker import drain
    from seed_search.catalog.harvest_native import save_checkpoint,checkpoint_observation
    root=tmp_path/'queue'
    with HarvestQueue(root) as first,HarvestQueue(root) as second:
        with first.supervisor() as acquired:
            assert acquired
            result=drain(second,lambda *a:pytest.fail('Second supervisor extracted'),lambda *a:None)
            assert result['stop_reason']=='worker_already_running'
        desc=descriptor(root,count=1)
        observation=make_complete_observation('0',{k:v for k,v in desc['observation_identity'].items() if k!='seed'})
        path=root/'staging'/'fixture.json'
        save_checkpoint(path,observation)
        assert checkpoint_observation(path)==observation
        value=json.loads(path.read_text());value['observation']['identity']['seed']='1'
        path.write_text(json.dumps(value))
        with pytest.raises(ValueError,match='checksum'):checkpoint_observation(path)


def test_explicit_clock_and_concurrent_atomic_bootstrap(tmp_path):
    import os
    root=tmp_path/'queue';repo=Path(__file__).resolve().parents[2]
    source='''
import sys
from seed_search.catalog.harvest import HarvestQueue
sys.stdin.read(1)
with HarvestQueue(sys.argv[1]) as queue:
 assert queue.status()['jobs']=={}
'''
    env=dict(os.environ,PYTHONPATH=str(repo/'src'))
    children=[subprocess.Popen([sys.executable,'-c',source,str(root)],env=env,cwd=repo,
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
    try:
        for child in children:child.stdin.write('x');child.stdin.flush()
        for child in children:
            _,error=child.communicate(timeout=10)
            assert child.returncode==0,error
    finally:
        for child in children:
            if child.poll() is None:child.terminate();child.wait(timeout=5)
    with HarvestQueue(root) as queue:
        queue.register(descriptor(root,count=1))
        job=queue.claim('simulated-clock',now=10,lease_seconds=10)
        queue.heartbeat(job,now=11)
        queue.fail(job,'clock fixture',now=12)
        with pytest.raises(ValueError):queue.claim('bad-clock',now=float('nan'))
