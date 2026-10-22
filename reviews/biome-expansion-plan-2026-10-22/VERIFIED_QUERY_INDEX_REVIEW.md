# Verified compact query index review

Existing32MiB index-cache half is shared; no cache/cap increase. Full manifest is loaded, schema-validated and digest-checked before compact context is cached. Every subsequent query rereads the binding and rehashes ALL index/pages compressed bytes against their exact previously verified CAS manifests. No mtime shortcuts or unverified JSON parser. Startup primes only the immutable index under the existing5second per-worker startup deadline; query-result/projection caches remain cold. Report startup latency separately.


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
            return cached['context']
        manifest=store.snapshot(sid);binding=store._binding(sid)
        value=store.artifacts.get_json(binding['artifact'])
        refs=[binding['artifact']]
        if value['revision'].startswith('catalog-snapshot-index-'):
            refs.extend(page['artifact'] for page in value['pages'])
        context={k:v for k,v in manifest.items() if k!='memberships'}
        cached=dict(context=context,binding=binding,artifacts=refs);size=len(canonical_json(cached))
        with self.cache_lock:
            if size<=self.cache_bytes:
                old=self.cache.pop(key,None)
                if old:self.cache_size-=old[1]
                self.cache[key]=(cached,size);self.cache_size+=size
                while self.cache_size>self.cache_bytes:
                    _,(_,removed)=self.cache.popitem(last=False);self.cache_size-=removed
        return context



    def _read_verified_raw(self,manifest):
        """Check the immutable wire bytes without allocating the decoded JSON tree."""
        self._validate_manifest(manifest)
        target_path = self._safe_resolve_key(manifest["relative_key"], check_exists=True)

        with open(target_path, "rb") as f:
            data = f.read(self.max_bytes + 1)

        if len(data) > self.max_bytes:
            raise ValueError(f"Artifact byte length exceeds limit {self.max_bytes}")
        if len(data) != manifest["byte_length"]:
            raise ValueError(f"Artifact byte length mismatch: expected {manifest['byte_length']}, got {len(data)}")

        actual_sha = hashlib.sha256(data).hexdigest()
        if actual_sha != manifest["sha256"]:
            raise ValueError(f"Artifact sha256 mismatch: expected {manifest['sha256']}, got {actual_sha}")

        return data

    def get_json(self, manifest: dict) -> dict:
        """Validate manifest, read, decompress within bounds, and strictly parse JSON dictionary."""
        data=self._read_verified_raw(manifest)
        codec = manifest["codec"]
        if codec == "gzip":
            decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        elif codec == "zlib":
            decompressor = zlib.decompressobj(zlib.MAX_WBITS)
        else:
            raise ValueError(f"Unsupported codec: {codec}")

        try:
            uncompressed = decompressor.decompress(data, self.max_bytes + 1)
        except Exception as exc:
            raise ValueError(f"Decompression failed: {exc}") from exc

        if decompressor.unconsumed_tail or len(uncompressed) > self.max_bytes:
            raise ValueError("Decompressed payload exceeds max_bytes limit")
        if not decompressor.eof or decompressor.unused_data:
            raise ValueError('Truncated or trailing compressed stream')
        if len(uncompressed) != manifest["uncompressed_length"]:
            raise ValueError(
                f"Decompressed length mismatch: expected {manifest['uncompressed_length']}, got {len(uncompressed)}"
            )

        try:
            payload = json.loads(
                uncompressed.decode("utf-8"),
                object_pairs_hook=_unique_pairs,
                parse_constant=_reject_constant
            )
        except Exception as exc:
            raise ValueError(f"Invalid or corrupt JSON: {exc}") from exc

        if not isinstance(payload, dict):
            raise ValueError("Decoded JSON root is not a dictionary")

        return payload



def _worker_main(channel, config):
    """Spawn target. Secret/config are local process arguments, never CLI/logs."""
    parent = config['parent']
    def parent_watch():
        while True:
            if os.getppid() != parent:
                os._exit(0)
            time.sleep(.1)
    threading.Thread(target=parent_watch, daemon=True).start()
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[key] = '1'
    from .service import CatalogService, ServiceError
    try:
        service = CatalogService(config['root'], secret=config['secret'], cache_bytes=config['cache_bytes'])
        with service._store() as store:
            store.info()
        # Load the compact immutable serving index before readiness.  Query result
        # and projection caches remain cold.  Startup retains its original deadline.
        from .automation_query import available,_store
        if available(service.root) and service.cache_bytes:
            automation_store=_store(service)
            service._query_snapshot(automation_store,automation_store._binding()['snapshot_id'])
        _send(channel, dict(protocol=PROTOCOL, kind='ready', generation=config['generation']), config['startup_deadline'], MAX_REPLY)
        while True:
            job = _receive(channel, None, MAX_REQUEST)
            if (set(job) != {'protocol', 'kind', 'generation', 'id', 'deadline', 'body'}
                    or job['protocol'] != PROTOCOL or job['kind'] != 'query'
                    or job['generation'] != config['generation']
                    or not isinstance(job['id'], str) or len(job['id']) != 32
                    or type(job['deadline']) not in (float, int) or not math.isfinite(job['deadline'])):
                raise ValueError('Invalid query worker protocol')
            deadline = job['deadline']
            service.query_seconds = min(config['query_seconds'], _remaining(deadline))
            envelope = dict(protocol=PROTOCOL, generation=config['generation'], id=job['id'])
            try:
                reply = dict(envelope, kind='result', payload=service.query(job['body']))
            except ServiceError as exc:
                reply = dict(envelope, kind='error', payload=dict(message=str(exc), code=exc.code, status=exc.status))
            except (ValueError, TypeError, KeyError):
                reply = dict(envelope, kind='error', payload=dict(message='Invalid request or unavailable snapshot', code='invalid_request', status=400))
            except Exception:
                reply = dict(envelope, kind='error', payload=dict(message='Catalog data is unavailable; inspect the local audit', code='catalog_unavailable', status=503))
            try:
                _send(channel, reply, deadline, MAX_REPLY)
            except ValueError:
                _send(channel, dict(envelope, kind='error', payload=dict(message='Query response exceeds the IPC allowance', code='response_too_large', status=503)), deadline, MAX_REPLY)
    except (EOFError, OSError, ValueError):
        pass
    finally:
        channel.close()




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

