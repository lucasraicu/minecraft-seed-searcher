import type { SearchConfig } from './types';
import { SEARCH_PROFILES } from './constants/baselinePolicy';
const policy = SEARCH_PROFILES.dynamic1664;
const activeCounts = { ...policy.counts };



export const INITIAL_CONFIG: SearchConfig = {
  profile: 'dynamic1664',
  requiredStructures: Object.keys(activeCounts),
  structureFloorCounts: { ...activeCounts },
  mandatoryFortressAndBastion: true,
  requireNetherOverlap: false,
  selectedBiomes: [...policy.requiredBiomes],
  playableRadiusOverworld: 1664,
  playableRadiusNether: 832,
  sweepSeedCount: 10000000,
  startIndex: '0',
  maxMisses: 3,
  openmpThreads: 34,
  batchSize: 16384,
};

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
