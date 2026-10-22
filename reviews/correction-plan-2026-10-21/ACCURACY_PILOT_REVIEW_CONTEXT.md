# Approved eight-world practical accuracy pilot actual execution

No game run yet. Codex froze4blind SHA256 seeds+4old targeted worlds,4OW/4Nether. Eachworld2tiles32x32 at sameXZ/differentY plus12..18boundarypoints,4chunks. 16496predictions frozen,8192 scalar/vector parity checks passed0.241s,manifest6db2f86e4c052d8bf3a981089bcca51cb2b193924d79e826dc8769b9903d931d. No locates/player joins/physical census. OneBDS2CPU2GiB at once,defaultstable2.10,280sbody/300sworld7200total4GiBoutput; save-confirm/clean/remove required; no retry. Reused runner already executed oldB controls; scoped diff below. Fresh-world OW topblock dirtied/restored exact permutation to persistrecords, never original worlds; Nether read-only unknownstorage allowed. Review actual bugs/resource misses, not demands for unapproved player/census guarantees. TOOL-FREE nocommands/edits.

## Observer
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
## Runner changes vs prior testedB
```diff
--- 
+++ 
@@ -178,7 +178,7 @@
             response = wait_for(lambda s: any(t in s for t in ('The nearest minecraft:', 'Syntax error', 'No valid structure', 'Could not find', 'Unknown command')), 25)
             report['queries'].append(dict(index=index, kind=query['feature'], dimension=dimension,
                 command_id=query['command_id'], query=[x, z], output=[response.rstrip()]))
-        payload_data = dict(points=case['points'], columns=case['columns'])
+        payload_data = dict(points=case['points'], columns=[],tiles=case['tiles'])
         if observer_options is not None:
             if (set(observer_options) != {'persistence_mode', 'dwell_ticks'} or
                     observer_options['persistence_mode'] not in ('read_only', 'dirty_restore') or
@@ -194,9 +194,10 @@
         if 'TARGET_ERROR ' in response:
             raise RuntimeError(response.strip())
         observation = json.loads(response.split('TARGET_RESULT ', 1)[1])
-        if [[r['x'], r['y'], r['z']] for r in observation['rows']] != case['points']:
+        expected_points=case['points']+[[x+dx,y,z+dz] for x,z,w,h,y in case['tiles'] for dz in range(h) for dx in range(w)]
+        if [[r['x'], r['y'], r['z']] for r in observation['rows']] != expected_points:
             raise ValueError('Observed coordinates differ from frozen request')
-        if any('error' in r for r in observation['rows']) or observation['biomeReads'] > 128 or observation['blockReads'] > 8192:
+        if any('error' in r for r in observation['rows']) or observation['biomeReads'] > 4096 or observation['blockReads'] > 8192:
             raise ValueError('Observation failure or read cap')
         report['target_result'] = observation
         report['biome_batches'] = [dict(id='target', rows=observation['rows'], ticking_areas_held=observation['tickingAreas'])]

```
## Outer driver
```python
import importlib.util,json,hashlib,subprocess,time,re,sys
from pathlib import Path
P=Path(__file__).parent
spec=importlib.util.spec_from_file_location('accuracy_pilot_runner',P/'runner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def run(execute=False):
 raw=(P/'frozen.json').read_bytes();manifest=json.loads(raw);sha=hashlib.sha256(raw).hexdigest()
 if sha!=(P/'frozen.sha256').read_text().strip():raise ValueError('Manifest changed')
 if len(manifest['worlds'])!=8 or len({w['seed']for w in manifest['worlds']})!=8:raise ValueError('Eight distinct worlds required')
 for f,h in manifest['files'].items():
  if hashlib.sha256((P/f).read_bytes()).hexdigest()!=h:raise ValueError('Frozen implementation differs')
 for c in manifest['worlds']:
  points=c['points']+[[x+dx,y,z+dz]for x,z,w,h,y in c['tiles']for dz in range(h)for dx in range(w)]
  if not 0<len(points)<=4096 or len({(p[0]//16,p[2]//16)for p in points})>10:raise ValueError('Read/chunk cap')
  if c['structures'] or len(c['tiles'])>4 or c['columns']:raise ValueError('Unsupported pilot request')
 if not execute:return dict(dry_run=True,sha256=sha,worlds=8)
 if subprocess.check_output(['docker','ps','-q'],text=True,timeout=5).strip():raise RuntimeError('Shared BDS resource occupied')
 if subprocess.check_output(['docker','image','inspect',m.IMAGE,'--format','{{.Id}}'],text=True,timeout=5).strip()!=m.IMAGE:raise ValueError('Pinned image differs')
 out=P/'game';out.mkdir(exist_ok=False);ledger=[];start=time.monotonic()
 for i,c in enumerate(manifest['worlds']):
  if time.monotonic()-start>6900 or m.owned_size(out)>3<<30:raise TimeoutError('Campaign safety headroom')
  t=time.monotonic();row=dict(index=i,seed=c['seed'],dimension=c['dimension'],state='starting');ledger.append(row)
  (out/'ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
  try:
   report=m.run_world(c,out/f'world-{i:02}',280,'docker',sha,out,observer_path=P/f'observer-{c["dimension"]}.js')
   ident=report.get('world_identity',{})
   good=(report['status']=='observed' and all(report.get(k)is True for k in ('clean_shutdown','owned_container_removed','save_confirmed')) and ident.get('seed')==c['seed'] and ident.get('dimension')==c['dimension'] and ident.get('api')=='2.10.0' and ident.get('players')==0 and re.search(r'\bVersion: 1\.26\.52\.3(?:\s|$)',(out/f'world-{i:02}/console.log').read_text()))
   if not good:raise RuntimeError('Game observation failed '+str(report.get('error')))
   row.update(state='complete',report_sha256=hashlib.sha256((out/f'world-{i:02}/report.json').read_bytes()).hexdigest())
  except Exception as e:
   row.update(state='failed',error=repr(e));raise
  finally:
   row.update(wall_seconds=time.monotonic()-t,total_seconds=time.monotonic()-start)
   (out/'ledger.json').write_text(json.dumps(ledger,indent=2)+'\n');print(json.dumps(row),flush=True)
  if row['wall_seconds']>300 or row['total_seconds']>7200 or m.owned_size(out)>4<<30:raise RuntimeError('No retry after budget exceeded')
 return dict(status='complete',worlds=8,seconds=time.monotonic()-start)
if __name__=='__main__':print(json.dumps(run('--execute'in sys.argv)),flush=True)

```
