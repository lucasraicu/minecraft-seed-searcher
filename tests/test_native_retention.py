"""Compact decisions, retained evidence, atomic coverage, exports and dispatch."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import sqlite3
import pytest
import numpy as np

from test_blueprint_batch_prototype import prototype,FixtureBackend,NAMES,IDS
from seed_search.realm.native_batch import persist_pipeline
from seed_search.realm.blueprint import evaluate_seed
from seed_search.realm.config import blueprint_config
from seed_search.realm.runner import run_scan
from seed_search.realm.store import RealmStore,canonical
from seed_search.realm.native_encoding import fast_records

class MaskedBackend(FixtureBackend):
    def __init__(self,fixture,mask):super().__init__(fixture);self.mask=mask
    def structure_pair(self,name,bounds):
        before=self.missing
        if name!='stronghold' and self.mask&(1<<NAMES.index(name)):self.missing=NAMES.index(name)
        try:return super().structure_pair(name,bounds)
        finally:self.missing=before
    def biome_points(self,points):
        values=[]
        for x,y,z in points:
            if x%64 or z%64:
                name='pale_garden' if self.mask&(1<<27) or x==self.x+32 else 'dark_forest'
            else:
                cave=y in (-48,0)
                choices=self.caves if cave else self.surface;k=(int(x)//64+int(z)//64)%len(choices)
                family=k+10 if cave else k
                if self.mask&(1<<(family+13)):values.append(-1);continue
                name=choices[k]
            values.append(IDS[name])
        return np.array(values,dtype=np.int32)

@pytest.mark.parametrize('limit',[0,1,2,3])
def test_retention_matches_independent_full_decisions_and_inventory(prototype,limit,tmp_path):
    masks=[0,1,1|(1<<13),1|(1<<13)|(1<<14), (1<<10)|(1<<11), (1<<18)|(1<<21)]
    seeds=[-1,-2**63,0,1,2**32+12345,2**63-1];fixtures=[(-1,-7,-1)]*len(seeds)
    expected=[]
    for i,(seed,mask) in enumerate(zip(seeds,masks)):
        oracle=evaluate_seed(i+17,seed,prototype.cfg,backend_factory=lambda _,m=mask:MaskedBackend(fixtures[i],m),short_circuit=False)
        if len(oracle['anchors'][0]['pending_reasons'])<=limit:expected.append(oracle)
    with prototype.sweep(seeds,2 if prototype.identity['openmp'] else 1,fixtures=fixtures,fixture_masks=masks,retention='survivors',max_misses=limit) as b:
        actual=b.retained_records(17);receipt=b.retention_receipt()
        assert all(r['prototype']['synthetic'] for r in actual)
        assert [r['seed'] for r in actual]==[r['seed'] for r in expected]
        for a,e in zip(actual,expected):
            a,e=a['anchors'][0],e['anchors'][0]
            for key in ('pending_reasons','required_structures','required_nether_structures','ranking','baseline_score_observed','qualification','bounds'):
                assert a[key]==e[key]
            assert a['biomes']['witnesses']==e['biomes']['witnesses']
            assert a['biomes']['missing_families']==e['biomes']['missing_families']
        with RealmStore(tmp_path,{'config':prototype.cfg,'retention':{'mode':'survivors','max_misses':limit}}) as s:
            s.configure_range(17,23,6);s.claim_range('test');p=s.prepare_retained_range(17,23,actual,receipt)
            b.close();s.complete_prepared(p,lease=('test',1));assert not s.complete_prepared(p)
            assert s.status()['completed_seeds']==6
            assert s.status()['saved_seed_rows']==len(actual)
            assert s.db.execute('SELECT count(*) FROM retention_receipts').fetchone()[0]==1
            assert s.db.execute('SELECT count(*) FROM variant_tasks').fetchone()[0]==len(actual)
            assert s.db.execute('SELECT count(*) FROM discovery_tasks').fetchone()[0]==2*len(actual)
            assert s.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            changed={**receipt,'input_decisions_sha256':'0'*64}
            with pytest.raises(ValueError,match='differs'):s.complete_prepared(s.prepare_retained_range(17,23,actual,changed))
            with pytest.raises(ValueError):s.prepare_range(17,23,actual)

@pytest.mark.parametrize('when',['before','transaction','after'])
def test_compact_crash_atomic_coverage(tmp_path,when):
    code='''
import os,sys
from seed_search.realm.store import RealmStore
s=RealmStore(sys.argv[1],{'retention':{'mode':'survivors','max_misses':2}})
s.configure_range(0,2,2);s.claim_range('crash')
r={'version':'native-retention-receipt-v1','inputs':2,'retained_inputs':0,'retained_anchors':0,'discovered_anchors':3,'input_decisions_sha256':'a'*64}
p=s.prepare_retained_range(0,2,[],r)
if sys.argv[2]=='before':os._exit(17)
if sys.argv[2]=='transaction':
 orig=s._set
 def fail(key,value):
  if key=='completed_seeds':os._exit(17)
  orig(key,value)
 s._set=fail
s.complete_prepared(p);os._exit(17)
'''
    assert subprocess.run([sys.executable,'-c',code,str(tmp_path),when]).returncode==17
    with RealmStore(tmp_path,resume=True) as s:
        done=when=='after'
        assert s.status()['completed_seeds']==(2 if done else 0)
        assert s.db.execute('SELECT count(*) FROM retention_receipts').fetchone()[0]==int(done)
        assert s.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        s.recover_assignments();assert s.claim_range('resume')==(None if done else (0,2))
        r={'version':'native-retention-receipt-v1','inputs':2,'retained_inputs':0,'retained_anchors':0,'discovered_anchors':3,'input_decisions_sha256':'a'*64}
        assert s.complete_prepared(s.prepare_retained_range(0,2,[],r))==(not done)


def test_public_native_resume_export_and_policy_guard(prototype,tmp_path):
    cfg=blueprint_config()
    run=tmp_path/'run'
    a=run_scan(cfg,run,65,execution='native',native_build=prototype.directory,native_threads=1,native_batch_size=16,retention='survivors',max_misses=2,stop_after=33)
    assert a['completed_seeds']==33
    b=run_scan(cfg,run,65,resume=True,execution='native',native_build=prototype.directory,native_threads=1,native_batch_size=32,retention='survivors',max_misses=2)
    assert b['completed_seeds']==65 and b['execution']['newly_committed']==32
    assert b['execution']['batch_latency_p50_seconds']>0
    assert b['execution']['batch_latency_p95_seconds']>=b['execution']['batch_latency_p50_seconds']
    with pytest.raises(ValueError,match='Incompatible resume'):
        run_scan(cfg,run,65,resume=True,execution='native',native_build=prototype.directory,native_threads=1,retention='survivors',max_misses=1)
    with pytest.raises(ValueError):run_scan(cfg,tmp_path/'python',1,retention='survivors',max_misses=2)
    with pytest.raises(ValueError):run_scan(cfg,tmp_path/'bad',True,execution='native',native_build=prototype.directory)
    with pytest.raises(ValueError):run_scan(cfg,tmp_path/'workers',1,workers=1,execution='native',native_build=prototype.directory)
    with pytest.raises(ValueError):run_scan(cfg,tmp_path/'scale',100001,execution='native',native_build=prototype.directory)
    with RealmStore(run,resume=True) as s:
        from seed_search.realm.reports import export
        result=export(s)
        assert (run/'results/baseline.jsonl').exists() or result
        assert s.status()['counts']['scanned_inputs']==65


def test_complete_encoder_and_marker_literals(prototype,tmp_path):
    cfg=copy.deepcopy(prototype.cfg)
    from seed_search.realm.native_batch import Prototype,semantic_record
    p=Prototype(prototype.directory,cfg)
    for complete in (False,True):
        with p.sweep([0],complete=complete,fixtures=[(0,0,0)]) as b,RealmStore(tmp_path/str(complete)) as s:
            actual=fast_records(b,0,s);direct=b.records()
            from seed_search.realm.native_encoding import PendingEncoder,candidate_encoding
            sample=copy.deepcopy(direct[0]['anchors'][0])
            sample['required_structures']['stronghold']['negative_meaning']='~seed~ ~counts~ 100% café'
            if not complete:
                encoder=PendingEncoder(sample,canonical)
                encoded=encoder.encode(b.pointer.results[0].anchors[0],0,'0')
                assert candidate_encoding(encoded,canonical)==canonical(sample)
            s.configure_range(0,1,1);s.claim_range('x');s.complete_range(0,1,actual)
            assert semantic_record(next(s.iter_results()))==semantic_record(direct[0])


def test_smaller_batches_split_recovered_native_leases(prototype,tmp_path):
    from seed_search.realm.native_batch import persist_pipeline
    run=tmp_path/'retry';cfg=prototype.cfg
    ident={'config':cfg,'prototype':prototype.identity,'count':65,'start_index':0,
           'evidence_schema':'realm-full-records-v1','adapter':'owned-native-pipeline-v1',
           'retention':{'mode':'full','max_misses':0}}
    with RealmStore(run,ident) as s:
        s.configure_range(0,65,64);assert s.claim_range('dead')==(0,64)
    persist_pipeline(prototype,run,65,resume=True,threads=1,batch_size=16)
    with RealmStore(run,resume=True) as s:
        assert s.status()['completed_seeds']==65
        assert all(int(end)-int(start)<=16 for start,end in s.db.execute('SELECT start,end FROM ranges'))


def test_prepared_near_miss_policy_cannot_cross_checkpoints(tmp_path):
    receipt={'version':'native-retention-receipt-v1','inputs':2,'retained_inputs':0,'retained_anchors':0,'discovered_anchors':3,'input_decisions_sha256':'a'*64}
    with RealmStore(tmp_path/'a',{'retention':{'mode':'survivors','max_misses':2}}) as a, RealmStore(tmp_path/'b',{'retention':{'mode':'survivors','max_misses':1}}) as b:
        p=a.prepare_retained_range(0,2,[],receipt)
        b.configure_range(0,2,2);b.claim_range('test')
        with pytest.raises(ValueError,match='allowance'):b.complete_prepared(p)
        assert b.status()['completed_seeds']==0


def test_real_multi_anchor_selection_preserves_owned_evidence(prototype):
    from seed_search.seeds import seed_from_index
    seeds=[seed_from_index(i,120260001000) for i in range(64)]
    threads=2 if prototype.identity['openmp'] else 1
    with prototype.sweep(seeds,threads,complete=True) as full:
        reference=full.records()
    # A relaxed diagnostic allowance selects a genuine mix of retained/dropped
    # anchors within a seed, including moving a later anchor into a freed slot.
    limits=[len(a['pending_reasons']) for r in reference for j,a in enumerate(r['anchors'])
            if j and any(len(p['pending_reasons'])>len(a['pending_reasons']) for p in r['anchors'][:j])]
    assert limits, 'Pinned natural controls must exercise within-seed compaction'
    limit=limits[0]
    expected=[(r,[a for a in r['anchors'] if len(a['pending_reasons'])<=limit]) for r in reference]
    expected=[(r,a) for r,a in expected if a]
    with prototype.sweep(seeds,threads,retention='survivors',max_misses=limit) as b:
        actual=b.retained_records();receipt=b.retention_receipt()
        assert receipt['retained_anchors']==sum(len(a) for r,a in expected)
        assert receipt['discovered_anchors']==sum(len(r['anchors']) for r in reference)
    assert [r['seed'] for r in actual]==[r['seed'] for r,a in expected]
    for actual_row,(reference_row,anchors) in zip(actual,expected):
        assert [a['stronghold'] for a in actual_row['anchors']]==[a['stronghold'] for a in anchors]
        for a,e in zip(actual_row['anchors'],anchors):
            for key in ('required_structures','required_nether_structures','ranking','pending_reasons','qualification','bounds'):
                assert a[key]==e[key]
            assert a['biomes']['witnesses']==e['biomes']['witnesses']
            assert a['biomes']['missing_families']==e['biomes']['missing_families']
