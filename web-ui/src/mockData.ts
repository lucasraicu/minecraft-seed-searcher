import type { SearchConfig } from './types';
import { SEARCH_PROFILES } from './constants/baselinePolicy';
export const DYNAMIC_2048_CONFIG: SearchConfig = {
  profile: 'dynamic2048',
  requiredStructures: Object.keys(SEARCH_PROFILES.dynamic2048.counts),
  structureFloorCounts: { ...SEARCH_PROFILES.dynamic2048.counts },
  mandatoryFortressAndBastion: true,
  requireNetherOverlap: false,
  selectedBiomes: [...SEARCH_PROFILES.dynamic2048.requiredBiomes],
  playableRadiusOverworld: SEARCH_PROFILES.dynamic2048.overworldSide,
  playableRadiusNether: SEARCH_PROFILES.dynamic2048.netherSide,
  sweepSeedCount: 10000000,
  startIndex: '0',
  maxMisses: SEARCH_PROFILES.dynamic2048.defaultMisses,
  openmpThreads: 34,
  batchSize: 16384,
};

export const INITIAL_CONFIG: SearchConfig = DYNAMIC_2048_CONFIG;

