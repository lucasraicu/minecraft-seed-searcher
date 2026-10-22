"""Read-only v2 serving over immutable public observations and membership snapshots."""
from pathlib import Path
import time
from .registry import digest
from .ingestion import verify_no_symlinks
from .geometry import bounds_for,inside
from .request import validate_request_v2
from .query import rank_v2

EVIDENCE='Predicted structure starts and biome witnesses at declared heights; no physical-count, player-landing, portal-safety or exact-absence certification.'


def available(root,snapshot_id=None):
    if root is None:return False
    if snapshot_id is not None and (not isinstance(snapshot_id,str) or len(snapshot_id)!=64 or any(c not in '0123456789abcdef' for c in snapshot_id)):
        raise ValueError('Invalid snapshot identity')
    path=Path(root)/'automation'/('current.json' if snapshot_id is None else 'snapshots/'+snapshot_id+'.json')
    return verify_no_symlinks(path).is_file()


def _store(service):
    from .store import AutomationStore
    if service.root is None:raise ValueError('Catalog root is not configured')
    return AutomationStore(service.root)


def info(store,snapshot_id=None,manifest=None):
    manifest=store.snapshot(snapshot_id) if manifest is None else manifest
    return _info_fields(manifest,digest(manifest))


def _info_fields(manifest,sid):
    worlds=manifest['worlds'];header={k:v for k,v in worlds[0]['identity'].items() if k!='seed'} if worlds else {}
    extra={}
    if manifest['revision']=='catalog-snapshot-v3':
        extra=dict(request_revision='catalog-query-v3',reserve_policy=manifest['reserve_policy'],registry_revision=digest(manifest['registry']),sampling_profile_revision=manifest['sampling_profile_revision'])
    return dict(snapshot_id=sid,revision=manifest['revision'],**extra,worlds=len(worlds),
        layouts=None,header=header,policy_revision=manifest['policy_revision'],
        generation=manifest['generation'],population_worlds=manifest['population_worlds'],
        anchor_modes=['recommended','origin','world_spawn_estimated'])


def query(service,body):
    from .service import ServiceError
    if not isinstance(body,dict) or set(body)-{'request','page_size','cursor'} or 'request' not in body:
        raise ServiceError('Expected request, optional page_size and cursor')
    size=body.get('page_size',20)
    if type(size) is not int or not 1<=size<=50:raise ServiceError('page_size must be1..50')
    start=time.monotonic()
    def check():
        if time.monotonic()-start>service.query_seconds:raise ServiceError('Catalog query time allowance exhausted','query_timeout',503)
    with service._slot():
        raw=body['request']
        if not isinstance(raw,dict):raise ServiceError('Expected a query object')
        sid=raw.get('catalog_snapshot_id')
        if not available(service.root,sid):raise ServiceError('Snapshot unavailable','not_found',404)
        store=_store(service);manifest=service._query_snapshot(store,sid);worlds=manifest['worlds'];header=worlds[0]['identity'] if worlds else {}
        v3=raw.get('request_revision')=='catalog-query-v3'
        if v3:
            if manifest['revision']!='catalog-snapshot-v3':raise ServiceError('This historical snapshot does not support individual biome filters','capability_error',409)
            from .request import validate_request_v3
            req=validate_request_v3(raw,registry=manifest['registry'],snapshot_id=sid,game_build_id=header.get('game_build_id'),world_settings_id=header.get('world_settings_id'))
        else:req=validate_request_v2(raw,snapshot_id=sid,game_build_id=header.get('game_build_id'),world_settings_id=header.get('world_settings_id'))
        # snapshot(sid) has already verified the canonical manifest digest against sid.
        proof=sid;key=digest(['automation-query-v3' if v3 else 'automation-query-v2',req,manifest['policy_revision']]);cached=service._cached_result(key)
        if cached is not None:
            if cached['proof']!=proof:raise ServiceError('Snapshot changed','integrity_error',503)
            ranked=cached['ranked'];matched=cached['matched'];extra=cached['extra']
        else:
            def layouts():
                from .read_views import filtered_summaries
                yield from filtered_summaries(service,store,manifest,req,check)
            if v3:
                from .query import rank_v3
                result=rank_v3(layouts(),req,limit=1000,keep_keys=True,registry=manifest['registry'])
            else:result=rank_v2(layouts(),req,limit=1000,keep_keys=True)
            ranked=result['results'];matched=result['matched_worlds']
            extra=dict(unresolved=result['unresolved_worlds'],potential=result['unresolved_candidates'])
            for candidate in extra['potential']:candidate.pop('_sort_key',None)
            service._save_result(key,ranked,matched,proof,extra)
        check();request_sha=digest(req);cursor=service._decode(body['cursor']) if body.get('cursor') else None
        if cursor and (cursor.get('revision')!='automation-cursor-v2' or cursor['request']!=request_sha or
                       cursor['snapshot']!=sid or cursor['size']!=size or cursor.get('policy')!=manifest['policy_revision']):
            raise ServiceError('Cursor belongs to another request/snapshot/policy','cursor_mismatch')
        offset=0
        if cursor:
            positions=[i for i,row in enumerate(ranked) if [str(v) for v in row['_sort_key']]==cursor['last']]
            if not positions:raise ServiceError('Page boundary unavailable','cursor_mismatch',409)
            offset=positions[0]+1
        page=[dict(row) for row in ranked[offset:offset+size]];next_cursor=None
        if offset+size<len(ranked):
            next_cursor=service._token(dict(revision='automation-cursor-v2',snapshot=sid,request=request_sha,
                policy=manifest['policy_revision'],size=size,last=[str(v) for v in page[-1]['_sort_key']],
                expires=cursor['expires'] if cursor else time.time()+3600))
        for row in page:row.pop('_sort_key',None)
        return dict(ok=True,snapshot_id=sid,request_sha256=request_sha,results=page,next_cursor=next_cursor,
            truncated=matched>1000,matched_worlds=matched,unresolved_worlds=extra['unresolved'],
            unresolved_candidates=extra['potential'],evidence_label=EVIDENCE,
            stats=dict(wall_seconds=time.monotonic()-start,result_cache_hit=cached is not None,
                       policy_revision=manifest['policy_revision']))


def product_results(service,body):
    from .service import ServiceError
    from .products import product_registry_v2
    if not isinstance(body,dict) or set(body)-{'revision','snapshot_id','product_id','page_size','cursor','view'} or not {'revision','snapshot_id','product_id'}<=set(body) or body['revision']!='catalog-product-request-v2':
        raise ServiceError('Expected v2 snapshot and product request')
    sid=body['snapshot_id'];pid=body['product_id'];size=body.get('page_size',20);view=body.get('view','primary')
    if view not in ('primary','reserve'):raise ServiceError('Expected primary or reserve view')
    if type(size) is not int or not 1<=size<=50:raise ServiceError('page_size must be1..50')
    product=next((p for p in product_registry_v2()['products'] if p['id']==pid and p['availability_status']=='predicted'),None)
    if product is None:raise ServiceError('Product unavailable','product_gated',409)
    if not available(service.root,sid):raise ServiceError('Snapshot has no v2 product memberships','product_gated',409)
    with service._slot():
        manifest=service._board_snapshot(_store(service),sid)
        if 'memberships'in manifest:
            results=[row['member']for row in manifest['memberships']if row['objective_id']==pid]
        else:results=manifest['board_members'].get(pid,[])
        # Publisher preserves numeric ledger ordering; never sort JSON/string ranks.
        extra={}
        if manifest['revision']=='catalog-snapshot-v3':
            from .retention import automation_primary_objectives_v3
            k=automation_primary_objectives_v3()[pid]
            extra=dict(primary_count=min(k,len(results)),reserve_count=max(0,len(results)-k),view=view,reserve_policy=manifest['reserve_policy'])
            results=results[:k] if view=='primary' else results[k:2*k]
            results=[dict(r,candidate_role=view,evidence_status='predicted') for r in results]
        elif view=='reserve':results=[]
        offset=0;cursor=service._decode(body['cursor']) if body.get('cursor') else None
        if cursor:
            if cursor.get('revision')!='catalog-product-cursor-v2' or cursor.get('snapshot')!=sid or cursor.get('product')!=pid or cursor.get('policy')!=manifest['policy_revision'] or cursor.get('size')!=size or cursor.get('view','primary')!=view:
                raise ServiceError('Cursor belongs to another product/snapshot','cursor_mismatch')
            offset=cursor.get('offset')
            if type(offset) is not int or not 0<=offset<=len(results):raise ServiceError('Invalid page offset')
        matched=len(results);page=results[offset:offset+size];next_cursor=None
        if offset+size<matched:
            next_cursor=service._token(dict(revision='catalog-product-cursor-v2',snapshot=sid,product=pid,policy=manifest['policy_revision'],size=size,view=view,offset=offset+size,expires=cursor['expires'] if cursor else time.time()+3600))
        return dict(ok=True,revision='catalog-product-results-v2',snapshot_id=sid,product_id=pid,
            **extra,results=page,matched_worlds=matched,next_cursor=next_cursor,scope=product['scope'],population_worlds=manifest['population_worlds'],
            evaluation_counts=manifest.get('product_status',{}).get(pid),
            policy_revision=manifest['policy_revision'],evidence_label=EVIDENCE)


def detail(service,sid,wid,lid):
    from .service import ServiceError
    from .registry import FEATURE_BY_ID_V2
    with service._slot():
        bundle=_store(service).world(sid,wid);obs=bundle['observation']
        definitions={f['id']:f for f in bundle.get('registry',{}).get('features',[])} if bundle['revision']=='catalog-world-bundle-v3' else FEATURE_BY_ID_V2
        summary=next((r for r in bundle['summaries'] if r['layout_id']==lid),None)
        if summary is None:raise ServiceError('Layout not in pinned snapshot','not_found',404)
        layout=dict(summary,**{key:summary['legacy'][key] for key in ('counts','complete','structure_nearest_d2','biome_nearest_d2')})
        layout['anchor_mode']=summary['anchor_modes'][0]
        ow_box=bounds_for(summary['anchor'],summary['border_side'])
        na=summary['nether_anchor'];nether_box=(na[0]-512,na[1]-512,na[0]+512,na[1]+512)
        structures={};nether={};witnesses=[];nether_witnesses=[];remaining=5000;truncated=False
        for fid,points in obs['structures'].items():
            dimension=definitions[fid]['dimension'];box=ow_box if dimension=='overworld' else nether_box
            selected=[p for p in points if inside(*p,box)];shown=selected[:remaining];remaining-=len(shown)
            (structures if dimension=='overworld' else nether)[fid]=shown;truncated|=len(shown)<len(selected)
        for fid,feature in summary['features'].items():
            if not fid.startswith('biome.') or feature['witness'] is None:continue
            x,y,z=feature['witness'];row=dict(feature=fid,x=x,y=y,z=z,distance_squared=feature['nearest_d2'])
            (witnesses if feature['dimension']=='overworld' else nether_witnesses).append(row)
        return dict(ok=True,snapshot_id=sid,world_id=wid,identity=obs['identity'],layout=layout,
            anchor_evidence=None,anchor_roles=[],
            anchor_sources=[a for a in obs['anchors'] if a['coordinate']==summary['anchor'] and a['mode'] in summary['anchor_modes']],
            structures=structures,nether_structures=nether,
            nether_bounds=list(nether_box),nether_biome_witnesses=nether_witnesses,
            structures_truncated=truncated,biome_witnesses=witnesses,coverage=obs['coverage'],
            structure_evidence={},sampling_profile_revision=summary.get('sampling_profile_revision'),
            source_extension_id=summary.get('source_extension_id'),
            biome_evidence=dict(method='saved_predicted_xyz_v3' if bundle['revision']=='catalog-world-bundle-v3' else 'saved_predicted_xyz_v2',interpretation='Predicted biome presence at sampled heights; missing witnesses remain unknown.',verifier_game_build_id=None,checks=[]),
            evidence_label=EVIDENCE)
