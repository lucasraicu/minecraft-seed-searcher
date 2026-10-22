# Approved query deadline correction: packed derived JSON projection
Measured baseline on refreshed222world snapshot: store.snapshot3.40s, redundant info digest0.85s, redundant proof digest0.89s, origin projections11.34s (reading82rows/world despite yielding1). HTTP cold query503 at10.05s. Must preserve10second deadline, originalraw/summaries/registries/retention/scoring and artifact/IPC/RSS/output caps. Codex separately owns automation_query.py digest redundancy; do NOT edit that file. Migration complete3150.624s/3600 and root817MB; only449.376s cumulative allocation remains for derived republish, not a reset.

Implement a compact BACKWARD COMPATIBLE v5 derived JSON query projection in existing store.py, plus bounded tests. Standard CAS JSON arrays; no custom DB engine or new raw observation format. Original bundle/summary/layoutID/policy unchanged. Only query projections/manifest references change. Codex rebuilds projections from existing validatedv4 projections, no extraction or world summary generation. Addedimplementation<=200lines preferred, tests<=180lines. No newlarge scripts/framework.

Suggested exactv5header fields samev4, only revisioncatalog-query-projection-v5 and rows packed. Registry features order is bound immutable; row compacttuple [layout_id,anchor,anchor_modes,legacy,feature_blocks]. Block order registry.features, each [counts,complete_mask,nearest_d2,witness]. For biome_witness counts may4bitmask, structure counts stay4integerlist. Complete4bitmask. Reconstruct all exact catalog-summary-v3 fields from immutable entry+projectionheaders, anchor/netherfloor, andtuple. Do NOT lose source_extension_id/profile/registry/sourceobs/seed or legacy fallback scoring. Witness XYZ/provenance unchanged. Validate packed tuple structure/types/bounds before use; current trustedvalidator same sourcebound principle asv4, old mismatchedvalidator fallbackfull validate_summary_v3. Optional mode argument lets v5filter by packed anchor_modes BEFORE unpacking irrelevantrows. iter_query_summaries passesmode, cleanup no mode readsallrows. V4/V3/V2 projections continue readableunchanged. No silentlyaccept malformed arrays/countmasks/featurelength/sourcebindings; strictcodec fallback stillworks. Pack only writer-validated V3 rows. Roundtrip exact equality test for everyfield, source/XYZ unknowns, modefilter and v4legacycompat; malformedblock tests mustreject.

Add pure helper methods _pack_query_rows(rows,registry) and _unpack_query_rows(rows,entry,registry,side,mode=None), or equivalent. Publisher choosesv5fornewV3, V2staysv3. Must supportcoordinator reindexcalling packinghelper on existing _projection() validatedrows and replacing artifact refs; no runtimepatching.

Relevant current store.py source follows. Do not rewrite unrelated code. All existingdirty changes are approved/included in snapshot. Permission: editonly store.py and tests/catalog/test_packed_v3_projection.py; use exact permitted run-command wrapper for declaredcheck, no othercommands. Contextauthoritative, no need reread whole73KBfile. No native builds/searches/servers/migrationwrites. Check environment uses primaryvenvinterpreter with PYTHONPATHsrc:tests in isolatedsnapshot.

```python
    def _query_validator_id(self):
        if self._query_validator is None:
            import hashlib
            folder=Path(__file__).parent
            self._query_validator=registry.digest([registry.REGISTRY_REVISION_V2,
                {name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in
                 ('codec.py','anchors.py','geometry.py','models.py')}])
        return self._query_validator


```

```python
    def publish(self,ledger,*,fault=None,registry_v3=None,sampling_profile_revision=None,historically_complete=False):
        from .ingestion import atomic_json,verify_no_symlinks
        members=ledger.members();worlds=[]
        v3=getattr(ledger,'policy_contract',None) is not None
        if v3 and registry_v3 is None:raise ValueError('V3registry required')
        winning=sorted({row['world_id'] for row in members})
        if winning!=sorted(ledger.retained_worlds()):raise ValueError('Retained union differs')
        for wid in winning:
            receipt=ledger.receipt(wid)
            if receipt is None:raise ValueError('Missing winning receipt')
            entry={key:receipt[key] for key in ('world_id','identity','observation_id','artifact')}
            bundle=self._bundle(self.artifacts.get_json(entry['artifact']),entry)
            if v3:
                source=bundle['summaries'][0]
                if bundle['registry']!=registry_v3:raise ValueError('Mixed snapshot registries')
                entry.update({k:source[k] for k in ('registry_revision','sampling_profile_revision','source_extension_id')})
            entry['summary_artifacts']={str(side):self.artifacts.put_json(dict(
                revision='catalog-query-projection-v4' if v3 else 'catalog-query-projection-v3',
                **(dict(registry=registry_v3,sampling_profile_revision=entry['sampling_profile_revision'],source_extension_id=entry['source_extension_id']) if v3 else {}),
                world_id=wid,identity=entry['identity'],
                observation_id=entry['observation_id'],bundle_sha256=entry['artifact']['sha256'],
                summary_validator_sha256=self._query_validator_id(),
                row_count=sum(r['border_side']==side for r in bundle['summaries']),
                border_side=side,rows=[r for r in bundle['summaries'] if r['border_side']==side])) for side in (2048,4096,8192)}
            worlds.append(entry)
        extra={}
        if v3:
            from .reserve_policy import reserve_metadata
            extra=dict(policy_contract=ledger.policy_contract,registry=registry_v3,
                sampling_profile_revision=sampling_profile_revision,reserve_policy=reserve_metadata(historically_complete=historically_complete))
        manifest=self._manifest(dict(revision='catalog-snapshot-v3' if v3 else 'catalog-snapshot-v2',**extra,policy_revision=ledger.policy_revision,
            generation=ledger.generation(),population_worlds=ledger.population(),worlds=worlds,memberships=members))
        from .products import launch_definitions
        definitions=launch_definitions()
        product_ids={p['id'] for p in [definitions['realm'],*definitions.get('realm_sizes',[]),*definitions['presets'],*definitions['records']]}
        product_status={pid:dict(match=0,no_match=0,pending=0) for pid in sorted(product_ids)}
        for receipt in ledger.receipts():
            seen=set()
            for evaluation in receipt['evaluations']:
                pid=evaluation.get('product_id');status=evaluation.get('status')
                if (pid not in product_ids or pid in seen or status not in ('match','no_match','pending')
                        or evaluation.get('world_id')!=receipt['world_id']
                        or evaluation.get('observation_id')!=receipt['observation_id']):raise ValueError('Invalid product evaluation source')
                seen.add(pid)
                product_status[pid][status]+=1
            for pid in product_ids-seen:product_status[pid]['pending']+=1
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
                    # Migrated workspaces retain snapshots from older policies.
                    # Generation counters are local to a policy's ledger.
                    historical=self.snapshot(existing['snapshot_id'])
                    if historical['policy_revision']!=manifest['policy_revision']:continue
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


```

```python
    def _projection(self,entry,side):
        """The immutable snapshot binds this derived view to its verified raw bundle."""
        value=self.artifacts.get_json(entry['summary_artifacts'][str(side)])
        fields={'revision','world_id','identity','observation_id','bundle_sha256','border_side','rows'}
        if (not isinstance(value,dict) or
                (value.get('revision'),frozenset(value)) not in (
                    ('catalog-query-projection-v2',frozenset(fields)),
                    ('catalog-query-projection-v3',frozenset(fields|{'summary_validator_sha256','row_count'})),
                    ('catalog-query-projection-v4',frozenset(fields|{'summary_validator_sha256','row_count','registry','sampling_profile_revision','source_extension_id'})))
                or any(value[k]!=entry[k] for k in ('world_id','identity','observation_id'))
                or value['bundle_sha256']!=entry['artifact']['sha256'] or value['border_side']!=side
                or not isinstance(value['rows'],list) or len(value['rows'])>1024):raise ValueError('Invalid query projection binding')
        v3=value['revision']=='catalog-query-projection-v4'
        current=value['revision'] in ('catalog-query-projection-v3','catalog-query-projection-v4')
        if v3 and (registry.digest(value['registry'])!=entry['registry_revision'] or any(value[k]!=entry[k] for k in ('sampling_profile_revision','source_extension_id'))):raise ValueError('Projected v3evidence differs')
        if current:
            self._sha(value['summary_validator_sha256'])
            if type(value['row_count']) is not int or value['row_count']!=len(value['rows']):raise ValueError('Projection row count mismatch')
        trusted=current and value['summary_validator_sha256']==self._query_validator_id()
        seen=set()
        for row in value['rows']:
            if (not isinstance(row,dict) or row.get('world_id')!=entry['world_id'] or row.get('source_observation_id')!=entry['observation_id']
                    or row.get('seed')!=entry['identity']['seed'] or row.get('border_side')!=side
                    or row.get('layout_id') in seen):raise ValueError('Invalid projected summary source')
            seen.add(row['layout_id'])
            if not trusted:
                if v3:
                    from .codec import validate_summary_v3
                    validate_summary_v3(row,registry=value['registry'])
                else:
                    from .codec import validate_summary_v2
                    validate_summary_v2(row)
        return value['rows']

    def iter_query_summaries(self,manifest,side,mode):
        """Read only the requested border; old immutable snapshots use their bundles."""
        for entry in manifest['worlds']:
            rows=self._projection(entry,side) if 'summary_artifacts' in entry else self._bundle(self.artifacts.get_json(entry['artifact']),entry)['summaries']
            for row in rows:
                if row['border_side']==side and mode in row['anchor_modes']:
                    # Current projections are exact views of fully validated writer
                    # input, bound by validator revision and the immutable CAS root.
                    yield row


```
