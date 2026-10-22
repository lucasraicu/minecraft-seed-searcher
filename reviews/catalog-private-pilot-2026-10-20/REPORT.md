# Private Catalog milestone — implementation and validation

2026-10-20. Implementation and automated checks are finished, with one intermittent
non-Catalog test recorded below. The user explicitly chose to leave browser QA pending; interactive acceptance
is deferred and is not claimed to have passed. This is a private research pilot, not a public launch.

The Catalog tab is implemented in the existing Sweep application, backed by a
separate segmented SQLite/artifact store. It supports eight editable category
presets, Required/Preferred structure and biome filters, borders2048/4096/8192,
Recommended settlement and advanced Origin, exact pinned details/maps, comparison,
device-local favorites and sharing. Spawn remains unavailable. There is no new
site, GPU implementation, custom durable database engine, billing or public hosting.

Operating instructions: [PRIVATE_PILOT.md](../../docs/catalog/PRIVATE_PILOT.md).
Detailed measurements: [measurements.json](measurements.json).

## What changed and why

- Bounded immutable leaf/internal manifests replace the flat all-layout serving
  manifest. SQLite publishes a new generation only after artifacts are durable.
  Old generations remain readable during append, pagination and recovery.
- World observations retain coordinates and coverage once; each center/border
  stores a packed summary referencing its observation. All Required conditions
  apply to one layout. No personal rejection requirement enters public queries.
- Rebuildable per-leaf bitmap indexes restrict geometry and Required rows before
  decoding. Exact scoring and global best-layout-per-world selection precede
  Top1000 pagination. HMAC cursors retain full canonical unrounded ties.
- A bounded one-hour result cache holds up to eight immutable result sets;
  membership proofs are rechecked on hits. Cache misses rerank the same pinned
  generation. The provisional10second iteration allowance replaces5seconds after
  measurements exceeded5seconds. No partial ranking is returned on timeout.
- The Catalog-only loopback backend avoids importing SweepManager. The preview
  proxies Catalog to3001 and personal Sweep to its existing3000 process. Direct
  Catalog links avoid mounting Sweep; hidden Sweep keyboard shortcuts are gated.
- Frontend fixes preserve signed64 seed strings, cancel stale response updates,
  retain each comparison's own snapshot, expose copy/storage failures and unknown
  coverage, show complete half-open bounds and distinguish Origin from spawn.
- Explicit participant-request export/import supports bounded local request
  corpora and disjoint participant holdouts. No telemetry or invented respondents.

## Natural corpus and recovery

The original100 worlds were imported from saved observations, without repeating
their extraction. The separately frozen cohort uses indices100..199 of the same
declared schedule, has no full-seed overlap, and freezes256 additional developer
requests before extraction.

New cohort:100/100 complete, all23 declared features,24,300 layouts, no failed,
missing, partial or invalid checkpoints. The supervised job finished in506.38s,
with peak monitored RSS2,393,030,656bytes and151,114,740bytes of output. Independent
retention-objective parity, partition merge and backup/restore passed. Default
retention keeps100; reduced policies keep97/99. These small natural populations
do not establish production recall or broad player demand.

Verified append produced200 worlds and48,600 layouts at:

`3d964acd07729a1aa50c23ba90e90a37754c009fc685f0313cc6cf0157eddd6a`

An offline audit rederived all48,600 summaries from raw coordinates and rebuilt
the saved indexes semantically. All18 fixed requests across three borders, both
modes, general/Required/Preferred scenarios matched exhaustive Top20 results.
Actual owned-publisher SIGKILL tests before/after SQLite promotion preserved old
readers, replayed idempotently and restored verified backups.

## Measured serving and fabricated scale

Paired measurements below use saved corpora and identical results on cold-service
and warm-result-cache requests. Filesystem caches may already be warm. They are
small developer workloads, not production latency guarantees.

| Corpus / mode | First query | Cached repeat |
|---|---:|---:|
|200 natural worlds / Origin|2.41s|12.7ms|
|200 natural worlds / Recommended|5.38s|12.7ms|
|1000 fabricated worlds / Origin|5.22s|282ms|
|1000 fabricated worlds / Recommended|5.39s|277ms|

The separate18-request cold audit had median2.51s, maximum/p95 of this small
sample5.97s, and sampled detail lookup0.95s. Origin decodes200 layouts for one
border; broad Recommended decodes16,200. Result-cache hits decode zero layouts
but still verify snapshot/membership metadata. The `index_cache_hits` statistic
also counts persisted leaf indexes; it is not solely an in-memory cache counter.

The fabricated probe contains1000 distinct identities but repeats spatial facts,
with two centers x three borders:6000 layouts. Leaf size4/fanout4 forces2000
leaves and deeper trees. Twelve Top50 comparisons matched exhaustive results.
Publication plus integrity audit took27.57s; the whole probe94.05s, peak process
RSS96,919,552bytes, supervised output42,205,902bytes. Some probe runtime overlapped
the failed BDS startup diagnostic, so this is not a calibrated throughput result.

## Actual-game evidence

Two fresh disposable world attempts used the already installed pinned BDS image
`sha256:cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8`.
The first failed startup under extra network isolation; it produced no accepted
observations. The second used the adapter's normal bridge network with no
published ports, under a reduced900s allowance. Combined actual attempt time was
140.73s, within the1200s cumulative cap. Both attempts removed their owned tagged
containers and volumes; existing worlds were outside the cleanup boundary.

The second attempt observed16/16 requested surface biomes, no missing cells,
with stable repeated scans. Its adapter status remains PARTIAL because point
observations do not certify a complete footprint. Matching XYZ predictor
comparisons had15 literal name matches; the remaining `jungle_edge` versus
`sparse_jungle` pair matches the project's preexisting alias map. Thus16/16 match
after that explicitly recorded normalization. This one-seed sample does not
validate the full model, all23 features, exact spawn or build compatibility.
Observed BDS1.26.52.3 and catalog `research:26.50` identities remain separate.

The resource wrapper labels fresh resources, refuses existing names, bounds
container CPU/memory/logs/root writes, monitors newly owned host+volume bytes,
and installs a container lifetime guard that survives coordinator failure.
Recorded samples are watchdog observations, not an atomic filesystem quota.

## Workers and independent checks

High Gemini storage0688996fb942 and indexa2467ae8dbb0 succeeded with exit0 and
no denied actions; Codex reviewed, integrated only owned files, and hardened the
implementation. UI7c283c6cfbc1 failed independent acceptance because its isolated
workspace could not resolve TypeScript dependencies. Provider exit0 was not
treated as acceptance: its owned new files were imported as unverified work,
corrected by Codex, and type/build/contract checks were run in the primary
environment.

High plan critique5d328b5f270f and game-wrapper critique7cd7c3d5d99f succeeded.
The latter's cleanup-signal and disk-accounting concerns were addressed; its
shell-alias warning did not apply to the actual Python function interception.
Optional final cache review9bdf2a9282b3 exceeded its180s limit and returned no
usable review; it is not counted as independent approval. Manual review and
focused cache/cursor/integrity tests passed. No quota/account switch or permission
bypass occurred.

Focused cache/integration/service checks:8 passed; detail/integrity/process-death
checks:10 passed; game-wrapper ownership and command construction:2 passed.
All18 existing Node network contracts and new signed64/filter/favorites/card-render
checks passed. Fresh external frontend builds passed without replacing live dist.
Full Python run:1488 passed,1 failed in561.22s; all215 Catalog tests passed.
The unchanged personal-pipeline test
`tests/test_native_throughput.py::test_pipeline_three_stages_and_exact_partial_resume`
failed its scheduler-overlap assertion at line171. Its exact isolated rerun passed
all checks in8.47s. The original failure is retained; this is not a clean all-pass
full run. No personal-pipeline source or test was changed to suppress it. Detailed
results: [verification.json](verification.json).

## Remaining gates and limits

- Connected-browser visual, responsive and keyboard acceptance after the latest
  fixes is pending: CUA reports no available browsers/apps. An earlier browser
  run visibly returned catalog results before the final presentation fixes.
  Server/API tests and static card rendering do not replace interactive QA.
- No actual player request corpus was supplied. Participant usefulness is
  explicitly not evaluated; developer/synthetic requests do not establish demand.
- Spawn, generated-structure presence, terrain/absence guarantees and public
  game-build compatibility remain unaccepted. Public capability/billing stay off.
- The legacy import bridge still loads a bounded old manifest and is capped at200
  source worlds. Publication holds scalar generation membership in memory;
  snapshots, metadata and matched-world accounting still grow with population.
  This is not evidence for million-world storage or throughput.
- Request cancellation discards stale client results; an admitted server request
  may continue until its iteration deadline. Blocking storage calls have their own
  timeouts. The service is loopback/private, not hardened multi-tenant hosting.
- No automatic garbage collection, physical eviction, accounts/cloud favorites,
  payments, GPU acceleration or custom durable database construction is included.

No commit, push, reset, stash, clean or live Sweep restart was performed. Final
preservation checks confirm both native binary hashes, HEAD and the staging index
match the baseline. Every baseline file outside the eight declared integration/
handoff changes is unchanged; no baseline file is missing. Original SweepPID60144
retains its October16 start time. Builds targeted external directories, preserving
live dist. The user subsequently chose “Leave browser QA pending.” This closes the current
implementation/automated-validation stage with interactive acceptance explicitly
deferred; public release and the other empirical gates remain unaccepted.
