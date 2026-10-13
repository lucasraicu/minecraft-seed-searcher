# Master Blueprint: measured performance and search planning

Measured 2026-10-12 on this repository's Intel Xeon W-2191B host: 18 physical cores, 36 logical CPUs, 64 GiB RAM. The active contract is `master_seed_blueprint_v1`, target Bedrock 26.52 / BDS 1.26.52.3, pinned predictor MC_26_50. [Feasibility analysis](BLUEPRINT_FEASIBILITY_ANALYSIS.md) covers the mathematical constraints and playability; [engineering audit](ENGINE_AUDIT_RESULTS.md) covers source changes and remaining model limitations.

**Result:** the production baseline measured **1,238.229493 input seeds/second** at 30 processes with one native thread each. This includes process startup, all discovered Stronghold anchors, applicable count/biome checks, IPC and SQLite persistence. It excludes coastal terrain and actual Bedrock generation. No full blueprint survivor was found in **30,000 distinct full64 inputs**, so full-blueprint success probability and verified-world completion time remain unknown. The blueprint's claimed rarity and leaderboard ETA are not established by these measurements.

## Measurement design and reproducibility

The headline results use only `recheck/scan-18.json` and `recheck/scan-30.json`: three disjoint 10,000-input permutation intervals, one final trial per interval per worker setting, run sequentially after integration. The cohorts use run keys 120260001000, 120261001000 and 120262001000. They are distinct deterministic samples, not a proof of independent random draws. Earlier shorter scans and repetitions reuse subsets of these inputs and do not increase the distinct sample count. Earlier exploratory scaling measurements included brief competing activity and are excluded from the headline comparison; their records are retained.

The final checks ran after the computational changes. Restoring the explicit YAML terrain setting to 18 threads afterward does not change these baseline timings: the benchmark constructs `blueprint_config()` and sets baseline process/native counts itself. The no-config portable constructor retains one terrain thread; use `--config config/realm.yaml` for the measured 18-thread terrain profile. The constructor and YAML select the same blueprint constraints.

Measurements are short pilots, not sustained million-input benchmarks. Decimal precision identifies the observed calculation; it does not imply equal predictive precision. Source/native/runtime identities accompany the raw records. Reference versus optimized tests always use the same required blueprint conjunction, not an easier historical count profile.

| Persisted baseline | Wall time, 30,000 inputs | Input seeds/sec | Wall time/input | Observed cohort range |
|---|---:|---:|---:|---:|
| 18 processes × 1 native thread | 26.321651 s | 1,139.746136 | 0.877388 ms | 1,126.05–1,148.44/s |
| 30 processes × 1 native thread | 24.228142 s | 1,238.229493 | 0.807605 ms | 1,229.14–1,242.87/s |

Thirty processes improved throughput by **8.6408%** over eighteen on this workload; the existing 30-worker baseline setting is retained. Peak measured process-tree RSS was 1,460,080,640 bytes versus 953,909,248 bytes, with the configured 8 GiB Docker reserve accounted for separately. These are short-run peaks, not long-run memory ceilings.

The 30-worker checkpoints occupied 430,600,192 bytes, about 14,353 bytes/input. Linear planning gives about **14.35 GB per million inputs**, before new terrain/game evidence and long-run database effects. The configured disk preflight remains more conservative at 65,536 bytes/input. Preserving pending model failures consumes storage; a faster rejection query does not eliminate persistence cost.

## Selectivity and measured cost at each stage

These 30,000 inputs produced 55,853 predicted anchors; 3,946 inputs had no discovered anchor and remain unresolved. Anchor denominators and input-seed denominators are different. A missing model witness is not authoritative actual-world absence.

| Ordered production check | Entered anchors | Passed anchors | Observed conditional pass | Inclusive worker time/entered query |
|---|---:|---:|---:|---:|
| Mansion ≥1 with Dark Forest witness | 55,853 | 266 | 0.476250% | 405.187 µs |
| Jungle Temple ≥1 | 266 | 38 | 14.285714% | 134.179 µs |
| Desert Pyramid ≥1 | 38 | 1 | 2.631579% | 128.132 µs |
| Ocean Monument ≥1 | 1 | 0 | 0/1 observed; population rate unknown | 120.310 µs |
| City, Villages, Trials, Portals, Shipwrecks, Mineshafts | 0 | — | Not estimated | Not measured on survivors |
| Final Nether Fortress + Bastion | 0 | — | Not estimated | Not measured on survivors |
| Exact four-Y biome conjunction | 0 | — | Not estimated | Not measured on survivors |
| Coastal Continent | 0 | — | Not estimated | Not measured on survivors |

Stronghold discovery cost averaged **396.209 µs per input seed** in summed inclusive worker time. This is not its aggregate machine throughput; workers overlap and also incur IPC/persistence work. The first four query costs above likewise cannot be multiplied by worker count to predict machine throughput. The single Monument query is insufficient to characterize even its average cost.

The blueprint's three conceptual stages require separate evidence:

| Conceptual stage | Available pass-through evidence | Measured diagnostic service rate | Limits |
|---|---|---:|---|
| Structure RNG capacity only | 47/48 retained layouts (97.9167%) in fresh applicable raw checks; historical lower32-only gate passed 65.596% tuning / 72.609% holdout | 4,501.131595 selected layouts/s; 222.166 µs/layout | Necessary capacity subset, not complete viability; different raw predicates/cohorts. Does not support 99.8% raw rejection. No separate raw gate was added to production. |
| Full viable structure conjunction | 0/30,000 distinct inputs in production predictor | Included in 1,238.229493 input seeds/s baseline | Count checks short-circuit. Later conditional probabilities are unknown. |
| Biome lattice | 0/48 unconditional selected layouts under exact narrow predicates | 29.529553 layouts/s; 33.864379 ms/layout using capped mode | Four Y planes, 2,304 points/layout at 64-block spacing; selected/correlated cohort, not structure survivors or actual surface/cave certification. |
| Coastal terrain | No complete baseline survivor tested | 0.838721 layouts/s; 1.192291 s/layout for the entire six-resolution ladder | Three selected layouts, 18 native threads, exact-point reuse; unconditional service cost, not conditional acceptance, persistence or actual BDS throughput. |

The full biome inventory median was 34.250808 ms/layout; capped mode was 33.864379 ms/layout. That approximately 1.0114× difference is not evidence of a substantial biome speedup. Negative palettes often need the entire lattice. Neither unconditional 0/48 nor 0/1 in the production Monument gate may be substituted for a zero population probability.

Zero model successes in 30,000 inputs gives a nominal independent-draw one-sided 95% upper bound of approximately 0.0099853% on **model success**. Deterministic sampling, imperfect discovery and conservative fixed-Y filters limit that interpretation; it is not a bound on actual-world feasibility. If the true rate were 1 in 1.5 million, the chance of zero successes in 30,000 independent trials would still be about 98.02%. There is no positive lower bound on full-blueprint success and no finite supported upper bound on required search volume.

## Implemented optimizations and their measured effects

The new production C count API stops after the required number of viable starts. It preserves full64 viability, includes Mineshaft's SIMD path and reports floor witnesses separately from complete counts. Full inventories and bonus ranking run only for baseline survivors. Early checks now prioritize Mansion, Jungle Temple, Pyramid and Monument; the irrelevant broad discovery Nether scan is removed, and the final Nether pair shares its query. The four-Y biome sampler reuses exact points across overlapping anchors and can stop after all positive witnesses.

The following isolated native-wrapper measurements used 48 retained holdout layouts, precreated handles and three counterbalanced repetitions. They exclude discovery, IPC, SQLite, terrain and game verification. **3,456 count comparisons had zero mismatches.** These are query rates, not full input-seed throughput.

| Structure and count floor | Full inventory queries/sec | First-N queries/sec | Full / first-N time |
|---|---:|---:|---:|
| Mansion 1 | 3,575.645 | 3,580.556 | 1.001× |
| Village 5 | 6,695.574 | 6,620.602 | 0.989× |
| Trial Chamber 2 | 10,833.539 | 38,168.666 | **3.523×** |
| Ancient City 1 | 6,223.055 | 7,558.949 | 1.215× |
| Desert Pyramid 1 | 13,317.781 | 13,468.833 | 1.011× |
| Jungle Temple 1 | 13,248.111 | 14,802.379 | 1.117× |
| Monument 1 | 2,132.688 | 3,211.885 | 1.506× |
| Ruined Portal 3 | 58,695.992 | 79,708.534 | 1.358× |
| Shipwreck 2 | 1,028.704 | 1,884.962 | **1.832×** |
| Mineshaft 5 | 315.555 | 2,019.439 | **6.400×** |
| Fortress 1, diagnostic only | 63,601.761 | 74,504.422 | 1.171× |
| Bastion 1, diagnostic only | 56,609.319 | 87,721.224 | 1.550× |

Production Mansion handling deliberately retains the full native inventory before its exact Dark Forest check, because an early Pale Garden witness could hide a later qualifying start. The native Mansion row is therefore only a kernel diagnostic. Production Nether handling uses the shared pair query, not the isolated first-N Fortress/Bastion arms. Village was 1.13% slower in this small timing; near-unity changes are not promoted as meaningful gains. Frequent early Mansion failures mean the large Mineshaft/Trial kernel improvements do not translate into the same total baseline speedup.

A matched 32-input serial comparison against an exhaustive implementation of the same blueprint constraints measured 2.117118 s versus 0.046121 s: **45.904×**. All 47 discovered anchors failed Mansion, so the benefit mainly reflects avoiding doomed downstream work. This is not a 45.9× improvement over the old production pipeline, which already short-circuited and evaluated a different contract. It excludes process/persistence overhead; a synthetic passing fixture separately verifies exact witness/count/score equivalence.

Coastal evaluation now uses one exact Stronghold-centered border with no center search or expanding halo. The retained exact-point cache can serve nested 128→64→32→16→8→4 grids. For three layouts, median complete-ladder time fell from **4.580162 s fresh** to **3.576873 s reused**, a **1.280493× speedup / 21.9051% reduction**. Native sample requests fell from 589,680 to 442,368; 147,312 exact points were reused. All **108 raster-hash/decision parity checks** matched. This preserves an existing exact noise engine and cache; it is not a newly accelerated noise formula or verified Bedrock terrain.

## Production planning without an invented success probability

At the measured short-run capacity, one million baseline inputs project to **13.46 minutes**. This is a throughput projection, not a timed million-input run or an ETA to a playable world.

Let `p` be the unknown full-blueprint success probability per independent input. Mean volume to one success is `1/p`; volume for a 95% chance of at least one is `ceil(log(.05)/log(1-p))`; mean volume to five is `5/p`. At 1,238.229493 inputs/s, conditional scenarios are:

| Assumed full success rate | Mean inputs to first | Inputs for 95% chance of first | Mean baseline time to first | Baseline time for 95% first | Mean baseline time to five |
|---|---:|---:|---:|---:|---:|
| 1 in 1.2 million | 1,200,000 | 3,594,878 | 16.15 min | 48.39 min | 1.35 h |
| 1 in 1.5 million | 1,500,000 | 4,493,597 | 20.19 min | 60.48 min | 1.68 h |
| 1 in 1.8 million | 1,800,000 | 5,392,317 | 24.23 min | 72.58 min | 2.02 h |
| 1 in 10 million | 10,000,000 | 29,957,322 | 2.24 h | 6.72 h | 11.22 h |
| 1 in 100 million | 100,000,000 | 299,573,226 | 22.43 h | 67.20 h | 112.17 h |

These are **assumptions, not forecasts**. The first three probabilities are the blueprint's unsupported range. Conditional terrain workload, actual generation/verification, long-run disk/thermal effects and imperfect predictor recall are omitted. A serial capacity model is `T(N) ≈ N/R_baseline + A_baseline_survivors*C_coastal + T_actual_verification`; overlapping services require separately measured resource allocation and queue rates. `A` counts surviving anchors, not just seeds. The illustrative coastal service cost is 1.192291 seconds per full ladder, but its conditional cost and survivor arrival rate remain unmeasured. Actual game verification has no measured full-blueprint service cost.

The existing BDS adapter's 16-tile coverage budget cannot certify every column of the full 1536-square. Its planner reports partial coverage rather than substituting a smaller box. Full structure extents, surface resources, cave accessibility, cliffs, rolling topology and border/portal playability still need an actual-game verification campaign. No production-length campaign or playable seed certification was performed during this audit.

## Safe cleanup and verification

Cleanup removed **114 files / 2,661,074 logical bytes**: reproducible test/Python caches, six empty ignored logs and one unreferenced debug screenshot. All core source, active and historical configs, tests, fixtures, native/runtime dependencies, benchmark baselines/checkpoints, nonempty evidence logs and linked historical reports were preserved. Cache files may be regenerated by the final test run. Large historical run directories are evidence, not disposable bloat. The cleanup receipt records every removed path, hash, size and reason.

Correctness fixes include native include fragments in source distributions, isolated/reproducible count-pilot builds, active V1-only queue accounting, fixed-box verification adapters and computation identities that include the new blueprint/coastal code. The isolated fresh pilot rebuild passed **405 comparisons**, including 189 positive over-cap cases.

Final integrated verification: **773 tests passed in 109.31 seconds**, including an isolated fresh pilot rebuild. The first run exposed one stale assertion equating historical island defaults with the newly active coastal profile; that test now compares the active constructor with the explicit active profile, and a separate assertion preserves the historical island/V2 defaults. No production change was required for that failure. CLI compatibility/status checks, final computation-identity parity against the timed baseline, coastal source hashes, JSON parsing, local report links and `git diff --check` passed. The restored YAML terrain thread setting affects only the explicit terrain profile. Evidence: [final test log](runs/blueprint-audit-2026-10-12/final-pytest.log) and [verification receipt](runs/blueprint-audit-2026-10-12/final-verification.json).

## Evidence and commands

Evidence directory: [runs/blueprint-audit-2026-10-12](runs/blueprint-audit-2026-10-12/).

* [Consolidated numbers and assumptions](runs/blueprint-audit-2026-10-12/benchmark-summary.json)
* [Final 30-worker baseline](runs/blueprint-audit-2026-10-12/recheck/scan-30.json) and [18-worker baseline](runs/blueprint-audit-2026-10-12/recheck/scan-18.json)
* [Per-type native counts](runs/blueprint-audit-2026-10-12/per-type-counts.json), [unconditional raw/biome diagnostics](runs/blueprint-audit-2026-10-12/diagnostics.json), [serial reference](runs/blueprint-audit-2026-10-12/serial.json)
* [Full coastal ladder](runs/blueprint-audit-2026-10-12/coastal-full-timing.json), [cleanup receipt](runs/blueprint-audit-2026-10-12/cleanup.json), [pre-change identities](runs/blueprint-audit-2026-10-12/before-identity.json)

Use fresh output directories and run timings sequentially without builds/tests competing for CPU:

```sh
.venv/bin/python scripts/benchmark_blueprint.py scan --count 10000 --trials 1 --workers 30 --output runs/new-blueprint-benchmark
.venv/bin/python scripts/benchmark_blueprint.py scan --count 10000 --trials 1 --workers 18 --output runs/new-blueprint-benchmark
.venv/bin/python scripts/benchmark_blueprint.py serial --count 32 --trials 3 --output runs/new-blueprint-benchmark
.venv/bin/python scripts/benchmark_blueprint.py diagnostic --output runs/new-blueprint-benchmark
.venv/bin/python scripts/benchmark_blueprint.py counts --output runs/new-blueprint-benchmark
.venv/bin/python scripts/benchmark_blueprint_coast.py --layouts 3 --trials 3 --threads 18 --resolutions 128 64 32 16 8 4 --output runs/new-blueprint-benchmark/coastal-full-timing.json
.venv/bin/python -m pytest -q
```

The author-supplied `MASTER_SEED_BLUEPRINT.md` remains unchanged. Its predictions are evaluated and corrected in these audit reports; it is not rewritten to present assumed performance as measured fact.
