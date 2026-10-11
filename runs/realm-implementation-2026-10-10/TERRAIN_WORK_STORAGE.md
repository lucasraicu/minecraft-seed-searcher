# Durable terrain storage

Additive schema tables `terrain_pools`, `terrain_pool_members`, and `terrain_work` preserve old checkpoint schema compatibility. Opening a run does not adopt historical terrain results into a new task system. Creating the first pool when historical variant results exist rejects and preserves them; changed provider/algorithm identity requires a separate checkpoint.

`ensure_terrain_pool(identity, statuses=None, revision=None, new_revision=False, progress=None)` atomically snapshots explicit candidate-ID membership using `INSERT SELECT`. Both variants use one revision. New baseline records do not enter that revision, and refreshing membership requires explicit `new_revision=True`. Pool metadata records selected statuses, identity and committed member count. The optional callback reports the completed snapshot count; it does not provide incremental progress during the initial atomic insertion. `iter_terrain_pool_candidates` reads bounded keyset pages sorted by candidate ID. Membership is fixed; candidate evidence/score payloads remain the current saved records.

`ensure_terrain_work` persists immutable evaluation payloads with stage, coarse center, resolution, halo level, exact raster bounds and lattice. Unit identity includes variant and pool revision. Sampling identity excludes variant and pool revision, allowing unchanged-provider prediction samples to be shared across variants and explicit pool revisions. Optional `sampling_scope` distinguishes actual-generation snapshots that the scheduler must not automatically reuse. These are storage identities; they do not independently validate provider output.

Work status is `pending`, `deferred`, `leased`, or `complete`. Bounded priority-ordered iteration, status counts, claim attempts and explicit abandoned-lease recovery support scheduler restarts. A scheduler must own the run lock before calling recovery. Pending/deferred units remain saved after an invocation budget ends. An empty queue or any unfinished unit prevents aggregate completion. Explicit older pool scheduling can pass `pool_revision` to the aggregate variant-status setter.

`complete_terrain_work` commits raw sampling observation, geometry/result metrics, arbitrary next-step state, up to 4096 successor units, variant result wrappers, and the completed unit/digest in one transaction. The observation must match sampling key, bounds, resolution and lattice and contain raw channels. Shared observations are immutable through this API. Identical completion retries are idempotent; conflicting retries reject. Validation and updates occur under `BEGIN IMMEDIATE`; caller transactions are rejected without being committed. Newly scheduled successor units preserve their evaluation chain. Compressed array encoding/decoding and actual-snapshot nonreuse belong to the terrain/raster scheduler.

Validation:

```text
.venv/bin/python -m pytest tests/test_realm_terrain_work_store.py tests/test_realm_store.py tests/test_realm_discovery_recovery.py tests/test_realm_report_recovery.py -q
29 passed in 1.20s
```

Tests cover fixed membership after baseline growth, explicit refresh, provider rejection, variant-independent sampling keys and scoped actual keys, priority/keyset iteration, transactional observation/result/state/successor rollback, exact retry digests, deferred budget retention, restart attempts, aggregate completion guards, and caller-transaction preservation. No native generation or benchmarks were run. Large pool snapshot duration and durable raster storage growth remain unmeasured; raw snapshot retention/garbage collection is a separate policy.
