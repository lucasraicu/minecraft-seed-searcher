# Coastal river revision and native score parity

12 October 2026. Implemented the requested river/score changes as active revision `locked-2048-1024-river-v2`. Geometry remains 2048×2048 Overworld / 1024×1024 Nether. The earlier locked v1 and original historical blueprint factories remain supported, with their original floors and scoring. Existing checkpoints must not silently acquire these changed eligibility rules; use a fresh run and rebuild the native batch extension. The pinned Bedrock 26.52 / predictor MC_26_50 runtime was preserved; this task did not change the generator version.

## Land, ocean and freshwater behavior

The active land model uses 8-way connectivity. Diagonal contact alone does not bridge a wide river, so enclosed freshwater explicitly joins geographic land components. Mainland area sums **dry land only**, excluding all freshwater cells. This preserves land-area constraints instead of counting rivers/lakes as solid ground. Historical coastal revisions retain face-connected land and their original decisions.

Ocean membership remains strictly `FAMILIES['ocean']` combined with known water evidence. `rivers_shores` also contains beaches; only actual `river` / `frozen_river` biome witnesses identify river water. Lakes require known non-ocean water enclosed by land/river, with incomplete or unknown enclosure excluded. Ocean-biome pools never become freshwater bridges. Only waterways belonging to the primary geographic landmass can satisfy the gate; an offshore island's long river cannot substitute. Actual surface-biome string observations take precedence over predicted numeric IDs, and conflicting observations cannot supply a witness.

The new configuration declares:

```yaml
land_connectivity: 8
bridge_inland_freshwater: true
river_corridor_min_length_blocks: 600
river_highway_hub_radius_blocks: 250
river_highway_bonus_points: 20
```

At least one face-connected freshwater component containing a river witness must have a sampled path length lower bound ≥600 blocks. A stand-alone lake does not satisfy this task's explicit river requirement. Cell count and bounding-box extent are not used as path length. Two graph sweeps find actual connected endpoints; a single-source distance vector gives their shortest-path length. This is a conservative diameter lower bound, not an exact longest-path calculation, and can leave additional qualifying paths unresolved. Queues preserve unresolved terrain; no approximation becomes authoritative absence or actual navigation certification.

A highway bonus requires the **same qualifying unfrozen river/freshwater component** to touch the approved coastal ocean and have a sampled point within 250 blocks of the **actual Stronghold coordinate**, including shifted anchors. Separate components cannot pool their length, hub proximity or coast contact. Enclosed lakes can join a river route. Frozen river cells remain inland freshwater but cannot supply the open-water highway. Metrics include component IDs, sample counts, endpoints, length lower bounds, hub distance, coastal contact, freshwater/river/lake areas and `river_highway_connected`.

`river_navigability_verified=false` and explicit pending actual checks remain. Samples do not prove depth, headroom, absence of obstructions, thawed water, continuous unsampled blocks or a boat route. The operational 75–85% dry-mainland range was preserved. The authored blueprint now says 70–80%; that separate threshold change was not requested here or silently adopted. Its lake-alternative prose likewise does not replace this task's required sampled river corridor.

## Floors, bonuses and durable ranking

The new core Nether floor is Fortress ≥2 / Bastion ≥3. The post-terrain Shipwreck floor is ≥5 qualifying coastal/beach starts. C fixture counts, screening miss bits, Python oracle, replay, direct records, deferred marine metadata, complete inventories, qualification labels and validation all use the revised floors. One unmet Bastion count still consumes exactly one baseline miss. The terrain river requirement is evaluated afterward, outside the 23 core criteria.

| Bonus | New formula |
|---|---|
| River highway | +20 once for a qualifying predicted hub-to-coast route |
| Mansion | +50 once when at least two qualifying predictor starts exist |
| Monument | +25 once when at least two qualifying coastal predictor starts exist |
| Bastion | +15 for each start above three; fourth and later copies count |
| Shipwreck | +5 for each qualifying start above five |

Other locked bonuses remain unchanged. Native baseline score excludes unqueried terrain/marine bonuses. Finest-resolution post-terrain marine completion adds the observed river/marine bonuses and persists their evidence alongside the candidate patch in the existing FULL SQLite terrain transaction. Exact duplicate completion does no work; a changed retry payload fails. Rescoring uses the saved river metrics, so it cannot erase or double-add the bonus. The existing indexed leaderboard reads the resulting score without requiring a separate schema migration.

## Measured traversal optimization

The initial independent Python queue traversal was correct but expensive. It was retained as `runs/river-highway-2026-10-12/python-traversal-coastal.py` and replaced with compiled SciPy sparse graph traversal. The sparse graph keeps at most four directed edges per sampled cell and preserves the oracle's up/down/left/right adjacency order. Calls request individual source traversals/distances, never an N×N all-pairs distance matrix. See the primary [breadth-first API documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.breadth_first_order.html) and [single-source unweighted distance documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.dijkstra.html).

Three retained natural near-miss 4-block rasters, three rotated repetitions, geometry only:

| Evaluation | Median three-control cohort seconds |
|---|---:|
| Earlier locked coastal geometry without river work | 0.10023 |
| River geometry with Python queue traversal | 0.64067 |
| **River geometry with compiled traversal** | **0.24992** |

Compiled traversal makes the complete river-aware geometry calculation **2.56× faster** than the Python implementation, with zero complete-result differences after excluding only timing metadata. Its total still exceeds the earlier geometry-only calculation because it adds required freshwater and river analysis. This is not native seed throughput, density generation timing, SQL performance or BDS latency. Average cohort cost is about 83 ms per anchor; full fine-density terrain sampling remains separate and takes seconds. One hundred deterministic random grids also match the independent queue oracle's path lengths and exact endpoints. No empirical parity exclusion hides water, connectivity, score or decision changes.

## Screening benchmarks and verification

Fresh bounded, counterbalanced CLI measurements are in `final-benchmarks/results.json`; they compare the preceding locked one-miss policy, the new river one-miss policy, and the new full-evidence native/Python routes. Compact/C use 50,000 distinct inputs, key `120267001000`, with three repetitions. Full evidence uses a contained 5,000-input subset, not additional distinct volume. Native compact uses 32 threads; full native uses 16 plus two pipeline slots; Python uses 36 single-thread workers. CLI wall timing includes startup, draining, FULL range commits and process exit. Terrain/BDS are excluded. Original controls and evidence remain intact.

Final rates and verification are appended below. The changed geometry/floors/river policy does not establish full-world discovery probability, and compact checkpointed inputs/sec remains different from saving every input's complete evidence.

Reproduce on fresh paths:

```sh
.venv/bin/python scripts/build_blueprint_batch.py --output runs/new-river-native \
  --openmp-prefix runs/master-implementation-2026-10-10/openmp/install
.venv/bin/python -m seed_search baseline --count 1000 \
  --executor native --native-build runs/new-river-native \
  --native-threads 32 --retention survivors --max-misses 1 --output runs/new-river-scan
.venv/bin/python scripts/benchmark_river_blueprint.py --native runs/new-river-native \
  --output runs/new-river-benchmark --count 50000 --trials 3
.venv/bin/python -m pytest -q
```

Omit the OpenMP prefix and use one thread for a portable serial build. Native policy ABI changes produce an explicit rebuild error on stale extensions. Keep the current host-only runtime prefix when using OpenMP. The prior BDS budget/coverage limits and prediction-scale/large-search gates still apply. No BDS world or unbounded search was launched for this task.

## Final correctness checks

**851 tests passed in 186.19 seconds** on the final implementation. The isolated serial AddressSanitizer run exercised **1248 river-policy inputs with diagnostic timing buffers and zero errors**. Serial ASan is not a parallel race certificate. The suite covers historical policies, revised signed64 native/direct/replay/Python records, serial/OpenMP owned outputs, all floor/miss handling, 100 random graph/queue comparisons, diagonal land versus water, unknown and conflicting evidence, frozen rivers, inland lakes versus ocean, disjoint components, shifted Stronghold hubs, and offshore rivers.

A production durable terrain fixture executes the entire 128/64/32/16/8/4 workflow, queries deferred marine structures once at finest resolution, stores highway/shipwreck bonuses in the candidate's SQL ranking, and resumes with zero work. Exact duplicate transaction retry is idempotent; changed retries fail. Rescoring retains the saved highway bonus. No actual navigability or full-world certification is manufactured by these prediction fixtures.

The revised native floors and bonus formula are adopted for the explicit native executor after parity verification. Python remains available and the default executor. Compact one-miss retention remains available; V2 remains outside active scheduling. Supported serial builds remain tested; no generator dependency or OpenMP runtime replacement was required.

Retained evidence is under `runs/river-highway-2026-10-12/`: `before/` and initial dirty-tree inventory; native build/identity; `final-suite.log`; `asan-river/result.json`; `final-geometry-profile-v2/results.json` with matched Python queue control; per-trial benchmark receipts/databases; CLI smoke/resume; and final source/verification manifests. Preliminary tests, profiles and benchmarks remain separately retained.

## Final throughput and resources

| Scope/policy | Median inputs/sec | Three-trial range |
|---|---:|---:|
| native_only: Prior locked v1, one miss | 12,988.15 | 12,986.28–13,030.45 |
| native_only: River revision, one miss | 15,227.87 | 15,149.89–15,284.25 |
| compact_cli: Prior locked v1, one miss | 10,494.51 | 10,475.37–10,542.92 |
| compact_cli: River revision, one miss | 12,086.87 | 11,939.02–12,156.34 |
| full_cli: River native full evidence | 1,218.96 | 1,216.74–1,233.40 |
| full_cli: River Python full evidence | 904.67 | 898.47–908.75 |

Comparable same-policy full-evidence speedup is **1.347× (34.74%)**, with zero full-record/durable-task semantic differences. New compact screening is **15.17% faster** than the fresh preceding policy, but this changes the Bastion floor from two to three. It is a policy/selectivity change, not an isolated same-policy C optimization. Shipwreck/river work stays deferred and is not included in these screening rates.

The compact cohort saved **zero** natural river-revision candidates; the prior policy retained one near miss. Positive/near-miss fixtures remain essential accepted-row and river-score evidence. No complete natural core or verified-world survivor was found; no success probability is inferred. Neither native-only nor compact checkpointed rate represents full-evidence persistence or complete terrain/BDS verification. The **5,000/sec full-evidence target remains unmet**.

| CLI policy | Peak process-tree RSS MiB | Largest final SQLite DB MiB |
|---|---:|---:|
| Prior locked v1, one miss | 144.90 | 0.31 |
| River revision, one miss | 142.43 | 0.20 |
| River native full evidence | 427.01 | 90.73 |
| River Python full evidence | 1647.50 | 91.07 |

Final DB size excludes transient WAL and raw artifacts. Each full-evidence run contains 5,000 inputs; compact contains 50,000. Preflight projected **21.63 GB** plus a 16 GiB reserve against **631.58 GB** free. Native/prepared queue caps and CPU budgets remain unchanged. Repetitions and the preliminary run reprocess the same defined inputs, not additional distinct search volume. All thirteen final benchmark/smoke databases passed integrity checks with FULL synchronization.

The actual default-configuration CLI smoke processed 256 inputs with default one-miss retention; resume committed zero new inputs. Source/build manifests match the final computation. Original generator SHA-256 remains `512df6a76cc24c90cd0a78eddd45e60fd06d0f1e945cb3a9521ab42fe75e385d`. The new private batch extension SHA-256 is `67ef684de99fb268a3ccfe6a41031d2c3d1cf5733486fa686966bf821d5637c3`; the pinned OpenMP runtime remains unchanged.

Raw final artifacts: [screening comparison](runs/river-highway-2026-10-12/final-benchmarks/results.json), [geometry/profile parity](runs/river-highway-2026-10-12/final-geometry-profile-v2/results.json), [final tests](runs/river-highway-2026-10-12/final-suite.log), [ASan](runs/river-highway-2026-10-12/asan-river/result.json), and [sealed verification record](runs/river-highway-2026-10-12/final-verification.json).
