import { useDialogFocus } from './useDialogFocus';
import { useState, useEffect } from 'react';
import type { CatalogQueryPayload, CatalogCandidate, FeedbackExportPayload } from './types';

interface QueryExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  queryPayload: CatalogQueryPayload;
  evidenceLabel: string;
  results: CatalogCandidate[];
  totalMatched: number;
}

export function QueryExportModal({
  isOpen,
  onClose,
  queryPayload,
  evidenceLabel,
  results,
  totalMatched,
}: QueryExportModalProps) {
  const [userNotes, setUserNotes] = useState('');
  const [isCopied, setIsCopied] = useState(false);
  const [copyError, setCopyError] = useState('');
  const [participant, setParticipant] = useState('');
  const [source, setSource] = useState<'player' | 'developer' | 'synthetic'>('player');

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

  const buildExportPayload = (): FeedbackExportPayload => {
    return {
      schema_version: 'catalog-query-feedback-v1',
      exported_at: new Date().toISOString(),
      snapshot_id: queryPayload.catalog_snapshot_id,
      evidence_label: evidenceLabel,
      request: queryPayload,
      user_notes: userNotes,
      results_summary: {
        total_matched: totalMatched,
        returned_count: results.length,
        candidates: results.map(c => ({
          world_id: c.world_id,
          seed: c.seed,
          score: c.score,
          border_side: c.border_side,
        })),
      },
    };
  };

  const handleDownload = () => {
    const payload = buildExportPayload();
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `catalog-feedback-${queryPayload.catalog_snapshot_id.slice(0, 8)}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyJson = async () => {
    const payload = buildExportPayload();
    setCopyError('');
    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch {
      setCopyError('Clipboard unavailable. Use Download JSON instead.');
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="feedback-export-title"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden flex flex-col my-8"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-950 border-b border-slate-800">
          <div>
            <h2 id="feedback-export-title" className="text-base font-bold text-slate-100 flex items-center gap-2">
              <span className="text-emerald-400">Export Query &amp; Feedback</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Client-only annotated JSON export &bull; No remote telemetry &bull; Private &amp; offline
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close export dialog"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 text-xs">
          {/* Query Summary Info */}
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1.5">
            <div className="flex justify-between">
              <span className="text-slate-400">Snapshot:</span>
              <span className="font-mono text-emerald-400">{queryPayload.catalog_snapshot_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Border &bull; Anchor:</span>
              <span className="text-slate-200">{queryPayload.border_side}m &bull; {queryPayload.anchor_mode}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Filter Rules:</span>
              <span className="text-slate-200">{queryPayload.rows.length} rows</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Matches:</span>
              <span className="text-slate-200">{totalMatched} worlds found ({results.length} on current page)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Evidence Label:</span>
              <span className="text-slate-300 italic">{evidenceLabel}</span>
            </div>
          </div>

          {/* User Annotations Form */}
          <div className="space-y-1.5">
            <label htmlFor="user-notes-input" className="font-medium text-slate-300 block">
              User Notes &amp; Search Feedback (optional):
            </label>
            <textarea
              id="user-notes-input"
              rows={4}
              maxLength={2000}
              value={userNotes}
              onChange={e => setUserNotes(e.target.value)}
              placeholder="Describe whether these results suit your play style. Predictions and world spawn remain unverified."
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          <div className="space-y-2 border-t border-slate-800 pt-3">
            <label className="block">Participant pseudonym (optional, no real name needed)
              <input aria-label="Participant pseudonym" value={participant} maxLength={80} onChange={e=>setParticipant(e.target.value)} className="block w-full mt-1 p-2 bg-slate-950 border border-slate-700 rounded" />
            </label>
            <label className="block">Request source
              <select aria-label="Request source" value={source} onChange={e=>setSource(e.target.value as typeof source)} className="ml-2 bg-slate-950 p-1 border border-slate-700 rounded">
                <option value="player">Player supplied</option><option value="developer">Developer supplied</option><option value="synthetic">Synthetic test</option>
              </select>
            </label>
            <button type="button" disabled={!participant.trim()} className="px-3 py-2 rounded bg-slate-800 disabled:opacity-40" onClick={()=>{
              const blob=new Blob([JSON.stringify([{participant:participant.trim(),request:queryPayload,annotation:userNotes,source}],null,2)],{type:'application/json'});
              const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='catalog-participant-request.json';a.click();URL.revokeObjectURL(url);
            }}>Download participant request</button>
            <p className="text-slate-400">This separate file can be imported for a participant-grouped holdout. No data is sent automatically.</p>
          </div>
          {copyError && <p role="alert" className="text-amber-300">{copyError}</p>}

          <p className="text-[11px] text-slate-400 italic">
            This export is generated entirely within your browser. You can save the JSON file to share reproducible feedback with researchers or keep notes locally.
          </p>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-950 border-t border-slate-800 flex items-center justify-between">
          <button
            type="button"
            onClick={handleCopyJson}
            className="px-3 py-1.5 text-xs font-medium rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
          >
            {isCopied ? '✓ Copied to Clipboard!' : 'Copy JSON'}
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs font-medium rounded text-slate-400 hover:text-slate-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="px-4 py-1.5 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-500 text-slate-950 transition-colors"
            >
              Download JSON
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
