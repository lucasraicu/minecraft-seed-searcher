# Implementation review reconciliation

The attachment explicitly approves the full reviewed plan including §5a. Existing plan critiques were reused. Every Gemini patch/changed file was read by Codex before scoped integration; worker status alone was not accepted. Complete task responses, actual checks, denied actions, usage and patch hashes are saved under `workers/`.

Core worker `4b117af27f1f` and retention worker `93ba15b1adf2` produced useful source, contracts and tests. Codex accepted their correct implementations and strengthened source/profile/provider/extension validation, exact group union, XYZ ties, auxiliary unknowns, spawn binding, real policy-bound ledger/storage, historical resume and actual-game receipt handling. Legacy scoring/native/vendor algorithms were preserved. Frozen legacy source hashes retain the prior public policy identity; V3 uses a distinct registry/profile/source-bound identity.

Initial UI worker `f835672587c2` and finalization correction `f702e3ad0787` failed with denied commands and no usable patch. UI retry `d87ec4b7296f` had substantive source changes but failed its declared rendering check. Its patch was reviewed, staged in isolation and corrected; no permission bypass was used. Codex fixed static gate assumptions, selected-snapshot negotiation, forbidden generic-query `view`, silent row/alternative truncation, stale list cursors, compact categories, false surface/mountain/cave height labels, missing-height fabrication and SSR fixture/tab assertions. Final UI25checks, all10catalog suites, network/telemetry suites and the production build are independently checked; final outcomes belong in RELEASE_REPORT, not worker self-report.

Research `b9c67897078b` incorrectly claimed no archived actual biome controls existed. Codex rejected that conclusion after verifying archive/member checksums and replaying19841exact points from29worlds. The report's missing variant-controls concern was supported. Both auxiliary variants remain gated. Fresh positive mountain controls filled the exact missing evidence, not a new broad search.

Finalization review `2ec76b079575` identified missing explicit candidate source fields and duplicate-index accounting; source-bound metadata was strengthened and distinct-seed semantics retained. Its suggested128/256/512border values confused radii with fixed border sides and were rejected. Actual scoped failure can be recorded before every other requirement is complete only with actual BDS proof, explicit scoped failure and a reason; a prediction alone never disproves a scope. Worries about releasing roots overlooked immutable snapshot/ranked-union protection. Claim that build identity was absent overlooked its existing descriptor binding; the adapter makes it explicit.

Final UI review context submissions `991ab184b976` and `8d0080cb8110` exceeded the bridge's30000byte cap and failed before review. They were narrowed, without changing permissions. High review `5aa1256416d5` then completed. Accepted: protect list switches against a request effect using an old cursor, thread dynamic metadata through the group helper, and simplify initialization to one selected-snapshot capability fetch. Its claim that reserve buttons did not reset cursors omitted the actual reviewed JSX handlers, which already reset them. Claimed permanently stale detail seed overlooked DetailModal's loaded identity rendering. Claimed unresolved pagination loss contradicted the backend, which returns the whole unresolved set/count on every page. Hypothetical semantic snapshot slugs and unprefixed atomic IDs contradicted strict SHA/registry contracts. Resetting results after editing filters is existing intended invalidation, and malformed over-limit rows never reach the server. Legacy UI contains fewer than16choices; its helper ceiling was nevertheless made explicit.

Audit worker `3ef4b167e15a` produced the independent coordinate oracle and23adversarial self-tests, actual acceptance exit0/denied[]. Codex read all1020lines and the patch. Two corrections were necessary: nearest-witness lists are bounded by their chosen border, not an unstated1024m circle; and retaining every decoded world summary would risk excessive memory. The audit now streams compact per-world best ranks, uses independently cross-checked NumPy geometry, checks missing old members, and compares historical manifests exactly.500randomized Python/NumPy oracle cases pass. Real222world audit outcomes are recorded separately; self-tests alone do not certify migration.

Supplemental High review `04b1e8e51a92` completed read-only. Accepted: cached lower passes must stay provisional behind unresolved higher ranks; explicit Nether reference anchors must not be projected a second time; clear reserve view when a response lacks the new run's metadata; avoid repeatedly serializing unchanged receipts/checkpoints. The supported operator entry point now resolves product and historical anchor bindings, separates list metadata from physical conditions for compatible receipt reuse, and checkpoints on existing SQLite/CAS mechanisms. Real storage tests exercise shared receipt reuse, legacy/product/Nether scopes, pending-before-reserve ordering, actual reclamation, and per-objective role overlap.

Rejected supplemental claims: different world IDs cannot share the same complete source-observation identity under this world's deterministic identity schema, so removing world binding would weaken proof. Actual product memberships do contain their evaluated scope/anchor, confirmed against source SQLite and an end-to-end product binding test. Promotion accounting counts distinct candidates, not raw duplicate rows: treating a duplicate as a lost primary slot would invent reserves. The internal low-level finalization primitive/legacy adapter is not the supported operator API; callers use `finalization_operator.finalize_objective` for canonical requirements, ordered completion and saved anchor resolution.

No quota/authentication failure was observed. Reported worker token usage is saved; no remaining-quota estimate is invented. No workers merge or push, no unrelated edits are overwritten, and no automatic BDS campaign is introduced.

Packed-projection worker c53383beaa38 timed out without a usable patch; Codex wrote
the packed decoder and regression checks. High review49563015a5f6 completed but its
five findings relied on incorrect assumptions: biome counts are Boolean presence,
legacy V1 payloads contain layout IDs and recommended rows include origin, this
frozen V2 source has validated projections/modes, spent() closes over the original
charged amount rather than the crash-reservation field, and the source correction
workspace is explicitly owned/unaccepted. Aggregate-copy preflight rejection is
intentional. Exact round-trip including stale-validator checks and real source
inspection support these resolutions. This does not excuse the later genuine
non-V1 legacy eligibility mismatch: correction now uses the same explicit revision
filter as the original automation policy.

Bulk-review9c5f030ebd39 failed on the bridge's context-size ceiling before review;
no patch/result was accepted. Narrow recovery critique5f465679eadf completed High,
exit0/denied[], read-only; its resource/accounting concerns and Codex resolutions
are recorded in MIGRATION_BUDGET_AMENDMENT.md. Budget extension awaits approval.

High review732780f7df7c found no concrete lazy-query defects. Codex independently
confirmed exact72case full-response parity, complete output feature dictionaries,
separate pending/matching maps and strict stale-validator fallback.

High review34102efd6ee4 raised six groups of concerns. Accepted the mutable returned
context concern: compact contexts are now stored as immutable JSON bytes and each
caller receives a fresh decoded object, covered by a mutation regression. The later
metadata-startup path also closes owned workers when initialization fails.
Rejected against source: cache fill calls snapshot(), which fully decodes/schema-
validates all pages and verifies the logical manifest digest; cache hits rehash the
exact same compressed index and every page, so no changed payload can bypass JSON
validation. Queries require worlds/registry/policy, not membership arrays. A changed
immutable binding deliberately fails closed; refreshing it under the old SID would
weaken identity. Existing shared index entries all use the same(data,size) tuple.
The established budget measures serialized cache bytes, with RSS separately bounded;
no cache ceiling increased. AutomationStore opens no connection requiring a context
manager. Invalid metadata must fail readiness, not silently serve. Actual requests
with rehashing pass well below10s, contradicting the claimed prohibitive overhead.

Snapshot listing previously decoded each historical manifest twice and exceeded
its12s client timeout. It now primes fully verified compact metadata before accepting
HTTP and uses the same checksummed cache thereafter. Startup cost is reported
separately; query result/projection caches remain cold. No request deadline widened.
The initial stress harness used unsupported importance2/4; it was corrected to the
existing1/3/5 contract while retaining all12rows and16alternatives. The reserve replay
audit initially compared version-dependent layout IDs and redundant embedded ranks;
it now compares all authoritative ranks/geometry/other fields and first requires
any embedded rank to equal the authoritative rank. Final rerun is required.
