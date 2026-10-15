import type { SeedCandidate } from '../types';

// Evaluate the radius before display rounding (100.04 blocks is outside 100).
export function spawnWithinRadius(candidate: SeedCandidate, radius: number): boolean | null {
  const point = candidate.spawnPoint;
  if (!point || !point.every(Number.isFinite)) return null;
  const center = candidate.evaluationCenter ?? [0, 0];
  return Math.hypot(point[0] - center[0], point[1] - center[1]) <= radius;
}

export function spawnEvidenceLabel(candidate: SeedCandidate): string {
  if (!candidate.spawnPoint) return 'Unknown';
  const evidence = candidate.spawnEvidence;
  if (evidence?.source?.kind === 'actual_generation' && evidence.evidence_kind === 'actual_initial_player_placement') {
    return 'Observed initial-player spawn';
  }
  if (evidence?.source?.kind === 'predictor') return 'Predicted spawn';
  return 'Unverified spawn';
}
