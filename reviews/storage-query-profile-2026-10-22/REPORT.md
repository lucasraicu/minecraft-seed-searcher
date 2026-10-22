# Current costs, storage and query bottlenecks — October 22, 2026

**Keep SQLite for control state. Improve checkpoint serialization and add targeted
serving read models before choosing a new database engine or porting the whole
pipeline to GPU.** A custom data layout is worth investigating; a hand-written
`.seedcat` database engine is not justified by the measured workload.

This task profiles and tests disposable prototypes only. No runtime optimization,
production schema, GPU implementation, database installation or deployment occurred.
All live services, source/native files, personal state and historical evidence remain.

## What a current public record costs

A fresh replay of one existing seed through the configured current v3 pipeline:

| Unprofiled stage | Wall time |
|---|---:|
| Base extraction, spawn/Realm/refinement and checkpointing |22.515s |
| Extra height evidence,3200points |0.227s |
| Summaries,246anchor/border rows |5.742s |
| Publication |1.445s |
| Other validation/product/retention/control work |2.498s |
| **Total** |**32.427s** |

This is consistent with the prior five current replays around35seconds/world;
there was no optimization between them. One seed is a mechanism probe, not an
estimate of every world's cost. It has102515Overworld and400Nether biome points,
31coverage entries, the current registry, and7543objective2Kretention semantics.
Native artifact remains `3fbb286e4f06a4726e3c1e7216a5aad4d30f2abc6b0bf7b97532bf085b372687`.

The extraction-child profile recorded **4105JSON dumps producing814.2MB of text**,
compared with an8.63MB final observation checkpoint. This includes canonical
serialization for hashes as well as checkpoint/refinement bookkeeping: it is not
814MB of measured physical disk writes. JSON encoding took8.58profiled seconds;
624fsync calls took0.241seconds. Deep copies, observation validation and repeated
checkpoint processing are other visible costs. Simply reducing durability/fsync
is not the evidence-supported first fix.

Visible general-native calls consumed2.92profiled seconds. Private CFFI calls,
external spawn code and profiler distortion prevent a reliable native-vs-Python
percentage or GPU speedup estimate. Full profiling changed elapsed time32.43→52.48s
and shortened the8192bounded search552→362evaluated centers, changing its
search-budget flag. Its selected result, geometry, biome samples and core Realm
values stayed the same, but **full extraction semantic equality did not pass**.
This profile is diagnostic and was never adopted or used as a production result.

To remove that confound, the same frozen observation was replayed through height
extension, summaries, products, retention and publication with/without profiling.
The snapshots matched **exactly**, including
`2fd170fc6171e87e0b3124fcc2d805279efb5b7a1a82ec896d335f04d582cd84`.
That fixed-work derivation took10.61s unprofiled and15.07s profiled. No extra base
world extraction was performed. See [profile parity](EXTRACTION_PROFILE_PARITY.json)
and [fixed replay](FIXED_REPLAY_PARITY.json).

## Query work is mainly CPU/deserialization at this scale

Current snapshot:222worlds,109918memberships. Three unprofiled trials per query,
normal10second request allowance, current scorer and full source/snapshot checks:

| Query | Result-cache miss median | Immediate result-cache hit median |
|---|---:|---:|
| Origin2048 |2.246s |0.103s |
| Broad Recommended8192 |4.588s |0.102s |
| Required igloo-basement +treasure-bastion |3.341s |0.071s |
| Required biome ANY +preferred village |4.233s |0.100s |
| Selective required structure counts |3.462s |0.074s |

These are isolated in-process service timings, not HTTP/IPC latency or a concurrent
production SLA. CPU time essentially equals elapsed time. Application context was
primed before the result-cache-miss trials, as current query workers do at startup;
priming took3.068s. OS filesystem cache was not flushed. The data fits this64GiB
machine, so none of these establish cold-disk behavior.

A separate counter-only broad query, **without cProfile**, took4.270s:

- JSON parsing:2.258s, about82.4MB input across226calls.
- Verified artifact reads including hashes/path checks:0.205s,42.0MB across279calls.
- Projection decompression:0.131s,20.3MB compressed→82.0MB JSON.

Counters are nested and must not be added together. The query reads manifest-page
wire bytes for integrity and222world projection blobs. Source verification remains
necessary; it need not imply rebuilding all Python objects on every request.
The mixed query was3.032s with2.166s in JSON parsing, despite its selective result.

A raw component microbenchmark measured0.03–0.07s fetching the20.3MB projection
blobs and~0.12s inflating them. Its parsing was slower than the production-shaped
counter run because it retained the full membership manifest and had different
allocation/GC state. Those micro-stages are diagnostic; they are not additive
components of the service latency above.

Predecoded rows cut a broad scorer call to1.849s and a mixed scorer call to0.083s.
Later cached-block ablations were faster again. These are memory/cache lower-bound
experiments, not shipping performance figures. Broad ranking still has meaningful
Python work after decoding; replacing only the storage engine will not remove it.

## What the disposable read models demonstrate

**Precomputed boards:** fetching five rows currently takes3.251s primary /3.298s
reserve, largely rehydrating and validating the entire109918-member manifest.
A private SQLite `WITHOUT ROWID` table keyed by(snapshot,objective,ordinal) built
all109918members in1.652s. The same five-row payload lookup, JSON decode, role fields
and metadata check took **~0.48ms** median. A cached in-memory BLOB lookup took
~0.05–0.07ms. The SQLplan uses the composite primary key.

This is strong evidence for a materialized per-objective read view. It is **not** a
thousands-fold production API speed guarantee: the prototype omits HTTP, signed
pagination, full cryptographic source-binding/corruption checks, crash recovery,
concurrent writers and snapshot lifecycle integration. Those must be designed and
tested before adoption. The combined narrow membership/filter SQLite prototype is75997184bytes; the three-feature numeric array is1079492bytes. Build costs are recorded separately.

**Personalized selection:** one8192Recommended projection has17983anchors.
A conservative count/completeness prefilter reduced the mixed variant case to
270anchors in17worlds. Fetching those world blobs and running the **unchanged exact
scorer** took0.254s, versus3.341s through the current service. It preserved the full
ordered results, pending candidates and exact Decimal tie-breaking. The prototype's
additional startup/source-guard/index-build work is outside that lookup timing.

The scalar SQLfilter's actual plan was a **table scan**, not demonstrated B-tree
acceleration; filtering a compact typed table still avoids decoding unrelated
world blobs. Numeric-array masks for the same narrow three-feature index took
~0.3–0.7ms. This is not a complete binary catalog engine.

Broad/biome-only requests retained all222worlds; in the RAM-heavy ablation they took
~7.5–7.9s loading a second set of blobs. There is **no demonstrated universal
prefilter speedup**. The empty selective query also has a trivial advantage that
must not be generalized. Full ordered output equality passed four actual cases;
four additional synthetic controls cover same-anchor ALL, unknown→pending,
known-negative exclusion and positive retention. Missing biome witnesses are never
used as negative evidence. See [read-model results](READMODELS.json) and
[predicate controls](PREFILTER_SEMANTICS.json).

## Storage footprint and duplication

The copied catalog totals~1.273GB, including historical snapshots and control DBs.
SQLite harvest state is111.8MB:109918members,222receipts, zero pending jobs and no
free pages in this copy. Its current metadata writer is serial; lock contention
or distributed multi-writer capacity was not measured.

Current-snapshot reachable compressed CAS is **241.3MB**:

| Current artifacts | Compressed | Expanded JSON |
|---|---:|---:|
|222world bundles |167.8MB |1305.1MB |
|666per-border query projections |51.7MB |232.3MB |
|55membership pages |21.6MB |79.4MB |
|Manifest index/world page |0.1MB |0.5MB |

All automation CAS objects total1036.5MB. The remaining~795.2MB includes older,
shared or currently unreferenced artifacts; this is **not deletion authorization
or a proof that they are garbage**. Historical links and rollback data remain
protected. Avoid extrapolating this small, versioned corpus linearly to a fleet.

Memberships and projections repeat identifiers/nested fields. Typed read blocks
and objective-local pages could reduce object construction and decoding while
leaving immutable raw evidence untouched. Their actual size/recovery tradeoffs
need a follow-up implementation benchmark, not speculative compression ratios.

## Database and GPU decision

| Layer | Recommended direction | Evidence / remaining proof |
|---|---|---|
|Queue, leases, receipts, metadata |Keep SQLite |No measured engine/locking bottleneck; preserve transactions/recovery |
|Precomputed boards |Snapshot-bound indexed/materialized SQLite read views |Narrow exact-payload prototype validates the access pattern; lifecycle/security gates remain |
|Flexible ranked filtering |Typed, immutable serving blocks with cheap candidate masks and the exact scorer |JSON/materialization is expensive; broad scoring still needs optimization |
|Large analytical scans /bulk processing |Benchmark DuckDB over columnar data as a candidate |Not installed or benchmarked here; no claim it wins |
|New `.seedcat`/custom engine or RocksDB migration |Defer |No current measurement establishes the need |

SQLite supports indexed incremental access rather than parsing an entire custom
file, consistent with the demonstrated board lookup. [SQLite application-file guidance](https://www.sqlite.org/appfileformat.html).
Apache Arrow is a standardized columnar memory/IPC format with adjacent typed arrays
and vectorization-friendly access; it is a **format candidate**, not a replacement
control database. [Arrow format specification](https://arrow.apache.org/docs/format/Columnar.html).
DuckDB targets analytical, vectorized SQL workloads; it is worth testing if large
scans dominate after the read model changes. [DuckDB design](https://www.duckdb.org/why_duckdb).
RocksDB is an embedded key-value engine, not a demonstrated solution for this
ranked-query workload. [RocksDB description](https://rocksdb.org/index.html).
None of those untested engines is a measured winner in this report.

The next engineering order supported by these measurements is:

1. Reduce repeated whole-observation serialization/copying during checkpointing,
   preserving bounded lost work, durable resume, heartbeats and source identities.
2. Add objective-local read views and measure a typed generic-query projection,
   retaining integrity, unknown/OR/ALL semantics, same-anchor ranking and exact ties.
3. Profile the native kernels independently, then define a one-device GPU parity
   and end-to-end useful-record benchmark. Measure transfer, queue and publication
   costs too; raw rejected-input seeds/sec is not useful-record throughput.
4. Use larger real snapshots, out-of-memory/cold-storage workloads and intended
   reader/writer concurrency to choose between SQLite read projections, Arrow/Parquet
   with DuckDB, or a more specialized design. No fixed fleet target was supplied.

GPU screening does not remove Python checkpointing, JSON construction or snapshot
validation. No GPU hardware was tested, and cProfile cannot establish CUDA speedup,
PCIe costs or a quantitative Amdahl bound. A custom serving schema is justified as
a next experiment; an entirely new database engine is not yet justified.

## Verification, failures and preservation

The query phase finished its timing/parity assertions but failed only at final
oracle export because JSON cannot encode Decimal sort keys. The original failure
log/resource exit remains. Full oracles were rebuilt with the original scorer,
exact Decimal values were saved as tagged strings, and direct Python equality
checks passed without precision conversion. [Export recovery](EXPORT_RECOVERY.json).
No expensive timing suite was repeated to hide that failure.

Both High critiques (`4cafb9086b5d`,`5952ca57ff8b`) succeeded, exit0/denied[], no edits
or tests. Codex checked the source, actual results and disagreements. The second
review's numerical90%non-native/Amdahl claim was rejected as unsupported; its
universal OR-index inference and suggestion to prioritize fsync removal were also
rejected. Current-scale/cold-cache/prototype caveats were accepted. All workers are
terminal; no quota/authentication pause occurred. [Reconciliation](REVIEW_RECONCILIATION.md).

Measured subprocess allocation: **320.54/900seconds**, sampled peak owned RSS
1231527936bytes (<4GiB),~1.39GB external output including the verified physical
catalog copy (<3GiB). Copying/preparation/reporting and read-only verification are
outside that measurement stopwatch; this is not total user elapsed time. Two base
world extractions, two frozen-observation derivation replays, no new search or BDS.

[Preservation](PRESERVATION.json) checks8624live non-SQLite files,208source/build/state
files and199protected personal/native/checkpoint files. PIDs91321/22035/17880,
selected personal run, public snapshot/configuration and paused automation with0s consumed of600s
remain unchanged. Mutable catalog DBs were copied through SQLite backup; no live
DB/schema writes or engine replacement were performed. No resets, deletions of
repository/evidence payloads, commits, merges or pushes occurred.

Evidence: [summary](SUMMARY.json),[storage](STORAGE.json),[queries](QUERIES.json),
[counter-only attribution](QUERY_COUNTERS.json),[resources](RESOURCES.json),
[artifact map](ARTIFACTS.json),[final verification](FINAL_VERIFICATION.json).
Raw copied catalogs, SQLite prototypes and `.prof` files remain under
`/Users/lucasraicu/.local/share/antigravity-worker-mcp/storage-query-profile-20261022`.
