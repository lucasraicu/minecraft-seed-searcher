import { world, system } from '@minecraft/server';

function observe(phase, player, initialSpawn) {
  try {
    const point = world.getDefaultSpawnLocation();
    const row = {
      phase, tick: system.currentTick, seed: world.seed,
      defaultSpawn: {x: point.x, y: point.y, z: point.z},
      players: world.getAllPlayers().length,
      spawnRadius: world.gameRules.spawnRadius,
      reference: 'BDS 1.26.52.3 Script API 2.10.0; no spawn mutation',
    };
    if (player) {
      const p = player.location;
      row.playerName = player.name;
      row.playerLocation = {x: p.x, y: p.y, z: p.z};
      row.initialSpawn = initialSpawn;
    }
    console.warn('SPAWN_AUDIT ' + JSON.stringify(row));
  } catch (e) {
    console.warn('SPAWN_AUDIT_ERROR ' + String(e));
  }
}
world.afterEvents.worldLoad.subscribe(() => {
  observe('world_load');
  system.runTimeout(() => observe('world_tick20'), 20);
  system.runTimeout(() => observe('world_tick40'), 40);
});
world.afterEvents.playerSpawn.subscribe(e => {
  observe('player_spawn', e.player, e.initialSpawn);
  system.runTimeout(() => observe('player_tick1', e.player, e.initialSpawn), 1);
  system.runTimeout(() => observe('player_tick20', e.player, e.initialSpawn), 20);
});
