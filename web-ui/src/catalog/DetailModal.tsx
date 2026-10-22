import { useDialogFocus } from './useDialogFocus';
import { useEffect, useState } from 'react';
import type { CatalogDetailResponse, BorderSide, AnchorMode } from './types';
import { SvgMap } from './SvgMap';
import { EvidenceSummary } from './EvidenceSummary';
import { ANCHOR_LABELS,featureLabel } from './constants';
import {NetherDetails} from './NetherDetails';

interface DetailModalProps {
  detail: CatalogDetailResponse | null;
  seedString: string;
  snapshotId: string;
  worldId: string;
  layoutId: string;
  isOpen: boolean;
  onClose: () => void;
  isLoading?: boolean;
  error?: string | null;
}

export function DetailModal({
  detail,
  seedString,
  snapshotId,
  worldId,
  layoutId,
  isOpen,
  onClose,
  isLoading = false,
  error = null,
}: DetailModalProps) {
  const [copyError, setCopyError] = useState('');
  const [copiedShare, setCopiedShare] = useState(false);
  const [copiedSeed, setCopiedSeed] = useState(false);
  const [activeTab, setActiveTab] = useState<'map' | 'structures' | 'biomes' | 'raw'>('map');

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  useDialogFocus(isOpen);

  if (!isOpen) return null;

  const handleCopySeed = async () => {
    setCopyError('');
    try {
      await navigator.clipboard.writeText(typeof detail?.identity.seed === 'string' ? detail.identity.seed : seedString);
      setCopiedSeed(true);
      setTimeout(() => setCopiedSeed(false), 2000);
    } catch {
      setCopyError('Clipboard unavailable. Select and copy the seed or address manually.');
    }
  };

  const handleCopyShareLink = async () => {
    setCopyError('');
    const shareUrl = `${window.location.origin}${window.location.pathname}#catalog?snapshot=${encodeURIComponent(
      snapshotId
    )}&world=${encodeURIComponent(worldId)}&layout=${encodeURIComponent(layoutId)}`;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopiedShare(true);
      setTimeout(() => setCopiedShare(false), 2500);
    } catch {
      setCopyError('Clipboard unavailable. Select and copy the seed or address manually.');
    }
  };

  const layout = detail?.layout;
  const borderSide = (layout?.border_side as BorderSide) || 4096;
  const anchor = (layout?.anchor as [number, number] | string) || [0, 0];
  const anchorMode:AnchorMode = detail?.anchor_evidence?.mode || detail?.anchor_roles?.[0]?.mode || layout?.anchor_mode || (Array.isArray(anchor) && anchor[0]===0 && anchor[1]===0 ? 'origin' : 'recommended');

  // Compute bounds from layout side and anchor if not explicit
  let bounds: [number, number, number, number] = [-borderSide / 2, -borderSide / 2, borderSide / 2, borderSide / 2];
  if (Array.isArray(anchor) && anchor.length === 2) {
    const half = borderSide / 2;
    bounds = [anchor[0] - half, anchor[1] - half, anchor[0] + half, anchor[1] + half];
  }

  const structures = detail?.structures || {};
  const biomeWitnesses = detail?.biome_witnesses || [];
  const totalStructurePoints = Object.values(structures).reduce((acc, pts) => acc + pts.length, 0);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="detail-modal-title"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden flex flex-col my-8 max-h-[90vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-start justify-between px-6 py-4 bg-slate-950 border-b border-slate-800 gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-950 text-emerald-400 border border-emerald-800">
                Seed Detail &bull; Pinned Leaf
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Snapshot: {snapshotId}
              </span>
            </div>
            <h2 id="detail-modal-title" className="text-lg font-bold text-slate-100 mt-1 flex items-center gap-3">
              <span className="font-mono text-emerald-400 select-all break-all">{typeof detail?.identity.seed === 'string' ? detail.identity.seed : seedString}</span>
              <button
                type="button"
                onClick={handleCopySeed}
                className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 shrink-0"
              >
                {copiedSeed ? '✓ Copied' : 'Copy'}
              </button>
            </h2>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={handleCopyShareLink}
              className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded bg-emerald-900/40 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-700 transition-colors"
            >
              {copiedShare ? '✓ Share Link Copied!' : 'Share Deep Link'}
            </button>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close seed detail dialog"
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {copyError && <p role="alert" className="px-6 py-2 text-xs text-amber-300">{copyError}</p>}
        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {isLoading && (
            <div className="py-16 text-center text-slate-400 space-y-3">
              <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
              <p className="text-sm">Fetching immutable leaf observation details...</p>
            </div>
          )}

          {error && !isLoading && (
            <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-sm">
              <div className="font-semibold mb-1">Failed to load seed details</div>
              <div>{error}</div>
            </div>
          )}

          {!isLoading && !error && detail && (
            <>
              {/* Evidence Banner */}
              <div className="flex items-center justify-between px-4 py-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                  <span className="font-medium text-slate-300">
                    Evidence Source: <strong className="text-emerald-400">{detail.evidence_label || 'Immutable segment leaf'}</strong>
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 italic">
                  Honest evidence &bull; Coordinates absolute &bull; No actual game certification
                </div>
              </div>

              {detail.structure_evidence && <section aria-label="BDS checks for this selected border" className="space-y-3">
                <p className="text-xs text-slate-400">BDS checks for the selected center and border. Map points remain predictor observations.</p>
                {Object.entries(detail.structure_evidence).filter(([, value]) => value.tested_count > 0).map(([feature, summary]) =>
                  <div key={feature}><p className="text-xs text-slate-300">{feature.replace('structure.', '').replaceAll('_', ' ')}</p>
                    <EvidenceSummary summary={summary} /></div>)}
                {!Object.values(detail.structure_evidence).some(value => value.tested_count > 0) &&
                  <p className="text-xs text-slate-400">These structure predictions have not been checked in BDS.</p>}
              </section>}
              {detail.biome_evidence && detail.biome_evidence.checks.length > 0 &&
                <p className="text-xs text-amber-300">{detail.biome_evidence.checks.length} BDS biome API observations inside this border. {detail.biome_evidence.interpretation}</p>}

              {(detail?.anchor_evidence || anchorMode.startsWith('world_spawn_')) && <p className="text-xs text-amber-200 mb-3">{ANCHOR_LABELS[anchorMode]}: X/Z only. Player landing, usable ground height and safety are unverified.</p>}
              {(detail?.anchor_roles?.length||0)>1 && <p className="text-xs text-amber-200 mb-3">This saved coordinate has both roles: {detail!.anchor_roles!.map(role=>ANCHOR_LABELS[role.mode]).join(' and ')}. Each retains its own evidence; player landing and safety remain unverified.</p>}
              {detail?.accuracy && <section className="text-xs border border-slate-700 rounded p-3 mb-3" aria-label="Biome refinement coverage">
                <p>{detail.accuracy.interpretation}</p>
                {detail.accuracy.tiles.length===0 ? <p>No exact-scope tiles saved for this world yet. Coarse missing witnesses do not prove absence.</p> : <ul>{detail.accuracy.tiles.map(tile=><li key={tile.tile_id}>{tile.provider} at Y={tile.y}: [{tile.bounds.join(', ')}), half-open X/Z bounds. Proof applies only to this provider and saved blocks.</li>)}</ul>}
              </section>}
              {detail?.nether_structures&&detail.nether_bounds&&<NetherDetails structures={detail.nether_structures} bounds={detail.nether_bounds} witnesses={detail.nether_biome_witnesses||[]} />}
              {detail?.structures_truncated&&<p className="text-amber-200 text-xs">Map coordinates are truncated; use the saved summary counts for the full scoped predictor inventory.</p>}
              {/* Layout metadata cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-slate-400">Border Dimensions</div>
                  <div className="text-sm font-semibold text-slate-100 mt-1">{borderSide} &times; {borderSide}</div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-slate-400">{detail?.anchor_evidence || layout?.anchor_mode ? ANCHOR_LABELS[anchorMode] : 'Saved center'}</div>
                  <div className="text-sm font-semibold text-slate-100 mt-1">{Array.isArray(anchor) ? `${anchor[0]}, ${anchor[1]}` : anchor}</div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-slate-400">Predicted structures inside</div>
                  <div className="text-sm font-semibold text-emerald-400 mt-1">{totalStructurePoints} points</div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-slate-400">Biome Witnesses</div>
                  <div className="text-sm font-semibold text-emerald-400 mt-1">{biomeWitnesses.length} samples</div>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex border-b border-slate-800 text-xs font-medium space-x-4">
                <button
                  type="button"
                  onClick={() => setActiveTab('map')}
                  className={`pb-2 border-b-2 transition-colors ${
                    activeTab === 'map'
                      ? 'border-emerald-500 text-emerald-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Interactive Map Canvas
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('structures')}
                  className={`pb-2 border-b-2 transition-colors ${
                    activeTab === 'structures'
                      ? 'border-emerald-500 text-emerald-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Structure Starts ({totalStructurePoints})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('biomes')}
                  className={`pb-2 border-b-2 transition-colors ${
                    activeTab === 'biomes'
                      ? 'border-emerald-500 text-emerald-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Biome Witnesses ({biomeWitnesses.length})
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('raw')}
                  className={`pb-2 border-b-2 transition-colors ${
                    activeTab === 'raw'
                      ? 'border-emerald-500 text-emerald-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Raw Layout JSON
                </button>
              </div>

              {/* Tab Contents */}
              {activeTab === 'map' && (
                <SvgMap
                  bounds={bounds}
                  borderSide={borderSide}
                  anchor={anchor}
                  anchorMode={anchorMode}
                  structures={structures}
                  biomeWitnesses={biomeWitnesses}
                />
              )}

              {activeTab === 'structures' && (
                <div className="bg-slate-950 rounded-lg border border-slate-800 p-4 max-h-96 overflow-y-auto">
                  {Object.keys(structures).length === 0 ? (
                    <p className="text-slate-500 text-xs">No structure starts recorded in this border layout.</p>
                  ) : (
                    <div className="space-y-4">
                      {Object.entries(structures).map(([feat, coords]) => (
                        <div key={feat} className="space-y-1.5">
                          <div className="flex items-center justify-between text-xs font-semibold text-emerald-400 border-b border-slate-800 pb-1">
                            <span>{featureLabel(feat)}</span>
                            <span className="text-slate-400 font-mono">{coords.length} found</span>
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                            {coords.map(([sx, sz], i) => (
                              <div key={i} className="text-[11px] font-mono bg-slate-900 px-2 py-1 rounded border border-slate-800 text-slate-300">
                                X: {sx}, Z: {sz}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'biomes' && (
                <div className="bg-slate-950 rounded-lg border border-slate-800 p-4 max-h-96 overflow-y-auto">
                  {biomeWitnesses.length === 0 ? (
                    <p className="text-slate-500 text-xs">No biome witness samples inside this border layout.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs text-slate-300">
                        <thead className="bg-slate-900 text-slate-400 border-b border-slate-800">
                          <tr>
                            <th className="py-2 px-3">Biome Feature</th>
                            <th className="py-2 px-3">X</th>
                            <th className="py-2 px-3">Y (Height)</th>
                            <th className="py-2 px-3">Z</th>
                            <th className="py-2 px-3">Evidence State</th>
                            <th className="py-2 px-3">Dist² from Anchor</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono">
                          {biomeWitnesses.map((bw, i) => {
                            const yHeight = Number.isSafeInteger(bw.y) ? bw.y : undefined;
                            const evidenceState = yHeight === undefined ? 'Height unavailable' : `Predicted sample at Y=${yHeight}`;
                            return (
                              <tr key={i} className="hover:bg-slate-900/50">
                                <td className="py-2 px-3 font-sans font-medium text-emerald-400">{featureLabel(bw.feature)}</td>
                                <td className="py-2 px-3">{bw.x}</td>
                                <td className="py-2 px-3 text-emerald-300 font-semibold">{yHeight ?? 'Unknown'}</td>
                                <td className="py-2 px-3">{bw.z}</td>
                                <td className="py-2 px-3 font-sans text-[11px] text-slate-400">{evidenceState}</td>
                                <td className="py-2 px-3">{bw.distance_squared}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'raw' && (
                <pre className="p-4 bg-slate-950 rounded-lg border border-slate-800 text-slate-300 font-mono text-[11px] max-h-96 overflow-auto">
                  {JSON.stringify(detail, null, 2)}
                </pre>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
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
