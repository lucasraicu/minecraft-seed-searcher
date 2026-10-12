"""Explain the limits and findings of positive-only million-run replay."""
from pathlib import Path
import json

ROOT=Path('runs/count-bits-2026-10-11')

def main():
    r=json.loads((ROOT/'million-count-feasibility.json').read_text())
    v=json.loads((ROOT/'million-count-replay-verification.json').read_text())
    bits=json.loads((ROOT/'million-bit-reuse-distribution.json').read_text())
    current_biome_example=json.loads((ROOT/'million-example-current-biome-grid.json').read_text())
    rows=[]
    for key,p in r['profile_results'].items():
        need=p['requirement'];s=p['distinct_seeds'];a=p['anchors']
        rows.append(f"| {key} | {need['village']} | {need['trial_chamber']} | {need['ancient_city']} | {need['mineshaft']} | {s.get('overworld',0):,} | {s.get('overworld_and_nether',0):,} | {s.get('overworld_nether_forest2_taiga1_first_witness_lower_bound',0):,} | {s.get('overworld_nether_forest3_taiga2_first_witness_lower_bound',0):,} |")
    maxima=[]
    ceilings={'village':16,'trial_chamber':16,'ancient_city':25,'mineshaft':9216,'monument':16,'outpost':4,'shipwreck':25,'ruined_portal':9}
    for name,item in r['retained_positive_maxima'].items():
        e=item['example'];ceiling=ceilings.get(name,'Nether; OW ceiling not applicable')
        maxima.append(f"| {name} | {item['count']} | {ceiling} | {e['seed']} | {e['stronghold']} |")
    profiles=r['profile_results']
    example=profiles['more_core']['examples'].get('overworld_nether_forest3_taiga2_first_witness_lower_bound')
    if example is None:example=profiles['more_core']['examples'].get('overworld_and_nether')
    text=f'''# Count requirement feasibility from the retained million-seed benchmark

The million run can establish **observed coexistence and larger observed counts for categories it actually recorded**. It cannot establish absolute achievable maxima, complete counts for unqueried categories, or current filter throughput. This analysis reused its saved coordinates without launching another seed search.

## Geometry and coverage

The historical benchmark ran 1,000,000 distinct full64 inputs with **5000×5000 discovery / 2688×2688 Overworld / 1024×1024 Nether**. Its 2,629,026 candidates are Stronghold anchors, not distinct seeds.

This read-only scan examined **{r['candidates_scanned']:,} candidate records**, retained **{r['retained_anchors_in_current_discovery']:,} anchors** across {r['distinct_seeds_with_retained_anchors']:,} distinct seeds inside today's 4000×4000 discovery, then cropped each recorded start inventory to **1536×1536 Overworld** at that same Stronghold and **896×896 Nether** at its exact Stronghold/8 center. Scan time was {r['elapsed_seconds']/60:.2f} minutes. No candidate centers were shifted to improve counts.

All retained anchors are considered; this differs from the smaller count pilot, which froze the first selected anchor per input. Lower and upper border membership use half-open bounds. Counts deduplicate coordinate pairs within each structure type. A profile is matched only when its requirements coexist in the same candidate's border.

## Selective combinations found

Each row requires at least the listed number of distinct starts of each type, plus its chosen Stronghold anchor. Columns show **distinct seeds with retained positive evidence**, not anchor totals, estimated world probabilities, or complete rejection rates. One seed can occur in several rows.

Nether means at least one Fortress and one Bastion together inside 896×896. Biome columns additionally require the listed number of **distinct active biome IDs** within Forest and Taiga, witnessed inside that same 1536×1536 border. These biome counts are conservative lower bounds from stored first witnesses at Y=63; they do not replay the new four-Y world-aligned sampling policy.

| Requirement profile | Villages | Trial Chambers | Ancient Cities | Mineshafts | OW evidence | + Nether | + Forest 2 / Taiga 1 | + Forest 3 / Taiga 2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

These selective requirements have positive examples; the zero-result rows only mean that this retained evidence did not demonstrate them. Old early exits left later checks unqueried, so a zero row is not a proof of impossibility. Terrain and actual-game generation remain unevaluated.

A concrete example for the `more_core` profile is seed **{example['seed']}**, centered at Stronghold **{example['stronghold']}**. Its retained cropped structure counts are `{json.dumps(example['counts'],sort_keys=True)}`. Its retained first-witness biome family counts are `{json.dumps(example['first_witness_biome_family_counts'],sort_keys=True)}`. This is one coherent border, rather than separate category maxima combined across seeds.

A fresh inventory of this example on the current world-aligned 64-block lattice at Y=63,-48,0,160 found **{current_biome_example['distinct_family_ID_counts']['forest']} Forest IDs and {current_biome_example['distinct_family_ID_counts']['taiga']} Taiga IDs** among {current_biome_example['sample_points']} sample points. The native capped Forest-3/Taiga-2 combination passed after {current_biome_example['native_points_queried']} queries. This checks one concrete example against the current policy; it is not a four-Y replay of every million-run candidate.

## Largest retained positive counts

These are observations in current-size crops, not absolute maxima or a promise that the entries coexist in one seed. Positive counts were recorded by the historical predictor; later skipped stages cannot lower the evidence but may hide larger counts elsewhere. The ten categories below are the useful historical inventories. Their individual maxima examples were independently replayed with the current full64 native predictor.

| Category | Largest retained count | OW placement slot ceiling | Example seed | Stronghold center |
| --- | ---: | --- | --- | --- |
{chr(10).join(maxima)}

Mineshaft's 9,216 ceiling counts possible starting-chunk slots and is not a realistic count target. Stronghold is excluded from this maximum table: each candidate explicitly stores its one chosen anchor, not a complete cropped Stronghold inventory.

The old run did not query Desert Pyramid, Jungle Temple, Swamp Hut, Igloo, Mansion, Ocean Ruin, Trail Ruins or Abandoned Camp. Buried Treasure and Monster Room were marked unsupported. It also did not inventory Nether portals or End Cities. Therefore the million run cannot replace the existing all-category pilot or settle maxima for those categories.

## Why maximum-everywhere is not a usable requirement

Independent maxima can conflict. Desert Pyramid, Jungle Temple, Swamp Hut and Igloo share placements and disjoint eligible biome sets in the pinned predictor. Their combined viable-start demand is at most **16** in this border. The earlier individually observed counts require **8 + 4 + 3 + 8 = 23** across those four types. Asking for all four observed maxima together is therefore impossible under these placement rules, even before adding other structures or terrain requirements.

Biome family maxima count distinct IDs, not repeated patches. The catalog ceiling is 56 active Overworld IDs across 19 families. A catalog lists possible IDs; it does not demonstrate all 56 occurring within one border. First-coordinate summaries cannot reconstruct every ID inside a smaller crop, and Y=63 records cannot inventory underground diversity across all requested Y levels. See [the placement and catalog ceilings](OVERWORLD_COUNT_LIMITS.md).

The interactive comparison uses the separate 896-layout structure / 48-layout biome pilot. Its preset match counts and observed maxima deliberately retain that sample's scope rather than mixing its arrays with the million-run replay.

## What the old run says about lower32 and lower48

The million inputs contain **{bits['distinct_lower32']:,} distinct lower32 values**, with only **{bits['repeated_lower32_input_occurrences']} repeated input occurrences**, and **{bits['distinct_lower48']:,} distinct lower48 values**, with **{bits['repeated_lower48_input_occurrences']} repeats**. Placement cache reuse additionally needs identical query bounds. This cohort offers almost no cross-seed lower-word reuse and does not represent deliberately repeated upper-bit siblings.

That does not rule out a useful uncached raw-count prefilter. Such a gate still needs an explicit matched benchmark using the final center and count requirements. Low full64 acceptance does not imply strong lower32 rejection: a raw placement may be common while its biome viability is rare. Historical full-inventory timings are not timings for today's capped native filters, and no new bit-strategy speed claims are inferred here.

## Verification and remaining work

- The complete scan checked every stored candidate's historical Overworld and exact fractional Nether geometry, reconciled all 2,629,026 rows and both original qualification totals, and verified crop histogram totals.
- {v['full64_structure_queries']} fresh full64 structure queries across {v['unique_example_borders']} extrema/profile example borders reproduced the recorded positive counts, with zero discrepancies.
- {v['biome_witness_queries']} fresh biome-ID queries at those examples' retained in-border witness points reproduced their IDs, with zero discrepancies. Earlier independent checks additionally matched 80 capped structure queries and 176 biome witness points.
- One concrete selective-combination example also passed the current four-Y world-aligned native biome diversity detector.
- The current and historical pinned vendor metadata identities match; this is still native prediction, not actual-game certification.

To complete the missing-category assessment, reuse these same saved full64 seeds and frozen centers, explicitly query every supported structure with counts capped at the proposed requirement, and run full64 biome diversity over the current four-Y lattice with retained witness refinement as needed. Compare direct full64, fused lower32 and fused lower48 on the same cases; deliberately grouped upper-bit siblings are needed to measure cache amortization. Terrain qualification and actual-game verification then determine whether a count-qualified candidate meets the Realm's full requirements.

Evidence: [million replay](runs/count-bits-2026-10-11/million-count-feasibility.json), [fresh example verification](runs/count-bits-2026-10-11/million-count-replay-verification.json), [current biome policy example](runs/count-bits-2026-10-11/million-example-current-biome-grid.json), [lower-word distribution](runs/count-bits-2026-10-11/million-bit-reuse-distribution.json), [original million benchmark](runs/master-implementation-2026-10-10/million/benchmark.json), [original million coverage audit](runs/master-implementation-2026-10-10/million-audit.json).
'''
    Path('COUNT_REQUIREMENT_FEASIBILITY.md').write_text(text)
    print('COUNT_REQUIREMENT_FEASIBILITY.md written')

if __name__=='__main__':main()
