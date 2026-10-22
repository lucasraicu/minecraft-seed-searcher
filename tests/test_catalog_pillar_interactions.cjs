// Exercise real component handlers with a deterministic hook/transport harness.
// These checks do not claim browser layout or DOM focus behavior.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const {createRequire} = require('node:module');
const root = path.resolve(__dirname, '..');
const req = createRequire(root+'/web-ui/package.json');
const React = req('react'), ts = req('typescript');
let slots=[], cursor=0, pending=[], requests=[], clipboardFails=false, copied=[];
const react = {...React,
 useState(initial) {const i=cursor++; if (!(i in slots)) slots[i]=initial;return [slots[i], value=>{slots[i]=typeof value==='function'?value(slots[i]):value;}];},
 useRef(initial) {const i=cursor++; return slots[i] ||= {current:initial};},
 useEffect(fn,deps) {const i=cursor++;const previous=slots[i];if(!previous || deps.some((x,k)=>x!==previous[k])) {slots[i]=deps;pending.push(fn);}},
};
const source=fs.readFileSync(root+'/web-ui/src/catalog/pillars/index.tsx','utf8');
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
const mod={exports:{}};
vm.runInNewContext(js+'\nexports.ResearchList=ResearchList;', {module:mod,exports:mod.exports,
 AbortController,navigator:{clipboard:{async writeText(seed){if(clipboardFails)throw Error('denied');copied.push(seed);}}},
 require:name=>name==='react'?react:name==='../../utils/network'?{requestJson:(url,options)=>new Promise((resolve,reject)=>requests.push({url,options,resolve,reject}))}:name==='../LaunchProductList'?{LaunchProductList:()=>null}:name==='../EvidenceSummary'?{EvidenceSummary:()=>null}:name==='../evidenceValidation'?{validStructureEvidence:()=>true}:req(name)});
function render(Component,props){cursor=0;return Component(props);}
function all(node){if(node==null || typeof node==='boolean')return [];if(Array.isArray(node))return node.flatMap(all);if(typeof node!=='object')return [node];return [node,...all(node.props?.children)];}
function text(node){return all(node).filter(n=>typeof n==='string'||typeof n==='number').join('');}
function element(tree,predicate){const found=all(tree).find(n=>typeof n==='object'&&predicate(n));assert.ok(found,'Expected element missing');return found;}
function button(tree,label){return element(tree,n=>n.type==='button'&&text(n)===label);}
async function effects(){const fns=pending;pending=[];fns.forEach(f=>f());await new Promise(resolve=>setImmediate(resolve));}
async function flush(){await new Promise(resolve=>setImmediate(resolve));}
(async()=>{
 const {ProductPillar,ResearchList}=mod.exports;
 const product={id:'preset.test',pillar_id:'presets',category:'Builders',label:'Build me',criteria_summary:'Example criteria',availability_status:'gated',missing_dependencies:['terrain'],evidence_needed:['Terrain evidence']};
 slots=[];pending=[];requests=[];
 const props={pillarId:'presets',snapshotId:'a'.repeat(64)};
 let tree=render(ProductPillar,props);await effects();
 assert.equal(requests[0].url,'/api/catalog/products?snapshot_id='+props.snapshotId);
 requests[0].resolve({data:{ok:true,revision:'catalog-products-v1',products:[product]}});
 await flush();tree=render(ProductPillar,props);
 let openerFocused=0,inspectorFocused=0;
 const opener={focus(){openerFocused++;}};
 button(tree,'Build meGatedExample criteriaEvidence pending · View criteria').props.onClick({currentTarget:opener});
 tree=render(ProductPillar,props);
 const inspector=element(tree,n=>n.type==='section'&&n.props.tabIndex===-1);
 inspector.props.ref.current={focus(){inspectorFocused++;}};
 await effects();assert.equal(inspectorFocused,1);
 let stopped=0;inspector.props.onKeyDown({key:'Escape',stopPropagation(){stopped++;}});
 assert.equal(stopped,1);assert.equal(openerFocused,1);
 tree=render(ProductPillar,props);assert.ok(!text(tree).includes('Matching results are unavailable'));
 button(tree,'Build meGatedExample criteriaEvidence pending · View criteria').props.onClick({currentTarget:opener});
 tree=render(ProductPillar,props);button(tree,'Close criteria').props.onClick();assert.equal(openerFocused,2);
 // Research transport, scoped copy status and textual map witnesses.
 slots=[];pending=[];requests=[];
 const research={...product,id:'research.origin.village.r2000',pillar_id:'rare',label:'Village density'};
 const rp={product:research,snapshotId:'a'.repeat(64)};
 render(ResearchList,rp);await effects();assert.equal(requests.length,1);
 const row={world_id:'world-1',seed:'-9223372036854775808',count:2,witnesses:[[16,-32],[128,256]]};
 requests[0].resolve({data:{ok:true,snapshot_id:rp.snapshotId,product_id:research.id,population_worlds:1,scope:{scope_type:'origin_euclidean_circle',radius:2000,anchor:[0,0]},results:[row],evidence_label:'Research'}});await flush();
 tree=render(ResearchList,rp);await button(tree,'Copy seed').props.onClick();assert.deepEqual(copied,[row.seed]);
 tree=render(ResearchList,rp);assert.ok(text(tree).includes('Seed copied.'));
 clipboardFails=true;await button(tree,'Copied').props.onClick();tree=render(ResearchList,rp);
 const article=element(tree,n=>n.type==='article');assert.ok(text(article).includes('Clipboard unavailable'));
 button(tree,'View circle map').props.onClick();tree=render(ResearchList,rp);
 const table=element(tree,n=>n.type==='table');assert.ok(text(table).includes('X')&&text(table).includes('Z'));
 assert.equal(all(table).filter(n=>n?.type==='tr').length,3);
 // Empty snapshot sends no request and exposes a useful message.
 const emptyProps={...rp,snapshotId:''};render(ResearchList,emptyProps);await effects();tree=render(ResearchList,emptyProps);
 assert.equal(requests.length,1);assert.ok(text(tree).includes('Select an available catalog snapshot'));
 // A stale completion cannot replace newer snapshot state.
 const nextProps={...rp,snapshotId:'b'.repeat(64)};render(ResearchList,nextProps);await effects();
 const latestProps={...rp,snapshotId:'c'.repeat(64)};render(ResearchList,latestProps);await effects();
 requests[1].resolve({data:{}});await flush();tree=render(ResearchList,latestProps);
 assert.ok(text(tree).includes('Loading research preview'));
 const malformed={...rp,product:{...research,id:'rare.monument'}};render(ResearchList,malformed);await effects();tree=render(ResearchList,malformed);
 assert.ok(text(tree).includes('Research product definition is invalid'));assert.equal(requests.length,3);
 console.log('Pillar handler checks passed: criteria focus, Escape/close, scoped copy, text coordinates, snapshot states.');
})().catch(error=>{console.error(error);process.exitCode=1;});
