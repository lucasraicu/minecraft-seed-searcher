import profiles from './searchProfiles.json';

export type SearchProfileName = keyof typeof profiles;
export interface SearchProfile {
  name: string;
  revision: string;
  counts: Record<string, number>;
  floors: Record<string, number>;
  flexible: string[];
  overworldSide: number;
  netherSide: number;
  maxMisses: number;
  deferredMarine: boolean;
}
export const SEARCH_PROFILES: Record<SearchProfileName, SearchProfile> = profiles;
export const getSearchProfile = (name: SearchProfileName): SearchProfile => SEARCH_PROFILES[name];

/** Read historical UI aliases once; internal state and API payloads are canonical. */
export function normalizeStructureCounts(counts: Record<string, number>): Record<string, number> {
  const { pyramid, ...canonical } = counts;
  if (canonical.desert_pyramid == null && pyramid != null) canonical.desert_pyramid = pyramid;
  return canonical;
}

export function normalizeStructureKeys(keys: string[]): string[] {
  return [...new Set(keys.map((key) => key === 'pyramid' ? 'desert_pyramid' : key))];
}
