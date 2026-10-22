// Read-only blocks; temporary owned ticking areas generate disposable worlds only.
import {world, system} from '@minecraft/server';
world.afterEvents.worldLoad.subscribe(() => console.warn('VARIANT_IDENTITY ' + JSON.stringify({seed: world.seed, api:'2.10.0', players:world.getAllPlayers().length})));
let busy=false, requests=0;
const tick=()=>new Promise(resolve=>system.run(resolve));
system.afterEvents.scriptEventReceive.subscribe(async event=>{
  if(event.id!=='variant_audit:observe')return;
  if(busy || requests>=8){console.warn('VARIANT_ERROR request cap');return;}
  busy=true;requests++;
  let reads=0;const owned=[];
  try {
    const q=JSON.parse(event.message);
    if(!['overworld','nether'].includes(q.dimension)||!Number.isInteger(q.id)||!Array.isArray(q.chunks)||q.chunks.length>10)throw Error('Request shape');
    const dim=world.getDimension(q.dimension), manager=world.tickingAreaManager;
    const chunks=new Set();
    for(const c of q.chunks){
      if(c.length!==2||!c.every(Number.isInteger)||c.some(v=>Math.abs(v)>320))throw Error('Chunk bounds');
      const key=c.join(',');if(chunks.has(key))throw Error('Duplicate chunk');chunks.add(key);
    }
    function block(x,y,z){
      if(++reads>8192||!chunks.has([Math.floor(x/16),Math.floor(z/16)].join(',')))throw Error('Read bounds');
      const b=dim.getBlock({x,y,z});if(!b)throw Error('Unavailable block');return b.typeId;
    }
    for(let i=0;i<q.chunks.length;i++){
      const [cx,cz]=q.chunks[i], name='variant_'+requests+'_'+i;
      const options={dimension:dim,from:{x:cx*16,y:63,z:cz*16},to:{x:cx*16,y:63,z:cz*16}};
      if(!manager.hasCapacity(options))throw Error('Ticking capacity');
      await manager.createTickingArea(name,options);owned.push(name);await tick();if(!q.points)block(cx*16,63,cz*16);
    }
    const palette=[],indices=[],lookup=new Map(),pointRows=[];
    if(q.points){
      if(q.volume!==null||!Array.isArray(q.points)||q.points.length>59)throw Error('Point cap');
      for(const point of q.points){
        if(point.length!==3||!point.every(Number.isInteger)||point[1]<-64||point[1]>319)throw Error('Point bounds');
        const [x,y,z]=point;pointRows.push({x,y,z,block:block(x,y,z)});await tick();
      }
    }
    if(q.volume){
      const v=q.volume;
      if(!Array.isArray(v)||v.length!==6||!v.every(Number.isInteger))throw Error('Volume shape');
      const [x0,y0,z0,x1,y1,z1]=v;
      if(x1<=x0||y1<=y0||z1<=z0||y0<0||y1>112||(x1-x0)*(y1-y0)*(z1-z0)+reads>8192)throw Error('Volume cap');
      for(let x=x0;x<x1;x++)for(let z=z0;z<z1;z++)for(let y=y0;y<y1;y++){
        const id=block(x,y,z);if(!lookup.has(id)){lookup.set(id,palette.length);palette.push(id);}indices.push(lookup.get(id));
        if(reads%512===0)await tick();
      }
    }
    // Dwell briefly to allow persistent tile entities to finish initialization.
    for(let i=0;i<4;i++)await tick();
    console.warn('VARIANT_RESULT '+JSON.stringify({id:q.id,dimension:q.dimension,chunks:q.chunks,volume:q.volume??null,palette,indices,pointRows,blockReads:reads,request:requests}));
  }catch(error){console.warn('VARIANT_ERROR '+JSON.stringify({error:String(error),blockReads:reads,request:requests}));}
  finally{for(const name of owned)try{world.tickingAreaManager.removeTickingArea(name);}catch(error){console.warn('VARIANT_CLEANUP_ERROR '+String(error));}busy=false;}
});
