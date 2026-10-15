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
  selectedBiomes: [
    'plains',
    'desert',
    'forest',
    'taiga',
    'jungle',
    'swamp',
    'snowy_ice',
    'dark_forest',
    'mountains',
    'cherry_grove',
    'badlands',
    'pale_garden',
    'deep_dark',
    'caves',
    'dripstone_caves',
  ],
  playableRadiusOverworld: 1664,
  playableRadiusNether: 832,
  sweepSeedCount: 10000000,
  startIndex: '0',
  maxMisses: 2,
  openmpThreads: 34,
  batchSize: 16384,
};
