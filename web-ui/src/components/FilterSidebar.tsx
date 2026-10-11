import React, { useState } from 'react';
import type { SearchConfig } from '../types';
import { PRESETS } from '../mockData';

interface FilterSidebarProps {
  config: SearchConfig;
  onChangeConfig: (newConfig: SearchConfig) => void;
  logs: string[];
}

export const FilterSidebar: React.FC<FilterSidebarProps> = ({
  config,
  onChangeConfig,
  logs,
}) => {
  const [activeTab, setActiveTab] = useState<'targets' | 'engine' | 'logs'>('targets');

  const ALL_STRUCTURES = [
    { id: 'stronghold', name: 'Stronghold', icon: '🏰' },
    { id: 'ancient_city', name: 'Ancient City', icon: '🏙️' },
    { id: 'village', name: 'Village', icon: '🏡' },
    { id: 'trial_chamber', name: 'Trial Chamber', icon: '⚔️' },
    { id: 'mansion', name: 'Mansion', icon: '🏚️' },
    { id: 'monument', name: 'Monument', icon: '🏛️' },
    { id: 'outpost', name: 'Outpost', icon: '🏹' },
  ];

  const ALL_BIOMES = [
    { id: 'mushroom_fields', name: 'Mushroom Fields', icon: '🍄' },
    { id: 'jungle', name: 'Jungle', icon: '🌴' },
    { id: 'badlands', name: 'Badlands', icon: '🏜️' },
    { id: 'pale_garden', name: 'Pale Garden', icon: '🪵' },
    { id: 'dappled_forest', name: 'Dappled Forest', icon: '🌲' },
    { id: 'cherry_grove', name: 'Cherry Grove', icon: '🌸' },
    { id: 'snowy_peaks', name: 'Snowy Peaks', icon: '❄️' },
  ];

  const toggleStructure = (id: string) => {
    const next = config.requiredStructures.includes(id)
      ? config.requiredStructures.filter((s) => s !== id)
      : [...config.requiredStructures, id];
    onChangeConfig({ ...config, requiredStructures: next });
  };

  const toggleBiome = (id: string) => {
    const next = config.selectedBiomes.includes(id)
      ? config.selectedBiomes.filter((b) => b !== id)
      : [...config.selectedBiomes, id];
    onChangeConfig({ ...config, selectedBiomes: next });
  };

  const handleSelectPreset = (presetName: string) => {
    const preset = PRESETS.find((p) => p.name === presetName);
    if (preset) {
      onChangeConfig({
        ...config,
        presetName: preset.name,
        ...preset.config,
      });
    }
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
          Targets
        </button>
        <button
          onClick={() => setActiveTab('engine')}
          className={`flex-1 py-3 text-xs font-semibold tracking-wider uppercase transition-all ${
            activeTab === 'engine'
              ? 'text-emerald-400 border-b-2 border-emerald-400 bg-slate-900/60'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Hardware
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
          {/* Presets */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Configuration Preset
            </label>
            <select
              value={config.presetName}
              onChange={(e) => handleSelectPreset(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white outline-none focus:border-emerald-500"
            >
              {PRESETS.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Required Overworld Structures */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Required Structures
            </label>
            <div className="grid grid-cols-2 gap-1.5">
              {ALL_STRUCTURES.map((s) => {
                const isSelected = config.requiredStructures.includes(s.id);
                return (
                  <button
                    key={s.id}
                    onClick={() => toggleStructure(s.id)}
                    className={`py-1.5 px-2 rounded text-xs font-medium flex items-center gap-1.5 transition-all text-left border ${
                      isSelected
                        ? 'bg-emerald-600/30 border-emerald-500/50 text-emerald-300'
                        : 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <span>{s.icon}</span>
                    <span className="truncate">{s.name}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Nether Requirements */}
          <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300">🔥 Nether Pair Policy</span>
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

          {/* Biome Families */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Required Biomes
            </label>
            <div className="flex flex-wrap gap-1.5">
              {ALL_BIOMES.map((b) => {
                const isSelected = config.selectedBiomes.includes(b.id);
                return (
                  <button
                    key={b.id}
                    onClick={() => toggleBiome(b.id)}
                    className={`py-1 px-2 rounded-full text-xs font-medium flex items-center gap-1 transition-all border ${
                      isSelected
                        ? 'bg-emerald-600/30 border-emerald-500/50 text-emerald-300'
                        : 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <span>{b.icon}</span>
                    <span>{b.name}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Terrain Spec */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              3D Terrain Specification
            </label>
            <div className="space-y-1.5">
              {[
                { id: 'v1_island', name: '🌊 V1 Ocean Island', desc: 'Flat center Y63, 48-ray water moat' },
                { id: 'v2_mountain', name: '⛰️ V2 Mountain Basin', desc: 'Continuous ring wall >Y150, flat valley' },
                { id: 'any', name: '✨ Any Terrain', desc: 'Fastest; ignores 3D density height' },
              ].map((t) => (
                <div
                  key={t.id}
                  onClick={() => onChangeConfig({ ...config, terrainSpec: t.id as any })}
                  className={`p-2.5 rounded-lg border cursor-pointer transition-all ${
                    config.terrainSpec === t.id
                      ? 'bg-slate-800 border-emerald-500/70 text-white'
                      : 'bg-slate-800/40 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="text-xs font-bold text-white">{t.name}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">{t.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Hardware & Acceleration Engine */}
      {activeTab === 'engine' && (
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {/* Concurrency Sliders */}
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-300 font-medium">Python Worker Processes:</span>
                <span className="font-mono text-emerald-400 font-bold">{config.workers} Workers</span>
              </div>
              <input
                type="range"
                min="1"
                max="32"
                value={config.workers}
                onChange={(e) => onChangeConfig({ ...config, workers: Number(e.target.value) })}
                className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
              />
              <span className="text-[10px] text-slate-500">Recommended for 18-Core Xeon: 14–16</span>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-300 font-medium">OpenMP C Threads per Worker:</span>
                <span className="font-mono text-emerald-400 font-bold">{config.openmpThreads} Threads</span>
              </div>
              <input
                type="range"
                min="1"
                max="4"
                value={config.openmpThreads}
                onChange={(e) => onChangeConfig({ ...config, openmpThreads: Number(e.target.value) })}
                className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
              />
            </div>
          </div>

          <hr className="border-slate-800" />

          {/* Native C Optimizations */}
          <div className="space-y-3">
            <span className="block text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Native C Accelerations
            </span>

            <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
              <label className="flex items-center justify-between text-xs text-slate-300 cursor-pointer">
                <span className="font-semibold">4×4 Quart Land Reuse</span>
                <input
                  type="checkbox"
                  checked={config.quartReuse}
                  onChange={(e) => onChangeConfig({ ...config, quartReuse: e.target.checked })}
                  className="rounded accent-emerald-500"
                />
              </label>
              <p className="text-[10px] text-slate-400">
                Reduces computed land columns by 92.5%; saves ~30% total candidate time.
              </p>
            </div>

            <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
              <label className="flex items-center justify-between text-xs text-slate-300 cursor-pointer">
                <span className="font-semibold">8-Block Y-Noise Cell Caching</span>
                <input
                  type="checkbox"
                  checked={config.yNoiseReuse}
                  onChange={(e) => onChangeConfig({ ...config, yNoiseReuse: e.target.checked })}
                  className="rounded accent-emerald-500"
                />
              </label>
              <p className="text-[10px] text-slate-400">
                Caches 33 aligned Perlin noise cells across 257 Y-levels in `bridge.c`.
              </p>
            </div>

            <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
              <label className="flex items-center justify-between text-xs text-slate-300 cursor-pointer">
                <span className="font-semibold">Docker BDS 1.26.52.3 Verifier</span>
                <input
                  type="checkbox"
                  checked={config.bdsValidation}
                  onChange={(e) => onChangeConfig({ ...config, bdsValidation: e.target.checked })}
                  className="rounded accent-emerald-500"
                />
              </label>
              <p className="text-[10px] text-slate-400">
                Spins up real Bedrock server container to verify exact palettes on finalists.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Live Terminal Logs */}
      {activeTab === 'logs' && (
        <div className="flex-1 bg-slate-950 p-3 font-mono text-[11px] overflow-y-auto space-y-1 text-slate-300 select-text">
          {logs.map((log, index) => (
            <div key={index} className="leading-tight">
              <span className="text-slate-500">[{new Date().toLocaleTimeString()}]</span>{' '}
              <span
                className={
                  log.includes('passed') || log.includes('Certified')
                    ? 'text-emerald-400'
                    : log.includes('BDS')
                    ? 'text-blue-400'
                    : 'text-slate-300'
                }
              >
                {log}
              </span>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
};
