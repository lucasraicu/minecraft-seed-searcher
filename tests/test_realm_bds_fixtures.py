"""Deterministic fixture mutation/restore and surface API controls; no server."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from test_realm_actual_columns import evaluate, block
from seed_search.realm.verification import raster_from_columns, tooling_identity
from seed_search.realm.bds_tools import probe_tools

TOOLS=Path(__file__).parents[1]/'src/seed_search/realm/bds_tools'
FIXTURE=(TOOLS/'fixture_policy.js').read_text().replace('export ','')
Q={'id':'fixture','x0':0,'z0':0,'side':32,'spacing':1,'disposableWorld':True}
MOCK='''
const resolve=(block,states)=>({block,type:{id:block},states:states||{},getAllStates:()=>states||{}});
function mockWorld(options={}) {
  const cells=new Map();let writes=0;
  const key=p=>`${p.x},${p.y},${p.z}`;
  const getBlock=p=>{
    if(!cells.has(key(p))) cells.set(key(p),{typeId:'minecraft:air',states:{},isWaterlogged:false,
      get permutation(){return {getAllStates:()=>this.states};},
      setPermutation(perm){writes++;if(writes===options.failWrite)throw new Error('injected write failure');
        if(options.failRestore && perm.block==='minecraft:air')throw new Error('restore failure');
        this.typeId=options.airBecomesWaterIfLogged && perm.block==='minecraft:air' && this.isWaterlogged?'minecraft:water':options.canonicalizeFlowing && perm.block==='minecraft:flowing_water'?'minecraft:water':perm.block;this.states=perm.states;this.isWaterlogged=false;},
      setWaterlogged(value){this.isWaterlogged=options.ignoreWaterlogging?false:value;}});
    return cells.get(key(p));
  };
  return {getBlock,cells,writes:()=>writes};
}
'''

def fixture(expression):
    return evaluate(result_expression=expression,extra_source=FIXTURE+MOCK+'\nconst q='+json.dumps(Q)+';')

def test_bounded_positive_cases_exact_journal_and_restart_restore():
    result=fixture('''(()=>{const world=mockWorld();const created=createFixtures(q,world.getBlock,resolve);
      const persisted=JSON.parse(JSON.stringify(created.journal));
      const restored=restoreFixtureJournal(q,persisted,world.getBlock,resolve);
      return {cases:created.cases.map(c=>c.label),cells:created.mutatedCells,expected:persisted.expectedCells,
        positive:persisted.mutations.filter(p=>p.observed.waterlogged).length,
        bounded:persisted.mutations.every(p=>p.x>=0&&p.x<32&&p.z>=0&&p.z<32&&p.y>=300&&p.y<=308),
        restored:restored.restoredCells,errors:restored.errors,
        allDryAir:[...world.cells.values()].every(b=>b.typeId==='minecraft:air'&&b.isWaterlogged===false)};})()''')
    assert result['cases']==['primary_water','flowing_water','waterlogged_plant','waterlogged_solid','thin_snow','solid_snow','powder_snow','ice_over_water','elevated_lake']
    assert result['positive']==2 and result['bounded'] and result['allDryAir']
    assert result['cells']==result['expected']==result['restored'] and not result['errors']

def test_non_air_preflight_and_missing_disposable_authorization_never_mutate():
    result=fixture('''(()=>{const world=mockWorld();const p=fixturePlan(q).mutations[30];world.getBlock(p).typeId='minecraft:stone';
      let error;try{createFixtures(q,world.getBlock,resolve);}catch(e){error=String(e);}
      let permissionError;try{fixturePlan({...q,disposableWorld:false});}catch(e){permissionError=String(e);}
      return {writes:world.writes(),error,permissionError};})()''')
    assert result['writes']==0 and 'preflight' in result['error'] and 'disposableWorld' in result['permissionError']

@pytest.mark.parametrize('options',[{'failWrite':20},{'ignoreWaterlogging':True}])
def test_setup_failure_rolls_back_every_original_cell(options):
    result=fixture('''(()=>{const world=mockWorld('''+json.dumps(options)+''');try{createFixtures(q,world.getBlock,resolve);}catch(e){return {
      status:e.fixtureReport.restoration.status,restored:e.fixtureReport.restoration.restoredCells,
      expected:e.fixtureReport.journal.expectedCells,allDryAir:[...world.cells.values()].every(b=>b.typeId==='minecraft:air'&&!b.isWaterlogged)};}})()''')
    assert result['status']=='RESTORED_SUBSET' and result['restored']==result['expected'] and result['allDryAir']

def test_restoration_failure_reports_diagnostics_not_success():
    result=fixture('''(()=>{const world=mockWorld({failRestore:true});const created=createFixtures(q,world.getBlock,resolve);
      const report=restoreFixtureJournal(q,created.journal,world.getBlock,resolve);return {status:report.status,errors:report.errors.length,restored:report.restoredCells};})()''')
    assert result['status']=='FAILED' and result['errors']>0 and result['restored']==0

def test_supplied_journal_rejects_tampered_target_before_writes():
    result=fixture('''(()=>{const world=mockWorld();const created=createFixtures(q,world.getBlock,resolve);const before=world.writes();
      created.journal.mutations[0].x=1000;let error;try{restoreFixtureJournal(q,created.journal,world.getBlock,resolve);}catch(e){error=String(e);}
      return {before,after:world.writes(),error};})()''')
    assert result['before']==result['after'] and 'unique planned original air' in result['error']

@pytest.mark.parametrize('surface,expected',[({'ground':{'y':60},'waterTop':100,'cover':[],'waterKnown':True},101),
    ({'ground':{'y':70},'waterTop':None,'cover':[{'y':71}],'waterKnown':True},72),
    ({'ground':{'y':70},'top':{'y':110},'waterTop':None,'cover':[],'waterKnown':True},71)])
def test_surface_query_uses_exposed_water_or_support_with_declared_canopy_rule(surface,expected):
    expression='observeSurfaceBiome('+json.dumps(surface)+",1,2,pos=>({id:'minecraft:roofed_forest'}))"
    result=evaluate(result_expression=expression)
    assert result['y']==expected and result['status']=='OBSERVED' and result['name']=='minecraft:roofed_forest'
    assert result['canopyRule']=='ignore_filtered_vegetation'

@pytest.mark.parametrize('surface,status',[({'ground':{'y':319},'waterKnown':True},'OUT_OF_RANGE'),
    ({'ground':{'y':70},'waterKnown':False},'UNKNOWN_SURFACE')])
def test_unqueryable_surface_does_not_call_biome_api(surface,status):
    result=evaluate(result_expression='observeSurfaceBiome('+json.dumps(surface)+",1,2,()=>{throw new Error('must not query');})")
    assert result['status']==status and result['error'] is None

@pytest.mark.parametrize('getter,status',[("()=>({id:123})",'INVALID_NAME'),("()=>{throw new Error('unloaded');}",'QUERY_FAILED')])
def test_surface_invalid_names_and_query_failures_are_explicit(getter,status):
    result=evaluate(result_expression="observeSurfaceBiome({ground:{y:70},waterKnown:true},1,2,"+getter+")")
    assert result['status']==status and result['name'] is None

@pytest.mark.parametrize('api,status',[("{}",'UNSUPPORTED'),("{BiomeTypes:{getAll(){return [{id:'minecraft:cold_taiga'},{id:'minecraft:roofed_forest'}];}}}",'OBSERVED'),("{BiomeTypes:{getAll(){throw new Error('missing');}}}",'QUERY_FAILED')])
def test_registry_feature_detection_does_not_require_named_import(api,status):
    result=evaluate(result_expression='observeBiomeRegistry('+api+')')
    assert result['status']==status
    if status=='OBSERVED':assert result['names']==['minecraft:cold_taiga','minecraft:roofed_forest']


def actual_row(x=0,z=0):
    surface={'x':x,'z':z,'y':71,'name':'minecraft:roofed_forest','status':'OBSERVED',
        'source':'official BDS 1.26.52.3 Script API 2.10.0 Dimension.getBiome',
        'queryPolicy':'one_cell_above_observed_exposed_support_or_water_including_snow_cover','canopyRule':'ignore_filtered_vegetation'}
    return {'x':x,'z':z,'ground':{'y':70},'waterTop':None,'waterDepth':0,'waterKnown':True,'policy':'actual-column-v2','surfaceBiome':surface}


def test_raster_persists_surface_strings_lattice_coverage_and_mapping_provenance():
    r=raster_from_columns((0,0,2,1),1,[actual_row(),actual_row(2)],{'stable':True})
    m=r.metadata
    assert r.biomes is None and m['surface_biome_observed_cells']==1 and m['surface_biome_expected_cells']==2
    assert m['surface_biome_missing_cells']==1 and not m['surface_biome_coverage_complete']
    assert m['surface_biome_observations'][0]['name']=='minecraft:roofed_forest'
    assert m['surface_biome_observations'][1]['status']=='MISSING'
    assert m['surface_biome_mapping_provenance']=='unmapped_names_no_native_numeric_ids'

@pytest.mark.parametrize('alteration',[{'y':61},{'queryPolicy':'underwater_ground'},{'name':3}])
def test_invalid_surface_evidence_cannot_supply_biome_coverage(alteration):
    row=actual_row();row['surfaceBiome'].update(alteration)
    r=raster_from_columns((0,0,1,1),1,[row],{'stable':True})
    assert r.metadata['surface_biome_observed_cells']==0


def test_unstable_biomes_are_retained_but_not_observed_coverage():
    r=raster_from_columns((0,0,1,1),1,[actual_row()],{'stable':False})
    assert r.metadata['surface_biome_observations'][0]['name']=='minecraft:roofed_forest'
    assert r.metadata['surface_biome_observations'][0]['status']=='UNSTABLE_OR_UNKNOWN_CELL'
    assert not r.metadata['surface_biome_coverage_complete']


def test_fixture_rows_rejected_from_natural_raster():
    with pytest.raises(ValueError,match='Controlled fixture'):
        raster_from_columns((0,0,1,1),1,[{**actual_row(),'evidenceRole':'controlled_fixture'}],{'stable':True})


def test_fixture_policy_bundled_and_hashed(tmp_path,monkeypatch):
    monkeypatch.setattr(probe_tools,'ROOT',tmp_path)
    monkeypatch.setattr(probe_tools,'docker',lambda *args,**kwargs:SimpleNamespace(stdout=''))
    probe_tools.create('fixture','1')
    assert (tmp_path/'fixture-pack/scripts/fixture_policy.js').read_bytes()==(TOOLS/'fixture_policy.js').read_bytes()
    assert 'fixture_policy.js' in tooling_identity()


def test_python_restore_chunks_are_bounded_and_failures_cannot_claim_success():
    p=probe_tools.Probe.__new__(probe_tools.Probe);calls=[]
    def request(action,q):
        calls.append(q)
        if len(calls)==2:raise TimeoutError('injected')
        return {'restoredCells':len(q['journal']['mutations']),'errors':[]}
    p.request=request
    mutations=[{'x':i,'y':300,'z':0,'original':{'block':'minecraft:air','states':{},'waterlogged':False}} for i in range(14)]
    journal={'policy':'disposable-column-fixtures-v1','x0':0,'z0':0,'expectedCells':14,'mutations':mutations}
    report=p.restore_fixtures(Q,journal)
    assert len(calls)==3 and all(len(json.dumps(q))<2048 for q in calls)
    assert report['status']=='FAILED' and report['restoredCells']==8 and report['requestErrors']
    with pytest.raises(ValueError,match='Complete'):
        p.restore_fixtures(Q,{**journal,'expectedCells':15})


def load_reader_helpers():
    script=TOOLS/'compare_saved_blocks.py';tree=ast.parse(script.read_text())
    names={'palette_entry','states_match'}
    scope={};exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),str(script),'exec'),scope)
    return scope


def test_saved_states_match_or_explicit_unknown():
    match=load_reader_helpers()['states_match']
    assert match({'liquid_depth':3},{'liquid_depth':3}) is True
    assert match({'liquid_depth':3},{'liquid_depth':0}) is False
    assert match(None,{}) is None and match({},None) is None


def test_palette_state_unsupported_tags_are_unknown():
    parse=load_reader_helpers()['palette_entry']
    IntTag=type('IntTag',(),{});value=IntTag();value.py_int=3
    name=SimpleNamespace(py_str='minecraft:flowing_water')
    result=parse(SimpleNamespace(compound={'name':name,'states':{'liquid_depth':value}}))
    assert result['states']=={'liquid_depth':3} and result['statesError'] is None
    result=parse(SimpleNamespace(compound={'name':name,'states':{'liquid_depth':object()}}))
    assert result['states'] is None and 'Unsupported state tag' in result['statesError']


def test_fixture_journal_request_reassembles_batches_without_runtime():
    import queue
    p=probe_tools.Probe.__new__(probe_tools.Probe)
    entry={'x':0,'y':300,'z':0,'original':{'block':'minecraft:air','states':{},'waterlogged':False}}
    batch='PROBE_FIXTURE_JOURNAL '+json.dumps({'id':'fixture','batch':0,'mutations':[entry]})
    final='PROBE_FIXTURE_CREATED '+json.dumps({'id':'fixture','journal':{'expectedCells':1}})
    p.lines=[batch,final];p.events=queue.Queue();p.events.put(batch);p.events.put(final)
    p.command=lambda command:None
    result=p.request('fixtures_create',Q)
    assert result['journal']['mutations']==[entry]


def test_main_module_syntax_and_registration_without_minecraft_runtime():
    # Strip module imports and provide registration-only mocks; compile the actual script.
    source=(TOOLS/'main.js').read_text()
    source='\n'.join(line for line in source.splitlines() if not line.startswith('import '))
    mock="const world={afterEvents:{worldLoad:{subscribe(){}}}};const system={afterEvents:{scriptEventReceive:{subscribe(){}}}};"
    assert evaluate(extra_source=FIXTURE+mock+source,result_expression="typeof column==='function'") is True


def test_unsupported_pinned_id_or_state_is_preflight_failure_without_writes():
    result=fixture("""(()=>{const world=mockWorld();try{createFixtures(q,world.getBlock,(id,states)=>{
      if(id==='minecraft:oak_slab')throw new Error('unsupported pinned identifier');return resolve(id,states);});}
      catch(e){return {writes:world.writes(),phase:e.fixtureReport.phase,requested:e.fixtureReport.requestedPermutation,
        restoration:e.fixtureReport.restoration.status,partialJournal:e.fixtureReport.journal.mutations.length};}})()""")
    assert result['writes']==0 and result['phase']=='PREFLIGHT'
    assert result['requested']['block']=='minecraft:oak_slab' and result['restoration']=='NOT_NEEDED'
    assert result['partialJournal']>0


def test_failed_request_attaches_complete_bounded_rollback_artifact():
    import queue
    entry={'x':0,'y':300,'z':0,'original':{'block':'minecraft:air','states':{},'waterlogged':False}}
    result={'x':0,'y':300,'z':0,'restored':False,'error':'restore failed'}
    lines=[
        'PROBE_FIXTURE_JOURNAL '+json.dumps({'id':'fixture','batch':0,'mutations':[entry]}),
        'PROBE_FIXTURE_ROLLBACK '+json.dumps({'id':'fixture','batch':0,'results':[result]}),
        'PROBE_FIXTURE_REPORT '+json.dumps({'id':'fixture','status':'FAILED','phase':'MUTATION','journal':{'expectedCells':1},'restoration':{'status':'FAILED','errors':[],'errorCount':1}}),
        'PROBE_FAILED '+json.dumps({'id':'fixture','error':'setter failed','fixtureReportAvailable':True}),
    ]
    p=probe_tools.Probe.__new__(probe_tools.Probe);p.lines=lines;p.events=queue.Queue()
    for line in lines:p.events.put(line)
    p.command=lambda command:None
    with pytest.raises(probe_tools.FixtureRequestError,match='setter failed') as error:
        p.request('fixtures_create',Q)
    report=error.value.fixture_report
    assert report['phase']=='MUTATION' and report['journal']['complete']
    assert report['journal']['mutations']==[entry] and report['restoration']['errors']==[result]


def test_real_main_failure_emits_bounded_report_before_error_marker():
    source='\n'.join(line for line in (TOOLS/'main.js').read_text().splitlines() if not line.startswith('import '))
    mock="""let handler;const emitted=[];const console={warn:line=>emitted.push(line)};
    const world={afterEvents:{worldLoad:{subscribe(){}}}};
    const system={afterEvents:{scriptEventReceive:{subscribe(callback){handler=callback;}}}};
    const BlockPermutation={resolve(id,states){if(id==='minecraft:flowing_water')throw new Error('unsupported flowing id');return resolve(id,states);}};
    """
    expression="""(()=>{const worldFixture=mockWorld();dim={getBlock:worldFixture.getBlock};handler({id:'bds_probe:fixtures_create',message:JSON.stringify(q)});
      return {writes:worldFixture.writes(),report:emitted.find(line=>line.startsWith('PROBE_FIXTURE_REPORT ')),failed:emitted.at(-1)};})()"""
    result=evaluate(extra_source=FIXTURE+MOCK+mock+source+'\nconst q='+json.dumps(Q)+';',result_expression=expression)
    assert result['writes']==0
    assert json.loads(result['report'].split(' ',1)[1])['phase']=='PREFLIGHT'
    assert json.loads(result['failed'].split(' ',1)[1])['fixtureReportAvailable'] is True


def test_resolved_fluid_identity_preserves_requested_id_and_exact_state():
    result=fixture("""(()=>{const world=mockWorld();const created=createFixtures(q,world.getBlock,(id,states)=>
      resolve(id==='minecraft:flowing_water'?'minecraft:water':id,states));
      const cell=created.journal.mutations.find(p=>p.block==='minecraft:flowing_water');
      return {status:created.status,requested:cell.block,resolved:cell.resolvedBlock,observed:cell.observed.block,
        requestedStates:cell.states,resolvedStates:cell.resolvedStates,observedStates:cell.observed.states};})()""")
    assert result['status']=='CREATED' and result['requested']=='minecraft:flowing_water'
    assert result['resolved']==result['observed']=='minecraft:water'
    assert result['requestedStates']==result['resolvedStates']==result['observedStates']=={'liquid_depth':3}


def test_mutation_failure_captures_current_target_not_last_preflight_target():
    result=fixture("""(()=>{const world=mockWorld({ignoreWaterlogging:true});try{createFixtures(q,world.getBlock,(id,states)=>
      resolve(id==='minecraft:flowing_water'?'minecraft:water':id,states));}
      catch(error){return {target:error.fixtureReport.requestedPermutation,phase:error.fixtureReport.phase,restoration:error.fixtureReport.restoration.status};}})()""")
    assert result['phase']=='MUTATION' and result['target']['block']=='minecraft:seagrass'
    assert result['target']['resolvedBlock']=='minecraft:seagrass' and result['target']['index']>0
    assert result['restoration']=='RESTORED_SUBSET'


def test_canonical_fluid_id_does_not_weaken_requested_state_assertion():
    result=fixture("""(()=>{const world=mockWorld();try{createFixtures(q,world.getBlock,(id,states)=>
      resolve(id==='minecraft:flowing_water'?'minecraft:water':id,id==='minecraft:flowing_water'?{liquid_depth:0}:states));}
      catch(error){return {target:error.fixtureReport.requestedPermutation,status:error.fixtureReport.status,restoration:error.fixtureReport.restoration.status};}})()""")
    assert result['status']=='FAILED' and result['target']['block']=='minecraft:flowing_water'
    assert result['target']['states']=={'liquid_depth':3} and result['restoration']=='RESTORED_SUBSET'


def test_pinned_flowing_water_setter_normalization_is_narrow_and_recorded():
    result=fixture("""(()=>{const world=mockWorld({canonicalizeFlowing:true});const report=createFixtures(q,world.getBlock,resolve);
      const cell=report.journal.mutations.find(p=>p.block==='minecraft:flowing_water');return {status:report.status,cell};})()""")
    cell=result['cell']
    assert result['status']=='CREATED' and cell['block']==cell['resolvedBlock']=='minecraft:flowing_water'
    assert cell['observed']['block']=='minecraft:water'
    assert cell['normalization']=='bedrock_flowing_water_setter_to_water'
    assert cell['states']==cell['resolvedStates']==cell['observed']['states']=={'liquid_depth':3}


def test_pinned_setter_normalization_rejects_changed_resolved_states():
    result=fixture("""(()=>{const world=mockWorld({canonicalizeFlowing:true});try{createFixtures(q,world.getBlock,(id,states)=>
      resolve(id,id==='minecraft:flowing_water'?{liquid_depth:0}:states));}
      catch(error){return {status:error.fixtureReport.status,target:error.fixtureReport.requestedPermutation,restoration:error.fixtureReport.restoration.status};}})()""")
    assert result['status']=='FAILED' and result['target']['block']=='minecraft:flowing_water'
    assert result['restoration']=='RESTORED_SUBSET'


def test_restore_clears_overlay_before_air_to_avoid_primary_water():
    result=fixture("""(()=>{const world=mockWorld({airBecomesWaterIfLogged:true});const created=createFixtures(q,world.getBlock,resolve);
      const restored=restoreFixtureJournal(q,created.journal,world.getBlock,resolve);return {restored:restored.restoredCells,
        expected:created.mutatedCells,status:restored.status,allDryAir:[...world.cells.values()].every(b=>b.typeId==='minecraft:air'&&!b.isWaterlogged)};})()""")
    assert result['status']=='RESTORED_SUBSET' and result['restored']==result['expected']==382 and result['allDryAir']


def test_read_only_resolve_probe_retains_requested_and_exact_resolved_states():
    result=fixture("observeResolvedPermutations([{block:'minecraft:stone',states:{}}],(id,states)=>resolve(id,{stone_type:'stone'}))")
    assert result[0]['status']=='RESOLVED' and result[0]['requested']['states']=={}
    assert result[0]['resolved']['states']=={'stone_type':'stone'}


def test_read_only_resolve_probe_errors_and_bounds_are_explicit():
    result=fixture("observeResolvedPermutations([{block:'minecraft:unknown',states:{}}],()=>{throw new Error('unsupported');})")
    assert result[0]['status']=='FAILED' and result[0]['resolved'] is None and 'unsupported' in result[0]['error']
    for entries in ([],[{'block':'minecraft:stone','states':{}}]*9,[{'block':'minecraft:stone','states':{'invalid':[]}}]):
        expr="(()=>{try{observeResolvedPermutations("+json.dumps(entries)+",resolve);}catch(error){return String(error);}})()"
        assert isinstance(fixture(expr),str)
