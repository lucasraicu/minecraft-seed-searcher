"""Automatic staging reclamation must preserve retries, shared data and old shares."""
from pathlib import Path
import pytest
from seed_search.catalog.harvest import HarvestQueue,AutomationLedger,make_descriptor
from seed_search.catalog.models import identity,empty_observation_v2,world_id
from seed_search.catalog.registry import digest
from seed_search.catalog.store import AutomationStore


@pytest.fixture
def prepared(tmp_path):
    template=identity('0',model_id='26.50',native_sha256='a'*64,source_sha256='b'*64)
    with HarvestQueue(tmp_path) as q:
        q.register(make_descriptor({'sequence':'manifest','manifest_seeds':['1','2','3','4']},0,4,template,'c'*64,tmp_path))
        store=AutomationStore(tmp_path);ledger=AutomationLedger(q,policy_revision='d'*64,objectives={'sample':10})
        jobs=[];snapshots=[]
        for i in range(4):
            job=q.claim('test');path=Path(job['checkpoint']);path.parent.mkdir(parents=True);path.write_text('owned checkpoint')
            jobs.append(job)
            if i<2:
                obs=empty_observation_v2(job['identity']);wid=world_id(obs['identity']);oid=digest(obs)
                ledger.offer(dict(world_id=wid,identity=obs['identity'],observation_id=oid,artifact=store.stage(obs,[]),
                    evaluations=[],replay={'resumable':i==1}),[dict(objective_id='sample',rank=[i],member=dict(world_id=wid,source_observation_id=oid))])
                sid=store.publish(ledger);snapshots.append((sid,wid));q.acknowledge(job,sid)
            elif i==3:q.fail(job,'partial',partial=True)
        yield q,ledger,store,jobs,snapshots


def test_completed_checkpoint_reclaimed_after_publication_but_retries_preserved(prepared,tmp_path):
    q,ledger,store,jobs,snapshots=prepared
    unknown=tmp_path/'staging'/('f'*64);unknown.mkdir();(unknown/'unrecognized').write_text('keep')
    with q.supervisor() as owned,q.ownership():
        assert owned
        store.cleanup(ledger)
        expected=[jobs[0]['task_id']]
        assert store.cleanup_completed_staging(ledger)['candidates']==expected
        store.cleanup_completed_staging(ledger,mode='quarantine')
        assert not Path(jobs[0]['checkpoint']).exists()
        # Restart at the move/delete boundary revalidates the quarantined job.
        reopened=AutomationStore(tmp_path)
        assert reopened.cleanup_completed_staging(ledger,mode='delete')['candidates']==expected
        assert reopened.cleanup_completed_staging(ledger)['candidates']==[]
        for job in jobs[1:]:assert Path(job['checkpoint']).is_file()
        assert (unknown/'unrecognized').is_file()
        for sid,wid in snapshots:assert reopened.world(sid,wid)['observation']['identity']


def test_symlink_or_deadline_prevents_any_staging_move(prepared,tmp_path):
    q,ledger,store,jobs,_=prepared
    source=Path(jobs[0]['checkpoint']).parent.parent
    bad=source/'outside';bad.symlink_to(tmp_path/'harvest.sqlite')
    with q.ownership(),pytest.raises(ValueError):store.cleanup_completed_staging(ledger,mode='quarantine')
    assert source.is_dir() and not (store.base/'staging-quarantine').exists()
    bad.unlink()
    def expired():raise TimeoutError('budget')
    with q.ownership(),pytest.raises(TimeoutError):store.cleanup_completed_staging(ledger,mode='quarantine',check=expired)
    assert Path(jobs[0]['checkpoint']).is_file()


def test_reclaim_crash_between_quarantine_and_delete_is_recoverable(prepared):
    q,ledger,store,_,snapshots=prepared
    obs=empty_observation_v2(identity('99',model_id='26.50',native_sha256='a'*64,source_sha256='b'*64))
    orphan=store.stage(obs,[]);target=store.quarantine_dir/orphan['relative_key']
    def after_move():
        if target.exists():raise TimeoutError('injected after quarantine')
    with q.ownership(),pytest.raises(TimeoutError):store.cleanup(ledger,mode='reclaim',check=after_move)
    assert target.is_file() and not (store.objects_dir/orphan['relative_key']).exists()
    with q.ownership():
        report=store.cleanup(ledger,mode='reclaim')
        assert orphan['relative_key'] in report['candidates']
    assert not target.exists()
    for sid,wid in snapshots:assert store.world(sid,wid)['observation']['identity']
