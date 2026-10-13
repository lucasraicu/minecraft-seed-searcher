"""Full evidence, ownership and durable failure gates for the owned pipeline."""
import copy
from dataclasses import FrozenInstanceError
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time

import pytest

from test_blueprint_batch_prototype import prototype, FixtureBackend
from scripts.blueprint_batch_prototype import semantic_record,persist_pipeline
from seed_search.realm.blueprint import evaluate_seed
from seed_search.realm.config import blueprint_config
from seed_search.realm.native_encoding import fast_records,candidate_encoding
from seed_search.realm.store import RealmStore,canonical
from seed_search.seeds import seed_from_index


def durable_tables(store):
    tables=('seeds','candidates','inventory_work','discovery_tasks','variant_tasks')
    return {name:list(store.db.execute(f'SELECT * FROM {name} ORDER BY 1,2')) for name in tables}


@pytest.mark.parametrize('complete',[False,True])
def test_direct_replay_and_independent_all_paths(prototype,complete):
    fixtures=[(-1,-7,-1),(0,0,-1),(511,-513,-1)]+[(0,0,k) for k in [*range(12),*range(13,28)]]
    seeds=[seed_from_index(i) for i in range(len(fixtures))]
    with prototype.sweep(seeds,2 if prototype.identity['openmp'] else 1,complete=complete,fixtures=fixtures) as b:
        direct=b.records(17);replay=b.records(17,adapter='replay')
        assert list(map(semantic_record,direct))==list(map(semantic_record,replay))
    for i,(seed,fixture,row) in enumerate(zip(seeds,fixtures,direct)):
        oracle=evaluate_seed(i+17,seed,blueprint_config(),backend_factory=lambda _,f=fixture:FixtureBackend(f),short_circuit=not complete)
        assert semantic_record(row)==semantic_record(oracle)


def test_template_encoding_complete_bytes_and_owned_preparation(prototype,tmp_path):
    # Include different discovery multiplicities plus complete positives and late failures.
    for synthetic in (False,True):
        fixtures=[(x,-7,k) for x in (-2000,-1,0,1999) for k in (0,-1,8,26,27)] if synthetic else None
        seeds=[seed_from_index(i,120260001000) for i in range(len(fixtures) if synthetic else 300)]
        with prototype.sweep(seeds,1,fixtures=fixtures) as b:
            direct=b.records()
            with RealmStore(tmp_path/f'encoded-{synthetic}',{'config':prototype.cfg}) as s:
                s.configure_range(0,len(seeds),len(seeds));s.claim_range('test')
                fast=fast_records(b,0,s)
                for e,d in zip(fast,direct):
                    for a,c in zip(e['anchors'],d['anchors']):assert candidate_encoding(a,canonical)==canonical(c)
                prepared=s.prepare_range(0,len(seeds),fast)
                with pytest.raises(FrozenInstanceError):prepared.digest='changed'
                b.close()  # Every durable string is owned before freeing C.
                s.complete_prepared(prepared)
                actual=list(s.iter_results())
                assert list(map(semantic_record,actual))==list(map(semantic_record,direct))
                assert s.db.execute('PRAGMA synchronous').fetchone()[0]==2
                assert s.db.execute('PRAGMA journal_mode').fetchone()[0]=='wal'
                assert s.db.execute('SELECT count(*) FROM discovery_tasks').fetchone()[0]==len(seeds)*2
                assert s.db.execute('SELECT count(*) FROM variant_tasks').fetchone()[0]==sum(len(r['anchors']) for r in actual)
                assert not s.complete_prepared(prepared)
                # Compare all task tables and canonical rows through dictionary API.
                with RealmStore(tmp_path/f'dictionary-{synthetic}',{'config':prototype.cfg}) as t:
                    t.configure_range(0,len(seeds),len(seeds));t.claim_range('test')
                    t.complete_range(0,len(seeds),fast)
                    assert durable_tables(s)==durable_tables(t)


def simple(index):
    return {'index':index,'seed':str(index),'anchors':[{'id':f'{index}:1:2','seed':str(index),
        'stronghold':[1,2],'qualification':'PENDING','bounds':{'overworld':[0,0,4,4]},
        'inventory':{'version':'fixture-v1','sampling_policy':{'spacing':4},'tasks':['structures','biomes']}}],
        'counts':{'anchors':1}}


def test_prepared_inventory_identity_legacy_digest_and_validation(tmp_path):
    for version in (1,2):
        with RealmStore(tmp_path/str(version),{'config':{'terrain':{'variants':['v1']}}}) as s:
            if version==1:s.set_state('range_digest_version',1);s._digest_version=1;s._preparation_policy=(1,s._inventory_backend_digest,s.active_variants)
            s.configure_range(0,2,2);s.claim_range('a');r=[simple(0),simple(1)]
            p=s.prepare_range(0,2,r);s.complete_prepared(p,lease=('a',1))
            for uid,cid,kind,identity in s.db.execute('SELECT unit_id,candidate_id,kind,identity FROM inventory_work'):
                import hashlib
                assert uid==hashlib.sha256(canonical([cid,kind,json.loads(identity)]).encode()).hexdigest()
            assert s.db.execute('SELECT count(*) FROM inventory_work').fetchone()[0]==4
            assert not s.complete_range(0,2,list(reversed(r)))
            bad=copy.deepcopy(r);bad[0]['counts']['anchors']=2
            with pytest.raises(ValueError,match='differs'):s.complete_range(0,2,bad)
            for field,value in [('seed','00'),('index',True)]:
                bad=copy.deepcopy(r);bad[0][field]=value
                with pytest.raises(ValueError):s.prepare_range(0,2,bad)
            bad=copy.deepcopy(r);bad[0]['anchors'][0]['inventory']['tasks']=['wrong']
            with pytest.raises(ValueError,match='inventory'):s.prepare_range(0,2,bad)


def test_prepared_rollback_and_stale_lease(tmp_path):
    with RealmStore(tmp_path) as s:
        s.configure_range(0,2,2);s.claim_range('a');p=s.prepare_range(0,2,[simple(0),simple(1)])
        s.recover_assignments();s.claim_range('b')
        with pytest.raises(ValueError,match='Stale'):s.complete_prepared(p,lease=('a',1))
        s.db.execute("CREATE TRIGGER fail_task BEFORE INSERT ON variant_tasks BEGIN SELECT RAISE(ABORT,'injected'); END")
        with pytest.raises(sqlite3.IntegrityError):s.complete_prepared(p,lease=('b',2))
        assert not list(s.iter_results()) and s.status()['completed_seeds']==0
        assert not s.db.execute('SELECT * FROM inventory_work').fetchall()
        s.db.execute('DROP TRIGGER fail_task');s.complete_prepared(p,lease=('b',2))


@pytest.mark.parametrize('when',['before','transaction','after'])
def test_process_crash_coverage_atomicity_and_retry(tmp_path,when):
    script='''
import os,sys
from seed_search.realm.store import RealmStore
r=[{'index':i,'seed':str(i),'anchors':[],'counts':{'inputs':1}} for i in range(2)]
s=RealmStore(sys.argv[1]);s.configure_range(0,2,2);s.claim_range('crashing')
p=s.prepare_range(0,2,r)
if sys.argv[2]=='before':os._exit(17)
if sys.argv[2]=='transaction':
 original=s._set
 def fail(key,value):
  if key=='completed_seeds':os._exit(17)
  original(key,value)
 s._set=fail
s.complete_prepared(p)
os._exit(17)
'''
    proc=subprocess.run([sys.executable,'-c',script,str(tmp_path),when])
    assert proc.returncode==17
    r=[{'index':i,'seed':str(i),'anchors':[],'counts':{'inputs':1}} for i in range(2)]
    with RealmStore(tmp_path,resume=True) as s:
        assert s.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        committed=when=='after'
        assert s.status()['completed_seeds']==(2 if committed else 0)
        assert len(list(s.iter_results()))==(2 if committed else 0)
        assert s.recover_assignments()==(0 if committed else 1)
        if not committed:s.claim_range('recovered')
        assert s.complete_range(0,2,r)==(not committed)
        assert s.status()['counts']=={'inputs':2}


def test_native_cap_rejects_without_partial_output(prototype):
    previous=prototype.policy.max_buffer_bytes
    try:
        prototype.policy.max_buffer_bytes=4096
        with pytest.raises(RuntimeError):prototype.sweep([0,-1],1)
    finally:prototype.policy.max_buffer_bytes=previous


def test_pipeline_three_stages_and_exact_partial_resume(prototype,tmp_path,monkeypatch):
    events=[];original=prototype.sweep;prepare_original=RealmStore.prepare_range;write_original=RealmStore.complete_prepared
    def sweep(*args,**kwargs):
        events.append(('native_start',time.perf_counter(),threading.get_ident()))
        b=original(*args,**kwargs);events.append(('native_end',time.perf_counter(),threading.get_ident()));return b
    def prepare(self,*args,**kwargs):
        events.append(('prepare_start',time.perf_counter(),threading.get_ident()));time.sleep(.01)
        p=prepare_original(self,*args,**kwargs);events.append(('prepare_end',time.perf_counter(),threading.get_ident()));return p
    def write(self,*args,**kwargs):
        events.append(('write_start',time.perf_counter(),threading.get_ident()));time.sleep(.01)
        p=write_original(self,*args,**kwargs);events.append(('write_end',time.perf_counter(),threading.get_ident()));return p
    monkeypatch.setattr(prototype,'sweep',sweep);monkeypatch.setattr(RealmStore,'prepare_range',prepare);monkeypatch.setattr(RealmStore,'complete_prepared',write)
    first=persist_pipeline(prototype,tmp_path,65,threads=1,batch_size=16,stop_after=33)
    assert first['newly_committed']==33 and first['max_outstanding_batches']<=3
    resumed=persist_pipeline(prototype,tmp_path,65,threads=1,batch_size=8,resume=True)
    assert resumed['newly_committed']==32
    assert len({e[2] for e in events})==3
    starts=[e[1] for e in events if e[0]=='write_start'];ends=[e[1] for e in events if e[0]=='write_end']
    assert any(a<e[1]<b for a,b in zip(starts,ends) for e in events if e[0]=='prepare_start')
    with RealmStore(tmp_path,resume=True) as s:
        rows=list(s.iter_results());assert [r['index'] for r in rows]==list(range(65))
        for r in rows:assert semantic_record(r)==semantic_record(evaluate_seed(r['index'],seed_from_index(r['index']),blueprint_config()))


def test_native_large_finite_range_requires_scale_and_resumes_without_large_run(prototype,tmp_path,monkeypatch):
    from seed_search.realm import native_batch
    cfg=copy.deepcopy(prototype.cfg)
    monkeypatch.setattr(native_batch,'Prototype',lambda directory,config:prototype)
    kwargs={'native_threads':1,'native_batch_size':2,'stop_after':3}
    with pytest.raises(ValueError,match='explicit prediction scale'):
        native_batch.run_native_scan(cfg,tmp_path,100001,**kwargs)
    with pytest.raises(ValueError,match='persisted compatibility'):
        native_batch.run_native_scan(cfg,tmp_path,100001,allow_prediction_scale=True,**kwargs)
    tmp_path.mkdir(exist_ok=True)
    (tmp_path/'compatibility.json').write_text(json.dumps({
        'target_version':'26.52','bds_version':'1.26.52.3',
        'prediction_model':'MC_26_50','features':{}}))
    first=native_batch.run_native_scan(cfg,tmp_path,100001,allow_prediction_scale=True,**kwargs)
    assert first['completed_seeds']==3
    second=native_batch.run_native_scan(cfg,tmp_path,100001,resume=True,allow_prediction_scale=True,**kwargs)
    assert second['completed_seeds']==6 and second['execution']['newly_committed']==3
    with RealmStore(tmp_path,resume=True) as store:
        assert store.get_state('range')==[0,100001]
        assert [row['index'] for row in store.iter_results()]==list(range(6))
        assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not store.db.execute("SELECT * FROM ranges WHERE status='in_progress'").fetchall()


def test_internal_large_pipeline_does_not_bypass_production_gate(prototype,tmp_path):
    with pytest.raises(ValueError,match='explicit production prediction scale'):
        persist_pipeline(prototype,tmp_path,100001,allow_prediction_scale=True,stop_after=0)
    with pytest.raises(ValueError,match='full64 range'):
        persist_pipeline(prototype,tmp_path,2,start_index=2**64-1,stop_after=0)


@pytest.mark.parametrize('failure',['prepare','native','cancel','bytes'])
@pytest.mark.parametrize('prepare_on_writer',[False,True])
def test_pipeline_failures_release_owned_buffers_and_recover(prototype,tmp_path,monkeypatch,failure,prepare_on_writer):
    import seed_search.realm.native_encoding as encoding
    owned=[];original=prototype.sweep;fast=encoding.fast_records
    def sweep(*args,**kwargs):
        if failure=='native' and owned:raise RuntimeError('injected native failure')
        b=original(*args,**kwargs);owned.append(b);return b
    def records(*args,**kwargs):
        if failure=='cancel':raise KeyboardInterrupt
        if failure=='prepare':raise RuntimeError('injected record failure')
        return fast(*args,**kwargs)
    monkeypatch.setattr(prototype,'sweep',sweep);monkeypatch.setattr(encoding,'fast_records',records)
    kwargs={'max_prepared_bytes':1} if failure=='bytes' else {}
    kwargs['prepare_on_writer']=prepare_on_writer
    if failure=='cancel':
        out=persist_pipeline(prototype,tmp_path,64,threads=1,batch_size=16,**kwargs)
        assert out['interrupted']
    else:
        with pytest.raises(RuntimeError):persist_pipeline(prototype,tmp_path,64,threads=1,batch_size=16,**kwargs)
    assert owned and all(b.pointer is None for b in owned)
    with RealmStore(tmp_path,resume=True) as s:
        assert not s.db.execute("SELECT * FROM ranges WHERE status='in_progress'").fetchall()
        assert len(list(s.iter_results()))==s.status()['completed_seeds']
    monkeypatch.setattr(prototype,'sweep',original);monkeypatch.setattr(encoding,'fast_records',fast)
    out=persist_pipeline(prototype,tmp_path,64,threads=1,batch_size=8,resume=True)
    assert out['status']['completed_seeds']==64
