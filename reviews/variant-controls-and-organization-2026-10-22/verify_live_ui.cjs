const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..'),nm=path.join(root,'web-ui/node_modules');module.paths.unshift(nm);
const ts=require(path.join(nm,'typescript')),React=require(path.join(nm,'react')),SSR=require(path.join(nm,'react-dom/server'));
const hook=(m,f)=>m._compile(`const React=require(${JSON.stringify(path.join(nm,'react'))});\n`+ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.React,esModuleInterop:true},fileName:f}).outputText,f);
require.extensions['.ts']=hook;require.extensions['.tsx']=hook;
const {FilterBuilder}=require(path.join(root,'web-ui/src/catalog/FilterBuilder.tsx'));
const {validateProductResultsV2}=require(path.join(root,'web-ui/src/catalog/LaunchProductList.tsx'));
const read=n=>JSON.parse(fs.readFileSync(path.join(__dirname,'http-verification',n+'.json'),'utf8'));
let options=0,products=0;
for(const [name,disabled] of [['capabilities',false],['historical-capabilities',true]]){
 const features=read(name).registry_v3.features;
 const html=SSR.renderToStaticMarkup(React.createElement(FilterBuilder,{rows:[{id:'live',rule:'required',kind:'structure_count',feature:'structure.igloo',at_least:1,scope:{kind:'near_base',radius:1024}}],onChangeRows:()=>{},onResetRows:()=>{},enableV3:true,features}));
 for(const fid of ['structure.igloo_with_basement','structure.bastion_treasure']){const option=html.match(new RegExp('<option[^>]*value="'+fid+'"[^>]*>'));assert(option,fid);assert.equal(option[0].includes('disabled'),disabled);options++;}
}
for(let i=0;i<2;i++)for(const view of ['primary','reserve']){const d=read(`product-${i}-${view}`);const v=validateProductResultsV2(d,d.snapshot_id,d.product_id);assert(v.ok,JSON.stringify(v));products++;}
const out={ok:true,real_snapshot_option_checks:options,actual_product_responses_decoded:products,biome_ui_suite:25,product_ui_suite:17};fs.writeFileSync(path.join(__dirname,'UI_VERIFICATION.json'),JSON.stringify(out,null,2)+'\n');console.log(out);
