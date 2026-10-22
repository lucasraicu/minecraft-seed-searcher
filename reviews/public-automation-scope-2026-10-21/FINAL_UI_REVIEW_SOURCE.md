Approved final UI source audit, no browser QA per user. Read-only evidence review only. APIwitness shape coordinate[x,y|null,z], dimension,feature,observation_id,provider,witness_id,distance_squared. P1budget1250 group845/265/140; Netherfixed1024 square and floor(OW/8), distancesNetherunits. Backendproductresults perpage<=20, cursorstr, snapshotSHA64, exactproduct_id, matched_worlds retainedcount, population_worlds evaluatedworlds. Fields sourcebound identity and observationID. These components are integrated source but independent Codex/Gemini final check required. Report ONLYconcrete source issues, no invented APIs or browser guarantees. Current4096/8192 gated until calibration; subsequentupdateownedCodex.

FILE web-ui/src/catalog/LaunchProductList.tsx
import { useEffect, useRef, useState } from 'react';
import { requestJson } from '../utils/network';

export type PillarId = 'realm' | 'presets' | 'personalized' | 'rare';

export interface Product {
  id: string;
  pillar_id: PillarId;
  kind: string;
  label: string;
  category: string;
  criteria_summary: string;
  availability_status: string;
  missing_dependencies: string[];
  evidence_needed: string[];
  scope?: Record<string, unknown>;
  ranking?: Record<string, unknown>;
}

export interface Witness {
  feature: string;
  dimension: string;
  coordinate: [number, number | null, number];
  distance_squared: number;
  method_id?: string;
  observation_id?:string;
  provider?:string;
  source_observation_id?: string;
  witness_id?: string;
}

export interface Anchor {
  mode: string;
  coordinate: [number, number];
  overworld: [number, number];
  nether: [number, number];
  nether_reference?: string;
}

export interface MetricFraction {
  numerator: number;
  denominator: number;
}

export type RankItem = number | string | MetricFraction;

export interface Evaluation {
  product_id: string;
  world_id: string;
  seed: string;
  observation_id: string;
  status: 'match' | string;
  rank: RankItem[];
  anchor: Anchor;
  witnesses: Witness[];
  metric?: Record<string, unknown>;
  reason?: string | null;
  scope: {
    dimension: string;
    radius: number;
    [key: string]: unknown;
  };
}

export interface ProductResultsV2Response {
  ok: boolean;
  revision: 'catalog-product-results-v2';
  snapshot_id: string;
  product_id: string;
  results: Evaluation[];
  matched_worlds: number;
  next_cursor: string | null;
  population_worlds: number;
  scope: Record<string, unknown>;
  policy_revision: string;
  evidence_label: string;
  error?: string;
  code?: string;
}

const BUTTON = 'rounded-lg border px-4 py-2 text-sm transition-colors';

export function formatRankItem(item: unknown): string {
  if (typeof item === 'number') {
    return Number.isInteger(item) ? String(item) : item.toFixed(2);
  }
  if (typeof item === 'object' && item !== null && 'numerator' in item && 'denominator' in item) {
    const f = item as MetricFraction;
    return Number.isFinite(f.numerator)&&Number.isFinite(f.denominator)&&f.denominator>0?`${f.numerator}/${f.denominator}`:'unknown';
  }
  if(item&&typeof item==='object'&&'decimal' in item)return String((item as {decimal:unknown}).decimal);
  return typeof item==='string'?item:'unknown';
}

export function validateProductResultsV2(data:unknown,expectedSnapshotId?:string,expectedProductId?:string):{ok:boolean;error?:string;value?:ProductResultsV2Response}{
  const fail=(error:string)=>({ok:false,error});
  if(!data||typeof data!=='object')return fail('Invalid product response');
  const res=data as ProductResultsV2Response;
  const sha=(v:unknown)=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
  const coord=(v:unknown):v is [number,number]=>Array.isArray(v)&&v.length===2&&v.every(n=>Number.isSafeInteger(n)&&Math.abs(n)<=30000000);
  if(!res.ok)return fail(res.error||'Product results are unavailable');
  if(res.revision!=='catalog-product-results-v2')return fail('Invalid revision');
  if(!sha(res.snapshot_id)||(expectedSnapshotId!==undefined&&res.snapshot_id!==expectedSnapshotId))return fail('Mismatched snapshot_id');
  if(typeof res.product_id!=='string'||(expectedProductId!==undefined&&res.product_id!==expectedProductId))return fail('Mismatched product_id');
  if(!sha(res.policy_revision)||!Array.isArray(res.results)||res.results.length>20||!Number.isSafeInteger(res.matched_worlds)||res.matched_worlds<res.results.length||!Number.isSafeInteger(res.population_worlds)||res.population_worlds<res.matched_worlds)return fail('Invalid product population/results');
  if(res.next_cursor!==null&&(typeof res.next_cursor!=='string'||!res.next_cursor||res.next_cursor.length>8192))return fail('Invalid page cursor');
  const seen=new Set<string>();
  for(const row of res.results){
    if(!row||row.product_id!==res.product_id||row.status!=='match'||!sha(row.world_id)||!sha(row.observation_id)||seen.has(row.world_id))return fail('Invalid or repeated result identity');
    seen.add(row.world_id);
    if(typeof row.seed!=='string'||row.seed.length>20||!/^(-?[1-9][0-9]*|0)$/.test(row.seed))return fail('Seed must be a canonical signed64 string');
    const seed=BigInt(row.seed);if(seed<-(1n<<63n)||seed>=(1n<<63n))return fail('Seed exceeds signed64 range');
    const anchor=row.anchor;
    if(!anchor||!coord(anchor.coordinate)||!coord(anchor.overworld)||!coord(anchor.nether)||anchor.nether.some((n,i)=>n!==Math.floor(anchor.overworld[i]/8)))return fail('Invalid anchor projection');
    if(!row.scope||!['overworld','nether'].includes(row.scope.dimension)||!Array.isArray(row.rank)||!Array.isArray(row.witnesses)||row.witnesses.length>5000)return fail('Invalid product scope');
    for(const witness of row.witnesses){
      if(!witness||typeof witness!=='object')return fail('Invalid witness');
      const xyz=witness.coordinate;
      if(!witness||!['overworld','nether'].includes(witness.dimension)||!Array.isArray(xyz)||xyz.length!==3||!coord([xyz[0],xyz[2]])||(xyz[1]!==null&&!Number.isSafeInteger(xyz[1]))||!Number.isSafeInteger(witness.distance_squared)||witness.distance_squared<0)return fail('Invalid witness geometry');
    }
  }
  return {ok:true,value:res};
}

export function renderMetricSummary(metric: Record<string, unknown> | undefined, isRealm: boolean) {
  if (!metric) {
    return <span className="text-slate-400">unknown</span>;
  }
  const parts: string[] = [];

  if (metric.count !== undefined) {
    parts.push(`${metric.count} predicted starts${metric.count_complete ? ' (complete)' : ''}`);
  }

  if (metric.farthest_witness_d2 !== undefined) {
    parts.push(`Max distance²: ${metric.farthest_witness_d2}`);
  }

  if (isRealm || metric.score !== undefined) {
    if (metric.score !== undefined) parts.push(`Score: ${metric.score}/1250 points`);
    if(metric.qualifying_core!==undefined)parts.push(`${metric.qualifying_core} × ${metric.qualifying_core} Overworld blocks`);
    if(metric.nether_core!==undefined)parts.push(`${metric.nether_core} × ${metric.nether_core} Nether blocks`);
    const groups=metric.group_scores as Record<string,unknown>|undefined;
    if(groups)parts.push(`Points: OW ${groups.overworld??'unknown'}/845, luxury ${groups.luxury_biomes??'unknown'}/265, Nether ${groups.nether??'unknown'}/140`);
  }

  if (metric.cluster_center !== undefined && Array.isArray(metric.cluster_center)) {
    parts.push(`Center: [${metric.cluster_center.join(', ')}], r²: ${metric.radius_squared ?? 'unknown'}`);
  }

  if (metric.families !== undefined) {
    const fams = Array.isArray(metric.families) ? metric.families.join(', ') : String(metric.families);
    parts.push(`Biome families: ${fams}`);
  }

  if (parts.length === 0) {
    const otherKeys = Object.entries(metric).filter(([k]) => !['count_complete', 'components'].includes(k));
    if (otherKeys.length > 0) {
      return (
        <span>
          {otherKeys
            .map(([k, v]) => `${k.replaceAll('_', ' ')}: ${formatRankItem(v)}`)
            .join(' · ')}
        </span>
      );
    }
    return <span className="text-slate-400">unknown</span>;
  }

  return <span>{parts.join(' · ')}</span>;
}

export function LaunchProductList({
  product,
  snapshotId,
  initialData,
  initialError,
}: {
  product: Product;
  snapshotId: string;
  initialData?: ProductResultsV2Response;
  initialError?: string;
}) {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [cursorStack, setCursorStack] = useState<string[]>([]);
  const [copied, setCopied] = useState<{ worldId: string; failed: boolean } | null>(null);
  const [inspectedWorld, setInspectedWorld] = useState<string | null>(null);

  const key = `${snapshotId}:${product?.id || ''}:${cursor || ''}`;
  const isRealm = product.pillar_id === 'realm' || product.id.startsWith('realm');

  const [state, setState] = useState<{
    key: string;
    loading: boolean;
    data?: ProductResultsV2Response;
    error?: string;
  }>(() => {
    if (initialError) {
      return { key, loading: false, error: initialError };
    }
    if (initialData) {
      return { key, loading: false, data: initialData };
    }
    return { key: '', loading: false };
  });

  const generation = useRef(0);

  useEffect(() => {
    setCursor(undefined);
    setCursorStack([]);
  }, [product?.id, snapshotId]);

  useEffect(() => {
    if (initialData && state.data === initialData && state.key === key) {
      return;
    }
    if (initialError && state.error === initialError && state.key === key) {
      return;
    }

    const controller = new AbortController();
    const current = ++generation.current;
    setCopied(null);
    setInspectedWorld(null);

    if (!product?.id) {
      setState({ key, loading: false, error: 'Product definition is invalid.' });
      return () => controller.abort();
    }
    if (!snapshotId) {
      setState({
        key,
        loading: false,
        error: 'Select an available catalog snapshot to browse product results.',
      });
      return () => controller.abort();
    }

    setState({ key, loading: true });

    requestJson<ProductResultsV2Response>('/api/catalog/product-results', {
      method: 'POST',
      body: {
        revision: 'catalog-product-request-v2',
        snapshot_id: snapshotId,
        product_id: product.id,
        page_size: 20,
        ...(cursor ? { cursor } : {}),
      },
      timeoutMs: 12000,
      signal: controller.signal,
    })
      .then(({ data }) => {
        if (controller.signal.aborted || generation.current !== current) return;
        const validation = validateProductResultsV2(data, snapshotId, product.id);
        if (!validation.ok || !validation.value) {
          setState({
            key,
            loading: false,
            error: validation.error || 'Product results did not match the expected contract.',
          });
          return;
        }
        setState({ key, loading: false, data: validation.value });
      })
      .catch(error => {
        if (!controller.signal.aborted && generation.current === current) {
          let msg = error instanceof Error ? error.message : 'Product results are unavailable.';
          if (error && typeof error === 'object' && 'responseBody' in error) {
            const body = (error as { responseBody?: { error?: string; code?: string } }).responseBody;
            if (body?.code === 'product_gated') {
              msg = `Product is gated for this snapshot: ${body.error || 'requires updated calibration.'}`;
            } else if (body?.error) {
              msg = body.error;
            }
          }
          setState({ key, loading: false, error: msg });
        }
      });

    return () => controller.abort();
  }, [key, product?.id, snapshotId, cursor, initialData, initialError]);

  const active = state.key === key ? state : { key, loading: true };

  return (
    <section aria-label={`${product?.label || 'Product'} launch results`} className="mt-4 space-y-4">
      <div className="space-y-1">
        <h3 className="font-semibold text-base">{product?.label}</h3>
        <p className="text-sm text-slate-300">{product?.criteria_summary}</p>
      </div>

      {isRealm && (
        <aside aria-label="Realm 2048 qualification notice" className="rounded-lg border border-emerald-800/60 bg-emerald-950/40 p-3 text-xs space-y-1">
          <p className="font-semibold text-emerald-200">Realm 2048 Qualification</p>
          <p className="text-slate-300">
            Maximum score: 1,250 points — 845 Overworld, 265 luxury biomes and 140 Nether.
          </p>
          <p className="text-amber-300">
            Larger 4096 and 8192 calibrations are pending and remain gated.
          </p>
        </aside>
      )}

      <p className="text-xs text-slate-400">
        Counts are predicted start coordinates, not a physical census. Distances are horizontal. Nether positions use floor(OW/8) and do not identify a verified portal.
      </p>

      {active.error && (
        <p role="alert" className="text-amber-300">
          {active.error}
        </p>
      )}

      {active.loading && !active.error && (
        <p role="status" className="text-slate-400">
          Loading product results…
        </p>
      )}

      {!active.loading && !active.error && active.data && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400 border-b border-slate-800 pb-2">
            <span>
              {active.data.matched_worlds} retained matches · {active.data.population_worlds} evaluated catalog worlds · {active.data.evidence_label}
            </span>
            <span className="text-slate-500">
              Policy revision: {active.data.policy_revision ? `${active.data.policy_revision.slice(0, 12)}…` : 'default'}
            </span>
          </div>

          {active.data.results.length === 0 && (
            <p className="text-slate-400 py-4">No retained matches in this snapshot. Some worlds may still lack the evidence needed to evaluate this product.</p>
          )}

          {active.data.results.map((row, i) => {
            const rowNumber = i + 1 + cursorStack.length * 20;
            const isWitnessOpen = inspectedWorld === row.world_id;
            const owCoord = row.anchor.overworld;
            const netherCoord = row.anchor?.nether;

            return (
              <article key={row.world_id} className="rounded-lg bg-slate-950 border border-slate-700 p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <strong>#{rowNumber}</strong>
                    <code className="break-all select-all font-mono text-emerald-300">{row.seed}</code>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      className={`${BUTTON} border-slate-700 hover:border-slate-500`}
                      onClick={async () => {
                        try {
                          if (typeof navigator !== 'undefined' && navigator.clipboard) {
                            await navigator.clipboard.writeText(row.seed);
                            setCopied({ worldId: row.world_id, failed: false });
                          } else {
                            setCopied({ worldId: row.world_id, failed: true });
                          }
                        } catch {
                          setCopied({ worldId: row.world_id, failed: true });
                        }
                      }}
                    >
                      {copied?.worldId === row.world_id && !copied.failed ? 'Copied' : 'Copy seed'}
                    </button>
                    <button
                      type="button"
                      className={`${BUTTON} border-slate-700 hover:border-slate-500`}
                      aria-expanded={isWitnessOpen}
                      onClick={() => setInspectedWorld(isWitnessOpen ? null : row.world_id)}
                    >
                      {isWitnessOpen ? 'Hide witnesses' : `View witnesses (${row.witnesses?.length || 0})`}
                    </button>
                  </div>
                </div>

                {copied?.worldId === row.world_id && (
                  <p role="status" className="text-xs text-slate-300">
                    {copied.failed
                      ? 'Clipboard unavailable; select and copy the seed text.'
                      : 'Seed copied.'}
                  </p>
                )}

                <div className="text-xs text-slate-400 space-y-1">
                  <p>
                    <span className="text-slate-300 font-medium">Anchor ({row.anchor.mode}):</span>{' '}
                    Overworld [X {owCoord[0]}, Z {owCoord[1]}]
                    {netherCoord && (
                      <>
                        {' · '}Nether [X {netherCoord[0]}, Z {netherCoord[1]}]{' '}
                        <span className="text-[11px] text-slate-500">(projected floor(OW/8); not a verified portal)</span>
                      </>
                    )}
                  </p>
                  <p>
                    <span className="text-slate-300 font-medium">Scope:</span>{' '}
                    {row.scope?.dimension || 'overworld'}, radius {row.scope?.radius ?? 'unknown'} blocks
                  </p>
                  <p>
                    <span className="text-slate-300 font-medium">Metrics:</span>{' '}
                    {renderMetricSummary(row.metric, isRealm)}
                  </p>
                  {Array.isArray(row.rank) && row.rank.length > 0 && (
                    <p>
                      <span className="text-slate-300 font-medium">Ranking measures:</span>{' '}
                      {row.rank.map(formatRankItem).join(', ')}
                    </p>
                  )}
                </div>

                {isWitnessOpen && (
                  <div className="mt-3 border-t border-slate-800 pt-3 space-y-2">
                    <h4 className="text-xs font-semibold text-slate-300">
                      Predicted Witnesses ({row.witnesses?.length || 0} shown)
                    </h4>
                    {(!row.witnesses || row.witnesses.length === 0) ? (
                      <p className="text-xs text-slate-500">No witnesses recorded in scope.</p>
                    ) : (
                      <div className="max-h-56 overflow-auto border border-slate-800 rounded bg-slate-900/60 p-2">
                        <table className="w-full text-left text-xs">
                          <caption className="sr-only">Witnesses for world {row.world_id}</caption>
                          <thead>
                            <tr className="border-b border-slate-700 text-slate-400">
                              <th scope="col" className="p-1">Feature</th>
                              <th scope="col" className="p-1">Dimension</th>
                              <th scope="col" className="p-1">Coordinates</th>
                              <th scope="col" className="p-1">Distance²</th>
                            </tr>
                          </thead>
                          <tbody>
                            {row.witnesses.map((w, wi) => (
                              <tr key={w.witness_id || `${w.feature}:${wi}`} className="border-b border-slate-800">
                                <td className="p-1 text-slate-300">{w.feature.replaceAll('_', ' ')}</td>
                                <td className="p-1 text-slate-400">{w.dimension}</td>
                                <td className="p-1 font-mono text-slate-300">
                                  {w.coordinate[1] !== null && w.coordinate[1] !== undefined
                                    ? `X ${w.coordinate[0]}, Y ${w.coordinate[1]}, Z ${w.coordinate[2]}`
                                    : `X ${w.coordinate[0]}, Z ${w.coordinate[2]}`}
                                </td>
                                <td className="p-1 text-slate-400">{w.distance_squared}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </article>
            );
          })}

          <nav aria-label="Product pagination" className="flex items-center justify-between pt-2">
            <button
              type="button"
              disabled={cursorStack.length === 0 || active.loading}
              onClick={() => {
                const prev = [...cursorStack];
                const prevCursor = prev.pop();
                setCursorStack(prev);
                setCursor(prevCursor);
              }}
              className={`${BUTTON} border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:border-slate-500`}
            >
              Previous 20
            </button>
            <span className="text-xs text-slate-400">
              Page {cursorStack.length + 1}
            </span>
            <button
              type="button"
              disabled={!active.data.next_cursor || active.loading}
              onClick={() => {
                if (active.data?.next_cursor) {
                  setCursorStack(prev => [...prev, cursor || '']);
                  setCursor(active.data.next_cursor);
                }
              }}
              className={`${BUTTON} border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:border-slate-500`}
            >
              Next 20
            </button>
          </nav>
        </>
      )}
    </section>
  );
}

FILE web-ui/src/catalog/NetherDetails.tsx
import type {BiomeWitnessPoint} from './types';
import {featureLabel} from './constants';

export function NetherDetails({structures,bounds,witnesses}:{structures:Record<string,[number,number][]>;bounds:[number,number,number,number];witnesses:BiomeWitnessPoint[]}){
  const [x0,z0,x1,z1]=bounds,ax=x0+512,az=z0+512;
  return <details className="my-3 rounded border border-amber-900 p-3 text-xs space-y-3">
    <summary className="cursor-pointer font-semibold text-amber-200">Nether observations · fixed 1024 × 1024 blocks</summary>
    <p>Projected reference X={ax}, Z={az}. These are Nether block coordinates, calculated by flooring the Overworld anchor divided by 8. A generated portal location has not been established.</p>
    <p>Bounds: X [{x0}, {x1}), Z [{z0}, {z1}); upper edges excluded.</p>
    <svg role="img" aria-label="Predicted Nether structure starts; north up, east right" viewBox={`${x0-24} ${z0-24} 1072 1072`} className="w-full max-w-sm bg-slate-900">
      <rect x={x0} y={z0} width={1024} height={1024} fill="none" stroke="#fbbf24" strokeWidth={3}/>
      <path d={`M ${ax-12} ${az} H ${ax+12} M ${ax} ${az-12} V ${az+12}`} stroke="white" strokeWidth={3}/>
      {Object.entries(structures).flatMap(([feature,points])=>points.map(([x,z])=><circle key={`${feature}:${x}:${z}`} cx={x} cy={z} r={6} fill={feature==='structure.fortress'?'#fb923c':'#a78bfa'}><title>{`${featureLabel(feature)} predicted start: X=${x}, Z=${z}`}</title></circle>))}
    </svg>
    {Object.entries(structures).map(([feature,points])=><section key={feature}><h4 className="font-semibold">{featureLabel(feature)} · {points.length} saved predicted starts</h4><p className="select-all break-words">{points.map(([x,z])=>`(${x}, ${z})`).join(' · ')||'No saved positive evidence.'}</p></section>)}
    <h4 className="font-semibold">Saved Nether biome witnesses</h4>
    <ul>{witnesses.map(w=><li key={w.feature}>{featureLabel(w.feature)}: X={w.x}, Y={w.y}, Z={w.z}; horizontal distance {Math.sqrt(w.distance_squared).toFixed(1)} Nether blocks.</li>)}</ul>
    {!witnesses.length&&<p>No saved biome witnesses. Missing samples do not establish absence.</p>}
  </details>;
}

FILE web-ui/src/catalog/PublicHarvestStatus.tsx
import {useEffect,useRef,useState} from 'react';
import {requestJson} from '../utils/network';

interface PublicState {
  ok:boolean;configured:boolean;state:string;consumed?:number;reason?:string|null;
  total_budget_seconds?:number;population_worlds?:number;retained_worlds?:number;
  queue?:{jobs:Record<string,number>;campaigns:Array<{id:string;state:string;scheduled_samples:number}>};
}

export function PublicHarvestStatus(){
  const [state,setState]=useState<PublicState|null>(null),[error,setError]=useState('');
  const [busy,setBusy]=useState(false);const generation=useRef(0),active=useRef(true),busyRef=useRef(false);
  const refresh=async(signal?:AbortSignal)=>{
    if(busyRef.current)return;
    const epoch=++generation.current;
    try{
      const {data}=await requestJson<PublicState>('/api/catalog/automation-status',{method:'GET',signal,timeoutMs:8000});
      if(!active.current||signal?.aborted||epoch!==generation.current)return;
      if(!data.ok||typeof data.configured!=='boolean'||typeof data.state!=='string')throw Error('Public worker status is unavailable.');
      setState(data);setError('');
    }catch(e){if(active.current&&!signal?.aborted&&epoch===generation.current)setError(e instanceof Error?e.message:String(e));}
  };
  useEffect(()=>{
    active.current=true;let controller=new AbortController();let timer:ReturnType<typeof setTimeout>;
    const poll=async()=>{await refresh(controller.signal);if(active.current)timer=setTimeout(()=>{controller=new AbortController();void poll();},3000);};
    void poll();return()=>{active.current=false;generation.current++;controller.abort();clearTimeout(timer);};
  },[]);
  const control=async(action:'pause'|'resume'|'allocate')=>{
    if(busyRef.current)return;busyRef.current=true;setBusy(true);generation.current++;
    try{
      const {data}=await requestJson<PublicState>('/api/catalog/automation-control',{method:'POST',body:{revision:'catalog-automation-control-v2',action},timeoutMs:8000});
      if(!active.current)return;
      if(!data.ok)throw Error('Public worker action was rejected.');
      setState(data);setError('');
    }catch(e){if(active.current)setError(e instanceof Error?e.message:String(e));}
    finally{busyRef.current=false;if(active.current)setBusy(false);}
  };
  const spent=state?.consumed||0,total=state?.total_budget_seconds||600;
  return <aside aria-label="Independent public harvesting" className="mx-auto my-3 w-full max-w-7xl rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs space-y-2">
    <h2 className="font-semibold text-emerald-300">Public harvesting · independent of personal search</h2>
    {error&&<p role="alert" className="text-amber-300">{error}</p>}
    {!state&&!error&&<p role="status">Loading public worker status…</p>}
    {state&&!state.configured&&<p className="text-slate-400">Public harvesting is not configured on this server. Personal search remains available.</p>}
    {state?.configured&&<>
      <p role="status">{state.state} · {state.population_worlds} evaluated worlds · {state.retained_worlds} retained worlds</p>
      <p>{Math.ceil(spent)} / {total} seconds of the current public compute budget used.</p>
      <progress aria-label="Public compute budget used" value={Math.min(spent,total)} max={total} className="w-full" />
      {state.queue&&<p>{Object.entries(state.queue.jobs).map(([name,count])=>`${count} ${name}`).join(' · ')||'No public jobs queued.'}</p>}
      {state.reason&&<p className="text-amber-200">{state.reason}</p>}
      <div className="flex flex-wrap gap-3">
        {state.state==='active'?<button type="button" disabled={busy} onClick={()=>void control('pause')}>Pause public harvesting</button>:<>
          <button type="button" disabled={busy||spent>=total} onClick={()=>void control('resume')}>Resume with remaining budget</button>
          <button type="button" disabled={busy} onClick={()=>void control('allocate')}>Resume with a new 10-minute budget</button>
        </>}
      </div>
      <p className="text-slate-400">These controls affect the public worker. A running world drains to its checkpoint; the personal sweep has its own stop control.</p>
    </>}
  </aside>;
}
