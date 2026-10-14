/**
 * Planning heuristic for the pinned v2 Bedrock search policy.
 *
 * Structure marginals and biome/terrain estimates come from separate historical
 * models. The combined result assumes independence and is not a calibrated joint
 * pass rate or a discovery guarantee.
 */

import type { SearchConfig } from '../types';
import {
  HARD_FLOORS,
  IDEAL_TARGETS,
  STRICT_STRUCTURE_IDS,
} from '../constants/structures';

// Helper to format fractional odds and percentages
export function formatOdds(p: number): string {
  if (p >= 0.5) {
    return `1 in ${(1 / p).toFixed(1)} (${(p * 100).toFixed(1)}%)`;
  }
  if (p >= 0.01) {
    return `1 in ${Math.round(1 / p).toLocaleString()} (${(p * 100).toFixed(2)}%)`;
  }
  if (p >= 1e-4) {
    return `1 in ${Math.round(1 / p).toLocaleString()} (${(p * 100).toFixed(4)}%)`;
  }
  if (p >= 1e-8) {
    return `1 in ${Math.round(1 / p).toLocaleString()} (${p.toExponential(2)})`;
  }
  return `1 in ${Math.round(1 / p).toExponential(2)}`;
}

// --------------------------------------------------------------------------
// 1. STAGE 1: STRUCTURE PROBABILITIES
// --------------------------------------------------------------------------

export function calculateStructureProb(type: string, requiredCount: number): number {
  const k = Math.max(0, requiredCount);
  if (k <= 0) return 1.0;

  switch (type) {
    case 'stronghold':
      // Overworld Ring 1 within [-1024, 1024]
      if (k === 1) return 0.357; // 35.7% of seeds have >=1 in 2048x2048
      if (k === 2) return 0.0625; // 6.25% have >=2
      if (k === 3) return 0.005; // 0.5% have >=3
      return 0.0001;

    case 'mansion':
      // 80-chunk grid + Dark Forest requirement
      if (k === 1) return 0.0185; // 1.85% have >=1 in 2048x2048
      if (k === 2) return 0.0002; // 0.02%
      return 0.00001;

    case 'village':
      // Viable village counts in 2048x2048 (mean ~3.96)
      if (k <= 1) return 0.96;
      if (k === 2) return 0.863;
      if (k === 3) return 0.703;
      if (k === 4) return 0.525;
      if (k === 5) return 0.372;
      if (k === 6) return 0.2445; // Blueprint target >=6: 24.45%
      if (k === 7) return 0.142;
      if (k === 8) return 0.071;
      if (k === 9) return 0.032;
      if (k === 10) return 0.012;
      return Math.max(1e-5, 0.012 * Math.pow(0.35, k - 10));

    case 'trial_chamber':
      // Deep underground deepslate layer (mean ~14.01)
      if (k <= 5) return 1.0; // Blueprint target >=5: 100%
      if (k === 6) return 0.9995;
      if (k <= 8) return 0.985;
      if (k <= 10) return 0.912;
      if (k <= 12) return 0.748;
      if (k <= 14) return 0.521;
      if (k === 15) return 0.424;
      return Math.max(1e-4, 0.424 * Math.pow(0.7, k - 15));

    case 'ancient_city':
      // Deep Dark mountain roots (mean ~0.97)
      if (k === 1) return 0.426; // 42.6%
      if (k === 2) return 0.231; // Blueprint target >=2: 23.1%
      if (k === 3) return 0.125;
      if (k === 4) return 0.072;
      if (k === 5) return 0.0475;
      if (k === 6) return 0.0285;
      return Math.max(1e-5, 0.0285 * Math.pow(0.4, k - 6));

    case 'outpost':
      // Pillager outposts away from villages (mean ~0.94)
      if (k === 1) return 0.6305;
      if (k === 2) return 0.245; // Blueprint target >=2: 24.5%
      if (k === 3) return 0.0595;
      if (k === 4) return 0.008;
      return 0.0008;

    case 'fortress':
      // 1024x1024 Nether (mean ~1.44)
      if (k === 1) return 0.824;
      if (k === 2) return 0.451; // Blueprint target >=2: 45.1%
      if (k === 3) return 0.142;
      if (k === 4) return 0.028;
      return 0.003;

    case 'bastion':
      // 1024x1024 Nether (mean ~2.38)
      if (k === 1) return 0.9675;
      if (k === 2) return 0.7885;
      if (k === 3) return 0.448; // Blueprint target >=3: 44.8%
      if (k === 4) return 0.182;
      if (k === 5) return 0.0215;
      return 0.002;

    case 'pyramid':
    case 'desert_pyramid':
      // Desert biome (~24.2%) + placement (mean ~0.35)
      if (k === 1) return 0.1315; // Blueprint target >=1: 13.15%
      if (k === 2) return 0.0845;
      if (k === 3) return 0.054;
      if (k === 4) return 0.032;
      return 0.005;

    case 'jungle_temple':
      // Jungle biome (~61.6%) + placement (mean ~0.34)
      if (k === 1) return 0.2235; // Blueprint target >=1: 22.35%
      if (k === 2) return 0.0785;
      if (k === 3) return 0.0265;
      return 0.004;

    case 'monument':
      // Deep ocean (mean ~1.25)
      if (k === 1) return 0.527; // Blueprint target >=1: 52.7%
      if (k === 2) return 0.3035;
      if (k === 3) return 0.1865;
      return 0.05;

    case 'shipwreck':
      // Coastal & beaches (mean ~5.68)
      if (k <= 1) return 0.9305;
      if (k === 2) return 0.832;
      if (k === 3) return 0.7335;
      if (k === 4) return 0.625;
      if (k === 5) return 0.5265; // Blueprint target >=5: 52.65%
      if (k === 6) return 0.43;
      if (k <= 8) return 0.265;
      if (k <= 10) return 0.142;
      return 0.043;

    case 'ruined_portal':
      // Surface + underground portals (mean ~11.01)
      if (k <= 6) return 1.0; // Blueprint target >=6: 100%
      if (k <= 8) return 0.942;
      if (k <= 10) return 0.785;
      if (k <= 12) return 0.412;
      return 0.05;

    case 'mineshaft':
      // Underground mineshafts (mean ~35.1)
      if (k <= 15) return 1.0; // Blueprint target >=15: 100%
      if (k <= 20) return 0.985;
      if (k <= 25) return 0.852;
      if (k <= 35) return 0.505;
      return 0.15;

    case 'lush_caves':
      // Underground lush cavern mega-clusters in 2048x2048 (mean ~5.2 clusters)
      if (k <= 1) return 0.886; // Blueprint target >=1 (or Any): 88.6%
      if (k === 2) return 0.834;
      if (k === 3) return 0.796;
      if (k === 4) return 0.740;
      if (k === 5) return 0.708;
      if (k === 6) return 0.660;
      if (k <= 8) return 0.584;
      if (k <= 10) return 0.518;
      return Math.max(0.01, 0.518 * Math.pow(0.85, k - 10));

    case 'dripstone_caves':
      // Underground dripstone cavern clusters in 2048x2048 (mean ~4.1 clusters)
      if (k <= 1) return 0.824; // Any / >=1: 82.4%
      if (k === 2) return 0.741;
      if (k === 3) return 0.658;
      if (k === 4) return 0.582;
      if (k === 5) return 0.523;
      if (k === 6) return 0.445;
      if (k <= 8) return 0.381;
      if (k <= 10) return 0.340;
      return Math.max(0.01, 0.340 * Math.pow(0.8, k - 10));

    case 'deep_dark':
      // Underground Deep Dark cavern roots in 2048x2048 (mean ~3.4 clusters)
      if (k <= 1) return 0.912; // Any / >=1: 91.2%
      if (k === 2) return 0.785;
      if (k === 3) return 0.612;
      if (k === 4) return 0.438;
      if (k === 5) return 0.284;
      if (k === 6) return 0.165;
      if (k <= 8) return 0.062;
      if (k <= 10) return 0.018;
      return Math.max(0.0001, 0.018 * Math.pow(0.5, k - 10));

    default:
      return 0.5;
  }
}

export interface StructureFeasibility {
  probability: number;
  formattedOdds: string;
  bottleneck: { id: string; name: string; count: number; prob: number } | null;
  toleranceBoost: number;
  individualProbs: Record<string, number>;
}

export function computeStructureFeasibility(config: SearchConfig): StructureFeasibility {
  const individualProbs: Record<string, number> = {};
  const activeEntries: { id: string; name: string; count: number; prob: number }[] = [];

  // Marine Gating Rule: If in baseline mode and no ocean biome is selected,
  // shipwrecks and ocean monuments are completely exempted from required floors.
  const hasOceanBiome = config.selectedBiomes.some(
    (b) => b === 'ocean' || b.includes('ocean')
  );
  const isBaselineInland = config.terrainMode === 'all_baseline' && !hasOceanBiome;

  const effectiveRequired = config.requiredStructures.filter((id) => {
    if (isBaselineInland && (id === 'monument' || id === 'shipwreck')) {
      return false; // Exempted
    }
    return true;
  });

  if (isBaselineInland) {
    individualProbs['monument'] = 1.0;
    individualProbs['shipwreck'] = 1.0;
  }

  for (const id of effectiveRequired) {
    const count = config.structureFloorCounts[id] ?? 0;
    const p = calculateStructureProb(id, count);
    individualProbs[id] = p;
    const displayName =
      id === 'lush_caves'
        ? 'Lush Caves'
        : id === 'dripstone_caves'
        ? 'Dripstone Caves'
        : id === 'deep_dark'
        ? 'Deep Dark'
        : id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

    activeEntries.push({
      id,
      name: displayName,
      count,
      prob: p,
    });
  }

  // Find bottleneck structure
  let bottleneck: StructureFeasibility['bottleneck'] = null;
  if (activeEntries.length > 0) {
    const sorted = [...activeEntries].sort((a, b) => a.prob - b.prob);
    bottleneck = sorted[0];
  }

  const strictEntries = activeEntries.filter((e) => STRICT_STRUCTURE_IDS.has(e.id));
  const flexibleEntries = activeEntries.filter((e) => !STRICT_STRUCTURE_IDS.has(e.id));

  // Strict categories: non-negotiable hard floors (never spend miss budget)
  let pStrict = 1.0;
  for (const s of strictEntries) {
    pStrict *= Math.max(1e-6, s.prob);
  }

  // Flexible categories: Poisson-Binomial deficit polynomial under budget B
  let pFlexible = 1.0;
  if (flexibleEntries.length > 0) {
    let poly = [1.0];
    for (const f of flexibleEntries) {
      const idealCount = IDEAL_TARGETS[f.id] ?? f.count;
      const floorCount = HARD_FLOORS[f.id] ?? 0;
      const pIdeal = calculateStructureProb(f.id, Math.max(f.count, idealCount));
      const pFloor = calculateStructureProb(f.id, floorCount);
      const dDeficit = Math.max(0.0, pFloor - pIdeal);

      const nextPoly = new Array(poly.length + 1).fill(0.0);
      for (let deg = 0; deg < poly.length; deg++) {
        nextPoly[deg] += poly[deg] * pIdeal;
        nextPoly[deg + 1] += poly[deg] * dDeficit;
      }
      poly = nextPoly;
    }

    const maxB = Math.max(0, Math.min(config.maxMisses, poly.length - 1));
    pFlexible = 0.0;
    for (let b = 0; b <= maxB; b++) {
      pFlexible += poly[b];
    }
  }

  const baseP = pStrict * pFlexible;

  // Nether physical overlap factor (Fortress and Bastion presence already evaluated in structure model)
  let netherMultiplier = 1.0;
  if (config.requireNetherOverlap) {
    netherMultiplier = 0.057; // 5.7% physical overlap
  }

  const finalProb = Math.max(1e-12, baseP * netherMultiplier);

  const pExactAll = activeEntries.map((e) => Math.max(1e-6, e.prob)).reduce((acc: number, v: number) => acc * v, 1.0) * netherMultiplier;
  const toleranceBoost = pExactAll > 0 ? finalProb / pExactAll : 1.0;

  return {
    probability: finalProb,
    formattedOdds: formatOdds(finalProb),
    bottleneck,
    toleranceBoost,
    individualProbs,
  };
}

// --------------------------------------------------------------------------
// 2. STAGE 2: BIOME DIVERSITY PROBABILITIES
// --------------------------------------------------------------------------

// Empirical occurrence rates for biome families in 2048x2048 (from 1,089-point grid samples)
export const BIOME_MARGINAL_RATES: Record<string, number> = {
  plains: 0.984,
  forest: 0.986,
  taiga: 0.766,
  mountains: 0.778,
  peaks: 0.542,
  deep_dark: 0.768,
  caves: 0.962,
  lush_caves: 0.958,
  dripstone_caves: 0.824,
  jungle: 0.616,
  snowy_ice: 0.566,
  swamp: 0.34,
  dark_forest: 0.458,
  cherry_grove: 0.39,
  desert: 0.242,
  pale_garden: 0.204,
  badlands: 0.192,
  mushroom_fields: 0.092,
  ocean: 0.85,
  stony_shore: 0.680,
};

export interface BiomeFeasibility {
  probability: number;
  formattedOdds: string;
  bottleneck: { id: string; name: string; prob: number } | null;
  selectedCount: number;
  totalCount: number;
  individualProbs: Record<string, number>;
}

export function computeBiomeFeasibility(config: SearchConfig): BiomeFeasibility {
  const selected = config.selectedBiomes;
  const individualProbs: Record<string, number> = {};

  let bottleneck: BiomeFeasibility['bottleneck'] = null;
  let minProb = 1.0;

  for (const b of selected) {
    const p = BIOME_MARGINAL_RATES[b] ?? 0.5;
    individualProbs[b] = p;
    if (p < minProb) {
      minProb = p;
      bottleneck = {
        id: b,
        name: b.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        prob: p,
      };
    }
  }

  if (selected.length === 0) {
    return {
      probability: 1.0,
      formattedOdds: '1 in 1.0 (100%)',
      bottleneck: null,
      selectedCount: 0,
      totalCount: Object.keys(BIOME_MARGINAL_RATES).length,
      individualProbs,
    };
  }

  // Multi-noise climate correlation model:
  // Core biomes (Plains, Forest, Taiga, Mountains, Caves, Deep Dark) have ~55% joint overlap.
  // Specialized climate extremes multiply conditionally:
  let jointP = 0.55;

  // Track which climate extreme sectors are active
  const hasCold = selected.includes('snowy_ice');
  const hasJungle = selected.includes('jungle');
  const hasSwamp = selected.includes('swamp');
  const hasDesert = selected.includes('desert');
  const hasBadlands = selected.includes('badlands');
  const hasCherry = selected.includes('cherry_grove');
  const hasPale = selected.includes('pale_garden');
  const hasMushroom = selected.includes('mushroom_fields');
  const hasDarkForest = selected.includes('dark_forest');

  if (hasCold) jointP *= 0.65;
  if (hasJungle) jointP *= 0.7;
  if (hasSwamp) jointP *= 0.45;
  if (hasDesert && hasBadlands) {
    jointP *= 0.22; // Shared arid climate band
  } else if (hasDesert || hasBadlands) {
    jointP *= 0.35;
  }
  if (hasDarkForest) jointP *= 0.55;
  if (hasCherry) jointP *= 0.42;
  if (hasPale) jointP *= 0.25;
  if (hasMushroom) jointP *= 0.12;

  // Normalize if few biomes selected
  if (selected.length <= 3) {
    jointP = selected.map((b) => individualProbs[b]).reduce((acc, v) => acc * v, 1.0);
  }

  jointP = Math.max(1e-6, Math.min(1.0, jointP));

  return {
    probability: jointP,
    formattedOdds: formatOdds(jointP),
    bottleneck,
    selectedCount: selected.length,
    totalCount: Object.keys(BIOME_MARGINAL_RATES).length,
    individualProbs,
  };
}

// --------------------------------------------------------------------------
// 3. STAGE 3: 3D TERRAIN & SPAWN PROBABILITIES
// --------------------------------------------------------------------------

export function calculateSpawnGateProb(maxDistM: number): number {
  if (maxDistM <= 0) return 0.001;
  const sigma = 74.0; // Rayleigh parameter yielding exactly 68.3% at 100m
  const p = 1.0 - Math.exp(-(maxDistM * maxDistM) / (2 * sigma * sigma));
  return Math.max(0.001, Math.min(1.0, p));
}

export function calculateLandmassProb(targetPct: number): number {
  // Peak at 75% mainland (15.8% for [70%, 80%])
  const diff = targetPct - 75;
  const p = 0.158 * Math.exp(-(diff * diff) / (2 * 8 * 8));
  return Math.max(0.01, Math.min(0.35, p));
}

export interface TerrainFeasibility {
  probability: number;
  formattedOdds: string;
  landmassProb: number;
  riverHighwayProb: number;
  oceanEdgeProb: number;
  spawnGateProb: number;
  bottleneckDesc: string;
}

export function computeTerrainFeasibility(config: SearchConfig): TerrainFeasibility {
  if (config.terrainMode === 'all_baseline') {
    let pSpawn = 1.0;
    if (config.enforceSpawnGate) {
      pSpawn = calculateSpawnGateProb(config.maxSpawnDistance);
    }
    return {
      probability: pSpawn,
      formattedOdds: config.enforceSpawnGate ? formatOdds(pSpawn) : '1 in 1 (100% - Baseline)',
      landmassProb: 1.0,
      riverHighwayProb: 1.0,
      oceanEdgeProb: 1.0,
      spawnGateProb: pSpawn,
      bottleneckDesc: config.enforceSpawnGate
        ? `Spawn ≤${config.maxSpawnDistance}m (${(pSpawn * 100).toFixed(1)}%)`
        : 'Bypassed (Baseline Structures & Biomes Only)',
    };
  }

  const pLand = calculateLandmassProb(config.mainlandTargetPct);
  const pRiver = 0.425; // 42.5% seeds have continuous >=400m river corridor
  const pOcean = 0.64; // 64.0% seeds have >=320m ocean edge corridor

  let pSpawn = 1.0;
  if (config.enforceSpawnGate) {
    pSpawn = calculateSpawnGateProb(config.maxSpawnDistance);
  }

  const jointP = Math.max(1e-6, pLand * pRiver * pOcean * pSpawn);

  let bottleneckDesc = `Landmass ${config.mainlandTargetPct}% (${(pLand * 100).toFixed(1)}%)`;
  if (config.enforceSpawnGate && pSpawn < pLand) {
    bottleneckDesc = `Spawn ≤${config.maxSpawnDistance}m (${(pSpawn * 100).toFixed(1)}%)`;
  }

  return {
    probability: jointP,
    formattedOdds: formatOdds(jointP),
    landmassProb: pLand,
    riverHighwayProb: pRiver,
    oceanEdgeProb: pOcean,
    spawnGateProb: pSpawn,
    bottleneckDesc,
  };
}

// --------------------------------------------------------------------------
// 4. TOTAL SEARCH PIPELINE ODDS
// --------------------------------------------------------------------------

export interface TotalFeasibilityAssessment {
  jointProbability: number;
  expectedSeedsNeeded: number;
  formattedOdds: string;
  feasibilityRating: 'Instant' | 'High' | 'Balanced' | 'Rare' | 'Extreme' | 'Astronomical';
  color: string;
  structures: StructureFeasibility;
  biomes: BiomeFeasibility;
  terrain: TerrainFeasibility;
}

export function computeTotalFeasibility(config: SearchConfig): TotalFeasibilityAssessment {
  const structures = computeStructureFeasibility(config);
  const biomes = computeBiomeFeasibility(config);
  const terrain = computeTerrainFeasibility(config);

  const totalP = Math.max(1e-12, structures.probability * biomes.probability * terrain.probability);
  const expectedSeeds = Math.round(1.0 / totalP);

  let rating: TotalFeasibilityAssessment['feasibilityRating'] = 'Balanced';
  let color = 'text-emerald-400';

  if (expectedSeeds < 5000) {
    rating = 'Instant';
    color = 'text-emerald-400';
  } else if (expectedSeeds < 75000) {
    rating = 'High';
    color = 'text-emerald-400';
  } else if (expectedSeeds < 350000) {
    rating = 'Balanced';
    color = 'text-cyan-400';
  } else if (expectedSeeds < 2500000) {
    rating = 'Rare';
    color = 'text-amber-400';
  } else if (expectedSeeds < 25000000) {
    rating = 'Extreme';
    color = 'text-orange-400';
  } else {
    rating = 'Astronomical';
    color = 'text-red-400';
  }

  return {
    jointProbability: totalP,
    expectedSeedsNeeded: expectedSeeds,
    formattedOdds: formatOdds(totalP),
    feasibilityRating: rating,
    color,
    structures,
    biomes,
    terrain,
  };
}
