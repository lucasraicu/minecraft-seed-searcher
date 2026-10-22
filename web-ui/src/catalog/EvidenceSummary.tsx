export interface StructureEvidenceSummary {
  revision: 'catalog-structure-evidence-summary-v1';
  feature_id: string;
  predicted_count: number;
  tested_count: number;
  located_exact: number;
  coordinate_difference: number;
  no_location: number;
  errors: number;
  untested_count: number;
  grouped_command: boolean;
  verifier_game_build_id: string | null;
  generated_count: null;
  exhaustive_count: null;
}


/** Per-feature counts for the selected scope; no inference about unobserved buildings. */
export function EvidenceSummary({summary}: {summary: StructureEvidenceSummary | null | undefined}) {
  if (!summary) return <p className="text-xs text-slate-400" aria-label="Bedrock evidence summary">
    Not checked in BDS. Untested evidence does not imply 0 structures.
  </p>;
  const unresolved = summary.coordinate_difference + summary.no_location + summary.errors;
  return <section aria-label="Bedrock evidence summary" className="rounded-lg border border-slate-700 bg-slate-900/60 p-3 text-xs space-y-2">
    <p className="text-slate-300">{`${summary.predicted_count} predicted`}
      {summary.tested_count > 0 && <span>{` · BDS ${summary.verifier_game_build_id}`}</span>}</p>
    {summary.tested_count === 0 ? <p className="text-slate-400">
      {`Not checked in BDS · ${summary.untested_count} untested. Untested evidence does not imply 0 structures.`}
    </p> : <>
      <p className="flex flex-wrap gap-x-4 gap-y-1">
        <span className="text-emerald-300">{`${summary.located_exact} BDS exact-location matches`}</span>
        <span className={unresolved ? 'text-amber-300' : 'text-slate-400'}>{`${unresolved} unresolved`}</span>
        <span className="text-slate-400">{`${summary.untested_count} untested`}</span>
      </p>
      {unresolved > 0 && <details className="text-slate-400">
        <summary className="cursor-pointer">Check details</summary>
        <p>{`coordinate difference: ${summary.coordinate_difference}; no location: ${summary.no_location}; errors: ${summary.errors}. These results do not indicate physical absence.`}</p>
      </details>}
    </>}
    {summary.grouped_command && <p className="text-amber-200">BDS checks generic temple locations, not specific subtypes.</p>}
    <p className="text-slate-400">Counts are not an exhaustive generated-building census.</p>
  </section>;
}
