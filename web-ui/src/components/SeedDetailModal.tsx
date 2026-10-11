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
    if (!candidate || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Render an isometric / cross-section 3D terrain profile
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

    // Draw terrain cross-section curve
    ctx.beginPath();
    ctx.moveTo(40, seaY);

    const isIsland = candidate.terrainType === 'V1 Island';
    const points = 60;
    const xStep = (w - 80) / points;

    for (let i = 0; i <= points; i++) {
      const x = 40 + i * xStep;
      const normalized = (i - points / 2) / (points / 2); // -1 to 1

      let elevation: number;
      if (isIsland) {
        // Island profile: elevated dome in middle, underwater on sides
        const dist = Math.abs(normalized);
        if (dist > 0.6) {
          elevation = seaY + 25 * (dist - 0.6); // Underwater ocean floor
        } else {
          elevation = seaY - (40 - dist * 45) * Math.cos(dist * Math.PI * 0.5); // Peak
        }
      } else {
        // Mountain Basin profile: high peak walls on left and right, flat valley floor at sea level in center
        const dist = Math.abs(normalized);
        if (dist > 0.45) {
          elevation = seaY - 75 * Math.sin((dist - 0.45) * Math.PI * 1.5); // Jagged Peaks
        } else {
          elevation = seaY - 2; // Flat valley floor
        }
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

    // Underground structure indicator (Ancient City at -52)
    ctx.fillStyle = '#06b6d4';
    ctx.beginPath();
    ctx.arc(w * 0.5, h * 0.82, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    ctx.font = '10px monospace';
    ctx.fillText('Ancient City (Y=-52)', w * 0.5 + 12, h * 0.82 + 3);
  }, [candidate]);

  if (!candidate) return null;

  const chunkbaseUrl = `https://www.chunkbase.com/apps/seed-map#seed=${candidate.seed}&platform=bedrock_1_21`;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-2xl w-full overflow-hidden shadow-2xl animate-in fade-in duration-150">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-white">Seed Candidate Inspection</h3>
              <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono font-bold text-xs">
                Score: {candidate.score} / 100
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
              <span className="font-semibold uppercase tracking-wider">
                Elevation Cross-Section & Underground Geometry
              </span>
              <span>{candidate.terrainType}</span>
            </div>
            <div className="border border-slate-800 rounded-lg overflow-hidden shadow-inner">
              <canvas ref={canvasRef} width={600} height={200} className="w-full h-48 block" />
            </div>
          </div>

          {/* Metric Details Cards */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Diameter</span>
              <div className="text-base font-bold text-emerald-400 font-mono">
                {candidate.terrainMetrics.diameter}m
              </div>
              <span className="text-[10px] text-slate-500">Target: 250–750m</span>
            </div>

            <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Water Moat</span>
              <div className="text-base font-bold text-blue-400 font-mono">
                {(candidate.terrainMetrics.waterEnclosure * 100).toFixed(0)}%
              </div>
              <span className="text-[10px] text-slate-500">48-Ray Enclosure</span>
            </div>

            <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Build Flat Space</span>
              <div className="text-base font-bold text-amber-400 font-mono">
                {candidate.terrainMetrics.flatAreaBlocks.toLocaleString()} m²
              </div>
              <span className="text-[10px] text-slate-500">Y=63–70 Solid</span>
            </div>
          </div>

          {/* BDS Ground Truth Audit Panel */}
          <div className="p-3.5 bg-slate-950 border border-blue-900/40 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-300 flex items-center gap-1.5">
                <span>🛡️</span> BDS 1.26.52.3 Container Ground Truth
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 font-bold">
                {candidate.bdsVerified ? 'VERIFIED PASSED' : 'PENDING'}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
              <div>
                <span className="text-slate-500">Palette Agreement: </span>
                <span className="font-mono text-emerald-400 font-semibold">
                  {candidate.bdsAccuracy.paletteAgreement}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Height MAE: </span>
                <span className="font-mono text-emerald-400 font-semibold">
                  {candidate.bdsAccuracy.heightMae} blocks
                </span>
              </div>
            </div>
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
            <a
              href={chunkbaseUrl}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-lg bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 text-xs font-semibold flex items-center gap-1"
            >
              ↗ Open in Chunkbase
            </a>
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
