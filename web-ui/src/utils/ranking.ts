import type { SeedCandidate } from '../types';

/** Match the saved-run leaderboard; user-selected alternate sorts remain separate. */
export function compareCandidateRank(a: SeedCandidate, b: SeedCandidate): number {
  const primary = (a.rankingTier ?? 99) - (b.rankingTier ?? 99)
    || (a.unmetRequirements ?? 0) - (b.unmetRequirements ?? 0)
    || (b.score ?? -1) - (a.score ?? -1);
  if (primary) return primary;
  if (a.screeningRevision === 'dynamic-envelope-1664-v1' && b.screeningRevision === a.screeningRevision) {
    const distance = (a.weightedRadialDistance ?? Infinity) - (b.weightedRadialDistance ?? Infinity)
      || (a.originDistance ?? Infinity) - (b.originDistance ?? Infinity);
    if (distance) return distance;
  }
  return a.id.localeCompare(b.id);
}
