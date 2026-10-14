import React, { useEffect, useRef } from 'react';

interface FunnelModalProps {
  onClose: () => void;
}

const STEPS = [
  {
    name: 'Stage 1 & 2: Native Baseline Screening',
    detail: 'Fast C screening against inland structure floors and 4-Y biome diversity lattice. Ocean Monuments & Shipwrecks are deliberately deferred from this stage. Seeds meeting these criteria qualify as Baseline Survivors.',
    evidence: 'Run counts and baseline candidate records come directly from the native sweep.',
    color: 'border-emerald-500 bg-emerald-500/10 text-emerald-400',
  },
  {
    name: 'Stage 3: Ocean Continent Terrain Pass-Through & Marine Gating',
    detail: 'A multi-resolution predictor screens the configured mainland and coastal corridor thresholds, then evaluates marine structure predictions. Actual-generation verification is separate.',
    evidence: 'Coastal geometry and marine evidence attached when backend supplies terrain pass.',
    color: 'border-cyan-500 bg-cyan-500/10 text-cyan-400',
  },
  {
    name: 'Stage 5: Authoritative BDS Docker Verification',
    detail: 'Explicit bounded Bedrock server requests can provide sampled block and surface evidence. Structure counts, portal rooms and first-player spawn require their own evidence; a terrain pass does not certify them.',
    evidence: 'A Bedrock server result is shown only when a candidate includes explicit verification evidence.',
    color: 'border-blue-500 bg-blue-500/10 text-blue-400',
  },
];

export const FunnelModal: React.FC<FunnelModalProps> = ({ onClose }) => {
  const modalRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key === 'Tab' && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && (document.activeElement === first || !modalRef.current.contains(document.activeElement))) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && (document.activeElement === last || !modalRef.current.contains(document.activeElement))) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    const timer = setTimeout(() => {
      const first = modalRef.current?.querySelector<HTMLElement>('button:not([disabled])');
      first?.focus();
    }, 0);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="funnel-modal-title"
        tabIndex={-1}
        className="bg-slate-900 border border-slate-700 rounded-xl max-w-3xl w-full overflow-hidden shadow-2xl animate-in fade-in duration-150 outline-none"
      >
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div>
            <h3 id="funnel-modal-title" className="text-lg font-bold text-white flex items-center gap-2">
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
};
