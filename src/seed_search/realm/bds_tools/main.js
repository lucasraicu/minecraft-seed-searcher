import { world, system, BlockVolume, BlockPermutation } from '@minecraft/server';
import * as serverApi from '@minecraft/server';
let dim;
import { classifySurface, isSupport, interpretColumn, observeBlock, observeSurfaceBiome, observeBiomeRegistry } from './column_policy.js';
import { fixturePlan, createFixtures, restoreFixtureJournal, observeResolvedPermutations } from './fixture_policy.js';
// Controlled experiments only, independent from the seed finder.
function valid(q) {
  for (const key of ['x0','z0','side','spacing']) if (!Number.isInteger(q[key])) throw new Error('Invalid '+key);
  if(q.side<1 || q.side>512 || q.spacing<1 || q.spacing>q.side) throw new Error('Invalid bounds');
  if(!/^[a-zA-Z0-9_-]+$/.test(q.id)) throw new Error('Invalid identifier');
}
let busy=false;
function* exportColumns(q) {
  const start=Date.now(); blockCalls=0;
  let samples=0,missing=0,mismatches=0,waterColumns=0,waterKnownColumns=0,waterUnknownColumns=0,rows=[],batch=0;
  for(let z=q.z0;z<q.z0+q.side;z+=q.spacing)
    for(let x=q.x0;x<q.x0+q.side;x+=q.spacing) {
      try {
        const ref=q.method==='cave_biomes' ? {x,z,caves:(q.caveYs||[0,-16,-32,-48]).map(y=>({x,y,z,biome:dim.getBiome({x,y,z}).id}))} : column(x,z,q.method==='compare'?'reference':q.method);
        let difference=null;
        if(q.method==='compare') {
          const fast=column(x,z,q.compareMethod||'topmost');
          if(JSON.stringify(ref)!==JSON.stringify(fast)) {mismatches++;difference={reference:ref,topmost:fast};}
        }
        samples++;if(ref.waterDepth>0)waterColumns++;
        if(ref.waterKnown===true) waterKnownColumns++;else if(q.method!=='cave_biomes') waterUnknownColumns++;
        rows.push({id:q.id,...ref,...(difference?{difference}:{})});
      } catch(e) {missing++;rows.push({id:q.id,x,z,error:String(e)});}
      if(rows.length >= (q.batchSize||32)) {console.warn('PROBE_BATCH '+JSON.stringify({id:q.id,batch:batch++,rows}));rows=[];}
      yield;
    }
  if(rows.length)console.warn('PROBE_BATCH '+JSON.stringify({id:q.id,batch:batch++,rows}));
  console.warn('PROBE_DONE '+JSON.stringify({id:q.id,method:q.method,samples,missing,mismatches,waterColumns,waterKnownColumns,waterUnknownColumns,blockCalls,batches:batch,scanMs:Date.now()-start,players:world.getAllPlayers().length}));
  busy=false;
}
function emitFixtureFailure(q,report) {
  const {journal,restoration,...summary}=report;
  if(journal)for(let i=0;i<journal.mutations.length;i+=8)
    console.warn('PROBE_FIXTURE_JOURNAL '+JSON.stringify({id:q.id,batch:i/8,mutations:journal.mutations.slice(i,i+8)}));
  if(restoration)for(let i=0;i<(restoration.results||[]).length;i+=8)
    console.warn('PROBE_FIXTURE_ROLLBACK '+JSON.stringify({id:q.id,batch:i/8,results:restoration.results.slice(i,i+8)}));
  console.warn('PROBE_FIXTURE_REPORT '+JSON.stringify({id:q.id,...summary,
    journal:journal?{...journal,mutations:undefined}:null,
    restoration:restoration?{...restoration,results:undefined,errors:restoration.errors.slice(0,5),errorCount:restoration.errors.length}:null}));
}
function scanFixtureColumns(q) {
  const cases=fixturePlan(q).cases;let mismatches=0,missing=0;const rows=[];
  for(const fixture of cases) {
    try {
      const ref=column(fixture.x,fixture.z,'reference'),fast=column(fixture.x,fixture.z,'native_top');
      const difference=JSON.stringify(ref)===JSON.stringify(fast)?null:{reference:ref,nativeTop:fast};
      if(difference)mismatches++;
      rows.push({id:q.id,...ref,fixture:fixture.label,evidenceRole:'controlled_fixture',...(difference?{difference}:{})});
    } catch(error) {missing++;rows.push({id:q.id,x:fixture.x,z:fixture.z,fixture:fixture.label,error:String(error),evidenceRole:'controlled_fixture'});}
  }
  console.warn('PROBE_FIXTURE_BATCH '+JSON.stringify({id:q.id,rows}));
  console.warn('PROBE_FIXTURE_DONE '+JSON.stringify({id:q.id,samples:rows.length,missing,mismatches,evidenceRole:'controlled_fixture'}));
}
system.afterEvents.scriptEventReceive.subscribe(async e=>{
  if(!e.id.startsWith('bds_probe:'))return;
  let q;
  try {
    q=JSON.parse(e.message);valid(q);
    if(busy)throw new Error('Concurrent request rejected');
    const manager=world.tickingAreaManager;
    if(e.id==='bds_probe:load') {
      busy=true;const start=Date.now();
      manager.removeAllTickingAreas();
      const tile=Math.min(q.side,q.tileSize||128);const promises=[];
      for(let dz=0;dz<q.side;dz+=tile)for(let dx=0;dx<q.side;dx+=tile) {
        const opts={dimension:dim,from:{x:q.x0+dx,y:-64,z:q.z0+dz},to:{x:Math.min(q.x0+dx+tile,q.x0+q.side)-1,y:319,z:Math.min(q.z0+dz+tile,q.z0+q.side)-1}};
        if(!manager.hasCapacity(opts))throw new Error('Capacity exceeded: '+manager.maxChunkCount);
        promises.push(manager.createTickingArea(q.id+'_'+dx+'_'+dz,opts));
      }
      await Promise.all(promises);
      const areas=manager.getAllTickingAreas();
      console.warn('PROBE_LOADED '+JSON.stringify({id:q.id,loadMs:Date.now()-start,chunks:manager.chunkCount,fullyLoaded:areas.every(a=>a.isFullyLoaded),players:world.getAllPlayers().length}));
      busy=false;
    } else if(e.id==='bds_probe:scan') {
      busy=true;system.runJob(exportColumns(q));
    } else if(e.id==='bds_probe:biome_registry') {
      console.warn('PROBE_BIOME_REGISTRY '+JSON.stringify({id:q.id,...observeBiomeRegistry(serverApi)}));
    } else if(e.id==='bds_probe:permutations_resolve') {
      const permutations=observeResolvedPermutations(q.permutations,(id,states)=>BlockPermutation.resolve(id,states));
      console.warn('PROBE_PERMUTATIONS_RESOLVED '+JSON.stringify({id:q.id,source:'official BDS 1.26.52.3 Script API 2.10.0 BlockPermutation.resolve',results:permutations}));
    } else if(e.id==='bds_probe:fixtures_create') {
      busy=true;
      const report=createFixtures(q,p=>dim.getBlock(p),(id,states)=>BlockPermutation.resolve(id,states));
      scanFixtureColumns(q); // Initial positive/reference observations before the next simulation tick.
      const {journal,...summary}=report;
      for(let i=0;i<journal.mutations.length;i+=8)
        console.warn('PROBE_FIXTURE_JOURNAL '+JSON.stringify({id:q.id,batch:i/8,mutations:journal.mutations.slice(i,i+8)}));
      console.warn('PROBE_FIXTURE_CREATED '+JSON.stringify({id:q.id,...summary,journal:{...journal,mutations:undefined}}));busy=false;
    } else if(e.id==='bds_probe:fixtures_restore') {
      busy=true;
      const report=restoreFixtureJournal(q,q.journal,p=>dim.getBlock(p),(id,states)=>BlockPermutation.resolve(id,states));
      console.warn('PROBE_FIXTURE_RESTORED '+JSON.stringify({id:q.id,...report}));busy=false;
    } else if(e.id==='bds_probe:fixtures_scan') {
      busy=true;scanFixtureColumns(q);busy=false;
    } else if(e.id==='bds_probe:dirty') {
      let changed=0,failed=0;
      // A disposable-world A/B test: change an air block at Y=319 then restore
      // its exact permutation immediately, without editing terrain below.
      for(let cz=Math.floor(q.z0/16);cz<=Math.floor((q.z0+q.side-1)/16);cz++)for(let cx=Math.floor(q.x0/16);cx<=Math.floor((q.x0+q.side-1)/16);cx++) {
        const x=Math.max(q.x0,cx*16),z=Math.max(q.z0,cz*16);
        const b=dim.getBlock({x,y:319,z});
        if(!b || b.typeId!=='minecraft:air') {failed++;continue;}
        const original=b.permutation;
        try {b.setType('minecraft:glass');} finally {b.setPermutation(original);}
        if(b.typeId!==original.type.id)throw new Error('Restoration failed');
        changed++;
      }
      console.warn('PROBE_DIRTY '+JSON.stringify({id:q.id,changed,failed,markerY:319,restored:true}));
    } else if(e.id==='bds_probe:check_sky') {
      let air=0,nonAir=0;
      for(let cz=Math.floor(q.z0/16);cz<=Math.floor((q.z0+q.side-1)/16);cz++)for(let cx=Math.floor(q.x0/16);cx<=Math.floor((q.x0+q.side-1)/16);cx++) {
        const b=dim.getBlock({x:Math.max(q.x0,cx*16),y:319,z:Math.max(q.z0,cz*16)});
        if(b?.typeId==='minecraft:air')air++;else nonAir++;
      }
      console.warn('PROBE_SKY '+JSON.stringify({id:q.id,air,nonAir}));
    } else if(e.id==='bds_probe:unload') {
      manager.removeAllTickingAreas();console.warn('PROBE_UNLOADED '+JSON.stringify({id:q.id,chunks:manager.chunkCount}));
    } else throw new Error('Unknown request');
  }catch(e){busy=false;if(e.fixtureReport)emitFixtureFailure(q,e.fixtureReport);console.warn('PROBE_FAILED '+JSON.stringify({id:q?.id,error:String(e),fixtureReportAvailable:!!e.fixtureReport}));}
});
world.afterEvents.worldLoad.subscribe(()=>{
  dim=world.getDimension('overworld');
  console.warn('PROBE_READY '+JSON.stringify({versionModule:'2.10.0',players:world.getAllPlayers().length,maxChunkCount:world.tickingAreaManager.maxChunkCount,getTopmostBlock:typeof dim.getTopmostBlock,getGeneratedStructures:typeof dim.getGeneratedStructures}));
});
let blockCalls=0;
function readBlock(pos) {blockCalls++; return dim.getBlock(pos);}
function column(x, z, method="reference") {
  const cells = []; const probes = [];
  let startY=319;
  if (method === "native_top") {
    const first=dim.getBlocks(new BlockVolume({x,y:-64,z},{x,y:319,z}),{excludeTypes:["minecraft:air"],closest:1,location:{x,y:319,z}},false).getBlockLocationIterator().next();
    if (first.done) throw new Error("Native top unavailable");
    startY=first.value.y;
  }
  if (method === "ray") {
    const hit=dim.getBlockFromRay({x:x+0.5,y:319.5,z:z+0.5},{x:0,y:-1,z:0},{includeLiquidBlocks:true,includePassableBlocks:true,maxDistance:384});
    if (!hit) throw new Error("Ray returned no surface");
    startY=hit.block.y;
  }
  if (method === "topmost") {
    const highest=dim.getTopmostBlock({x,z});
    if (!highest) throw new Error("Topmost block unavailable");
    startY=highest.y;
  }
  let heights;
  if (method === "native_column") {
    const positions=dim.getBlocks(new BlockVolume({x,y:-64,z},{x,y:319,z}),{excludeTypes:["minecraft:air"]},false).getBlockLocationIterator();
    heights=Array.from(positions,p=>p.y).sort((a,b)=>b-a);
  } else {
    heights=(function*(){for(let y=startY;y>=-64;y--)yield y;})();
  }
  for (const y of heights) {
    const b = readBlock({x, y, z});
    if (!b) throw new Error('unloaded block');
    const id = b.typeId;
    const cell=observeBlock(b,y);
    const {waterlogged}=cell;
    cells.push(cell);
    if(!['minecraft:air','minecraft:cave_air','minecraft:void_air'].includes(id))
      probes.push({x,y,z,block:id,states:cell.states,statesError:cell.statesError,...(waterlogged===null?{}:{waterlogged})});
    if(isSupport(classifySurface(id)) && !['minecraft:air','minecraft:cave_air','minecraft:void_air'].includes(id)) break;
  }
  const result=interpretColumn(cells);
  const surfaceBiome=observeSurfaceBiome(result,x,z,pos=>dim.getBiome(pos));
  return {x,z,...result,surfaceBiome,biome:surfaceBiome.name,biomeQueryY:surfaceBiome.y,biomeError:surfaceBiome.error,probes};
}
