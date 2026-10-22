# BDS supported-type validation — 2026-10-20

User clarified: all supported types first, expand after results. Completed this finite
type-coverage audit before starting Stage D implementation. This is not full-catalog
point validation or certification of all future seeds.

## Results

Three deliberately diverse seeds: `3477702448211353566`, `-4565879772552070118`,
`-9103892851552028103`. All22 engine structure types were queried:193 predicted
positions plus176 independent fixed-location discovery queries. Every run observed
the exact signed world.seed on pinned BDS1.26.52.3, Script API2.10.0.

| Structure | Queries | Exact reported coordinate | Different coordinate | No reported location |
|---|---:|---:|---:|---:|
| trial_chamber | 9 | 0 | 9 | 0 |
| stronghold | 9 | 0 | 9 | 0 |
| mineshaft | 9 | 0 | 9 | 0 |
| ancient_city | 9 | 9 | 0 | 0 |
| village | 9 | 9 | 0 | 0 |
| ruined_portal | 9 | 9 | 0 | 0 |
| shipwreck | 9 | 9 | 0 | 0 |
| monument | 9 | 9 | 0 | 0 |
| outpost | 9 | 0 | 9 | 0 |
| fortress | 9 | 0 | 9 | 0 |
| bastion | 9 | 9 | 0 | 0 |
| desert_pyramid | 8 | 7 | 1 | 0 |
| jungle_temple | 9 | 8 | 1 | 0 |
| swamp_hut | 8 | 6 | 2 | 0 |
| igloo | 8 | 7 | 1 | 0 |
| ocean_ruin | 9 | 9 | 0 | 0 |
| mansion | 7 | 7 | 0 | 0 |
| buried_treasure | 9 | 9 | 0 | 0 |
| trail_ruins | 9 | 0 | 9 | 0 |
| abandoned_camp | 9 | 0 | 0 | 9 |
| ruined_portal_nether | 9 | 9 | 0 | 0 |
| end_city | 9 | 4 | 5 | 0 |

Biome cohort:360 points,66 predictor classes (56 Overworld,5 Nether,5 End).
Overworld sameXYZY63: 292/330 current block-lookup matches after
existing name normalization. An isolated raw-quart lookup matches 311/330;
vendor block lookup matches 292/330. These are selected
feature controls, not an unbiased accuracy rate. Initial snowy pilot:239/256 current
matches versus253/256 raw-quart matches. No production algorithm was altered.

Nether identifier pairs `hell`/`nether_wastes` and `soulsand_valley`/`soul_sand_valley`
must be treated as explicit nomenclature mappings; existing realm canonicalizer
does not include them. Do not call those literal-name differences algorithm failures.
All four outer-End predictor terrain classes were reported as `minecraft:the_end`
by BDS. That verifies the API identifier, not distinct terrain-class correctness.

Additional28 vertical/local-coordinate controls on the original village seed:
at three columns, Y=-48 yieldeddeep_dark, Y0/Y120/Y180/Y256/Y319 agreed with surface
names, but Y63 retained cave-versus-surface disagreement. This rejects the claim
that our Y63/Y63 comparison accidentally used different requested heights. Nearby
X446..452 control also supports a quart-vs-block sampling convention discrepancy.
This remains a diagnostic result; no universal replacement algorithm is validated.

## Interpretation and limitations

- Several raw-coordinate differences follow stable offsets: stronghold(-2,-2),
  mineshaft/fortress(-8,-8), outpost(+8,+8). These have supporting source-convention
  evidence and cohort controls, but no global fuzzy matching was applied.
- Trial chamber/trail ruins offsets vary; piece/orientation explanations remain
  hypotheses until independently established. Retain both coordinates.
- Large village/city/shipwreck/temple/End-city disagreements remain unresolved.
  Missing a locate match is not proof of physical absence or a specific terrain cause.
- Abandoned camp had no successful locate control. It remains unverified; nine
  no-location results do not establish global absence or command capability.
- The temple command groups desert/jungle/hut/igloo. An exact temple position
  is not independent subtype/building certification.
- Independent probes were deduplicated, but cannot establish exhaustive recall.
- `getGeneratedStructures` remained undefined on the actual pinned runtime.
  No physical-building census, safe spawn, farm suitability or generated-piece proof.

## Resource and isolation verification

Started with one BDS; later used at most two after observed memory was~0.5GiB.
CPU caps2 each. First cohort memory cap5GiB, subsequent2GiB; combined running
caps stayed within the8GiB Docker VM.600s/world,8GiB owned-output cap, no published
ports, unique labels and owned-only cleanup. Pilot259.56s. Cohort runtimes:
- `-9103892851552028103`: 294.56s; clean shutdown and owned-container removal.
- `-4565879772552070118`: 289.66s; clean shutdown and owned-container removal.
- `3477702448211353566`: 278.79s; clean shutdown and owned-container removal.

All game jobs ended before Stage D. Existing Sweep/catalog services and native
binaries preserved. No new seed-search campaign or project-source edit during audit.

## Workers and reconciliation

Gemini High critiques10fc702886ba/833bb6471b3d and analysis ef69bede9c65 completed
exit0/SUCCESS, denied[], files[]. They reviewed supplied evidence tool-free, not
independent BDS execution. Codex executed/parsing-checked the actual game probes.
Rejected worker claims of physical absence/terrain root cause, arbitrary tolerances,
global accuracy, unmeasured multi-TB costs and a Y319/Y63 explanation for sameXYZY63
differences. See PLAN.md for the explicit reconciliation.

## Next authorized work

Stage D evidence steps1–3: shared versioned verification overlays and honest
API/UI summaries, retaining disagreements and keeping unqualified presets gated.
No blanket verification badge, native predictor rewrite or silent raw snapshot mutation.
Broader native semantic fixes require a focused evidence-backed plan.

## Evidence

[type-summary.json](type-summary.json), [pilot-biome-summary.json](pilot-biome-summary.json).
Raw reproducible scripts, reports, logs, controlled worlds and comparison source hashes:
`~/.local/share/antigravity-worker-mcp/catalog-all-predictions-audit-20261020/`.

Command/XYZ semantics consulted against official Microsoft docs:
[locate](https://learn.microsoft.com/en-us/minecraft/creator/commands/commands/locate?view=minecraft-bedrock-stable),
[Dimension.getBiome](https://learn.microsoft.com/en-us/minecraft/creator/scriptapi/minecraft/server/dimension?view=minecraft-bedrock-stable).
Runtime output takes precedence over API availability in newer documentation.
