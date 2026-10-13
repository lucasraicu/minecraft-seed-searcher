import copy
import pytest

from scripts.build_blueprint_batch import ROOT,build
from seed_search.realm.config import outpost_blueprint_config,river_blueprint_config,validate_config
from seed_search.realm.native_batch import Prototype,semantic_record
from seed_search.realm.blueprint import evaluate_seed
from seed_search.realm.store import RealmStore
from test_river_highway import RiverFixture


class OutpostFixture(RiverFixture):
    def structure_pair(self,name,bounds):
        raw,viable=super().structure_pair(name,bounds)
        if name=='outpost':
            point=(bounds[0]+800+len(raw)*16,bounds[1]+800)
            raw=raw+[point];viable=viable+[point]
        return raw,viable


@pytest.fixture(scope='module')
def native(tmp_path_factory):
    directory=tmp_path_factory.mktemp('outpost-native')
    prefix=ROOT/'runs/master-implementation-2026-10-10/openmp/install'
    build(directory,prefix if (prefix/'include/omp.h').exists() else None)
    return Prototype(directory,outpost_blueprint_config())


@pytest.mark.parametrize('complete',[False,True])
@pytest.mark.parametrize('reverse',[False,True])
def test_native_direct_replay_python_all_misses_and_order(native,complete,reverse):
    cfg=outpost_blueprint_config()
    if reverse:cfg['search']['structure_order'].reverse()
    p=Prototype(native.directory,cfg)
    fixtures=[(-1,-7,-1),(123,-321,-1)]+[(0,0,i) for i in range(28)]
    with p.sweep(list(range(len(fixtures))),2 if p.identity['openmp'] else 1,fixtures=fixtures,complete=complete) as batch:
        direct=batch.records();replay=batch.records(adapter='replay')
    for i,f in enumerate(fixtures):
        oracle=evaluate_seed(i,i,cfg,backend_factory=lambda _,f=f:OutpostFixture(f),short_circuit=not complete)
        assert semantic_record(direct[i])==semantic_record(replay[i])==semantic_record(oracle)
    assert direct[0]['anchors'][0]['required_structures']['outpost']['predicted_count']==4
    assert direct[0]['anchors'][0]['deferred_requirements']==['count_monument','count_shipwreck']


def test_outpost_compact_inventory_sql_and_resume(native,tmp_path):
    with native.sweep([0,1,2],fixtures=[(0,0,-1)]*3,fixture_masks=[0,1<<12,(1<<12)|(1<<13)],
                      retention='survivors',max_misses=1) as batch:
        records=batch.retained_records();receipt=batch.retention_receipt()
    assert len(records)==2
    assert records[1]['anchors'][0]['pending_reasons']==['count_outpost']
    for r in records:
        a=r['anchors'][0]
        assert a['retention']['requirements_total']==24
        assert a['required_structures']['outpost']['inventory_status']=='COMPLETE'
    with RealmStore(tmp_path,{'config':native.cfg,'retention':{'mode':'survivors','max_misses':1}}) as s:
        s.configure_range(0,3,3);s.claim_range('test')
        prepared=s.prepare_retained_range(0,3,records,receipt)
        assert s.complete_prepared(prepared,lease=('test',1))
        assert not s.complete_prepared(prepared)
        wrong=copy.deepcopy(records);wrong[0]['anchors'][0]['retention']['requirements_total']=23
        with pytest.raises(ValueError):s.prepare_retained_range(0,3,wrong,receipt)
    with RealmStore(tmp_path,resume=True) as s:
        assert s.status()['completed_seeds']==3 and s.status()['saved_seed_rows']==2
        assert s.claim_range('resume') is None
        assert s.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def test_policy_floor_and_order_validation(native):
    cfg=outpost_blueprint_config();validate_config(cfg)
    assert 'outpost' not in river_blueprint_config()['structures']['minimum_counts']
    cfg['structures']['minimum_counts']['outpost']=1
    with pytest.raises(ValueError):validate_config(cfg)
    policy=native.ffi.new('NBPolicy *',native.policy[0])
    policy.structure_order[0]=policy.structure_order[1]
    seeds=native.ffi.new('uint64_t[]',[0])
    assert native.lib.nb_sweep(seeds,1,policy,1)==native.ffi.NULL


def test_marine_preserves_required_outpost_inventory_and_score(native):
    import numpy as np
    from seed_search.realm.raster import Raster
    from seed_search.realm.coastal import evaluate_coastal
    from seed_search.realm.marine import evaluate_marine_stage
    from seed_search.realm.reports import _candidate_rescore
    from test_river_highway import IDS
    from test_locked_blueprint import MarineBackend
    with native.sweep([0],fixtures=[(0,0,-1)]) as batch:
        candidate=batch.records()[0]['anchors'][0]
    xx,zz=np.meshgrid(np.arange(-1024,1024,4),np.arange(-1024,1024,4))
    ocean=xx<-576;river=(zz==0)&(xx>=-576)&(xx<=320);water=ocean|river
    raster=Raster((-1024,-1024,1024,1024),4,np.where(water,50.,85.),water=water,
                  biomes=np.where(ocean,IDS['ocean'],np.where(river,IDS['river'],IDS['plains'])),metadata={'source':'prediction'})
    class Backend(MarineBackend):
        calls=[]
        def structure_pair(self,name,bounds):
            self.calls.append(name)
            points={'monument':[(-800,-200),(-800,200)],'shipwreck':[(-800,i*16) for i in range(6)]}[name]
            return points,points
    pre=evaluate_coastal(raster,stronghold=(0,0),thresholds=native.cfg['terrain']['v1'],require_monument=False)
    terrain,patch=evaluate_marine_stage(candidate,native.cfg,raster,pre,backend_factory=Backend)
    assert Backend.calls==['monument','shipwreck']
    assert patch['required_structures']['outpost']==candidate['required_structures']['outpost']
    assert patch['ranking']['bonuses']['outpost']==40
    assert patch['ranking']['bonuses']['river_highway']==20
    assert _candidate_rescore({**candidate,**patch},native.cfg,'new')['ranking']==patch['ranking']


def test_coastal_line_reduction_matches_unique_with_empty_and_unknown_cells():
    import numpy as np
    from seed_search.realm.coastal import _coastal_line_ids
    rng=np.random.default_rng(451)
    for _ in range(200):
        labels=rng.integers(0,8,size=(23,37),dtype=np.int32)
        selected=rng.random(labels.shape)<rng.uniform(0,1)
        selected[0]=False;labels[1]=3;labels[2]=0
        for lines,masks in ((labels,selected),(labels.T,selected.T)):
            expected=[]
            for line,mask in zip(lines,masks):
                ids=np.unique(line[mask])
                expected.append(int(ids[0]) if len(ids)==1 and ids[0]!=0 else 0)
            assert np.array_equal(_coastal_line_ids(lines,masks),expected)
    assert not _coastal_line_ids(labels,np.zeros_like(selected)).any()


def test_natural_complete_native_records_match_python_for_signed_seeds(native):
    # Full enumeration exercises real generator state, independent of fixtures
    # and regardless of whether these natural inputs happen to survive.
    seeds=[-1,2**63-1]
    with native.sweep(seeds,2 if native.identity['openmp'] else 1,complete=True) as batch:
        actual=batch.records()
    for i,seed in enumerate(seeds):
        assert semantic_record(actual[i])==semantic_record(evaluate_seed(i,seed,native.cfg,short_circuit=False))


def test_serial_and_concurrent_owned_outpost_records(native,tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    build(tmp_path/'serial')
    serial=Prototype(tmp_path/'serial',native.cfg)
    def run(prototype,threads):
        with prototype.sweep([0,1,2],threads,fixtures=[(0,0,-1),(0,0,12),(0,0,13)],
                             retention='survivors',max_misses=1) as batch:
            return list(map(semantic_record,batch.retained_records())),batch.retention_receipt()
    expected=run(serial,1)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(run,native,2 if native.identity['openmp'] else 1) for _ in range(3)]
        assert all(f.result()==expected for f in futures)
