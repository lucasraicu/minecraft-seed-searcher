# Four-pillar private catalog and CPU harvesting bridge

2026-10-20. Stage B/C explicitly approved by user “i approve. go ahead” after
independent High Gemini critiques. Implementation is now present; verification
and actual worker contributions are recorded in REPORT.md. Original scope and
review reconciliation below are retained as the approved design.

## Objective and source evidence

Organize the existing Catalog tab into four distinct product entry points and
connect future opt-in native personal scans to independently scheduled public
extraction. Keep existing SQLite/artifacts and publicquery-v1 semantics.

Source inspected: Public_Catalog_Master_Plan.md stages B/C; platform sections 4/5;
catalog extract.py, ingestion.py, service.py, web/catalog_routes.py;
realm/native_batch.py compute/submit/persist_pipeline and run_native_scan;
realm/cli.py and runner.py; web/server.py SweepManager; CatalogWorkspace.tsx.
Native compute generates seeds BEFORE prototype.sweep. Native survivors are
already personally filtered and cannot be the public source. Existing ingestion
is a frozen 100-world validation harness, not a general campaign queue.

Existing pilot: 200 natural worlds/48,600 layouts, 23 Overworld features, 81
candidate anchors, square border sides 2048/4096/8192, radii 256/512/1024,
Required/Preferred counts, best eligible anchor per world. Preserve these APIs.
Full previous regression: 1488 passed/1 timing failure, isolated rerun passed;
all 215 catalog tests passed. Browser QA explicitly deferred. Preserve original
Sweep PID60144, loaded binaries, live dist and all unrelated dirty changes.

## Deliverables and explicit capability boundaries

1. Four named entries: Realm/Server Seeds, Presets, Personalized Selection, Rare
   Seeds. Existing flexible workspace becomes Personalized without losing saved
   state, comparisons, detail, favorites, sharing or exports. Existing Sweep stays
   mounted with keyboard isolation and no live-job restart.
2. Versioned server-owned product registry: stable IDs, display category, exact
   predicate/dependencies, geometry/anchor, ranking/ties, evidence requirement,
   availability reason. Keep commercial proposals in documents for this stage. Do not use
   bitmask membership as evidence or an entitlement. No account/payment activation.
3. Sweet16: all sixteen existing named presets across five themes, one-click
   cards, no border/radius forms. Keep exact 150/200/300m requirements and subtype,
   portal, terrain and spawn requirements. Do NOT round to v1 radii, substitute
   Origin for spawn, or claim coastal/contiguous/farm safety from sampled biomes.
   Initially unavailable where a complete evaluator is absent; explain missing
   evidence rather than show an empty certified list. Gated cards open a criteria
   inspector with structured missing dependencies and evidence requirements. This stage does not make
   all sixteen usable: estimated-spawn integration remains Stage D.
4. Realm: distinct discovery view explaining qualification requirements and
   capability status. Show only independently qualified PUBLIC observations,
   never personal winners republished as certified catalog entries. Current pilot
   has no complete Realm certification artifact: show unavailable, not fake seeds.
5. Rare: four themed halls with the 22 actually named records in platform section
   5. The stated target is 50 but only 22 definitions are supplied; do not invent
   28 definitions or claim completed50. Gate underspecified predicates (radius,
   reference point, tie order) and missing terrain/Y/Nether/spawn evidence.
   Provide useful separate, explicitly labeled RESEARCH previews for predicted
   village, trial, portal, pyramid and shipwreck start counts within a fixed
   Origin-centered 2000-block Euclidean circle. These have separate research IDs,
   not the identity/claim of a spawn record. Rank count descending, world ID
   ascending; one result/world with count>0, Top100 in selected immutable snapshot. No border
   controls or universal/world-record claims. Structures are predicted starts.
   Publish previews from a bounded offline derivation over existing observations,
   checksummed and bound to snapshot/definition/build; no per-request raw scan.
6. Opt-in CPU bridge for NEW native CLI scans; existing running scan untouched.
   Public scheduling sees the deterministic seed sequence independently of
   personal gates, and can retain a seed that personal search rejects.

## Dual-branch design and durability

Use one immutable campaign descriptor written atomically BEFORE any opt-in
personal native evaluation: run key, supported sequence kind, start/count,
manifest seeds or low32 stride where relevant, source/model/native hashes,
registry/extraction version, deterministic sampling policy, public root and caps.
The same descriptor produces both seed streams. Reuse seeds.py parse_seed and
seed_from_index/seed_strided: canonical signed64 decimal STRING seed values on
disk and wire, Python integers internally, uint64 bit patterns only at native
boundary. Sequence indices/counts are unsigned decimal strings (count may reach
2^64), distinct from seeds. No JSON numeric seeds or JavaScript Number coercion.
Fail explicit unsupported sequence/config
at preflight, not midway through scanning. Never select only personal survivors.

Keep the public queue in its OWN SQLite database. Register descriptor + range
cursor once, then lazily expand deterministic sample indices into bounded work
rows; do not insert a trillion per-seed jobs. Unique keys bind full world identity
and extraction version. Public tasks may run ahead of personal completion in the
declared campaign: statuses must say scheduled/extracted, not personally visited.
Use uniformly spaced deterministic index sampling with recorded offset/stride
for the first bounded bridge, not advertised as a statistically unbiased sample.
Public retention policy still applies; no all-seeds or all-preferences guarantee.

Personal launch does NOT wait on public extraction or a full public queue.
Queue uses WAL, short bounded transactions and a personal-registration busy
timeout250ms; the worker may wait up to5000ms. Descriptor is the durable local
spool on registration contention; no personal progress writes to public SQLite.
Descriptor registration occurs before personal startup; if catalog registration
fails, report detached/failed catalog state and allow personal work with the
durable descriptor as a replay source. If descriptor itself cannot be persisted,
abort opt-in preflight clearly; user may explicitly launch catalog-off. No claim
of lossless handoff under arbitrary disk failure. A registered range remains
pending when queue/storage caps are hit; never silently advance past deferred work.

Catalog worker is a separately launched, single-process-owner supervisor, with
one single-thread native extraction child at a time initially. CLI opt-in writes
and registers work; it does not silently start an unbounded background daemon.
An explicit worker command drains accepted work while a personal job runs. This
separation makes CPU budget and stop/resume explicit. Descriptor and CLI help
state that personal SIGINT does not cancel registered catalog samples; explicit
catalog cancel/pause controls affect only catalog ownership. Future Sweep toggle and
automatic sidecar lifecycle are deferred; do not add HTTP job-launch endpoints.

Queue states pending/leased/complete/partial/failed/deferred with attempts, owned
process identity, heartbeat, checkpoint and checksum. Expired lease reclaim must
not terminate a live unrelated/reused PID. Use worker UUID, process start identity
and monotonically increasing lease generation; acknowledgement/checkpoint writes
must match the generation. Hold an exclusive publisher ownership lock through
lease validation and publication/receipt reconciliation so stale generations
cannot publish. Lease claim/reclaim/generation changes acquire that same ownership
lock; cannot revoke a lease while its publication holds the lock. A hung publisher
pauses catalog recovery rather than bypassing ownership; personal work continues.
Queue transaction must not span extraction. Only signal directly
owned unreaped subprocess groups; never kill an external PID from stale DB data.
Atomic observation checkpoints stay in private staging and resume only compatible
complete features. Require all23features complete for this bridge's initial
publication path; partial work remains resumable/unknown, never a completed zero.
Existing catalog partial-coverage semantics stay unchanged. Publish via current segmented store after
validation; idempotent world identity and publication receipt reconcile crash
after publication before queue acknowledgement. No personal DB ownership/writer
changes, no native C branch or OpenMP fork, no modification of frozen cohort harness.

Reuse current public observations when identity + coverage match. Personal native
survivor packets are NOT complete public inventories; first bridge re-extracts
independently rather than pretending all expensive facts are shared. Record this
additional CPU cost. Later reusable fact adapters need coverage/provenance checks.

Child uses one native/OpenMP/BLAS thread and POSIX nice+10 where supported;
record effective settings, do not silently change personal thread settings.
No CPU affinity guarantee on macOS and no zero-slowdown promise.
Initial hard defaults: bridge OFF; campaign public sample cap100; queue pending
cap100; one extraction child/native thread; per-world wall120s; total worker
wall600s; RSS4GiB; output2GiB; max3 attempts with bounded backoff. All receipts
record caps and stop reason; bounded logs. User can configure lower caps; larger
campaigns require their own budget. Tests use injected fake clock/extractor and
tiny manifests; no new natural cohort required for software acceptance.

## Files, order and ownership

Phase1 Codex freezes product/queue schemas and tests interfaces, records baseline
hashes/processes. Proposed new files may be split for clarity without widening
ownership. No ignored dependencies are assumed in isolated snapshots.

Milestone B: product registry, UI, offline previews and acceptance first.
Milestone C: queue, bridge integration and recovery acceptance second. Independent
High Gemini coding workers, at most two concurrent within useful boundaries:
- Product worker owns catalog/products.py, catalog/product_views.py and
  tests/catalog/test_products.py. Implement registry/availability and offline
  research preview derivation/parity. No web/service/native/UI writes.
- Queue worker owns catalog/harvest.py, catalog/harvest_worker.py and
  tests/catalog/test_harvest.py. Implement independent queue/supervisor with
  injected extractor, budgets, recovery, descriptor validation. No personal scan,
  existing ingestion harness, native or HTTP writes.

Phase3 UI worker (after product schema freeze) owns new web-ui/src/catalog/pillars/
components and their focused contract tests. Existing CatalogWorkspace/App shared
integration belongs to Codex. Worker receives explicit dependency paths and
TypeScript command; cannot claim build success without installed dependencies.

Codex owns product endpoint/service/http adapter integration, offline preview CLI,
scripts/catalog_harvest.py entrypoint, realm CLI/runner/native_batch opt-in wiring,
CatalogWorkspace/App integration, independent oracles/integration tests, documents
and handoff. Review patches before applying; no commits/pushes/merges.

Expose bounded metadata/product results under /api/catalog/products and
/api/catalog/product-results with strict versioned body schema, immutable snapshot
and product IDs, stable pagination or Top100 bound, same detail world/layout IDs.
Keep /api/catalog/query unchanged. Research results must use a compatible Origin
layout for storage lookup, with a MANDATORY explicit research detail scope
{scope_type:origin_euclidean_circle, anchor:[0,0], radius:2000}. Research map renders
that circle and only matching witnesses; no square border masquerades as scope.
Bind scope to artifact/definition revision; preserve existing detail API behavior.
No filesystem paths, arbitrary predicates or extraction in HTTP requests.

## Verification and acceptance

- Registry exactly4pillars/16namedpresets/22namedrecords; every unavailable entry
  has dependency reason. No fictional certification/entitlement/seed IDs.
- Research count independent raw-coordinate oracle: boundaries at r=2000,
  negative coords, duplicates, partial coverage, missing vszero, deterministic
  ties, snapshot/build mismatch and artifact corruption; all existing200worlds
  reused without extraction. Offline read bound<=5min/4GiB/2GiB, stop explicitly
  if cap reached; HTTP only precomputed bounded artifacts.
- Queue/bridge: seed enumeration parity all supported sequences; full64-bit values;
  personal reject/public accept; identical personal semantic results OFF/ON;
  simulated queue full, registration/storage failure, timeout, cancellation,
  PID reuse, lease contention/fencing, registration SQLITE_BUSY fallback, corrupt
  checkpoint, output cap exhaustion, publication crash + replay;
  two consumers never double own; identity/build change rejected; capped sample
  stays independent of personal score; zero-survivor campaign still feeds public;
  explicit personal stop/catalog continuation/cancel tests; native thread/niceness
  settings verified; no dangling owned child after shutdown.
- Actual subprocess crash/replay test uses tiny fake extractor, not seed scans.
- Existing catalog + native persistence/CLI targeted regression, frontend tsc and
  isolated-output production build, then full Python suite once after integration.
  Preserve/report known timing failure separately; do not weaken tests.
- Browser visual/keyboard acceptance remains pending under prior user instruction.
  No server restart/live-dist overwrite. No new BDS worlds/native rebuild/GPU,
  large seed campaign, custom durable database, payments or public deployment.

## Complexity, risks and estimate

UI grouping is moderate; availability registry is moderate; durable independent
queue and crash-safe publication are high complexity. Plan/review about10minutes;
implementation estimate3–6 focused engineering days, with a checkpoint after UI
and again after bridge integration. This is an estimate, not a completion promise.
Main risks: mostly gated product cards until StageD; incomplete50record definition;
extra CPU extraction can compete with personal scan despite one-thread cap; disk
failure recovery; inherited dirty state; no connected browser acceptance. No claim
of zero slowdown: personal SEMANTICS must match, resource effects are reported.

## Independent critique and reconciliation

High tool-free reviews adea4a21cc67 (product) and109c192cfe33 (bridge) completed
with process exit0, denied_actions[], substantive responses, no changed files;
model gemini-3.8-flash-high, reasoning_effort high. No tests run by these reviewers.
Full returned status evidence saved alongside this plan. Codex incorporated circle
scope, usable gating inspectors, canonical strings, queue lock timeouts, lease
fencing, private staging, separate B/C checkpoints and additional failure cases.

Consequential disagreements resolved from source/contract:
- Reviewer suggested5000ms SQLite timeout everywhere; personal registration uses
  250ms with descriptor fallback to protect startup; worker may use5000ms.
- Reviewer suggested restricting public samples to personal progress. Rejected:
  independent declared campaign is deliberate, stated above; explicit catalog
  cancellation avoids coupling public qualification to personal completion.
- Reviewers disagreed linear sampling versus hash/LCG replacement. Keep the small
  declared deterministic extraction cohort, not an unbiased sample claim. No
  evidence establishes spatial region periods in seed-index arithmetic; modulo
  hash/LCG does not itself prove uniqueness/unbiasedness. Existing retention's
  separate stable-hash reference objective remains unchanged.
- Partial observations are not inherently invalid: models.py and extract.py
  explicitly preserve unknown/partial coverage. Initial bridge publication uses
  complete worlds for simpler acceptance, without weakening existing semantics.
- Do not introduce worker-suggested global native thread recalculation or Linux
  affinity assumptions on macOS. Explicit single-thread low-priority child and
  reported resource competition are the scoped controls.
- Structures are start points in extract.py, not bounding boxes. Record preview
  tests circle containment of starts; do not promise physical structure clipping.
