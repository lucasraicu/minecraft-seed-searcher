import React from 'react';
import type { TelemetryState, ConnectionStatus, RuntimeIdentity } from '../types';
import { formatLastContact } from '../utils/network';

interface TelemetryBarProps {
  telemetry: TelemetryState;
  dataMode: ConnectionStatus;
  lastContactTime?: number | null;
  runtimeIdentity?: RuntimeIdentity | null;
  targetVolume?: number;
  onChangeTargetVolume?: (vol: number) => void;
  onToggleSweep: () => void;
  onPauseSweep?: () => void;
  onContinueSweep?: () => void;
  onOpenFunnel: () => void;
  onExport: () => void;
  onBeginBDSParity?: () => void;
}

export const TelemetryBar: React.FC<TelemetryBarProps> = ({
  telemetry,
  dataMode,
  lastContactTime,
  runtimeIdentity,
  targetVolume,
  onChangeTargetVolume,
  onToggleSweep,
  onPauseSweep,
  onContinueSweep,
  onOpenFunnel,
  onExport,
  onBeginBDSParity,
}) => {
  const [clock, setClock] = React.useState(() => Date.now());
  React.useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Generate sparkline path from history
  const history = telemetry.history.length > 0 ? telemetry.history : [0, 0, 0, 0, 0];
  const maxVal = Math.max(...history, 1000);
  const minVal = Math.min(...history, 0);
  const range = maxVal - minVal || 1;

  const points = history
    .map((val, idx) => {
      const x = (idx / Math.max(1, history.length - 1)) * 120;
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
  const isDisconnected = dataMode === 'disconnected';
  const isStale = dataMode === 'stale';
  const isConnecting = dataMode === 'connecting';
  const isLive = dataMode === 'live';

  const hasLiveTelemetry =
    isLive && (telemetry.status === 'running' || Boolean(telemetry.runId));
  const hasPreservedTelemetry =
    (isStale || isDisconnected) && (telemetry.totalScanned > 0 || Boolean(telemetry.runId));

  // Determine status pill dot & text
  let statusDotClass = 'bg-slate-600';
  let statusText = 'Idle';

  if (isDisconnected) {
    statusDotClass = 'bg-rose-500 shadow-[0_0_8px_#f43f5e]';
    if (telemetry.status === 'running') {
      statusText = 'Disconnected (was Sweeping)';
    } else if (telemetry.status === 'paused') {
      statusText = 'Disconnected (was Paused)';
    } else if (telemetry.status === 'completed') {
      statusText = 'Disconnected (last: Complete)';
    } else if (telemetry.status === 'bds_verifying') {
      statusText = 'Disconnected (was BDS Verifying)';
    } else if (telemetry.status === 'error') {
      statusText = 'Disconnected (Error)';
    } else {
      statusText = 'Disconnected (Offline)';
    }
  } else if (isConnecting) {
    statusDotClass = 'bg-amber-400 animate-pulse';
    statusText = 'Connecting...';
  } else {
    // live or stale
    if (telemetry.status === 'running') {
      statusDotClass = isStale
        ? 'bg-amber-400 shadow-[0_0_8px_#f59e0b]'
        : 'bg-emerald-400 animate-pulse shadow-[0_0_8px_#10b981]';
      statusText = isStale ? 'Sweeping Native Kernel (Stale)' : 'Sweeping Native Kernel';
    } else if (telemetry.status === 'paused') {
      statusDotClass = 'bg-amber-400 shadow-[0_0_8px_#f59e0b]';
      statusText = isStale ? 'Sweep Paused (Stale)' : 'Sweep Paused';
    } else if (telemetry.status === 'bds_verifying') {
      statusDotClass = isStale
        ? 'bg-amber-400'
        : 'bg-blue-400 animate-ping shadow-[0_0_8px_#38bdf8]';
      statusText = isStale ? 'BDS Verifying (Stale)' : 'BDS 1.26.52.3 Verifying...';
    } else if (telemetry.status === 'error') {
      statusDotClass = 'bg-red-500';
      statusText = isStale ? 'Sweep Error (Stale)' : 'Sweep Error';
    } else if (telemetry.status === 'completed') {
      statusDotClass = isStale ? 'bg-slate-500' : 'bg-emerald-600';
      statusText = isStale ? 'Sweep Complete (Stale)' : 'Sweep Complete';
    } else {
      statusDotClass = 'bg-slate-600';
      statusText = isStale ? 'Idle (Stale)' : 'Idle';
    }
  }

  const sparklineStroke = isLive ? '#10b981' : isStale ? '#eab308' : '#64748b';

  return (
    <header className="min-h-16 shrink-0 bg-slate-900 border-b border-slate-800 px-4 py-3 flex flex-wrap items-center justify-between gap-3 z-20 shadow-md">
      {/* Left: Brand & Status */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 font-bold text-sm shadow-inner">
            ⛏️
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight leading-none">
              Bedrock Seed Searcher
            </h1>
            <span className="text-[10px] text-slate-400 font-mono">
              {isConnecting
                ? 'Connecting to local backend...'
                : isStale
                ? 'Backend connection stale (retrying...)'
                : isDisconnected
                ? 'Disconnected from backend'
                : 'Live backend connected'}
            </span>
          </div>
        </div>

        <div className="h-6 w-px bg-slate-800"></div>

        <span
          className={`px-2 py-1 rounded text-[10px] font-bold tracking-wide border ${
            isConnecting
              ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
              : isStale
              ? 'bg-yellow-500/10 text-yellow-300 border-yellow-500/30'
              : isDisconnected
              ? 'bg-rose-500/10 text-rose-300 border-rose-500/30'
              : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
          }`}
        >
          {dataMode.toUpperCase()}
        </span>

        {/* Last Contact Timestamp */}
        {lastContactTime ? (
          <span
            className="text-[10px] text-slate-400 font-mono"
            title={`Last successful backend response: ${new Date(lastContactTime).toLocaleTimeString()}`}
          >
            contact: {formatLastContact(lastContactTime, clock)}
          </span>
        ) : null}

        {/* Technical Fingerprint Tooltip */}
        {runtimeIdentity && (
          <span
            className="cursor-help text-[10px] text-slate-500 hover:text-slate-300 font-mono px-1.5 py-0.5 rounded bg-slate-950/80 border border-slate-800 transition-colors"
            title={`Server Runtime Fingerprint:\n• PID: ${runtimeIdentity.pid ?? 'n/a'}\n• Started: ${runtimeIdentity.processStartedAt ? new Date(runtimeIdentity.processStartedAt * 1000).toLocaleString() : 'unknown'}\n• Source SHA: ${runtimeIdentity.loadedServerSourceSha256 ?? 'n/a'}\n• Native Build: ${runtimeIdentity.nativeBuild?.digest ?? runtimeIdentity.nativeBuild?.path ?? 'unknown'} (${runtimeIdentity.nativeBuild?.source ?? 'unverified'})${telemetry.statusSchemaVersion ? `\n• Schema Version: v${telemetry.statusSchemaVersion}` : ''}${telemetry.generation !== undefined ? `\n• Generation: ${telemetry.generation}` : ''}`}
          >
            v2 • {runtimeIdentity.pid ? `PID ${runtimeIdentity.pid}` : 'daemon'}
          </span>
        )}

        {/* Global Status Pill */}
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${statusDotClass}`}></span>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            {statusText}
          </span>
        </div>
      </div>

      {/* Middle: Live Telemetry Gauges + Sparkline */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Sparkline & Throughput */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col text-right">
            <span className="text-[10px] text-slate-400 uppercase font-semibold">Throughput</span>
            <span className="font-mono text-sm font-bold text-emerald-400">
              {hasLiveTelemetry ? (
                <>
                  {telemetry.seedsPerSec.toLocaleString()}{' '}
                  <span className="text-[10px] text-slate-500 font-normal">seeds/s</span>
                </>
              ) : hasPreservedTelemetry ? (
                <span className={isDisconnected ? 'text-slate-400' : 'text-amber-400'}>
                  {isDisconnected ? 0 : telemetry.seedsPerSec.toLocaleString()}{' '}
                  <span className="text-[10px] text-slate-500 font-normal">
                    {isDisconnected ? 'seeds/s (offline)' : 'seeds/s (stale)'}
                  </span>
                </span>
              ) : (
                <>
                  — <span className="text-[10px] text-slate-500 font-normal">seeds/s</span>
                </>
              )}
            </span>
          </div>

          {/* SVG Sparkline */}
          <div className="w-28 h-7 bg-slate-950/60 border border-slate-800 rounded px-1 flex items-center">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 120 28">
              <polyline
                fill="none"
                stroke={sparklineStroke}
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
              {telemetry.targetCount > 0 && (hasLiveTelemetry || hasPreservedTelemetry)
                ? `${((telemetry.totalScanned / telemetry.targetCount) * 100).toFixed(0)}%`
                : '0%'}
            </span>
          </div>
          <div className="flex items-baseline gap-1.5 font-mono">
            <span className={`text-sm font-bold ${isDisconnected ? 'text-slate-400' : isStale ? 'text-amber-300' : 'text-slate-200'}`}>
              {hasLiveTelemetry
                ? telemetry.totalScanned.toLocaleString()
                : hasPreservedTelemetry
                ? `${telemetry.totalScanned.toLocaleString()}`
                : '—'}
            </span>
            <span className="text-[10px] text-slate-500">
              / {hasLiveTelemetry || hasPreservedTelemetry ? telemetry.targetCount.toLocaleString() : '—'}
              {hasPreservedTelemetry && (
                <span className="ml-1 text-[9px] text-amber-400">
                  [{isDisconnected ? 'offline' : 'stale'}]
                </span>
              )}
            </span>
          </div>
          {isLive && telemetry.status === 'running' && etaSec > 0 && (
            <span className="text-[9px] font-mono text-cyan-400">ETA: ~{etaSec}s</span>
          )}
        </div>

        <div className="h-6 w-px bg-slate-800"></div>

        {/* Elapsed / Memory */}
        <div className="flex flex-col">
          <span className="text-[10px] text-slate-400 uppercase font-semibold">Elapsed / RSS</span>
          <span className="font-mono text-xs font-semibold text-slate-300">
            {hasLiveTelemetry ? (
              formatTime(telemetry.elapsedSeconds)
            ) : hasPreservedTelemetry ? (
              <span className={isDisconnected ? 'text-slate-400' : 'text-amber-300'}>
                {formatTime(telemetry.elapsedSeconds)} ({isDisconnected ? 'frozen' : 'stale'})
              </span>
            ) : (
              '—'
            )}{' '}
            <span className="text-slate-500">•</span>{' '}
            <span className="text-cyan-400">
              {(hasLiveTelemetry || hasPreservedTelemetry) && telemetry.memoryRssGib !== null
                ? `${telemetry.memoryRssGib} GB RSS`
                : 'RSS unknown'}
            </span>
          </span>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex flex-wrap items-center gap-3">
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

        {/* Quick Volume Target Selector */}
        {onChangeTargetVolume && (
          <div className="hidden md:flex items-center gap-1 bg-slate-950/90 border border-slate-800 rounded-lg p-1 text-[10px] font-mono">
            <span className="text-slate-500 uppercase px-1 font-semibold">Target:</span>
            {[100_000, 1_000_000, 10_000_000, 100_000_000, 1_000_000_000].map((v) => {
              const active = (targetVolume ?? telemetry.targetCount) === v;
              return (
                <button
                  key={v}
                  onClick={() => onChangeTargetVolume(v)}
                  disabled={telemetry.status === 'running' || telemetry.status === 'paused' || telemetry.status === 'bds_verifying'}
                  className={`px-1.5 py-0.5 rounded transition-all ${
                    active
                      ? 'bg-emerald-600 text-white font-bold shadow'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-50'
                  }`}
                  title={`Set sweep target volume: ${v.toLocaleString()} seeds`}
                >
                  {v >= 1_000_000_000 ? `${v / 1_000_000_000}B` : v >= 1_000_000 ? `${v / 1_000_000}M` : `${v / 1_000}k`}
                </button>
              );
            })}
          </div>
        )}

        {/* Sample Surface Button */}
        {onBeginBDSParity && (
          <button
            onClick={onBeginBDSParity}
            disabled={telemetry.status === 'bds_verifying'}
            className="px-3.5 py-2 rounded-lg font-bold text-xs uppercase tracking-wider text-blue-200 bg-blue-600/30 hover:bg-blue-600/50 border border-blue-500/40 shadow-lg shadow-blue-500/10 transition-all flex items-center gap-1.5 disabled:opacity-50"
            title="Begin Bedrock Dedicated Server (BDS) 1.26.52.3 Parity Audit on active candidate"
          >
            <span className={telemetry.status === 'bds_verifying' ? 'animate-spin' : ''}>🛡️</span>
            <span>{telemetry.status === 'bds_verifying' ? 'Verifying BDS...' : 'Sample Surface'}</span>
          </button>
        )}

        {telemetry.status === 'running' ? (
          <div className="flex items-center gap-2">
            <button
              onClick={onPauseSweep}
              className="px-4 py-2 rounded-lg font-bold text-xs uppercase tracking-wider text-white bg-amber-500 hover:bg-amber-600 shadow-lg shadow-amber-500/20 transition-all flex items-center gap-1.5"
              title="Pause and retain committed checkpoint; unfinished batches remain retryable"
            >
              <span>⏸</span> Pause
            </button>
            <button
              onClick={onToggleSweep}
              className="px-4 py-2 rounded-lg font-bold text-xs uppercase tracking-wider text-white bg-red-500 hover:bg-red-600 shadow-lg shadow-red-500/20 transition-all flex items-center gap-1.5"
              title="Stop and abort sweep immediately"
            >
              <span className="w-2 h-2 rounded-full bg-white animate-ping"></span>
              Stop
            </button>
          </div>
        ) : telemetry.status === 'paused' ? (
          <div className="flex items-center gap-2">
            <button
              onClick={onContinueSweep}
              className="px-5 py-2 rounded-lg font-bold text-xs uppercase tracking-wider text-white bg-emerald-500 hover:bg-emerald-600 shadow-lg shadow-emerald-500/30 transition-all flex items-center gap-1.5 animate-pulse"
              title="Continue sweep from last paused seed"
            >
              <span>▶</span> Continue Sweep
            </button>
            <button
              onClick={onToggleSweep}
              className="px-3 py-2 rounded-lg font-semibold text-xs text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 transition-all border border-slate-700"
              title="Reset or stop current run"
            >
              ⏹ Stop
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            {Boolean(telemetry.runId && telemetry.totalScanned > 0 && telemetry.totalScanned < telemetry.targetCount) && (
              <button
                onClick={onContinueSweep}
                className="px-4 py-2 rounded-lg font-bold text-xs uppercase tracking-wider text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-600/30 transition-all flex items-center gap-1.5"
                title="Continue saved sweep run to completion"
              >
                <span>▶</span> Continue Sweep
              </button>
            )}
            <button
              onClick={onToggleSweep}
              className="px-5 py-2 rounded-lg font-bold text-xs uppercase tracking-wider text-white bg-emerald-500 hover:bg-emerald-600 shadow-lg shadow-emerald-500/30 transition-all flex items-center gap-1.5"
              title="Start a new sweep"
            >
              <span>▶</span> Start Sweep
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
