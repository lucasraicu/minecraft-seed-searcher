import React, { useEffect, useRef } from 'react';
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
        // Coastal shoreline rise / beach
        const t = (normalized - 0.28) / 0.07;
        elevation = seaY + 28 * (1 - t) - 4 * t;
      } else if (normalized < 0.52) {
        // River Highway channel dip
        const t = (normalized - 0.35) / 0.17;
        const riverDip = Math.sin(t * Math.PI) * 16;
        elevation = seaY - 12 + riverDip;
      } else if (normalized < 0.75) {
        // Inland Plateau / Plains / Stronghold hub
        elevation = seaY - 18 + Math.sin(normalized * 12) * 4;
      } else {
        // Mountain Cliffs / Stony Peaks ridge (>Y120)
        const t = (normalized - 0.75) / 0.25;
        elevation = seaY - 18 - Math.sin(t * Math.PI * 0.9) * 58;
      }

      ctx.lineTo(x, elevation);
    }

    ctx.lineTo(w - 40, h - 20);
    ctx.lineTo(40, h - 20);
    ctx.closePath();

    // Terrain ground gradient fill
    const groundGrad = ctx.createLinearGradient(0, seaY - 80, 0, h);
    groundGrad.addColorStop(0, '#15803d'); // Grass top
    groundGrad.addColorStop(0.3, '#78350f'); // Dirt
    groundGrad.addColorStop(0.7, '#334155'); // Deepslate stone
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
  }, [candidate]);

  if (!candidate) return null;

  const chunkbaseUrl = candidate.chunkbaseUrl;
  const spawn = candidate.spawnPoint;
  const spawnDist = candidate.spawnDistance;
  const terrainMetrics = candidate.terrainMetrics;
  const isDemo = candidate.provenance === 'reference';

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-2xl w-full overflow-hidden shadow-2xl animate-in fade-in duration-150">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-white">Seed Candidate Inspection</h3>
              <span className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] ${
                isDemo
                  ? 'bg-purple-500/20 text-purple-300'
                  : candidate.provenance === 'live'
                    ? 'bg-emerald-500/20 text-emerald-300'
                    : 'bg-slate-700 text-slate-300'
              }`}>
                {isDemo ? 'DEMO SAMPLE' : candidate.provenance === 'live' ? 'LIVE' : 'SOURCE UNKNOWN'}
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono font-bold text-xs">
                {candidate.score === null ? 'Unrated' : `Score: ${candidate.score} / 100`}
              </span>
            </div>
            <p className="text-xs font-mono text-slate-400 mt-0.5">Seed: {candidate.seed}</p>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center text-sm font-bold"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
          {/* 3D Elevation Cross-Section Canvas */}
          <div>
            <div className="flex justify-between items-center text-xs mb-1.5 text-slate-400">
              <span className="font-semibold uppercase tracking-wider">Terrain Profile</span>
              <span className="font-semibold text-slate-400">
                {candidate.terrainPassed === true
                  ? 'Terrain passed'
                  : candidate.terrainPassed === false
                    ? 'Terrain failed'
                    : 'Unknown / pending evidence'}
              </span>
            </div>
            <div className="border border-slate-800 rounded-lg overflow-hidden shadow-inner">
              {isDemo ? (
                <>
                  <canvas ref={canvasRef} width={600} height={200} className="w-full h-48 block" />
                  <p className="px-3 py-1.5 bg-purple-950/40 text-[10px] text-purple-300">
                    Illustrative demo profile; this is not measured terrain evidence.
                  </p>
                </>
              ) : (
                <div className="h-48 flex items-center justify-center bg-slate-950 text-xs text-slate-400">
                  No measured terrain profile / pending evidence
                </div>
              )}
            </div>
          </div>

          {/* Metric Details Cards */}
          <div className="grid grid-cols-4 gap-2.5">
            <div className="p-2.5 bg-slate-950/70 border border-slate-800 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Spawn Offset</span>
              <div
                className={`text-sm font-bold font-mono ${
                  spawnDist != null && spawnDist <= 50
                    ? 'text-emerald-400'
                    : spawnDist != null && spawnDist <= 100
                    ? 'text-cyan-400'
                    : 'text-amber-400'
                }`}
              >
                {spawnDist == null ? 'Unknown / pending evidence' : `${spawnDist} ${candidate.spawnDistanceUnits ?? 'blocks'}`}
              </div>
              <span className="text-[9px] text-slate-500">
                {spawn ? `(${spawn[0]}, ${spawn[1]})` : 'Coordinates pending'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-950/70 border border-slate-800 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Mainland Share</span>
              <div className="text-sm font-bold text-emerald-400 font-mono">
                {terrainMetrics?.mainlandFraction == null
                  ? 'Unknown / pending evidence'
                  : `${(terrainMetrics.mainlandFraction * 100).toFixed(0)}%`}
              </div>
              <span className="text-[9px] text-slate-500">
                {terrainMetrics?.mainlandFraction == null ? 'Not measured' : 'Measured value'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-950/70 border border-slate-800 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Ocean Edge</span>
              <div
                className={`text-sm font-bold font-mono truncate ${
                  terrainMetrics?.oceanEdge ? 'text-blue-400' : 'text-slate-400'
                }`}
              >
                {terrainMetrics?.oceanEdge ?? 'Unknown / pending evidence'}
              </div>
              <span className="text-[9px] text-slate-500">
                {terrainMetrics?.oceanEdge ? 'Measured terrain evidence' : 'Not measured'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-950/70 border border-slate-800 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Flat Build Land</span>
              <div className="text-sm font-bold text-amber-400 font-mono truncate">
                {terrainMetrics?.flatAreaBlocks == null
                  ? 'Unknown / pending evidence'
                  : `${(terrainMetrics.flatAreaBlocks / 1000).toFixed(0)}k m²`}
              </div>
              <span className="text-[9px] text-slate-500">
                {terrainMetrics?.flatAreaBlocks == null ? 'Not measured' : 'Backend-reported area'}
              </span>
            </div>
          </div>

          {/* Observed Structures with Euclidean Distances */}
          <div>
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5 font-semibold uppercase tracking-wider">
              <span>Recorded Structures ({candidate.structures.length})</span>
              <span>Distance evidence</span>
            </div>
            <div className="max-h-44 overflow-y-auto space-y-1 bg-slate-950/50 p-2 rounded-lg border border-slate-800 text-xs">
              {candidate.structures.map((s) => {
                const dist = s.distanceToHub;
                return (
                  <div
                    key={s.id}
                    className="flex items-center justify-between py-1 px-2 rounded hover:bg-slate-800/60 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span>{s.icon}</span>
                      <span className="text-slate-200 font-medium">{s.name}</span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        ({s.dimension === 'nether' ? 'Nether' : 'Overworld'})
                      </span>
                    </div>
                    <div className="flex items-center gap-3 font-mono text-[11px]">
                      <span className="text-slate-400">X:{s.x} Z:{s.z}</span>
                      <span className="text-emerald-400 font-bold w-32 text-right">
                        {dist == null ? 'Unknown / pending evidence' : `${dist} ${s.distanceUnits ?? 'blocks'}`}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Subterranean Features: Ravines & Cave Clusters */}
          {((candidate.ravines && candidate.ravines.length > 0) ||
            (candidate.caveClusters && candidate.caveClusters.length > 0)) && (
            <div>
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5 font-semibold uppercase tracking-wider">
                <span>Underground & Terrain Chasms</span>
                <span className="text-[10px] text-amber-400 font-mono">
                  {candidate.ravines?.length || 0} Ravines (
                  {candidate.ravines?.filter((r) => r.giant).length || 0} Mega) •{' '}
                  {candidate.caveClusters?.length || 0} Cave Clusters
                </span>
              </div>
              <div className="grid grid-cols-2 gap-1.5 bg-slate-950/50 p-2 rounded-lg border border-slate-800 text-xs">
                {candidate.ravines?.slice(0, 4).map((r) => (
                  <div
                    key={r.id}
                    className="flex items-center justify-between py-1 px-2 rounded bg-slate-900/60 border border-slate-800/80"
                  >
                    <span className="flex items-center gap-1.5 text-slate-200">
                      <span>🌋</span>
                      <span className="font-medium">{r.giant ? 'Mega Ravine' : 'Ravine'}</span>
                      {r.underwater && (
                        <span className="text-[9px] text-cyan-400">(Trench)</span>
                      )}
                    </span>
                    <span className="font-mono text-[10px] text-slate-400">
                      X:{r.x} Z:{r.z} (Y={r.y ?? 'unknown'})
                    </span>
                  </div>
                ))}
                {candidate.caveClusters?.map((c) => (
                  <div
                    key={c.id}
                    className="flex items-center justify-between py-1 px-2 rounded bg-slate-900/60 border border-slate-800/80"
                  >
                    <span className="flex items-center gap-1.5 text-slate-200">
                      <span>{c.icon}</span>
                      <span className="font-medium truncate max-w-[110px]">{c.name}</span>
                    </span>
                    <span className="font-mono text-[10px] text-emerald-400 font-bold">
                      Y={c.y ?? 'unknown'}
                    </span>
                  </div>
                ))}
              </div>
                  {isDemo && candidate.ravines?.some((r) => r.giant && Math.hypot(r.x, r.z) <= 200) && (
                <div className="mt-2 p-2 bg-orange-950/30 border border-orange-500/40 rounded-lg flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 text-orange-300 font-semibold">
                    <span>🌋</span>
                    <span>Jackpot Bonus: Mega Ravine Hub (+35 pts)</span>
                  </span>
                  <span className="text-[10px] text-orange-200/80 font-mono">
                    Directly intersects ≤200m origin hub
                  </span>
                </div>
              )}
            </div>
          )}

          {/* BDS Ground Truth Audit Panel */}
          <div className="p-3.5 bg-slate-950 border border-blue-900/40 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-300 flex items-center gap-1.5">
                <span>🛡️</span> Authoritative Bedrock Verification
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 font-bold">
                {candidate.bdsVerified === true ? 'VERIFIED' : 'Unknown / pending evidence'}
              </span>
            </div>

            {candidate.bdsVerified === true && candidate.bdsAccuracy ? (
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                <div>
                  <span className="text-slate-500">Palette Agreement: </span>
                  <span className="font-mono text-emerald-400 font-semibold">
                    {candidate.bdsAccuracy.paletteAgreement ?? 'Not reported'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Height MAE: </span>
                  <span className="font-mono text-emerald-400 font-semibold">
                    {candidate.bdsAccuracy.heightMae == null
                      ? 'Not reported'
                      : `${candidate.bdsAccuracy.heightMae} blocks`}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-400">
                No authoritative Bedrock verification evidence is attached to this record.
              </p>
            )}
          </div>
        </div>

        {/* Modal Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <div className="flex gap-2">
            <button
              onClick={() => {
                navigator.clipboard.writeText(candidate.seed);
                onCopyNotice(`Copied Seed: ${candidate.seed}`);
              }}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold"
            >
              📋 Copy Seed
            </button>
            {chunkbaseUrl && <a
              href={chunkbaseUrl}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-lg bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 text-xs font-semibold flex items-center gap-1"
            >
              ↗ Open in Chunkbase
            </a>}
          </div>

          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
