"""Migration must change only the one estimated anchor, never world facts."""
import copy
import pytest
from scripts.reanchor_catalog import reanchor_observation,reanchor_summaries,committed_migration
from seed_search.catalog.anchors import make_anchor
from tests.catalog.test_product_evaluation_v2 import observation


def anchor(obs,provider='estimated_world_spawn_v1'):
    return make_anchor(dict(identity=obs['identity'],dimension='overworld',provider=provider,
        observed_build=None if provider=='estimated_world_spawn_v1' else '1.26.52.3',
        evidence_sha256='e'*64),[-7,23])


def test_replace_only_estimate_preserving_raw_facts_and_other_modes():
    before=observation();before['anchors'].append(dict(mode='world_spawn_observed',coordinate=[1,2],source_id='a'*64))
    frozen=copy.deepcopy(before);new=anchor(before)
    after=reanchor_observation(before,new)
    assert before==frozen
    assert {k:v for k,v in after.items() if k!='anchors'}=={k:v for k,v in before.items() if k!='anchors'}
    assert after['anchors'][-1]==before['anchors'][-1]
    assert next(a for a in after['anchors'] if a['mode']=='world_spawn_estimated')==dict(
        mode='world_spawn_estimated',coordinate=[-7,23],source_id=new['anchor_id'])


def test_wrong_world_or_observed_provider_cannot_replace_prediction():
    obs=observation();wrong=anchor(obs);wrong['context']['identity']=dict(obs['identity'],seed='999')
    with pytest.raises(ValueError):reanchor_observation(obs,wrong)
    with pytest.raises(ValueError):reanchor_observation(obs,anchor(obs,'observed_world_spawn_v1'))


def test_missing_grid_cannot_publish_a_spawn_only_migration():
    before=observation();after=reanchor_observation(before,anchor(before))
    with pytest.raises(ValueError,match='Missing fixed-grid'):reanchor_summaries(before,after,[])


def test_committed_receipt_replay_preserves_generation_and_rejects_wrong_pin_or_corrupt_bytes(tmp_path):
    from seed_search.catalog.store import AutomationStore
    from seed_search.catalog.harvest import HarvestQueue,AutomationLedger
    from seed_search.catalog.registry import digest
    from seed_search.catalog.models import world_id
    obs=observation();oid=digest(obs);wid=world_id(obs['identity']);store=AutomationStore(tmp_path)
    with HarvestQueue(tmp_path) as queue:
        ledger=AutomationLedger(queue,policy_revision='a'*64,objectives={'test':1})
        assert committed_migration(store,ledger,wid,oid,'b'*64,obs) is None
        artifact=store.stage(obs,[])
        receipt=dict(world_id=wid,identity=obs['identity'],observation_id=oid,artifact=artifact,
                     evaluations=[],replay={'migration_pin':'b'*64})
        ledger.offer(receipt,[])
        assert committed_migration(store,ledger,wid,oid,'b'*64,obs)==receipt
        assert ledger.population()==ledger.generation()==1
        with pytest.raises(ValueError,match='Conflicting'):committed_migration(store,ledger,wid,oid,'c'*64,obs)
        (store.objects_dir/artifact['relative_key']).write_bytes(b'corrupt')
        with pytest.raises(ValueError):committed_migration(store,ledger,wid,oid,'b'*64,obs)


@pytest.mark.parametrize('coordinate',[[-7,23],[0,0]])
def test_summary_reuse_equals_full_rederivation_and_restores_grid_iterator(coordinate):
    from seed_search.catalog import summaries
    before=observation();new=make_anchor(anchor(before)['context'],coordinate)
    after=reanchor_observation(before,new)
    original=summaries.anchors
    full=summaries.summarize_v2(after)
    reused=reanchor_summaries(before,after,summaries.summarize_v2(before))
    assert sorted(reused,key=lambda r:r['layout_id'])==sorted(full,key=lambda r:r['layout_id'])
    assert summaries.anchors is original
    after['structures']['structure.village'].append([123,456])
    with pytest.raises(ValueError,match='raw facts changed'):reanchor_summaries(before,after,[])


@pytest.mark.parametrize('count',[0,2])
def test_missing_or_ambiguous_original_estimate_is_not_silently_migrated(count):
    obs=observation();saved=copy.deepcopy(obs['anchors'][0]);new=anchor(obs)
    obs['anchors']=[copy.deepcopy(saved) for _ in range(count)]
    if count==2:obs['anchors'][1]['coordinate']=[100,100]
    with pytest.raises(ValueError,match='exactly one' if count==0 else 'Ambiguous spawn'):
        reanchor_observation(obs,new)
