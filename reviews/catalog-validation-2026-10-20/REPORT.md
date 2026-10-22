# Bounded CPU catalog ingestion, retention and recovery validation

2026-10-20. This implements the user-approved [next validation stage](../phase3-reference-2026-10-20/NEXT_VALIDATION_PLAN.md),
following High critique617ed6a13c38. It does not implement the public website,
activate product flags, generate Bedrock worlds, use GPUs or construct a custom
database engine. The original personal search and two-world reference CLI remain
separate. No existing server was restarted and no commit/push was performed.

## Outcome

The actual 100-world run completed successfully. Every world completed all 23
declared features; there were no failed, partial, invalid or unattempted records.
It produced 24,300 layouts:81 anchors x3 border sides per world. All borders use
the same saved envelope, rather than three extraction passes.

The independent retention oracle agrees, partitioned merges agree, backup and
restore agree, and completed-world resume dispatched zero extraction commands.
The durable ingestion ledger remained byte-for-byte unchanged during that resume.
Full regression: **1,387 passed** in504.89s (8min24.89s), including113 catalog tests
and the existing personal-search regressions. There were no failures.

Raw run, including controls, receipts, observations, SQLite/artifacts, selected
memberships and per-request results:
`/Users/lucasraicu/.local/share/antigravity-worker-mcp/catalog-validation-20261020`.
Snapshot: `50d6935290393476a803247d5bdbe1f3efb90642b760d8fa65005fc43bdb8807`.
Portable measurements and provenance are in [measurements.json](measurements.json);
final checks and preservation evidence are in [verification.json](verification.json).

## Implementation

- `validation_contracts.py` freezes 100 distinct seeds before relevance evaluation:
  `seed_from_index(i,0xCA7A11)`, i=0..99. Controls pin source, binary, model, settings,
  registry, policy, requests and cumulative resource budgets. The preflight 10 and
  remaining 90 share one extraction allowance. No personal-search survivors select
  this population.
- `ingestion.py` saves explicit 100-world receipts and per-feature checkpoints;
  enforces root ownership, bounded retries and conservative crashed reservations;
  gates child execution until its process lease is durable; handles cancellation,
  verifies stale process identity before cleanup, and rejects corrupt completed
  checkpoints. Captured subprocess output has a bounded tail. Aggregate monitors
  fail closed when unavailable. Watchdogs are polling limits, not instantaneous
  resource guarantees or hostile-workload isolation.
- `retention.py` implements all 6,931 fixed objectives from the existing policy,
  including all 9 advertised biome families, landmark pairs, profiles, diversity,
  stable-hash sampling and explicit pins. Each world contributes its best eligible
  layout per objective before TopK; retained candidate lists are capacity-bounded.
  Policy/build identity travels with merge results. Overlapping world partitions
  choose the globally best anchor; contradictory ranks for the same layout fail.
  The reference still holds input layouts in memory and preserves all observations;
  this is a derived selection view, not a production streaming/eviction service.
- `view.py` verifies raw records once and freezes a defensive copy of layout facts.
  Repeated queries retain the existing Required/Preferred rules, same-anchor
  matching, version/evidence checks and unique-world ranking. `query.py` gained
  a shared internal ranking function; personal search was not changed.
- `evaluation.py` freezes 200 requests across 8 categories,3 borders and both
  supported modes before inspecting results. Counts, Required/Preferred and biome
  alternatives are represented. The request SHA256 is
  `2a9b0fdb379077907c6cd9d4b1bffe7df4cb4b3ab487c009977f5b5069d5958f`.
  This is a reproducible developer workload, not evidence of player demand.
- `retention_oracle.py` independently sorts all qualifying layouts, then deduplicates
  worlds and truncates. It does not call the production admission/rank/profile
  helpers. The actual corpus is checked against it; reduced policies must match
  the corresponding exact rank prefixes. `scripts/catalog_validate.py` supervises
  the experiment and publishes separate reference, selection and loss evidence.

Two actual High Gemini coding workers contributed isolated, nonoverlapping files:
ingestion 034b2efe8d9f and retention ad7e8899e946. Both exited0 with nonempty results,
no denied actions and passing declared checks 12/18. Codex reviewed both patches,
integrated only their owned files and corrected recovery, preflight, output,
checksum and merge issues with independent tests. [WORKERS.json](WORKERS.json)
records actual model/effort, usage, checks and patch hashes. No worker integration
was automatic, and neither authentication nor quota needed a workaround.

## Measurements

Actual machine: Intel Xeon W-2191B, 18 physical/36 logical CPUs, 64 GiB RAM.
One native CPU thread, serial engine; existing web server remained running.
There was no concurrent full pytest run during the timed experiment. This is
not a measurement on the two16-V100 fleet hosts. Identity is explicitly
`research:26.50`; predictions are not accepted as exact public game-build evidence.

| Stage | Measured seconds |
|---|---:|
| First 10 extraction receipts |24.39|
| All 100 extraction receipts, cumulative |245.26|
| Ingestion including resume validation/checkpoint collection |263.86|
| Derive 24,300 summaries |46.47|
| Publish and fully read/verify snapshot |39.82|
| Build immutable verified view |16.69|
| Default retention |10.64|
| Independent actual-corpus retention oracle |22.98|
| Reduced K1 / K2 retention |11.05 /10.91|
| Entire supervised experiment, including all queries/merge/restore |503.78|
| Additional saved-data zero-extraction resume |7.82|
| Additional fully verified snapshot reconstruction |16.96|
| Additional rebuilt immutable view |15.74|

The extra saved-data verification reserves and charges the original cumulative
30-minute job allowance; it does not obtain a fresh allowance. Its script refuses
any extraction dispatch. See `cumulative_validation_budget` in measurements.
The full experiment peaked at 2,400,821,248 polled aggregate-RSS bytes (~2.24GiB),
and ~150.8MB output including backup/checkpoints/reports: below 4 GiB/2 GiB caps.
The largest per-world receipt was2.65s. Receipt CPU includes interpreter startup
and process-monitor commands; native feature timings are reported separately.

The biome plane dominated native extraction:157.46s total wall for100 worlds,
median 1.57s, p95 1.63s. This is one Y63/stride64 lattice per world. Structure-start
inventories, checkpoint I/O and process/watchdog overhead are separate costs;
do not treat this workload as personal early-rejection throughput.

Default unpruned query medians were4.93ms for Origin and52.65ms for Recommended;
reference p95 values were7.70ms/124.53ms. The repeated default-retained pass had
a slower Recommended tail: p95 244.53ms and maximum1.57s. These are individual
local query samples, not concurrent-user service guarantees. Raw validation/view
construction costs above are excluded from warm-query times. Cached reference
results in later ablations are excluded from baseline timing statistics.

| Storage, one100-world catalog | Bytes |
|---|---:|
| Packed layout payloads only,364 bytes each |8,845,200|
| Observation JSON, uncompressed |50,656,342|
| Observation bundles, compressed |9,140,900|
| All101 artifacts, compressed |11,890,573|
| SQLite metadata, indexes and packed payloads |35,622,912|

SQLite plus compressed artifacts is about47.5MB here. Output is larger because it
also keeps checkpoints, evaluation results, selections and a validated backup.
This is not a production per-world capacity promise. We store structure-start
coordinates and sampled biome positions, not every generated block. Alternative
anchors/borders reuse those absolute facts; they add derived summaries.

## Retention quality and its limits

All natural-corpus results below use exactly the same frozen requests and query
semantics.34/200 requests had no reference answer; these are excluded from
preservation, recall and regret denominators. Top10 recall is the mean per-query
fraction of the reference's unique-world Top10 recovered, across 166 nonempty
reference requests. Nonempty-reference/empty-retained regret is defined as 1;
empty references have no regret observation.

| Natural100-world experiment | Retained worlds | Nonempty preserved | Mean Top10 recall | Mean normalized score regret |
|---|---:|---:|---:|---:|
| Production-default capacities |100|166/166|100%|0|
| Reduced K1, reference reservoir 5 |96|166/166|98.73%|0|
| Reduced K2, reference reservoir 5 |99|166/166|99.58%|0|

Defaults are **non-discriminating**: the 10,000-world reference reservoir alone
retains this entire 100-world population. Reduced policies prune only 4/1 worlds,
so their good local recall is weak evidence about aggressive pruning. No policy
was retuned on these requests, and no 95%/90% production target is certified.

Two separate synthetic checks exercise harder conditions:

1. 768 fabricated summary identities cover every one of 256 diversity cells with
  three worlds per cell and all three borders. At K1, all 6,931 objectives are
  oversubscribed; memberships match the independent global-sort oracle. Separate
  partial-coverage/multi-anchor/unsigned-seed/overlapping-partition cases agree.
2. 64 explicitly fabricated worlds share identical spatial observations, with 3
  anchors x3 borders each. Reduced K1/reservoir5 retains 6 worlds. Across 200
  requests, 184 references are nonempty, nonempty preservation is 100%, Top10 recall
  is 20%, and score regret remains 0 because the worlds have identical qualities.
  This exposes identity-recall loss even when the best score remains unchanged.
  These are constructed fixtures, not generated Minecraft worlds or demand data.

## Recovery and verification

The new tests include actual owned-process SIGKILL at a saved feature checkpoint
and immediately before/after SQLite publication. Recovery conservatively retains
crashed reservations, readers see the last complete generation, replay is
idempotent, and metadata plus artifacts restore independently. Supervisor-lifeline
death, failed durable lease writes, stale-PID refusal, output/RSS/time limits,
checkpoint corruption and explicit partial-population reporting are covered.
Existing artifact truncation/checksum/missing-file/revision/failed-write/concurrent
reader tests remain required. No live service or unrelated process is killed.
SIGKILL recovery tests do not establish hardware power-loss durability.

Contract validation passes:8 categories,23 features,3 sides,83,944 maximum fixed
retention slots and 364-byte payloads. Runtime and billing flags remain false.
The existing 220-case raw-coordinate query oracle remains in the regression suite.

## What this tells us to do next

1. Keep SQLite and checksummed compressed observations for the next pilot. The
   concrete storage problem is the current **flat snapshot manifest**: 4,891,473
   uncompressed bytes at 100 worlds, against a 16 MiB per-artifact limit. At similar
   density that cap would be reached around 340 worlds. Segment manifests and
   publication before a larger campaign; merely increasing this cap would retain
   whole-population validation/memory costs.
2. Build/measure metadata-only serving access and selective indexes over the
   packed summaries. Current queries scan layouts in Python, and initial raw
   verification takes seconds. The measurements support neither million-world
   serving nor a custom engine rewrite yet. Preserve provenance when caching.
3. Expand selective-quality evaluation only with a separately sized/approved
   population that meaningfully exceeds retention capacities, plus held-out player
   requests. The 100-world results cannot decide broad catalog usefulness alone.
4. Public API/UI, game-build acceptance, spawn integration, actual-game evidence,
   entitlement/payments and hosting remain separate implementation/acceptance
   stages. This stage changes none of those gates, pricing or feature parity.

Reproduce analysis without new seed work:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python reviews/catalog-validation-2026-10-20/analyze.py \
  /Users/lucasraicu/.local/share/antigravity-worker-mcp/catalog-validation-20261020
```

The separate validation CLI and source/build-matching resume instructions are in
[the catalog guide](../../src/seed_search/catalog/README.md). Starting a new campaign
requires its own appropriate scope; do not rerun extraction just to inspect this run.
