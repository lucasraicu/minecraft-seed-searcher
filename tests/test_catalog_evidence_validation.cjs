const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..'),req=createRequire(root+'/web-ui/package.json');
const ts=req('typescript'),mod={exports:{}};
const js=ts.transpileModule(fs.readFileSync(root+'/web-ui/src/catalog/evidenceValidation.ts','utf8'),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
vm.runInNewContext(js,{module:mod,exports:mod.exports});
const {validStructureEvidence:valid}=mod.exports;
const good={revision:'catalog-structure-evidence-summary-v1',feature_id:'structure.village',
 predicted_count:28,tested_count:28,located_exact:27,coordinate_difference:1,no_location:0,errors:0,
 untested_count:0,grouped_command:false,verifier_game_build_id:'1.26.52.3',generated_count:null,exhaustive_count:null};
assert.ok(valid(good,28,'structure.village'));
for(const patch of [{located_exact:28},{tested_count:27},{untested_count:1},{generated_count:27},
 {exhaustive_count:28},{grouped_command:true},{verifier_game_build_id:null},{verifier_game_build_id:'research:26.50'},
 {predicted_count:NaN},{errors:-1},{located_exact:true},{feature_id:'structure.shipwreck'}])
 assert.ok(!valid({...good,...patch},28,'structure.village'),JSON.stringify(patch));
assert.ok(valid({...good,tested_count:0,located_exact:0,coordinate_difference:0,untested_count:28,verifier_game_build_id:null}));
assert.ok(!valid(null));
assert.ok(valid({...good,feature_id:'structure.desert_pyramid',grouped_command:true},28,'structure.desert_pyramid'));
console.log('Evidence count/provenance decoder checks passed.');
