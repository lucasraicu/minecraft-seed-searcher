export type Dimension = 'overworld' | 'nether';
export type MapLabelMode = 'smart' | 'all' | 'minimal';
export type MapElevationFilter = 'all' | 'surface' | 'underground';

export interface StructureMarker {
  id: string;
  type:
    | 'stronghold'
    | 'fortress'
    | 'bastion'
    | 'ancient_city'
    | 'village'
    | 'mansion'
    | 'trial_chamber'
    | 'monument'
    | 'outpost'
    | 'ruined_portal'
    | 'shipwreck'
    | 'pyramid'
    | 'desert_pyramid'
    | 'jungle_temple'
    | 'mineshaft'
    | 'lush_caves'
    | 'dripstone_caves'
    | 'deep_dark';
  name: string;
  x: number;
  z: number;
  y?: number;
  dimension: Dimension;
  icon: string;
  color: string;
  viable: boolean;
  distanceToHub?: number;
  notes?: string;
}

export interface BiomeRegion {
  name: string;
  category:
    | 'ocean'
    | 'mountain'
    | 'mushroom'
    | 'forest'
    | 'plains'
    | 'jungle'
    | 'badlands'
    | 'nether_wastes'
    | 'crimson_forest'
    | 'warped_forest'
    | 'soul_sand_valley'
    | 'basalt_deltas';
  color: string;
  polygon: [number, number][]; // Relative block coords
}

export interface RavineMarker {
  id: string;
  x: number;
  z: number;
  y: number;
  yaw: number; // heading in radians
  pitch?: number;
  length: number; // 84 to 112 blocks
  thick: number; // width factor
  giant: boolean; // mega-ravine flag
  underwater: boolean;
}

export interface CaveClusterMarker {
  id: string;
  type: 'lush_caves' | 'dripstone_caves' | 'deep_dark';
  name: string;
  x: number;
  z: number;
  y: number;
  icon: string;
  color: string;
  notes?: string;
}

export interface SeedCandidate {
  id: string;
  seed: string;
  score: number;
  strongholdAnchor: [number, number];
  spawnPoint?: [number, number];
  spawnDistance?: number;
  chunkbaseUrl?: string;
  terrainType: 'Coastal Continent' | 'Coastal Continent (River Highway)' | 'Baseline (Structures Only)' | string;
  terrainPassed?: boolean;
  terrainMetrics: {
    diameter: number;
    waterEnclosure: number;
    flatAreaBlocks: number;
    ridgeRelief?: number;
    elevationRange?: [number, number];
    mainlandFraction?: number;
    oceanEdge?: string;
    riverCorridor?: string;
  };
  structures: StructureMarker[];
  ravines?: RavineMarker[];
  caveClusters?: CaveClusterMarker[];
  biomes: string[];
  bdsVerified: boolean;
  bdsAccuracy: {
    paletteAgreement: string;
    heightMae: number;
    settledColumns: number;
  };
  discoveredAt: string;
  provenance?: 'reference' | 'live';
}

export interface TelemetryState {
  status: 'idle' | 'running' | 'paused' | 'completed' | 'bds_verifying' | 'error';
  seedsPerSec: number;
  totalScanned: number;
  targetCount: number;
  candidatesFound: number;
  elapsedSeconds: number;
  currentStage: string;
  memoryRssGib: number;
  activeThreads: number;
  sweepProgress: number; // 0 to 100
  history: number[]; // Last 20 data points for sparkline
  runId?: string;
}

export interface SearchConfig {
  requiredStructures: string[];
  structureFloorCounts: Record<string, number>;
  mandatoryFortressAndBastion: boolean;
  requireNetherOverlap: boolean;
  selectedBiomes: string[];
  terrainMode: 'coastal_continent' | 'all_baseline';
  mainlandTargetPct: number; // 70 to 80%
  oceanEdgeWidthM: number; // 320m
  riverHighwayLengthM: number; // >= 400m
  enforceSpawnGate: boolean;
  maxSpawnDistance: number;
  playableRadiusOverworld: number;
  playableRadiusNether: number;
  sweepSeedCount: number;
  maxMisses: number; // 0 = exact match, 1 = allow 1 miss, 2 = allow 2 misses
  openmpThreads: number;
  batchSize: number;
}
