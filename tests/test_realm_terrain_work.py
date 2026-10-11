"""Durable center/stage scheduling with deterministic nonnative raster providers."""
import copy
import numpy as np
import pytest
from seed_search.realm.raster import Raster
from seed_search.realm.store import RealmStore
from seed_search.realm.terrain import run_terrain

IDENTITY={'provider':'durable-test','build':'1'}
CFG={'terrain':{'maximum_refinements_per_anchor':1,'resolutions':[128,64,32,16],
                'center_spacing':64,'refine_center_spacing':16,'maximum_halo_expansions':2,
                'v1':{'diameter_max':100,'ideal_water_width':10,'water_width':4},
                'v2':{'distance_max':80,'ridge_support_width':4}}}


def checkpoint(path,count=1):
    store=RealmStore(path,identity={'config':CFG})
    store.configure_range(0,count);store.claim_range('test')
    candidate=dict(id='42:0:0',seed='42',stronghold=[0,0],bounds={'overworld':[-256,-256,256,256]},qualification='PREDICTED',baseline_score=30)
    rows=[dict(index=i,seed=str(42+i),anchors=[{**candidate,'id':f'{42+i}:0:0','seed':str(42+i)}]) for i in range(count)]
    store.complete_range(0,count,rows)
    return store,candidate


class Provider:
    def __init__(self):self.calls=[];self.fail_resolution=None
    def sample_raster(self,seed,bounds,resolution,stage,dimension,settings):
        self.calls.append((tuple(bounds),resolution,stage))
        if resolution==self.fail_resolution:raise RuntimeError('controlled interruption')
        shape=(int(np.ceil((bounds[3]-bounds[1])/resolution)),int(np.ceil((bounds[2]-bounds[0])/resolution)))
        return Raster(bounds,resolution,np.full(shape,80.),metadata={'source':'prediction'},water=np.zeros(shape,bool))


def controls(monkeypatch,centers=((0,0),),low=False,unresolved=False):
    monkeypatch.setattr('seed_search.realm.terrain.propose_centers',lambda *a:list(centers))
    def evaluate(raster,center,*args,**kwargs):
        score=10. if low else 90.
        return dict(center=list(center),geometry_score=score,biome_fit=kwargs.get('biome_fit',0),
                    baseline_quality=kwargs.get('baseline_quality',0),geometry_pass=not low,
                    evidence='PREDICTED',qualification='PREDICTED_NEAR_MATCH' if low else 'PREDICTED',
                    reasons=['fixture low geometry'] if low else [],metrics={'fixture_resolution':raster.resolution},
                    pending_work=[],border_fit={'complete':not unresolved,'state':'unknown' if unresolved else 'within'},
                    provider=raster.metadata,resolution=raster.resolution)
    monkeypatch.setattr('seed_search.realm.terrain.evaluate_v1',evaluate)
    monkeypatch.setattr('seed_search.realm.terrain.evaluate_v2',evaluate)


def run(store,provider,variants=('v1',),**kwargs):
    return run_terrain(store,CFG,variants,provider_factory=lambda seed:provider,provider_identity=IDENTITY,**kwargs)


def test_budget_retains_all_centers_and_repeated_invocation_advances_without_resampling(tmp_path,monkeypatch):
    controls(monkeypatch,centers=((0,0),(64,0),(128,0)))
    store,candidate=checkpoint(tmp_path);provider=Provider()
    try:
        first=run(store,provider)
        assert first['pending_work']==2 and first['results']==3
        assert store.get_variant_task_status(candidate['id'],'v1')=='started'
        calls=copy.deepcopy(provider.calls)
        second=run(store,provider)
        assert second['pending_work']==1 and second['results']==3
        assert all(call not in calls for call in provider.calls[len(calls):])
        third=run(store,provider)
        assert third['pending_work']==third['deferred_work']==0
        assert store.get_variant_task_status(candidate['id'],'v1')=='complete'
        calls=copy.deepcopy(provider.calls)
        resumed=run_terrain(store,CFG,('v1',),provider_factory=lambda seed:(_ for _ in ()).throw(AssertionError('no generator')),provider_identity=IDENTITY)
        assert resumed['results']==0 and provider.calls==calls
        assert store.get_candidate(candidate['id'])==candidate
    finally:store.close()


def test_low_score_finer_unit_is_deferred_then_progresses_without_repeat(tmp_path,monkeypatch):
    controls(monkeypatch,low=True)
    store,candidate=checkpoint(tmp_path);provider=Provider()
    try:
        first=run(store,provider)
        assert first['deferred_work']==1
        assert [call[1] for call in provider.calls]==[128,64,32]
        assert store.get_variant_task_status(candidate['id'],'v1')!='complete'
        first_metrics=list(store.iter_variants())[0]['result']
        assert any('finer geometry' in reason for reason in first_metrics['pending_work'])
        second=run(store,provider)
        assert [call[1] for call in provider.calls]==[128,64,32,16]
        assert second['pending_work']==second['deferred_work']==0
        assert store.get_variant_task_status(candidate['id'],'v1')=='complete'
    finally:store.close()


def test_interruption_resumes_next_stage_and_keeps_committed_metrics(tmp_path,monkeypatch):
    controls(monkeypatch)
    store,candidate=checkpoint(tmp_path);provider=Provider();provider.fail_resolution=32
    try:
        with pytest.raises(RuntimeError,match='interruption'):run(store,provider)
        prior=list(store.iter_variants())[0]['result']
        assert prior['resolution']==64
        revision=store.get_state('terrain_pool_revision')
        assert store.terrain_work_counts(revision)['leased']==1
        provider.fail_resolution=None
        run(store,provider)
        assert [call[1] for call in provider.calls].count(64)==1
        assert [call[1] for call in provider.calls].count(128)==1
        assert list(store.iter_variants())[0]['result']['resolution']==16
        assert store.terrain_work_counts(revision).get('leased',0)==0
    finally:store.close()


def test_independent_variants_reuse_durable_prediction_channels_across_invocations(tmp_path,monkeypatch):
    controls(monkeypatch)
    store,candidate=checkpoint(tmp_path);provider=Provider()
    try:
        v1=run(store,provider,('v1',));calls=copy.deepcopy(provider.calls)
        def forbidden(seed):raise AssertionError('V2 should decode shared exact sampling observations')
        v2=run_terrain(store,CFG,('v2',),provider_factory=forbidden,provider_identity=IDENTITY)
        assert v1['results']==v2['results']==3
        assert v2['durable_raster_hits']==4
        assert provider.calls==calls
        assert {r['variant'] for r in store.iter_variants()}=={'v1','v2'}
        for observation in store.iter_observations():
            if observation.get('kind')=='terrain_raster':
                assert observation['channels']['encoding']=='npz-base64'
                assert set(observation['lattice'])=={'x0','z0','step','shape'}
    finally:store.close()


def test_halo_cap_leaves_manual_pending_and_explicit_continuation_advances_once(tmp_path,monkeypatch):
    controls(monkeypatch,unresolved=True)
    store,candidate=checkpoint(tmp_path);provider=Provider()
    try:
        run(store,provider)
        run(store,provider);run(store,provider)
        revision=store.get_state('terrain_pool_revision')
        remaining=list(store.iter_terrain_work(revision,status='deferred'))
        assert len(remaining)==1
        assert remaining[0]['payload']['halo_level']==3
        assert remaining[0]['payload']['manual_continuation_required']
        assert remaining[0]['payload']['needed_bounds']==remaining[0]['payload']['raster_bounds']
        calls=len(provider.calls)
        stopped=run(store,provider)
        assert stopped['candidates']==0 and len(provider.calls)==calls
        assert store.get_variant_task_status(candidate['id'],'v1')=='started'
        advanced=run(store,provider,continue_deferred_halos=True)
        assert advanced['work_completed']==1 and len(provider.calls)==calls+1
        assert list(store.iter_terrain_work(revision,status='deferred'))[0]['payload']['halo_level']==4
        assert store.get_candidate(candidate['id'])==candidate
    finally:store.close()


@pytest.mark.parametrize('failure',['failed','unsupported','unknown_source','missing','unstable_actual'])
def test_bad_nomination_stays_retryable_then_recovers_without_stale_raw_cache(tmp_path,monkeypatch,failure):
    controls(monkeypatch)
    store,candidate=checkpoint(tmp_path)
    class FirstBad(Provider):
        def sample_raster(self,*args,**kwargs):
            raster=super().sample_raster(*args,**kwargs)
            if failure=='unstable_actual':raster.metadata={'source':'actual','stable_sampled_observations':len(self.calls)>1}
            elif len(self.calls)==1:
                if failure=='unknown_source':raster.metadata={}
                elif failure=='missing':raster.known[0,0]=False
                else:raster.metadata={'source':'prediction',failure:True}
            return raster
    provider=FirstBad();identity={**IDENTITY,**({'source':'actual'} if failure=='unstable_actual' else {})}
    def invoke():return run_terrain(store,CFG,('v1',),provider_factory=lambda seed:provider,provider_identity=identity)
    try:
        first=invoke();revision=first['pool_revision']
        nomination=list(store.iter_terrain_work(revision))[0]
        assert nomination['status']=='deferred'
        assert first['deferred_work']==1
        assert store.get_variant_task_status(candidate['id'],'v1')!='complete'
        assert store.get_observation(nomination['sampling_key']) is None
        assert store.get_observation(nomination['sampling_key']+':unit:'+nomination['unit_id']+':attempt:1') is not None
        assert list(store.iter_variants())[0]['result']['qualification']=='PENDING'
        invoke()
        restored=store.get_terrain_work(nomination['unit_id'])
        assert restored['status']=='complete' and restored['attempts']==2
        assert sum(stage=='nomination' for _,_,stage in provider.calls)==2
        assert store.get_observation(nomination['sampling_key']) is not None
        assert store.get_candidate(candidate['id'])==candidate
    finally:store.close()


def test_partial_height_retains_closest_metrics_and_retries_exact_uncommitted_stage(tmp_path,monkeypatch):
    controls(monkeypatch)
    store,candidate=checkpoint(tmp_path)
    class PartialOnce(Provider):
        partial=True
        def sample_raster(self,*args,**kwargs):
            raster=super().sample_raster(*args,**kwargs)
            if kwargs['stage']=='height' and kwargs['resolution']==64 and self.partial:
                raster.known[0,0]=False;self.partial=False
            return raster
    provider=PartialOnce()
    try:
        first=run(store,provider)
        assert first['deferred_work']==1
        closest=list(store.iter_variants())[0]['result']
        assert closest['qualification']=='PENDING' and closest['metrics']['fixture_resolution']==64
        assert any('missing' in reason for reason in closest['pending_work'])
        second=run(store,provider)
        assert second['deferred_work']==0
        assert sum(res==64 for _,res,_ in provider.calls)==2
        assert sum(res==128 for _,res,_ in provider.calls)==1
        assert list(store.iter_variants())[0]['result']['resolution']==16
    finally:store.close()


def test_rotating_limit_one_reaches_later_anchor_despite_permanent_first_failure(tmp_path,monkeypatch):
    controls(monkeypatch)
    store,candidate=checkpoint(tmp_path,count=2)
    class FirstAnchorFails(Provider):
        seeds=[]
        def sample_raster(self,*args,**kwargs):
            self.seeds.append(kwargs['seed'])
            raster=super().sample_raster(*args,**kwargs)
            if kwargs['seed']=='42':raster.metadata={'source':'prediction','failed':True}
            return raster
    provider=FirstAnchorFails()
    try:
        first=run(store,provider,limit=1)
        assert first['pool_cursor']=='42:0:0'
        assert store.get_variant_task_status('42:0:0','v1')!='complete'
        store.close();store=RealmStore(tmp_path,resume=True)
        second=run(store,provider,limit=1)
        assert second['pool_revision']==first['pool_revision']
        assert second['pool_cursor']=='43:0:0'
        assert store.get_variant_task_status('43:0:0','v1')=='complete'
        assert store.get_variant_task_status('42:0:0','v1')!='complete'
        third=run(store,provider,limit=1)
        assert third['pool_cursor']=='42:0:0'
        assert provider.seeds.count('42')==2
        assert store.get_terrain_pool(first['pool_revision'])['members']==2
    finally:store.close()


def test_variant_cursor_is_independent_of_other_variant_progress(tmp_path,monkeypatch):
    controls(monkeypatch)
    store,candidate=checkpoint(tmp_path,count=2);provider=Provider()
    try:
        v1=run(store,provider,('v1',),limit=1)
        v2=run(store,provider,('v2',),limit=1)
        assert v1['pool_cursor']==v2['pool_cursor']=='42:0:0'
        assert v1['pool_revision']==v2['pool_revision']
        assert store.get_variant_task_status('43:0:0','v1')=='pending'
        assert store.get_variant_task_status('43:0:0','v2')=='pending'
        assert run(store,provider,('v1',),limit=1)['pool_cursor']=='43:0:0'
        assert run(store,provider,('v2',),limit=1)['pool_cursor']=='43:0:0'
    finally:store.close()


def test_actual_variants_keep_private_snapshots_and_resample_instead_of_raw_cache_reuse(tmp_path,monkeypatch):
    controls(monkeypatch)
    store,candidate=checkpoint(tmp_path)
    class Actual(Provider):
        def sample_raster(self,*args,**kwargs):
            raster=super().sample_raster(*args,**kwargs)
            raster.metadata={'source':'actual','stable_sampled_observations':True}
            return raster
    provider=Actual();identity={**IDENTITY,'source':'actual'}
    try:
        first=run_terrain(store,CFG,('v1',),provider_factory=lambda seed:provider,provider_identity=identity)
        second=run_terrain(store,CFG,('v2',),provider_factory=lambda seed:provider,provider_identity=identity)
        assert first['durable_raster_hits']==second['durable_raster_hits']==0
        assert len(provider.calls)==8
        observations=[o for o in store.iter_observations() if o.get('kind')=='terrain_raster']
        assert len(observations)==8
        assert all(o['metadata']['source']=='actual' for o in observations)
        assert all(row['result']['verified_score'] is None for row in store.iter_variants())
    finally:store.close()


def test_failed_prediction_variants_journal_attempts_without_shared_id_collision(tmp_path,monkeypatch):
    controls(monkeypatch)
    store,candidate=checkpoint(tmp_path)
    class TwoFailures(Provider):
        def sample_raster(self,*args,**kwargs):
            raster=super().sample_raster(*args,**kwargs)
            if len(self.calls)<=2:raster.metadata={'source':'prediction','failed':True}
            return raster
    provider=TwoFailures()
    try:
        first=run(store,provider,('v1','v2'))
        assert first['deferred_work']==2
        attempts=[o for o in store.iter_observations() if ':attempt:' in o['id']]
        assert len(attempts)==2 and len({o['id'] for o in attempts})==2
        second=run(store,provider,('v1','v2'))
        assert second['pending_work']==second['deferred_work']==0
        assert second['durable_raster_hits']==4
        assert store.get_variant_task_status(candidate['id'],'v1')=='complete'
        assert store.get_variant_task_status(candidate['id'],'v2')=='complete'
    finally:store.close()


def test_durable_raw_observation_roundtrip_preserves_every_channel_and_exact_lattice():
    from seed_search.realm.terrain import _encode_terrain_raster,_decode_terrain_raster,_terrain_work_payload
    bounds=(-3,-2,7,7);resolution=4
    height=np.arange(9,dtype=float).reshape(3,3);height[0,0]=np.nan
    known=np.isfinite(height);water=np.array([[False,True,False]]*3)
    ground=np.array([[True,False,True]]*3)
    biomes=np.arange(9,dtype=np.int16).reshape(3,3)
    raster=Raster(bounds,resolution,height,known=known,water=water,natural_ground=ground,biomes=biomes,
                  metadata={'source':'prediction','water_evidence':'height_proxy'})
    unit={'sampling_key':'fixture-key','payload':_terrain_work_payload('height',(0,0),resolution,bounds)}
    observation=_encode_terrain_raster(raster,unit)
    restored=_decode_terrain_raster(observation)
    assert restored.bounds==bounds and restored.resolution==resolution
    for channel in ('height','known','water','natural_ground','biomes'):
        np.testing.assert_array_equal(getattr(restored,channel),getattr(raster,channel))
    assert restored.metadata==raster.metadata


def test_limit_and_zero_work_report_uninitialized_pool_members_without_generation(tmp_path):
    store,candidate=checkpoint(tmp_path,count=2)
    try:
        def forbidden(seed):raise AssertionError('Limit zero must not construct provider')
        summary=run_terrain(store,CFG,('v1',),limit=0,provider_factory=forbidden,provider_identity=IDENTITY)
        assert summary['pending_work']==summary['deferred_work']==0
        assert summary['work_status']=={'pending':0,'deferred':0,'leased':0,'complete':0}
        assert summary['pool_uninitialized_by_variant']=={'v1':2,'v2':2}
        assert summary['uninitialized_variant_tasks']==4
        assert summary['requested_uninitialized_variant_tasks']==2
    finally:store.close()


def test_cursor_advances_even_if_first_anchor_provider_raises_before_observation(tmp_path,monkeypatch):
    controls(monkeypatch)
    store,candidate=checkpoint(tmp_path,count=2)
    class RaisesFirst(Provider):
        def sample_raster(self,*args,**kwargs):
            if kwargs['seed']=='42':raise RuntimeError('first anchor provider failure')
            return super().sample_raster(*args,**kwargs)
    provider=RaisesFirst()
    try:
        with pytest.raises(RuntimeError,match='provider failure'):run(store,provider,limit=1)
        revision=store.get_state('terrain_pool_revision')
        assert store.get_state(f'terrain_pool_cursor:{revision}:v1')=='42:0:0'
        assert store.terrain_work_counts(revision)['leased']==1
        second=run(store,provider,limit=1)
        assert second['pool_cursor']=='43:0:0'
        assert store.get_variant_task_status('43:0:0','v1')=='complete'
        assert store.get_variant_task_status('42:0:0','v1')!='complete'
        assert store.terrain_work_counts(revision).get('leased',0)==0
    finally:store.close()
