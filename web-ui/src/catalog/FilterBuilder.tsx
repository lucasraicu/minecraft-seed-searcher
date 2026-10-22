import { useState } from 'react';
import type { FilterRow, FilterRule, FilterKind, ScopeKind, NearRadius, Dimension, StructureFilterRow, BiomeFilterRow, FeatureV3Metadata } from './types';
import {
  KNOWN_STRUCTURES,
  KNOWN_BIOMES,
  NEAR_RADII,
  OVERWORLD_NEAR_RADII,
  NETHER_NEAR_RADII,
  V2_STRUCTURES,
  V2_BIOMES,
  V3_STRUCTURES,
  V3_BIOME_GROUPS,
  V3_EXACT_BIOMES,
  V3_ALL_BIOMES,
  MAX_FILTER_ROWS,
  MAX_FILTER_ROW_ALTERNATIVES,
  DEFAULT_OVERWORLD_NEAR_RADIUS,
  DEFAULT_NETHER_NEAR_RADIUS,
  getFeatureDimension,
  normalizeRadiusForDimension,
  getFeatureV3Metadata,
  type FeatureOption,
} from './constants';

export interface FilterBuilderProps {
  rows: FilterRow[];
  onChangeRows: (rows: FilterRow[]) => void;
  onResetRows: () => void;
  enableV2?: boolean;
  enableV3?: boolean;
  features?: FeatureV3Metadata[];
}

/**
 * Determine the effective dimension of a filter row.
 * For structure_count: based on the structure's dimension metadata.
 * For biome_witness: based on the biomes in any_of (Nether if any Nether biome is present).
 */
export function getRowDimension(row: FilterRow): Dimension {
  if (row.kind === 'structure_count') {
    return getFeatureDimension(row.feature);
  }
  if (row.kind === 'biome_witness') {
    if (row.any_of && row.any_of.length > 0) {
      return row.any_of.some(b => getFeatureDimension(b) === 'nether') ? 'nether' : 'overworld';
    }
  }
  return 'overworld';
}

/**
 * Pure helper to switch feature on a structure row.
 * If switching dimension in V2/V3, normalizes incompatible radius to 512 (OW) or 128 (Nether),
 * retaining compatible radius (e.g. 256) and all other choices (rule, at_least, importance).
 */
export function switchRowFeature(
  row: StructureFilterRow,
  newFeature: string,
  enableV2 = false,
  enableV3 = false
): StructureFilterRow {
  if (!enableV2 && !enableV3) {
    return { ...row, feature: newFeature };
  }
  const oldDim = getFeatureDimension(row.feature);
  const newDim = getFeatureDimension(newFeature);
  if (oldDim === newDim || row.scope.kind !== 'near_base') {
    return { ...row, feature: newFeature };
  }
  const normalizedRadius = normalizeRadiusForDimension(newDim, row.scope.radius);
  return {
    ...row,
    feature: newFeature,
    scope: {
      kind: 'near_base',
      radius: normalizedRadius,
    },
  };
}

/**
 * Pure helper to switch the biome dimension for a biome row.
 * Enforces single-dimension biome OR by selecting a default biome in the target dimension.
 * Normalizes incompatible radius to 512 (OW) or 128 (Nether) while retaining other choices.
 */
export function switchBiomeDimension(
  row: BiomeFilterRow,
  targetDimension: Dimension,
  enableV3 = false
): BiomeFilterRow {
  const currentDim = getRowDimension(row);
  if (currentDim === targetDimension) {
    return row;
  }
  const defaultOW = enableV3 ? 'biome.exact.cherry_grove' : 'biome.cherry_grove';
  const newAnyOf = targetDimension === 'nether' ? ['biome.nether_wastes'] : [defaultOW];
  let newScope = row.scope;
  if (row.scope.kind === 'near_base') {
    newScope = {
      kind: 'near_base',
      radius: normalizeRadiusForDimension(targetDimension, row.scope.radius),
    };
  }
  return {
    ...row,
    any_of: newAnyOf,
    scope: newScope,
  };
}

/**
 * Pure helper to filter a list of biomes/groups by a search query.
 */
export function filterBiomesBySearch(biomes: FeatureOption[], query: string): FeatureOption[] {
  const q = query.trim().toLowerCase();
  if (!q) return biomes;
  return biomes.filter(
    b =>
      b.label.toLowerCase().includes(q) ||
      b.id.toLowerCase().includes(q) ||
      b.category.toLowerCase().includes(q) ||
      (b.canonical_members || []).some(id=>id.replaceAll('_',' ').includes(q))
  );
}

/**
 * Pure helper to toggle or select a biome in a biome row.
 * When enableV2 & enableV3 are false: legacy multi-select within Overworld.
 * When enableV2 or enableV3 is true: enforces single-dimension biome OR.
 * In V3: enforces 16-alternative limit and prevents selecting disabled/gated options.
 */
export function toggleBiomeSelectionInRow(
  row: BiomeFilterRow,
  biomeId: string,
  enableV2 = false,
  enableV3 = false,
  features?: FeatureV3Metadata[]
): BiomeFilterRow {
  if (!enableV2 && !enableV3) {
    let next: string[];
    if (row.any_of.includes(biomeId)) {
      next = row.any_of.filter(b => b !== biomeId);
      if (next.length === 0) next = [biomeId]; // Keep at least one
    } else {
      if(row.any_of.length>=MAX_FILTER_ROW_ALTERNATIVES)return row;
      next = [...row.any_of, biomeId];
    }
    return { ...row, any_of: next };
  }

  // Check if feature is gated and unavailable
  const meta = features?.find(f=>f.id===biomeId) || getFeatureV3Metadata(biomeId);
  if (meta && meta.available === false) {
    return row;
  }

  const currentDim = getRowDimension(row);
  const clickedDim = getFeatureDimension(biomeId);

  // If clicked a biome from the other dimension, switch dimension!
  if (clickedDim !== currentDim) {
    let newScope = row.scope;
    if (row.scope.kind === 'near_base') {
      newScope = {
        kind: 'near_base',
        radius: normalizeRadiusForDimension(clickedDim, row.scope.radius),
      };
    }
    return {
      ...row,
      any_of: [biomeId],
      scope: newScope,
    };
  }

  // Same dimension: toggle within this dimension
  let next: string[];
  if (row.any_of.includes(biomeId)) {
    next = row.any_of.filter(b => b !== biomeId);
    if (next.length === 0) next = [biomeId]; // Keep at least one
  } else {
    // Enforce 16 maximum alternatives limit
    if (row.any_of.length >= MAX_FILTER_ROW_ALTERNATIVES) {
      return row; // Limit reached
    }
    next = [...row.any_of, biomeId];
  }
  return { ...row, any_of: next };
}

/**
 * Helper to select or toggle a named biome group in a row.
 */
export function selectBiomeGroupInRow(
  row: BiomeFilterRow,
  groupId: string,
  enableV3 = false,
  features?: FeatureV3Metadata[]
): BiomeFilterRow {
  return toggleBiomeSelectionInRow(row, groupId, true, enableV3, features);
}

export function FilterBuilder({
  rows,
  onChangeRows,
  onResetRows,
  enableV2 = false,
  enableV3 = false,
  features,
}: FilterBuilderProps) {
  const isV3 = Boolean(enableV3);
  const isV2 = Boolean(enableV2 || enableV3);
  const options=(fallback:FeatureOption[]):FeatureOption[]=>fallback.map(option=>{
    const meta=features?.find(f=>f.id===option.id);
    return meta?{...option,available:meta.available,unavailable_reason:meta.unavailable_reason,
      eligible_y:meta.eligible_y,canonical_members:meta.atomic_members || meta.canonical_members?.map(id=>id.startsWith('biome.')?id:`biome.exact.${id}`) || option.canonical_members}:option;
  });
  const structures=options(V3_STRUCTURES), groups=options(V3_BIOME_GROUPS), exactBiomes=options(V3_EXACT_BIOMES), allBiomes=options(V3_ALL_BIOMES);


  const [searchTerms, setSearchTerms] = useState<Record<string, string>>({});
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

  const handleAddRow = (kind: FilterKind = 'structure_count') => {
    if (rows.length >= MAX_FILTER_ROWS) return;
    const newId = `row_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    if (kind === 'structure_count') {
      const newRow: FilterRow = {
        id: newId,
        rule: 'preferred',
        kind: 'structure_count',
        feature: 'structure.village',
        at_least: 1,
        importance: 3,
        scope: { kind: 'near_base', radius: 512 },
      };
      onChangeRows([...rows, newRow]);
    } else {
      const defaultBiome = isV3 ? 'biome.exact.cherry_grove' : 'biome.cherry_grove';
      const newRow: FilterRow = {
        id: newId,
        rule: 'preferred',
        kind: 'biome_witness',
        any_of: [defaultBiome],
        importance: 3,
        scope: { kind: 'inside_border' },
      };
      onChangeRows([...rows, newRow]);
    }
  };

  const handleRemoveRow = (id: string) => {
    onChangeRows(rows.filter(r => r.id !== id));
  };

  const handleUpdateRow = (id: string, updates: Partial<FilterRow>) => {
    onChangeRows(
      rows.map(r => {
        if (r.id !== id) return r;
        return { ...r, ...updates } as FilterRow;
      })
    );
  };

  return (
    <div className="space-y-3">
      {/* Header with add buttons */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Filter Rules ({rows.length}/{MAX_FILTER_ROWS})
          </label>
          {rows.length >= MAX_FILTER_ROWS && (
            <span className="text-[10px] font-mono text-amber-400 bg-amber-950/60 px-1.5 py-0.5 rounded border border-amber-800">
              Row limit (12) reached
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {rows.length > 0 && (
            <button
              type="button"
              onClick={onResetRows}
              className="text-xs text-slate-400 hover:text-rose-400 transition-colors"
            >
              Clear all
            </button>
          )}
          <button
            type="button"
            onClick={() => handleAddRow('structure_count')}
            disabled={rows.length >= MAX_FILTER_ROWS}
            className="px-2.5 py-1 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 border border-slate-700 transition-colors"
          >
            + Structure Filter
          </button>
          <button
            type="button"
            onClick={() => handleAddRow('biome_witness')}
            disabled={rows.length >= MAX_FILTER_ROWS}
            className="px-2.5 py-1 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 border border-slate-700 transition-colors"
          >
            + Biome OR Filter
          </button>
        </div>
      </div>

      {/* V2 / V3 Reference Notice: Cleartext Anchor Projection & No Actual Portal Claim */}
      {isV2 && (
        <div
          data-testid="v2-anchor-projection-notice"
          className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 text-xs text-slate-300 space-y-1.5"
        >
          <div className="flex items-center gap-2 font-semibold text-emerald-400">
            <span>Nether Coordinate Scaling &amp; Fixed Boundary Notice</span>
          </div>
          <p>
            All requirements share the chosen Overworld anchor and its floor(OW/8) projection.
            Nether distances are clearly distinct: near-base radii are 64m, 128m, or 256m, and inside-border evaluation is constrained to a fixed 1024m square.
          </p>
          <p className="text-slate-400">
            No actual portal claim: coordinates are calculated via 1:8 coordinate projection from the Overworld anchor;
            this does not simulate in-game portal generation, obsidian placement, portal search logic, or portal link validation.
          </p>
        </div>
      )}

      {/* Rows List */}
      {rows.length === 0 ? (
        <div className="p-6 bg-slate-950/60 rounded-lg border border-slate-800/80 text-center text-slate-500 text-xs">
          No active filter rules. Showing all indexed seeds for the selected border and profile.
          Select a preset above or click a button to add custom requirements.
        </div>
      ) : (
        <div className="space-y-2.5">
          {rows.map((row, index) => {
            const rowDim = isV2 ? getRowDimension(row) : 'overworld';
            const isNether = isV2 && rowDim === 'nether';

            return (
              <div
                key={row.id}
                className={`p-3 bg-slate-950 rounded-lg border space-y-3 text-xs ${
                  isNether ? 'border-amber-900/70' : 'border-slate-800'
                }`}
              >
                {/* Row Top Controls: Rule, Kind, Scope, Importance */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-slate-500 text-[11px]">#{index + 1}</span>

                    {/* Nether Row Badge */}
                    {isNether && (
                      <span className="text-[10px] font-mono font-semibold text-amber-400 bg-amber-950/60 px-1.5 py-0.5 rounded border border-amber-800/60">
                        Nether &middot; floor(OW/8)
                      </span>
                    )}

                    {/* Rule (Required / Preferred) */}
                    <select
                      value={row.rule}
                      onChange={e => handleUpdateRow(row.id, { rule: e.target.value as FilterRule })}
                      aria-label="Filter rule type"
                      className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 font-semibold focus:outline-none focus:ring-1 focus:ring-emerald-500"
                    >
                      <option value="required">Required (Hard Filter)</option>
                      <option value="preferred">Preferred (Utility Score)</option>
                    </select>

                    {/* Scope Selector */}
                    <div className="flex items-center gap-1.5 bg-slate-900 px-2 py-1 rounded border border-slate-700">
                      <span className="text-slate-400 text-[11px]">Scope:</span>
                      <select
                        value={row.scope.kind}
                        onChange={e => {
                          const kind = e.target.value as ScopeKind;
                          const defaultRad = isNether ? DEFAULT_NETHER_NEAR_RADIUS : DEFAULT_OVERWORLD_NEAR_RADIUS;
                          handleUpdateRow(row.id, {
                            scope: kind === 'near_base' ? { kind, radius: defaultRad } : { kind },
                          });
                        }}
                        aria-label="Filter scope kind"
                        className="bg-transparent text-slate-200 focus:outline-none"
                      >
                        <option value="near_base">Near Base</option>
                        <option value="inside_border">
                          {isNether ? 'Fixed 1024m Square' : 'Inside Border'}
                        </option>
                      </select>

                      {row.scope.kind === 'near_base' && (
                        <select
                          value={
                            row.scope.radius ||
                            (isNether ? DEFAULT_NETHER_NEAR_RADIUS : DEFAULT_OVERWORLD_NEAR_RADIUS)
                          }
                          onChange={e =>
                            handleUpdateRow(row.id, {
                              scope: { kind: 'near_base', radius: Number(e.target.value) as NearRadius },
                            })
                          }
                          aria-label="Near base radius"
                          className={`bg-slate-800 font-semibold px-1 rounded focus:outline-none ${
                            isNether ? 'text-amber-400' : 'text-emerald-400'
                          }`}
                        >
                          {!isV2 ? (
                            NEAR_RADII.map(r => (
                              <option key={r} value={r}>
                                &le; {r}m
                              </option>
                            ))
                          ) : isNether ? (
                            NETHER_NEAR_RADII.map(r => (
                              <option key={r} value={r}>
                                &le; {r}m (Nether)
                              </option>
                            ))
                          ) : (
                            OVERWORLD_NEAR_RADII.map(r => (
                              <option key={r} value={r}>
                                &le; {r}m
                              </option>
                            ))
                          )}
                        </select>
                      )}
                    </div>

                    {/* Importance (1..5) for Preferred rule */}
                    {row.rule === 'preferred' && (
                      <div className="flex items-center gap-1.5 bg-slate-900 px-2 py-1 rounded border border-slate-700">
                        <span className="text-slate-400 text-[11px]">Importance:</span>
                        <select
                          value={row.importance}
                          onChange={e => handleUpdateRow(row.id, { importance: Number(e.target.value) })}
                          aria-label="Filter importance"
                          className="bg-transparent text-amber-400 font-semibold focus:outline-none"
                        >
                          <option value={1}>1 (Low)</option>
                          <option value={3}>3 (Moderate)</option>
                          <option value={5}>5 (Critical)</option>
                        </select>
                      </div>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={() => handleRemoveRow(row.id)}
                    aria-label="Delete filter rule"
                    className="text-slate-500 hover:text-rose-400 p-1 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {/* Specific Rule Parameters */}
                {row.kind === 'structure_count' ? (
                  <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-slate-800/80">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">Structure:</span>
                      <select
                        value={row.feature}
                        onChange={e => {
                          const updated = switchRowFeature(row, e.target.value, isV2, isV3);
                          handleUpdateRow(row.id, updated);
                        }}
                        aria-label="Structure feature"
                        className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-slate-100 font-medium focus:outline-none focus:ring-1 focus:ring-emerald-500"
                      >
                        {!isV2 ? (
                          KNOWN_STRUCTURES.map(s => (
                            <option key={s.id} value={s.id}>
                              {s.label} ({s.category})
                            </option>
                          ))
                        ) : !isV3 ? (
                          <>
                            <optgroup label="Overworld">
                              {V2_STRUCTURES.filter(s => s.dimension === 'overworld').map(s => (
                                <option key={s.id} value={s.id}>
                                  {s.label} ({s.category})
                                </option>
                              ))}
                            </optgroup>
                            <optgroup label="Nether">
                              {V2_STRUCTURES.filter(s => s.dimension === 'nether').map(s => (
                                <option key={s.id} value={s.id}>
                                  {s.label} ({s.category})
                                </option>
                              ))}
                            </optgroup>
                          </>
                        ) : (
                          <>
                            <optgroup label="Overworld">
                              {structures.filter(s => s.dimension === 'overworld').map(s => (
                                <option
                                  key={s.id}
                                  value={s.id}
                                  disabled={s.available === false}
                                >
                                  {s.label} {s.available === false ? `(Gated: ${s.unavailable_reason})` : `(${s.category})`}
                                </option>
                              ))}
                            </optgroup>
                            <optgroup label="Nether">
                              {structures.filter(s => s.dimension === 'nether').map(s => (
                                <option
                                  key={s.id}
                                  value={s.id}
                                  disabled={s.available === false}
                                >
                                  {s.label} {s.available === false ? `(Gated: ${s.unavailable_reason})` : `(${s.category})`}
                                </option>
                              ))}
                            </optgroup>
                          </>
                        )}
                      </select>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">At least:</span>
                      <input
                        type="number"
                        min={1}
                        max={16}
                        value={row.at_least}
                        onChange={e =>
                          handleUpdateRow(row.id, {
                            at_least: Math.min(16, Math.max(1, parseInt(e.target.value, 10) || 1)),
                          })
                        }
                        aria-label="Minimum count"
                        className="w-16 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-100 text-center font-mono focus:outline-none focus:ring-1 focus:ring-emerald-500"
                      />
                      <span className="text-slate-400">starts</span>
                    </div>

                    {/* Gated feature notice for selected structure */}
                    {(() => {
                      const meta = getFeatureV3Metadata(row.feature);
                      if (meta && meta.available === false) {
                        return (
                          <div className="w-full text-[11px] text-amber-400 bg-amber-950/40 border border-amber-800/60 p-1.5 rounded">
                            Notice: {meta.unavailable_reason || 'This structure filter is currently gated.'}
                          </div>
                        );
                      }
                      return null;
                    })()}
                  </div>
                ) : (
                  <div className="pt-2 border-t border-slate-800/80 space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-slate-400">
                        {isV3
                          ? 'Match any of these biomes (OR logic \u00B7 max 16 alternatives \u00B7 single dimension only):'
                          : isV2
                          ? 'Match any of these biomes (OR logic \u00B7 single dimension only):'
                          : 'Match any of these biomes (OR logic):'}
                      </span>

                      {isV2 ? (
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] text-slate-400">Dimension:</span>
                          <button
                            type="button"
                            aria-label="Switch to Overworld biomes"
                            onClick={() => {
                              const updated = switchBiomeDimension(row, 'overworld', isV3);
                              handleUpdateRow(row.id, updated);
                            }}
                            className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-colors border ${
                              rowDim === 'overworld'
                                ? 'bg-emerald-950 text-emerald-300 border-emerald-600'
                                : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                            }`}
                          >
                            Overworld
                          </button>
                          <button
                            type="button"
                            aria-label="Switch to Nether biomes"
                            onClick={() => {
                              const updated = switchBiomeDimension(row, 'nether', isV3);
                              handleUpdateRow(row.id, updated);
                            }}
                            className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-colors border ${
                              rowDim === 'nether'
                                ? 'bg-amber-950 text-amber-300 border-amber-600'
                                : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                            }`}
                          >
                            Nether
                          </button>
                          <span
                            className={`text-[11px] font-semibold ${
                              rowDim === 'nether' ? 'text-amber-400' : 'text-emerald-400'
                            }`}
                          >
                            {row.any_of.length}{isV3 ? '/16' : ''} selected
                          </span>
                        </div>
                      ) : (
                        <span className="text-[11px] text-emerald-400">
                          {row.any_of.length} selected
                        </span>
                      )}
                    </div>

                    {/* V3 Alternative Limit Notice */}
                    {isV3 && row.any_of.length >= MAX_FILTER_ROW_ALTERNATIVES && (
                      <div className="text-[11px] text-amber-300 bg-amber-950/60 border border-amber-800/80 px-2 py-1 rounded">
                        Row alternative ceiling reached: maximum {MAX_FILTER_ROW_ALTERNATIVES} choices per OR row. Deselect an option to choose another.
                      </div>
                    )}

                    {!isV2 ? (
                      <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto p-1.5 bg-slate-900 rounded border border-slate-800">
                        {KNOWN_BIOMES.map(b => {
                          const isSelected = row.any_of.includes(b.id);
                          return (
                            <button
                              key={b.id}
                              type="button"
                              onClick={() => {
                                const updated = toggleBiomeSelectionInRow(row, b.id, false, false);
                                handleUpdateRow(row.id, updated);
                              }}
                              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors border ${
                                isSelected
                                  ? 'bg-emerald-950 text-emerald-300 border-emerald-600'
                                  : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                              }`}
                            >
                              {isSelected ? '\u2713 ' : ''}{b.label}
                            </button>
                          );
                        })}
                      </div>
                    ) : !isV3 ? (
                      <div className="space-y-2">
                        {/* Overworld Biomes Group (V2) */}
                        <div>
                          <div className="text-[11px] font-medium text-slate-400 mb-1 flex items-center justify-between">
                            <span>Overworld Biomes (9)</span>
                            {rowDim !== 'overworld' && (
                              <span className="text-[10px] text-slate-500 italic">
                                Clicking switches dimension to Overworld
                              </span>
                            )}
                          </div>
                          <div className="flex flex-wrap gap-1.5 p-1.5 bg-slate-900 rounded border border-slate-800">
                            {V2_BIOMES.filter(b => b.dimension === 'overworld').map(b => {
                              const isSelected = rowDim === 'overworld' && row.any_of.includes(b.id);
                              return (
                                <button
                                  key={b.id}
                                  type="button"
                                  onClick={() => {
                                    const updated = toggleBiomeSelectionInRow(row, b.id, true, false);
                                    handleUpdateRow(row.id, updated);
                                  }}
                                  className={`px-2 py-1 rounded text-[11px] font-medium transition-colors border ${
                                    isSelected
                                      ? 'bg-emerald-950 text-emerald-300 border-emerald-600'
                                      : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                                  }`}
                                >
                                  {isSelected ? '\u2713 ' : ''}{b.label}
                                </button>
                              );
                            })}
                          </div>
                        </div>

                        {/* Nether Biomes Group (V2) */}
                        <div>
                          <div className="text-[11px] font-medium text-amber-400/90 mb-1 flex items-center justify-between">
                            <span>Nether Biomes (5)</span>
                            {rowDim !== 'nether' && (
                              <span className="text-[10px] text-slate-500 italic">
                                Clicking switches dimension to Nether
                              </span>
                            )}
                          </div>
                          <div className="flex flex-wrap gap-1.5 p-1.5 bg-slate-900 rounded border border-slate-800">
                            {V2_BIOMES.filter(b => b.dimension === 'nether').map(b => {
                              const isSelected = rowDim === 'nether' && row.any_of.includes(b.id);
                              return (
                                <button
                                  key={b.id}
                                  type="button"
                                  onClick={() => {
                                    const updated = toggleBiomeSelectionInRow(row, b.id, true, false);
                                    handleUpdateRow(row.id, updated);
                                  }}
                                  className={`px-2 py-1 rounded text-[11px] font-medium transition-colors border ${
                                    isSelected
                                      ? 'bg-amber-950 text-amber-300 border-amber-600'
                                      : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                                  }`}
                                >
                                  {isSelected ? '\u2713 ' : ''}{b.label}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* V3 Biome Selector: Compact, Searchable, Expandable Groups Any+Individual */
                      <div className="space-y-3">
                        {rowDim === 'overworld' ? (
                          <div className="space-y-2.5">
                            {/* Search bar */}
                            <div className="flex items-center gap-2 bg-slate-900 px-2.5 py-1.5 rounded border border-slate-700">
                              <span className="text-slate-500 text-xs">&#128269;</span>
                              <input
                                type="text"
                                placeholder="Search biomes & groups (e.g. cherry, ocean, badlands, dark forest)..."
                                value={searchTerms[row.id] || ''}
                                onChange={e =>
                                  setSearchTerms(prev => ({ ...prev, [row.id]: e.target.value }))
                                }
                                aria-label="Search biomes and groups"
                                className="bg-transparent text-slate-100 placeholder-slate-500 text-xs w-full focus:outline-none"
                              />
                              {searchTerms[row.id] && (
                                <button
                                  type="button"
                                  onClick={() =>
                                    setSearchTerms(prev => ({ ...prev, [row.id]: '' }))
                                  }
                                  className="text-slate-400 hover:text-slate-200 text-xs px-1"
                                >
                                  &times;
                                </button>
                              )}
                            </div>

                            {/* Biome Groups Section (Any + Expand for atomic) */}
                            <div className="p-2 bg-slate-900 rounded border border-slate-800 space-y-2">
                              <div className="flex items-center justify-between text-[11px] font-semibold text-slate-300">
                                <span>Biome Groups (Any group OR individual atomic selection)</span>
                                <span className="text-[10px] text-slate-400 font-normal">
                                  Named group counts as 1 choice
                                </span>
                              </div>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                {filterBiomesBySearch(groups, searchTerms[row.id] || '').map(group => {
                                  const isGroupSelected = row.any_of.includes(group.id);
                                  const isExpanded = Boolean(expandedGroups[`${row.id}:${group.id}`]);
                                  const members = (group.canonical_members || [])
                                    .map(mid => exactBiomes.find(b => b.id === mid))
                                    .filter(Boolean) as FeatureOption[];
                                  const selectedMembersCount = members.filter(m =>
                                    row.any_of.includes(m.id)
                                  ).length;
                                  const isAtLimit =
                                    row.any_of.length >= MAX_FILTER_ROW_ALTERNATIVES && !isGroupSelected;

                                  return (
                                    <div
                                      key={group.id}
                                      className="p-2 bg-slate-950 rounded border border-slate-800 space-y-1.5"
                                    >
                                      <div className="flex items-center justify-between gap-1.5">
                                        <button
                                          type="button"
                                          disabled={isAtLimit}
                                          onClick={() => {
                                            const updated = toggleBiomeSelectionInRow(
                                              row,
                                              group.id,
                                              true,
                                              true, features
                                            );
                                            handleUpdateRow(row.id, updated);
                                          }}
                                          className={`flex-1 py-1 px-2 rounded text-[11px] font-medium text-left transition-colors border flex items-center justify-between ${
                                            isGroupSelected
                                              ? 'bg-emerald-950 text-emerald-300 border-emerald-600'
                                              : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-600'
                                          } ${isAtLimit ? 'opacity-40 cursor-not-allowed' : ''}`}
                                        >
                                          <span>
                                            {isGroupSelected ? '\u2713 ' : ''}Any {group.label}
                                          </span>
                                          <span className="text-[10px] opacity-75 font-mono">
                                            Group choice
                                          </span>
                                        </button>
                                        <button
                                          type="button"
                                          aria-expanded={isExpanded}
                                          onClick={() =>
                                            setExpandedGroups(prev => ({
                                              ...prev,
                                              [`${row.id}:${group.id}`]: !isExpanded,
                                            }))
                                          }
                                          className="px-2 py-1 text-[10px] font-medium bg-slate-900 text-slate-300 hover:text-white border border-slate-700 rounded transition-colors"
                                        >
                                          {isExpanded
                                            ? '▾ Hide'
                                            : `▸ Atomic (${selectedMembersCount > 0 ? `${selectedMembersCount}/` : ''}${members.length})`}
                                        </button>
                                      </div>

                                      {isExpanded && (
                                        <div className="pl-2 pt-1.5 border-l-2 border-slate-800 space-y-1">
                                          <div className="text-[10px] text-slate-400">
                                            Select specific atomic member biomes:
                                          </div>
                                          <div className="flex flex-wrap gap-1">
                                            {members.map(member => {
                                              const isMemSelected = row.any_of.includes(member.id);
                                              const isMemLimit =
                                                row.any_of.length >= MAX_FILTER_ROW_ALTERNATIVES &&
                                                !isMemSelected;
                                              return (
                                                <button
                                                  key={member.id}
                                                  type="button"
                                                  disabled={isMemLimit}
                                                  onClick={() => {
                                                    const updated = toggleBiomeSelectionInRow(
                                                      row,
                                                      member.id,
                                                      true,
                                                      true, features
                                                    );
                                                    handleUpdateRow(row.id, updated);
                                                  }}
                                                  className={`px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors border ${
                                                    isMemSelected
                                                      ? 'bg-emerald-950 text-emerald-300 border-emerald-600'
                                                      : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                                                  } ${isMemLimit ? 'opacity-40 cursor-not-allowed' : ''}`}
                                                >
                                                  {isMemSelected ? '\u2713 ' : ''}
                                                  {member.label}
                                                </button>
                                              );
                                            })}
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>

                            {/* Categorized Biomes */}
                            <div className="space-y-2">
                              {Array.from(
                                new Set(exactBiomes.map(b => b.category))
                              ).map(category => {
                                const biomesInCategory = filterBiomesBySearch(
                                  exactBiomes.filter(b => b.category === category),
                                  searchTerms[row.id] || ''
                                );
                                if (biomesInCategory.length === 0) return null;

                                const isGatedCategory = biomesInCategory.every(b=>b.available===false);

                                return (
                                  <details key={category} open={searchTerms[row.id] ? true : undefined} className="space-y-1">
                                    <summary className="cursor-pointer text-[11px] font-medium text-slate-400">
                                      <span>
                                        {category} ({biomesInCategory.length})
                                      </span>
                                      {isGatedCategory && (
                                        <span className="text-[10px] text-amber-400 font-mono">
                                          Gated: sample controls pending
                                        </span>
                                      )}
                                    </summary>
                                    <div className="flex flex-wrap gap-1.5 p-1.5 bg-slate-900 rounded border border-slate-800">
                                      {biomesInCategory.map(b => {
                                        const isSelected = row.any_of.includes(b.id);
                                        const isGated = b.available === false;
                                        const isAtLimit =
                                          row.any_of.length >= MAX_FILTER_ROW_ALTERNATIVES && !isSelected;

                                        return (
                                          <button
                                            key={b.id}
                                            type="button"
                                            disabled={isGated || isAtLimit}
                                            title={
                                              isGated
                                                ? `Gated: ${b.unavailable_reason}`
                                                : isAtLimit
                                                ? 'Maximum 16 alternatives reached'
                                                : b.label
                                            }
                                            onClick={() => {
                                              if (isGated) return;
                                              const updated = toggleBiomeSelectionInRow(
                                                row,
                                                b.id,
                                                true,
                                                true, features
                                              );
                                              handleUpdateRow(row.id, updated);
                                            }}
                                            className={`px-2 py-1 rounded text-[11px] font-medium transition-colors border ${
                                              isGated
                                                ? 'bg-slate-950/40 text-slate-600 border-slate-800/60 line-through cursor-not-allowed opacity-50'
                                                : isSelected
                                                ? 'bg-emerald-950 text-emerald-300 border-emerald-600'
                                                : isAtLimit
                                                ? 'bg-slate-950 text-slate-600 border-slate-800/80 cursor-not-allowed opacity-40'
                                                : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                                            }`}
                                          >
                                            {isSelected ? '\u2713 ' : ''}
                                            {b.label}
                                            {isGated && (
                                              <span className="text-[9px] text-amber-500/80 no-underline ml-1">
                                                (Gated)
                                              </span>
                                            )}
                                          </button>
                                        );
                                      })}
                                    </div>
                                  </details>
                                );
                              })}
                            </div>
                          </div>
                        ) : (
                          /* Nether Biomes Group (V3) */
                          <div>
                            <div className="text-[11px] font-medium text-amber-400/90 mb-1 flex items-center justify-between">
                              <span>Nether Biomes (5)</span>
                              <span className="text-[10px] text-amber-500/80">
                                Constrained to Nether radii (64m, 128m, 256m)
                              </span>
                            </div>
                            <div className="flex flex-wrap gap-1.5 p-1.5 bg-slate-900 rounded border border-slate-800">
                              {allBiomes.filter(b => b.dimension === 'nether').map(b => {
                                const isSelected = rowDim === 'nether' && row.any_of.includes(b.id);
                                const isAtLimit =
                                  row.any_of.length >= MAX_FILTER_ROW_ALTERNATIVES && !isSelected;
                                return (
                                  <button
                                    key={b.id}
                                    type="button"
                                    disabled={isAtLimit}
                                    onClick={() => {
                                      const updated = toggleBiomeSelectionInRow(
                                        row,
                                        b.id,
                                        true,
                                        true, features
                                      );
                                      handleUpdateRow(row.id, updated);
                                    }}
                                    className={`px-2 py-1 rounded text-[11px] font-medium transition-colors border ${
                                      isSelected
                                        ? 'bg-amber-950 text-amber-300 border-amber-600'
                                        : isAtLimit
                                        ? 'bg-slate-950 text-slate-600 border-slate-800/80 cursor-not-allowed opacity-40'
                                        : 'bg-slate-950 text-slate-400 border-slate-800 hover:border-slate-700'
                                    }`}
                                  >
                                    {isSelected ? '\u2713 ' : ''}
                                    {b.label}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
