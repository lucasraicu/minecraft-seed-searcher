from seed_search.catalog import finalization_operator as op
from seed_search.catalog.registry import digest


def test_real_cas_ledger_scoped_checkpoint_resume_and_pending_gc(tmp_path):
    import json
    from seed_search.catalog.registry import REGISTRY_V3,SAMPLING_PROFILE_REVISION_V3
    from seed_search.catalog.models import empty_observation_v2,identity,world_id
    from seed_search.catalog.summaries import summarize_v2,summarize_v3
    from seed_search.catalog.store import AutomationStore
    from seed_search.catalog.harvest import HarvestQueue,AutomationLedger
    from seed_search.catalog.retention import automation_objectives_v3,automation_offers_v3
    from seed_search.catalog.reserve_policy import contract_id
    from seed_search.catalog.finalization import evidence_identity,make_evidence_receipt
    obs=empty_observation_v2(identity('17',model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64))
    obs['biomes']['overworld']=[[0,63,0,4]];obs['biome_names']={'4':'forest'}
    obs['structures']={'structure.village':[[0,0]]}
    obs['coverage']['structure.village']={'status':'complete','bounds':obs['bounds']['overworld'],'method_id':'synthetic-complete'}
    obs['anchors']=[dict(mode='world_spawn_estimated',coordinate=[-17,-25],source_id='f'*64)]
    from seed_search.catalog.product_evaluation import evaluate_products
    evaluations=evaluate_products(obs)
    summaries=summarize_v3(obs,base_summaries=summarize_v2(obs));store=AutomationStore(tmp_path)
    objective='v3.near:biome.exact.forest:2048:origin'
    context=dict(build_id='1.26.52.3',provider_id='c'*64,profile='sampled-xyz',dimension='overworld',evidence_policy='actual-scoped',requirements=dict(objective_id=objective,policy_revision='e'*64,features=['biome.exact.forest']))
    calls=[]
    def verify(c,eid):
        calls.append(c['world_id'])
        scope=evidence_identity(c['seed'],anchor=c['anchor'],border=c['border_side'],dimension=c['dimension'],profile=c['profile'],build_id=c['build_id'],requirements=c['requirements'],world_settings_id=c['world_settings_id'],source_observation_id=c['source_observation_id'],provider_id=c['provider_id'],evidence_policy=c['evidence_policy'])[1]
        return make_evidence_receipt(eid,c['world_id'],c['seed'],'pass',details=dict(actual=True,source='actual',provider='official BDS 1.26.52.3',scope=scope,requirements_complete=True,evidence_artifacts=['d'*64]))
    with HarvestQueue(tmp_path) as queue:
        ledger=AutomationLedger(queue,policy_revision='e'*64,objectives=automation_objectives_v3(),policy_contract=contract_id())
        artifact=store.stage(obs,summaries,registry_v3=REGISTRY_V3)
        with queue.ownership():
            ledger.offer(dict(world_id=world_id(obs['identity']),identity=obs['identity'],observation_id=digest(obs),artifact=artifact,evaluations=evaluations,replay={}),automation_offers_v3(obs,summaries,evaluations,registry=REGISTRY_V3))
            sid=store.publish(ledger,registry_v3=REGISTRY_V3,sampling_profile_revision=SAMPLING_PROFILE_REVISION_V3)
        result=op.finalize_objective(store,ledger,sid,objective,context,verifier=verify,budget=1)
        assert result['verified_count']==1 and not result['is_complete'] and calls==[world_id(obs['identity'])]
        # A new invocation reconstructs receipts/progress from SQLite, not JSON or a process cache.
        resumed=op.finalize_objective(AutomationStore(tmp_path),ledger,sid,objective,context,budget=0)
        assert resumed['verified_count']==1 and resumed['checks_performed']==0
        other='v3.near:biome.exact.forest:2048:recommended'
        other_context=dict(context,requirements=dict(context['requirements'],objective_id=other))
        reused=op.finalize_objective(AutomationStore(tmp_path),ledger,sid,other,other_context,budget=0)
        assert reused['verified_count']==1 and reused['checks_performed']==0
        assert calls==[world_id(obs['identity'])]
        assert len(ledger.conn.execute("SELECT key FROM automation_meta WHERE key LIKE 'verification.evidence.%'").fetchall())==1
        protected=json.loads(ledger.conn.execute("SELECT value FROM automation_meta WHERE key='verification_worlds'").fetchone()[0])
        assert world_id(obs['identity']) in protected
        with queue.ownership():store.cleanup(ledger,mode='dry_run')
        assert store.world(sid,world_id(obs['identity']))['observation']==obs
        reference='reference_sample'
        ref_context=dict(context,dimension='nether',requirements=dict(objective_id=reference,policy_revision='e'*64,features=['biome.nether_wastes'],verification_anchor=[-3,-4],verification_border_side=1024))
        pending=op.finalize_objective(store,ledger,sid,reference,ref_context,budget=0)
        assert pending['pending'][0]['anchor']==[-3,-4] and pending['pending'][0]['border_side']==1024
        product='record.v2.village_density'
        product_context=dict(context,requirements=dict(objective_id=product,policy_revision='e'*64,features=['structure.village'],radius=2000))
        pending=op.finalize_objective(store,ledger,sid,product,product_context,budget=0)
        assert pending['pending'][0]['anchor']==[-17,-25] and pending['pending'][0]['border_side']==4096
        manifest=store.snapshot(sid)
        legacy=next(r for r in manifest['memberships'] if r['member'].get('layout_id') and not isinstance(r['member'].get('anchor'),list) and not isinstance(r['member'].get('anchor'),dict))
        old_context=dict(context,requirements=dict(objective_id=legacy['objective_id'],policy_revision='e'*64,features=['biome.forest']))
        pending=op.finalize_objective(store,ledger,sid,legacy['objective_id'],old_context,budget=0)
        assert len(pending['pending'][0]['anchor'])==2



def test_pending_higher_rank_prevents_premature_cached_reserve_finalists():
    from test_finalization_scopes import candidate,receipt,scope
    from seed_search.catalog.finalization import evidence_identity
    rows=[candidate(i) for i in range(1,5)];cache={}
    for c in rows[2:]:
        eid=evidence_identity(c['seed'],anchor=c['anchor'],border=c['border_side'],dimension=c['dimension'],profile=c['profile'],build_id=c['build_id'],requirements=c['requirements'],world_settings_id=c['world_settings_id'],source_observation_id=c['source_observation_id'],provider_id=c['provider_id'],evidence_policy=c['evidence_policy'])[0]
        cache[eid]=receipt(c,eid)
    out=op.advance_ordered_finalization('obj',rows,2,cache,budget=0)
    assert out['verified_count']==0 and not out['is_complete'] and len(out['provisional_passes'])==2
    def verify(c,eid):return receipt(c,eid,'fail' if c['seed']=='1' else 'pass')
    done=op.advance_ordered_finalization('obj',rows,2,out['receipts'],verifier=verify,budget=2,previous=out['progress'])
    assert done['is_complete'] and [c['seed'] for c in done['finalized']]==['2','3']
    assert [c['seed'] for c in done['promoted']]==['3']
