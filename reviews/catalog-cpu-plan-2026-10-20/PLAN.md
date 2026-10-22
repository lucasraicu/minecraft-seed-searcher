# Next-phase proposal: CPU public-catalog reference slice

2026-10-20, America/Los_Angeles. Status: proposed, awaiting user approval.
This is a new catalog milestone, not a continuation of unfinished Phase 1/2 work.

## Objective and result

Build an isolated, reproducible local catalog reference implementation that answers
supported player requests from saved world observations. Demonstrate that one
observation envelope supports 81 centers and exactly three border side lengths:
2048, 4096 and 8192. Preserve personal search and all active services.

The output is a developer CLI, small test catalog, recovery evidence and measured
cost report. A public website, retention campaign and production deployment are
not deliverables. This establishes a correctness reference for later GPU and
specialized lookup experiments; it does not establish actual-game accuracy.

## Evidence and source reconciliation

- Phase 1/2: 1,274 tests passed; frontend build passed. Those are recorded results,
  not tests rerun during this plan. See ../phase12-2026-10-20/REPORT.md.
- Personal rejection profiling cannot estimate complete public records/second.
  The measured ~289 KB positive personal record is not a public record estimate.
- No runtime catalog package exists. docs/catalog/v1 is proposed only; use the
  consolidated PUBLIC_CATALOG_SYSTEM_SPEC.md over conflicting older plans.
- Backend.biome_points supports biome-only batched queries. Backend.grid also
  computes climate and approximate height; avoid paying that cost for raw IDs.
- Backend uses a process-wide RLock. Start serially; do not claim multiple Python
  threads give independent native calls. Later process workers must each own their
  Backend and stay within the aggregate CPU budget.
- native/bridge.c:inside uses inclusive upper bounds. The new catalog adapter must
  translate half-open [lo,hi) to inclusive [lo,hi-1], then independently validate
  returned points. Do not change existing native/personal boundary semantics.
- Backend.structures reports a negative native capacity result as an error. Treat
  that as failed/incomplete coverage, never a valid truncated inventory.
- MC_26_50 model identity and target_version 26.52 are not exact-build game proof.
  Preserve predictor identity separately; any game-build compatibility assertion
  requires an explicit evidence-scoped mapping. Unaccepted mappings remain research
  only and cannot be published as an available player capability.

## Architecture and file ownership

New src/seed_search/catalog/ only, plus dedicated tests/catalog/ and a new bounded
scripts/catalog_reference.py entry point. Package/module names are proposed.

1. Codex: models.py, capabilities.py, geometry.py, request.py; freeze interfaces
   before delegation. Reuse registry IDs and family mappings through read-only
   versioned loading, not a second hand-maintained registry. Explicit runtime
   capability checks supplement the proposed JSON request schema.
2. Gemini A (High): extract.py and coverage.py, with owned extraction tests.
3. Gemini B (High): artifacts.py and store.py, with owned crash/recovery tests.
4. Gemini C (High): summaries.py and query.py, with owned query tests; begin only
   after frozen observation and store interfaces exist. Three useful workers at
   most; one or two where dependencies constrain useful independence.
5. Codex: independently written coordinate-based query oracle, CLI/integration,
   regression checks, source-drift review and final report.

Coding workers receive isolated snapshots including dirty changes; no overlapping
writable ownership, merges, pushes or modification of the original working tree.
No existing native source, personal admission/scoring, running server or live web
assets are changed. No production routes, accounts or billing migrations.

## Data and query contract

- Store full signed int64 seeds and serialize them as decimal strings in JSON.
  Retain world/settings, predictor binary/source, registry/extractor/method,
  geometry and summary revisions in identities and manifests.
- Raw structures use absolute dimension-qualified start coordinates with feature
  and evidence identity. Do not store every block or duplicate coordinates for
  each center/border. Stable deduplication must not collapse distinct start types.
- Biomes: raw model IDs on a world-aligned 64-block lattice at Y=63, in 256-block
  tiles. The largest aligned envelope [-5120,5120) has 160x160 samples: 25,600
  samples, 51,200 raw uint16 bytes/world before compression. Validate representable
  IDs; preserve unknown/unmapped IDs without wrapping. No surface/absence claim.
- Anchors: Cartesian product of [-976,-768,-512,-256,0,256,512,768,976]. Origin is
  the existing (0,0) anchor with an additional role, not duplicate observations.
- 81 anchors x 3 sides = 243 layouts/world. Initial modes: Recommended and Origin.
  Spawn integration remains disabled; prior estimated-world-spawn evidence is not
  exact initial-player placement. Stronghold mandatory counts remain unsupported.
- Counts are full uint32, not clipped at UI maximum16; use wider integer arithmetic
  for intermediate distances and overflow validation. Near-base circles intersect
  the half-open border. Keep witness references and deterministic witness ties.
- Coverage is feature/method scoped with unknown/partial/complete/failed states.
  Complete means declared predictor enumeration/sample coverage, not complete game
  truth. Distinguish unavailable capability, missing data, known sampled zero and
  observed positive evidence. Uncertain predicates cannot become definite matches.
- Query all Required rows on the same layout. OR biome alternatives within a row;
  AND rows. Score only eligible layouts using the versioned declared formula,
  without silently relaxing requirements. Establish each world's best eligible
  layout before unique-world Top K, with stable total ties using the contract's
  canonical unsigned seed ordering and declared anchor tie keys, not platform
  iteration order. No top-25 shortcut.
- The independent oracle reads raw observations and geometry, not packed summaries
  or the query engine's predicate helpers. Compare result IDs, counts, witness
  distances, score contributions, chosen layouts and order.
- Pilot evaluation has no public eviction and no personal qualification gate.
  Retain the entire bounded cohort, including partial/failed receipts. Do not infer
  specialist/diversity retention recall or natural player demand from this sample.

## Persistence and resource limits

Use a separate local SQLite metadata database plus compressed checksummed immutable
bundles with a standard codec. No personal database migration or shared network WAL.
Defer custom binary segments, bitmap indexes and new durability primitives.

Artifacts must be durable before a transaction references them as published.
Use staging, immutable content identity, validated manifests and atomic snapshot
publication. Define orphan cleanup separately; interrupted writes must not expose
complete snapshots. Test restore of metadata plus every referenced artifact.
File durability includes fsync of artifacts and the containing directory before
publishing metadata references; a SQLite transaction alone cannot make files durable.
Only accept opaque IDs/validated relative artifact keys; reject traversal, symlink
escape, incompatible revisions and oversized/decompression-bomb payloads.

After approval, synthetic fixtures precede any real extraction. Then at most TWO
independently preselected signed64 seeds, chosen before observing results, one
process initially, aggregate <=4 CPU threads, <=5 minutes total real-extraction
wall time, <=1 GiB pilot output and explicit memory ceilings. Enforce timeouts via
supervised subprocesses; checks between native calls cannot stop a blocked call.
Stop safely with partial receipts; do not loosen features or hide incomplete worlds.
No BDS world generation, GPU access or large sweep. Expansion to100 worlds needs a
separate cost-based approval; this proposal does not authorize that expansion.

## Order, gates and verification

A. Contracts and synthetic geometry (estimated 0.5–1 focused working day).
   Freeze records, capability matrix for all23 planned features, parser behavior,
   request/ranking semantics and storage interfaces. Unsupported features fail
   explicitly; no blanket claim that every advertised filter is available.
B. Extraction/persistence/summaries (1–2 days, partially parallel).
   Implement one complete envelope and243 summaries, feature-level restart,
   idempotent retries and raw-coordinate oracle. Record limitations per feature.
C. Integration, two-world probe and review (0.5–1 day).
   Measure stage wall/CPU time, memory, bytes/world, successful/partial/failed
   counts and query results. Reuse observations across three borders without
   rerunning noise. Report predictor parity separately from game verification.

Planning estimate: 2–4 focused working days after approval; actual extraction cost
is unknown. Report ETA changes after interface freeze and first complete record.
The two-world probe is a smoke/cost test, not representative public throughput.

Required tests: signed64 round trips, negative tile flooring, all three borders,
positive exclusive and negative inclusive edges, clipped-circle edges, count>16,
missing/unmapped IDs, partial coverage, unsupported modes/features, invalid and
nonfinite fields, revision mismatch, deterministic ties, per-world deduplication,
query AND/OR and best alternative center, random/synthetic oracle parity including
at least200 query cases, failure/timeout replay, concurrent readers of immutable
published snapshots, artifact corruption/truncation and backup/restore. Include
relevant personal regression and backend tests; broaden only when integration
changes or failures warrant it. Contract validator results alone do not satisfy
runtime acceptance. No production capability flags are enabled by test success.

## Expected benefit and unresolved risks

This proves where coordinates live, how borders reuse them, and whether query
summaries reproduce declared evidence. It provides real complete-record cost to
choose later GPU, batching and specialized read-index experiments. It does not
justify pricing, fleet forecasts, a custom durable database or production scale.

Main risks: per-feature enumeration limitations, misleading build/version mapping,
unknown interpreted as absent, same-anchor mistakes, crash-inconsistent artifact
publication, schema drift and resource-heavy extraction. The gates above require
explicit evidence rather than silently reducing the public promise.

## Independent High Gemini critique and resolution

MCP review task3414045be6eb succeeded with gemini-3.8-flash-high and explicit
--effort high, exit0, nonempty SUCCESS, no denied actions and no changed files.
Actual launch.json was inspected. Raw tool evidence: gemini-critique.json.
The first submission80ff5a7a44da exceeded the 30,000-byte context bound and was
rejected before provider execution; a narrower read-only submission succeeded.
No permissions or context limit were broadened; no quota/auth failure occurred.

Accepted: interface freeze before workers; native lock serialization; avoid extra
grid computation; translate inclusive bounds; feature-specific unknown handling;
durable artifacts before metadata publication; deterministic ranking; separately
gate the100-world cohort. These appear in the final scope above.

Codex corrections to reviewer statements, checked against source/contracts:
- The243 layouts are81 anchors x3 BORDER SIZES, not three radii. Each layout also
  has three near-base radii plus an inside-border scope.
- A364-byte payload is not91 uint32 fields: it is352 bytes of numeric arrays
  plus12 bytes of completion bits, per storage_layout.json.
- A full native buffer is not evidence of silent truncation: native emit returns
  -2 on overflow and Backend.structures raises on negative returns. Preserve and
  test that failure, with no complete coverage receipt on error.
- Multiprocessing is an option for independent calls, not a requirement to add a
  parallel scheduler in this tiny pilot. Begin serially under a watchdog; defer
  extraction concurrency until measured. Existing native OpenMP is a separate axis.
- Prefer the existing biome_points adapter; a new native grid optimization is
  outside this proposal. No need to modify the established personal backend.
- Preserve the versioned canonical rank, rather than inventing signed-seed ties.

No implementation, benchmark, extraction or actual-game verification was performed
during planning. No second critique was needed for this coherent bounded slice.
