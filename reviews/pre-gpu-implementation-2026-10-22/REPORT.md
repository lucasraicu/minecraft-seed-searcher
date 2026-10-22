# Completed readiness execution — October 22, 2026

Implemented and verified the approved CPU/catalog readiness work, defined the GPU
contract without implementing a GPU kernel, and compared database/layout options.
All application changes are in the working tree; nothing was committed or pushed.
Validation used private roots. **Live services were preserved, so their loaded code
and bundled SQLite runtime were not upgraded or restarted.**

Deliverables: [GPU contract](../../docs/gpu/GPU_CONTRACT_V1.md),
[machine contract](../../docs/gpu/gpu_contract_v1.json),
[database decision](../../docs/catalog/DATABASE_COMPARISON.md),
[completion audit](COMPLETION_AUDIT.md), [final preservation](FINAL_VERIFICATION.json).

## Changed implementation

| Files | Result |
|---|---|
| `catalog/ingestion.py`, `harvest_native.py` | Encode each observation once for checkpoint hash and payload. Keep the existing envelope/reader, finite JSON, symlink checks, atomic replace, file fsync and parent-directory fsync. |
| `catalog/summaries_fast.py`, `automation.py` | Add a call-local int64 biome index with exact half-open geometry and `(distance²,X,Y,Z)` ties. New V3 workspaces bind its version and source SHA in policy options. Existing configurations retain their exact declared implementation. |
| `catalog/service.py`, `automation_query.py` | Source-bound board read views reuse verified ordered members, without reparsing every membership page. Every warm request still rehashes every original bound CAS page and checks the snapshot binding. |
| `catalog/read_views.py` | Bounded typed structure-count/completeness masks remove only proven complete failures at the same anchor. Unknowns survive; biome ANY rows and preferences do not exclude. The original scorer remains authoritative. Warm masks rehash their source projection. |
| Four new test files | Check durable checkpoint failures/tampering, exact integer derivation, versioned compatibility, guarded cache integrity/cursors/eviction, and full 100-candidate reserve mechanics. |

The original `summaries.py` is byte-identical to the task's baseline. Its source
contributes to existing immutable policy identities. An initial direct edit correctly
triggered the compatibility guard; the additive source-pinned path resolves that
without rewriting existing jobs or weakening the guard. See [compatibility record](POLICY_COMPATIBILITY.md).

Read views are ephemeral immutable caches sharing the existing serialized cache
allowance, not a new durable index or schema. They have no new publication/GC root;
a restart discards them and normal verified reads repopulate bounded query helpers.
Queries publish no index files and launch no extraction. Existing immutable snapshot
publication, cursor and recovery rules stay in effect. Historical shares remain pinned.

## Measured results

Matched unprofiled record trials replayed one existing world in three counterbalanced
pairs. Each produced 102,515 Overworld samples, 400 Nether samples and 246 summaries,
without a resource-stop result. This is a small fixed cohort, not population throughput.

| Cost | Before | Updated |
|---|---:|---:|
| Complete current record, median | 34.55s | 24.97s |
| Fixed-observation summary derivation, median | 5.86s | 2.43s |
| Durable single checkpoint write, median | 0.131s | 0.061s |
| Primary board service request, median | 3.425s | 0.146s |
| Reserve board service request, median | 3.261s | 0.146s |
| Broad recommended request, median | 5.028s | 4.575s |
| Mixed variants, result uncached | 3.761s median | 3.250s with masks cold; 0.480/0.456s warm |
| Selective request, result uncached | 3.952s median | 0.206s median with masks warm |

Origin requests improved from 2.424s to 2.228s; biome-OR remained comparable
(4.433s versus 4.452s). Loopback HTTP board median was 0.157s. These are warm-filesystem
measurements with explicit cache states, not cold-storage results, p95s or an SLA.
The cache used about 16.9MB of its existing 33.6MB index allowance in the serving test;
the separate result allowance is unchanged. The 10s query limit was not increased.

Complete ordered outputs, witnesses, pending candidates and counts matched for all
five query cases, including cursor traversal. All 36 products / 72 primary-reserve
views matched the original complete membership ordering, totals and product statuses.
See [serving measurements](SERVING_AFTER.json), [parity](SERVING_PARITY.json),
[record trials](RECORD_REPLAY.json) and [derivation trials](DERIVATION_AFTER.json).

A frozen-observation pipeline replay matched every world artifact, extension,
summary, membership, product status and generation after excluding only the explicit
new policy revision. Whole snapshot IDs intentionally differ with that policy.
Time-bounded 8192 searches may complete different work; fixed-work parity is assessed
separately rather than promoting wall-budget partial results to exact equality.
[Fixed replay evidence](FIXED_REPLAY_PARITY.json).

## Sustained screening, selection and intake

Two approximately 150-second arms used the same previously benchmarked 262,144-input
cohort repeatedly, with 34 native threads and durable receipts. There were 43 control
and 39 loaded runs: 21,495,808 evaluations, not that many distinct seeds. Median rates
were **74,467 input seeds/sec control** and **67,122/sec loaded**. This sequential-arm
screen is an operational coexistence check, not a new counterbalanced causal estimate.

The loaded arm included two private HTTP query workers, 1,944 successful requests
(1,928 result-cache hits), and three complete existing-world replays. Extraction
covered 135.69s of 152.43s personal work; both clients overlapped essentially that
whole interval. Each loaded public record took about 45 seconds, versus about 25
seconds in isolation. A fast personal emitter therefore does not make catalog
completion free. Distinguish input rates from completed observations and retention.

The long cohort had zero personal survivors, so its selected-personal-candidate rate
was zero. A supplemental already-benchmarked positive cohort retained exactly one
candidate: current control and loaded runs matched the prior full receipts, counts,
records and ordered-record SHA. A synthetic full-100 test separately covers heap
filling, ties, deduplication, persistence, cutoff and promotion. Natural full-100
performance and new unique useful-world discovery/hour were **not measured**.
Three repeated public publications are not three new discoveries or retention-quality
proof. Current replay completion rate during extraction was about 0.022/sec; do not
advertise that as a natural unique-world discovery rate.

An additional private metadata experiment registered eight descriptors over 32 saved
seeds. Thirty-two expansion calls stayed at the configured four pending jobs, then
cancelled/fenced the four jobs. The sustained handoff selected at most its two sampled
worlds even though the personal branch rejected every input; its owned descriptor was
retired. No new seed campaign or BDS run was launched. See [sustained evidence](SUSTAINED.json),
[positive path](POSITIVE_COEXISTENCE.json) and [backpressure](BACKPRESSURE.json).

Available `pmset` diagnostics reported scheduler/speed limits at 100%, 36 available
logical CPUs and no recorded warnings. This is not direct per-core frequency or
continuous temperature telemetry; raw initial/end diagnostics are preserved.

## Correctness, recovery and dependency verification

- **687 selected tests passed in 297.50s:** the entire current catalog suite plus
  affected reserve/native guard/refinement/optimization parity checks. One known
  multithreaded-fork warning occurs in its explicit regression.
- All **222 saved worlds / 54,615 summaries** passed **151,848** count/completeness
  mask comparisons. **28 stratified full derivations** matched the original scalar
  summaries exactly. No new base extraction was used for that correctness replay.
- All **10 catalog Node suites** and the frontend build passed. UI source remained
  unchanged; the existing interactive-browser waiver remains in effect.
- Existing selected tests cover process kills, leases/fencing, budgets, disk/output
  limits, corrupted pages, rollback, historical cursors, shares and reserve roots.
  New tests cover changed checkpoint/cache boundaries and concurrent publication.
- **75 CPU oracle vectors** replayed, including signed seeds, finite generation,
  negative floor division, border points and raw village attempts on five existing
  worlds. Record widths and seven malformed seed-map frame examples were checked.
  This is CPU contract verification, not GPU parity or a production codec test.

SQLite's documented WAL-reset fix is absent from the bundled 3.50.4 runtime. A private
3.54.1 library and matching CPython3.13.15 adapter were built, with the official SQLite
archive SHA3 verified. A private validation environment loads that adapter in parent
and child processes. Its selected-suite coverage was 678 initial passes plus nine
successful reruns after correcting editable-package startup; the failed bootstrap
run is preserved and is not presented as a clean single-run pass. The application
suite's independent 687-test run on the normal environment passed as stated above.

The private SQLite and DuckDB tests preserved acknowledged commits across SIGKILL,
rolled back uncommitted inserts, demonstrated idempotent retry, reader snapshots and
explicit writer conflicts, and rejected a corrupt source-bound index. These are local
engine tests, not a distributed durability proof. See [runtime manifest](SQLITE_PRIVATE_RUNTIME.json),
[database recovery](DATABASE_RECOVERY.json), [original full log](full-regression.log),
[private first log](patched-sqlite-regression.log), [corrected rerun](patched-sqlite-recovery.log),
[all-fact replay](SAVED_FACT_REPLAY.json), [Node/build receipts](FRONTEND_CHECKS.json).

Checkpoint frequency and acknowledged progress semantics were not weakened. V3 replay
quanta remain one structure inventory, one 1,024-point base/coarse batch, one additional
height plane (at most ceil(14,000/64)² = 47,961 points), or one ≤4,096-point refinement
tile, depending on stage. The larger-Realm stage retains its existing ≤5s search
budget. Parent world-time fencing is ≤120s; tile execution ≤60s. Acknowledged full
checkpoints survive replacement failure; corrupt checkpoints fail closed. Reservations
are charged before execution, and no allocation was reset to recover elapsed work.

## GPU contract and database decision

The [GPU contract](../../docs/gpu/GPU_CONTRACT_V1.md) defines independent admission,
integer/provider/coordinate semantics, source identities, exact ranking/reserves,
concrete bounded frame layouts, completeness, overflow, durable ownership, replay,
backpressure, CPU fallback and acceptance gates. Its first operations are finite seed
mapping or raw village placement, with proven-rejection disabled. No GPU kernel,
transport integration, device speed or fleet scaling was implemented or claimed.
The current host's Vega56/8GB is verified; the intended conversion hardware is unknown.

The [database comparison](../../docs/catalog/DATABASE_COMPARISON.md) measures SQLite3.54.1,
DuckDB2.0, Parquet and NumPy mmap on identical facts, plus clearly labeled 4× row
replicas. SQLite wins the narrow ordered board lookup here; columnar scans favor
DuckDB/mmap in some cases. The measured full API remains much larger than either
lookup. Keep SQLite coordination and guarded views, with the runtime patch at
controlled adoption. A future analytical layout or shared-writer database needs an
actual fleet workload; no custom engine or production replacement is justified now.

DuckDB2.0's Quack client-server option supports multi-process writers; the old blanket
single-process limitation is not an accurate description of all current modes.
PostgreSQL, Quack and Arrow IPC were assessed or identified but not benchmarked here.
Current documentation links and precise limitations are in the database decision.

A registry-count error in the earlier readiness prose was corrected: 93 registry
entries comprise 19 structures and 74 biomes, including nine legacy Overworld aliases.
That correction changes documentation only; actual registry bytes were preserved.

## Scope, preservation and review history

The source snapshot contains 978 files and was extracted into an isolated directory
with matching hashes and native import smoke checks. A supplemental custom-build
restore explicitly rebinds only the copied extension locator, preserving original
metadata/content hashes and verified external runtime pins; see [recovery procedure](RESTORE.md)
and [native restore receipt](RESTORE_NATIVE_SMOKE.json). The full private catalog copy
used SQLite backup APIs, preserving WAL-consistent data. Frozen source, oracles,
controls, earlier reports and failed attempts remain available.

No project-native source/binary, personal database/checkpoint, live snapshot, registry,
configuration, job, consumed budget or process was adopted/replaced. No commits,
pushes, physical organization moves or live cleanup occurred. Final hashes and API/
process reconciliation are in [FINAL_VERIFICATION.json](FINAL_VERIFICATION.json).

The original two Gemini High plan critiques were reused and reconciled. Two coding
workers (`c27d5a82c593`, `8ff74cff4f2a`) attempted denied RunCommand actions and failed;
no patches were integrated. Two supplemental tool-free High source reviews
(`048cd901ee8c`, `200e3433e2de`) timed out with no usable findings. Codex implemented,
reviewed and verified the actual changes. No model downgrade, account switch or
quota bypass occurred. Worker launch/results and all failures are preserved.

Other preserved attempts: policy binding stopped an initial AFTER replay before
extraction; nine private-runtime tests initially lacked editable-package startup;
one database script had a pre-execution syntax error; a positive-path harness
compared JSON lists with Python tuples even though counts and record SHA matched.
Each was corrected with actual evidence, without weakening numerical acceptance or
silently restarting completed work. Earlier elapsed extraction time remains charged.

Live activation, a patched production interpreter, confirmed GPU hardware, a bounded
kernel implementation proposal and any fleet database migration remain separate
transition actions. Large real retention-quality studies, exhaustive game accuracy,
stronghold recall, terrain/landing safety and public hosting/billing are separate
projects; they were not relabeled as completed by this readiness task.
