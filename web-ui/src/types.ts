import type { SearchProfileName } from './constants/baselinePolicy';

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
  y?: number | null;
  dimension: Dimension;
  icon: string;
  color: string;
  viable: boolean;
  distanceToHub?: number | null;
  distanceToOrigin?: number | null;
  distanceToSpawn?: number | null;
  distanceUnits?: string;
  evidenceStatus?: string | null;
  notes?: string;
}

export interface RavineMarker {
  id: string;
  x: number;
  z: number;
  y: number | null;
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
  y: number | null;
  icon: string;
  color: string;
  notes?: string;
}

export interface SeedCandidate {
  id: string;
  seed: string;
  score: number | null;
  rankingTier?: number | null;
  weightedRadialDistance?: number | null;
  originDistance?: number | null;
  radialKey?: number | null;
  originDistanceSquared?: number | null;
  scoreComponents?: Record<string, any> | null;
  scenicBonus?: number | null;
  scenicWitness?: [number, number] | null;
  riverWitness?: [number, number] | null;
  villageSpreadBonus?: number | null;
  villageTriple?: [number, number][] | null;
  treasureBastion?: number | null;
  starterHubVillage?: [number, number] | null;
  deficitPenalty?: number | null;
  bonusTotal?: number | null;
  unmetRequirements?: number | null;
  strongholdAnchor?: [number, number] | null;
  evaluationCenter?: [number, number] | null;
  playableBounds?: { overworld?: [number, number, number, number]; final_nether?: [number, number, number, number]; final_nether_exact?: [number, number][] } | null;
  predictedStrongholds?: [number, number][];
  spawnPoint?: [number, number] | null;
  spawnDistance?: number | null;
  spawnWithin100?: boolean | null;
  spawnDistanceToOrigin?: number | null;
  spawnDistanceUnits?: string;
  spawnEvidence?: {
    status?: string;
    source?: { kind?: string; version?: string };
    coordinates?: number[] | null;
    [key: string]: unknown;
  } | null;
  chunkbaseUrl?: string | null;
  terrainType?: 'Coastal Continent' | 'Coastal Continent (River Highway)' | 'Coastal Continent (Near-Miss)' | 'Baseline (Structures Only)' | string | null;
  terrainPassed?: boolean | null;
  terrainStatus?: 'passed' | 'near_miss' | 'failed' | 'pending' | 'not_applicable' | null;
  terrainGeometryScore?: number | null;
  terrainReasons?: string[] | null;
  terrainMetrics?: {
    diameter?: number | null;
    waterEnclosure?: number | null;
    flatAreaBlocks?: number | null;
    ridgeRelief?: number | null;
    elevationRange?: [number, number] | null;
    mainlandFraction?: number | null;
    oceanEdge?: string | null;
    riverCorridor?: string | null;
    [key: string]: unknown;
  } | null;
  structures: StructureMarker[];
  ravines?: RavineMarker[];
  caveClusters?: CaveClusterMarker[];
  biomes?: string[] | null;
  biomeWitnesses?: Record<string, any> | null;
  netherBiomeWitnesses?: Record<string, { coordinate: number[]; biome: string; id: number }> | null;
  biomeSamples?: Array<{ biome: string; coordinate?: number[]; x?: number; y?: number; z?: number; id?: number }> | null;
  bdsVerified?: boolean | null;
  bdsAccuracy?: {
    paletteAgreement?: string | null;
    heightMae?: number | null;
    settledColumns?: number | null;
    [key: string]: unknown;
  } | null;
  baselineStatus?: string | null;
  marineStatus?: string | null;
  actualGenerationStatus?: string | null;
  surfaceVerification?: { status: string; observedBiomes: string[]; observationId?: string | null; scope: string } | null;
  screeningRevision?: string | null;
  discoveredAt: string;
  provenance?: 'reference' | 'live' | 'unknown';
}

export interface TelemetryState {
  status: 'idle' | 'running' | 'paused' | 'completed' | 'bds_verifying' | 'error';
  seedsPerSec: number;
  totalScanned: number;
  targetCount: number;
  candidatesFound: number;
  elapsedSeconds: number;
  currentStage: string;
  memoryRssGib: number | null;
  activeThreads: number | null;
  sweepProgress: number; // 0 to 100
  history: number[]; // Last 20 data points for sparkline
  runId?: string;

}

export interface SearchConfig {
  profile: SearchProfileName;
  requiredStructures: string[];
  structureFloorCounts: Record<string, number>;
  mandatoryFortressAndBastion: boolean;
  requireNetherOverlap: boolean;
  selectedBiomes: string[];
  playableRadiusOverworld: number;
  playableRadiusNether: number;
  sweepSeedCount: number;
  startIndex: string;
  maxMisses: number; // 0 = exact match, 1 = allow 1 miss, 2 = allow 2 misses
  openmpThreads: number;
  batchSize: number;
}
