import { SEARCH_PROFILES } from './baselinePolicy';

export interface StructureMeta {
  id: string;
  name: string;
  icon: string;
  min: number;
  max: number;
}

export const ALL_STRUCTURES: StructureMeta[] = [
  { id: 'stronghold', name: 'Stronghold', icon: '🏰', min: 1, max: 3 },
  { id: 'mansion', name: 'Woodland Mansion', icon: '🏛️', min: 0, max: 3 },
  { id: 'village', name: 'Villages', icon: '🏡', min: 5, max: 15 },
  { id: 'trial_chamber', name: 'Trial Chambers', icon: '⚔️', min: 8, max: 15 },
  { id: 'ancient_city', name: 'Ancient Cities', icon: '🏙️', min: 1, max: 8 },
  { id: 'outpost', name: 'Pillager Outposts', icon: '🏹', min: 1, max: 8 },
  { id: 'fortress', name: 'Nether Fortresses', icon: '🏯', min: 1, max: 8 },
  { id: 'bastion', name: 'Bastion Remnants', icon: '🐖', min: 1, max: 8 },
  { id: 'desert_pyramid', name: 'Desert Pyramids', icon: '🏺', min: 1, max: 6 },
  { id: 'jungle_temple', name: 'Jungle Temples', icon: '🌿', min: 1, max: 6 },
  { id: 'monument', name: 'Ocean Monuments', icon: '🏛️', min: 1, max: 6 },
  { id: 'shipwreck', name: 'Shipwrecks', icon: '⛵', min: 1, max: 15 },
  { id: 'ruined_portal', name: 'Ruined Portals', icon: '🚪', min: 5, max: 15 },
  { id: 'mineshaft', name: 'Mineshafts', icon: '⛏️', min: 17, max: 40 },
];

export const CAVE_CLUSTERS: StructureMeta[] = [
  { id: 'lush_caves', name: 'Lush Caves', icon: '🌿', min: 0, max: 10 },
  { id: 'deep_dark', name: 'Deep Dark', icon: '🌌', min: 0, max: 10 },
  { id: 'dripstone_caves', name: 'Dripstone Caves', icon: '🪨', min: 0, max: 10 },
];

// Counts come from the generated engine policy; do not duplicate YAML targets.
export const DEFAULT_STRUCTURE_FLOORS: Record<string, number> = {
  ...SEARCH_PROFILES.dynamic1664.counts,
};
