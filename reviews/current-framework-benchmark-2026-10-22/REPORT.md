# Current framework benchmark — October 22, 2026

The current personal pipeline screened **69,058 seeds/sec** at the median while
one full current catalog worker and two real query streams were active, versus
**75,666 seeds/sec** in its paired personal-only controls. Median paired elapsed
increase was **9.70%** (range7.14–11.43%); median paired throughput reduction8.84%.
These are short bounded measurements on this iMac, not a sustained fleet rate.

## Results and controls

Intel Xeon W-2191B,18physical/36logical CPUs,64GiB RAM;34OpenMP threads plus pipeline
preparation/writing, batch16384, current dynamic2048 strict policy, compact survivor
retention, Top50/100candidate capacity. Current native artifact SHA
`3fbb286e4f06a4726e3c1e7216a5aad4d30f2abc6b0bf7b97532bf085b372687`.
Catalog policy `1b3ff7b9cd1897444ff3747825c7f1ac6eba4ccbcc544b2a0f6ff23a39835e9b`;
registry `c65202c6f9f3da17be52d095308f4bd3748e6b3b7caf15d499f3588a717eb707`.

| Measurement | Median / observed range |
|---|---|
| Personal-only controls in active-load phase |75,666seeds/sec;74,016–75,756 |
| Same personal pipeline + registration + current worker +2queries |69,058seeds/sec;67,908–69,085 |
| Paired active-work elapsed increase |9.70%;7.14–11.43% |
| Personal-only in separate registration phase |72,028seeds/sec;69,165–75,742 |
| Registration-only paired elapsed increase |2.30%;−1.57–4.17% |
| Native kernel, excluding persistence/preflight |81,517seeds/sec |
| Full current public worker,3active one-world replays |35.50s/world;34.51–35.66s |
| Six simultaneous-load query responses, all result-cache misses |5.51–5.69s;all pass10s allowance |

Three fixed262144-input cohorts, key2026101630 and offsets0/262144/524288, were
replayed in three counterbalanced pairs per comparison. Each pair uses identical
current code, native artifact, seed sequence, policy and output semantics. Warmup
4096; interpreter startup and post-run correctness checks excluded. Durable timing
includes build/source preflight, registration when enabled, actual OpenMP work,
SQLite writes, drain and close. Native kernel trials exclude that overhead.
The larger cohorts differ from Oct21's65536; today's higher screening rate is not
proof of an optimization. Compare within paired current-code trials.

One predicted survivor occurred in cohort1; cohorts0/2 retained none. The earlier
progress statement that all cohorts rejected everything was premature and is
corrected here. Semantic retained records/counts/ranges matched across all pairs;
all96per-batch decision receipts matched exactly. SQLite integrity/FULLsync pass.
All12personal runs persist100candidate capacity. The heap never filled, so these
measurements do not establish full-reserve pruning/retention cost or winner-heavy
throughput. The one predicted survivor retains declared stronghold coverage limits;
it is not independently game-certified or adopted into the live personal run.

For active comparisons, the worker started from a fresh private root and re-extracted
an existing catalog seed through configured protocol2: pinned spawn, Realm/native
checks, biome refinement/height planes, v3 extension/summaries, product evaluation,
7543objective2Kretention and immutable publication. No cached observation replaced
extraction. Source/config/registry pins exactly match current production.
Each active trial's extraction interval and both actual HTTP request intervals
cover100% of the personal timing interval. All six HTTP requests have distinct
payloads and report result-cache misses; they use the actual222-world current
snapshot on the existing public server. OS filesystem caches were not flushed.

The personal handoff points to a distinct unconfigured private queue (cap2), while
an explicit private worker performs the active extraction. This avoids starting an
additional automatic supervisor during a bounded test. It measures registration
plus real current worker/query contention; it does not benchmark automatic
supervisor startup/election/retry lifecycle. Registration-only queues have zero
jobs, staging areas or published worlds. The live automation remains paused.

## Why personal screening slows modestly

1. **The catalog is a separate, bounded consumer.** Personal launch registers a
   descriptor/independent sample before personal qualification; it does not call
   full extraction for every input. A separate worker drains a finite queue under
   its own sample, memory and time budgets. The nominal production cap is100sampled
   worlds per campaign and600seconds; the benchmark uses2registration samples.
   Queue growth is bounded. This architecture protects personal throughput by
   limiting public intake, not by processing every personal seed at catalog depth.
2. **Personal screening still rejects almost everything cheaply.** It uses native
   batched OpenMP and early strict gates, persisting compact range/decision receipts
   for rejected inputs. Only one of786432distinct inputs produced a retained
   predicted candidate. The catalog's full observations are a different work unit.
3. **One extracted world supports many views.**56Overworld biome choices and groups
   classify shared biome IDs; they are not56independent world scans. Coordinates
   and observations are shared across borders, anchors and the four pillars.
   The additional height extension in these worlds was3200points and~0.22seconds;
   v3 summarization was~6–7seconds. Rank-list capacities do not multiply raw seed
   screening by7543, and2Kretention doubles maximum membership capacity rather than
   repeating every seed's native prediction.
4. **The active public worker uses one native/numeric thread.** The actual settings
   prove its extraction child runs at nice10; personal screening uses34OpenMP
   threads. That limits contention. The benchmark measured its cost rather than
   assuming spare physical cores: this machine has18physical,36logical CPUs.

Relevant implementation: [handoff](../../src/seed_search/catalog/bridge.py),
[personal launch](../../src/seed_search/realm/native_batch.py),
[bounded worker](../../src/seed_search/catalog/automation.py),
[extraction](../../src/seed_search/catalog/harvest_native.py),
[extra height evidence](../../src/seed_search/catalog/biome_extension.py),
[retention capacities](../../src/seed_search/catalog/retention.py).

## The catalog itself has become more expensive

Current full-record work is **about35.5seconds/world** in these active trials,
roughly0.028worlds/sec per serial worker. It is not69,000complete records/sec.
That is materially more work than the Oct21 legacy protocol1 probe's3.885seconds
per record: it now includes~102500Overworld biome samples,400Nether samples,
31feature-family coverage entries,3200extra height points,246anchor/border summaries,
Realm/spawn/refinement work and current retention/publication. The old probe had
25600Y63biome points,23families and243layouts. This difference cannot be attributed
solely to adding biome names, the latest two variants, or2Kreserves.

A two-world serial diagnostic also completed in69.73seconds (~34.86s/world).
It accidentally applied nice10 to the parent as well as the extraction child,
causing that child's actual nice19. The scheduling mismatch was corrected before
all active trials (whose settings prove production nice10). Preserve the serial
result as a diagnostic; the main current-cost figure above uses the correctly
scheduled active trials. Both code variants and raw settings are retained.

Consequently the public catalog grows much more slowly than personal screening.
The queue/budget may pause or defer intake; the design does not promise to ingest
all screened seeds. New-record publication into a1–2world private catalog also does
not establish incremental publication cost against222worlds or long history.

## Preservation, resources and review

Execution completed in228.31of600seconds cumulatively, peak sampled owned RSS
840790016bytes (<4GiB),~65.5MB new external output (<1GiB). Five existing-world
replays, no new BDS world/game launch or unbounded search. Each world fits90seconds.
Owned RSS excludes the already-running public server/query processes; those stayed
running and their actual HTTP work is measured separately. Thermal diagnostics at
capture report speed/scheduler limits100 and no recorded thermal warning; this is
not continuous thermal/frequency instrumentation.

[Preservation](PRESERVATION.json) verifies208source/build/state files,6129immutable
current-catalog files,199protected personal/checkpoint/native files, exact selected
personal run and service identities. Personal91321,public22035,Vite17880 preserved.
Live snapshot/configuration/control unchanged; public consumed0,paused,no jobs.
No source/native/frontend changes, service restart, commit, merge or push occurred.

Gemini High `f43a4356b66c` independently critiqued the benchmark; exit0,denied[],
no edits/tests. [Reconciliation](REVIEW_RECONCILIATION.md) accepts overlap, survivor,
cache and paired-ratio controls and rejects unsupported saturation/starvation claims.
Codex reviewed the harness, actual results, metadata, SQLite receipts and hashes.
No worker remains active or quota/authentication pause occurred.

Evidence: [summary](SUMMARY.json),[personal trials](personal-results.json),
[active trials](active-results.json),[receipt audit](RECEIPT_AUDIT.json),
[resources](RESOURCES.json),[artifact map](ARTIFACTS.json). Raw isolated outputs stay
in `/Users/lucasraicu/.local/share/antigravity-worker-mcp/current-framework-benchmark-20261022`.
These are short fixed-cohort comparisons, not sustained thermal, fleet, full-heap,
public-scale or universal seed-population throughput guarantees.
