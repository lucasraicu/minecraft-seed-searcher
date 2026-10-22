# Narrow actual observer review
Prior review timed out without results. This is one controlled narrower retry.
User already approved8-world practical pilot. DefaultstableBDS1.26.52.3/API2.10.
One disposable container2CPU/2GiB atonce. Four blind+four oldtargeted signedseeds;
4OW4Nether; each2x32x32planes+12..18heightpoints in4chunks. 16496predictions frozen,
8192independent scalar/vector checks pass0.241s. Outer validatesmanifest/filehashes,
noothercontainers, frozenownedoutputonly;280sbody300sworld7200stotal4GiBoutput;
strictcoordinate/order/readcounts/save/clean/remove checks. Existing runner tested
old8starts. Its onlydiffs: compacttiles passedin eventpayload, expectedpoints
expanded in Z/Xorder, readcap4096instead128. No player/locate/instanceclaims.
Observer below createsup to4areas, reads<=4096biomes/8192blocks, OW dirty/restores
319blockperchunk forknownpersistence; nooriginalworldmount, Netherread-only.
No new code changes requested fromreviewer. TOOL-FREE. <=400words, specific
blocking defect with source mechanism or state no blocker. Do not recursively
simulate testing or demand unrelated fullworldverification.

```js
// Owned disposable default-settings worlds only. No player joins or instance census.
import {world,system} from '@minecraft/server';
const DIMENSION='__DIMENSION__';
const tick=()=>new Promise(resolve=>system.run(resolve));
world.afterEvents.worldLoad.subscribe(()=>console.warn('TARGET_IDENTITY '+JSON.stringify({
 seed:world.seed,api:'2.10.0',players:world.getAllPlayers().length,dimension:DIMENSION,
 worldSpawn:world.getDefaultSpawnLocation(),membershipAvailable:typeof world.getDimension(DIMENSION).getGeneratedStructures==='function',
})));
let busy=false;
system.afterEvents.scriptEventReceive.subscribe(async event=>{
 if(event.id!=='predictor_audit:observe')return;
 if(busy){console.warn('TARGET_ERROR duplicate');return;}busy=true;
 let biomeReads=0,blockReads=0;
 const dim=world.getDimension(DIMENSION),manager=world.tickingAreaManager;
 try{
  const q=JSON.parse(event.message);
  if(!Array.isArray(q.points)||q.points.length>64||!Array.isArray(q.tiles)||q.tiles.length>4)throw Error('Input cap');
  const points=q.points.map(p=>[...p]);
  for(const t of q.tiles){
   if(!Array.isArray(t)||t.length!==5||!t.every(Number.isInteger))throw Error('Tile schema');
   const [x,z,w,h,y]=t;if(w<1||h<1||w>32||h>32)throw Error('Tile cap');
   for(let dz=0;dz<h;dz++)for(let dx=0;dx<w;dx++)points.push([x+dx,y,z+dz]);
  }
  if(points.length>4096)throw Error('Biome budget');
  const chunks=new Map();
  for(const p of points){
   if(!Array.isArray(p)||p.length!==3||!p.every(Number.isInteger)||Math.max(Math.abs(p[0]),Math.abs(p[2]))>5120||p[1]<(DIMENSION==='overworld'?-64:0)||p[1]>(DIMENSION==='overworld'?319:127))throw Error('XYZ');
   chunks.set(Math.floor(p[0]/16)+','+Math.floor(p[2]/16),p);
  }
  if(chunks.size>10)throw Error('Chunk cap');
  let index=0;
  for(const [x,y,z]of chunks.values()){
   let loaded=false;try{blockReads++;loaded=!!dim.getBlock({x,y,z});}catch(_){}
   if(!loaded){
    const options={dimension:dim,from:{x,y,z},to:{x,y,z}};
    if(!manager.hasCapacity(options))throw Error('Capacity');
    let ready=false,failure;
    manager.createTickingArea('accuracy_'+index++,options).then(()=>ready=true).catch(e=>failure=e);
    for(let n=0;!ready&&!failure&&n<400;n++)await tick();
    if(!ready||failure)throw Error('Chunk load failed '+String(failure));
   }
  }
  const rows=[];
  for(let i=0;i<points.length;i++){
   const [x,y,z]=points[i];
   if(++biomeReads>4096||++blockReads>8192)throw Error('Read cap');
   try{
    const block=dim.getBlock({x,y,z});if(!block)throw Error('Block unavailable');
    rows.push({x,y,z,dimension:DIMENSION,id:dim.getBiome({x,y,z}).id,block:block.typeId});
   }catch(error){rows.push({x,y,z,dimension:DIMENSION,error:String(error)});}
   if(i%32===31)await tick();
  }
  const mutations=[];
  // Persist actual biome records: only owned fresh Overworld copies, exact restoration.
  if(DIMENSION==='overworld')for(const[x,,z]of chunks.values()){
   if(++blockReads>8192)throw Error('Read cap');
   const b=dim.getBlock({x,y:319,z});if(!b)throw Error('Marker unavailable');
   const original=b.permutation,before=b.typeId,states=JSON.stringify(original.getAllStates());
   try{b.setType(before==='minecraft:barrier'?'minecraft:air':'minecraft:barrier');}finally{b.setPermutation(original);}
   if(++blockReads>8192)throw Error('Read cap');
   if(b.typeId!==before||JSON.stringify(b.permutation.getAllStates())!==states)throw Error('Restore failed');
   mutations.push({x,y:319,z,before,after:b.typeId,restored:true});
  }
  await tick();
  console.warn('TARGET_RESULT '+JSON.stringify({rows,columns:[],biomeReads,blockReads,tickingAreas:index,chunks:manager.chunkCount,mutations,
    worldSpawn:world.getDefaultSpawnLocation(),interpretation:'Exact point API observations; no physical structure census'}));
 }catch(error){console.warn('TARGET_ERROR '+JSON.stringify({error:String(error),biomeReads,blockReads}));}
});

```
