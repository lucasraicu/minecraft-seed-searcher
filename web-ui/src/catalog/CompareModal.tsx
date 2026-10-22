import { useDialogFocus } from './useDialogFocus';
import { useEffect } from 'react';
import type { CatalogCandidate } from './types';
import { featureLabel } from './constants';

interface CompareModalProps {
  candidates: CatalogCandidate[];
  isOpen: boolean;
  onClose: () => void;
  onRemove: (candidate: CatalogCandidate) => void;
  onClearAll: () => void;
  onInspect: (candidate: CatalogCandidate) => void;
}

export function CompareModal({
  candidates,
  isOpen,
  onClose,
  onRemove,
  onClearAll,
  onInspect,
}: CompareModalProps) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  useDialogFocus(isOpen);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="compare-modal-title"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-5xl bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden flex flex-col my-8 max-h-[90vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-950 border-b border-slate-800">
          <div>
            <h2 id="compare-modal-title" className="text-base font-bold text-slate-100 flex items-center gap-2">
              <span className="text-emerald-400">Seed Comparison</span>
              <span className="text-xs font-normal text-slate-400">({candidates.length} of 4 max)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Side-by-side evaluation of authoritative catalog rankings and layout parameters
            </p>
          </div>
          <div className="flex items-center gap-3">
            {candidates.length > 0 && (
              <button
                type="button"
                onClick={onClearAll}
                className="text-xs text-slate-400 hover:text-rose-400 transition-colors"
              >
                Clear all
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Close seed comparison dialog"
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Comparison Grid */}
        <div className="flex-1 overflow-x-auto p-6">
          {candidates.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-sm">
              No seeds selected for comparison. Click "Compare" on any candidate card to add up to 4 seeds.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 min-w-[700px]">
              {candidates.map(c => {
                const [lox, loz, hix, hiz] = c.bounds || [0, 0, 0, 0];
                return (
                  <div
                    key={`${c.world_id}:${c.layout_id}`}
                    className="flex flex-col bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-3"
                  >
                    {/* Seed Header */}
                    <div className="flex items-start justify-between gap-1">
                      <div className="min-w-0 flex-1">
                        <span className="text-[10px] uppercase font-semibold text-slate-400">Seed</span>
                        <div
                          className="font-mono text-xs font-bold text-emerald-400 select-all break-all"
                          title={c.seed}
                        >
                          {c.seed}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => onRemove(c)}
                        aria-label="Remove from comparison"
                        className="text-slate-500 hover:text-rose-400 p-1 text-xs"
                      >
                        &times;
                      </button>
                    </div>

                    {/* Metrics */}
                    <div className="space-y-1.5 pt-2 border-t border-slate-800/80 text-xs">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Score</span>
                        <span className="font-semibold text-emerald-400">
                          {typeof c.score === 'number' ? c.score.toFixed(1) : c.score}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Utility</span>
                        <span className="text-slate-200">{c.utility_units ?? '-'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Border Side</span>
                        <span className="text-slate-200">{c.border_side}m</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Saved center</span>
                        <span className="text-slate-200">
                          {Array.isArray(c.anchor) ? `[${c.anchor.join(', ')}]` : String(c.anchor)}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Tie-breaker Dist</span>
                        <span className="text-slate-200">
                          {typeof c.distance_tie === 'number' ? c.distance_tie.toFixed(1) : c.distance_tie}
                        </span>
                      </div>
                    </div>

                    {/* Bounds */}
                    <div className="pt-2 border-t border-slate-800/80 text-[11px] font-mono text-slate-400">
                      <div>Bounds X: [{lox}, {hix})</div>
                      <div>Bounds Z: [{loz}, {hiz})</div>
                    </div>

                    {/* Contributions */}
                    <div className="flex-1 space-y-1 pt-2 border-t border-slate-800/80">
                      <span className="text-[10px] uppercase font-semibold text-slate-400">Contributions</span>
                      <div className="space-y-0.5">
                        {(c.contributions || []).length === 0 ? (
                          <div className="text-[11px] text-slate-500">None</div>
                        ) : (
                          c.contributions.map((contribution, index) => {const feat=contribution.feature || contribution.any_of?.map(featureLabel).join(' or ') || contribution.kind || `Preference ${index+1}`;const w=contribution.max_units ? contribution.utility_units*100/contribution.max_units : 0;return (
                            <div key={`${feat}-${index}`} className="flex justify-between text-[11px]">
                              <span className="text-slate-400 truncate max-w-[110px]" title={feat}>
                                {featureLabel(feat)}
                              </span>
                              <span className="text-emerald-400 font-mono">{contribution.status === 'unknown' ? 'Unknown' : `${w.toFixed(1)}%`}</span>
                            </div>
                          );})
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="pt-3 border-t border-slate-800">
                      <button
                        type="button"
                        onClick={() => onInspect(c)}
                        className="w-full py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-500 text-slate-950 transition-colors"
                      >
                        Inspect Details
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-950 border-t border-slate-800 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
