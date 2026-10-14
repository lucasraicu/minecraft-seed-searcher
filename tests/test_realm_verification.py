import numpy as np
import pytest
from seed_search.realm.verification import VerificationAdapter, tiles, final_nether_evidence, raster_from_columns


def runtime(seed, requests):
    rows = []
    for q in requests:
        rows.extend({'x':x,'z':z,'ground':{'y':80},'policy':'actual-column-v2','waterKnown':True,'waterDepth':2 if x%8==0 else 0}
                    for z in range(q['z0'],q['z0']+q['side'],q['spacing'])
                    for x in range(q['x0'],q['x0']+q['side'],q['spacing']))
    return {'columns':rows, 'stable':True}


def test_tiled_lattice_complete_and_cache():
    calls=[]
    def wrapped(seed, requests):
        calls.append(requests)
        return runtime(seed,requests)
    a=VerificationAdapter({'bds':{'verification_budget':1}},runtime=wrapped)
    r=a.verify('-9223372036854775808',(-259,-131,342,172),7,'top')
    assert r['status']=='PARTIAL'
    raster=a.sample_raster('-9223372036854775808',(-259,-131,342,172),7)
    assert raster.known.all() and not raster.natural_ground.any()
    assert len(calls)==1 and len(calls[0])==6
    assert a.verify('2',(0,0,8,8))['reason']=='Verification budget exhausted'
    for q in calls[0]:
        chunks=((q['x0']+q['side']-1)//16-q['x0']//16+1)*((q['z0']+q['side']-1)//16-q['z0']//16+1)
        assert q['side']<=256 and chunks<=300


def test_unstable_snapshot_unknown_and_overlap_disagreement():
    r=raster_from_columns((0,0,1,1),1,[{'x':0,'z':0,'ground':{'y':90},'policy':'actual-column-v2','waterKnown':True,'waterDepth':0}],{'stable':False})
    assert not r.known.any()
    with pytest.raises(ValueError,match='disagree'):
        raster_from_columns((0,0,1,1),1,[{'x':0,'z':0,'ground':{'y':90}}, {'x':0,'z':0,'ground':{'y':91}}],{'stable':True})


def test_no_automatic_large_generation():
    a=VerificationAdapter({},runtime=lambda *args:pytest.fail('Large run should be deferred'))
    assert a.verify('1',(-1344,-1344,1344,1344))['status']=='PARTIAL'
    assert a.used==0
    with pytest.raises(ValueError):
        list(tiles((0,0,1,1),False))


def test_fractional_negative_nether_positive_and_unknown():
    a=VerificationAdapter({})
    r=a.verify_final_nether('1',(-1,-9))
    assert r['center']==[-.125,-1.125]
    assert r['bounds']==[-448,-449,448,447]
    evidence={'seed':'1','bds_version':'1.26.52.3','dimension':'nether','source':'snapshot-abc',
              'structures':{'fortress':[{'x':-448,'y':64,'z':-449,'actual':True}],
                            'bastion':[{'x':447,'y':64,'z':446,'actual':True}]}}
    # 1 Fortress + 1 Bastion is insufficient under policy-aware verification (requires 2 fortresses, 3 bastions)
    assert a.verify_final_nether('1',(-1,-9),evidence=evidence)['status']=='PARTIAL'
    evidence['structures']['fortress'].append({'x':-100,'y':64,'z':-100,'actual':True})
    evidence['structures']['bastion'].extend([{'x':100,'y':64,'z':100,'actual':True},
                                             {'x':200,'y':64,'z':200,'actual':True}])
    assert a.verify_final_nether('1',(-1,-9),evidence=evidence)['status']=='VERIFIED'
    evidence['structures']['bastion']=[{'x':448,'y':64,'z':446,'actual':True}]
    assert a.verify_final_nether('1',(-1,-9),evidence=evidence)['status']=='PARTIAL'
    evidence.update(exhaustive=True,coverage_complete=True,bounds=r['bounds'])
    assert a.verify_final_nether('1',(-1,-9),evidence=evidence)['status']=='FAILED'
    evidence.pop('source')
    with pytest.raises(ValueError,match='source'):
        a.verify_final_nether('1',(-1,-9),evidence=evidence)


def test_budget_persists_in_store(tmp_path):
    from seed_search.realm.store import RealmStore
    with RealmStore(tmp_path,{}) as store:
        a=VerificationAdapter({'bds':{'verification_budget':1}},store,runtime=runtime)
        r=a.verify('1',(0,0,8,8))
        assert store.get_state('bds_verification_used')==1
        b=VerificationAdapter({'bds':{'verification_budget':1}},store,runtime=lambda *args:pytest.fail('Cached'))
        assert b.verify('1',(0,0,8,8))==r
        assert b.verify('2',(0,0,8,8))['status']=='PARTIAL'


def test_calibration_selected_sample_biases_explicit():
    from seed_search.realm.verification import calibrate_prediction
    class Predictor:
        seed=1
        def heights(self,points,step):
            return np.array([62.,80.]), np.array([0,0])
    result=calibrate_prediction(Predictor(),{'seed':'1','bounds':[0,0,2,1],'spacing':1,'evidence':{'stable':True,'columns':[
        {'x':0,'z':0,'ground':{'y':60},'policy':'actual-column-v2','waterKnown':True,'waterDepth':0},
        {'x':1,'z':0,'ground':{'y':85},'policy':'actual-column-v2','waterKnown':True,'waterDepth':2}]}})
    assert result['sample_count']==2 and result['height_mae_blocks']==3.5
    assert result['height_max_absolute_error_blocks']==5
    assert result['water_proxy_mismatch_count']==2
    assert 'height_at_or_below_sea_level_proxy'==result['predicted_water_evidence']


def test_failed_provider_persisted_and_explicit_retry_budget(tmp_path):
    from seed_search.realm.store import RealmStore
    def broken(*args):
        raise RuntimeError('provider unavailable')
    with RealmStore(tmp_path,{}) as store:
        a=VerificationAdapter({'bds':{'verification_budget':2}},store,runtime=broken)
        result=a.verify('1',(0,0,8,8))
        assert result['status']=='FAILED' and result['seed_eligibility']=='UNKNOWN'
        assert result['error']=={'type':'RuntimeError','message':'provider unavailable'}
        assert result['attempt']==1 and store.get_state('bds_verification_used')==1
        assert len(list(store.iter_observations()))==2
        b=VerificationAdapter({'bds':{'verification_budget':2}},store,runtime=runtime)
        assert b.verify('1',(0,0,8,8))==result
        assert store.get_state('bds_verification_used')==1
        assert b.sample_raster('1',(0,0,8,8),4).quality()=='FAILED'
        success=b.verify('1',(0,0,8,8),retry_failed=True)
        assert success['status']=='PARTIAL' and success['attempt']==2
        assert store.get_state('bds_verification_used')==2
        assert b.verify('2',(0,0,8,8))['reason']=='Verification budget exhausted'
        assert store.get_observation(result['id']+':attempt:1')['status']=='FAILED'
        assert store.status()['completed_seeds']==0


def test_interruptions_propagate():
    def interrupted(*args):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        VerificationAdapter({},runtime=interrupted).verify('1',(0,0,8,8))


@pytest.mark.parametrize('field,value', [('x',1.5),('y',64.0),('z',True),('actual',1),('source','')])
def test_imported_anchor_invalid(field,value):
    evidence={'seed':'1','bds_version':'1.26.52.3','dimension':'nether','source':'stopped snapshot',
              'structures':{'fortress':[{'x':0,'y':64,'z':0,'actual':True,field:value}]}}
    with pytest.raises(ValueError):
        final_nether_evidence('1',(0,0),evidence)


def test_import_unknown_and_wrong_build_seed():
    evidence={'seed':'1','bds_version':'1.26.52.3','dimension':'nether','source':'stopped snapshot',
              'structures':{'fortress':[{'x':0,'y':64,'z':0,'actual':False}]}}
    result=final_nether_evidence('1',(0,0),evidence)
    assert result['status']=='PARTIAL' and result['structures']['fortress']['status']=='UNKNOWN'
    evidence['bds_version']='wrong'
    with pytest.raises(ValueError,match='mismatch'):
        final_nether_evidence('1',(0,0),evidence)
    with pytest.raises(ValueError):
        final_nether_evidence('9223372036854775808',(0,0))
    with pytest.raises(ValueError):
        final_nether_evidence('1',(False,0))


@pytest.mark.parametrize('key,value', [('version','1.26.50'),('cpus',2),('memory_gib',8),('maximum_region_side',128),('persist_snapshot','false'),('unknown_world_option',True)])
def test_runtime_overrides_cannot_be_ignored(key,value):
    with pytest.raises(ValueError):
        VerificationAdapter({'bds':{key:value}},runtime=lambda *a:pytest.fail('No generation'))


def test_supplied_world_settings_and_identity():
    from seed_search.realm.verification import pinned_world_settings
    settings=pinned_world_settings()
    assert settings['gamemode']=='creative' and 'level-seed' not in settings
    a=VerificationAdapter({'bds':{'world_settings':{'difficulty':'peaceful','allow-cheats':'true'}}})
    assert a.identity['world_settings']==settings
    assert a.identity['runtime_allocation']=={'cpus':4,'memory_gib':6,'published_ports':[]}
    for supplied in ({'difficulty':'hard'},{'level-seed':'1'},{'allow-cheats':True}):
        with pytest.raises(ValueError,match='world_settings'):
            VerificationAdapter({'bds':{'world_settings':supplied}})
    with pytest.raises(ValueError,match='game setting'):
        VerificationAdapter({'game':{'bds_version':'wrong'}})


def test_profile_rejects_previously_permitted_unmeasured_allocation():
    from seed_search.realm.config import default_config,validate_config
    for key,value in [('cpus',1),('memory_gib',4),('maximum_region_side',64)]:
        cfg=default_config();cfg['bds'][key]=value
        with pytest.raises(ValueError):validate_config(cfg)
    assert validate_config(default_config())


def test_thin_tile_overscan_permits_single_requested_sample():
    q=list(tiles((-1,-1,0,0),16))[0]
    assert q['side']==16 and q['spacing']==16
    rows=runtime('1',[q])['columns']
    raster=raster_from_columns((-1,-1,0,0),16,rows,{'stable':True})
    assert raster.shape==(1,1) and raster.known.all()


@pytest.mark.parametrize('budget',[1,3])
def test_concurrent_store_connections_reserve_unique_bounded_attempts(tmp_path,budget):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    from seed_search.realm.store import RealmStore
    workers=6
    start=threading.Barrier(workers)
    legacy_reads=threading.Barrier(workers)
    calls=[]
    class SynchronizedLegacyRead(RealmStore):
        def get_state(self,key):
            value=super().get_state(key)
            if key=='bds_verification_used':
                # Force the former read-then-set implementation to race;
                # atomic reservations bypass this nontransactional getter.
                legacy_reads.wait(timeout=10)
            return value
    with RealmStore(tmp_path,{}) as original:
        original.set_state('bds_verification_used',0)
    def provider(seed,requests):
        calls.append(seed)
        return runtime(seed,requests)
    def worker(index):
        with SynchronizedLegacyRead(tmp_path,resume=True) as store:
            adapter=VerificationAdapter({'bds':{'verification_budget':budget}},store,runtime=provider)
            start.wait(timeout=10)
            return adapter.verify(str(index+1),(0,0,8,8))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results=list(executor.map(worker,range(workers)))
    attempted=[r for r in results if 'attempt' in r]
    assert len(calls)==len(attempted)==budget
    assert sorted(r['attempt'] for r in attempted)==list(range(1,budget+1))
    assert all(r.get('reason')=='Verification budget exhausted' for r in results if 'attempt' not in r)
    with RealmStore(tmp_path,resume=True) as saved:
        assert saved.get_state('bds_verification_used')==budget
        assert len(list(saved.iter_observations()))==budget
        # Resume uses the same persisted cap; no provider call is allowed.
        adapter=VerificationAdapter({'bds':{'verification_budget':budget}},saved,runtime=lambda *a:pytest.fail('Budget exceeded'))
        assert adapter.verify('100',(0,0,8,8))['reason']=='Verification budget exhausted'


def test_reservation_rejects_open_caller_transaction_without_committing(tmp_path):
    from seed_search.realm.store import RealmStore
    with RealmStore(tmp_path,{}) as store:
        store.db.execute("INSERT INTO meta VALUES ('caller_pending','true')")
        adapter=VerificationAdapter({},store,runtime=lambda *a:pytest.fail('No provider'))
        with pytest.raises(RuntimeError,match='open caller transaction'):
            adapter.verify('1',(0,0,8,8))
        assert store.db.in_transaction
        store.db.rollback()
        assert store.get_state('caller_pending') is None
        assert store.get_state('bds_verification_used') is None


def test_in_memory_concurrent_calls_keep_local_attempt_ids():
    from concurrent.futures import ThreadPoolExecutor
    import threading
    finish_together=threading.Barrier(2)
    def provider(seed,requests):
        finish_together.wait(timeout=10)
        return runtime(seed,requests)
    adapter=VerificationAdapter({'bds':{'verification_budget':2}},runtime=provider)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results=list(executor.map(lambda seed:adapter.verify(seed,(0,0,8,8)),['1','2']))
    assert sorted(r['attempt'] for r in results)==[1,2]
    assert adapter.used==2


def test_interrupted_reserved_attempt_stays_consumed_on_resume(tmp_path):
    from seed_search.realm.store import RealmStore
    def interrupted(*args):
        raise KeyboardInterrupt()
    with RealmStore(tmp_path,{}) as store:
        adapter=VerificationAdapter({'bds':{'verification_budget':1}},store,runtime=interrupted)
        with pytest.raises(KeyboardInterrupt):adapter.verify('1',(0,0,8,8))
        assert store.get_state('bds_verification_used')==1
    with RealmStore(tmp_path,resume=True) as store:
        adapter=VerificationAdapter({'bds':{'verification_budget':1}},store,runtime=lambda *a:pytest.fail('Consumed reservation'))
        assert adapter.verify('2',(0,0,8,8))['reason']=='Verification budget exhausted'


def test_calibration_filters_overscan_off_lattice_and_unknown_actuals():
    from seed_search.realm.verification import calibrate_prediction
    class Predictor:
        def heights(self,points,step):
            assert points.tolist()==[[0,0],[2,0]]
            return np.array([80.,81.]),np.zeros(2)
    rows=[{'x':x,'z':z,'ground':{'y':80},'policy':'actual-column-v2','waterKnown':True,'waterDepth':0} for x,z in [(0,0),(2,0),(4,0),(1,0),(0,2)]]
    rows += [{'x':0,'z':1,'ground':{'y':900}}, {'x':2,'z':1,'ground':{'y':90},'policy':'actual-column-v2','waterKnown':True,'waterDepth':0,'error':'unloaded'}]
    observation={'bounds':[0,0,3,2],'spacing':2,'evidence':{'stable':True,'columns':rows}}
    result=calibrate_prediction(Predictor(),observation)
    assert result['sample_count']==2 and result['height_mae_blocks']==.5
    assert result['bounds']==[0,0,3,2]


def test_calibration_saved_mask_and_stability_authoritative():
    from seed_search.realm.verification import calibrate_prediction
    rows=[{'x':x,'z':0,'ground':{'y':80+x},'policy':'actual-column-v2','waterKnown':True,'waterDepth':0} for x in range(3)]
    a=VerificationAdapter({},runtime=lambda *args:{'stable':True,'columns':rows})
    observation=a.verify('1',(0,0,3,1),1)
    observation['raster']['known'][0][1]=False
    observation['raster']['height'][0][2]=99  # Conflict cannot replace saved evidence.
    class Predictor:
        def heights(self,points,step):
            assert points.tolist()==[[0,0]]
            return np.array([80.]),np.zeros(1)
    result=calibrate_prediction(Predictor(),observation)
    assert result['sample_count']==1 and result['excluded_actual_cell_count']==2
    observation['evidence']['stable']=False
    assert calibrate_prediction(None,observation)['status']=='UNSUPPORTED'
    observation['evidence'].pop('stable')
    assert calibrate_prediction(None,observation)['status']=='UNSUPPORTED'
    observation['evidence']['stable']=True
    observation['raster']['metadata'].pop('stable_sampled_observations')
    assert calibrate_prediction(None,observation)['status']=='UNSUPPORTED'


@pytest.mark.parametrize('missing',['bounds','spacing','stable'])
def test_raw_calibration_requires_explicit_lattice_and_stability(missing):
    from seed_search.realm.verification import calibrate_prediction
    observation={'bounds':[0,0,1,1],'spacing':1,'stable':True,
                 'columns':[{'x':0,'z':0,'ground':{'y':80},'policy':'actual-column-v2','waterKnown':True,'waterDepth':0}]}
    observation.pop(missing)
    assert calibrate_prediction(None,observation)['status']=='UNSUPPORTED'


def test_calibration_excludes_snapshot_unknowns_and_predictor_unknowns():
    from seed_search.realm.verification import calibrate_prediction
    class Predictor:
        def heights(self,points,step):
            return np.array([np.nan,63.,np.inf]),np.zeros(3)
    observation={'bounds':[0,0,3,1],'spacing':1,'stable':True,
                 'columns':[{'x':x,'z':0,'ground':{'y':80},'policy':'actual-column-v2','waterKnown':True,'waterDepth':1} for x in range(3)]}
    result=calibrate_prediction(Predictor(),observation)
    assert result['sample_count']==3 and result['known_prediction_count']==1
    assert result['actual_exposed_water_count']==1 and result['actual_exposed_water_sample_count']==3
    assert result['height_mae_blocks']==17 and result['water_proxy_mismatch_count']==0
    observation['saved_blocks']={'unknownCount':1}
    assert calibrate_prediction(None,observation)['status']=='UNSUPPORTED'


def test_interpretation_hashes_change_observation_identity(monkeypatch):
    from pathlib import Path
    from seed_search.realm.verification import tooling_identity
    identity=tooling_identity()
    assert set(identity)>={'verification.py','raster.py'}
    before=VerificationAdapter({},runtime=runtime).verify('1',(0,0,8,8))
    original=Path.read_bytes
    def changed(path):
        data=original(path)
        return data+b'\n# changed interpretation\n' if path.name=='raster.py' else data
    monkeypatch.setattr(Path,'read_bytes',changed)
    after=VerificationAdapter({},runtime=runtime).verify('1',(0,0,8,8))
    assert identity['raster.py']!=tooling_identity()['raster.py']
    assert before['id']!=after['id']


def test_saved_raster_only_requires_stable_evidence_and_keeps_known_mask():
    from seed_search.realm.verification import calibrate_prediction
    observation=VerificationAdapter({},runtime=runtime).verify('1',(0,0,8,8),4)
    observation['evidence'].pop('columns')
    observation['raster']['known'][0][0]=False
    class Predictor:
        def heights(self,points,step):
            assert points.tolist()==[[4,0],[0,4],[4,4]]
            return np.array([80.,80.,80.]),np.zeros(3)
    result=calibrate_prediction(Predictor(),observation)
    assert result['sample_count']==3 and result['excluded_actual_cell_count']==1
    observation['evidence']['complete_snapshot']=False
    assert calibrate_prediction(None,observation)['status']=='UNSUPPORTED'


def test_calibration_all_prediction_unknowns_keep_empty_metrics():
    from seed_search.realm.verification import calibrate_prediction
    class Predictor:
        def heights(self,points,step):
            return np.full(len(points),np.nan),np.zeros(len(points))
    observation={'bounds':[0,0,1,1],'spacing':1,'stable':True,
                 'columns':[{'x':0,'z':0,'ground':{'y':80},'policy':'actual-column-v2','waterKnown':True,'waterDepth':0}]}
    result=calibrate_prediction(Predictor(),observation)
    assert result['status']=='PARTIAL' and result['known_prediction_count']==0
    assert result['height_mae_blocks'] is None and result['height_max_absolute_error_blocks'] is None
    assert result['water_proxy_mismatch_count']==0 and result['actual_exposed_water_count']==0


def test_nether_verification_hard_floor_and_policy():
    cfg = {'structures': {'nether_minimum_counts': {'fortress': 1, 'bastion': 1}}}
    a = VerificationAdapter(cfg)
    evidence = {'seed': '1', 'bds_version': '1.26.52.3', 'dimension': 'nether', 'source': 'snap',
                'structures': {'fortress': [{'x': 0, 'y': 64, 'z': 0, 'actual': True}],
                               'bastion': [{'x': 0, 'y': 64, 'z': 0, 'actual': True}]}}
    # Resolve the current distinct hard floors (Fortress 1, Bastion 2), not a shared invented floor.
    r = a.verify_final_nether('1', (0, 0), evidence=evidence)
    assert r['status'] == 'PARTIAL'
    assert r['required_counts']['fortress'] == 1
    assert r['required_counts']['bastion'] >= 2


def test_guard_nested_none_dict_accesses():
    a = VerificationAdapter({'deployment': None, 'bds': {'verification_budget': 1}})
    # verify_candidate with None bounds
    candidate = {'seed': '42', 'stronghold': [0, 0], 'bounds': None, 'id': 'cand-1'}
    # bounds derived from center square without AttributeError
    r = a.verify_candidate(candidate, spacing=16)
    assert r is not None

    # final_nether_evidence with None structures
    r2 = final_nether_evidence('1', (0, 0), evidence={'seed': '1', 'bds_version': '1.26.52.3', 'dimension': 'nether', 'source': 's', 'structures': None})
    assert r2['status'] == 'PARTIAL'
