import type { StructureEvidenceSummary } from './EvidenceSummary';

/** Reject contradictory verification counts before presenting a BDS badge. */
export function validStructureEvidence(
  value: unknown, expectedCount?: number, expectedFeature?: string,
): value is StructureEvidenceSummary {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const row = value as Record<string, unknown>;
  const counts = ['predicted_count', 'tested_count', 'located_exact', 'coordinate_difference',
    'no_location', 'errors', 'untested_count'];
  if (counts.some(key => typeof row[key] !== 'number' || !Number.isSafeInteger(row[key]) ||
      (row[key] as number) < 0 || (row[key] as number) > 200000)) return false;
  if (row.revision !== 'catalog-structure-evidence-summary-v1' ||
      typeof row.feature_id !== 'string' || !/^structure\.[a-z_]+$/.test(row.feature_id) ||
      (expectedFeature !== undefined && row.feature_id !== expectedFeature) ||
      (expectedCount !== undefined && row.predicted_count !== expectedCount) ||
      row.generated_count !== null || row.exhaustive_count !== null) return false;
  if ((row.located_exact as number) + (row.coordinate_difference as number) +
      (row.no_location as number) + (row.errors as number) !== row.tested_count ||
      (row.tested_count as number) + (row.untested_count as number) !== row.predicted_count) return false;
  const grouped = ['structure.desert_pyramid', 'structure.jungle_temple', 'structure.swamp_hut', 'structure.igloo'];
  if (row.grouped_command !== grouped.includes(row.feature_id)) return false;
  if (row.verifier_game_build_id === null) return row.tested_count === 0;
  return typeof row.verifier_game_build_id === 'string' && row.verifier_game_build_id.length > 0 &&
    row.verifier_game_build_id.length <= 128 && !row.verifier_game_build_id.startsWith('research:');
}
