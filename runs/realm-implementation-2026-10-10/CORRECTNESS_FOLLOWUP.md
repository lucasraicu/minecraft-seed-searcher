# Correctness follow-up — 10 October 2026

The full implementation goal remains unfinished. This batch changes source/tests and preserves prior candidate databases, benchmark outputs and historical exports. It does not start another seed benchmark or generate a BDS world.

## Implemented and covered in focused regressions

- V1 closed-wide-lake border error reproduced before fixing. Missing opposite shores now prevent complete-fit claims; measured overflow and lower-bound expansion remain visible. Local branches beyond ray reach retain uncertainty instead of certifying the truncated local belt.
- Missing/failed/unsupported provider rasters refresh, preventing an additional stale in-memory cache layer. Deterministic native predictions retain their exact-coordinate reuse.
- BDS budgets use atomic SQLite reservations, unique attempt numbers and no write lock held during extraction. Competing connections cannot exceed the cap. Interrupted reservations remain consumed; same-key in-flight dedup is still open.
- Calibration compares stable known actual cells within requested half-open bounds and sample lattice. Tile overscan, missing water/ground, saved-mask uncertainty and nonfinite predictions do not become comparison evidence. Verification/raster interpretation hashes are recorded in observation identity.
- Memory budgets reject invalid/nonfinite/negative settings before checkpoint mutation. Unavailable monitoring stops dispatch and drains submitted batches. Wrong-seed worker results cannot commit coverage; their leases remain retryable.
- Shared score policy is used in prediction, actual CLI and generation-free rescore. Nested actual and predicted channels remain separate. Verified ranking requires complete geometry/footprint and verified evidence for positively weighted components. Actual raster biome fit is explicitly passed with its provenance; legacy copied prediction fits cannot be resurrected from a status change.
- Explicit manual cave checks return failure artifacts, preserve initial positives through failed/missing refinements and refine bounded uncertain neighborhoods. No automatic cave invocation or score effect was added.

## Evidence

Combined Realm regression before the final actual-biome edge correction: **145 passed in 7.74 seconds** (`correctness-followup-tests.log`). Subsequent focused scoring regression: **51 passed in 1.45 seconds**; final cave overlap regression: **8 passed in 0.11 seconds**. The full final-source regression passed **290 tests in 106.68 seconds**, recorded in `correctness-followup-full-tests.log` (process exit 0). All pinned source/test hashes were rechecked after it finished. `correctness-followup-manifest.json` pins the batch source/test files.

These are correctness controls, not a new scanner throughput measurement or proof of whole-region Bedrock generation. The most recent measured baseline rates remain 16.876 seeds/s at one worker and 155.375 at 30 on matched 1,000-input runs; 204.936 at 30 on 10,000 inputs. The earlier 100,000-input rate predates the reporting/postprocessing fixes.

## Remaining

The maintained FIX_BACKLOG.md remains the authoritative remaining-work list: complete native/custom provider task identity, interrupted rescore/export revision handling, discovery/surface-biome recovery and uncertainty, stronger mountain controls, verification backlog/cleanup/full halo planning, natural-ground/water semantics, authoritative required structures and final Nether generation, complete V1/V2 actual controls and population calibration. No exact Realm or final goal-completion claim is made.
