import { useEffect, useRef, useState } from 'react';
import { requestJson } from '../../utils/network';
import { EvidenceSummary } from '../EvidenceSummary';
import type { StructureEvidenceSummary } from '../EvidenceSummary';
import { validStructureEvidence } from '../evidenceValidation';
import { LaunchProductList } from '../LaunchProductList';

export type PillarId = 'realm' | 'presets' | 'personalized' | 'rare';
export interface Product {
  id: string; pillar_id: PillarId; kind: string; label: string; category: string;
  criteria_summary: string; availability_status: string;
  missing_dependencies: string[]; evidence_needed: string[];
  scope?: Record<string, unknown>;
  ranking?: Record<string, unknown>;
}
export interface Registry { ok: boolean; revision: string; products: Product[]; evidence_label: string }
interface ResearchRow {
  world_id: string; seed: string; count: number; witnesses: [number, number][];
  witnesses_truncated?: boolean;
  structure_evidence?: StructureEvidenceSummary;
}
interface ResearchResult {
  ok: boolean; snapshot_id: string; product_id: string; population_worlds: number;
  scope: {scope_type: string; anchor: [number, number]; radius: number};
  results: ResearchRow[]; evidence_label: string;
}
const PILLARS: [PillarId, string][] = [
  ['realm', 'Realm/Server Seeds'], ['presets', 'Presets'],
  ['personalized', 'Personalized Selection'], ['rare', 'Rare Seeds'],
];
const BUTTON = 'rounded-lg border px-4 py-2 text-sm transition-colors';

export function PillarNavigation({value, onChange}: {value: PillarId; onChange: (id: PillarId) => void}) {
  return <nav aria-label="Catalog pillars" className="max-w-7xl mx-auto w-full px-4 sm:px-6 pt-5 flex flex-wrap gap-2">
    {PILLARS.map(([id, label]) => <button key={id} type="button" aria-current={id === value ? 'page' : undefined}
      onClick={() => onChange(id)} className={`${BUTTON} ${id === value ? 'border-emerald-500 bg-emerald-950 text-emerald-200' : 'border-slate-700 bg-slate-950 text-slate-300 hover:border-slate-500'}`}>
      {label}</button>)}
  </nav>;
}

function ResearchList({product, snapshotId}: {product: Product; snapshotId: string}) {
  const key = `${snapshotId}:${product.id}`;
  const feature = /^research\.origin\.(village|trial_chamber|ruined_portal|desert_pyramid|shipwreck)\.r2000$/.exec(product.id)?.[1];
  const [state, setState] = useState<{key: string; data?: ResearchResult; error?: string}>({key: ''});
  const [inspected, setInspected] = useState<string | null>(null);
  const [copied, setCopied] = useState<{worldId: string; failed: boolean} | null>(null);
  const generation = useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    const current = ++generation.current;
    setInspected(null); setCopied(null);
    if (!feature) {setState({key, error: 'Research product definition is invalid.'}); return () => controller.abort();}
    if (!snapshotId) {setState({key, error: 'Select an available catalog snapshot to browse research results.'}); return () => controller.abort();}
    setState({key});
    requestJson<ResearchResult>('/api/catalog/product-results', {
      method: 'POST', body: {revision: 'catalog-product-request-v1', snapshot_id: snapshotId, product_id: product.id},
      timeoutMs: 12000, signal: controller.signal,
    }).then(({data}) => {
      if (controller.signal.aborted || generation.current !== current) return;
      if (!data.ok || data.snapshot_id !== snapshotId || data.product_id !== product.id ||
          data.scope?.scope_type !== 'origin_euclidean_circle' || data.scope.radius !== 2000 ||
          data.scope.anchor?.[0] !== 0 || data.scope.anchor?.[1] !== 0 ||
          !Array.isArray(data.results) || data.results.length > 100 ||
          data.results.some(row => typeof row.seed !== 'string' || !Number.isInteger(row.count) || row.count < 1 ||
            !Array.isArray(row.witnesses) || row.witnesses.length > 5000 ||
            (row.structure_evidence !== undefined && !validStructureEvidence(row.structure_evidence, row.count, 'structure.'+feature)) ||
            row.witnesses.some(p => !Array.isArray(p) || p.length !== 2 ||
              !p.every(Number.isInteger) || p[0]*p[0]+p[1]*p[1] > 2000*2000))) {
        setState({key, error: 'Research response did not match the selected scope.'}); return;
      }
      setState({key, data});
    }).catch(error => {
      if (!controller.signal.aborted && generation.current === current)
        setState({key, error: error instanceof Error ? error.message : 'Research preview is unavailable.'});
    });
    return () => controller.abort();
  }, [key, product.id, snapshotId, feature]);
  const active = state.key === key ? state : {key};
  return <section aria-label={`${product.label} research results`} className="mt-4 space-y-4">
    <h3 className="font-semibold">{product.label}</h3>
    <p className="text-sm text-slate-400">Predicted structure starts inside a 2,000-block circle around Origin (0, 0). Origin is not world spawn. Research ranking uses predicted counts within the selected catalog population. BDS checks are shown separately.</p>
    {active.error && <p role="alert" className="text-amber-300">{active.error}</p>}
    {!active.error && !active.data && <p role="status">Loading research preview…</p>}
    {active.data && <>
      <p className="text-xs text-slate-400">{active.data.population_worlds} catalog worlds · {active.data.evidence_label}</p>
      {!active.data.results.length && <p>No positive counts with complete coverage in this snapshot.</p>}
      {active.data.results.map((row, i) => <article key={row.world_id} className="rounded-lg bg-slate-950 border border-slate-700 p-4 space-y-3">
        <div className="flex flex-wrap items-center gap-3"><strong>#{i+1} · {row.count} {feature?.replaceAll('_', ' ') || 'structure'} predictions</strong>
          <code className="break-all select-all">{row.seed}</code>
          <button type="button" className={`${BUTTON} border-slate-700`} onClick={async () => {
            try {await navigator.clipboard.writeText(row.seed); setCopied({worldId: row.world_id, failed: false});}
            catch {setCopied({worldId: row.world_id, failed: true});}
          }}>{copied?.worldId === row.world_id && !copied.failed ? 'Copied' : 'Copy seed'}</button>
          <button type="button" className={`${BUTTON} border-slate-700`} aria-expanded={inspected === row.world_id}
            onClick={() => setInspected(inspected === row.world_id ? null : row.world_id)}>View circle map</button>
        </div>
        {copied?.worldId === row.world_id && <p role="status" className="text-sm text-slate-300">
          {copied.failed ? 'Clipboard unavailable; select and copy the seed text.' : 'Seed copied.'}</p>}
        <EvidenceSummary summary={row.structure_evidence} />
        {inspected === row.world_id && <figure>
          <svg viewBox="-2200 -2200 4400 4400" role="img" aria-label={`${row.count} predicted starts within 2000 blocks of Origin; east right, south down`}
            className="w-full max-w-lg mx-auto bg-slate-900 rounded-lg">
            <circle cx="0" cy="0" r="2000" fill="none" stroke="#34d399" strokeWidth="12" />
            <path d="M -100 0 H 100 M 0 -100 V 100" stroke="#e2e8f0" strokeWidth="14" />
            {row.witnesses.map(([x,z]) => <circle key={`${x}:${z}`} cx={x} cy={z} r="25" fill="#fbbf24"><title>{`X ${x}, Z ${z}`}</title></circle>)}
          </svg>
          <figcaption className="text-xs text-slate-400">Predicted locations. Circle: radius 2,000 blocks. Center: Origin. North is up.
            {row.witnesses_truncated ? ' Map witnesses are truncated; the displayed count includes all predicted starts in scope.' : ''}</figcaption>
          <details className="mt-3 text-sm"><summary className="cursor-pointer">Predicted coordinates ({row.witnesses.length} shown)</summary>
            <div className="max-h-64 overflow-auto"><table className="w-full text-left">
              <caption className="sr-only">Predicted {product.label} locations, in block coordinates</caption>
              <thead><tr><th scope="col">X</th><th scope="col">Z</th></tr></thead>
              <tbody>{row.witnesses.map(([x,z]) => <tr key={`${x}:${z}`}><td>{x}</td><td>{z}</td></tr>)}</tbody>
            </table></div>
          </details>
        </figure>}
      </article>)}
    </>}
  </section>;
}

export function ProductPillar({
  pillarId,
  snapshotId,
  initialRegistry,
  initialSelected,
}: {
  pillarId: PillarId;
  snapshotId: string;
  initialRegistry?: Registry;
  initialSelected?: string;
}) {
  const [registry, setRegistry] = useState<Registry | null>(initialRegistry || null);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<string | null>(initialSelected || null);
  const inspector = useRef<HTMLElement>(null);
  const opener = useRef<HTMLButtonElement | null>(null);
  const closeCriteria = () => {setSelected(null); opener.current?.focus();};
  useEffect(() => {
    if (initialRegistry && registry === initialRegistry) return;
    const controller = new AbortController();
    setRegistry(null);setSelected(null);setError('');
    requestJson<Registry>(`/api/catalog/products${snapshotId ? `?snapshot_id=${encodeURIComponent(snapshotId)}` : ''}`, {method: 'GET', timeoutMs: 12000, signal: controller.signal})
      .then(({data}) => {if (!controller.signal.aborted) {
        if (!data.ok || (data.revision !== 'catalog-products-v1' && data.revision !== 'catalog-products-v2') || !Array.isArray(data.products))
          throw new Error('Catalog product definitions are unavailable.');
        setRegistry(data);
      }})
      .catch(e => {if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Catalog unavailable.');});
    return () => controller.abort();
  }, [initialRegistry,snapshotId]);
  useEffect(() => {if (!initialSelected) setSelected(null);}, [pillarId]);
  useEffect(() => {if (selected) inspector.current?.focus();}, [selected]);
  const products = registry?.products.filter(p => p.pillar_id === pillarId) || [];
  const chosen = products.find(p => p.id === selected);
  const categories = [...new Set(products.map(p => p.category))];
  return <main className="max-w-7xl mx-auto w-full p-4 sm:p-6 space-y-6">
    <h2 className="text-xl font-semibold">{PILLARS.find(([id]) => id === pillarId)?.[1]}</h2>
    {pillarId === 'realm' && <p className="text-slate-300">Browse worlds for shared survival play. Qualification requires public observations against the declared Realm blueprint; personal search winners are not automatically certified. Separate 2048, 4096 and 8192 Overworld boards use size-specific requirements and the same 1,250-point budget: 845 OW / 265 luxury / 140 Nether. The Nether square stays 1024 × 1024. Results are predicted at a supported center; an empty list means no retained match.</p>}
    {pillarId === 'presets' && <p className="text-slate-300">Sixteen fixed play-style presets. Open a card to inspect its exact criteria and browse launch results.</p>}
    {pillarId === 'rare' && <p className="text-slate-300">{registry?.revision==='catalog-products-v1' ? 'Legacy Origin-centered research density previews. Choose the current snapshot for the new record products.' : 'Seventeen record categories based on predicted structure counts, proximity, clusters and biome witnesses. Rankings describe this evaluated catalog, which includes selected research controls; these are not global Minecraft records.'}</p>}
    {pillarId === 'personalized' && <p className="text-slate-300">Personalized selection and criteria.</p>}
    {error && <p role="alert" className="text-amber-300">{error}</p>}
    {!registry && !error && <p role="status">Loading catalog definitions…</p>}
    {categories.map(category => <section key={category} className="space-y-3">
      <h3 className="font-semibold text-emerald-300">{category}</h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{products.filter(p => p.category === category).map(p =>
        <button key={p.id} type="button" aria-expanded={chosen?.id === p.id} onClick={e => {opener.current = e.currentTarget; setSelected(p.id);}}
          className="text-left rounded-xl border border-slate-700 bg-slate-950 p-4 hover:border-emerald-500 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <span className="block font-semibold">{p.label}</span>
            {p.availability_status === 'predicted' && (
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded border border-emerald-600 bg-emerald-950/70 text-emerald-300">
                Launch
              </span>
            )}
            {p.availability_status === 'research' && (
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded border border-sky-600 bg-sky-950/70 text-sky-300">
                Research
              </span>
            )}
            {p.availability_status !== 'predicted' && p.availability_status !== 'research' && (
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded border border-amber-600/70 bg-amber-950/70 text-amber-300">
                Gated
              </span>
            )}
          </div>
          <span className="block text-xs text-slate-400">{p.criteria_summary}</span>
          <span className={`block text-xs ${p.availability_status === 'predicted' || p.availability_status === 'research' ? 'text-emerald-300' : 'text-amber-300'}`}>
            {p.availability_status === 'predicted' ? 'Browse launch results' : (p.availability_status === 'research' ? 'Browse research preview' : 'Evidence pending · View criteria')}
          </span>
        </button>)}</div>
    </section>)}
    {chosen && <section ref={inspector} tabIndex={-1} aria-label={`${chosen.label} criteria`} onKeyDown={e => {if (e.key === 'Escape') {e.stopPropagation(); closeCriteria();}}}
      className="rounded-xl border border-emerald-700 p-5 bg-slate-950 space-y-3 outline-none focus:ring-2 focus:ring-emerald-500">
      <div className="flex justify-between gap-3"><h3 className="font-bold">{chosen.label}</h3>
        <button type="button" className="text-sm underline" onClick={closeCriteria}>Close criteria</button></div>
      <p>{chosen.criteria_summary}</p>
      {chosen.availability_status !== 'research' && chosen.availability_status !== 'predicted' && <>
        <p className="text-amber-300">Matching results are unavailable until the required evidence is implemented.</p>
        <ul className="list-disc pl-5 text-sm text-slate-300">{chosen.evidence_needed?.map(e => <li key={e}>{e}</li>)}</ul>
        {chosen.missing_dependencies?.length > 0 && (
          <p className="text-xs text-slate-400">Pending: {chosen.missing_dependencies.join(', ').replaceAll('_', ' ')}</p>
        )}
      </>}
      {chosen.availability_status === 'research' && <ResearchList key={chosen.id} product={chosen} snapshotId={snapshotId} />}
      {chosen.availability_status === 'predicted' && <LaunchProductList key={chosen.id} product={chosen} snapshotId={snapshotId} />}
    </section>}
  </main>;
}
