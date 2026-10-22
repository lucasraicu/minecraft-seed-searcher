"""Versioned spawn-layout query path; normal HTTP never creates observations."""
import time
from .request import validate_request
from .registry import digest
from .accuracy_store import read_bundle
from .anchors import MODES
from .geometry import bounds_for
from .query import _rank

REVISION='catalog-query-accuracy-v1'


def validate_accuracy_request(value,**expected):
    if not isinstance(value,dict) or value.get('request_revision')!=REVISION:
        raise ValueError('Expected versioned accuracy query')
    from .accuracy import sha256
    sha256(value.get('accuracy_generation'))
    if value.get('evidence_policy')!='predicted_plus_refined_witnesses_v1':raise ValueError('Unsupported accuracy evidence policy')
    if value.get('anchor_mode') not in MODES+('origin','recommended'):raise ValueError('Unsupported accuracy anchor mode')
    baseline=dict(value);generation=baseline.pop('accuracy_generation')
    mode=baseline['anchor_mode'];baseline.update(request_revision='catalog-query-v1',evidence_policy='predicted_observations_v1',anchor_mode=mode if mode in ('origin','recommended') else 'recommended')
    canonical=validate_request(baseline,**expected)
    return dict(canonical,request_revision=REVISION,anchor_mode=mode,accuracy_generation=generation,evidence_policy='predicted_plus_refined_witnesses_v1')


def _bound_bundle(store,snapshot_id,generation):
    generation,bundle=read_bundle(store.root,snapshot_id,generation)
    info=store.info(snapshot_id);store._verified_membership(snapshot_id)
    membership={r[0]:(r[1],r[2]) for r in store.conn.execute(
        'SELECT world_id,observation_id,seed FROM observation_ref WHERE snapshot_id=?',(snapshot_id,))}
    for entry in bundle['anchors']:
        if membership.get(entry['world_id'])!=(entry['observation_id'],entry['anchor']['context']['identity']['seed']):
            raise ValueError('Accuracy anchor is not in the pinned snapshot')
        ident=entry['anchor']['context']['identity']
        if {k:v for k,v in ident.items() if k!='seed'}!=info['header']:
            raise ValueError('Accuracy anchor build/settings differ from snapshot')
    return bundle


def bound_entries(store,snapshot_id,generation):
    return _bound_bundle(store,snapshot_id,generation)['anchors']


def query(service,body):
    from .service import ServiceError,EVIDENCE
    if set(body)-{'request','page_size','cursor'}:raise ServiceError('Unexpected query field')
    size=body.get('page_size',20)
    if type(size) is not int or not 1<=size<=50:raise ServiceError('page_size must be1..50')
    start=time.monotonic()
    with service._slot(),service._store() as store:
        req=validate_accuracy_request(body['request']);sid=req['catalog_snapshot_id'];info=store.info(sid)
        if info['worlds']>2000:raise ServiceError('Accuracy query cohort cap exceeded','capacity_limit',503)
        req=validate_accuracy_request(req,snapshot_id=sid,game_build_id=info['header']['game_build_id'],world_settings_id=info['header']['world_settings_id'])
        try:bundle=_bound_bundle(store,sid,req['accuracy_generation'])
        except FileNotFoundError:raise ServiceError('Pinned accuracy generation is unavailable','accuracy_unavailable',409) from None
        except (ValueError,KeyError,TypeError,OSError):raise ServiceError('Accuracy generation failed integrity validation','integrity_error',503) from None
        entries=bundle['anchors']
        cache_key=digest(['accuracy-query',req])
        proof=digest([req['accuracy_generation'],store.conn.execute('SELECT world_id,observation_id,seed,manifest_sha256 FROM observation_ref WHERE snapshot_id=? ORDER BY world_id',(sid,)).fetchall()])
        cached=service._cached_result(cache_key)
        if cached is not None:
            if cached['proof']!=proof:raise ServiceError('Snapshot membership changed','integrity_error',503)
            return _page(service,body,req,size,cached['ranked'],cached['matched'],cached['extra'],start,cached=True)
        by_layout={};provenance={};unavailable=0
        from .refined_witnesses import model_witnesses,apply_witnesses
        fine={};fine_rows={}
        def add_layout(layout):
            observation={'identity':dict(info['header'],seed=layout['seed'])}
            wid=layout['world_id']
            if wid not in fine:fine[wid]=model_witnesses(observation,bundle['tiles'])
            if any(fine[wid].values()):
                row,witnesses=apply_witnesses(layout,fine[wid])
            else:
                # Query-local rows remain read-only during scoring. Isolate the
                # top-level mapping without copying unused nested inventories.
                row,witnesses=dict(layout),[]
            by_layout[row['layout_id']]=row;fine_rows[row['layout_id']]=witnesses
        if req['anchor_mode'] in ('origin','recommended'):
            baseline=dict(req,request_revision='catalog-query-v1',evidence_policy='predicted_observations_v1');baseline.pop('accuracy_generation')
            # Coarse biome indexes cannot prune newly recovered fine witnesses.
            # Keep structure predicates only in the coarse prefilter.
            baseline['rows']=[r for r in baseline['rows'] if r['kind']=='structure_count']
            for segment in store.iter_segments(sid,request=baseline):
                if time.monotonic()-start>service.query_seconds:raise ServiceError('Accuracy query time allowance exhausted','query_timeout',503)
                if not segment['layouts']:continue
                for layout in segment['layouts']:
                    if layout['border_side']==req['border_side'] and (req['anchor_mode']!='origin' or layout['anchor']==[0,0]):
                        add_layout(layout)
        for entry in entries:
            if entry['anchor']['mode']!=req['anchor_mode']:continue
            for layout in entry['layouts']:
                if layout['border_side']!=req['border_side']:continue
                # Out-of-envelope layouts remain saved and can receive coverage
                # later, but cannot rank as a complete user-selected world area.
                box=bounds_for(layout['anchor'],layout['border_side'])
                from .registry import ENVELOPE
                if not (ENVELOPE[0]<=box[0] and ENVELOPE[1]<=box[1] and box[2]<=ENVELOPE[2] and box[3]<=ENVELOPE[3]):
                    unavailable+=1;continue
                add_layout(layout);provenance[layout['layout_id']]=entry['anchor']
        scoring=dict(req,anchor_mode=req['anchor_mode'] if req['anchor_mode'] in ('origin','recommended') else 'recommended',request_revision='catalog-query-v1');scoring.pop('accuracy_generation')
        ranked=_rank(list(by_layout.values()),scoring,4000,validate_records=False,keep_keys=True,positive_witnesses=True)
        matched_ids={r['world_id'] for r in ranked}
        from .query import STRUCTURE_SLOTS,BIOME_SLOTS,RADII_MAP
        from .codec import MISSING
        potential={}
        for layout in by_layout.values():
            unknown=False;impossible=False
            for predicate in req['rows']:
                if predicate['rule']!='required':continue
                scope=predicate['scope'];slot=3 if scope['kind']=='inside_border' else RADII_MAP[scope['radius']]
                if predicate['kind']=='structure_count':
                    feature=STRUCTURE_SLOTS[predicate['feature']]
                    if not layout['complete'][feature][slot]:unknown=True
                    elif layout['counts'][feature][slot]<predicate['at_least']:
                        impossible=True;break
                else:
                    radius=None if scope['kind']=='inside_border' else scope['radius']
                    present=any(layout['biome_nearest_d2'][BIOME_SLOTS[f]]!=MISSING and
                        (radius is None or layout['biome_nearest_d2'][BIOME_SLOTS[f]]<=radius*radius) for f in predicate['any_of'])
                    # No sparse witness is UNKNOWN, even if its lattice was
                    # fully evaluated. No seed is removed from catalog retention.
                    if not present or not all(layout['complete'][14+BIOME_SLOTS[f]][slot] for f in predicate['any_of']):unknown=True
            if unknown and not impossible and layout['world_id']not in matched_ids:
                potential.setdefault(layout['world_id'],dict(world_id=layout['world_id'],seed=layout['seed'],layout_id=layout['layout_id'],anchor=layout['anchor'],border_side=layout['border_side'],status='unresolved',reason='Required evidence is incomplete; this is not a matching result or a rejected seed'))
        matched_worlds=len(ranked);ranked=ranked[:1000]
        if time.monotonic()-start>service.query_seconds:raise ServiceError('Accuracy query time allowance exhausted','query_timeout',503)
        for row in ranked:
            layout=by_layout[row['layout_id']]
            for field in ('counts','structure_nearest_d2','biome_nearest_d2','complete'):row[field]=layout[field]
            row.update(bounds=list(bounds_for(layout['anchor'],layout['border_side'])),anchor_evidence=provenance.get(row['layout_id']),refined_biome_witnesses=fine_rows[row['layout_id']],accuracy_generation=req['accuracy_generation'])
        extra=dict(unavailable=unavailable,unresolved=len(potential),potential=list(potential.values())[:50],layouts=len(by_layout))
        service._save_result(cache_key,ranked,matched_worlds,proof,extra=extra)
        return _page(service,body,req,size,ranked,matched_worlds,extra,start,cached=False)


def _page(service,body,req,size,ranked,matched_worlds,extra,start,*,cached):
        from .service import ServiceError,EVIDENCE
        if time.monotonic()-start>service.query_seconds:raise ServiceError('Accuracy query time allowance exhausted','query_timeout',503)
        sid=req['catalog_snapshot_id'];request_sha=digest(req);cursor=service._decode(body['cursor']) if body.get('cursor') else None
        if cursor and (cursor['request']!=request_sha or cursor['snapshot']!=sid or cursor['size']!=size):
            raise ServiceError('Cursor belongs to another request','cursor_mismatch')
        offset=0
        if cursor:
            positions=[i for i,row in enumerate(ranked) if [str(v) for v in row['_sort_key']]==cursor['last']]
            if not positions:raise ServiceError('Page boundary unavailable','cursor_mismatch',409)
            offset=positions[0]+1
        page=[dict(r) for r in ranked[offset:offset+size]];next_cursor=None
        if offset+size<len(ranked):
            next_cursor=service._token(dict(snapshot=sid,request=request_sha,size=size,
                last=[str(v) for v in page[-1]['_sort_key']],expires=cursor['expires'] if cursor else time.time()+3600))
        for row in page:row.pop('_sort_key')
        return dict(ok=True,snapshot_id=sid,request_sha256=request_sha,results=page,next_cursor=next_cursor,
            truncated=matched_worlds>1000,matched_worlds=matched_worlds,unavailable_layouts=extra['unavailable'],
            unresolved_worlds=extra['unresolved'],unresolved_candidates=extra['potential'],accuracy_generation=req['accuracy_generation'],
            evidence_label=EVIDENCE+' World-spawn coordinates do not establish player landing or safety.',
            stats=dict(wall_seconds=time.monotonic()-start,accuracy_layouts=extra['layouts'],result_cache_hit=cached))
