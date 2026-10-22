# Restart and bounded framework comparison

User explicitly authorized restarting the personal server to adopt restored
OpenMP, then measuring the new framework against old personal-only search.
This is operational verification/benchmarking, with no predictor/source change,
GPU work, billing activation, live catalog publication or large seed campaign.

Restart completed: old60144 stopped after proving completed status; new77988
selects native-corrected-openmp-2026-10-21. Saved personal run
web-sweep-20261020-143452-e5161c27 and seed -3336796033057908633/score336 persist,
two existing run files hash unchanged. No auto-continue. Catalog77098 and Vite
65292 remain. Runtime telemetry says selected_on_disk/loaded=false until a job
uses the extension: do not call that proof a sweep already ran. Bounded benchmarks
below use that exact selected artifact and verify actual OpenMP team/work results.

Historical evidence: native-refinement-2026-10-16/benchmark.json, same host,
V3 dynamic2048 profile, run_key2026101630, cohorts65536 at offsets0/65536/131072,
34threads, batch16384, survivors/max_misses0, Top50, full durable receipts.
Median107428 input seeds/s (kernel121698 with refinement), zero survivors.
Historical artifact used -march=native/-mavx2/-mfma/-flto, while restored artifact
is portable O3. Predictor correctness changed. Date/load/compiler/code differences
mean old-vs-current rates are observed historical differences, NOT pure catalog
overhead or semantic parity. Do not bypass stale-native/source checks to rerun old
libraries in current code. No fabricated portability/accuracy proof.

Measure current, sequential bounded phases on this iMac:

1. Reproduce historical cohort/control with current corrected artifact: warm4096,
   3 kernel trials65536, refinement enabled, and3 durable personal trials. Fresh
   external outputs, exact committed coverage/integrity/retention receipt checks.
2. Pair current personal CLI/pipeline with and without opt-in handoff registration
   using identical config/cohort34threads/batch16384. Counterbalance3pairs, include
   actual registration I/O in caller wall time and also report pipeline-only time.
   Verify full retained semantic results/counts match. Descriptor/queue only;
   personal start does NOT run extraction. Keep roots separate/nonnested.
3. Measure full catalog extraction/publication on two already studied catalog
   seeds into a fresh disposable root, one native/numeric thread, nice+10,
   <=120s/world, <=300s total, <=4GiB RSS, <=512MiB output. No live catalog changes.
   Record extract/checkpoint/summary/publication wall cost, complete23features,
   25600biome samples and243layouts/world. This is catalog records/s, not scanned
   personal candidates/s. No population-wide extrapolation from two worlds.
4. If phases fit <=600s overall, run bounded personal trials during a known active
   catalog extraction (and separately cold queries if practical). Synchronize
   actual active work; do not measure mere process startup as active load. Report
   overlap, repetitions/variability, CPU/RSS and identical personal results.
   Short overlapping trials are diagnostic, not a sustained fleet/load SLA.

Reuse existing sources and scripts/helpers where applicable. No server benchmark
launch through UI; personal saved run stays selected. All benchmark writes outside
primary runs/live catalog. One benchmark controller owns only its children; cap
each native/personal child120s, total600s, aggregate4GiB, output512MiB. No building,
reset/stash/clean/merge/commit/push, account switch or deadline weakening.

Codex owns measurement and interpretation. One Gemini High read-only critique
checks measurement design/confounds; no overlapping coding agents needed. This
explicitly requested benchmark/restart requires no new implementation approval.
Report actual medians/ranges, exact source/build/config identities and pending
work honestly. Update handoff, verify saved run/catalog identity and API/proxy
again, then final-task notification only when this requested work is complete.

## High critique reconciliation

Gemini a8ac3588b4cc succeeded with explicit High,exit0,denied[],read-only/no tests.
Accept historical compiler/correctness confounds and distinct work-unit warnings;
exact same-current-code paired tests isolate registration cost instead. Verify
queue jobs remain unleased/no staging after registration-only trials. Fresh roots
for every trial prevent reused results without deleting evidence; OS filesystem
caches remain unflushed, counterbalancing reduces but cannot eliminate bias.
Lower public world cap to60s and total120s for the two-world probe, retaining the
600s benchmark budget. Explicitly report actual overlap and one-thread public
worker vs34-thread personal, plus writer/preparer costs. No OS sandbox is claimed.
Reject deterministic saturation/throttling assertions:35compute threads alone
do not prove saturation or thermal throttling on36logical CPUs. Capture available
thermal/load diagnostics; do not invent throttling telemetry. A32-thread sweep
comparison is optional future tuning, not necessary to answer the current34-thread
configuration. No performance changes or arbitrary deadline loosening authorized.
