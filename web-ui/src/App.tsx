import { useState, useEffect, useRef, useCallback } from 'react';
import type { SeedCandidate, TelemetryState, SearchConfig, Dimension } from './types';
import { INITIAL_CONFIG } from './mockData';
import { SEARCH_PROFILES, getSearchProfile } from './constants/baselinePolicy';
import type { SearchProfileName } from './constants/baselinePolicy';
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
  const [candidates, setCandidates] = useState<SeedCandidate[]>([]);
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
  const applyEffectiveConfig = useCallback((effective: any) => {
    if (!effective?.structures) return;
    const counts = { ...effective.structures.minimum_counts, ...effective.structures.nether_minimum_counts };
    if (counts.desert_pyramid != null) counts.pyramid = counts.desert_pyramid;
    const profile = (Object.keys(SEARCH_PROFILES) as SearchProfileName[]).find((name) => SEARCH_PROFILES[name].revision === effective.screening_revision);
    setConfig((previous) => ({ ...previous, ...(profile ? { profile } : {}),
      playableRadiusOverworld: effective.deployment?.overworld_side_blocks ?? previous.playableRadiusOverworld,
      playableRadiusNether: effective.deployment?.nether_side_blocks ?? previous.playableRadiusNether,
      structureFloorCounts: { ...previous.structureFloorCounts, ...counts } }));
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
      const policy = getSearchProfile(config.profile);
      const counts: Record<string, number> = {};
      for (const [key, defaultIdeal] of Object.entries(policy.counts)) {
        if (key === 'pyramid') continue; // UI alias maps to the canonical API key below.
        const ideal = config.structureFloorCounts[key === 'desert_pyramid' ? 'pyramid' : key];
        if (!Number.isInteger(ideal) || ideal < 0 || ideal > 64) throw new Error(`${key}: enter a whole count from 0 to 64`);
        const floor = config.profile === 'dynamic1664' && key !== 'stronghold' ? policy.floors[key] : policy.flexible.includes(key) ? policy.floors[key] : undefined;
        if (floor == null && ideal !== defaultIdeal) throw new Error(`${key}: the selected policy fixes this target at ${defaultIdeal}`);
        if (floor != null && ideal < floor) throw new Error(`${key}: the active policy requires at least ${floor}`);
        if (ideal !== defaultIdeal) counts[key] = ideal;
      }
      const data = await postCommand('/api/sweep/start', {
        count: config.sweepSeedCount, startIndex: config.startIndex, threads: config.openmpThreads,
        batchSize: config.batchSize, maxMisses: config.maxMisses, counts, profile: config.profile,
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
          sweepRunning={telemetry.status === 'running'}
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
