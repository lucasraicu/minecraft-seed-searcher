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
      if(!controller.signal.aborted&&value.ok&&value.snapshot_id===selectedSnapshotId){setCapabilities(value);if(value.evidence_label)setEvidenceLabel(value.evidence_label);}
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
    void Promise.allSettled([fetchCatalogStatus(controller.signal),fetchCatalogSnapshots(controller.signal)]).then(([stat,snaps])=>{
      if(!active)return;
      if(stat.status==='fulfilled'&&stat.value.ok){setStatus(stat.value);if(stat.value.snapshot_id)setSelectedSnapshotId(stat.value.snapshot_id);}
      else setInitError(stat.status==='rejected'?String(stat.reason):'Catalog unavailable');
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
