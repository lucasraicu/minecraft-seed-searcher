"""Locked geometry parity and durable post-terrain marine handoff."""
import copy

import numpy as np
import pytest

from scripts.build_blueprint_batch import build,ROOT
from seed_search.backend import biome_catalog
from seed_search.realm.blueprint import evaluate_seed, biome_gate, smart_score
from seed_search.realm.config import locked_blueprint_config, blueprint_config, validate_config
from seed_search.realm.native_batch import Prototype, NAMES, semantic_record
from seed_search.realm.coastal import evaluate_coastal
from seed_search.realm.marine import evaluate_marine_stage
from seed_search.realm.raster import Raster
from seed_search.realm.store import RealmStore

IDS={r['name']:r['id'] for r in biome_catalog()}


class LockedFixture:
    surface=['plains','desert','forest','taiga','jungle','swamp','snowy_plains','dark_forest','jagged_peaks','stony_shore']
    caves=['lush_caves','dripstone_caves','deep_dark']
    def __init__(self,fixture,mask=0):self.x,self.z,self.missing=fixture;self.mask=mask;self.native_work={};self.calls=[]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def structure_pair(self,name,bounds):
        self.calls.append(name)
        if name=='stronghold':return [(self.x,self.z)],[(self.x,self.z)]
        cfg=locked_blueprint_config();slot=NAMES.index(name)
        goal=cfg['structures']['minimum_counts'].get(name,cfg['structures']['nether_minimum_counts'].get(name,1))
        n=goal-1 if self.missing==slot or self.mask&(1<<slot) else goal+2
        points=[(bounds[0]+800+i*16,bounds[1]+800) for i in range(n)]
        return points,points
    def structure_count(self,name,bounds,minimum):return self.structure_pair(name,bounds)[1][:minimum]
    def nether_structure_pairs(self,bounds):return {n:self.structure_pair(n,bounds) for n in ('fortress','bastion')}
    def biome_points(self,points):
        values=[]
        for x,y,z in points:
            if x%64 or z%64:name='pale_garden' if self.missing==27 or x==self.x+32 else 'dark_forest'
            else:
                cave=y in (-48,0)
                if self.missing==26:name='dark_forest' if cave else 'lush_caves'
                else:
                    choices=self.caves if cave else self.surface;k=(int(x)//64+int(z)//64)%len(choices);family=k+10 if cave else k
                    if self.missing==family+13 or self.mask&(1<<(family+13)):values.append(-1);continue
                    name=choices[k]
            values.append(IDS[name])
        return np.array(values,dtype=np.int32)


@pytest.fixture(scope='module')
def locked_native(tmp_path_factory):
    output=tmp_path_factory.mktemp('locked-native')
    prefix=ROOT/'runs/master-implementation-2026-10-10/openmp/install'
    build(output,prefix if (prefix/'include/omp.h').exists() else None)
    return Prototype(output,locked_blueprint_config())


def test_revision_geometry_floors_and_historical_config():
    old=blueprint_config();cfg=locked_blueprint_config();validate_config(old);validate_config(cfg)
    assert old['deployment']['overworld_side_blocks']==1536
    assert cfg['deployment']=={'overworld_side_blocks':2048,'nether_side_blocks':1024}
    assert cfg['structures']['nether_minimum_counts']=={'fortress':2,'bastion':2}
    assert cfg['structures']['minimum_counts']['shipwreck']==4
    for path,value in [(('deployment','overworld_side_blocks'),1792),(('structures','minimum_counts','village'),5),(('structures','nether_minimum_counts','fortress'),1)]:
        bad=copy.deepcopy(cfg);parent=bad
        for key in path[:-1]:parent=parent[key]
        parent[path[-1]]=value
        with pytest.raises(ValueError):validate_config(bad)


@pytest.mark.parametrize('complete',[False,True])
def test_native_direct_replay_and_independent_all_floors_and_four_y(locked_native,complete):
    fixtures=[(-1,-7,-1),(0,0,-1),(-1025,1023,-1)]+[(0,0,k) for k in [0,1,2,4,5,6,7,9,10,11,*range(13,28)]]
    seeds=list(range(len(fixtures)))
    with locked_native.sweep(seeds,fixtures=fixtures,complete=complete) as batch:
        records=batch.records();replayed=batch.records(adapter='replay')
        for r in [batch.pointer.results[i] for i in range(len(seeds))]:
            for j in range(r.nanchors):
                assert not r.anchors[j].observations[3].evaluated
                assert not r.anchors[j].observations[8].evaluated
                assert not r.anchors[j].observations[12].evaluated
    for i,(fixture,row,replay) in enumerate(zip(fixtures,records,replayed)):
        expected=evaluate_seed(i,i,locked_blueprint_config(),backend_factory=lambda _,f=fixture:LockedFixture(f),short_circuit=not complete)
        assert semantic_record(row)==semantic_record(replay)==semantic_record(expected),fixture
    candidate=records[0]['anchors'][0]
    assert candidate['bounds']['overworld']==[-1025,-1031,1023,1017]
    assert candidate['bounds']['final_nether']==[-512.125,-512.875,511.875,511.125]
    assert candidate['biomes']['sampling']['expected_points']==4096
    assert not candidate['full_blueprint_certification'] and candidate['marine_stage']['status']=='DEFERRED'


@pytest.mark.parametrize('complete',[False,True])
def test_real_full64_negative_boundaries_parity(locked_native,complete):
    seeds=[0,-1,-2**63,2**63-1,12345,2**32+12345]
    with locked_native.sweep(seeds,complete=complete) as batch:rows=batch.records()
    for i,(seed,row) in enumerate(zip(seeds,rows)):
        assert semantic_record(row)==semantic_record(evaluate_seed(i,seed,locked_blueprint_config(),short_circuit=not complete))


def test_nether_first_reject_skips_expensive_overworld(locked_native):
    with locked_native.sweep([1],fixtures=[(0,0,10)]) as batch:
        c=batch.pointer.results[0].anchors[0]
        assert c.count_missing==(1<<10)
        assert not any(c.observations[k].evaluated for k in range(10))
        assert batch.records()[0]['anchors'][0]['pending_reasons']==['count_fortress']


def test_one_miss_retains_floor_shortfall_and_two_misses_discard(locked_native,tmp_path):
    fixtures=[(0,0,-1)]*4; masks=[0,1<<5,(1<<5)|(1<<10),1<<(13+6)]
    with locked_native.sweep([1,2,3,4],fixtures=fixtures,fixture_masks=masks,retention='survivors',max_misses=1) as batch:
        records=batch.retained_records();receipt=batch.retention_receipt()
    assert [r['index'] for r in records]==[0,1,3]
    assert records[1]['anchors'][0]['retention']['requirements_total']==23
    ident={'config':locked_blueprint_config(),'retention':{'mode':'survivors','max_misses':1}}
    with RealmStore(tmp_path/'checkpoint',identity=ident) as store:
        store.configure_range(0,4,4);start,end=store.claim_range('fixture')
        prepared=store.prepare_retained_range(start,end,records,receipt)
        store.complete_prepared(prepared)
        assert store.status()['completed_seeds']==4
        assert store.db.execute('SELECT count(*) FROM candidates').fetchone()[0]==3
        assert store.db.execute("SELECT count(*) FROM variant_tasks WHERE variant='v1'").fetchone()[0]==3
        assert store.db.execute('PRAGMA synchronous').fetchone()[0]==2


def test_rare_family_after_initial_128_points_still_survives():
    cfg=locked_blueprint_config()
    class Late(LockedFixture):
        count=0
        def biome_points(self,points):
            values=super().biome_points(points)
            for i,(x,y,z) in enumerate(points):
                if self.count+i<512 and values[i]==IDS['snowy_plains']:values[i]=IDS['plains']
            self.count+=len(points)
            return values
    result=biome_gate(Late((0,0,-1)),(-1024,-1024,1024,1024),cfg)
    assert result['qualification']=='PREDICTED' and result['sample_count']>512
    assert result['witnesses']['snowy_ice']['biome']=='snowy_plains'


def coastal_raster():
    shape=(512,512);water=np.zeros(shape,bool);water[:,-128:]=True
    return Raster((-1024,-1024,1024,1024),4,np.where(water,50.,70.),
                  biomes=np.where(water,IDS['deep_ocean'],IDS['plains']),water=water,
                  metadata={'source':'prediction','data_status':'PREDICTED'})


class MarineBackend:
    calls=[]
    def __init__(self,seed):pass
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def structure_pair(self,name,bounds):
        self.calls.append(name)
        values={'monument':[(800,0),(0,0)],'shipwreck':[(800,i*16) for i in range(4)]+[(0,0)],'outpost':[(0,16)]}[name]
        return values,values


def test_marine_waits_for_complete_finest_coast_and_filters_full_inventories():
    cfg=locked_blueprint_config();raster=coastal_raster();candidate=evaluate_seed(0,1,cfg,backend_factory=lambda _:LockedFixture((0,0,-1)))['anchors'][0]
    pre=evaluate_coastal(raster,bounds=candidate['bounds']['overworld'],thresholds=cfg['terrain']['v1'],require_monument=False)
    assert pre['model_geometry_pass'] and pre['metrics']['known_fraction']==1.
    MarineBackend.calls=[]
    failed=copy.deepcopy(pre);failed['model_geometry_pass']=False
    assert evaluate_marine_stage(candidate,cfg,raster,failed,backend_factory=MarineBackend)[1] is None
    raster.known[0,0]=False
    unknown=evaluate_coastal(raster,thresholds=cfg['terrain']['v1'],require_monument=False)
    assert evaluate_marine_stage(candidate,cfg,raster,unknown,backend_factory=MarineBackend)[1] is None
    assert MarineBackend.calls==[]
    raster.known[:]=True
    result,patch=evaluate_marine_stage(candidate,cfg,raster,pre,backend_factory=MarineBackend)
    assert MarineBackend.calls==['monument','shipwreck','outpost']
    assert patch['marine_stage']['status']=='PREDICTED' and result['geometry_pass']
    assert patch['required_structures']['monument']['predicted_count']==1
    assert len(patch['required_structures']['monument']['unfiltered_predicted_viable'])==2
    assert patch['required_structures']['shipwreck']['predicted_count']==4
    assert not patch['full_blueprint_certification']
    assert evaluate_marine_stage({**candidate,**patch},cfg,raster,result,backend_factory=MarineBackend)[1] is None


def test_locked_bonus_thresholds():
    def obs(n):return {'predicted_viable':[(i,0) for i in range(n)]}
    core={name:obs(n) for name,n in [('village',6),('trial_chamber',5),('ancient_city',2),('ruined_portal',6),('mineshaft',15)]}
    assert smart_score(core,{'fortress':obs(2),'bastion':obs(2)},{},locked=True)['score']==0
    core.update(village=obs(7),trial_chamber=obs(7),ancient_city=obs(4),mineshaft=obs(18))
    assert smart_score(core,{'fortress':obs(4),'bastion':obs(3)},{},locked=True)['score']==103


def test_parallel_owned_results_and_same_adapter_concurrent_calls(locked_native):
    from concurrent.futures import ThreadPoolExecutor
    if not locked_native.identity['openmp']:pytest.skip('Serial host')
    seeds=[0,-1,-2**63,12345,2**32+12345]*4
    def run(threads):
        with locked_native.sweep(seeds,threads,retention='survivors',max_misses=1) as batch:
            return batch.retention_receipt(),list(map(semantic_record,batch.retained_records()))
    expected=run(1)
    with ThreadPoolExecutor(2) as executor:
        assert list(executor.map(run,[2,3]))==[expected,expected]


def test_marine_patch_and_terrain_completion_are_atomic_and_exact_retry(tmp_path):
    cfg=locked_blueprint_config();candidate_record=evaluate_seed(0,1,cfg,backend_factory=lambda _:LockedFixture((0,0,-1)))
    candidate=candidate_record['anchors'][0];raster=coastal_raster()
    pre=evaluate_coastal(raster,thresholds=cfg['terrain']['v1'],require_monument=False)
    result,patch=evaluate_marine_stage(candidate,cfg,raster,pre,backend_factory=MarineBackend)
    with RealmStore(tmp_path/'marine',identity={'config':cfg}) as store:
        store.configure_range(0,1,1);store.claim_range('test');store.complete_range(0,1,[candidate_record])
        revision=store.ensure_terrain_pool({'test':'marine'})
        unit_id=store.ensure_terrain_work(revision,candidate['id'],'v1',{
            'stage':'height','raster_bounds':candidate['bounds']['overworld'],
            'resolution':4,'lattice':{'version':'fixture-v1'},'halo_level':0,'coarse_center':[0,0]})
        unit=store.claim_terrain_work(unit_id,'test')
        from seed_search.realm.terrain import _encode_terrain_raster
        observation=_encode_terrain_raster(raster,unit)
        invalid={**patch,'id':'unknown'}
        with pytest.raises(ValueError):store.complete_terrain_work(unit_id,result=result,observation=observation,candidate_update=invalid)
        assert store.get_candidate(candidate['id'])['marine_stage']['status']=='DEFERRED'
        assert store.get_terrain_work(unit_id)['status']=='leased'
        assert store.complete_terrain_work(unit_id,result=result,observation=observation,candidate_update=patch)
        assert store.get_candidate(candidate['id'])['marine_stage']['status']=='PREDICTED'
        assert not store.complete_terrain_work(unit_id,result=result,observation=observation,candidate_update=patch)
        with pytest.raises(ValueError,match='retry differs'):
            store.complete_terrain_work(unit_id,result=result,observation=observation,candidate_update={**patch,'baseline_score_observed':100000})


def test_actual_durable_terrain_entrypoint_queries_marine_once_and_resumes(tmp_path,monkeypatch):
    from seed_search.realm.terrain import run_terrain
    import seed_search.realm.marine as marine
    cfg=locked_blueprint_config()
    class Provider:
        calls=[]
        def __init__(self,seed):pass
        def sample_raster(self,*,bounds,resolution,**kwargs):
            self.calls.append(resolution)
            xx,zz=np.meshgrid(np.arange(bounds[0],bounds[2],resolution),np.arange(bounds[1],bounds[3],resolution))
            water=xx>=512
            return Raster(bounds,resolution,np.where(water,50.,70.),water=water,
                          biomes=np.where(water,IDS['deep_ocean'],IDS['plains']),metadata={'source':'prediction'})
    original=marine.evaluate_marine_stage
    monkeypatch.setattr(marine,'evaluate_marine_stage',lambda *a,**kw:original(*a,**kw,backend_factory=MarineBackend))
    MarineBackend.calls=[]
    record=evaluate_seed(0,1,cfg,backend_factory=lambda _:LockedFixture((0,0,-1)))
    with RealmStore(tmp_path/'workflow',identity={'config':cfg}) as store:
        store.configure_range(0,1,1);store.claim_range('fixture');store.complete_range(0,1,[record])
        result=run_terrain(store,cfg,limit=1,provider_factory=Provider,provider_identity={'build':'locked-coast-fixture-v1'})
        assert result['results']==5
        candidate=store.get_candidate('1:0:0')
        assert candidate['marine_stage']['status']=='PREDICTED'
        assert MarineBackend.calls==['monument','shipwreck','outpost']
        assert Provider.calls==[128,64,32,16,8,4]
        resumed=run_terrain(store,cfg,limit=1,provider_factory=Provider,provider_identity={'build':'locked-coast-fixture-v1'})
        assert resumed['results']==0 and len(MarineBackend.calls)==3
