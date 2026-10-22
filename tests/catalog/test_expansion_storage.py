import copy
import pytest
from seed_search.catalog.registry import REGISTRY_V3,SAMPLING_PROFILE_REVISION_V3,digest
from seed_search.catalog.biome_extension import provider_id,validate_extension
from seed_search.catalog.models import empty_observation_v2,identity,world_id
from seed_search.catalog.summaries import summarize_v3,summarize_v2
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.harvest import HarvestQueue,AutomationLedger
from seed_search.catalog.retention import automation_objectives_v3,automation_offers_v3
from seed_search.catalog.reserve_policy import contract_id


def observation():
    o=empty_observation_v2(identity('1',model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64))
    o['biomes']['overworld']=[[256,160,0,4],[0,63,256,4]];o['biome_names']={'4':'forest'}
    return o


def extension(o):
    return dict(revision='catalog-biome-extension-v3',base_observation_id=digest(o),
        sampling_profile_revision=SAMPLING_PROFILE_REVISION_V3,provider_id=provider_id(o),
        bounds=o['bounds']['overworld'],biomes={'overworld':[[0,96,0,4]]},biome_names={'4':'forest'})


def test_extension_strict_source_profile_provider_namespace_and_xyz():
    o=observation();e=extension(o);validate_extension(e,o)
    for key,value in [('provider_id','f'*64),('sampling_profile_revision','x'),('base_observation_id','f'*64),('biome_names',{'4':'desert'}),('biomes',{'overworld':[[1,96,0,4]]}),('biomes',{'overworld':[[256,160,0,4]]})]:
        with pytest.raises(ValueError):validate_extension(dict(e,**{key:value}),o)


def test_group_equals_member_union_and_xyz_tie():
    o=observation();s=summarize_v3(o,base_summaries=summarize_v2(o));r=next(r for r in s if r['anchor']==[0,0] and r['border_side']==2048)
    assert r['features']['biome.group.forest']==r['features']['biome.exact.forest']
    assert r['features']['biome.exact.forest']['witness']==[0,63,256]
    base=summarize_v2(o);foreign=copy.deepcopy(base);foreign[0]['source_observation_id']='f'*64
    with pytest.raises(ValueError):summarize_v3(o,base_summaries=foreign)


def test_v3_real_cas_ledger_paging_and_gc_extension(tmp_path):
    o=observation();e=extension(o);sums=summarize_v3(o,extension=e,base_summaries=summarize_v2(o))
    store=AutomationStore(tmp_path);store._PAGE_THRESHOLD_BYTES=1;store._PAGE_ITEM_LIMIT=8
    with HarvestQueue(tmp_path) as q:
        caps=automation_objectives_v3()
        with pytest.raises(ValueError):AutomationLedger(q,policy_revision='a'*64,objectives=caps)
        bad=dict(caps);bad[next(iter(bad))]+=1
        with pytest.raises(ValueError):AutomationLedger(q,policy_revision='a'*64,objectives=bad,policy_contract=contract_id())
        ledger=AutomationLedger(q,policy_revision='a'*64,objectives=caps,policy_contract=contract_id())
        artifact=store.stage(o,sums,extension=e,registry_v3=REGISTRY_V3)
        receipt=dict(world_id=world_id(o['identity']),identity=o['identity'],observation_id=digest(o),artifact=artifact,evaluations=[],replay={'verification_in_progress':True})
        with q.ownership():
            ledger.offer(receipt,automation_offers_v3(o,sums,[],registry=REGISTRY_V3))
            sid=store.publish(ledger,registry_v3=REGISTRY_V3,sampling_profile_revision=SAMPLING_PROFILE_REVISION_V3)
        m=store.snapshot(sid);assert m['revision']=='catalog-snapshot-v3';assert m['reserve_policy']['retained_slots']==231928
        assert store.world(sid,receipt['world_id'])['observation']==o
        projected=list(store.iter_query_summaries(m,2048,'origin'));assert len(projected)==1
        assert projected[0]==next(r for r in sums if r['border_side']==2048 and r['anchor']==[0,0])
        with q.ownership():report=store.cleanup(ledger,mode='dry_run')
        assert report is not None


def test_reserve_only_objective_roles_and_verification_gc_roots(tmp_path):
    a='v3.near:biome.exact.forest:2048:origin';b='v3.near:biome.exact.forest:2048:recommended'
    store=AutomationStore(tmp_path);refs={};worlds=[]
    with HarvestQueue(tmp_path) as queue:
        ledger=AutomationLedger(queue,policy_revision='e'*64,objectives=automation_objectives_v3(),policy_contract=contract_id())
        with queue.ownership():
            for i in range(22):
                o=observation();o['identity']=identity(str(i+1),model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64)
                e=extension(o);base=[s for s in summarize_v2(o) if s['anchor']==[0,0]]
                sums=summarize_v3(o,extension=e,base_summaries=base);artifact=store.stage(o,sums,extension=e,registry_v3=REGISTRY_V3)
                wid=world_id(o['identity']);worlds.append(wid);refs[wid]=artifact
                member=dict(world_id=wid,source_observation_id=digest(o),anchor=[0,0],layout_id=sums[0]['layout_id'])
                offers=[] if i==21 else [dict(objective_id=a,rank=[i],member=member),dict(objective_id=b,rank=[-i],member=member)]
                ledger.offer(dict(world_id=wid,identity=o['identity'],observation_id=digest(o),artifact=artifact,evaluations=[],replay={}),offers)
            sid=store.publish(ledger,registry_v3=REGISTRY_V3,sampling_profile_revision=SAMPLING_PROFILE_REVISION_V3)
            members=store.snapshot(sid)['memberships'];first=[r['world_id'] for r in members if r['objective_id']==a];second=[r['world_id'] for r in members if r['objective_id']==b]
            assert first[20]==worlds[20] and second[0]==worlds[20]  # reserve here, primary there
            assert set(ledger.retained_worlds())==set(worlds[:21])
            store.pin(sid,worlds[20]);ledger.protect_verification([worlds[21]])
            orphan=store.artifacts.put_json({'unreachable':True})
            report=store.cleanup(ledger,mode='reclaim')
            assert orphan['relative_key'] in report['candidates']
            # Both reserve-only and non-retained in-progress bundles retain their separate extension objects.
            for wid in (worlds[20],worlds[21]):
                bundle=store.artifacts.get_json(refs[wid]);assert store.artifacts.get_json(bundle['extension_artifact'])['base_observation_id']==ledger.receipt(wid)['observation_id']
            ledger.protect_verification([worlds[21]],release=True)
            report=store.cleanup(ledger,mode='reclaim')
            assert refs[worlds[21]]['relative_key'] in report['candidates']
            assert store.world(sid,worlds[20])['observation']['identity']['seed']=='21'
            from seed_search.catalog.service import CatalogService
            service=CatalogService(tmp_path,secret=b'reserve-union-test')
            try:
                header=store.snapshot(sid)['worlds'][0]['identity']
                req=dict(request_revision='catalog-query-v3',edition='bedrock',dimension='overworld',game_build_id=header['game_build_id'],world_settings_id=header['world_settings_id'],catalog_snapshot_id=sid,evidence_policy='predicted_observations_v3',fallback_profile='balanced_survival',border_side=2048,anchor_mode='origin',rows=[])
                result=service.query(dict(request=req,page_size=50))
                assert result['matched_worlds']==21
                assert worlds[20] in {c['world_id'] for c in result['results']}
            finally:service.close()



def test_spawn_collision_preserves_each_original_legacy_payload():
    o=observation();o['anchors']=[dict(mode='world_spawn_estimated',coordinate=[0,0],source_id='f'*64)]
    original=summarize_v2(o);expanded=summarize_v3(o,base_summaries=original)
    by_scope={(tuple(s['anchor']),s['border_side'],tuple(s['anchor_modes'])):s['legacy'] for s in original}
    for row in expanded:
        assert row['legacy']==by_scope[(tuple(row['anchor']),row['border_side'],tuple(row['anchor_modes']))]
