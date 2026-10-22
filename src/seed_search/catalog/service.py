"""Private snapshot-pinned serving. No search/extraction subprocesses or personal DB."""
import base64
from collections import OrderedDict
from contextlib import contextmanager
from decimal import Decimal
import hashlib
import heapq
import hmac
import json
import secrets
import threading
import time

from .registry import REGISTRY, POLICY, STRUCTURES, BIOMES, PROFILES, SIDES, RADII, CONTRACT_ROOT, canonical_json, digest
from .request import validate_request
from .query import _rank
from .geometry import bounds_for
from .codec import MISSING

EVIDENCE='Research predictions: structure starts and sampled Y63/stride64 biome witnesses. Generated structures and exact player spawn are unverified.'


class ServiceError(ValueError):
    def __init__(self,message,code='invalid_request',status=400):
        super().__init__(message);self.code=code;self.status=status


class _Worst:
    def __init__(self,key,wid,version):self.key=key;self.wid=wid;self.version=version
    def __lt__(self,other):return self.key>other.key


class TopWorlds:
    """Exact streaming unique-world TopK; evicted worlds can reenter with better anchors."""
    def __init__(self,limit=1000):self.limit=limit;self.members={};self.heap=[];self.version=0
    def _prune(self):
        while self.heap and self.members.get(self.heap[0].wid,(None,None))[0]!=self.heap[0].version:
            heapq.heappop(self.heap)
    def offer(self,result):
        wid=result['world_id'];key=result['_sort_key'];old=self.members.get(wid)
        if old and old[1]['_sort_key']<=key:return
        self._prune()
        if not old and len(self.members)>=self.limit:
            if key>=self.heap[0].key:return
            del self.members[heapq.heappop(self.heap).wid]
        self.version+=1;self.members[wid]=(self.version,result)
        heapq.heappush(self.heap,_Worst(key,wid,self.version))
        if len(self.heap)>2*self.limit:
            self.heap=[_Worst(r['_sort_key'],w,v) for w,(v,r) in self.members.items()];heapq.heapify(self.heap)
    def results(self):return sorted((r for _,r in self.members.values()),key=lambda r:r['_sort_key'])


class CatalogService:
    def __init__(self,root=None,*,secret=None,query_seconds=10.,cache_bytes=64<<20,query_processes=0):
        self.root=root;self.secret=secret or secrets.token_bytes(32);self.query_seconds=query_seconds
        self.cache_bytes=cache_bytes//2;self.cache=OrderedDict();self.cache_size=0;self.cache_lock=threading.Lock()
        self.result_bytes=cache_bytes-self.cache_bytes;self.result_cache=OrderedDict();self.result_size=0
        self.admission=threading.BoundedSemaphore(4);self.execution=threading.BoundedSemaphore(2)
        self.query_workers=None
        if query_processes:
            from .query_workers import QueryWorkerPool
            self.query_workers=QueryWorkerPool(root,secret=self.secret,workers=query_processes,
                query_seconds=query_seconds,cache_bytes=cache_bytes)

    def close(self):
        if self.query_workers is not None:self.query_workers.close()

    @contextmanager
    def _store(self):
        if self.root is None:raise ServiceError('Catalog root is not configured','unavailable',503)
        from pathlib import Path
        if not (Path(self.root)/'pilot.sqlite').is_file():
            raise ServiceError('Catalog has not been imported','unavailable',503)
        from .segments import SegmentedCatalog
        with SegmentedCatalog(self.root) as store:yield store

    @contextmanager
    def _slot(self,wait_seconds=2):
        if not self.admission.acquire(blocking=False):raise ServiceError('Catalog is busy; try again','busy',429)
        acquired=False
        try:
            acquired=self.execution.acquire(timeout=wait_seconds)
            if not acquired:raise ServiceError('Catalog query queue timed out','busy',429)
            yield
        finally:
            if acquired:self.execution.release()
            self.admission.release()

    def status(self):
        from .automation_query import available,info,_store
        if available(self.root):
            store=_store(self);sid=store._binding()['snapshot_id']
            from .automation_query import _info_fields
            result=dict(ok=True,available=True,**_info_fields(self._query_snapshot(store,sid),sid))
            if self.query_workers is not None:result['query_workers']=self.query_workers.status()
            return result
        try:
            with self._store() as store:
                result=dict(ok=True,available=True,**store.info())
                if self.query_workers is not None:result['query_workers']=self.query_workers.status()
                return result
        except ServiceError as exc:return dict(ok=True,available=False,reason=str(exc))

    def _accuracy(self, snapshot_id):
        from .accuracy_store import read_bundle
        try:
            generation,bundle=read_bundle(self.root,snapshot_id)
        except FileNotFoundError:
            return {}
        return dict(accuracy_generation=generation,
            accuracy_anchor_modes=sorted({e['anchor']['mode'] for e in bundle['anchors']}))

    def capabilities(self,snapshot_id=None):
        presets=json.loads((CONTRACT_ROOT/'ui_presets.json').read_text())['presets']
        from .registry import REGISTRY_V2
        extra={}
        from .automation_query import available,_store
        if available(self.root,snapshot_id):
            store=_store(self);sid=store._binding(snapshot_id)['snapshot_id']
            manifest=self._query_snapshot(store,sid)
            if manifest['revision']=='catalog-snapshot-v3':
                extra=dict(registry_v3=manifest['registry'],request_revision='catalog-query-v3',snapshot_id=sid,reserve_policy=manifest['reserve_policy'])
        return dict(ok=True,**extra,registry_v2=REGISTRY_V2,nether_near_radii=[64,128,256],registry={k:REGISTRY[k] for k in ('categories','features')},presets=presets,
            profiles=[{'id':p} for p in PROFILES],border_sides=list(SIDES),near_radii=list(RADII),
            anchor_modes=['recommended','origin'],max_rows=12,max_compare=4,evidence_label=EVIDENCE)

    def snapshots(self):
        from .automation_query import available,info,_store
        rows=[]
        if self.root is not None:
            from pathlib import Path
            if (Path(self.root)/'pilot.sqlite').is_file():
                with self._store() as store:rows=[dict(row,**self._accuracy(row['snapshot_id'])) for row in store.snapshots()]
        if available(self.root):
            store=_store(self)
            from .automation_query import _info_fields
            rows += sorted((_info_fields(self._query_snapshot(store,sid),sid) for sid in store.snapshot_ids()),key=lambda row:(row['generation'],row['snapshot_id']))
        if not rows:raise ServiceError('Catalog has not been imported','unavailable',503)
        return dict(ok=True,snapshots=rows)

    def products(self,snapshot_id=None):
        from .products import product_registry,product_registry_v2
        from .automation_query import available
        return product_registry_v2() if available(self.root,snapshot_id) else product_registry()

    def product_results(self, body):
        if isinstance(body,dict) and body.get('revision')=='catalog-product-request-v2':
            from .automation_query import product_results
            return product_results(self,body)
        from .products import product_registry
        from .product_views import read_previews
        if (not isinstance(body, dict) or set(body) != {'revision', 'snapshot_id', 'product_id'}
                or body['revision'] != 'catalog-product-request-v1'):
            raise ServiceError('Expected versioned snapshot and product request')
        sid, pid = body['snapshot_id'], body['product_id']
        if not isinstance(sid, str) or len(sid) != 64 or any(c not in '0123456789abcdef' for c in sid):
            raise ServiceError('Invalid snapshot identity')
        if not isinstance(pid, str) or len(pid) > 128:
            raise ServiceError('Invalid product identity')
        registry = product_registry()
        product = next((p for p in registry['products'] if p['id'] == pid), None)
        if product is None:raise ServiceError('Unknown catalog product', 'not_found', 404)
        if product['availability_status'] != 'research':
            return dict(ok=False, code='product_gated', product_id=pid,
                        error='This product requires additional evidence before activation',
                        missing_dependencies=product['missing_dependencies'],
                        evidence_needed=product['evidence_needed'], results=[])
        start = time.monotonic()
        with self._slot(), self._store() as store:
            info = store.info(sid)
            store._verified_membership(sid)
            try:
                payload = read_previews(self.root, sid, expected_header=info['header'])
            except FileNotFoundError:
                raise ServiceError('Research preview has not been derived for this snapshot', 'preview_unavailable', 503) from None
            except (ValueError, KeyError, TypeError):
                raise ServiceError('Research preview failed integrity validation', 'integrity_error', 503) from None
            rows = payload['lists'][pid]
            if payload['population_worlds'] != info['worlds']:
                raise ServiceError('Research population does not match snapshot', 'integrity_error', 503)
            from .evidence import read_evidence, summarize_structure
            annotated = []
            feature_id = 'structure.' + pid.split('.')[2]
            for row in rows:
                membership = store.conn.execute(
                    'SELECT seed, observation_id FROM observation_ref WHERE snapshot_id=? AND world_id=?',
                    (sid, row['world_id'])).fetchone()
                if membership is None or membership[0] != row['seed']:
                    raise ServiceError('Research result is not a member of this snapshot', 'integrity_error', 503)
                try:
                    evidence = read_evidence(self.root, sid, row['world_id'], membership[1])
                    summary = summarize_structure(evidence, feature_id, row['witnesses'], total_count=row['count'])
                except (ValueError, OSError, KeyError, TypeError):
                    raise ServiceError('Research evidence failed integrity validation', 'integrity_error', 503) from None
                annotated.append(dict(row, structure_evidence=summary))
                if time.monotonic() - start > self.query_seconds:
                    raise ServiceError('Research evidence time allowance exhausted', 'query_timeout', 503)
            if time.monotonic() - start > self.query_seconds:
                raise ServiceError('Research preview time allowance exhausted', 'query_timeout', 503)
            return dict(ok=True, revision='catalog-product-results-v1', snapshot_id=sid,
                        product_id=pid, scope=product['scope'], results=annotated,
                        population_worlds=payload['population_worlds'], evidence_label=registry['evidence_label'])

    def _token(self,payload):
        raw=canonical_json(payload);encoded=base64.urlsafe_b64encode(raw).decode().rstrip('=')
        return encoded+'.'+hmac.new(self.secret,raw,hashlib.sha256).hexdigest()

    def _decode(self,token):
        try:
            if not isinstance(token,str) or len(token)>8192:raise ValueError()
            encoded,signature=token.split('.');raw=base64.b64decode(encoded+'='*(-len(encoded)%4),altchars=b'-_',validate=True)
            if not hmac.compare_digest(hmac.new(self.secret,raw,hashlib.sha256).hexdigest(),signature):raise ValueError()
            payload=json.loads(raw)
            if payload['expires']<time.time():raise ServiceError('Cursor expired; restart this search','cursor_expired',410)
            return payload
        except ServiceError:raise
        except (ValueError,KeyError,TypeError):raise ServiceError('Invalid pagination cursor','invalid_cursor') from None

    def _query_snapshot(self,store,sid):
        """Reuse a verified compact query index; rehash every bound CAS page each time.

        Shares the existing index-cache byte budget.  The full manifest is checked
        before insertion.  Neither source bindings nor content checks are skipped.
        """
        key=('verified-query-snapshot',sid)
        with self.cache_lock:
            found=self.cache.pop(key,None)
            if found is not None:self.cache[key]=found
        if found is not None:
            cached=found[0]
            if store._binding(sid)!=cached['binding']:raise ValueError('Cached snapshot binding changed')
            for reference in cached['artifacts']:store.artifacts._read_verified_raw(reference)
            return json.loads(cached['context'])
        manifest=store.snapshot(sid);binding=store._binding(sid)
        value=store.artifacts.get_json(binding['artifact'])
        refs=[binding['artifact']]
        if value['revision'].startswith('catalog-snapshot-index-'):
            refs.extend(page['artifact'] for page in value['pages'])
        self._save_board_view(manifest,binding,refs)
        context={k:v for k,v in manifest.items() if k!='memberships'}
        # Store the query context as immutable bytes; callers receive independent
        # decoded objects and cannot mutate a future query's verified metadata.
        context_bytes=canonical_json(context)
        cached=dict(context=context_bytes,binding=binding,artifacts=refs)
        size=len(context_bytes)+len(canonical_json(dict(binding=binding,artifacts=refs)))
        with self.cache_lock:
            if size<=self.cache_bytes:
                old=self.cache.pop(key,None)
                if old:self.cache_size-=old[1]
                self.cache[key]=(cached,size);self.cache_size+=size
                while self.cache_size>self.cache_bytes:
                    _,(_,removed)=self.cache.popitem(last=False);self.cache_size-=removed
        return context

    def _read_view_get(self,key):
        """Independent decoded metadata plus immutable typed columns."""
        with self.cache_lock:
            found=self.cache.pop(key,None)
            if found is None:return None
            self.cache[key]=found
            header,columns=found[0]
        return json.loads(header),columns

    def _read_view_put(self,key,value):
        header,columns=value
        header=canonical_json(header)
        if not isinstance(columns,bytes):raise TypeError('Read-view columns must be immutable')
        size=len(header)+len(columns)+len(canonical_json(key))
        with self.cache_lock:
            old=self.cache.pop(key,None)
            if old:self.cache_size-=old[1]
            if size>self.cache_bytes:return
            self.cache[key]=((header,columns),size);self.cache_size+=size
            while self.cache_size>self.cache_bytes:
                _,(_,removed)=self.cache.popitem(last=False);self.cache_size-=removed

    def _save_board_view(self,manifest,binding,refs):
        from .products import product_registry_v2
        products={p['id']for p in product_registry_v2()['products']}
        members={pid:[]for pid in products}
        for row in manifest['memberships']:
            if row['objective_id']in members:members[row['objective_id']].append(row['member'])
        context={k:v for k,v in manifest.items()if k not in ('worlds','memberships','registry','policy_contract')}
        context['board_members']=members
        self._read_view_put(('verified-board-view-v1',binding['snapshot_id']),
            (dict(context=context,binding=binding,artifacts=refs),b''))

    def _board_snapshot(self,store,sid):
        key=('verified-board-view-v1',sid);found=self._read_view_get(key)
        if found is not None:
            cached,_=found
            if store._binding(sid)!=cached['binding']:raise ValueError('Cached snapshot binding changed')
            for reference in cached['artifacts']:store.artifacts._read_verified_raw(reference)
            return cached['context']
        # A cold or evicted view always derives from the full original verifier.
        # It is ephemeral; queries never publish files or regenerate an index.
        manifest=store.snapshot(sid);binding=store._binding(sid)
        value=store.artifacts.get_json(binding['artifact']);refs=[binding['artifact']]
        if value['revision'].startswith('catalog-snapshot-index-'):
            refs.extend(page['artifact']for page in value['pages'])
        self._save_board_view(manifest,binding,refs)
        found=self._read_view_get(key)
        if found is not None:return found[0]['context']
        # A zero/tiny cache is valid; don't require retention to serve correctly.
        return dict(manifest,board_members={})

    def _cached_index(self,layouts):
        from .index import build_index,index_identity
        key=index_identity(layouts)
        with self.cache_lock:
            found=self.cache.pop(key,None)
            if found is not None:self.cache[key]=found;return found[0],True
        index=build_index(layouts);size=len(canonical_json(index))
        with self.cache_lock:
            old=self.cache.pop(key,None)
            if old:self.cache_size-=old[1]
            if size<=self.cache_bytes:
                self.cache[key]=(index,size);self.cache_size+=size
                while self.cache_size>self.cache_bytes:
                    _,(_,n)=self.cache.popitem(last=False);self.cache_size-=n
        return index,False

    def _cached_result(self,key):
        with self.cache_lock:
            found=self.result_cache.pop(key,None)
            if found is None:return None
            blob,expires=found
            if time.monotonic()>expires:self.result_size-=len(blob);return None
            self.result_cache[key]=found
        return json.loads(blob)

    def _save_result(self,key,ranked,matched,proof,extra=None):
        # Store immutable JSON bytes; page responses cannot mutate future pages.
        blob=canonical_json(dict(ranked=[dict(row,_sort_key=[str(v) for v in row['_sort_key']]) for row in ranked],matched=matched,proof=proof,**({'extra':extra} if extra is not None else {})))
        if len(blob)>self.result_bytes:return
        with self.cache_lock:
            old=self.result_cache.pop(key,None)
            if old:self.result_size-=len(old[0])
            self.result_cache[key]=(blob,time.monotonic()+3600);self.result_size+=len(blob)
            while len(self.result_cache)>8 or self.result_size>self.result_bytes:
                _,(removed,_)=self.result_cache.popitem(last=False);self.result_size-=len(removed)

    def query(self,body):
        if self.query_workers is not None:
            start=time.monotonic();deadline=start+self.query_seconds
            with self._slot(wait_seconds=min(2,self.query_seconds)):
                return self.query_workers.query(body,deadline=deadline,acquire_deadline=min(start+2,deadline))
        if isinstance(body,dict) and isinstance(body.get('request'),dict) and body['request'].get('request_revision') in ('catalog-query-v2','catalog-query-v3'):
            from .automation_query import query
            return query(self,body)
        if isinstance(body,dict) and isinstance(body.get('request'),dict) and body['request'].get('request_revision')=='catalog-query-accuracy-v1':
            from .accuracy_query import query
            return query(self,body)
        if not isinstance(body,dict) or set(body)-{'request','page_size','cursor'} or 'request' not in body:
            raise ServiceError('Expected request, optional page_size and cursor')
        size=body.get('page_size',20)
        if type(size) is not int or not 1<=size<=50:raise ServiceError('page_size must be 1..50')
        start=time.monotonic();deadline=start+self.query_seconds
        def check():
            if time.monotonic()>deadline:raise ServiceError('Catalog query exceeded its time allowance','query_timeout',503)
        with self._slot(),self._store() as store:
            req=validate_request(body['request']);info=store.info(req['catalog_snapshot_id']);header=info['header']
            req=validate_request(req,snapshot_id=info['snapshot_id'],game_build_id=header['game_build_id'],world_settings_id=header['world_settings_id'])
            request_sha=digest(req);cursor=self._decode(body['cursor']) if body.get('cursor') else None
            if cursor and (cursor['request']!=request_sha or cursor['snapshot']!=info['snapshot_id'] or cursor['size']!=size):
                raise ServiceError('Cursor belongs to another request or snapshot','cursor_mismatch')
            check();key=digest([info['snapshot_id'],request_sha])
            proof=digest(store.conn.execute('SELECT world_id,observation_id,seed,manifest_sha256 FROM observation_ref WHERE snapshot_id=? ORDER BY world_id',(info['snapshot_id'],)).fetchall())
            cached=self._cached_result(key);segments=decoded=eligible=cache_hits=0
            if cached is not None:
                store._verified_membership(info['snapshot_id']);check()
                if cached['proof']!=proof:raise ServiceError('Snapshot observation membership changed','integrity_error',503)
                ranked=cached['ranked'];matched_count=cached['matched']
            else:
                from .index import candidate_indices
                collector=TopWorlds();matched=set()
                for segment in store.iter_segments(info['snapshot_id'],request=req):
                    check();rows=segment['layouts'];segments+=1;decoded+=len(rows)
                    index=segment.get('index')
                    if index is None:
                        index,hit=self._cached_index(rows)
                    else:hit=True
                    cache_hits+=int(hit)
                    indices=list(range(len(rows))) if segment.get('prefiltered') else candidate_indices(rows,req,index=index,trusted=True)
                    eligible+=len(indices)
                    by_layout={r['layout_id']:r for r in rows}
                    for result in _rank([rows[i] for i in indices],req,1000,validate_records=False,keep_keys=True):
                        check();matched.add(result['world_id']);layout=by_layout[result['layout_id']]
                        for field in ('counts','structure_nearest_d2','biome_nearest_d2','complete'):result[field]=layout[field]
                        result['bounds']=list(bounds_for(layout['anchor'],layout['border_side']));collector.offer(result)
                ranked=collector.results();matched_count=len(matched)
                self._save_result(key,ranked,matched_count,proof)
            check();offset=0
            if cursor:
                # Canonical rank serialized as decimal text; reranking compares the
                # exact original tuple, including deterministic50-digit profile H.
                last=cursor['last']
                matches=[i for i,r in enumerate(ranked) if [str(v) for v in r['_sort_key']]==last]
                if not matches:raise ServiceError('Saved page boundary is unavailable','cursor_mismatch',409)
                offset=matches[0]+1
            page=ranked[offset:offset+size];next_cursor=None
            if offset+size<len(ranked):
                next_cursor=self._token(dict(snapshot=info['snapshot_id'],request=request_sha,size=size,
                    last=[str(v) for v in page[-1]['_sort_key']],expires=cursor['expires'] if cursor else time.time()+3600))
            for row in page:row.pop('_sort_key')
            return dict(ok=True,snapshot_id=info['snapshot_id'],request_sha256=request_sha,results=page,
                next_cursor=next_cursor,truncated=matched_count>1000,matched_worlds=matched_count,
                stats=dict(segments=segments,decoded_layouts=decoded,eligible_layouts=eligible,index_cache_hits=cache_hits,
                    result_cache_hit=cached is not None,wall_seconds=time.monotonic()-start),evidence_label=EVIDENCE)

    def biome_scope(self,body):
        from .accuracy_store import read_bundle
        from .refinement import evaluate_scope,provider_id
        from .models import world_id
        required={'snapshot_id','accuracy_generation','world_id','provider_id','bounds','y','any_ids'}
        if not isinstance(body,dict) or not required<=set(body) or set(body)-required-{'anchor','radius'}:
            raise ServiceError('Invalid exact-scope biome request')
        from .accuracy import sha256,integer
        from .refinement import _bounds
        for key in ('snapshot_id','accuracy_generation','world_id','provider_id'):sha256(body[key])
        _bounds(body['bounds'],cap=65536);integer(body['y'],-64,319)
        if not isinstance(body['any_ids'],list) or not 1<=len(body['any_ids'])<=256:raise ServiceError('Invalid biome alternatives')
        for value in body['any_ids']:integer(value,0,0xfffffffe)
        if ('anchor'in body)!=('radius'in body):raise ServiceError('Circle needs anchor and radius')
        if 'anchor'in body:
            if not isinstance(body['anchor'],list) or len(body['anchor'])!=2:raise ServiceError('Invalid scope anchor')
            for value in body['anchor']:integer(value,-30000000,30000000)
            integer(body['radius'],0,8192)
        start=time.monotonic()
        with self._slot(),self._store() as store:
            sid=body['snapshot_id'];store.info(sid);store._verified_membership(sid)
            member=store.conn.execute('SELECT seed FROM observation_ref WHERE snapshot_id=? AND world_id=?',(sid,body['world_id'])).fetchone()
            if member is None:raise ServiceError('World is not in snapshot')
            _,bundle=read_bundle(self.root,sid,body['accuracy_generation'])
            tiles=[t for t in bundle['tiles'] if world_id(t['context']['identity'])==body['world_id'] and provider_id(t['context'])==body['provider_id'] and t['y']==body['y']]
            if not tiles:return dict(ok=True,status='unknown',reason='No saved tile for this provider/height; no game or refinement job was launched')
            proof=evaluate_scope(tiles,tiles[0]['context'],body['bounds'],body['y'],body['any_ids'],anchor=body.get('anchor'),radius=body.get('radius'))
            if time.monotonic()-start>self.query_seconds:raise ServiceError('Biome scope allowance exhausted','query_timeout',503)
            return dict(ok=True,snapshot_id=sid,accuracy_generation=body['accuracy_generation'],**proof)

    def detail(self,snapshot_id,world_id,layout_id):
        start=time.monotonic()
        for value in (snapshot_id,world_id,layout_id):
            if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
                raise ServiceError('Invalid detail identity')
        from .automation_query import available,detail
        if available(self.root,snapshot_id):return detail(self,snapshot_id,world_id,layout_id)
        with self._slot(),self._store() as store:
            store.info(snapshot_id);layout=None
            for segment in store.iter_segments(snapshot_id,layout_key=(world_id,layout_id)):
                if time.monotonic()-start>self.query_seconds:raise ServiceError('Catalog detail wall allowance exhausted','timeout',504)
                layout=next((r for r in segment['layouts'] if r['world_id']==world_id and r['layout_id']==layout_id),None)
                if layout is not None:break
            anchor_evidence=None;anchor_roles=[]
            if layout is None:
                from .accuracy_query import bound_entries
                try:
                    for entry in bound_entries(store,snapshot_id,None):
                        if entry['world_id']!=world_id:continue
                        found=next((row for row in entry['layouts'] if row['layout_id']==layout_id),None)
                        if found is not None:
                            layout=found;anchor_roles.append(entry['anchor'])
                    if len(anchor_roles)==1:anchor_evidence=anchor_roles[0]
                except FileNotFoundError:pass
            if layout is None:raise ServiceError('Layout is not in this snapshot','not_found',404)
            obs=store.observation(snapshot_id,world_id);lo_x,lo_z,hi_x,hi_z=bounds_for(layout['anchor'],layout['border_side'])
            points={};remaining=5000;truncated=False
            for fid,rows in obs['structures'].items():
                inside=[p for p in rows if lo_x<=p[0]<hi_x and lo_z<=p[1]<hi_z]
                points[fid]=inside[:remaining];remaining-=len(points[fid]);truncated|=len(inside)>len(points[fid])
            witnesses=[]
            for feature in BIOMES:
                slot=feature['slot'];ref=layout['biome_witness_refs'][slot]
                if ref==MISSING:continue
                if not 0<=ref<len(obs['biomes']):raise ServiceError('Invalid saved witness reference','integrity_error',503)
                x,y,z,_=obs['biomes'][ref]
                witnesses.append(dict(feature=feature['id'],x=x,y=y,z=z,distance_squared=layout['biome_nearest_d2'][slot]))
            from .evidence import read_evidence, summarize_structure, validate_evidence
            from .models import observation_id
            try:
                evidence = read_evidence(self.root, snapshot_id, world_id, observation_id(obs))
                if evidence is not None:
                    validate_evidence(evidence, observation=obs)
                structure_evidence = {}
                for fid, positions in points.items():
                    total = sum(lo_x <= x < hi_x and lo_z <= z < hi_z for x,z in obs['structures'][fid])
                    structure_evidence[fid] = summarize_structure(evidence, fid, positions, total_count=total)
                biome_checks = [] if evidence is None else [row for row in evidence['biome_checks']
                    if lo_x <= row['position'][0] < hi_x and lo_z <= row['position'][2] < hi_z]
            except (ValueError, OSError, KeyError, TypeError):
                raise ServiceError('Detail evidence failed integrity validation', 'integrity_error', 503) from None
            if time.monotonic()-start > self.query_seconds:
                raise ServiceError('Catalog detail evidence wall allowance exhausted','timeout',504)
            from .accuracy_store import read_bundle
            from .refinement import provider_id
            from .models import world_id as identify_world
            accuracy=None
            try:
                generation,bundle=read_bundle(self.root,snapshot_id)
                accuracy=dict(generation=generation,tiles=[dict(tile_id=t['tile_id'],provider=t['context']['provider'],provider_id=provider_id(t['context']),bounds=t['bounds'],y=t['y'],biome_names=t['biome_names'])
                    for t in bundle['tiles'] if identify_world(t['context']['identity'])==world_id],
                    interpretation='Saved exact-scope tiles only; uncovered points and other providers remain unknown.')
            except FileNotFoundError:pass
            return dict(ok=True,snapshot_id=snapshot_id,world_id=world_id,identity=obs['identity'],layout=layout,anchor_evidence=anchor_evidence,anchor_roles=anchor_roles,accuracy=accuracy,
                structures=points,structures_truncated=truncated,biome_witnesses=witnesses,coverage=obs['coverage'],evidence_label=EVIDENCE,
                structure_evidence=structure_evidence,biome_evidence=dict(method='BDS getBiome at the recorded XYZ',
                    interpretation='Sampling semantics remain under review; these observations do not certify biome witnesses.',
                    verifier_game_build_id=None if evidence is None else evidence['verifier']['game_build_id'],checks=biome_checks))
