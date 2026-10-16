import React, { useState, useEffect, useRef } from 'react';
import type { SeedCandidate } from '../types';
import { spawnWithinRadius, spawnEvidenceLabel } from '../utils/spawn';

interface SeedDetailModalProps {
  candidate: SeedCandidate | null;
  onClose: () => void;
  onCopyNotice: (msg: string) => void;
  onVerifyBDS?: (candidate: SeedCandidate) => void;
  isVerifyingBDS?: boolean;
}

export const SeedDetailModal: React.FC<SeedDetailModalProps> = ({
  candidate,
  onClose,
  onCopyNotice,
  onVerifyBDS,
  isVerifyingBDS,
}) => {
  const modalRef = useRef<HTMLDivElement | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'structures' | 'biomes' | 'underground'>('overview');
  const [structureDimFilter, setStructureDimFilter] = useState<'all' | 'overworld' | 'nether'>('all');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === 'Tab' && modalRef.current) {
        const focusableElements = modalRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement || !modalRef.current.contains(document.activeElement)) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement || !modalRef.current.contains(document.activeElement)) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    const timer = setTimeout(() => {
      if (modalRef.current) {
        const firstFocusable = modalRef.current.querySelector<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        firstFocusable?.focus();
      }
    }, 0);

    return () => {
      clearTimeout(timer);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose]);

  if (!candidate) return null;

  const chunkbaseUrl = candidate.chunkbaseUrl;
  const spawn = candidate.spawnPoint;
  const spawnDist = candidate.spawnDistance;
  const isDemo = candidate.provenance === 'reference';
  const stronghold = candidate.strongholdAnchor;
  const center = candidate.evaluationCenter ?? [0, 0];
  const isHubOrigin = center[0] === 0 && center[1] === 0;

  const overworldStructures = candidate.structures.filter((s) => s.dimension === 'overworld');
  const netherStructures = candidate.structures.filter((s) => s.dimension === 'nether');

  const displayedStructures = candidate.structures.filter((s) => {
    if (structureDimFilter === 'overworld') return s.dimension === 'overworld';
    if (structureDimFilter === 'nether') return s.dimension === 'nether';
    return true;
  });

  const tpCommand = spawn
    ? `/tp @p ${Math.round(spawn[0])} ~ ${Math.round(spawn[1])}`
    : stronghold
    ? `/tp @p ${Math.round(stronghold[0])} ~ ${Math.round(stronghold[1])}`
    : `/tp @p 0 ~ 0`;

  const copyText = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      onCopyNotice(`Copied ${label}: ${text}`);
    } catch (err) {
      onCopyNotice(`Failed to copy: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-5"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="seed-modal-title"
        tabIndex={-1}
        className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-5xl w-full max-h-[90vh] flex flex-col overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-150 outline-none"
      >
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 bg-slate-950/90 flex items-center justify-between shrink-0">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 id="seed-modal-title" className="text-lg font-bold text-white flex items-center gap-1.5">
                <span>🌱</span>
                <span>Expanded Seed Candidate Report</span>
              </h3>
              <span
                className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] border ${
                  isDemo
                    ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                    : candidate.provenance === 'live'
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : 'bg-slate-700 text-slate-300 border-slate-600'
                }`}
              >
                {isDemo ? 'DEMO SAMPLE' : candidate.provenance === 'live' ? '⚡ LIVE' : 'SOURCE UNKNOWN'}
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono font-bold text-xs border border-emerald-500/30">
                {candidate.score === null ? 'Unrated' : `Score: ${candidate.score} pts`}
              </span>
              <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 font-mono text-[10px] border border-cyan-500/30">
                Candidate Evidence
              </span>
              {candidate.rankingTier != null && (
                <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 font-mono text-[10px] border border-amber-500/30">
                  {candidate.screeningRevision === 'dynamic-envelope-1664-v1' ? 'Deficit Tier' : 'Ranking Tier'} #{candidate.rankingTier}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs font-mono text-slate-400 mt-1 flex-wrap">
              <span>Seed: <strong className="text-emerald-300 font-bold select-all">{candidate.seed}</strong></span>
              {candidate.discoveredAt && <span>Discovered: {candidate.discoveredAt}</span>}
              {candidate.screeningRevision && (
                <span className="text-slate-500">Screening Revision: {candidate.screeningRevision}</span>
              )}
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center text-sm font-bold transition-colors shrink-0"
            title="Close expanded view (Esc)"
          >
            ✕
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="px-5 py-2.5 bg-slate-950/60 border-b border-slate-800/80 flex items-center gap-1.5 overflow-x-auto shrink-0 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'overview'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30 font-bold'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <span>🧭</span>
            <span>Strategic Overview</span>
          </button>
          <button
            onClick={() => setActiveTab('structures')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'structures'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30 font-bold'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <span>🏰</span>
            <span>Structure Catalog ({candidate.structures.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('biomes')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'biomes'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30 font-bold'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <span>🗺️</span>
            <span>Biomes &amp; Witnesses ({candidate.biomes?.length || Object.keys(candidate.biomeWitnesses || {}).length || 0})</span>
          </button>
          <button
            onClick={() => setActiveTab('underground')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'underground'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30 font-bold'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <span>🌋</span>
            <span>Caves &amp; Ravines ({(candidate.ravines?.length || 0) + (candidate.caveClusters?.length || 0)})</span>
          </button>
        </div>

        {/* Modal Scrollable Content */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1">
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-4">
              {/* Strategic Anchors & Key Coordinates Banner */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* 1. Stronghold Anchor */}
                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-semibold uppercase tracking-wider flex items-center gap-1">
                      <span>🏰</span> Stronghold Anchor
                    </span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 font-mono font-bold">
                      {stronghold ? 'Pinned' : 'Pending'}
                    </span>
                  </div>
                  <div className="text-sm font-bold font-mono text-emerald-400">
                    {stronghold ? `X: ${stronghold[0]}, Z: ${stronghold[1]}` : 'None reported'}
                  </div>
                  <p className="text-[10px] text-slate-500">
                    Anchor structure used for radial deployment &amp; geometry evaluation
                  </p>
                </div>

                {/* 2. World Spawn */}
                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-semibold uppercase tracking-wider flex items-center gap-1">
                      <span>🧭</span> Spawn · 100-block target
                    </span>
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold ${
                        spawnWithinRadius(candidate, 50) === true
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : spawnWithinRadius(candidate, 100) === true
                          ? 'bg-cyan-500/20 text-cyan-300'
                          : 'bg-amber-500/20 text-amber-300'
                      }`}
                    >
                      {spawnDist != null ? `${spawnDist} blocks · ${spawnWithinRadius(candidate, 100) ? 'within 100' : 'outside 100'}` : 'Unknown'}
                    </span>
                  </div>
                  <div className="text-sm font-bold font-mono text-cyan-400">
                    {spawn ? `X: ${spawn[0]}, Z: ${spawn[1]}` : 'Coordinates pending'}
                  </div>
                  <p className="text-[10px] text-slate-500">
                    {spawnEvidenceLabel(candidate)}. Horizontal distance from the evaluation hub. This metric does not filter the native sweep; initial-player placement needs its own evidence.
                  </p>
                </div>

                {/* 3. Evaluation Center */}
                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-semibold uppercase tracking-wider flex items-center gap-1">
                      <span>🎯</span> Evaluation Center
                    </span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 font-mono font-bold">
                      {center[0] === 0 && center[1] === 0 ? 'Origin Hub' : 'Custom Center'}
                    </span>
                  </div>
                  <div className="text-sm font-bold font-mono text-indigo-300">
                    X: {center[0]}, Z: {center[1]}
                  </div>
                  <p className="text-[10px] text-slate-500">
                    {candidate.screeningRevision === 'dynamic-envelope-1664-v1' ? 'Selected density center for the 1664-block playable window' : 'Evaluation center of this historical search'}
                  </p>
                </div>

                {/* Baseline qualification is independent of historical terrain records. */}
                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                  <span className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">🏰 Baseline qualification</span>
                  <div className="text-sm font-bold font-mono text-white">{candidate.baselineStatus ?? 'PREDICTED'}</div>
                  <p className="text-[10px] text-slate-500">
                    {candidate.screeningRevision === 'dynamic-envelope-1664-v1'
                      ? 'Mandatory Mansion, Stronghold, Monument, Outposts, Fortresses and Bastions, bounded category deficits and biome witnesses inside the selected window; actual generation remains unverified.'
                      : candidate.screeningRevision === 'origin-fixed-2048-two-group-marine-v3'
                      ? 'Predicted structure starts, including one Monument and three Shipwrecks, and biome families; terrain geometry and actual generation remain unverified.'
                      : 'Historical baseline structure and biome screening; marine structures and terrain geometry were deferred.'}
                  </p>
                </div>
              </div>

              {candidate.suggestedSpawn && (
                <div className="p-4 bg-slate-950/80 border border-emerald-900/40 rounded-xl space-y-2 text-xs">
                  <h4 className="font-bold text-emerald-300">Suggested community spawn</h4>
                  {candidate.suggestedSpawn.coordinates ? (
                    <p>X: {candidate.suggestedSpawn.coordinates[0]}, Z: {candidate.suggestedSpawn.coordinates[2]} · {candidate.suggestedSpawn.biome} · {Math.round(candidate.suggestedSpawn.distance ?? 0)} blocks from hub</p>
                  ) : <p>{candidate.suggestedSpawn.reason ?? 'No suggestion available'}</p>}
                  <p className="text-slate-400">Biome-based prediction sampled at Y=63. Actual ground height and safety remain unverified.</p>
                </div>
              )}
              {candidate.playerInspections && (
                <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2 text-xs">
                  <h4 className="font-bold text-slate-200">Optional player inspections</h4>
                  {Object.entries(candidate.playerInspections).map(([name, inspection]) => (
                    <div key={name} className="space-y-1">
                      <p className="text-slate-300">{({ end_access: 'End access', portal_links: 'Portal arrival and return links', snow_ice_resources: 'Snow and ice resources' } as Record<string, string>)[name] ?? name}: <span className="font-mono">{inspection.status}</span></p>
                      <p className="text-slate-400">{inspection.reason}</p>
                      {inspection.source && <p className="text-slate-500">Source: {[inspection.source.kind, inspection.source.provider, inspection.source.version].filter(Boolean).join(' · ')}</p>}
                    </div>
                  ))}
                </div>
              )}

              {/* V3 Player Scoring Breakdown (when available) */}
              {(candidate.scoreComponents || candidate.bonusTotal != null) && (() => {
                const center = candidate.evaluationCenter ?? [0, 0];
                const pnx = Math.floor(center[0] / 8);
                const pnz = Math.floor(center[1] / 8);
                const fortresses = candidate.structures.filter((s) => s.type === 'fortress');
                const bastions = candidate.structures.filter((s) => s.type === 'bastion');
                const hasCloseFortress = fortresses.some((s) => (s.x - pnx) ** 2 + (s.z - pnz) ** 2 <= 256 ** 2);
                const hasCloseBastion = bastions.some((s) => (s.x - pnx) ** 2 + (s.z - pnz) ** 2 <= 256 ** 2);
                const computedNetherCore = (hasCloseFortress ? 10 : 0) + (hasCloseBastion ? 10 : 0);
                const netherCoreBonus = candidate.netherCoreBonus ?? candidate.scoreComponents?.nether_core_bonus ?? computedNetherCore;
                const isFortressClose = hasCloseFortress || netherCoreBonus === 20 || (netherCoreBonus === 10 && !hasCloseBastion);
                const isBastionClose = hasCloseBastion || netherCoreBonus === 20 || (netherCoreBonus === 10 && !hasCloseFortress);

                const isV3 = candidate.screeningRevision ? candidate.screeningRevision === 'dynamic-envelope-2048-v3' : true;
                const coreSurplus = candidate.scoreComponents?.core_surplus ?? 0;
                const optionalBonus = candidate.scoreComponents?.optional_bonus ?? 0;
                const luxuryBiomes = candidate.scoreComponents?.luxury_biomes ?? 0;
                const hubBonus = candidate.scoreComponents?.hub_bonus ?? 0;
                const scenicBonus = candidate.scenicBonus ?? candidate.scoreComponents?.scenic_bonus ?? 0;
                const villageSpreadBonus = candidate.villageSpreadBonus ?? candidate.scoreComponents?.village_spread_bonus ?? 0;
                const treasureBastionBonus = candidate.scoreComponents?.treasure_bastion_bonus ?? (candidate.treasureBastion ? (isV3 ? 20 : 40) : 0);
                const spatialNetherBonus = hubBonus + netherCoreBonus + scenicBonus + villageSpreadBonus + (isV3 ? treasureBastionBonus : 0);

                const deficitPenalty = candidate.deficitPenalty ?? candidate.scoreComponents?.deficit_penalty ?? 0;
                const unmet = candidate.unmetRequirements ?? 0;
                const hasDeficits = deficitPenalty > 0 || unmet > 0;

                return (
                  <div className="p-4 bg-slate-950/80 border border-indigo-900/40 rounded-xl space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-300 flex items-center gap-1.5">
                        <span>💎</span>
                        <span>Player Quality Score Breakdown ({isV3 ? 'dynamic-v3: 1,250 Pts Max' : 'dynamic-v2: 1,140 Pts Max'})</span>
                      </h4>
                      <span className="text-xs font-mono font-bold text-emerald-400">
                        Score: {candidate.score} / Bonus: {candidate.bonusTotal ?? candidate.scoreComponents?.bonus_total ?? 0}
                        {deficitPenalty > 0 && (
                          <span className="text-rose-400 ml-1.5">
                            (-{deficitPenalty} deficit penalty)
                          </span>
                        )}
                      </span>
                    </div>

                    {/* 4 Primary Categories Breakdown */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs font-mono">
                      <div className="p-2.5 bg-slate-900/90 rounded-lg border border-slate-800">
                        <span className="text-indigo-400 text-[10px] block font-semibold uppercase">Core Surplus</span>
                        <span className="text-white font-bold text-base">+{coreSurplus}</span>
                        <span className="text-[10px] text-slate-400 block font-sans">{isV3 ? '+650 max' : '+540 max'}</span>
                      </div>
                      <div className="p-2.5 bg-slate-900/90 rounded-lg border border-slate-800">
                        <span className="text-indigo-400 text-[10px] block font-semibold uppercase">Optional Structures</span>
                        <span className="text-white font-bold text-base">+{optionalBonus}</span>
                        <span className="text-[10px] text-slate-400 block font-sans">{isV3 ? '+200 max' : '+240 max'}</span>
                      </div>
                      <div className="p-2.5 bg-slate-900/90 rounded-lg border border-slate-800">
                        <span className="text-indigo-400 text-[10px] block font-semibold uppercase">Luxury Biomes</span>
                        <span className="text-white font-bold text-base">+{luxuryBiomes}</span>
                        <span className="text-[10px] text-slate-400 block font-sans">+265 max</span>
                      </div>
                      <div className="p-2.5 bg-slate-900/90 rounded-lg border border-slate-800">
                        <span className="text-indigo-400 text-[10px] block font-semibold uppercase">Spatial &amp; Nether</span>
                        <span className="text-emerald-400 font-bold text-base">+{spatialNetherBonus}</span>
                        <span className="text-[10px] text-slate-400 block font-sans">{isV3 ? '+135 max' : '+95 max'}</span>
                      </div>
                    </div>

                    {/* Spatial & Nether Details & Badges */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 text-center text-xs font-mono">
                      <div className="p-2 bg-slate-900/70 rounded-lg border border-slate-800">
                        <span className="text-slate-400 text-[10px] block font-semibold uppercase">Starter Hub</span>
                        <span className="text-white font-bold text-sm">+{hubBonus}</span>
                        <span className="text-[9px] text-slate-400 block font-sans">+45 max</span>
                        {candidate.starterHubVillage ? (
                          <span className="text-[9px] text-cyan-400 block font-sans truncate">Village ({candidate.starterHubVillage[0]}, {candidate.starterHubVillage[1]})</span>
                        ) : null}
                      </div>
                      <div className="p-2 bg-slate-900/70 rounded-lg border border-slate-800">
                        <span className="text-slate-400 text-[10px] block font-semibold uppercase">Nether Portal Core</span>
                        <span className="text-white font-bold text-sm">+{netherCoreBonus}</span>
                        <span className="text-[9px] text-slate-400 block font-sans">+20 max</span>
                        <div className="flex flex-col gap-0.5 text-[8.5px] mt-0.5 font-sans">
                          <span className={isFortressClose ? 'text-emerald-400 font-semibold' : 'text-slate-400'}>
                            Fortress ≤256m (+10)
                          </span>
                          <span className={isBastionClose ? 'text-emerald-400 font-semibold' : 'text-slate-400'}>
                            Bastion ≤256m (+10)
                          </span>
                        </div>
                      </div>
                      <div className="p-2 bg-slate-900/70 rounded-lg border border-slate-800">
                        <span className="text-slate-400 text-[10px] block font-semibold uppercase">Scenic River</span>
                        <span className="text-white font-bold text-sm">+{scenicBonus}</span>
                        <span className="text-[9px] text-slate-400 block font-sans">{isV3 ? '+25 max' : '+20 max'}</span>
                        {candidate.scenicWitness ? (
                          <span className="text-[9px] text-cyan-400 block font-sans truncate">Pair ({candidate.scenicWitness[0]}, {candidate.scenicWitness[1]})</span>
                        ) : null}
                      </div>
                      <div className="p-2 bg-slate-900/70 rounded-lg border border-slate-800">
                        <span className="text-slate-400 text-[10px] block font-semibold uppercase">Village Spread</span>
                        <span className="text-white font-bold text-sm">+{villageSpreadBonus}</span>
                        <span className="text-[9px] text-slate-400 block font-sans">{isV3 ? '+25 max' : '+15 max'}</span>
                        {candidate.villageTriple ? (
                          <span className="text-[9px] text-emerald-400 block font-sans">Tri-Quadrant (3)</span>
                        ) : null}
                      </div>
                      <div className="p-2 bg-slate-900/70 rounded-lg border border-slate-800">
                        <span className="text-slate-400 text-[10px] block font-semibold uppercase">Treasure Bastion</span>
                        <span className="text-white font-bold text-sm">+{treasureBastionBonus}</span>
                        <span className="text-[9px] text-slate-400 block font-sans">{isV3 ? '+20 max (v3)' : '+40 max (v2 in optional)'}</span>
                        {candidate.treasureBastion ? (
                          <span className="text-[9px] text-amber-400 block font-sans">Treasure Bastion (+{isV3 ? 20 : 40})</span>
                        ) : null}
                      </div>
                    </div>

                    {/* Deficits card: conditionally rendered only when deficits exist */}
                    {hasDeficits && (
                      <div className="p-2.5 bg-rose-950/40 rounded-lg border border-rose-900/60 flex items-center justify-between text-xs font-mono px-3">
                        <span className="text-rose-400 font-semibold uppercase text-[11px] flex items-center gap-1.5">
                          <span>⚠️</span> Deficits Penalty
                        </span>
                        <span className="text-rose-400 font-bold">
                          -{deficitPenalty} pts ({unmet} missing requirement{unmet === 1 ? '' : 's'})
                        </span>
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Quick Summary Counts Cards */}
              <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <span>📊</span>
                    <span>Structure &amp; Feature Inventory Summary</span>
                  </h4>
                  <span className="text-[10px] font-mono text-emerald-400">
                    {candidate.structures.length} Total Structures Recorded
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 text-center text-xs font-mono">
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">🏡</span>
                    <span className="text-slate-400 text-[10px] block">Villages</span>
                    <span className="text-amber-400 font-bold">{candidate.structures.filter((s) => s.type === 'village').length}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">⚔️</span>
                    <span className="text-slate-400 text-[10px] block">Trial Chambers</span>
                    <span className="text-yellow-400 font-bold">{candidate.structures.filter((s) => s.type === 'trial_chamber').length}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">🏙️</span>
                    <span className="text-slate-400 text-[10px] block">Ancient Cities</span>
                    <span className="text-cyan-400 font-bold">{candidate.structures.filter((s) => s.type === 'ancient_city').length}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">🏯</span>
                    <span className="text-slate-400 text-[10px] block">Fortresses</span>
                    <span className="text-red-400 font-bold">{candidate.structures.filter((s) => s.type === 'fortress').length}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">🐖</span>
                    <span className="text-slate-400 text-[10px] block">Bastions</span>
                    <span className="text-orange-400 font-bold">{candidate.structures.filter((s) => s.type === 'bastion').length}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">🏛️</span>
                    <span className="text-slate-400 text-[10px] block">Monuments</span>
                    <span className="text-blue-400 font-bold">{candidate.structures.filter((s) => s.type === 'monument').length}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">⛵</span>
                    <span className="text-slate-400 text-[10px] block">Shipwrecks</span>
                    <span className="text-sky-400 font-bold">{candidate.structures.filter((s) => s.type === 'shipwreck').length}</span>
                  </div>
                </div>
              </div>

              {/* Predicted Stronghold Rings */}
              {candidate.predictedStrongholds && candidate.predictedStrongholds.length > 0 && (
                <div className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white flex items-center gap-1.5">
                      <span>🏰</span> Predicted Stronghold Rings ({candidate.predictedStrongholds.length})
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">Bedrock Stronghold Generation</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    {candidate.predictedStrongholds.map((coords, i) => (
                      <div
                        key={i}
                        className="p-2 bg-slate-900 rounded-lg border border-slate-800 flex items-center justify-between text-xs font-mono"
                      >
                        <span className="text-slate-400">Ring #{i + 1}</span>
                        <span className="text-emerald-400 font-bold">X: {coords[0]}, Z: {coords[1]}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="p-3.5 bg-slate-950 border border-blue-900/40 rounded-xl space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold text-blue-300">BDS Surface Point Observations</span>
                  <span className="text-[10px] text-slate-400">{candidate.surfaceVerification?.status ?? 'PENDING'}</span>
                </div>
                <p className="text-xs text-slate-400">
                  Samples explicit surface witness points with the pinned Bedrock server. Sparse observations do not verify structures, loot, portal rooms or initial player spawn.
                </p>
                {candidate.surfaceVerification && (
                  <div className="text-xs text-slate-300 space-y-1">
                    <p>{candidate.surfaceVerification.observedBiomes.length ? `Observed biomes: ${candidate.surfaceVerification.observedBiomes.join(', ')}` : 'No confirmed surface biome observations.'}</p>
                    {candidate.surfaceVerification.observationId && <p className="text-[10px] text-slate-500 break-all">Observation: {candidate.surfaceVerification.observationId}</p>}
                  </div>
                )}
                {onVerifyBDS && <button onClick={() => onVerifyBDS(candidate)} disabled={isVerifyingBDS}
                  className="w-full py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold disabled:opacity-50">
                  {isVerifyingBDS ? 'Sampling surface points…' : 'Sample Surface with BDS'}
                </button>}
              </div>
            </div>
          )}

          {/* TAB 2: FULL STRUCTURE INVENTORY */}
          {activeTab === 'structures' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-1.5 text-xs font-semibold">
                  <span className="text-slate-400">Filter Dimension:</span>
                  <button
                    onClick={() => setStructureDimFilter('all')}
                    className={`px-2.5 py-1 rounded transition-colors ${
                      structureDimFilter === 'all'
                        ? 'bg-slate-700 text-white font-bold'
                        : 'bg-slate-800/60 text-slate-400 hover:text-white'
                    }`}
                  >
                    All ({candidate.structures.length})
                  </button>
                  <button
                    onClick={() => setStructureDimFilter('overworld')}
                    className={`px-2.5 py-1 rounded transition-colors ${
                      structureDimFilter === 'overworld'
                        ? 'bg-emerald-600/30 text-emerald-300 font-bold border border-emerald-500/40'
                        : 'bg-slate-800/60 text-slate-400 hover:text-white'
                    }`}
                  >
                    Overworld ({overworldStructures.length})
                  </button>
                  <button
                    onClick={() => setStructureDimFilter('nether')}
                    className={`px-2.5 py-1 rounded transition-colors ${
                      structureDimFilter === 'nether'
                        ? 'bg-red-600/30 text-red-300 font-bold border border-red-500/40'
                        : 'bg-slate-800/60 text-slate-400 hover:text-white'
                    }`}
                  >
                    Nether ({netherStructures.length})
                  </button>
                </div>
                <span className="text-xs font-mono text-slate-400">
                  Showing {displayedStructures.length} of {candidate.structures.length} structures
                </span>
              </div>

              {/* Full Uncompressed Structures Table */}
              <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950/70">
                <div className="overflow-x-auto max-h-[460px]">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900/90 text-slate-400 font-semibold uppercase text-[10px] tracking-wider border-b border-slate-800 sticky top-0 z-10 backdrop-blur">
                      <tr>
                        <th className="py-2.5 px-3">Structure</th>
                        <th className="py-2.5 px-3">Dimension</th>
                        <th className="py-2.5 px-3 font-mono">X</th>
                        <th className="py-2.5 px-3 font-mono">Y</th>
                        <th className="py-2.5 px-3 font-mono">Z</th>
                        <th className="py-2.5 px-3 text-right">Dist to (0,0)</th>
                        {!isHubOrigin && (
                          <>
                            <th className="py-2.5 px-3 text-right">Dist to Hub</th>
                            <th className="py-2.5 px-3 text-right">Dist to Spawn</th>
                          </>
                        )}
                        <th className="py-2.5 px-3 text-center">Status</th>
                        <th className="py-2.5 px-3 text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {displayedStructures.map((s) => {
                        const isMarine = s.type === 'monument' || s.type === 'shipwreck';
                        const distOrigin = Math.round(s.distanceToOrigin ?? Math.hypot(s.x, s.z));
                        const distHub = s.distanceToHub != null ? Math.round(s.distanceToHub) : null;
                        const distSpawn = s.distanceToSpawn != null
                          ? Math.round(s.distanceToSpawn)
                          : spawn != null
                          ? Math.round(s.dimension === 'nether' ? Math.hypot(s.x - spawn[0] / 8, s.z - spawn[1] / 8) : Math.hypot(s.x - spawn[0], s.z - spawn[1]))
                          : null;
                        return (
                          <tr key={s.id} className="hover:bg-slate-800/40 transition-colors">
                            <td className="py-2 px-3 font-medium text-white flex items-center gap-2">
                              <span className="text-sm">{s.icon}</span>
                              <span>{s.name}</span>
                              {isMarine && (
                                <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                                  Marine
                                </span>
                              )}
                            </td>
                            <td className="py-2 px-3">
                              <span
                                className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                                  s.dimension === 'nether'
                                    ? 'bg-red-500/10 text-red-300 border border-red-500/30'
                                    : 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30'
                                }`}
                              >
                                {s.dimension === 'nether' ? 'Nether' : 'Overworld'}
                              </span>
                            </td>
                            <td className="py-2 px-3 font-mono text-emerald-400 font-bold">{s.x}</td>
                            <td className="py-2 px-3 font-mono text-slate-400">{s.y ?? '~'}</td>
                            <td className="py-2 px-3 font-mono text-emerald-400 font-bold">{s.z}</td>
                            <td className="py-2 px-3 font-mono text-right text-cyan-300 font-semibold">
                              {distOrigin}b
                            </td>
                            {!isHubOrigin && (
                              <>
                                <td className="py-2 px-3 font-mono text-right text-slate-300 font-semibold">
                                  {distHub != null ? `${distHub}b` : `${distOrigin}b`}
                                </td>
                                <td className="py-2 px-3 font-mono text-right text-emerald-300 font-semibold">
                                  {distSpawn != null ? `${distSpawn}b` : '—'}
                                </td>
                              </>
                            )}
                            <td className="py-2 px-3 text-center">
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                                {s.evidenceStatus ?? 'UNKNOWN'}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-center">
                              <button
                                onClick={() => copyText(`/tp @p ${s.x} ${s.y ?? '~'} ${s.z}`, `${s.name} /tp`)}
                                className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-mono transition-colors"
                                title="Copy teleport command"
                              >
                                /tp
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: BIOMES & WITNESSES */}
          {activeTab === 'biomes' && (
            <div className="space-y-4">
              {/* Biome Sampling Header */}
              <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1.5">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-1.5">
                    <span>🗺️</span>
                    <span>Bedrock World-Lattice Biome Evidence</span>
                  </h4>
                  <span className="text-[10px] font-mono text-cyan-400">
                    Overworld: Y=63, −48, 0, 160 • Nether: Y=64 • Spacing: 64 blocks
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Screened through native C11 OpenMP Bedrock generator sampling. Biome witnesses record exact coordinates where the predictor detected required families during screening.
                </p>
              </div>

              {candidate.netherBiomeWitnesses && <div className="p-3 bg-slate-950 rounded-xl border border-red-900/40 space-y-2">
                <h5 className="text-xs font-semibold text-red-300">Nether Biome Witnesses · Predicted</h5>
                {Object.entries(candidate.netherBiomeWitnesses).map(([name, witness]) =>
                  <p key={name} className="text-xs text-slate-300 font-mono">{name.replaceAll('_', ' ')} · {witness.coordinate.join(', ')}</p>)}
              </div>}

              {/* Biome Witness Coordinate Table */}
              {candidate.biomeWitnesses && Object.keys(candidate.biomeWitnesses).length > 0 && (
                <div className="space-y-2">
                  <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Predicted Biome Witness Coordinates
                  </h5>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                    {Object.entries(candidate.biomeWitnesses).map(([biomeName, coord]) => {
                      const coordArr = Array.isArray(coord) ? coord : coord?.coordinate;
                      if (!Array.isArray(coordArr) || coordArr.length < 2) return null;
                      return (
                        <div
                          key={biomeName}
                          className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between text-xs"
                        >
                          <div className="flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shrink-0" />
                            <span className="font-semibold text-white capitalize">
                              {biomeName.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <div className="flex items-center gap-1 font-mono text-[11px] text-emerald-400">
                            <span>X:{coordArr[0]}</span>
                            <span>Z:{coordArr.length >= 3 ? coordArr[2] : coordArr[1]}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Detected Biomes Catalog */}
              <div className="space-y-2">
                <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Predicted Biomes ({candidate.biomes?.length || 0})
                </h5>
                {candidate.biomes && candidate.biomes.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {candidate.biomes.map((biome, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-xs font-medium text-emerald-300 flex items-center gap-1.5 shadow-sm"
                      >
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        <span className="capitalize">{biome.replace(/_/g, ' ')}</span>
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl text-center text-xs text-slate-400">
                    Predicted biome grid sampled dynamically via <code className="text-emerald-400 font-mono">/api/candidate/biome-grid</code> on map canvas.
                  </div>
                )}
              </div>
            </div>
          )}

          <p className="text-xs text-slate-400 px-1">River and frozen river colors on the map are sampled biome predictions. Width, depth, navigability, and ocean connection are unverified.</p>

          {/* TAB 5: UNDERGROUND CAVES & RAVINES */}
          {activeTab === 'underground' && (
            <div className="space-y-4">
              {/* Ravines Section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-300 font-semibold uppercase tracking-wider">
                  <span className="flex items-center gap-1.5">
                    <span>🌋</span> Measured Ravine Chasms ({candidate.ravines?.length || 0})
                  </span>
                  <span className="text-[10px] font-mono text-amber-400">
                    {candidate.ravines?.filter((r) => r.giant).length || 0} Mega Ravines
                  </span>
                </div>
                {candidate.ravines && candidate.ravines.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {candidate.ravines.map((r) => (
                      <div
                        key={r.id}
                        className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-lg">🌋</span>
                          <div>
                            <span className="font-bold text-white block">
                              {r.giant ? 'Mega Ravine' : 'Standard Ravine'}
                            </span>
                            <span className="text-[10px] text-slate-400">
                              Length: {r.length}m • Width factor: {r.thick}
                              {r.underwater && ' • Trench (underwater)'}
                            </span>
                          </div>
                        </div>
                        <div className="text-right font-mono text-[11px]">
                          <span className="text-amber-400 font-bold block">X: {r.x}, Z: {r.z}</span>
                          <span className="text-slate-500">Y={r.y ?? '~'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl text-center text-xs text-slate-400">
                    No ravine fissures recorded for this candidate.
                  </div>
                )}
              </div>

              {/* Cave Clusters Section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-300 font-semibold uppercase tracking-wider">
                  <span className="flex items-center gap-1.5">
                    <span>🌿</span> Subterranean Cave Clusters ({candidate.caveClusters?.length || 0})
                  </span>
                  <span className="text-[10px] font-mono text-emerald-400">
                    Lush Caves • Deep Dark • Dripstone
                  </span>
                </div>
                {candidate.caveClusters && candidate.caveClusters.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    {candidate.caveClusters.map((c) => (
                      <div
                        key={c.id}
                        className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-base">{c.icon}</span>
                          <span className="font-semibold text-white">{c.name}</span>
                        </div>
                        <span className="font-mono text-[11px] text-emerald-400 font-bold">
                          Y={c.y ?? '~'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl text-center text-xs text-slate-400">
                    Cave cluster inventory requires manual cave sampling activation.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/90 flex items-center justify-between shrink-0 flex-wrap gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => copyText(candidate.seed, 'Seed')}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              <span>📋</span>
              <span>Copy Seed</span>
            </button>
            <button
              onClick={() => copyText(tpCommand, 'Teleport Command')}
              className="px-3 py-1.5 rounded-lg bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 border border-emerald-500/40 text-xs font-semibold flex items-center gap-1.5 transition-colors font-mono"
            >
              <span>🧭</span>
              <span>{tpCommand}</span>
            </button>
            {chunkbaseUrl && (
              <a
                href={chunkbaseUrl}
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1.5 rounded-lg bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <span>↗</span>
                <span>Open in Chunkbase</span>
              </a>
            )}
          </div>

          <button
            onClick={onClose}
            className="px-5 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold transition-colors shadow-md shadow-emerald-500/20"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
