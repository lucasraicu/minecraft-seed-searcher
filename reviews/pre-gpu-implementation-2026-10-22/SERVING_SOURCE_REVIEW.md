User approved A-D, GPU contract only, DB comparison. High read-only tool-free critique; do not invoke any tools/commands or edit files. Report concrete correctness defects with evidence.

Existing _query_snapshot verifies full manifest/digest on insertion and rehashes binding plus all bound pages on every reuse, within existing32MiB index/32MiB result budget. New ephemeral board views use same guards; no disk publication or migration. Typed masks only exclude proven complete structure failures. Original scorer retains ANY biome unknowns and ALL required same-anchor.

SERVICE SOURCE
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



READ VIEW SOURCE
"""Ephemeral immutable read models; original CAS and scorer remain authoritative.

No query writes an index or starts extraction. Read models share CatalogService's
existing serialized-cache allowance and are expendable after a process restart.
"""
import struct
from .registry import canonical_json,digest


def structure_rules(request,registry):
    """Only proven complete structure failures can remove an anchor.

    Missing biome witnesses always remain unknown; a biome ANY row cannot exclude
    anything. Preferences cannot exclude anything either.
    """
    by_id={f['id']:f for f in registry['features']};rules=[]
    for row in request['rows']:
        if row['rule']!='required' or row['kind']!='structure_count':continue
        fid=row['feature'];dimension=by_id[fid]['dimension'];scope=row['scope']
        radii=registry.get('nether_radii',(64,128,256))if dimension=='nether'else registry.get('overworld_radii',(256,512,1024))
        index=3 if scope['kind']=='inside_border'else list(radii).index(scope['radius'])
        rules.append((fid,index,row['at_least']))
    return rules


def pack_masks(rows,registry):
    features=[f['id']for f in registry['features']if f['kind']=='structure_count']
    # Counts are factual uint32 values, never clipped to the UI maximum 32.
    stride=len(rows)*20;parts=[]
    for fid in features:
        for row in rows:
            blocks=getattr(row['features'],'blocks',None)
            if blocks is not None:
                slot,_=row['features'].slots[fid]
                counts,complete,_,_=blocks[slot]
            else:
                block=row['features'][fid];counts=block['counts']
                complete=sum(int(bool(v))<<i for i,v in enumerate(block['complete']))
            parts.append(struct.pack('<5I',*counts,complete))
    return dict(features=features,layouts=[r['layout_id']for r in rows],stride=stride),b''.join(parts)


def candidate_layouts(header,columns,rules):
    slots={fid:i for i,fid in enumerate(header['features'])};allowed=[]
    for i,lid in enumerate(header['layouts']):
        keep=True
        for fid,scope,minimum in rules:
            offset=slots[fid]*header['stride']+i*20
            count=struct.unpack_from('<I',columns,offset+scope*4)[0]
            complete=struct.unpack_from('<I',columns,offset+16)[0]
            if count<minimum and complete&(1<<scope):keep=False;break
        if keep:allowed.append(lid)
    return set(allowed)


def filtered_summaries(service,store,manifest,request,check):
    """Warm typed masks avoid JSON decoding worlds with no possible anchor.

    Every reused mask rehashes its bound projection, even when no rows survive.
    Snapshot pages/bindings have already been checked by _query_snapshot. Cold
    masks come through the original projection validation and are request-local.
    """
    registry=manifest.get('registry')
    if registry is None:
        from .registry import REGISTRY_V2
        registry=REGISTRY_V2
    rules=structure_rules(request,registry)
    side=request['border_side'];mode=request['anchor_mode']
    if not rules:
        for row in store.iter_query_summaries(manifest,side,mode,lazy_features=True):check();yield row
        return
    validator=store._query_validator_id()
    for entry in manifest['worlds']:
        check()
        if 'summary_artifacts'not in entry:
            # Old immutable snapshots retain the original fully verified path.
            for row in store.iter_query_summaries(dict(manifest,worlds=[entry]),side,mode,lazy_features=True):yield row
            continue
        reference=entry['summary_artifacts'][str(side)]
        key=('typed-structure-mask-v1',digest([entry,side,mode,validator]))
        cached=service._read_view_get(key)
        rows=None
        if cached is not None:
            # Includes length/SHA and symlink checks. Never trust stat/mtime alone.
            store.artifacts._read_verified_raw(reference)
            header,columns=cached
        else:
            rows=store._projection(entry,side,mode,lazy_features=True)
            header,columns=pack_masks(rows,registry)
            service._read_view_put(key,(header,columns))
        selected=candidate_layouts(header,columns,rules)
        if not selected:continue
        if rows is None:rows=store._projection(entry,side,mode,lazy_features=True)
        for row in rows:
            if row['layout_id']in selected:check();yield row


QUERY INTEGRATION: layouts() now delegates to filtered_summaries(service,store,manifest,req,check). Boards call _board_snapshot instead of fullsnapshot and read board_members[pid]; tinycache fallback uses original manifest memberships. Cursor, reserve splitting, counts and response assembly unchanged.

Masks built via original store._projection validates source bindings, dimensions, registry/profile, original trusted summary_validator fingerprint. Warm mask reuse rehashes exact summary artifact; identity key digest(entry,side,mode,validator). Existing result-cache hits still verify snapshot pages but do not re-read projection; unchanged existing contract.

Tests include mutation isolation, bound unrelated-page corruption, binding swaps, tinycache/eviction, sameanchor split witnesses, unknown survival, unclipped factualcounts, original fullscorer equality and warmprojection corruption. Tool-free review does not run tests.