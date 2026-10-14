import { useState, useEffect, useRef, useCallback } from 'react';
import type { SeedCandidate, TelemetryState, SearchConfig, Dimension } from './types';
import { INITIAL_CONFIG, MOCK_CANDIDATES } from './mockData';
import { DEFAULT_SWEEP_IDEAL_COUNTS, V2_FLEXIBLE_FLOORS } from './constants/structures';
import { MapCanvas } from './components/MapCanvas';
import { CandidateFeed } from './components/CandidateFeed';
import { TelemetryBar } from './components/TelemetryBar';
import { FilterSidebar } from './components/FilterSidebar';
import { SeedDetailModal } from './components/SeedDetailModal';
import { FunnelModal } from './components/FunnelModal';

const VALID_TELEMETRY_STATUSES: TelemetryState['status'][] = [
  'idle',
  'running',
  'paused',
  'completed',
  'bds_verifying',
  'error',
];

function App() {
  const [config, setConfig] = useState<SearchConfig>(INITIAL_CONFIG);
  const [candidates, setCandidates] = useState<SeedCandidate[]>(MOCK_CANDIDATES);
  const [selectedCandidate, setSelectedCandidate] = useState<SeedCandidate | null>(MOCK_CANDIDATES[0]);
  const [inspectedCandidate, setInspectedCandidate] = useState<SeedCandidate | null>(null);
  const [isFunnelOpen, setIsFunnelOpen] = useState<boolean>(false);
  const [dataMode, setDataMode] = useState<'demo' | 'live'>('demo');

  // Map display settings
  const [dimension, setDimension] = useState<Dimension>('overworld');
  const [showBorders, setShowBorders] = useState<boolean>(true);
  const [showBiomes, setShowBiomes] = useState<boolean>(true);
  const [showGrid, setShowGrid] = useState<boolean>(true);
  const [showRavines, setShowRavines] = useState<boolean>(true);
  const [showCaves, setShowCaves] = useState<boolean>(true);

  // Live Telemetry state
  const [telemetry, setTelemetry] = useState<TelemetryState>({
    status: 'idle',
    seedsPerSec: 0,
    totalScanned: 0,
    targetCount: INITIAL_CONFIG.sweepSeedCount,
    candidatesFound: 0,
    elapsedSeconds: 0,
    currentStage: 'Waiting for a live sweep',
    memoryRssGib: null,
    activeThreads: null,
    sweepProgress: 0,
    history: [0, 0, 0, 0, 0, 0, 0, 0],
  });

  // Console Logs
  const [logs, setLogs] = useState<string[]>([
    'DEMO PREVIEW: sample records are illustrative and are not live scan results.',
    'Live sweep evidence appears here after the backend accepts a run.',
  ]);

  // Toast feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = useCallback((msg: string) => {
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
    }
    setToastMessage(msg);
    toastTimerRef.current = setTimeout(() => {
      setToastMessage(null);
      toastTimerRef.current = null;
    }, 3500);
  }, []);

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current);
      }
    };
  }, []);


  const apiGeneration = useRef(0);
  const commandInFlight = useRef(false);
  const postCommand = useCallback(async (path: string, payload: Record<string, unknown> = {}) => {
    if (commandInFlight.current) throw new Error('Another command is still pending');
    commandInFlight.current = true;
    apiGeneration.current += 1;
    try {
      const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Command failed');
      return data;
    } finally {
      commandInFlight.current = false;
      apiGeneration.current += 1;
    }
  }, []);
  const applyEffectiveConfig = useCallback((effective: any) => {
    if (!effective?.structures) return;
    const counts = { ...effective.structures.minimum_counts, ...effective.structures.nether_minimum_counts };
    setConfig((previous) => ({ ...previous, structureFloorCounts: { ...previous.structureFloorCounts, ...counts } }));
  }, []);

  // On mount, load any existing candidate database from backend
  useEffect(() => {
    let active = true;
    const generation = apiGeneration.current;
    fetch('/api/candidates')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (active && generation === apiGeneration.current && data && data.candidates && data.candidates.length > 0) {
          setCandidates(data.candidates);
          setSelectedCandidate(data.candidates[0]);
          setDataMode('live');
        }
      })
      .catch(() => {});

    // Check system status
    fetch('/api/sweep/status')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!active || generation !== apiGeneration.current || !data) return;
        const resolvedStatus = VALID_TELEMETRY_STATUSES.includes(data.status)
          ? (data.status as TelemetryState['status'])
          : (data.status === 'running' ? 'running' : 'idle');
        if (data.status === 'running') {
          setDataMode('live');
          setCandidates((current) => current.filter((candidate) => candidate.provenance === 'live'));
          setSelectedCandidate((current) => current?.provenance === 'live' ? current : null);
        }
        setTelemetry((prev) => ({
          ...prev,
          status: resolvedStatus,
          totalScanned: data.totalScanned || 0,
          targetCount: data.targetCount ?? INITIAL_CONFIG.sweepSeedCount,
          seedsPerSec: data.seedsPerSec || 0,
          elapsedSeconds: data.elapsedSeconds || 0,
          sweepProgress: data.sweepProgress || 0,
          history: data.history || prev.history,
        }));
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  const prevStatusRef = useRef<string>(telemetry.status);

  // Poll real backend for sweep status
  useEffect(() => {
    const pollInterval = telemetry.status === 'running' || telemetry.status === 'bds_verifying' ? 650 : 3000;

    let polling = false;
    let active = true;
    const timer = setInterval(() => {
      if (polling || commandInFlight.current) return;
      polling = true;
      const generation = apiGeneration.current;
      fetch('/api/sweep/status')
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (!active || generation !== apiGeneration.current || !data) return;

          // Detect completion
          if (prevStatusRef.current === 'running' && data.status === 'completed') {
            showToast(
              `🎉 Sweep Completed! ${data.totalScanned.toLocaleString()} seeds scanned in ${data.elapsedSeconds}s (${data.seedsPerSec.toLocaleString()} seeds/s)!`
            );
          }
          if (data.error && data.status === 'error' && prevStatusRef.current !== 'error') showToast(`Sweep error: ${data.error}`);
          prevStatusRef.current = data.status;

          const resolvedStatus = VALID_TELEMETRY_STATUSES.includes(data.status)
            ? (data.status as TelemetryState['status'])
            : (data.status === 'running' ? 'running' : 'idle');

          setTelemetry((prev) => ({
            ...prev,
            status: resolvedStatus,
            seedsPerSec: data.seedsPerSec || 0,
            totalScanned: data.totalScanned || 0,
            targetCount: data.targetCount ?? config.sweepSeedCount,
            candidatesFound: data.candidatesFound ?? 0,
            elapsedSeconds: data.elapsedSeconds || 0,
            sweepProgress: data.sweepProgress || 0,
            memoryRssGib: data.memoryRssGib ?? null,
            activeThreads: data.activeThreads ?? null,
            history: data.history && data.history.length > 0 ? data.history : prev.history,
            runId: data.runId,
            terrainStatus: data.terrainStatus ?? 'idle',
            terrainProgress: data.terrainProgress ?? prev.terrainProgress,
          }));

          if (Array.isArray(data.candidates)) {
            setCandidates(data.candidates);
            setDataMode('live');
            setSelectedCandidate((current) =>
              data.candidates.find((candidate: SeedCandidate) => candidate.id === current?.id) ??
              data.candidates[0] ??
              null
            );
          }

          if (data.logs && data.logs.length > 0) {
            setLogs((prev) => {
              const combined = [...data.logs, ...prev];
              return Array.from(new Set(combined)).slice(0, 50);
            });
          }
        })
        .catch(() => {})
        .finally(() => { polling = false; });
    }, pollInterval);

    return () => { active = false; clearInterval(timer); };
  }, [telemetry.status, config.sweepSeedCount, config.openmpThreads, showToast]);

  const handleToggleSweep = useCallback(async () => {
    try {
      if (telemetry.status === 'running' || telemetry.status === 'paused') {
        await postCommand('/api/sweep/stop');
        setTelemetry((prev) => ({ ...prev, status: 'idle', seedsPerSec: 0 }));
        showToast('Sweep stopped; checkpoint retained');
        return;
      }
      if (!Number.isSafeInteger(config.sweepSeedCount) || config.sweepSeedCount < 1 || !/^\d+$/.test(config.startIndex) ||
          BigInt(config.startIndex) + BigInt(config.sweepSeedCount) > (1n << 64n)) {
        throw new Error('Enter a positive whole seed count and a valid full64 starting index');
      }
      const data = await postCommand('/api/sweep/start', {
        count: config.sweepSeedCount, startIndex: config.startIndex, threads: config.openmpThreads,
        batchSize: config.batchSize, maxMisses: config.maxMisses,
        counts: Object.fromEntries(Object.entries(DEFAULT_SWEEP_IDEAL_COUNTS)
          .filter(([key, defaultIdeal]) => {
            const ideal = config.structureFloorCounts[key];
            return Number.isInteger(ideal) && ideal >= (V2_FLEXIBLE_FLOORS[key] ?? 0) && ideal !== defaultIdeal;
          }).map(([key]) => [key, config.structureFloorCounts[key]])),
      });
      applyEffectiveConfig(data.effectiveConfig);
      setTelemetry((prev) => ({ ...prev, status: 'running', runId: data.runId, totalScanned: 0,
        targetCount: config.sweepSeedCount, elapsedSeconds: 0, sweepProgress: 0 }));
      setDataMode('live'); setCandidates([]); setSelectedCandidate(null);
      showToast(`Native sweep started (${config.sweepSeedCount.toLocaleString()} seeds)`);
    } catch (error) {
      showToast(`Sweep command failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }, [telemetry.status, config, showToast, postCommand, applyEffectiveConfig]);

  const handleResumeSweep = useCallback(async (runId: string) => {
    try {
      const data = await postCommand('/api/sweep/resume', { runId });
      applyEffectiveConfig(data.effectiveConfig);
      setDataMode('live');
      setTelemetry((prev) => ({ ...prev, status: 'running' }));
      setLogs((prev) => [`Resuming saved sweep ${runId}`, ...prev]);
      showToast('Saved sweep resumed');
    } catch (error) {
      showToast(`Resume failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }, [showToast, postCommand, applyEffectiveConfig]);

  const handlePauseSweep = useCallback(async () => {
    try {
      showToast('Pausing sweep: finishing active batch...');
      const data = await postCommand('/api/sweep/pause', {});
      setTelemetry((prev) => ({ ...prev, status: 'paused', seedsPerSec: 0 }));
      setLogs((prev) => [`Sweep checkpoint retained at ${data.scannedCount ? data.scannedCount.toLocaleString() : 'active'} seeds`, ...prev]);
      showToast('Sweep paused; durable checkpoint retained');
    } catch (error) {
      showToast(`Pause failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }, [showToast, postCommand]);

  const handleContinueSweep = useCallback(async () => {
    try {
      showToast('Resuming sweep...');
      const data = await postCommand('/api/sweep/continue', { runId: telemetry.runId });
      applyEffectiveConfig(data.effectiveConfig);
      setDataMode('live');
      setTelemetry((prev) => ({ ...prev, status: 'running' }));
      setLogs((prev) => [`Continuing sweep from seed ${data.scannedCount ? data.scannedCount.toLocaleString() : telemetry.totalScanned.toLocaleString()}...`, ...prev]);
      showToast('▶ Sweep Continued');
    } catch (error) {
      showToast(`Continue failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }, [telemetry.runId, telemetry.totalScanned, showToast, postCommand, applyEffectiveConfig]);

  const handleStartTerrain = useCallback(async () => {
    try {
      showToast('Starting Continental Ocean Terrain Filtering...');
      await postCommand('/api/terrain/start', {});
      setTelemetry((prev) => ({ ...prev, terrainStatus: 'running' }));
      showToast('🌊 Terrain Filtering Started');
    } catch (error) {
      showToast(`Terrain start error: ${error instanceof Error ? error.message : String(error)}`);
    }
  }, [showToast, postCommand]);

  const handleStopTerrain = useCallback(async () => {
    try {
      showToast('Stopping Terrain Filtering...');
      await postCommand('/api/terrain/stop', {});
      setTelemetry((prev) => ({ ...prev, terrainStatus: 'idle' }));
      showToast('Terrain Filtering Stopped');
    } catch (error) {
      showToast(`Terrain stop error: ${error instanceof Error ? error.message : String(error)}`);
    }
  }, [showToast, postCommand]);

  const handleExport = () => {
    const dataStr =
      'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(candidates, null, 2));
    const dl = document.createElement('a');
    dl.setAttribute('href', dataStr);
    dl.setAttribute('download', `minecraft-seeds-${Date.now()}.json`);
    dl.click();
    showToast(`Exported ${candidates.length} displayed candidates to JSON`);
  };

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.repeat || e.ctrlKey || e.altKey || e.metaKey) return;
      const target = e.target as HTMLElement | null;
      const isInput =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        target instanceof HTMLButtonElement ||
        Boolean(target?.isContentEditable) ||
        Boolean(target?.closest('input, textarea, select, button, [role="button"], dialog, [role="dialog"]'));

      const isModalOpen = Boolean(inspectedCandidate) || isFunnelOpen;

      if (e.code === 'Space') {
        if (isInput || isModalOpen) return;
        e.preventDefault();
        handleToggleSweep();
        return;
      }

      if (isInput || isModalOpen) return;

      if (e.key.toLowerCase() === 'd') {
        setDimension((d) => (d === 'overworld' ? 'nether' : 'overworld'));
        showToast(`Switched to ${dimension === 'overworld' ? 'Nether' : 'Overworld'}`);
      } else if (e.key.toLowerCase() === 'b') {
        setShowBorders((b) => !b);
      } else if (e.key.toLowerCase() === 'g') {
        setShowGrid((g) => !g);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleToggleSweep, dimension, showToast, inspectedCandidate, isFunnelOpen]);

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 font-sans overflow-hidden select-none">
      {/* Top Telemetry & Controls HUD */}
      <TelemetryBar
        telemetry={telemetry}
        dataMode={dataMode}
        targetVolume={config.sweepSeedCount}
        onChangeTargetVolume={(vol) => setConfig({ ...config, sweepSeedCount: vol })}
        onToggleSweep={handleToggleSweep}
        onPauseSweep={handlePauseSweep}
        onContinueSweep={handleContinueSweep}
        onStartTerrain={handleStartTerrain}
        onStopTerrain={handleStopTerrain}
        onOpenFunnel={() => setIsFunnelOpen(true)}
        onExport={handleExport}
      />

      {/* Main 3-Column Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left: Configuration Sidebar */}
        <FilterSidebar
          config={config}
          onChangeConfig={setConfig}
          logs={logs}
          onClearLogs={() => setLogs([])}
          onResumeSweep={handleResumeSweep}
          sweepRunning={telemetry.status === 'running'}
        />

        {/* Center: Interactive Pan/Zoom Map Canvas */}
        <div className="flex-1 flex flex-col relative h-full">
          <MapCanvas
            candidate={selectedCandidate}
            dimension={dimension}
            onDimensionChange={setDimension}
            showBorders={showBorders}
            onToggleBorders={() => setShowBorders((b) => !b)}
            showBiomes={showBiomes}
            onToggleBiomes={() => setShowBiomes((b) => !b)}
            showGrid={showGrid}
            onToggleGrid={() => setShowGrid((g) => !g)}
            showRavines={showRavines}
            onToggleRavines={() => setShowRavines((r) => !r)}
            showCaves={showCaves}
            onToggleCaves={() => setShowCaves((c) => !c)}
          />
        </div>

        {/* Right: Candidate Feed & Drawer */}
        <CandidateFeed
          candidates={candidates}
          selectedCandidate={selectedCandidate}
          onSelectCandidate={setSelectedCandidate}
          onInspectCandidate={setInspectedCandidate}
          onCopyNotice={showToast}
          onClearCandidates={() => setCandidates([])}
        />
      </div>

      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-emerald-500 text-white text-xs font-bold px-4 py-2.5 rounded-lg shadow-2xl shadow-emerald-500/30 flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2 duration-150">
          <span>✓</span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* 3D Elevation / Detail Modal */}
      {inspectedCandidate && (
        <SeedDetailModal
          candidate={inspectedCandidate}
          onClose={() => setInspectedCandidate(null)}
          onCopyNotice={showToast}
        />
      )}

      {/* Search Rejection Funnel Modal */}
      {isFunnelOpen && <FunnelModal onClose={() => setIsFunnelOpen(false)} />}
    </div>
  );
}

export default App;
