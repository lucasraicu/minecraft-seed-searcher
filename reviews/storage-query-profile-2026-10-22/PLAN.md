# Current cost/storage/query profiling — operational measurements

User requests profiling and measurement to guide GPU conversion and database choice.
No runtime optimization, production schema migration, GPU implementation, database
installation/service, or live policy activation is included. Codex owns bounded
measurement scripts, source review, evidence and interpretation. One neutral Gemini
High tool-free critique checks design/confounds; reuse prior benchmark baselines.
The explicit request authorizes profiling; any later significant product change
requires its own reviewed plan and approval.

Preserve personal91321/public22035/Vite17880, inherited dirty source, active222-world
snapshot and all historical evidence. All new writable state in a fresh external
root; a verified physical copy of the current catalog supplies local query tests.
Use SQLite backup for mutable DBs; copy immutable bytes with SHA verification.
No searches, BDS, native rebuilds, restart, deletion or commit/push.

1. Storage inventory: physical/logical bytes by layer, SQLite page/freelist/table/index
   stats and query plans; current snapshot's reachable CAS bytes vs historical/shared
   objects; raw/compressed world observations, projections, membership/index pages.
   Reuse exact222-world manifest and5world replay evidence; do not claim per-seed
   population sizing or linear fleet extrapolation.
2. Profile one existing world through current full v3 pipeline using cProfile in
   parent and extraction child; collect real stage wall/CPU times and JSON/gzip/hash/
   write/fsync counters. Pair with one unprofiled current run; report profiling
   overhead and reject profiled timing as production latency. Verify semantic
   numerical/prediction parity while excluding only declared timing fields/IDs.
   Native calls remain opaque: no assertion of GPU speedup from Python profiles.
3. Current query workload on isolated222-world copy: broad Origin/Recommended,
   mixed/selective structure+biome rows, product primary/reserve and detail. Measure
   fresh application/result cache vs warm, wall/CPU, reads/bytes/decompression/JSON/
   validation/scoring allocations, page counts. OS cache stays unflushed. cProfile
   diagnostic calls isolated from unprofiled latency runs. Keep production10s limits
   for latency; offline profile-only scoring may bypass request deadline with explicit
   bounded allowance and identical algorithm, never modify production limits.
4. Decompose projection loading vs scoring using same current scorer and fully
   verified saved data. In-memory/predecoded ablations give lower-bound diagnostic
   evidence, not a production benchmark or validated replacement implementation.
   Prefix25/100/222world scaling only if within bounds, no fabricated new worlds.
5. Narrow disposable read-model comparisons: SQLite indexed precomputed memberships
   vs existing full-manifest product lookup; row-index prefilter on exact structure
   counts/known-completeness plus immutable projection and SAME scorer, and optionally
   a simple contiguous numeric-array filter. Test a finite request matrix and full
   ordered result equality before reporting speedups. Do not implement a complete
   alternative engine or skip provenance, unknown/OR/ALL semantics or per-world best
   anchor rules. Report build/write amplification/storage and missing lifecycle tests.
6. Recommend GPU boundary and storage choices from measured bottlenecks; consult
   primary official engine docs for capability claims. SQLite for control state is
   distinct from analytical/serving read projections. No custom engine is assumed
   necessary and no comparative speed claimed for engines not benchmarked.

Limits:900s cumulative instrumented/uninstrumented measurement subprocess wall,
owned aggregate4GiB RSS,3GiB new logical output INCLUDING isolated catalog copy,
2existing-world full extractions max120s unprofiled/240s profiled; one public worker,
native/numeric threads1. Per profiling phase explicit timeout; abort only owned
children and preserve partial failures if caps are reached. No automatic scope or
resource expansion. Read-only inspection/reports outside the measurement stopwatch
must still remain bounded; distinguish total user elapsed time.

Acceptance: actual source/native/policy/registry/snapshot hashes and schema pins;
untouched live files/processes/control; passing semantic/ordered query parity and
SQLite integrity; stage totals not double-counted; instrumentation overhead measured;
actual file/page/byte and CPU work; current-scale limitations, no p95/SLA from tiny
samples; evidence-supported recommendation with proof gates for untested engines.
