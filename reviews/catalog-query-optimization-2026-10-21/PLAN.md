# Catalog query optimization — evidence-based plan

Status: user approved this concrete plan with "Yes". The scoped reader patch is
implemented and correctness-verified; overall concurrent capacity remains FAILED.
See REPORT.md and the separately reviewed, unapproved FOLLOWUP_PLAN.md.
The user requested number one, catalog query optimization. No GPU work, database
engine replacement, predictor change, seed generation or personal activation.

## Objective and measured baseline

Remove avoidable CPU work from cold queries while retaining exact rankings,
same-anchor filters, provenance, unknown semantics, integrity checks and cursors.
Keep the current10-second service allowance and2-execution/4-admission limits.

Diagnosis used fresh disposable copies of the existing500-world synthetic corpus
and200-world natural catalog. No live data was changed. Cold means fresh service,
result/index caches; the OS filesystem cache was not flushed. One unprofiled
measurement per selected case, with separate cProfile runs for attribution:

| Case,8192 border | Unprofiled wall | Profile attribution, with profiler overhead |
|---|---:|---|
|500-world v1 Origin, broad |6.274s |1000 index validations for500 leaves;17.40s of20.61s profiled time in index validation |
|500-world v1 Recommended, broad |14.000s |1000 index validations;81000 summary validations for40500 decoded layouts;17.56s index+17.94s summary inclusive costs of46.69s total |
|200-world accuracy Recommended, broad |7.606s |400 index validations;32400 summary validations for16200 layouts;9.00s applying witnesses, including copies, of27.77s total |

Cumulative costs are nested; do not sum them as disjoint stages or compare profiled
seconds with unprofiled service deadlines. Index decode makes about65million Python
character checks per500-world query. A diagnostic compiled ASCII lowercase-hex
fullmatch agrees with the character predicate on25025 bounded ASCII/Unicode
examples and runs6.31x faster on representative valid strings. This is a small
character-check microbenchmark, not a proved end-to-end speedup or complete decoder
parity. Existing500-world18-query cold maximum14.497s; warm maximum0.0295s.

## Proposed changes and ownership

1. `src/seed_search/catalog/index.py`: replace the per-character Python generator
with a compiled `[0-9a-f]*` fullmatch. Keep string-type, exact byte-derived hex
length, integer value and reserved-bit checks. Empty zero-row form, uppercase,
Unicode, whitespace and malformed inputs must retain existing behavior. All
public validators/filter functions remain strict.
2. `src/seed_search/catalog/segments.py`: normalize/validate the optional request
once per iterator. Each loaded index still receives full schema/digest/bitset
validation plus row/payload/policy/registry binding before selection. Use the
private already-validated selection routine within that boundary instead of
calling the public validating wrapper again. After `unpack_summary`, which already
validates the entire decoded summary, remove the immediate duplicate validation.
Preserve payload hashes, expected layout IDs, build/member/geometry checks and
the legacy no-index path. No cache persists trusted validation across reads.
3. `src/seed_search/catalog/accuracy_query.py`: skip witness application/deep copying
only when all model-matched per-feature point lists are empty, explicitly
`not any(fine[wid].values())`. A dictionary with empty lists is not itself empty.
Use a cheap top-level `dict(layout)` copy on this branch. Otherwise call the
existing function unchanged. The query-local summary is only
read by ranking/potential checks; no public shared mutable cache is introduced.
Keep the `apply_witnesses` public scoring-copy contract, all positive OR semantics,
unknown handling, evidence generation binding and pre-cache integrity checks.
4. Add meaningful regressions for malformed bitsets, corrupted index/payloads at
the optimized reader boundary, direct public filter validation, and no-witness
versus real-witness accuracy responses/cached mutation isolation. Reuse existing
oracle/cursor/TopK/unknown/geometry tests rather than mirroring implementation.

Codex owns these three source files and integration. Gemini High independently
critiques this plan read-only, then reviews the resulting small patch/evidence.
There is little useful writable independence here; do not launch coding workers
on overlapping hot paths. No four-worker fan-out. Test/profile helpers and new
reports have separate ownership; no worker merges, pushes or modifies the primary.

## Order and validation

Freeze the current source hashes and selected request/result keys. After approval,
implement the three bounded changes, run focused existing tests, then compare a
matched before/after build on the same corpus and interpreter. No native build.
Use the existing representative18-query set (3 borders,2 grid modes,broad/selective/
mixed requests), full ordered unique-world pagination and an independent exhaustive
oracle. Run the full18-case cold suite once after the change and repeat the
selected broad baseline cases three times before/after, sequentially, reporting
the range/median. Fresh service caches per cold query; report warm behavior too.
Do not claim disk-cold performance or population-tail confidence from this sample.

Check current accuracy queries across4 modes/3 borders, positive fine recovery,
partial OR, unresolved candidates, detail/favorites API contracts and cached
integrity/cursor expiry. No frontend change or BDS experiment is needed.
Run eight simultaneous distinct cold HTTP requests on the disposable500 corpus
with unchanged admission/deadline settings; admitted requests must complete
correctly, excess load may return explicit429. Preserve all500-world pagination.

Acceptance: exact result/world/layout/order/score/contribution parity with the
baseline and independent oracle; all existing corruption/geometry/unknown/cursor
tests pass; no lost refined witnesses; no new retention rule or capability gate;
all18 selected single cold requests finish within10s; at least two correct200
responses and no query-timeout503 in the eight-request bounded load test, with
remaining responses200 or429. Treat unmet capacity as failure, not partial success.
Report individual samples and errors. Warm query behavior must remain comparable.

Resource limits: existing corpora only; one benchmark process and one query suite
at a time, at most120s per diagnostic/profile case,2GiB RSS,512MiB new reports/
copies,600s outer wall per validation phase. The bounded8-request test uses only
its existing2 active requests. Stop on cap failures and preserve evidence; no
automatic benchmark retries, new natural worlds or larger ingestion campaign.

Only after checks and final reconciliation, refresh the owned catalog preview if
needed. Preserve the personalPID60144/run/library and all immutable snapshot files;
no primary native rebuild, automatic commit/push or SQLite/schema migration.

## Risks, alternatives and expected benefit

Deduplication must remove repeated work only after identical full validation has
already happened. Never introduce a public caller-controlled trust bypass. Regex
must use fullmatch with the explicit ASCII language, not permissive `int` alone.
The accuracy no-witness branch must not alias mutable state shared across requests
or suppress a real fine witness. Query-thread contention still needs measurement;
single-query acceleration alone cannot establish concurrent capacity.

This targets the dominant measured work without changing persisted formats or
scoring. Expected benefit is materially faster cold lookup; no numeric end-to-end
speedup is promised before paired measurements. Avoiding copies helps the current
accuracy UI. Index-schema redesign, extra caches, multiprocessing, approximate
scores, more concurrent workers and a custom database are deferred alternatives.
If these changes do not pass the unchanged capacity gate, retain the failure and
prepare a separately scoped follow-up from the new profile.

Relative complexity: low-to-medium source change, medium correctness/performance
verification. Estimated approved execution20–35minutes, subject to test/review
results. Current diagnosis+plan is not implementation approval.

## Gemini High critique reconciliation

Review2d2445eb1f5a succeeded, exit0, denied_actions=[],27794 reported tokens,
modelgemini-3.8-flash-high/efforthigh; no tools, edits or tests. Preparation of the
earlier95ba7403fec7 failed the30KB context limit before model execution; one
bounded narrower retry succeeded. No quota/auth failure or model/permission bypass.

Accepted explicit empty-list detection and module-level compiled fullmatch.
Accepted a cheap top-level copy for future isolation, but rejected the review's
specific claim that today's `_rank` inserts `_sort_key` into input layouts: current
query.py constructs a separate candidate dict. A diagnostic actual81-layout leaf
probe confirms input dictionaries unchanged and sort keys present only in results.
Nested vectors remain read-only on this branch; existing public `apply_witnesses`
copy behavior and serialized-cache mutation isolation remain unchanged and tested.

The reviewer raised queue+GIL contention. This is a valid capacity risk, not a
reason to shift the clock or weaken the gate. Current time budget already includes
admission waiting; the2s execution-wait limit returns429 if it cannot acquire.
Keep these contracts and measure the actual8-request case. Two active Python
queries can contend even after single-query improvement; report any remaining503.
The reviewer agreed validation deduplication is sound only at the verified reader
boundary and public filter validation must remain strict. Those are explicit
requirements above. No unresolved plan blocker; achieved speed remains unmeasured.

## Request-local validation deduplication addendum

The initial patch passed all18 single queries but failed concurrent capacity.
Post-change profiling shows40500 world-ID derivations for500 member seeds and
two identical layout-ID derivations per decoded row. Consolidate these duplicates
in the same approved segments.py validation boundary: memoize expected world IDs
only within one iterator/header and only after seed/observation membership checks;
retain per-row equality checks. Let the already-strict unpack_summary perform the
layout-ID derivation once. No persistent trust cache or public API change. Add a
legacy no-index malformed-ID regression, then repeat exactness/capacity checks.
The initial failed gate remains preserved in INITIAL_QUERY_VALIDATION.json.
Multiprocessing FOLLOWUP_PLAN.md remains an unapproved fallback, not implemented.
