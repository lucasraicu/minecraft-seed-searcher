# Public catalog: player contract and retention policy draft

> Current consolidated proposal: [PUBLIC_CATALOG_SYSTEM_SPEC.md](PUBLIC_CATALOG_SYSTEM_SPEC.md). It defines the exact three border sizes, current Origin/Recommended modes with spawn gated on cost/accuracy, complete UI, retention capacities, billing, and storage contracts. Its decisions take precedence where this earlier player draft differs.

Date: 2026-10-17. Status: proposed product contract; not implemented or validated demand. Audience: a broad catalog across play styles, as selected by Lucas. This elaborates [PUBLIC_CATALOG_IMPLEMENTATION_PLAN.md](PUBLIC_CATALOG_IMPLEMENTATION_PLAN.md) and the [architecture review](reviews/catalog-architecture-2026-10-17/REVIEW.md). It does not replace the personal search policy.

## 1. Start with the questions players can ask

Proposed promise: **Choose a planned world border and the features you want near your base or inside that border, compare matching worlds on a map, and copy the seed and coordinates for your supported Bedrock version.**

The initial product searches a catalog of observed locations. It does not search every possible Minecraft seed on demand. A suggested base location is not necessarily world spawn. Results carry prediction and verification information; a predicted start is not certified physical generation.

Define the supported query vocabulary before choosing a physical database format. The logical schema should preserve reusable world facts; the serving index should make the supported queries inexpensive.

## 2. Player-facing search format

Use one editable search form with optional preset starting points. Do not ask players to choose an internal retention bucket or a universal quality score.

| Player question | Launch control | Exact meaning |
|---|---|---|
| Which Minecraft world? | Bedrock + supported exact version | Return only records compatible with that declared scope |
| How big is my playable world? | 2048, 4096, or 8192 blocks per side | A square border centered on the selected spawn/base anchor for the initial layout model |
| Where do I want to start? | Find me a place to settle; Origin advanced; Spawn gated | Origin fixes the anchor at (0,0); settlement ranks saved anchors by the player's request; spawn needs validation |
| What must be nearby? | Add a structure or biome row; choose Required | Every required row must pass at one anchor |
| How many? | Structures: at least 1–16 | Count distinct predicted starts; biome rows use an eligible observed witness |
| Where must that feature be? | Near base: 256/512/1024; or Anywhere inside border | Near uses a horizontal circle, clipped to the border; inside border uses the square |
| What would make a match better? | Add Preferred rows, with Low/Medium/High importance | Rank qualifying anchors by the existing proposed request-relative utility |
| What else should affect my result? | Unselected features are ignored | No hidden personal mansion, Nether, or biome-palette requirements |

“Find me a place to settle” is the launch default while spawn integration is unavailable. The [independent audit](reviews/spawn-validation-2026-10-17/README.md) supports adding **Estimated spawn**: “Search around estimated world spawn. Your actual starting position may differ.” It found all 108 estimates within 11.32 horizontal blocks of the default world-spawn reference on BDS 1.26.52.3; that is an observed result, not an error guarantee. Actual-player placement remains unvalidated, and integration/coverage/full-record cost gates remain open. Origin is an advanced fixed-center option. Preserve spawn as a gated capability: its estimate must pass measured Bedrock accuracy/cost checks before becoming a general public mode, and established observations remain separately labeled. Do not present an unavailable spawn mode as working. For records with verified spawn, a future base-distance-from-spawn filter is a separate field and predicate, not distance from origin. Show unknown when unavailable.

For Start at spawn, the requested anchor is fixed: never move it to a denser location and still label the result spawn. For Find me a place to settle, first eliminate saved layouts that fail any required row, then rank the eligible layouts by the player's preferred rows and the declared deterministic tie rules. With no preferred rows, use the visibly labeled Balanced survival fallback. This finds the best matching **saved** location, not an optimum over every possible coordinate.

Density is one possible preference or preset, not the definition of a good public center. A builder's biome request, an ocean player's monument request, and a village-focused request can select different centers in the same seed. Keep the declared anchor summaries rather than replacing them with one permanently chosen densest center. Show spawn-to-base distance whenever established spawn data exists; otherwise show it as unknown. Choosing a recommended base does not relocate the player in game automatically.

Example player request:

> Find a 4096-by-4096 world where I have at least three villages within 512 blocks, an observed cherry grove within 256, and a monument somewhere inside the border. Prefer two trial chambers within 1024. I can move to the recommended base coordinates.

The result must satisfy every required row under the **same** base/border layout. A village-rich location on one side of the world and cherry on the other side do not combine into a nearby match. A monument anywhere inside the border is intentionally a looser condition.

Default users can begin with one or two rows. An advanced view exposes the complete supported menu without forcing everyone through every setting. Show numerical distances alongside any short labels such as “close.” Map rings should use the same geometry as the query.

As a proposed extension to the original plan, let one biome row select several acceptable families: “cherry **or** mushroom within 256.” A row matches when any selected family has an eligible witness. Separate required rows remain AND conditions: “cherry within 256 **and** mushroom within 1024.” A preferred alternatives row earns its utility once, even if several alternatives match; use the nearest qualifying selected-family witness for its distance tie component. This positive OR needs no new world observations beyond the individual family summaries. Keep arbitrary nested expressions out of the initial interface.

### World border profiles and extraction cost

Lucas requested 4096 and 8192 options in addition to the existing 2048 size. Treat these as **side lengths**, not radii. The public player's base is also the border center in this initial contract; independent base and border centers are a later relationship capability. This is a planned playable-area/search setting. Applying the border in game requires a supported border setup; changing the picker does not change Minecraft seed generation.

| Border side | Center-to-edge distance | Playable block columns | Area relative to 2048 |
|---|---:|---:|---:|
| 2048 | 1024 | 4,194,304 | 1x |
| 4096 | 2048 | 16,777,216 | 4x |
| 8192 | 4096 | 67,108,864 | 16x |

For center `(cx, cz)` and side `S`, border membership is the half-open square `[cx-S/2,cx+S/2) × [cz-S/2,cz+S/2)`. A nearby row additionally requires `dx²+dz² <= R²`. All counted starts/witnesses must be inside the selected border. This explicitly handles the positive-edge point of a radius-1024 circle in a 2048 border. The map must show the same clipping.

Increasing the border does not turn “village within 512” into “village somewhere within 4096.” Near-base requirements remain the same distances. An Anywhere inside border row is a separate scope with no radius value. Every request records side length, center policy, scope per row, and geometry revision. No selected feature can be satisfied outside the playable border.

Use one world observation set and several derived layout summaries. Observations for an 8192 layout can supply nested 4096/2048 layouts at the same center and compatible observation method. Do not create three independent copies of the raw seed observations. Additional summaries/memberships may scale with three profiles, but extraction and raw observation storage depend mainly on covered area, feature density, and sampling resolution. Independent full scans of the three nested squares would cover 1+4+16=21 units of area; sharing the largest square covers 16. These are geometric comparisons, not runtime predictions.

The current extractor already observes a 4000-side macro envelope around the origin for the 81 candidate centers. Holding center coordinates in `[-976,976]²`, the union of side-S layouts has side `S+1952`. Thus the three required square observation envelopes are 4000, 6048, and 10144 blocks per side. The largest envelope has about 6.43 times the area of the current 4000-square envelope. This is a different baseline from comparing a single 8192 playable square to a single 2048 square. Actual runtime and bytes must be benchmarked; structure placement, lazy evaluation, and compression do not scale identically.

The current personal kernel hardcodes the 4000 envelope, 64-side prefix workspace, and personal center-domain derivation. A 4096 or 8192 profile is not a safe configuration-only change. Parameterize public bounds and workspaces in the independent catalog extractor; preserve the personal policy and kernel behavior. Public Nether behavior remains deferred; no Overworld picker implicitly changes personal Nether borders.

Retain useful results separately for each world-size scope. A large world's total structure count should not evict every compact-world specialist. Deduplicate the underlying world data across memberships. Fixed-radius objectives whose border-clipped geometry and rank are identical can share results rather than duplicating lists mechanically.

Proposed rollout: keep all three sizes in the product contract; implement complete 2048 reference coverage first and benchmark expansion to 4096/8192 on the same seed cohort. Enable inside-border predicates for a size only when coverage and extraction semantics support it. A larger preview outline with only central observations is not a complete larger-world inventory. Full large-area extraction can be scheduled separately; a weak 2048 center cannot by itself justify rejecting an 8192 candidate whose useful features may lie farther out.

### Presets for broad play styles

These are proposed starting hypotheses for interviews, not measured audience segments or restrictions on catalog membership. Presets populate editable rows. A player can combine needs from several play styles.

| Starting point | Example preference rows | Capability limit |
|---|---|---|
| Easy survival start | Village near base; ruined portal nearby | No promise of safety, village habitability, or portal usability |
| Build near a favorite biome | Player-selected cherry, mushroom, badlands, mangrove, or other supported family near base | Nearby observation does not establish base surface biome, flatness, or biome size |
| Adventure | Trials, ancient cities, temples, and mansion proximity | No loot, intactness, or navigability guarantee |
| Exploration | Several selected biome families and structure types within reach | Only declared families and observation coverage participate |
| Ocean exploration | Monument and shipwreck preferences | No island, coast, beach, or water-access geometry claim |
| Technical planning | Outpost or swamp-hut locations near base | Predicted positions do not establish functioning farms or an AFK-compatible cluster |

Leave requirements empty until the player explicitly makes one required, or clearly show any requirements a selected preset adds. All rows remain visible and editable. Preset selection never secretly modifies personal scoring.

### Nearby, inside, and beside are different requests

| Player wording | Required observation | Launch position |
|---|---|---|
| Cherry grove within 256 of my base | Eligible biome witness coordinates and distance to anchor | Supported under declared predictor/sampling semantics |
| My base is inside cherry grove | Validated surface-biome query at the actual base location | Defer pending surface capability validation |
| A village beside cherry grove | Structure-relative biome observations and a defined distance from the village | Later relationship query; two independent base-radius predicates do not imply it |
| Several huts close enough for a farm | Structure layout, pair/cluster geometry, and version-specific farm evidence | Later dedicated capability |
| A large cherry grove or flat build area | Surface mapping plus patch connectivity/area or slope observations | Defer; a biome bit or single witness is insufficient |

This distinction is particularly important for a broad catalog: builders may value area and shape more than another structure, while technical players may value spatial relationships more than total counts. Record unsupported requests during research rather than pretending the launch features answer them.

### Launch feature menu

Use the initial plan's 14 structure categories: village, trial chamber, ancient city, mansion, monument, outpost, desert pyramid, jungle temple, swamp hut, igloo, trail ruins, ruined portal, shipwreck, and mineshaft. Keep variants separately capability-gated. Stronghold mandatory-count/absence and public Nether search remain deferred as in that plan.

Use versioned biome-family definitions for cherry grove, mushroom fields, bamboo jungle, desert, badlands, snowy terrain, mangrove swamp, forest, and plains. Do not quietly merge distinct requested families. Exact ID membership and eligible Y/sample methods are capability metadata. Treat “nearby biome” as an eligible observed witness, with sampling limitations in result details, until validated surface semantics exist.

## 3. Result behavior

Return distinct worlds with their best matching saved anchor and optional alternative anchors. Each result shows seed, exact version, base coordinates, map, the measured count/distance for each requested feature, evidence labels, and a preference explanation.

Required rows are conjunctive eligibility rules. Preferred structure utility is `min(count / requested_count, 1)`; preferred biome utility is 1 for an eligible witness in range and 0 otherwise. Importance weights remain 1/3/5. Compute the weighted percentage only after requirements pass. A score of 100 means all selected preference targets matched, not that the world is universally perfect. Preserve the existing proposed deterministic tie rule and label any no-preferences fallback.

Incomplete required facts do not pass. Require complete declared observation coverage for each requested geometry: border-clipped nearby circle or whole playable square, as selected. A sampled biome miss is not proof of physical absence. Only advertise a world-size/search-scope combination when the required observations are available.

No matches means no matches in this snapshot. Show possible relaxations with explicit user actions; do not silently remove a required biome, reduce a count, or widen a radius. Allow the unchanged request to be saved for future catalog updates. Log unsupported and unmatched requests separately.

## 4. Translate the player vocabulary into retention objectives

Public retention is a union of bounded protection lists. A world is retained while it belongs to at least one list, the reference sample, or a pinned snapshot. It does not have to satisfy a shared personal baseline or a single minimum public score.

| Objective family | Why players need it | Proposed retention direction |
|---|---|---|
| Structure specialists | High counts or unusually close structures | Per structure, count rankings at each supported radius/inside-border scope plus a proximity ranking |
| Biome specialists | A requested biome even without impressive structures | Per advertised biome family, near-anchor witness rankings; later add area objectives when validated |
| Useful combinations | A preferred biome with useful nearby activities | Versioned biome + landmark query templates, evaluated at the same anchor |
| Play-style examples | Good starting results before a player customizes | Separate editable-profile rankings; keep distinct tradeoffs rather than one global best list |
| Observation diversity | Layouts missed by dominant profile rankings | Declared feature cells or other tested diversity objectives; bits mean observed/not observed |
| Unbiased reference | Measure what the other objectives miss | Existing stable-hash sample selected independently of relevance gates |

For a broad launch, every advertised feature should receive some explicit protection. Do not give structures dedicated lists while leaving mangrove, badlands, or ordinary preferred biomes dependent only on aggregate variety scores.

A concrete structure count list can require at least one observed start and rank by count within its radius descending, nearest distance ascending, then a canonical seed order. A proximity list requires a qualifying observed start and ranks by nearest distance, count within its declared radius, and seed order. Define the canonical order once. Preserve qualifying anchor IDs as well as the world membership.

Example combination template:

```json
{
  "template_id": "cherry-village-v1",
  "anchor_kind": "recommended_settlement",
  "requires": [
    {"kind": "biome_witness", "feature": "cherry_grove", "within_blocks": 256},
    {"kind": "structure_count", "feature": "village", "at_least": 1, "within_blocks": 512}
  ],
  "rank": [
    "village_count_512_desc",
    "cherry_witness_distance_sq_asc",
    "nearest_village_distance_sq_asc",
    "canonical_seed_asc"
  ]
}
```

This is an illustrative fixed retention objective, not the public request's scoring algorithm. Expand selected biome/landmark templates from actual requests. Do not materialize every possible feature subset, radius tuple, and count combination.

Each objective has a versioned capacity K, exact eligibility predicate, complete rank tuple, and coverage requirements. Rank a world by its best eligible saved anchor for that objective and keep all declared anchor summaries for retained worlds. A seed failing the personal mansion requirement can still enter the cherry-village list; a biome-only specialist need not have a village.

Objective identity includes the world-size/layout scope when it affects eligibility or ranking. For the example combination template, instantiate and record the applicable layout policy; do not combine feature counts from different borders or centers. A retained world can have memberships for all three sizes while sharing its observation artifacts.

Do not adopt new numerical quotas before testing reference queries and measuring bytes/world. The earlier 70,384 upper bound will change when lists are added. The total upper bound is the sum of capacities before deduplication, plus pins. Use measured query-family failures to allocate capacity; retain a minimum breadth allocation so popular survival searches do not consume every biome/technical niche. Revisions are explicit campaign policies, not hidden changes caused by an individual query.

For fixed lists, workers keep the same K and ordering as the global list, deduplicate world identities before truncation, and merge idempotently. A changing popularity or diversity algorithm needs its own merge/correctness design. Failure to enter one list does not justify stopping extraction while another objective or sample can still admit the seed.

## 5. Let this contract define the logical database

Separate authoritative observations, derived summaries, and replaceable indexes.

| Data | Store once per | Purpose |
|---|---|---|
| World identity | Edition/game build/seed identity | Distinguish worlds; keep predictor/extraction revisions on observations |
| Spawn evidence | World + source/settings + evidence revision | Established spawn coordinates, provenance, status, or explicit unknown; independent of settlement selection |
| Structure observations | World + dimension + distinct start + observation revision | Exact coordinates, type/variant, evidence, and coverage for later summaries |
| Biome observations | World + dimension + sample/query identity + revision | Biome IDs, X/Y/Z, eligible method/stride, and provenance |
| Anchor | World + saved location | Exact X/Z, role, coverage; preserve all 81 settlement locations and add an established spawn location |
| Layout | World + anchor + border profile | Side 2048/4096/8192, exact square bounds, geometry revision, extraction coverage |
| Structure summary | Layout + feature + scope/radius + summary revision | Count within clipped 256/512/1024 circles or whole border; exact nearest distance where eligible |
| Biome summary | Layout + family + scope + observation policy + revision | Eligible nearest witness, distance, and presence at supported scopes |
| Membership | World + objective + policy revision | Why the world is retained, rank tuple, qualifying anchor |
| Saved search/result | User + canonical request/snapshot | Reproducible preferences, results, and future-match checks |

Do not duplicate all structure coordinates and biome samples 81 times. Store observations once and derive summaries for each anchor. Do not collapse unknown and known zero. Keep exact counts where retention uses actual counts. A separately capped search-index value is safe only when it preserves every supported predicate and rank key; it must not overwrite the authoritative value.

### Save spawn and settlement choices together

These are two query modes over one retained world, not mutually exclusive storage choices. Save the seed identity and observations once, the spawn evidence separately, and both anchor roles. A complete pilot world can have 81 settlement anchors plus one spawn anchor. If spawn coincides with a saved settlement coordinate, both roles can reference the same location and compatible summaries.

For example, one world can have a spawn anchor at `(120,-80)` and settlement anchors at `(0,0)` and `(768,256)`. These coordinates are illustrative, not an observed Minecraft seed. Spawn mode searches the spawn layout; settlement mode compares the settlement layouts under the user's requirements. Each anchor can have covered 2048/4096/8192 layouts. Never combine a spawn count with a settlement biome witness to satisfy one request.

The additional spawn summaries can reuse the existing observations when their requested geometries are covered. If spawn or its larger border extends beyond coverage, schedule additional extraction or mark that layout incomplete; do not report invented zero counts. Spawn acquisition and missing-area extraction have separate costs from adding another anchor record. Unknown spawn does not prevent retaining a useful settlement world, and established spawn data can be added later with versioned derived summaries.

Apply retention protection to both use cases: a world useful at spawn can enter a spawn objective even if none of its settlement objectives admit it, and a good settlement world need not have a good spawn. Underlying world data is deduplicated across these memberships. A spawn objective requires eligible spawn evidence and coverage; it cannot use origin as a substitute. Recalculate list capacity bounds when adding these objectives.

The nearby circle test is `dx*dx + dz*dz <= R*R` in integer block coordinates, together with membership in the selected border. Three villages within 512 means three distinct starts pass both tests. A 1024-radius count plus one nearest distance cannot derive this answer. Query all required summaries for the same layout ID (anchor and border), score eligible layouts, then group by world.

For fixed radii and three border profiles, use indexed per-scope counts/presence instead of scanning all raw coordinates on every query. Summaries that are identical across nested layouts can share storage, but that equivalence must follow from geometry and observations. Retaining raw coordinates lets later versions derive additional radii or centers for retained worlds within covered bounds. It does not recover rejected worlds, unobserved bounds, surface shape, or missing features automatically. Indexes can evolve from database tables into arrays/bitmaps without changing the player contract or source facts.

Define a feature registry containing stable feature ID, version support, dimension, observation method, count/witness semantics, supported predicates (including biome alternatives where enabled), radii/scopes, border-profile coverage, variants, and evidence policy. Generate or validate the UI, request parser, extractor, and summary builder against it. Reject unsupported requests explicitly.

## 6. Learn what broad audiences actually want

Other products establish useful design examples, not demand percentages. [Chunkbase's own Seed Finder documentation](https://www.chunkbase.com/apps/seed-finder) distinguishes a target from nearby conditions and exposes biome, structure, terrain, and cluster predicates. [MC Seed Map's documentation](https://mcseedmap.com/seed-finder) explicitly distinguishes nearby biomes from biome constraints attached to structures. Our narrower launch should state its actual capabilities clearly.

Recruit an initial research group across survival/realms, builders, adventurers, explorers, ocean players, and technical players. A practical starting exercise is four people in each group, while allowing overlapping identities. This is a discovery sample, not a representative market survey.

Before showing the feature picker, collect:

1. The last world they wanted to start and their desired seed in their own words.
2. Their non-negotiable features, acceptable nearby distances, preferred border size, anywhere-in-border needs, and willingness to relocate from spawn.
3. One tradeoff: which condition they would relax when no match exists.
4. Two or three example map results and which they would actually choose, with reasons.

Record the original wording, a canonical query when representable, unsupported needs, preferred starting mode, requirement versus preference, and eventual favorite/result choice. Do not contact anyone or collect responses automatically as part of this document task.

Use the queries to build the implementation plan's 200-request reference corpus. Include rare and unsupported requests in separate reports. Hold out people as well as queries and seeds when possible. Keep deliberately rare seed cohorts distinguishable from uniform samples. Report query coverage by play style/feature family, alongside overall coverage, top-result recall, score regret, and extraction/storage cost.

The existing proposed >=95% nonempty preservation and >=90% mean top-10 recall remain engineering goals against a declared reference, not proof of market coverage. Revise feature scope, templates, capacities, or extraction when specific families fail. Lack of matches may indicate insufficient scanning, overly selective retention, anchor spacing, missing observations, or an unsupported request; diagnose these separately.

## 7. First deliverable before a database-engine decision

Produce a versioned feature registry, canonical request schema, six editable preset drafts, explicit retention-objective definitions, and a small complete extraction/reference dataset. Test the user questions against that dataset, then benchmark physical layouts. Maintain the broader wish list so a narrow launch does not silently become the definition of what all players want.

This draft changes no source code, approved personal requirements, billing, or running searches.
