import React from 'react';
import type { TelemetryState } from '../types';

interface TelemetryBarProps {
  telemetry: TelemetryState;
  onToggleSweep: () => void;
  onOpenFunnel: () => void;
  onExport: () => void;
}

export const TelemetryBar: React.FC<TelemetryBarProps> = ({
  telemetry,
  onToggleSweep,
  onOpenFunnel,
  onExport,
}) => {
  // Generate sparkline path from history
  const history = telemetry.history.length > 0 ? telemetry.history : [0, 0, 0, 0, 0];
  const maxVal = Math.max(...history, 1000);
  const minVal = Math.min(...history, 0);
  const range = maxVal - minVal || 1;

  const points = history
    .map((val, idx) => {
      const x = (idx / (history.length - 1)) * 120;
      const y = 28 - ((val - minVal) / range) * 24;
      return `${x},${y}`;
    })
    .join(' ');

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const remaining = Math.max(0, telemetry.targetCount - telemetry.totalScanned);
  const etaSec = telemetry.seedsPerSec > 0 ? Math.ceil(remaining / telemetry.seedsPerSec) : 0;

  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 px-6 flex items-center justify-between z-20 shadow-md">
      {/* Left: Brand & Status */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 font-bold text-sm shadow-inner">
            ⛏️
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight leading-none">
              Bedrock Seed Searcher
            </h1>
            <span className="text-[10px] text-slate-400 font-mono">
              Intel Xeon W-2191B • C11 OpenMP Native
            </span>
          </div>
        </div>

        <div className="h-6 w-px bg-slate-800"></div>

        {/* Global Status Pill */}
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              telemetry.status === 'running'
                ? 'bg-emerald-400 animate-pulse shadow-[0_0_8px_#10b981]'
                : telemetry.status === 'bds_verifying'
                ? 'bg-blue-400 animate-ping shadow-[0_0_8px_#38bdf8]'
                : 'bg-slate-600'
            }`}
          ></span>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            {telemetry.status === 'running'
              ? 'Sweeping Native Kernel'
              : telemetry.status === 'bds_verifying'
              ? 'BDS 1.26.52.3 Verifying...'
              : 'Idle'}
          </span>
        </div>
      </div>

      {/* Middle: Live Telemetry Gauges + Sparkline */}
      <div className="flex items-center gap-6">
        {/* Sparkline & Throughput */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col text-right">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Throughput</span>
            <span className="font-mono text-sm font-bold text-emerald-400">
              {telemetry.seedsPerSec.toLocaleString()}{' '}
              <span className="text-[10px] text-slate-500 font-normal">seeds/s</span>
            </span>
          </div>

          {/* SVG Sparkline */}
          <div className="w-28 h-7 bg-slate-950/60 border border-slate-800 rounded px-1 flex items-center">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 120 28">
              <polyline
                fill="none"
                stroke="#10b981"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                points={points}
              />
            </svg>
          </div>
        </div>

        <div className="h-6 w-px bg-slate-800"></div>

        {/* Total Scanned with Progress Bar */}
        <div className="flex flex-col min-w-[130px]">
          <div className="flex justify-between items-center text-[10px] text-slate-400 font-semibold mb-0.5">
            <span className="uppercase">Scanned</span>
            <span className="font-mono text-emerald-400">
              {telemetry.targetCount > 0
                ? `${((telemetry.totalScanned / telemetry.targetCount) * 100).toFixed(0)}%`
                : '0%'}
            </span>
          </div>
          <div className="flex items-baseline gap-1.5 font-mono">
            <span className="text-sm font-bold text-slate-200">
              {telemetry.totalScanned.toLocaleString()}
            </span>
            <span className="text-[10px] text-slate-500">
              / {telemetry.targetCount.toLocaleString()}
            </span>
          </div>
          {telemetry.status === 'running' && etaSec > 0 && (
            <span className="text-[9px] font-mono text-cyan-400">ETA: ~{etaSec}s</span>
          )}
        </div>

        <div className="h-6 w-px bg-slate-800"></div>

        {/* Elapsed / Memory */}
        <div className="flex flex-col">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Elapsed / RSS</span>
          <span className="font-mono text-xs font-semibold text-slate-300">
            {formatTime(telemetry.elapsedSeconds)}{' '}
            <span className="text-slate-500">•</span>{' '}
            <span className="text-cyan-400">{telemetry.memoryRssGib} GB</span>
          </span>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenFunnel}
          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold transition-all border border-slate-700 flex items-center gap-1.5"
          title="View Rejection Funnel Architecture"
        >
          📊 Funnel
        </button>

        <button
          onClick={onExport}
          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold transition-all border border-slate-700 flex items-center gap-1.5"
          title="Export surviving seeds to JSON"
        >
          💾 Export
        </button>

        <button
          onClick={onToggleSweep}
          className={`px-5 py-2 rounded-lg font-bold text-xs uppercase tracking-wider text-white transition-all shadow-lg flex items-center gap-2 ${
            telemetry.status === 'running'
              ? 'bg-red-500 hover:bg-red-600 shadow-red-500/20'
              : 'bg-emerald-500 hover:bg-emerald-600 shadow-emerald-500/30'
          }`}
        >
          {telemetry.status === 'running' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-white animate-ping"></span>
              Stop Sweep
            </>
          ) : (
            <>
              <span>▶</span> Start Sweep
            </>
          )}
        </button>
      </div>
    </header>
  );
};
