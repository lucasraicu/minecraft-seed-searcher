# Personal server adoption and framework throughput

Completed the explicitly requested restart and bounded comparison on2026-10-21.
No source/predictor/native-binary modification or large seed campaign. Benchmark
writes stayed in disposable external roots; the existing UI and catalog remain.

## Server adoption

Stopped exact old personal server60144 after verifying completed status and
capturing its saved state. New personal PID77988 serves3000 with auto-continue
disabled. System/status APIs and the5173 proxy select
`runs/dynamic-baseline-2048/native-corrected-openmp-2026-10-21`, SHA
`3fbb286e4f06a4726e3c1e7216a5aad4d30f2abc6b0bf7b97532bf085b372687`.
Read-only preview uses that build and34threads for the next sweep. Actual bounded
production-API benchmarks loaded the same extension and executed its OpenMP work.
The server's telemetry honestly says `selected_on_disk/loaded=false` for a new
child sweep until one is launched; no live personal sweep was started by restart.

Saved run `web-sweep-20261020-143452-e5161c27` remains selected/completed with one
scanned seed, candidate `-3336796033057908633`, score336. Both existing run files
retain their hashes. Catalog PID77098/workers77100/77101, snapshot18ca9deb…ba93,
and all2,494 existing catalog files remain unchanged. Both personal and catalog
API routes through5173 pass. Vite65292 was not restarted.

## Measured rates

Same iMac, V3 dynamic2048 strict personal policy, key2026101630,65536inputs/cohort,
offsets0/65536/131072,34OpenMP threads,16384batch, compact survivors, Top50.
Three counterbalanced paired trials per current comparison; warm-up4096. Rates
include production preflight, durable SQLite commits/drain/close and optional
handoff registration; interpreter startup and correctness checks are outside
timing. The kernel-only number excludes persistence. All measured screening
cohorts retained zero candidates: these measure predominantly rejected inputs,
not fully evaluated accepted-world throughput.

| Workload | Measured result |
| --- | --- |
| Current personal-only, first paired phase | Median61,875 input seeds/s; trial range61,388–72,495 |
| Same current search with catalog handoff registration | Median62,150 input seeds/s; range57,983–73,783 |
| Current personal kernel only | Median69,193 input seeds/s |
| Personal-only control in later active-load pairs | Median67,071 input seeds/s |
| Same search + handoff + one active catalog extractor + two cold catalog queries | Median60,914 input seeds/s |
| Paired active-work elapsed-time increase | 7.01%,7.51%,10.46%; median7.51% |
| Two cold Recommended queries over existing200-world copy, during each active trial | All six succeed,4.243–4.484s, under unchanged10s allowance |
| Full current public record, serial worker, two existing stored seeds | 7.770s total;3.885s/record average,0.257records/s |

**The catalog handoff alone has no clear slowdown in these short trials.** Its
paired elapsed ratios span0.983–1.059, with median0.996; a tiny apparent speedup
is noise, not an optimization. Initializing a new queue is included, and no
background extraction was triggered: each registration-only root has one
campaign, zero jobs, no staging and no published catalog. The registered public
sampling budget was2 for this probe, not a claim every personal seed is extracted.

Active trials synchronize on the real extraction child's settings file and two
busy query-worker leases, then execute the personal run. Actual extraction and
both query intervals overlap every timed personal run (~0.98–1.08s). Independent
processes perform public extraction/publication; they do not accidentally share
the personal process's GIL. Public extraction uses native/numeric threads1 and
nice+10; personal uses34, plus preparation/writing. Queries use two processes.
Cold query results report cache misses and match200worlds. Personal retained
semantic records, counters, completed ranges and coverage receipts are identical
within every pair; SQLite integrity and FULL synchronization pass.

Public records here contain23supported feature families,25,600Y63/stride64 biome
points and243anchor/border summaries. The two existing seeds were
`-9037391848063581383` and `8395430397596713336`. Extraction plus durable checkpoints
took2.995/2.967s; summaries, compression/indexing and publication took0.812/0.833s.
This is a CPU prediction-record cost, not Bedrock world generation or physical
verification. Two worlds do not establish a population-wide throughput guarantee.
The three overlap trials re-extracted one of these worlds into fresh roots.

## Historical personal-only comparison

Retained2026-10-16 evidence reports **107,428 input seeds/s** durable median and
121,698kernel median on the same nominal cohort/thread/batch/profile controls.
Current61,875 is an observed **42.4% lower rate**. That is a real historical gap,
but **it does not isolate catalog overhead**:

- Historical native flags included `-march=native -mavx2 -mfma -flto`; the restored
  current artifact uses portable O3 without those host-specific flags.
- The predictor was corrected after the historical measurement. Computational
  work and qualifying results can change; old/native result parity is not assumed.
- Historical timings call `persist_pipeline` directly; current production API
  includes build/source preflight and adapter construction. Both exclude process
  startup, but the boundary is not identical. Measurement date/load also differ.

No stale native/source guard was bypassed to rerun an old library against new
code. The valid isolation experiment is current personal-only versus the same
current code with handoff/active public work. That experiment finds small/no clear
registration cost and ~7–10.5% additional elapsed time during the measured bursts.
Next performance diagnosis should compare the corrected source with matched
historical compiler flags in isolation before assigning the old/new gap to a
specific cause. Such optimization/deployment was not performed by this task.

## Limits, failures and review

These are short warm-interpreter screening bursts, not sustained thermal/fleet
benchmarks. Different phase medians62k/67k show normal workload/order/load
variation; do not divide unrelated phase medians to claim precise overhead.
Use paired ratios. Filesystem caches were not flushed. No thermal/performance
warnings were recorded; `pmset` reported scheduler/speed limits100 and36available
logical CPUs at the final sample, not continuous frequency/throttle telemetry.
Sampled owned-process RSS peaks:175.6MB personal,123.2MB two-world catalog,
663.2MB combined;4GiB/512MiB/600s phase caps were not exceeded. Final successful
phase wall times were9.74s,8.07s and19.41s respectively. Setup time is separate.

Two harness failures are retained, not accepted results:

1. Initial personal benchmark omitted the required persisted compatibility report.
   Production preflight stopped it; no personal range was published. The harness
   now writes the existing real compatibility report before invoking the API.
2. Initial one-world overlap helper mistakenly retained a two-world drain limit.
   During concurrent registration, the bounded drain correctly consumed a second
   queued world in its disposable root, then the helper's expected-count assertion
   failed. One extra personal-cohort seed was fully extracted locally; no live
   catalog or personal UI run changed. Limit corrected to explicit manifest length,
   old logs/outputs preserved and fresh counterbalanced trials passed. Failed
   timings are excluded. This was a benchmark-helper error, not a production
   queue limit violation; the production worker honored the supplied cap2.

Gemini High review a8ac3588b4cc succeeded,exit0,denied[],no edits/tests. Codex
accepted compiler/work-unit warnings, fresh-root controls, queue-only proof,
bounded public budgets and actual overlap checks. Its deterministic saturation/
throttling claim was not accepted without telemetry; optional32thread tuning was
left outside this34thread comparison. Data isolation is not an OS sandbox.
No account/quota/permission bypass or model downgrade. No additional tests needed
for unchanged implementation; actual production-path benchmarks, exact pair
checks, runtime preflight and final API/data preservation provide verification.

The four-pillar/heap/storage explanation requested during this work is in
[ARCHITECTURE.md](ARCHITECTURE.md). Raw scripts, results, failure logs and resource
reports are bound by ARTIFACTS.json. No source commit/push/merge/reset/cleanup.
