"""Audit the completed pilots and publish readable tables without rerunning them."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from seed_search import _native

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/count-bits-2026-10-11"
ARMS = ("full64_direct", "fused_lower32", "fused_lower48", "cached_lower32", "cached_lower48")


def read(name):
    return json.loads((OUT / name).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(name, rows):
    rows = list(rows)
    with (OUT / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def table(headers, rows):
    return "\n".join([
        "| " + " | ".join(map(str, headers)) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(map(str, row)) + " |" for row in rows),
    ])


def main():
    structures = read("structures-report.json")
    variants = read("biome-variants-report.json")
    biomes = read("biomes-report.json")
    siblings = read("lower48-siblings-report.json")
    discovery = read("discovery-included-report.json")
    identity = read("structures-identity.json")
    catalog = read("biomes-identity.json")["catalog"]
    families = read("biome-variants-identity.json")["families"]
    variant_observations = read("biome-variant-observations.json")
    maximum_passes = {
        cohort: {name: sum(r["variant_counts"][name]["full64"] == info["capacity"]
                          for r in variant_observations if r["cohort"] == cohort)
                 for name, info in families.items()}
        for cohort in ("tuning", "holdout")
    }

    checks = []
    for filename in ("native/identity.json", "native-biomes/identity.json"):
        native = read(filename)
        assert sha(native["extension"]) == native["extension_sha256"], filename
        for path, digest in native["inputs"].items():
            assert sha(ROOT / path) == digest, path
        checks.append({"identity": filename, "binary_and_source_hashes_match": True})
    for filename, script in (
        ("structures-identity.json", "pilot_count_bits_structures.py"),
        ("biomes-identity.json", "pilot_count_bits_biomes.py"),
        ("biome-variants-identity.json", "pilot_biome_variant_counts.py"),
        ("discovery-included-report.json", "pilot_count_bits_discovery.py"),
    ):
        assert read(filename)["script_sha256"] == sha(ROOT / "scripts" / script), filename
    assert sha(_native.__file__) == identity["reference_native_sha256"]
    variant_identity = read("biome-variants-identity.json")
    assert variant_identity["input_sha256"] == sha(OUT / "biome-observations.json")
    for cohort, digest in identity["parent_sha256"].items():
        assert sha(ROOT / f"runs/locked-stronghold-2026-10-11/{cohort}/centers.json") == digest
    ids = [ident for family in families.values() for ident in family["ids"]]
    assert len(ids) == len(set(ids)) == len(catalog) == 66
    assert set(ids) == {r["id"] for r in catalog}
    assert len(families) == 29
    assert len(identity["structure_placement_bits"]) == 22
    assert structures["differences"] == variants["differences"] == siblings["differences"] == discovery["differences"] == 0
    assert biomes["full64_count_differences"] == 0

    rows = []
    for cohort, result in structures["cohorts"].items():
        for name, goals in result["individual_structures"].items():
            for n, r in goals.items():
                rows.append({
                    "cohort": cohort, "structure": name, "required_starts": n,
                    "placement_seed_bits": identity["structure_placement_bits"][name],
                    "inputs": result["all_21_ow_nether"][n]["inputs"],
                    "raw_positive": r["raw_positive"], "viable_positive": r["viable_positive"],
                    **{arm + "_mean_us_exploratory": value for arm, value in r["mean_microseconds"].items()},
                })
    write_csv("structure-counts.csv", rows)

    rows = []
    for cohort, result in structures["cohorts"].items():
        for profile in identity["profiles"]:
            for n, r in result[profile].items():
                for arm in ARMS:
                    bits = "48" if arm.endswith("48") else "32"
                    rows.append({
                        "cohort": cohort, "profile": profile, "required_starts_each": n, "arm": arm,
                        "layouts": r["inputs"], "viable_positive": r["viable_positive"],
                        "raw_rejection_percent": r["raw_rejection_percent"][bits] if arm != "full64_direct" else "",
                        "conditional_layouts_per_second": r["layouts_per_second"][arm],
                        "time_change_percent": r["time_change_percent"][arm],
                    })
    write_csv("structure-combinations.csv", rows)

    rows = []
    for cohort, result in variants["cohorts"].items():
        for family, info in result["families"].items():
            for n, r in info["counts"].items():
                rows.append({
                    "cohort": cohort, "family": family, "variants_required": n,
                    "catalog_capacity": info["capacity"], "catalog_impossible": r["catalog_impossible"],
                    "inputs": result["inputs"], "full64_positive": r["full64_positive"],
                    "all_active_variants_positive": maximum_passes[cohort][family],
                    "full64_rejection_percent": r["full64_rejection_percent"],
                    "native_full64_mean_us_exploratory": r["native_mean_microseconds"],
                    "mean_sample_points_queried": r["mean_queried_points"],
                    **{arm + "_" + key: value for arm, counts in r["unsafe_truncation"].items() for key, value in counts.items()},
                    "variant_names": ";".join(info["variants"]),
                })
    write_csv("biome-variant-counts.csv", rows)

    id_family = {ident: name for name, info in families.items() for ident in info["ids"]}
    rows = []
    for cohort, result in biomes["cohorts"].items():
        for biome in catalog:
            r = result["individual"]["biome:" + biome["name"]]["1"]
            rows.append({
                "cohort": cohort, "id": biome["id"], "biome": biome["name"],
                "dimension": biome["dimension"], "family": id_family[biome["id"]],
                "inputs": result["inputs"], "full64_sample_presence_positive": r["full64_support_positive"],
                "native_full64_mean_us_exploratory": r["count_query_microseconds"],
                "mean_sample_points_queried": r["mean_queried_points"],
                **{arm + "_" + key: value for arm, counts in r["unsafe_truncation"].items() for key, value in counts["support"].items()},
            })
    write_csv("biome-ids.csv", rows)

    rows = []
    for cohort, result in structures["cohorts"].items():
        for structure, groups in result["structure_family_counts"].items():
            for family, goals in groups.items():
                for n, positives in goals.items():
                    rows.append({"cohort": cohort, "structure": structure, "family_at_declared_y": family,
                                 "required_starts": n, "inputs": result["all_21_ow_nether"][n]["inputs"],
                                 "full64_positive": positives, "query_y": identity["structure_biome_y"][structure]})
    write_csv("structure-family-counts.csv", rows)
    timings = defaultdict(list)
    for row in read("structure-family-query-timings.json"):
        key = tuple(row[k] for k in ("cohort", "structure", "family", "count", "arm"))
        timings[key].append(row)
    write_csv("structure-family-query-times.csv", ({
        "cohort": key[0], "structure": key[1], "family": key[2], "required_starts": key[3], "arm": key[4],
        "tested_query_cases": len(values), "positive": sum(r["positive"] for r in values),
        "mean_us_exploratory": 1e6 * sum(r["seconds"] for r in values) / len(values),
    } for key, values in sorted(timings.items())))

    comparisons = {
        "structures_including_dependency_and_family_checks": structures["comparisons"],
        "sampled_biome_presence": biomes["full64_count_comparisons"],
        "distinct_biome_variant_checks": variants["full64_comparisons"],
        "lower48_sibling_raw_layouts": siblings["lower48_raw_layout_comparisons"],
        "discovery_included_decisions": discovery["comparisons"],
    }
    audit = {
        "checks": checks, "production_native_unchanged": True,
        "structures_covered": 22, "active_biome_ids_covered": 66, "biome_families_covered": 29,
        "passing_comparison_events": comparisons, "total_passing_comparison_events": sum(comparisons.values()),
        "differences_from_defined_full64_predictor_reference": 0,
        "actual_game_accuracy_certified": False,
        "masked_point_negative_control_comparisons": biomes["masked_point_comparisons"],
        "artifact_sha256": {name: sha(OUT / name) for name in (
            "structures-report.json", "biomes-report.json", "biome-variants-report.json",
            "lower48-siblings-report.json", "discovery-included-report.json",
        )},
    }
    (OUT / "completion-audit.json").write_text(json.dumps(audit, indent=2) + "\n")

    sh = structures["cohorts"]["holdout"]
    vh = variants["cohorts"]["holdout"]
    bh = biomes["cohorts"]["holdout"]
    dh = discovery["cohorts"]["holdout"]
    lines = [
        "# Structure multiplicity, biome diversity and seed-bit pilots",
        "",
        "Completed 11 October 2026. All measurements are serial on this host; they are pilot results, not a new massive production benchmark.",
        "",
        "## Decision",
        "",
        "Requiring **two or more distinct viable structure starts** makes a fused lower32 placement gate useful for the expanded combination's conditional count stage. At two of every Overworld/Nether structure, cached lower32 reduces count-stage time by 40.1%; lower48 gives practically the same result. Requiring only one of each makes both gates slower. Stronghold discovery and context preparation erase most of the count-stage gain, so there is no demonstrated large improvement in complete seed-search throughput.",
        "",
        "For biomes, the requested multiplicity is **different active biome IDs within a family**. A repeated patch of Forest counts once. Use the full64 seed for every biome query. Native early stopping can be much faster for readily satisfied diversity goals, but a broad rare-family conjunction can be slower than batched inventory because it must inspect essentially the whole grid.",
        "",
        "These pilots do not change production structure requirements, adopted borders, search policy or the production native extension. No combination requiring every structure produced a fully viable layout in this sample; this prevents a claim about time to a qualifying all-structure world.",
        "",
        "## Geometry, cohorts and comparison",
        "",
        "Discovery is 4000×4000. Each full64 seed chooses its first sorted discovered Stronghold before screening. Deployment is 1536×1536 Overworld at that anchor and 896×896 Nether at the exact fractional anchor/8. Coordinates use the existing half-open border contract converted to inclusive native bounds. The End-city control uses a diagnostic 1536-square window in its own dimension; no End border is adopted. Production's evaluation of all eligible anchors remains unchanged.",
        "",
        "Structure counts use 436 tuning and 460 held-out selected-center layouts: 896 full64 inputs in 256 disjoint lower32 groups. Another 128 of the original 1024 inputs had no discovered anchor and remain unresolved. A separate discovery-included replay uses the first 128 full64 inputs per cohort, including unresolved inputs. Biome tests use 24 layouts per cohort and are a small correlated-sibling pilot, not 48 independently drawn lower-bit groups.",
        "",
        "The five arms are: direct full64 viable-start counting; fused lower32 raw capacity plus fresh full64 viability; fused lower48; and those two fused arms with a bounded raw-prefix cache. Counts stop at the required number. A failed threshold need not return an exact partial inventory. Raw prefixes retain coordinates and the enumeration cursor, so viability continues without redoing placement. Cache reset, construction and misses are charged. Keys include the proved seed bits, structure, exact bounds and threshold; cached biome or viability answers are never shared between full64 seeds.",
        "",
        "The direct baseline already uses cheap placement internally. Merely masking a seed does not intrinsically make the RNG faster. Stronghold count queries are a special case: count two or more requires full64 bounded enumeration and deduplication; a one-Stronghold combination can reuse its already selected anchor. Mineshaft uses its specialized count-capped vector kernel. The four shared feature families require at least 4×N distinct raw slots, with separately checked disjoint viable-biome sets.",
        "",
        "Orders were learned on tuning and frozen for holdout. Structure combinations use five counterbalanced trials with four passes per trial, each with an empty paid cache. Biome combinations and discovery-included replay use three counterbalanced trials. Individual-family microsecond means are exploratory single passes; interpret them as cost indicators, not robust timing rankings.",
        "",
        "## All 21 supported Overworld/Nether structures together",
        "",
        "Conditional layouts/second excludes Stronghold discovery, native context creation, terrain and biome inventory. It includes raw gating and full64 viable-count checks reached after rejection. Both bit modes have identical raw rejection in these cohorts.",
        "",
        table(["N each", "Direct64", "Fused32", "Fused48", "Cached32", "Cached48", "Raw rejection", "Viable passes /460"], [
            [n, *(f"{sh['all_21_ow_nether'][str(n)]['layouts_per_second'][a]:,.0f}" for a in ARMS),
             f"{sh['all_21_ow_nether'][str(n)]['raw_rejection_percent']['32']:.2f}%", sh['all_21_ow_nether'][str(n)]['viable_positive']]
            for n in range(1, 5)]),
        "",
        "At N=1 the cached32 arm takes 35.5% more time; at N=2 it takes 40.1% less (1.67× throughput); at N=3 and N=4 it takes 50.8% and 51.8% less. Uncached fused32 at N=2 takes 21.7% less time. Tuning raw rejection at N=1/2/3/4 is 36.70%/96.79%/100%/100%, supporting the direction of the conditional-stage result. Observed 100% rejection is a finite-sample result, not proof of universal impossibility or a guaranteed 99.9% rejection rate.",
        "",
        "Lower48 does not add raw rejections because all layouts already have at least four raw Trial Chamber, Trail Ruin and Abandoned Camp placements. Those three LCG families require lower48 for correct placement, but their final biome eligibility still uses full64. In 64 dependency controls per LCG family, naively truncating to lower32 changed every raw layout; lower48 matched every one. The safe lower32 arm simply leaves those families on the full-seed path.",
        "",
        "The all-16-MT and all-22-with-End profiles are also in the detailed combination CSV. At N=2 cached32 count-stage time falls 37.5% for all-16-MT and about 38.9% for all-22. Neither profile yielded a qualifying held-out layout. Every all-structure profile also had zero fully viable tuning layouts.",
        "",
        "## Include discovery before interpreting throughput",
        "",
        table(["N each", "Direct64 input seeds/s", "Fused32", "Fused48", "Cached32", "Cached48"], [
            [n, *(f"{dh[str(n)]['seeds_per_second'][a]:,.0f}" for a in ARMS)] for n in range(1, 5)]),
        "",
        "These figures include full64 Stronghold discovery, both diagnostic contexts, bounds/FFI preparation and count filtering. They exclude terrain, biome inventory, persistence, IPC and actual game generation, and therefore are still not final pipeline throughput. Of 128 holdout inputs, 13 have no discovered center and remain unresolved; all discovered layouts fail the all-21 conjunction. The extra diagnostic context is common to every arm.",
        "",
        "Cached32 N=2 is 4.5% faster by elapsed time on this replay, but it is 4.2% slower on tuning. Changes at N=3/4 are roughly 0–2% and change sign across modes/cohorts. Consequently the small replay does not establish a robust overall speedup. In the held-out direct N=2 pass, median discovery is about 45.5ms and setup 15.2ms per 128 inputs, while count plus preparation is about 9.2ms. Optimizing just a few microseconds after selecting a full64 anchor cannot remove those preceding costs. Medians of components need not sum to the total median.",
        "",
        "## Current Village / Ancient City / Fortress / Bastion requirements",
        "",
        table(["N each", "Direct64 layouts/s", "Fused32", "Cached32", "Raw rejection", "Viable passes /460"], [
            [n, *(f"{sh['current_four'][str(n)]['layouts_per_second'][a]:,.0f}" for a in ('full64_direct','fused_lower32','cached_lower32')),
             f"{sh['current_four'][str(n)]['raw_rejection_percent']['32']:.2f}%", sh['current_four'][str(n)]['viable_positive']]
            for n in range(1, 5)]),
        "",
        "Two each still permits four held-out layouts, and cached32 reduces this conditional stage's time by about 7.0%. Uncached fusion at two each is about 3.5% slower. One each remains approximately neutral for fusion/cache. This is why the all-structure multiplicity finding does not justify inserting a universal lower32 gate into the current search.",
        "",
        "## Every exposed structure",
        "",
        "Each pass count below is out of 460 full64 holdout layouts. The costs are direct native count queries in microseconds, before selecting an order; Stronghold's individual count-one query includes enumeration rather than using the already known anchor. Raw placement count is necessary but often weak compared with biome viability. See the CSV for raw passes and both fused-arm times at all four thresholds.",
        "",
        table(["Structure", "Placement bits", "Viable N1", "N2", "N3", "N4", "Direct N1 µs", "Direct N4 µs"], [
            [name, identity['structure_placement_bits'][name], *(r[str(n)]['viable_positive'] for n in range(1,5)),
             f"{r['1']['mean_microseconds']['full64_direct']:.1f}", f"{r['4']['mean_microseconds']['full64_direct']:.1f}"]
            for name, r in sh['individual_structures'].items()]),
        "",
        "Mansion, Outpost and Fortress raw scarcity drives the count-two gate. Mansion raw passes fall from 451 at N1 to 197 at N2, 42 at N3 and zero at N4; Outpost from 449 to 184/40/7; Fortress from 368 to 140/26/2. In contrast, Ancient City has at least four raw positions in every layout, but only 14 have four viable starts. Its rarity is full64 biome viability, so lower32 cannot recognize that rarity.",
        "",
        "Buried Treasure (675µs at N1; 1324µs at N4), Shipwreck (307/742µs) and Monument (292/430µs) are the largest remaining regional count costs. Their raw capacity passes every layout through N4, so adding a raw gate does not remove their biome work. Count-capping avoids complete inventories on successful requirements, while negative cases still need all relevant candidates. Mineshaft scales from 104 to 383µs for N1→N4 and already uses its specialized lower32 kernel; adding another raw pass provides no selectivity. Defer expensive families behind cheap selective checks, retain cursors/prefixes and batch/reuse exact full64 biome samples where profiling shows overlap. These latter production improvements are proposed, not measured implementations in this pilot.",
        "",
        "## Different biome variants within each family",
        "",
        "All 66 active pinned-predictor biome IDs were observed somewhere across the 48 layouts. The existing canonical grouping partitions them into 29 families, including singleton cave, Nether and End groups. No sampled layout contains all 66 IDs or every family's maximum diversity. A Nether/End group with one active ID cannot have two distinct variants under this grouping; a broader user-defined grouping would be a separate requirement.",
        "",
        "The reference grid is world-aligned at 64-block spacing. Overworld samples Y=63,-48,0,160 (2304 points/layout), Nether Y=33 (196), and End Y=63 (576). Early stopping sees the identical point set in dispersed order. Unseen biomes outside this defined sampling lattice remain unknown; sample absence is not an exhaustive actual-world rejection.",
        "",
        table(["Family", "Active variants", "N1 /24", "N2 /24", "N3 /24", "N4 /24", "All variants /24"], [
            [name, info['capacity'], *("impossible" if info['counts'][str(n)]['catalog_impossible'] else info['counts'][str(n)]['full64_positive'] for n in range(1,5)), maximum_passes['holdout'][name]]
            for name, info in vh['families'].items()]),
        "",
        "Forest has six active variants: Forest, Birch Forest, Windswept Forest, Flower Forest, Old Growth Birch Forest and Dappled Forest. Taiga has four, Jungle three, Dark/Pale two and Cherry one. Requests above a family's active capacity fail before querying terrain. That is exact catalog impossibility, not a lower32/lower48 achievement. Counts should be configured independently per family, rather than requiring four everywhere.",
        "",
        table(["Full64 diversity goal", "Passes /24", "Full inventory layouts/s", "Native stop layouts/s", "Elapsed time change"], [
            [profile + ' N=' + n, r['positive'], f"{r['layouts_per_second']['full_inventory']:,.1f}",
             f"{r['layouts_per_second']['native_distinct_stop']:,.1f}", f"{r['time_change_percent']:+.1f}%"]
            for profile, goals in vh['combinations'].items() for n, r in goals.items() if not r['catalog_impossible']]),
        "",
        "Increasing diversity makes full64 queries more selective but typically requires more samples: the forest-only native means rise from 6.5 queried points at N1 to 315.9/470.9/1169.9 at N2/3/4. Two forest variants stop early and save 83.9% of inventory time; four save 41.2%. Four each of Forest+Taiga scans all 2304 points on every held-out layout and costs 17.7% more than inventory. Three-family N2 likewise scans the whole grid and costs 16.5% more. The current native combination loops over family masks per point, adding overhead when no early success occurs. A future disjoint-ID→family lookup with one shared seen-ID bitset and batched full64 sampling can reduce that overhead; it must be measured before adoption.",
        "",
        "## Accuracy: safe bits versus truncating biome seeds",
        "",
        "Safe lower32/lower48 modes never truncate biome generation, Stronghold selection or terrain seeds. All count predicates and tested raw layouts match the defined full64 reference. The intentionally unsafe truncation controls change biome IDs and eligibility:",
        "",
        table(["Dimension", "Lower32 point-ID disagreement", "Lower48 disagreement", "Full64 inventory points/s"], [
            [name, f"{bh['inventory'][str(dim)]['point_disagreement_percent']['unsafe32']:.2f}%",
             f"{bh['inventory'][str(dim)]['point_disagreement_percent']['unsafe48']:.2f}%",
             f"{bh['inventory'][str(dim)]['points_per_second']['full64']:,.0f}"]
            for dim, name in ((0,'Overworld'),(-1,'Nether'),(1,'End'))]),
        "",
        "For two forest variants, full64 accepts 21/24 layouts. Truncated lower32 wrongly rejects 9 of those and wrongly accepts 2 others; truncated lower48 wrongly rejects 2 and wrongly accepts 1. With four forest variants, full64 accepts 13/24, but lower32 wrongly rejects 10 and accepts 1 invalid layout, while lower48 wrongly rejects 4 and accepts 4 invalid layouts. More rarity does not make a wrong truncated biome generator safe.",
        "",
        "The high16-sibling control tested 32 lower48 groups and four high16 choices per group, discovering each full64 anchor independently. It obtained 114 centers (52 tuning/62 holdout), with 18/17 repeated exact-border queries. All 342 LCG raw-layout comparisons matched lower48. Even with that real reuse, lower48 cache time changes for the three-LCG combination on holdout were +0.06%/+0.11%/−0.16%/−0.33% at N1/2/3/4, with zero raw rejections through N4. Correct lower48 grouping exists, but it has no demonstrated useful acceleration here.",
        "",
        "Ancillary structure-in-biome-family counts also cover all structures and all canonical groups. Family-qualified native queries were audited at N=1,2,4 on 24 layouts/cohort, including observed families and an absent-family control. They use the biome at the logged start column and declared Y: generally OW63, City−48, Mineshaft/Trial Chamber0, Nether33, End63. They do not certify a structure's actual generated pieces or surface biome. Additional family-qualified rarity still needs full64 biome queries; it cannot be assumed to improve raw lower-bit rejection.",
        "",
        "## Verification and practical next changes",
        "",
        f"There are {sum(comparisons.values()):,} passing safe comparison events across the structure, biome, sibling and discovery replays, with zero differences from their full64 predictor references. These are repeated check events, not that many independent seeds. The separate unsafe controls contain {biomes['masked_point_comparisons']:,} point comparisons. Production native hashes, both private binaries, source inputs, frozen parent cohorts, script identities and the 66-ID partition passed the completion audit. Focused native/count/geometry tests passed: 34 tests.",
        "",
        "Predictor parity does not certify the actual game. Existing Stronghold recall and Ancient City/Bastion game-validation gaps remain, including the pinned MC_26_50 model versus the configured 26.52 target. The pilot never replaces unresolved discovery or unsampled biome evidence with a claimed actual-world absence.",
        "",
        "1. Add per-structure required counts and per-family required distinct biome IDs as separate configuration concepts. Validate requested diversity against each active catalog capacity and preserve evidence coordinates/IDs.",
        "2. Promote native count-capped detection with retained prefixes/cursors; enable a fused raw gate only for combinations/thresholds whose paid timing repays it. A raw pass remains necessary evidence, followed by full64 viability.",
        "3. Keep the raw cache bounded and keyed by version, proved bits, family, exact border and cap. Reuse only placement. Avoid exhaustive enumeration of upper32/high16 siblings without an equal-CPU useful-yield experiment.",
        "4. Use full64 distinct-ID early stopping for frequently satisfied diversity goals; keep shared batched inventory for broad rare goals until an optimized disjoint-family native path beats it on holdout. Retain unknown states outside sampled evidence.",
        "5. Profile and reduce paid full64 discovery/context/border-preparation costs before claiming a major complete-search gain. Re-run on more independent groups and actual positive worlds with the production all-anchor policy and terrain/verification stages included.",
        "",
        "## Detailed artifacts",
        "",
        "- [Every structure at every count and bit mode](runs/count-bits-2026-10-11/structure-counts.csv)",
        "- [All combination/cohort/mode timings](runs/count-bits-2026-10-11/structure-combinations.csv)",
        "- [All 29 families, capacities, N1–4 diversity, query costs and truncation errors](runs/count-bits-2026-10-11/biome-variant-counts.csv)",
        "- [All 66 individual biome IDs, presence and costs](runs/count-bits-2026-10-11/biome-ids.csv)",
        "- [Every structure × biome-family count](runs/count-bits-2026-10-11/structure-family-counts.csv)",
        "- [Family-qualified native query timings](runs/count-bits-2026-10-11/structure-family-query-times.csv)",
        "- [Discovery-included repeated trials](runs/count-bits-2026-10-11/discovery-included-report.json)",
        "- [Completion audit and frozen report hashes](runs/count-bits-2026-10-11/completion-audit.json)",
        "",
        "Reproduce native builds with `.venv/bin/python scripts/build_count_pilot.py` and `.venv/bin/python scripts/build_biome_diversity_pilot.py`; run the pilots with `.venv/bin/python -m scripts.pilot_count_bits_structures`, then `scripts.pilot_count_bits_biomes`, `scripts.pilot_biome_variant_counts`, `scripts.pilot_lower48_siblings` and `scripts.pilot_count_bits_discovery` using the same `-m` invocation. The frozen predecessor center files are required. Generate these tables with `.venv/bin/python -m scripts.report_count_bits`. Pilot modules intentionally depend on their private build identities.",
        "",
    ]
    (ROOT / "MULTIPLICITY_SEED_BIT_RESULTS.md").write_text("\n".join(lines))
    print(json.dumps({"report": "MULTIPLICITY_SEED_BIT_RESULTS.md", "passing_comparison_events": sum(comparisons.values()), "differences": 0}))


if __name__ == "__main__":
    main()
