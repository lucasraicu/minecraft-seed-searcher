export type Dimension = 'overworld' | 'nether';

export interface StructureMarker {
  id: string;
  type: 'stronghold' | 'fortress' | 'bastion' | 'ancient_city' | 'village' | 'mansion' | 'trial_chamber' | 'monument' | 'outpost' | 'ruined_portal';
  name: string;
  x: number;
  z: number;
  y?: number;
  dimension: Dimension;
  icon: string;
  color: string;
  viable: boolean;
  notes?: string;
}

export interface BiomeRegion {
  name: string;
  category: 'ocean' | 'mountain' | 'mushroom' | 'forest' | 'plains' | 'jungle' | 'badlands' | 'nether_wastes' | 'crimson_forest' | 'warped_forest' | 'soul_sand_valley' | 'basalt_deltas';
  color: string;
  polygon: [number, number][]; // Relative block coords
}

export interface SeedCandidate {
  id: string;
  seed: string;
  score: number;
  strongholdAnchor: [number, number];
  terrainType: 'V1 Island' | 'V2 Mountain Basin' | 'Coastal Ridge';
  terrainMetrics: {
    diameter: number;
    waterEnclosure: number;
    ridgeRelief?: number;
    flatAreaBlocks: number;
    elevationRange: [number, number];
  };
  structures: StructureMarker[];
  biomes: string[];
  bdsVerified: boolean;
  bdsAccuracy: {
    paletteAgreement: string;
    heightMae: number;
    settledColumns: number;
  };
  discoveredAt: string;
}

export interface TelemetryState {
  status: 'idle' | 'running' | 'paused' | 'bds_verifying';
  seedsPerSec: number;
  totalScanned: number;
  candidatesFound: number;
  elapsedSeconds: number;
  currentStage: string;
  memoryRssGib: number;
  activeThreads: number;
  sweepProgress: number; // 0 to 100
  history: number[]; // Last 20 data points for sparkline
}

export interface SearchConfig {
  presetName: string;
  requiredStructures: string[];
  mandatoryFortressAndBastion: boolean;
  requireNetherOverlap: boolean;
  selectedBiomes: string[];
  terrainSpec: 'v1_island' | 'v2_mountain' | 'any';
  playableRadiusOverworld: number;
  playableRadiusNether: number;
  workers: number;
  openmpThreads: number;
  quartReuse: boolean;
  yNoiseReuse: boolean;
  bdsValidation: boolean;
}
