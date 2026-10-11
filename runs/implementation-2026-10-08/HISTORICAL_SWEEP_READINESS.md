# Optimized Bedrock search: finite sweep readiness

> **Superseded for the requested next sweep, 8 October 2026.** The user approved 2304/928 and requested a staged lower32/upper32 plan. The evidence below covers 3008/992 only. Audit documentation changes also invalidate its hashed artifact manifest. Do not reuse these start commands for the new target. Complete [AUDIT_IMPLEMENTATION_PLAN.md](AUDIT_IMPLEMENTATION_PLAN.md) and assemble new evidence first. The sweep remains unstarted.

> The subsequent [native test](SIMD_TEST_RESULTS.md) also found order-dependent Mineshaft predictions for cold seed -1 in the installed backend. P2 must repair MT initialization and add cold/warm worker tests before new readiness; the historical frozen regression alone does not cover this defect.

The large sweep remains unstarted. The current verified package is
`runs/filter-optimization/readiness.json`; it supersedes prior readiness identities.
Prior sources and readiness are retained in `runs/filter-optimization/prior-sources.zip`
and `prior-readiness.json`. Details: [FILTER_OPTIMIZATION.md](FILTER_OPTIMIZATION.md).

Bedrock26.52 maps to pinned MC_26_50. Full signed64-bit worlds, three landscape
types, exact3008/992 squares, required Fortress and Stronghold, optional Bastion,
flatness, ocean isolation and mountain criteria are unchanged. This is a finite
heuristic search with explicit deferred cases, not an exhaustive stronghold census.

## Implemented shortcuts

Stronghold and Fortress placement run before discovery terrain. A joint
eight-block center-window intersection filters nominal locations before
preliminary/coast/full-raster work; fixed island centers are checked again before
full landscape sampling. Unknown predictions are exported in
`stronghold-deferred.json` and `stronghold-deferred-seeds.txt`. They are **deferred**,
not proven absent. The default `defer_unpredicted` mode can miss worthy seeds because
the Stronghold iterator is incomplete and nomination envelopes are heuristic.
`config/review-all.yaml` disables that fast exclusion for a separate recovery run.
Accepted candidates still need matching-version website marker confirmation.

One native placement enumeration followed by full-seed viability replaces duplicate
raw/viable scans. A bounded128-entry per-process cache shares ONLY raw lower32-bit
MT layouts for eight tested families. Stronghold village iteration, Mineshaft,
Trial Chamber, biome, density and viability never share those raw keys. The seed
sequence still covers full64-bit numeric values. Random lower32 collisions are rare;
this cache is most useful for explicit high-bit sibling workloads, and no generic
speed improvement from it is claimed.

Necessary dry/gentle upper bounds inspect a small basin patch including all eight
allowed nearby floor proposals and gradient/kernel halo. Lazy mountain rays stop
after enough proven misses make75% impossible; unseen rays remain possible, with
a5000-point overhead budget. Survivors retain full-raster global connectivity and
the original criteria. Shared immutable raster calculations avoid repeated labels,
gradients and local ranges. Exact per-seed/stride cache and persisted maps remain.

Controlled four-negative-basin A/B: 30.72s →
1.39s, 189268 →
11016 native density columns. All four early failures also
fail the original full-raster/recenter criteria. Synthetic positive and nearby-floor
controls pass. Combined structure scan saves
40.88%
in the isolated four-seed test, with identical typed predictions.

## Verification and scope

112 tests pass. Supported editable native rebuild and dependency checks pass;
vendor source/license hashes are preserved. Frozen880 structure/159 coordinate
comparison remains874 unique typed correspondences, six visible disagreements,
zero reused starts; original height MAE1/max5. Independent20-seed checkpoint/resume
and worker-count comparison matches exact predictions, metrics, cache counts,
rejections and deterministic counters, excluding only timings/RSS/PIDs.

Common old/new centers have exact unchanged metrics and scores:
95 compared, 95 identical.
Fast exclusions and newly reached finite-budget nominees change candidate coverage;
this is not an unchanged-workload overall A/B speed claim. Fresh matching-version
UI checks re-confirm both required markers for two retained ocean-island controls,
including high-bit/negative-coordinate seed4294979641. Prior landscape/control
observations are preserved with their original scope/date and new checks identified
separately. No actual Minecraft generation evidence was invented. No real dry-basin
positive is established by this chosen sample.

## Measured workload

Twenty fixed input seeds, 96 scored locations;
345.58s total including two exports, 310.89s
analysis, 34.69s reports, 17.28s
effective per input. Individual worker mean80.79s,
range40.88–129.15s.
These are input costs, not time to find worthy seeds. Uninterrupted identical20-seed
cohorts take233.65s with8 workers
versus212.59s with12; all exact
results match. Twelve saves9.01% analysis
wall time in this one-trial comparison and is the current recommendation. Both use
reusable maps so report time is separate. No18-worker/global-optimality claim.
For2000 inputs, measured12-worker analysis plus amortized reports projects
**5.92h**; applying the interrupted8-worker pilot's full overhead per
input gives a conservative9.60h. A1.5× planning allowance
is8.87–14.40h, plus manual review.
Yield and throughput can vary; the chosen sample is small.

| Stage | Summed worker seconds | Share |
|---|---:|---:|
| discovery | 8.24 | 0.51% |
| structures | 13.97 | 0.87% |
| proxy | 5.88 | 0.36% |
| preliminary | 379.49 | 23.51% |
| coast | 767.40 | 47.54% |
| landscape | 435.03 | 26.95% |
| scoring | 4.25 | 0.26% |

Source/config/backend/evidence hashes gate the finite2000-input launch. The actual
command passes a positive dry run from `/tmp`, missing/stale/tampered readiness is
rejected, and no sweep directory has been created. Resume uses the original identity.

Start (unstarted):

```sh
/Users/lucasraicu/Downloads/minecraft-seed-searcher/.venv/bin/python -m seed_search --config /Users/lucasraicu/Downloads/minecraft-seed-searcher/runs/filter-optimization/config/sweep.yaml search --count 2000 --start-index 100 --workers 12 --readiness /Users/lucasraicu/Downloads/minecraft-seed-searcher/runs/filter-optimization/readiness.json --output /Users/lucasraicu/Downloads/minecraft-seed-searcher/runs/optimized-sweep-2000
```

Resume after interruption:

```sh
/Users/lucasraicu/Downloads/minecraft-seed-searcher/.venv/bin/python -m seed_search --config /Users/lucasraicu/Downloads/minecraft-seed-searcher/runs/filter-optimization/config/sweep.yaml resume --run /Users/lucasraicu/Downloads/minecraft-seed-searcher/runs/optimized-sweep-2000 --workers 12
```

Recovery uses the supplied review-all config and the saved deferred seed list in
a **new** bounded rank run; prediction/config changes cannot resume fast-mode
checkpoints. The CLI continues to require separately verified readiness for any
recovery workload over1000 inputs. Split review batches into at most1000 supplied
seeds rather than bypassing that gate.
