# Proposed follow-up: two isolated catalog query processes

Historical proposal below. User approved this plan and subsequent OpenMP restoration
on2026-10-21; implementation and acceptance are complete. See
[final report](../catalog-query-processes-2026-10-21/REPORT.md). Earlier pending
approval and no-implementation statements describe the proposal's original state.

Status: High-reviewed proposal with reconciled clarifications; awaiting user approval.
No process-serving implementation is authorized yet. The approved three-file
optimization is implemented and preserves exact results, but its concurrent
capacity acceptance FAILED. No service deadline was increased. This follow-up
implements no GPU path, custom database, new seed campaign or predictor change.

## Evidence and objective

All18 representative500-world cold queries now finish below10s; slowest7.732s.
Complete results/pagination equal a frozen-code enumeration of all121500 layouts.
Matched median Recommended latency improves13.372s to7.594s; current200-world
accuracy Recommended7.187s to3.569s.118 focused checks pass and Gemini High patch
review2367802e7a2e found no blocker; broader checks are recorded separately.

The initial unchanged eight-request gate produced two503timeouts and six429busy.
After additional request-local identity deduplication, one eight-request burst
passed, but it admitted different cheaper queries4and8. Deterministic admission
of the previously failed mixed Recommended2048(query5) and selective Recommended
4096(query10) still produces two503timeouts. Two broad Recommended queries3and15
also both time out. Record overall capacity as FAILED, not scheduling-dependent
success. Python decoding/validation remains CPU-heavy.
The installed interpreter's GIL can serialize that work between HTTP threads;
this is a source-supported explanation, not proof every delay has that cause.
A post-initial-change profile measured20.20CPU seconds in20.22wall seconds
(99.91%) with GIL enabled; it predates the final two identity deduplications and
is attribution evidence, not a current unprofiled latency or full causal proof.

Objective: use two CPU cores for the existing two active queries, while preserving
the10-second end-to-end allowance,2active/4admitted bounds, exact algorithm,
immutable evidence checks, pagination and explicit overload responses. No increase
in parallel admitted work or approximation to make the gate pass.

## Architecture and files

-New `src/seed_search/catalog/query_workers.py`: a fixed pool of two persistent
Python `spawn` children dedicated to catalog queries. Each owns its CatalogService,
query-scoped SQLite connections and bounded existing result cache. It executes only the existing
query path against the configured catalog root; no shell, dynamic code, extraction
or native/BDS job API. Use bounded IPC messages and owned process handles, not
global process-name killing or an unbounded executor backlog.
-`service.py`: optional pool integration at the query entry boundary. Parent keeps
existing admission/execution semaphores. Forward an absolute monotonic deadline
including queue/IPC time; child receives only the remaining allowance, never a
new10-second budget. In-process service mode remains available for embedding and
reference tests. Children disable recursive pool creation.
-`http_server.py`: initialize/wait for the two ready workers before accepting
queries, report startup separately, close them on normal server shutdown. Enable
this only on the owned Catalog preview after acceptance. The personal server
process and its current embedded service are untouched.
-New tests for worker lifecycle, deadlines, exact queries, cursor/cache affinity,
corruption, overload and failure cleanup; retain all existing pure query tests.
Update operational docs and handoff with actual resource/results evidence.

Keep a small parent routing directory (at most16 request keys) to prefer the
idle worker already holding a request's cached results. If that worker is busy,
use the other idle worker; correctness must not depend on cache or affinity.
All workers share the parent's in-memory cursor-signing secret, not a printed
CLI argument. A cursor can rerank on either worker with the same expiry, snapshot,
generation, request and page-size binding. Send built-in data only; validate and
bound IPC requests/replies (1MiB input/4MiB output initially) and reject malformed
protocol/job/generation IDs. No shared mutable decoded-layout cache.

Parent owns process lifecycle. Timeout, EOF or worker crash produces an explicit
503 and never partial results. Terminate/join only the assigned owned worker;
invalidate its routing entries. No automatic replay of a failed request. Replace
a failed idle worker under a bounded restart policy (at most3 failures per5minutes,
then unavailable until explicit recovery), preserving other workers. Closed pipes,
late responses and stale lease generations must not affect a later request.

Worker caches preserve the existing64MiB serialized budget per worker; there are
two budgets rather than one. Account for Python overhead and report parent+child
RSS; cap the experiment at2GiB aggregate. Application read-only query behavior
is not an OS security sandbox. Existing loopback/Host/Origin/body limits remain.
No account credentials, process IPC contents or raw signing secrets in logs.

## Execution, assignments and acceptance

After High critique and user approval: freeze the optimized in-process baseline;
Codex owns pool/service/HTTP integration and bounded tests. Use one Gemini High
read-only final patch reviewer. These paths are coupled; no overlapping coding
agents or four-worker fan-out. Existing uncommitted changes are the baseline.

Test a single worker first, then two: exact mode/border/rank/contribution/full-page
parity with the frozen121500-layout oracle; accuracy modes, positive fine patches,
unknowns, cache mutation isolation, corruption even on warm hits and cursor expiry.
Warm same-query/page requests must normally reach their cached worker; after a
crash they must rerank correctly on another worker with the same signing secret.
Test real owned-worker SIGKILL, timeout and server close; verify no orphan children
or stale replies. No broad search/ingestion or expensive new game experiments.

Rerun the exact eight distinct cold HTTP cases under the unchanged10s budget:
at least two correct200 responses, remaining200/429, no timeout503. Also run two
distinct broad Recommended requests simultaneously to avoid a result dependent
on which cheap requests win admission. Both must finish correctly within10s.
All18 single cold cases must remain below10s. Measure immediate warm repeats,
full cursor pagination, startup, IPC overhead, CPU and aggregate RSS. Provisional
warm budgets:500-world median<=0.15s and200-world accuracy<=0.25s; disclose overhead
relative to the current approximately0.03s/0.11s warm paths.

One benchmark phase at a time, existing disposable500/200 corpora,600s outer wall
per phase, at most2 active query processes,2GiB aggregate RSS and512MiB new output.
Stop/retain diagnostics on failures; no deadline increase, quota bypass, larger
pool, silent acceptance changes or repeated benchmark attempts to obtain a pass.
Only after complete acceptance refresh the owned3001 preview and verify both
it and5173 proxy, immutable snapshot hashes and unchanged personalPID/run/library.

## Tradeoffs and alternatives

Benefits are an explicit hypothesis: independent interpreters can run the two
CPU-bound queries on different cores. This adds process startup, memory, IPC,
cache affinity and recovery complexity. Two caches may duplicate data. Parent
timeouts and worker cleanup must remain bounded. GIL diagnosis does not prove
parallel speedup; the actual heavy-pair test decides.

Alternatives: further optimize packed-summary validation in one interpreter, or
add a content-verified immutable decoded cache with single-flight work. The former
changes more validation logic; the latter changes cache/trust/memory contracts
and may not help first-ever cold requests. Reducing active queries to one changes
admission semantics; raising the timeout hides the gate failure. A custom database
does not directly address the measured Python validation CPU cost.

Estimated effort after approval:35–60minutes including lifecycle and load checks,
subject to failures. This is a separate significant implementation requiring
approval; the user's approval of the earlier three-file patch is not extended
silently to a multiprocessing serving architecture.

## High critique reconciliation and required clarifications

Reviewa9c60bf1fa00 succeeded, exit0, denied_actions=[], explicit High reasoning;
no tools, edits or tests. Its issues below are resolved as requirements before
implementation; code and achieved capacity still require actual tests.

-Keep one absolute parent deadline from request entry through queue, dispatch,
serialization and reply. Child remaining time cannot reset it. Keep one total
execution-wait budget of at most2s; do not add another independent2s pool wait.
Measure IPC and deadline margins. Do not invent a worst-case runtime predictor
or silently reject valid requests from an unmeasured feasibility estimate. Lack
of a healthy idle lease yields explicit overload/unavailable, not an unbounded
queue. Exact tight-margin requests may still time out; admission/capacity tests
must expose that rather than change the time allowance.
The deadline must bound IPC writes as well as reply reads: a blocking pipe send
cannot become an unbounded parent wait if a child stops reading. Use bounded
nonblocking framing or a fenced deadline watchdog that terminates only that
assigned child and unblocks the writer; verify this with a deliberately hung child.
-A ready, healthy worker lease is authoritative: at most one request per worker,
and leased requests never exceed min(healthy workers,2). Static2-execution is an
upper ceiling, not permission to dispatch two jobs to one surviving process.
Quarantine failed workers and invalidate their route before releasing the lease.
No dispatch while replacement is starting. Test one-dead/one-live and zero-live
states, late replies, exhaustion of restart budget and bounded2s total admission.
Also test parent SIGTERM and SIGKILL. Idle children exit on closed control pipes;
busy children need a bounded parent-liveness check/watchdog, not an assumption
that Python's normal finalizers run after abrupt parent death. Verify no orphan
children remain within a declared cleanup bound; record that bound and actual time.
-Correct the review's cache-budget reading: each worker retains32MiB result plus
32MiB fallback-index budget,64MiB each/128MiB total serialized budget, not64MiB
split across workers. Python/runtime overhead is additional and aggregate RSS is
measured. Affinity is an idle-worker hint only; never wait behind a busy key owner
while another healthy worker is idle.
-Correct the IPC concern's unit: worker.query returns a page of at most50 results,
not the private Top1000 cache. Current500-world pages with an8192byte cursor stay
well below4MiB; see IPC_SIZING.json. Before implementation acceptance, bound all
valid current response shapes including12 contributions, unresolved candidates
and accuracy metadata. Check the actual frame length before IPC write; unexpected
oversize must return a small explicit error, never silently drop/truncate a pipe
or change pagination. The1MiB input/4MiB output caps remain provisional until that
bound is demonstrated.
-Startup readiness includes import, initialized bounded cache, catalog root/schema
and metadata ping; no full-layout/result prewarm. Preserve query-scoped connection
lifecycle. Separate startup/health time from application-cache-cold requests, and
retain the unflushed OS-cache caveat.

Reject the review's assertions that multiprocessing is the only viable design
and that different queries cannot share decoded data. They can share snapshot
leaves/indexes, although selected rows may differ. C validation, packed views and
verified single-flight caches are alternatives with different risk/complexity,
not forbidden solutions. Choose two processes as a bounded experiment preserving
the current exact algorithm. Single-query CPU/GIL evidence supports the hypothesis;
it does not guarantee multicore speedup or prove every delay's cause. The two
deterministically admitted failure pairs and heavy-pair gate decide acceptance.
