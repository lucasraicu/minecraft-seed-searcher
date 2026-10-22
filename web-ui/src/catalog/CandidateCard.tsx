import { useState } from 'react';
import type { CatalogCandidate } from './types';
import { featureLabel, ANCHOR_LABELS } from './constants';

interface CandidateCardProps {
  candidate: CatalogCandidate;
  snapshotId: string;
  isCompared: boolean;
  canCompare: boolean;
  isFavorite: boolean;
  onToggleCompare: (candidate: CatalogCandidate) => void;
  onToggleFavorite: (candidate: CatalogCandidate) => void;
  onInspect: (candidate: CatalogCandidate) => void;
}

export function CandidateCard({
  candidate,
  snapshotId: _snapshotId,
  isCompared,
  canCompare,
  isFavorite,
  onToggleCompare,
  onToggleFavorite,
  onInspect,
}: CandidateCardProps) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState('');

  const handleCopySeed = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setCopyError('');
    try {
      await navigator.clipboard.writeText(candidate.seed);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopyError('Clipboard unavailable. Select and copy the seed above.');
    }
  };

  const [lox, loz, hix, hiz] = candidate.bounds || [0, 0, 0, 0];
  const topContributions = (candidate.contributions || []).map((c,i) =>
    [c.feature || c.any_of?.map(featureLabel).join(' or ') || c.kind || `Preference ${i+1}`, c.max_units ? c.utility_units*100/c.max_units : 0, c.status] as const)
    .sort((a,b)=>b[1]-a[1]).slice(0,3);

  return (
    <div className="flex flex-col bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-lg p-4 transition-colors shadow-sm">
      {candidate.anchor_evidence && <p className="text-xs text-amber-200 mb-2">{ANCHOR_LABELS[candidate.anchor_evidence.mode]} · X/Z reference, not player landing</p>}
      {/* Top row: Seed String + Copy + Favorite */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1">
            Bedrock Seed
          </div>
          <div className="flex items-center gap-2">
            <span
              className="font-mono text-base font-bold text-emerald-400 select-all break-all tracking-tight"
              title={candidate.seed}
            >
              {candidate.seed}
            </span>
            <button
              type="button"
              onClick={handleCopySeed}
              aria-label={`Copy seed string ${candidate.seed}`}
              className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors shrink-0"
            >
              {copied ? (
                <span className="text-emerald-400 flex items-center gap-1 font-semibold">
                  &check; Copied
                </span>
              ) : (
                'Copy'
              )}
            </button>
          </div>
        </div>

        <button
          type="button"
          onClick={() => onToggleFavorite(candidate)}
          aria-label={isFavorite ? 'Remove from favorites' : 'Save to favorites'}
          className={`p-1.5 rounded transition-colors shrink-0 ${
            isFavorite
              ? 'text-amber-400 hover:text-amber-300 bg-amber-400/10'
              : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
          }`}
        >
          <svg className="w-5 h-5 fill-current" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        </button>
      </div>

      {/* Middle row: Badges, authorative Score & Utility units */}
      <div className="flex flex-wrap items-center gap-2 mt-3 text-xs">
        <span className="inline-flex items-center px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800 font-semibold">
          Score: {typeof candidate.score === 'number' ? candidate.score.toFixed(1) : candidate.score}
        </span>
        {candidate.utility_units !== undefined && (
          <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            Utility: {candidate.utility_units}
          </span>
        )}
        <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
          Side: {candidate.border_side}m
        </span>
        <span className="inline-flex items-center px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
          World: <span className="font-mono ml-1 text-slate-300">{candidate.world_id.slice(0, 8)}</span>
        </span>
      </div>

      {/* Bounds coordinates info */}
      <div className="mt-2 text-[11px] font-mono text-slate-400">
        Base: [{candidate.anchor[0]}, {candidate.anchor[1]}] · Bounds: [{lox}, {loz}] &rarr; [{hix}, {hiz}] (upper edges excluded)
      </div>
      {copyError && <p role="alert" className="text-xs text-amber-300 mt-2">{copyError}</p>}

      {/* Top contributions / evidence points */}
      {topContributions.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {topContributions.map(([feat, weight, status], index) => (
            <span
              key={`${feat}-${index}`}
              className="text-[10px] bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800 text-slate-400"
            >
              {featureLabel(feat)}: {status === 'unknown' ? 'unknown coverage' : `${weight.toFixed(1)}% fulfilled`}
            </span>
          ))}
        </div>
      )}

      {/* Bottom actions: Compare toggle & Inspect detail */}
      <div className="flex items-center justify-between gap-2 mt-4 pt-3 border-t border-slate-800/80">
        <button
          type="button"
          onClick={() => onToggleCompare(candidate)}
          disabled={!isCompared && !canCompare}
          aria-label={isCompared ? 'Remove from comparison' : 'Add to comparison'}
          className={`px-2.5 py-1 text-xs font-medium rounded border transition-colors ${
            isCompared
              ? 'bg-emerald-600 text-white border-emerald-500'
              : !canCompare
              ? 'bg-slate-800 text-slate-500 border-slate-700 cursor-not-allowed'
              : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
          }`}
        >
          {isCompared ? 'In Compare (Selected)' : 'Compare'}
        </button>

        <button
          type="button"
          onClick={() => onInspect(candidate)}
          className="px-3 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-500 text-slate-950 transition-colors"
        >
          Inspect Details &rarr;
        </button>
      </div>
    </div>
  );
}
