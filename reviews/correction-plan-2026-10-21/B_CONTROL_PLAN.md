# B source diagnostic independent controls (no native edits)
Approved NEXT_FIX_PLAN B requires concrete source mechanisms before consequential
predictor changes. Source-derived prototypes currently explain all216 original
Nether points,25 default local rechecks and12 Beta local rechecks; these are
reanalysis, not blind tests. City/Bastion source gates restore known omissions.

Freeze four deterministic unseen logical seeds: 8467329634092353248, 8467328534580725472, -3239846069929595036, -3239846065634627740.
Two SHA256 seeds plus bit40/bit32 upper-bit pairs, disjoint from original24.
No reroll, no seed sweep. Eight FRESH default worlds: per seed Nether then
Overworld (four logical seeds, two fresh same-seed worlds each); stable API2.10,
no Beta, copies, membership or volume scanning.104 total biome points,29 locates.
Nether independent fixed XZ five points × Y16/64/112 plus two first sorted old/new
selector disagreements from fixed stride64 grid and +1 coordinate neighbors.
Biased disagreement controls explicitly labeled, not random population accuracy.
Structure raw candidates only these four seeds ±2048, first sorted old/new
positive/disagreement groups plus independent origin locate and fortress coupling.
A different locate is inconclusive absence, not evidence a candidate doesn't exist.
All predictions are frozen SHA5728b55b71527251489855c407653f5f4bf364b5813ab96d652480b3373e0120.

Budget one BDS at a time,2CPU/2GiB each,140s/pass,300s/logical seed,1200s total incl
setup/cleanup,1GiB output. Same campaign flock, reject any preexisting running
container, pinned image no pull/ports, owned mounts only. Stop after failure,
no automatic retries, preserve ledger/controls/results. Runtime driver/helper/
observers pinned into controls before dispatch. First seed is pilot; expansion
only after both passes succeed inside unchanged caps. Extra mechanisms cannot be
implemented from this diagnostic alone; review and applicable approval remain.

Runner is a copy of previously audited budgeted runner, external only. Exact
changes: cap4GiB→1GiB; require case dimension OW/Nether, execute locates there and
record it. Existing observer direct-read-first then at most400ticks loading,
max10chunks,64point cap; freeze here <=25points. Clean shutdown/save/container
removal and game1.26.52.3 identity are acceptance. Output files remain external.
Review the supplied driver and observer; underlying pinned runner follows the
already inspected source, no additional unsafe permissions introduced.

## run_b_heldout.py
```
"""Execute only frozen source-diagnostic controls; default dry run, no predictor edits."""
import argparse,fcntl,hashlib,json,re,subprocess,sys,time
from pathlib import Path
P=Path(__file__).parent;ROOT=Path('/Users/lucasraicu/Downloads/minecraft-seed-searcher')
sys.path[:0]=[str(P),str(ROOT/'scripts')]
from b_targeted_runner import run_world,IMAGE,owned_size

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,v):t=p.with_suffix('.tmp');t.write_text(json.dumps(v,indent=2)+'\n');t.replace(p)
def run(execute=False):
 raw=(P/'b-heldout-frozen.json').read_bytes();f=json.loads(raw)
 if hashlib.sha256(raw).hexdigest()!=(P/'b-heldout-frozen.sha256').read_text().strip():raise ValueError('Manifest changed')
 expected=['8467329634092353248','8467328534580725472','-3239846069929595036','-3239846065634627740']
 assert f['seeds']==expected and len(f['cases'])==8
 for name,digest in f['hashes'].items():assert sha(P/name)==digest
 for i,c in enumerate(f['cases']):
  assert c['seed']==expected[i//2] and c['dimension']==('nether' if i%2==0 else 'overworld')
  assert c['columns']==[] and 1<=len(c['points'])<=25 and len(c['structures'])<=5
  assert len({tuple(p) for p in c['points']})==len(c['points'])
  assert len({(p[0]//16,p[2]//16) for p in c['points']})<=10
  for x,y,z in c['points']:
   assert all(type(n) is int for n in (x,y,z)) and max(abs(x),abs(z))<=2048
   assert (0 if c['dimension']=='nether' else -64)<=y<=(127 if c['dimension']=='nether' else 319)
  for q in c['structures']:
   assert (q['feature'],q['command_id']) in [('structure.bastion','bastion_remnant'),('structure.fortress','fortress'),('structure.ancient_city','ancient_city')]
   assert (q['feature']=='structure.ancient_city')==(c['dimension']=='overworld')
   assert len(q['point'])==2 and all(type(n)is int and abs(n)<=2048 for n in q['point'])
 if not execute:return dict(dry_run=True,starts=8,points=sum(len(c['points'])for c in f['cases']),locates=sum(len(c['structures'])for c in f['cases']),caps=f['limits'])
 out=P/'b-heldout-game'
 with (P.parent/'generalization-validation-20261020/game/campaign.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  assert not subprocess.check_output(['docker','ps','-q'],text=True,timeout=5).strip(),'Another container is running; do not overlap or terminate it'
  assert subprocess.check_output(['docker','image','inspect',IMAGE,'--format','{{.Id}}'],text=True,timeout=5).strip()==IMAGE
  out.mkdir(exist_ok=False)
  frozen_files=['run_b_heldout.py','b_targeted_runner.py','b-observer-nether.js','b-observer-overworld.js','b-heldout-frozen.json']
  atomic(out/'controls.json',dict(hashes={n:sha(P/n)for n in frozen_files},caps=f['limits'],world_policy='fresh default settings stable2.10; no beta/copy/membership/volume; source diagnostic only'))
  start=time.monotonic();ledger=[]
  for i,c in enumerate(f['cases']):
   if time.monotonic()-start>1045 or owned_size(out)>1<<30:raise TimeoutError('Total campaign cap/headroom')
   if i%2 and sum(r['wall_seconds']for r in ledger if r['seed']==c['seed'])>145:raise TimeoutError('Per-seed headroom')
   row=dict(index=i,seed=c['seed'],dimension=c['dimension'],state='starting',wall_seconds=0)
   ledger.append(row);atomic(out/'ledger.json',ledger);t=time.monotonic()
   try:
    report=run_world(c,out/f'pass-{i:02}',140,'docker',hashlib.sha256(raw).hexdigest(),out,observer_path=P/f'b-observer-{c["dimension"]}.js')
    identity=report.get('world_identity',{})
    ok=(report['status']=='observed' and all(report.get(k)is True for k in ('clean_shutdown','owned_container_removed','save_confirmed')) and identity.get('dimension')==c['dimension'] and re.search(r'\bVersion: 1\.26\.52\.3(?:\s|$)',(out/f'pass-{i:02}/console.log').read_text()))
    row.update(state='complete' if ok else 'failed',error=report.get('error'),report_sha256=sha(out/f'pass-{i:02}/report.json'))
   except Exception as e:row.update(state='failed',error=repr(e))
   finally:
    row['wall_seconds']=time.monotonic()-t;row['total_seconds']=time.monotonic()-start;atomic(out/'ledger.json',ledger)
   print(json.dumps(row),flush=True)
   if row['state']!='complete' or row['total_seconds']>1200 or owned_size(out)>1<<30:raise RuntimeError('Stop after failure/cap; preserve all evidence, no automatic retry')
   if sum(r['wall_seconds']for r in ledger if r['seed']==c['seed'])>300:raise RuntimeError('Per seed300s cap')
 return dict(status='complete',starts=len(ledger),wall_seconds=time.monotonic()-start)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args();print(json.dumps(run(args.execute)),flush=True)

```

## b-observer-nether.js
```
// Targeted, read-only membership on a disposable already-saved world copy.
import {world, system} from '@minecraft/server';
const DIMENSION = 'nether';
const tick = () => new Promise(resolve => system.run(resolve));
let busy = false;
world.afterEvents.worldLoad.subscribe(() => console.warn('TARGET_IDENTITY ' + JSON.stringify({
  seed: world.seed, api: '2.10.0', players: world.getAllPlayers().length,
  dimension: DIMENSION,
  membershipAvailable: typeof world.getDimension(DIMENSION).getGeneratedStructures === 'function',
})));
system.afterEvents.scriptEventReceive.subscribe(async event => {
  if (event.id !== 'predictor_audit:observe') return;
  if (busy) { console.warn('TARGET_ERROR duplicate request'); return; }
  busy = true;
  let biomeReads = 0, blockReads = 0, membershipReads = 0;
  const dim = world.getDimension(DIMENSION), manager = world.tickingAreaManager;
  try {
    const q = JSON.parse(event.message);
    if (!Array.isArray(q.points) || !Array.isArray(q.columns) || q.columns.length ||
        q.points.length < 1 || q.points.length > 64) throw Error('Input cap');
    const chunks = new Map();
    for (const p of q.points) {
      if (!Array.isArray(p) || p.length !== 3 || !p.every(Number.isInteger) ||
          Math.max(Math.abs(p[0]), Math.abs(p[2])) > 5120 ||
          p[1] < (DIMENSION === 'nether' ? 0 : -64) ||
          p[1] > (DIMENSION === 'nether' ? 127 : 319)) throw Error('Invalid XYZ');
      chunks.set(Math.floor(p[0] / 16) + ',' + Math.floor(p[2] / 16), p);
    }
    if (chunks.size > 10) throw Error('Ticking-area cap');
    let index = 0;
    const loaded = [];
    for (const p of chunks.values()) {
      const [x,y,z] = p;
      let available = false;
      try { available = !!dim.getBlock({x,y,z}); blockReads++; } catch (_) { blockReads++; }
      if (!available) {
        const options = {dimension: dim, from: {x,y,z}, to: {x,y,z}};
        if (!manager.hasCapacity(options)) throw Error('Ticking-area capacity');
        let ready = false, failure;
        manager.createTickingArea('generalization_member_' + index++, options)
          .then(() => { ready = true; }).catch(error => { failure = error; });
        for (let n = 0; !ready && !failure && n < 400; n++) await tick();
        if (failure) throw failure;
        if (!ready) throw Error('Bounded chunk loading did not complete');
      }
      if (++blockReads > 8192 || !dim.getBlock({x,y,z})) throw Error('Chunk unavailable');
      loaded.push({x,y,z});
    }
    const rows = [];
    for (const [x,y,z] of q.points) {
      try {
        if (++biomeReads > 128 || ++blockReads > 8192) throw Error('Read cap');
        const id = dim.getBiome({x,y,z}).id;
        const block = dim.getBlock({x,y,z});
        if (!block) throw Error('Block unavailable');
        rows.push({x,y,z,dimension:DIMENSION,id,block:block.typeId});
      } catch (error) { rows.push({x,y,z,dimension:DIMENSION,error:String(error)}); }
      await tick();
    }
    // Hold owned areas through the caller's save and clean shutdown, on this copy only.
    console.warn('TARGET_RESULT ' + JSON.stringify({rows,columns:[],loaded,
      biomeReads,blockReads,membershipReads,tickingAreas:index,chunks:manager.chunkCount,
      interpretation:'Default-API biome recheck on fresh diagnostic world; no block mutations or census'}));
  } catch (error) {
    console.warn('TARGET_ERROR ' + JSON.stringify({error:String(error),biomeReads,blockReads,membershipReads}));
  }
});

```
