// Render actual pillar components against the actual Python product registry.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {spawnSync}=require('node:child_process');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const req=createRequire(root+'/web-ui/package.json');
const ts=req('typescript'),React=req('react');
const {renderToStaticMarkup}=req('react-dom/server');
const py=spawnSync(root+'/.venv/bin/python',['-c','import json;from seed_search.catalog.products import product_registry;print(json.dumps(product_registry()))'],
 {cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
assert.equal(py.status,0,py.stderr);
const registry=JSON.parse(py.stdout);
let stateValues=[],stateIndex=0;
const react={...React,useState:initial=>[stateValues[stateIndex++]??initial,()=>{}],useEffect(){},useRef:initial=>({current:initial})};
const js=ts.transpileModule(fs.readFileSync(root+'/web-ui/src/catalog/pillars/index.tsx','utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
const mod={exports:{}};
vm.runInNewContext(js,{module:mod,exports:mod.exports,require:name=>name==='react'?react:name.startsWith('.')?{requestJson(){throw new Error('SSR must not request data');}}:req(name)});
const {PillarNavigation,ProductPillar}=mod.exports;
const nav=renderToStaticMarkup(React.createElement(PillarNavigation,{value:'personalized',onChange(){}}));
for(const label of ['Realm/Server Seeds','Presets','Personalized Selection','Rare Seeds'])assert.ok(nav.includes(label));
assert.equal((nav.match(/aria-current="page"/g)||[]).length,1);
for(const pillar of ['realm','presets','rare']){
 stateIndex=0;stateValues=[registry,'',null];
 const html=renderToStaticMarkup(React.createElement(ProductPillar,{pillarId:pillar,snapshotId:'a'.repeat(64)}));
 const expected=registry.products.filter(p=>p.pillar_id===pillar);
 for(const p of expected)assert.ok(html.includes(p.label.replaceAll('&','&amp;').replaceAll("'",'&#x27;')),p.label);
 assert.ok(!html.includes('<select')&&!html.includes('type="range"'),'Fixed product pillars have no scope forms');
}
stateIndex=0;stateValues=[registry,'',registry.products.find(p=>p.kind==='preset').id];
const gated=renderToStaticMarkup(React.createElement(ProductPillar,{pillarId:'presets',snapshotId:'a'.repeat(64)}));
assert.ok(gated.includes('Matching results are unavailable'));
assert.ok(!gated.includes('Copy seed'),'Gated cards never invent matching worlds');
console.log('Four-pillar rendering passed: all defined cards, fixed scopes and honest criteria gates.');
