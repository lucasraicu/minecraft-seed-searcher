import React, { useState, useEffect, useRef } from 'react';
import type { SeedCandidate } from '../types';

interface SeedDetailModalProps {
  candidate: SeedCandidate | null;
  onClose: () => void;
  onCopyNotice: (msg: string) => void;
}

export const SeedDetailModal: React.FC<SeedDetailModalProps> = ({
  candidate,
  onClose,
  onCopyNotice,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const modalRef = useRef<HTMLDivElement | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'structures' | 'biomes' | 'terrain' | 'underground'>('overview');
  const [structureDimFilter, setStructureDimFilter] = useState<'all' | 'overworld' | 'nether'>('all');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === 'Tab' && modalRef.current) {
        const focusableElements = modalRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement || !modalRef.current.contains(document.activeElement)) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement || !modalRef.current.contains(document.activeElement)) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    const timer = setTimeout(() => {
      if (modalRef.current) {
        const firstFocusable = modalRef.current.querySelector<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        firstFocusable?.focus();
      }
    }, 0);

    return () => {
      clearTimeout(timer);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose]);

  useEffect(() => {
    if (!candidate || candidate.provenance !== 'reference' || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Cross-section 3D terrain profile of Coastal Continent
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, w, h);

    // Sky gradient
    const skyGrad = ctx.createLinearGradient(0, 0, 0, h * 0.7);
    skyGrad.addColorStop(0, '#020617');
    skyGrad.addColorStop(1, '#1e293b');
    ctx.fillStyle = skyGrad;
    ctx.fillRect(0, 0, w, h * 0.65);

    // Sea Level reference line (Y=63)
    const seaY = h * 0.58;
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(40, seaY);
    ctx.lineTo(w - 40, seaY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = '#38bdf8';
    ctx.font = '10px monospace';
    ctx.fillText('Sea Level (Y=63)', w - 130, seaY - 6);

    // Water fill below sea level
    ctx.fillStyle = 'rgba(14, 116, 144, 0.35)';
    ctx.fillRect(40, seaY, w - 80, h * 0.35);

    // Draw Coastal Continent cross-section curve
    ctx.beginPath();
    ctx.moveTo(40, seaY);

    const points = 80;
    const xStep = (w - 80) / points;

    for (let i = 0; i <= points; i++) {
      const x = 40 + i * xStep;
      const normalized = i / points; // 0 (West Ocean) to 1 (East Continent)

      let elevation: number;
      if (normalized < 0.28) {
        // West 320m Open Ocean trench
        elevation = seaY + 28 - Math.sin(normalized * Math.PI * 3) * 6;
      } else if (normalized < 0.35) {
        // Coastal Shore beach shelf (rising through sea level)
        const t = (normalized - 0.28) / 0.07;
        elevation = seaY + 28 - t * 38;
      } else if (normalized < 0.72) {
        // Mainland continental plate (~70-80% plateau, elevation Y=68 to 82)
        const t = (normalized - 0.35) / 0.37;
        elevation = seaY - 10 - Math.sin(t * Math.PI) * 14;
      } else if (normalized < 0.88) {
        // Mountain Ridge Barrier (+45m relief up to Y=125)
        const t = (normalized - 0.72) / 0.16;
        elevation = seaY - 24 - Math.sin(t * Math.PI) * 42;
      } else {
        // East drop-off
        const t = (normalized - 0.88) / 0.12;
        elevation = seaY - 24 + t * 32;
      }

      ctx.lineTo(x, elevation);
    }

    ctx.lineTo(w - 40, h);
    ctx.lineTo(40, h);
    ctx.closePath();

    // Fill cross section ground
    const groundGrad = ctx.createLinearGradient(0, seaY - 40, 0, h);
    groundGrad.addColorStop(0, '#15803d'); // Grass surface
    groundGrad.addColorStop(0.12, '#854d0e'); // Dirt
    groundGrad.addColorStop(0.35, '#334155'); // Stone
    groundGrad.addColorStop(0.7, '#1e293b'); // Deepslate
    groundGrad.addColorStop(1, '#020617'); // Bedrock
    ctx.fillStyle = groundGrad;
    ctx.fill();

    ctx.strokeStyle = '#22c55e';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Ancient City at Y=-52 indicator
    ctx.fillStyle = '#06b6d4';
    ctx.beginPath();
    ctx.arc(w * 0.62, h * 0.82, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.font = '10px monospace';
    ctx.fillText('Ancient City (Y=-52)', w * 0.62 + 10, h * 0.82 + 3);

    // Ravine Fissure indicator in cross-section
    ctx.strokeStyle = '#ea580c';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(w * 0.48, seaY - 14);
    ctx.lineTo(w * 0.48, seaY + 28);
    ctx.stroke();
    ctx.fillStyle = '#f97316';
    ctx.font = '9px monospace';
    ctx.fillText('🌋 Ravine (Y=44)', w * 0.48 + 5, seaY + 14);

    // Lush Cave Cavern at Y=-48
    ctx.fillStyle = '#10b981';
    ctx.beginPath();
    ctx.arc(w * 0.52, h * 0.82, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#a7f3d0';
    ctx.font = '9px monospace';
    ctx.fillText('🌿 Lush Cavern (Y=-48)', w * 0.52 + 8, h * 0.82 + 3);

    // River Highway channel label
    ctx.fillStyle = '#38bdf8';
    ctx.fillText('River Channel (Y=62)', w * 0.38, seaY + 16);

    // West ocean shelf label
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('320m Ocean Trench', 50, seaY + 40);
  }, [candidate, activeTab]);

  if (!candidate) return null;

  const chunkbaseUrl = candidate.chunkbaseUrl;
  const spawn = candidate.spawnPoint;
  const spawnDist = candidate.spawnDistance;
  const terrainMetrics = candidate.terrainMetrics;
  const isDemo = candidate.provenance === 'reference';
  const stronghold = candidate.strongholdAnchor;
  const center = candidate.evaluationCenter ?? [0, 0];
  const isHubOrigin = center[0] === 0 && center[1] === 0;

  const overworldStructures = candidate.structures.filter((s) => s.dimension === 'overworld');
  const netherStructures = candidate.structures.filter((s) => s.dimension === 'nether');
  const marineStructures = candidate.structures.filter((s) => s.type === 'monument' || s.type === 'shipwreck');

  const displayedStructures = candidate.structures.filter((s) => {
    if (structureDimFilter === 'overworld') return s.dimension === 'overworld';
    if (structureDimFilter === 'nether') return s.dimension === 'nether';
    return true;
  });

  const tpCommand = spawn
    ? `/tp @p ${Math.round(spawn[0])} ~ ${Math.round(spawn[1])}`
    : stronghold
    ? `/tp @p ${Math.round(stronghold[0])} ~ ${Math.round(stronghold[1])}`
    : `/tp @p 0 ~ 0`;

  const copyText = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      onCopyNotice(`Copied ${label}: ${text}`);
    } catch (err) {
      onCopyNotice(`Failed to copy: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-5"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="seed-modal-title"
        tabIndex={-1}
        className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-5xl w-full max-h-[90vh] flex flex-col overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-150 outline-none"
      >
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 bg-slate-950/90 flex items-center justify-between shrink-0">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 id="seed-modal-title" className="text-lg font-bold text-white flex items-center gap-1.5">
                <span>🌱</span>
                <span>Expanded Seed Candidate Report</span>
              </h3>
              <span
                className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] border ${
                  isDemo
                    ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                    : candidate.provenance === 'live'
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : 'bg-slate-700 text-slate-300 border-slate-600'
                }`}
              >
                {isDemo ? 'DEMO SAMPLE' : candidate.provenance === 'live' ? '⚡ LIVE' : 'SOURCE UNKNOWN'}
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono font-bold text-xs border border-emerald-500/30">
                {candidate.score === null ? 'Unrated' : `Score: ${candidate.score} pts`}
              </span>
              <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 font-mono text-[10px] border border-cyan-500/30">
                Candidate Evidence
              </span>
              {candidate.rankingTier != null && (
                <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 font-mono text-[10px] border border-amber-500/30">
                  Ranking Tier #{candidate.rankingTier}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs font-mono text-slate-400 mt-1 flex-wrap">
              <span>Seed: <strong className="text-emerald-300 font-bold select-all">{candidate.seed}</strong></span>
              {candidate.discoveredAt && <span>Discovered: {candidate.discoveredAt}</span>}
              {candidate.screeningRevision && (
                <span className="text-slate-500">Screening Revision: {candidate.screeningRevision}</span>
              )}
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center text-sm font-bold transition-colors shrink-0"
            title="Close expanded view (Esc)"
          >
            ✕
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="px-5 py-2.5 bg-slate-950/60 border-b border-slate-800/80 flex items-center gap-1.5 overflow-x-auto shrink-0 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'overview'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30 font-bold'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <span>🧭</span>
            <span>Strategic Overview</span>
          </button>
          <button
            onClick={() => setActiveTab('structures')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'structures'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30 font-bold'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <span>🏰</span>
            <span>Structure Catalog ({candidate.structures.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('biomes')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'biomes'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30 font-bold'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <span>🗺️</span>
            <span>Biomes &amp; Witnesses ({candidate.biomes?.length || Object.keys(candidate.biomeWitnesses || {}).length || 0})</span>
          </button>
          <button
            onClick={() => setActiveTab('terrain')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'terrain'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30 font-bold'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <span>🌊</span>
            <span>Terrain &amp; Continents</span>
          </button>
          <button
            onClick={() => setActiveTab('underground')}
            className={`px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'underground'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30 font-bold'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <span>🌋</span>
            <span>Caves &amp; Ravines ({(candidate.ravines?.length || 0) + (candidate.caveClusters?.length || 0)})</span>
          </button>
        </div>

        {/* Modal Scrollable Content */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1">
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-4">
              {/* Strategic Anchors & Key Coordinates Banner */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* 1. Stronghold Anchor */}
                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-semibold uppercase tracking-wider flex items-center gap-1">
                      <span>🏰</span> Stronghold Anchor
                    </span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 font-mono font-bold">
                      {stronghold ? 'Pinned' : 'Pending'}
                    </span>
                  </div>
                  <div className="text-sm font-bold font-mono text-emerald-400">
                    {stronghold ? `X: ${stronghold[0]}, Z: ${stronghold[1]}` : 'None reported'}
                  </div>
                  <p className="text-[10px] text-slate-500">
                    Anchor structure used for radial deployment &amp; geometry evaluation
                  </p>
                </div>

                {/* 2. World Spawn */}
                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-semibold uppercase tracking-wider flex items-center gap-1">
                      <span>🧭</span> Player Spawn
                    </span>
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold ${
                        spawnDist != null && spawnDist <= 50
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : spawnDist != null && spawnDist <= 100
                          ? 'bg-cyan-500/20 text-cyan-300'
                          : 'bg-amber-500/20 text-amber-300'
                      }`}
                    >
                      {spawnDist != null ? `${spawnDist} blocks` : 'Pending'}
                    </span>
                  </div>
                  <div className="text-sm font-bold font-mono text-cyan-400">
                    {spawn ? `X: ${spawn[0]}, Z: ${spawn[1]}` : 'Coordinates pending'}
                  </div>
                  <p className="text-[10px] text-slate-500">
                    {candidate.spawnEvidence?.source?.kind
                      ? `Bedrock spawn calculation (${candidate.spawnEvidence.source.kind})`
                      : 'Authentic Bedrock player spawn position'}
                  </p>
                </div>

                {/* 3. Evaluation Center */}
                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-semibold uppercase tracking-wider flex items-center gap-1">
                      <span>🎯</span> Evaluation Center
                    </span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 font-mono font-bold">
                      {center[0] === 0 && center[1] === 0 ? 'Origin Hub' : 'Custom Center'}
                    </span>
                  </div>
                  <div className="text-sm font-bold font-mono text-indigo-300">
                    X: {center[0]}, Z: {center[1]}
                  </div>
                  <p className="text-[10px] text-slate-500">
                    Center origin for 2048-block Continental search footprint
                  </p>
                </div>

                {/* 4. Qualification & Terrain Status */}
                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="font-semibold uppercase tracking-wider flex items-center gap-1">
                      <span>🌊</span> Terrain Pass
                    </span>
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold ${
                        candidate.terrainPassed === true || candidate.terrainStatus === 'passed'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                          : candidate.terrainStatus === 'near_miss'
                          ? 'bg-amber-500/25 text-amber-300 border border-amber-500/50'
                          : candidate.terrainPassed === false || candidate.terrainStatus === 'failed'
                          ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {candidate.terrainPassed === true || candidate.terrainStatus === 'passed'
                        ? 'PASSED'
                        : candidate.terrainStatus === 'near_miss'
                        ? 'NEAR MISS'
                        : candidate.terrainPassed === false || candidate.terrainStatus === 'failed'
                        ? 'FAILED'
                        : 'PENDING'}
                    </span>
                  </div>
                  <div className="text-sm font-bold font-mono text-white truncate">
                    {candidate.terrainType ?? (candidate.terrainPassed ? 'Ocean Continent' : 'Baseline Survivor')}
                  </div>
                  <p className="text-[10px] text-slate-500">
                    {candidate.terrainPassed === true || candidate.terrainStatus === 'passed'
                      ? 'Promoted to Ocean Continent finalist'
                      : candidate.terrainStatus === 'near_miss'
                      ? `Near Miss: ${candidate.terrainGeometryScore ? Math.round(candidate.terrainGeometryScore) + ' pts' : 'High'} geometry score`
                      : candidate.terrainStatus === 'failed'
                      ? 'Did not meet strict continental geometry thresholds'
                      : 'Baseline Stage 1 survivor awaiting terrain verification'}
                  </p>
                </div>
              </div>

              {/* Quick Summary Counts Cards */}
              <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <span>📊</span>
                    <span>Structure &amp; Feature Inventory Summary</span>
                  </h4>
                  <span className="text-[10px] font-mono text-emerald-400">
                    {candidate.structures.length} Total Structures Recorded
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 text-center text-xs font-mono">
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">🏡</span>
                    <span className="text-slate-400 text-[10px] block">Villages</span>
                    <span className="text-amber-400 font-bold">{candidate.structures.filter((s) => s.type === 'village').length}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">⚔️</span>
                    <span className="text-slate-400 text-[10px] block">Trial Chambers</span>
                    <span className="text-yellow-400 font-bold">{candidate.structures.filter((s) => s.type === 'trial_chamber').length}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">🏙️</span>
                    <span className="text-slate-400 text-[10px] block">Ancient Cities</span>
                    <span className="text-cyan-400 font-bold">{candidate.structures.filter((s) => s.type === 'ancient_city').length}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">🏯</span>
                    <span className="text-slate-400 text-[10px] block">Fortresses</span>
                    <span className="text-red-400 font-bold">{candidate.structures.filter((s) => s.type === 'fortress').length}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">🐖</span>
                    <span className="text-slate-400 text-[10px] block">Bastions</span>
                    <span className="text-orange-400 font-bold">{candidate.structures.filter((s) => s.type === 'bastion').length}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">🏛️</span>
                    <span className="text-slate-400 text-[10px] block">Monuments</span>
                    <span className="text-blue-400 font-bold">{candidate.structures.filter((s) => s.type === 'monument').length}</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded-lg border border-slate-800">
                    <span className="text-base block">⛵</span>
                    <span className="text-slate-400 text-[10px] block">Shipwrecks</span>
                    <span className="text-sky-400 font-bold">{candidate.structures.filter((s) => s.type === 'shipwreck').length}</span>
                  </div>
                </div>
              </div>

              {/* Predicted Stronghold Rings */}
              {candidate.predictedStrongholds && candidate.predictedStrongholds.length > 0 && (
                <div className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white flex items-center gap-1.5">
                      <span>🏰</span> Predicted Stronghold Rings ({candidate.predictedStrongholds.length})
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">Bedrock Stronghold Generation</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    {candidate.predictedStrongholds.map((coords, i) => (
                      <div
                        key={i}
                        className="p-2 bg-slate-900 rounded-lg border border-slate-800 flex items-center justify-between text-xs font-mono"
                      >
                        <span className="text-slate-400">Ring #{i + 1}</span>
                        <span className="text-emerald-400 font-bold">X: {coords[0]}, Z: {coords[1]}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* BDS Ground Truth Audit Panel */}
              <div className="p-3.5 bg-slate-950 border border-blue-900/40 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-blue-300 flex items-center gap-1.5">
                    <span>🛡️</span> Bedrock Dedicated Server (BDS) Certification
                  </span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                      candidate.bdsVerified === true
                        ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {candidate.bdsVerified === true ? 'VERIFIED' : 'Pending Verification'}
                  </span>
                </div>
                {candidate.bdsVerified === true && candidate.bdsAccuracy ? (
                  <div className="grid grid-cols-3 gap-2 text-xs text-slate-300 pt-1 font-mono">
                    <div className="p-2 bg-slate-900/80 rounded border border-slate-800">
                      <span className="text-slate-500 block text-[10px]">Palette Agreement</span>
                      <span className="text-emerald-400 font-bold text-sm">
                        {candidate.bdsAccuracy.paletteAgreement ?? 'Unavailable'}
                      </span>
                    </div>
                    <div className="p-2 bg-slate-900/80 rounded border border-slate-800">
                      <span className="text-slate-500 block text-[10px]">Height MAE</span>
                      <span className="text-cyan-400 font-bold text-sm">
                        {candidate.bdsAccuracy.heightMae != null ? `${candidate.bdsAccuracy.heightMae} blocks` : 'Unavailable'}
                      </span>
                    </div>
                    <div className="p-2 bg-slate-900/80 rounded border border-slate-800">
                      <span className="text-slate-500 block text-[10px]">Settled Columns</span>
                      <span className="text-white font-bold text-sm">
                        {candidate.bdsAccuracy.settledColumns != null ? `${candidate.bdsAccuracy.settledColumns}` : 'N/A'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">
                    BDS ground-truth verification audit confirms runtime voxel blocks against official Mojang bedrock server binary when activated.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: FULL STRUCTURE INVENTORY */}
          {activeTab === 'structures' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-1.5 text-xs font-semibold">
                  <span className="text-slate-400">Filter Dimension:</span>
                  <button
                    onClick={() => setStructureDimFilter('all')}
                    className={`px-2.5 py-1 rounded transition-colors ${
                      structureDimFilter === 'all'
                        ? 'bg-slate-700 text-white font-bold'
                        : 'bg-slate-800/60 text-slate-400 hover:text-white'
                    }`}
                  >
                    All ({candidate.structures.length})
                  </button>
                  <button
                    onClick={() => setStructureDimFilter('overworld')}
                    className={`px-2.5 py-1 rounded transition-colors ${
                      structureDimFilter === 'overworld'
                        ? 'bg-emerald-600/30 text-emerald-300 font-bold border border-emerald-500/40'
                        : 'bg-slate-800/60 text-slate-400 hover:text-white'
                    }`}
                  >
                    Overworld ({overworldStructures.length})
                  </button>
                  <button
                    onClick={() => setStructureDimFilter('nether')}
                    className={`px-2.5 py-1 rounded transition-colors ${
                      structureDimFilter === 'nether'
                        ? 'bg-red-600/30 text-red-300 font-bold border border-red-500/40'
                        : 'bg-slate-800/60 text-slate-400 hover:text-white'
                    }`}
                  >
                    Nether ({netherStructures.length})
                  </button>
                </div>
                <span className="text-xs font-mono text-slate-400">
                  Showing {displayedStructures.length} of {candidate.structures.length} structures
                </span>
              </div>

              {/* Full Uncompressed Structures Table */}
              <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950/70">
                <div className="overflow-x-auto max-h-[460px]">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900/90 text-slate-400 font-semibold uppercase text-[10px] tracking-wider border-b border-slate-800 sticky top-0 z-10 backdrop-blur">
                      <tr>
                        <th className="py-2.5 px-3">Structure</th>
                        <th className="py-2.5 px-3">Dimension</th>
                        <th className="py-2.5 px-3 font-mono">X</th>
                        <th className="py-2.5 px-3 font-mono">Y</th>
                        <th className="py-2.5 px-3 font-mono">Z</th>
                        <th className="py-2.5 px-3 text-right">Dist to (0,0)</th>
                        {!isHubOrigin && (
                          <>
                            <th className="py-2.5 px-3 text-right">Dist to Hub</th>
                            <th className="py-2.5 px-3 text-right">Dist to Spawn</th>
                          </>
                        )}
                        <th className="py-2.5 px-3 text-center">Status</th>
                        <th className="py-2.5 px-3 text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {displayedStructures.map((s) => {
                        const isMarine = s.type === 'monument' || s.type === 'shipwreck';
                        const distOrigin = Math.round(s.distanceToOrigin ?? Math.hypot(s.x, s.z));
                        const distHub = s.distanceToHub != null ? Math.round(s.distanceToHub) : null;
                        const distSpawn = s.distanceToSpawn != null
                          ? Math.round(s.distanceToSpawn)
                          : spawn != null
                          ? Math.round(s.dimension === 'nether' ? Math.hypot(s.x - spawn[0] / 8, s.z - spawn[1] / 8) : Math.hypot(s.x - spawn[0], s.z - spawn[1]))
                          : null;
                        return (
                          <tr key={s.id} className="hover:bg-slate-800/40 transition-colors">
                            <td className="py-2 px-3 font-medium text-white flex items-center gap-2">
                              <span className="text-sm">{s.icon}</span>
                              <span>{s.name}</span>
                              {isMarine && (
                                <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                                  Marine
                                </span>
                              )}
                            </td>
                            <td className="py-2 px-3">
                              <span
                                className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                                  s.dimension === 'nether'
                                    ? 'bg-red-500/10 text-red-300 border border-red-500/30'
                                    : 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30'
                                }`}
                              >
                                {s.dimension === 'nether' ? 'Nether' : 'Overworld'}
                              </span>
                            </td>
                            <td className="py-2 px-3 font-mono text-emerald-400 font-bold">{s.x}</td>
                            <td className="py-2 px-3 font-mono text-slate-400">{s.y ?? '~'}</td>
                            <td className="py-2 px-3 font-mono text-emerald-400 font-bold">{s.z}</td>
                            <td className="py-2 px-3 font-mono text-right text-cyan-300 font-semibold">
                              {distOrigin}b
                            </td>
                            {!isHubOrigin && (
                              <>
                                <td className="py-2 px-3 font-mono text-right text-slate-300 font-semibold">
                                  {distHub != null ? `${distHub}b` : `${distOrigin}b`}
                                </td>
                                <td className="py-2 px-3 font-mono text-right text-emerald-300 font-semibold">
                                  {distSpawn != null ? `${distSpawn}b` : '—'}
                                </td>
                              </>
                            )}
                            <td className="py-2 px-3 text-center">
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                                {s.evidenceStatus ?? 'VERIFIED'}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-center">
                              <button
                                onClick={() => copyText(`/tp @p ${s.x} ${s.y ?? '~'} ${s.z}`, `${s.name} /tp`)}
                                className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-mono transition-colors"
                                title="Copy teleport command"
                              >
                                /tp
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: BIOMES & WITNESSES */}
          {activeTab === 'biomes' && (
            <div className="space-y-4">
              {/* Biome Sampling Header */}
              <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-1.5">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-1.5">
                    <span>🗺️</span>
                    <span>Bedrock World-Lattice Biome Evidence</span>
                  </h4>
                  <span className="text-[10px] font-mono text-cyan-400">
                    Lattice: World • Sample Height: Y=63 • Spacing: 64 blocks
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Screened through native C11 OpenMP Bedrock generator sampling. Biome witnesses record exact coordinates where the predictor detected required families during screening.
                </p>
              </div>

              {/* Biome Witness Coordinate Table */}
              {candidate.biomeWitnesses && Object.keys(candidate.biomeWitnesses).length > 0 && (
                <div className="space-y-2">
                  <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Predicted Biome Witness Coordinates
                  </h5>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                    {Object.entries(candidate.biomeWitnesses).map(([biomeName, coord]) => {
                      const coordArr = Array.isArray(coord) ? coord : coord?.coordinate;
                      if (!Array.isArray(coordArr) || coordArr.length < 2) return null;
                      return (
                        <div
                          key={biomeName}
                          className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between text-xs"
                        >
                          <div className="flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shrink-0" />
                            <span className="font-semibold text-white capitalize">
                              {biomeName.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <div className="flex items-center gap-1 font-mono text-[11px] text-emerald-400">
                            <span>X:{coordArr[0]}</span>
                            <span>Z:{coordArr.length >= 3 ? coordArr[2] : coordArr[1]}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Detected Biomes Catalog */}
              <div className="space-y-2">
                <h5 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Detected Continental Biomes ({candidate.biomes?.length || 0})
                </h5>
                {candidate.biomes && candidate.biomes.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {candidate.biomes.map((biome, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-xs font-medium text-emerald-300 flex items-center gap-1.5 shadow-sm"
                      >
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        <span className="capitalize">{biome.replace(/_/g, ' ')}</span>
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl text-center text-xs text-slate-400">
                    Full biome lattice sampled dynamically via <code className="text-emerald-400 font-mono">/api/candidate/biome-grid</code> on map canvas.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: TERRAIN & CONTINENTS */}
          {activeTab === 'terrain' && (
            <div className="space-y-4">
              {/* 3D Elevation Cross-Section Canvas */}
              <div>
                <div className="flex justify-between items-center text-xs mb-1.5 text-slate-400">
                  <span className="font-semibold uppercase tracking-wider">Coastal Continent Cross-Section Elevation (Y=-64 to Y=128)</span>
                  <span className="font-semibold text-slate-400">
                    {candidate.terrainPassed === true || candidate.terrainStatus === 'passed'
                      ? '✓ Terrain Passed'
                      : candidate.terrainStatus === 'near_miss'
                      ? `🎯 Near Miss (${candidate.terrainGeometryScore ? Math.round(candidate.terrainGeometryScore) + ' pts' : '50+ pts'})`
                      : candidate.terrainPassed === false || candidate.terrainStatus === 'failed'
                      ? '✕ Terrain Failed'
                      : 'Unknown / pending evidence'}
                  </span>
                </div>
                <div className="border border-slate-800 rounded-xl overflow-hidden shadow-inner bg-slate-950">
                  {isDemo ? (
                    <>
                      <canvas ref={canvasRef} width={750} height={220} className="w-full h-52 block" />
                      <p className="px-3 py-1.5 bg-purple-950/40 text-[10px] text-purple-300 border-t border-purple-900/40">
                        Reference baseline profile illustrating 320m ocean trench, mainland plateau, and mountain ridge barrier.
                      </p>
                    </>
                  ) : (
                    <div className="h-52 flex flex-col items-center justify-center text-xs text-slate-400 p-4 text-center space-y-1.5">
                      <span className="text-2xl">
                        {candidate.terrainPassed === true || candidate.terrainStatus === 'passed' ? '🌊' : candidate.terrainStatus === 'near_miss' ? '🎯' : '🏔️'}
                      </span>
                      <span className="font-bold text-white">
                        {candidate.terrainPassed === true || candidate.terrainStatus === 'passed'
                          ? 'V1 Coastal Continent Screened'
                          : candidate.terrainStatus === 'near_miss'
                          ? `Near Miss Formation (${candidate.terrainGeometryScore ? Math.round(candidate.terrainGeometryScore) + ' pts' : '50+ pts'})`
                          : candidate.terrainStatus === 'failed'
                          ? 'Geometry Requirements Not Met'
                          : 'Live Measured Terrain Verification'}
                      </span>
                      <span className="text-[11px] text-slate-400 max-w-md">
                        {candidate.terrainPassed === true || candidate.terrainStatus === 'passed'
                          ? 'V1 Coastal Continent passed geometry screening with 32 adaptive rays, sampled mainland fraction, and ocean trench.'
                          : candidate.terrainStatus === 'near_miss'
                          ? 'This candidate achieved a high-scoring continental formation with extensive contiguous mainland and ocean proximity, falling just shy of strict requirements.'
                          : candidate.terrainStatus === 'failed'
                          ? 'Did not meet strict geometry screening thresholds.'
                          : 'Baseline candidate verified in Stages 1 & 2 screening. Full terrain raycast evaluation is pending or scheduled.'}
                      </span>
                      {candidate.terrainReasons && candidate.terrainReasons.length > 0 && (
                        <div className="p-2 bg-amber-950/40 border border-amber-800/40 rounded-lg max-w-lg text-[10px] text-amber-300 font-mono text-left">
                          <span className="font-bold uppercase tracking-wider block text-amber-400 mb-0.5">Unmet Thresholds:</span>
                          <ul className="list-disc list-inside space-y-0.5">
                            {candidate.terrainReasons.map((r, i) => (
                              <li key={i}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Metric Details Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block">Mainland Share</span>
                  <div className="text-base font-bold text-emerald-400 font-mono mt-0.5">
                    {terrainMetrics?.mainlandFraction == null
                      ? 'Pending'
                      : `${(terrainMetrics.mainlandFraction * 100).toFixed(1)}%`}
                  </div>
                  <span className="text-[9px] text-slate-500">Target: 70% – 80% contiguous land</span>
                </div>

                <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block">Ocean Trench</span>
                  <div className="text-base font-bold text-blue-400 font-mono mt-0.5 truncate">
                    {terrainMetrics?.oceanEdge ?? 'Pending'}
                  </div>
                  <span className="text-[9px] text-slate-500">Western ocean boundary buffer</span>
                </div>

                <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block">Flat Build Land</span>
                  <div className="text-base font-bold text-amber-400 font-mono mt-0.5">
                    {terrainMetrics?.flatAreaBlocks == null
                      ? 'Pending'
                      : `${(terrainMetrics.flatAreaBlocks / 1000).toFixed(0)}k m²`}
                  </div>
                  <span className="text-[9px] text-slate-500">Low-slope building territory</span>
                </div>

                <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block">River Highway</span>
                  <div className="text-base font-bold text-cyan-400 font-mono mt-0.5 truncate">
                    {terrainMetrics?.riverCorridor ?? 'Pending'}
                  </div>
                  <span className="text-[9px] text-slate-500">≥400m continuous navigable channel</span>
                </div>
              </div>

              {/* Marine Structure Section */}
              <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <span>⛵</span> Marine Structures ({marineStructures.length} Recorded)
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold border border-blue-500/30">
                    Status: {candidate.marineStatus ?? 'DEFERRED'}
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Ocean Monuments and Shipwrecks are deferred from Stage 1 Baseline screening to avoid premature pruning. Marine predictions are evaluated after coastal geometry screening; actual verification remains a separate evidence stage.
                </p>
              </div>
            </div>
          )}

          {/* TAB 5: UNDERGROUND CAVES & RAVINES */}
          {activeTab === 'underground' && (
            <div className="space-y-4">
              {/* Ravines Section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-300 font-semibold uppercase tracking-wider">
                  <span className="flex items-center gap-1.5">
                    <span>🌋</span> Measured Ravine Chasms ({candidate.ravines?.length || 0})
                  </span>
                  <span className="text-[10px] font-mono text-amber-400">
                    {candidate.ravines?.filter((r) => r.giant).length || 0} Mega Ravines
                  </span>
                </div>
                {candidate.ravines && candidate.ravines.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {candidate.ravines.map((r) => (
                      <div
                        key={r.id}
                        className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-lg">🌋</span>
                          <div>
                            <span className="font-bold text-white block">
                              {r.giant ? 'Mega Ravine' : 'Standard Ravine'}
                            </span>
                            <span className="text-[10px] text-slate-400">
                              Length: {r.length}m • Width factor: {r.thick}
                              {r.underwater && ' • Trench (underwater)'}
                            </span>
                          </div>
                        </div>
                        <div className="text-right font-mono text-[11px]">
                          <span className="text-amber-400 font-bold block">X: {r.x}, Z: {r.z}</span>
                          <span className="text-slate-500">Y={r.y ?? '~'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl text-center text-xs text-slate-400">
                    No ravine fissures recorded for this candidate.
                  </div>
                )}
              </div>

              {/* Cave Clusters Section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-300 font-semibold uppercase tracking-wider">
                  <span className="flex items-center gap-1.5">
                    <span>🌿</span> Subterranean Cave Clusters ({candidate.caveClusters?.length || 0})
                  </span>
                  <span className="text-[10px] font-mono text-emerald-400">
                    Lush Caves • Deep Dark • Dripstone
                  </span>
                </div>
                {candidate.caveClusters && candidate.caveClusters.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    {candidate.caveClusters.map((c) => (
                      <div
                        key={c.id}
                        className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-base">{c.icon}</span>
                          <span className="font-semibold text-white">{c.name}</span>
                        </div>
                        <span className="font-mono text-[11px] text-emerald-400 font-bold">
                          Y={c.y ?? '~'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl text-center text-xs text-slate-400">
                    Cave cluster inventory requires manual cave sampling activation.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/90 flex items-center justify-between shrink-0 flex-wrap gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => copyText(candidate.seed, 'Seed')}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              <span>📋</span>
              <span>Copy Seed</span>
            </button>
            <button
              onClick={() => copyText(tpCommand, 'Teleport Command')}
              className="px-3 py-1.5 rounded-lg bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-300 border border-emerald-500/40 text-xs font-semibold flex items-center gap-1.5 transition-colors font-mono"
            >
              <span>🧭</span>
              <span>{tpCommand}</span>
            </button>
            {chunkbaseUrl && (
              <a
                href={chunkbaseUrl}
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1.5 rounded-lg bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <span>↗</span>
                <span>Open in Chunkbase</span>
              </a>
            )}
          </div>

          <button
            onClick={onClose}
            className="px-5 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold transition-colors shadow-md shadow-emerald-500/20"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
