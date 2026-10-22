# Bedrock correctness pass — completed

Subsequent validation: the separate
[generalization audit](../generalization-validation-2026-10-20/PLAN.md) is in
progress. New BDS-exact village references expose over-rejection in the current
preliminary check; a narrow exact-Y correction is proposed and awaiting approval.
Other structure omissions are being investigated. The completed historical pass
and its controls below do not certify the current predictor on all seeds.

The approved four-step pass is finished: persisted-data diagnosis, source-backed
biome and structure fixes, regression validation, and a verified refresh of the
same 200 catalog worlds. This is scoped evidence, not an all-seed accuracy or
physical-world census claim. Earlier REPORT/CONTINUATION_REPORT checkpoints are
historical and are superseded here.

## What changed

- Storage: the original missing-record campaign found 21 absent records and six
  repeat-marker cases. Disposable dirty/restore persistence made all original 54
  coordinates readable. The newer fresh/reload/retained-copy experiment established
  that runtime queries above encoded coverage use the last explicit section's top
  plane. New v3 sampling models that behavior; strict v1 stays unchanged and v2
  whole-array replay is explicitly historical. Missing/interior gaps remain unknown.
- Biomes: native MC_26_50 Overworld block sampling now uses the Bedrock 8-block grid
  and lower-32-bit jitter, retaining full-seed climate noise. The optimized C bridge
  uses the same selector. Raw quart classification and other model paths remain
  unchanged. Earlier source-backed old-growth spruce aliases are retained.
- Village/outpost checks: use the pinned engine's preliminary-height 3D biome
  checks, rather than a sky-level substitute. This rejects the two preserved bad
  starts and retains 51 positive controls. No slope or ancient-city veto was added.
- Stronghold: retain the independently confirmed static stronghold at (820,-1708)
  on seed -9103892851552028103. A remote /locate response was not absence proof.

Changed areas: vendor generator/cave/finders files, the biome fast path in
native/bridge.c, realm/bedrock_biome_storage.py, predictor_storage_probe.py, storage
verification documentation, a frozen 20-file game-evidence bundle, and 12 native
regression tests. Existing unrelated dirty edits are preserved.

## Verification and scope

The native tests match 8,320 frozen stored-data points and 330 direct BDS biome
observations, preserve 3,920 raw quart classifications, exercise 1,800 coordinate/
seed edge cases, and check 51 positive plus two negative structure controls.
Actual scalar/batch/grid C bridge calls are covered. Three disposable game runs
added 99 consistent API reads; all stopped cleanly and retained sources stayed
unchanged. These datasets have distinct purposes and must not be summed into a
population-accuracy estimate.

Focused final checks: **54 passed and 14 subtests**, 5.96 seconds. Expanded isolated
checks: 346 passed, one skipped, and one missing external review-fixture failure;
the affected test passed after preparing that fixture. No code failure remains.
The fresh isolated O3/CFFI runtime also matched the 8,320+330 biome cases.

The independent NumPy validator checked all **48,600 layouts**, all three border
sides and 81 declared anchors, every count/nearest/witness/completion field, and
five research rankings against observations. It also detected an intentionally
corrupted count. The first validator run used incorrect +/-1024 edge anchors;
that script error was corrected against frozen policy +/-976 before rerunning.
The catalog data was unchanged. All 18 indexed/exhaustive Top20 comparisons passed.
Measured serving calls were 2.51–6.27 seconds on this 200-world developer workload;
these are not production capacity or representative player-demand measurements.

## Refreshed catalog

Published generation:
`b48a7932a54a4e69b1ba28dc56f9ec5f973f9706399a2c483f7ecb6e9e8e66ae`.
Previous `ab4089...` and original `3d964...` remain available.

The same 200 seeds now contain 5.12 million sampled biome points and 516,214
predicted structure positions. Relative to the preceding generation, 210,114
biome labels changed, 750 village starts and 75 outpost starts were removed, and
other catalog structure inventories were unchanged. These are fresh native
predictions, not 5.12 million new game checks. All predecessor game-check rows
remain applicable; four overlays preserve their raw outcomes and report hashes,
with explicit predecessor bindings.

Independent validation took 238.70 seconds; extraction 599.26 seconds, preparation
326.89 seconds, live publication 226.81 seconds. The transition monitor observed
99 successful samples, old-to-new visibility, and zero errors. Final checks found
1,270 old immutable files unchanged and all 609 rehearsal immutable files identical
in the published root. Query/detail/status/product checks passed on 3001 and 5173.
The known Rare village control has 27 predicted starts and 27 exact BDS locate
matches; generated/exhaustive physical totals remain null.

Preview: http://127.0.0.1:5173/#catalog . Reload to select the new default generation;
old pinned links retain historical results. Backend PID44415/session78588 and Vite
PID44435/session40751 are intentionally running. Browser QA remains deferred.

## Workers and preserved runtime

Gemini High supplied plan and final critiques (22565162c182, 950de3cd29d3,
8fda04b14c64, plus preceding discriminator/structure reviews). Codex reconciled
unsupported recommendations against the pinned source and tests; see
ENGINE_RECONCILIATION.md. Coding workers fd7858918e87 and49d7341a4b93 timed out
without patches or checks. Codex implemented and independently tested the fixes.
No worker is still running; no quota/auth failure occurred. No commit, merge,
push, new seed discovery, GPU job or account switch was performed.

The primary personal server PID60144/start Oct16 and its loaded extension were
intentionally preserved. Its selected completed inspection result remains seed
-3336796033057908633, score336, run web-sweep-20261020-143452-e5161c27. Its running
engine has NOT been hot-updated. Fresh corrected extensions and sources live at:
`~/.local/share/antigravity-worker-mcp/predictor-engine-20261020/integrated-runtime/`.
Future native execution must use that verified runtime or a controlled rebuild;
new primary imports correctly reject the stale primary extension fingerprint.
No new personal search was launched to validate this pass.

## Remaining platform work

This closes the reported-error correction pass, not stages D–H. Remaining work
includes controlled personal-engine activation; estimated-spawn/richer preset,
Nether/stronghold evidence integration; wider game/player and scale/retention/
recovery validation; deferred browser QA; and hosting/accounts/payments. GPU and
specialized storage remain separately measured experiments. Public/billing flags
and currently gated products were not enabled.

Exact results: ENGINE_RESULTS.json. External raw checkpoints, builds and logs:
`~/.local/share/antigravity-worker-mcp/predictor-engine-20261020/`. Operational
refresh and independent verifier scripts are retained alongside this report.
