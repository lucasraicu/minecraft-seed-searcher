import React from 'react';

interface FunnelModalProps {
  onClose: () => void;
}

export const FunnelModal: React.FC<FunnelModalProps> = ({ onClose }) => {
  const TIERS = [
    {
      tier: 'Tier 0',
      name: 'Lower-32 Raw MT Structure Sweep',
      engine: 'Native C11 / OpenMP (SIMD)',
      input: '4,294,967,296 seeds',
      survivors: '52,100 candidates',
      rejectionRate: '99.99%',
      speed: '~1.5 Million layouts/sec',
      cost: 'Microseconds per seed',
      color: 'border-emerald-500 bg-emerald-500/10 text-emerald-400',
    },
    {
      tier: 'Tier 1',
      name: '64-bit Biome Viability & Stronghold Anchors',
      engine: 'C `cubiomes` 2D Climate Grid',
      input: '52,100 candidates',
      survivors: '2,600 candidates',
      rejectionRate: '95.0%',
      speed: '~1,200 seeds/sec',
      cost: 'Milliseconds per candidate',
      color: 'border-cyan-500 bg-cyan-500/10 text-cyan-400',
    },
    {
      tier: 'Tier 2',
      name: 'Surface Biome & Wooded Families Coverage',
      engine: 'NumPy / CFFI 2D Batching',
      input: '2,600 candidates',
      survivors: '310 candidates',
      rejectionRate: '88.1%',
      speed: '~350 candidates/sec',
      cost: 'Centiseconds per candidate',
      color: 'border-amber-500 bg-amber-500/10 text-amber-400',
    },
    {
      tier: 'Tier 3',
      name: '3D Terrain Density (V1 Island / V2 Basin)',
      engine: 'Accelerated `ss_land` (4x4 Quart + 8-block Y)',
      input: '310 candidates',
      survivors: '14 candidates',
      rejectionRate: '95.5%',
      speed: '~3.5 sec per candidate',
      cost: 'Heavy 3D Perlin math (optimized)',
      color: 'border-purple-500 bg-purple-500/10 text-purple-400',
    },
    {
      tier: 'Tier 4',
      name: 'Authoritative BDS 1.26.52.3 Ground Truth',
      engine: 'Official Bedrock Dedicated Server (Docker)',
      input: '14 candidates',
      survivors: '4 Certified Winners',
      rejectionRate: '71.4%',
      speed: '~20 sec per seed',
      cost: 'Real game engine chunk generation',
      color: 'border-blue-500 bg-blue-500/10 text-blue-400',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-3xl w-full overflow-hidden shadow-2xl animate-in fade-in duration-150">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <span>📊</span> Multi-Tier Search Rejection Funnel
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              How the algorithmic pipeline short-circuits 4.29 billion seeds into 4 certified winners.
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center text-sm font-bold"
          >
            ✕
          </button>
        </div>

        <div className="p-5 space-y-3 max-h-[70vh] overflow-y-auto">
          {TIERS.map((t, index) => (
            <div
              key={t.tier}
              className={`p-3.5 rounded-lg border ${t.color} flex flex-col gap-2 relative`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-white">
                    {t.tier}
                  </span>
                  <span className="font-bold text-sm text-white">{t.name}</span>
                </div>
                <span className="font-mono text-xs font-bold">
                  {t.rejectionRate} culled
                </span>
              </div>

              <div className="grid grid-cols-4 gap-2 text-xs">
                <div>
                  <span className="text-[10px] text-slate-400 block">Input Pool:</span>
                  <span className="font-mono text-slate-200 font-semibold">{t.input}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">Surviving Output:</span>
                  <span className="font-mono text-emerald-400 font-semibold">{t.survivors}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">Throughput:</span>
                  <span className="font-mono text-slate-200">{t.speed}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">Engine Layer:</span>
                  <span className="truncate text-slate-300">{t.engine}</span>
                </div>
              </div>

              {index < TIERS.length - 1 && (
                <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 w-6 h-6 rounded-full bg-slate-800 border border-slate-700 text-[10px] flex items-center justify-center text-slate-400 z-10">
                  ↓
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="p-4 border-t border-slate-800 bg-slate-950/80 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-bold"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
