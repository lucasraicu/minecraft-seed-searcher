# Predictor resolution — evidence and implemented corrections

> Historical checkpoint: the subsequent native corrections and full same-cohort refresh are complete. See [ENGINE_REPORT.md](ENGINE_REPORT.md) for current results and limits.

The missing-record problem and two biome-name aliases are resolved in diagnostic
tooling. The static stronghold exists. Two reviewed structure starts have strong
false-positive evidence. A general native cave-boundary or village/outpost
rejection fix has **not** been established. Do not describe this stage as 100%
prediction accuracy or a complete catalog census.

## Persistence and storage

The original strict export supplied 27/54 readable points. Raw key inspection
found no Data3D records for 21 points; six more used `0xff` repeat markers.
The original exports and strict decoder remain unchanged.

Four fresh worlds tested read-only versus dirty/restore with equal 200-tick dwell
on the same two seeds. Read-only saved 9/11 requested chunks (68/78 target points);
dirty/restore saved 11/11 (78/78). A temporary marker was written only to an
originally-air Y319 block in each owned disposable chunk and synchronously restored
with permutation/state checks. No barrier remained in saved block palettes.
Original stopped worlds were read-only.

`resolve_repeated_sections` explicitly copies the entire preceding 16³ section,
with leading/malformed repeats rejected. Independent Dragonfly source and BDS
height observations support the semantics. CLI `compare --resolve-repeats` returns
revision v2; default strict v1 is unchanged. All original 54 coordinates are now
readable in newly persisted worlds, with numeric IDs and raw-record checksums.
Readability does not establish native prediction agreement.

## Biomes

Mojang biome definitions and the Chestnut wolf biome filter establish that
`redwood_taiga_mutated` and `redwood_taiga_hills_mutated` are old-growth spruce
taiga. The shared canonical alias table now reflects that. Six old cohort
mismatches across three seeds were alias errors; frozen historical comparisons
retain their original raw names and policy.

Cave boundaries remain unresolved. Tests of Y+1 quart offset, continuous climate
coordinates, Java-style Voronoi hash variants, climate interpolation and vertical
shift alternatives each improve some points but break other known-good controls.
No serving native sampler was changed or rebuilt. Solid deepslate can contain
Deep Dark biome values, so solid-block cave rejection is unsupported.

## Structures

| Seed | Candidate | Finding | Interpretation |
|---|---|---|---|
| -9103892851552028103 | stronghold (820,-1708) | Saved stronghold-like blocks, BDS membership at Y1..25 and independent player confirmation | Exists; retain static enumeration. Locate reports another stronghold. |
| -3509659830737203357 | village (-296,-312) | No village membership throughout start chunk; player reports no village | Reviewed false-positive start. |
| -3509659830737203357 | outpost raw (528,512) | No outpost membership throughout start chunk, including projected (536,520) | Reviewed false-positive start. |
| -3509659830737203357 | village (-360,248) | 11,264 member blocks in positive chunk | Positive control, not 11,264 structures. |
| -3509659830737203357 | outpost raw (-1008,400) | 5,632 member blocks in positive chunk | Positive control, not a world census. |

The four complete chunks require 393,216 membership queries. Queries used the
experimental 2.11.0-beta API only on separately copied worlds, with source hashes
unchanged. Full Y columns and individual points are retained separately. Empty
individual membership points are unconfirmed, not automatic absence.

Both disputed chunks contain Ancient City membership below the surface. This is
correlation, not proof of an Ancient City exclusion rule. Village viability at Y0
would incorrectly reject seven of the 27 previously located villages; lower-height
outpost filters also lose positives. These native changes were rejected.

## Catalog correction

`ADJUDICATIONS.json` pins seed, original world/observation/snapshot, source header,
BDS proof hashes and target/control chunks. Only its exact reviewed digest is
accepted. It excludes the two candidate starts, never all near-city structures.
New research identities bind the transformation, original header and ledger.
Original snapshots, raw audits and evidence remain intact. Retained audit rows
keep their original outcomes and verifier/report hashes; excluded checks remain
in derivative observation provenance and the original audit. No new stable audit
is fabricated from beta membership.

Only the affected world's 243 summaries are recomputed. The other 48,357 numeric
payloads are preserved exactly under newly bound metadata. Biome samples are not
re-extracted or silently corrected. Recognized reviewed-exclusion coverage remains
predictor inventory coverage, not physical-world recall. The publication callback
writes and reads back evidence/previews before SQLite COMMIT makes the new
generation visible. Failure keeps the previous latest; unreachable immutable files
are safe to reuse on retry.

Live refresh passed: new snapshot
`ab4089d3ccd9c4cbb9fec395382cf5c277be8370e287cde8c91abe8ea81b24da`,
original `3d964acd07729a1aa50c23ba90e90a37754c009fc685f0313cc6cf0157eddd6a`
retained. The Origin/radius2000 Rare village list is now 27, with 27 retained exact
BDS locate matches; exhaustive/generated physical counts remain null. The affected
whole-envelope village inventory is 122 (formerly 123), outpost 30 (formerly 31).

Final isolated verification checked all 200 world's spatial facts, all 48,357
unaffected numeric summaries, raw counts/distances for all 243 corrected layouts,
four derived audits and indexed Top20 parity on three border/anchor contexts.
Live verification compared 1,272 immutable files to that rehearsal, old file hashes
and snapshot row, SQL membership, status/query/product/detail on ports3001 and5173,
and the preserved personal view on3000. The 103-sample live transition monitor saw
zero errors and found previews/evidence ready with the new generation. Live refresh
took206.23seconds including monitor overhead; final isolated verification111.47s.
See CATALOG_REFRESH_RESULT.json for exact results. Plain reload of
http://127.0.0.1:5173/#catalog selects the new generation; old pinned links retain
historical values.

## Verification and remaining work

Portable replay: `python3 -S scripts/predictor_diagnostics.py --resolution-fixtures
fixtures/bedrock-26.52/predictor-resolution`. Resolution/storage/coordinate/alias
and evidence regressions passed 130 tests plus 29 subtests before catalog refresh
implementation. The broader catalog/predictor suite passed395tests+29subtests in162.41s; final
focused correction/historical replay checks passed29tests in1.14s (overlapping
counts). Node syntax passed for all three new observers; standard-library replay
passed. Crash-before-commit and fresh-reader callback regressions passed.
`git diff --check` reports a preexisting native/bridge.c:536 EOF blank line; its
baseline hash is unchanged. No unrelated edits were repaired or overwritten.
Gemini High contributed neutral plan, research and code reviews; narrow final
review6ee7ad011953 succeeded with no critical defect, no edits and no test execution.
Earlier larger reviewfa6b604cd0f9 timed out without a result; it is not counted as
successful verification.

All nine lifecycle/copied-world BDS runs stopped cleanly and removed owned
containers. Aggregate measured game-wall time is 279.18 seconds, excluding setup,
export, compilation, analysis and worker reviews. No new seed-search campaign,
GPU job, serving native rebuild or personal Sweep restart was started.

Remaining substantive algorithm work: an independently validated Bedrock biome
zoomer/cave-boundary rule, a general village/outpost rejection explanation tested
on held-out positives, and broader recall tests. Targeted exclusions do not solve
those problems. Browser QA remains explicitly deferred by the user.
