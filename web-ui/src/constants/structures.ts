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
  { id: 'pyramid', name: 'Desert Pyramids', icon: '🏺', min: 1, max: 6 },
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

export const V2_FLEXIBLE_FLOORS: Record<string, number> = {
  mansion: 0,
  trial_chamber: 8,
  village: 5,
  ruined_portal: 5,
  mineshaft: 17,
  ancient_city: 1,
  fortress: 1,
  bastion: 2,
  lush_caves: 0,
  deep_dark: 0,
  dripstone_caves: 0,
};

export const HARD_FLOORS: Record<string, number> = {
  stronghold: 1,
  desert_pyramid: 1,
  pyramid: 1,
  jungle_temple: 1,
  outpost: 1,
  mansion: 0,
  ancient_city: 1,
  fortress: 1,
  bastion: 2,
  trial_chamber: 8,
  village: 5,
  ruined_portal: 5,
  mineshaft: 17,
  monument: 1,
  shipwreck: 3,
  lush_caves: 0,
  deep_dark: 0,
  dripstone_caves: 0,
};

export const IDEAL_TARGETS: Record<string, number> = {
  stronghold: 1,
  desert_pyramid: 1,
  pyramid: 1,
  jungle_temple: 1,
  outpost: 1,
  mansion: 1,
  ancient_city: 2,
  fortress: 2,
  bastion: 3,
  trial_chamber: 10,
  village: 7,
  ruined_portal: 7,
  mineshaft: 20,
  monument: 1,
  shipwreck: 5,
  lush_caves: 0,
  deep_dark: 0,
  dripstone_caves: 0,
};

export const DEFAULT_STRUCTURE_FLOORS: Record<string, number> = {
  stronghold: 1,
  mansion: 1,
  village: 7,
  trial_chamber: 10,
  ancient_city: 2,
  outpost: 1,
  fortress: 2,
  bastion: 3,
  pyramid: 1,
  jungle_temple: 1,
  monument: 1,
  shipwreck: 3,
  ruined_portal: 7,
  mineshaft: 20,
  lush_caves: 0,
  dripstone_caves: 0,
  deep_dark: 0,
};

export const STRICT_STRUCTURE_IDS = new Set([
  'stronghold',
  'pyramid',
  'desert_pyramid',
  'jungle_temple',
  'outpost',
]);

export const DEFAULT_SWEEP_IDEAL_COUNTS: Record<string, number> = {
  mansion: 1,
  trial_chamber: 10,
  village: 7,
  ruined_portal: 7,
  mineshaft: 20,
  ancient_city: 2,
  fortress: 2,
  bastion: 3,
};
