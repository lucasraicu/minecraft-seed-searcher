# Public catalog biome expansion — implementation plan

Status: COMPLETED AND ADOPTED. The user approved the reviewed scope including section 5a and a separately reviewed one-time 180-second migration amendment (3,780 seconds cumulative). Release evidence is in reviews/biome-expansion-plan-2026-10-22/RELEASE_REPORT.md. Historical planning language below preserves the original proposal.
Date: 2026-10-22. Existing approved catalog work is complete.

## 1. Outcome and boundaries

Expand Personalized Selection in the existing four-pillar UI to individual Overworld
biomes, retaining convenient groups. Support bounded height-aware positive witnesses
where inexpensive. Reuse observations, SQLite/CAS, checkpoints, heaps and query workers.
No new site, terrain-generation pipeline, GPU work or custom database engine.

Keep the existing 17 structure filters, 16 presets, 17 record products, three Realm
boards and 2048/4096/8192 borders. Nether remains 1024 square with radii 64/128/256;
Overworld radii remain 256/512/1024. Personal scoring and public Realm calibration
remain unchanged: 845 Overworld + 265 luxury biomes + 140 Nether = 1250.
No new searches, native predictor changes, backend restarts or catalog migration
before approval. Implementation approval will authorize the bounded saved-world
validation/migration described below, not a new billion-seed campaign.

Do not add ocean ruins, buried treasure, camps, Nether ruined portals, End searches,
fossils, dungeons, geodes, desert wells or other lower-level generation features.
Do not restore the five removed terrain-heavy products. Exact landing, safety,
physical totals/footprints, biome area/contiguity, arbitrary sliders and exact
whole-border absence remain excluded.

## 2. Exact biome choices

Current model inventory: 56 active Overworld IDs, five Nether IDs. Shipped-name
comparison found 89 biome asset names covered through aliases; this does NOT
establish generation accuracy, nor justify 89 different UI options.

Expose each of the 56 active Overworld biomes as its own choice; preserve all five
Nether choices. Define atomic IDs as biome.exact.<canonical_name> in a new contract.
Legacy names are aliases, not additional player choices; ice_caves is outside the
pinned model and must not appear. New choices absent from current group coverage:

| Category | Biomes |
|---|---|
| Oceans | Ocean, Deep Ocean, Warm Ocean, Lukewarm Ocean, Deep Lukewarm Ocean, Cold Ocean, Deep Cold Ocean, Frozen Ocean, Deep Frozen Ocean |
| Rivers/shores | River, Frozen River, Beach, Snowy Beach, Stony Shore |
| Forest/taiga | Dark Forest, Pale Garden, Dappled Forest, Taiga, Old Growth Pine Taiga, Old Growth Spruce Taiga, Windswept Forest |
| Jungle | Jungle, Sparse Jungle |
| Savanna | Savanna, Savanna Plateau, Windswept Savanna |
| Swamp | Swamp |
| Mountains | Windswept Hills, Windswept Gravelly Hills, Jagged Peaks, Frozen Peaks, Stony Peaks, Grove |
| Caves | Lush Caves, Dripstone Caves, Deep Dark, Sulfur Caves |

Split the 14 current grouped members into independent choices:
- Badlands, Eroded Badlands, Wooded Badlands.
- Snowy Plains, Snowy Slopes, Snowy Taiga, Ice Spikes.
- Forest, Birch Forest, Flower Forest, Old Growth Birch Forest.
- Plains, Sunflower Plains, Meadow.
Keep the five already singleton choices: Cherry Grove, Mushroom Fields, Bamboo
Jungle, Desert, Mangrove Swamp. Thus 37 + 14 + 5 = 56.

Retain four convenient group choices, defined strictly as ORs of their atomic
members above, using biome.group.<name> IDs. A witness may satisfy both its atomic
choice and its group. Selecting alternatives in ONE row means OR; required rows
mean AND around the SAME anchor. A group is not a requirement for every member.
Do not use one canonical-name-to-one-feature dictionary: current summaries.py
would overwrite overlapping group/member membership.

## 3. Evidence and rollout

These are predicted biome-presence filters. Player copy says 'Predicted biome
presence'; detail gives predicted XYZ, sampled heights and method.
Never call a Y63 witness a surface-height/terrain guarantee or a missing witness
proof of absence. No fixed-Y profile certifies a walkable surface. Per-world missing samples remain
UNKNOWN, never absent. A valid OR witness can satisfy the row despite unknown
alternatives; an AND requirement without a witness remains unresolved. Globally
gated/unsupported atomic selections get an explicit capability error, not a query
exception or an empty-success response. Groups retain all declared members: a
partial member set without any positive is unresolved, not silently narrowed.

Core release: reuse existing world-aligned Y63/stride64 Overworld samples and
Y64/stride64 Nether samples. Add the 27 non-cave/non-mountain missing choices and
split group members using compatible saved samples. Existing mountain-related
members such as Snowy Slopes receive the same evidence caveat, not a terrain claim.

Height-aware release gate: six missing mountain choices plus four cave choices
require appropriate saved or newly computed multi-height witnesses and the tests
below before activation. Proposed deterministic extra survey is Overworld Y96,
Y160 and Y224 for mountains; Y-48 and Y0 for caves, stride256 over the SAME saved
observation envelope, not per anchor or per world border. At a 10240 square envelope
this is at most 8,000 additional points/world before reuse (40 * 40 * five planes). Reuse exact compatible
XYZ/provider results first; deduplicate points across Realm/public products. The
existing Realm BiomeIndex already consumes -48/0/63/160 evidence where present;
first inventory its actual saved coverage rather than presuming those heights are
missing. Extra points belong to a source-bound extension artifact, not silently
added inputs to the frozen Realm scoring evaluation. Non-cave filters accept their
compatible Y63 plus enabled 96/160/224 profile witnesses; cave filters accept
compatible -48/0/63 witnesses. Each group uses the union of its member predicates.

Treat these levels as a bounded presence survey, NOT exhaustive detection. Pilot
16 existing saved worlds (eight fixed-hash ordinary worlds and eight deterministic
feature-targeted worlds, frozen before timing). Compare baseline and expanded
extractor on identical seeds/settings with interleaved runs. Activation requires
median per-world wall increase <=25%, all worlds within the existing 120s native
world cap, and unchanged personal results. This 25% is a proposed product cost
ceiling, not a measured prediction. If it fails, keep height-dependent choices
unavailable and report measurements; do not silently increase resources or change
the profile. Core filters can ship independently. No HTTP query launches extraction
or BDS. Existing per-world/600s allocation/RSS/output limits remain enforced.

Groups always evaluate the union of the SAME eligible atomic witnesses, including
height policy and availability. New v3 semantics are versioned; existing v2 group
queries/presets/retention continue using their original Y63 evidence. A historical
snapshot never silently acquires new features.

## 4. Other accuracy items

Predicted igloo basements and treasure bastions: use the existing Realm auxiliary
inventories only. Add two optional structure-count filters (igloo_with_basement,
bastion_treasure), with the same anchor/dimension/radii and at-least controls.
No new structure scans, village subtype rules or physical safety guarantees.
Auxiliary filters use complete/partial evidence explicitly and deduplicate starts
against their parent structure; no duplicate count across generic and subtype lists.
They activate only after independent pinned-version positive and negative controls
validate the existing methods; otherwise remain unavailable with an explanation.
Do not infer a basement/variant from the generic structure label. Preserve unknown
and failed auxiliary inventories. Other bastion variants and village subtypes are
not part of this initial release.

Strongholds: include an evidence-only coverage investigation, reusing archived
independent discoveries and existing regressions. Produce a report of known bounds,
reference semantics and any source-backed improvement. Keep the partial label and
current predictor. No stronghold algorithm change is approved by this plan; any
consequential correction gets a separate reviewed proposal.

## 5. Storage, retention and migration

Add versioned contracts under docs/catalog/v3/: feature registry, sampling profiles
and public retention extension. Keep v1/v2 immutable and dispatch requests/readers
by the snapshot's revision. Reuse existing sparse observations and arbitrary-height
point representation. Extend summary/request versions only where needed; do not
create a parallel persistence/queue framework. Keep legacy packed summaries for
unchanged scoring/products. Store only newly computed XYZ samples and profile/
provider provenance in one checksummed CAS extension artifact per world, bound to
the original observation ID. Existing points are referenced, not recopied as new
measurements. Add dictionary summaries for atomic/group/variant filters bound to
BOTH original observation and extension IDs. Allow extension_id=null when no new
points were computed; do not fabricate empty artifacts. A referenced extension
must exist, pass checksums, match base/profile/provider and remain protected by
snapshot/pin/receipt reachability through reclamation. The extension is an artifact using
existing storage, not a separate database or worker framework. Original Realm
evaluators consume their original observation, never the extension implicitly. Existing CAS per-side projections remain the query
path; no raw-world scan per query. Include profile/registry/policy/source identity
in cache/cursor/projection bindings and validation. Keep the existing 16MiB
uncompressed artifact cap, 1MiB query-worker request cap and 4MiB reply cap. Use
existing manifest paging/projection partitioning rather than raising caps; if the
minimum representation cannot fit within existing bounds, stop with a measured
blocker rather than silently widening them.

New per-feature retention: one nearest-witness Top20 list for EACH atomic OW biome,
each of three borders and Origin/Recommended/estimated Spawn modes. Best eligible
anchor per WORLD enters each list once. Rank by horizontal squared distance, then
world ID, anchor X/Z and witness XYZ; witness must be inside the selected border.
World-spawn-estimated lists use only actual saved compatible spawn anchors. No
synthetic Origin fallback. Add nine Top20 lists for predicted basement igloos; treasure bastions get only
three Top20 lists (one per mode), since the Nether window does not change with
Overworld border size. These use predicted starts. Existing five Nether lists and all previous
objectives stay unchanged. No combinatorial list for every filter subset.

Maximum extension: 56 * 3 borders * 3 modes * 20 + 3 * 3 * 20 basement slots
+ 3 * 20 treasure-bastion slots = 10,320 membership slots;
105,644 existing + 10,320 = 115,964 slots. Slots are NOT unique world counts or
storage-byte forecasts. Inactive features offer nothing; capacities stay reserved.
These115,964slots are primary targets; section5a defines the2x retained capacity.
These are explicit primary targets (Top20), never inherited v2 Top100 defaults;
section5a applies the requested2x retained capacity to every objective.
There are 516 added objectives and 7,543 total objectives at full scope. Empty
objective lists are valid and do not fabricate worlds. These ranks measure the
nearest SAVED PREDICTED WITNESS, not the true nearest biome boundary or instance.
This cannot preserve the best seed for every future combination. Existing reference
sample, diversity buckets and landmark pair lists continue; no unbounded new pairs.

Use an isolated NEW policy root, replay the same 222 retained worlds, reuse raw
facts and compatible heights, compute only approved missing evidence into extensions, rebuild
summaries/offers/projections and publish atomically. Old root and all historical
snapshots/links/pins remain readable; no in-place policy rewrite. Existing discarded
seeds cannot be recovered by changing retention. Future opt-in intake uses the new
policy only after adoption. Verify GC protects old snapshots and live receipts.

## 5a. Whole-sweep 2x reserve — requested amendment

For every enabled finite winner/retention target K, persist up to 2*K DISTINCT
seed/world candidates: K primary predicted candidates and K reserves. This means
100 TOTAL for a Top50, not50+100. Display the primary target by default; reserves
remain inspectable under a separate reserve view/status. No score, hard floor,
anchor geometry or advertised winner target changes. Disabled K=0 stays0.

Personal: search.top_k remains the requested display/winner limit (default50).
Derive a separate candidate_capacity=2*top_k (default100). Build the existing
Top50Tracker with the effective100 and use its cutoff only after100 distinct
eligible seeds fill it. All native pruning/early materialization must use the
reserve cutoff, not the50th score. This does not change C scoring. Persist both
limits and reserve_factor=2 in checkpoint/run identity, authoritative SQLite and
presentation-cache metadata. The top50.json legacy name can remain for readers,
but its visible primary results must stay at50; expose reserves explicitly.
Validate effective capacities against configured resource bounds, never clamp
away the requested reserve or silently raise maximums.

Public: each existing and proposed objective declares primary_k and effective
retained_k=2*primary_k. Apply this to specialist, pair, profile, diversity, reference
sample, Realm, preset and rare-product lists. The proposed biome Top20 target
becomes40 retained memberships per list. Inactive features offer none. Do not
create separate primary/reserve world copies: one ranked2K membership sequence
per objective, with tier determined per objective, and deduplicated world storage.
A world can be primary for objectiveA and reserve for objectiveB; never assign a
global seed-level reserve flag. Protect the UNION of primary, reserve, pinned and
verification-in-progress worlds from reclamation.

Primary capacity115,964 becomes a maximum231,928 retained membership slots under
the full new policy; current objectives alone would rise105,644->211,288. The
objective count remains7,543, including516 expansion objectives; this is a capacity
change, not extra objective families. These are slot bounds, not2x unique worlds,
2x scan time or2x disk-byte forecasts. Legacy105,644-slot ledger/manifest guards
in harvest.py/store.py must remain valid for old policies; new known-policy guards
must derive the declared231,928 bound consistently in ledgers, paged manifests,
projections, recovery and validators. Do not accept an arbitrary caller-supplied
capacity. Keep16MiB artifacts/1MiB requests/4MiB replies and existing resource caps.

Finalization: future BDS verification consumes candidates in frozen rank order,
checks the advertised conditions for that seed/anchor/dimension/border/profile,
and promotes passing reserves when primary candidates fail. Unknown/error stays
pending; a failure for one product does not globally blacklist the seed. Retain
verification cache/job receipts keyed by actual evidence identity, not just seed.
Use existing scoped verification mechanisms, not a second orchestration system.
This amendment authorizes NO automatic BDS campaign or larger verification budget.
Until checked, primary rows are explicitly predicted/provisional, not verified
winners. If the existing BDS budget cannot produceK passing results, show the
actual verified count and pending status; do not pretend the target was met.
Generic Personalized Selection continues querying the union of retained candidates
and choosing its own same-anchor best match; reserve position on some unrelated
objective must not hide an otherwise matching world from that search. Per-objective
primary/reserve views apply to boards with explicitK, not pagination or page size.

Compatibility: defaults apply to new runs/new-policy intake after approved adoption.
Do not change an active run's capacity mid-resume: current native_batch.py rejects
that for a correctness reason. Completed personal databases/catalog observations
may rebuild reserves ONLY from saved compatible candidates/receipts, marked
historically incomplete when earlier pruning discarded inputs. No retrospective
Top100-over-the-whole-old-sweep claim or rescan is authorized. Preserve existing
primary snapshots and historical limits rather than silently rewriting them.

Verification additions: compare2K tracker/pruned pipeline against an independent
full sort on bounded synthetic cases, distinct-seed dedup, tie handling and delayed
cutoff until2K; sameK first-half parity with old retained datasets; resume/crash and
JSON-cache rebuild for primary+reserve; per-objective role overlap and promotion;
no global discard from scoped failure; GC reachability for reserve-only worlds;
policy-bound231,928 ledger/manifest/paging cases; no change to public admission
before personal rejection. Measure additional survivor materialization, bytes and
heap/SQLite time: larger reserves can make the scan slower despite unchanged seed
count. Preserve the10s query deadline and resource caps; report blockers rather
than dropping reserves or increasing resources silently.

Additional ownership: Codex owns personal config/native_batch/top_tracker/checkpoint
and server compatibility changes; GeminiA owns policy/heap reserve fields within
its existing catalog ownership; GeminiB owns UI role/count display. All remain
proposed until user reviews the amended plan.

## 6. UI, compatibility and files

Personalized Selection gets category search, expandable group/member choices,
clear Any-of versus All-required row behavior, disabled gated options with reasons,
and witness height/dimension in seed detail. Preserve the 12-row limit and existing required/preferred semantics; cap each
explicit OR row at 16 unique choices. Convenient named groups each count as one
choice; do not expand payloads to a 56-way OR just because the registry grows.
No new query operator language. Favorites, comparison, pagination and shared URLs
remain snapshot-bound; unsupported old filters produce a clear error, never an
empty success. Load capability metadata from the selected snapshot, not hardcoded
assumptions that every stored world supports every feature. Reuse current controls.
Add primary/reserve counts and status without doubling default displayed rows.
No site redesign, new payment flow or score-budget changes.

Likely scoped files: catalog/{registry,models,extract,summaries,codec,request,query,
retention,automation_query,store,realm_observations}.py; native worker adapter only
for bounded extra biome_points calls; web/catalog_routes.py; web-ui/src/catalog/
(types/constants/validators/query builder/filter controls/detail); docs/catalog/v3/;
a new bounded migration CLI using existing import/reanchor patterns. Keep all
native/vendor sources and personal scoring policy files read-only. Section5a
adds personal retention/checkpoint config changes, not scoring changes.

## 7. Work order and worker ownership

1. Codex freezes contracts, feature/profile semantics and migration baseline (medium).
2. Gemini A: native-free summary/query/retention work and tests in an isolated dirty
   snapshot (medium). No UI/store/native ownership.
3. Gemini B concurrently: UI controls/decoder tests against frozen fixtures (medium).
   Own web-ui/src/catalog and associated CJS tests only.
4. Codex: bounded height pilot, validation, migration/history/integrity and integration
   (medium to high). These depend on contracts; migration waits for stable summaries.
5. Gemini C: independent final read-only source/evidence review at High. Can review
   after A/B; no need to run four workers continuously. All Gemini uses High.

## 8. Verification, resource limits and acceptance

Meaningful checks: independent coordinate oracle per atomic/group feature and
all radii/borders/anchor modes; multi-match group/member case; XYZ/provider/version
rejection; no-witness unknown; mixed-height OR/AND at one anchor; negative Nether
floor division; old/new request and decoder compatibility; deterministic TopK vs
independent full sorting, partitions/replay and saved checkpoint recovery; variant
unknowns and source identity; actual HTTP query/detail/pagination/old share links;
all nine existing Node catalog suites, changed Python suites and frontend build.

Re-use frozen actual-game evidence first, replaying the current predictor at
archived ground-truth coordinates where edition/build/settings match (an old
predictor fingerprint does not invalidate the independently observed game result).
Before any fresh BDS work, build a per-feature matrix showing two independent
world witnesses already available and exact missing coordinates. Feature activation
is conditional on this matrix, not on a guessed number of worlds. After
implementation only, validate up to 8 existing seeds in isolated disposable BDS worlds/copies, one server at a time,
2 CPUs/2GiB, <=280s/world, <=1,800s total game wall, pinned image/settings/observations.
Freeze desired positive/negative/boundary cases before generation; separate ordinary
and targeted outcomes. Require matching positive XYZ controls on two independent
worlds per newly enabled biome/method, reusing compatible archived controls first.
Negative controls refer to exact queried XYZ or independently established variant
outcomes, not absence across a sparsely sampled world. Version/name coverage alone
is insufficient for activation. Select cases that cover the added methods; no universal
accuracy percentage or physical count inferred. If required controls are missing
or contradict prediction, leave the affected feature gated and report it.
Do not rerun unrelated historic campaigns or perform a full-volume census.

Pilot native budget: <=1,800s total, one native/numeric thread and 4GiB RSS.
Migration budget: <=3,600s cumulative with durable progress, same 4GiB/2GiB output
caps, no automatic allocation reset. Preflight required bytes including preserved
history/copies against the output cap before creating the new root. Stop with
checkpoints on cap exhaustion; do not delete evidence or raise limits silently.
Measure bytes/world, summary/index size, ingestion and cold query latency. All nine
existing mixed queries plus 12-row and 16-alternative stress cases must meet the
unchanged 10s HTTP deadline on the refreshed 222-world cohort, with accurate
unknown counts and disjoint pagination. Precompute summaries; never traverse raw
world samples or enumerate filter subsets while serving requests.

Release only with unchanged raw structures, Realm evaluations and personal database/
native hashes; old snapshots readable; new evidence indexed correctly; every enabled
feature has an eligibility method and retention objective. Browser interactive QA
remains waived; automated Codex/Gemini UI checks and build are required. Restart
only the idle public backend after checks; preserve the personal server. No commits,
merges or pushes. Report enabled versus gated features and actual timing/limitations.

## 9. Approval requested

Approve the core expansion plus bounded height/auxiliary-variant validation and
new-policy migration above. Gates may keep expensive/unvalidated features disabled;
finishing this scope means delivering core filters plus an explicit pass/fail report
for the conditional additions and the separate stronghold investigation, not
promising every conditional feature becomes available. Implementation starts only
after the user reviews the reconciled Gemini critiques and approves this plan.

## 10. Gemini critique reconciliation

Two independent read-only reviews used gemini-3.8-flash-high with --effort high:
0562b6da8853 (biome method/cost) and 566cba085cd8 (storage/retention/UI). A narrow
follow-up 5d564be6a21b checked final evidence-extension and cost/query changes and
found no new architectural blocker. All three succeeded, exit 0, denied_actions [],
no edits or tests. Detailed findings and
Codex responses are in reviews/biome-expansion-plan-2026-10-22/RECONCILIATION.md.
Accepted: overlapping group mapping, height-profile identity, coarse-witness
limitations, cost risk, explicit Top20 settings, projection caps, snapshot negotiation.
Revised survey from stride128/32,000 extra points to stride256/8,000, prioritizing
saved Realm layers, with the 25% median cost gate unchanged. This is a trial, not
a performance promise. Preserved raw scoring inputs using the extension artifact.
Accepted follow-up: nullable extension IDs for core-only worlds. Rejected its
suggestion to silently drop gated group members; the declared OR remains intact
and unresolved without a valid witness. Query performance is measured at release,
not guaranteed by an architectural review.
Rejected: treating unsampled biomes as absent; claiming 20 point witnesses cannot
fit within eight worlds; treating empty TopK lists as a defect. All worlds can
provide multiple biome controls, and unknowns remain unknown. Reviewer's inclusive
lattice arithmetic is corrected to the actual half-open envelope. No second
whole implementation framework is introduced. All changes remain proposed.

Reserve amendment review11d530d30c6c also completed at High, exit0/denied[], no
edits/tests. Codex verified native cutoff/resume and public capacity guards against
source. Its recommendation to reuse a single ranked2K list agrees with section5a.
The amended whole-sweep reserve remains proposed until clear implementation approval.
