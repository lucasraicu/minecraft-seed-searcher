"""Derived read views preserve exact ranking and remain protected immutable roots."""
import copy
import pytest
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.harvest import HarvestQueue,AutomationLedger
from seed_search.catalog.models import identity,empty_observation_v2,world_id
from seed_search.catalog.summaries import summarize_v2
from seed_search.catalog.query import rank_v2
from seed_search.catalog.registry import digest
from seed_search.catalog.ingestion import atomic_json


def build(root,seed,rank):
    store=AutomationStore(root)
    obs=empty_observation_v2(identity(seed,model_id='26.50',native_sha256='a'*64,source_sha256='b'*64))
    obs['structures']={'structure.village':[[-1,0],[512,0]],'structure.bastion':[[-1,0]]}
    obs['anchors']=[dict(mode='world_spawn_estimated',coordinate=[-1,-9],source_id='d'*64)]
    rows=summarize_v2(obs);wid=world_id(obs['identity']);oid=digest(obs)
    receipt=dict(world_id=wid,identity=obs['identity'],observation_id=oid,artifact=store.stage(obs,rows),evaluations=[],replay={})
    with HarvestQueue(root) as q:
        ledger=AutomationLedger(q,policy_revision='c'*64,objectives={'test':1})
        ledger.offer(receipt,[dict(objective_id='test',rank=[rank],member=dict(world_id=wid,source_observation_id=oid))])
        sid=store.publish(ledger)
    return store,sid,obs,rows


def test_all_sides_modes_and_dimension_combinations_match_raw_bundle(tmp_path):
    store,sid,obs,rows=build(tmp_path,'1',1);manifest=store.snapshot(sid)
    for side in (2048,4096,8192):
        for mode in ('recommended','origin','world_spawn_estimated'):
            req=dict(request_revision='catalog-query-v2',edition='bedrock',dimension='overworld',
                game_build_id=obs['identity']['game_build_id'],world_settings_id='default',catalog_snapshot_id=sid,
                evidence_policy='predicted_observations_v2',fallback_profile='balanced_survival',border_side=side,
                anchor_mode=mode,rows=[dict(rule='required',kind='structure_count',feature='structure.village',at_least=1,
                    scope=dict(kind='inside_border')),dict(rule='preferred',kind='structure_count',feature='structure.bastion',
                    at_least=2,importance=3,scope=dict(kind='near_base',radius=64))])
            assert rank_v2(rows,req,keep_keys=True)==rank_v2(store.iter_query_summaries(manifest,side,mode),req,keep_keys=True)
    # Legacy four-field world references still use their verified raw bundle.
    old=copy.deepcopy(manifest)
    for entry in old['worlds']:entry.pop('summary_artifacts')
    assert list(store.iter_query_summaries(old,2048,'origin'))==[r for r in rows if r['border_side']==2048 and 'origin' in r['anchor_modes']]


@pytest.mark.parametrize('damage',['world','bundle','side','summary','file'])
def test_corruption_and_source_mismatch_fail_closed(tmp_path,damage):
    store,sid,_,_=build(tmp_path,'1',1);manifest=store.snapshot(sid);entry=manifest['worlds'][0]
    artifact=entry['summary_artifacts']['2048'];value=store.artifacts.get_json(artifact)
    if damage=='file':
        (store.objects_dir/artifact['relative_key']).write_bytes(b'corrupt')
    else:
        if damage=='world':value['world_id']='f'*64
        if damage=='bundle':value['bundle_sha256']='f'*64
        if damage=='side':value['border_side']=4096
        if damage=='summary':value['rows'][0]['source_observation_id']='f'*64
        entry['summary_artifacts']['2048']=store.artifacts.put_json(value)
    with pytest.raises(ValueError):list(store.iter_query_summaries(manifest,2048,'recommended'))


def test_historical_projection_pages_survive_gc_and_old_generation_is_not_rewritten(tmp_path):
    store,sid,_,_=build(tmp_path,'1',10);before=store.snapshot(sid)
    projection_keys={a['relative_key'] for a in before['worlds'][0]['summary_artifacts'].values()}
    assert before['product_status']['realm.v2.qualified']=={'match':0,'no_match':0,'pending':1}
    _,sid2,_,_=build(tmp_path,'2',0)
    with HarvestQueue(tmp_path) as q:
        ledger=AutomationLedger(q,policy_revision='c'*64,objectives={'test':1})
        report=store.cleanup(ledger,mode='quarantine')
        assert not projection_keys.intersection(report['candidates'])
        assert store.publish(ledger)==sid2
    assert len(list(store.iter_query_summaries(store.snapshot(sid),2048,'origin')))==1


def test_same_generation_projection_upgrade_preserves_old_snapshot(tmp_path):
    store,sid,_,_=build(tmp_path,'1',1);manifest=store.snapshot(sid)
    for entry in manifest['worlds']:entry.pop('summary_artifacts')
    old_sid=digest(manifest);artifact=store._write_manifest(manifest)
    binding=dict(revision='catalog-snapshot-binding-v2',snapshot_id=old_sid,generation=manifest['generation'],artifact=artifact)
    # Model an existing pre-projection namespace, not a mutation of public data.
    (store.snapshots_dir/(sid+'.json')).unlink()
    atomic_json(store.snapshots_dir/(old_sid+'.json'),binding)
    atomic_json(store.generations_dir/(manifest['policy_revision']+'-'+str(manifest['generation'])+'.json'),binding)
    atomic_json(store.current_path,binding)
    with HarvestQueue(tmp_path) as q:
        ledger=AutomationLedger(q,policy_revision='c'*64,objectives={'test':1})
        assert store.publish(ledger)==old_sid
    assert 'summary_artifacts' not in store.snapshot()['worlds'][0]


def test_validator_bound_fast_path_and_legacy_fallback(tmp_path,monkeypatch):
    from seed_search.catalog import codec
    store,sid,_,_=build(tmp_path,'1',1);manifest=store.snapshot(sid);entry=manifest['worlds'][0]
    original=codec.validate_summary_v2;calls=[]
    def track(row):calls.append(row['layout_id']);return original(row)
    monkeypatch.setattr(codec,'validate_summary_v2',track)
    expected=list(store.iter_query_summaries(manifest,2048,'recommended'))
    assert expected and calls==[]  # Full validation happened at stage/publication.
    value=store.artifacts.get_json(entry['summary_artifacts']['2048'])
    value['summary_validator_sha256']='f'*64
    entry['summary_artifacts']['2048']=store.artifacts.put_json(value)
    assert list(store.iter_query_summaries(manifest,2048,'recommended'))==expected
    assert len(calls)==len(value['rows'])
    value['revision']='catalog-query-projection-v2'
    value.pop('row_count');value.pop('summary_validator_sha256')
    entry['summary_artifacts']['2048']=store.artifacts.put_json(value)
    assert list(store.iter_query_summaries(manifest,2048,'recommended'))==expected


def test_projection_truncation_and_invalid_fallback_rows_are_rejected(tmp_path):
    store,sid,_,_=build(tmp_path,'1',1);manifest=store.snapshot(sid);entry=manifest['worlds'][0]
    value=store.artifacts.get_json(entry['summary_artifacts']['2048'])
    value['rows'].pop()
    entry['summary_artifacts']['2048']=store.artifacts.put_json(value)
    with pytest.raises(ValueError,match='row count'):list(store.iter_query_summaries(manifest,2048,'origin'))
    value['row_count']=len(value['rows']);value['summary_validator_sha256']='f'*64
    value['rows'][0]['features']['structure.village']['counts']=[2,1,0,0]
    entry['summary_artifacts']['2048']=store.artifacts.put_json(value)
    with pytest.raises(ValueError):list(store.iter_query_summaries(manifest,2048,'origin'))
