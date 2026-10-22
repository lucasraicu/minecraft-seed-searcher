# Predictor corrections: proposed execution plan

Status: APPROVED for execution by user “Go ahead” after the concrete plan and
Gemini High reviews were presented. Scope remains diagnostic-only as stated below.

## Objective

Improve the meaning and correctness of player-facing biome/structure locations
without fitting tests, silently changing personal-search rules, or rewriting old
catalog observations. Reuse saved BDS outputs; distinguish API semantics from game
world generation. Deliver audited coordinate adapters and a biome sampling verdict.

## Evidence

Saved BDS1.26.52.3/API2.10.0 cohort:330 Overworld Y63 points, current block lookup
292matches versus311 raw-quart matches after existing alias map. Initial snowy
256points:239 versus253.19 raw-quart differences in broadcohort include cave biomes,
6 old-growth spruce vs taiga mappings and1 savanna vs plains; rawquart is not a
universal fix. Vertical/local controls show genuine sameXYZ discrepancies.
Structure offsets: mineshaft and fortress(-8,-8), outpost(+8,+8) each9/9 in3seeds;
stronghold(-2,-2)8/9 with1 large mismatch. Trial-chamber and trail-ruins offsets
vary; no arbitrary radius makes them verified. Prior village27/28 and selected
cohort9/9 do not erase the known mismatch. Grouped temples, Endcity and camp remain
incompletely validated. EVIDENCE.json summarizes saved results.

## Order and architecture

1. Freeze portable regression fixtures from saved game reports and exact hashes,
   seed/build/settings/method/coordinate identities; preserve raw names/responses.
   Source: new fixtures under fixtures/bedrock-26.52/predictor-corrections/ and
   focused tests. Never fabricate or recategorize a recorded mismatch as a match.
2. Add explicit coordinate conventions in a new pure Python module
   src/seed_search/realm/structure_coordinates.py. Retain original predictor starts
   and distinguish candidate chunk, predicted reference and BDS locate reference.
   Implement exact deterministic adapters for outpost(+8,+8), mineshaft/fortress
   (-8,-8) under versioned conventions. Stronghold(-2,-2) stays diagnostic-only,
   with no production adapter; its large disagreement must remain unresolved.
   Trial chambers/trail ruins stay unresolved until source-derived orientation or
   piece rules are demonstrated. Keep raw Backend.structures and native search
   unchanged so existing admission, summary boundaries and hashes do not drift.
   A coordinate adapter is not a proof that a structure physically generated.
3. Resolve biome observation semantics before changing ss_biome or extraction.
   Compare saved sameXYZ BDS API observations with raw quart and existing block
   interpolation, explicitly including cave and boundary cases. Validate alias map
   against pinned game definitions: don't map old spruce to taiga simply to pass.
   New bounded diagnostic harness and isolated native helper outside serving
   binaries; preserve negative-coordinate floor division. If fresh BDS is needed:
   at most2 existing seeds,128XYZ points total,32structurecommands,2CPU/2GiB one
   container at a time,600s total,4GiB owned output. No seed-search jobs or broad
   new cohort. Add direct command / biome API / saved-world observations where
   available to distinguish API retrieval from generated data; unavailable APIs
   remain a capability gap, not a pass. Do not claim latest docs equal pinned API.
4. Only after semantic evidence: add an explicit versioned BDS-observation comparison
   mode if raw quart is its demonstrated contract. Leave existing biome predictor
   semantics intact until an independent generated-world oracle supports replacement.
   No nearest-name or majority-vote cave fallback. If no authoritative correction
   emerges, deliver a documented unresolved result rather than a guessed patch.
5. Document adapter effects and tests; any integration into catalog extraction is
   a new identity/extractor revision, rebuilt summaries/indexes/retention and new
   snapshot. Never reinterpret v1 geometry or overwrite immutable evidence. First
   slice exposes separate diagnostic coordinates only; do not change rankings or
   counts from shifted points. Estimated-spawn codec migration follows separately.

## Workers and boundaries

Two Gemini High read-only critiques: biome plan and coordinate/versioning plan.
Codex owns evidence extraction, analysis, integration and final validation. After
approval, independent isolated workers may own pure coordinate module/tests and
portable fixture validator/tests; never overlap native source files or run BDS.
Native helper and game verification are Codex-owned. No account/model changes or
permission bypass. Preserve dirty primary workspace and original SweepPID60144.

## Tests, acceptance and resource needs

- Full saved fixtures reproduced with hash/provenance checks; raw results retained.
- Exact source-backed offset matches evaluated separately from remote mismatches;
  zero tolerance, negative coordinates and boundary-crossing examples.
- Holdout BDS evidence not used to choose adapter constants; at least4 distinct
  controls per proposed adapter across2seeds if current data cannot serve holdout.
- Biome raw-quart/block diagnostics across all saved points, sameXYZ, multiY,
  boundaries/raretypes; raw and canonical names separate. No selected-cohort
  population-accuracy claim or treating failed/unloaded queries as mismatch.
- Existing realm/native parity checks for affected code, relevant catalog regressions
  if service/contracts change. No primary native rebuild/restart without a justified
  change and explicit isolated validation. No expensive performance campaign.
- User data, old artifacts, original Sweep/native binaries preserved. Catalog/Vite
  last-known PIDs22102/24886 no longer present at inspection; port availability
  checked before any restart. No need to restart them for this planning stage.

Main risks: BDS API may expose a different biome representation; minor build
compatibility remains unproved; locate matching is not physical generation;
coordinate shifts can cross borders and change counts if applied silently;
model/native source fingerprints affect both private search and catalog identity.

Relative complexity: fixture/convention layer moderate; biome root cause uncertain.
Planning/diagnosis completed. Both Gemini High critiques are reconciled in
REVIEW_RESOLUTION.md; detailed task JSON is adjacent. Independent fixed-position
discovery results are preserved in DISCOVERY_CONTROLS.json.

Estimated execution after concrete-plan approval: 1–2 hours for fixtures,
coordinate diagnostics and biome analysis, plus 30–60 minutes if bounded fresh
BDS controls are necessary. Root-cause resolution is uncertain; this estimate
covers a reproducible diagnostic verdict, not a promise to eliminate every error.
No main native binary rebuild, automatic global raw-quart replacement, public UI
claim changes or catalog recount is included. Any exact alias correction requires
pinned source-backed identity evidence. Unresolved findings remain regressions.
