# C — Approved guarded serving read views

Use explicit High reasoning. Implement package C from the approved readiness plan.
Owned ONLY: src/seed_search/catalog/service.py, automation_query.py, store.py,
new read_views.py, new tests/catalog/test_guarded_read_views.py.
No edits to registry/models/artifacts/query.py/native or other paths. No recursively
delegated tasks. Use scoped file tools; no shell commands from model. Coordinator
executes tests. Do not send notification. ≤900s wall,≤240CPU s,≤1024MiB RAM.

Current boards call AutomationStore.snapshot every page, rebuild/validate/hash109k
memberships (~3.25s). CatalogService._query_snapshot already caches immutable compact
context (without memberships), rehashing all bound raw CAS pages on EACH reuse;
DO NOT bypass any existing corruption checks, binding checks or response isolation.
Board objective-local read views may derive from verified snapshot and cache only
bounded serialized blobs in existing64MiB budget. They MUST revalidate original
bindings and ALL bound CAS pages before warm reuse. Cold queries can build a view in
memory from verified manifest; never write/regenerate extraction/index files during
HTTP query. Versioned optional explicit offline view builder can stage/fsync/checksum
and atomically publish; missing optional views must safely fall back. No need to
force disk engine/schema changes if safely bounded snapshot read views suffice.

Generic query: add conservative typed candidate masks, source-bound to full original
projection, retaining original rank_v2/v3 scorer. Same-anchor required rows ALL,
within-row alternatives ANY, unknown survives, broad fallback. Integrate rather than
leave prototype unused. Avoid full predecode on every query; every warm projection
reuse must still rehash its original bound blob and validator identity. Store cache
as immutable bytes within64MiB per-worker allowance (including new views/masks),
bound SQLite/mmap/temp independently if used. No module-global1GB decoded cache.

Preserve all72boardviews, statuses, primary/reserve order, exact witnesses/pending/
ties/cursors, historical V2 and current V3, old shares, concurrent immutable snapshots.
Queries cannot mutate cached entries. Corruption fail closed. Existing10s timeout
unchanged; illustrate ≤250ms board firstpage after context prime, complete guardedAPI,
not unguarded SQL microlookup. Focus tests on corruption after warmup (including
unrelated membership page), mutation isolation, registry/profile mismatch, cursor
wrong-view/snapshot, cache eviction and exact baseline scorer equality for masks.
Use tiny synthetic fixtures following existing catalog tests. Codex independently
benchmarks current222worlds, all36products/72views after integration.
