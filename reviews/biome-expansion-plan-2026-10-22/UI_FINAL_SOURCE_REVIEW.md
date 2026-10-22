# Final UI source review
Read-only review of approved implementation; sources below are isolated and authoritative. No implementation/plan approval request. Migration is running; do not launch jobs or commands. Find concrete semantic regressions, snapshot capability negotiation, races, gate enforcement, strict query shape, reserve vs union semantics. All selected snapshot V3 features are active except 2 contextual structures. Historical V2 remains supported. Back end accepts no generic-query view. Product-results accepts view and binds cursor. Interactive browser waived, coordinator runs automated SSR and build.

## useCatalogState.ts
```tsx
import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type {CatalogStatusResponse,CatalogCapabilitiesResponse,CatalogSnapshotInfo,CatalogCandidate,CatalogDetailResponse,CatalogFavorite,CatalogPreset,FilterRow,BorderSide,AnchorMode,CatalogQueryPayload} from './types';
import {CATEGORY_PRESETS,FAVORITES_STORAGE_KEY,MAX_COMPARE_SEEDS,DEFAULT_PAGE_SIZE,KNOWN_STRUCTURES,KNOWN_BIOMES,ALL_FEATURES_V3,isV3Feature} from './constants';
import {fetchCatalogStatus,fetchCatalogCapabilities,fetchCatalogSnapshots,postCatalogQuery,fetchCatalogDetail} from './api';
import {validFavorites, serializeRows, filterLimitsError} from './validation';

export function useCatalogState() {
  const [status,setStatus]=useState<CatalogStatusResponse|null>(null);
  const [capabilities,setCapabilities]=useState<CatalogCapabilitiesResponse|null>(null);
  const [snapshots,setSnapshots]=useState<CatalogSnapshotInfo[]>([]);
  const [isInitializing,setIsInitializing]=useState(true),[initError,setInitError]=useState<string|null>(null);
  const [selectedSnapshotId,setSelectedSnapshotId]=useState('');
  const [borderSide,setBorderSide]=useState<BorderSide>(2048),[requestedAnchorMode,setAnchorMode]=useState<AnchorMode>('recommended');
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
  const detailEpoch=useRef(0),queryAllPending=useRef(false);
  const selectedSnapshot=snapshots.find(s=>s.snapshot_id===selectedSnapshotId);
  const pinnedHeader=selectedSnapshot?.header || (status?.snapshot_id===selectedSnapshotId ? status.header : undefined);
  const snapshotRevision=selectedSnapshot?.revision || (status?.snapshot_id===selectedSnapshotId ? status.revision : undefined);
  const isV3Snapshot=snapshotRevision==='catalog-snapshot-v3';
  const isV2Snapshot=isV3Snapshot || snapshotRevision==='catalog-snapshot-v2';
  const legacyIds=new Set([...KNOWN_STRUCTURES,...KNOWN_BIOMES].map(f=>f.id));
  const unsupportedLegacyFilters=!isV2Snapshot&&filterRows.some(r=>(r.kind==='structure_count'?[r.feature]:r.any_of).some(id=>!legacyIds.has(id)));
  const unsupportedV2Filters=!isV3Snapshot&&filterRows.some(r=>(r.kind==='structure_count'?[r.feature]:r.any_of).some(id=>isV3Feature(id)));
  const accuracyModes=isV2Snapshot?(selectedSnapshot?.anchor_modes||status?.anchor_modes||['recommended','origin','world_spawn_estimated']):(selectedSnapshot?.accuracy_anchor_modes||[]);
  const anchorMode=requestedAnchorMode.startsWith('world_spawn_')&&!accuracyModes.includes(requestedAnchorMode)?'recommended':requestedAnchorMode;
  const accuracyGeneration=selectedSnapshot?.accuracy_generation;
  const limitsError=filterLimitsError(filterRows);
  const snapshotCapabilities=capabilities?.snapshot_id===selectedSnapshotId?capabilities:null;
  useEffect(()=>{
    if(!selectedSnapshotId)return;
    const controller=new AbortController();
    void fetchCatalogCapabilities(controller.signal,selectedSnapshotId).then(value=>{
      if(!controller.signal.aborted&&value.ok&&value.snapshot_id===selectedSnapshotId)setCapabilities(value);
    }).catch(error=>{if(!controller.signal.aborted)setQueryError(String(error));});
    return ()=>controller.abort();
  },[selectedSnapshotId]);
  const currentQueryPayload=useMemo<CatalogQueryPayload>(()=>({
    request_revision: isV3Snapshot ? 'catalog-query-v3' : isV2Snapshot ? 'catalog-query-v2' : accuracyGeneration ? 'catalog-query-accuracy-v1' : 'catalog-query-v1',
    ...(accuracyGeneration?{accuracy_generation:accuracyGeneration}:{}),
    edition:'bedrock',
    dimension:'overworld',
    game_build_id:String(pinnedHeader?.game_build_id||''),
    world_settings_id:String(pinnedHeader?.world_settings_id||''),
    catalog_snapshot_id:selectedSnapshotId,
    evidence_policy: isV3Snapshot ? 'predicted_observations_v3' : isV2Snapshot ? 'predicted_observations_v2' : accuracyGeneration ? 'predicted_plus_refined_witnesses_v1' : 'predicted_observations_v1',
    fallback_profile:profile,
    border_side:borderSide,
    anchor_mode:anchorMode,
    rows:limitsError?[]:serializeRows(filterRows)
  }),[pinnedHeader,selectedSnapshotId,profile,borderSide,anchorMode,filterRows,accuracyGeneration,isV2Snapshot,isV3Snapshot,limitsError]);
  const payloadKey=JSON.stringify(currentQueryPayload);

  // Unchanged favorite persistence/compare helpers omitted.
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
    if(limitsError){setQueryError(limitsError);return;}
    if(isV3Snapshot&&!snapshotCapabilities){setQueryError('Selected snapshot capabilities are loading. Please retry shortly.');return;}
    if(unsupportedLegacyFilters){setQueryError('This historical snapshot does not support the selected stronghold or Nether filters. Choose a v2 or v3 snapshot or remove those filters.');return;}
    if(unsupportedV2Filters){setQueryError('This snapshot does not support individual Overworld biomes, groups, or contextual structures. Choose a v3 snapshot or remove those filters.');return;}
    const gatedFeature = filterRows.flatMap(r => r.kind === 'structure_count' ? [r.feature] : r.any_of)
      .find(id => {
        const meta = snapshotCapabilities?.registry_v3?.features?.find(f => f.id === id) || ALL_FEATURES_V3.find(f => f.id === id);
        return meta && meta.available === false;
      });
    if(gatedFeature){
      const meta = snapshotCapabilities?.registry_v3?.features?.find(f => f.id === gatedFeature) || ALL_FEATURES_V3.find(f => f.id === gatedFeature);
      setQueryError(`Feature "${meta?.label || gatedFeature}" is gated: ${meta?.unavailable_reason || 'This capability is currently unavailable.'}`);
      return;
    }
    if(!selectedSnapshotId||!pinnedHeader){setQueryError('Selected snapshot metadata is unavailable.');return;}
    if(more&&!nextCursor)return;
    queryAbort.current?.abort();const controller=new AbortController();queryAbort.current=controller;const epoch=++requestEpoch.current;
    setQueryError(null);setHasQueried(true);if(more)setIsFetchingMore(true);else {setIsQueryLoading(true);setResults([]);setNextCursor(null);}
    try {const body={request:currentQueryPayload,page_size:DEFAULT_PAGE_SIZE,...(more?{cursor:nextCursor}: {})};const data=await postCatalogQuery(body,controller.signal);
      if(controller.signal.aborted||epoch!==requestEpoch.current)return;
      if(!data.ok)throw Error(data.error||'Catalog query failed');
      if(data.snapshot_id!==selectedSnapshotId)throw Error('Query snapshot identity mismatch');
      if(currentQueryPayload.accuracy_generation&&data.accuracy_generation!==currentQueryPayload.accuracy_generation)throw Error('Query accuracy generation mismatch');
      const incoming=data.results.map(c=>({...c,snapshot_id:data.snapshot_id}));
      setResults(prev=>more?[...prev,...incoming.filter(c=>!prev.some(p=>p.world_id===c.world_id))]:incoming);
      setNextCursor(data.next_cursor);setUnresolvedWorlds(data.unresolved_worlds||0);setUnresolvedCandidates(data.unresolved_candidates||[]);setTotalMatched(data.matched_worlds);setIsTruncated(data.truncated);setEvidenceLabel(data.evidence_label);
    } catch(error) {if(!controller.signal.aborted&&epoch===requestEpoch.current)setQueryError(error instanceof Error?error.message:String(error));}
    finally {if(epoch===requestEpoch.current){setIsQueryLoading(false);setIsFetchingMore(false);}}
  },[selectedSnapshotId,pinnedHeader,nextCursor,currentQueryPayload,unsupportedLegacyFilters,unsupportedV2Filters,filterRows,snapshotCapabilities,limitsError,isV3Snapshot]);
  const runQuery=useCallback(()=>execute(false),[execute]),loadMore=useCallback(()=>execute(true),[execute]);
  const clearFiltersAndQuery=useCallback(()=>{
    setActivePresetId(null);
    if(filterRows.length===0){void execute(false);return;}
    queryAllPending.current=true;setFilterRows([]);
  },[filterRows.length,execute]);
  useEffect(()=>{
    if(!queryAllPending.current)return;
    queryAllPending.current=false;
    let cancelled=false;
    if(filterRows.length===0)queueMicrotask(()=>{if(!cancelled)void execute(false);});
    return()=>{cancelled=true;};
  },[execute,filterRows.length]);
  return {isV2Snapshot,isV3Snapshot,status,capabilities:snapshotCapabilities,snapshots,selectedSnapshotId,setSelectedSnapshotId,borderSide,setBorderSide,anchorMode,setAnchorMode,profile,setProfile,
    activePresetId,setActivePresetId,filterRows,setFilterRows,selectPreset,results,nextCursor,totalMatched,unresolvedWorlds,unresolvedCandidates,isTruncated,isQueryLoading,isFetchingMore,queryError,storageError,
    evidenceLabel,hasQueried,runQuery,loadMore,clearFiltersAndQuery,comparedCandidates,isCompareOpen,setIsCompareOpen,toggleCompare,removeCompared,clearCompared,
    favorites,isFavoritesOpen,setIsFavoritesOpen,toggleFavorite,removeFavorite,clearFavorites,importFavorites,inspectedCandidate,detailData,isDetailLoading,detailError,
    inspectCandidate,closeDetail,isExportOpen,setIsExportOpen,currentQueryPayload,isInitializing,initError};
}

```

## validation.ts
```tsx
import type {CatalogFavorite,FilterRow} from './types';

export function filterLimitsError(rows:FilterRow[]):string|null {
  if(rows.length>12)return 'At most 12 filter rows are supported. Remove a row before querying.';
  if(rows.some(row=>row.kind==='biome_witness'&&new Set(row.any_of).size>16))return 'At most 16 alternatives are supported per biome row. Remove an alternative before querying.';
  return null;
}

export function serializeRows(rows:FilterRow[]):Array<Record<string,unknown>> {
  const error=filterLimitsError(rows);if(error)throw Error(error);
  return rows.map(row=>({rule:row.rule,kind:row.kind,
    scope:row.scope.kind==='inside_border'?{kind:'inside_border'}:{kind:'near_base',radius:row.scope.radius},
    ...(row.rule==='preferred'?{importance:row.importance||3}:{}),
    ...(row.kind==='structure_count'
      ? {feature:row.feature,at_least:row.at_least}
      : {any_of:[...new Set(row.any_of)]})}));
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

## API note
fetchCatalogCapabilities(signal,snapshotId) sends GET capabilities?snapshot_id=<encoded>; AbortSignal propagated. Generic requests serialize their payload unchanged.

## FilterBuilder helper/dynamic options
```tsx
import { useState } from 'react';
import type { FilterRow, FilterRule, FilterKind, ScopeKind, NearRadius, Dimension, StructureFilterRow, BiomeFilterRow, FeatureV3Metadata } from './types';
import {
  KNOWN_STRUCTURES,
  KNOWN_BIOMES,
  NEAR_RADII,
  OVERWORLD_NEAR_RADII,
  NETHER_NEAR_RADII,
  V2_STRUCTURES,
  V2_BIOMES,
  V3_STRUCTURES,
  V3_BIOME_GROUPS,
  V3_EXACT_BIOMES,
  V3_ALL_BIOMES,
  MAX_FILTER_ROWS,
  MAX_FILTER_ROW_ALTERNATIVES,
  DEFAULT_OVERWORLD_NEAR_RADIUS,
  DEFAULT_NETHER_NEAR_RADIUS,
  getFeatureDimension,
  normalizeRadiusForDimension,
  getFeatureV3Metadata,
  type FeatureOption,
} from './constants';

export interface FilterBuilderProps {
  rows: FilterRow[];
  onChangeRows: (rows: FilterRow[]) => void;
  onResetRows: () => void;
  enableV2?: boolean;
  enableV3?: boolean;
  features?: FeatureV3Metadata[];
}

/**
 * Determine the effective dimension of a filter row.
 * For structure_count: based on the structure's dimension metadata.
 * For biome_witness: based on the biomes in any_of (Nether if any Nether biome is present).
 */
export function getRowDimension(row: FilterRow): Dimension {
  if (row.kind === 'structure_count') {
    return getFeatureDimension(row.feature);
  }
  if (row.kind === 'biome_witness') {
    if (row.any_of && row.any_of.length > 0) {
      return row.any_of.some(b => getFeatureDimension(b) === 'nether') ? 'nether' : 'overworld';
    }
  }
  return 'overworld';
}

/**
 * Pure helper to switch feature on a structure row.
 * If switching dimension in V2/V3, normalizes incompatible radius to 512 (OW) or 128 (Nether),
 * retaining compatible radius (e.g. 256) and all other choices (rule, at_least, importance).
 */
export function switchRowFeature(
  row: StructureFilterRow,
  newFeature: string,
  enableV2 = false,
  enableV3 = false
): StructureFilterRow {
  if (!enableV2 && !enableV3) {
    return { ...row, feature: newFeature };
  }
  const oldDim = getFeatureDimension(row.feature);
  const newDim = getFeatureDimension(newFeature);
  if (oldDim === newDim || row.scope.kind !== 'near_base') {
    return { ...row, feature: newFeature };
  }
  const normalizedRadius = normalizeRadiusForDimension(newDim, row.scope.radius);
  return {
    ...row,
    feature: newFeature,
    scope: {
      kind: 'near_base',
      radius: normalizedRadius,
    },
  };
}

/**
 * Pure helper to switch the biome dimension for a biome row.
 * Enforces single-dimension biome OR by selecting a default biome in the target dimension.
 * Normalizes incompatible radius to 512 (OW) or 128 (Nether) while retaining other choices.
 */
export function switchBiomeDimension(
  row: BiomeFilterRow,
  targetDimension: Dimension,
  enableV3 = false
): BiomeFilterRow {
  const currentDim = getRowDimension(row);
  if (currentDim === targetDimension) {
    return row;
  }
  const defaultOW = enableV3 ? 'biome.exact.cherry_grove' : 'biome.cherry_grove';
  const newAnyOf = targetDimension === 'nether' ? ['biome.nether_wastes'] : [defaultOW];
  let newScope = row.scope;
  if (row.scope.kind === 'near_base') {
    newScope = {
      kind: 'near_base',
      radius: normalizeRadiusForDimension(targetDimension, row.scope.radius),
    };
  }
  return {
    ...row,
    any_of: newAnyOf,
    scope: newScope,
  };
}

/**
 * Pure helper to filter a list of biomes/groups by a search query.
 */
export function filterBiomesBySearch(biomes: FeatureOption[], query: string): FeatureOption[] {
  const q = query.trim().toLowerCase();
  if (!q) return biomes;
  return biomes.filter(
    b =>
      b.label.toLowerCase().includes(q) ||
      b.id.toLowerCase().includes(q) ||
      b.category.toLowerCase().includes(q) ||
      (b.canonical_members || []).some(id=>id.replaceAll('_',' ').includes(q))
  );
}

/**
 * Pure helper to toggle or select a biome in a biome row.
 * When enableV2 & enableV3 are false: legacy multi-select within Overworld.
 * When enableV2 or enableV3 is true: enforces single-dimension biome OR.
 * In V3: enforces 16-alternative limit and prevents selecting disabled/gated options.
 */
export function toggleBiomeSelectionInRow(
  row: BiomeFilterRow,
  biomeId: string,
  enableV2 = false,
  enableV3 = false,
  features?: FeatureV3Metadata[]
): BiomeFilterRow {
  if (!enableV2 && !enableV3) {
    let next: string[];
    if (row.any_of.includes(biomeId)) {
      next = row.any_of.filter(b => b !== biomeId);
      if (next.length === 0) next = [biomeId]; // Keep at least one
    } else {
      next = [...row.any_of, biomeId];
    }
    return { ...row, any_of: next };
  }

  // Check if feature is gated and unavailable
  const meta = features?.find(f=>f.id===biomeId) || getFeatureV3Metadata(biomeId);
  if (meta && meta.available === false) {
    return row;
  }

  const currentDim = getRowDimension(row);
  const clickedDim = getFeatureDimension(biomeId);

  // If clicked a biome from the other dimension, switch dimension!
  if (clickedDim !== currentDim) {
    let newScope = row.scope;
    if (row.scope.kind === 'near_base') {
      newScope = {
        kind: 'near_base',
        radius: normalizeRadiusForDimension(clickedDim, row.scope.radius),
      };
    }
    return {
      ...row,
      any_of: [biomeId],
      scope: newScope,
    };
  }

  // Same dimension: toggle within this dimension
  let next: string[];
  if (row.any_of.includes(biomeId)) {
    next = row.any_of.filter(b => b !== biomeId);
    if (next.length === 0) next = [biomeId]; // Keep at least one
  } else {
    // Enforce 16 maximum alternatives limit
    if (row.any_of.length >= MAX_FILTER_ROW_ALTERNATIVES) {
      return row; // Limit reached
    }
    next = [...row.any_of, biomeId];
  }
  return { ...row, any_of: next };
}

/**
 * Helper to select or toggle a named biome group in a row.
 */
export function selectBiomeGroupInRow(
  row: BiomeFilterRow,
  groupId: string,
  enableV3 = false
): BiomeFilterRow {
  return toggleBiomeSelectionInRow(row, groupId, true, enableV3);
}

export function FilterBuilder({
  rows,
  onChangeRows,
  onResetRows,
  enableV2 = false,
  enableV3 = false,
  features,
}: FilterBuilderProps) {
  const isV3 = Boolean(enableV3);
  const isV2 = Boolean(enableV2 || enableV3);
  const options=(fallback:FeatureOption[]):FeatureOption[]=>fallback.map(option=>{
    const meta=features?.find(f=>f.id===option.id);
    return meta?{...option,available:meta.available,unavailable_reason:meta.unavailable_reason,
      eligible_y:meta.eligible_y,canonical_members:meta.atomic_members || meta.canonical_members?.map(id=>id.startsWith('biome.')?id:`biome.exact.${id}`) || option.canonical_members}:option;
  });
  const structures=options(V3_STRUCTURES), groups=options(V3_BIOME_GROUPS), exactBiomes=options(V3_EXACT_BIOMES), allBiomes=options(V3_ALL_BIOMES);


  const [searchTerms, setSearchTerms] = useState<Record<string, string>>({});
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});


```

## Product request/view lifecycle
```tsx
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
  const [view, setView] = useState<'primary' | 'reserve'>('primary');
  const [copied, setCopied] = useState<{ worldId: string; failed: boolean } | null>(null);
  const [inspectedWorld, setInspectedWorld] = useState<string | null>(null);

  const key = `${snapshotId}:${product?.id || ''}:${view}:${cursor || ''}`;
  const isRealm = Boolean(product?.pillar_id === 'realm' || product?.id?.startsWith('realm'));
  const declaredSides=product?.scope?.border_sides;
  const realmSide=Array.isArray(declaredSides)&&[2048,4096,8192].includes(declaredSides[0])?declaredSides[0]:2048;

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
    setView('primary');
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
        view,
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


```
