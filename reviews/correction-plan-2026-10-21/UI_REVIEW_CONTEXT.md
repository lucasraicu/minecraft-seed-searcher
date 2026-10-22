# Final UI review context
User explicitly waived browser QA, requires Codex and Gemini checks. Read-only
High review. No tools/edits/tests; use embedded files. Give concrete defects, not
hypothetical feature expansion. Focus return, copy status, text coordinate fixes
are intended. Parent provides snapshot selector and Personalized view. Ordinary
nav buttons aria-current need not be converted to tabs. Inline criteria isn't a
modal; no focus trap required. Missing evidence remains gated. Review actual
component and handler test; state tests lack DOM/layout verification. <=500words.

## Parent source excerpt (lines90-200)
```tsx
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
```
