import { useState } from 'react';
import {PublicHarvestStatus} from './PublicHarvestStatus';
import { PillarNavigation, ProductPillar } from './pillars';
import { useCatalogState } from './useCatalogState';
import { CategoryPresets } from './CategoryPresets';
import { FilterBuilder } from './FilterBuilder';
import { CandidateCard } from './CandidateCard';
import { DetailModal } from './DetailModal';
import { CompareModal } from './CompareModal';
import { FavoritesDrawer } from './FavoritesDrawer';
import { QueryExportModal } from './QueryExportModal';
import {
  BORDER_SIDES,
  ANCHOR_MODES,
  ANCHOR_LABELS,
  DEFAULT_PROFILES,
  CATEGORY_PRESETS,
  MAX_COMPARE_SEEDS,
} from './constants';
import type { CatalogCandidate } from './types';

export function CatalogWorkspace() {
  const [pillar, setPillar] = useState<'realm'|'presets'|'personalized'|'rare'>('personalized');
  const {
    isV2Snapshot,
    isV3Snapshot,
    status,
    capabilities,
    snapshots,
    selectedSnapshotId,
    setSelectedSnapshotId,
    borderSide,
    setBorderSide,
    anchorMode,
    setAnchorMode,
    profile,
    setProfile,
    activePresetId,
    setActivePresetId,
    filterRows,
    setFilterRows,
    selectPreset,
    results,
    nextCursor,
    totalMatched,
    unresolvedWorlds,
    unresolvedCandidates,
    isTruncated,
    isQueryLoading,
    isFetchingMore,
    queryError,
    storageError,
    evidenceLabel,
    hasQueried,
    runQuery,
    clearFiltersAndQuery,
    loadMore,
    comparedCandidates,
    isCompareOpen,
    setIsCompareOpen,
    toggleCompare,
    removeCompared,
    clearCompared,
    favorites,
    isFavoritesOpen,
    setIsFavoritesOpen,
    toggleFavorite,
    removeFavorite,
    clearFavorites,
    importFavorites,
    inspectedCandidate,
    detailData,
    isDetailLoading,
    detailError,
    inspectCandidate,
    closeDetail,
    isExportOpen,
    setIsExportOpen,
    currentQueryPayload,
    isInitializing,
    initError,
  } = useCatalogState();

  const presets = capabilities?.presets?.length ? capabilities.presets : CATEGORY_PRESETS;
  const profiles = capabilities?.profiles?.length ? capabilities.profiles : DEFAULT_PROFILES;
  const borderSides = capabilities?.border_sides?.length ? capabilities.border_sides : BORDER_SIDES;
  const anchorModes = [...new Set([...(capabilities?.anchor_modes?.length ? capabilities.anchor_modes : ANCHOR_MODES),...(isV2Snapshot?(snapshots.find(s=>s.snapshot_id===selectedSnapshotId)?.anchor_modes||status?.anchor_modes||[]):(snapshots.find(s=>s.snapshot_id===selectedSnapshotId)?.accuracy_anchor_modes||[]))])];

  const isAvailable = status ? status.available : true;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      {storageError && <p role="alert" className="bg-amber-950 text-amber-200 p-3">Saved favorites: {storageError}</p>}
      {/* Top Navbar */}
      <header className="bg-slate-950 border-b border-slate-800 px-4 sm:px-6 py-3 sticky top-0 z-30 shadow-md">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
          {/* Title & Badge */}
          <div className="flex items-center gap-3">
            <h1 className="text-base sm:text-lg font-bold tracking-tight text-white flex items-center gap-2">
              <span className="text-emerald-400">&bull;</span>
              <span>Private Catalog</span>
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-950 text-emerald-400 border border-emerald-800">
              Pilot Index
            </span>
          </div>

          {/* Snapshot selector & Status badge */}
          <div className="flex items-center gap-2 sm:gap-4 flex-wrap">
            {snapshots.length > 0 && (
              <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs">
                <span className="text-slate-400 text-[11px]">Snapshot:</span>
                <select
                  value={selectedSnapshotId}
                  onChange={e => setSelectedSnapshotId(e.target.value)}
                  aria-label="Pinned catalog snapshot"
                  className="bg-transparent text-emerald-400 font-mono font-medium focus:outline-none"
                >
                  {snapshots.map(s => (
                    <option key={s.snapshot_id} value={s.snapshot_id} className="bg-slate-900 text-slate-200">
                      {s.snapshot_id.slice(0, 12)}… ({s.worlds} worlds, {s.layouts} layouts)
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Availability status badge */}
            <div className="flex items-center gap-1.5 text-xs">
              <span
                className={`w-2 h-2 rounded-full ${
                  isInitializing
                    ? 'bg-amber-400 animate-pulse'
                    : isAvailable
                    ? 'bg-emerald-400'
                    : 'bg-rose-500'
                }`}
              ></span>
              <span className="text-slate-300 text-[11px] hidden sm:inline">
                {isInitializing
                  ? 'Connecting...'
                  : isAvailable
                  ? 'Catalog Ready'
                  : 'Catalog Unavailable'}
              </span>
            </div>

            {/* Quick Actions (Compare, Favorites, Export) */}
            <div className="flex items-center gap-1.5 sm:gap-2">
              <button
                type="button"
                onClick={() => setIsCompareOpen(true)}
                aria-label="Open compare tray"
                className={`px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors flex items-center gap-1.5 ${
                  comparedCandidates.length > 0
                    ? 'bg-emerald-950/80 text-emerald-300 border-emerald-600'
                    : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-slate-200'
                }`}
              >
                <span>Compare</span>
                <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] font-mono">
                  {comparedCandidates.length}/{MAX_COMPARE_SEEDS}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setIsFavoritesOpen(true)}
                aria-label="Open saved favorites"
                className={`px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors flex items-center gap-1.5 ${
                  favorites.length > 0
                    ? 'bg-amber-950/60 text-amber-300 border-amber-600'
                    : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-slate-200'
                }`}
              >
                <span>★ Favorites</span>
                <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] font-mono">
                  {favorites.length}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setIsExportOpen(true)}
                aria-label="Export query and feedback"
                className="px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700 transition-colors"
              >
                Export
              </button>
            </div>
          </div>
        </div>
      </header>

      <PillarNavigation value={pillar} onChange={setPillar} />
      <PublicHarvestStatus />
      {pillar !== 'personalized' && <ProductPillar pillarId={pillar} snapshotId={selectedSnapshotId} />}

      {/* Main Container */}
      <main hidden={pillar !== 'personalized'} className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-6 flex-1 space-y-6">
        {/* Initialization Error Banner */}
        {initError && (
          <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs">
            <div className="font-bold mb-1">Catalog Connection Issue:</div>
            <div>{initError}</div>
          </div>
        )}

        {/* Unavailable Banner */}
        {!isAvailable && status?.reason && (
          <div className="p-4 rounded-lg bg-amber-950/40 border border-amber-800 text-amber-300 text-xs">
            <div className="font-bold mb-1">Catalog Currently Unavailable:</div>
            <div>{status.reason}</div>
          </div>
        )}

        {/* Search Query Control Panel */}
        <section className="bg-slate-950 border border-slate-800 rounded-xl p-5 shadow-lg space-y-5">
          {/* Category Presets Tabs */}
          <CategoryPresets
            presets={presets}
            activePresetId={activePresetId}
            onSelectPreset={selectPreset}
          />

          {/* Mode, Border & Profile Controls */}
          <div className="pt-4 border-t border-slate-800/80 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            {/* Border Side Selector */}
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300 uppercase tracking-wider text-[11px] block">
                Border Side Dimension
              </label>
              <div className="flex gap-2">
                {borderSides.map(side => (
                  <button
                    key={side}
                    type="button"
                    onClick={() => setBorderSide(side)}
                    className={`flex-1 py-1.5 px-2 rounded-lg border font-mono text-center font-medium transition-colors ${
                      borderSide === side
                        ? 'bg-emerald-950 text-emerald-300 border-emerald-500'
                        : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    {side}m
                  </button>
                ))}
              </div>
            </div>

            {/* Anchor Mode Selector */}
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300 uppercase tracking-wider text-[11px] block">
                Anchor Mode
              </label>
              <div className="flex gap-2">
                {anchorModes.map(mode => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setAnchorMode(mode)}
                    aria-pressed={anchorMode === mode}
                    className={`flex-1 py-1.5 px-2 rounded-lg border text-center font-medium capitalize transition-colors ${
                      anchorMode === mode
                        ? 'bg-emerald-950 text-emerald-300 border-emerald-500'
                        : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    {ANCHOR_LABELS[mode]}
                  </button>
                ))}
              </div>
            </div>

            <p className="text-xs text-slate-400">Origin is (0, 0), not world spawn. Recommended settlement selects the best saved center for your request. World spawn modes appear when this snapshot has saved anchors. An estimate is not game-observed spawn; neither mode establishes player landing, terrain height or safety.</p>
            {unresolvedWorlds>0 && <details className="text-xs text-amber-200">
              <summary>{unresolvedWorlds} additional retained worlds need refinement</summary>
              <p>Required evidence is incomplete. These are potential candidates, separate from matches under the selected evidence policy. Inspecting a world reads saved data; it does not start a game check.</p>
              <ul>{unresolvedCandidates.map(candidate=><li key={candidate.world_id} className="mt-1"><button type="button" className="underline" onClick={()=>inspectCandidate(candidate.seed,selectedSnapshotId,candidate.world_id,candidate.layout_id)}>Inspect {candidate.seed}</button> · center {candidate.anchor.join(', ')}</li>)}</ul>
              {unresolvedWorlds>unresolvedCandidates.length && <p>Showing the first {unresolvedCandidates.length} potential candidates.</p>}
            </details>}
            {/* Profile Dropdown */}
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300 uppercase tracking-wider text-[11px] block">
                Evaluation Profile
              </label>
              <select
                value={profile}
                onChange={e => setProfile(e.target.value)}
                aria-label="Evaluation scoring profile"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-100 font-medium focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                {profiles.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.label || p.id}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Editable Filter Rules */}
          <div className="pt-4 border-t border-slate-800/80">
            <FilterBuilder
              features={capabilities?.registry_v3?.features}
              enableV2={isV2Snapshot}
              enableV3={isV3Snapshot}
              rows={filterRows}
              onChangeRows={rows => {
                setFilterRows(rows);
                setActivePresetId(null); // Custom changes detach from active preset
              }}
              onResetRows={() => {
                setFilterRows([]);
                setActivePresetId(null);
              }}
            />
          </div>

          {/* Query Action Bar */}
          <div className="pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-slate-400 font-mono">
              Request: {borderSide}m &bull; {anchorMode} &bull; {profile} &bull; {filterRows.length} rules
            </div>

            <button
              type="button"
              onClick={runQuery}
              disabled={isQueryLoading || !selectedSnapshotId}
              className="px-6 py-2 rounded-lg font-bold text-xs uppercase tracking-wider bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-slate-950 shadow-md transition-all flex items-center gap-2"
            >
              {isQueryLoading ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></span>
                  <span>Querying Index...</span>
                </>
              ) : (
                <span>Execute Catalog Query</span>
              )}
            </button>
          </div>
        </section>

        {/* Results Area */}
        <section className="space-y-4">
          {/* Header Bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 px-1">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                Catalog Results
              </h2>
              {hasQueried && !isQueryLoading && (
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-800 text-emerald-400 border border-slate-700">
                    {totalMatched} worlds matched
                  </span>

                </div>
              )}
            </div>

            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span>Evidence: <strong className="text-slate-400 font-normal">{evidenceLabel}</strong></span>
              <span>&bull;</span>
              <span className="italic">No actual game certification</span>
            </div>
          </div>

          {/* Query Error State */}
          {queryError && (
            <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center justify-between gap-4">
              <div>
                <span className="font-bold">Query Error:</span> {queryError}
              </div>
              <button
                type="button"
                onClick={runQuery}
                className="px-3 py-1 rounded bg-rose-900/60 hover:bg-rose-900 text-rose-200 border border-rose-700 shrink-0 font-semibold"
              >
                Retry
              </button>
            </div>
          )}

          {/* Loading Skeleton */}
          {isQueryLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map(i => (
                <div
                  key={i}
                  className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 animate-pulse space-y-3"
                >
                  <div className="h-4 bg-slate-800 rounded w-1/3"></div>
                  <div className="h-6 bg-slate-800 rounded w-4/5"></div>
                  <div className="h-4 bg-slate-800 rounded w-1/2"></div>
                  <div className="h-10 bg-slate-800 rounded mt-4"></div>
                </div>
              ))}
            </div>
          )}

          {/* Empty Results State */}
          {!isQueryLoading && hasQueried && results.length === 0 && !queryError && (
            <div className="p-12 bg-slate-950 rounded-xl border border-slate-800 text-center space-y-3">
              <div className="text-base font-semibold text-slate-300">
                {unresolvedWorlds>0 ? 'No evidence-backed matches yet' : 'No matching seeds found'}
              </div>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                {unresolvedWorlds>0 ? 'Potential worlds remain in the refinement list. Missing coarse witnesses do not establish absence.' : `No indexed worlds have matching evidence for the selected ${borderSide}-block border and anchor mode. Try preferred rules or different requirements.`}
              </p>
              <button
                type="button"
                onClick={clearFiltersAndQuery}
                className="mt-2 px-4 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
              >
                Clear Filters &amp; Query All
              </button>
            </div>
          )}

          {/* Pre-query Idle State */}
          {!isQueryLoading && !hasQueried && (
            <div className="p-12 bg-slate-950/60 rounded-xl border border-slate-800/80 text-center space-y-3">
              <div className="text-base font-semibold text-slate-300">
                Ready to Explore Pinned Catalog
              </div>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Choose a category preset or build custom structure and biome criteria, then click "Execute Catalog Query" above to search the immutable index.
              </p>
            </div>
          )}

          {/* Candidates Grid */}
          {!isQueryLoading && results.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {results.map((candidate: CatalogCandidate) => {
                const favId = `${selectedSnapshotId}:${candidate.world_id}:${candidate.layout_id}`;
                const isFav = favorites.some(f => f.id === favId);
                const isComp = comparedCandidates.some(
                  c => c.world_id === candidate.world_id && c.layout_id === candidate.layout_id && c.snapshot_id === candidate.snapshot_id
                );
                const canComp = comparedCandidates.length < MAX_COMPARE_SEEDS;

                return (
                  <CandidateCard
                    key={`${candidate.world_id}:${candidate.layout_id}`}
                    candidate={candidate}
                    snapshotId={selectedSnapshotId}
                    isCompared={isComp}
                    canCompare={canComp}
                    isFavorite={isFav}
                    onToggleCompare={toggleCompare}
                    onToggleFavorite={toggleFavorite}
                    onInspect={c =>
                      inspectCandidate(c.seed, selectedSnapshotId, c.world_id, c.layout_id)
                    }
                  />
                );
              })}
            </div>
          )}

          {/* Pagination Controls */}
          {!isQueryLoading && results.length > 0 && (
            <div className="pt-4 flex flex-col items-center justify-center space-y-2">
              {nextCursor ? (
                <button
                  type="button"
                  onClick={loadMore}
                  disabled={isFetchingMore}
                  className="px-6 py-2 rounded-lg text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 shadow-sm transition-colors flex items-center gap-2"
                >
                  {isFetchingMore ? (
                    <>
                      <span className="w-3.5 h-3.5 border-2 border-slate-300 border-t-transparent rounded-full animate-spin"></span>
                      <span>Loading Next Page...</span>
                    </>
                  ) : (
                    <span>Load More Candidates &darr;</span>
                  )}
                </button>
              ) : (
                <div className="text-xs text-slate-400 font-mono">
                  {isTruncated ? `Top ${results.length} ranked worlds loaded out of ${totalMatched} matches; narrow your filters to see other worlds.` : `All ${totalMatched} candidate results loaded.`}
                </div>
              )}
            </div>
          )}
        </section>
      </main>

      {/* Overlays / Modals */}
      <DetailModal
        detail={detailData}
        seedString={inspectedCandidate?.seedString || ''}
        snapshotId={inspectedCandidate?.snapshotId || selectedSnapshotId}
        worldId={inspectedCandidate?.worldId || ''}
        layoutId={inspectedCandidate?.layoutId || ''}
        isOpen={inspectedCandidate !== null}
        onClose={closeDetail}
        isLoading={isDetailLoading}
        error={detailError}
      />

      <CompareModal
        candidates={comparedCandidates}
        isOpen={isCompareOpen}
        onClose={() => setIsCompareOpen(false)}
        onRemove={removeCompared}
        onClearAll={clearCompared}
        onInspect={c => {
          setIsCompareOpen(false);
          inspectCandidate(c.seed, c.snapshot_id || selectedSnapshotId, c.world_id, c.layout_id);
        }}
      />

      <FavoritesDrawer
        favorites={favorites}
        isOpen={isFavoritesOpen}
        onClose={() => setIsFavoritesOpen(false)}
        onRemoveFavorite={removeFavorite}
        onClearFavorites={clearFavorites}
        onImportFavorites={importFavorites}
        onInspectFavorite={fav => {
          setIsFavoritesOpen(false);
          inspectCandidate(fav.seed, fav.snapshot_id, fav.world_id, fav.layout_id);
        }}
      />

      <QueryExportModal
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        queryPayload={currentQueryPayload}
        evidenceLabel={evidenceLabel}
        results={results}
        totalMatched={totalMatched}
      />
    </div>
  );
}
export default CatalogWorkspace;
