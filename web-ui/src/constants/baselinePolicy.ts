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
