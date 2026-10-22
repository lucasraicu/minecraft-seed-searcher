# Public catalog automation v2

The supported contract is [PUBLIC_CATALOG_AUTOMATION_PLAN.md](../../../PUBLIC_CATALOG_AUTOMATION_PLAN.md). This is the existing Sweep application's catalog tab; GPU, custom database engines, billing and public hosting are separate work.

- Realm/Server Seeds: separate2048,4096,8192 Overworld boards. Scores remain1250 maximum:845 Overworld,265 luxury biomes,140 Nether. Nether stays1024×1024. Personal2048 scoring is unchanged.
- Presets:16 fixed rules centered on estimated world spawn (Nether: floor(X/8),floor(Z/8)). Distances are horizontal circles of150/200/300 blocks in the named dimension.
- Personalized Selection:31 features, all required rules at the same selected anchor. OW near-radii256/512/1024; Nether64/128/256 with fixed1024square. Strongholds remain bounded predictor observations. No arbitrary distance slider or route planning.
- Rare Seeds:17 defined launch records. The five terrain-heavy proposals are removed from the current catalog: Direct-Drop Portal, Badlands Spine, Mega Cherry Grove, Triple Mineshaft and Deep Dark Void. Historical definitions remain readable. Claims apply to the declared evaluated population and method, not all Minecraft seeds.

Exact rule names, scopes, capacities and predicates are in [products.json](products.json); no prose target is an admission rule. [realm_calibration.json](realm_calibration.json) freezes larger floors/bonus tiers and evidence. Original167development/33holdout split was retained. Original33holdouts had no larger qualifiers;21 selectively found independent controls validate2 qualifying4096 and19 qualifying8192 results without refitting. These are not prevalence or player-preference estimates. Score budgets preserve ceilings, not observed percentage contributions on each seed.

The frozen `deferred` IDs in products.json are historical metadata, not active
cards or promised future products. They have no extraction jobs or retention
objectives. Removing their cards does not change the existing policy digest,
saved scores, memberships or snapshots. No per-seed terrain generation, portal
traversal, physical-instance census or broad exact-absence scan is being added.

A public campaign selects at most100 deterministic sequence-index samples before personal rejection. One public child uses one numeric/native thread, nice+10,120s/world,4GiB RSS and2GiB output. A durable600-second allocation is never reset by ordinary resume. Personal and public jobs/checkpoints are independent. A personal winner is not automatically a public product match.

The catalog stores each world's absolute-coordinate structure observations, dimension/Y-specific biome samples and anchor provenance once. Derived per-anchor/per-border summaries drive filters; product memberships record their exact source/anchor. SQLite stores queue/receipts/TopK, while checksummed compressed CAS holds observations, summaries and immutable snapshots. Per-side CAS read projections avoid loading raw biome records during filtering. Large manifests page without changing their logical snapshot hash. Historical snapshots, pins, pending generations and resumable work protect shared objects before quarantine/deletion.

Missing sampled biomes stay unknown. Counts are viable predicted starts, not a physical census. Estimated spawn is X/Z evidence, not verified player landing, ground height or safety. Nether references are projected coordinates, not verified portals. Provider/height evidence accompanies refined biome witnesses.

The corrected helper retains the fitness-search X/Z before chunk centering.
It matched124distinct BDS1.26.52.3 controls, including8fresh frozen seeds; it
remains a prediction for unobserved worlds. The222-world migration reuses all
raw observations and preserves Realm/recommended results and historical links.
See the [spawn release evidence](../../../reviews/accuracy-advanced-products-2026-10-21/RELEASE_REPORT.md).

Operator commands (project virtualenv):

```sh
.venv/bin/python scripts/catalog_harvest.py --root /absolute/catalog/folder automation-status
.venv/bin/python scripts/catalog_harvest.py --root /absolute/catalog/folder automation-pause
.venv/bin/python scripts/catalog_harvest.py --root /absolute/catalog/folder automation-resume
.venv/bin/python scripts/catalog_harvest.py --root /absolute/catalog/folder automation-allocate
.venv/bin/python scripts/catalog_harvest.py --root /absolute/catalog/folder cleanup --mode dry_run
```

Configure pinned native/spawn adapters first with automation-configure. In the personal Sweep form select “Also build public catalog” and its configured absolute root. Public pause lets the current world drain; personal stop does not cancel registered public work. Allocate is an explicit new600-second public budget. Ordinary finite campaigns finish without an external manual drain. No new seed campaign is launched just by opening the UI.

With the folder blank, opt-in preview/start resolves the active catalog server's
configured root; an explicit folder remains an override. This avoids sending new
work to an old policy after migration, without restarting the personal backend.
The current local root is
`~/.local/share/antigravity-worker-mcp/spawn-correction-approved-20261021/catalog`.

Automated TypeScript/build, handler/contract, Python/source and Gemini High checks replace interactive browser QA at the user's request. Runtime/load measurements belong in the release report; no unmeasured billion-seed public throughput is promised.
