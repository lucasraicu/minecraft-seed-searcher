# Phase3 CPU public-catalog reference — completion report

2026-10-20, America/Los_Angeles. User approved the corrected CPU reference slice
after the Argon review and SQLite-first decision. This is not Argon's numbered
CUDA phase. The separately requested larger validation stage is now included in
overall planning; its concrete limits/plan await approval, and no larger run started.

## Delivered behavior

The new source-tree developer CLI extracts independent public observations, saves
them in a separate SQLite/artifact store, derives all243 saved layouts per world,
and answers supported requests without applying personal search's admission floors.
No custom database engine, GPU kernel, personal scoring change, live service
restart, public UI, payment or game-world certification was added.

- One absolute structure inventory and one Y63/stride64 biome plane per world
  cover the shared tile-aligned[-5120,5120) envelope. Each of81 anchors can use
  side2048/4096/8192. Origin shares the existing(0,0) anchor.
- Exactly14 structure and9 biome-family reference features; strict Required AND
  on one layout, positive biome alternatives OR, distinct Preferred utility,
  declared profile fallback, deterministic unsigned-seed ties and world dedup
  before TopK. No arbitrary radius sliders or hidden floor relaxation.
- Full uint32 counts for256/512/1024 and whole border, border-clipped nearest
  squared distances, saved biome witness references and feature completion flags.
  Layout feature payloads are364 bytes, rather than Argon's insufficient card.
- Unknown, partial, failed and complete observations remain distinct. Incomplete
  Required facts fail; incomplete Preferred facts earn zero and stay labeled
  unknown. Backend inclusive bounds are translated to the new half-open contract.
- Version/settings/model/source/native/registry/extractor identities are explicit;
  seed JSON uses signed64 decimal strings. Actual model label is26.50, exposed as
  research:26.50, not accepted support for every Bedrock1.21+ build. Public game
  acceptance, spawn, mandatory strongholds, verified basements and Nether stay gated.
- Standard deterministic gzip bundles are bounded/checksummed. SQLite stores
  metadata and packed payloads; publication follows durable artifact creation.
  Snapshot IDs bind memberships, payload hashes and policy/registry revisions.
  Readers verify references; replay does not silently accept corrupted manifests.
- Separate catalog roots reject incompatible/personal databases before write-mode
  pragmas. Symlink/traversal, truncated compressed streams, corrupt payloads and
  failed durability calls fail closed. Reader startup does not delete live staging.
- CLI uses fresh output roots, exact source/control checks for resume, supervised
  native child processes and cumulative budget reservations. Completed seeds are
  reused without new extraction. Backup includes SQLite plus referenced artifacts
  and validates the restored snapshot independently of the original data paths.

Guide: [src/seed_search/catalog/README.md](../../src/seed_search/catalog/README.md).
Entry point: [scripts/catalog_reference.py](../../scripts/catalog_reference.py).
Registry/policy documents remain source-tree dependencies; no product runtime
activation flag was changed. The illustrative catalog SQL is not applied to the
personal database; this reference has its own marked runtime schema.

## Worker provenance and coordinator review

High Gemini via antigravity-workers, isolated dirty snapshots:
- fde7cc492717: artifacts/SQLite and12 original passing worker tests.
- 0f6ca51da4b8: summaries/query and13 original passing worker tests.
- e45dab129e51: extraction task failed on denied RunCommand; empty SUCCESS was
  rejected, no patch accepted and no permissions broadened. Codex wrote extraction.

Actual launch flags gemini-3.8-flash-high --effort high, exit status, denied actions,
checks and ownership/drift were inspected. Only the six owned new successful files
were manually integrated. Codex wrote shared contracts, CLI, independent raw oracle,
resource validation and additional safety tests, then repaired integration defects.

Material coordinator corrections: incomplete positive evidence could pass Required
or earn Preferred utility; uncaught limits/build/layout identity mismatches; rounded
reported scores; unknown fallback components; reader cleanup of live staging;
symlink temporary/database paths; silent directory-fsync errors; missing gzip EOF
checks; manifests not binding actual layout BLOB hashes; corrupt snapshot replay.
The original worker test that rewarded incomplete biome scopes was corrected to
the approved conservative contract. Regression checks were strengthened, not hidden.
Full details: workers.json and verification.json.

## Verification

**Full project suite:1342 passed,0 failed,459.63s.** New catalog suite:68 tests,
including one220-case independently generated raw-coordinate request oracle.
Focused existing personal/backend/seed/store/leaderboard/recovery checks:79 passed.
No frontend build was needed; no frontend files changed in this phase.

The two independently preselected signed64 seeds were-5959916077745768304 and
454251624725559791 (seed_from_index indices0/1 with fixed key0xCA7A10), selected
before relevance evaluation. Both completed all23 predictor feature observations,
each with25600 biome samples and respectively2617/2629 predicted structure starts.
There were no personal gates, missing feature failures or additional real seeds.

An independent raw-coordinate calculation checked every actual saved layout:
486 layouts;27216 structure scope counts;6804 nearest structure distances;4374
biome nearest distances and4374 witness references. All matched. This verifies
summary arithmetic over stored predictor observations, not physical Minecraft.

Actual snapshot restore and all six size/mode combinations passed; CLI JSON query
execution also passed. Resume produced the identical snapshot with0.0 additional
extraction wall seconds and both jobs marked resumed_without_extraction.

## Small-cohort measurements

One native CPU thread on the shared iMac, two worlds only; not a throughput model.

| Measurement | Observed |
|---|---:|
| Total extraction subprocess wall |4.783s|
| Fresh entire run including summaries/publication |6.442s|
| Per-world summary derivation |0.404s /0.364s|
| Publication and verified reload |0.735s|
| Polled peak child RSS |~72.5MB /64.4MB|
| Packed feature payloads for486 layouts |176904 bytes|
| Compressed world observation bundles |90728 /91557 bytes|
| Snapshot manifest bundle |56410 bytes|
| Initial run directory including checkpoints/SQLite/artifacts |2056758 bytes|

Canonical JSON lengths differ from the report's default-spaced JSON diagnostic
lengths; measurements.json lists both actual bundle sizes and diagnostic lengths.
Do not divide a two-world directory size into a production bytes/world estimate.
Backups and later verification files add more bytes than the initial report.

Six functional query calls took~0.17–0.19s each including repeated raw-observation
validation under simultaneous background regression tests. These are not a clean
latency benchmark, cache/index measurement or p95. They motivate separating a
verified immutable snapshot read view from repeated full raw validation later;
they do not validate Argon's submillisecond API claims.

The probe stayed inside its approved2-seed,300s,<=4CPU-thread,4GiB child-RSS and
1GiB output watchdog limits. Watchdogs poll, and are not instantaneous kernel
isolation guarantees. No actual fleet device was used or extrapolated.

## Preserved state and limitations

Baseline1268 files:1262 unchanged; six preexisting documentation/handoff files
updated to describe the reference. Existing implementation/native/UI files,
Argon's document, Git HEAD/index and original native binary hashes are unchanged.
Original server PID60144 remained running with its original start time. No commit,
push, reset, stash, clean, deployment or existing checkpoint modification occurred.
The preexisting native/bridge.c:536 EOF blank-line diff warning remains untouched.

Research limits: no actual-game recall/accuracy audit; no partial-tile query API;
conservative whole-envelope completion; standard gzip JSON rather than optimized
binary tile observations; flat manifests with16MiB/artifact caps; no orphan GC;
conservative crash-budget reservation rather than tested campaign process-death
recovery; no selective retention, large corpus, public routes/UI or billing. A
root process can still mutate its own developer records; this is not hostile
multi-tenant isolation. Current backup tests and exception injections are not
hardware power-loss or production deployment certification.

## Next requested work

[NEXT_VALIDATION_PLAN.md](NEXT_VALIDATION_PLAN.md) proposes the now-requested larger
ingestion/retention/recovery stage:100 predeclared worlds,10+90 preflight,serial1CPU,
15min extraction /30min job cap,4GiB RSS,2GiB output, reduced-cap/adversarial retention
experiments, held-out query metrics and owned-process-death tests. It has an
independent High critique617ed6a13c38 and reconciled objections. Earlier review
8c467d607100 failed on a denied command; no result/permission bypass accepted.
The installed server remains capped at4 workers despite permission to use more
if helpful; no extra concurrency was necessary. No100-world job has run.

Current Phase3 is complete. Under AGENTS.md the new significant execution plan
must be presented for approval before its implementation/run. Estimated engineering
work remains several focused days to1–2 weeks, with measured tails/recovery findings
determining the next ETA; the bounded compute job itself is not a week-long run.
