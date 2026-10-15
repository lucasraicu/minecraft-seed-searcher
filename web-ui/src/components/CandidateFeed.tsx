import { compareCandidateRank } from '../utils/ranking';
import React, { useState } from 'react';
import type { SeedCandidate } from '../types';
import { spawnWithinRadius, spawnEvidenceLabel } from '../utils/spawn';

interface CandidateFeedProps {
  candidates: SeedCandidate[];
  selectedCandidate: SeedCandidate | null;
  onSelectCandidate: (candidate: SeedCandidate) => void;
  onInspectCandidate: (candidate: SeedCandidate) => void;
  onCopyNotice: (msg: string) => void;
  onClearCandidates?: () => void;
  onVerifyBDS?: (candidate: SeedCandidate) => void;
  isVerifyingBDS?: boolean;
}

export const CandidateFeed: React.FC<CandidateFeedProps> = ({
  candidates,
  selectedCandidate,
  onSelectCandidate,
  onInspectCandidate,
  onCopyNotice,
  onClearCandidates,
  onVerifyBDS,
  isVerifyingBDS,
}) => {
  const [minScore, setMinScore] = useState<number>(0);
  const [secondaryFilter, setSecondaryFilter] = useState<'all' | 'spawn50' | 'spawn100' | 'bds'>('all');
  const [sortBy, setSortBy] = useState<'rank' | 'score' | 'spawn' | 'structures'>('rank');

  const filtered = candidates
    .filter((c) => {
      if (c.score !== null && c.score < minScore) return false;
      if (secondaryFilter === 'spawn50' && spawnWithinRadius(c, 50) !== true) return false;
      if (secondaryFilter === 'spawn100' && spawnWithinRadius(c, 100) !== true) return false;
      if (secondaryFilter === 'bds' && c.surfaceVerification?.status !== 'PARTIAL') return false;
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'rank') {
        return compareCandidateRank(a, b);
      }
      if (sortBy === 'spawn') {
        return (a.spawnDistance ?? Number.POSITIVE_INFINITY) - (b.spawnDistance ?? Number.POSITIVE_INFINITY);
      }
      if (sortBy === 'structures') {
        return b.structures.length - a.structures.length;
      }
      return (b.score ?? -1) - (a.score ?? -1);
    });

  const handleCopySeed = async (seed: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(seed);
      onCopyNotice(`Copied Seed: ${seed}`);
    } catch (err) {
      onCopyNotice(`Failed to copy seed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleCopyTp = async (c: SeedCandidate, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!c.strongholdAnchor) return;
    const cmd = `/tp @s ${c.strongholdAnchor[0]} 100 ${c.strongholdAnchor[1]}`;
    try {
      await navigator.clipboard.writeText(cmd);
      onCopyNotice(`Copied Teleport: ${cmd}`);
    } catch (err) {
      onCopyNotice(`Failed to copy teleport: ${err instanceof Error ? err.message : String(err)}`);
    }
  };


  return (
    <div className="w-84 h-full bg-slate-900 border-l border-slate-800 flex flex-col z-10 shadow-2xl">
      {/* Header & Controls */}
      <div className="p-4 border-b border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
            <h2 className="text-sm font-bold uppercase tracking-wider text-white">Baseline Candidates</h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-xs font-mono font-bold text-amber-400">
              {filtered.length} / {candidates.length}
            </span>
            {onVerifyBDS && selectedCandidate && (
              <button
                onClick={() => onVerifyBDS(selectedCandidate)}
                disabled={isVerifyingBDS}
                className="px-2 py-0.5 rounded bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 text-[10px] font-bold flex items-center gap-1 transition-all disabled:opacity-40"
                title={`Sample surface points with BDS for seed ${selectedCandidate.seed}`}
              >
                <span>🛡️</span>
                <span>{isVerifyingBDS ? 'Verifying...' : 'Sample Surface'}</span>
              </button>
            )}
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

        <p className="text-[10px] text-slate-400">Canonical baseline order from structure and biome screening. Historical terrain results do not affect this list.</p>

        {/* Marine Timing Notice Banner */}
        <div className="p-2 rounded bg-slate-950/70 border border-slate-800 text-[10px] leading-relaxed text-slate-300">
          <div className="flex items-center gap-1 text-cyan-300 font-semibold mb-0.5">
            <span>⛵</span>
            <span>Marine Gating Notice:</span>
          </div>
          <p className="text-slate-400 text-[9px] leading-tight">
            <strong>Shipwrecks &amp; Ocean Monuments</strong> are required by the current sliding-window baseline. Historical profiles retain their recorded marine scope; actual generation remains unverified.
          </p>
        </div>

        {/* Sort & Filter Controls */}
        <div className="space-y-2 text-xs">
          <div className="flex justify-between items-center text-slate-400">
            <span>Score Threshold:</span>
            <span className="font-mono text-emerald-400 font-bold">{minScore}+</span>
          </div>
          <input
            type="range"
            min="0"
            max={Math.max(100, ...candidates.map((candidate) => Math.ceil(candidate.score ?? 0)))}
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />

          {/* Quick Filter Badges Row: Secondary Attributes */}
          <div className="grid grid-cols-4 gap-1">
            <button
              onClick={() => setSecondaryFilter('all')}
              className={`py-1 rounded text-[10px] font-semibold transition-all ${
                secondaryFilter === 'all'
                  ? 'bg-slate-700 text-white'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
            >
              Any Spawn
            </button>
            <button
              onClick={() => setSecondaryFilter('spawn50')}
              className={`py-1 rounded text-[10px] font-semibold transition-all ${
                secondaryFilter === 'spawn50'
                  ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/30'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
              title="Recorded spawn within 50 horizontal blocks of the evaluation hub; unknown distances are excluded"
            >
              ≤50 blocks
            </button>
            <button
              onClick={() => setSecondaryFilter('spawn100')}
              className={`py-1 rounded text-[10px] font-semibold transition-all ${
                secondaryFilter === 'spawn100'
                  ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/30'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
              title="Recorded spawn within 100 horizontal blocks of the evaluation hub; unknown distances are excluded"
            >
              ≤100 blocks
            </button>
            <button
              onClick={() => setSecondaryFilter('bds')}
              className={`py-1 rounded text-[10px] font-semibold transition-all ${
                secondaryFilter === 'bds'
                  ? 'bg-blue-600/30 text-blue-300 border border-blue-500/30'
                  : 'bg-slate-800/60 text-slate-400 hover:text-white'
              }`}
            >
              BDS points
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
              <option value="rank">Canonical Ranking</option>
              <option value="score">Highest Score</option>
              <option value="spawn">Closest Supplied Spawn</option>
              <option value="structures">Most Structures</option>
            </select>
          </div>
        </div>
      </div>

      {/* Candidate Cards Scrollable List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {filtered.map((cand, idx) => {
          const rank = idx + 1;
          const isSelected = selectedCandidate?.id === cand.id;
          const chunkbaseUrl = cand.chunkbaseUrl;

          const villageCount = cand.structures.filter((s) => s.type === 'village').length;
          const trialCount = cand.structures.filter((s) => s.type === 'trial_chamber').length;
          const bastionCount = cand.structures.filter((s) => s.type === 'bastion').length;
          const fortressCount = cand.structures.filter((s) => s.type === 'fortress').length;
          const monumentCount = cand.structures.filter((s) => s.type === 'monument').length;
          const shipwreckCount = cand.structures.filter((s) => s.type === 'shipwreck').length;

          return (
            <div
              key={cand.id}
              onClick={() => onSelectCandidate(cand)}
              onDoubleClick={(e) => {
                e.stopPropagation();
                onInspectCandidate(cand);
              }}
              title="Click to select on map • Double-click for full expanded candidate details"
              style={{ contentVisibility: 'auto', containIntrinsicSize: '0 160px' }}
              className={`p-3 rounded-lg border transition-all cursor-pointer relative group select-none ${
                isSelected
                  ? 'bg-slate-800/95 border-emerald-500 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500/50'
                  : 'bg-slate-900/80 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
              }`}
            >
              {/* Top Row: Rank, Seed & Score */}
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span
                    className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border shrink-0 ${
                      rank === 1
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 font-extrabold'
                        : rank === 2
                        ? 'bg-slate-300/20 text-slate-200 border-slate-300/40'
                        : rank === 3
                        ? 'bg-orange-700/20 text-orange-300 border-orange-600/40'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                    title={`Rank #${rank} in the displayed filtered pool`}
                  >
                    #{rank}
                  </span>
                  <span className="font-mono text-xs font-bold text-white group-hover:text-emerald-300 transition-colors truncate max-w-[140px]">
                    {cand.seed}
                  </span>
                </div>
                <span
                  className={`text-[11px] font-mono font-bold px-1.5 py-0.5 rounded shrink-0 ${
                    cand.score !== null && cand.score >= 90
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : cand.score !== null && cand.score >= 75
                      ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      : 'bg-slate-700 text-slate-300'
                  }`}
                >
                  {cand.score === null ? 'Unrated' : `${cand.score} pts`}
                </span>
              </div>

              {/* Terrain, Spawn Distance & Verification Badges */}
              <div className="flex items-center gap-1.5 mb-2 flex-wrap">
                {cand.provenance === 'reference' ? (
                  <span className="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 text-[10px] font-semibold border border-purple-500/30" title="Illustrative sample; not a live scan result">
                    DEMO SAMPLE
                  </span>
                ) : cand.provenance === 'live' ? (
                  <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-semibold border border-emerald-500/30" title="Candidate record returned by the live backend">
                    ⚡ Live
                  </span>
                ) : (
                  <span className="px-1.5 py-0.5 rounded bg-slate-700 text-slate-300 text-[10px] font-semibold border border-slate-600" title="Source provenance was not provided">
                    Source unknown
                  </span>
                )}
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-semibold border border-slate-700"
                  title="Baseline structure and biome candidate; terrain geometry is not a qualification gate">
                  🏰 Baseline candidate
                </span>
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px] border border-slate-700"
                  title={(cand.screeningRevision === 'origin-fixed-2048-two-group-marine-v3' || cand.screeningRevision === 'dynamic-envelope-1664-v1')
                    ? 'Marine start counts are required by this baseline; actual generation is unverified'
                    : 'Historical baseline deferred marine structures'}>
                  ⛵ Marine: {cand.marineStatus?.toLowerCase() ??
                    ((cand.screeningRevision === 'origin-fixed-2048-two-group-marine-v3' || cand.screeningRevision === 'dynamic-envelope-1664-v1') ? 'required' : 'deferred')}
                </span>
                {cand.ravines?.some((r) => r.giant && Math.hypot(r.x, r.z) <= 200) && (
                  <span
                    className="px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-300 text-[10px] font-semibold border border-orange-500/30"
                    title="Ravine marker supplied by candidate record"
                  >
                    🌋 Mega ravine marker
                  </span>
                )}
                {(
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold flex items-center gap-0.5 ${
                      spawnWithinRadius(cand, 50) === true
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : spawnWithinRadius(cand, 100) === true
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                        : spawnWithinRadius(cand, 100) === false
                        ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                        : 'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}
                    title={`${spawnEvidenceLabel(cand)}; distance from evaluation hub. Target: 100 horizontal blocks. Unknown is not a pass.`}
                  >
                    🧭 {cand.spawnDistance == null ? 'Spawn ≤100: unknown' : `${cand.spawnDistance} blocks · ${spawnEvidenceLabel(cand)}`}
                    {cand.spawnDistance != null && (spawnWithinRadius(cand, 100) ? ' · ≤100' : ' · >100')}
                  </span>
                )}
                {cand.surfaceVerification?.status === 'PARTIAL' && (
                  <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 text-[10px] font-semibold border border-blue-500/30">
                    BDS surface points
                  </span>
                )}
              </div>

              {/* Structure Floor Quick Badges with Instant Tooltips */}
              <div className="flex items-center gap-1.5 mb-2 text-[10px] font-mono text-slate-400 flex-wrap">
                {villageCount > 0 && (
                  <div className="relative group/tip inline-flex items-center cursor-help">
                    <span className="px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 flex items-center gap-1 hover:bg-amber-500/20 transition-colors">
                      <span>🏡</span> <span>{villageCount}</span>
                    </span>
                    <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover/tip:flex flex-col items-center z-50 whitespace-nowrap rounded-md bg-slate-950 px-2.5 py-1 text-[11px] font-semibold text-white shadow-2xl border border-slate-700 animate-in fade-in zoom-in-95 duration-100">
                      <div className="flex items-center gap-1">
                        <span>🏡</span>
                        <span className="font-bold text-amber-400">Village ({villageCount})</span>
                      </div>
                      <span className="text-[9px] text-slate-400 font-normal">Overworld population center</span>
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
                    </div>
                  </div>
                )}
                {trialCount > 0 && (
                  <div className="relative group/tip inline-flex items-center cursor-help">
                    <span className="px-1.5 py-0.5 rounded bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 flex items-center gap-1 hover:bg-yellow-500/20 transition-colors">
                      <span>⚔️</span> <span>{trialCount}</span>
                    </span>
                    <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover/tip:flex flex-col items-center z-50 whitespace-nowrap rounded-md bg-slate-950 px-2.5 py-1 text-[11px] font-semibold text-white shadow-2xl border border-slate-700 animate-in fade-in zoom-in-95 duration-100">
                      <div className="flex items-center gap-1">
                        <span>⚔️</span>
                        <span className="font-bold text-yellow-400">Trial Chamber ({trialCount})</span>
                      </div>
                      <span className="text-[9px] text-slate-400 font-normal">Underground combat chamber</span>
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
                    </div>
                  </div>
                )}
                {fortressCount > 0 && (
                  <div className="relative group/tip inline-flex items-center cursor-help">
                    <span className="px-1.5 py-0.5 rounded bg-red-500/10 border border-red-500/30 text-red-300 flex items-center gap-1 hover:bg-red-500/20 transition-colors">
                      <span>🏯</span> <span>{fortressCount}</span>
                    </span>
                    <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover/tip:flex flex-col items-center z-50 whitespace-nowrap rounded-md bg-slate-950 px-2.5 py-1 text-[11px] font-semibold text-white shadow-2xl border border-slate-700 animate-in fade-in zoom-in-95 duration-100">
                      <div className="flex items-center gap-1">
                        <span>🏯</span>
                        <span className="font-bold text-red-400">Nether Fortress ({fortressCount})</span>
                      </div>
                      <span className="text-[9px] text-slate-400 font-normal">Blaze rods & Nether wart source</span>
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
                    </div>
                  </div>
                )}
                {bastionCount > 0 && (
                  <div className="relative group/tip inline-flex items-center cursor-help">
                    <span className="px-1.5 py-0.5 rounded bg-amber-600/10 border border-amber-600/30 text-amber-200 flex items-center gap-1 hover:bg-amber-600/20 transition-colors">
                      <span>🐖</span> <span>{bastionCount}</span>
                    </span>
                    <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover/tip:flex flex-col items-center z-50 whitespace-nowrap rounded-md bg-slate-950 px-2.5 py-1 text-[11px] font-semibold text-white shadow-2xl border border-slate-700 animate-in fade-in zoom-in-95 duration-100">
                      <div className="flex items-center gap-1">
                        <span>🐖</span>
                        <span className="font-bold text-amber-300">Bastion Remnant ({bastionCount})</span>
                      </div>
                      <span className="text-[9px] text-slate-400 font-normal">Piglin bartering & Netherite upgrade</span>
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
                    </div>
                  </div>
                )}
                {monumentCount > 0 && (
                  <div className="relative group/tip inline-flex items-center cursor-help">
                    <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 flex items-center gap-1 hover:bg-cyan-500/20 transition-colors">
                      <span>🏛️</span> <span>{monumentCount}</span>
                    </span>
                    <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover/tip:flex flex-col items-center z-50 whitespace-nowrap rounded-md bg-slate-950 px-2.5 py-1 text-[11px] font-semibold text-white shadow-2xl border border-slate-700 animate-in fade-in zoom-in-95 duration-100">
                      <div className="flex items-center gap-1">
                        <span>🏛️</span>
                        <span className="font-bold text-cyan-300">Ocean Monument ({monumentCount})</span>
                      </div>
                      <span className="text-[9px] text-slate-400 font-normal">Deep ocean Elder Guardian temple</span>
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
                    </div>
                  </div>
                )}
                {shipwreckCount > 0 && (
                  <div className="relative group/tip inline-flex items-center cursor-help">
                    <span className="px-1.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/30 text-blue-300 flex items-center gap-1 hover:bg-blue-500/20 transition-colors">
                      <span>⛵</span> <span>{shipwreckCount}</span>
                    </span>
                    <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover/tip:flex flex-col items-center z-50 whitespace-nowrap rounded-md bg-slate-950 px-2.5 py-1 text-[11px] font-semibold text-white shadow-2xl border border-slate-700 animate-in fade-in zoom-in-95 duration-100">
                      <div className="flex items-center gap-1">
                        <span>⛵</span>
                        <span className="font-bold text-blue-300">Shipwreck ({shipwreckCount})</span>
                      </div>
                      <span className="text-[9px] text-slate-400 font-normal">Buried treasure map & supply loot</span>
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
                    </div>
                  </div>
                )}
                {cand.ravines && cand.ravines.length > 0 && (
                  <div className="relative group/tip inline-flex items-center cursor-help">
                    <span className="px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 flex items-center gap-1 hover:bg-amber-500/20 transition-colors">
                      <span>🌋</span> <span>{cand.ravines.length}</span>
                    </span>
                    <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover/tip:flex flex-col items-center z-50 whitespace-nowrap rounded-md bg-slate-950 px-2.5 py-1 text-[11px] font-semibold text-white shadow-2xl border border-slate-700 animate-in fade-in zoom-in-95 duration-100">
                      <div className="flex items-center gap-1">
                        <span>🌋</span>
                        <span className="font-bold text-amber-300">Ravines ({cand.ravines.length})</span>
                      </div>
                      <span className="text-[9px] text-slate-400 font-normal">{cand.ravines.filter((r) => r.giant).length} Mega ravines detected</span>
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
                    </div>
                  </div>
                )}
                {cand.caveClusters && cand.caveClusters.length > 0 && (
                  <div className="relative group/tip inline-flex items-center cursor-help">
                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-1 hover:bg-emerald-500/20 transition-colors">
                      <span>🌿</span> <span>{cand.caveClusters.length}</span>
                    </span>
                    <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover/tip:flex flex-col items-center z-50 whitespace-nowrap rounded-md bg-slate-950 px-2.5 py-1 text-[11px] font-semibold text-white shadow-2xl border border-slate-700 animate-in fade-in zoom-in-95 duration-100">
                      <div className="flex items-center gap-1">
                        <span>🌿</span>
                        <span className="font-bold text-emerald-300">Subterranean Caves ({cand.caveClusters.length})</span>
                      </div>
                      <span className="text-[9px] text-slate-400 font-normal">Lush, Deep Dark, & Dripstone clusters</span>
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
                    </div>
                  </div>
                )}
              </div>

              {/* Structure Icons row with Instant Interactive Tooltips */}
              <div className="flex items-center gap-1.5 mb-2.5 text-xs flex-wrap">
                {cand.structures.slice(0, 10).map((s) => (
                  <div key={s.id} className="relative group/tip inline-flex items-center cursor-help">
                    <span className="opacity-90 hover:scale-130 transition-transform p-0.5 rounded hover:bg-slate-800">
                      {s.icon}
                    </span>
                    {/* Instant Hover Tooltip */}
                    <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/tip:flex flex-col items-center z-50 whitespace-nowrap rounded-md bg-slate-950 px-2.5 py-1.5 text-[11px] font-semibold text-white shadow-2xl border border-slate-700 animate-in fade-in zoom-in-95 duration-100">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm">{s.icon}</span>
                        <span className="font-bold text-emerald-400">{s.name}</span>
                        <span className="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-slate-300 uppercase font-mono border border-slate-700">
                          {s.dimension}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-300 font-mono mt-0.5">
                        <span className="text-cyan-300 font-semibold">{Math.round(s.distanceToOrigin ?? Math.hypot(s.x, s.z))} blocks from (0,0)</span>
                        {s.distanceToHub != null && Math.abs((s.distanceToHub ?? 0) - Math.hypot(s.x, s.z)) > 2 && (
                          <span className="text-slate-400"> • {s.distanceToHub} to Hub</span>
                        )}
                        {s.distanceToSpawn != null && (
                          <span className="text-emerald-400"> • {s.distanceToSpawn} to Spawn</span>
                        )}
                        {' • '}X: {s.x}, Z: {s.z}
                        {s.y != null && `, Y: ${s.y}`}
                      </div>
                      {s.type === 'monument' || s.type === 'shipwreck' ? (
                        <span className="text-[9px] text-cyan-400 mt-0.5">Marine structure</span>
                      ) : null}
                      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
                    </div>
                  </div>
                ))}
                {cand.structures.length > 10 && (
                  <span className="text-[10px] text-slate-500 font-mono">
                    +{cand.structures.length - 10} more
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
                  disabled={!cand.strongholdAnchor}
                  className="flex-1 py-1 px-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-slate-800 text-slate-300 transition-colors font-medium flex items-center justify-center gap-1"
                  title={cand.strongholdAnchor ? 'Copy teleport to supplied stronghold anchor' : 'Stronghold anchor coordinates are pending'}
                >
                  🧭 /tp
                </button>
                {chunkbaseUrl && <a
                  href={chunkbaseUrl}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex-1 py-1 px-1.5 rounded bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/30 transition-colors font-medium flex items-center justify-center gap-1"
                  title="Backend supplied a verified map link"
                >
                  ↗ Map
                </a>}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onInspectCandidate(cand);
                  }}
                  className="py-1 px-2 rounded bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 transition-colors font-medium flex items-center gap-1"
                  title="Open Full Expanded Candidate Details (or Double-Click card)"
                >
                  🔍 Inspect
                </button>
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="p-8 text-center text-slate-500 text-xs space-y-2">
            <div>No baseline candidates matching current filters.</div>
          </div>
        )}
      </div>
    </div>
  );
};
