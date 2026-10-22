# Public catalog automation — implementation plan

Date: 2026-10-21. Status: approved local automation milestone completed; see [release evidence](reviews/public-automation-scope-2026-10-21/RELEASE_REPORT.md).

The user accepted the simplified product scope and dimension-specific distances
on 2026-10-21, then requested this plan. This document is the implementation
reference for that scope. Earlier feasibility reports remain historical evidence.
Numeric defaults introduced here are explicitly identified below; they are design
choices implemented for this local milestone; measured capacity is scoped in the release report.

## 1. Deliverable and boundaries

One opt-in public pipeline runs beside the existing personal sweep:

`seed-range descriptor -> independent public sample -> extraction -> product evaluation -> retention -> snapshot -> existing catalog UI`

Personal rejection never rejects a seed from the public sample. Public work may
continue after the personal sweep finishes. The personal evaluator, OpenMP
parallelism, scoring and Top 50 behavior stay authoritative for personal results.

Deliver all four pillars with the supported rules below, automatic bounded queue
processing, durable membership updates, publication, restart recovery and safe
orphan cleanup. Keep SQLite metadata, compressed checksummed observations and
the existing two-process query service. No GPU port, custom database engine,
payment activation, new site or BDS generation on every seed in this milestone.
No generalized rule language, plugin system, message broker or new service stack.

## 2. Shared rules

| Item | Exact contract |
|---|---|
| World identity | Existing seed/model/source/native/settings identity; canonical signed seed string |
| Coordinates | Absolute world X/Z, with dimension; preserve Y for biome witnesses and available structure evidence |
| Distance | Horizontal Euclidean; compare squared distances with inclusive `d² <= r²` |
| Structure reference | Distinct viable predicted starts, deduplicated by type/dimension/X/Z; physical footprints and instance totals are separate evidence |
| Overworld border | Existing half-open square, sides 2,048 / 4,096 / 8,192 blocks |
| Personalized OW near | 256 / 512 / 1,024 OW blocks, intersected with selected border |
| Personalized Nether near | 64 / 128 / 256 Nether blocks |
| Nether window | Proposed fixed 1,024 × 1,024 Nether square about the linked reference; independent of OW border size |
| Nether reference | `(floor(OW_X/8), floor(OW_Z/8))`; tag `projected_overworld_anchor_nether`; never label it an actual portal |
| Personalized anchors | Preserve Origin, Recommended settlement and existing supported estimated/observed world-spawn modes; all rules use the same selected anchor and linked Nether reference |
| Preset/record anchor | Estimated world spawn; its linked projected reference for Nether products. Observed spawn remains separately identified evidence |
| Biome evidence | Provider, model revision, dimension, height, coordinates and sampling method accompany each witness |
| Initial biome planes | Existing OW Y=63; proposed Nether Y=64. Additional record/Realm layers are explicitly listed below |
| Missing evidence | `pending/unknown`, never physical absence or a completed zero |
| Coverage | Require the entire requested scope for complete counts. Enrich missing envelopes or leave pending; never clip silently |
| Publication state | Product match, no match under declared method, or pending; show prediction/evidence scope |

Fixed preset/record circles are independent of the player's border selector.
They must not be rounded to the personalized 256/512/1,024 scopes. Negative
coordinates use floor division when projected into the Nether. Compute the
projected reference once in Python and pass it to existing native APIs; test
-9,-8,-1,0,1,7,8 to prevent C truncation from changing the chosen coordinates.
Reuse the existing [-5120,5120) OW observation square where it contains the
requested circle; otherwise schedule the missing survey coverage independently
of the display border. The default 2,048 border does not limit record extraction.

## 3. Product rules

### Pillar 1 — Realm/Server Seeds

Call the existing `dynamic_v3_blueprint_config()` and corresponding evaluator;
store the configuration digest, qualifying center, score and component evidence.
Do not copy its qualification algorithm into the catalog or substitute the
81 public grid anchors for its refined qualifying center.

Current hard floors: stronghold 1, mansion 1, village 6, trial chamber 8, ancient city 2,
desert pyramid 1, monument 1, ruined portal 8, shipwreck 4, mineshaft 10, outpost 1,
fortress 1 and bastion 2. Preserve its required OW/Nether biome families, height
layers, zero allowed misses and existing score calculation without new cutoffs.

**Approved size calibration (2026-10-21):** personal search and the 2,048
Pillar 1 scoring remain unchanged. Qualify and rank 4,096 and 8,192 worlds using
size-specific Overworld floors and count-bonus thresholds derived from measured
seed cohorts, rather than treating them as outer borders around a 2,048 core.
Keep total score 1,250 and group ceilings fixed: Overworld structures/spatial 845,
luxury biomes 265, Nether 140. The Nether square remains 1,024; retain its floors,
thresholds and geometry. Preserve luxury-biome rules and evaluate saturation.
No automatic area-proportional floors or new point budgets.

Calibration runs independently alongside automation/UI work. Reuse saved natural
observations, distinguish unbiased samples from selected high-score controls,
and split development/held-out worlds deterministically by full world identity.
Report qualification rate, per-feature distributions, bonus saturation, group
contributions and rank sensitivity for each size. Freeze source-bound scoring
revisions and test monotonicity, caps, same-anchor qualification and 2,048 parity.
Larger rankings remain gated until held-out validation and independent Gemini
High review pass. Never mix policies in membership/checkpoints; re-evaluate saved
observations to build the new policy namespace without changing personal results.
See docs/catalog/v2/CALIBRATION_PLAN.md for the bounded calibration procedure.

Rank unique worlds within each size/revision by score descending, world ID
ascending and stable center-coordinate ties. Retention allocations are versioned as 3,334 / 3,333 / 3,333
for 2,048 / 4,096 / 8,192; larger boards remain gated until calibration activation. The current 10,000-slot P1 total is the
storage budget; do not silently triple it when splitting leaderboards by size.

### Pillar 2 — sixteen presets

Each unqualified structure requirement below means at least one distinct start.
Every requirement must satisfy the same reference/radius. All OW biome witnesses
use Y=63 for these presets; no terrain or architectural subtype is implied.

| Launch label | Required features | Radius / dimension |
|---|---|---|
| Six-Pack | Village, ruined portal, desert pyramid, outpost, trial chamber, ancient city | 300 OW |
| Loot Run | Ancient city, trial chamber | 200 OW |
| Mansion Village | Mansion, village | 300 OW |
| Triple Start | Village, shipwreck, ruined portal | 200 OW |
| Temple Rush | Desert pyramid, ruined portal | 150 OW |
| Nether Duo | Fortress, bastion | 200 Nether |
| Cherry Blossom Haven | Cherry grove witness, village | 150 OW |
| Meadow & Cherry | Meadow witness, cherry grove witness | 300 OW |
| Bamboo Temple | Bamboo jungle witness, jungle temple | 300 OW |
| Frozen Frontier | Snowy-family witness, ice-spikes witness, village, igloo, ruined portal | 300 OW |
| Badlands & Desert | Badlands witness, desert pyramid, village, trail ruins | 300 OW |
| Village & Two Shipwrecks | Village, at least two distinct shipwrecks | 200 OW |
| Mushroom & Monument | Mushroom-fields witness, monument | 300 OW |
| Villagers & Pillagers | Village, outpost | 300 OW |
| Witch Next Door | Village, swamp hut | 200 OW |
| Warped Forest & Bastion | Warped-forest witness, bastion | 200 Nether |

Reuse canonical biome aliases/family mappings; meadow and ice spikes are exact
named biomes, not broad mountain/snow substitutions. Version the mapping. Frozen
Frontier may use an ice-spikes witness to satisfy its snowy family as well.

Proposed ranking: ascending `(largest required witness d², sum of required witness
d², world ID)`. Use the nearest saved qualifying start/witness per feature and
the nearest two shipwreck starts where required. This ranks recorded evidence;
it does not claim the true nearest biome boundary. Save the selected witness IDs.
If refinement supplies better witnesses, reevaluate that world's memberships.
Retain Top 250 unique worlds per preset. A preset may contain fewer or zero matches.

Weakened definitions receive new stable IDs; original stronger definitions remain
gated and existing links continue to resolve. No hidden “plains village,” bay,
flat plateau, igloo basement, safety, touching-footprint or real-portal condition.

### Pillar 3 — Personalized Selection

Keep the existing 23 public features. Add exactly 8: stronghold, fortress, bastion,
Nether wastes, crimson forest, warped forest, soul-sand valley and basalt deltas.
The public query vocabulary is 31 features. Meadow/ice-spikes/record-family facts
may support products without becoming additional selectable public filters.

Preserve max 12 rows, structure minimums 1–16, Required/Preferred, importance 1/3/5,
and the current scoring/tie behavior for unchanged requests. Biome OR-groups must
stay within one dimension; limit alternatives to that dimension's feature set.
Use the dimension's scopes from section 2. Add separate OW and Nether UI groups.
Stronghold observations support positive matches; bounded enumeration must not
be presented as proof that no other strongholds exist. Unknown required rows do
not enter confirmed-match results; preserve them for enrichment/pending views.
An “at least N” rule can pass from N distinct supported starts even when the
complete total is unknown; display the known lower bound. Distance tie scores
use each row's own radius, or dimension-specific half-window for inside-window
rules (512 Nether blocks, OW selected-side/2). Never compare raw cross-dimension distances.

### Pillar 4 — seventeen launch record products

Record population means evaluated public worlds under the same model/product
revision and scope. Display that population and its pending count. Do not count
all personal inputs as publicly evaluated worlds or claim a global world record.

| Products | Exact proposed launch metric / qualification |
|---|---|
| Megacity, Trial Gauntlet, Ancient City Density, Outpost Siege, Ruined Kingdom, Desert Dynasty, Shipwreck Density | Count the corresponding village/trial/city/outpost/portal/pyramid/shipwreck starts in the closed radius 2,000 OW circle about estimated spawn; admit count>=1, rank count descending |
| Fortress Empire, Bastion Fleet | Corresponding count in the closed radius 500 Nether circle about projected spawn; admit count>=1, rank count descending |
| Mansion Near Spawn, Ancient City Near Spawn, Monument Near Spawn | Nearest corresponding start within 50 OW blocks of estimated spawn; rank d² ascending |
| Four-Type Structure Cluster | Four different OW structure types, all within 300 of estimated spawn, all six pair distances<=100; rank maximum pair d² then sum of pair d² ascending |
| Four-Hut Cluster | Four distinct huts in the radius 2,000 OW survey circle with minimum enclosing-circle radius<=128; rank enclosing radius² ascending |
| Double/Triple Monument Cluster | Two or three distinct monuments in that OW survey circle with minimum enclosing-circle radius<=128; prefer three, then smaller enclosing radius² |
| Close Fortress & Bastion | One of each in the radius 500 Nether survey circle, pair distance<=64; rank pair d² ascending |
| 14-Family Biome Sampler | All 14 families below have a recorded witness within 1,000 OW blocks of estimated spawn; rank largest required witness d², then sum d² ascending |

All ties: world ID ascending. Within a world, resolve tied witness groups by
canonical type/coordinate tuples. Keep one best qualifying group per world.
Four-Type Structure Cluster uses the 15 selectable OW structure types, including
stronghold; each of the four types must have its own supported positive start.
Cluster centers are geometric X/Z suggestions; no AFK, loading or farm claim.
Use an actual minimum enclosing circle for two/three/four points, not their
centroid. Use squared/rational comparisons for exact threshold decisions.

The 14-family definition is an explicit proposed choice: the existing Realm 13
families plus badlands: plains, desert, forest, taiga, jungle, swamp, snowy/ice,
dark forest, peaks, stony shore, lush caves, dripstone caves, deep dark, badlands.
Reuse `realm.blueprint` family mappings plus `realm.biomes.FAMILIES['badlands']`;
record witnesses on the existing layers Y=63,-48,0,160. Match the existing height
roles: lush/dripstone/deep-dark at -48/0, all other families at 63/160. One witness per family
is sufficient; count each family once. Name this product **14-Family Biome Sampler**,
not “all biomes,” and display witness heights. No walking route claim.

Retain Top 100 worlds per record. Existing five Origin research lists remain
compatibility views; do not silently reinterpret their anchor as world spawn.

**Removed from the active catalog by user direction2026-10-21:** the two large
contiguous-biome products (cherry/badlands), Direct-Drop Portal, Intersecting Triple
Mineshaft and Endless Deep Dark Void. Their historical definitions/IDs remain
readable, but they are not current cards or promised work. Physical overlap,
safe terrain and working-farm guarantees are also outside this scope. The
additional28 undefined categories remain outside this implementation. The active
catalog contains17 supported/revised records, without terrain-heavy placeholders.

## 4. Public intake and resource policy

Reuse `catalog.bridge.prepare_campaign` before personal qualification and its
durable descriptor. Reuse `HarvestQueue` leases, retries, pause/resume and dedup.
Add automatic supervised draining; do not perform public extraction in a personal
batch thread or an HTTP request.

The current sampling rule is deterministic sequence-index stride:
`stride = ceil(input_count / sample_cap)`, selected offsets `0, stride, ...`.
Preserve it for the first automated release, with **at most 100 selected worlds per
campaign**. This is an explicit launch limit, not exhaustive public search or a
uniform random sample of all Minecraft seeds. Display selected/evaluated/pending
counts. Use the same descriptor on restart; never resample after personal failure.
Increasing campaign caps or replacing this sampler is a measured later change.

One public extraction child at a time, numeric/native threads 1, nice+10. Reuse
pending 100, 120 seconds/world, 4 GiB child RSS, max 3 attempts, and the existing bounded
retry backoff. Preserve the 600-second drain safety budget: when exhausted, pause
with a reason; the supervisor must not silently reset it to run forever. Ordinary
completed campaigns need no manual drain. An operator resumes a budget-paused one.
Automatic processing requires no manual drain command; the 100-world selection
limit is an upper bound, not a guarantee all 100 finish within 600 seconds.
Treat the existing 2 GiB output allowance as a hard cap for the automated batch
including new artifacts; measure bytes, do not assume metadata-only cost.

The supervisor runs while public automation is enabled, discovers registered or
durably spooled campaigns, and services them fairly in stable order. Keep queue
operations short. Record the campaign cursor separately from job completion;
queue expansion is not successful evaluation. Stop/start of personal search must
not cancel public jobs. Cancellation must target the owned public child only.

Add an opt-in “Also build public catalog” control to the existing sweep start
flow. It registers the descriptor and starts or reuses the one supervisor for
that catalog root. Show public progress and pause/resume separately from personal
progress. Turning the option off affects future campaigns; stopping the personal
sweep does not implicitly stop an existing public campaign. Visiting a catalog
page never starts extraction. Codex owns the personal launch/server integration.

## 5. Storage and retention

### Reuse and extend

- `harvest.sqlite`: existing campaigns/jobs/leases; additive tables for evaluated
  worlds, objective memberships and committed publication generations. Do not
  repurpose its existing task-to-campaign `membership` table.
- Existing observation/segment files: absolute structure positions and biome
  facts once per world/provider/scope; compressed, checksummed and immutable.
- Summaries: derived anchor/dimension/radius/border counts and witness references.
  Preserve original 364-byte v1 records and hashes. Introduce a separately versioned
  typed format for added data; never reinterpret the old slots as 31 features.
- Existing snapshot manifests/cursors/caches: include new data, product and policy
  revisions in compatibility/cache keys. Old snapshots remain readable.

Each new evaluation records world identity, source observation IDs, policy/product
revision, anchor pair, coverage state, selected witnesses, rank key and status.
Coverage is per feature/scope: pending stronghold or a missing biome must not
block publication of an independently ready village product. Replace the legacy
whole-world completion assumption at the v2 publication boundary, retaining strict
schema/integrity checks and independent per-product requirements.
Keep compact evaluation receipts for counted population/replay even if a world
wins no retention objective. A receipt is not a promise to keep its full observations.

### Finite membership rules

Preserve the existing 6,931 specialist/profile/diversity/sample objectives and
83,944 maximum slots, with their current ranking rules. Do not generate all
possible combinations of the 31 query features.

Explicit proposed additions for the 8 new public features, using the existing
Origin/Recommended retention modes and Top 100/objective:

| Additional objective | Number |
|---|---:|
| Stronghold count:4 scopes ×3 borders ×2 modes |24|
| Stronghold proximity<=256 OW:3 borders ×2 modes |6|
| Fortress/bastion count:2 types ×4 Nether scopes ×2 modes |16|
| Fortress/bastion proximity<=64 Nether:2 types ×2 modes |4|
| Five Nether biome proximity<=256 Nether ×2 modes |10|

That is 60 objectives/6,000 slots; Nether objectives are not duplicated by OW
border. Add Pillar 1 10,000, Pillar 2 4,000 and Pillar 4 1,700 slots. Total maximum
**105,644 membership slots before deduplication**, plus separately tracked explicit
pins. Existing Origin research lists are derived views, not another retention cap.
Spawn-query coverage comes from spawn product memberships and retained worlds;
no claim that every possible spawn preference has a dedicated retention list.

Reuse current rank comparison; implement persistent bounded ordered membership
sets in SQLite. There is no requirement to add a heap abstraction. Offer a world
to every eligible objective using its best qualifying anchor/group; retain one
entry per world/objective. A loss in one objective removes only that membership.
It remains stored while any objective, sample, pin or protected snapshot needs it.

Incremental updates operate only within an immutable policy/provider revision.
Rank-affecting corrections/new policies trigger an explicit rebuild from the
declared replayable population; do not claim exact TopK after silently deleting
old candidates that could become winners under a changed rule.
Receipts preserve canonical world identity, input descriptor, scopes, anchors,
evaluator/provider versions and completed refinement progress. A rebuild can
re-extract pruned worlds only with the required pinned runtime available. If it
is unavailable, report the population as non-replayable and do not claim an
all-population rebuild; retained receipts alone cannot reconstruct observations.

### Publication and cleanup

1. Durably write/checksum candidate artifacts in staging; do not publish every loser.
2. Transactionally commit evaluation receipt, winning memberships and a generation
   to publish. Protect all referenced artifacts while that generation is pending.
3. Write/validate its immutable manifest, then atomically replace the current pointer.
4. Mark the generation published and acknowledge the job. Restart reconciles all
   four crash boundaries idempotently; job completion never precedes publication.
5. Reclaim unreferenced staging/orphan artifacts only after reachability checks.

If membership/evidence visible in the catalog did not change, commit the receipt
and reference the existing snapshot instead of publishing an identical manifest.
A completed bounded job may leave individual products pending; product readiness
and queue completion are separate states. Protect checkpoints needed by explicitly
resumable pending evaluations even after their original extraction job completes.

Protect current and historical published snapshots, pending generations, active
readers/cursors, pins and active jobs. On malformed metadata, do not delete.
Use dry-run then quarantine before deletion. This milestone does not expire old
published snapshots or break old shares; therefore disk exhaustion pauses intake.
Snapshot expiry and bounded long-term history are a later explicit product policy.

## 6. Biome work without terrain generation

Reuse `refinement.py`, `refinement_queue.py`, `refinement_worker.py` and native
biome APIs. Preserve provider separation from BDS saved-chunk observations.

Check structure prerequisites first, then existing compatible biome witnesses.
For the 14-family record, first sample the radius 1,000 circle on the existing
world-aligned 64-block lattice at its four declared layers, honoring family height
roles. This gives that product its required coarse evidence before dense work.
If required witnesses are missing, queue world-aligned 64×64 tiles at declared Y
layers intersecting the exact product circle. Visit tiles in deterministic order
by distance to reference, then X/Z/Y; reuse completed tiles across products.
Sample every block in a selected tile using the existing capped helper. Stop
when required positive witnesses are found, or the per-world budget is reached.
Proposed additional bound: at most 64 newly sampled dense tiles per world/evaluation
revision, across all products, dimensions, heights and retries (262,144 block
lookups). Round-robin eligible products in stable ID order, reuse duplicate tiles,
and preserve each product's tile order. On exhaustion, record
`pending: tile_budget_exhausted`; retries do not reset the tile allowance.
For the biome-only sampler, schedule by public intake order; a missing coarse
sample never makes the world ineligible for refinement.

Do not increase the existing 4,096-block tile cap or materialize a multi-million
block Python scope just to prove absence. Aggregate witness/coverage progress
across tiles. Unfinished work stays pending with a reason and checkpoint. Never
screen only the current TopK and assume unknown candidates cannot qualify.
Refinement uses the same one-child resource budget as extraction; no second
unbounded queue of automatic BDS or dense full-world jobs.

## 7. Implementation order, ownership and acceptance

All paths below are under `src/seed_search/` unless prefixed otherwise. Keep changes
inside existing modules where they fit. The only initially justified new modules
are a small public supervisor and a product-evaluator module. Additional modules
need a concrete responsibility that existing modules cannot sensibly own.

| Step | Work / principal files | Owner and dependency | Done when |
|---|---|---|---|
|1. Freeze contracts|`catalog/products.py`, `registry.py`; additive `docs/catalog/v2/` contracts and representative fixtures|Codex first|All product IDs, geometry, rank keys, family maps, coverage and defaults match this plan; old contracts still load|
|2. Add facts and summaries|`catalog/models.py`, `extract.py`, `coverage.py`, `summaries.py`, `codec.py`, `index.py`, native-call adapters as needed|Gemini A, High; after 1|All 31 features and product-only witnesses have typed provenance; raw-to-summary parity and v1 readability pass|
|3. Implement product evaluators|`catalog/products.py`, new `product_evaluation.py`, `product_views.py`; reuse Realm evaluator/refinement modules|Codex; after 1, uses 2 fixtures|Pillar 1, 16 presets, 17 records produce correct match/pending/rank results on independent boundary fixtures|
|4. Connect continuous membership/publication|`catalog/bridge.py`, `harvest.py`, `harvest_worker.py`, `harvest_native.py`, `retention.py`, `store.py`; new `supervisor.py`; `scripts/catalog_harvest.py`|Gemini B, High; after 1, interfaces coordinated with 2/3|No manual ordinary drain; independent intake; persistent TopK equals offline oracle; crash/restart and budget pauses pass|
|5. Wire existing UI/API|`catalog/request.py`, `query.py`, `service.py`, `web/catalog_routes.py`; existing catalog FilterBuilder, types, constants, pillars UI. Codex owns `web/server.py` and personal sweep launch wiring|Gemini A after 2; Codex integrates after 3/4|Four pillars use actual memberships;31 filters, correct units/anchors, public-start control, pending states and legacy links work|
|6. Integrate and release-check|Existing `tests/catalog/`, UI contract tests and bounded validation scripts; handoff/report|Codex + independent Gemini High review|All acceptance cases below pass; measured resource results reported; no unsupported products enabled|

Workers use isolated snapshots containing relevant uncommitted work. At most two
implementation workers are useful initially; never overlap writable ownership.
Step 2's worker does not own step 4's modules. Codex owns cross-module integration.
No live service restart, public activation or new large seed campaign is hidden
inside an implementation worker's assignment.

## 8. Required verification and release conditions

- **Geometry:** inclusive circle boundaries, half-open squares, negative floor/8,
  same-anchor binding, exact 150/200/300 scopes and out-of-envelope spawn.
- **Evidence:** partial stronghold/biome data stays unknown; a positive witness
  retains provider/Y; subtype, actual portal and physical-instance claims stay gated.
- **Products:** independent hand-built positives/negatives/pending fixtures for
  every evaluator family; duplicate starts, counts>=2, cluster pairwise vs common
  center, tie groups, family aliases and updated witness ranking.
- **Storage/query:** v1 files unchanged; v2 counts/ranks/index results match raw
  coordinate oracles, including OW/Nether combinations and legacy requests.
- **Retention:** streaming result equals offline full sort across all objectives,
  ties, multiple anchors, duplicate jobs and worlds winning/losing several lists.
- **Recovery:** kill before/after membership commit, manifest publication and job
  acknowledgement; replay cannot lose a winner, double-count population or skip
  sampled work. Test full disk, expired lease, cancellation and budget pause.
- **Reclamation:** never remove artifacts reachable from any protected root;
  prove loser cleanup and shared-object preservation on disposable stores.
- **Personal isolation:** exact personal results match with public automation
  enabled/disabled on the same bounded fixture campaign; retain OpenMP operation.
- **UI:** existing TypeScript/Vite build and meaningful handler/contract tests,
  plus Codex/Gemini review. Interactive browser QA remains waived.
- **Performance:** reuse existing 200-world natural and 500-world synthetic fixtures;
  report new extraction/refinement cost, ingestion bytes, retention time and query
  latency. The existing 10-second query deadline is unchanged. Do not infer billion-seed
  public throughput from the personal screening rate or two-world timings.

Steps 2/3 are medium complexity;4 is highest because it joins transactions,
publication and recovery;5 is medium;6 depends on measured failures, not a guessed
calendar deadline. Benchmark only affected paths after correctness checks pass.

Completion means the automated bounded pipeline and supported products work
end-to-end, with reproducible evidence and clear pending states. It does not
require finding a natural match for every rare combination in the 200-world pilot.
Publish an empty list honestly rather than weaken thresholds. Record actual test
results and remaining coverage/resource limits in one release report and handoff.
