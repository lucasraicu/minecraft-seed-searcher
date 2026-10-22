# Spawn correction and catalog simplification

Status: completed and adopted on localhost2026-10-21.
User explicitly approved SPAWN_CORRECTION_PROPOSAL.md on2026-10-21 after its
explanation. Earlier approval-block checkpoints are historical.

## Implemented and validated

The separate helper uses the existing vendor fitness/search kernels without
chunk-center rounding. Vendor sources and both personal/native engines remain
unchanged. The actual helper matches world-spawn X/Z in116 independently retained
Bedrock worlds plus8 fresh frozen controls,124 distinct seeds total. All8 fresh
worlds have API observations at load/ticks20/40 and independent saved level.dat
agreement,0 players and clean owned-resource cleanup. This supports the pinned
BDS1.26.52.3/default-world reference, not exact player landing, Y, safety or all
worlds/versions. The app's mode remains prediction-based.

Actual old/new helper batches (116seeds,5interleaved repetitions) have medians
6.4947/6.4821ms per input; each input performs2reference computations and emits
JSON. This shows no material added local CPU cost, not a fleet throughput claim.

The five terrain-heavy proposals have already been removed from the current
registry/UI by user direction.16presets,17records,31public filters and3Realm boards
remain. Historical IDs are preserved. No portal traversal, physical-instance
census, long connected-biome survey or per-screened-seed terrain work was added.

Portable fresh evidence: fixtures/bedrock-26.52/spawn-correction/ (31checksummed
archive members,15kB compressed). It retains the frozen protocol, pre-generation
predictions, API/saved metadata, raw level.dat, source/observer/properties/logs and
helper build provenance. Two initial startup failures (Docker inspect/create race
and daemon log-driver option) created no world DB; their reports remain preserved.
All eight completed worlds used the same fixed seeds after harness correction.

## Integration and resource evidence

The migration uses a separate policy workspace and helper executable pin. It
reuses raw absolute-coordinate observations and Realm facts, replaces only the
estimated anchor, rebinds unchanged grid summaries and derives changed spawn rows.
It recomputes source-bound product memberships and publishes immutable snapshots.
The original catalog remains untouched; the new root now serves the local catalog.

Initial full-grid recomputation was unnecessary; Codex checkpointed its owned
process and reused previously validated geometry instead. The remaining original
allocation then checkpointed89worlds. An explicit conditional600s allocation
advanced past180worlds before its margin stop; subsequent explicit bounded600s
allocations completed the remaining worlds and recovered publication. These are migration
allocations from saved data, not new seed searches or automatic budget resets.
All222unique receipts published successfully.221worlds changed X/Z; one already
had the same coordinate and received updated helper provenance. Publication
initially rejected the old/new policy's shared generation number222; its historical
fallback now compares policy identity before treating equal counters as a conflict.
A realCAS/SQLite regression preserves both policy histories and existing
same-policy divergence guards. Publication recovery completed in159.18s.

Current code adds no new durable database engine/schema. CPU/numeric work stays
single-threaded, nice+10,4GiB RSS and2GiB output limits. Original frozen scoring
budgets845/265/140, personal Top50/checkpoints and native binaries are preserved.

## Review and tests

Codex ran80 affected Python tests successfully in30.61s, including actual compiled
helper evidence replay, malformed signed64 input, source-manifest/link guarantees,
re-anchor invariants, cached/noncached geometry parity, missing-grid rejection,
actualCAS/SQLite committed-receipt replay and wrong-pin/corrupt-artifact rejection,
existing retention/store/HTTP/query/product regressions.
After the policy-generation fix,30focused store/paging/query tests passed;12HTTP/
product checks passed for active-root metadata. All9Node catalog suites pass,
20network/actual-App-handler checks pass, and the final TypeScript/Vite build
passes54modules. All36actual product HTTP responses pass the real UI decoder.

Gemini High plan1521fe97f525 and source reviewsab26dd481f9b/2cb7769672dc succeeded
with nonempty output, exit0 and denied_actions[]. Reviews ran no tests; Codex
independently reconciled them. Codex implemented the missing grid and replay tests
suggested by the last review. Its module-patch concern is restricted to this
single-threaded isolated migration CLI; serving/extraction modules are unchanged.

Coding worker6d4c848fa7a2 attempted a forbidden RunCommand and returned empty
SUCCESS. The bridge rejected it as permission_denied; no patch was integrated.
Codex authored the helper/migration changes directly. Vendor warnings printed by
the real build are preexisting unused/C23-label warnings, not vendor modifications.

## Independent final audit and adoption

`audit_migrated_catalog.py` checks all222worlds against original absolute facts
using independent NumPy coordinate tests and full sorting. It passed20,646feature
scope counts/nearest distances across all3borders/dimensions,6,216independent
preset/density/proximity evaluations, all36product TopK boards,53,949unchanged
recommended rows, unchanged Realm evaluations and every copied historical snapshot.
Cluster checks combine the unchanged evaluator's regressions, raw witness distances
and independent membership full-sort; they do not certify physical instances.

Nine mixed OW/Nether HTTP queries (3borders×Origin/Recommended/estimatedSpawn)
passed in5.80–6.81s with disjoint pagination; the10sservice deadline was unchanged.
These are application-cold cases on this local workload with warm OS caches,
not latency proof during a saturated personal sweep or production traffic.

The idle catalog-only backend now serves snapshot
`c834df429b4e7c704ed05d40c8e9898e7f37f622ce21876a066ef69d676f726b`,
policy`5c253b10e0e3663a989b685fb5b56daac0b070624273b71062b0edce2fb289a4`.
New root is the external base's catalog/ folder. Old snapshots/legacy registries
remain readable there; the entire original catalog root's3,910recorded files are
byte-for-byte unchanged. Personal SQLite/WAL/restoration and both native binaries
match their saved hashes, and all semantic candidate/status fields are unchanged.
Only preexisting read-time progressUpdatedAt/discoveredAt timestamps differed.

Live UI: http://127.0.0.1:5173/#catalog . Backend97398/3001, query97400/97401;
personal91321/3000 and Vite65292 remain unchanged. Public control is active with
0/600s consumed and no campaigns/jobs. No new seed campaign was launched. An
actual personal-server preview accepts the new root and starts no work.

Blank opt-in catalog folders now resolve the serving catalog's root before both
preview/start; explicit user folders are preserved and personal-only adds no
lookup. Destination resolution runs inside the existing command mutex, so a
second click cannot issue a duplicate launch and a failed lookup sends no POST.
Gemini reviewd62800902469 identified this concurrency issue; Codex fixed it and
verified the actual App callback through a TypeScript-AST harness. Its claims of
empty preview dependencies and swallowed HTTP errors were rejected: actual
dependencies are[request,previewKey], and requestJson propagates network/HTTP errors.

Interactive browser QA remains waived. GPU/custom engine, public hosting/billing,
terrain-heavy products, exact player landing and physical-instance certification
remain outside the approved scope. No commit, merge, push or account switch.

External evidence/workspace root:
~/.local/share/antigravity-worker-mcp/spawn-correction-approved-20261021/.
