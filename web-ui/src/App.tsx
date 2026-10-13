import { useState, useEffect, useRef } from 'react';
import type { SeedCandidate, TelemetryState, SearchConfig, Dimension } from './types';
import { INITIAL_CONFIG, MOCK_CANDIDATES } from './mockData';
import { MapCanvas } from './components/MapCanvas';
import { CandidateFeed } from './components/CandidateFeed';
import { TelemetryBar } from './components/TelemetryBar';
import { FilterSidebar } from './components/FilterSidebar';
import { SeedDetailModal } from './components/SeedDetailModal';
import { FunnelModal } from './components/FunnelModal';

function App() {
  const [config, setConfig] = useState<SearchConfig>(INITIAL_CONFIG);
  const [candidates, setCandidates] = useState<SeedCandidate[]>(MOCK_CANDIDATES);
  const [selectedCandidate, setSelectedCandidate] = useState<SeedCandidate | null>(MOCK_CANDIDATES[0]);
  const [inspectedCandidate, setInspectedCandidate] = useState<SeedCandidate | null>(null);
  const [isFunnelOpen, setIsFunnelOpen] = useState<boolean>(false);

  // Map display settings
  const [dimension, setDimension] = useState<Dimension>('overworld');
  const [showBorders, setShowBorders] = useState<boolean>(true);
  const [showBiomes, setShowBiomes] = useState<boolean>(true);
  const [showGrid, setShowGrid] = useState<boolean>(true);
  const [showRavines, setShowRavines] = useState<boolean>(true);
  const [showCaves, setShowCaves] = useState<boolean>(true);

  // Toast feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Live Telemetry state
  const [telemetry, setTelemetry] = useState<TelemetryState>({
    status: 'idle',
    seedsPerSec: 0,
    totalScanned: 0,
    targetCount: INITIAL_CONFIG.sweepSeedCount,
    candidatesFound: MOCK_CANDIDATES.length,
    elapsedSeconds: 0,
    currentStage: 'Stage 1: Origin-Fixed Structure RNG Screening',
    memoryRssGib: 3.8,
    activeThreads: 32,
    sweepProgress: 0,
    history: [0, 0, 0, 0, 0, 0, 0, 0],
  });

  // Console Logs
  const [logs, setLogs] = useState<string[]>([
    'Initialized C11 bridge kernel with OpenMP 32 threads on Intel Xeon W-2191B',
    'Target policy: origin-fixed-2048-v1 (Overworld 2048x2048 / Nether 1024x1024)',
    'Loaded 13 blueprint structure floors & 70–80% Coastal Continent terrain spec',
    'Stage 3 downstream spawn symmetry gate active: spawn <= 100m from (0,0)',
    'Ready. Click "Start Sweep" to execute real native seed search on your computer.',
  ]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // On mount, load any existing candidate database from backend
  useEffect(() => {
    fetch('/api/candidates')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.candidates && data.candidates.length > 0) {
          setCandidates(data.candidates);
          setSelectedCandidate(data.candidates[0]);
        }
      })
      .catch(() => {});

    // Check system status
    fetch('/api/sweep/status')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.status === 'running') {
          setTelemetry((prev) => ({
            ...prev,
            status: 'running',
            totalScanned: data.totalScanned || 0,
            targetCount: data.targetCount || config.sweepSeedCount,
            seedsPerSec: data.seedsPerSec || 0,
            elapsedSeconds: data.elapsedSeconds || 0,
            sweepProgress: data.sweepProgress || 0,
            history: data.history || prev.history,
          }));
        }
      })
      .catch(() => {});
  }, []);

  const prevStatusRef = useRef<string>(telemetry.status);

  // Poll real backend for sweep status
  useEffect(() => {
    const pollInterval = telemetry.status === 'running' ? 650 : 3000;

    const timer = setInterval(() => {
      fetch('/api/sweep/status')
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (!data) return;

          // Detect completion
          if (prevStatusRef.current === 'running' && data.status === 'completed') {
            showToast(
              `🎉 Sweep Completed! ${data.totalScanned.toLocaleString()} seeds scanned in ${data.elapsedSeconds}s (${data.seedsPerSec.toLocaleString()} seeds/s)!`
            );
          }
          prevStatusRef.current = data.status;

          setTelemetry((prev) => ({
            ...prev,
            status: data.status === 'running' ? 'running' : 'idle',
            seedsPerSec: data.seedsPerSec || 0,
            totalScanned: data.totalScanned || 0,
            targetCount: data.targetCount || config.sweepSeedCount,
            candidatesFound: data.candidatesFound || prev.candidatesFound,
            elapsedSeconds: data.elapsedSeconds || 0,
            sweepProgress: data.sweepProgress || 0,
            memoryRssGib: data.memoryRssGib || prev.memoryRssGib,
            activeThreads: data.activeThreads || (data.status === 'running' ? config.openmpThreads : 0),
            history: data.history && data.history.length > 0 ? data.history : prev.history,
            runId: data.runId,
          }));

          if (data.candidates && data.candidates.length > 0) {
            setCandidates(data.candidates);
            if (!selectedCandidate) {
              setSelectedCandidate(data.candidates[0]);
            }
          }

          if (data.logs && data.logs.length > 0) {
            setLogs((prev) => {
              const combined = [...data.logs, ...prev];
              return Array.from(new Set(combined)).slice(0, 50);
            });
          }
        })
        .catch(() => {});
    }, pollInterval);

    return () => clearInterval(timer);
  }, [telemetry.status, config.sweepSeedCount, config.openmpThreads, selectedCandidate]);

  const handleToggleSweep = () => {
    if (telemetry.status === 'running') {
      // Abort active sweep
      fetch('/api/sweep/stop', { method: 'POST' })
        .then(() => {
          setTelemetry((prev) => ({ ...prev, status: 'idle', seedsPerSec: 0 }));
          setLogs((prev) => ['Sweep aborted by user via Web UI', ...prev]);
          showToast('Sweep Stopped');
        })
        .catch((err) => {
          showToast(`Error stopping sweep: ${err}`);
        });
    } else {
      // Start real sweep
      setLogs((prev) => [
        `Spawning native C11 sweep on computer: ${config.sweepSeedCount.toLocaleString()} seeds across ${config.openmpThreads} OpenMP threads...`,
        ...prev,
      ]);
      setTelemetry((prev) => ({
        ...prev,
        status: 'running',
        totalScanned: 0,
        targetCount: config.sweepSeedCount,
        elapsedSeconds: 0,
        sweepProgress: 0,
      }));

      fetch('/api/sweep/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          count: config.sweepSeedCount,
          threads: config.openmpThreads,
          batchSize: config.batchSize,
          maxMisses: config.maxMisses,
          structureFloors: config.structureFloorCounts,
          requiredStructures: config.requiredStructures,
        }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.ok) {
            showToast(`🚀 Native OpenMP Sweep Started (${config.sweepSeedCount.toLocaleString()} seeds)`);
          } else {
            showToast(`Failed to start: ${data.error}`);
            setTelemetry((prev) => ({ ...prev, status: 'idle' }));
          }
        })
        .catch((err) => {
          showToast(`Error starting sweep: ${err}`);
          setTelemetry((prev) => ({ ...prev, status: 'idle' }));
        });
    }
  };

  const handleExport = () => {
    const dataStr =
      'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(candidates, null, 2));
    const dl = document.createElement('a');
    dl.setAttribute('href', dataStr);
    dl.setAttribute('download', `minecraft-seeds-${Date.now()}.json`);
    dl.click();
    showToast('Exported surviving candidates to JSON');
  };

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
      if (e.code === 'Space') {
        e.preventDefault();
        handleToggleSweep();
      } else if (e.key.toLowerCase() === 'd') {
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
  }, [telemetry.status, dimension, config]);

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 font-sans overflow-hidden select-none">
      {/* Top Telemetry & Controls HUD */}
      <TelemetryBar
        telemetry={telemetry}
        onToggleSweep={handleToggleSweep}
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
