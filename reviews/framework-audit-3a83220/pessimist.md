# Pessimist review of 3a83220

Reviewed the current source at `3a83220`, the preceding implementation push `84a83ba`, selected prior-audit leads, and current native artifacts. Production source was not changed. Findings distinguish reproduced integration defects from accuracy/performance limitations.

## Prioritized findings

### P1 — The Web server selects a stale native implementation and accepts it at launch

**Locations:** `src/seed_search/web/server.py:41–46,184–191,250–254`; `src/seed_search/realm/native_batch.py:75–95`.

The server prefers `runs/dynamic-baseline-2048/native-mansion-bound-2026-10-16` merely because its `identity.json` exists. Its startup preflight constructs `Prototype`, which checks the binary's own recorded digest and its OpenMP runtime, but does not compare the recorded native/vendor input hashes against the current policy implementation. The file being authentic to an old identity does not establish compatibility with the new score schedules or center weights.

The root reviewer independently reproduced successful construction followed by `RuntimeError: Native/direct dynamic record parity failure at anchor 0` for seed `456`, fixture `(0,0,-1)`, using the default directory. The current `runs/dynamic-baseline-2048/native` and packaged extension instead produce the current fixture score **479**. The default directory has **11** native/vendor input mismatches against this checkout; the nondefault current private build has **zero** recorded source-input mismatches.

**Impact:** Ordinary rejecting seeds can run without exposing the mismatch; the positive evidence path can fail only when a survivor is prepared. This is a deployment compatibility defect, not evidence that the newly rebuilt scorer's arithmetic is wrong.

**Action:** Select a current build, validate a semantic policy/build version or complete relevant input hashes before creating a run, and include an executable positive-path compatibility check. Preserve explicit historical builds only when executing their matching historical policy/code.

### P2 — Ordinary production v3 runs do not activate the blueprint's automatic Top-50 cutoff

**Locations:** `src/seed_search/realm/config.py:388–413`; `src/seed_search/realm/native_batch.py:555–558,581–583,724,747–751`; `src/seed_search/realm/cli.py:264–269`; `src/seed_search/web/server.py:184–191`; `MASTER_SEED_BLUEPRINT.md:169,245`.

`dynamic_v3_blueprint_config()` supplies no `search.top_k`. `run_native_scan()` defaults to `top_k=0` and resolves a missing config field to zero. Neither the ordinary CLI flags nor the Web launch command activate Top-K. The tracker and native pruning are implemented and accessible to explicit Python callers/configuration, but the current default product path does not use them.

The isolated `integration_probe.py` runs a known positive seed with the default Top-K setting and an explicitly empty Overworld palette, then checks for the tracker artifacts. See `integration_probe.json` for its completed run, saved candidate, and absent Top-50 artifacts.

**Impact:** The documented ratchet does not operate in an ordinary run; this matters once enough qualifying candidates exist. It cannot explain initial zero yield and should not be presented as the main acceleration before 50 candidates exist.

**Action:** Decide whether Top-50 is an active policy requirement or an opt-in feature; set the v3 default and persist/report the setting if active, otherwise correct the specification. Add an entry-point test that starts the same config/command the UI launches and observes the setting reaching the native pipeline.

### P2 — The nominal portable x86 build now requires AVX2 and FMA without runtime dispatch

**Locations:** `vendor/cubiomes-bedrock/noise.c:7–12,133,195–219,480–519,603–623`; `native/build.py:11,15–16`; `scripts/build_blueprint_batch.py:36–43,136–137`.

The architecture check enables `NOISE_USE_AVX2` for every x86-64 GCC/Clang build and marks normal noise entry points with `target("avx2,fma")`. It does not test CPU support or dispatch to a scalar implementation at runtime. The scalar branch is selected for other architectures, not for older x86 processors. As a result, the build advertised as portable, and a private build with the AVX2 option left off, still contain and call AVX2/FMA noise routines on x86.

**Impact:** An x86-64 CPU lacking those features can compile/install this code but execute unsupported instructions when sampling. This host supports the instructions; no unsupported-CPU crash was reproduced here. It is a source-established compatibility defect, not a local throughput or accuracy failure.

**Action:** Preserve scalar entry points and add guarded runtime dispatch, or make the minimum ISA explicit and enforce it before scanning. Ensure the build manifest reflects the actual ISA requirement; currently the optional build flag is not an effective scalar control.

### P2 — The latest push leaves positive-path regression expectations stale, and the broad parity claim exceeds the test

**Locations:** `tests/test_native_mansion_bound_and_recovery.py:56–82`; `tests/test_v3_optimizations_parity.py:1–9,96–138`; `tests/test_avx2_noise.py:27–37`.

The focused test invocation below completed with **30 passed / 4 failed in 29.52 seconds**. All four failures are recovery-test assertions at line 81 expecting the historical score **296**, while the current stored score is **311**. Earlier assertions in all four cases establish that missing/corrupt/stale/valid Top-K checkpoint handling preserved the leader. This is a stale expected-score defect; it does not reproduce the old recovery corruption.

The test called `test_v3_5000_seeds_sweep_and_zero_false_positives` verifies every retained native candidate, but when no candidates survive it evaluates only **8 of 5,000** inputs with Python. It cannot establish zero false negatives over all 5,000. The synthetic direct/replay path also consumes native evidence and does not independently validate world generation. The existing AVX test checks file hashes and four valid biome IDs; it never compares scalar and SIMD results.

**Action:** Update golden score baselines deliberately, retain the four recovery cases, and make parity claims match the checked population. Add held-out positive candidates and genuine scalar/SIMD and version-matched game-reference comparisons.

## Numerical control experiment: no observed classification regression

`build_noise_controls.py` builds two isolated libraries using identical current generator/biome code. One uses the pre-`84a83ba` scalar `noise.c`, with a trivial four-call compatibility wrapper; the other uses current SIMD `noise.c`. Both compile with `-ffp-contract=off`, so the scalar control does not silently fuse the original arithmetic. `compare_noise.py` uses fixed RNG seed `20261016`, 64 world seeds, coordinates within the audited Overworld domain, and the four blueprint Y planes.

| Comparison | Samples | Mismatches |
| --- | ---: | ---: |
| Final biome IDs | 131,072 | 0 |
| Mansion dark-forest prefilter | 131,072 | 0 |
| Raw double climate values, bit comparison | 98,304 | 65,778 |
| Same climate values converted to float32 | 98,304 | 0 |

Maximum observed absolute raw climate delta: **4.440892098500626e-16**. Evidence: `noise_comparison.json` and the reproducible control sources/scripts in this directory.

This shows the FMA rewrite does change double arithmetic; it does **not** demonstrate a changed biome or rejected valid candidate in the tested domain. It also does not prove equality to Bedrock. Native/Python parity can share the same altered generator implementation. The four-call `sampleDoublePerlin_4x()` wrapper contains four sequential calls in source; any speedup attributed to it requires measurement or generated-code evidence.

## Versioning and recovery assessment

The rebalance preserves `dynamic-envelope-2048-v3` while changing both score values and selected-center behavior. This weakens the human-readable revision label. However, do not report resumed-run score mixing as established: validation now rejects the previous v3 centroid dictionary (`config.py:460`), and computational/configuration identities guard normal resume (`capabilities.py:45–53`; `store.py:34–51,216–218`). The isolated probe records the old-config validation error.

A historical completed run can still display old-v3 results. Applying the current scorer to a saved chosen window cannot discover the newly optimal center because the old run retains only that window's evidence; rescoring is not reevaluation. Introduce a new score/selection revision and make the migration choice explicit: retain historical output, or reevaluate seeds with the new center policy.

The old corrupt/missing/stale Top-K JSON recovery bug and disabled-preflight initialization bug are fixed in the current source and passed their relevant positive-path assertions in the focused run. They should not be carried forward as open production findings.

## Remaining limits of a maximum-speed/maximum-accuracy claim

- Backend capabilities explicitly declare incomplete Stronghold recall and known Ancient City/Bastion fixture disagreements (`capabilities.py:19–21,31–35`). Internal scorer parity does not close those real-generation accuracy gaps.
- Center selection checks constrained centroid representatives; it does not prove a global maximum over all 8-block centers for hub/scenic/optional bonuses (`native/blueprint_dynamic.inc:1125–1138,1168–1191`). This is an objective/coverage limitation already acknowledged by the blueprint, not an automatically demonstrated violation of its defined representative rule.
- The v3 upper bounds remain conservative after this rebalance: core cap 650; remaining categories total 600; later 335 and 135 bounds correspond to optional+spatial and spatial respectively. No arithmetic underestimate was found in this review.
- A Top-K cutoff based only on score assumes homogeneous eligibility tiers. The tracker itself orders tier before score; mixed-tier restoration needs an explicit eligibility rule before reusing the root score as a native cutoff. This is an API invariant concern, not a reproduced mixed-tier fresh-v3 failure.
- Root review reproduced the separate strided-sequence domain issue: scalar, list, and vector generators repeat seed `12345` at indexes `0` and `2**32`, and direct `run_native_scan()` accepts and commits an input starting at `2**32`. See `strided-wrap.json` and the root synthesis. `scripts/shard_campaign.py` applies the narrower domain, but direct entry points require the same protection to avoid duplicate coverage.

## Reproducing the numerical controls

The builder is saved at `reviews/framework-audit-3a83220/build_noise_controls.py`; it records the exact Clang flags, retrieves scalar `noise.c` from commit `15ab3ad`, and builds both controls without changing production files. On this macOS host, run from the repository root:

```sh
.venv/bin/python reviews/framework-audit-3a83220/build_noise_controls.py
.venv/bin/python reviews/framework-audit-3a83220/compare_noise.py
```

## Focused verification command

```sh
.venv/bin/python -m pytest -q tests/test_dynamic_v3_2048.py tests/test_v3_optimizations_parity.py tests/test_native_mansion_bound_and_recovery.py tests/test_audit_remediations_a1_a10.py
```

Full-suite, Web-build, CPU-throughput, and additional independent-survivor results are owned by the root review and should be consolidated there. No production source was edited and no task-complete notification was sent by this role.
