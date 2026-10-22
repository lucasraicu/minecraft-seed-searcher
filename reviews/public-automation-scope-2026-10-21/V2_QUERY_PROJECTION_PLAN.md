# Measured v2 query read-path correction within approved steps2/5

Measured actual20-world origin query fails at10.034s unchanged10sdeadline. Current iter_worlds loads/validates full102400point observations for summaries; raw facts irrelevant to query. No query rule/scoring/threshold/native changes.

Proposal: immutable world entries may ADD optional summary_artifacts map with exactly keys2048/4096/8192 and each a normal CASref. Existing4field world entries remain accepted. Publication after fully verifying bundle and summary source binding derives three projection artifacts, each {revision:catalog-query-projection-v2,world_id,identity,observation_id,bundle_sha256,border_side,rows:[full unchanged summary dicts for thatside]}. Normal16MiB CAS/readcaps remain. Snapshot hash directly binds refs; projection decoder validates exactschema, metadata againstentry, side/rowcap<=1024, each validate_summary_v2 and source/identity/duplicatebinding. Query reads only requestedside, filtersanchor_mode before per-summaryvalidation/ranking. All selectedrowvectors/sourceIDs stayunchanged, no approximateanswers. Older snapshots withoutprojection fall back fullverifiedbundle. Detail always usesrawbundle. GC verifies and protects ALL projection refs of ALL histories/pendinggenerations beforemoves. Refactoring publish samegeneration must reuse existing immutablebinding when logical memberships/population/source artifacts match; addingderivedprojections cannotchange samegeneration snapshot. Newgenerations can include them. No quota/sandbox/service/DBengine change. Need compare fullbundle vs projected queries exactly acrossall3sizes/modes/OW+Nether and strictcorruptions/sourcebinding/historicalGC. Re-measure cold actual200+ worlds under10s, no raisedtimeout. If JSONprojection still too slow report and measure next, no inventedlatency.

User-approvedrootplan already includes models/summaries/index readpath, SQLitemetadata+checksummedfacts and existing2queryprocesses; this is necessary measured correction, no publicscope expansion.

Relevant current source excerpts:

class AutomationStore:
    """Additive immutable v2 bundles/snapshots; caller serializes writers with queue ownership."""
    _PAGE_THRESHOLD_BYTES = 8 * 1024 * 1024
    _PAGE_ITEM_LIMIT = 2048
    _PAGE_BYTE_LIMIT = 4 * 1024 * 1024
    _INDEX_PAGE_LIMIT = 1024

    def __init__(self,root):
        from .ingestion import verify_no_symlinks
        self.root=verify_no_symlinks(Path(root).absolute())
        for name in _FORBIDDEN_PERSONAL_FILES:
            if (self.root/name).exists():raise ValueError('Personal database root prohibited')
        self.base=verify_no_symlinks(self.root/'automation')
        self.objects_dir=self.base/'objects';self.snapshots_dir=self.base/'snapshots'
        self.current_path=self.base/'current.json';self.quarantine_dir=self.base/'quarantine'
        self.generations_dir=self.base/'generations'
        self._artifacts=None

    @property
    def artifacts(self):
        if self._artifacts is None:self._artifacts=ArtifactStore(self.objects_dir)
        return self._artifacts

    @staticmethod
    def _sha(value):
        if not isinstance(value,str) or not _HEX64_RE.fullmatch(value):raise ValueError('Invalid SHA identity')
        return value

    def _read(self,path,*,max_bytes=16384):
        from .ingestion import verify_no_symlinks,strict_json_loads
        path=verify_no_symlinks(path)
        if not path.is_file():raise FileNotFoundError(path)
        if path.stat().st_size>max_bytes:raise ValueError('Metadata byte cap')
        return strict_json_loads(path.read_bytes())

    def _bundle(self,value,entry=None):
        from .models import validate_observation_v2
        from .codec import validate_summary_v2
        if not isinstance(value,dict) or set(value)!={'revision','observation','summaries'} or value['revision']!='catalog-world-bundle-v2':
            raise ValueError('Invalid world bundle')
        obs=validate_observation_v2(value['observation']);oid=registry.digest(obs);wid=models.world_id(obs['identity'])
        if entry is not None and (entry['world_id']!=wid or entry['identity']!=obs['identity'] or entry['observation_id']!=oid):
            raise ValueError('World bundle source mismatch')
        rows=value['summaries']
        if not isinstance(rows,list) or len(rows)>1024:raise ValueError('Summary count cap')
        seen=set()
        for row in rows:
            validate_summary_v2(row)
            if row['world_id']!=wid or row['seed']!=obs['identity']['seed'] or row['source_observation_id']!=oid:
                raise ValueError('Summary source mismatch')
            if row['layout_id'] in seen:raise ValueError('Duplicate layout')
            seen.add(row['layout_id'])
        return value

    def stage(self,observation,summaries):
        bundle=self._bundle(dict(revision='catalog-world-bundle-v2',observation=observation,summaries=summaries))
        return self.artifacts.put_json(bundle)

    def _manifest(self,value):
        from .harvest import _validate_rank
        fields={'revision','policy_revision','generation','population_worlds','worlds','memberships'}
        if not isinstance(value,dict) or set(value)!=fields or value['revision']!='catalog-snapshot-v2':raise ValueError('Invalid snapshot schema')
        self._sha(value['policy_revision'])
        for key in ('generation','population_worlds'):
            if type(value[key]) is not int or value[key]<0:raise ValueError('Invalid snapshot counters')
        worlds=value['worlds'];members=value['memberships']
        if not isinstance(worlds,list) or len(worlds)>105644 or len(worlds)>value['population_worlds'] or not isinstance(members,list) or len(members)>105644:
            raise ValueError('Snapshot capacity exceeded')
        by_world={};headers=set()
        for entry in worlds:
            if not isinstance(entry,dict) or set(entry)!={'world_id','identity','observation_id','artifact'}:raise ValueError('Invalid world reference')
            wid=self._sha(entry['world_id']);self._sha(entry['observation_id']);models.validate_identity(entry['identity'])
            if wid in by_world or models.world_id(entry['identity'])!=wid:raise ValueError('Duplicate or unbound world')
            self.artifacts._validate_manifest(entry['artifact']);by_world[wid]=entry
            headers.add(registry.digest({k:v for k,v in entry['identity'].items() if k!='seed'}))
        if len(headers)>1:raise ValueError('Mixed predictor generations')
        seen=set();previous=None
        for row in members:
            if not isinstance(row,dict) or set(row)!={'objective_id','world_id','rank','member'}:raise ValueError('Invalid membership')
            oid=row['objective_id'];wid=row['world_id'];member=row['member']
            if not isinstance(oid,str) or not 1<=len(oid)<=256 or wid not in by_world or not isinstance(member,dict) or member.get('world_id')!=wid:
                raise ValueError('Unbound winning member')
            key=(oid,wid)
            if key in seen:raise ValueError('Duplicate winning membership')
            seen.add(key)
            for field in ('source_observation_id','observation_id'):
                if field in member and member[field]!=by_world[wid]['observation_id']:raise ValueError('Stale member source')
            ordered=(oid,_validate_rank(row['rank']),wid)
            if previous is not None and ordered<previous:raise ValueError('Unordered winning members')
            previous=ordered
        if set(by_world)!={r['world_id'] for r in members}:raise ValueError('Unreferenced snapshot world')
        return value

    # Existing paged manifest writer/reader omitted; no changes planned.
    def publish(self,ledger,*,fault=None):
        from .ingestion import atomic_json,verify_no_symlinks
        members=ledger.members();worlds=[]
        winning=sorted({row['world_id'] for row in members})
        if winning!=sorted(ledger.retained_worlds()):raise ValueError('Retained union differs')
        for wid in winning:
            receipt=ledger.receipt(wid)
            if receipt is None:raise ValueError('Missing winning receipt')
            entry={key:receipt[key] for key in ('world_id','identity','observation_id','artifact')}
            self._bundle(self.artifacts.get_json(entry['artifact']),entry)
            worlds.append(entry)
        manifest=self._manifest(dict(revision='catalog-snapshot-v2',policy_revision=ledger.policy_revision,
            generation=ledger.generation(),population_worlds=ledger.population(),worlds=worlds,memberships=members))
        sid=registry.digest(manifest)
        if self.current_path.exists():
            current=self.snapshot()
            if current['policy_revision']!=manifest['policy_revision']:raise ValueError('Policy namespace differs; rebuild separately')
            if current['generation']>manifest['generation']:raise ValueError('Stale publication generation')
            if current['generation']==manifest['generation'] and registry.digest(current)!=sid:
                raise ValueError('Same generation has conflicting content')
        generation_path=verify_no_symlinks(self.generations_dir/(manifest['policy_revision']+'-'+str(manifest['generation'])+'.json'))
        existing_binding=None
        if generation_path.exists():
            prev=self._read(generation_path)
            if not isinstance(prev,dict) or prev.get('generation')!=manifest['generation'] or prev.get('snapshot_id')!=sid:
                raise ValueError('Conflicting immutable generation')
            existing_binding=prev
        snap_path=verify_no_symlinks(self.snapshots_dir/(sid+'.json'))
        if snap_path.exists():
            prev=self._read(snap_path)
            if not isinstance(prev,dict) or prev.get('snapshot_id')!=sid or prev.get('generation')!=manifest['generation']:
                raise ValueError('Immutable snapshot binding differs')
            if existing_binding is not None and prev!=existing_binding:
                raise ValueError('Immutable snapshot binding differs')
            existing_binding=prev
        if not generation_path.exists():
            for previous in self.snapshots_dir.glob('*.json'):
                existing=self._binding(previous.stem)
                if existing['generation']==manifest['generation']:
                    if existing['snapshot_id']!=sid:raise ValueError('Conflicting historical generation')
                    if existing_binding is not None and existing!=existing_binding:
                        raise ValueError('Conflicting historical generation')
                    existing_binding=existing
                    break
        if existing_binding is not None:
            if (set(existing_binding)!={'revision','snapshot_id','generation','artifact'}
                    or existing_binding['revision']!='catalog-snapshot-binding-v2'
                    or type(existing_binding['generation']) is not int):raise ValueError('Invalid reused snapshot binding')
            reused=self._resolve_manifest(existing_binding['artifact'])
            if registry.digest(reused)!=sid:raise ValueError('Reused snapshot content differs')
            binding=existing_binding
        else:
            artifact=self._write_manifest(manifest)
            binding=dict(revision='catalog-snapshot-binding-v2',snapshot_id=sid,generation=manifest['generation'],artifact=artifact)
        if generation_path.exists():
            if self._read(generation_path)!=binding:raise ValueError('Conflicting immutable generation')
        else:
            atomic_json(generation_path,binding)
        if fault:fault('after_generation')
        if snap_path.exists():
            if self._read(snap_path)!=binding:raise ValueError('Immutable snapshot binding differs')
        else:atomic_json(snap_path,binding)
        if fault:fault('after_manifest')
        if not self.current_path.exists() or self._read(self.current_path)!=binding:atomic_json(self.current_path,binding)
        if fault:fault('after_pointer')
        return sid

    def _binding(self,snapshot_id=None):
        if snapshot_id is not None:self._sha(snapshot_id)
        binding=self._read(self.current_path if snapshot_id is None else self.snapshots_dir/(snapshot_id+'.json'))
        if not isinstance(binding,dict) or set(binding)!={'revision','snapshot_id','generation','artifact'} or binding['revision']!='catalog-snapshot-binding-v2':
            raise ValueError('Invalid snapshot binding')
        sid=self._sha(binding['snapshot_id'])
        if snapshot_id is None and self._read(self.snapshots_dir/(sid+'.json'))!=binding:
            raise ValueError('Current pointer lacks matching immutable binding')
        if snapshot_id is not None and sid!=snapshot_id:raise ValueError('Snapshot identity differs')
        if type(binding['generation']) is not int or binding['generation']<0:raise ValueError('Invalid binding generation')
        self.artifacts._validate_manifest(binding['artifact'])
        return binding

    def snapshot(self,snapshot_id=None):
        binding=self._binding(snapshot_id);manifest=self._resolve_manifest(binding['artifact'])
        if registry.digest(manifest)!=binding['snapshot_id'] or manifest['generation']!=binding['generation']:raise ValueError('Snapshot digest/generation mismatch')
        return manifest

    def snapshots(self):
        from .ingestion import verify_no_symlinks
        verify_no_symlinks(self.snapshots_dir)
        if not self.snapshots_dir.exists():return []
        values=[]
        for path in sorted(self.snapshots_dir.iterdir()):
            verify_no_symlinks(path)
            if re.fullmatch(r'\.[a-f0-9]{64}\.json\.tmp\.[0-9]+\.[0-9]+',path.name) and path.is_file():continue
            if not path.is_file() or path.suffix!='.json':raise ValueError('Unexpected snapshot entry')
            sid=self._sha(path.stem);manifest=self.snapshot(sid)
            values.append(dict(snapshot_id=sid,generation=manifest['generation'],worlds=len(manifest['worlds']),population_worlds=manifest['population_worlds']))
        return sorted(values,key=lambda row:(row['generation'],row['snapshot_id']))

    def iter_worlds(self,snapshot_id):
        """Verify one manifest, then stream each bound bundle without quadratic reloading."""
        manifest=self.snapshot(snapshot_id)
        for entry in manifest['worlds']:
            yield self._bundle(self.artifacts.get_json(entry['artifact']),entry)

    def world(self,snapshot_id,world_id):
        self._sha(world_id);manifest=self.snapshot(snapshot_id)
        entry=next((entry for entry in manifest['worlds'] if entry['world_id']==world_id),None)
        if entry is None:raise KeyError('World is not in snapshot')
        return self._bundle(self.artifacts.get_json(entry['artifact']),entry)

    def pin(self,snapshot_id,world_id):
        """Explicit pin under writer ownership; historical snapshots already protect shares."""
        from .ingestion import atomic_json
        self.world(snapshot_id,world_id)
        path=self.base/'pins.json';pins=self._read(path,max_bytes=256<<10) if path.exists() else []
        if not isinstance(pins,list) or len(pins)>1000:raise ValueError('Invalid pins')
        value=dict(snapshot_id=snapshot_id,world_id=world_id)
        if value not in pins:
            if len(pins)>=1000:raise ValueError('Explicit pin capacity1000 reached')
            pins.append(value)
        atomic_json(path,pins)

    def cleanup(self,ledger,*,mode='dry_run'):
        """Fail closed before any move; immutable history and resumable receipts are roots."""
        from .ingestion import verify_no_symlinks
        from .artifacts import _CONTENT_ADDR_RE,_fsync_dir
        if mode not in ('dry_run','quarantine','delete'):raise ValueError('Unknown cleanup mode')
        protected=set();known={}
        def referenced_manifests():
            for row in self.snapshots():
                binding=self._binding(row['snapshot_id']);manifest=self._resolve_manifest(binding['artifact'],protected=protected)
                if registry.digest(manifest)!=binding['snapshot_id'] or manifest['generation']!=binding['generation']:raise ValueError('Snapshot digest/generation mismatch')
                known[binding['snapshot_id']]=(manifest['policy_revision'],binding)
                yield manifest
            verify_no_symlinks(self.generations_dir)
            if not self.generations_dir.exists():return
            for path in self.generations_dir.iterdir():
                verify_no_symlinks(path)
                if re.fullmatch(r'\.[a-f0-9]{64}-[0-9]+\.json\.tmp\.[0-9]+\.[0-9]+',path.name) and path.is_file():continue
                match=re.fullmatch(r'([a-f0-9]{64})-([0-9]+)\.json',path.name)
                if not match or not path.is_file():raise ValueError('Invalid generation entry')
                binding=self._read(path)
                if not isinstance(binding,dict) or set(binding)!={'revision','snapshot_id','generation','artifact'} or binding['revision']!='catalog-snapshot-binding-v2':raise ValueError('Invalid generation binding')
                sid=self._sha(binding['snapshot_id'])
                if sid in known:
                    policy,expected=known[sid]
                    if policy!=match[1] or str(binding['generation'])!=match[2] or binding!=expected:raise ValueError('Generation binding mismatch')
                    continue
                manifest=self._resolve_manifest(binding['artifact'],protected=protected)
                if registry.digest(manifest)!=sid or manifest['policy_revision']!=match[1] or str(manifest['generation'])!=match[2] or binding['generation']!=manifest['generation']:
                    raise ValueError('Generation binding mismatch')
                known[sid]=(manifest['policy_revision'],binding)
                yield manifest
        for manifest in referenced_manifests():
            for entry in manifest['worlds']:
                key=entry['artifact']['relative_key']
                if key not in protected:
                    self._bundle(self.artifacts.get_json(entry['artifact']),entry)
                    protected.add(key)
        if self.current_path.exists():self.snapshot()
        pins_path=verify_no_symlinks(self.base/'pins.json')
        if pins_path.exists():
            pins=self._read(pins_path,max_bytes=256<<10)
            if not isinstance(pins,list) or len(pins)>1000:raise ValueError('Invalid pins')
            for pin in pins:
                if not isinstance(pin,dict) or set(pin)!={'snapshot_id','world_id'}:raise ValueError('Invalid pin')
                self.world(pin['snapshot_id'],pin['world_id'])
        wanted=set(ledger.retained_worlds())
        if not callable(getattr(ledger,'receipts',None)):raise ValueError('All receipts are required for safe cleanup')
        receipts=ledger.receipts()
        for receipt in receipts:
            if not isinstance(receipt,dict) or not isinstance(receipt.get('replay'),dict):raise ValueError('Malformed replay receipt')
            if receipt['world_id'] in wanted or receipt['replay'].get('resumable'):
                self._bundle(self.artifacts.get_json(receipt['artifact']),receipt)
                protected.add(receipt['artifact']['relative_key']);wanted.discard(receipt['world_id'])
        if wanted:raise ValueError('Incomplete receipt roots')
        inventories={}
        for directory in (self.objects_dir,self.quarantine_dir):
            verify_no_symlinks(directory);entries=[]
            if directory.exists():
                for path in directory.rglob('*'):
                    verify_no_symlinks(path)
                    if path.is_dir():continue
                    relative=path.relative_to(directory).as_posix()
                    if relative.startswith('.tmp/') and directory==self.objects_dir:continue
                    if not path.is_file() or not _CONTENT_ADDR_RE.fullmatch(relative):raise ValueError('Unexpected object namespace entry')
                    if relative not in protected:entries.append((relative,path,path.stat().st_size))
            inventories[directory]=sorted(entries)
        selected=inventories[self.quarantine_dir if mode=='delete' else self.objects_dir]
        # Validate every destination before the first mutation.
        if mode=='quarantine':
            for key,source,_ in selected:
                target=verify_no_symlinks(self.quarantine_dir/key)
                if target.exists():raise ValueError('Quarantine destination exists; inspect duplicate first')
        for key,path,_ in selected:
            if mode=='delete':path.unlink();_fsync_dir(path.parent)
            elif mode=='quarantine':
                target=self.quarantine_dir/key;target.parent.mkdir(parents=True,exist_ok=True)
                path.replace(target);_fsync_dir(path.parent);_fsync_dir(target.parent)
        return dict(mode=mode,candidates=[key for key,_,_ in selected],bytes=sum(n for _,_,n in selected))


QUERY
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
    manifest=store.snapshot(snapshot_id) if manifest is None else manifest;sid=digest(manifest)
    worlds=manifest['worlds'];header={k:v for k,v in worlds[0]['identity'].items() if k!='seed'} if worlds else {}
    return dict(snapshot_id=sid,revision='catalog-snapshot-v2',worlds=len(worlds),
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
        req=validate_request_v2(body['request']);sid=req['catalog_snapshot_id']
        if not available(service.root,sid):raise ServiceError('V2 snapshot unavailable','not_found',404)
        store=_store(service);manifest=store.snapshot(sid);header=info(store,sid,manifest)['header']
        req=validate_request_v2(req,snapshot_id=sid,game_build_id=header.get('game_build_id'),world_settings_id=header.get('world_settings_id'))
        proof=digest(manifest);key=digest(['automation-query-v2',req]);cached=service._cached_result(key)
        if cached is not None:
            if cached['proof']!=proof:raise ServiceError('Snapshot changed','integrity_error',503)
            ranked=cached['ranked'];matched=cached['matched'];extra=cached['extra']
        else:
            def layouts():
                for bundle in store.iter_worlds(sid):
                    check()
                    identity=bundle['observation']['identity']
                    if {k:v for k,v in identity.items() if k!='seed'}!=header:raise ServiceError('Mixed predictor identities','integrity_error',503)
                    yield from bundle['summaries']
                    check()
            result=rank_v2(layouts(),req,limit=1000,keep_keys=True)
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

