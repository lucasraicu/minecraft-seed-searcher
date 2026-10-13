"""The isolated C evaluator must match full existing evidence, including positives."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from scripts.build_blueprint_batch import ROOT, build
from scripts.blueprint_batch_prototype import NAMES, Prototype, persist_scan, semantic_record
from seed_search.backend import biome_catalog
from seed_search.realm.blueprint import evaluate_seed
from seed_search.realm.config import blueprint_config
from seed_search.realm.store import RealmStore
from seed_search.seeds import seed_from_index

IDS={row['name']:row['id'] for row in biome_catalog()}


@pytest.fixture(scope='module')
def prototype(tmp_path_factory):
    output=tmp_path_factory.mktemp('native-blueprint')
    production=ROOT/'src/seed_search/_native.abi3.so'
    before=hashlib.sha256(production.read_bytes()).hexdigest()
    prefix=ROOT/'runs/master-implementation-2026-10-10/openmp/install'
    identity=build(output,prefix if (prefix/'include/omp.h').is_file() else None)
    assert not identity['production_extension_replaced']
    assert hashlib.sha256(production.read_bytes()).hexdigest()==before
    yield Prototype(output,blueprint_config())
    assert hashlib.sha256(production.read_bytes()).hexdigest()==before


class FixtureBackend:
    """Independent Python provider for explicit synthetic positive/negative inputs."""
    surface=['plains','desert','forest','taiga','jungle','swamp','snowy_plains','dark_forest','jagged_peaks','stony_shore']
    caves=['lush_caves','dripstone_caves','deep_dark']
    def __init__(self,fixture):self.x,self.z,self.missing=fixture;self.native_work={}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def structure_pair(self,name,bounds):
        if name=='stronghold':return [(self.x,self.z)],[(self.x,self.z)]
        slot=NAMES.index(name);goal=blueprint_config()['structures']['minimum_counts'].get(name,1)
        n=goal-1 if self.missing==slot else goal+2
        points=[(bounds[0]+800+i*16,bounds[1]+800) for i in range(n)]
        return points,points
    def structure_count(self,name,bounds,minimum):return self.structure_pair(name,bounds)[1][:minimum]
    def nether_structure_pairs(self,bounds):return {n:self.structure_pair(n,bounds) for n in ('fortress','bastion')}
    def biome_points(self,points):
        values=[]
        for x,y,z in points:
            if x%64 or z%64:
                name='pale_garden' if self.missing==27 or x==self.x+32 else 'dark_forest'
            else:
                cave=y in (-48,0)
                if self.missing==26:name='dark_forest' if cave else 'lush_caves'
                else:
                    choices=self.caves if cave else self.surface;k=(int(x)//64+int(z)//64)%len(choices)
                    family=k+10 if cave else k
                    if self.missing==family+13:values.append(-1);continue
                    name=choices[k]
            values.append(IDS[name])
        return np.array(values,dtype=np.int32)


@pytest.mark.parametrize('complete',[False,True])
def test_real_extreme_sibling_seeds_and_full_evidence_match(prototype,complete):
    seeds=[0,-1,-2**63,2**63-1,12345,2**32+12345,-2**32+12345,seed_from_index(84,120260001000)]
    with prototype.sweep(seeds,complete=complete) as batch:actual=batch.records()
    for i,(seed,row) in enumerate(zip(seeds,actual)):
        expected=evaluate_seed(i,seed,blueprint_config(),short_circuit=not complete)
        assert semantic_record(row)==semantic_record(expected)
    if complete:
        # Real inventories exercise bonus caps above the fixture's exact caps.
        assert any(a['required_structures']['trial_chamber']['predicted_count']>4 for row in actual for a in row['anchors'])


@pytest.mark.parametrize('complete',[False,True])
def test_synthetic_all_positive_every_floor_and_biome_negative(prototype,complete):
    fixtures=[(0,0,-1),(-1,-7,-1),(-513,511,-1),(-2000,-2000,-1),(1999,1999,-1)]
    fixtures += [(0,0,missing) for missing in [*range(12),*range(13,28)]]
    seeds=[seed_from_index(i) for i in range(len(fixtures))]
    threads=2 if prototype.identity['openmp'] else 1
    with prototype.sweep(seeds,threads,complete=complete,fixtures=fixtures) as batch:
        actual=batch.records();summary=batch.summary()
    for i,(seed,fixture,row) in enumerate(zip(seeds,fixtures,actual)):
        expected=evaluate_seed(i,seed,blueprint_config(),backend_factory=lambda _,f=fixture:FixtureBackend(f),short_circuit=not complete)
        assert semantic_record(row)==semantic_record(expected),(fixture,'semantic mismatch')
        assert row['prototype']['synthetic']
        if i<5:assert row['anchors'][0]['qualification']=='PREDICTED'
    assert all(row['anchors'][0]['qualification']=='PENDING' for row in actual[5:])
    # The first Mansion start is Pale Garden: a later Dark Forest must survive.
    mansion=actual[0]['anchors'][0]['required_structures']['mansion']
    assert mansion['anchor_biome_witnesses'][0]['biome']=='pale_garden'
    assert len(mansion['predicted_viable'])==2
    assert actual[1]['anchors'][0]['bounds']['final_nether']==[-448.125,-448.875,447.875,447.125]
    assert summary[0]['anchors'][0]['score']==actual[0]['anchors'][0]['baseline_score']


def test_parallel_state_isolation_repeated_uint64_max_and_record_order(prototype):
    if not prototype.identity['openmp']:pytest.skip('No local OpenMP runtime')
    seeds=[seed_from_index(i,120260001000) for i in range(129)]+[-1]*17
    with prototype.sweep(seeds,1) as batch:serial=batch.records()
    for threads in (2,4):
        with prototype.sweep(seeds,threads) as batch:parallel=batch.records()
        assert list(map(semantic_record,parallel))==list(map(semantic_record,serial))


def test_policy_errors_and_buffer_lifetime(prototype):
    for seeds,threads in [([],1),([True],1),([2**63],1),([0],True),([0],37)]:
        with pytest.raises(ValueError):prototype.sweep(seeds,threads)
    with pytest.raises(ValueError):prototype.sweep([0],fixtures=[(-2**31,0,-1)])
    with pytest.raises(ValueError):prototype.sweep([0],fixtures=[])
    ffi,lib=prototype.ffi,prototype.lib
    invalid=ffi.new('NBPolicy *');ffi.memmove(invalid,prototype.policy,ffi.sizeof('NBPolicy'))
    invalid.goals[5]=4
    assert lib.nb_sweep(ffi.new('uint64_t[]',[0]),1,invalid,1)==ffi.NULL
    batch=prototype.sweep([0]);batch.close();batch.close()
    with pytest.raises(ValueError):batch.records()
    with pytest.raises(ValueError):batch.summary()


def test_complete_realm_checkpoint_and_no_work_resume(prototype,tmp_path):
    run=tmp_path/'persisted';result=persist_scan(prototype,run,33,run_key=120260001000,threads=1,batch_size=16)
    assert result['status']['completed_seeds']==33 and result['batches']==3
    with RealmStore(run,resume=True) as store:
        rows=list(store.iter_results())
        assert store.active_variants==('v1',)
        assert store.db.execute('SELECT COUNT(*) FROM seeds').fetchone()[0]==33
        assert store.db.execute("SELECT COUNT(*) FROM ranges WHERE status='complete'").fetchone()[0]==3
    for i,row in enumerate(rows):
        expected=evaluate_seed(i,seed_from_index(i,120260001000),blueprint_config())
        assert semantic_record(row)==semantic_record(expected)
    resumed=persist_scan(prototype,run,33,run_key=120260001000,threads=1,batch_size=16,resume=True)
    assert resumed['batches']==0 and resumed['status']['completed_seeds']==33
    with pytest.raises(ValueError,match='Incompatible resume'):
        persist_scan(prototype,run,33,run_key=120260001001,threads=1,resume=True)


def test_portable_serial_private_build_matches_parallel_build(prototype,tmp_path):
    identity=build(tmp_path/'serial')
    assert not identity['openmp']
    # A fresh interpreter selects exactly this serial artifact, avoiding a
    # preloaded extension with the same Python module name from another build.
    script='''
import json,sys
from scripts.blueprint_batch_prototype import Prototype,semantic_record
from seed_search.realm.config import blueprint_config
from seed_search.realm.blueprint import evaluate_seed
p=Prototype(sys.argv[1],blueprint_config())
seeds=[0,-1,-2**63,2**63-1,12345]
with p.sweep(seeds) as b:
 assert b.pointer.effective_threads==1
 rows=b.records()
for i,(seed,row) in enumerate(zip(seeds,rows)):
 assert semantic_record(row)==semantic_record(evaluate_seed(i,seed,blueprint_config()))
try:p.sweep([0],2)
except ValueError:pass
else:raise AssertionError('Serial artifact accepted parallel request')
print(json.dumps({'real_records':len(rows),'mismatches':0,'effective_threads':1}))
'''
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path/'serial')],cwd=ROOT,check=True,capture_output=True,text=True)
    assert json.loads(result.stdout)=={'real_records':5,'mismatches':0,'effective_threads':1}
