# Catalog query optimization — verified patch, capacity goal still open

The approved three-file optimization is implemented and verified in the workspace.
Single-query latency improves substantially, with exact results preserved. Concurrent
capacity remains unresolved. The live preview has **not** been restarted because
the deterministic admitted-query checks still fail the10-second deadline.

## Changes

`index.py` uses a module-level compiled ASCII lowercase-hex fullmatch in place of
the Python character loop, retaining type/length/zero/reserved-bit validation.
`segments.py` validates each index and decoded summary once, normalizes a request
once, and reuses a derived world identity only within the same iterator's fixed
header and membership-checked seed. Every row still checks membership, expected
world ID, geometry, payload hash and strict decoded layout identity. Public index
filter validation remains strict. No validation cache survives the iterator.
`accuracy_query.py` avoids deep copying when all model-matched witness lists are
empty, using a query-local top-level copy. Real witnesses still use the existing
copy/refinement function. Scoring, required predicates, unknowns, provenance,
snapshot/generation bindings, signed cursors and serialized-cache isolation stay
unchanged. No schema, native predictor, GPU, database-engine or data-generation change.

## Matched measurements

Three sequential runs before and after on the same interpreter/corpora. Before
uses a frozen copy of the actual uncommitted pre-change source. Cold means fresh
service/result/index caches; the OS filesystem cache was not flushed. These are
local samples, not production tail estimates or disk-cold throughput.

| Query,8192 border | Before median | Final median | Speed ratio |
|---|---:|---:|---:|
|500-world Origin |5.985s |3.047s |1.96x |
|500-world Recommended |13.372s |7.594s |1.76x |
|200-world accuracy Recommended |7.187s |3.569s |2.01x |

All complete paginated responses in these comparisons match exactly, including
world/layout ordering, scores, contributions and saved summary fields. The500-world
corpus is synthetic transformed template data, not500 newly searched natural seeds.

All18 representative500-world single cold queries now finish within10s, maximum
7.732s. Full ordered results match frozen-code enumeration of all121500 layouts,
without request bitmap filtering. That exhaustive reference uses the frozen scorer,
not an independently rederived scoring formula. Existing independent raw-observation
oracle tests pass as well. Warm maximum in the18-case run remains about0.030s.

The current accuracy HTTP checks pass all4 anchor modes×3 borders, immediate warm
repeats,200-world unique pagination and18 saved provider-tile presence checks.
No new game certification or whole-border absence claim follows.

## Why the concurrent goal is not complete

The first optimized eight-request burst still produced two503 query_timeouts and
six429 busy responses. Its full failure remains in INITIAL_QUERY_VALIDATION.json.
Profiling then exposed further duplicated world/layout identity work; the small
request-local reader addendum removes it while retaining strict checks.

After that addendum, the planned eight-request burst passes: queries4and8 finish
correctly in about6.61/6.63s; six others return busy. However, those are different,
cheaper queries than the initially admitted failures. Treating this alone as a
fixed capacity problem would be misleading.

Deterministically admitting the actual previous failure pair(query5 mixed
Recommended2048 and query10 selective Recommended4096) still yields two503 errors
at10.01–10.04s. Two broad Recommended queries3and15 together also yield two503
errors at about10.04s. These are retained in ADMITTED_PAIRS.json. The10-second
allowance and2active/4admitted limits were never changed.

A post-initial-change profile measured20.20CPU seconds in20.22wall seconds with
the installed GIL-enabled interpreter. That profile predates the final identity
deduplication; it supports the CPU-contention diagnosis but is not a current
unprofiled latency or complete causal proof. Independent CPU query processes are
a proposed next step, not implemented or assumed to solve the problem.

## Verification and reviews

-118 focused checks passed52.72s;84 broader checks passed50.10s; after the final
identity addendum,67 reader/oracle/accuracy checks passed36.52s. These suites overlap;
the counts are not a sum of unique tests. Regressions include malformed/reserved
bitsets, public/legacy invalid requests, corrupted indexed/unindexed identities,
cross-leaf geometry, cold/warm mutation isolation and positive fine witnesses.
-Gemini High plan2d2445eb1f5a, patch2367802e7a2e and final reader09cf03dde7d5
reviews succeeded, exit0/denied_actions=[]. Codex independently executed checks
and reconciled inaccuracies; reviewers ran no tests or edits. See RECONCILIATION.md.
-Only the approved three existing catalog source files differ from the frozen
catalog source baseline. Tests and planning/evidence documents are additive.
No native build, new seed search, source reset/stash/clean, commit/push or merge.
-PersonalPID60144, its run/status and primary binary byte hash are unchanged.
Catalog previewPID69020 remains its prior process. Non-SQLite live files were
compared against the pre-diagnosis copy without changes; exact count and hashes
are recorded in OVERALL_ACCEPTANCE.json and ARTIFACTS.json.

## Next approval boundary

The three-file patch is ready but remains unactivated on the owned preview while
capacity is unresolved. FOLLOWUP_PLAN.md proposes two persistent isolated CPU query
processes with unchanged admission, end-to-end deadlines, exact algorithms and
bounded lifecycle/cache behavior. That is a significant serving architecture change,
separate from the approved reader patch, and needs High critique plus user approval.
High critiquea9c60bf1fa00 is complete; deadline, healthy-worker leasing, bounded IPC,
cache, startup and parent-death mitigations are reconciled in that plan. User
approval is pending. No process-based serving implementation, GPU work or custom
database has begun.

See PLAN.md, BEFORE.json, AFTER.json, QUERY_VALIDATION.json, ACCURACY_HTTP.json,
ADMITTED_PAIRS.json and OVERALL_ACCEPTANCE.json for the actual scoped evidence.
