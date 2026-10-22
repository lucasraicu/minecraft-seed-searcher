# Private Catalog in Sweep — proposed implementation plan

2026-10-20. User requested all six proposed pre-GPU catalog steps and confirmed
Catalog as a separate tab in the existing Sweep app. This is the concrete plan
for High critique and final approval required by root AGENTS.md. No runtime code
or new seed/game work starts during planning. Existing dirty files are preserved.

## Goal, scope and completion

Deliver a usable loopback/private Catalog tab in the same React application:
category browsing, editable filters, three borders, Origin/Recommended settlement,
seed details, comparison, device-local favorites and snapshot-pinned sharing.
Back it with segmented SQLite/artifact publication and measured selective indexes.
Add incremental ingestion/recovery, broader bounded corpus checks and scoped
game-evidence validation. Preserve current Sweep state and live process60144.

No GPU, custom durable engine, checkout/accounts/cloud favorites, external hosting,
global public feature activation, automatic commit/push or live-server restart.
Preview the changed app on a separate loopback listener with a fresh build output;
do not overwrite the current live frontend dist. A Catalog route is distinct from
the existing personal candidate routes/data. Public availability stays off.

The application and validation tools can be completed autonomously after this
plan is approved. Real player demand cannot be manufactured: deliver explicit
opt-in request export/import and a held-out usefulness report; mark player-demand
validation pending if no actual participants supply requests. Similarly, limited
game probes never certify all advertised structures or every generated block.
Those external empirical gates must remain visible in the final result.

## Current evidence and invariants

CPU reference:100 complete worlds,24,300 layouts (81 centers x3 borders),1,387
passing tests. Extraction245s; full experiment504s; peak2.24GiB. SQLite35.6MB,
compressed artifacts11.9MB. A flat manifest is4.89MB uncompressed and has a16MiB
cap, approximately340 worlds at current density. Warm median Origin/Recommended
queries ~5/53ms on100 worlds; Recommended repeated-pass maximum1.57s. Current
query code scans Python layouts and raw verified reconstruction takes~17s.

Freeze public_policy/feature_registry/request semantics:8 categories,23 Overworld
features,16 profiles; border sides2048/4096/8192; radii256/512/1024; counts1..16;
at most12 request rows; preferred importance1/3/5; biome OR alternatives. All
Required rows match ONE layout; choose the best eligible anchor per world BEFORE
TopK. Unknown coverage is not a completed zero. Biomes are positive Y63/stride64
witnesses, not absence/terrain guarantees. Keep full signed64 seed strings over
HTTP/JavaScript and unsigned bit-pattern tie order. Origin is not world spawn;
spawn remains gated. Research identity stays research:26.50, not an accepted
exact Bedrock build. Preserve original personal/native/scoring algorithms.

## A. Segmented publication and incremental storage

New `catalog/segments.py` and versioned fresh pilot schema/root, leaving the
existing CatalogStore/v1 run readable and unchanged. Import v1 through verified
read APIs into the fresh root; never mutate the only source corpus in place.

Use standard SQLite plus existing content-addressed durable gzip artifacts.
Immutable leaf manifests contain at most256 layout descriptors and at most1MiB
uncompressed. Bounded fanout128 internal manifests form a content-addressed tree;
the root binds revisions, world settings/model, policy and ordered membership.
Enforce both byte and entry limits. Every layout binds metadata and the packed
364-byte payload hash; observations retain their own identities/checksums.
No monolithic all-layout descriptor or unbounded root child list.

Persist new artifacts before one SQLite transaction makes a generation visible.
Readers pin a generation/root until their request finishes. Appends reuse existing
world/observation IDs, segments and artifacts; differing observations of the same
world are explicit replacements, not duplicate worlds or silent count merges.
Reject incompatible build/settings/schema; expose intentional replacement as a
new generation. A failed commit leaves the previous generation readable. No
automatic orphan deletion or WAL/shm removal. Recovery/backup walks validated
reachable manifests and preserves the source generation.

Stream bounded batches during import/publication. Indexes, membership metadata and
root descriptors are validated before promotion. Distinguish artifact integrity,
verified extraction provenance and actual game evidence; a checksum is not proof
that fabricated observations came from Minecraft. Verification state is persisted
only with exact source/root/revision bindings and trusted local importer provenance.

## B. Rebuildable selective query index

New `catalog/index.py`, standard SQLite metadata and bounded segment bitsets.
For each segment index the declared structure thresholds1..16 for each supported
scope, positive biome-witness scope membership and coverage. Initial query pass
restricts side/mode and intersects Required bitsets; a biome alternative ORs its
members inside that same row before intersecting other rows. Never intersect
world-level flags that can join different anchors.

Bitsets are rebuildable derived artifacts bound to segment payload hashes,
policy/registry/geometry and index revision. Generations bind those independent
content digests without entering their derivation keys. Check length/reserved bits,
membership bounds, checksums and consistent local row order. Missing/stale indexes
either rebuild explicitly or use a declared exact fallback, never return partial
matches or silently skip a segment. Bound rebuild concurrency and cache bytes.

After candidate selection use the existing deterministic query rank arithmetic,
coverage/evidence checks and canonical ties. Deduplicate worlds globally before
TopK/pagination across segments. No approximate scoring/top-anchor shortcut.
Preferred-only requests may still score all layouts; measure and report this.
Do not promise every query is submillisecond or bitmap-filterable.

Index reuse keys include segment content, index/geometry/policy/registry revisions
and source identity; they EXCLUDE generation/root identity. A generation binds the
selected content-index digests separately, so append does not force full reindexing.
World layouts may span leaf boundaries; query aggregation must retain each world's
best eligible candidate across ALL its segments before global TopK. A fixed leaf
size never changes logical query grouping or permits cross-anchor joins.

Read serving summaries/metadata without reparsing every raw biome sample per
request. On first segment access validate its immutable descriptor, payload hash
and observation identity bindings. Detail requests load raw observations lazily.
An explicit offline/import audit verifies the full raw corpus and derived facts.

## C. Local API and existing application shell

New `catalog/service.py` and a narrow `web/catalog_routes.py` integration into
WebSearchHandler. Configure a dedicated Catalog root explicitly; an unset root
returns an informative unavailable status. Do not silently create/query personal
databases. Reuse existing POST Origin/Referer/Sec-Fetch-Site guards; add bounded
JSON parsing and no arbitrary filesystem or native-evaluation HTTP parameters.
The existing handler POST allowlist/body parser needs a deliberate integration,
not a bypass inserted before its request guards. Use dependency injection in tests.

Proposed routes under `/api/catalog/`: capabilities/status, category presets,
snapshot-bound query and world/layout detail. Usefulness feedback uses explicit
local query annotation/export and an offline import CLI; no telemetry endpoint.
Response includes snapshot, research build, settings, policy/evidence revisions,
selected coordinates, exact border bounds, counts/witness scope and coverage,
plus ranking explanation and explicit empty/unavailable/error states.
Limit queries to12 rows/16KiB body, pages1..50 results and a documented maximum
of1,000 ranked worlds per query. Return truncation explicitly. Snapshot/request-
bound opaque cursors must not skip/duplicate worlds or mix generations. Use a
bounded expiring result cache (initially8 queries/64MiB) as an optimization only.
Choose an HMAC-authenticated keyset cursor binding snapshot/root, request digest,
exact canonical rank tuple, page size and expiry. A cache miss performs exact
reranking for the same pinned generation; it does not itself invalidate a cursor.
Return the true global Top1000 after all qualifying layouts/worlds are considered,
never the first1000 scanned. Match existing unrounded utility/distance/unsigned-
seed/anchor/layout tie order, not a replacement hash tie. Use a bounded TopK
collector after each world's best qualifying layout is known; explicitly report
truncation and reject token tampering/expiry/removed snapshots. Initially limit
Catalog execution to2 active jobs plus2 queued, with observable query cancellation,
iteration deadlines and busy/time-limit errors. Set provisional5s warm-query
wall limits, measured/tunable before acceptance; no arbitrary100ms promise.

Keep the existing `App.tsx` Sweep workspace intact with a narrow shell extraction:
one top-level Sweep/Catalog navigation, lazy Catalog load, preserve mounted Sweep
state after first use using persistent mounting/hidden tabs, and make direct
Catalog links avoid initializing personal work. Namespace Catalog URL state and
handle browser back/forward without resetting Sweep. JSX remounting is not an
acceptable way to switch away from an active personal workspace.
No browser change, route, GET or Catalog search may start seed generation.

For browser QA, run a Catalog-only loopback backend without importing the existing
server's global SweepManager. Use the existing app in Vite on port5173 with
strict-port behavior and an explicit development proxy: Catalog routes to the new
backend; Sweep routes to original port3000. Port5173 is already allowed by existing
Origin guards and was free at inspection. If occupied later, do not stop its owner
or weaken guards; report the preview conflict. Existing PID60144 remains untouched.
The eventual integrated WebSearchHandler routes are tested on disposable injected
managers, not by restarting live Sweep. Browser QA never starts/stops a real sweep;
use mocked controls for those flows. Build fresh static assets for review separately
from the current live dist. A controlled production integration remains a later
explicit deployment action.

New frontend `web-ui/src/catalog/` for types, API client, workspace, filters, result
cards/details, compare and local persistence. Reuse project styling/network
conventions without changing Sweep's behavior. Worker owns only these new files;
Codex owns App/server integration to avoid overlapping dirty-file ownership.

## D. Player experience and useful actions

Eight existing categories/presets are starting points, not locked search modes.
Show and allow editing all preset rows, Required/Preferred and importance. Defaults
are Recommended settlement and the declared default border. Offer advanced Origin,
with a clear explanation; spawn control remains disabled/explained.

Results display full seed strings, anchor coordinates, border, evidence/version,
matched Required facts and Preferred score contributions. Detail shows predicted
structure starts and sampled biome witnesses, scope/coverage and supported download
of seed/settings/query metadata. Any map uses absolute saved coordinates, labels
samples/starts correctly, and avoids claiming complete terrain or structure extent.

Comparison:2..4 seeds, each column retains its own layout/anchor/border, with
different geometries prominently labeled rather than silently normalized.
Favorites: versioned browser-local storage, exact seed/world/snapshot/layout keys,
export/import/delete and malformed-data recovery; label "saved on this device".
Sharing: same app URL with Catalog tab and snapshot/world/layout IDs. Resolve the
exact saved generation or show unavailable; do not silently reinterpret against
the newest snapshot. Full query export is JSON; bounded URL query encoding is
optional and must not leak personal sweep state or filesystem paths.

Handle loading, stale responses/cancellation, empty matches, storage quota failure,
unavailable old snapshots and copy/share failure. Keyboard navigation, readable
labels, focus management and narrow-screen layout are acceptance checks.

## E. Bounded validation and empirical gates

Start with existing100 natural worlds; never rerun their extraction. Synthetic
storage/index fixtures span at least1,000 world identities (explicitly fabricated),
three sizes/modes and forced small page/fanout limits so tree boundaries and deep
hierarchies are tested cheaply. A separately timed synthetic scaling probe may use
up to10,000 fabricated identities, only after correctness; no game generation.
Give that synthetic probe its own cumulative15min wall/4GiB RSS/2GiB output cap;
stop and report partial scaling evidence on exhaustion. Large probes are owned
asynchronous coordinator jobs, not delegated reviewers'240s tool calls.

Proposed additional natural cohort:100 NEW distinct full seeds, indices100..199
from the same declared seed_from_index(i,0xCA7A11) schedule. Serial one native
thread,900s extraction cap;1,800s full corpus validation, aggregate RSS4GiB,
new output2GiB. Preflight10 plus90 shares one durable allowance. Assert no overlap
with imported seeds. Give this cohort its own frozen campaign controls rather
than weakening the existing100-world CLI's original cohort contract. Stream index/publication batches and report every partial/
failed receipt. Stop on projected budget exhaustion rather than enlarge limits.

Freeze256 additional developer requests before extracting/evaluating the new
cohort. Keep original200 requests as regression, not a tuning set. Compare indexed
queries to exhaustive summary and raw-coordinate oracles, including adversarial
partial coverage, biome OR, same-anchor requirements, boundary coordinates,
multi-anchor duplicates, signed extremes and global pagination ties. Report
nonempty/recall/regret denominators and actual retention fraction.200 natural
worlds still do not establish production-capacity recall or real player usefulness.

Player request validation: opt-in local feedback with explicit export/import,
bounded retention and delete controls; no automatic sending or invented respondents.
Separate developer/synthetic requests from actual player submissions, version
the corpus, split by participant/world group and withhold a test set before tuning.
Report "not evaluated" when external player evidence is absent or insufficient.

Actual-game checks are a separate bounded sub-job using only an ALREADY installed
pinned BDS image, with digest/build/settings verified. Readiness inspection does
not upgrade evidence. Proposed cap4 fresh disposable worlds x16 fixed observation
targets, one world at a time,4 CPU/6GiB per container,20min cumulative wall and
8GiB newly owned Docker output. Use request-tagged fresh resources and logs;
never touch existing worlds/containers, never pull an unpinned image or download
credentials. Include observer readiness, clean shutdown and resumable receipts.
This is an offline, separately receipted empirical gate and does not block
completion of the private research UI if unavailable. It remains an OPEN actual-
game acceptance gate in that case. Reuse the existing actual surface-point adapter
where suitable; do not attempt a whole generated-structure verifier in this scope.
A fixed-Y63 predictor witness and an observed surface biome may be different
predicates: compare matching coordinates/Y/methods, or report them as different
scopes without inventing a mismatch or agreement. Keep observed1.26.52.3 identity
separate from research:26.50; any compatibility acceptance is evidence-scoped.
Compare only the actual biome/block/coordinate observations the adapter supports;
positive structure presence needs scoped generated evidence, not a height heuristic.
If the image, exact adapter or scoped predicate is unavailable, report that gate
as blocked/unverified and keep the affected advertised capability unaccepted.
No certification of the full23-feature catalog from64 point observations.

## Ownership, dependencies and tests

Codex: source/preservation baseline, frozen interfaces, migration/integration CLI,
API routes, App shell, coordination/oracles, browser QA, final regression/report.
Gemini A High: new segments module and tests. Gemini B High: index module/tests
after segment interfaces freeze. Gemini C High: frontend catalog directory and
its scoped tests. Gemini D High, only if independent: evidence/request-validation
module/tests after provenance API freezes. No shared writable files. Normally2–3
workers concurrently, maximum4. Freeze manifest/index/HTTP/TypeScript contracts
before coding; A precedes B integration, C starts only after API fixtures/types
are fixed, and D is optional. No worker blocks idle on another worker's files; isolate snapshots with the dirty baseline.

Verification: focused Python/storage/index/HTTP tests, original1,387 regressions,
frontend type/build into a fresh private output, frontend action/error/state tests,
actual browser navigation/filter/details/compare/favorites/share QA on loopback,
snapshot/cursor refresh while ingestion commits, owned-process death before/after
promotion, corruption/missing-page/index mismatch, interrupted import/replay and
reachable backup restoration. Preserve original native hashes, personal files,
Git staging/HEAD and original server PID/start time. Never weaken Required or
evidence labels to pass an index/performance test.

Measure publication peak RSS/bytes and incremental cost; cold verified opening
separately from warm serving; Required-filter selectivity and actual decoded/scored
layouts; broad Preferred-only cost; p50/p95/max and failures. Compare against the
same saved corpus/workload/source/hardware. No production latency guarantee.

## Estimate and approval boundary

Planning estimate: storage/index work2–4 focused working days, API/UI/actions3–5,
integration/recovery/usefulness tooling2–4, with overlap giving roughly1–2
focused weeks. These are engineering estimates, not a promise based on100-world
extraction time. The bounded existing-adapter game probe may be attempted in parallel after
readiness; implementing new whole-structure verification is excluded. Actual-player
participation and wider generated-structure evidence
have external dependencies and no honest completion date yet. Update estimates
after storage/index parity and first usable browser milestone.

Broad scope/UI choice are already authorized. Root AGENTS.md additionally requires
the final detailed plan, critiques, risks and assignments be presented for approval
before significant implementation. Obtain that final plan approval once critiques
are reconciled, including the concrete new-corpus/BDS limits above; do not seek
repeat approval for ordinary implementation within that approved scope.


## Final critique reconciliation and execution authorization

High review5d328b5f270f succeeded, exit0, no denied actions/changes and explicit
marker. Raw final response: FINAL_CRITIQUE.json. User approved the six-step scope,
confirmed existing Catalog tab and subsequently said Continue; proceed within that
scope without a repeated permission request. The concrete plan and assignments
were presented in chat before implementation. New bounded empirical limits remain
as specified above; external evidence cannot be claimed when unavailable.

Accepted: reusable content-only index identities, compact cache entries where
useful, strict preview port and exact global dedup/ranks. Initial segment default
will be one complete world (243 layouts) per leaf, at most256 descriptors/1MiB;
partial research worlds may have fewer layouts. Larger-world batches are optional
only if entry AND byte caps hold; the review's claim3888 descriptors necessarily
fit1MiB is unmeasured. Cross-leaf same-world best-rank tests remain mandatory.
Reviewer corrections: world IDs are256-bit hashes, not64-bit integers; use stable
local offsets or full hashes, never truncate identity to satisfy cache estimates.
Sweep uses backend processes, not presumed browser-local generator workers. Proxy
all noncatalog /api routes to existing3000, not only nonexistent /api/search.
No fixed coarse-anchor shortcut, arbitrary100ms deadline, encrypted cursor or
new destructive GC is required. Use HMAC-authenticated full canonical ties.
