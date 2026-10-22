# Four pillars and opt-in CPU harvesting

This is a private research implementation in the existing Sweep/Catalog app.
It does not activate payments, public hosting, GPU kernels or a new database
engine. Browser acceptance remains deferred by the user's instruction.

## What the four entries provide

| Entry | Current behavior |
|---|---|
| Realm/Server Seeds | Qualification criteria and explicit evidence gates; no fabricated certified seeds |
| Presets | All16 named Sweet16 cards in five themes; fixed150/200/300-block predicates, inspectable unmet dependencies |
| Personalized Selection | Existing23-feature query engine, Required/Preferred filters, three square borders, Origin/Recommended, details/comparison/favorites/export |
| Rare Seeds | Four halls with22 named future records and five separate research density previews |

Presets are gated until their exact evaluators, anchor coverage and evidence are
available. The platform describes a target of50 records but defines only22;
the other28 are not invented. Research preview IDs are deliberately distinct from
promised spawn/terrain/farm records. They rank predicted village, trial chamber,
ruined portal, desert pyramid and shipwreck starts within a **closed2,000-block
Euclidean circle centered on Origin(0,0)**. No world border is applied. Counts are
exact over saved predicted starts, not proof of generated blocks. Ties use world
ID ascending; lists contain up to100 positive-count worlds with complete coverage.
Maps draw the actual circle and only its witnesses. Seeds remain signed64-bit
decimal strings throughout JSON and UI.

## Use the preview without touching the running Sweep

Follow [PRIVATE_PILOT.md](PRIVATE_PILOT.md) to run a separate Catalog backend3001
and Vite5173, then open `http://127.0.0.1:5173/#catalog`. The existing process3000
does not hot-load Python changes. Its source and live `web-ui/dist` were not
replaced/restarted by this implementation. A new backend/preview loads new source.

Derive research lists for an existing immutable snapshot (no seed extraction):

```sh
.venv/bin/python scripts/catalog_products.py \
  --root /absolute/path/to/segmented/catalog --snapshot SNAPSHOT_HEX64
```

The default local corpus is outside Git at
`~/.local/share/antigravity-worker-mcp/private-pilot-indexed-import-20261020/catalog`.
Its200-world snapshot is
`3d964acd07729a1aa50c23ba90e90a37754c009fc685f0313cc6cf0157eddd6a`.
Five previews were derived from those observations without extraction. A new
snapshot needs its own derivation. Files under `product-previews/` bind snapshot,
definitions, build header and checksum; HTTP serving reads these bounded files,
not raw worlds. Missing/corrupt previews return explicit errors.

## Connect a NEW native personal scan

Append these options to your existing new native CLI scan command, retaining its
policy, output, thread/build and range options:

```text
--catalog-root /absolute/path/to/public-catalog --catalog-sample-cap 100
```

The public root and personal run directory must be separate, nonnested, real
directories. The flag defaults off. It is supported for new native scans only;
Python scans reject it, and it cannot be added to an existing checkpoint on resume.
An enabled scan retains the same catalog identity on resume. Dry-run does not
write/register a handoff. No extractor is launched by this flag or an HTTP query.

Before personal qualification, the CLI writes an immutable descriptor to
`PERSONAL_RUN/catalog-handoff/CAMPAIGN_ID.json`, then registers it in the separate
public `harvest.sqlite`. It records the declared sequence/range, source/build,
sampling and resource limits. Public samples do not depend on personal survivors
or score. Descriptor persistence failure stops opt-in preflight; queue contention
or failure reports `detached` while personal work proceeds with a replay source.

Public work may run ahead of personal progress. **Stopping the personal scan does
not cancel the separately registered public samples.** Inspect or control them:

```sh
.venv/bin/python scripts/catalog_harvest.py --root /absolute/path/to/public-catalog status
.venv/bin/python scripts/catalog_harvest.py --root /absolute/path/to/public-catalog drain --max-worlds 100
.venv/bin/python scripts/catalog_harvest.py --root /absolute/path/to/public-catalog pause --campaign CAMPAIGN_ID
.venv/bin/python scripts/catalog_harvest.py --root /absolute/path/to/public-catalog resume --campaign CAMPAIGN_ID
.venv/bin/python scripts/catalog_harvest.py --root /absolute/path/to/public-catalog cancel --campaign CAMPAIGN_ID
```

Drain is explicit and performs real CPU extraction; setup/testing did not run a
new natural campaign. Only one drain/native child runs per public root. A second
drain reports `worker_already_running`. Future Sweep UI launch controls are not
included. Do not start real drains until you choose the campaign/resource budget.

Initial caps: at most100 deterministic, evenly spaced indices per campaign,
100 pending jobs, one native/numerical thread at nice+10 where supported,
120 seconds/world,600 seconds/drain,4GiB RSS and2GiB output with publication
headroom, at most3 attempts and bounded backoff/logs. Lower limits are allowed;
larger limits/campaigns need a separately measured budget. Scheduling is a declared
bounded cohort, not a claim of unbiased sampling. Personal results must remain
identical; resource contention can still affect elapsed time.

## Recovery and data ownership

Re-register a detached descriptor without rerunning personal search:

```sh
.venv/bin/python scripts/catalog_harvest.py --root /absolute/path/to/public-catalog \
  register --descriptor /absolute/path/to/personal-run/catalog-handoff/CAMPAIGN_ID.json
```

Queue expansion is lazy; backpressure leaves the remaining frontier recorded.
Pause/resume/cancel operate on the selected campaign; shared world jobs retain
other active owners. Cancellation cannot be reversed, but a new campaign may
independently request the same world. Failed/partial/deferred are not complete
zero counts. Status reports job states and scheduled samples, not personal visits.

Each lease has an owner and increasing generation; stale generations cannot
acknowledge or publish. Checkpoints are atomic checksummed envelopes in private
generation-specific staging. Only compatible complete features are reused. New
publication requires all23 features and the full sampled biome lattice; existing
public-query unknown semantics stay unchanged. Existing compatible published
observations are reused. A crash after publication but before acknowledgement
replays against the existing world and acknowledges it without duplicating it.

The supervisor signals only directly owned subprocess groups, never a PID from
stale queue metadata. Native children watch for parent death. Publication and
lease transitions share an ownership lock; a hung publisher pauses catalog
recovery rather than allowing stale publication. Personal registration does not
take that lock and has a250ms SQLite wait plus durable spool fallback.

This bridge independently enriches public worlds; it does not pretend compact
personal survivor packets contain complete public inventories. SQLite/artifacts
remain canonical. Spawn, Nether records, physical structures, terrain contiguity,
farms and portal safety retain their separate evidence gates.
