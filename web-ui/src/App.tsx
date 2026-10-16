import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type { SeedCandidate, TelemetryState, SearchConfig, Dimension, LaunchReceipt } from './types';
import { INITIAL_CONFIG } from './mockData';
import { SEARCH_PROFILES, normalizeStructureCounts } from './constants/baselinePolicy';
import type { SearchProfileName } from './constants/baselinePolicy';
import { MapCanvas } from './components/MapCanvas';
import { CandidateFeed } from './components/CandidateFeed';
import { TelemetryBar } from './components/TelemetryBar';
import { FilterSidebar } from './components/FilterSidebar';
import { SeedDetailModal } from './components/SeedDetailModal';
import { FunnelModal } from './components/FunnelModal';
import { buildSweepRequest } from './utils/sweep';

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
  const [lastLaunch, setLastLaunch] = useState<LaunchReceipt | null>(null);
  const [preview, setPreview] = useState<{ key: string; receipt: LaunchReceipt | null; error: string }>({ key: '', receipt: null, error: '' });
  const request = useMemo(() => {
    try { return { body: buildSweepRequest(config), error: '' }; }
    catch (error) { return { body: null, error: error instanceof Error ? error.message : String(error) }; }
  }, [config]);
  const previewKey = JSON.stringify(request.body);
  useEffect(() => {
    if (!request.body) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const response = await fetch('/api/sweep/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request.body), signal: controller.signal });
        const data = await response.json();
        if (controller.signal.aborted) return;
        setPreview({ key: previewKey, receipt: data.ok ? data.launch : null, error: data.ok ? '' : data.error });
      } catch (error) {
        if (!controller.signal.aborted) setPreview({ key: previewKey, receipt: null, error: error instanceof Error ? error.message : String(error) });
      }
    }, 300);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [request, previewKey]);
  const [candidates, setCandidates] = useState<SeedCandidate[]>([]);
  const [candidateOffset, setCandidateOffset] = useState(0);
  const [candidateTotal, setCandidateTotal] = useState(0);
  const candidatePageSize = 100;
  const candidateRunId = useRef<string | null | undefined>(undefined);
  const [selectedCandidate, setSelectedCandidate] = useState<SeedCandidate | null>(null);
  const [inspectedCandidate, setInspectedCandidate] = useState<SeedCandidate | null>(null);
  const [isFunnelOpen, setIsFunnelOpen] = useState<boolean>(false);
  const [dataMode, setDataMode] = useState<'connecting' | 'live'>('connecting');

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
  const applyEffectiveConfig = useCallback((effective: any, controls?: LaunchReceipt['controls']) => {
    if (!effective?.structures) return;
    const profile = (Object.keys(SEARCH_PROFILES) as SearchProfileName[]).find((name) => SEARCH_PROFILES[name].revision === effective.screening_revision);
    if (!profile) return;
    const counts = normalizeStructureCounts({ ...effective.structures.minimum_counts, ...effective.structures.nether_minimum_counts });
    setConfig((previous) => ({ ...previous, profile,
      playableRadiusOverworld: effective.deployment.overworld_side_blocks,
      playableRadiusNether: effective.deployment.nether_side_blocks,
      requiredStructures: Object.keys(counts), selectedBiomes: effective.biomes.required_families,
      maxMisses: effective.search.max_misses,
      ...(controls ? { sweepSeedCount: controls.count, startIndex: controls.start_index,
        openmpThreads: controls.threads, ...(controls.batch_size != null ? { batchSize: controls.batch_size } : {}) } : {}),
      structureFloorCounts: counts }));
  }, []);
  const lastCommandKey = useRef('');
  const applyLaunch = useCallback((data: any, force = false) => {
    if (!data.launch) return;
    if (force || lastCommandKey.current !== data.launch.shellCommand) {
      lastCommandKey.current = data.launch.shellCommand;
      setLastLaunch(data.launch);
      applyEffectiveConfig(data.effectiveConfig, data.launch.controls);
    }
  }, [applyEffectiveConfig]);

  // On mount, load any existing candidate database from backend
  useEffect(() => {
    let active = true;
    const generation = apiGeneration.current;
    // Check system status
    fetch('/api/sweep/status')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!active || generation !== apiGeneration.current || !data) return;
        applyLaunch(data);
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
          runId: data.runId,
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
  }, [applyLaunch]);

  useEffect(() => {
    let active = true;
    let loading = false;
    const loadPage = async () => {
      if (loading || commandInFlight.current) return;
      loading = true;
      const generation = apiGeneration.current;
      try {
        const response = await fetch(`/api/candidates?limit=${candidatePageSize}&offset=${candidateOffset}`);
        if (!response.ok) throw new Error('Could not load candidate page');
        const data = await response.json();
        if (!active || generation !== apiGeneration.current) return;
        if (candidateRunId.current !== data.runId) {
          candidateRunId.current = data.runId;
          if (candidateOffset !== 0) { setCandidateOffset(0); return; }
        }
        setCandidateTotal(data.total);
        if (data.total > 0 && candidateOffset >= data.total) {
          setCandidateOffset(Math.floor((data.total - 1) / candidatePageSize) * candidatePageSize);
          return;
        }
        setCandidates(data.candidates);
        setDataMode('live');
        setSelectedCandidate((current) => data.candidates.find((c: SeedCandidate) => c.id === current?.id) ?? data.candidates[0] ?? null);
      } catch (error) {
        if (active && generation === apiGeneration.current) showToast(error instanceof Error ? error.message : String(error));
      } finally { loading = false; }
    };
    void loadPage();
    const timer = setInterval(loadPage, 3000);
    return () => { active = false; clearInterval(timer); };
  }, [candidateOffset, telemetry.runId, showToast]);

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

          applyLaunch(data);
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
          }));

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
  }, [telemetry.status, config.sweepSeedCount, config.openmpThreads, showToast, applyLaunch]);

  const handleToggleSweep = useCallback(async () => {
    try {
      if (telemetry.status === 'running' || telemetry.status === 'paused') {
        await postCommand('/api/sweep/stop');
        setTelemetry((prev) => ({ ...prev, status: 'idle', seedsPerSec: 0 }));
        showToast('Sweep stopped; checkpoint retained');
        return;
      }
      const data = await postCommand('/api/sweep/start', buildSweepRequest(config));
      applyLaunch(data, true);
      setTelemetry((prev) => ({ ...prev, status: 'running', runId: data.runId, totalScanned: 0,
        targetCount: config.sweepSeedCount, elapsedSeconds: 0, sweepProgress: 0 }));
      setDataMode('live'); setCandidates([]); setSelectedCandidate(null); setCandidateOffset(0); setCandidateTotal(0);
      showToast(`Native sweep started (${config.sweepSeedCount.toLocaleString()} seeds)`);
    } catch (error) {
      showToast(`Sweep command failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }, [telemetry.status, config, showToast, postCommand, applyLaunch]);

  const handleResumeSweep = useCallback(async (runId: string) => {
    try {
      const data = await postCommand('/api/sweep/resume', { runId });
      applyLaunch(data, true);
      setDataMode('live');
      setTelemetry((prev) => ({ ...prev, status: 'running' }));
      setLogs((prev) => [`Resuming saved sweep ${runId}`, ...prev]);
      showToast('Saved sweep resumed');
    } catch (error) {
      showToast(`Resume failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }, [showToast, postCommand, applyLaunch]);

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
      applyLaunch(data, true);
      setDataMode('live');
      setTelemetry((prev) => ({ ...prev, status: 'running' }));
      setLogs((prev) => [`Continuing sweep from seed ${data.scannedCount ? data.scannedCount.toLocaleString() : telemetry.totalScanned.toLocaleString()}...`, ...prev]);
      showToast('▶ Sweep Continued');
    } catch (error) {
      showToast(`Continue failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }, [telemetry.runId, telemetry.totalScanned, showToast, postCommand, applyLaunch]);

  const [verificationPending, setVerificationPending] = useState(false);
  const isVerifyingBDS = verificationPending || telemetry.status === 'bds_verifying';

  const handleBeginBDSParity = useCallback(
    async (targetCandidate?: SeedCandidate | null) => {
      const cand = targetCandidate || selectedCandidate || candidates[0];
      if (!cand) {
        showToast('Select a candidate first to begin BDS parity');
        return;
      }
      setVerificationPending(true);
      showToast(`🛡️ Launching BDS surface observation job for seed ${cand.seed}...`);
      setLogs((prev) => [
        `[BDS] Launching Bedrock Dedicated Server 1.26.52.3 verification for seed ${cand.seed}...`,
        ...prev,
      ]);

      try {
        const data = await postCommand('/api/bds/verify', {
          seed: cand.seed,
          candidateId: cand.id,
        });

        if (data && data.ok) {
          setTelemetry((prev) => ({ ...prev, status: 'bds_verifying' }));
          setLogs((prev) => [`[BDS] Surface observation job accepted for ${cand.id}; full Realm verification remains pending.`,...prev]);
          showToast(`BDS surface job started for ${data.points} points. Results appear after the provider finishes.`);
        } else {
          throw new Error(data?.error || 'BDS verification failed');
        }
      } catch (error) {
        showToast(`BDS Verification failed: ${error instanceof Error ? error.message : String(error)}`);
        setLogs((prev) => [
          `[BDS] Error: ${error instanceof Error ? error.message : String(error)}`,
          ...prev,
        ]);
      } finally {
        setVerificationPending(false);
      }
    },
    [selectedCandidate, candidates, showToast, postCommand]
  );

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
        onOpenFunnel={() => setIsFunnelOpen(true)}
        onExport={handleExport}
        onBeginBDSParity={() => handleBeginBDSParity(selectedCandidate)}
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
          sweepRunning={telemetry.status === 'running' || telemetry.status === 'paused' || telemetry.status === 'bds_verifying'}
          preview={preview.key === previewKey && !request.error ? preview.receipt : null}
          previewError={request.error || (preview.key === previewKey ? preview.error : '')}
          lastLaunch={lastLaunch}
          onCopyNotice={showToast}
        />

        {/* Center: Interactive Pan/Zoom Map Canvas */}
        <div className="flex-1 flex flex-col relative h-full">
          <MapCanvas
            candidate={selectedCandidate}
            profile={config.profile}
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
          pagination={{ offset: candidateOffset, total: candidateTotal, limit: candidatePageSize, onChangeOffset: setCandidateOffset }}
          selectedCandidate={selectedCandidate}
          onSelectCandidate={setSelectedCandidate}
          onInspectCandidate={setInspectedCandidate}
          onCopyNotice={showToast}
          onClearCandidates={() => setCandidates([])}
          onVerifyBDS={handleBeginBDSParity}
          isVerifyingBDS={isVerifyingBDS}
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
          onVerifyBDS={handleBeginBDSParity}
          isVerifyingBDS={isVerifyingBDS}
        />
      )}

      {/* Search Rejection Funnel Modal */}
      {isFunnelOpen && <FunnelModal onClose={() => setIsFunnelOpen(false)} />}
    </div>
  );
}

export default App;
