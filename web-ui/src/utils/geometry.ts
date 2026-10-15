import type { Dimension, SeedCandidate } from '../types';
import { SEARCH_PROFILES, getSearchProfile } from '../constants/baselinePolicy';
import type { SearchProfileName } from '../constants/baselinePolicy';

export function playableBounds(candidate: SeedCandidate | null, dimension: Dimension, profile: SearchProfileName): [number, number, number, number] {
  const exact = candidate?.playableBounds?.final_nether_exact;
  if (dimension === 'nether' && exact && exact.length === 4 && exact.every((pair) => pair.length === 2 && pair.every(Number.isFinite) && pair[1] > 0)) {
    return exact.map((pair) => pair[0] / pair[1]) as [number, number, number, number];
  }
  const reported = dimension === 'overworld' ? candidate?.playableBounds?.overworld : candidate?.playableBounds?.final_nether;
  if (reported && reported.length === 4 && reported.every(Number.isFinite) && reported[2] > reported[0] && reported[3] > reported[1]) return reported;
  const policy = Object.values(SEARCH_PROFILES).find((item) => item.revision === candidate?.screeningRevision) ?? getSearchProfile(profile);
  const center = candidate?.evaluationCenter ?? candidate?.strongholdAnchor ?? [0, 0];
  const scale = dimension === 'overworld' ? 1 : 1 / 8;
  const half = (dimension === 'overworld' ? policy.overworldSide : policy.netherSide) / 2;
  return [center[0] * scale - half, center[1] * scale - half, center[0] * scale + half, center[1] * scale + half];
}
