# Proposed full public automation — plan for review and scope approval

Historical scope proposal. The user accepted the simplified scope on2026-10-21
and requested a specific implementation plan. Use
[PUBLIC_CATALOG_AUTOMATION_PLAN.md](../../PUBLIC_CATALOG_AUTOMATION_PLAN.md)
for the current execution sequence and explicit proposed defaults.

2026-10-21, planning only. Companion FEASIBILITY.md inventories all16 presets and
22 records. No code/process/data changes or seed searches during this review.

## Objective and evidence

Connect public admission, enrichment, objective membership, publication and safe
storage lifecycle without inheriting personal rejection or disrupting personal
OpenMP work. Existing: durable personal batches/Top50; bounded public handoff before
personal qualification; explicit separate serial drain; immutable observations;
243 layouts/world; separate offline retention; two-process catalog query service.
Missing: continuous bounded supervisor, incremental multi-objective replacement,
publication lifecycle and safe reclamation. Product declarations are gated.

User approves the direction for Pillar1 and requests Pillar3 public Nether and
stronghold, with explicit dimension distances and no arbitrary sliders/travel
geometry. Pillar2/4 simplified product definitions below need scope confirmation.

## Contracts to freeze first (Codex owns)

1. Pillar1 binds the actual versioned dynamic_v3 blueprint/config digest, all
13 hard floors, required biome families and current score, preserving its actual
qualifying center rather than substituting the public81-anchor grid. No new
score threshold invented. Proposed outer border options2048/4096/8192 surround
the same qualified2048 OW core and1024 Nether core; do not pretend larger-border
qualification was measured. If this interpretation is not chosen, expose only
the qualified2048 size until separate4096/8192 blueprints exist. Proposed public
Top10000, distinct from personalTop50; no claim of certification without evidence.
2. Pillar3 registry: current23 features +stronghold +fortress/bastion +five Nether
biomes =31. No change to OW radii256/512/1024 or world sides2048/4096/8192. Proposed
Nether near64/128/256 **Nether blocks**, inside an independently declared1024-side
Nether window. Nether reference is floor(OW_anchor_x/8),floor(OW_anchor_z/8), linked
to the selected OW anchor; schema tag `projected_overworld_anchor_nether`, not an actual generated
portal. UI never calls200 Nether blocks200 OW blocks (nominal OW scale1600).
All requirements bind the same OW/Nether anchor pair. Stronghold incomplete
recall cannot become complete absence. Fixed-Y Nether biome provider/layer must
be declared; candidate Y64 is a proposed model lookup layer, not a safe floor.
3. Pillar2/4 follow FEASIBILITY.md revised predictions: actual world-spawn estimate
as reference, start coordinates rather than footprints, fixed finite geometry,
scoped record population. Top250/preset, Top100/record proposed. Defer physical
safety/farms/collision/portal-room/cave-route promises. Connected biome patches
follow later after targeted cost measurements. No arbitrary slider or walk route.
4. New biome-dependent products requiring meadow/ice-spikes/14 OW families need
their own raw biome mapping and witnesses;31 public filters do not magically
provide14 OW families. Missing required coverage is pending, not an empty result.

## Architecture/files and order

A. Freeze versioned product, evidence, ranking, capacity and sampling contracts;
update products.py, registry/contracts and query schema. Define distinct new IDs
for weaker renamed products (e.g. `preset.village_two_shipwrecks`) and preserve
stronger original promises gated. Do not reuse an old starter_portal anchor tag
for a projected coordinate. Use one
shared typed geometry definition for retention, browse and details.

B. Additive dimension observation and summary generation in models/extraction/
summaries/codec/index modules; keep legacy364-byte23-feature records readable and
hash-identical. New schema supports dimension, coordinate reference, bounds,
height/provider, precision, completeness and provenance, not an expanded untyped
array read as old version. Save raw world facts once; per-anchor summaries reference
them. Only compute summaries for registered scopes; no3x world generation per size.
Sparse biome witnesses support positive findings; refine potential decisions
conservatively so small patches do not become false-negative exact absence.

C. Bounded public supervisor around harvest.py, harvest_worker.py and retention.py:
durable task identity/leases/retries; personal resource priority; one extraction
worker initially with current numeric-thread/resource caps. Sampling/shard frontier
is persisted before expensive public qualification, independent of personal score.
Capacity exhaustion pauses public dispatch and records exact unevaluated ranges;
it never silently implies every personal input was inspected publicly. Producer
and consumer progress must be decoupled; replay/skip policy explicitly tracked.

Incremental objective winners are persistent and keyed by policy/product/evidence
revision. Memberships reference world+qualifying anchor+metric+evidence; replacing
one membership does not remove other memberships, diversity/sample or pins.
Bound objective count/slots/bytes and extraction backlog. Existing6931-objective
83,944-slot policy is not blindly multiplied across31 features and arbitrary
feature subsets. Registered combinations only; bounded storage cannot preserve
the best answer for every future filter combination. Updates use transactional
membership generations and idempotent replay; immutable manifests are published
atomically only after all artifacts are durable. Resume from committed frontier.

D. Product evaluators use raw coordinates at exact150/200/300 etc. thresholds,
not approximate summary scopes. Generalist density and pair geometry first;
refinement and subtype alternatives second. Publish per-policy population and
frontier/completeness alongside records. Support overlap/multiple memberships
without duplicate observations; compare streaming retention to offline oracle.

E. Safe reclamation: explicit protected roots include current/pinned/retained
snapshot manifests, active readers/cursors/jobs, references shared by dimensions,
and staged valid transactions. Only unreferenced artifacts can be collected.
First release performs dry-run/quarantine and orphan/staging cleanup; no automatic
deletion of existing published snapshots. Protect old shares indefinitely unless
the user approves a separate snapshot/link-expiry policy. Disk ceilings therefore
pause ingestion rather than promise unbounded publication with bounded disk.
Full published-generation expiry is a distinct lifecycle decision, not hidden GC.

F. Existing four-pillar UI: explicit predictions/evidence, distances with dimension
units, actual reference coordinate and subtype/terrain limitations; availability
gates remain for unsupported promises. Automated contracts/handler/build checks
and independent Gemini review; interactive browser QA waived by user. No billing
activation or new payment guarantees in this automation milestone.

## Assignments, dependencies and resources

Codex owns contracts, main integration, process safety and final validation.
After contracts are approved: Gemini High workerA owns isolated storage/dimension
schema+tests; workerB owns isolated supervisor/membership/lifecycle+tests, dependent
on frozen interface fixtures; workerC owns isolated product evaluators/UI+tests
after contracts, with disjoint files. Schedule fewer when dependencies block.
Independent critiques now: one product-feasibility reviewer, one automation/schema
reviewer, tool-free supplied context only,180s each; no edits/commands permitted.

Relative cost: pipeline/membership/recovery high; typedNether/stronghold medium;
simple geometry low; biome refinement medium; dense patch analysis medium/high
and deferred. Existing2-world3.885s/world extraction cost is not a new31-feature
throughput promise. No GPU/customDB, new campaign or expensive BDS required to
approve scope; later bounded measurements validate added extraction cost.

## Acceptance and risk gates

- Personal fail/public winner retained; partial/unknown does not become zero;
  public disabled/enabled preserves exact personal output under fixed schedule.
- Negative coordinates/floor division/8, dimension units, paired-anchor binding,
  bounds, circle equality, windows and requested envelopes; no silent clipping.
- Legacy records hashes/readability and new schema raw-to-summary/index parity;
  exact new geometry vs raw oracle at all thresholds; evidence revision separation.
- Stronghold positive/unknown coverage and subtype/sparse biome witness semantics;
  independent held-out seeds/points before changing model accuracy claims.
- Stream TopK identical to offline full-sort oracle incl ties, duplicate seeds,
  multiple qualifying anchors, overlapping memberships/pins and replacement.
- Fault injection before/after commit/publication/ack, stale leases, disk full,
  crashes, bounded retries and restart; no durable frontier advancing past lost work.
- GC dry-run/live reader/cursor/shared-generation reachability, malformed manifests
  fail closed, no published snapshot deletion; disk-full pause/recovery.
- Reuse existing correctness/load evidence, then bounded tests of new scopes,
  incremental retention overhead and cold/warm queries on fixture/copy stores.
  No broad new seed sweep or live service restart without concrete need/authorization.

Final scope approval is needed for the specific renamed/weakened products and
new policy defaults, per AGENTS.md, before significant implementation; this does
not rescind the user's authorization of the overall automation objective.
