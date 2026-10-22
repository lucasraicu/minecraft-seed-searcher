import {world,system} from '@minecraft/server';
world.afterEvents.worldLoad.subscribe(()=>console.warn('SPAWN_AUDIT '+JSON.stringify({seed:world.seed,players:world.getAllPlayers().length,api:'2.10.0',generatedStructures:typeof world.getDimension('overworld').getGeneratedStructures})));
let busy=false;
system.afterEvents.scriptEventReceive.subscribe(async e=>{
 if(e.id!=='all_audit:biomes')return;
 let q;
 try {
  q=JSON.parse(e.message);
  if(busy||!Array.isArray(q.points)||q.points.length>16)throw Error('Invalid batch');
  busy=true;
  const dim=world.getDimension(q.dimension||'overworld'),manager=world.tickingAreaManager,rows=[];
  for(let i=0;i<q.points.length;i++) {
   const [x,y,z]=q.points[i];
   if(![x,y,z].every(Number.isInteger)||(y< -64||y>319)||Math.abs(x)>5120||Math.abs(z)>5120)throw Error('Invalid XYZ');
   let loaded=false;
   try {
    let id;
    try{id=dim.getBiome({x,y,z}).id;}catch(first){
     const opts={dimension:dim,from:{x,y,z},to:{x,y,z}};
     if(!manager.hasCapacity(opts))throw Error('Chunk capacity');
     await manager.createTickingArea('audit_'+q.id+'_'+i,opts);loaded=true;
     id=dim.getBiome({x,y,z}).id;
    }
    rows.push({x,y,z,id,loaded});
   }catch(err){rows.push({x,y,z,error:String(err),loaded});}
  }
  manager.removeAllTickingAreas();
  console.warn('BIOME_AUDIT '+JSON.stringify({id:q.id,rows,chunksAfterUnload:manager.chunkCount}));
 } catch(err){console.warn('BIOME_AUDIT_ERROR '+JSON.stringify({id:q?.id,error:String(err)}));}
 finally{busy=false;}
});
