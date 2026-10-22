# Proposed next correction experiment

Status: APPROVED by user Continue with this after the reviewed concrete stage
was presented for approval. Implement this bounded storage/BDS scope only.
The user's Continue authorized this source/saved-evidence investigation; no native
changes, migrations or new BDS world-generation runs have been made.

## Objective and evidence

Explain the actual biome/structure failures before changing catalog extraction or
personal-search admission. An isolated external comparison rejects disabling depth
or replacing Y with319: cohort311/330quart vs310depth-zero/highY; snowy pilot253/256
vs239/256; both flattening alternatives erase all3correct underground DeepDark
controls. Neither is a general correction.

Two clean stopped worlds were inspected with source mounts read-only, network off,
1CPU/512MiB, copied DBs in bounded tmpfs; only Python LevelDB readers ran, no BDS.
Original signed seed verified from level.dat. Two implementations of packed-array
decoding agree on1,166populated sections across the saves. 95/284 API observations
have directly decoded corresponding stored cells; missing/negative-header sections
remain unknown rather than inventing an inheritance rule. Two disputed Y63 cave
samples contain stored IDs12/30 matching their nearby noncave API controls. Numeric
IDs are not assumed equal to predictor IDs (saved DeepDark190 vs predictor183).
Boundary448..451 and third cave column still lack a directly decoded saved cell.

Structure tracing: outpost(528,512) is admitted through a Y319 raw-quart biome
check; wrapper provides no structure footprint/terrain validation. Stronghold
(820,-1708) is a static region candidate, not the village-associated iterator.
Its returned BDS location corresponds to a different village-associated prediction
(100,-2028) with village(104,-2024). Candidate validity/absence cause remains
unproved. Failed village(-296,-312) passes the existing snowy-biome check.

## Execution order and ownership

1. Portable storage diagnostics: new standalone read-only tooling under
   scripts/predictor_storage_probe.py and a pure decoder under
   src/seed_search/realm/bedrock_biome_storage.py; tests and small raw fixtures under
   fixtures/bedrock-26.52/storage-regressions/. Support only inspected format cases;
   include zero-bit uniform sections as a single32-bit ID covering16×16×16blocks;
   validate packed sections at full block resolution (the exploratory Amulet
   crosscheck covered only the corresponding4-block lattice). Explicitly
   reject malformed lengths/palette indices, report absent/inherited-unknown sections
   explicitly, retain block XYZ/seed/build/raw key/digest and numeric-ID namespace.
   Do not add an assumed numeric-ID-to-name map. No writes to source worlds.
2. Targeted BDS experiment using existing pinned image and two already-tested seeds:
   -3509659830737203357 and -9103892851552028103. Choose fixed failure and positive
   controls before execution. At most128biome XYZ observations and32locate commands
   total; at most8192explicit block reads total to inspect small vertical columns
   around those cases. No large footprint search or world census. Explicitly
   allocate ticking areas and await successful block reads at each target; locate
   queries alone are not a saved-chunk readiness check. Keep loaded
   evidence regions alive through an acknowledged save/shutdown so disputed cells
   can be read back; verify the saved chunks and record any gap as inconclusive.
   Compare API/storage at boundaries, cave/solid positions, Y319 and independently
   observed exposed-surface points. Query 3failed and at least3existing positive
   structure controls. Do not equate locate coordinates with physical completeness.
3. Isolated fixed-mode sampler comparison: current block, raw quart, depth-zero
   diagnostic and explicit-Y observations against held-out controls, preserving
   source/build fingerprints and legitimate underground positives. Codex owns game
   execution/interpretation; no guessed fallback, distance tolerance, or fitted
   cave threshold. A better match count is not proof of a new algorithm.
4. Deliver point-level API/storage concordance and source-path discrimination,
   or a precise remaining limitation. Terrain observations are descriptive and
   cannot alone prove engine-internal rejection rules or general3Dbiome rules.
   A source-backed rule-level correction is possible, not promised. Native replacement,
   alias migration and catalog re-extraction are excluded until an evidenced rule
   and versioned migration plan are reviewed. No automatic implementation at the
   end of a successful probe. Existing persisted observations retain their meaning.

All XYZ input/output positions are block coordinates. Raw-quart sampling uses
(floor(X/4),floor(Y/4),floor(Z/4)); the existing high-Y check uses blockY319,
quartY79, never quartY319. Persist both coordinate spaces in diagnostics/tests.

One isolated Gemini High worker may own only the pure decoder/tests; Codex owns
fixtures, stopped-world copy wrapper, bounded BDS harness/integration and validation.
No overlapping edits, recursive delegation, account changes, merges or pushes.
Reuse existing High source research44126da18699 and request an independent critique
of this concrete proposal before presenting final scope for approval. Critique
4568a3226c1c completed High; responses and reconciled objections are adjacent.

## Limits, verification, risks and acceptance

Moderate tooling work; inference may remain uncertain. Estimate1–2h for portable
tooling and checks, plus30–60min for bounded game preparation/execution/analysis.
One BDS at a time,2CPU/2GiB, cumulative600seconds game wall time,4GiB newly owned
output cap. Do not increase budgets after failure without reporting the cause.
Offline readers:1CPU/512MiB/256MiB tmpfs, copied stopped DB only. No live DB access,
world mutation, original Sweep restart, GPU/customDB, billing or new seed search.

Acceptance: source world DB/level.dat hashes unchanged; exact seed/build/settings
and query provenance; strict malformed/incomplete-data tests and independent
decoder cross-check; no false success on absent saved cells or failed APIs; preserve
known mismatches and positive underground controls. Relevant regression tests pass.
Report each hypothesis supported/rejected/undetermined; no population accuracy or
complete village count claimed. A stopped-world palette proves persisted data,
not every internal world-generation stage or structure's physical completeness.

Implementation risks: packed-format/version differences, unsupported inheritance,
save lifecycle gaps, Bedrock numeric-ID namespaces, version drift, biome-vs-terrain
mechanics, insufficient memory/time or API capabilities. Stop inconclusive arms;
do not silently widen bounds or alter acceptance. Browser QA remains deferred.
