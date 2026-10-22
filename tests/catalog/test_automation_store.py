"""Actual CAS, SQLite retention, publication crash windows and safe reclamation."""
from pathlib import Path
import copy
import pytest
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.models import identity,empty_observation_v2,world_id
from seed_search.catalog.registry import digest
from seed_search.catalog.summaries import summarize_v2
from seed_search.catalog.harvest import HarvestQueue,AutomationLedger
from seed_search.catalog.ingestion import atomic_json


def obs(seed='123'):
    return empty_observation_v2(identity(seed,model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64))


def offer(store,ledger,observation,rank=0,*,winner=True,resumable=False):
    wid=world_id(observation['identity']);oid=digest(observation);artifact=store.stage(observation,[])
    receipt=dict(world_id=wid,identity=observation['identity'],observation_id=oid,artifact=artifact,evaluations=[],replay={'resumable':resumable})
    ledger.offer(receipt,[dict(objective_id='test',rank=[rank],member=dict(world_id=wid,source_observation_id=oid))] if winner else [])
    return receipt


@pytest.fixture
def setup(tmp_path):
    with HarvestQueue(tmp_path) as queue:
        yield AutomationStore(tmp_path),AutomationLedger(queue,policy_revision='c'*64,objectives={'test':1})


def test_unconfigured_reads_do_not_create_root(tmp_path):
    root=tmp_path/'missing';store=AutomationStore(root)
    assert store.snapshots()==[]
    with pytest.raises(FileNotFoundError):store.snapshot()
    assert not root.exists()


def test_policy_local_generation_can_coexist_with_copied_history(tmp_path):
    import shutil
    source=tmp_path/'old';target=tmp_path/'new'
    old=AutomationStore(source)
    with HarvestQueue(source) as queue:
        ledger=AutomationLedger(queue,policy_revision='a'*64,objectives={'test':1})
        first=offer(old,ledger,obs('1'));sid1=old.publish(ledger)
    for folder in ('objects','snapshots','generations'):
        shutil.copytree(source/'automation'/folder,target/'automation'/folder)
    new=AutomationStore(target)
    with HarvestQueue(target) as queue:
        ledger=AutomationLedger(queue,policy_revision='b'*64,objectives={'test':1})
        second=offer(new,ledger,obs('2'));sid2=new.publish(ledger)
        assert new.publish(ledger)==sid2
    assert sid1!=sid2
    assert new.snapshot(sid1)['generation']==new.snapshot(sid2)['generation']==1
    assert new.world(sid1,first['world_id'])['observation']==obs('1')
    assert new.world(sid2,second['world_id'])['observation']==obs('2')
    assert old.snapshot()['policy_revision']=='a'*64


def test_stage_validates_real_summaries_and_source_binding(setup):
    store,ledger=setup;observation=obs();row=summarize_v2(observation)[0]
    artifact=store.stage(observation,[row]);assert store.artifacts.get_json(artifact)['summaries']==[row]
    bad=copy.deepcopy(row);bad['world_id']='f'*64
    with pytest.raises(ValueError):store.stage(observation,[bad])
    with pytest.raises(ValueError,match='Duplicate'):store.stage(observation,[row,row])
    with pytest.raises(ValueError):store.stage(observation,[{'layout_id':'f'*64}])


@pytest.mark.parametrize('point',['after_manifest','after_pointer'])
def test_crash_replay_before_and_after_pointer(setup,point):
    store,ledger=setup;receipt=offer(store,ledger,obs())
    def fault(stage):
        if stage==point:raise OSError('injected '+stage)
    with pytest.raises(OSError):store.publish(ledger,fault=fault)
    sid=store.publish(ledger);binding_before=store.current_path.read_bytes()
    assert store.publish(ledger)==sid and store.current_path.read_bytes()==binding_before
    assert store.world(sid,receipt['world_id'])['observation']==obs()
    assert len(store.snapshots())==1


def test_historical_shares_survive_membership_replacement_and_gc(setup):
    store,ledger=setup;first=offer(store,ledger,obs('1'),rank=5);sid1=store.publish(ledger)
    second=offer(store,ledger,obs('2'),rank=0);sid2=store.publish(ledger)
    pending=offer(store,ledger,obs('3'),winner=False,resumable=True)
    orphan=offer(store,ledger,obs('4'),winner=False,resumable=False)
    dry=store.cleanup(ledger);assert dry['candidates']==[orphan['artifact']['relative_key']]
    store.pin(sid1,first['world_id']);store.cleanup(ledger,mode='quarantine')
    assert (store.quarantine_dir/orphan['artifact']['relative_key']).is_file()
    assert store.world(sid1,first['world_id'])['observation']['identity']['seed']=='1'
    assert store.world(sid2,second['world_id'])['observation']['identity']['seed']=='2'
    assert store.artifacts.get_json(pending['artifact'])['observation']['identity']['seed']=='3'
    store.cleanup(ledger,mode='delete');assert not (store.quarantine_dir/orphan['artifact']['relative_key']).exists()
    with pytest.raises(KeyError):store.world(sid2,first['world_id'])


def test_corrupt_protected_data_fails_closed_before_orphan_move(setup):
    store,ledger=setup;first=offer(store,ledger,obs('1'));store.publish(ledger)
    orphan=offer(store,ledger,obs('2'),winner=False)
    source=store.objects_dir/first['artifact']['relative_key'];source.write_bytes(b'corrupt')
    with pytest.raises(ValueError):store.cleanup(ledger,mode='quarantine')
    assert (store.objects_dir/orphan['artifact']['relative_key']).is_file()
    assert not store.quarantine_dir.exists()


def test_missing_immutable_binding_and_symlinks_fail_closed(setup,tmp_path):
    store,ledger=setup;offer(store,ledger,obs());sid=store.publish(ledger)
    binding=store.snapshots_dir/(sid+'.json');saved=binding.read_bytes();binding.unlink()
    with pytest.raises(FileNotFoundError):store.snapshot()
    binding.write_bytes(saved)
    target=tmp_path/'unrelated';target.mkdir();link=store.objects_dir/'zz';link.symlink_to(target,target_is_directory=True)
    with pytest.raises(ValueError):store.cleanup(ledger,mode='quarantine')


def test_membership_must_bind_current_receipt_source(setup):
    store,ledger=setup;offer(store,ledger,obs())
    with ledger.queue.transaction():
        ledger.conn.execute('UPDATE automation_members SET member_json=?',('{"world_id":"'+world_id(obs()['identity'])+'","source_observation_id":"'+'f'*64+'"}',))
    with pytest.raises(ValueError,match='Stale'):store.publish(ledger)
    assert not store.current_path.exists()


def test_stale_generation_or_new_policy_cannot_overwrite_current(setup):
    store,ledger=setup;offer(store,ledger,obs('1'));sid=store.publish(ledger)
    original=store.current_path.read_bytes()
    ledger.policy_revision='d'*64
    with pytest.raises(ValueError,match='Policy'):store.publish(ledger)
    assert store.current_path.read_bytes()==original
    ledger.policy_revision='c'*64
    with ledger.queue.transaction():ledger.conn.execute("UPDATE automation_meta SET value='0' WHERE key='generation'")
    with pytest.raises(ValueError,match='Stale'):store.publish(ledger)
    assert store.current_path.read_bytes()==original


def test_after_generation_crash_protects_pending_manifest_and_fences_divergence(setup):
    store,ledger=setup;offer(store,ledger,obs('1'))
    def fault(stage):
        if stage=='after_generation':raise OSError('injected')
    with pytest.raises(OSError):store.publish(ledger,fault=fault)
    assert not store.current_path.exists() and store.snapshots()==[]
    assert store.cleanup(ledger)['candidates']==[]
    offer(store,ledger,obs('2'),rank=-1)
    with ledger.queue.transaction():ledger.conn.execute("UPDATE automation_meta SET value='1' WHERE key='generation'")
    with pytest.raises(ValueError,match='generation'):store.publish(ledger)


def test_more_than_one_hundred_pins_and_crash_temps_do_not_wedge_cleanup(setup):
    store,ledger=setup;receipt=offer(store,ledger,obs());sid=store.publish(ledger)
    pin=dict(snapshot_id=sid,world_id=receipt['world_id'])
    atomic_json(store.base/'pins.json',[pin]*150)
    temp=store.snapshots_dir/('.'+'f'*64+'.json.tmp.123.456');temp.write_text('partial unpublished metadata')
    assert store.cleanup(ledger)['candidates']==[]
    assert store.snapshots()[0]['snapshot_id']==sid
