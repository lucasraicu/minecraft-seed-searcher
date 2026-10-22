# Final source-backed readpath / status review
Approvedscope sharedautomation steps2/4/5. Frozen1250/845/265/140,personalscoreNativeunchanged. Measuredold20world10.034s timeout. Newper-sideCASprojectionsoptionalinimmutablemanifest, rawbundlealwayskeptanddetailunchanged. 37focusedtests pass; latest39checks inprogress afterpendingcounters added. 500worldfullsortoracle/21.8MiB CAS20page tests passed, no overallcompletionclaim. Review concrete implementeddefects only; no newproductscope or latencyinventions. Previousplanreviewtypo corrected:bundle_sha uses artifact.sha256. Samegenerationreuse intentionally ignoresderivedprojection/statmetadata, never overwrites existingbinding. Productionimport firstallocationcurrentlyoldloadedstore, nextallocationadoptsnewsource.

    def _manifest(self,value):
        from .harvest import _validate_rank
        fields={'revision','policy_revision','generation','population_worlds','worlds','memberships'}
        if not isinstance(value,dict) or set(value) not in (fields,fields|{'product_status'}) or value['revision']!='catalog-snapshot-v2':raise ValueError('Invalid snapshot schema')
        self._sha(value['policy_revision'])
        for key in ('generation','population_worlds'):
            if type(value[key]) is not int or value[key]<0:raise ValueError('Invalid snapshot counters')
        if 'product_status' in value and not isinstance(value['product_status'],dict):raise ValueError('Invalid product status totals')
        for pid,counts in value.get('product_status',{}).items():
            if (not isinstance(pid,str) or not isinstance(counts,dict) or set(counts)!={'match','no_match','pending'}
                    or any(type(n) is not int or n<0 for n in counts.values())
                    or sum(counts.values())>value['population_worlds']):raise ValueError('Invalid product status totals')
        worlds=value['worlds'];members=value['memberships']
        if not isinstance(worlds,list) or len(worlds)>105644 or len(worlds)>value['population_worlds'] or not isinstance(members,list) or len(members)>105644:
            raise ValueError('Snapshot capacity exceeded')
        by_world={};headers=set()
        for entry in worlds:
            fields={'world_id','identity','observation_id','artifact'}
            if not isinstance(entry,dict) or set(entry) not in (fields,fields|{'summary_artifacts'}):raise ValueError('Invalid world reference')
            wid=self._sha(entry['world_id']);self._sha(entry['observation_id']);models.validate_identity(entry['identity'])
            if wid in by_world or models.world_id(entry['identity'])!=wid:raise ValueError('Duplicate or unbound world')
            self.artifacts._validate_manifest(entry['artifact']);by_world[wid]=entry
            if 'summary_artifacts' in entry:
                if not isinstance(entry['summary_artifacts'],dict) or set(entry['summary_artifacts'])!={'2048','4096','8192'}:
                    raise ValueError('Invalid summary projection scopes')
                for artifact in entry['summary_artifacts'].values():self.artifacts._validate_manifest(artifact)
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

    def publish(self,ledger,*,fault=None):
        from .ingestion import atomic_json,verify_no_symlinks
        members=ledger.members();worlds=[]
        winning=sorted({row['world_id'] for row in members})
        if winning!=sorted(ledger.retained_worlds()):raise ValueError('Retained union differs')
        for wid in winning:
            receipt=ledger.receipt(wid)
            if receipt is None:raise ValueError('Missing winning receipt')
            entry={key:receipt[key] for key in ('world_id','identity','observation_id','artifact')}
            bundle=self._bundle(self.artifacts.get_json(entry['artifact']),entry)
            entry['summary_artifacts']={str(side):self.artifacts.put_json(dict(
                revision='catalog-query-projection-v2',world_id=wid,identity=entry['identity'],
                observation_id=entry['observation_id'],bundle_sha256=entry['artifact']['sha256'],
                border_side=side,rows=[r for r in bundle['summaries'] if r['border_side']==side])) for side in (2048,4096,8192)}
            worlds.append(entry)
        manifest=self._manifest(dict(revision='catalog-snapshot-v2',policy_revision=ledger.policy_revision,
            generation=ledger.generation(),population_worlds=ledger.population(),worlds=worlds,memberships=members))
        product_status={}
        for receipt in ledger.receipts():
            seen=set()
            for evaluation in receipt['evaluations']:
                pid=evaluation.get('product_id');status=evaluation.get('status')
                if (not isinstance(pid,str) or pid in seen or status not in ('match','no_match','pending')
                        or evaluation.get('world_id')!=receipt['world_id']
                        or evaluation.get('observation_id')!=receipt['observation_id']):raise ValueError('Invalid product evaluation source')
                seen.add(pid)
                counts=product_status.setdefault(pid,dict(match=0,no_match=0,pending=0));counts[status]+=1
        if product_status:manifest['product_status']=product_status
        self._manifest(manifest)
        sid=registry.digest(manifest)
        if self.current_path.exists():
            current=self.snapshot()
            if current['policy_revision']!=manifest['policy_revision']:raise ValueError('Policy namespace differs; rebuild separately')
            if current['generation']>manifest['generation']:raise ValueError('Stale publication generation')
            if current['generation']==manifest['generation'] and registry.digest(current)!=sid:
                # Derived read projections cannot rewrite an existing generation.
                def without_projections(value):
                    return dict({k:v for k,v in value.items() if k!='product_status'},worlds=[{k:v for k,v in e.items() if k!='summary_artifacts'} for e in value['worlds']])
                if without_projections(current)!=without_projections(manifest):raise ValueError('Same generation has conflicting content')
                manifest=current;sid=registry.digest(current)
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

    def _projection(self,entry,side):
        """The immutable snapshot binds this derived view to its verified raw bundle."""
        value=self.artifacts.get_json(entry['summary_artifacts'][str(side)])
        fields={'revision','world_id','identity','observation_id','bundle_sha256','border_side','rows'}
        if (not isinstance(value,dict) or set(value)!=fields or value['revision']!='catalog-query-projection-v2'
                or any(value[k]!=entry[k] for k in ('world_id','identity','observation_id'))
                or value['bundle_sha256']!=entry['artifact']['sha256'] or value['border_side']!=side
                or not isinstance(value['rows'],list) or len(value['rows'])>1024):raise ValueError('Invalid query projection binding')
        seen=set()
        for row in value['rows']:
            if (not isinstance(row,dict) or row.get('world_id')!=entry['world_id'] or row.get('source_observation_id')!=entry['observation_id']
                    or row.get('seed')!=entry['identity']['seed'] or row.get('border_side')!=side
                    or row.get('layout_id') in seen):raise ValueError('Invalid projected summary source')
            seen.add(row['layout_id'])
        return value['rows']

    def iter_query_summaries(self,manifest,side,mode):
        """Read only the requested border; old immutable snapshots use their bundles."""
        from .codec import validate_summary_v2
        for entry in manifest['worlds']:
            rows=self._projection(entry,side) if 'summary_artifacts' in entry else self._bundle(self.artifacts.get_json(entry['artifact']),entry)['summaries']
            for row in rows:
                if row['border_side']==side and mode in row['anchor_modes']:
                    yield validate_summary_v2(row)

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
                for side,artifact in entry.get('summary_artifacts',{}).items():
                    if artifact['relative_key'] not in protected:
                        for row in self._projection(entry,int(side)):
                            from .codec import validate_summary_v2
                            validate_summary_v2(row)
                        protected.add(artifact['relative_key'])
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

UIcountsdecode
export interface ProductResultsV2Response {
  ok: boolean;
  revision: 'catalog-product-results-v2';
  snapshot_id: string;
  product_id: string;
  results: Evaluation[];
  matched_worlds: number;
  next_cursor: string | null;
  population_worlds: number;
  evaluation_counts?: {match:number;no_match:number;pending:number} | null;
  scope: Record<string, unknown>;
  policy_revision: string;
  evidence_label: string;
  error?: string;
  code?: string;
}

const BUTTON = 'rounded-lg border px-4 py-2 text-sm transition-colors';

