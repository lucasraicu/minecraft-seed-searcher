# Accuracy UI actual source changes; interactive browser QA user-waived
Codex/Gemini automated checks required. Existing4pillars preserved. Addper-snapshotworld_spawn_estimated/world_spawn_observed onlywhenimmutableaccuracybundleavailable. V2queriesgeneration-pinned, 3borders, samplesonceworldalignment. Semantics XZworldreference, no landing/safety/physicalcensus claims. Rawcoarse missingbiome required predicates remainpotentialworlds ratherthanseedreject. Separate details listpotentialseedstrings+inspectreadsavedevidence, nevergamejobs. Favoritesv1storage accepts2additionalmodeenumvalues, oldentriesunchanged. Hooksabortstalequery/detailresponses. 200worldsestimated+3observed available in rehearsal; notpublishedyet. Existing6Nodecontract/renderfiles pass,frontendbuildpassed beforelatestpotentialpanel/cachechange; rerunplanned. Review actualcodeexcerptsbelow neutrally for real binding/UX/error bugs; no tool/testclaims.

## useCatalogState.ts:1
```tsx
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type {CatalogStatusResponse,CatalogCapabilitiesResponse,CatalogSnapshotInfo,CatalogCandidate,CatalogDetailResponse,CatalogFavorite,CatalogPreset,FilterRow,BorderSide,AnchorMode,CatalogQueryPayload} from './types';
import {CATEGORY_PRESETS,FAVORITES_STORAGE_KEY,MAX_COMPARE_SEEDS,DEFAULT_PAGE_SIZE} from './constants';
import {fetchCatalogStatus,fetchCatalogCapabilities,fetchCatalogSnapshots,postCatalogQuery,fetchCatalogDetail} from './api';
import {validFavorites, serializeRows} from './validation';

export function useCatalogState() {
  const [status,setStatus]=useState<CatalogStatusResponse|null>(null);
  const [capabilities,setCapabilities]=useState<CatalogCapabilitiesResponse|null>(null);
  const [snapshots,setSnapshots]=useState<CatalogSnapshotInfo[]>([]);
  const [isInitializing,setIsInitializing]=useState(true),[initError,setInitError]=useState<string|null>(null);
  const [selectedSnapshotId,setSelectedSnapshotId]=useState('');
  const [borderSide,setBorderSide]=useState<BorderSide>(2048),[anchorMode,setAnchorMode]=useState<AnchorMode>('recommended');
  const [profile,setProfile]=useState('balanced_survival'),[activePresetId,setActivePresetId]=useState<string|null>('general');
  const [filterRows,setFilterRows]=useState<FilterRow[]>(()=>CATEGORY_PRESETS[0].rows.map((r,i)=>({...r,id:`initial-${i}`} as FilterRow)));
  const [results,setResults]=useState<CatalogCandidate[]>([]),[nextCursor,setNextCursor]=useState<string|null>(null);
  const [isTruncated,setIsTruncated]=useState(false);
  const [unresolvedWorlds,setUnresolvedWorlds]=useState(0);
  const [unresolvedCandidates,setUnresolvedCandidates]=useState<Array<{world_id:string;seed:string;layout_id:string;anchor:number[];border_side:number;status:string;reason:string}>>([]);
  const [totalMatched,setTotalMatched]=useState(0),[hasQueried,setHasQueried]=useState(false);
  const [isQueryLoading,setIsQueryLoading]=useState(false),[isFetchingMore,setIsFetchingMore]=useState(false);
  const [queryError,setQueryError]=useState<string|null>(null),[evidenceLabel,setEvidenceLabel]=useState('Research predictions; structure starts and sampled biome witnesses, not generated-world certification.');
  const [comparedCandidates,setComparedCandidates]=useState<CatalogCandidate[]>([]),[isCompareOpen,setIsCompareOpen]=useState(false);
  const [storageError,setStorageError]=useState<string|null>(null);
  const [favorites,setFavorites]=useState<CatalogFavorite[]>(()=>{
    try {return validFavorites(JSON.parse(localStorage.getItem(FAVORITES_STORAGE_KEY)||'[]'));} catch {return [];}
  });
  useEffect(()=>{try {validFavorites(JSON.parse(localStorage.getItem(FAVORITES_STORAGE_KEY)||'[]'));}
    catch {setStorageError('Saved favorites could not be read. Original storage was preserved; import a valid backup or clear favorites.');}},[]);
  const [isFavoritesOpen,setIsFavoritesOpen]=useState(false),[isExportOpen,setIsExportOpen]=useState(false);
  const [inspectedCandidate,setInspectedCandidate]=useState<{seedString:string;snapshotId:string;worldId:string;layoutId:string}|null>(null);
  const [detailData,setDetailData]=useState<CatalogDetailResponse|null>(null),[isDetailLoading,setIsDetailLoading]=useState(false),[detailError,setDetailError]=useState<string|null>(null);
  const requestEpoch=useRef(0),queryAbort=useRef<AbortController|null>(null),detailAbort=useRef<AbortController|null>(null);
  const detailEpoch=useRef(0);
  const pinnedHeader=snapshots.find(s=>s.snapshot_id===selectedSnapshotId)?.header || (status?.snapshot_id===selectedSnapshotId ? status.header : undefined);
  const accuracySnapshot=snapshots.find(s=>s.snapshot_id===selectedSnapshotId);
  const accuracyModes=accuracySnapshot?.accuracy_anchor_modes||[];
  useEffect(()=>{if(anchorMode.startsWith('world_spawn_')&&!accuracyModes.includes(anchorMode))setAnchorMode('recommended');},[selectedSnapshotId,JSON.stringify(accuracyModes),anchorMode]);
  const currentQueryPayload=useMemo<CatalogQueryPayload>(()=>({request_revision:accuracySnapshot?.accuracy_generation?'catalog-query-accuracy-v1':'catalog-query-v1',...(accuracySnapshot?.accuracy_generation?{accuracy_generation:accuracySnapshot.accuracy_generation}:{}),edition:'bedrock',dimension:'overworld',
    game_build_id:String(pinnedHeader?.game_build_id||''),world_settings_id:String(pinnedHeader?.world_settings_id||''),
    catalog_snapshot_id:selectedSnapshotId,evidence_policy:'predicted_observations_v1',fallback_profile:profile,
    border_side:borderSide,anchor_mode:anchorMode,rows:serializeRows(filterRows)}),[pinnedHeader,selectedSnapshotId,profile,borderSide,anchorMode,filterRows,accuracySnapshot?.accuracy_generation]);
  const payloadKey=JSON.stringify(currentQueryPayload);

  const persistFavorites=useCallback((next:CatalogFavorite[])=>{
    try {const valid=validFavorites(next);localStorage.setItem(FAVORITES_STORAGE_KEY,JSON.stringify(valid));setFavorites(valid);setStorageError(null);return {success:true,message:'Saved on this device.'};}
    catch (error) {const message=`Could not save favorites: ${error instanceof Error?error.message:String(error)}`;setStorageError(message);return {success:false,message};}
  },[]);
  const toggleFavorite=useCallback((c:CatalogCandidate)=>{
    const snapshotId=String(c.snapshot_id||selectedSnapshotId),id=`${snapshotId}:${c.world_id}:${c.layout_id}`;
    const existing=favorites.some(f=>f.id===id);
    return persistFavorites(existing?favorites.filter(f=>f.id!==id):[...favorites,{id,seed:c.seed,world_id:c.world_id,snapshot_id:snapshotId,layout_id:c.layout_id,border_side:c.border_side,anchor_mode:anchorMode,score:c.score,saved_at:Date.now(),bounds:c.bounds}]);
  },[favorites,persistFavorites,selectedSnapshotId,anchorMode]);
  const removeFavorite=useCallback((id:string)=>persistFavorites(favorites.filter(f=>f.id!==id)),[favorites,persistFavorites]);
  const clearFavorites=useCallback(()=>persistFavorites([]),[persistFavorites]);
  const importFavorites=useCallback((items:CatalogFavorite[])=>{
    try {const next=new Map(favorites.map(f=>[f.id,f]));for(const f of validFavorites(items))next.set(f.id,f);return persistFavorites([...next.values()]);}
    catch(error) {return {success:false,message:error instanceof Error?error.message:String(error)};}
  },[favorites,persistFavorites]);
  const toggleCompare=useCallback((c:CatalogCandidate)=>setComparedCandidates(prev=>{
    const enriched={...c,snapshot_id:c.snapshot_id||selectedSnapshotId};
    const exists=prev.some(x=>x.world_id===c.world_id&&x.layout_id===c.layout_id&&x.snapshot_id===enriched.snapshot_id);
    return exists?prev.filter(x=>!(x.world_id===c.world_id&&x.layout_id===c.layout_id&&x.snapshot_id===enriched.snapshot_id)):prev.length<MAX_COMPARE_SEEDS?[...prev,enriched]:prev;
  }),[selectedSnapshotId]);
  const removeCompared=useCallback((c:CatalogCandidate)=>setComparedCandidates(prev=>prev.filter(x=>!(x.world_id===c.world_id&&x.layout_id===c.layout_id&&x.snapshot_id===c.snapshot_id))),[]);
  const clearCompared=useCallback(()=>setComparedCandidates([]),[]);

  const inspectCandidate=useCallback(async(seedString:string,snapshotId:string,worldId:string,layoutId:string)=>{
    detailAbort.current?.abort();const controller=new AbortController();detailAbort.current=controller;const epoch=++detailEpoch.current;
    setInspectedCandidate({seedString,snapshotId,worldId,layoutId});setDetailData(null);setDetailError(null);setIsDetailLoading(true);
    const hash=`#catalog?snapshot=${encodeURIComponent(snapshotId)}&world=${encodeURIComponent(worldId)}&layout=${encodeURIComponent(layoutId)}`;
    if(window.location.hash!==hash)window.history.pushState(null,'',hash);
    try {const data=await fetchCatalogDetail(snapshotId,worldId,layoutId,controller.signal);
      if(epoch!==detailEpoch.current||controller.signal.aborted)return;
      if(!data.ok)throw Error(data.error||'Saved layout unavailable');
      if(data.snapshot_id!==snapshotId||data.world_id!==worldId||data.layout?.layout_id!==layoutId)throw Error('Detail identity mismatch');
      setDetailData(data);
    } catch(error) {if(!controller.signal.aborted&&epoch===detailEpoch.current)setDetailError(error instanceof Error?error.message:String(error));}
    finally {if(epoch===detailEpoch.current)setIsDetailLoading(false);}
  },[]);
  const closeDetail=useCallback(()=>{
    detailEpoch.current++;detailAbort.current?.abort();setInspectedCandidate(null);setDetailData(null);setDetailError(null);setIsDetailLoading(false);
    if(window.location.hash.startsWith('#catalog?'))window.history.pushState(null,'','#catalog');
  },[]);
  useEffect(()=>{
    const controller=new AbortController();let active=true;
    const hash=()=>{
      if(!window.location.hash.startsWith('#catalog'))return;
      const params=new URLSearchParams(window.location.hash.split('?')[1]||'');
      const sid=params.get('snapshot'),wid=params.get('world'),lid=params.get('layout');
      if(sid&&wid&&lid){setSelectedSnapshotId(sid);void inspectCandidate('Loading seed…',sid,wid,lid);}
      else {detailEpoch.current++;detailAbort.current?.abort();setInspectedCandidate(null);setDetailData(null);setIsDetailLoading(false);}
    };
    void Promise.allSettled([fetchCatalogStatus(controller.signal),fetchCatalogCapabilities(controller.signal),fetchCatalogSnapshots(controller.signal)]).then(([stat,cap,snaps])=>{
      if(!active)return;
      if(stat.status==='fulfilled'&&stat.value.ok){setStatus(stat.value);if(stat.value.snapshot_id)setSelectedSnapshotId(stat.value.snapshot_id);}
      else setInitError(stat.status==='rejected'?String(stat.reason):'Catalog unavailable');
      if(cap.status==='fulfilled'&&cap.value.ok){setCapabilities(cap.value);if(cap.value.evidence_label)setEvidenceLabel(cap.value.evidence_label);}
      if(snaps.status==='fulfilled'&&snaps.value.ok)setSnapshots(snaps.value.snapshots);
      hash();setIsInitializing(false);
    });
    window.addEventListener('hashchange',hash);window.addEventListener('popstate',hash);
    return ()=>{active=false;controller.abort();queryAbort.current?.abort();detailAbort.current?.abort();requestEpoch.current++;detailEpoch.current++;window.removeEventListener('hashchange',hash);window.removeEventListener('popstate',hash);};
  },[inspectCandidate]);

  useEffect(()=>{
    requestEpoch.current++;queryAbort.current?.abort();setResults([]);setNextCursor(null);setTotalMatched(0);setUnresolvedWorlds(0);setUnresolvedCandidates([]);setIsTruncated(false);setHasQueried(false);setQueryError(null);setIsQueryLoading(false);setIsFetchingMore(false);
  },[payloadKey]);
  const selectPreset=useCallback((preset:CatalogPreset)=>{setActivePresetId(preset.id);setProfile(preset.fallback_profile);setFilterRows(preset.rows.map((r,i)=>({...r,id:`preset-${i}-${Date.now()}`} as FilterRow)));},[]);
  const execute=useCallback(async(more:boolean)=>{
    if(!selectedSnapshotId||!pinnedHeader){setQueryError('Selected snapshot metadata is unavailable.');return;}
    if(more&&!nextCursor)return;
    queryAbort.current?.abort();const controller=new AbortController();queryAbort.current=controller;const epoch=++requestEpoch.current;
    setQueryError(null);setHasQueried(true);if(more)setIsFetchingMore(true);else {setIsQueryLoading(true);setResults([]);setNextCursor(null);}
    try {const body={request:currentQueryPayload,page_size:DEFAULT_PAGE_SIZE,...(more?{cursor:nextCursor}: {})};const data=await postCatalogQuery(body,controller.signal);
      if(controller.signal.aborted||epoch!==requestEpoch.current)return;
      if(!data.ok)throw Error(data.error||'Catalog query failed');
      if(data.snapshot_id!==selectedSnapshotId)throw Error('Query snapshot identity mismatch');
      const incoming=data.results.map(c=>({...c,snapshot_id:data.snapshot_id}));
      setResults(prev=>more?[...prev,...incoming.filter(c=>!prev.some(p=>p.world_id===c.world_id))]:incoming);
      setNextCursor(data.next_cursor);setUnresolvedWorlds(data.unresolved_worlds||0);setUnresolvedCandidates(data.unresolved_candidates||[]);setTotalMatched(data.matched_worlds);setIsTruncated(data.truncated);setEvidenceLabel(data.evidence_label);
    } catch(error) {if(!controller.signal.aborted&&epoch===requestEpoch.current)setQueryError(error instanceof Error?error.message:String(error));}
    finally {if(epoch===requestEpoch.current){setIsQueryLoading(false);setIsFetchingMore(false);}}
  },[selectedSnapshotId,pinnedHeader,nextCursor,currentQueryPayload]);
  const runQuery=useCallback(()=>execute(false),[execute]),loadMore=useCallback(()=>execute(true),[execute]);
  return {status,capabilities,snapshots,selectedSnapshotId,setSelectedSnapshotId,borderSide,setBorderSide,anchorMode,setAnchorMode,profile,setProfile,
    activePresetId,setActivePresetId,filterRows,setFilterRows,selectPreset,results,nextCursor,totalMatched,unresolvedWorlds,unresolvedCandidates,isTruncated,isQueryLoading,isFetchingMore,queryError:queryError||storageError,
    evidenceLabel,hasQueried,runQuery,loadMore,comparedCandidates,isCompareOpen,setIsCompareOpen,toggleCompare,removeCompared,clearCompared,
    favorites,isFavoritesOpen,setIsFavoritesOpen,toggleFavorite,removeFavorite,clearFavorites,importFavorites,inspectedCandidate,detailData,isDetailLoading,detailError,
    inspectCandidate,closeDetail,isExportOpen,setIsExportOpen,currentQueryPayload,isInitializing,initError};
```

## CatalogWorkspace.tsx:20
```tsx

export function CatalogWorkspace() {
  const [pillar, setPillar] = useState<'realm'|'presets'|'personalized'|'rare'>('personalized');
  const {
    status,
    capabilities,
    snapshots,
    selectedSnapshotId,
    setSelectedSnapshotId,
    borderSide,
    setBorderSide,
    anchorMode,
    setAnchorMode,
    profile,
    setProfile,
    activePresetId,
    setActivePresetId,
    filterRows,
    setFilterRows,
    selectPreset,
    results,
    nextCursor,
    totalMatched,
    unresolvedWorlds,
    unresolvedCandidates,
    isTruncated,
    isQueryLoading,
    isFetchingMore,
    queryError,
    evidenceLabel,
    hasQueried,
    runQuery,
    loadMore,
    comparedCandidates,
    isCompareOpen,
    setIsCompareOpen,
    toggleCompare,
    removeCompared,
    clearCompared,
    favorites,
    isFavoritesOpen,
    setIsFavoritesOpen,
    toggleFavorite,
    removeFavorite,
    clearFavorites,
    importFavorites,
    inspectedCandidate,
    detailData,
    isDetailLoading,
    detailError,
    inspectCandidate,
    closeDetail,
    isExportOpen,
    setIsExportOpen,
    currentQueryPayload,
    isInitializing,
    initError,
  } = useCatalogState();

  const presets = capabilities?.presets?.length ? capabilities.presets : CATEGORY_PRESETS;
  const profiles = capabilities?.profiles?.length ? capabilities.profiles : DEFAULT_PROFILES;
  const borderSides = capabilities?.border_sides?.length ? capabilities.border_sides : BORDER_SIDES;
  const anchorModes = [...(capabilities?.anchor_modes?.length ? capabilities.anchor_modes : ANCHOR_MODES),...(snapshots.find(s=>s.snapshot_id===selectedSnapshotId)?.accuracy_anchor_modes||[])];

  const isAvailable = status ? status.available : true;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="bg-slate-950 border-b border-slate-800 px-4 sm:px-6 py-3 sticky top-0 z-30 shadow-md">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
          {/* Title & Badge */}
          <div className="flex items-center gap-3">
            <h1 className="text-base sm:text-lg font-bold tracking-tight text-white flex items-center gap-2">
              <span className="text-emerald-400">&bull;</span>
              <span>Private Catalog</span>
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-950 text-emerald-400 border border-emerald-800">
              Pilot Index
            </span>
          </div>
```

## CatalogWorkspace.tsx:240
```tsx
                ))}
              </div>
            </div>

            {/* Anchor Mode Selector */}
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300 uppercase tracking-wider text-[11px] block">
                Anchor Mode
              </label>
              <div className="flex gap-2">
                {anchorModes.map(mode => (
                  <button
                    key={ANCHOR_LABELS[mode]}
                    type="button"
                    onClick={() => setAnchorMode(mode)}
                    className={`flex-1 py-1.5 px-2 rounded-lg border text-center font-medium capitalize transition-colors ${
                      anchorMode === mode
                        ? 'bg-emerald-950 text-emerald-300 border-emerald-500'
                        : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    {ANCHOR_LABELS[mode]}
                  </button>
                ))}
              </div>
            </div>

            <p className="text-xs text-slate-400">Origin is (0, 0), not world spawn. Recommended settlement selects the best saved center for your request. World spawn modes appear when this snapshot has saved anchors. An estimate is not game-observed spawn; neither mode establishes player landing, terrain height or safety.</p>
            {unresolvedWorlds>0 && <details className="text-xs text-amber-200">
              <summary>{unresolvedWorlds} additional retained worlds need refinement</summary>
              <p>Required evidence is incomplete. These are potential candidates, separate from matches under the selected evidence policy. Inspecting a world reads saved data; it does not start a game check.</p>
              <ul>{unresolvedCandidates.map(candidate=><li key={candidate.world_id} className="mt-1"><button type="button" className="underline" onClick={()=>inspectCandidate(candidate.seed,selectedSnapshotId,candidate.world_id,candidate.layout_id)}>Inspect {candidate.seed}</button> · center {candidate.anchor.join(', ')}</li>)}</ul>
              {unresolvedWorlds>unresolvedCandidates.length && <p>Showing the first {unresolvedCandidates.length} potential candidates.</p>}
            </details>}
            {/* Profile Dropdown */}
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300 uppercase tracking-wider text-[11px] block">
                Evaluation Profile
              </label>
              <select
                value={profile}
                onChange={e => setProfile(e.target.value)}
                aria-label="Evaluation scoring profile"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-100 font-medium focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                {profiles.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.label || p.id}
                  </option>
```

## DetailModal.tsx:72
```tsx
      setCopyError('Clipboard unavailable. Select and copy the seed or address manually.');
    }
  };

  const layout = detail?.layout;
  const borderSide = (layout?.border_side as BorderSide) || 4096;
  const anchor = (layout?.anchor as [number, number] | string) || [0, 0];
  const anchorMode:AnchorMode = detail?.anchor_evidence?.mode || (Array.isArray(anchor) && anchor[0]===0 && anchor[1]===0 ? 'origin' : 'recommended');

  // Compute bounds from layout side and anchor if not explicit
  let bounds: [number, number, number, number] = [-borderSide / 2, -borderSide / 2, borderSide / 2, borderSide / 2];
  if (Array.isArray(anchor) && anchor.length === 2) {
    const half = borderSide / 2;
    bounds = [anchor[0] - half, anchor[1] - half, anchor[0] + half, anchor[1] + half];
  }

  const structures = detail?.structures || {};
  const biomeWitnesses = detail?.biome_witnesses || [];
  const totalStructurePoints = Object.values(structures).reduce((acc, pts) => acc + pts.length, 0);
```

## DetailModal.tsx:190
```tsx

              {detail?.anchor_evidence && <p className="text-xs text-amber-200 mb-3">{ANCHOR_LABELS[anchorMode]}: X/Z only. Player landing, usable ground height and safety are unverified.</p>}
              {detail?.accuracy && <section className="text-xs border border-slate-700 rounded p-3 mb-3" aria-label="Biome refinement coverage">
                <p>{detail.accuracy.interpretation}</p>
                {detail.accuracy.tiles.length===0 ? <p>No exact-scope tiles saved for this world yet. Coarse missing witnesses do not prove absence.</p> : <ul>{detail.accuracy.tiles.map(tile=><li key={tile.tile_id}>{tile.provider} at Y={tile.y}: [{tile.bounds.join(', ')}), half-open X/Z bounds. Proof applies only to this provider and saved blocks.</li>)}</ul>}
              </section>}
              {/* Layout metadata cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-slate-400">Border Dimensions</div>
                  <div className="text-sm font-semibold text-slate-100 mt-1">{borderSide} &times; {borderSide}</div>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-slate-400">{detail?.anchor_evidence ? ANCHOR_LABELS[anchorMode] : 'Saved center'}</div>
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
```

## CandidateCard.tsx:1
```tsx
import { useState } from 'react';
import type { CatalogCandidate } from './types';
import { featureLabel, ANCHOR_LABELS } from './constants';

interface CandidateCardProps {
  candidate: CatalogCandidate;
  snapshotId: string;
  isCompared: boolean;
  canCompare: boolean;
```

## CandidateCard.tsx:48
```tsx
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
```

## validation.ts:1
```tsx
import type {CatalogFavorite,FilterRow} from './types';

export function serializeRows(rows:FilterRow[]):Array<Record<string,unknown>> {
  return rows.map(row=>({rule:row.rule,kind:row.kind,
    scope:row.scope.kind==='inside_border'?{kind:'inside_border'}:{kind:'near_base',radius:row.scope.radius},
    ...(row.rule==='preferred'?{importance:row.importance||3}:{}),
    ...(row.kind==='structure_count'?{feature:row.feature,at_least:row.at_least}:{any_of:row.any_of})}));
}

export function validFavorites(value:unknown):CatalogFavorite[] {
  if(!Array.isArray(value)||value.length>1000)throw Error('Favorites must contain at most 1000 entries');
  const seen=new Set<string>();const result:CatalogFavorite[]=[];
  for(const f of value){
    if(!f||typeof f!=='object'||typeof f.seed!=='string'||! /^-?(0|[1-9][0-9]*)$/.test(f.seed)||f.seed==='-0')throw Error('Invalid seed string');
    const seed=BigInt(f.seed);if(seed<-(1n<<63n)||seed>=(1n<<63n))throw Error('Seed exceeds signed64 range');
    for(const key of ['world_id','layout_id','snapshot_id'])if(typeof f[key]!=='string'||! /^[a-f0-9]{64}$/.test(f[key]))throw Error('Invalid favorite identity');
    const id=`${f.snapshot_id}:${f.world_id}:${f.layout_id}`;
    if(f.id!==id||![2048,4096,8192].includes(f.border_side)||!['origin','recommended','world_spawn_estimated','world_spawn_observed'].includes(f.anchor_mode)||!Number.isFinite(f.score)||!Number.isFinite(f.saved_at))throw Error('Invalid favorite metadata');
    if(f.bounds&&(!Array.isArray(f.bounds)||f.bounds.length!==4||!f.bounds.every(Number.isSafeInteger)))throw Error('Invalid favorite bounds');
    if(!seen.has(id)){seen.add(id);result.push({id,seed:f.seed,world_id:f.world_id,layout_id:f.layout_id,snapshot_id:f.snapshot_id,border_side:f.border_side,
      anchor_mode:f.anchor_mode,score:f.score,saved_at:f.saved_at,...(f.bounds?{bounds:f.bounds}: {})});}
  }
  return result;
}
```
