"""Pinned semantic confirmation and restart fault paths use mocks only."""
import copy
import json
from types import SimpleNamespace
import pytest
from seed_search.realm import verification as v
from seed_search.realm.bds_tools import probe_tools as p,poc_control as control


def mismatch(block='minecraft:dirt',expected=None,saved=None,logged=False,overlay=False):
    expected={'dirt_type':'normal'} if expected is None else expected
    saved={} if saved is None else saved
    names=[block,'minecraft:water' if overlay else 'minecraft:air']
    return {'probe':{'x':0,'y':70,'z':0,'block':block,'states':expected,'waterlogged':logged},
            'savedLayers':names,'savedEntries':[{'name':block,'states':saved,'statesError':None},{'name':names[1],'states':{},'statesError':None}]}

@pytest.fixture
def runtime(tmp_path,monkeypatch):
    state={'startup_error':None,'request_error':None,'cleanup_error':None,'clean':True,'possible_live':False,
           'resolver':lambda request:{'block':request['block'],'states':{'dirt_type':'normal'}},'source':v.SEMANTIC_SOURCE,'status':'RESOLVED','error':None}
    calls=[]
    monkeypatch.setattr(v,'CLEANUP_GUARD',tmp_path/'guard.json')
    monkeypatch.setattr(control,'container_state',lambda name:{'stopped':True,'exit_code':0})
    class Console:
        start_seconds=.2
        def __init__(self,name,label):
            calls.append(('start',name,label))
            assert v.CLEANUP_GUARD.exists()
            if state['startup_error']:raise state['startup_error']
        def request(self,action,q,timeout):
            calls.append(('request',action,q,timeout))
            assert action=='permutations_resolve' and timeout==30 and len(q['permutations'])<=8
            if state['request_error']:raise state['request_error']
            return {'id':q['id'],'source':state['source'],'results':[
                {'requested':request,'resolved':state['resolver'](request),'status':state['status'],'error':state['error']} for request in q['permutations']]}
    monkeypatch.setattr(p,'Probe',Console)
    def cleanup(name,console):
        calls.append(('cleanup',name))
        if state['cleanup_error']:raise state['cleanup_error']
        return {'clean_shutdown':state['clean'],'stopped':not state['possible_live'],'removed':False,'exit_code':0}
    monkeypatch.setattr(control,'cleanup_container',cleanup)
    adapter=v.VerificationAdapter({'bds':{'persist_snapshot':True}})
    def confirm(mismatches,unknown=0):
        saved={'mismatches':copy.deepcopy(mismatches),'unknownCount':unknown,'matches':5}
        report={'name':'same-container','saved_blocks':saved}
        adapter._confirm_saved_block_semantics('same-container',[{'x0':0,'z0':0}],saved,tmp_path,report,tmp_path/'stopped-copy')
        return saved
    return state,calls,adapter,confirm,tmp_path


def test_exact_full_runtime_equivalence_preserves_raw_mismatches_and_deduplicates(runtime):
    state,calls,adapter,confirm,tmp_path=runtime
    original=[mismatch(),mismatch()];saved=confirm(original)
    assert saved['mismatches']==original and saved['matches']==5
    assert saved['semantic_match_count']==2 and saved['unresolved_mismatch_count']==0
    assert v.saved_blocks_consistent(saved)
    proof=saved['semantic_validation']
    assert [case['mismatch_index'] for case in proof['cases']]==[0,1]
    assert proof['identity']==adapter.identity and proof['source']==v.SEMANTIC_SOURCE
    assert len([c for c in calls if c[0]=='request'])==1
    assert len([c for c in calls if c[0]=='request'][0][2]['permutations'])==1
    assert not v.CLEANUP_GUARD.exists() and (tmp_path/'same-container-results.json').exists()

@pytest.mark.parametrize('resolved',[{'block':'minecraft:stone','states':{'dirt_type':'normal'}},
    {'block':'minecraft:dirt','states':{'dirt_type':'wrong'}}, {'block':'minecraft:dirt','states':{}},
    {'block':'minecraft:dirt','states':{'dirt_type':'normal','extra':False}}])
def test_wrong_type_wrong_state_missing_or_extra_state_never_proven(runtime,resolved):
    state,calls,adapter,confirm,tmp_path=runtime;state['resolver']=lambda request:resolved
    saved=confirm([mismatch()])
    assert saved['semantic_match_count']==0 and saved['unresolved_mismatch_count']==1
    assert not v.saved_blocks_consistent(saved)


def test_overlay_or_primary_mismatch_cannot_be_repaired_by_state_resolution(runtime):
    state,calls,adapter,confirm,tmp_path=runtime
    wrong_primary=mismatch();wrong_primary['savedLayers'][0]='minecraft:stone';wrong_primary['savedEntries'][0]['name']='minecraft:stone'
    saved=confirm([mismatch(logged=False,overlay=True),wrong_primary])
    assert not calls and saved['unresolved_mismatch_count']==2 and not v.saved_blocks_consistent(saved)

@pytest.mark.parametrize('field,value',[('states',None),('waterlogged',None)])
def test_unsupported_or_missing_api_evidence_remains_unresolved(runtime,field,value):
    state,calls,adapter,confirm,tmp_path=runtime
    bad=mismatch();bad['probe'][field]=value
    saved=confirm([bad]);assert not calls and not v.saved_blocks_consistent(saved)


def test_mixed_cases_and_unknowns_keep_unresolved_geometry(runtime):
    state,calls,adapter,confirm,tmp_path=runtime
    saved=confirm([mismatch(),mismatch(logged=True,overlay=False)],unknown=1)
    assert saved['semantic_match_count']==1 and saved['unresolved_mismatch_count']==1
    assert saved['unknownCount']==1 and not v.saved_blocks_consistent(saved)
    only_unknown=confirm([mismatch()],unknown=1)
    assert only_unknown['semantic_match_count']==1 and not v.saved_blocks_consistent(only_unknown)

@pytest.mark.parametrize('field,value',[('source','wrong runtime'),('status','FAILED'),('error','unsupported palette')])
def test_unsupported_runtime_or_wrong_source_never_proven(runtime,field,value):
    state,calls,adapter,confirm,tmp_path=runtime;state[field]=value
    saved=confirm([mismatch()]);assert saved['unresolved_mismatch_count']==1 and not v.saved_blocks_consistent(saved)


def test_resolved_boolean_and_integer_are_not_equal_by_coercion(runtime):
    state,calls,adapter,confirm,tmp_path=runtime
    state['resolver']=lambda request:{'block':'minecraft:dirt','states':{'flag':1}}
    saved=confirm([mismatch(expected={'flag':True})]);assert not v.saved_blocks_consistent(saved)

@pytest.mark.parametrize('field',[('identity','bds_version'),('identity','image_id'),('identity','script_api'),
    ('identity','tools_sha256'),('','source'),('','same_container_restart'),('','snapshot_copied_before_restart')])
def test_provenance_tampering_invalidates_consistency(runtime,field):
    state,calls,adapter,confirm,tmp_path=runtime;saved=confirm([mismatch()]);proof=saved['semantic_validation']
    container,key=field;target=proof[container] if container else proof;target[key]='wrong'
    assert not v.saved_blocks_consistent(saved)


def test_empty_unresolved_claim_without_per_case_proof_is_not_trusted():
    saved={'mismatches':[mismatch()],'unknownCount':0,'unresolved_mismatch_count':0,'unresolved_mismatches':[]}
    assert not v.saved_blocks_consistent(saved)

@pytest.mark.parametrize('location',['startup_error','request_error'])
def test_restart_or_resolver_fault_preserves_primary_and_runs_cleanup(runtime,location):
    state,calls,adapter,confirm,tmp_path=runtime;error=TimeoutError('primary semantic fault');state[location]=error
    with pytest.raises(TimeoutError) as caught:confirm([mismatch()])
    assert caught.value is error and ('cleanup','same-container') in calls and not v.CLEANUP_GUARD.exists()
    report=json.loads((tmp_path/'same-container-results.json').read_text())
    assert report['saved_blocks']['semantic_validation']['error']['message']=='primary semantic fault'


def test_failed_cleanup_retains_guard_and_does_not_mask_original_fault(runtime):
    state,calls,adapter,confirm,tmp_path=runtime
    error=RuntimeError('primary resolver');state.update(request_error=error,clean=False,possible_live=True)
    with pytest.raises(RuntimeError) as caught:confirm([mismatch()])
    assert caught.value is error and v.CLEANUP_GUARD.exists()
    saved=json.loads((tmp_path/'same-container-results.json').read_text())['saved_blocks']
    assert not v.saved_blocks_consistent(saved)


def test_clean_responses_with_unclean_stop_still_fail_and_persist(runtime):
    state,calls,adapter,confirm,tmp_path=runtime;state['clean']=False
    with pytest.raises(RuntimeError,match='Clean stopped semantic'):confirm([mismatch()])
    saved=json.loads((tmp_path/'same-container-results.json').read_text())['saved_blocks']
    assert not v.saved_blocks_consistent(saved)


def test_restart_interrupt_consumes_no_new_reservation_and_cleans(runtime):
    state,calls,adapter,confirm,tmp_path=runtime;state['request_error']=KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):confirm([mismatch()])
    assert adapter.used==0 and ('cleanup','same-container') in calls


def test_semantic_batches_and_overflow_are_bounded(runtime):
    state,calls,adapter,confirm,tmp_path=runtime
    state['resolver']=lambda request:request
    originals=[mismatch(expected={'value':i},saved={'value':i}) for i in range(65)]
    saved=confirm(originals)
    assert len([call for call in calls if call[0]=='request'])==8
    assert saved['semantic_match_count']==64 and saved['unresolved_mismatch_count']==1
    assert not v.saved_blocks_consistent(saved)


def test_raster_accepts_proven_states_only_and_retains_natural_gate(runtime):
    state,calls,adapter,confirm,tmp_path=runtime;saved=confirm([mismatch()])
    column={'x':0,'z':0,'ground':{'y':70},'waterDepth':0,'waterKnown':True,'policy':'actual-column-v2'}
    r=v.raster_from_columns((0,0,1,1),1,[column],{'stable':True,'complete_snapshot':True,'saved_blocks':saved})
    assert r.known[0,0] and not r.natural_ground[0,0]
    saved['unknownCount']=1
    r=v.raster_from_columns((0,0,1,1),1,[column],{'stable':True,'saved_blocks':saved})
    assert not r.known[0,0]

# Reuse the existing Docker fault harness, including authoritative stopped checks.
from test_realm_bds_cleanup import environment


def test_extract_restarts_same_container_only_after_stopped_snapshot_and_uses_one_attempt(environment,monkeypatch):
    state,calls,snapshots,adapter,read_report=environment
    adapter.identity['persist_snapshot']=True
    adapter.options['persist_snapshot']=True
    original_docker=control.docker;original_console=p.Probe;original_snapshot=p.snapshot
    stages=[];starts=[]
    class Console(original_console):
        def __init__(self,name,label):
            stages.append('start');starts.append(name);state['running']=True
            super().__init__(name,label)
        def request(self,action,q,**kwargs):
            if action=='dirty':return {'failed':0}
            if action=='check_sky':return {'nonAir':0}
            if action=='permutations_resolve':
                assert stages.index('snapshot')<len(stages)-1
                return {'id':q['id'],'source':v.SEMANTIC_SOURCE,'results':[{'requested':request,
                    'resolved':{'block':request['block'],'states':{'dirt_type':'normal'}},'status':'RESOLVED','error':None} for request in q['permutations']]}
            return super().request(action,q)
        def rows(self,q):return [{'x':0,'z':0,'ground':{'y':70},'waterDepth':0,'waterKnown':True,'policy':'actual-column-v2'}]
    monkeypatch.setattr(p,'Probe',Console)
    def snapshot(*args):
        stages.append('snapshot');assert not state['running'];return original_snapshot(*args)
    monkeypatch.setattr(p,'snapshot',snapshot)
    def docker(*args,**kwargs):
        if args[0]=='run' and '/bin/df' not in args:
            assert stages==['start','snapshot']
            return SimpleNamespace(stdout=json.dumps({'mismatches':[mismatch()],'unknownCount':0,'matches':0}))
        return original_docker(*args,**kwargs)
    monkeypatch.setattr(control,'docker',docker)
    result=adapter.verify('1',(0,0,1,1),1)
    assert result['status']=='PARTIAL' and result['raster']['known']==[[True]]
    assert adapter.used==1 and result['attempt']==1 and starts[0]==starts[1]
    assert stages==['start','snapshot','start'] and len(snapshots)==1 and not state['running']
    report=read_report()
    assert report['saved_blocks']['mismatches'] and report['saved_blocks']['semantic_match_count']==1
    assert report['saved_blocks']['semantic_validation']['restart_cleanup']['clean_shutdown']
