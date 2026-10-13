import React, { useState } from 'react';
import type { SeedCandidate } from '../types';

interface CandidateFeedProps {
  candidates: SeedCandidate[];
  selectedCandidate: SeedCandidate | null;
  onSelectCandidate: (candidate: SeedCandidate) => void;
  onInspectCandidate: (candidate: SeedCandidate) => void;
  onCopyNotice: (msg: string) => void;
  onClearCandidates?: () => void;
}

export const CandidateFeed: React.FC<CandidateFeedProps> = ({
  candidates,
  selectedCandidate,
  onSelectCandidate,
  onInspectCandidate,
  onCopyNotice,
  onClearCandidates,
}) => {
  const [minScore, setMinScore] = useState<number>(65);
  const [filterMode, setFilterMode] = useState<'all' | 'continent' | 'baseline' | 'spawn50' | 'spawn100' | 'bds'>('all');
  const [sortBy, setSortBy] = useState<'score' | 'spawn' | 'structures'>('score');

  const continentCount = candidates.filter((c) => c.terrainPassed !== false).length;
  const baselineCount = candidates.filter((c) => c.terrainPassed === false).length;

  const filtered = candidates
    .filter((c) => {
      if (c.score < minScore) return false;
      if (filterMode === 'continent' && c.terrainPassed === false) return false;
      if (filterMode === 'baseline' && c.terrainPassed !== false) return false;
      if (filterMode === 'spawn50' && (c.spawnDistance ?? 999) > 50) return false;
      if (filterMode === 'spawn100' && (c.spawnDistance ?? 999) > 100) return false;
      if (filterMode === 'bds' && !c.bdsVerified) return false;
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'spawn') {
        return (a.spawnDistance ?? 999) - (b.spawnDistance ?? 999);
      }
      if (sortBy === 'structures') {
        return b.structures.length - a.structures.length;
      }
      return b.score - a.score;
    });

  const handleCopySeed = (seed: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(seed);
    onCopyNotice(`Copied Seed: ${seed}`);
  };

  const handleCopyTp = (c: SeedCandidate, e: React.MouseEvent) => {
    e.stopPropagation();
    const cmd = `/tp @s ${c.strongholdAnchor[0]} 100 ${c.strongholdAnchor[1]}`;
    navigator.clipboard.writeText(cmd);
    onCopyNotice(`Copied Teleport: ${cmd}`);
  };

  return (
    <div className="w-84 h-full bg-slate-900 border-l border-slate-800 flex flex-col z-10 shadow-2xl">
      {/* Header & Controls */}
      <div className="p-4 border-b border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
            <h2 className="text-sm font-bold uppercase tracking-wider text-white">Candidates</h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-xs font-mono font-bold text-amber-400">
              {filtered.length} / {candidates.length}
            </span>
            {onClearCandidates && candidates.length > 0 && (
              <button
                onClick={onClearCandidates}
                className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
                title="Clear current candidate feed"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Sort & Filter Controls */}
        <div className="space-y-2 text-xs">
          <div className="flex justify-between items-center text-slate-400">
            <span>Score Threshold:</span>
            <span className="font-mono text-emerald-400 font-bold">{minScore}+</span>
          </div>
          <input
            type="range"
            min="60"
            max="98"
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />

          {/* Quick Filter Badges Row 1: Stage Filter */}
          <div className="grid grid-cols-3 gap-1 pt-1">
            <button
              onClick={() => setFilterMode('all')}
              className={`py-1 rounded text-[10px] font-semibold transition-all ${
                filterMode === 'all'
                  ? 'bg-slate-700 text-white'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
            >
              All ({candidates.length})
            </button>
            <button
              onClick={() => setFilterMode('continent')}
              className={`py-1 rounded text-[10px] font-semibold transition-all flex items-center justify-center gap-1 ${
                filterMode === 'continent'
                  ? 'bg-cyan-600/40 text-cyan-300 border border-cyan-500/40'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
              title="Seeds certified with 70–80% Coastal Continent terrain"
            >
              <span>🌊</span> Continent ({continentCount})
            </button>
            <button
              onClick={() => setFilterMode('baseline')}
              className={`py-1 rounded text-[10px] font-semibold transition-all flex items-center justify-center gap-1 ${
                filterMode === 'baseline'
                  ? 'bg-amber-600/40 text-amber-300 border border-amber-500/40'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
              title="Seeds passing structure & biome floors (unconstrained terrain)"
            >
              <span>🏰</span> Baseline ({baselineCount})
            </button>
          </div>

          {/* Quick Filter Badges Row 2: Secondary Attributes */}
          <div className="grid grid-cols-3 gap-1">
            <button
              onClick={() => setFilterMode('spawn50')}
              className={`py-1 rounded text-[10px] font-semibold transition-all ${
                filterMode === 'spawn50'
                  ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/30'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
              title="Spawn point within 50m of (0,0)"
            >
              ≤50m Spawn
            </button>
            <button
              onClick={() => setFilterMode('spawn100')}
              className={`py-1 rounded text-[10px] font-semibold transition-all ${
                filterMode === 'spawn100'
                  ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/30'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
              title="Spawn point within 100m of (0,0)"
            >
              ≤100m Spawn
            </button>
            <button
              onClick={() => setFilterMode('bds')}
              className={`py-1 rounded text-[10px] font-semibold transition-all ${
                filterMode === 'bds'
                  ? 'bg-blue-600/30 text-blue-300 border border-blue-500/30'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
            >
              BDS ✓
            </button>
          </div>

          {/* Sort Selector */}
          <div className="flex items-center justify-between pt-1 text-[11px] text-slate-400">
            <span>Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-slate-800 border border-slate-700 rounded px-1.5 py-0.5 text-[10px] text-white outline-none focus:border-emerald-500"
            >
              <option value="score">Highest Score</option>
              <option value="spawn">Closest Spawn to (0,0)</option>
              <option value="structures">Most Structures</option>
            </select>
          </div>
        </div>
      </div>

      {/* Candidate Cards Scrollable List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {filtered.map((cand) => {
          const isSelected = selectedCandidate?.id === cand.id;
          const chunkbaseUrl =
            cand.chunkbaseUrl ||
            `https://www.chunkbase.com/apps/seed-map#${cand.seed}&version=b1.21&x=0&z=0`;

          const villageCount = cand.structures.filter((s) => s.type === 'village').length;
          const trialCount = cand.structures.filter((s) => s.type === 'trial_chamber').length;
          const bastionCount = cand.structures.filter((s) => s.type === 'bastion').length;
          const fortressCount = cand.structures.filter((s) => s.type === 'fortress').length;

          return (
            <div
              key={cand.id}
              onClick={() => onSelectCandidate(cand)}
              className={`p-3 rounded-lg border transition-all cursor-pointer relative group ${
                isSelected
                  ? 'bg-slate-800/95 border-emerald-500 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500/50'
                  : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
              }`}
            >
              {/* Top Row: Seed & Score */}
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-mono text-xs font-bold text-white group-hover:text-emerald-300 transition-colors truncate max-w-[170px]">
                  {cand.seed}
                </span>
                <span
                  className={`text-[11px] font-mono font-bold px-1.5 py-0.5 rounded ${
                    cand.score >= 90
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : cand.score >= 75
                      ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      : 'bg-slate-700 text-slate-300'
                  }`}
                >
                  {cand.score}
                </span>
              </div>

              {/* Terrain, Spawn Distance & Verification Badges */}
              <div className="flex items-center gap-1.5 mb-2 flex-wrap">
                {cand.provenance === 'reference' ? (
                  <span className="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 text-[10px] font-semibold border border-purple-500/30" title="Curated reference finalist from benchmark suite">
                    ★ Reference
                  </span>
                ) : (
                  <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-semibold border border-emerald-500/30" title="Live candidate discovered by native engine sweep">
                    ⚡ Live
                  </span>
                )}
                {cand.terrainPassed !== false ? (
                  <span
                    className="px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-[10px] font-semibold border border-cyan-500/30"
                    title="Certified Coastal Continent: 70–80% mainland & 320m ocean edge"
                  >
                    🌊 Continent
                  </span>
                ) : (
                  <span
                    className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-semibold border border-amber-500/30"
                    title="Baseline Candidate: Passed structure & biome floors; terrain unconstrained"
                  >
                    🏰 Baseline
                  </span>
                )}
                {cand.terrainType.includes('River Highway') && (
                  <span
                    className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 text-[10px] font-semibold border border-blue-500/30"
                    title="Jackpot River Highway: Navigable water corridor linking (0,0) to Sea (+35 pts)"
                  >
                    🛶 River Link (+35)
                  </span>
                )}
                {cand.ravines?.some((r) => r.giant && Math.hypot(r.x, r.z) <= 200) && (
                  <span
                    className="px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-300 text-[10px] font-semibold border border-orange-500/30"
                    title="Jackpot Mega Ravine Hub: Giant magma chasm within ≤200m of (0,0) hub (+35 pts)"
                  >
                    🌋 Mega Ravine Hub (+35)
                  </span>
                )}
                {cand.spawnDistance !== undefined && (
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold flex items-center gap-0.5 ${
                      cand.spawnDistance <= 50
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : cand.spawnDistance <= 100
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                        : 'bg-red-500/20 text-red-300 border border-red-500/30'
                    }`}
                    title={`Spawn Point: (${cand.spawnPoint?.[0] ?? 0}, ${cand.spawnPoint?.[1] ?? 0})`}
                  >
                    🧭 {cand.spawnDistance}m spawn
                  </span>
                )}
                {cand.bdsVerified && (
                  <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 text-[10px] font-semibold border border-blue-500/30">
                    ✓ BDS Certified
                  </span>
                )}
              </div>

              {/* Structure Floor Quick Badges */}
              <div className="flex items-center gap-2 mb-2 text-[10px] font-mono text-slate-400">
                {villageCount > 0 && <span title="Villages">🏡 {villageCount}</span>}
                {trialCount > 0 && <span title="Trial Chambers">⚔️ {trialCount}</span>}
                {fortressCount > 0 && <span title="Nether Fortresses">🏯 {fortressCount}</span>}
                {bastionCount > 0 && <span title="Bastion Remnants">🐖 {bastionCount}</span>}
                {cand.ravines && cand.ravines.length > 0 && (
                  <span
                    title={`Predicted Ravines: ${cand.ravines.length} (${cand.ravines.filter((r) => r.giant).length} Mega)`}
                    className="text-amber-400"
                  >
                    🌋 {cand.ravines.length}
                  </span>
                )}
                {cand.caveClusters && cand.caveClusters.length > 0 && (
                  <span
                    title={`Subterranean Cave Clusters: ${cand.caveClusters.length}`}
                    className="text-emerald-400"
                  >
                    🌿 {cand.caveClusters.length}
                  </span>
                )}
              </div>

              {/* Structure Icons row with Euclidean Distance tooltips */}
              <div className="flex items-center gap-1 mb-2.5 text-xs flex-wrap">
                {cand.structures.slice(0, 6).map((s) => (
                  <span
                    key={s.id}
                    title={`${s.name} (${s.dimension}): ${s.distanceToHub ?? Math.round(Math.sqrt(s.x * s.x + s.z * s.z))}m from hub (X:${s.x}, Z:${s.z})`}
                    className="opacity-90 hover:scale-125 transition-transform cursor-help"
                  >
                    {s.icon}
                  </span>
                ))}
                {cand.structures.length > 6 && (
                  <span className="text-[10px] text-slate-500 font-mono">
                    +{cand.structures.length - 6} more
                  </span>
                )}
              </div>

              {/* Quick Actions Bar */}
              <div className="flex items-center gap-1.5 pt-2 border-t border-slate-800/80 text-[10px]">
                <button
                  onClick={(e) => handleCopySeed(cand.seed, e)}
                  className="flex-1 py-1 px-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors font-medium flex items-center justify-center gap-1"
                  title="Copy Seed Number"
                >
                  📋 Seed
                </button>
                <button
                  onClick={(e) => handleCopyTp(cand, e)}
                  className="flex-1 py-1 px-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors font-medium flex items-center justify-center gap-1"
                  title="Copy /tp command"
                >
                  🧭 /tp
                </button>
                <a
                  href={chunkbaseUrl}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex-1 py-1 px-1.5 rounded bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/30 transition-colors font-medium flex items-center justify-center gap-1"
                  title="One-click open in Chunkbase Bedrock 1.21"
                >
                  ↗ Map
                </a>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onInspectCandidate(cand);
                  }}
                  className="py-1 px-2 rounded bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 transition-colors font-medium"
                  title="View Elevation & 3D Profile"
                >
                  3D View
                </button>
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="p-8 text-center text-slate-500 text-xs">
            No candidates matching current filters ({minScore}+).
          </div>
        )}
      </div>
    </div>
  );
};
