import type { SeedCandidate } from '../types';

const cmpId = (x: string, y: string) => (x < y ? -1 : x > y ? 1 : 0);

/** Match the saved-run leaderboard; user-selected alternate sorts remain separate. */
export function compareCandidateRank(a: SeedCandidate, b: SeedCandidate): number {
  if ((a.screeningRevision === 'dynamic-envelope-1664-v2' || a.screeningRevision === 'dynamic-envelope-2048-v3') && b.screeningRevision === a.screeningRevision) {
    const primary = (a.rankingTier ?? 99) - (b.rankingTier ?? 99)
      || (b.score ?? -Infinity) - (a.score ?? -Infinity)
      || (a.unmetRequirements ?? 0) - (b.unmetRequirements ?? 0)
      || (a.radialKey ?? (a.weightedRadialDistance != null ? Math.round(a.weightedRadialDistance * 1e6) : Infinity))
       - (b.radialKey ?? (b.weightedRadialDistance != null ? Math.round(b.weightedRadialDistance * 1e6) : Infinity))
      || (a.originDistanceSquared ?? (a.originDistance != null ? Math.round(a.originDistance ** 2) : Infinity))
       - (b.originDistanceSquared ?? (b.originDistance != null ? Math.round(b.originDistance ** 2) : Infinity))
      || (a.evaluationCenter?.[0] ?? 0) - (b.evaluationCenter?.[0] ?? 0)
      || (a.evaluationCenter?.[1] ?? 0) - (b.evaluationCenter?.[1] ?? 0)
      || cmpId(a.id, b.id);
    return primary;
  }
  const primary = (a.rankingTier ?? 99) - (b.rankingTier ?? 99)
    || (a.unmetRequirements ?? 0) - (b.unmetRequirements ?? 0)
    || (b.score ?? -Infinity) - (a.score ?? -Infinity);
  if (primary) return primary;
  if (a.screeningRevision === 'dynamic-envelope-1664-v1' && b.screeningRevision === a.screeningRevision) {
    const distance = (a.weightedRadialDistance ?? Infinity) - (b.weightedRadialDistance ?? Infinity)
      || (a.originDistance ?? Infinity) - (b.originDistance ?? Infinity);
    if (distance) return distance;
  }
  return cmpId(a.id, b.id);
}
