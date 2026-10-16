import type { SearchConfig } from '../types';
import { getSearchProfile, normalizeStructureCounts } from '../constants/baselinePolicy';

/** One request builder for both server preview and actual launch. */
export function buildSweepRequest(config: SearchConfig) {
  if (!Number.isSafeInteger(config.sweepSeedCount) || config.sweepSeedCount < 1 ||
      !/^\d{1,20}$/.test(config.startIndex) || BigInt(config.startIndex) >= (1n << 64n) ||
      BigInt(config.startIndex) + BigInt(config.sweepSeedCount) > (1n << 64n)) {
    throw new Error('Enter a positive whole seed count and a valid full64 starting index');
  }
  const policy = getSearchProfile(config.profile);
  const counts: Record<string, number> = {};
  const requested = normalizeStructureCounts(config.structureFloorCounts);
  for (const [key, defaultIdeal] of Object.entries(policy.counts)) {
    const ideal = requested[key];
    if (!Number.isInteger(ideal) || ideal < 0 || ideal > 64) throw new Error(`${key}: enter a whole count from 0 to 64`);
    if (!policy.editableCounts.includes(key) && ideal !== defaultIdeal) throw new Error(`${key}: the selected policy fixes this target at ${defaultIdeal}`);
    if (ideal < (policy.floors[key] ?? defaultIdeal)) throw new Error(`${key}: the active policy requires at least ${policy.floors[key] ?? defaultIdeal}`);
    counts[key] = ideal; // Send every visible target; never rely on a hidden server default.
  }
  if (!Number.isInteger(config.maxMisses) || config.maxMisses < 0) throw new Error('Select a supported deficit budget');
  const maxMisses = Math.min(config.maxMisses, policy.maxMisses);
  if (!Number.isInteger(config.openmpThreads) || config.openmpThreads < 1 || config.openmpThreads > 34) throw new Error('Threads must be 1–34');
  if (!Number.isInteger(config.batchSize) || config.batchSize < 1 || config.batchSize > 16384) throw new Error('Batch size must be 1–16,384');
  const biomes = config.selectedBiomes;
  if (new Set(biomes).size !== biomes.length || biomes.some(id => !policy.requiredBiomes.includes(id))) throw new Error('Select supported biome families');
  if (config.profile !== 'dynamic1664' && config.profile !== 'dynamic2048' && (biomes.length !== policy.requiredBiomes.length || policy.requiredBiomes.some(id => !biomes.includes(id)))) throw new Error('Historical profiles keep their fixed biome requirements');
  return { biomes, count: config.sweepSeedCount, startIndex: config.startIndex, threads: config.openmpThreads,
    batchSize: config.batchSize, maxMisses, counts, profile: config.profile };
}
