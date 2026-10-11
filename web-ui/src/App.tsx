import { useState, useEffect } from 'react';
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

  // Toast feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Live Telemetry state
  const [telemetry, setTelemetry] = useState<TelemetryState>({
    status: 'idle',
    seedsPerSec: 0,
    totalScanned: 1420500,
    candidatesFound: MOCK_CANDIDATES.length,
    elapsedSeconds: 42,
    currentStage: 'Tier 0: Lower-32 MT Structure Sweep',
    memoryRssGib: 4.2,
    activeThreads: 36,
    sweepProgress: 32.4,
    history: [1420000, 1450000, 1435000, 1480000, 1475000, 1510000, 1495000, 1520000],
  });

  // Console Logs
  const [logs, setLogs] = useState<string[]>([
    'Initialized C11 bridge kernel with 16 Python workers + OpenMP',
    'Allocated pinned SeedContext memory pool (25 GiB target / 30 GiB max)',
    'Loaded schema-5 search boundary: Overworld 2688x2688 / Nether 1024x1024',
    'Lower-32 raw MT sweep adapter ready: Villages, Fortresses, Bastions, Ancient Cities',
    'BDS container fixture initialized on bedrock-verification-poc:1.26.52.3',
  ]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Telemetry loop when sweeping
  useEffect(() => {
    let timer: number;
    if (telemetry.status === 'running') {
      timer = setInterval(() => {
        setTelemetry((prev) => {
          const delta = Math.floor(Math.random() * 80000) - 40000;
          const currentSpeed = Math.max(1200000, Math.min(1600000, prev.seedsPerSec + delta || 1480000));
          const newTotal = prev.totalScanned + Math.round(currentSpeed / 2);
          const nextHistory = [...prev.history.slice(1), currentSpeed];

          return {
            ...prev,
            seedsPerSec: currentSpeed,
            totalScanned: newTotal,
            elapsedSeconds: prev.elapsedSeconds + 1,
            history: nextHistory,
            memoryRssGib: Number((4.1 + Math.random() * 0.3).toFixed(1)),
          };
        });

        // Occasionally discover a mock candidate
        if (Math.random() > 0.88) {
          const randomSeed = Math.floor(Math.random() * 9000000000000000) - 4500000000000000;
          const newScore = Number((91 + Math.random() * 8).toFixed(1));
          const newCand: SeedCandidate = {
            id: `cand-${Date.now()}`,
            seed: String(randomSeed),
            score: newScore,
            strongholdAnchor: [
              Math.floor(Math.random() * 1200) - 600,
              Math.floor(Math.random() * 1200) - 600,
            ],
            terrainType: Math.random() > 0.5 ? 'V1 Island' : 'V2 Mountain Basin',
            terrainMetrics: {
              diameter: Math.floor(Math.random() * 300) + 350,
              waterEnclosure: Number((0.85 + Math.random() * 0.14).toFixed(2)),
              flatAreaBlocks: Math.floor(Math.random() * 150000) + 120000,
              elevationRange: [63, 120],
            },
            structures: [
              {
                id: `s-${Date.now()}-1`,
                type: 'stronghold',
                name: 'Stronghold Portal',
                x: 180,
                z: -120,
                y: 32,
                dimension: 'overworld',
                icon: '🏰',
                color: '#10b981',
                viable: true,
              },
              {
                id: `s-${Date.now()}-2`,
                type: 'ancient_city',
                name: 'Ancient City',
                x: 240,
                z: 60,
                y: -52,
                dimension: 'overworld',
                icon: '🏙️',
                color: '#06b6d4',
                viable: true,
              },
              {
                id: `s-${Date.now()}-3`,
                type: 'fortress',
                name: 'Nether Fortress',
                x: 20,
                z: -15,
                y: 58,
                dimension: 'nether',
                icon: '🏯',
                color: '#ef4444',
                viable: true,
              },
              {
                id: `s-${Date.now()}-4`,
                type: 'bastion',
                name: 'Bastion Remnant',
                x: 45,
                z: 22,
                y: 65,
                dimension: 'nether',
                icon: '🐖',
                color: '#d97706',
                viable: true,
              },
            ],
            biomes: ['Mushroom Fields', 'Warm Ocean', 'Jungle'],
            bdsVerified: newScore > 96,
            bdsAccuracy: {
              paletteAgreement: '100% (64/64 probes)',
              heightMae: 0.9,
              settledColumns: 16,
            },
            discoveredAt: new Date().toLocaleTimeString(),
          };

          setCandidates((prev) => [newCand, ...prev]);
          setLogs((prev) => [
            `[Hit] Discovered candidate seed ${newCand.seed} (Score ${newCand.score})`,
            ...prev.slice(0, 40),
          ]);
        }
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [telemetry.status]);

  const handleToggleSweep = () => {
    if (telemetry.status === 'running') {
      setTelemetry((prev) => ({ ...prev, status: 'paused', seedsPerSec: 0 }));
      setLogs((prev) => ['Sweep paused by user', ...prev]);
      showToast('Sweep Paused');
    } else {
      setTelemetry((prev) => ({
        ...prev,
        status: 'running',
        seedsPerSec: 1450000,
      }));
      setLogs((prev) => [
        'Sweep started across 4,294,967,296 lower-32 candidate layouts',
        ...prev,
      ]);
      showToast('Sweep Started (C11 OpenMP Engine Active)');
    }
  };

  const handleExport = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(candidates, null, 2));
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
  }, [telemetry.status, dimension]);

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
        <FilterSidebar config={config} onChangeConfig={setConfig} logs={logs} />

        {/* Center: Interactive Pan/Zoom Map Canvas */}
        <div className="flex-1 flex flex-col relative h-full">
          {/* Quick Layer Toggles Toolbar */}
          <div className="absolute top-4 right-4 z-20 flex items-center gap-1.5 bg-slate-900/90 backdrop-blur border border-slate-700/80 rounded-lg p-1 shadow-xl">
            <button
              onClick={() => setShowBorders((b) => !b)}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-all ${
                showBorders ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'
              }`}
              title="Toggle Playable Boundaries (Press B)"
            >
              Bounds
            </button>
            <button
              onClick={() => setShowBiomes((b) => !b)}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-all ${
                showBiomes ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'
              }`}
              title="Toggle Biome Terrain Shading"
            >
              Terrain
            </button>
            <button
              onClick={() => setShowGrid((g) => !g)}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-all ${
                showGrid ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'
              }`}
              title="Toggle Coordinate Grid (Press G)"
            >
              Grid
            </button>
          </div>

          <MapCanvas
            candidate={selectedCandidate}
            dimension={dimension}
            onDimensionChange={setDimension}
            showBorders={showBorders}
            showBiomes={showBiomes}
            showGrid={showGrid}
          />
        </div>

        {/* Right: Candidate Feed & Drawer */}
        <CandidateFeed
          candidates={candidates}
          selectedCandidate={selectedCandidate}
          onSelectCandidate={setSelectedCandidate}
          onInspectCandidate={setInspectedCandidate}
          onCopyNotice={showToast}
        />
      </div>

      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-emerald-500 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-2xl shadow-emerald-500/30 flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2 duration-150">
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
