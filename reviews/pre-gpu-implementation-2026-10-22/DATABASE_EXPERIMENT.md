# Bounded database/layout comparison

Approved user scope: compare options after readiness and GPU contract definition.
This is a disposable measurement, not an engine migration or production selection.

Workloads: current immutable 222-world snapshot, 109,918 memberships, all structure
count/completeness fields at 8192/recommended, four saved flexible queries and board
lookups. Compare SQLite3.54.1 typed rows, DuckDB2.0 typed rows/Parquet and NumPy mmap.
Use 1x real rows and 4x identical row replicas for scan scaling only. Replicas are
not independent worlds, retention evidence, a cold-disk test or a fleet forecast.

Target for this decision: keep verified 222-world board pages under the reviewed
250ms illustrative median goal and identify remaining broad-query CPU/format costs.
No future fleet population, QPS or writer count has been specified; therefore this
experiment cannot select a fleet engine. PostgreSQL is assessed from official
concurrency documentation, not assigned invented local timings.

Keep original scorer for complete finite output equality. Predicates only exclude
proven complete structure failures; unknown biome absence cannot filter. Report
build, storage, predicate materialization, query plans and narrow board lookups
separately from complete guarded API numbers already measured. Verify metadata and
file hashes, restart/transaction recovery and local writer behavior in disposable DBs.

Bounds remain aggregate4GiB RSS and3GiB new logical disk, including prior input copy,
source/engine/runtime/staging/index/WAL/temp files. DuckDB one thread/512MB memory,
256MB temporary cap; SQLite16MiB pagecache/no mmap; trials filesystem warm. DuckDB
package is installed only into the private benchmark directory, no project dependency
or active server change. No PostgreSQL/Quack daemon or new GPU workload is launched.
