# Actual additive store source for independent review

Caller holds HarvestQueue.ownership/publication flock for mutations. Existing ArtifactStore validates compressed SHA,length,key,codec,decompression cap16MiB. Existing atomic_json fsyncs file/parent and rejects symlink paths. Existing models/codec validators are real, strict and independently tested. No fallback validators.

```python
class AutomationStore:
    """Additive immutable v2 bundles/snapshots; caller serializes writers with queue ownership."""
    def __init__(self,root):
        from .ingestion import verify_no_symlinks
        self.root=verify_no_symlinks(Path(root).absolute())
        for name in _FORBIDDEN_PERSONAL_FILES:
            if (self.root/name).exists():raise ValueError('Personal database root prohibited')
        self.base=verify_no_symlinks(self.root/'automation')
        self.objects_dir=self.base/'objects';self.snapshots_dir=self.base/'snapshots'
        self.current_path=self.base/'current.json';self.quarantine_dir=self.base/'quarantine'
        self._artifacts=None

    @property
    def artifacts(self):
        if self._artifacts is None:self._artifacts=ArtifactStore(self.objects_dir)
        return self._artifacts

    @staticmethod
    def _sha(value):
        if not isinstance(value,str) or not _HEX64_RE.fullmatch(value):raise ValueError('Invalid SHA identity')
        return value

    def _read(self,path):
        from .ingestion import verify_no_symlinks,strict_json_loads
        path=verify_no_symlinks(path)
        if not path.is_file():raise FileNotFoundError(path)
        if path.stat().st_size>16384:raise ValueError('Binding byte cap')
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
        artifact=self.artifacts.put_json(manifest)
        binding=dict(revision='catalog-snapshot-binding-v2',snapshot_id=sid,generation=manifest['generation'],artifact=artifact)
        path=verify_no_symlinks(self.snapshots_dir/(sid+'.json'))
        if path.exists():
            if self._read(path)!=binding:raise ValueError('Immutable snapshot binding differs')
        else:atomic_json(path,binding)
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
        binding=self._binding(snapshot_id);manifest=self._manifest(self.artifacts.get_json(binding['artifact']))
        if registry.digest(manifest)!=binding['snapshot_id'] or manifest['generation']!=binding['generation']:raise ValueError('Snapshot digest/generation mismatch')
        return manifest

    def snapshots(self):
        from .ingestion import verify_no_symlinks
        verify_no_symlinks(self.snapshots_dir)
        if not self.snapshots_dir.exists():return []
        values=[]
        for path in sorted(self.snapshots_dir.iterdir()):
            verify_no_symlinks(path)
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
        path=self.base/'pins.json';pins=self._read(path) if path.exists() else []
        if not isinstance(pins,list):raise ValueError('Invalid pins')
        value=dict(snapshot_id=snapshot_id,world_id=world_id)
        if value not in pins:pins.append(value)
        atomic_json(path,pins)

    def cleanup(self,ledger,*,mode='dry_run'):
        """Fail closed before any move; immutable history and resumable receipts are roots."""
        from .ingestion import verify_no_symlinks
        from .artifacts import _CONTENT_ADDR_RE,_fsync_dir
        if mode not in ('dry_run','quarantine','delete'):raise ValueError('Unknown cleanup mode')
        protected=set()
        for row in self.snapshots():
            binding=self._binding(row['snapshot_id']);protected.add(binding['artifact']['relative_key'])
            for entry in self.snapshot(row['snapshot_id'])['worlds']:
                self._bundle(self.artifacts.get_json(entry['artifact']),entry)
                protected.add(entry['artifact']['relative_key'])
        if self.current_path.exists():self.snapshot()
        pins_path=verify_no_symlinks(self.base/'pins.json')
        if pins_path.exists():
            pins=self._read(pins_path)
            if not isinstance(pins,list):raise ValueError('Invalid pins')
            for pin in pins:
                if not isinstance(pin,dict) or set(pin)!={'snapshot_id','world_id'}:raise ValueError('Invalid pin')
                self.world(pin['snapshot_id'],pin['world_id'])
        wanted=set(ledger.retained_worlds())
        receipts=ledger.receipts() if hasattr(ledger,'receipts') else [ledger.receipt(wid) for wid in wanted]
        for receipt in receipts:
            if receipt is None:raise ValueError('Missing retained receipt')
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

```
