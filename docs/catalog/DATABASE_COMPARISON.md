# Database and serving-layout decision — October 22, 2026

**Recommendation: retain SQLite for current coordination/metadata, adopt a patched
SQLite runtime at the next controlled activation, and use the implemented guarded
read views. A custom database engine is not justified by these measurements.**
DuckDB/Parquet is a credible analytical or later immutable-read-layout option;
PostgreSQL is a candidate when a real shared-writer/network workload requires it.
Neither was selected as the project's production replacement.

## What was actually compared

The private experiment used SQLite 3.54.1, DuckDB 2.0.0 and NumPy 2.5.3 on this iMac.
Input was the same immutable 222-world catalog: 109,918 memberships and 17,983
8192/recommended anchor rows, with all 19 structure-count/completeness columns.
The source registry contains **93 entries: 19 structure and 74 biome entries**;
the biome entries include the nine legacy Overworld aliases. Earlier readiness prose
incorrectly inferred 28 structure choices by subtracting the visible biome choices.
The registry and UI were not changed to fit that incorrect arithmetic.

Both engines and mmap returned exactly the same candidate IDs for four saved query
shapes. The original scorer then matched complete ordered results, witnesses and
unknown/pending outputs. Checks also covered committed/uncommitted process kills,
idempotent receipt retry, reader snapshots, writer conflicts, source bindings and
index checksum corruption. These are finite local experiments, not fleet proof.

| Warm predicate/materialization, real 17,983 rows | SQLite typed rows | DuckDB typed rows | DuckDB/Parquet | NumPy mmap |
|---|---:|---:|---:|---:|
| Broad: return all IDs | 7.56ms | 5.13ms | 6.90ms | 0.53ms |
| Mixed variants: 270 IDs | 6.49ms | 2.53ms | 3.86ms | 0.29ms |
| Selective: zero IDs | 1.57ms | 1.41ms | 1.84ms | 0.27ms |

At 4× identical row copies, the mixed predicate took 26.94ms / 2.27ms / 5.56ms /
2.60ms respectively. These are replicas of the same facts, not 888 independent
worlds, and remain cache resident. They demonstrate layout/scan behavior, not cold
storage, production selectivity, retention quality or a population-size threshold.

Narrow five-member board lookups took about **0.12ms in SQLite and 2.5ms in DuckDB**.
Those omit the complete serving contract. The implemented full guarded service path
measured about **146ms**, and loopback HTTP about **157ms**, with context primed and
filesystem cache warm. Changing the engine does not eliminate integrity checks,
response generation, cursor handling or CPU scoring.

The larger flexible-query cost is still JSON materialization and the scorer. A
millisecond predicate benchmark is not a millisecond complete API response. The new
source-bound masks already skip impossible worlds without replacing that scorer.

## Storage, build and recovery evidence

SQLite typed-row insertion took 1.75s versus DuckDB CSV ingestion 0.49s; membership
insertion took 0.63s versus 0.57s. CSV preparation and source decoding are separate
costs, so these are not matched whole-pipeline build speedups. SQLite indexes took
0.25s and Parquet export 0.18s. Seven lookup trials followed, under one-thread DuckDB
with a 512MB limit and 256MB temporary cap; SQLite used a 16MiB page cache/no mmap.

The SQLite file was 83.3MB and DuckDB 30.4MB, each including 4× structure rows plus
109,918 member payloads. The 4× NumPy file was 27.9MB and Parquet 0.76MB, **excluding
member payloads, biome/witness payloads and raw observations**. Identical replicas
compress unusually well. These sizes cannot forecast the full catalog's growth or
be compared as complete equivalent warehouses. Current live CAS/history was retained.

Both disposable engines preserved acknowledged commits across SIGKILL, discarded
uncommitted inserts and accepted idempotent retries. SQLite's second writer was
bounded by its configured timeout; DuckDB reported a conflicting writer explicitly.
Source/file checksum tests rejected corrupt derived data before use. No new engine
was connected to live queues, publications, queries or personal checkpoints.

## Options and decision rules

| Option | Fit here | Decision now / trigger for reconsideration |
|---|---|---|
| Patched SQLite + guarded caches/read views | Existing queues, leases, receipts, small coordinated writes and ordered board access | Keep. Measure actual writer wait/queue growth before changing coordination. |
| DuckDB + Parquet | Analytical scans, batch inspection and immutable columnar serving experiments | Useful candidate. Prototype broad-query layout/scoring only if the full guarded API still misses a declared target. |
| NumPy mmap / future Arrow IPC blocks | Compact typed predicates over immutable source-bound facts | NumPy mmap tested; Arrow IPC was not. Prefer standard formats over a hand-written engine, but preserve schema, checksums, publication and lifecycle rules. |
| PostgreSQL | Central transactional coordination for actual networked writers, accounts and concurrent services | Not benchmarked or installed. Consider when a concrete distributed writer/operations workload is specified. |
| Custom KV/`.seedcat` engine | Specialized storage requiring application-owned query, indexing, durability and recovery behavior | No demonstrated need. Reconsider only if standard engines/layouts fail a measured workload strongly enough to justify maintenance. |

SQLite WAL permits concurrent readers and one writer on a host, and its shared-memory
model is unsuitable for sharing the database file across machines. Use a coordinator
rather than putting a WAL file on network storage. [SQLite WAL documentation](https://www.sqlite.org/wal.html).

The bundled Python SQLite 3.50.4 predates the documented rare WAL-reset race fix.
A private CPython-matched SQLite 3.54.1 adapter was built from the official source
with its published SHA3 checked. All 687 selected tests passed on the project runtime;
private-runtime coverage was 678 initial passes plus nine successful reruns after
correcting its editable-package bootstrap. Failed bootstrap runs/logs are preserved.
The live runtime remains unchanged and needs a controlled upgrade before production
concurrent-writer adoption. [SQLite fix details](https://www.sqlite.org/wal.html#walreset),
[official source download](https://www.sqlite.org/download.html).

DuckDB 2.0 embedded read-write mode still uses one writer process with concurrent
threads. **Multiple processes can now write through Quack's client-server protocol**;
older blanket claims that DuckDB cannot support that are outdated. Quack and
DuckLake/PostgreSQL combinations were not benchmarked here. [DuckDB 2.0 concurrency](https://duckdb.org/docs/2.0/connect/concurrency),
[release calendar](https://duckdb.org/release_calendar).

PostgreSQL provides MVCC and multiuser transaction facilities, making it an option
for a future central service; that architectural fit is not a measured speed claim
on this machine. [PostgreSQL concurrency](https://www.postgresql.org/docs/current/mvcc-intro.html).

Before selecting any fleet engine, specify real distinct-world/membership scale,
history retention, useful completed ingestion rate, reader/writer concurrency,
latency, RAM, storage and recovery targets on the intended hardware. GPU raw seeds/sec
alone does not supply these requirements. An engine decision can therefore remain
“keep SQLite now” while GPU contract work proceeds independently.

Evidence: [experiment scope](../../reviews/pre-gpu-implementation-2026-10-22/DATABASE_EXPERIMENT.md),
[measurements](../../reviews/pre-gpu-implementation-2026-10-22/DATABASE_COMPARISON.json),
[recovery](../../reviews/pre-gpu-implementation-2026-10-22/DATABASE_RECOVERY.json),
[private runtime](../../reviews/pre-gpu-implementation-2026-10-22/SQLITE_PRIVATE_RUNTIME.json),
[readiness execution report](../../reviews/pre-gpu-implementation-2026-10-22/REPORT.md).
