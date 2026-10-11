"""Bounded selected surface evidence: mocked provider only, no world generation."""
from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from seed_search.realm.verification import VerificationAdapter, BUILD
from seed_search.realm.store import RealmStore

SOURCE='official BDS '+BUILD+' Script API 2.10.0 Dimension.getBiome'
POLICY='one_cell_above_observed_exposed_support_or_water_including_snow_cover'

def row(x,z,name='minecraft:roofed_forest'):
    return {'x':x,'z':z,'ground':{'y':70},'waterTop':None,'waterDepth':0,'waterKnown':True,'policy':'actual-column-v2',
            'surfaceBiome':{'x':x,'z':z,'y':71,'name':name,'status':'OBSERVED','source':SOURCE,'queryPolicy':POLICY,'canopyRule':'ignore_filtered_vegetation'}}

def provider(seed,requests):
    return {'stable':True,'columns':[row(q['x0'],q['z0']) for q in requests]}

def test_point_canonicalization_one_world_single_attempt_and_existence_only():
    calls=[]
    def runtime(seed,requests):calls.append((seed,requests));return provider(seed,requests)
    adapter=VerificationAdapter({'bds':{'verification_budget':1}},runtime=runtime)
    points=[[20000000,-10000000],[-1,2],[-1,2]]
    result=adapter.verify_surface_points('-9223372036854775808',points,'manual',candidate_id='c',selection_probability=.5)
    assert result['requested_points']==[[-1,2],[20000000,-10000000]] and result['status']=='PARTIAL'
    assert result['operation']=='surface_points_v1' and result['source']=='actual' and result['actual']
    assert result['existence_only'] and not result['absence_verified'] and 'raster' not in result
    assert result['surface_biome_observed_cells']==2 and result['surface_biome_coverage_complete']
    assert result['selection_reason']=='manual' and result['selection_probability']==.5 and result['candidate_id']=='c'
    assert len(calls)==1 and adapter.used==1 and len(calls[0][1])==2
    assert all(q['side']==q['spacing']==1 for q in calls[0][1])
    assert not any(cell['natural_ground'] for cell in result['point_cells'])
    assert adapter.verify_surface_points(result['seed'],list(reversed(points))) is result
    assert adapter.get_cached_surface_points(result['seed'],points) is result


def test_cache_helpers_do_no_provider_work_or_reservation():
    adapter=VerificationAdapter({},runtime=lambda *args:pytest.fail('No generation'))
    key=adapter.observation_id_surface_points('0001',[[0,0],[1,1],[0,0]])
    assert key==adapter.observation_id_surface_points(1,[[1,1],[0,0]])
    assert key!=adapter.observation_id('1',(0,0,2,2),1)
    assert adapter.get_cached_surface_points('1',[[0,0],[1,1]]) is None and adapter.used==0
    adapter.identity={**adapter.identity,'script_api':'different'}
    assert key!=adapter.observation_id_surface_points('1',[[0,0],[1,1]])

@pytest.mark.parametrize('points',[[],[[True,0]],[[0.5,0]],[[0]],[[0,0,0]],'0,0',[[i,0] for i in range(17)]])
def test_invalid_points_before_provider_or_budget(points):
    adapter=VerificationAdapter({},runtime=lambda *args:pytest.fail('No generation'))
    with pytest.raises(ValueError):adapter.verify_surface_points('1',points)
    assert adapter.used==0

@pytest.mark.parametrize('seed',['9223372036854775808','-9223372036854775809','garbage'])
def test_full_signed_seed_validation(seed):
    adapter=VerificationAdapter({},runtime=lambda *args:pytest.fail('No generation'))
    with pytest.raises(ValueError):adapter.observation_id_surface_points(seed,[[0,0]])


def test_missing_unknown_overscan_and_off_point_rows_remain_honest():
    def runtime(seed,requests):
        bad=row(1,1);bad['waterKnown']=False
        return {'stable':True,'columns':[row(0,0),bad,row(2,2),row(999,999)]}
    result=VerificationAdapter({},runtime=runtime).verify_surface_points('1',[[0,0],[1,1],[3,3]])
    assert [r['status'] for r in result['surface_biome_observations']]==['OBSERVED','UNKNOWN_SURFACE','MISSING']
    assert result['surface_biome_observed_cells']==1 and result['surface_biome_missing_cells']==2
    assert not result['surface_biome_coverage_complete'] and not result['absence_verified']
    assert [(r['x'],r['z']) for r in result['surface_biome_observations']]==[(0,0),(1,1),(3,3)]


def test_saved_unknown_and_unstable_cells_never_qualify_names():
    for extra in ({'stable':False},{'stable':True,'saved_blocks':{'unknownCount':1}}, {'stable':True,'complete_snapshot':False}):
        result=VerificationAdapter({},runtime=lambda *args:{'columns':[row(0,0)],**extra}).verify_surface_points('1',[[0,0]])
        assert result['surface_biome_observed_cells']==0
        assert result['surface_biome_observations'][0]['status']=='UNSTABLE_OR_UNKNOWN_CELL'


def test_points_and_rectangle_share_verification_budget():
    adapter=VerificationAdapter({'bds':{'verification_budget':1}},runtime=provider)
    assert adapter.verify('1',(0,0,1,1),1)['attempt']==1
    denied=adapter.verify_surface_points('1',[[1,1]])
    assert denied['reason']=='Verification budget exhausted' and denied['requested_points']==[[1,1]]
    assert not denied['actual'] and denied['surface_biome_observations']==[]


def test_bounded_configuration_and_disabled_preserve_request_without_attempt():
    for options,points in [({'enabled':False},[[0,0]]),({'max_tiles_per_request':1},[[0,0],[1,1]])]:
        adapter=VerificationAdapter({'bds':options},runtime=lambda *args:pytest.fail('No generation'))
        result=adapter.verify_surface_points('1',points)
        assert result['requested_points']==points and not result['actual'] and adapter.used==0


def test_persisted_cache_failure_journal_explicit_retry_and_baseline_untouched(tmp_path):
    def failed(*args):raise RuntimeError('provider unavailable')
    with RealmStore(tmp_path,{}) as store:
        store.set_state('baseline_control',{'qualification':'PREDICTED','score':123})
        with store.db:
            store.db.execute('INSERT INTO candidates(id,idx,seed,qualification,result) VALUES (?,?,?,?,?)',
                             ('candidate','00000000000000000000','1','PREDICTED',json.dumps({'score':123})))
        adapter=VerificationAdapter({'bds':{'verification_budget':2}},store,runtime=failed)
        result=adapter.verify_surface_points('1',[[0,0]],candidate_id='candidate')
        key=result['id']
        assert result['status']=='FAILED' and result['seed_eligibility']=='UNKNOWN' and result['attempt']==1
        assert store.get_observation(key+':attempt:1')['error']['message']=='provider unavailable'
        json.dumps(result,allow_nan=False)
    with RealmStore(tmp_path,resume=True) as store:
        adapter=VerificationAdapter({'bds':{'verification_budget':2}},store,runtime=provider)
        assert adapter.get_cached_surface_points('1',[[0,0]])['status']=='FAILED'
        assert adapter.verify_surface_points('1',[[0,0]])['attempt']==1 and store.get_state('bds_verification_used')==1
        success=adapter.verify_surface_points('1',[[0,0]],candidate_id='candidate',retry_failed=True)
        assert success['status']=='PARTIAL' and success['attempt']==2 and store.get_state('bds_verification_used')==2
        assert store.get_observation(key+':attempt:1')['status']=='FAILED'
        assert store.get_state('baseline_control')=={'qualification':'PREDICTED','score':123}
        assert store.db.execute('SELECT qualification,result FROM candidates WHERE id=?',('candidate',)).fetchone()==('PREDICTED',json.dumps({'score':123}))


def test_concurrent_surface_requests_respect_shared_atomic_budget():
    adapter=VerificationAdapter({'bds':{'verification_budget':2}},runtime=provider)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results=list(executor.map(lambda i:adapter.verify_surface_points(str(i),[[i,i]]),range(1,5)))
    assert sorted(r['attempt'] for r in results if 'attempt' in r)==[1,2] and adapter.used==2
    assert sum(r.get('actual',False) for r in results)==2


def test_interruption_consumes_reserved_attempt_without_false_failed_cache():
    def interrupted(*args):raise KeyboardInterrupt()
    adapter=VerificationAdapter({'bds':{'verification_budget':1}},runtime=interrupted)
    with pytest.raises(KeyboardInterrupt):adapter.verify_surface_points('1',[[0,0]])
    assert adapter.used==1 and adapter.get_cached_surface_points('1',[[0,0]]) is None


def test_fixture_evidence_rejected_and_failed_attempt_recorded():
    for raw in ({'stable':True,'evidenceRole':'controlled_fixture','columns':[row(0,0)]},
                {'stable':True,'columns':[{**row(0,0),'evidenceRole':'controlled_fixture'}]}):
        result=VerificationAdapter({},runtime=lambda *args:raw).verify_surface_points('1',[[0,0]])
        assert result['status']=='FAILED' and not result['actual'] and result['seed_eligibility']=='UNKNOWN'
