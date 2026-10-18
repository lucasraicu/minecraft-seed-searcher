# Personal Blueprint + Public Seed Catalog Implementation Plan

> Current consolidated proposal: [PUBLIC_CATALOG_SYSTEM_SPEC.md](PUBLIC_CATALOG_SYSTEM_SPEC.md), with [versioned contract artifacts](docs/catalog/v1/README.md). It supersedes conflicting public sizes, anchor-mode activation, retention-capacity and storage details below. This earlier phase plan remains design context; no catalog implementation or billing is activated by the specification.

Date: 2026-10-17. Status: **proposed implementation, not implemented**.

## 1. Product decision

Run two independent selection policies using compatible world observations:

- **Personal realm:** preserve Lucas's current `dynamic-envelope-2048-v3` mandatory floors, 1,250-point additive bonus model, center selection/refinement, and Top-50 ordering.
- **Public catalog:** retain varied seed-center candidates without requiring Lucas's floors. Customers search this catalog using explicit requirements and their own bonus priorities.

Public promise: “Find matching seed locations in our catalog for this Bedrock version.” No promise of every possible seed, complete biome absence, optimal scenery, or globally optimal settlement centers. The public product initially searches predicted observations; verified facts get separate evidence badges.

Build a CPU-only pilot first. No GPU purchase, production rewrite, paid launch, or price change is authorized by this plan. Numerical capacities, prices, and performance gates below are proposed defaults to test, not measured results.

## 2. Preserve the personal framework

Use the actual `dynamic_v3_blueprint_config()` in `src/seed_search/realm/config.py`; do not use historical `config/realm_1664.yaml` as the active policy.

Freeze a versioned personal policy snapshot containing configuration, scoring functions/build hashes, and the total ordering. Preserve:

| Property | Personal policy |
|---|---|
| Overworld discovery envelope | `[-2000,2000)` on both axes: 4000×4000 |
| Playable square | 2048×2048, half-open boundaries |
| Legal center domain | `[-976,976]²` |
| Nether playable square | Existing 1024×1024 policy and coordinate mapping |
| Mandatory Overworld floors | Stronghold 1; mansion 1; villages 6; trials 8; ancient cities 2; pyramid 1; monument 1; ruined portals 8; shipwrecks 4; mineshafts 10; outpost 1 |
| Mandatory Nether floors | Fortress 1; bastions 2 |
| Bonus architecture | Core 600 + optional 250 + biome 265 + spatial/Nether 135 = 1,250 maximum |
| Miss budget / leaderboard | Zero misses; Top 50 under existing deterministic rank |
| Center policy | Existing centroid weights and native 16-grid plus declared local 8-grid refinement |

Public preferences never modify these weights, floors, or cutoff. A customer subscription cannot change Lucas's leaderboard. Public discoveries only enter personal consideration after a complete evaluation under the frozen personal policy; public scores cannot be compared to personal bonus points.

Persist `personal_policy_id`, score breakdown, original/refined center, refinement scope, and prediction/verification evidence for personal results. Export personal finalists to the catalog if desired, but label their origin and keep personal favorites pinned independently of public retention capacity.

## 3. Exact customer selections for the first release

### Screen 1: choose the world and reference location

1. **Edition:** Bedrock only. Java is unavailable until separately implemented and tested.
2. **Game version:** select from exact version labels backed by the capability registry and populated catalog. No automatic assumption that a new version matches an old one.
3. **Search around:** `Recommended settlement` (default) or `World spawn` (only for records with separately established spawn coordinates and sufficient coverage).
4. **Play style:** `Custom`, `Balanced survival`, `Village life`, `Explorer`, `Trial adventurer`, `Ocean explorer`, or `Biome variety`. Presets fill preference rows; they do not constrain the catalog to one internal profile.

Explain recommended settlement: “Results include a suggested base location. It may be away from where you first spawn.” Show spawn-to-base distance only when spawn is known. Never call origin (0,0) world spawn.

### Screen 2: requirements and preferences

Initial structure picker: village, trial chamber, ancient city, woodland mansion, ocean monument, outpost, desert pyramid, jungle temple, swamp hut, igloo, trail ruins, ruined portal, shipwreck, mineshaft. Igloo basement is a separate capability-dependent variant, never inferred from an igloo start. Stronghold can appear as predicted map information but is not a launch mandatory-count/absence filter because enumeration is known incomplete. Nether search is deferred; personal Nether scoring continues unchanged.

Each structure row selects:

| Control | Exact values / interpretation |
|---|---|
| Rule | `Must have` or `Prefer` |
| Count | Integer 1–16; at least that many distinct predicted starts |
| Distance | 256, 512, or 1024 blocks from the selected anchor |
| Preference importance | Low = 1, Medium = 3, High = 5; only for Prefer |

Distances are horizontal Euclidean distances, not travel paths. Count means all N starts lie within the selected circle, not that the nearest one does. A 1024-radius circle is different from the personal 2048-square window. Only evaluate an anchor if the whole requested circle is covered; return unknown otherwise.

Biome picker: cherry grove, mushroom fields, bamboo jungle, desert, badlands, snowy terrain, mangrove swamp, plus ordinary forest/plains. Families resolve through a versioned ID mapping. Each row selects Must have / Prefer, distance 256/512/1024, and importance for Prefer. “Have” means an observed biome witness within distance, with sampling method shown. Sample absence does not establish biome absence. For initial cost control, use 64-block sampled predictor observations with explicit Y planes/provenance; label these as biome observations, not guaranteed surface terrain. Surface-only claims require a surface-query capability that has been separately validated.

Do not expose hard “no biome,” “no structure,” exact island shape, flat buildable area, intact portal room, loot guarantees, or farm functionality at launch. Current capabilities do not establish those negatives/physical properties. Later “prefer fewer predicted structures” can be added as an explicitly predictive preference with coverage metadata, not an absolute absence guarantee.

### Screen 3: results and saved searches

Show: seed, exact version, anchor coordinates, map, each requirement's evidence, preference match score, observation scope, and verification labels. Allow copy seed on both tiers. A result may have several matching centers; group by seed and expose alternatives.

No matches: show “No matches in our current catalog,” identify optional relaxations, and require a user action to apply them. Paid users can save the unchanged request for future-match alerts. No per-request full seed sweep is included in either tier.

## 4. Public preference score: additive bonuses without personal floors

Personal scoring remains byte-for-byte policy compatible. Public scoring uses the same understandable pattern—qualify first, then add bonuses—with a separate versioned score:

- A Must-have row is a predicate, never compensated for by another bonus.
- For a structure preference asking for N starts within R, utility `u = min(observed_count_within_R / N, 1)`.
- For a biome preference, utility `u = 1` if an eligible witness exists within R, otherwise 0. This is an observed-data score, not proof of absence.
- Public match score `100 * sum(importance * u) / sum(importance)`; show per-row contributions. Compute ordering with rational/integer arithmetic where possible, round only for display.
- With no preference rows, order by selected preset score; Custom with no preferences uses Balanced survival and labels this fallback.
- Ties: mean normalized nearest distance for requested features (missing = 1), then canonical seed ID, then center X/Z. Unknown required facts never pass.

Example: Must have village ≥1 within 512; Prefer trials ≥2 within 1024 with importance 5; Prefer cherry witness within 512 with importance 3. If both trials and cherry match, score 100. With one trial and cherry, score 68.75. Without the required village, do not return the result regardless of bonus score.

The score is relative to this request, not a universal seed-quality rating. Cache by canonical request, exact version, catalog snapshot, scoring revision, and evidence policy.

## 5. Exact public retention policy v1

### 5.1 Evaluate a declared finite set of centers

For the public pilot, evaluate the Cartesian product of axis coordinates `[-976,-768,-512,-256,0,256,512,768,976]`: 81 settlement anchors inside the existing envelope. This is intentionally different from personal center optimization. Preserve every one of these anchors' summaries for retained worlds; this lets new preferences choose among all 81, not merely yesterday's winning center.

Spawn may be added as an 82nd anchor only when its coordinates are established and requested coverage exists. Do not generate a false negative when spawn falls outside the observed envelope. User-specified arbitrary coordinates and new center optimization are later features; the first product ranks saved anchors only and says so.

Compute observations independently of personal floors. Full public observation is expensive: do not reuse throughput numbers measured for early-reject personal screening. Missing/incomplete feature extractions remain unknown and cannot yield a purportedly complete inventory.

### 5.2 Three bounded buckets plus a reference sample

All capacities apply per edition/game-version/generator-revision catalog and are **world capacities**, deduplicated by world identity. A seed's best qualifying anchor supplies its rank in a group; keep its other anchor summaries as well.

**A. Specialists: up to 1,000 worlds per feature per objective.** Use the 14 launch structure categories. For each category, maintain a count objective and a proximity objective (28 lists; at most 28,000 worlds before deduplication).

Count admission minima within 1024 of any anchor:

| Feature | Minimum count |
|---|---:|
| Village | 6 |
| Trial chamber | 4 |
| Ancient city | 2 |
| Mansion | 1 |
| Monument | 2 |
| Outpost | 2 |
| Desert pyramid | 2 |
| Jungle temple | 2 |
| Swamp hut | 2 |
| Igloo | 2 |
| Trail ruins | 2 |
| Ruined portal | 6 |
| Shipwreck | 4 |
| Mineshaft | 8 |

Rank count lists by count descending, distance to the Nth qualifying start ascending, then canonical seed ID. Proximity admission requires at least one start within 256; rank by nearest distance ascending, count within 1024 descending, then seed ID. Thresholds are provisional policy choices, not percentile estimates. A matching world can still be evicted when its list fills; do not promise retention of every specialist hit.

**B. Play styles: 16 profiles × top 1,000 worlds.** Use normalized features below and the coefficient table. The 16 profiles are internal retention directions, independent of subscription tier. Evaluate each profile over all declared anchors; retain each world's maximum with deterministic ties.

Features within 1024: `V=min(villages/6,1)`, `T=min(trials/4,1)`, `A=min(cities/2,1)`, `O=min((monuments+shipwrecks)/6,1)`, `E=min(distinct observed launch structure types/14,1)`, `B=min(observed biome families/8,1)`. `H=max(0,1-nearest_village_distance/1024)` with 0 if missing. `R=min((jungle_temples+swamp_huts+igloos+trail_ruins)/4,1)`. Utilities are explicitly predictive and saturating.

| Internal profile | V | T | A | O | E | B | H | R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Balanced survival | 2 | 1 | 1 | 1 | 2 | 2 | 2 | 1 |
| Village life | 5 | 0 | 0 | 0 | 1 | 1 | 5 | 0 |
| Trial adventurer | 1 | 5 | 1 | 0 | 1 | 1 | 2 | 0 |
| Ancient-city explorer | 1 | 1 | 5 | 0 | 1 | 1 | 1 | 0 |
| Ocean explorer | 0 | 0 | 0 | 5 | 2 | 2 | 1 | 1 |
| Biome variety | 0 | 0 | 0 | 1 | 1 | 5 | 1 | 0 |
| Structure collector | 1 | 1 | 1 | 1 | 5 | 1 | 0 | 2 |
| Archaeology | 0 | 0 | 0 | 0 | 2 | 2 | 1 | 5 |
| Compact starter | 2 | 1 | 0 | 0 | 1 | 1 | 5 | 0 |
| Village and trials | 4 | 4 | 0 | 0 | 1 | 1 | 2 | 0 |
| Village and ocean | 4 | 0 | 0 | 4 | 1 | 1 | 2 | 0 |
| Village and biomes | 4 | 0 | 0 | 0 | 1 | 4 | 2 | 0 |
| Cities and trials | 0 | 4 | 4 | 0 | 1 | 1 | 1 | 0 |
| Ocean and biomes | 0 | 0 | 0 | 4 | 1 | 4 | 1 | 0 |
| Rare structures and biomes | 0 | 0 | 0 | 0 | 1 | 4 | 1 | 4 |
| Multiplayer variety | 4 | 3 | 1 | 1 | 3 | 3 | 2 | 1 |

Normalize by sum of coefficients. These are explicit starting weights for coverage experiments, not empirically optimal utilities. They do not change Lucas's weights.

**C. Combination diversity: 256 cells × up to 64 worlds.** Use an actual eight-boolean tuple, not a hash masquerading as a unique combination: observed cherry, mushroom, jungle/bamboo, snowy family, village, trial, ancient city, monument within 1024 of an anchor. Each exact tuple defines a cell. A world may qualify for multiple cells through different anchors.

Within each cell retain the union of top-16 distinct worlds for Balanced survival, Biome variety, Compact starter, and Archaeology. Capacity is at most 64 per cell, 16,384 total before deduplication. Cell membership requires completed declared sampling; false bits mean “not observed,” not absent. This captures only these eight attributes and does not guarantee all rare combinations.

**Reference sample:** additionally retain the 10,000 smallest stable hash priorities of evaluated seed IDs, independent of scores, across the full evaluated population. Use a policy-pinned hash and salt. Selection for the sample occurs before any relevance gate, with full extraction for selected worlds. The sample can overlap buckets.

Initial upper bound: 28,000 + 16,000 + 16,384 + 10,000 = **70,384 distinct public worlds per version/model**, plus pinned personal results and immutable user-owned snapshots. Do not confuse this bounded pilot catalog with a promised percentage of seeds scanned. Increase caps only after storage and query-recall measurements justify it.

### 5.3 Distributed correctness

For each fixed list, workers keep the same K as the global list, deduplicating by world ID before capacity truncation. Merge by exactly the same total ordering. For diversity, merge the four top-16 lists separately. Reference sample merges by stable hash priority. Shards must partition full seed identities or reconcile duplicates before truncation. Do not merge local 4,096 into a supposedly exact global 50,000.

Repeated incremental scans merge immutable segment contributions idempotently. Pinning for a customer does not manipulate public ranking. Eviction removes a live membership; only garbage-collect world data after all memberships and snapshot references are gone.

## 6. Persistence and retrieval

Add a new `src/seed_search/catalog/` package; do not relax personal `validate_blueprint_config()` to accept arbitrary public weights.

| Entity | Required fields |
|---|---|
| world | ID; signed int64 seed; edition; game version; generator/build identity; discovered time; covered bounds; extraction status |
| structure observation | World; dimension; type/variant; unique start identity; X/Z and optional Y; prediction/evidence status |
| biome observation | World; biome ID/family; X/Y/Z; query method; stride; evidence source |
| anchor | World; anchor ID/kind; exact block X/Z; geometry; summary revision; coverage; feature summaries |
| membership | World; bucket/list/cell; policy ID; qualifying anchor; fixed rank tuple |
| scan shard | Full-seed domain/range; policy/model identities; leased generation; segment checksum; completion receipt |
| saved search | User; canonical request; request revision; notification opt-in; last catalog snapshot checked |
| saved result | User; world/anchor; request and score explanation snapshot; source catalog/evidence revisions |
| entitlement | User; tier; effective dates; provider event ID; export/search counters |

Represent seed IDs as decimal strings in JSON/JavaScript to avoid loss of 64-bit integer precision. Keep coordinates in integer blocks. Do not saturate counts at 15 or turn unknown distances into zero. Enforce uniqueness for duplicate structure starts.

Pilot: keep SQLite as the transactional catalog/control store on one service host; use indexed world/anchor summaries plus compressed observation artifacts, and batch writes. Public ingestion has its own database. Avoid a new binary `.sseg` decoder in v1. Add immutable Parquet snapshots for analytics and a DuckDB query benchmark when observed catalog scale warrants it; do not assume compression or latency. DuckDB supports column/filter pushdown: https://duckdb.org/docs/current/data/parquet/overview .

Publish an artifact by writing a temporary file, flushing/fsyncing it, atomically renaming, ensuring directory durability, and transactionally referencing its checksum in the manifest. Reconcile orphan files and stale leases on restart. A SQLite transaction cannot atomically commit a separate file by itself. Back up metadata and referenced artifacts as one snapshot and test restoration.

Query summaries must be conservative: prefilters cannot omit anchors that satisfy supported predicates. Evaluate coordinate-based counts and requested biome witnesses for all surviving anchors; rank all eligible candidates under the request. Do not simply verify the first 25 and call that an exact catalog-wide top 5. Group by world only after choosing its best eligible anchor. Catalog-wide exactness applies only to saved anchors and declared observation semantics.

Public endpoints: `GET /api/catalog/capabilities`, `POST /api/catalog/search`, `GET /api/catalog/worlds/{id}`, `POST /api/catalog/saved-searches`, `POST /api/catalog/saved-results`, `POST /api/catalog/exports`. Require server-side capability checks, entitlement limits, user ownership checks, and query validation. Keep personal scan-control/admin endpoints private; public users cannot submit shell commands, filesystem paths, raw SQL, or launch the personal scanner.

## 7. Free versus paid: proposed launch offer

Test these prices with prospective users; they are hypotheses, not market-derived optimal prices. One product feature set with two purchase options avoids charging casual players for an unwanted recurring subscription.

| Feature | Free account | Plus access |
|---|---|---|
| Price hypothesis | $0 | $4.99/month recurring, or $2.99 for a non-renewing 7-day pass |
| Daily searches | 20 | 200 |
| Total requirement/preference rows | 3 | 12 |
| Presets and exact-version selection | All launch presets | Same |
| Returned worlds per search | Top 5 | Top 50, pagination within that cap |
| Seed copy / basic coordinate map | Included | Included |
| Importance controls | Low/Medium/High | Same; more rows, not a different truth standard |
| Saved favorites | 10 | 200 |
| Saved search alerts | None | 20; once-daily new-match digest, explicit opt-in |
| Side-by-side comparison | 2 worlds | 5 worlds |
| Exports | None | 20 reports/day; map + coordinate CSV + evidence summary |
| On-demand scanning / BDS certification | Not included | Not included |

All tiers use the same evidence labels, capability limits, and scoring for an identical request. Do not sell unsupported accuracy as a premium benefit. Requests beyond limits return an understandable upgrade or reset-time response, not partial predicates. Cache repeated queries but rate-limit request processing too; budget expensive queries by measured cost if needed.

Exported reports and saved favorites pin reproducible snapshots. Cancellation stops new Plus features after expiry; preserve read/copy access to already-saved results and downloaded reports. Do not silently delete favorites above the free limit; block new additions until under it. Saved-search alerts pause on expiry.

Track trial-to-paid conversion, weekly repeat use, export use, unmet-query frequency, and cost per active paying account. Test subscription versus pass usage before adding an annual plan or “unlimited” tier. Brand and checkout must be reviewed against current Minecraft usage terms before commercial launch; this document does not establish legal permission: https://www.minecraft.net/en-us/usage-guidelines .

## 8. Impact on Lucas's seed selection and machine

| Situation | Personal outcome | Public outcome |
|---|---|---|
| Seed meets all personal floors and scores highly | Normal Top-50 consideration/refinement | Can also enter public buckets |
| Mansion missing but cherry/village layout is excellent | Still rejected personally | May be saved for public users |
| Seed is popular with customers but poor for Lucas | No promotion or weight change | Ranked for their requests |
| Public seed looks promising for the realm | Run full personal evaluator before admission | Original public record remains |
| Customer chooses a different center | Personal refined center remains | Separate anchor selection |
| Customer asks for unsupported terrain | No scoring changes | Explain unavailable filter |

Default scheduler: **personal-only remains the existing default; public pilot is explicitly enabled and runs when personal scanning is paused.** This avoids claiming that public extraction is free. If concurrent operation is later desired, start with 80% personal / 20% public CPU-time allocation, pin a thread budget to prevent oversubscription, and measure both workloads. Roughly 20% less personal CPU time means roughly 25% longer completion time if throughput scales linearly; cache/memory contention may make it worse. This is a planning estimate, not a benchmark.

Public data starts with a 20 GiB pilot storage budget. Pause ingestion at 80% budget until retention/storage is reviewed; never delete pinned results to keep scanning. Actual bytes/world include all 81 anchors and biome observations, not just a small feature vector. Record p50/p95 bytes/world, scan time, and per-query CPU cost before increasing capacity or adding versions.

Only share read-only observation caches across modes after including edition/version/model/seed/dimension/bounds/query method in cache keys and proving parity. Personal rejection receipts cannot be treated as completed public evaluations. Old discarded seeds need reprocessing to obtain public features; merely changing storage cannot recover them.

## 9. Delivery phases and concrete acceptance gates

| Phase | Proposed implementation targets | Deliverable / completion gate |
|---|---|---|
| 0. Freeze personal behavior | `realm/config.py`, `realm/blueprint.py`, `realm/dynamic.py`, `tests/test_catalog_personal_isolation.py` | Snapshot identities and representative qualified/rejected fixtures; same personal eligibility, scores, centers, and ordering with catalog disabled. Do not alter weights. |
| 1. Contracts and storage | New `catalog/models.py`, `capabilities.py`, `store.py`; `config/catalog_v1.json` | Typed versioned world/anchor/request schemas; integer seed round-trip; evidence/unknown handling; unique observations; backups and restart recovery tested. |
| 2. Reference extraction | New `catalog/extract.py`, `scripts/build_catalog_reference.py`; reuse backend observation APIs | Independent deterministic cohorts totaling 10,000 full seed IDs, fully observed without personal floors; store all worlds and 81 anchors as reference. Start with 100 to measure cost and ensure the 20 GiB budget is sufficient. |
| 3. Admission and recall | New `catalog/admission.py`, `profiles.py`, `scripts/evaluate_catalog_retention.py` | Exact A/B/C/hash rules and distributed replay; tune on one cohort, evaluate on held-out seeds and requests. No false claim that a non-filling 10k pilot validates the production 70k capacity. |
| 4. Search API and UI | New `catalog/query.py`; separate router integrated with `src/seed_search/web/server.py`; new `web-ui/src/catalog/` components | Three-screen flow, per-row score explanation, exact saved-anchor ranking, deduplication, no-match handling, save/copy, and private personal admin surface. |
| 5. Free private beta | New query feedback and usage metrics | At least 20 testers submit their own searches; investigate coverage gaps and confusion between spawn/base/prediction. No payment required during validation. |
| 6. Paid access | New entitlement layer and billing adapter, saved-search scheduler, export worker | Idempotent billing events, ownership isolation, limits, cancellation behavior, consent, snapshot exports, and cost instrumentation tested. Payment integration remains disabled until explicitly launched. |
| 7. Scale | Native public extraction only if profiling warrants; Parquet/DuckDB query prototype | Increase scan/capacity in measured steps, validate restore, and publish catalog coverage/latency limits. GPU support is a separate project. |

Reference evaluation: define at least 200 requests spanning single features, paired/triple combinations, strict distances, biome observations, presets, and hard-to-match requests. Split tuning/holdout queries and seeds. Supplement with actual tester queries. Exclude impossible/reference-empty queries from recall denominators but report them separately.

Measure (a) fraction of reference-nonempty requests still nonempty after retention, (b) recall of reference top-10 unique worlds with deterministic tie handling, (c) normalized preference-score regret, (d) per-query-family failures, and (e) bytes and extraction time. Initial launch targets: ≥95% nonempty preservation and ≥90% mean top-10 recall on held-out supported queries, with each supported query family reported separately. These are engineering acceptance goals, not universal guarantees. If failed, expand capacity, add diversity objectives, or narrow the advertised feature scope.

Since 10,000 reference worlds cannot stress a 70,384-world upper bound, run explicitly labeled smaller-cap retention experiments first, then a larger-than-capacity full-observation reference experiment before making production retention claims. Do not present all-seeds-retained recall as successful selection validation.

Search target: p95 ≤1 second for supported queries at five concurrent users on declared hardware, against a declared-size snapshot. Map/report generation may be asynchronous. Measure worst-case low-selectivity queries and query limits; no <4 ms promise. Test exact count distances, boundaries, no-match queries, unknowns, version mismatches, 64-bit seeds, and independent user ownership. Personal-mode performance regression target: ≤5% change with public mode disabled on matched repeated benchmarks; larger changes must be investigated.

## 10. What to implement first

First change set: personal policy snapshot + isolated catalog schemas + 100-seed extraction benchmark. Second: complete the 10,000-seed reference, implement bounded buckets, and report query coverage. Third: public UI and free beta. Paid functionality comes after coverage, performance, and observed demand.

This plan adds a second purpose to the engine while preserving Lucas's original selection purpose. It does not certify current weights as optimal or treat the existing implementation-plan completion banner as proof of end-to-end BDS verification.
