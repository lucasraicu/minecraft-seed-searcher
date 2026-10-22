import { useDialogFocus } from './useDialogFocus';
import { useState, useRef, useEffect } from 'react';
import type { CatalogFavorite } from './types';
import { FAVORITES_STORAGE_KEY } from './constants';

interface FavoritesDrawerProps {
  favorites: CatalogFavorite[];
  isOpen: boolean;
  onClose: () => void;
  onRemoveFavorite: (id: string) => void;
  onClearFavorites: () => void;
  onImportFavorites: (imported: CatalogFavorite[]) => { success: boolean; message: string };
  onInspectFavorite: (fav: CatalogFavorite) => void;
}

export function FavoritesDrawer({
  favorites,
  isOpen,
  onClose,
  onRemoveFavorite,
  onClearFavorites,
  onImportFavorites,
  onInspectFavorite,
}: FavoritesDrawerProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [importFeedback, setImportFeedback] = useState<{ text: string; isError: boolean } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleCopy = async (seed: string, id: string) => {
    try {
      await navigator.clipboard.writeText(seed);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      setImportFeedback({text:'Clipboard unavailable. Select and copy the seed manually.',isError:true});
    }
  };

  const handleExportJson = () => {
    const payload = {
      schema_version: 'catalog-favorites-v1',
      exported_at: new Date().toISOString(),
      count: favorites.length,
      favorites,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `catalog-favorites-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportCsv = () => {
    const headers = ['seed', 'world_id', 'snapshot_id', 'layout_id', 'border_side', 'anchor_mode', 'score', 'saved_at'];
    const rows = favorites.map(f => [
      `"${f.seed}"`,
      `"${f.world_id}"`,
      `"${f.snapshot_id}"`,
      `"${f.layout_id}"`,
      f.border_side,
      `"${f.anchor_mode}"`,
      f.score,
      f.saved_at,
    ]);
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `catalog-favorites-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    setImportFeedback(null);
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = ev => {
      try {
        const text = ev.target?.result as string;
        const parsed = JSON.parse(text);
        let list: any[] = [];
        if (Array.isArray(parsed)) {
          list = parsed;
        } else if (parsed && typeof parsed === 'object' && Array.isArray(parsed.favorites)) {
          list = parsed.favorites;
        } else {
          setImportFeedback({
            text: 'Malformed import file: expected array or { favorites: [...] } format',
            isError: true,
          });
          return;
        }

        const validFavorites: CatalogFavorite[] = [];
        for (const item of list) {
          if (!item || typeof item !== 'object') continue;
          if (typeof item.seed !== 'string' || !item.world_id || !item.snapshot_id || !item.layout_id) {
            continue;
          }
          validFavorites.push({
            id: item.id || `${item.snapshot_id}:${item.world_id}:${item.layout_id}`,
            seed: String(item.seed),
            world_id: String(item.world_id),
            snapshot_id: String(item.snapshot_id),
            layout_id: String(item.layout_id),
            border_side: (item.border_side as any) || 4096,
            anchor_mode: (item.anchor_mode as any) || 'recommended',
            score: typeof item.score === 'number' ? item.score : 0,
            saved_at: typeof item.saved_at === 'number' ? item.saved_at : Date.now(),
            bounds: item.bounds,
            notes: item.notes,
          });
        }

        if (validFavorites.length === 0) {
          setImportFeedback({
            text: 'No valid seed favorite records found in file',
            isError: true,
          });
          return;
        }

        const res = onImportFavorites(validFavorites);
        setImportFeedback({ text: res.message, isError: !res.success });
      } catch (err) {
        setImportFeedback({
          text: `Failed to parse JSON: ${err instanceof Error ? err.message : String(err)}`,
          isError: true,
        });
      } finally {
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    };
    reader.readAsText(file);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="favorites-title"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden flex flex-col my-8 max-h-[90vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-950 border-b border-slate-800">
          <div>
            <h2 id="favorites-title" className="text-base font-bold text-slate-100 flex items-center gap-2">
              <span className="text-amber-400">&starf;</span>
              <span>Device-Local Favorites</span>
              <span className="text-xs font-normal text-slate-400">({favorites.length})</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Saved in local browser storage (`{FAVORITES_STORAGE_KEY}`) &bull; Private &amp; offline
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close favorites dialog"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Action Bar (Export/Import) */}
        <div className="px-6 py-3 bg-slate-900/60 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleExportJson}
              disabled={favorites.length === 0}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition-colors"
            >
              Export JSON
            </button>
            <button
              type="button"
              onClick={handleExportCsv}
              disabled={favorites.length === 0}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 transition-colors"
            >
              Export CSV
            </button>
            <label className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 cursor-pointer transition-colors">
              Import JSON
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          </div>

          {favorites.length > 0 && (
            <button
              type="button"
              onClick={onClearFavorites}
              className="text-slate-400 hover:text-rose-400 transition-colors"
            >
              Clear All Favorites
            </button>
          )}
        </div>

        {/* Import Feedback Banner */}
        {importFeedback && (
          <div
            className={`px-6 py-2 text-xs border-b ${
              importFeedback.isError
                ? 'bg-rose-950/50 border-rose-800 text-rose-300'
                : 'bg-emerald-950/50 border-emerald-800 text-emerald-300'
            }`}
          >
            {importFeedback.text}
          </div>
        )}

        {/* List of Favorites */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {favorites.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-sm">
              No favorites saved yet. Click the star icon on any seed candidate to save it to your device.
            </div>
          ) : (
            favorites.map(fav => (
              <div
                key={fav.id}
                className="flex items-center justify-between gap-4 p-3 bg-slate-950 rounded-lg border border-slate-800 hover:border-slate-700 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold text-emerald-400 select-all break-all">
                      {fav.seed}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(fav.seed, fav.id)}
                      className="text-[11px] px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 shrink-0"
                    >
                      {copiedId === fav.id ? '✓ Copied' : 'Copy'}
                    </button>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-1 text-[11px] text-slate-400">
                    <span>Score: <strong className="text-slate-200">{fav.score.toFixed(1)}</strong></span>
                    <span>&bull;</span>
                    <span>Side: {fav.border_side}m</span>
                    <span>&bull;</span>
                    <span>Mode: {fav.anchor_mode}</span>
                    <span>&bull;</span>
                    <span className="text-slate-500 font-mono">Snap: {fav.snapshot_id.slice(0, 8)}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => onInspectFavorite(fav)}
                    className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-500 text-slate-950 transition-colors"
                  >
                    Inspect
                  </button>
                  <button
                    type="button"
                    onClick={() => onRemoveFavorite(fav.id)}
                    aria-label={`Remove favorite ${fav.seed}`}
                    className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))
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
