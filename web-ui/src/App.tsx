import { lazy, Suspense, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type {
  SeedCandidate,
  TelemetryState,
  SearchConfig,
  Dimension,
  LaunchReceipt,
  ConnectionStatus,
  RuntimeIdentity,
  BackendStatusResponse,
} from './types';
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
import {
  requestJson,
  resolvePublicCatalogRoot,
  TimeoutError,
  calculateBackoff,
  determineConnectionStatus,
  isResponseStale,
  validStatusPayload,
  validCandidatePage,
  snapshotMismatch,
} from './utils/network';

const VALID_TELEMETRY_STATUSES: TelemetryState['status'][] = [
  'idle',
  'running',
  'paused',
  'completed',
  'bds_verifying',
  'error',
];

function SweepWorkspace({active = true}: {active?: boolean}) {
  const [config, setConfig] = useState<SearchConfig>(INITIAL_CONFIG);
  const [lastLaunch, setLastLaunch] = useState<LaunchReceipt | null>(null);
  const [preview, setPreview] = useState<{ key: string; receipt: LaunchReceipt | null; error: string }>({
    key: '',
    receipt: null,
    error: '',
  });

  const request = useMemo(() => {
    try {
      return { body: buildSweepRequest(config), error: '' };
    } catch (error) {
      return { body: null, error: error instanceof Error ? error.message : String(error) };
    }
  }, [config]);

  const previewKey = JSON.stringify(request.body);
  useEffect(() => {
    if (!request.body) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const result = await requestJson<{ ok: boolean; launch?: LaunchReceipt; error?: string }>(
          '/api/sweep/preview',
          {
            method: 'POST',
            body: await resolvePublicCatalogRoot(request.body, {signal: controller.signal}),
            timeoutMs: 5000,
            signal: controller.signal,
          }
        );
        if (controller.signal.aborted) return;
        const data = result.data;
        setPreview({
          key: previewKey,
          receipt: data?.ok ? data.launch ?? null : null,
          error: data?.ok ? '' : data?.error || 'Preview failed',
        });
      } catch (error) {
        if (!controller.signal.aborted) {
          setPreview({
            key: previewKey,
            receipt: null,
            error: error instanceof Error ? error.message : String(error),
          });
        }
      }
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [request, previewKey]);

  const [candidates, setCandidates] = useState<SeedCandidate[]>([]);
  const [candidateOffset, setCandidateOffset] = useState(0);
  const [candidateTotal, setCandidateTotal] = useState(0);
  const [candidateView,setCandidateView]=useState<'primary'|'reserve'>('primary');
  const [candidateCounts,setCandidateCounts]=useState<{primary:number;reserve:number}|null>(null);
  const candidatePageSize = 100;
  const candidateRunId = useRef<string | null | undefined>(undefined);
  const latestBackend = useRef<{ runId?: string | null; generation?: number }>({});
  const progressError = useRef<string | null>(null);
  const [candidatePageError, setCandidatePageError] = useState<string | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<SeedCandidate | null>(null);
  const [inspectedCandidate, setInspectedCandidate] = useState<SeedCandidate | null>(null);
  const [isFunnelOpen, setIsFunnelOpen] = useState<boolean>(false);

  // Freshness and connection state
  const [dataMode, setDataMode] = useState<ConnectionStatus>('connecting');
  const [lastContactTime, setLastContactTime] = useState<number | null>(null);
  const [runtimeIdentity, setRuntimeIdentity] = useState<RuntimeIdentity | null>(null);
  const consecutiveStatusFailures = useRef(0);
  const consecutivePageFailures = useRef(0);
  const hasEverConnected = useRef(false);
  const lastContactTimestampRef = useRef<number | null>(null);
  const prevModeRef = useRef<ConnectionStatus>('connecting');

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
    statusSchemaVersion: 2,
    candidatePageUrl: '/api/candidates',
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

  const applyEffectiveConfig = useCallback((effective: any, controls?: LaunchReceipt['controls']) => {
    if (!effective?.structures) return;
    const profile = (Object.keys(SEARCH_PROFILES) as SearchProfileName[]).find(
      (name) => SEARCH_PROFILES[name].revision === effective.screening_revision
    );
    if (!profile) return;
    const counts = normalizeStructureCounts({
      ...effective.structures.minimum_counts,
      ...effective.structures.nether_minimum_counts,
    });
    setConfig((previous) => ({
      ...previous,
      profile,
      playableRadiusOverworld: effective.deployment.overworld_side_blocks,
      playableRadiusNether: effective.deployment.nether_side_blocks,
      requiredStructures: Object.keys(counts),
      selectedBiomes: effective.biomes.required_families,
      maxMisses: effective.search.max_misses,
      ...(controls
        ? {
            sweepSeedCount: controls.count,
            startIndex: controls.start_index,
            openmpThreads: controls.threads,
            publicCatalogHarvest: controls.catalog_enabled||false,
            publicCatalogRoot: controls.catalog_root||previous.publicCatalogRoot,
            ...(controls.batch_size != null ? { batchSize: controls.batch_size } : {}),
          }
        : {}),
      structureFloorCounts: counts,
    }));
  }, []);

  const lastCommandKey = useRef('');
  const applyLaunch = useCallback(
    (data: any, force = false) => {
      if (!data.launch) return;
      if (force || lastCommandKey.current !== data.launch.shellCommand) {
        lastCommandKey.current = data.launch.shellCommand;
        setLastLaunch(data.launch);
        applyEffectiveConfig(data.effectiveConfig, data.launch.controls);
      }
    },
    [applyEffectiveConfig]
  );

  const prevStatusRef = useRef<string>(telemetry.status);

  // Poll real backend status with generation guard, timeout, and bounded backoff
  const pollStatus = useCallback(
    async (signal?: AbortSignal) => {
      const generation = apiGeneration.current;
      try {
        const result = await requestJson<BackendStatusResponse>('/api/sweep/status', {
          timeoutMs: 5000,
          signal,
        });
        if (signal?.aborted || isResponseStale(generation, apiGeneration.current)) {
          return;
        }
        const data = result.data;
        if (!validStatusPayload(data)) throw new Error('Backend returned an invalid status snapshot');
        if (latestBackend.current.runId !== undefined && data.runId !== undefined
            && latestBackend.current.runId !== data.runId) {
          setCandidates([]);
          setSelectedCandidate(null);
          setCandidateOffset(0);setCandidateView('primary');setCandidateCounts(null);
        }
        latestBackend.current = { runId: data.runId, generation: data.generation };
        progressError.current = data.progressReadError ?? null;

        const now = Date.now();
        consecutiveStatusFailures.current = 0;
        hasEverConnected.current = true;
        lastContactTimestampRef.current = now;
        setLastContactTime(now);

        if (prevModeRef.current === 'disconnected') {
          showToast('Backend connection restored');
        }
        const receivedMode = data.progressReadError ? 'stale' : 'live';
        prevModeRef.current = receivedMode;
        setDataMode(receivedMode);

        if (data.runtimeIdentity) {
          setRuntimeIdentity(data.runtimeIdentity);
        }
        applyLaunch(data);

        if (prevStatusRef.current === 'running' && data.status === 'completed') {
          showToast(
            `🎉 Sweep Completed! ${(data.totalScanned ?? 0).toLocaleString()} seeds scanned in ${data.elapsedSeconds ?? 0}s (${(data.seedsPerSec ?? 0).toLocaleString()} seeds/s)!`
          );
        }
        if (data.error && data.status === 'error' && prevStatusRef.current !== 'error') {
          showToast(`Sweep error: ${data.error}`);
        }
        prevStatusRef.current = data.status;

        const resolvedStatus = VALID_TELEMETRY_STATUSES.includes(data.status)
          ? data.status
          : data.status === 'running'
          ? 'running'
          : 'idle';

        if (data.status === 'running') {
          setCandidates((current) => current.filter((c) => c.provenance === 'live'));
          setSelectedCandidate((current) => (current?.provenance === 'live' ? current : null));
        }

        setTelemetry((prev) => ({
          ...prev,
          status: resolvedStatus,
          statusSchemaVersion: data.statusSchemaVersion ?? 2,
          runtimeIdentity: data.runtimeIdentity ?? prev.runtimeIdentity,
          generation: data.generation ?? prev.generation,
          lastContactTime: now,
          isStale: Boolean(data.progressReadError),
          progressReadError: data.progressReadError,
          progressUpdatedAt: data.progressUpdatedAt,
          candidatePageUrl: data.candidatePageUrl ?? prev.candidatePageUrl ?? '/api/candidates',
          seedsPerSec: data.seedsPerSec !== undefined ? data.seedsPerSec : prev.seedsPerSec,
          totalScanned: data.totalScanned !== undefined ? data.totalScanned : prev.totalScanned,
          targetCount: data.targetCount ?? prev.targetCount ?? config.sweepSeedCount,
          candidatesFound: data.candidatesFound !== undefined ? data.candidatesFound : prev.candidatesFound,
          elapsedSeconds: data.elapsedSeconds !== undefined ? data.elapsedSeconds : prev.elapsedSeconds,
          sweepProgress: data.sweepProgress !== undefined ? data.sweepProgress : prev.sweepProgress,
          memoryRssGib: data.memoryRssGib !== undefined ? data.memoryRssGib : prev.memoryRssGib,
          activeThreads: data.activeThreads !== undefined ? data.activeThreads : prev.activeThreads,
          history: data.history && data.history.length > 0 ? data.history : prev.history,
          runId: data.runId !== undefined ? data.runId : prev.runId,
        }));

        if (data.logs && data.logs.length > 0) {
          setLogs((prev) => {
            const combined = [...data.logs!, ...prev];
            return Array.from(new Set(combined)).slice(0, 50);
          });
        }
      } catch (err: any) {
        if (signal?.aborted || isResponseStale(generation, apiGeneration.current)) {
          return;
        }
        consecutiveStatusFailures.current += 1;
        const newStatus = determineConnectionStatus({
          hasEverConnected: hasEverConnected.current,
          consecutiveFailures: consecutiveStatusFailures.current,
          lastContactTimestamp: lastContactTimestampRef.current,
        });

        if (newStatus === 'disconnected' && prevModeRef.current !== 'disconnected') {
          showToast(`Backend connection lost: ${err instanceof Error ? err.message : String(err)}`);
        }
        prevModeRef.current = newStatus;
        setDataMode(newStatus);
        setTelemetry((prev) => ({ ...prev, isStale: true }));
      }
    },
    [applyLaunch, config.sweepSeedCount, showToast]
  );

  // Execute POST commands with timeout explanation and status refresh without auto-retry
  const postCommand = useCallback(
    async (path: string, payload: Record<string, unknown> | (() => Promise<Record<string, unknown>>) = {}) => {
      if (commandInFlight.current) throw new Error('Another command is still pending');
      commandInFlight.current = true;
      apiGeneration.current += 1;
      let refreshAfterCommand = false;
      let requestSent = false;
      try {
        const body = typeof payload === 'function' ? await payload() : payload;
        requestSent = true;
        const result = await requestJson<any>(path, {
          method: 'POST',
          body,
          timeoutMs: 10000,
        });
        const data = result.data;
        if (!data || data.ok !== true) {
          throw new Error(data?.error || `Command ${path} failed`);
        }
        return data;
      } catch (err: any) {
        if (err instanceof TimeoutError && requestSent) {
          // Immediately refresh status rather than auto-retrying starting jobs
          refreshAfterCommand = true;
          setDataMode('stale');
          setTelemetry(prev => ({ ...prev, isStale: true }));
          throw new Error(
            `Command POST ${path} timed out after 10s. Server outcome may be unknown; refreshing backend status rather than retrying.`
          );
        }
        throw err;
      } finally {
        commandInFlight.current = false;
        apiGeneration.current += 1;
        if (refreshAfterCommand) void pollStatus();
      }
    },
    [pollStatus]
  );

  // Candidate page loading with bounded timeout, abort on cleanup, and bounded backoff
  useEffect(() => {
    let active = true;
    let timerId: any = null;
    let controller: AbortController | null = null;
    let loading = false;

    const loadPage = async () => {
      if (!active) return;
      if (loading || commandInFlight.current) { scheduleNextPage(); return; }
      loading = true;
      const generation = apiGeneration.current;
      controller = new AbortController();

      try {
        const result = await requestJson<{
          total: number;
          primary_count?:number;reserve_count?:number;view?:'primary'|'reserve';
          candidates: SeedCandidate[];
          runId?: string | null;
          generation?: number;
        }>(`/api/candidates?limit=${candidatePageSize}&offset=${candidateOffset}&view=${candidateView}`, {
          timeoutMs: 6000,
          signal: controller.signal,
        });

        if (!active || isResponseStale(generation, apiGeneration.current)) {
          return;
        }

        const data = result.data;
        if (!validCandidatePage(data)) throw new Error('Backend returned an invalid candidate page');
        if (snapshotMismatch(data, latestBackend.current)) return;
        if((data.view!==undefined&&data.view!==candidateView)||(candidateView==='reserve'&&data.primary_count===undefined)){setCandidateView('primary');setCandidateCounts(null);setCandidateOffset(0);return;}
        setCandidateCounts(data.primary_count!==undefined&&data.reserve_count!==undefined?{primary:data.primary_count,reserve:data.reserve_count}:null);
        consecutivePageFailures.current = 0;
        setCandidatePageError(null);

        if (
          candidateRunId.current !== undefined &&
          data.runId !== undefined &&
          candidateRunId.current !== data.runId
        ) {
          candidateRunId.current = data.runId;
          if (candidateOffset !== 0) {
            setCandidateOffset(0);
            return;
          }
        } else if (candidateRunId.current === undefined && data.runId !== undefined) {
          candidateRunId.current = data.runId;
        }

        setCandidateTotal(data.total);
        if (data.total > 0 && candidateOffset >= data.total) {
          setCandidateOffset(Math.floor((data.total - 1) / candidatePageSize) * candidatePageSize);
          return;
        }

        setCandidates(data.candidates);
        setSelectedCandidate(
          (current) =>
            data.candidates.find((c: SeedCandidate) => c.id === current?.id) ??
            data.candidates[0] ??
            null
        );
      } catch (err: any) {
        if (!active || isResponseStale(generation, apiGeneration.current) || controller?.signal.aborted) {
          return;
        }
        consecutivePageFailures.current += 1;
        setCandidatePageError('Candidate list could not refresh. Showing the last loaded page; retrying.');
        // Do not flood toasts on polling failure; only show once if manual page change failed
        if (candidateOffset > 0 && consecutivePageFailures.current === 1) {
          showToast(`Failed to load page: ${err instanceof Error ? err.message : String(err)}`);
        }
      } finally {
        loading = false;
        scheduleNextPage();
      }
    };

    const scheduleNextPage = () => {
      if (!active) return;
      const delay = calculateBackoff(consecutivePageFailures.current, 3000, 10000);
      timerId = setTimeout(loadPage, delay);
    };

    void loadPage();

    return () => {
      active = false;
      if (timerId !== null) clearTimeout(timerId);
      if (controller) controller.abort();
    };
  }, [candidateOffset, candidateView, telemetry.runId, showToast]);

  // Bounded status polling loop with adaptive backoff
  useEffect(() => {
    let active = true;
    let timerId: any = null;
    let controller: AbortController | null = null;

    const scheduleNext = () => {
      if (!active) return;
      const baseInterval =
        telemetry.status === 'running' || telemetry.status === 'bds_verifying' ? 650 : 3000;
      const delay = calculateBackoff(consecutiveStatusFailures.current, baseInterval, 10000);
      timerId = setTimeout(async () => {
        if (!active || commandInFlight.current) {
          scheduleNext();
          return;
        }
        controller = new AbortController();
        await pollStatus(controller.signal);
        scheduleNext();
      }, delay);
    };

    // Initial immediate poll on mount
    const initialController = new AbortController();
    controller = initialController;
    void Promise.resolve().then(() => pollStatus(initialController.signal)).finally(() => {
      scheduleNext();
    });

    return () => {
      active = false;
      if (timerId !== null) clearTimeout(timerId);
      if (controller) controller.abort();
    };
  }, [telemetry.status, pollStatus]);

  // Freshness ages even when the browser receives no fetch completion.
  useEffect(() => {
    const timer = setInterval(() => {
      let mode = determineConnectionStatus({ hasEverConnected: hasEverConnected.current,
        consecutiveFailures: consecutiveStatusFailures.current,
        lastContactTimestamp: lastContactTimestampRef.current });
      if (progressError.current && mode === 'live') mode = 'stale';
      setDataMode(mode);
      setTelemetry(previous => previous.isStale === (mode !== 'live') ? previous
        : { ...previous, isStale: mode !== 'live' });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleToggleSweep = useCallback(async () => {
    try {
      if (telemetry.status === 'running' || telemetry.status === 'paused') {
        await postCommand('/api/sweep/stop');
        setTelemetry((prev) => ({ ...prev, status: 'idle', seedsPerSec: 0 }));
        showToast('Sweep stopped; checkpoint retained');
        return;
      }
      const data = await postCommand('/api/sweep/start', () => resolvePublicCatalogRoot(buildSweepRequest(config)));
      applyLaunch(data, true);
      setTelemetry((prev) => ({
        ...prev,
        status: 'running',
        runId: data.runId,
        totalScanned: 0,
        targetCount: config.sweepSeedCount,
        elapsedSeconds: 0,
        sweepProgress: 0,
        isStale: false,
      }));
      setDataMode('live');
      setCandidates([]);
      setSelectedCandidate(null);
      setCandidateOffset(0);
      setCandidateTotal(0);
      showToast(`Native sweep started (${config.sweepSeedCount.toLocaleString()} seeds)`);
    } catch (error) {
      showToast(`Sweep command failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }, [telemetry.status, config, showToast, postCommand, applyLaunch]);

  const handleResumeSweep = useCallback(
    async (runId: string) => {
      try {
        const data = await postCommand('/api/sweep/resume', { runId });
        applyLaunch(data, true);
        setDataMode('live');
        setTelemetry((prev) => ({ ...prev, status: 'running', isStale: false }));
        setLogs((prev) => [`Resuming saved sweep ${runId}`, ...prev]);
        showToast('Saved sweep resumed');
      } catch (error) {
        showToast(`Resume failed: ${error instanceof Error ? error.message : String(error)}`);
      }
    },
    [showToast, postCommand, applyLaunch]
  );

  const handlePauseSweep = useCallback(async () => {
    try {
      showToast('Pausing sweep: finishing active batch...');
      const data = await postCommand('/api/sweep/pause', {});
      setTelemetry((prev) => ({ ...prev, status: 'paused', seedsPerSec: 0 }));
      setLogs((prev) => [
        `Sweep checkpoint retained at ${data.scannedCount ? data.scannedCount.toLocaleString() : 'active'} seeds`,
        ...prev,
      ]);
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
      setTelemetry((prev) => ({ ...prev, status: 'running', isStale: false }));
      setLogs((prev) => [
        `Continuing sweep from seed ${data.scannedCount ? data.scannedCount.toLocaleString() : telemetry.totalScanned.toLocaleString()}...`,
        ...prev,
      ]);
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
          setLogs((prev) => [
            `[BDS] Surface observation job accepted for ${cand.id}; full Realm verification remains pending.`,
            ...prev,
          ]);
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

  // A mounted but hidden Sweep must never respond to Catalog keyboard events.
  // Keyboard Shortcuts
  useEffect(() => {
    if (!active) return;
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
  }, [active, handleToggleSweep, dimension, showToast, inspectedCandidate, isFunnelOpen]);

  return (
    <div className="flex flex-col h-[calc(100dvh-57px)] w-full bg-slate-950 text-slate-100 font-sans overflow-hidden select-none">
      {/* Top Telemetry & Controls HUD */}
      <TelemetryBar
        telemetry={telemetry}
        dataMode={dataMode}
        lastContactTime={lastContactTime}
        runtimeIdentity={runtimeIdentity}
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
          reserveSelection={candidateCounts?{...candidateCounts,view:candidateView,onChange:(view)=>{setCandidateOffset(0);setCandidateView(view);}}:undefined}
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

      {candidatePageError && (
        <div role="status" className="fixed bottom-3 right-3 z-40 max-w-xs rounded bg-amber-950 border border-amber-600 px-3 py-2 text-xs text-amber-100">
          {candidatePageError}
        </div>
      )}

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

const CatalogWorkspace = lazy(() => import('./catalog/CatalogWorkspace').then(module => ({default: module.CatalogWorkspace})));

function App() {
  const selectedTab = () => window.location.hash.startsWith('#catalog') ? 'catalog' : 'sweep';
  const [tab, setTab] = useState(selectedTab);
  const [sweepVisited, setSweepVisited] = useState(() => selectedTab() === 'sweep');
  const [catalogVisited, setCatalogVisited] = useState(() => selectedTab() === 'catalog');
  const catalogLocation = useRef('#catalog');
  useEffect(() => {
    const changed = () => {
      const next = selectedTab();
      if (next === 'catalog') {setCatalogVisited(true); catalogLocation.current = window.location.hash;}
      else setSweepVisited(true);
      setTab(next);
    };
    window.addEventListener('hashchange', changed);
    window.addEventListener('popstate', changed);
    return () => {window.removeEventListener('hashchange', changed);window.removeEventListener('popstate', changed);};
  }, []);
  return <>
    <nav aria-label="Workspace" className="flex gap-2 border-b border-slate-700 bg-slate-950 px-4 py-2">
      <a href="#sweep" aria-current={tab === 'sweep' ? 'page' : undefined} className={`rounded px-4 py-2 ${tab === 'sweep' ? 'bg-emerald-700 text-white' : 'text-slate-300'}`}>Sweep</a>
      <a href={catalogLocation.current} aria-current={tab === 'catalog' ? 'page' : undefined} className={`rounded px-4 py-2 ${tab === 'catalog' ? 'bg-emerald-700 text-white' : 'text-slate-300'}`}>Catalog <span className="text-xs opacity-70">Private pilot</span></a>
    </nav>
    <div hidden={tab !== 'sweep'}>{sweepVisited && <SweepWorkspace active={tab === 'sweep'} />}</div>
    <div hidden={tab !== 'catalog'}>{catalogVisited && <Suspense fallback={<p role="status" className="p-6">Loading Catalog…</p>}><CatalogWorkspace /></Suspense>}</div>
  </>;
}

export default App;
