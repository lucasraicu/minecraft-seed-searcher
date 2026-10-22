// Render the actual Rare list with the shared evidence component wired in.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {createRequire}=require('node:module'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),req=createRequire(root+'/web-ui/package.json');
const ts=req('typescript'),React=req('react'),{renderToStaticMarkup}=req('react-dom/server');
const py=spawnSync(root+'/.venv/bin/python',['-c','import json;from seed_search.catalog.products import product_registry;print(json.dumps(product_registry()))'],{cwd:root,encoding:'utf8'});
assert.equal(py.status,0,py.stderr);const registry=JSON.parse(py.stdout);
let stateValues=[],stateIndex=0;
const react={...React,useState:init=>[stateValues[stateIndex++]??init,()=>{}],useEffect(){},useRef:init=>({current:init})};
const cache={};
function load(file){
 if(cache[file])return cache[file].exports;
 const mod={exports:{}};cache[file]=mod;
 const js=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
 vm.runInNewContext(js,{module:mod,exports:mod.exports,require:name=>{
  if(name==='react')return react;
  if(name.includes('utils/network'))return {requestJson(){throw Error('SSR must not request');}};
  if(name.startsWith('.')){
   const base=path.resolve(path.dirname(file),name);
   return load(fs.existsSync(base+'.tsx')?base+'.tsx':base+'.ts');
  }
  return req(name);
 }});return mod.exports;
}
const {ProductPillar}=load(root+'/web-ui/src/catalog/pillars/index.tsx');
const pid='research.origin.village.r2000',sid='a'.repeat(64),wid='b'.repeat(64);
const summary={revision:'catalog-structure-evidence-summary-v1',feature_id:'structure.village',predicted_count:28,tested_count:28,
 located_exact:27,coordinate_difference:1,no_location:0,errors:0,untested_count:0,grouped_command:false,
 verifier_game_build_id:'1.26.52.3',generated_count:null,exhaustive_count:null};
const row={world_id:wid,seed:'-3509659830737203357',count:28,witnesses:Array.from({length:28},(_,i)=>[i*16,0]),structure_evidence:summary};
function render(value){
 stateIndex=0;stateValues=[registry,'',pid,{key:`${sid}:${pid}`,data:{ok:true,snapshot_id:sid,product_id:pid,population_worlds:200,
  scope:{scope_type:'origin_euclidean_circle',anchor:[0,0],radius:2000},results:[value],evidence_label:registry.evidence_label}},wid,null];
 return renderToStaticMarkup(React.createElement(ProductPillar,{pillarId:'rare',snapshotId:sid}));
}
const html=render(row);
for(const text of ['28 village predictions','27 BDS exact-location matches','1 unresolved','Research ranking uses predicted counts','Predicted locations. Circle: radius 2,000 blocks.'])assert.ok(html.includes(text),text);
assert.ok(!html.includes('28 verified'));
const old={...row};delete old.structure_evidence;
assert.ok(render(old).includes('Not checked in BDS'));
console.log('Integrated Rare list: scoped BDS evidence, research ranking and missing-evidence fallback passed.');
