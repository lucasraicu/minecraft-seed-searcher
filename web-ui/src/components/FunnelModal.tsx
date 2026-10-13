import React from 'react';

interface FunnelModalProps {
  onClose: () => void;
}

const STEPS = [
  {
    name: 'Native seed screening',
    detail: 'Corrected v2 two-group policy. B defaults to 2 deficit categories; fatal floors and required biome families remain enforced.',
    evidence: 'Run counts and retained rows come from the live run record.',
    color: 'border-emerald-500 bg-emerald-500/10 text-emerald-400',
  },
  {
    name: 'Downstream world evidence',
    detail: 'Spawn, marine structures, terrain, and measured heights are reported only when the backend supplies evidence.',
    evidence: 'Missing evidence stays pending; it does not become a pass or a rejection here.',
    color: 'border-cyan-500 bg-cyan-500/10 text-cyan-400',
  },
  {
    name: 'Authoritative verification',
    detail: 'A Bedrock server result is shown only when a candidate includes explicit verification evidence.',
    evidence: 'No verification totals or pass rates are assumed by this preview.',
    color: 'border-blue-500 bg-blue-500/10 text-blue-400',
  },
];

export const FunnelModal: React.FC<FunnelModalProps> = ({ onClose }) => (
  <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
    <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-3xl w-full overflow-hidden shadow-2xl animate-in fade-in duration-150">
      <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <span>📊</span> Evidence Pipeline
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Live counts and verification status come from backend run records. Demo records are illustrative.
          </p>
        </div>
        <button
          onClick={onClose}
          className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white flex items-center justify-center text-sm font-bold"
          aria-label="Close evidence pipeline"
        >
          ✕
        </button>
      </div>

      <div className="p-5 space-y-3 max-h-[70vh] overflow-y-auto">
        {STEPS.map((step, index) => (
          <div key={step.name} className={`p-4 rounded-lg border ${step.color}`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono text-xs font-bold px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-white">
                {index + 1}
              </span>
              <span className="font-bold text-sm text-white">{step.name}</span>
            </div>
            <p className="text-xs text-slate-200">{step.detail}</p>
            <p className="text-[11px] text-slate-400 mt-1">{step.evidence}</p>
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
