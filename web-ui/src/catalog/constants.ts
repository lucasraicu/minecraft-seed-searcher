// Canonical pilot contract vocabulary; no unsupported Nether/spawn filters.
import type { CatalogPreset, CatalogProfile, BorderSide, NearRadius, AnchorMode, Dimension } from './types';
export const FAVORITES_STORAGE_KEY='seed-search.catalog.favorites.v1';
export const MAX_FILTER_ROWS=12, MAX_COMPARE_SEEDS=4, DEFAULT_PAGE_SIZE=20;
export const MAX_FILTER_ROW_ALTERNATIVES = 16;
export const BORDER_SIDES:BorderSide[]=[2048,4096,8192];
export const NEAR_RADII:NearRadius[]=[256,512,1024];
export const OVERWORLD_NEAR_RADII:NearRadius[]=[256,512,1024];
export const NETHER_NEAR_RADII:NearRadius[]=[64,128,256];
export const ALL_NEAR_RADII:NearRadius[]=[64,128,256,512,1024];
export const NETHER_FIXED_SIDE = 1024;
export const DEFAULT_OVERWORLD_NEAR_RADIUS:NearRadius = 512;
export const DEFAULT_NETHER_NEAR_RADIUS:NearRadius = 128;
export const ANCHOR_MODES:AnchorMode[]=['recommended','origin'];

export interface FeatureOption {
  id: string;
  label: string;
  kind: 'structure' | 'biome';
  category: string;
  dimension?: Dimension;
  available?: boolean;
  unavailable_reason?: string | null;
  canonical_members?: string[];
  eligible_y?: number[];
}

export const KNOWN_STRUCTURES:FeatureOption[]=[
  {"id": "structure.village", "label": "Village", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.trial_chamber", "label": "Trial chamber", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.ancient_city", "label": "Ancient city", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.mansion", "label": "Woodland mansion", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.monument", "label": "Ocean monument", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.outpost", "label": "Pillager outpost", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.desert_pyramid", "label": "Desert pyramid", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.jungle_temple", "label": "Jungle temple", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.swamp_hut", "label": "Swamp hut", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.igloo", "label": "Igloo", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.trail_ruins", "label": "Trail ruins", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.ruined_portal", "label": "Ruined portal", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.shipwreck", "label": "Shipwreck", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.mineshaft", "label": "Mineshaft", "kind": "structure", "category": "Overworld", "dimension": "overworld"}
];

export const KNOWN_BIOMES:FeatureOption[]=[
  {"id": "biome.cherry_grove", "label": "Cherry grove", "kind": "biome", "category": "Overworld", "dimension": "overworld"},
  {"id": "biome.mushroom_fields", "label": "Mushroom fields", "kind": "biome", "category": "Overworld", "dimension": "overworld"},
  {"id": "biome.bamboo_jungle", "label": "Bamboo jungle", "kind": "biome", "category": "Overworld", "dimension": "overworld"},
  {"id": "biome.desert", "label": "Desert", "kind": "biome", "category": "Overworld", "dimension": "overworld"},
  {"id": "biome.badlands", "label": "Badlands", "kind": "biome", "category": "Overworld", "dimension": "overworld"},
  {"id": "biome.snowy", "label": "Snowy terrain", "kind": "biome", "category": "Overworld", "dimension": "overworld"},
  {"id": "biome.mangrove_swamp", "label": "Mangrove swamp", "kind": "biome", "category": "Overworld", "dimension": "overworld"},
  {"id": "biome.forest", "label": "Forest / birch", "kind": "biome", "category": "Overworld", "dimension": "overworld"},
  {"id": "biome.plains", "label": "Plains / meadow", "kind": "biome", "category": "Overworld", "dimension": "overworld"}
];

// V2 Additional Features: 1 OW Stronghold, 2 Nether structures, 5 Nether biomes (8 total)
export const V2_NEW_STRUCTURES: FeatureOption[] = [
  {"id": "structure.stronghold", "label": "Stronghold", "kind": "structure", "category": "Overworld", "dimension": "overworld"},
  {"id": "structure.fortress", "label": "Nether fortress", "kind": "structure", "category": "Nether", "dimension": "nether"},
  {"id": "structure.bastion", "label": "Bastion remnant", "kind": "structure", "category": "Nether", "dimension": "nether"}
];

export const V2_NEW_BIOMES: FeatureOption[] = [
  {"id": "biome.nether_wastes", "label": "Nether Wastes", "kind": "biome", "category": "Nether", "dimension": "nether"},
  {"id": "biome.crimson_forest", "label": "Crimson Forest", "kind": "biome", "category": "Nether", "dimension": "nether"},
  {"id": "biome.warped_forest", "label": "Warped Forest", "kind": "biome", "category": "Nether", "dimension": "nether"},
  {"id": "biome.soul_sand_valley", "label": "Soul Sand Valley", "kind": "biome", "category": "Nether", "dimension": "nether"},
  {"id": "biome.basalt_deltas", "label": "Basalt Deltas", "kind": "biome", "category": "Nether", "dimension": "nether"}
];

export const V2_STRUCTURES: FeatureOption[] = [
  ...KNOWN_STRUCTURES,
  ...V2_NEW_STRUCTURES
];

export const V2_BIOMES: FeatureOption[] = [
  ...KNOWN_BIOMES,
  ...V2_NEW_BIOMES
];

export const ALL_FEATURES_V2: FeatureOption[] = [
  ...V2_STRUCTURES,
  ...V2_BIOMES
];

export const V3_NEW_STRUCTURES: FeatureOption[] = [
  {
    id: "structure.igloo_with_basement",
    label: "Igloo with basement",
    kind: "structure",
    category: "Overworld",
    dimension: "overworld",
    available: false,
    unavailable_reason: "Requires independent positive/negative auxiliary controls.",
    eligible_y: [63]
  },
  {
    id: "structure.bastion_treasure",
    label: "Bastion treasure room",
    kind: "structure",
    category: "Nether",
    dimension: "nether",
    available: false,
    unavailable_reason: "Requires independent positive/negative auxiliary controls.",
    eligible_y: [64]
  }
];

export const V3_STRUCTURES: FeatureOption[] = [
  ...V2_STRUCTURES,
  ...V3_NEW_STRUCTURES
];

export const V3_BIOME_GROUPS: FeatureOption[] = [
  {
    id: "biome.group.badlands",
    label: "Badlands group",
    kind: "biome",
    category: "Groups",
    dimension: "overworld",
    available: true,
    unavailable_reason: null,
    canonical_members: [
      "biome.exact.badlands",
      "biome.exact.eroded_badlands",
      "biome.exact.wooded_badlands"
    ]
  },
  {
    id: "biome.group.snowy",
    label: "Snowy group",
    kind: "biome",
    category: "Groups",
    dimension: "overworld",
    available: true,
    unavailable_reason: null,
    canonical_members: [
      "biome.exact.snowy_plains",
      "biome.exact.snowy_slopes",
      "biome.exact.snowy_taiga",
      "biome.exact.ice_spikes"
    ]
  },
  {
    id: "biome.group.forest",
    label: "Forest / birch group",
    kind: "biome",
    category: "Groups",
    dimension: "overworld",
    available: true,
    unavailable_reason: null,
    canonical_members: [
      "biome.exact.forest",
      "biome.exact.birch_forest",
      "biome.exact.flower_forest",
      "biome.exact.old_growth_birch_forest"
    ]
  },
  {
    id: "biome.group.plains",
    label: "Plains / meadow group",
    kind: "biome",
    category: "Groups",
    dimension: "overworld",
    available: true,
    unavailable_reason: null,
    canonical_members: [
      "biome.exact.plains",
      "biome.exact.sunflower_plains",
      "biome.exact.meadow"
    ]
  }
];

export const V3_EXACT_BIOMES: FeatureOption[] = [
  // Oceans (9)
  { id: "biome.exact.ocean", label: "Ocean", kind: "biome", category: "Oceans", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.deep_ocean", label: "Deep ocean", kind: "biome", category: "Oceans", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.warm_ocean", label: "Warm ocean", kind: "biome", category: "Oceans", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.lukewarm_ocean", label: "Lukewarm ocean", kind: "biome", category: "Oceans", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.deep_lukewarm_ocean", label: "Deep lukewarm ocean", kind: "biome", category: "Oceans", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.cold_ocean", label: "Cold ocean", kind: "biome", category: "Oceans", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.deep_cold_ocean", label: "Deep cold ocean", kind: "biome", category: "Oceans", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.frozen_ocean", label: "Frozen ocean", kind: "biome", category: "Oceans", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.deep_frozen_ocean", label: "Deep frozen ocean", kind: "biome", category: "Oceans", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },

  // Rivers & Shores (5)
  { id: "biome.exact.river", label: "River", kind: "biome", category: "Rivers & Shores", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.frozen_river", label: "Frozen river", kind: "biome", category: "Rivers & Shores", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.beach", label: "Beach", kind: "biome", category: "Rivers & Shores", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.snowy_beach", label: "Snowy beach", kind: "biome", category: "Rivers & Shores", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.stony_shore", label: "Stony shore", kind: "biome", category: "Rivers & Shores", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },

  // Forest & Taiga (7)
  { id: "biome.exact.dark_forest", label: "Dark forest", kind: "biome", category: "Forest & Taiga", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.pale_garden", label: "Pale garden", kind: "biome", category: "Forest & Taiga", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.dappled_forest", label: "Dappled forest", kind: "biome", category: "Forest & Taiga", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.taiga", label: "Taiga", kind: "biome", category: "Forest & Taiga", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.old_growth_pine_taiga", label: "Old growth pine taiga", kind: "biome", category: "Forest & Taiga", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.old_growth_spruce_taiga", label: "Old growth spruce taiga", kind: "biome", category: "Forest & Taiga", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.windswept_forest", label: "Windswept forest", kind: "biome", category: "Forest & Taiga", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },

  // Jungle (2)
  { id: "biome.exact.jungle", label: "Jungle", kind: "biome", category: "Jungle", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.sparse_jungle", label: "Sparse jungle", kind: "biome", category: "Jungle", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },

  // Savanna (3)
  { id: "biome.exact.savanna", label: "Savanna", kind: "biome", category: "Savanna", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.savanna_plateau", label: "Savanna plateau", kind: "biome", category: "Savanna", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.windswept_savanna", label: "Windswept savanna", kind: "biome", category: "Savanna", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },

  // Swamp (1)
  { id: "biome.exact.swamp", label: "Swamp", kind: "biome", category: "Swamp", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },

  // Split Badlands (3)
  { id: "biome.exact.badlands", label: "Badlands", kind: "biome", category: "Badlands", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.eroded_badlands", label: "Eroded badlands", kind: "biome", category: "Badlands", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.wooded_badlands", label: "Wooded badlands", kind: "biome", category: "Badlands", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },

  // Split Snowy (4)
  { id: "biome.exact.snowy_plains", label: "Snowy plains", kind: "biome", category: "Snowy", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.snowy_slopes", label: "Snowy slopes", kind: "biome", category: "Snowy", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.snowy_taiga", label: "Snowy taiga", kind: "biome", category: "Snowy", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.ice_spikes", label: "Ice spikes", kind: "biome", category: "Snowy", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },

  // Split Forest / Birch (4)
  { id: "biome.exact.forest", label: "Forest", kind: "biome", category: "Forest & Taiga", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.birch_forest", label: "Birch forest", kind: "biome", category: "Forest & Taiga", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.flower_forest", label: "Flower forest", kind: "biome", category: "Forest & Taiga", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.old_growth_birch_forest", label: "Old growth birch forest", kind: "biome", category: "Forest & Taiga", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },

  // Split Plains / Meadow (3)
  { id: "biome.exact.plains", label: "Plains", kind: "biome", category: "Plains & Meadow", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.sunflower_plains", label: "Sunflower plains", kind: "biome", category: "Plains & Meadow", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.meadow", label: "Meadow", kind: "biome", category: "Plains & Meadow", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },

  // Singletons (5)
  { id: "biome.exact.cherry_grove", label: "Cherry grove", kind: "biome", category: "Plains & Meadow", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.mushroom_fields", label: "Mushroom fields", kind: "biome", category: "Oceans", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.bamboo_jungle", label: "Bamboo jungle", kind: "biome", category: "Jungle", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.desert", label: "Desert", kind: "biome", category: "Savanna", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },
  { id: "biome.exact.mangrove_swamp", label: "Mangrove swamp", kind: "biome", category: "Swamp", dimension: "overworld", available: true, unavailable_reason: null, eligible_y: [63] },

  // Mountains (6 - gated initially)
  { id: "biome.exact.windswept_hills", label: "Windswept hills", kind: "biome", category: "Mountains", dimension: "overworld", available: false, unavailable_reason: "Requires multi-height mountain profile validation (Y96/Y160/Y224).", eligible_y: [96, 160, 224] },
  { id: "biome.exact.windswept_gravelly_hills", label: "Windswept gravelly hills", kind: "biome", category: "Mountains", dimension: "overworld", available: false, unavailable_reason: "Requires multi-height mountain profile validation (Y96/Y160/Y224).", eligible_y: [96, 160, 224] },
  { id: "biome.exact.jagged_peaks", label: "Jagged peaks", kind: "biome", category: "Mountains", dimension: "overworld", available: false, unavailable_reason: "Requires multi-height mountain profile validation (Y96/Y160/Y224).", eligible_y: [96, 160, 224] },
  { id: "biome.exact.frozen_peaks", label: "Frozen peaks", kind: "biome", category: "Mountains", dimension: "overworld", available: false, unavailable_reason: "Requires multi-height mountain profile validation (Y96/Y160/Y224).", eligible_y: [96, 160, 224] },
  { id: "biome.exact.stony_peaks", label: "Stony peaks", kind: "biome", category: "Mountains", dimension: "overworld", available: false, unavailable_reason: "Requires multi-height mountain profile validation (Y96/Y160/Y224).", eligible_y: [96, 160, 224] },
  { id: "biome.exact.grove", label: "Grove", kind: "biome", category: "Mountains", dimension: "overworld", available: false, unavailable_reason: "Requires multi-height mountain profile validation (Y96/Y160/Y224).", eligible_y: [96, 160, 224] },

  // Caves (4 - gated initially)
  { id: "biome.exact.lush_caves", label: "Lush caves", kind: "biome", category: "Caves", dimension: "overworld", available: false, unavailable_reason: "Requires subterranean cave height profile validation (Y-48/Y0).", eligible_y: [-48, 0] },
  { id: "biome.exact.dripstone_caves", label: "Dripstone caves", kind: "biome", category: "Caves", dimension: "overworld", available: false, unavailable_reason: "Requires subterranean cave height profile validation (Y-48/Y0).", eligible_y: [-48, 0] },
  { id: "biome.exact.deep_dark", label: "Deep dark", kind: "biome", category: "Caves", dimension: "overworld", available: false, unavailable_reason: "Requires subterranean cave height profile validation (Y-48/Y0).", eligible_y: [-48, 0] },
  { id: "biome.exact.sulfur_caves", label: "Sulfur caves", kind: "biome", category: "Caves", dimension: "overworld", available: false, unavailable_reason: "Requires subterranean cave height profile validation (Y-48/Y0).", eligible_y: [-48, 0] }
];

export const V3_ALL_BIOMES: FeatureOption[] = [
  ...V3_BIOME_GROUPS,
  ...V3_EXACT_BIOMES,
  ...V2_NEW_BIOMES
];

export const ALL_FEATURES_V3: FeatureOption[] = [
  ...V3_STRUCTURES,
  ...V3_ALL_BIOMES,
  ...KNOWN_BIOMES
];

export function isV3Feature(featureId: string): boolean {
  return featureId.startsWith('biome.exact.') ||
    featureId.startsWith('biome.group.') ||
    featureId === 'structure.igloo_with_basement' ||
    featureId === 'structure.bastion_treasure';
}

export function getFeatureV3Metadata(featureId: string): FeatureOption | undefined {
  return ALL_FEATURES_V3.find(f => f.id === featureId);
}

export function getFeatureDimension(featureId: string): Dimension {
  const feat = ALL_FEATURES_V3.find(f => f.id === featureId) || ALL_FEATURES_V2.find(f => f.id === featureId);
  return feat?.dimension || 'overworld';
}

export function isNetherFeature(featureId: string): boolean {
  return getFeatureDimension(featureId) === 'nether';
}

export function normalizeRadiusForDimension(dimension: Dimension, radius?: NearRadius): NearRadius {
  if (dimension === 'nether') {
    if (radius === 64 || radius === 128 || radius === 256) {
      return radius;
    }
    return DEFAULT_NETHER_NEAR_RADIUS;
  }
  if (radius === 256 || radius === 512 || radius === 1024) {
    return radius;
  }
  return DEFAULT_OVERWORLD_NEAR_RADIUS;
}

export function getValidRadiiForDimension(dimension: Dimension): NearRadius[] {
  return dimension === 'nether' ? [...NETHER_NEAR_RADII] : [...OVERWORLD_NEAR_RADII];
}
export const DEFAULT_PROFILES:CatalogProfile[]=[{"id": "balanced_survival", "label": "Balanced Survival"}, {"id": "village_life", "label": "Village Life"}, {"id": "trial_adventurer", "label": "Trial Adventurer"}, {"id": "ancient_city_explorer", "label": "Ancient City Explorer"}, {"id": "ocean_explorer", "label": "Ocean Explorer"}, {"id": "biome_variety", "label": "Biome Variety"}, {"id": "structure_collector", "label": "Structure Collector"}, {"id": "archaeology", "label": "Archaeology"}, {"id": "compact_starter", "label": "Compact Starter"}, {"id": "village_and_trials", "label": "Village And Trials"}, {"id": "village_and_ocean", "label": "Village And Ocean"}, {"id": "village_and_biomes", "label": "Village And Biomes"}, {"id": "cities_and_trials", "label": "Cities And Trials"}, {"id": "ocean_and_biomes", "label": "Ocean And Biomes"}, {"id": "rare_and_biomes", "label": "Rare And Biomes"}, {"id": "multiplayer_variety", "label": "Multiplayer Variety"}];
export const CATEGORY_PRESETS:CatalogPreset[]=[{"id": "general", "label": "General catalog", "fallback_profile": "balanced_survival", "rows": [], "editable": true, "adds_hidden_requirements": false}, {"id": "builders", "label": "Builders", "fallback_profile": "biome_variety", "rows": [{"rule": "preferred", "kind": "biome_witness", "any_of": ["biome.cherry_grove"], "importance": 5, "scope": {"kind": "near_base", "radius": 256}}, {"rule": "preferred", "kind": "structure_count", "feature": "structure.village", "at_least": 1, "importance": 1, "scope": {"kind": "near_base", "radius": 512}}], "editable": true, "adds_hidden_requirements": false}, {"id": "rare", "label": "Rare & unusual", "fallback_profile": "structure_collector", "rows": [{"rule": "preferred", "kind": "biome_witness", "any_of": ["biome.mushroom_fields"], "importance": 5, "scope": {"kind": "near_base", "radius": 1024}}, {"rule": "preferred", "kind": "structure_count", "feature": "structure.mansion", "at_least": 1, "importance": 3, "scope": {"kind": "inside_border"}}], "editable": true, "adds_hidden_requirements": false}, {"id": "survival", "label": "Survival & realms", "fallback_profile": "village_life", "rows": [{"rule": "preferred", "kind": "structure_count", "feature": "structure.village", "at_least": 1, "importance": 5, "scope": {"kind": "near_base", "radius": 512}}, {"rule": "preferred", "kind": "structure_count", "feature": "structure.ruined_portal", "at_least": 1, "importance": 3, "scope": {"kind": "near_base", "radius": 512}}, {"rule": "preferred", "kind": "biome_witness", "any_of": ["biome.plains"], "importance": 1, "scope": {"kind": "near_base", "radius": 512}}], "editable": true, "adds_hidden_requirements": false}, {"id": "adventure", "label": "Adventure", "fallback_profile": "trial_adventurer", "rows": [{"rule": "preferred", "kind": "structure_count", "feature": "structure.trial_chamber", "at_least": 2, "importance": 5, "scope": {"kind": "near_base", "radius": 1024}}, {"rule": "preferred", "kind": "structure_count", "feature": "structure.ancient_city", "at_least": 1, "importance": 3, "scope": {"kind": "near_base", "radius": 1024}}, {"rule": "preferred", "kind": "structure_count", "feature": "structure.desert_pyramid", "at_least": 1, "importance": 1, "scope": {"kind": "near_base", "radius": 1024}}], "editable": true, "adds_hidden_requirements": false}, {"id": "biomes", "label": "Biome explorers", "fallback_profile": "biome_variety", "rows": [{"rule": "preferred", "kind": "biome_witness", "any_of": ["biome.forest", "biome.plains"], "importance": 1, "scope": {"kind": "near_base", "radius": 1024}}, {"rule": "preferred", "kind": "biome_witness", "any_of": ["biome.cherry_grove", "biome.mushroom_fields"], "importance": 5, "scope": {"kind": "near_base", "radius": 1024}}, {"rule": "preferred", "kind": "biome_witness", "any_of": ["biome.mangrove_swamp", "biome.bamboo_jungle"], "importance": 3, "scope": {"kind": "near_base", "radius": 1024}}], "editable": true, "adds_hidden_requirements": false}, {"id": "ocean", "label": "Ocean exploration", "fallback_profile": "ocean_explorer", "rows": [{"rule": "preferred", "kind": "structure_count", "feature": "structure.monument", "at_least": 1, "importance": 5, "scope": {"kind": "inside_border"}}, {"rule": "preferred", "kind": "structure_count", "feature": "structure.shipwreck", "at_least": 2, "importance": 3, "scope": {"kind": "near_base", "radius": 1024}}], "editable": true, "adds_hidden_requirements": false}, {"id": "technical", "label": "Technical planning", "fallback_profile": "archaeology", "rows": [{"rule": "preferred", "kind": "structure_count", "feature": "structure.outpost", "at_least": 1, "importance": 5, "scope": {"kind": "near_base", "radius": 1024}}, {"rule": "preferred", "kind": "structure_count", "feature": "structure.swamp_hut", "at_least": 1, "importance": 3, "scope": {"kind": "inside_border"}}], "editable": true, "adds_hidden_requirements": false}];

const PROFILE_COMPONENT_LABELS:Record<string,string>={V:'Villages',T:'Trial chambers',A:'Ancient cities',O:'Ocean structures',E:'Structure variety',B:'Biome variety',H:'Village proximity',R:'Special structures'};
export function featureLabel(id:string):string {
  return PROFILE_COMPONENT_LABELS[id] ||
    ALL_FEATURES_V3.find(f=>f.id===id)?.label ||
    ALL_FEATURES_V2.find(f=>f.id===id)?.label ||
    [...KNOWN_STRUCTURES,...KNOWN_BIOMES].find(f=>f.id===id)?.label ||
    id.replace(/^(structure|biome)\.(exact\.|group\.)?/,'').replace(/_/g, ' ');
}

export const ANCHOR_LABELS = {recommended:'Recommended settlement',origin:'Origin (advanced)',world_spawn_estimated:'World spawn (estimated)',world_spawn_observed:'World spawn (game observed)'} as const;
