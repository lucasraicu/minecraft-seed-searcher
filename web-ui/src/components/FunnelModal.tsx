import React from 'react';

interface FunnelModalProps {
  onClose: () => void;
}

export const FunnelModal: React.FC<FunnelModalProps> = ({ onClose }) => {
  const TIERS = [
    {
      tier: 'Stage 1',
      name: 'Origin-Fixed Structure RNG Screening (13 Floors)',
      engine: 'Native C11 OpenMP batch (origin-fixed-2048-v1)',
      input: '10,000,000 seeds',
      survivors: '14,200 seeds',
      rejectionRate: '99.86%',
      speed: '44,972 seeds/sec (Intel Xeon 32T)',
      cost: '22 µs per seed',
      color: 'border-emerald-500 bg-emerald-500/10 text-emerald-400',
    },
    {
      tier: 'Stage 2',
      name: 'Biome Lattice & River Highway Connectivity',
      engine: '2D Multi-Noise Climate Lattice',
      input: '14,200 seeds',
      survivors: '420 candidates',
      rejectionRate: '97.04%',
      speed: '~1,450 seeds/sec',
      cost: '0.69 ms per candidate',
      color: 'border-cyan-500 bg-cyan-500/10 text-cyan-400',
    },
    {
      tier: 'Stage 3',
      name: 'Downstream Spawn Gate (≤100m) & Coastal Terrain',
      engine: '3D Density Perlin & Origin Spawn Evaluation',
      input: '420 candidates',
      survivors: '286 finalists',
      rejectionRate: '31.7% (Filters ocean-center spawns)',
      speed: 'Zero cost during Stage 1 screening',
      cost: 'Evaluated on finalists only',
      color: 'border-purple-500 bg-purple-500/10 text-purple-400',
    },
    {
      tier: 'Stage 4',
      name: '3D Coastal Continent (70–80%) & 320m Ocean Edge',
      engine: '4×4 Quart Land Reuse & 8-block Y caching',
      input: '286 finalists',
      survivors: '12 certified continents',
      rejectionRate: '95.8%',
      speed: '~3.2 sec per candidate',
      cost: 'Dense 3D height field audit',
      color: 'border-amber-500 bg-amber-500/10 text-amber-400',
    },
    {
      tier: 'Stage 5',
      name: 'Authoritative BDS 1.26.52.3 Ground Truth',
      engine: 'Official Bedrock Dedicated Server (Docker)',
      input: '12 finalists',
      survivors: '4 Certified Realm Worlds',
      rejectionRate: '66.7%',
      speed: '~18 sec per candidate',
      cost: 'Real game engine world generation',
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
              How the algorithmic pipeline short-circuits millions of Bedrock seeds down to certified continent winners.
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
                  {t.rejectionRate}
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
