import type { StructureEvidenceSummary } from './EvidenceSummary';

/**
 * Type definitions for Private Catalog UI and HTTP contract.
 * Conforms to reviews/catalog-private-pilot-2026-10-20/INTERFACES.md.
 */

export type BorderSide = 2048 | 4096 | 8192;
export type AnchorMode = 'recommended' | 'origin' | 'world_spawn_estimated' | 'world_spawn_observed';
export interface AnchorEvidence {mode: AnchorMode; coordinate: [number,number]; y:null; semantics:string; anchor_id:string; context:Record<string,unknown>}
export type Dimension = 'overworld' | 'nether';
export type OverworldNearRadius = 256 | 512 | 1024;
export type NetherNearRadius = 64 | 128 | 256;
export type NearRadius = 64 | 128 | 256 | 512 | 1024;
export type FilterRule = 'required' | 'preferred';
export type FilterKind = 'structure_count' | 'biome_witness';
export type ScopeKind = 'inside_border' | 'near_base';

export interface FilterScope {
  kind: ScopeKind;
  radius?: NearRadius;
}

export interface StructureFilterRow {
  id: string;
  rule: FilterRule;
  kind: 'structure_count';
  feature: string;
  at_least: number; // 1..16
  importance?: number; // 1..5
  scope: FilterScope;
}

export interface BiomeFilterRow {
  id: string;
  rule: FilterRule;
  kind: 'biome_witness';
  any_of: string[]; // biome OR list
  importance?: number; // 1..5
  scope: FilterScope;
}

export type FilterRow = StructureFilterRow | BiomeFilterRow;
export type PresetRow = Omit<StructureFilterRow,'id'> | Omit<BiomeFilterRow,'id'>;

export interface FeatureV3Metadata {
  id: string;
  label: string;
  kind: 'structure_count' | 'biome_witness';
  dimension: Dimension;
  category: string;
  available: boolean;
  unavailable_reason: string | null;
  eligible_y?: number[];
  canonical_members?: string[];
  atomic_members?: string[];
}

export interface CatalogPreset {
  id: string;
  label: string;
  fallback_profile: string;
  rows: PresetRow[];
  editable?: boolean;
  adds_hidden_requirements?: boolean;
}

export interface CatalogProfile {
  id: string;
  label?: string;
}

export interface CatalogStatusResponse {
  anchor_modes?:AnchorMode[];
  ok: boolean;
  available: boolean;
  revision?: string;
  snapshot_id?: string;
  worlds?: number;
  layouts?: number;
  header?: Record<string, unknown>;
  reason?: string;
  error?: string;
  code?: string;
}

export interface CatalogCapabilitiesResponse {
  snapshot_id?: string;
  ok: boolean;
  revision?: string;
  registry?: {
    categories?: Array<{id:string;label:string}>;
    features?: Array<{id:string;label:string;kind:string;slot:number}>;
  };
  registry_v2?: Record<string, unknown>;
  registry_v3?: {
    revision?: string;
    features?: FeatureV3Metadata[];
    categories?: Array<{id:string;label:string}>;
    [key: string]: unknown;
  };
  request_revision?: string;
  reserve_policy?: {
    reserve_factor: number;
    historically_complete: boolean;
  };
  primary_count?: number;
  reserve_count?: number;
  nether_near_radii?: NearRadius[];
  presets?: CatalogPreset[];
  profiles?: CatalogProfile[];
  border_sides?: BorderSide[];
  near_radii?: NearRadius[];
  anchor_modes?: AnchorMode[];
  max_rows?: number;
  max_compare?: number;
  evidence_label?: string;
  error?: string;
  code?: string;
}

export interface CatalogSnapshotInfo {
  anchor_modes?:AnchorMode[];
  revision?: string;
  accuracy_generation?: string;
  accuracy_anchor_modes?: AnchorMode[];
  snapshot_id: string;
  worlds: number;
  layouts: number;
  header: Record<string, unknown>;
}

export interface CatalogSnapshotsResponse {
  ok: boolean;
  snapshots: CatalogSnapshotInfo[];
  error?: string;
  code?: string;
}

export interface CatalogQueryPayload {
  request_revision: 'catalog-query-v1' | 'catalog-query-accuracy-v1' | 'catalog-query-v2' | 'catalog-query-v3';
  accuracy_generation?: string;
  edition: 'bedrock';
  dimension: 'overworld';
  game_build_id: string;
  world_settings_id: string;
  catalog_snapshot_id: string;
  evidence_policy: 'predicted_observations_v1' | 'predicted_plus_refined_witnesses_v1' | 'predicted_observations_v2' | 'predicted_observations_v3';
  fallback_profile: string;
  border_side: BorderSide;
  anchor_mode: AnchorMode;
  rows: Array<Record<string,unknown>>;
}

export interface CatalogQueryRequestBody {
  request: CatalogQueryPayload;
  page_size?: number;
  cursor?: string | null;
}

export interface CatalogCandidate {
  anchor_evidence?: AnchorEvidence;
  accuracy_generation?: string;
  snapshot_id?:string;
  world_id: string;
  seed: string; // Full long string. UI never converts to Number(seed)
  layout_id: string;
  anchor: [number, number] | string;
  nether_anchor?: [number, number] | string;
  border_side: BorderSide;
  score: number;
  utility_units: number | string;
  distance_tie: number;
  contributions: Array<{feature?:string;kind?:string;any_of?:string[];utility_units:number;max_units:number;status?:string}>;
  counts?: number[][] | number[];
  feature_counts?: Record<string, number> | number[] | Record<string, unknown>;
  structure_nearest_d2?: number[];
  biome_nearest_d2?: number[];
  complete?: boolean[][] | boolean[];
  feature_complete?: Record<string, boolean> | boolean[] | Record<string, unknown>;
  bounds: [number, number, number, number]; // [lox, loz, hix, hiz]
}

export interface CatalogQueryResponse {
  accuracy_generation?:string;
  unresolved_worlds?:number;
  unresolved_candidates?:Array<{world_id:string;seed:string;layout_id:string;anchor:number[];border_side:number;status:string;reason:string}>;
  ok: boolean;
  snapshot_id: string;
  request_sha256: string;
  results: CatalogCandidate[];
  next_cursor: string | null;
  truncated: boolean;
  matched_worlds: number;
  primary_count?: number;
  reserve_count?: number;
  stats: Record<string, unknown>;
  evidence_label: string;
  error?: string;
  code?: string;
}

export interface BiomeWitnessPoint {
  feature: string;
  x: number;
  y: number;
  z: number;
  distance_squared: number;
}

export interface CatalogDetailResponse {
  nether_structures?:Record<string,[number,number][]>;
  nether_bounds?:[number,number,number,number];
  nether_biome_witnesses?:BiomeWitnessPoint[];
  structures_truncated?:boolean;
  anchor_roles?:AnchorEvidence[];
  accuracy?: {generation:string;interpretation:string;tiles:Array<{tile_id:string;provider:string;provider_id:string;bounds:number[];y:number;biome_names:Record<string,string>}>} | null;
  anchor_evidence?: AnchorEvidence | null;
  ok: boolean;
  snapshot_id: string;
  world_id: string;
  identity: Record<string, unknown>;
  layout: {
    border_side: number;
    anchor: [number, number] | string;
    anchor_mode?: AnchorMode;
    [key: string]: unknown;
  };
  structures: Record<string, [number, number][]>;
  structure_evidence?: Record<string, StructureEvidenceSummary>;
  biome_evidence?: {
    method: string; interpretation: string; verifier_game_build_id: string | null;
    checks: Array<{position: [number, number, number]; observed_name: string | null; outcome: string}>;
  };
  biome_witnesses: BiomeWitnessPoint[];
  coverage: Record<string, unknown>;
  evidence_label: string;
  error?: string;
  code?: string;
}

export interface CatalogFavorite {
  id: string; // `${snapshot_id}:${world_id}:${layout_id}`
  seed: string;
  world_id: string;
  snapshot_id: string;
  layout_id: string;
  border_side: BorderSide;
  anchor_mode: AnchorMode;
  score: number;
  saved_at: number;
  bounds?: [number, number, number, number];
  tags?: string[];
  notes?: string;
}

export interface FeedbackExportPayload {
  schema_version: 'catalog-query-feedback-v1';
  exported_at: string;
  snapshot_id: string;
  evidence_label: string;
  request: CatalogQueryPayload;
  user_notes: string;
  results_summary: {
    total_matched: number;
    returned_count: number;
    candidates: Array<{
      world_id: string;
      seed: string;
      score: number;
      border_side: BorderSide;
    }>;
  };
}
