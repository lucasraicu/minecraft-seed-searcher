import React, { useState, useMemo } from 'react';
import type { SearchConfig } from '../types';
import {
  V2_FLEXIBLE_FLOORS,
  ALL_STRUCTURES,
  CAVE_CLUSTERS,
  DEFAULT_STRUCTURE_FLOORS,
} from '../constants/structures';
import { computeTotalFeasibility } from '../utils/probability';

interface FilterSidebarProps {
  config: SearchConfig;
  onChangeConfig: (newConfig: SearchConfig) => void;
  logs: string[];
  onClearLogs?: () => void;
  onResumeSweep: (runId: string) => void;
  sweepRunning: boolean;
}

export const FilterSidebar: React.FC<FilterSidebarProps> = ({
  config,
  onChangeConfig,
  logs,
  onClearLogs,
  onResumeSweep,
  sweepRunning,
}) => {
  const [savedRuns, setSavedRuns] = useState<Array<{ runId: string; completedSeeds: number; targetCount: number; resumable: boolean }>>([]);
  const [resumeRunId, setResumeRunId] = useState('');
  const [runsError, setRunsError] = useState('');
  const refreshRuns = async () => {
    try {
      const response = await fetch('/api/sweep/runs');
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not load saved runs');
      const runs = data.runs.filter((run: { resumable: boolean }) => run.resumable);
      setSavedRuns(runs);
      setResumeRunId((current) => runs.some((run: { runId: string }) => run.runId === current) ? current : runs[0]?.runId || '');
      setRunsError('');
    } catch (error) { setRunsError(error instanceof Error ? error.message : String(error)); }
  };
  const [activeTab, setActiveTab] = useState<'targets' | 'engine' | 'logs'>('targets');
  const feasibility = useMemo(() => computeTotalFeasibility(config), [config]);

  const ALL_BIOMES = [
    { id: 'plains', name: 'Plains / Meadow', icon: '🌾' },
    { id: 'forest', name: 'Forest / Dark Forest', icon: '🌲' },
    { id: 'jungle', name: 'Jungle', icon: '🌴' },
    { id: 'desert', name: 'Desert / Badlands', icon: '🏜️' },
    { id: 'taiga', name: 'Taiga / Old Growth', icon: '🌲' },
    { id: 'snowy_ice', name: 'Snowy Plains / Spikes', icon: '❄️' },
    { id: 'swamp', name: 'Swamp / Mangrove', icon: '🐊' },
    { id: 'cherry_grove', name: 'Cherry Grove', icon: '🌸' },
    { id: 'mountains', name: 'Jagged / Stony Peaks', icon: '🏔️' },
    { id: 'mushroom_fields', name: 'Mushroom Fields', icon: '🍄' },
    { id: 'pale_garden', name: 'Pale Garden', icon: '🪵' },
    { id: 'deep_dark', name: 'Deep Dark', icon: '🌌' },
    { id: 'caves', name: 'Lush Caves', icon: '🌿' },
    { id: 'dripstone_caves', name: 'Dripstone Caves', icon: '🪨' },
    { id: 'ocean', name: 'Ocean / Deep Sea', icon: '🌊' },
  ];

  const hasOceanBiome = config.selectedBiomes.some(
    (b) => b === 'ocean' || b.includes('ocean')
  );
  const isBaselineInland = config.terrainMode === 'all_baseline' && !hasOceanBiome;

  const handleCountChange = (id: string, delta: number) => {
    if (isBaselineInland && (id === 'monument' || id === 'shipwreck')) return;
    const minVal = V2_FLEXIBLE_FLOORS[id];
    if (minVal === undefined) return;
    const current = config.structureFloorCounts[id] ?? DEFAULT_STRUCTURE_FLOORS[id] ?? minVal;
    const nextVal = Math.min(64, Math.max(minVal, current + delta));
    const nextFloorCounts = { ...config.structureFloorCounts, [id]: nextVal };


    // If currently not selected, add it
    const nextRequired = config.requiredStructures.includes(id)
      ? config.requiredStructures
      : [...config.requiredStructures, id];

    onChangeConfig({
      ...config,
      structureFloorCounts: nextFloorCounts,
      requiredStructures: nextRequired,
    });
  };

  const toggleStructure = (id: string) => {
    if (isBaselineInland && (id === 'monument' || id === 'shipwreck')) return;
    const isSelected = config.requiredStructures.includes(id);
    const nextRequired = isSelected
      ? config.requiredStructures.filter((s) => s !== id)
      : [...config.requiredStructures, id];

    onChangeConfig({ ...config, requiredStructures: nextRequired });
  };

  const toggleBiome = (id: string) => {
    const isAdding = !config.selectedBiomes.includes(id);
    const nextBiomes = isAdding
      ? [...config.selectedBiomes, id]
      : config.selectedBiomes.filter((b) => b !== id);

    let nextStructures = config.requiredStructures;
    if (config.terrainMode === 'all_baseline') {
      const hasOcean = nextBiomes.some((b) => b === 'ocean' || b.includes('ocean'));
      if (!hasOcean) {
        nextStructures = nextStructures.filter((s) => s !== 'monument' && s !== 'shipwreck');
      } else {
        nextStructures = Array.from(new Set([...nextStructures, 'monument', 'shipwreck']));
      }
    }

    onChangeConfig({ ...config, selectedBiomes: nextBiomes, requiredStructures: nextStructures });
  };

  const handleResetDefaults = () => {
    onChangeConfig({
      ...config,
      requiredStructures: Object.keys(DEFAULT_STRUCTURE_FLOORS),
      structureFloorCounts: { ...DEFAULT_STRUCTURE_FLOORS },
      mainlandTargetPct: 75,
      oceanEdgeWidthM: 320,
      riverHighwayLengthM: 400,
      enforceSpawnGate: true,
      maxSpawnDistance: 100,
    });
  };

  return (
    <aside className="w-80 h-full bg-slate-900 border-r border-slate-800 flex flex-col z-10 shadow-xl">
      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 bg-slate-950/50">
        <button
          onClick={() => setActiveTab('targets')}
          className={`flex-1 py-3 text-xs font-semibold tracking-wider uppercase transition-all ${
            activeTab === 'targets'
              ? 'text-emerald-400 border-b-2 border-emerald-400 bg-slate-900/60'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Blueprint Targets
        </button>
        <button
          onClick={() => setActiveTab('engine')}
          className={`flex-1 py-3 text-xs font-semibold tracking-wider uppercase transition-all ${
            activeTab === 'engine'
              ? 'text-emerald-400 border-b-2 border-emerald-400 bg-slate-900/60'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Xeon Hardware
        </button>
        <button
          onClick={() => setActiveTab('logs')}
          className={`flex-1 py-3 text-xs font-semibold tracking-wider uppercase transition-all ${
            activeTab === 'logs'
              ? 'text-emerald-400 border-b-2 border-emerald-400 bg-slate-900/60'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Console
        </button>
      </div>

      {/* Tab 1: Search Targets */}
      {activeTab === 'targets' && (
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {/* Master Blueprint Banner & Reset */}
          <div className="p-3 bg-slate-950/80 border border-emerald-500/30 rounded-lg flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span className="text-xs font-bold text-white">Corrected v2 Policy</span>
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">
                Fixed structure floors and required biome families
              </p>
            </div>
            <button
              onClick={handleResetDefaults}
              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-[10px] font-semibold border border-slate-700 transition-colors"
              title="Reset all structure counts and gates to Blueprint defaults"
            >
              Reset
            </button>
          </div>

          <div className="p-2.5 rounded-lg border border-amber-500/30 bg-amber-950/20 text-[10px] leading-relaxed text-amber-100">
            Live sweeps use the fixed v2 categories. The eight flexible structure ideals, B, count, starting index, threads and batch size apply to live sweeps. Required categories and biome rules remain fixed. Optional planning controls never change live qualification.
          </div>

          {/* Box 4: Total Search Odds Hero Card (End-to-End Pipeline) */}
          <div className="p-3 bg-gradient-to-b from-slate-900 to-slate-950 border border-emerald-500/40 rounded-xl space-y-2.5 shadow-xl relative overflow-hidden">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="text-sm">🎯</span>
                <span className="text-[11px] font-bold uppercase tracking-wider text-white">
                  Planning Model (Heuristic)
                </span>
              </div>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                  feasibility.feasibilityRating === 'Astronomical'
                    ? 'bg-red-500/20 text-red-400 border-red-500/40'
                    : feasibility.feasibilityRating === 'Extreme'
                    ? 'bg-orange-500/20 text-orange-400 border-orange-500/40'
                    : feasibility.feasibilityRating === 'Rare'
                    ? 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                    : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                }`}
              >
                {feasibility.feasibilityRating}
              </span>
            </div>

            {/* Main Joint Probability Banner */}
            <div className="bg-slate-950/90 rounded-lg p-2.5 border border-slate-800 shadow-inner">
              <div className="flex justify-between items-center text-[10px] text-slate-400 mb-0.5">
                <span>Uncalibrated model odds:</span>
                <span className="font-mono text-emerald-400 font-bold">~{feasibility.expectedSeedsNeeded.toLocaleString()} inputs at 1/P</span>
              </div>
              <div className={`font-mono text-base font-extrabold ${feasibility.color} tracking-tight`}>
                {feasibility.formattedOdds}
              </div>
            </div>

            {/* 3-Stage Multiplier Breakdown */}
            <div className="grid grid-cols-3 gap-1.5 text-[10px] font-mono">
              <div className="p-1.5 bg-slate-900/90 rounded border border-slate-800 text-center">
                <span className="text-slate-500 block text-[9px]">🏰 Struct</span>
                <span className="text-white font-bold">
                  {(feasibility.structures.probability * 100).toFixed(feasibility.structures.probability < 0.01 ? 3 : 1)}%
                </span>
              </div>
              <div className="p-1.5 bg-slate-900/90 rounded border border-slate-800 text-center">
                <span className="text-slate-500 block text-[9px]">🌿 Biomes</span>
                <span className="text-cyan-400 font-bold">
                  {(feasibility.biomes.probability * 100).toFixed(1)}%
                </span>
              </div>
              <div className="p-1.5 bg-slate-900/90 rounded border border-slate-800 text-center">
                <span className="text-slate-500 block text-[9px]">🌊 Terrain</span>
                <span className="text-blue-400 font-bold">
                  {(feasibility.terrain.probability * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* 1-Click Sync Button */}
            <button
              onClick={() => {
                const targetVol = Math.min(
                  100_000_000_000,
                  Math.max(1, isFinite(feasibility.expectedSeedsNeeded) ? Math.round(feasibility.expectedSeedsNeeded) : 100_000_000)
                );
                onChangeConfig({ ...config, sweepSeedCount: targetVol });
              }}
              className="w-full py-1.5 px-2 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 rounded-lg text-[10px] font-semibold flex items-center justify-center gap-1.5 transition-all shadow-sm"
              title="Set the input volume to calculated 1/P probability scale (automatically partitioned into 16,384-seed batches by native engine)"
            >
              <span>⚡</span>
              <span>Sync Sweep Volume ({feasibility.expectedSeedsNeeded >= 1000000000 ? `${(feasibility.expectedSeedsNeeded / 1000000000).toFixed(2)}B` : feasibility.expectedSeedsNeeded >= 1000000 ? `${(feasibility.expectedSeedsNeeded / 1000000).toFixed(1)}M` : `${feasibility.expectedSeedsNeeded.toLocaleString()}`} seeds)</span>
            </button>
          </div>


          {/* Box 1: Structure Odds Box (Stage 1 Screening) */}
          <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="text-xs">🏰</span>
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
                  Modeled Structure Marginals
                </span>
              </div>
              <span className="font-mono text-[10px] font-bold text-emerald-400">
                {feasibility.structures.formattedOdds}
              </span>
            </div>

            {feasibility.structures.bottleneck && (
              <div className="flex items-center justify-between text-[10px] px-2 py-1 bg-slate-900/80 rounded border border-slate-800 text-slate-400">
                <span className="truncate">
                  Rarest: <strong className="text-slate-200">{feasibility.structures.bottleneck.name} ({feasibility.structures.bottleneck.count > 0 ? `≥${feasibility.structures.bottleneck.count}` : 'Any'})</strong>
                </span>
                <span className="font-mono text-amber-400 font-bold ml-1">
                  {(feasibility.structures.bottleneck.prob * 100).toFixed(feasibility.structures.bottleneck.prob < 0.05 ? 2 : 1)}%
                </span>
              </div>
            )}

            <div className="flex items-center justify-between text-[9px] text-slate-500">
              <span>Tolerance: {config.maxMisses} miss allowed</span>
              <span className="font-mono text-cyan-400 font-semibold">
                {feasibility.structures.toleranceBoost > 1 ? `${feasibility.structures.toleranceBoost.toFixed(1)}× boost` : 'strict'}
              </span>
            </div>
          </div>

          {/* Structure Counts with Steppers */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Structure Floors ({ALL_STRUCTURES.length})
              </label>
              <span className="text-[10px] text-emerald-400 font-mono font-bold">
                {ALL_STRUCTURES.filter((s) => config.requiredStructures.includes(s.id) && (!isBaselineInland || (s.id !== 'monument' && s.id !== 'shipwreck'))).length} active
              </span>
            </div>

            {/* Marine Evaluation Timing Notice */}
            <div className="mb-2 p-2 rounded-lg bg-blue-950/30 border border-blue-500/30 text-[10px] text-blue-200 leading-relaxed flex items-start gap-1.5">
              <span className="text-blue-400 text-xs mt-0.5">⛵</span>
              <div>
                <span className="font-bold text-white">Marine Evaluation Timing: </span>
                <span>
                  <strong>Ocean Monuments &amp; Shipwrecks</strong> are <strong>deferred from Stage 1 Baseline screening</strong>. They are strictly evaluated in <strong>Stage 3 Terrain Pass-Through</strong> once coastal ocean is confirmed. Qualifying seeds retain Baseline Survivor status regardless of marine presence.
                </span>
              </div>
            </div>

            <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
              {ALL_STRUCTURES.map((s) => {
                const isMarine = s.id === 'monument' || s.id === 'shipwreck';
                const isExempt = isBaselineInland && isMarine;
                const isSelected = !isExempt && config.requiredStructures.includes(s.id);
                const count = config.structureFloorCounts[s.id] ?? DEFAULT_STRUCTURE_FLOORS[s.id] ?? 1;
                const indP = feasibility.structures.individualProbs[s.id];

                if (isExempt) {
                  return (
                    <div
                      key={s.id}
                      className="flex items-center justify-between px-2.5 py-1.5 rounded-lg border bg-slate-950/40 border-slate-800/60 text-slate-500 opacity-60"
                      title="Exempt in inland baseline mode (no ocean biome selected)"
                    >
                      <div className="flex items-center gap-1.5 truncate">
                        <span className="text-sm">{s.icon}</span>
                        <span className="text-xs font-semibold truncate line-through opacity-70">{s.name}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 font-bold">
                          Exempt (No Ocean)
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono italic pr-1">
                          N/A
                        </span>
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={s.id}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg border transition-all ${
                      isSelected
                        ? 'bg-slate-800/80 border-slate-700 text-slate-200 shadow-sm'
                        : 'bg-slate-950/40 border-slate-800/60 text-slate-500 opacity-60'
                    }`}
                  >
                    {/* Toggle check & Structure Label */}
                    <button
                      onClick={() => toggleStructure(s.id)}
                      title="Planning selection only; live sweep floors remain required"
                      className="flex items-center justify-between gap-1 text-left truncate flex-1 hover:text-white transition-colors"
                    >
                      <div className="flex items-center gap-1.5 truncate">
                        <span className="text-sm">{s.icon}</span>
                        <span className="text-xs font-semibold truncate">{s.name}</span>
                        {isMarine && (
                          <span
                            className="text-[9px] font-mono px-1 py-0.2 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30"
                            title="Deferred from Stage 1 Baseline; evaluated in Stage 3 Terrain Pass once coastal ocean is confirmed"
                          >
                            Stage 3
                          </span>
                        )}
                      </div>
                      {isSelected && indP !== undefined && (
                        <span
                          className={`text-[9px] font-mono px-1 rounded mr-1 ${
                            indP < 0.2
                              ? 'text-amber-400 bg-amber-500/10 font-bold'
                              : 'text-slate-400'
                          }`}
                          title={`Uncalibrated modeled marginal: ${(indP * 100).toFixed(1)}%`}
                        >
                          {(indP * 100).toFixed(0)}%
                        </span>
                      )}
                    </button>

                    {/* Stepper Count Controls */}
                    <div className="flex items-center gap-1.5 ml-2">
                      <button
                        onClick={() => handleCountChange(s.id, -1)}
                        disabled={!(s.id in V2_FLEXIBLE_FLOORS) || count <= (V2_FLEXIBLE_FLOORS[s.id] ?? s.min)}
                        title={s.id in V2_FLEXIBLE_FLOORS ? `Cannot go below v2 fatal floor ${V2_FLEXIBLE_FLOORS[s.id]}` : 'This target is fixed by v2'}
                        className="w-5 h-5 rounded bg-slate-700 hover:bg-slate-600 disabled:opacity-30 disabled:hover:bg-slate-700 text-white text-xs font-bold flex items-center justify-center transition-all"
                      >
                        -
                      </button>
                      <span className="font-mono text-xs font-bold text-emerald-400 w-5 text-center">
                        {count}
                      </span>
                      <button
                        onClick={() => handleCountChange(s.id, 1)}
                        disabled={count >= 64 || !(s.id in V2_FLEXIBLE_FLOORS)}
                        title={count >= 64 ? 'Maximum goal reached (64)' : s.id in V2_FLEXIBLE_FLOORS ? 'Adjust live ideal count' : 'This target is fixed by v2'}
                        className="w-5 h-5 rounded bg-slate-700 hover:bg-slate-600 disabled:opacity-30 disabled:hover:bg-slate-700 text-white text-xs font-bold flex items-center justify-center transition-all"
                      >
                        +
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <section aria-label="Planning estimates only" className="space-y-4">
          <p className="text-xs text-amber-200">Planning only: the following controls do not change live sweep filtering.</p>
          {/* Nether Requirements */}
          <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300">🔥 Nether Fort &amp; Bastion Pairing</span>
              <span className="text-[10px] text-red-400 font-mono">1024 × 1024</span>
            </div>

            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={config.mandatoryFortressAndBastion}
                onChange={(e) =>
                  onChangeConfig({ ...config, mandatoryFortressAndBastion: e.target.checked })
                }
                className="rounded accent-emerald-500"
              />
              <span>Require Both Fortress AND Bastion</span>
            </label>

            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={config.requireNetherOverlap}
                onChange={(e) =>
                  onChangeConfig({ ...config, requireNetherOverlap: e.target.checked })
                }
                className="rounded accent-emerald-500"
              />
              <span>Physical Overlap / Touching Only</span>
            </label>
          </div>

          {/* Dedicated Underground Cave Clusters Card */}
          <div className="p-3 bg-slate-950/80 border border-emerald-500/30 rounded-xl space-y-2 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="text-sm">💎</span>
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-200">
                  Underground Cave Clusters ({CAVE_CLUSTERS.length})
                </span>
              </div>
              <span className="text-[10px] text-emerald-400 font-mono font-bold">
                {CAVE_CLUSTERS.filter((c) => config.requiredStructures.includes(c.id)).length} active
              </span>
            </div>

            <p className="text-[10px] text-slate-400 leading-tight">
              Subterranean biomes (Y ≤ 0). Active (green) with unconstrained count (Any) by default; step + to require minimum cluster count.
            </p>

            <div className="space-y-1.5 pt-1">
              {CAVE_CLUSTERS.map((c) => {
                const isSelected = config.requiredStructures.includes(c.id);
                const count = config.structureFloorCounts[c.id] ?? DEFAULT_STRUCTURE_FLOORS[c.id] ?? 0;
                const indP = feasibility.structures.individualProbs[c.id];

                return (
                  <div
                    key={c.id}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg border transition-all ${
                      isSelected
                        ? 'bg-emerald-950/25 border-emerald-500/50 text-slate-100 shadow-sm'
                        : 'bg-slate-950/40 border-slate-800/60 text-slate-500 opacity-60'
                    }`}
                  >
                    {/* Toggle check & Cave Label */}
                    <button
                      type="button"
                      onClick={() => toggleStructure(c.id)}
                      className="flex items-center justify-between gap-1 text-left truncate flex-1 hover:text-white transition-colors"
                    >
                      <div className="flex items-center gap-1.5 truncate">
                        <span className="text-sm">{c.icon}</span>
                        <span className="text-xs font-semibold truncate">{c.name}</span>
                      </div>
                      {isSelected && indP !== undefined && (
                        <span
                          className={`text-[9px] font-mono px-1.5 py-0.5 rounded mr-1 font-bold ${
                            indP < 0.3
                              ? 'text-red-400 bg-red-500/10 border border-red-500/30'
                              : indP < 0.7
                              ? 'text-amber-400 bg-amber-500/10 border border-amber-500/30'
                              : 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/30'
                          }`}
                          title={`Uncalibrated modeled marginal: ${(indP * 100).toFixed(1)}%`}
                        >
                          {(indP * 100).toFixed(0)}%
                        </span>
                      )}
                    </button>

                    {/* Stepper Count Controls */}
                    <div className="flex items-center gap-1.5 ml-2">
                      <button
                        type="button"
                        onClick={() => handleCountChange(c.id, -1)}
                        disabled={count <= 0 || !isSelected}
                        className="w-5 h-5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-20 disabled:hover:bg-slate-800 text-white text-xs font-bold flex items-center justify-center border border-slate-700 transition-all"
                        title="Decrease cluster requirement"
                      >
                        -
                      </button>
                      <span
                        className={`font-mono text-xs font-bold w-7 text-center ${
                          count === 0 ? 'text-emerald-400/90 italic text-[11px]' : 'text-emerald-300'
                        }`}
                        title={count === 0 ? 'Any (presence in 2048x2048)' : `≥${count} clusters`}
                      >
                        {count === 0 ? 'Any' : count}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleCountChange(c.id, 1)}
                        disabled={count >= 64 || !isSelected}
                        className="w-5 h-5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-20 disabled:hover:bg-slate-800 text-white text-xs font-bold flex items-center justify-center border border-slate-700 transition-all"
                        title={count >= 64 ? 'Maximum goal reached (64)' : 'Increase cluster requirement'}
                      >
                        +
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Box 2: Biome Diversity Odds Box (Stage 2 Lattice) */}
          <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="text-xs">🌿</span>
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
                  Modeled Biome Marginals (not sent live)
                </span>
              </div>
              <span className="font-mono text-[10px] font-bold text-cyan-400">
                {feasibility.biomes.formattedOdds}
              </span>
            </div>

            {feasibility.biomes.bottleneck && (
              <div className="flex items-center justify-between text-[10px] px-2 py-1 bg-slate-900/80 rounded border border-slate-800 text-slate-400">
                <span className="truncate">
                  Rarest Active: <strong className="text-slate-200">{feasibility.biomes.bottleneck.name}</strong>
                </span>
                <span className="font-mono text-amber-400 font-bold ml-1">
                  {(feasibility.biomes.bottleneck.prob * 100).toFixed(1)}%
                </span>
              </div>
            )}

            <div className="flex items-center justify-between text-[9px] text-slate-500">
              <span>Selected: {feasibility.biomes.selectedCount} / {feasibility.biomes.totalCount}</span>
              <span className="text-slate-400">4-Y Lattice (Y: 63, -48, 0, 160)</span>
            </div>
          </div>

          {/* Biome Families */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Biome Planning Toggles ({ALL_BIOMES.length})
              </label>
              <span className="text-[10px] text-emerald-400 font-mono">
                {config.selectedBiomes.length} / {ALL_BIOMES.length}
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {ALL_BIOMES.map((b) => {
                const isSelected = config.selectedBiomes.includes(b.id);
                const prob = feasibility.biomes.individualProbs[b.id];
                return (
                  <button
                    key={b.id}
                    onClick={() => toggleBiome(b.id)}
                    className={`py-1 px-2 rounded-full text-[11px] font-medium flex items-center gap-1 transition-all border ${
                      isSelected
                        ? 'bg-emerald-600/30 border-emerald-500/50 text-emerald-300'
                        : 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <span>{b.icon}</span>
                    <span>{b.name}</span>
                    {prob !== undefined && (
                      <span className="text-[9px] font-mono opacity-60 ml-0.5">
                        {(prob * 100).toFixed(0)}%
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Terrain Screening Mode Segmented Control */}
          <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="text-sm">🧭</span>
              <span className="text-xs font-bold text-white uppercase tracking-wider">Terrain Planning Mode</span>
              </div>
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                  config.terrainMode === 'all_baseline'
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                }`}
              >
                {config.terrainMode === 'all_baseline' ? 'BASELINE (STRUCTURES)' : 'COASTAL CONTINENT'}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-1.5 p-1 bg-slate-900 rounded-lg border border-slate-800">
              <button
                type="button"
                onClick={() => {
                  const hasOcean = config.selectedBiomes.some((b) => b === 'ocean' || b.includes('ocean'));
                  const nextReq = hasOcean
                    ? config.requiredStructures
                    : config.requiredStructures.filter((s) => s !== 'monument' && s !== 'shipwreck');
                  onChangeConfig({ ...config, terrainMode: 'all_baseline', requiredStructures: nextReq });
                }}
                className={`py-2 px-2 rounded text-[11px] font-semibold flex flex-col items-center gap-0.5 transition-all ${
                  config.terrainMode === 'all_baseline'
                    ? 'bg-amber-600 text-white shadow-md shadow-amber-600/30 font-bold'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <span className="flex items-center gap-1 font-bold">🏰 Baseline Only</span>
                <span className="text-[9px] opacity-80 font-normal">Inland structures (marine exempt)</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  const nextReq = Array.from(new Set([...config.requiredStructures, 'monument', 'shipwreck']));
                  onChangeConfig({ ...config, terrainMode: 'coastal_continent', requiredStructures: nextReq });
                }}
                className={`py-2 px-2 rounded text-[11px] font-semibold flex flex-col items-center gap-0.5 transition-all ${
                  config.terrainMode === 'coastal_continent'
                    ? 'bg-cyan-600 text-white shadow-md shadow-cyan-600/30 font-bold'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <span className="flex items-center gap-1 font-bold">🌊 Coastal Continent</span>
                <span className="text-[9px] opacity-80 font-normal">70–80% Mainland + Sea</span>
              </button>
            </div>

            <p className="text-[10px] text-slate-400 leading-relaxed">
              {config.terrainMode === 'all_baseline'
                ? '★ Baseline Mode retains all seeds passing core structure & biome floors (marine structures auto-exempted if no ocean biome is selected).'
                : '★ Coastal Continent Mode strictly verifies 70%–80% continuous mainland, 320m ocean edge corridor, coastal monuments/shipwrecks, and river highway.'}
            </p>
          </div>

          {/* Box 3: 3D Terrain & Spawn Odds Box (Stage 3 Verification) */}
          <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="text-xs">🌊</span>
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
                  Modeled Terrain / Spawn Estimates
                </span>
              </div>
              <span className="font-mono text-[10px] font-bold text-blue-400">
                {feasibility.terrain.formattedOdds}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-1 text-[9px] font-mono text-slate-400">
              <div className="px-1.5 py-1 bg-slate-900 rounded border border-slate-800/80 flex justify-between">
                <span>Landmass {config.mainlandTargetPct}%:</span>
                <span className={config.terrainMode === 'all_baseline' ? 'text-amber-400 font-semibold' : 'text-white font-semibold'}>
                  {config.terrainMode === 'all_baseline' ? 'Bypassed' : `${(feasibility.terrain.landmassProb * 100).toFixed(1)}%`}
                </span>
              </div>
              <div className="px-1.5 py-1 bg-slate-900 rounded border border-slate-800/80 flex justify-between">
                <span>River Highway:</span>
                <span className={config.terrainMode === 'all_baseline' ? 'text-amber-400 font-semibold' : 'text-cyan-400 font-semibold'}>
                  {config.terrainMode === 'all_baseline' ? 'Bypassed' : '42.5%'}
                </span>
              </div>
              <div className="px-1.5 py-1 bg-slate-900 rounded border border-slate-800/80 flex justify-between">
                <span>Ocean Edge 320m:</span>
                <span className={config.terrainMode === 'all_baseline' ? 'text-amber-400 font-semibold' : 'text-blue-400 font-semibold'}>
                  {config.terrainMode === 'all_baseline' ? 'Bypassed' : '64.0%'}
                </span>
              </div>
              <div className="px-1.5 py-1 bg-slate-900 rounded border border-slate-800/80 flex justify-between">
                <span>Spawn ≤{config.maxSpawnDistance}m:</span>
                <span className="text-emerald-400 font-semibold">{(feasibility.terrain.spawnGateProb * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>

          {/* 3D Terrain Spec: Dedicated Coastal Continent */}
          <div
            className={`p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-3 transition-opacity ${
              config.terrainMode === 'all_baseline' ? 'opacity-60' : 'opacity-100'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="text-sm">🌊</span>
                <span className="text-xs font-bold text-white">Coastal Continent Specification</span>
              </div>
              <span
                className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                  config.terrainMode === 'all_baseline'
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    : 'bg-emerald-500/20 text-emerald-400'
                }`}
              >
                {config.terrainMode === 'all_baseline' ? 'BYPASSED' : 'ACTIVE'}
              </span>
            </div>

            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span>Target Mainland Landmass:</span>
                <span className="font-mono text-emerald-400 font-bold">{config.mainlandTargetPct}%</span>
              </div>
              <input
                type="range"
                min="65"
                max="85"
                disabled={config.terrainMode === 'all_baseline'}
                value={config.mainlandTargetPct}
                onChange={(e) =>
                  onChangeConfig({ ...config, mainlandTargetPct: Number(e.target.value) })
                }
                className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500 disabled:opacity-40"
              />
              <span className="text-[10px] text-slate-500">Master blueprint target: 70% – 80%</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-300 pt-1 border-t border-slate-800/80">
              <div className="p-1.5 bg-slate-900 rounded border border-slate-800">
                <span className="text-slate-500 block">River Highway:</span>
                <span className="font-mono text-cyan-400 font-semibold">
                  {config.terrainMode === 'all_baseline' ? 'Optional' : '≥400m Navigable'}
                </span>
              </div>
              <div className="p-1.5 bg-slate-900 rounded border border-slate-800">
                <span className="text-slate-500 block">Ocean Edge Corridor:</span>
                <span className="font-mono text-blue-400 font-semibold">
                  {config.terrainMode === 'all_baseline' ? 'Optional' : '320m Deep Sea'}
                </span>
              </div>
            </div>
          </div>

          {/* Downstream Stage 3 Spawn Gate */}
          <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-xs text-slate-300 font-bold cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.enforceSpawnGate}
                  onChange={(e) =>
                    onChangeConfig({ ...config, enforceSpawnGate: e.target.checked })
                  }
                  className="rounded accent-emerald-500"
                />
                  <span>Spawn model toggle (planning only)</span>
              </label>
              <span className="text-[10px] font-mono text-emerald-400 font-bold">
                ≤{config.maxSpawnDistance}m
              </span>
            </div>
            {config.enforceSpawnGate && (
              <div>
                <input
                  type="range"
                  min="25"
                  max="200"
                  step="25"
                  value={config.maxSpawnDistance}
                  onChange={(e) =>
                    onChangeConfig({ ...config, maxSpawnDistance: Number(e.target.value) })
                  }
                  className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                />
              </div>
            )}
            <p className="text-[10px] text-slate-400 leading-tight">
              Planning heuristic only. Spawn evidence is downstream and remains pending until the backend supplies it; this control is not part of the live v2 sweep request.
            </p>
          </div>
          </section>
        </div>
      )}

      {/* Tab 2: Hardware & Engine Tuning */}
      {activeTab === 'engine' && (
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {/* Host CPU Banner */}
          <div className="p-3 bg-slate-950 border border-emerald-500/30 rounded-lg space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                <span>⚡</span> Intel(R) Xeon(R) W-2191B
              </span>
              <span className="text-[10px] font-mono text-slate-400">18C / 36T</span>
            </div>
            <p className="text-[10px] text-slate-400">
              Run controls for the corrected v2 native policy. Throughput is reported only from live run telemetry.
            </p>
          </div>

          {/* Sweep Seed Volume - Interactive Fill-In Input */}
          <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-300">
                Sweep Seed Volume
              </label>
              <span className="text-[10px] text-emerald-400 font-mono font-bold">
                {config.sweepSeedCount.toLocaleString()} seeds
              </span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max={Number.MAX_SAFE_INTEGER}
                step="5000"
                value={config.sweepSeedCount || ''}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  onChangeConfig({ ...config, sweepSeedCount: isNaN(val) ? 0 : Math.min(Number.MAX_SAFE_INTEGER, Math.max(1, val)) });
                }}
                className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm font-mono font-bold text-emerald-400 outline-none focus:border-emerald-500 shadow-inner"
                placeholder="Enter seed count, e.g. 100000"
              />
              <span className="text-xs font-mono text-slate-400">seeds</span>
            </div>

            {/* Quick 1-click convenience chips */}
            <div className="flex flex-wrap items-center gap-1 pt-1">
              {[100000, 1000000, 10000000, 100000000, 1000000000].map((v) => (
                <button
                  key={v}
                  onClick={() => onChangeConfig({ ...config, sweepSeedCount: v })}
                  className={`px-2 py-0.5 rounded text-[10px] font-mono transition-colors border ${
                    config.sweepSeedCount === v
                      ? 'bg-emerald-600/30 border-emerald-500/60 text-emerald-300 font-bold'
                      : 'bg-slate-800/40 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {v >= 1000000000 ? `${v / 1000000000}B` : v >= 1000000 ? `${v / 1000000}M` : `${v / 1000}k`}
                </button>
              ))}
              <button
                onClick={() => {
                  const targetVol = Math.min(
                    100_000_000_000,
                    Math.max(1, isFinite(feasibility.expectedSeedsNeeded) ? Math.round(feasibility.expectedSeedsNeeded) : 100_000_000)
                  );
                  onChangeConfig({
                    ...config,
                    sweepSeedCount: targetVol,
                  });
                }}
                className="px-2 py-0.5 rounded text-[10px] font-mono transition-colors border bg-cyan-600/20 border-cyan-500/40 text-cyan-300 hover:bg-cyan-600/30"
                title="Set input volume near the uncalibrated heuristic 1/P scale, subject to disk and range limits"
              >
                1/P ({feasibility.expectedSeedsNeeded >= 1000000000 ? `${(feasibility.expectedSeedsNeeded / 1000000000).toFixed(1)}B` : feasibility.expectedSeedsNeeded >= 1000000 ? `${(feasibility.expectedSeedsNeeded / 1000000).toFixed(1)}M` : `${Math.round(feasibility.expectedSeedsNeeded / 1000)}k`})
              </button>
            </div>
            <p className="text-[10px] text-slate-400">
              Uncalibrated planning heuristic: about <strong className="text-emerald-400">{feasibility.expectedSeedsNeeded.toLocaleString()} inputs at 1/P</strong>. It assumes independent stages and is not a calibrated joint pass rate or ETA.
            </p>
          </div>

          <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
            <label htmlFor="start-index" className="text-xs font-semibold text-slate-300">Starting seed index</label>
            <input id="start-index" type="text" inputMode="numeric" value={config.startIndex}
              onChange={(event) => { if (/^\d*$/.test(event.target.value)) onChangeConfig({ ...config, startIndex: event.target.value }); }}
              className="w-full bg-slate-800 rounded px-3 py-2 text-sm font-mono" />
            <p className="text-[10px] text-slate-400">Exact full64 sequence index. Memory and disk budgets still apply to larger runs.</p>
          </div>
          <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
            <div className="flex justify-between"><span className="text-xs font-semibold">Resume saved sweep</span>
              <button onClick={refreshRuns} className="text-xs text-cyan-300">Refresh runs</button></div>
            <select aria-label="Saved sweep" value={resumeRunId} onChange={(event) => setResumeRunId(event.target.value)}
              className="w-full bg-slate-800 rounded px-2 py-2 text-xs">
              <option value="">Select a saved incomplete run</option>
              {savedRuns.map((run) => <option key={run.runId} value={run.runId}>{run.runId} — {run.completedSeeds.toLocaleString()}/{run.targetCount.toLocaleString()}</option>)}
            </select>
            <button disabled={!resumeRunId || sweepRunning} onClick={() => onResumeSweep(resumeRunId)}
              className="w-full bg-emerald-700 disabled:opacity-40 rounded py-2 text-xs">Resume with saved settings</button>
            <p className="text-[10px] text-slate-400">Uses the saved range, policy and native build; current controls do not override the run.</p>
            {runsError && <p role="alert" className="text-xs text-red-300">{runsError}</p>}
          </div>
          {/* Near-Miss Retention Policy */}
          <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300">Deficit Budget B</span>
              <span className="text-[10px] font-mono text-cyan-400 font-bold">
                B = {config.maxMisses}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-1">
              {[
                { val: 0, label: 'B = 0', desc: 'No deficit categories' },
                { val: 1, label: 'B = 1', desc: 'One category below ideal' },
                { val: 2, label: 'B = 2', desc: 'Two categories below ideal' },
              ].map((m) => (
                <button
                  key={m.val}
                  onClick={() => onChangeConfig({ ...config, maxMisses: m.val })}
                  className={`py-1.5 px-1 rounded text-center border transition-all ${
                    config.maxMisses === m.val
                      ? 'bg-emerald-600/30 border-emerald-500/60 text-emerald-300 font-bold'
                      : 'bg-slate-800/40 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <div className="text-[11px] font-semibold">{m.label}</div>
                  <div className="text-[9px] text-slate-500">{m.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Concurrency Sliders */}
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-300 font-medium">OpenMP Native Threads:</span>
                <span className="font-mono text-emerald-400 font-bold">{config.openmpThreads} Threads</span>
              </div>
              <input
                type="range"
                min="1"
                max="34"
                value={config.openmpThreads}
                onChange={(e) => onChangeConfig({ ...config, openmpThreads: Number(e.target.value) })}
                className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
              />
              <span className="text-[10px] text-slate-500">34 native threads reserve two host slots for preparation and writing.</span>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-300 font-medium">Native Batch Chunk Size:</span>
                <span className="font-mono text-emerald-400 font-bold">{config.batchSize.toLocaleString()}</span>
              </div>
              <input
                type="range"
                min="4096"
                max="16384"
                step="4096"
                value={config.batchSize}
                onChange={(e) => onChangeConfig({ ...config, batchSize: Number(e.target.value) })}
                className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
              />
              <span className="text-[10px] text-slate-500">Native batch size sent to the live sweep API.</span>
            </div>
          </div>

          <hr className="border-slate-800" />

          {/* Built-in Engine Architecture Info */}
          <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-1.5 text-[11px] text-slate-300">
            <span className="font-bold text-white block uppercase tracking-wider text-[10px]">
              Active Engine Capabilities
            </span>
            <div className="flex items-center gap-2 text-slate-400">
              <span className="text-emerald-400">✓</span>
              <span>Native OpenMP sweep with corrected v2 policy identity</span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <span className="text-emerald-400">✓</span>
              <span>Fixed fatal floors and two-group deficit classification</span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <span className="text-emerald-400">✓</span>
              <span>Biome families remain required by the v2 policy</span>
            </div>
            <div className="flex items-center gap-2 text-slate-400">
              <span className="text-emerald-400">✓</span>
              <span>Downstream evidence stays pending unless supplied by backend</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Live Terminal Logs */}
      {activeTab === 'logs' && (
        <div className="flex-1 bg-slate-950 p-3 font-mono text-[11px] overflow-y-auto space-y-1 text-slate-300 select-text flex flex-col justify-between">
          <div className="space-y-1">
            {logs.map((log, index) => (
              <div key={index} className="leading-tight">
                <span className="text-slate-500">[LOG {logs.length - index}]</span>{' '}
                <span
                  className={
                    log.includes('complete') || log.includes('Certified') || log.includes('passed')
                      ? 'text-emerald-400 font-semibold'
                      : log.includes('Spawning') || log.includes('Started')
                      ? 'text-cyan-400 font-semibold'
                      : log.includes('BDS')
                      ? 'text-blue-400'
                      : log.includes('error') || log.includes('Error')
                      ? 'text-red-400'
                      : 'text-slate-300'
                  }
                >
                  {log}
                </span>
              </div>
            ))}
          </div>

          {onClearLogs && (
            <div className="pt-2 border-t border-slate-800 flex justify-end">
              <button
                onClick={onClearLogs}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white text-[10px]"
              >
                Clear Console
              </button>
            </div>
          )}
        </div>
      )}
    </aside>
  );
};
