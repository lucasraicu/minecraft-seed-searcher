# Framework corrections — October 16, 2026

Implements the actionable source and integration corrections from the [five-role audit](../framework-audit-3a83220/REPORT.md). Scoring points, hard floors and production centroid weights are unchanged. Expensive world-generation verification remains a separate finalist operation.

## Changes

- **Native compatibility:** both generator extensions embed a fingerprint of the C/header/vendor inputs. Private builds additionally require a complete matching input manifest and matching binary/runtime digests. Web default selection chooses a compatible build, preferring `runs/dynamic-baseline-2048/native-fixed-2026-10-16`. Explicit overrides fail rather than silently substituting another build. This rejects the earlier stale web artifact before scanning or record construction.
- **Seed coverage:** shared range validation enforces the 32-bit upper-sibling domain for strided streams in scalar/vector generators, native/Python entry points and aggregate completed coverage. Permutation streams retain their full64 domain. An empty range at the domain's exclusive end remains legal.
- **Top-50:** active v3 configuration enables `search.top_k=50`; the standard CLI/web run policy reaches the native pipeline without an extra flag. Explicit Python `top_k=0` disables it. Capacity is retained in pipeline state, cannot change on resume, and is preserved when rebuilding the tracker after rescore. Tracker updates remain downstream of SQLite commits.
- **Portable noise:** AVX2/FMA noise is compiled only when the corresponding compiler feature macros are enabled. Ordinary builds retain scalar code; the existing explicit host/AVX2 options remain available. This is compile-time portability, not runtime dispatch inside an AVX2-specific binary. Vendor patch hashes were updated.
- **Tests:** replaced stale 296/482 golden values with 311/479; serial package tests request one thread; the legacy web machine-contract test explicitly uses its v2 profile and targets. Web tests build a source-compatible fixture instead of depending on an untracked old local binary. Parity-test descriptions now match retained-candidate and sampled-reject coverage.
- **Measurement:** the v3 throughput script reports median timing, actual recorded build flags, labels its historical constants as unpaired references, and distinguishes the full-retention stage profile from compact scanning.
- **Finalist centers:** `scripts/refine_candidate_centers.py` independently regenerates complete macro evidence and evaluates every eligible center on a 16-block grid (15,129 possible centers) or an explicitly selected 8-block grid (60,025 possible centers). It uses the existing complete score and tie breaks. Required counts use vectorized exact half-open containment with bounded temporary arrays. Native replay evidence is rejected because it contains only the previously selected window. The original and refined records retain distinct provenance; a recommended source avoids silently preferring a worse result when the grid has a different alignment scope.

The main native sweep continues to use centroid representatives. Exhaustive refinement is deliberately a bounded operation on one finalist seed, preserving the fast rejection path and existing sweep identities.

## Rebuild and use

```sh
.venv/bin/python native/build.py
.venv/bin/python native/blueprint_build.py
.venv/bin/python scripts/build_blueprint_batch.py \
  --output runs/dynamic-baseline-2048/native-fixed-2026-10-16 \
  --openmp-prefix runs/master-implementation-2026-10-10/openmp/install \
  --cpu-native --avx2 --lto

.venv/bin/python scripts/refine_candidate_centers.py --seed <seed> \
  --config <run>/policy.yaml --grid-step 16 --output <fresh-result>.json
```

Supply the installed OpenMP prefix for the target host. Compiled extensions are local artifacts, not portable Git deliverables. Restart the web server to load the new source and build selection. Saved checkpoints still enforce their original computation identity; an old run is not silently migrated into a new algorithm.

## Verification

The synthetic full-floor center regression recovers `(32,0)`, **105 points**, where centroid representatives score **90**. The known natural seed `-3336796033057908633`, with an explicitly **custom empty Overworld palette**, remains at `(-480,0)`, **311 points**, in the 16-grid comparison. This is not a complete-default-blueprint survivor or a BDS verification. Its independent output and selection provenance are in `refined-natural-final.json`.

Compiler preprocessing confirms that `-mno-avx2 -mno-fma` selects scalar noise, and explicit `-mavx2 -mfma` selects the optimized branch (`isa-check.json`). The rebuilt web-selected OpenMP engine passes source checks and the positive 479-point fixture.

The frontend build and all **13** JavaScript contract checks passed. The full Python run completed **1,207 passing tests** with one failure in **579.93 seconds**: the new shared range guard rejected the correct invalid input but changed an existing exception-message contract. The `full64 range` wording was restored, and that exact test subsequently passed (`range-contract.log` and `failed-rechecks.log`). The final focused run passed **46 tests**, including the source guards, natural-positive recovery, legacy web machine contract, new seed-domain merge test and finalist-center regressions (`final-regressions.log`). Three additional focused guards passed (`guards.log`).

There are **1,209 currently collected test cases**, all covered across the full run and focused rechecks, including the one new merge case added after the full run collected its tests. There is no remaining known test failure. This report does not describe the original full invocation as an all-green run; its original log is retained in `pytest.log`.

A final **31-test** run covering the new framework guards, Top-K integration and scalar/vector seed generation also passed (`final-guards.log`).

The rebuilt web-selected OpenMP engine returned identical natural-positive centers, scores and components at **1, 4 and 34 threads** (`positive-final.json`). This positive case uses the explicitly custom empty Overworld palette described above.

The separate [weight investigation](../../CENTER_WEIGHT_RESEARCH.md) tested 27 settings plus repeated controls in four cases. It leaves production weights unchanged and records proposed calibration work. The implementation initially remained local at the user's request. The user subsequently authorized committing and pushing these completed changes while the separate read-only Qwen audit continues.

## Remaining empirical questions

The score remains a preference model. No new player-calibrated weights, complete stronghold recall, actual structure footprints, guaranteed portal rooms, buildable hub geometry or resource replenishment claim is introduced. Those require held-out player comparisons and version-matched generated-world evidence. The exhaustive search is exact for its declared predictor grid and score; it does not establish actual game-world optimality.
