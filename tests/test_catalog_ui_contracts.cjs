const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const ts=require('../web-ui/node_modules/typescript');
const file=path.join(__dirname,'../web-ui/src/catalog/validation.ts');
const code=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const moduleObject={exports:{}};vm.runInNewContext(code,{module:moduleObject,exports:moduleObject.exports});
const {validFavorites,serializeRows}=moduleObject.exports;
const plain=value=>JSON.parse(JSON.stringify(value));
const favorite={seed:'-9223372036854775808',world_id:'a'.repeat(64),layout_id:'b'.repeat(64),snapshot_id:'c'.repeat(64),border_side:8192,anchor_mode:'recommended',score:0,saved_at:1};
favorite.id=`${favorite.snapshot_id}:${favorite.world_id}:${favorite.layout_id}`;
for(const seed of ['-9223372036854775808','9223372036854775807','0'])assert.equal(validFavorites([{...favorite,seed}])[0].seed,seed);
for(const seed of ['9223372036854775808','-9223372036854775809','-0','01',9007199254740992])assert.throws(()=>validFavorites([{...favorite,seed}]));
assert.equal(validFavorites([favorite,favorite]).length,1);
assert.throws(()=>validFavorites([{...favorite,snapshot_id:'d'.repeat(64)}]));
assert.throws(()=>validFavorites([{...favorite,bounds:[0,0,Infinity,0]}]));
assert.deepEqual(plain(serializeRows([{id:'ui-only',rule:'required',kind:'structure_count',feature:'structure.village',at_least:3,importance:5,scope:{kind:'inside_border',radius:512}}])),[{rule:'required',kind:'structure_count',scope:{kind:'inside_border'},feature:'structure.village',at_least:3}]);
assert.deepEqual(plain(serializeRows([{id:'ui-only',rule:'preferred',kind:'biome_witness',any_of:['biome.badlands','biome.mangrove_swamp'],importance:5,scope:{kind:'near_base',radius:512}}])),[{rule:'preferred',kind:'biome_witness',scope:{kind:'near_base',radius:512},importance:5,any_of:['biome.badlands','biome.mangrove_swamp']}]);
console.log('Catalog UI contracts passed: signed64 identities, malformed favorites, deduplication and canonical request serialization.');

// Render the actual component: unknown evidence must not look like a known zero,
// and every coordinate and the full seed must survive the presentation layer.
const {createRequire}=require('node:module');
const webRequire=createRequire(path.join(__dirname,'../web-ui/package.json'));
const React=webRequire('react');const {renderToStaticMarkup}=webRequire('react-dom/server');
function load(relative){
 const filename=path.join(__dirname,'../web-ui/src/catalog',relative);
 const result=ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}});
 const mod={exports:{}};
 vm.runInNewContext(result.outputText,{module:mod,exports:mod.exports,require:id=>id.startsWith('.')?load(id+'.ts'):webRequire(id),setTimeout});return mod.exports;
}
const {CandidateCard}=load('CandidateCard.tsx');
const html=renderToStaticMarkup(React.createElement(CandidateCard,{candidate:{...favorite,anchor:[256,-256],bounds:[-768,-1280,1280,768],contributions:[{feature:'V',utility_units:0,max_units:1,status:'unknown'}]},snapshotId:favorite.snapshot_id,isCompared:false,canCompare:true,isFavorite:false,onToggleCompare(){},onToggleFavorite(){},onInspect(){}}));
assert.ok(html.includes('-9223372036854775808'));
assert.ok(html.includes('unknown coverage'));
assert.ok(html.includes('upper edges excluded'));
assert.ok(!html.includes('hiz'));
assert.ok(html.includes('1280')&&html.includes('768'));
console.log('Catalog card rendering passed: full seed, complete bounds and explicit unknown coverage.');
