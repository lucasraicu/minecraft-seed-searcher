// Bounded observation only: no blocks, entities, gamerules or seeds are changed.
import { world, system } from '@minecraft/server';
world.afterEvents.worldLoad.subscribe(() => console.warn('TARGET_IDENTITY ' + JSON.stringify({
  seed: world.seed, api: '2.10.0', players: world.getAllPlayers().length,
})));
let busy = false;
const nextTick = () => new Promise(resolve => system.run(resolve));
system.afterEvents.scriptEventReceive.subscribe(async event => {
  if (event.id !== 'predictor_audit:observe') return;
  if (busy) { console.warn('TARGET_ERROR duplicate request'); return; }
  busy = true;
  let blockReads = 0, biomeReads = 0;
  const dim = world.getDimension('overworld');
  const manager = world.tickingAreaManager;
  function block(x, y, z) {
    if (++blockReads > 8192) throw Error('Block-read cap');
    const result = dim.getBlock({ x, y, z });
    if (!result) throw Error('Block unavailable');
    return result;
  }
  function biome(x, y, z) {
    if (++biomeReads > 128) throw Error('Biome-read cap');
    return dim.getBiome({ x, y, z }).id;
  }
  try {
    const q = JSON.parse(event.message);
    if (!Array.isArray(q.points) || !Array.isArray(q.columns) || q.points.length > 64 || q.columns.length > 10) throw Error('Input cap');
    for (const point of q.points) {
      if (point.length !== 3 || !point.every(Number.isInteger) || point[1] < -64 || point[1] > 319 || Math.abs(point[0]) > 5120 || Math.abs(point[2]) > 5120) throw Error('Bad XYZ');
    }
    for (const point of q.columns) {
      if (point.length !== 2 || !point.every(Number.isInteger) || point.some(v => Math.abs(v) > 5120)) throw Error('Bad column');
    }
    const chunks = new Map();
    for (const [x, , z] of q.points) chunks.set(Math.floor(x / 16) + ',' + Math.floor(z / 16), [x, z]);
    for (const [x, z] of q.columns) chunks.set(Math.floor(x / 16) + ',' + Math.floor(z / 16), [x, z]);
    if (chunks.size > 10) throw Error('Ticking-area cap');
    let index = 0;
    for (const [x, z] of chunks.values()) {
      const opts = { dimension: dim, from: { x, y: 63, z }, to: { x, y: 63, z } };
      if (!manager.hasCapacity(opts)) throw Error('Ticking-area capacity');
      await manager.createTickingArea('predictor_' + index++, opts);
      await nextTick();
      block(x, 63, z); // A real block read must work before collecting evidence.
    }
    const rows = [];
    for (const [x, y, z] of q.points) {
      try { rows.push({ x, y, z, id: biome(x, y, z), block: block(x, y, z).typeId }); }
      catch (error) { rows.push({ x, y, z, error: String(error) }); }
      await nextTick();
    }
    const columns = [];
    for (const [x, z] of q.columns) {
      let top = null;
      for (let y = 319; y >= -64; y--) {
        const typeId = block(x, y, z).typeId;
        if (!['minecraft:air', 'minecraft:cave_air', 'minecraft:void_air'].includes(typeId)) { top = { y, block: typeId }; break; }
        if (y % 32 === 0) await nextTick();
      }
      const row = { x, z, top, policy: 'highest_nonair_including_water_and_canopy' };
      if (top && top.y < 319) row.above = { y: top.y + 1, id: biome(x, top.y + 1, z), block: block(x, top.y + 1, z).typeId };
      columns.push(row);
      await nextTick();
    }
    // Keep owned ticking areas alive until host confirms save and clean shutdown.
    console.warn('TARGET_RESULT ' + JSON.stringify({ rows, columns, blockReads, biomeReads, tickingAreas: index, chunks: manager.chunkCount }));
  } catch (error) {
    console.warn('TARGET_ERROR ' + JSON.stringify({ error: String(error), blockReads, biomeReads }));
  }
});
