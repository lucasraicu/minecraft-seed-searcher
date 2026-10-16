# Blueprint-preserving kernel optimization

The final implementation only reuses the raw Mansion positions already enumerated by `nb_dynamic_raw_preflight`, instead of generating them a second time. The isolated change is in [implemented.patch](implemented.patch). Existing uncommitted changes were preserved.

## Blueprint compatibility

The first enumeration covers the entire inclusive macro-envelope `[-2000,1999]^2`. The Nether-derived `feasible` box is a subset of this envelope. Filtering the previously enumerated Mansion positions through the same `inside` predicate therefore produces the same count as repeating the placement scan. The configured goal is still enforced, including goals above one. No biome viability is inferred from a raw placement.

Hard floors, targets, deficit budgets, filter order, center lattice, half-open borders, scoring, later inventories, and retained evidence are unchanged. No SIMD, floating-point, allocation, or worker-layout changes were made.

## Experiments not adopted

A corrected Mansion/Nether center intersection was implemented in an isolated experiment. It intersects center intervals, retains all Mansion alternatives, snaps to the eight-block lattice, then expands back to structure positions. It affects only raw preflight checks. Eleven geometry tests passed, including 100 randomized cases checked against every legal center, boundary cases, and the center-800/Mansion-0/structure-1600 counterexample. The experimental source and tests are retained here; that code is not in production source.

The proposed Ancient City / Trial Chamber / Village / Outpost / Mansion ordering was also compared. Neither the tighter bounds nor reordering established a compelling performance improvement, so both were removed from the final implementation. AVX sampling and blanket alignment were not implemented.

## Validation

- Final native CPU-native + LTO OpenMP build compiled successfully; its input hashes match the final repository sources. See [final-build-identity.json](final-build-identity.json).
- Baseline and final implementation matched decision fingerprints and retained-record fingerprints on 300,000 tuning inputs and a disjoint 600,000-input held-out cohort, repeated three times per arm.
- Both v1 and v2 matched full semantic records on 256 real inputs and three synthetic late-stage fixtures, including positive fixtures. Random-cohort retained counts are recorded in the JSON; empty retained sets are not evidence of real positive-seed coverage.
- Final targeted tests: **85 passed in 27.66 seconds**, covering dynamic baseline, v2 scoring, and remaining-audit regressions. See [final-tests.log](final-tests.log).

## Measurements and limits

[Reuse measurements](reuse-results.json): held-out median native throughput was approximately 228,042 inputs/s for the baseline and 230,125 inputs/s for reuse (about +0.9%). This is not a reliable speedup claim: another pytest process and compiler activity were observed during measurement. The first experiment results are in [benchmark-results.json](benchmark-results.json).

All measurements used private native builds with matching CPU-native/LTO/OpenMP flags, 34 threads, batches of 16,384, and no PGO. They are kernel measurements, not durable pipeline measurements. No 1.3–1.6x or 300k–350k seeds/s claim is justified.

The final tested private build is `runs/kernel-preflight-2026-10-15/reuse`. Packaged and default production binaries were not replaced; source changes take effect on rebuild, or when this private build is explicitly selected with `--native-build`. No running search was restarted.
