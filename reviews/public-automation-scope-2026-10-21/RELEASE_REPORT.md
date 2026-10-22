# Public catalog automation — completed local milestone

Completed2026-10-21. Approved scope: [implementation plan](../../PUBLIC_CATALOG_AUTOMATION_PLAN.md), including the full existing UI and calibrated larger Realm boards. No GPU port, custom database engine, payment activation, public hosting or new personal sweep was added.

## Delivered behavior

Personal search keeps its2048 policy, OpenMP build, Top50 and checkpoints. Its opt-in catalog descriptor is registered before personal rejection. A separate bounded CPU supervisor automatically extracts the deterministic public sample, evaluates products, updates persistent TopK memberships, publishes immutable snapshots and acknowledges work. Personal stop does not cancel the registered public campaign. Ordinary retries wait automatically without renewing the durable allocation.

The existing catalog tab has four working pillars:3 Realm boards,16 fixed Presets,31-feature Personalized Selection including strongholds and dimension-specific Nether filters, and17 defined Rare Seed products. Five unsupported terrain/farm records remain deferred. Current UI uses actual memberships, source-bound witnesses, separate OW/Nether scopes, pending counts, pagination and full signed64 seed strings. Legacy Origin research appears only with a legacy snapshot; old shares and research endpoints remain readable.

| Current Realm board | Retained matches | Pending evaluations | Best retained score |
|---|---:|---:|---:|
|2048|1|0|377|
|4096|2|161|640|
|8192|21|173|785|

These are predictions at declared supported centers. Pending center budgets are not failed seeds or physical absence. All scores retain1250maximum and group ceilings845OW/265luxury/140Nether. The Nether square remains1024×1024. Floors and surplus tiers are frozen in [realm_calibration.json](../../docs/catalog/v2/realm_calibration.json).

## Calibration and refreshed data

The original200-world cohort retained167development/33held-out seeds. CDF thresholds were frozen before a bounded2000-input expansion from receipt-proven completed personal sweep inputs. Twenty-one selectively prioritized independent controls passed raw-coordinate, lattice, family and shared-score oracles:2 qualifying4096 and19 qualifying8192. Original holdouts still have0 larger qualifiers; no parameter was refitted to them. Controls establish feasible rule execution, not population prevalence or player-preference calibration. Luxury saturation at8192 was17/33 original holdouts; a Gemini misquote of17/21controls was rejected.

The v2 sidecar now contains222 worlds (200 original,21 selected expansion controls,1 known personal control),53,846 winning memberships and7,027 registered objectives/105,644 total slots. It preserves the legacy200-world snapshot rather than replacing its files. Raw facts include dimension/Y-specific biome observations,17 public structure inventories, internal Realm facts, and anchor provenance. Per-border summaries and CAS read projections reuse those observations; there is no threefold raw-world extraction.

Current snapshot: `3d5b0d69a3afda2a6af3333b9860c3ef5b71c45ac4e8d2a5fc72d2a7a0e69232`.
Legacy snapshot: `18ca9deb3da9ed0d9dec553cf1447d3ffbf9ac2ed003d1dccc5a0d5af336ba93`.

Catalog root: `~/.local/share/antigravity-worker-mcp/private-pilot-indexed-import-20261020/catalog`.
Evidence/log root: `~/.local/share/antigravity-worker-mcp/public-automation-20261021/`.

## Reliability and measured performance

- Durable budget600s; one public child, one native/numeric thread, nice+10,120s/world,4GiB RSS,2GiB output,3attempts,100 samples/campaign. Ordinary resume does not renew allocation.
- CAS staging precedes transactional membership; generation/manifest/pointer publication precedes job acknowledgement. Real import budget interruptions at90/165/219 durable worlds recovered to222 unique worlds without losing winners or altering old shares.
- Idle/output-pressure reclamation is connected to the supervisor. It reserves the remaining existing budget before work, verifies protected history/pending roots and source-bound bundles, quarantines before deletion, and only reclaims acknowledged explicitly non-resumable staging. Partial, leased, failed and unknown work is preserved. Tests cover symlinks, resource exhaustion, quarantine crashes and replay. Deadline checks occur between bounded reads/file operations; elapsed time is charged, including an operation finishing beyond its prior check.
- Large logical manifests page into checksummed CAS objects. A21.80MiB/20,000-reference synthetic manifest roundtripped through20 default-limit pages with identical logical digest. This is a metadata-capacity proof, not20,000 natural worlds.
- Fixed an observed per-offer full-observation rehash:496 offers remained identical,23.06s became0.37s. Indexed refinement-pending checks preserved all64 tile IDs/order, facts and product decisions. The same real public control completed in30.15s versus81.77s earlier. These are single-control timings, not personal-screening or billion-seed throughput claims.
- Nine application-cold query cases each passed for all3 borders ×3 anchor modes: actual222 worlds5.26–5.80s;500 synthetic worlds/123,000 layouts5.25–7.01s. OS disk caches were not flushed; some import work ran concurrently. These timings do not establish latency during a fully saturated personal sweep. The10s service deadline was unchanged.
- Two simultaneous real HTTP queries through the two owned query processes passed in5.82/6.28s. Cache/cursor pages and disjoint result pages passed. The full query result and unresolved statistics match raw-summary oracles across sides/modes/dimensions.
- Queries use immutable per-side projections bound by CAS root, raw-bundle/source identity, exact row count and validator fingerprint. Full schema validation remains at stage/publication, raw detail and reclamation; older/mismatched projections take full validation. Corruptions and source splices fail closed.

## Verification and independent review

- Final Python catalog + telemetry suite: **560 passed** in231.65s. Focused HTTP checks36passed and reclamation/controller/storage checks56passed cover the final integrations.
- All9 Node catalog suites pass, including16 v2 product/decoder checks, handler focus/close/copy/stale-state checks, scoped registry loading and signed64 guards. All36 actual launch-product HTTP responses also pass the real frontend decoder.
- Final TypeScript/Vite build passes (54modules). Interactive browser QA was waived by the user; no visual/browser session is claimed.
- Real HTTP opt-in preview passes its catalog fields to the machine command with `--catalog-root`, `--catalog-sample-cap100` and the corrected OpenMP build. It does not launch a search. A real handler regression catches the request-allowlist omission discovered during final integration.
- Gemini High implementation workers7486d9c2dfb9/35cdb54f4b54/edbafad8f3c2/274b63ced4c4 supplied fitter, observations, retry and paging components;1c06d3bea000 supplied scale tests. Codex reviewed patches and corrected additional validation, accounting and oracle issues. High critiques/reconciliations are retained in this directory, including calibration2f90898caf0e, UIa20316b6c0e9, projectionsd3115949707f/f3d965a71c15/d900b0fd9a11 and reclamation1735714614d1. No rejected suggestion was automatically accepted.
- The MCP bridge separately passed42 tests and real coding tasks lasting771/790s, proving the expanded worker deadlines. High reasoning, isolation, denied-action checks and shared-account quota rules remain enabled. No account switch or quota bypass occurred.

## Adoption, preservation and remaining boundaries

UI: http://127.0.0.1:5173/#catalog . Catalog91320/3001 owns query workers91323/91325; personal backend91321/3000; Vite65292. Both backends load current source. Public control is active with0consumed/600s and no registered campaign; no seed search was started by adoption. The existing Sweep checkbox can register future independently sampled work against the configured root. See [operator instructions](../../docs/catalog/v2/README.md).

Personal run `web-sweep-20261020-143452-e5161c27` still shows seed `-3336796033057908633` at historical336. Its SQLite/restoration hashes and both native binaries are unchanged. Current-source catalog replay gives377 at[-624,-776], without rewriting the historical score. Native source fingerprint remains `72694b1420170b4582358eef577cc252c11e138daec817bbf97d4af68e645c1a`. Existing dirty work was preserved; no commit, merge or push was performed.

Estimated spawn remains estimated X/Z, not first-player landing/ground/safety. Counts remain viable predicted starts, not a physical structure census. Sampling cannot prove unsampled biome absence. Record ranks describe the evaluated, selected catalog population, not global Minecraft records. Historical snapshots do not expire in this milestone, so protected history can exhaust the2GiB allowance and pause intake. History expiry, production hosting/billing, GPU/fleet scaling and a custom serving-engine comparison remain separate work.
