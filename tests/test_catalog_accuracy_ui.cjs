// Actual hook/decoder/render checks. No claim of browser layout or native focus QA.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {createRequire}=require('node:module');const root=path.resolve(__dirname,'..'),req=createRequire(root+'/web-ui/package.json');
const React=req('react'),ts=req('typescript'),{renderToStaticMarkup}=req('react-dom/server');
const sid='a'.repeat(64),generation='b'.repeat(64);let slots=[],cursor=0,effects=[],bodies=[],storageFails=false;
const react={...React,
 useState(initial){const i=cursor++;if(!(i in slots))slots[i]=typeof initial==='function'?initial():initial;return[slots[i],v=>{slots[i]=typeof v==='function'?v(slots[i]):v;}];},
 useRef(initial){const i=cursor++;return slots[i]||=( {current:initial});},
 useEffect(fn,deps){const i=cursor++,old=slots[i];if(!old||deps.some((v,k)=>v!==old[k])){slots[i]=deps;effects.push(fn);}},
 useMemo(fn,deps){const i=cursor++,old=slots[i];if(!old||deps.some((v,k)=>v!==old.deps[k]))slots[i]={deps,value:fn()};return slots[i].value;},useCallback(fn,deps){return react.useMemo(()=>fn,deps);},
};
const api={
 async fetchCatalogStatus(){return{ok:true,available:true,snapshot_id:sid,header:{game_build_id:'research:26.50',world_settings_id:'default'}};},
 async fetchCatalogCapabilities(){return{ok:true,anchor_modes:['recommended','origin']};},
 async fetchCatalogSnapshots(){return{ok:true,snapshots:[{snapshot_id:sid,worlds:200,layouts:48600,header:{game_build_id:'research:26.50',world_settings_id:'default'},accuracy_generation:generation,accuracy_anchor_modes:['world_spawn_estimated','world_spawn_observed']},{snapshot_id:'c'.repeat(64),worlds:1,layouts:243,header:{game_build_id:'research:26.50',world_settings_id:'default'}}]};},
 async postCatalogQuery(body){bodies.push(JSON.parse(JSON.stringify(body)));return{ok:true,snapshot_id:sid,accuracy_generation:body.request.accuracy_generation,results:[],next_cursor:null,matched_worlds:0,truncated:false,evidence_label:'Research',unresolved_worlds:1,unresolved_candidates:[{world_id:'d'.repeat(64),seed:'-9223372036854775808',layout_id:'e'.repeat(64),anchor:[7,13],border_side:2048,status:'unresolved',reason:'Missing evidence'}]};},
 async fetchCatalogDetail(){throw Error('Not invoked');},
};
const window={location:{hash:'#catalog'},history:{pushState(){}},addEventListener(){},removeEventListener(){}};
function load(file,overrides={}){
 const full=root+'/web-ui/src/catalog/'+file;const js=ts.transpileModule(fs.readFileSync(full,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;const mod={exports:{}};
 vm.runInNewContext(js,{module:mod,exports:mod.exports,AbortController,URLSearchParams,queueMicrotask,window,localStorage:{getItem(){if(storageFails)throw Error('Storage blocked');return'[]';},setItem(){}},setTimeout,
 require:name=>overrides[name]||(name==='react'?react:name==='./api'?api:name.startsWith('.')?load(name.slice(2)+(fs.existsSync(path.join(path.dirname(full),name+'.ts'))?'.ts':'.tsx')):req(name))});return mod.exports;
}
const hook=load('useCatalogState.ts').useCatalogState;
function render(){cursor=0;return hook();}
async function flush(){const pending=effects;effects=[];pending.forEach(f=>f());await new Promise(r=>setImmediate(r));}
(async()=>{
 let state=render();await flush();state=render();await flush();state=render();
 state.setAnchorMode('world_spawn_estimated');state=render();await flush();state=render();
 assert.equal(state.currentQueryPayload.anchor_mode,'world_spawn_estimated');assert.equal(state.currentQueryPayload.request_revision,'catalog-query-accuracy-v1');assert.equal(state.currentQueryPayload.accuracy_generation,generation);
 await state.runQuery();state=render();assert.equal(bodies[0].request.accuracy_generation,generation);assert.equal(state.totalMatched,0);assert.equal(state.unresolvedWorlds,1);assert.equal(state.unresolvedCandidates[0].seed,'-9223372036854775808');
 state.clearFiltersAndQuery();state=render();await flush();state=render();assert.equal(bodies.at(-1).request.rows.length,0,'Query All must use cleared criteria rather than the previous request');
 state.setSelectedSnapshotId('c'.repeat(64));state=render();await flush();state=render();
 assert.equal(state.anchorMode,'recommended');assert.equal(state.currentQueryPayload.request_revision,'catalog-query-v1');assert.ok(!('accuracy_generation'in state.currentQueryPayload));assert.equal(state.unresolvedWorlds,0);
 const {validFavorites}=load('validation.ts');const fav={id:`${sid}:${'d'.repeat(64)}:${'e'.repeat(64)}`,seed:'-9223372036854775808',snapshot_id:sid,world_id:'d'.repeat(64),layout_id:'e'.repeat(64),anchor_mode:'world_spawn_observed',border_side:8192,score:0,saved_at:1};assert.equal(validFavorites([fav])[0].anchor_mode,'world_spawn_observed');
 const {CandidateCard}=load('CandidateCard.tsx');const candidate={...fav,anchor:[0,0],bounds:[-4096,-4096,4096,4096],contributions:[],anchor_evidence:{mode:'world_spawn_estimated',coordinate:[0,0],y:null}};
 const html=renderToStaticMarkup(React.createElement(CandidateCard,{candidate,isCompared:false,canCompare:true,isFavorite:false,onToggleCompare(){},onToggleFavorite(){},onInspect(){}}));
 assert.ok(html.includes('World spawn (estimated)')&&html.includes('not player landing'));
 slots=[];effects=[];storageFails=true;state=render();await flush();state=render();assert.ok(state.storageError.includes('favorites'));assert.equal(state.queryError,null);
 console.log('Accuracy UI checks passed: version/generation binding, unavailable-mode reset, unresolved separation, favorites and spawn semantics.');
})().catch(e=>{console.error(e);process.exitCode=1;});
