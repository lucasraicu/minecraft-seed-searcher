import React, { useState, useMemo } from 'react';
import type { SearchConfig, LaunchReceipt } from '../types';
import { ALL_STRUCTURES } from '../constants/structures';
import { SEARCH_PROFILES, getSearchProfile, normalizeStructureCounts } from '../constants/baselinePolicy';
import { computeTotalFeasibility, BIOME_MARGINAL_RATES } from '../utils/probability';
import type { SearchProfileName } from '../constants/baselinePolicy';

interface FilterSidebarProps {
  config: SearchConfig;
  onChangeConfig: (newConfig: SearchConfig) => void;
  logs: string[];
  onClearLogs?: () => void;
  onResumeSweep: (runId: string) => void;
  sweepRunning: boolean;
  preview?: LaunchReceipt | null;
  previewError?: string;
  lastLaunch?: LaunchReceipt | null;
  onCopyNotice?: (message: string) => void;
}

export const FilterSidebar: React.FC<FilterSidebarProps> = ({
  config, onChangeConfig, logs, onClearLogs, onResumeSweep, sweepRunning,
  preview, previewError, lastLaunch, onCopyNotice,
}) => {
  const [activeTab, setActiveTab] = useState<'targets' | 'engine' | 'logs'>('targets');
  const [savedRuns, setSavedRuns] = useState<Array<{ runId: string; completedSeeds: number; targetCount: number; resumable: boolean }>>([]);
  const [resumeRunId, setResumeRunId] = useState('');
  const [runsError, setRunsError] = useState('');
  const policy = getSearchProfile(config.profile);
  const floorCounts = normalizeStructureCounts(config.structureFloorCounts);
  const feasibility = useMemo(() => computeTotalFeasibility({ ...config,
    requiredStructures: Object.keys(policy.counts), structureFloorCounts: floorCounts,
  }), [config, policy, floorCounts]);
  const biomeName = (id: string) => id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const toggleBiome = (id: string) => {
    if (sweepRunning || (config.profile !== 'dynamic1664' && config.profile !== 'dynamic2048')) return;
    const selected = new Set(config.selectedBiomes);
    if (selected.has(id)) selected.delete(id); else selected.add(id);
    onChangeConfig({ ...config, selectedBiomes: policy.requiredBiomes.filter(f => selected.has(f)) });
  };
  const percentage = (p: number) => p < 0.0001 ? `${(p * 100).toExponential(2)}%` : `${(p * 100).toFixed(2)}%`;
  const setCount = (id: string, delta: number) => {
    if (sweepRunning || !policy.editableCounts.includes(id)) return;
    const count = Math.min(64, Math.max(policy.floors[id] ?? policy.counts[id], (floorCounts[id] ?? policy.counts[id]) + delta));
    onChangeConfig({ ...config, structureFloorCounts: { ...floorCounts, [id]: count }, requiredStructures: Object.keys(policy.counts) });
  };
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
  const copy = async (value: string) => {
    try { await navigator.clipboard.writeText(value); onCopyNotice?.('Copied command'); }
    catch { onCopyNotice?.('Could not copy command'); }
  };
  const commandView = (receipt: LaunchReceipt, title: string) => (
    <details className="rounded border border-slate-700 bg-slate-950 p-2 text-[10px]" open={receipt.kind === 'preview'}>
      <summary className="cursor-pointer font-bold text-cyan-300">{title}</summary>
      <p className="mt-2 text-slate-400">Working directory: {receipt.cwd}</p>
      <pre className="my-2 max-h-32 overflow-auto whitespace-pre-wrap break-all select-text">{receipt.shellCommand}</pre>
      <button onClick={() => copy(receipt.shellCommand)} className="text-cyan-300">{receipt.kind === 'preview' ? 'Copy command template' : 'Copy runnable command'}</button>
      <p className="mt-2 text-slate-400">{receipt.controls.count.toLocaleString()} inputs · index {receipt.controls.start_index} · {receipt.controls.threads} threads · batch {receipt.controls.batch_size ?? 'saved'} · deficit budget {receipt.controls.max_misses}</p>
      <details className="mt-2"><summary className="cursor-pointer">Resolved policy (includes edited structure targets)</summary>
        <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap select-text">{receipt.policyYaml}</pre>
      </details>
    </details>
  );

  return (
    <aside className="w-80 h-full bg-slate-900 border-r border-slate-800 flex flex-col z-10 shadow-xl">
      <div className="flex border-b border-slate-800">
        {(['targets', 'engine', 'logs'] as const).map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)} className={`flex-1 py-3 text-xs font-semibold ${activeTab === tab ? 'text-emerald-400' : 'text-slate-400'}`}>
            {tab === 'targets' ? 'Search targets' : tab === 'engine' ? 'Run settings' : 'Console'}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <p className="text-xs text-slate-300">Editable search settings below are sent to the machine. {sweepRunning ? 'Settings are locked while a job is active or paused. Stop it to configure a new sweep.' : 'Changes apply to the next new sweep.'} Map and result-view controls only change the display.</p>
        {activeTab === 'targets' && (
          <fieldset disabled={sweepRunning} className="space-y-4 disabled:opacity-60">
            <label className="block text-xs space-y-2"><span>Search policy</span>
              <select aria-label="Search policy" value={config.profile} disabled={sweepRunning} onChange={(event) => {
                const profile = event.target.value as SearchProfileName;
                const selected = getSearchProfile(profile);
                onChangeConfig({ ...config, profile, structureFloorCounts: { ...selected.counts }, requiredStructures: Object.keys(selected.counts),
                  maxMisses: selected.defaultMisses, selectedBiomes: selected.requiredBiomes,
                  playableRadiusOverworld: selected.overworldSide, playableRadiusNether: selected.netherSide });
              }} className="w-full rounded bg-slate-950 border border-slate-700 p-2">
                {(Object.keys(SEARCH_PROFILES) as SearchProfileName[]).map((name) => <option key={name} value={name}>{SEARCH_PROFILES[name].name}</option>)}
              </select>
            </label>
            <div className="text-xs text-slate-400">{policy.revision} · Overworld {policy.overworldSide} × {policy.overworldSide} · Nether {policy.netherSide} × {policy.netherSide}</div>
            <section aria-label="Probability estimate" className="rounded-lg border border-emerald-700/50 bg-slate-950 p-3 space-y-2">
              <div className="flex items-center justify-between text-xs"><h3 className="font-bold text-emerald-300">Probability estimate</h3><span className="text-slate-400">Planning model</span></div>
              <p className={`font-mono text-lg font-bold ${feasibility.color}`}>{feasibility.formattedOdds}</p>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="rounded bg-slate-800 p-2">Structures<span className="block font-mono text-emerald-300">{percentage(feasibility.structures.probability)}</span></div>
                <div className="rounded bg-slate-800 p-2">Selected biomes<span className="block font-mono text-cyan-300">{percentage(feasibility.biomes.probability)}</span></div>
              </div>
              {feasibility.biomes.bottleneck && <p className="text-[11px] text-slate-400">Rarest selected biome: <span className="text-slate-200">{feasibility.biomes.bottleneck.name}</span></p>}
              <p className="text-[10px] text-slate-400">Historical 2048-block estimates, uncalibrated for the sliding 1664 search. Correlated requirements mean these odds are not a measured success rate or a guarantee.</p>
            </section>
            <section aria-label="Biome selection" className="rounded-lg border border-slate-700 p-3 space-y-3">
              <div className="flex items-center justify-between text-xs"><h3 className="font-bold">Required biomes</h3><span className="font-mono text-emerald-400">{config.selectedBiomes.length} / {policy.requiredBiomes.length}</span></div>
              <p className="text-[11px] text-slate-400">{(config.profile === 'dynamic1664' || config.profile === 'dynamic2048') ? 'Selected families are required in the live search. Deselecting relaxes the default blueprint palette; biome bonuses stay unchanged.' : 'This historical profile keeps its recorded biome requirements.'}</p>
              <div className="flex flex-wrap gap-1.5">
                {policy.requiredBiomes.map(id => {
                  const selected = config.selectedBiomes.includes(id);
                  return <button key={id} type="button" aria-label={`Require ${biomeName(id)}`} aria-pressed={selected}
                    disabled={sweepRunning || (config.profile !== 'dynamic1664' && config.profile !== 'dynamic2048')} onClick={() => toggleBiome(id)}
                    className={`rounded-full border px-2 py-1 text-[11px] transition-colors disabled:cursor-not-allowed ${selected ? 'border-emerald-500/50 bg-emerald-600/20 text-emerald-200' : 'border-slate-700 bg-slate-800 text-slate-400'}`}>
                    {selected ? '✓ ' : '+ '}{biomeName(id)} <span className="opacity-60">{Math.round((BIOME_MARGINAL_RATES[id] ?? 0) * 100)}%</span>
                  </button>;
                })}
              </div>
              {(config.profile === 'dynamic1664' || config.profile === 'dynamic2048') && <div className="flex gap-4 text-[11px] text-cyan-300">
                <button type="button" onClick={() => onChangeConfig({ ...config, selectedBiomes: [...policy.requiredBiomes] })}>Restore blueprint biomes</button>
                <button type="button" onClick={() => onChangeConfig({ ...config, selectedBiomes: [] })}>Clear selection</button>
              </div>}
              {config.selectedBiomes.length === 0 && <p className="text-[11px] text-amber-300">No Overworld palette requirement. Structure viability and Nether biome requirements still apply.</p>}
              <p className="text-[10px] text-slate-400">Surface families use Y=63/160; cave families use Y=−48/0. Mansions still require a Dark Forest start even when its palette toggle is off.</p>
            </section>
            <div className="flex justify-between items-center"><h3 className="text-xs font-bold">Live structure targets</h3>
              <button onClick={() => onChangeConfig({ ...config, structureFloorCounts: { ...policy.counts }, requiredStructures: Object.keys(policy.counts), maxMisses: policy.defaultMisses })}
                className="text-xs text-cyan-300">Reset</button>
            </div>
            {ALL_STRUCTURES.filter((s) => s.id in policy.counts).map((s) => {
              const count = floorCounts[s.id] ?? policy.counts[s.id];
              const editable = policy.editableCounts.includes(s.id);
              const floor = policy.floors[s.id] ?? policy.counts[s.id];
              return <div key={s.id} className="flex justify-between items-center rounded bg-slate-800 px-2 py-2 text-xs">
                <span>{s.icon} {s.name}<span className="block text-[10px] text-slate-400">{editable ? policy.flexible.includes(s.id) ? `Hard floor ${floor}; deficits below target` : `Required count; minimum target ${floor}` : 'Fixed by policy'}</span></span>
                <div className="flex items-center gap-2">
                  <button title="Decrease target count" aria-label={`Decrease ${s.name}`} disabled={sweepRunning || !editable || count <= floor} onClick={() => setCount(s.id, -1)} className="px-1 disabled:opacity-25">−</button>
                  <span className="font-mono text-emerald-400">{count}</span>
                  <button title="Increase target count" aria-label={`Increase ${s.name}`} disabled={sweepRunning || !editable || count >= 64} onClick={() => setCount(s.id, 1)} className="px-1 disabled:opacity-25">+</button>
                </div>
              </div>;
            })}
            <div className="rounded border border-slate-700 p-3 text-xs space-y-2">
              <h3 className="font-bold">Other policy rules (read-only)</h3>
              <p className="text-slate-400">Selected Overworld families: {config.selectedBiomes.length ? config.selectedBiomes.map(biomeName).join(', ') : 'None'}.</p>
              {policy.netherBiomes.length > 0 && <p className="text-slate-400">Required Nether biomes: {policy.netherBiomes.join(', ')}.</p>}
              <p className="text-slate-400">Fortress and Bastion targets apply inside the playable Nether window. Physical overlap is not a filter. Biome predictions do not establish navigable cave openings.</p>
            </div>
          </fieldset>
        )}
        {activeTab === 'engine' && <>
          <p className="text-xs text-emerald-300">Compact retention: saves surviving candidates and range checkpoints, not rejected seeds. Billion-seed runs are supported; actual disk usage is checked before each write.</p>
          <fieldset disabled={sweepRunning} className="space-y-4 disabled:opacity-60">
            <label className="block text-xs space-y-1"><span>Seed count</span>
              <input aria-label="Seed count" type="number" min="1" max={Number.MAX_SAFE_INTEGER} step="1" value={config.sweepSeedCount || ''} onChange={(e) => onChangeConfig({ ...config, sweepSeedCount: Number(e.target.value) })} className="w-full rounded bg-slate-800 p-2 font-mono" />
            </label>
            <label className="block text-xs space-y-1"><span>Starting seed index</span>
              <input aria-label="Starting seed index" type="text" inputMode="numeric" value={config.startIndex} onChange={(e) => { if (/^\d*$/.test(e.target.value)) onChangeConfig({ ...config, startIndex: e.target.value }); }} className="w-full rounded bg-slate-800 p-2 font-mono" />
            </label>
            <label className="block text-xs space-y-1"><span>Deficit budget</span>
              <select aria-label="Deficit budget" value={config.maxMisses} onChange={(e) => onChangeConfig({ ...config, maxMisses: Number(e.target.value) })} className="w-full rounded bg-slate-800 p-2">
                {Array.from({ length: policy.maxMisses + 1 }, (_, value) => <option key={value} value={value}>{value} deficient categories</option>)}
              </select>
            </label>
            <label className="block text-xs space-y-1"><span>Native threads (1–34)</span>
              <input aria-label="Native threads" type="number" min="1" max="34" step="1" value={config.openmpThreads} onChange={(e) => onChangeConfig({ ...config, openmpThreads: Number(e.target.value) })} className="w-full rounded bg-slate-800 p-2" />
            </label>
            <label className="block text-xs space-y-1"><span>Native batch size (1–16,384)</span>
              <input aria-label="Native batch size" type="number" min="1" max="16384" step="1" value={config.batchSize} onChange={(e) => onChangeConfig({ ...config, batchSize: Number(e.target.value) })} className="w-full rounded bg-slate-800 p-2" />
            </label>
          </fieldset>
          <div className="rounded border border-slate-700 p-3 text-xs space-y-2">
            <button onClick={refreshRuns} className="text-cyan-300">Refresh saved runs</button>
            <select aria-label="Saved sweep" value={resumeRunId} onChange={(e) => setResumeRunId(e.target.value)} className="w-full rounded bg-slate-800 p-2">
              <option value="">Select an incomplete run</option>
              {savedRuns.map((run) => <option key={run.runId} value={run.runId}>{run.runId} — {run.completedSeeds.toLocaleString()}/{run.targetCount.toLocaleString()}</option>)}
            </select>
            <button disabled={!resumeRunId || sweepRunning} onClick={() => onResumeSweep(resumeRunId)} className="text-cyan-300 disabled:opacity-30">Resume with saved settings</button>
            <p className="text-slate-400">Resume uses the checkpoint's saved policy, range, threads, and batch size. It does not apply draft edits.</p>
            {runsError && <p role="alert" className="text-red-300">{runsError}</p>}
          </div>
        </>}
        {activeTab === 'logs' && <div className="space-y-2 text-xs">
          <button onClick={onClearLogs} className="text-cyan-300">Clear console</button>
          {logs.map((line, index) => <p key={index} className="font-mono break-words text-slate-300">{line}</p>)}
        </div>}
        <div className="space-y-2">
          <h3 className="text-xs font-bold">Machine command</h3>
          {previewError && <p role="alert" className="text-xs text-red-300">{previewError}</p>}
          {preview && !previewError && commandView(preview, 'Next new sweep — validated preview')}
          {!preview && !previewError && <p className="text-xs text-slate-400">Validating current settings…</p>}
          <p className="text-[10px] text-slate-400">The preview uses &lt;new-run&gt; until launch assigns a directory. Edited targets are saved in policy.yaml; expand the resolved policy to inspect them. Disk capacity is checked in the preview and again at launch; build availability is checked at launch.</p>
          {lastLaunch && commandView(lastLaunch, `Last executed command (${lastLaunch.kind})`)}
        </div>
      </div>
    </aside>
  );
};
