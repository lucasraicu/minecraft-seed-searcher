# Actual reserve source evidence
Review only section5a of the plan; all other plan work already has reconciled High
reviews. No implementation authorized. User asks whole personal/public sweep2x
reserve before displaying winners/finalists, and says Lmk.

native_batch.py creates Top50Tracker(capacity=top_k) and top50.json; resume rebuilds
tracker from durable candidates table; changing top_k on resume explicitly fails.
Its compute() obtains tracker.cutoff_score() and passes cutoff_score to prototype.sweep.
Hence keeping50 while adding aUI reserve cannot recover inputs pruned below50th.
Top50Tracker deduplicates best record per seed. Public automation independently
keeps topK per objective and raw observation objects by world. Existing guards hard
code105644 membership slots in harvest.py and paged manifest validation in store.py.
New biome plan primary targets115964 across7543objectives;2x231928, no newobjectives.
Current standalone personal backend/run is preserved and completed; no newjobs.

## Actual native pipeline excerpt
```python
    except (ValueError,TypeError):run_key_int=int.from_bytes(hashlib.sha256(str(run_key_val).encode()).digest()[:8], 'big')
    tracker=None;top50_path=None
    if top_k>0:
        from seed_search.realm.top_tracker import Top50Tracker
        tracker=Top50Tracker(capacity=top_k)
        top50_path=Path(run)/'top50.json'
    def observe_committed(rows):
        for seed_payload,candidate_payload in rows:
            record=json.loads(seed_payload)
            record.pop('anchor_ids',None)
            record['anchors']=[json.loads(candidate_payload)]
            tracker.observe(record)
        seed_seconds=time.perf_counter()-before
        cutoff=tracker.cutoff_score() if tracker is not None else None
        sweep_kw={'retention':retention,'max_misses':max_misses} if retention=='survivors' else {}
        if cutoff is not None:sweep_kw['cutoff_score']=cutoff
        if dynamic_v3_policy(cfg):sweep_kw['refine_centers']=True
        return prototype.sweep(seeds,threads,**sweep_kw),seed_seconds
    def prepare(native_future,first,end,store):
        batch,seed_seconds=native_future.result()
    with _scan_lock(run),_numerical_threads(),RealmStore(run,identity=identity,resume=resume) as store:
        previous_pipeline=store.get_state('native_pipeline') or {}
        if resume and 'top_k' in previous_pipeline and previous_pipeline['top_k']!=top_k:
            raise ValueError('Top-K capacity cannot change on resume; use a fresh run')
        store.configure_range(start_index,start_index+count,batch_size);store.recover_assignments()
        if tracker is not None and resume:
            # The candidate table and range receipts commit together. JSON is only
            # a presentation cache and may be stale, absent, or corrupt at restart.
            cursor=store.db.execute(
                'SELECT s.result,c.result FROM candidates c JOIN seeds s ON s.idx=c.idx ORDER BY c.id')
            while rows:=cursor.fetchmany(256):
                observe_committed(rows)
        if tracker is not None and not top50_path.is_file():
            tracker.save_to_json(str(top50_path))
        completed=store.get_state('completed_seeds')
```
