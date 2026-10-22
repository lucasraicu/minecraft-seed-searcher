// Read-only, bounded biome observations in an owned disposable world.
import { world, system } from '@minecraft/server';
let busy = false, biomeReads = 0, blockReads = 0;
const tick = () => new Promise(resolve => system.run(resolve));
world.afterEvents.worldLoad.subscribe(() => console.warn('GENERALIZATION_IDENTITY ' + JSON.stringify({
  seed: world.seed, api: '2.10.0', players: world.getAllPlayers().length,
  membershipAvailable: typeof world.getDimension('overworld').getGeneratedStructures === 'function',
})));
system.afterEvents.scriptEventReceive.subscribe(async event => {
  if (event.id !== 'generalization:observe') return;
  let q;
  try {
    if (busy) throw Error('Concurrent request');
    busy = true; q = JSON.parse(event.message);
    if (!Number.isInteger(q.id) || !['overworld', 'nether', 'the_end'].includes(q.dimension) ||
        !Array.isArray(q.points) || q.points.length < 1 || q.points.length > 12) throw Error('Invalid batch');
    const dim = world.getDimension(q.dimension), manager = world.tickingAreaManager;
    const rows = [];
    for (const p of q.points) {
      if (!Array.isArray(p) || p.length !== 3 || !p.every(Number.isInteger) ||
          Math.abs(p[0]) > 5120 || Math.abs(p[2]) > 5120 ||
          p[1] < (q.dimension === 'overworld' ? -64 : 0) ||
          p[1] > (q.dimension === 'nether' ? 127 : (q.dimension === 'the_end' ? 255 : 319))) throw Error('Invalid XYZ');
    }
    for (const [x, y, z] of q.points) {
      const row = {x, y, z, dimension: q.dimension, lookupMode: 'direct_api', harnessCreatedTickingArea: false};
      if (++biomeReads > 1024) throw Error('Cumulative biome-read cap');
      try {
        try { row.id = dim.getBiome({x, y, z}).id; }
        catch (initial) {
          row.initialError = String(initial); row.lookupMode = 'after_ticking_area';
          manager.removeAllTickingAreas();
          const opts = {dimension: dim, from: {x, y, z}, to: {x, y, z}};
          if (!manager.hasCapacity(opts)) throw Error('Ticking-area capacity');
          let ready = false, failure;
          manager.createTickingArea('generalization_' + q.id + '_' + biomeReads, opts)
            .then(() => { ready = true; }).catch(error => { failure = error; });
          row.harnessCreatedTickingArea = true;
          for (let n = 0; !ready && !failure && n < 100; n++) await tick();
          if (failure) throw failure;
          if (!ready) throw Error('Bounded ticking-area load did not complete');
          row.id = dim.getBiome({x, y, z}).id;
        }
        if (++blockReads > 8192) throw Error('Cumulative block-read cap');
        try { row.block = dim.getBlock({x, y, z})?.typeId ?? null; }
        catch (error) { row.blockUnavailable = String(error); }
      } catch (error) { row.error = String(error); }
      rows.push(row); await tick();
    }
    manager.removeAllTickingAreas();
    console.warn('GENERALIZATION_RESULT ' + JSON.stringify({id: q.id, dimension: q.dimension,
      rows, biomeReads, blockReads, chunksAfterUnload: manager.chunkCount}));
  } catch (error) {
    try { world.tickingAreaManager.removeAllTickingAreas(); } catch (_) {}
    console.warn('GENERALIZATION_ERROR ' + JSON.stringify({id: q?.id, error: String(error), biomeReads, blockReads}));
  } finally { busy = false; }
});
