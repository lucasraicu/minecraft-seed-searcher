"""Real native synthetic-fixture parity; no natural seed campaign or rebuild."""
import copy
import sqlite3

import pytest

from seed_search.catalog import bridge
from seed_search.catalog.harvest import HarvestQueue
from seed_search.realm import native_batch
from seed_search.realm.config import blueprint_config
from seed_search.realm.store import RealmStore


def test_personal_native_fixture_results_off_on_identical_and_public_independent(tmp_path,monkeypatch):
    cfg=blueprint_config()
    prototype=native_batch.Prototype(None,cfg)
    original=prototype.sweep
    # Explicit synthetic personal failures: missing mansion requirement.
    def sweep(seeds,threads,**kwargs):
        return original(seeds,threads,fixtures=[(0,0,0)]*len(seeds),**kwargs)
    monkeypatch.setattr(prototype,'sweep',sweep)
    monkeypatch.setattr(native_batch,'Prototype',lambda directory,config:prototype)
    options=dict(native_threads=1,native_batch_size=2,top_k=0,
                 identity={'config':cfg,'count':4,'start_index':0})
    off=native_batch.run_native_scan(cfg,tmp_path/'off',4,**options)
    on=native_batch.run_native_scan(cfg,tmp_path/'on',4,catalog_root=tmp_path/'public',**options)
    assert off['completed_seeds']==on['completed_seeds']==4
    with RealmStore(tmp_path/'off',resume=True) as first,RealmStore(tmp_path/'on',resume=True) as second:
        a=list(map(native_batch.semantic_record,first.iter_results()))
        b=list(map(native_batch.semantic_record,second.iter_results()))
        assert a==b
        assert all(anchor['required_structures']['mansion']['predicted_count']==0
                   for row in a for anchor in row['anchors'])
    assert on['catalog_harvest']['state']=='registered'
    with HarvestQueue(tmp_path/'public') as queue:
        queue.expand()
        assert queue.status()['jobs']=={'pending':4}
        job=queue.claim('public-fixture')
        from tests.catalog.test_ingestion import make_complete_observation
        from seed_search.catalog.harvest_native import publish_observation
        from seed_search.catalog.segments import SegmentedCatalog
        observation=make_complete_observation(job['seed'],{k:v for k,v in job['identity'].items() if k!='seed'})
        observation['structures']['structure.village']=[[0,0]]
        with queue.publication(job):
            snapshot=publish_observation(tmp_path/'public',job,observation)
            queue.acknowledge(job,snapshot)
        with SegmentedCatalog(tmp_path/'public') as public:
            assert public.info(snapshot)['worlds']==1
    # Registration happened even though every synthetic personal seed failed.
    assert list((tmp_path/'on'/'catalog-handoff').glob('*.json'))


def test_partial_resume_reuses_same_campaign_and_preserves_personal_output(tmp_path,monkeypatch):
    cfg=blueprint_config();prototype=native_batch.Prototype(None,cfg);original=prototype.sweep
    monkeypatch.setattr(prototype,'sweep',lambda seeds,threads,**kw:original(seeds,threads,fixtures=[(0,0,0)]*len(seeds),**kw))
    monkeypatch.setattr(native_batch,'Prototype',lambda directory,config:prototype)
    options=dict(native_threads=1,native_batch_size=2,top_k=0,
        identity={'config':cfg,'count':4,'start_index':0},catalog_root=tmp_path/'public')
    first=native_batch.run_native_scan(cfg,tmp_path/'personal',4,stop_after=2,**options)
    assert first['completed_seeds']==2
    options['native_batch_size']=1
    second=native_batch.run_native_scan(cfg,tmp_path/'personal',4,resume=True,**options)
    assert second['completed_seeds']==4
    assert first['catalog_harvest']['campaign_id']==second['catalog_harvest']['campaign_id']
    assert len(list((tmp_path/'personal'/'catalog-handoff').glob('*.json')))==1
    with HarvestQueue(tmp_path/'public') as queue:
        queue.expand();assert len(queue.status()['campaigns'])==1
        assert queue.status()['jobs']=={'pending':4}


def test_queue_registration_failure_preserves_spool_and_personal_can_continue(tmp_path,monkeypatch):
    from seed_search.catalog import harvest
    def unavailable(self,descriptor):raise sqlite3.OperationalError('database is locked')
    monkeypatch.setattr(harvest.HarvestQueue,'register',unavailable)
    receipt=bridge.prepare_campaign({'sequence':'sequential'},tmp_path/'personal',0,2,
                                    {'code':'fixture'},tmp_path/'public')
    assert receipt['state']=='detached' and 'locked' in receipt['reason']
    assert len(list((tmp_path/'personal'/'catalog-handoff').glob('*.json')))==1


def test_python_executor_and_nested_roots_fail_before_handoff(tmp_path):
    from seed_search.realm.runner import run_scan
    with pytest.raises(ValueError,match='execution=native'):
        run_scan(blueprint_config(),tmp_path/'run',0,catalog_root=tmp_path/'public')
    with pytest.raises(ValueError,match='separate'):
        bridge.prepare_campaign({'sequence':'sequential'},tmp_path/'run',0,0,{},tmp_path/'run'/'catalog')
    assert not (tmp_path/'run'/'catalog-handoff').exists()
