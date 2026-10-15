"""River model semantics, revised floors/scoring, and native/durable parity."""
import copy

import numpy as np
import pytest
import yaml

from scripts.build_blueprint_batch import ROOT,build
from seed_search.backend import biome_catalog
from seed_search.realm.config import two_group_blueprint_config,origin_blueprint_config,outpost_blueprint_config,river_blueprint_config,locked_blueprint_config,validate_config
from seed_search.realm.coastal import evaluate_coastal,_ocean_mask,_freshwater_masks,_corridor_components
from seed_search.realm.blueprint import evaluate_seed,smart_score
from seed_search.realm.native_batch import Prototype,NAMES,semantic_record
from seed_search.realm.raster import Raster
from seed_search.realm.marine import evaluate_marine_stage
from seed_search.realm.reports import _candidate_rescore
from test_locked_blueprint import LockedFixture,MarineBackend

IDS={r['name']:r['id'] for r in biome_catalog()}


def river_raster(*,shift=(0,0),frozen=False):
    bounds=tuple(v+shift[i%2] for i,v in enumerate((-1024,-1024,1024,1024)))
    xx,zz=np.meshgrid(np.arange(bounds[0],bounds[2],16)-shift[0],np.arange(bounds[1],bounds[3],16)-shift[1])
    ocean=xx<-576
    channel=(zz==0)&(xx>=-576)&(xx<=320)
    water=ocean|channel
    ids=np.where(ocean,IDS['deep_ocean'],np.where(channel,IDS['frozen_river' if frozen else 'river'],IDS['plains']))
    return Raster(bounds,16,np.where(water,50.,85.),water=water,biomes=ids,metadata={'source':'prediction'})


def result(raster,shift=(0,0)):
    return evaluate_coastal(raster,stronghold=shift,thresholds=river_blueprint_config()['terrain']['v1'],require_monument=False)


def test_river_revision_active_floors_and_old_revision_are_distinct():
    from seed_search.realm.cli import load
    cfg=river_blueprint_config();validate_config(cfg);old=locked_blueprint_config();validate_config(old)
    explicit=yaml.safe_load((ROOT/'config/realm.yaml').read_text());validate_config(explicit)
    from seed_search.realm.config import dynamic_blueprint_config
    assert load(None)['screening_revision']==dynamic_blueprint_config()['screening_revision']
    assert origin_blueprint_config()['screening_revision']=='origin-fixed-2048-v1'
    assert explicit['structures']==dynamic_blueprint_config()['structures']
    assert explicit['terrain']['v1']==dynamic_blueprint_config()['terrain']['v1']
    assert 'river_corridor_min_length_blocks' not in explicit['terrain']['v1']['coastal_continent']
    assert cfg['structures']['nether_minimum_counts']=={'fortress':2,'bastion':3}
    assert cfg['structures']['minimum_counts']['shipwreck']==5
    assert old['structures']['nether_minimum_counts']['bastion']==2
    assert old['structures']['minimum_counts']['shipwreck']==4
    for section,key,value in [('nether_minimum_counts','bastion',2),('minimum_counts','shipwreck',4)]:
        bad=copy.deepcopy(cfg);bad['structures'][section][key]=value
        with pytest.raises(ValueError):validate_config(bad)


@pytest.mark.parametrize('shift',[(0,0),(123,-321)])
def test_river_bridges_split_land_without_counting_water_and_reaches_true_hub(shift):
    raster=river_raster(shift=shift);xx,zz=raster.coordinates()
    extension=(zz==shift[1])&(xx>=shift[0]-576)
    raster.water[extension]=True;raster.biomes[extension]=IDS['river'];raster.height[extension]=50.
    r=result(raster,shift);m=r['metrics']
    assert r['model_geometry_pass'],r['reasons']
    assert m['mainland_fraction']==pytest.approx(m['land_fraction'])
    assert .75<m['mainland_fraction']<.85
    assert m['river_corridor_model_pass'] and m['river_highway_connected']
    assert m['river_components'][0]['length_lower_bound_blocks']==1584
    assert m['river_components'][0]['hub_distance_blocks']==0
    assert m['inland_freshwater_area']>0 and not m['river_navigability_verified']
    legacy=evaluate_coastal(raster,stronghold=shift,thresholds=locked_blueprint_config()['terrain']['v1'],require_monument=False)
    assert not legacy['model_geometry_pass'] and legacy['metrics']['mainland_fraction']<.5
    ocean,_,_=_ocean_mask(raster)
    assert not ocean[raster.biomes==IDS['river']].any()


def test_missing_channel_link_and_unknowns_cannot_claim_highway():
    raster=river_raster();xx,zz=raster.coordinates()
    cut=(zz==0)&(abs(xx)<80)
    raster.water[cut]=False;raster.biomes[cut]=IDS['plains'];raster.height[cut]=85.
    r=result(raster)
    assert not r['metrics']['river_highway_connected'] and not r['metrics']['river_corridor_model_pass']
    assert not r['geometry_pass']
    raster=river_raster();raster.known[(zz==0)&(abs(xx)<80)]=False
    r=result(raster)
    assert not r['geometry_pass'] and not r['metrics']['river_highway_connected']


def test_frozen_river_is_freshwater_but_not_a_boat_highway():
    r=result(river_raster(frozen=True))
    assert r['metrics']['river_corridor_model_pass']
    assert not r['metrics']['river_highway_connected']
    assert r['metrics']['inland_freshwater_area']>0


def test_inland_lakes_are_enclosed_non_ocean_water_not_shores_or_sea():
    raster=river_raster();xx,zz=raster.coordinates();pond=(abs(xx-600)<80)&(abs(zz-400)<80)
    raster.water[pond]=True;raster.height[pond]=50;raster.biomes[pond]=IDS['plains']
    ocean,_,_=_ocean_mask(raster);land=raster.known&~raster.water
    fresh,river,_,lakes=_freshwater_masks(raster,np.ones(raster.shape,bool),land,ocean)
    assert lakes[pond].all() and not ocean[pond].any()
    raster.biomes[pond]=IDS['deep_ocean'];ocean,_,_=_ocean_mask(raster)
    fresh,_,_,lakes=_freshwater_masks(raster,np.ones(raster.shape,bool),land,ocean)
    assert not fresh[pond].any() and not lakes[pond].any()
    # A dry beach/stony shore is neither ocean nor a river.
    raster.biomes[~raster.water]=IDS['stony_shore']
    assert result(raster)['metrics']['river_area']>0


def test_diagonal_land_contact_allowed_but_diagonal_water_is_not_continuous():
    raster=river_raster();mask=np.zeros(raster.shape,bool)
    for i in range(40):mask[i,i]=True
    components=_corridor_components(mask,raster,(0,0),np.zeros(mask.shape,bool),600,250)
    assert len(components)==40 and all(c['length_lower_bound_blocks']==0 for c in components)
    # Two large pieces sharing only one diagonal count as one geographic landmass.
    shape=(128,128);land=np.zeros(shape,bool);land[:64,:64]=True;land[64:,64:]=True
    raster.water=~land;raster.biomes=np.where(land,IDS['plains'],IDS['ocean']);raster.height=np.where(land,85.,50.)
    new=result(raster);old=evaluate_coastal(raster,thresholds=locked_blueprint_config()['terrain']['v1'],require_monument=False)
    assert new['metrics']['mainland_fraction']==.5 and old['metrics']['mainland_fraction']==.25


def test_lake_cell_count_is_not_corridor_length_and_components_cannot_share_credit():
    raster=river_raster();mask=np.zeros(raster.shape,bool);mask[50:70,50:70]=True
    components=_corridor_components(mask,raster,(0,0),np.zeros(mask.shape,bool),1000,250)
    assert components[0]['sampled_cells']==400
    assert components[0]['length_lower_bound_blocks']==608
    assert not components[0]['minimum_length_model_pass']
    # A long inland channel and a disconnected short mouth do not make a highway.
    xx,zz=raster.coordinates();raster.water=xx<-576;raster.biomes=np.where(raster.water,IDS['ocean'],IDS['plains'])
    long=(xx==0)&(zz>=-400)&(zz<=400);mouth=(zz==0)&(xx>=-576)&(xx<=-320)
    raster.water|=long|mouth;raster.biomes[long|mouth]=IDS['river'];raster.height=np.where(raster.water,50.,85.)
    r=result(raster);assert r['metrics']['river_corridor_model_pass'] and not r['metrics']['river_highway_connected']


def test_actual_string_biomes_win_over_numeric_predictions_and_conflicts():
    raster=river_raster();xx,zz=raster.coordinates();raster.metadata={'source':'actual','surface_biome_observations':[
        {'x':int(x),'z':int(z),'name':'minecraft:deep_ocean' if ocean else 'minecraft:river' if water else 'minecraft:plains','status':'OBSERVED'}
        for x,z,ocean,water in zip(xx.ravel(),zz.ravel(),(raster.biomes==IDS['deep_ocean']).ravel(),raster.water.ravel())]}
    raster.biomes[:]=IDS['ocean']
    r=result(raster);assert r['metrics']['river_highway_connected']
    raster.metadata['surface_biome_observations'].append({'x':0,'z':0,'name':'minecraft:deep_ocean','status':'OBSERVED'})
    assert not result(raster)['metrics']['river_highway_connected']


def test_bonus_matrix_with_cumulative_bastions_and_no_implicit_highway():
    def obs(n):return {'predicted_viable':[(i,0) for i in range(n)]}
    base={'shipwreck':obs(5),'mansion':obs(1),'monument':obs(1)}
    assert smart_score(base,{'bastion':obs(3)},{},locked=True,river=True)['score']==0
    for bastions in (3,4,5,7):
        core={**base,'shipwreck':obs(6),'mansion':obs(3),'monument':obs(3)}
        score=smart_score(core,{'bastion':obs(bastions)},{},locked=True,river=True,metrics={'river_highway_connected':True})
        assert score['score']==100+15*(bastions-3)
        assert score['bonuses']['mansion']==50 and score['bonuses']['monument']==25
    assert smart_score(base,{}, {},locked=True,river=True,metrics={'river_highway_connected':'unverified'})['bonuses']['river_highway']==0


class RiverFixture(LockedFixture):
    def structure_pair(self,name,bounds):
        raw,viable=super().structure_pair(name,bounds)
        if name=='bastion':
            point=(bounds[0]+800+len(raw)*16,bounds[1]+800);raw=raw+[point];viable=viable+[point]
        return raw,viable


@pytest.fixture(scope='module')
def river_native(tmp_path_factory):
    directory=tmp_path_factory.mktemp('river-native');prefix=ROOT/'runs/master-implementation-2026-10-10/openmp/install'
    build(directory,prefix if (prefix/'include/omp.h').exists() else None)
    return Prototype(directory,river_blueprint_config())


@pytest.mark.parametrize('complete',[False,True])
def test_revised_native_direct_replay_python_parity_and_new_bastion_miss(river_native,complete):
    fixtures=[(-1,-7,-1),(123,-321,-1),(0,0,11),(0,0,0),(0,0,13)]
    with river_native.sweep(list(range(5)),fixtures=fixtures,complete=complete) as batch:
        direct=batch.records();replay=batch.records(adapter='replay')
        for i,fixture in enumerate(fixtures):
            python=evaluate_seed(i,i,river_native.cfg,backend_factory=lambda _,f=fixture:RiverFixture(f),short_circuit=not complete)
            assert semantic_record(direct[i])==semantic_record(replay[i])==semantic_record(python)
        candidate=direct[2]['anchors'][0]
        assert 'count_bastion' in candidate['pending_reasons']
        assert candidate['required_nether_structures']['bastion']['minimum_count']==3
        assert direct[0]['anchors'][0]['marine_stage']['required_counts']['shipwreck']==5
        assert direct[0]['anchors'][0]['ranking']['bonuses']['mansion']==50


def test_river_compact_positive_and_near_miss_save_retry_and_resume(river_native,tmp_path):
    from seed_search.realm.store import RealmStore
    with river_native.sweep([0,1,2],fixtures=[(0,0,-1),(0,0,11),(0,0,-1)],
                            fixture_masks=[0,1<<11,(1<<11)|(1<<13)],
                            retention='survivors',max_misses=1) as batch:
        records=batch.retained_records();receipt=batch.retention_receipt()
    assert len(records)==2
    assert [r['anchors'][0]['retention']['classification'] for r in records]==['PREDICTED_SURVIVOR','NEAR_MISS']
    assert all(r['anchors'][0]['retention']['requirements_total']==23 for r in records)
    identity={'config':river_native.cfg,'retention':{'mode':'survivors','max_misses':1}}
    with RealmStore(tmp_path,identity) as store:
        store.configure_range(0,3,3);store.claim_range('review')
        prepared=store.prepare_retained_range(0,3,records,receipt)
        assert store.complete_prepared(prepared,lease=('review',1))
        assert not store.complete_prepared(prepared)
        wrong=copy.deepcopy(records);wrong[0]['anchors'][0]['retention']['requirements_total']=25
        with pytest.raises(ValueError,match='eligibility'):
            store.prepare_retained_range(0,3,wrong,receipt)
    with RealmStore(tmp_path,resume=True) as store:
        assert store.status()['completed_seeds']==3
        assert store.status()['saved_seed_rows']==2
        assert store.db.execute('SELECT count(*) FROM candidates').fetchone()[0]==2
        assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert store.db.execute('PRAGMA synchronous').fetchone()[0]==2
        assert store.claim_range('resume') is None


def test_marine_river_bonus_persists_through_rescore_and_atomic_retry(river_native,tmp_path):
    from seed_search.realm.store import RealmStore
    cfg=river_native.cfg
    with river_native.sweep([0],fixtures=[(0,0,-1)]) as batch:record=batch.records()[0]
    candidate=record['anchors'][0]
    # Rebuild the full finest raster rather than relabeling a coarse array.
    xx,zz=np.meshgrid(np.arange(-1024,1024,4),np.arange(-1024,1024,4));ocean=xx<-576;channel=(zz==0)&(xx>=-576)&(xx<=320);water=ocean|channel
    raster=Raster((-1024,-1024,1024,1024),4,np.where(water,50.,85.),water=water,biomes=np.where(ocean,IDS['ocean'],np.where(channel,IDS['river'],IDS['plains'])),metadata={'source':'prediction'})
    class Backend(MarineBackend):
        def structure_pair(self,name,bounds):
            values={'monument':[(-800,-200),(-800,200)],'shipwreck':[(-800,i*16) for i in range(6)],'outpost':[]}[name]
            return values,values
    pre=result(raster)
    terrain,patch=evaluate_marine_stage(candidate,cfg,raster,pre,backend_factory=Backend)
    assert terrain['model_geometry_pass'] and patch['marine_stage']['status']=='PREDICTED'
    assert patch['ranking']['bonuses']['river_highway']==20
    assert patch['ranking']['bonuses']['monument']==25 and patch['ranking']['bonuses']['shipwreck']==5
    updated={**candidate,**patch};again=_candidate_rescore(copy.deepcopy(updated),cfg,'new-score')
    assert again['ranking']==updated['ranking']
    # Atomic candidate patch and duplicate retry use the production store API.
    with RealmStore(tmp_path,identity={'config':cfg}) as store:
        store.configure_range(0,1,1);store.claim_range('test');store.complete_range(0,1,[record])
        revision=store.ensure_terrain_pool({'test':'river'})
        unit_id=store.ensure_terrain_work(revision,candidate['id'],'v1',{
            'stage':'height','raster_bounds':candidate['bounds']['overworld'],
            'resolution':4,'lattice':{'version':'fixture-v1'},'halo_level':0,'coarse_center':[0,0]})
        unit=store.claim_terrain_work(unit_id,'test')
        from seed_search.realm.terrain import _encode_terrain_raster
        observation=_encode_terrain_raster(raster,unit)
        assert store.complete_terrain_work(unit_id,result=terrain,observation=observation,candidate_update=patch)
        assert not store.complete_terrain_work(unit_id,result=terrain,observation=observation,candidate_update=patch)
        saved=store.get_candidate(candidate['id'])
        assert saved['ranking']['bonuses']['river_highway']==20
        with pytest.raises(ValueError,match='retry differs'):
            store.complete_terrain_work(unit_id,result=terrain,observation=observation,candidate_update={**patch,'baseline_score_observed':999})


@pytest.mark.parametrize('outpost',[False,True])
def test_production_terrain_pipeline_applies_river_and_marine_score_once_and_resumes(river_native,tmp_path,monkeypatch,outpost):
    from seed_search.realm.store import RealmStore
    from seed_search.realm.terrain import run_terrain
    import seed_search.realm.marine as marine
    cfg=outpost_blueprint_config() if outpost else river_native.cfg
    native=Prototype(river_native.directory,cfg)
    class Provider:
        calls=[]
        def __init__(self,seed):pass
        def sample_raster(self,*,bounds,resolution,**kwargs):
            self.calls.append(resolution)
            xx,zz=np.meshgrid(np.arange(bounds[0],bounds[2],resolution),np.arange(bounds[1],bounds[3],resolution))
            ocean=xx<-576;channel=(zz==0)&(xx>=-576)&(xx<=320);water=ocean|channel
            return Raster(bounds,resolution,np.where(water,50.,85.),water=water,
                biomes=np.where(ocean,IDS['ocean'],np.where(channel,IDS['river'],IDS['plains'])),metadata={'source':'prediction'})
    class Backend(MarineBackend):
        calls=[]
        def structure_pair(self,name,bounds):
            self.calls.append(name)
            points={'monument':[(-800,-200),(-800,200)],'shipwreck':[(-800,i*16) for i in range(6)],'outpost':[]}[name]
            return points,points
    original=marine.evaluate_marine_stage
    monkeypatch.setattr(marine,'evaluate_marine_stage',lambda *args,**kw:original(*args,**kw,backend_factory=Backend))
    with native.sweep([0],fixtures=[(0,0,-1)]) as batch:record=batch.records()[0]
    cid=record['anchors'][0]['id']
    with RealmStore(tmp_path,identity={'config':cfg}) as store:
        store.configure_range(0,1,1);store.claim_range('test');store.complete_range(0,1,[record])
        first=run_terrain(store,cfg,limit=1,provider_factory=Provider,provider_identity={'fixture':'river-v2'})
        assert first['results']==5
        saved=store.get_candidate(cid)
        assert saved['marine_stage']['required_counts']=={'monument':1,'shipwreck':5}
        assert saved['ranking']['bonuses']['river_highway']==20
        assert saved['ranking']['bonuses']['shipwreck']==5
        from seed_search.realm.reports import ranked
        assert ranked(store,limit=1)[0]['smart_score']==saved['ranking']['score']
        assert Backend.calls==(['monument','shipwreck'] if outpost else ['monument','shipwreck','outpost'])
        if outpost:assert saved['required_structures']['outpost']['predicted_count']==4
        assert Provider.calls==[128,64,32,16,8,4]
        resumed=run_terrain(store,cfg,limit=1,provider_factory=Provider,provider_identity={'fixture':'river-v2'})
        assert resumed['results']==0 and len(Backend.calls)==(2 if outpost else 3)


def test_compiled_river_paths_match_independent_queue_oracle():
    from collections import deque
    from scipy import ndimage
    rng=np.random.default_rng(48210)
    for repeat in range(100):
        mask=rng.random((12,15))>.35
        raster=Raster((0,0,60,48),4,np.full(mask.shape,50.),water=mask)
        actual=_corridor_components(mask,raster,(0,0),np.zeros(mask.shape,bool),32,12)
        labels,_=ndimage.label(mask)
        for report in actual:
            component=labels==report['component_id'];start=tuple(np.argwhere(component)[0])
            def farthest(start):
                queue=deque([start]);distance={start:0};last=start
                while queue:
                    r,c=last=queue.popleft()
                    for point in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                        rr,cc=point
                        if 0<=rr<12 and 0<=cc<15 and component[point] and point not in distance:
                            distance[point]=distance[last]+1;queue.append(point)
                return last,distance[last]
            end,_=farthest(start);other,steps=farthest(end)
            assert report['length_lower_bound_blocks']==steps*4
            assert report['path_endpoints']==[[point[1]*4,point[0]*4] for point in (end,other)]


def test_river_parallel_and_serial_owned_records_match(river_native):
    if not river_native.identity['openmp']:pytest.skip('Serial host')
    seeds=[0,-1,-2**63,2**32+12345]*8
    fixtures=[(-1,-7,-1),(0,0,11),(0,0,0),(0,0,13)]*8
    def run(threads):
        with river_native.sweep(seeds,threads,fixtures=fixtures,retention='survivors',max_misses=1) as batch:
            return batch.retention_receipt(),list(map(semantic_record,batch.retained_records()))
    expected=run(1)
    assert run(3)==expected


def test_offshore_island_river_cannot_satisfy_mainland_waterway():
    raster=river_raster();xx,zz=raster.coordinates()
    # Remove the mainland channel, then add a separate offshore island/river.
    mainland_channel=raster.biomes==IDS['river'];raster.water[mainland_channel]=False;raster.biomes[mainland_channel]=IDS['plains']
    island=(abs(xx+896)<=32)&(abs(zz)<=400)
    channel=(xx==-896)&(abs(zz)<=400)
    raster.water[island]=False;raster.biomes[island]=IDS['plains']
    raster.water[channel]=True;raster.biomes[channel]=IDS['river'];raster.height=np.where(raster.water,50.,85.)
    r=result(raster)
    assert not r['metrics']['river_corridor_model_pass']
    assert not r['metrics']['river_highway_connected']
    assert r['metrics']['river_area']==0 and r['metrics']['river_components']==[]
