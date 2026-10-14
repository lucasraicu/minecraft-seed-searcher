# Bedrock Coastal Continent seed search

The active CLI and `config/realm.yaml` implement the explicit `master_seed_blueprint_v1` contract from [MASTER_SEED_BLUEPRINT.md](MASTER_SEED_BLUEPRINT.md). The supported runtime remains pinned to Bedrock **26.52 / BDS 1.26.52.3** and predictor **MC_26_50**. A version pin does not establish actual-game equivalence.

The active screening revision is `origin-fixed-2048-v1`. One evaluation center at world origin (0,0) uses the exact Overworld square `[-1024,-1024,1024,1024)` and Nether square `[-512,-512,512,512)`. Actual game spawn is not assumed to be origin. A predicted Stronghold inside the Overworld square is mandatory and cannot consume the one-miss allowance; its regional and village-associated starts are both inventoried when reached. The other 24 baseline requirements remain 11 structure-count floors and 13 biome predicates. Marine, river and actual Bedrock verification remain downstream. The historical `locked-2048-1024-outpost-v3` policy and its benchmarks remain available through its factory and saved run identities.

Screening runs the Nether pair, Portals and Chambers, then queries Strongholds only when the miss budget permits. It continues through Outposts, Pyramid, Temple, Mansion, Cities, Villages and Mineshafts. A first unmet secondary floor is retained as a possible one-miss candidate; a second stops further work. Retained origin candidates receive complete Stronghold and core structure inventories plus the complete four-Y biome lattice so bonus biomes are scored from sampled evidence. Stage 3 still evaluates coastal terrain, river and deferred Monuments/Shipwrecks. `PREDICTED` means the core screen passed; it is not complete-world or actual-game certification.

The [fixed-origin pilot](ORIGIN_FIXED_RESULTS.md) measured **41,854 checkpointed compact inputs/sec** on the production CLI pipeline, versus **30,500/sec** for the historical Stronghold-centered policy on the same repeated 30,000-input cohort (+37.2%). Including CLI startup, the medians were **21,735 versus 18,412/sec** (+18.0%). This policy comparison changes eligibility and geometry, and no natural complete baseline survivor appeared. It does not establish a complete-world yield or the proposed 150,000/sec rate.

The historical Outpost floor, measured filter order and coastal optimization are documented in [OUTPOST_OPTIMIZATION_RESULTS.md](OUTPOST_OPTIMIZATION_RESULTS.md). Under the active policy, Outposts above the floor of two earn +10 each. The one-miss allowance includes an unmet Outpost floor. A new run and rebuilt native extension are required for this policy revision.

Earlier river semantics, tests and measurements are documented in [RIVER_HIGHWAY_RESULTS.md](RIVER_HIGHWAY_RESULTS.md).

The river revision uses 8-way geographic land connectivity and lets enclosed inland freshwater join river banks without adding water area to dry-land totals. Ocean water requires an ocean-family biome; dry shores, rivers and enclosed non-ocean lakes cannot supply the ocean strip. River paths use face connectivity, so diagonal water contact cannot establish a channel. A two-sweep graph path gives a conservative sampled length witness; a lake alone does not satisfy the river gate. Under the active origin policy, a qualifying unfrozen freshwater route passing within 250 blocks of `(0, 0)` and touching the approved coastal ocean earns **35 points**. Historical Stronghold-centered policies use their saved scoring rules. This is a predicted connection: depth, boat clearance, ice and unsampled continuity require actual verification.

The latest full-evidence optimization measures **2,466.15 durably persisted inputs/sec**, up from **1,413.39/sec** for the preserved implementation on the same 30,000-input cohort (**1.745×**). A separate 5,000-input comparison measures **1,855.75/sec native versus 906.33/sec Python**. All records and task fingerprints match; **880 tests passed**. The 5,000/sec full-evidence target remains unmet. See [FULL_EVIDENCE_OPTIMIZATION_RESULTS.md](FULL_EVIDENCE_OPTIMIZATION_RESULTS.md) for profiles, variability, resource costs and rejected alternatives. Use a fresh run for the changed Python source identity; the verified Outpost-v3 native extension remains compatible.

The preceding Outpost-v3 report measured **22,525.37 checkpointed compact inputs/sec** and **1,179.67 full-evidence persisted inputs/sec** versus **886.78/sec** for its matching Python control. Compact throughput was 1.88× the fresh previous-policy control, including the added Outpost floor's selectivity. C-only screening measured **35,385.17/sec** on that held-out cohort. Exact coastal geometry evaluation improved another **1.13×**; density generation and BDS verification are separate. See the Outpost results report for its trial ranges, resource costs and parity evidence.

Historical river-revision medians were **12,086.87 checkpointed compact inputs/sec**, **15,227.87/sec C only**, and **1,218.96 full-evidence persisted inputs/sec** versus **904.67/sec** for the matching Python control. River/terrain/BDS work is separate. The stricter Bastion floor changes selectivity; this is not an isolated screening optimization. River-aware coastal evaluation became **2.56× faster** with compiled traversal while preserving complete results against the Python queue oracle.

The active score awards **50 points each for a second Mansion and a second distinct predicted Stronghold**, **25 for a second qualifying Monument**, **20 per Bastion above three**, and **5 per qualifying Shipwreck above five**. River evidence and its score commit with finest-resolution marine/terrain completion and survive rescoring. Historical configurations retain their original thresholds and formulas. New source/configuration identities require a fresh run and rebuilt batch extension. The current operational mainland range remains 75–85%; the authored blueprint's newer 70–80% wording is a separate unresolved policy difference.

Saved highway evidence can be inspected directly:

```sql
SELECT seed,
       json_extract(result,'$.ranking.score') AS smart_score,
       json_extract(result,'$.ranking.bonuses.river_highway') AS river_bonus,
       json_extract(result,'$.terrain_score_metrics.river_highway_connected') AS predicted_highway
FROM candidates
WHERE json_extract(result,'$.screening_revision')='origin-fixed-2048-v1';
```

The biome gate uses a world-aligned 64-block lattice at **Y=63, -48, 0 and 160**. The ten surface predicates (nine resource families with peaks and stony shore required separately) use Y=63/160; Lush Caves, Dripstone Caves and Deep Dark use Y=-48/0. Pale Garden does not substitute for Dark Forest, and a broad mountain family does not substitute for Jagged/Stony Peaks. The Mansion start additionally needs a Dark Forest predictor witness at Y=63. These fixed-Y samples establish model witnesses, not exposed surface biomes, actual cave generation, packed/blue ice quantities or absence of unseen biomes.

**V1 Coastal Continent** evaluates the connected primary landmass against **75–85% of the entire border area**, a connected ocean strip at least **250 blocks wide** touching a continuous border sector at least **1024 blocks long**, and monument containment in coastal water. The half-edge sector is the explicit operational interpretation of the blueprint's “edge or coastal quadrant”; 400 blocks is a preference, not a mandatory upper limit. The ±80-block box around a predicted monument start is an engineering screening envelope, not a known structure footprint. Whole-world certification also requires actual terrain, resource and structure evidence. V2 mountain enclosure has been retired from active scheduling; `terrain --variant all` uses only the profile's active variants. Historical island V1 and V2 saved configurations retain their original meaning and remain readable and reproducible.

```sh
.venv/bin/python -m seed_search doctor
.venv/bin/python -m seed_search baseline --count 1000 --output runs/my-blueprint
.venv/bin/python -m seed_search status --run runs/my-blueprint
.venv/bin/python -m seed_search terrain --run runs/my-blueprint --variant all --limit 1
.venv/bin/python -m seed_search results --run runs/my-blueprint --variant v1 --export
.venv/bin/python -m seed_search verify-terrain --run runs/my-blueprint --variant v1 --top 1
```

Place `--config config/realm.yaml` before the command to select the profile explicitly. Use fresh run directories when changing the contract or computation identity. Above 1000 inputs the existing `--prediction-scale` gate and persisted compatibility report remain required. Baseline survivors already have their scoring inventory; historical deferred inventory commands remain available for older runs. `inventory --all-starts --candidate ...` can retain a separate explicit predictor audit.

Production builds include the count kernel directly through `native/bridge.h` and `native/filters.inc`; no ignored pilot library is loaded. `native/build.py` builds a portable serial extension by default. Optional OpenMP requires an explicitly supplied runtime prefix and, on macOS, an explicit matching host `ARCHFLAGS`. Baseline uses multiple spawned processes with one native/numeric thread each; terrain native threads are configured separately. Concurrent workloads need their own measured resource profile. The existing backend lock serializes shared Python-process handle access while OpenMP parallelizes immutable native column/point work.

The React dashboard in `web-ui/` connects to `seed_search.web.server`, launches explicit native sweeps, and reads durable SQLite progress and a bounded candidate pool. Initial demo records are labeled illustrative; prediction, terrain screening and actual BDS evidence remain distinct. Some controls are explicitly planning-only. Use CLI exports for complete result sets, and use the saved original computation identity when resuming; this dashboard does not certify actual worlds or exhaustive CPU optimality.

See [ENGINE_AUDIT_RESULTS.md](ENGINE_AUDIT_RESULTS.md) for implementation and correctness findings, [BLUEPRINT_FEASIBILITY_ANALYSIS.md](BLUEPRINT_FEASIBILITY_ANALYSIS.md) for requirement feasibility, and [BLUEPRINT_BENCHMARK_RESULTS.md](BLUEPRINT_BENCHMARK_RESULTS.md) for measured throughput, stage costs, cleanup and conditional runtime scenarios. The 30,000-input pilot measured 1,238.23 baseline inputs/second; full-blueprint success probability and verified-world runtime remain unknown.

The following throughput numbers describe the **historical 1536/896 policy**, before the locked-border revision. The original isolated prototype is retained in [NATIVE_BASELINE_PROTOTYPE_RESULTS.md](NATIVE_BASELINE_PROTOTYPE_RESULTS.md). Its 19,835.87/sec C-only rate was not persisted throughput. The implementation and fresh comparisons are recorded in [NATIVE_THROUGHPUT_RESULTS.md](NATIVE_THROUGHPUT_RESULTS.md): full evidence measured 3,061.70 persisted inputs/sec on the repeated 30,000-input cohorts and 2,793.36/sec on the repeated 100,000-input held-out cohort, versus 1,164.12 and 996.41/sec for the fresh Python controls. The final actual CLI held-out comparison measured **3,730.73 full-evidence persisted inputs/sec** versus **1,174.71/sec** for Python. Compact scanning with up to two misses measured **12,226.51 checkpointed inputs/sec**; strict survivors measured **17,252.74/sec**. Each is a three-trial median on 100,000 inputs. The compact cohort saved no natural candidates, so accepted-record cost remains supported by positive fixtures. The 5,000/sec full-evidence target remains unmet.

Native execution is an explicit option for the audited blueprint eligibility profile. The Python route remains the default and the replay adapter remains an oracle. Build a separate native batch extension without replacing the existing generator:

```sh
.venv/bin/python scripts/build_blueprint_batch.py \
  --output runs/my-native-build \
  --openmp-prefix runs/master-implementation-2026-10-10/openmp/install
.venv/bin/python -m seed_search baseline --count 10000 --prediction-scale \
  --executor native --native-build runs/my-native-build \
  --native-threads 16 --native-batch-size 4096 --output runs/my-native-full
```

Omit `--openmp-prefix` for a portable serial build and use `--native-threads 1`. Standard package builds also include `seed_search._blueprint_batch`; `native/blueprint_build.py` builds just that extension. Serial is the default, with the same explicit OpenMP prefix/architecture rules as `native/build.py`. There is no silent fallback if the selected extension or profile is incompatible. Each invocation is bounded to 100,000 inputs; native batches are bounded to 16,384. The pipeline reserves two CPU slots for preparation/writing, limits outstanding batches and bytes, monitors process-tree memory, and preserves WAL with FULL synchronization and disk reserves.

Private builds accept `--work-chunk 16`, `64` or `128` for measured atomic scheduling experiments. The default remains 16: larger chunks slowed the current compact workload. Reproduce the same-policy comparison with `scripts/benchmark_native_chunks.py --output <fresh-directory> --openmp-prefix <runtime-prefix>`. See [GEMINI_PIPELINE_REVIEW_RESULTS.md](GEMINI_PIPELINE_REVIEW_RESULTS.md) for retained measurements and review findings. Process-tree monitoring failures stop new dispatch; current-process peak RSS cannot replace live parent-and-worker memory.

For compact storage, save predicted survivors and near misses instead of individual rejected inputs:

```sh
.venv/bin/python -m seed_search baseline --count 10000 --prediction-scale \
  --executor native --native-build runs/my-native-build \
  --native-threads 32 --native-batch-size 4096 \
  --retention survivors --max-misses 1 --output runs/my-native-near-misses
.venv/bin/python -m seed_search resume --run runs/my-native-near-misses
.venv/bin/python -m seed_search results --run runs/my-native-near-misses --export
```

`--retention full` saves every processed seed and discovered anchor with all original tasks. `--retention survivors` defaults to one allowed miss under the locked revision (two for historical configurations); specify `--max-misses 0` for strict survivors. A miss is one unmet core structure-count requirement (11 in total) or one missing biome family (13 in total) **at the same evaluation center**. Three villages when six are required is one miss. This allowance applies to baseline predictor requirements; terrain/V1 requirements are evaluated afterward. Near misses stay `PENDING`; all-24 core baseline survivors stay `PREDICTED`. Both retain exact missing requirements, predictor counts, witnesses and uncertainty. SQL stores the near-miss label in `result.retention.classification`, also exported in JSONL/CSV. For example:

```sql
SELECT seed, json_extract(result,'$.retention.unmet_requirements') AS misses
FROM candidates
WHERE json_extract(result,'$.retention.classification')='NEAR_MISS';
```

In compact mode C stops when an anchor already exceeds the allowance and drops its evidence before Python record construction. Accepted near misses receive complete core predictor inventories. Deferred marine requirements do not count against the baseline miss allowance and are not silently certified. Only retained seeds/anchors receive evidence rows and discovery/V1 tasks. Saved near misses remain pending and do not enter automatic terrain evaluation unless `terrain.include_pending` is explicitly enabled in the run configuration. SQLite still atomically commits a completed range, a decision digest and counts with the retained records. These checkpoints permit reliable resume; discarded inputs have no individual evidence and cannot later be reconsidered without rescanning. Status distinguishes processed range coverage from saved row counts. Retention mode and miss allowance cannot change on resume; use a fresh run. Compact scan rates are **checkpointed scanned inputs/sec**, a different storage contract from full-evidence persisted inputs/sec. Neither rate measures actual-game verification or world-discovery time.

The 2048 border has 4,096 defined biome samples (32×32×4), using the same dispersed order and four-Y roles. A missing rare family in the first 64–128 samples does **not** justify rejection: valid late witnesses are regression-tested. Retained origin candidates use the complete lattice for optional biome bonuses; missing families are never inferred from sparse negative samples.

The baseline leaderboard is now an indexed SQLite view. `results --run ... --limit 20`
reads a consistent live snapshot and returns `smart_score`, `leaderboard_rank`,
`unmet_requirements` and the score's `ranking_view`. Verified candidates precede
complete predicted baseline survivors, then near misses, then other pending records.
Near misses with fewer unmet requirements come first; within each group, scores
descend, with candidate ID breaking ties. Active origin-policy runs have at most one
evaluation-center candidate per input seed; historical runs can have several Stronghold anchors.

`smart_score` uses the selected revision's baseline bonus formula. Near misses use the observed
partial predictor score, while deferred full-evidence inventories retain their
provisional interval-midpoint ranking. Missing requirements are not silently waived
or treated as complete scores. JSONL/CSV exports include `smart_score`. Index entries
update in the same transaction as saved candidates and subsequent score/evidence
updates; candidate JSON, coverage and retry digests remain authoritative. Existing
databases acquire the additive view/index when opened through `RealmStore`. The SQL
view hides results during an incomplete rescore revision, and the CLI explains that
the rescore must finish.

For a dashboard or read-only SQLite client:

```sql
SELECT seed, qualification, retention_classification, unmet_requirements, smart_score
FROM candidate_leaderboard_view
ORDER BY ranking_tier, unmet_requirements, smart_score DESC, id
LIMIT 20;
```

Stage profiling is a separate diagnostic build, preserving production performance
and the selected compact miss allowance. Run it on bounded inputs:

```sh
.venv/bin/python scripts/build_blueprint_batch.py \
  --output runs/my-profile-build --profile \
  --openmp-prefix runs/master-implementation-2026-10-10/openmp/install
.venv/bin/python scripts/profile_native_stages.py \
  --native runs/my-native-build --profile-native runs/my-profile-build \
  --locked --output runs/my-stage-profile --count 10000 --diagnostic-count 128 \
  --threads 32 --diagnostic-threads 8 --trials 3
```

Omit the OpenMP prefix and use both thread arguments equal to one for serial builds.
Profiles retain count, total, mean, min/max, worst seed/coordinate and bounded p99
histogram intervals for entered structure stages, all four Y levels, generated biome
IDs and each of the 13 biome-family predicates. Query timings grouped by a family
describe shared generator queries returning that family, rather than independent
family searches. Locked one-miss execution (`--locked`), historical two-miss execution and forced complete diagnostics are
reported separately. Fortress/Bastion share their production scan; separate forced
inventory probes are labeled. Diagnostic timings survive rejected-record discard.
Timing buffers are capped at 64 MiB per call, in addition to the existing native
output/scratch cap. The profiler checks full-record/control parity and measures its
own overhead; these C-only measurements are not persisted throughput.

Historical locked geometry, regressions and measured comparisons are documented in [NATIVE_LOCKED_GEOMETRY_RESULTS.md](NATIVE_LOCKED_GEOMETRY_RESULTS.md). Rebuild private or packaged batch extensions for the revised native policy ABI; previously compiled batch extensions fail with an explicit rebuild message. Use fresh checkpoints when changing geometry or screening identity. `blueprint_config()`, `locked_blueprint_config()`, `river_blueprint_config()` and `outpost_blueprint_config()` preserve historical policies; `origin_blueprint_config()` supplies the active CLI default.

The preceding locked v1 policy (2 Bastions / 4 Shipwrecks, without the river gate) measured **10,192.81 checkpointed inputs/sec** with one-miss compact retention, **5,783.05/sec** with two misses, and **1,281.97 full-evidence persisted inputs/sec** versus **961.98/sec** for the comparable Python control. C-only one-miss screening is 12,646.71/sec. These are three-trial medians; terrain and BDS are separate. The full-evidence 5,000/sec target remains unmet.

Terrain already uses a bounded coarse-to-fine cascade with exact point reuse. The measured 128/32/4 alternative improved the three-control cohort by only 1.76%, so the existing six-level schedule remains. Coarse nomination cannot safely prove a fine-resolution rejection. Complete 4-block density still takes seconds per anchor.

Official BDS verification stays outside screening and retains its persistent 20-attempt budget. `verify-terrain --top 20` selects only eligible finalists within the remaining budget; use `--top 1` for a small first check. Headless execution, exact request caching, same-world tile batching and copied LevelDB inspection already exist. The 16-tile default cap cannot certify all 64 tiles of a 2048 border: oversized or incomplete requests remain PARTIAL. View-distance 5 versus 8 measured about 11 seconds for a tiny region, with partial coverage and block-state differences; no production property change was adopted. Full-world verification time remains unestablished. See the linked locked-geometry report for bounded reproduction commands and retained evidence.

The earlier 1536/896 ranking/profile changes and bounded Mansion reuse are documented in
[NATIVE_RANKING_PROFILE_RESULTS.md](NATIVE_RANKING_PROFILE_RESULTS.md). The longer
matched C controls measured about 2.9% improvement; fresh two-miss CLI trials measured
about 1.9%. These modest scan gains are separate from the much larger leaderboard
query improvement. Rebuild the extension for Mansion reuse; a build with
`--disable-mansion-cache` provides the uncached control. Use a fresh run after a
computation-identity change.

Original controls and raw evidence remain under `runs/native-throughput-2026-10-12/`; no retained prototype runs or source dependencies were removed. The implementation plan is [NATIVE_THROUGHPUT_IMPLEMENTATION_PLAN.md](NATIVE_THROUGHPUT_IMPLEMENTATION_PLAN.md).

## Historical schema 5 island and mountain profiles

The remainder of this section records the prior schema-5 contracts. Statements about defaults, mandatory families, V1 islands and V2 apply only to saved legacy configurations, not the active blueprint profile.

Historical target: **4000×4000 discovery in each dimension, 1536×1536 Overworld, 896×896 Nether**. The [compact search implementation plan](COMPACT_SEARCH_IMPLEMENTATION_PLAN.md) is implemented; measured results and remaining prediction limits are in [COMPACT_SEARCH_IMPLEMENTATION_RESULTS.md](COMPACT_SEARCH_IMPLEMENTATION_RESULTS.md). Older benchmark results retain their original geometry. Use fresh run directories for changed computation identities.

The default `search`, `doctor`, and `benchmark` commands now use the new Realm contract. Explicit schema 3/4 configurations and existing historical checkpoints retain their legacy interfaces. New results are predictions until actual Bedrock evidence establishes otherwise.

The new universal baseline discovers Strongholds in `[-2000,2000)` on both axes and records each anchor separately. Its mandatory Overworld region and Realm border are 1536×1536, centered on that Stronghold and allowed beyond discovery bounds. Village, Trial Chamber, Ancient City and Mineshaft are mandatory, together with the anchor, a broad initial Nether Fortress and at least two of five wooded families. Missing unvalidated predictions remain pending. Savanna is neutral and caves are manual-only.

V1 finds islands with connected surrounding water; V2 finds mountain basins and accepts jagged or steep interiors. Both independently consume the same saved provisionally qualified baseline pool. The former combined variant is retired. Formation-fit status stays separate; promising outside/uncertain footprints remain recorded. Final Nether bounds are 896×896 around exact Stronghold/8, requiring Fortress and Bastion. Exact generated structure enumeration and complete natural-ground validation remain unsupported/unverified; no fully verified Realm candidate is claimed.

The active terrain preferences now require **250,000 square blocks of one connected main island**, favor about **650,000**, and permit area-equivalent diameters up to **1300 blocks**. Disconnected islets do not add to the main island's area; irregular outlines are allowed and border fit uses the sampled footprint. V2 uses an inclusive **surrounding mountains** policy: substantial elevated terrain on at least **16 of 32 directions**, at least **24 blocks** above the sampled interior, at **150–700 blocks**, with no empty angular gap above **135°**. Separate mountains, open passes, rough interiors and water interiors are allowed; strict connected-arc shape is an optional historical policy. These are nomination preferences, with actual geometry verification separate. See [terrain preference update](TERRAIN_PREFERENCE_UPDATE.md). Existing results retain their old policy and need a fresh matching computation identity for further work.

```sh
.venv/bin/python -m seed_search compatibility --output runs/compatibility.json
.venv/bin/python -m seed_search baseline --count 1000 --output runs/my-realm
.venv/bin/python -m seed_search status --run runs/my-realm
.venv/bin/python -m seed_search inventory --run runs/my-realm --limit 20
.venv/bin/python -m seed_search inventory --run runs/my-realm --candidate='<seed>:<sx>:<sz>' --all-starts
.venv/bin/python -m seed_search resume --run runs/my-realm --workers 24
.venv/bin/python -m seed_search terrain --run runs/my-realm --variant all --limit 1
.venv/bin/python -m seed_search results --run runs/my-realm --variant v2 --export
.venv/bin/python -m seed_search verify-terrain --run runs/my-realm --variant v2 --top 1
.venv/bin/python -m seed_search verify-biomes --run runs/my-realm --candidate='<seed>:<sx>:<sz>' --points points.json
.venv/bin/python -m seed_search verify-realm --run runs/my-realm --candidate='<seed>:<sx>:<sz>'
.venv/bin/python -m seed_search verify-caves --seed 12345 --stronghold-x 0 --stronghold-z 0 --provider predictor --output runs/manual-caves.json
```

Use `--config config/realm.yaml` before the command for the explicit profile. Above 1000 inputs, scans need `--prediction-scale`; the persisted compatibility report records that scale is prediction-only. Benchmarks explicitly exercise this mode. `rescore --run <run> --policy <profile.yaml>` changes recorded bonus/score weights without world-generation queries. An interrupted revision resumes with `rescore --run <run> --resume`, using its persisted policy; status remains available while ranking/generation are guarded. JSONL, CSV and readable summaries export every candidate pair, independent of shortlist limits. Export sets publish atomically through `results/current`; resolve that generation once when reading multiple files.

The default eligibility pass records one viable structure-start witness where presence is enough, and visits biome points in small batches until two wooded families are found. It retains incomplete scores and durable inventory tasks. `inventory` completes family-presence bonuses and the canonical biome sample; it does not imply complete start counts or actual generation. `--all-starts --candidate` saves a separate complete bounded predictor start audit. Terrain and verification nominations complete their candidate's scoring inventory before use. `search.inventory_mode: complete` remains available for complete baseline scans.

Biome sampling uses a versioned world-aligned lattice, caches exact full-seed points, and preserves in-border positive witnesses across overlapping borders. A bounded 128-point refinement can resolve additional wooded positives; misses remain pending. Nether and End samples are supplemental; End biome IDs are predictor classes, with actual Bedrock names unverified. All 22 exposed regional/start structure families are available, including buried treasure and the correctly initialized End dimension. Monster rooms and special terrain/decorator features still require separate support.

Docker runs only for explicitly selected verification requests, including optional random low-ranking audits to detect predictor misses. It does not run per baseline seed or automatically check cave diversity. Use `verify-terrain --top N --borderline N --unusual N --random N` to select observations under the persisted budget. The pinned runtime is BDS 1.26.52.3; the native MC_26_50 predictor is separately labeled approximate. The initial verifier limits one server and 16 tiles per request; larger footprints return partial status until their budget is explicitly expanded. Verified-generation ground masking, full-sized formation controls and rare-event recall remain gates, not inferred from the small extraction tests.

Verification skips cached observations by default. `--include-cached` explicitly reviews them without charging new-attempt slots; `--retry-failed` retries failures within the remaining budget. `calibration --run <run>` reports independent V1/V2 formation diagnostics only when complete actual geometry evidence is available. Partial results never become negative truth, and selected-cohort metrics are not population accuracy estimates.

Terrain work uses a fixed saved membership revision for both variants and durable center/resolution/halo queues. Repeated limited invocations advance a rotating pool cursor, retain lower-ranked and failed work, and reuse exact prediction rasters across variants. `--pool-revision pool-00000001` selects a saved membership; `--new-pool-revision` explicitly includes later baseline arrivals. Automatic halo expansion has a resource cap; `--continue-deferred-halos` permits one additional queued expansion per center. Status separates queued pending/deferred units from pool members whose work has not been initialized. Raw terrain storage cost and retention limits still need measurement and policy.

`verify-biomes` explicitly loads up to 16 points in one BDS world. `points.json` is an array such as `[[100,200],[-300,400]]`; every point must be inside the candidate's Stronghold-centered Realm. Stable observed names can establish two wooded families, while absent or unsupported samples stay unknown. Actual surface evidence and bonus intervals are saved separately from prediction scores and exposed in exports. This command never certifies the required structures, exhaustive biome coverage, or whole terrain geometry, and never invokes cave scanning.

Measured performance and exact supported/unverified scope are in [PERFORMANCE_BASELINE.md](PERFORMANCE_BASELINE.md), [REALM_IMPLEMENTATION_RESULTS.md](REALM_IMPLEMENTATION_RESULTS.md) and `runs/realm-implementation-2026-10-10/`.

The completed [master implementation](MASTER_IMPLEMENTATION_PLAN.md) adds mandatory final-square Fortress/Bastion prediction checks, exact eight-Y noise reuse and native quart deduplication. `config/realm.yaml` selects 18 OpenMP threads for its single-process terrain scheduler running alone; baseline remains 30 processes with one native/numerical thread each. Concurrent discovery/terrain/BDS needs a separately measured smaller profile. The code defaults retain serial compatibility. `terrain.scheduler: priority` enables the experimental durable 3:1 ranked/oldest dispatcher; rotation remains the measured default. Native thread counts and numerical-library limits are separate.

`native/build.py` builds a portable serial extension by default. On this Intel Mac, its optional host-only OpenMP build is:

```sh
ARCHFLAGS='-arch x86_64' SEED_SEARCH_OPENMP_PREFIX="$PWD/runs/master-implementation-2026-10-10/openmp/install" .venv/bin/python native/build.py
```

Keep that local runtime prefix while using the OpenMP extension. Its library hash is included in computation identity. Rebuild serial before moving to a machine without that runtime; unsupported multi-thread requests fail explicitly. No AVX ISA flag is shipped by default.

The bounded lower32 experiment has its own checkpoint and explicit raw-only ranking policy:

```sh
.venv/bin/python -m seed_search.realm.raw scan --count 4096 --threads 4 --output runs/raw-diagnostic
.venv/bin/python -m seed_search.realm.raw siblings --selection runs/raw-diagnostic/raw-selection.json --limit 128 --output runs/raw-siblings
.venv/bin/python -m seed_search raw-scan --count 4096 --mode presence --threads 18 --output runs/raw-presence
.venv/bin/python -m seed_search raw-scan --count 4096 --mode capped --ranking geometry --output runs/raw-geometry
.venv/bin/python -m seed_search raw-adaptive --selection runs/raw-geometry/geometry-selection.json --budget 4096 --output runs/adaptive-siblings
```

Use `--resume` with the original range/selection to finish interrupted chunks. Chunk/thread sizes may change while the selection identity stays fixed. Raw counts cover conservative envelopes for all permitted Stronghold centers; they cannot establish joint-center feasibility or generated-world absence. Full64 siblings pass the same required-structure baseline before terrain/verification. Scanner and terrain writes check physical workspace growth/free space as well as the existing logical raster cap. BDS checks host evidence and Docker filesystem headroom before generation. No automatic evidence deletion is performed.

Raw `presence`, `capped`, `complete`, and `reference` modes have different explicit contracts. Only capped/reference counts support the legacy density score. Geometry ranking and adaptive 1/4/16 sibling rounds are bounded experiments with an exploration reserve; independent full64 remains the default because the held-out CPU comparison did not meet the adoption gate. A full32 sweep is not justified by native throughput alone.

## Historical schema 3/4 profiles

The following sections document the preserved earlier profiles and their results. Their boundaries, categories, and defaults apply when an explicit historical configuration is supplied.

> **8 October implementation:** 2304 × 2304 Overworld / 928 × 928 Nether; four categories; mandatory Stronghold and Fortress; separate weighted biome bonus; bounded lower32/upper32 mode. Implementation and bounded verification are complete. Reference search is recommended after the two-key comparison; staged search remains available. The older sweep package is historical. No production sweep has started.

Local full signed-64-bit search for **Bedrock 26.52**, explicitly mapped to the pinned Bedrock fork's **MC_26_50** model. Matching-version Chunkbase is the external prediction reference. Actual Minecraft observations remain separate and optional. The Overworld square is 2304 × 2304; the Nether square is 928 × 928 at the Overworld center divided exactly by eight.

The pipeline searches structures-only locations, enclosed inner islands, ocean islands, and dry flat mountain basins. Bastion is optional and contributes at most two of the ten Nether proximity points. The default fast mode screens joint Stronghold/Fortress center windows before expensive terrain work. Missing predictions and incompatible nomination envelopes are saved in `stronghold-deferred.json` and `stronghold-deferred-seeds.txt`; they are not proof of absence. Recover those cases in a new bounded rank run with `config/review-all.yaml`. Known Stronghold misses mean fast mode can overlook worthy worlds. It then refines density coast connectivity, scores terrain and structures, ranks distinct seeds, and checkpoints completed indices in SQLite. This is a bounded heuristic search, not exhaustive coverage. The pinned density model excludes caves, aquifers, decoration and actual chunk interpolation; woodland is a surface-biome proxy.

Large sweeps require a readiness record matching configuration, source/native identity and verified evidence artifacts. Changing `large_search_enabled` cannot open the gate. Work status and finite pilot budgets are in [PROGRESS.md](PROGRESS.md); current results and commands are in [IMPLEMENTATION_RESULTS.md](IMPLEMENTATION_RESULTS.md) and [SWEEP_COMMANDS.md](SWEEP_COMMANDS.md). The production sweep remains unstarted.

## Commands

From this project directory, with the existing `.venv`:

```sh
.venv/bin/python -m seed_search doctor
.venv/bin/python -m seed_search regression --output runs/sweep-readiness/regression
.venv/bin/python -m pytest -q
.venv/bin/python -m seed_search search --count 10 --workers 4 --output runs/new-pilot
.venv/bin/python -m seed_search rank --seeds seeds.txt --output runs/new-ranking
.venv/bin/python -m seed_search resume --run runs/new-pilot
```

Specify `--config path.yaml` **before** the command. Automatic enumeration applies the SplitMix64 finalizer to `(index + run_key) mod 2^64`; indices never wrap in a run. Supplied seeds are one signed decimal integer per line. JSON/CSV/SQLite seeds are decimal text. Worker scheduling does not affect predictions or ranking.

`search --dry-run` validates the finite workload and readiness gate without starting it. `--stop-after N` saves a partial bounded run for resume verification. Resume checks the original configuration, complete backend/source identity and seed sequence; incompatible resumes fail. Each completed seed is committed independently, so interrupted or out-of-order work is rerun without skipping an unfinished index.

Outputs include all center metrics and explicit rejection/deferred reasons, separate numeric rankings and interval review lists, and shortlist folders with `candidate.json`, Overworld/Nether PNGs and `inspection.md`. Required disputed raw starts remain available for Chunkbase review; they cannot be presented as website-confirmed eligible first. Marker/start border membership is separate from accessible structure footprints.

Optimization details and controlled measurements are in [FILTER_OPTIMIZATION.md](FILTER_OPTIMIZATION.md). Raw MT structure layouts alone can share lower32-bit cache keys; full seeds still determine biome/terrain/viability, and the seed sequence is unchanged. The prior readiness records do not validate this changed algorithm; use the current command and record in [SWEEP_READINESS.md](SWEEP_READINESS.md).

Fresh actual website reviews can be recorded in the schema implemented by `review.py`, then imported:

```sh
.venv/bin/python -m seed_search review --run runs/new-pilot --evidence path/to/fresh-review.json
```

`chunkbase_checked` never becomes an actual-game observation. [Frozen external regression](fixtures/bedrock-26.52/chunkbase-accuracy-audit.json) contains 159 coordinate and 880 structure rows. Six structure discrepancies remain explicitly reviewable. Exact local baseline comparisons detect new drift even within per-type empirical marker conventions. Capped positive lists do not establish complete recall or a false-positive rate.

Diagnostic `benchmark`, `probe` and actual-phone `compare` commands remain available. Their historical artifacts are preserved; stage microbenchmarks alone do not establish end-to-end throughput. The user-skipped Overworld point is not requested again.

## Native build and provenance

The supported install/rebuild path is:

```sh
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m seed_search doctor
```

The dependency lock targets Intel macOS/Python 3.13. The vendored Bedrock backend commit is `294c72ab0392dd818a91d293dbd5774d4874d64b`. [vendor/backend.json](vendor/backend.json) records 33 source/license hashes. Compile flags are `-O3 -std=c11 -fwrapv`, without fast-math. The direct `native/build.py` compilation entry point now changes to the repository root before compiling; its standalone CFFI target is `_native.abi3.so`, matching the Python loader. Prefer the supported editable-install path.

Current implementation verification artifacts are under `runs/implementation-2026-10-08`; `runs/filter-optimization` contains historical measurements; earlier sweep/expansion/preflight/phone/audit evidence remains preserved. [SEARCH_TARGETS.md](SEARCH_TARGETS.md) defines distances and eligibility; [CHUNKBASE_WORKFLOW.md](CHUNKBASE_WORKFLOW.md) defines external review; [GOAL.md](GOAL.md) records the implementation goal and history.

## Distributed sweeps

See [DISTRIBUTED_README.md](DISTRIBUTED_README.md) for disjoint index ranges under a shared run key, per-machine native validation, safe SQLite backups and a read-only aggregate leaderboard. Production execution currently supports up to 34 native threads and 16,384 inputs per batch. The tuner reports bounded native-kernel comparisons; throughput on other machines and complete actual-world certification require their own evidence.

## Sweep verification

The prior `runs/filter-optimization/readiness.json` is incompatible with the new geometry and prediction identity. Final tests, two run keys with 256 inputs per search mode, three 20-seed quart comparisons, worker/resume tests and new-border external reviews are being sealed under `runs/implementation-2026-10-08`. Do not reuse the historical 2000-seed command. [SWEEP_READINESS.md](SWEEP_READINESS.md) tracks the gate.

## Enumeration and biome ranking

`full_64_bit_reference` is the default. `lower32_staged` examines 10,000 distinct raw low32 layouts, keeps 48 by raw cluster proximity plus 16 deterministic exploration selections, and evaluates four unique high32 siblings per layout. Raw placement is shared only for eight audited families. Strongholds, Trial Chambers, Mineshafts, terrain, biomes and final viability are evaluated for each complete seed. The strategy is biased; per-category useful yield must justify any default promotion.

All four categories keep the same mandatory structures. Structures-only retains a base score out of 30; terrain categories retain a base out of 100. A separate sampled resource-family bonus adds at most five points. Surface, Nether and unmeasured cave coverage are labeled separately; biome variety never repairs failed eligibility. Weights and sampling are documented in [BIOME_DIVERSITY_PLAN.md](BIOME_DIVERSITY_PLAN.md). Exact quart reuse shares raw-land booleans only; height and biome sample coordinates remain independent.

## Current landscape and structure policy

`search.example.yaml` enables four categories. The three terrain types share a finite eight-refinement budget; structures-only has its own two-center budget and skips terrain qualification. `enclosed_island` preserves separation, surrounding water/mountains and external woodland; `ocean_island` requires predicted separation plus majority ocean biomes and density water over a 1400-square window and counts woodland on the island; `mountain_basin` checks a 192-block-wide dry/gentle core and a mountain ring within 800 blocks that is connected to the floor without an inner island/moat. Defaults are tunable preferences, with finite raster/sampling uncertainty exposed. Each type has a separate distinct-seed shortlist.

Fortress and Stronghold markers must be eligible inside their respective exact squares. Missing local Strongholds remain unresolved because the enumerator is incomplete. A missing Bastion cannot veto a candidate. Website review must include Stronghold and Fortress; required checks depend on landscape type. Nothing promotes website evidence to actual Minecraft evidence.

A bounded 64 MiB exact per-seed cache separates seeds, operations and height strides. Analysis persists the sampled candidate terrain under `terrain-cache`; report generation verifies its identity and content hash before reuse. Completed-map cache reuse is invalidated by prediction/configuration/renderer/review changes. The original baseline configuration is retained at `runs/sweep-readiness/config/sweep.yaml` for regression.
