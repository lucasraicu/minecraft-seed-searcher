# Chunkbase review workflow

Adopted 7 October 2026 at the user's request: use Chunkbase as the primary external prediction reference and defer building a Minecraft/BDS validator. Actual Minecraft confirmation is an optional final check, not a prerequisite for the bounded pilot.

## Search and review

1. Use the local native model to discover and rank seed/center candidates quickly. Complete the remaining terrain metrics, ranking and persistence work, then measure a small bounded pilot before increasing its budget.
2. Review a small shortlist in [Chunkbase Seed Map](https://www.chunkbase.com/apps/seed-map). Enter the full seed as decimal text and select **Bedrock 26.50–26.52**. Check both the Overworld and Nether, and recheck the matching selection if the target version changes.
3. Enable **Terrain** for coastline review. Check the proposed island, surrounding water, high terrain and woodland biome coverage. Do not equate woodland biomes with measured log/canopy density, or visual map separation with a block-perfect island guarantee.
4. Check structure locations and border eligibility at each candidate's actual centers. The Overworld square is 3008 blocks wide; the Nether square is 992 blocks wide. Record displayed coordinates, offsets, dimension and whether the marker lies inside the square. Whole structure access/footprints near an edge remain uncertain.
5. Use Chunkbase to resolve candidate-level predictor disagreements for selection. Local viability rejection alone must not be described as proof of absence; retain promising disagreements for review, particularly required Nether targets. The implemented ranking/filtering pipeline preserves raw rejected starts and requires recorded website markers before disputed required targets can become website-confirmed eligible.
6. Save each external result with the version, seed, coordinates, source link and review notes. Label it `chunkbase_checked`, while actual Minecraft confirmation remains a separate evidence field. A brief optional phone inspection of the chosen island and required structures can catch the remaining practical issues before Realm setup.

## Practical limits

The existing browser-based audit demonstrates that shortlist review is usable. The site's documented search operates around positions within one seed and supports feature/biome/terrain conditions. This project has no verified public bulk-search API or unattended high-volume integration; millions of website lookups are not the proposed search engine. Use the native model for volume and the website for finalists.

The claimed **99.99% accuracy** was not substantiated by Chunkbase's own Seed Map documentation. The site lists missing/incorrect features, occasional structure generation failures, marker offsets and coastline differences. These remain accepted prediction limitations, not automatically failed project gates. No external prediction is relabeled as an observed Minecraft fact.

[Chunkbase's own limitations](https://www.chunkbase.com/apps/seed-map#troubleshooting), [our four-seed audit](runs/accuracy-audit/REPORT.md), and [existing phone observations](fixtures/bedrock-26.52/seed-12345.user-observations.json) remain available separately.

The large-search flag stays false. The implemented readiness gate additionally requires verified, matching-identity evidence before a large sweep. No server, VM, launcher, addon verifier or new large search was installed or started by adopting this workflow.

## Current expanded landscape policy

The later user instruction requires **Fortress in the992-block Nether square and Stronghold in the3008-block Overworld square**. Bastion is optional. Check the landscape-specific fields: ocean islands need separation/ocean setting/nearby wood/build ground; dry mountain basins need a dry connected flat floor, enclosing mountains and nearby wood; enclosed inner islands retain the water/mountain/external-wood review. Preserve missing Strongholds as unresolved enumeration rather than treating them as known absent. The authorized fast filter saves unpredicted locations in `stronghold-deferred.json` and a recovery seed file. Use a separate bounded `review-all.yaml` rank run to restore terrain analysis for those cases. The initial expansion/guide assessment is in [LANDSCAPE_EXPANSION.md](LANDSCAPE_EXPANSION.md); current filtering and verification are in [FILTER_OPTIMIZATION.md](FILTER_OPTIMIZATION.md).
