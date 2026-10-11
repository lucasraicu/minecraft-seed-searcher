"""Resume provenance checks without native generation or provider construction."""
from types import SimpleNamespace
import importlib.util
import pytest
from seed_search.realm.store import RealmStore
from seed_search.realm.terrain import run_terrain, terrain_algorithm_identity

CFG={'terrain':{'center_spacing':128,'maximum_refinements_per_anchor':1,'resolutions':[128,64]}}
DECLARED={'provider':'fixture','build':'v1','extractor':{'water':'explicit'}}


def checkpoint(tmp_path):
    store=RealmStore(tmp_path,identity={'config':CFG})
    store.configure_range(0,1);store.claim_range('fixture')
    candidate=dict(id='42:0:0',seed='42',stronghold=[0,0],bounds={'overworld':[-128,-128,128,128]},qualification='PREDICTED',baseline_score=60)
    store.complete_range(0,1,[dict(index=0,seed='42',anchors=[candidate])])
    return store


def forbidden(*args,**kwargs):
    raise AssertionError('Identity checks/completed task resume must not construct a provider')


def complete(store):
    revision=store.get_state('terrain_pool_revision')
    for variant in ('v1','v2'):
        if revision:
            payload={'stage':'height','coarse_center':[0,0],'resolution':1,'halo_level':0,
                     'raster_bounds':[0,0,1,1],'lattice':{'x0':0,'z0':0,'step':1,'shape':[1,1]}}
            uid=store.ensure_terrain_work(revision,'42:0:0',variant,payload)
            unit=store.claim_terrain_work(uid,'identity-fixture')
            observation=None if store.get_observation(unit['sampling_key']) else {
                'id':unit['sampling_key'],'bounds':payload['raster_bounds'],'resolution':1,
                'lattice':payload['lattice'],'channels':{'fixture':'no generation'}}
            store.complete_terrain_work(uid,result={'fixture':'completed'},observation=observation)
        store.set_variant_task_status('42:0:0',variant,'complete')


def test_unchanged_custom_build_resumes_across_distinct_factories_without_calls(tmp_path):
    store=checkpoint(tmp_path)
    try:
        run_terrain(store,CFG,limit=0,provider_factory=lambda seed: forbidden(),provider_identity=DECLARED)
        complete(store)
        resumed=run_terrain(store,CFG,provider_factory=forbidden,provider_identity=dict(DECLARED))
        assert resumed['resumed_tasks']==2
        assert resumed['candidates']==resumed['results']==0
    finally:store.close()


def test_changed_custom_identity_rejects_before_completed_skip_preserving_records(tmp_path):
    store=checkpoint(tmp_path)
    try:
        run_terrain(store,CFG,limit=0,provider_factory=forbidden,provider_identity=DECLARED)
        store.upsert_variant('42:0:0','v1',[0,0],{'score':5,'evidence':'PREDICTED'})
        complete(store);before=store.get_variant('42:0:0','v1',[0,0])
        old=store.get_state('terrain_algorithm_identity')
        with pytest.raises(ValueError,match='identity changed'):
            run_terrain(store,CFG,provider_factory=forbidden,provider_identity={**DECLARED,'build':'v2'})
        assert store.get_state('terrain_algorithm_identity')==old
        assert store.get_variant('42:0:0','v1',[0,0])==before
    finally:store.close()


@pytest.mark.parametrize('identity',[None,lambda:DECLARED,{'build':object()},{'build':float('nan')},{}])
def test_undeclared_or_nonstatic_custom_factory_rejected_before_sampling(tmp_path,identity):
    store=checkpoint(tmp_path)
    try:
        complete(store)
        with pytest.raises(ValueError,match='static JSON'):
            run_terrain(store,CFG,provider_factory=forbidden,provider_identity=identity)
        assert store.get_state('terrain_algorithm_identity') is None
    finally:store.close()


def test_static_factory_attribute_is_supported_and_pinned_by_value(tmp_path):
    store=checkpoint(tmp_path)
    def factory(seed):return forbidden()
    factory.terrain_identity=dict(DECLARED)
    try:
        run_terrain(store,CFG,limit=0,provider_factory=factory)
        complete(store)
        assert run_terrain(store,CFG,provider_factory=factory)['resumed_tasks']==2
        factory.terrain_identity['build']='changed'
        with pytest.raises(ValueError,match='identity changed'):run_terrain(store,CFG,provider_factory=factory)
    finally:store.close()


def test_native_binary_bytes_checked_before_completed_skip_without_load_or_build(tmp_path,monkeypatch):
    binary=tmp_path/'_native.abi3.so';binary.write_bytes(b'build-one-not-a-real-library')
    monkeypatch.setattr(importlib.util,'find_spec',lambda name:SimpleNamespace(origin=str(binary)))
    import seed_search.backend as backend
    monkeypatch.setattr(backend,'Backend',forbidden)
    store=checkpoint(tmp_path/'run')
    try:
        run_terrain(store,CFG,limit=0);complete(store)
        pinned=store.get_state('terrain_algorithm_identity')
        assert 'native_extension' in pinned['sampling_provider']['sha256']
        assert run_terrain(store,CFG)['resumed_tasks']==2
        binary.write_bytes(b'build-two-not-a-real-library')
        with pytest.raises(ValueError,match='identity changed'):run_terrain(store,CFG)
        assert store.get_state('terrain_algorithm_identity')==pinned
    finally:store.close()


def test_backend_wrapper_hash_participates_in_identity(monkeypatch):
    from pathlib import Path
    original=Path.read_bytes
    before=terrain_algorithm_identity(CFG)
    def changed(path):
        content=original(path)
        return content+b'\n# altered wrapper' if path.name=='backend.py' else content
    monkeypatch.setattr(Path,'read_bytes',changed)
    after=terrain_algorithm_identity(CFG)
    assert before['sampling_provider']['sha256']['backend_wrapper']!=after['sampling_provider']['sha256']['backend_wrapper']
    assert before['sha256']!=after['sha256']


def test_historical_tasks_without_pin_not_adopted_or_overwritten(tmp_path):
    store=checkpoint(tmp_path)
    try:
        store.upsert_variant('42:0:0','v1',[0,0],{'score':7})
        before=store.get_variant('42:0:0','v1',[0,0])
        with pytest.raises(ValueError,match='lack a pinned'):
            run_terrain(store,CFG,provider_factory=forbidden,provider_identity=DECLARED)
        assert store.get_state('terrain_algorithm_identity') is None
        assert store.get_variant('42:0:0','v1',[0,0])==before
    finally:store.close()


def test_missing_native_extension_cannot_resume_completed_tasks(tmp_path,monkeypatch):
    store=checkpoint(tmp_path)
    try:
        run_terrain(store,CFG,limit=0);complete(store)
        monkeypatch.setattr(importlib.util,'find_spec',lambda name:None)
        with pytest.raises(ValueError,match='extension unavailable'):run_terrain(store,CFG)
    finally:store.close()


def test_static_cache_identity_alias_and_settings_are_pinned(tmp_path):
    store=checkpoint(tmp_path)
    def factory(seed):return forbidden()
    factory.cache_identity={'build':'static-test-v1'}
    try:
        run_terrain(store,CFG,limit=0,provider_factory=factory);complete(store)
        assert run_terrain(store,CFG,provider_factory=factory)['resumed_tasks']==2
        altered={**CFG,'world_settings':{'type':'changed'}}
        with pytest.raises(ValueError,match='identity changed'):run_terrain(store,altered,provider_factory=factory)
    finally:store.close()
