import React, { useState } from 'react';
import type { SeedCandidate } from '../types';

interface CandidateFeedProps {
  candidates: SeedCandidate[];
  selectedCandidate: SeedCandidate | null;
  onSelectCandidate: (candidate: SeedCandidate) => void;
  onInspectCandidate: (candidate: SeedCandidate) => void;
  onCopyNotice: (msg: string) => void;
}

export const CandidateFeed: React.FC<CandidateFeedProps> = ({
  candidates,
  selectedCandidate,
  onSelectCandidate,
  onInspectCandidate,
  onCopyNotice,
}) => {
  const [minScore, setMinScore] = useState<number>(90);
  const [terrainFilter, setTerrainFilter] = useState<string>('all');

  const filtered = candidates.filter((c) => {
    if (c.score < minScore) return false;
    if (terrainFilter !== 'all' && c.terrainType !== terrainFilter) return false;
    return true;
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
    <div className="w-80 h-full bg-slate-900 border-l border-slate-800 flex flex-col z-10 shadow-2xl">
      {/* Header & Filter Controls */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
            <h2 className="text-sm font-bold uppercase tracking-wider text-white">Candidates Found</h2>
          </div>
          <span className="px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-xs font-mono font-bold text-amber-400">
            {filtered.length} / {candidates.length}
          </span>
        </div>

        {/* Filter Sliders / Dropdowns */}
        <div className="space-y-2 text-xs">
          <div className="flex justify-between items-center text-slate-400">
            <span>Min Score:</span>
            <span className="font-mono text-emerald-400 font-bold">{minScore}+</span>
          </div>
          <input
            type="range"
            min="80"
            max="98"
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />

          <div className="flex gap-1.5 pt-1">
            <button
              onClick={() => setTerrainFilter('all')}
              className={`flex-1 py-1 rounded text-[11px] font-semibold transition-all ${
                terrainFilter === 'all'
                  ? 'bg-slate-700 text-white'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setTerrainFilter('V1 Island')}
              className={`flex-1 py-1 rounded text-[11px] font-semibold transition-all ${
                terrainFilter === 'V1 Island'
                  ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/30'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
            >
              V1 Island
            </button>
            <button
              onClick={() => setTerrainFilter('V2 Mountain Basin')}
              className={`flex-1 py-1 rounded text-[11px] font-semibold transition-all ${
                terrainFilter === 'V2 Mountain Basin'
                  ? 'bg-blue-600/30 text-blue-300 border border-blue-500/30'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
            >
              V2 Basin
            </button>
          </div>
        </div>
      </div>

      {/* Candidate Cards Scrollable List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {filtered.map((cand) => {
          const isSelected = selectedCandidate?.id === cand.id;
          return (
            <div
              key={cand.id}
              onClick={() => onSelectCandidate(cand)}
              className={`p-3 rounded-lg border transition-all cursor-pointer relative group ${
                isSelected
                  ? 'bg-slate-800/90 border-emerald-500 shadow-lg shadow-emerald-500/10'
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
                    cand.score >= 95
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}
                >
                  {cand.score}
                </span>
              </div>

              {/* Terrain & Verification Badges */}
              <div className="flex items-center gap-1.5 mb-2 flex-wrap">
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 font-medium">
                  {cand.terrainType}
                </span>
                {cand.bdsVerified ? (
                  <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 text-[10px] font-semibold border border-blue-500/30 flex items-center gap-1">
                    ✓ BDS Certified
                  </span>
                ) : (
                  <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">
                    Predicted
                  </span>
                )}
                <span className="text-[10px] text-slate-400 font-mono">
                  Ø {cand.terrainMetrics.diameter}m
                </span>
              </div>

              {/* Structure Icons row */}
              <div className="flex items-center gap-1 mb-2.5 text-xs">
                {cand.structures.slice(0, 5).map((s) => (
                  <span key={s.id} title={`${s.name} (${s.dimension})`} className="opacity-90 hover:scale-125 transition-transform">
                    {s.icon}
                  </span>
                ))}
                {cand.structures.length > 5 && (
                  <span className="text-[10px] text-slate-500 font-mono">+{cand.structures.length - 5}</span>
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
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onInspectCandidate(cand);
                  }}
                  className="py-1 px-2 rounded bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 transition-colors font-medium"
                  title="View Elevation & 3D Wireframe Profile"
                >
                  3D View
                </button>
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="p-8 text-center text-slate-500 text-xs">
            No candidates matching current score filter ({minScore}+).
          </div>
        )}
      </div>
    </div>
  );
};
