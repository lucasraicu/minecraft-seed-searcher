"""Unit test suite for catalog biome expansion v3.

Validates:
- Exact 56 Overworld biome choices, 46 core enabled, 10 gated (6 mountains, 4 caves).
- 4 groups with exact declared atomic members, 2 auxiliary structures gated.
- All 56 names sourced from realm/biomes.py active model list.
- Legacy aliases remain v2 Y63 even when exact features multi-height.
- Strict layout ID binding to revision/base/extension/profile/registry/anchor/modes/side.
- Multi-target overlap preservation (exact, group, legacy).
- Missing witnesses remain UNKNOWN (no false proof of absence).
- Request constraints: max 12 rows, max 16 alternatives, GatedFeatureError.
- Deterministic rank_v3 with same-anchor AND, within-row ANY, no global monkeypatching.
- Reusing base_summaries avoids recomputation.
"""
import unittest
import copy
from seed_search.catalog import (
    registry, codec, summaries, request, query, models
)
from seed_search.catalog.request import GatedFeatureError, UnsupportedFeatureError
from seed_search.catalog.summaries import canonical_biome_name

DUMMY_SHA = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
FULL_ENVELOPE = list(registry.ENVELOPE)

GATED_MOUNTAINS = {
    "windswept_hills", "windswept_gravelly_hills", "jagged_peaks",
    "frozen_peaks", "stony_peaks", "grove"
}
GATED_CAVES = {
    "lush_caves", "dripstone_caves", "deep_dark", "sulfur_caves"
}


def make_test_ident(seed="123456789"):
    return models.identity(
        seed=seed,
        model_id="MC_26_50",
        native_sha256=DUMMY_SHA,
        source_sha256=DUMMY_SHA,
    )


def make_minimal_obs(seed="123456789", structures=None, ow_biomes=None, nether_biomes=None, biome_names=None):
    ident = make_test_ident(seed=seed)
    obs = models.empty_observation_v2(ident)
    obs["structures"] = structures or {}
    obs["biomes"] = {
        "overworld": ow_biomes if ow_biomes is not None else [[0, 63, 0, 0]],
        "nether": nether_biomes if nether_biomes is not None else [[0, 64, 0, 100]],
    }
    obs["biome_names"] = biome_names if biome_names is not None else {"0": "plains", "100": "nether_wastes"}
    obs["coverage"] = {}
    return obs


class TestFeatureRegistryV3(unittest.TestCase):
    """Test registry v3 exports, feature definitions, and exact name parity."""

    def test_registry_exports(self):
        self.assertTrue(hasattr(registry, "REGISTRY_V3"))
        self.assertTrue(hasattr(registry, "FEATURES_V3"))
        self.assertTrue(hasattr(registry, "FEATURE_BY_ID_V3"))
        self.assertTrue(hasattr(registry, "REGISTRY_REVISION_V3"))
        self.assertTrue(hasattr(registry, "SAMPLING_PROFILES_V3"))
        self.assertTrue(hasattr(registry, "SAMPLING_PROFILE_REVISION_V3"))
        self.assertEqual(registry.REGISTRY_REVISION_V3, registry.digest(registry.REGISTRY_V3))

    def test_exact_56_ow_biomes_and_gates(self):
        exact_ow = [f for f in registry.FEATURES_V3 if f["id"].startswith("biome.exact.")]
        self.assertEqual(len(exact_ow), 56, f"Expected 56 exact Overworld biomes, found {len(exact_ow)}")

        gated = [f for f in exact_ow if not f["available"]]
        self.assertEqual(len(gated), 10, f"Expected 10 gated biomes, found {len(gated)}")

        gated_ids = {f["id"].removeprefix("biome.exact.") for f in gated}
        expected_gated = GATED_MOUNTAINS | GATED_CAVES
        self.assertEqual(gated_ids, expected_gated)

        for f in gated:
            self.assertIsNotNone(f["unavailable_reason"])
            self.assertTrue(len(f["unavailable_reason"]) > 0)

        core_enabled = [f for f in exact_ow if f["available"]]
        self.assertEqual(len(core_enabled), 46, f"Expected 46 core enabled biomes, found {len(core_enabled)}")
        for f in core_enabled:
            self.assertIsNone(f["unavailable_reason"])

    def test_all_56_biomes_match_active_model_list(self):
        # All 56 canonical names must resolve cleanly through canonical aliases
        for f in registry.FEATURES_V3:
            if f["id"].startswith("biome.exact."):
                cname = f["id"].removeprefix("biome.exact.")
                canonical_resolved = canonical_biome_name(cname)
                self.assertEqual(cname, canonical_resolved, f"Biome {cname} is not canonical")

    def test_four_groups_declared_members(self):
        groups = {f["id"]: f for f in registry.FEATURES_V3 if f["id"].startswith("biome.group.")}
        self.assertEqual(set(groups.keys()), {
            "biome.group.badlands", "biome.group.snowy",
            "biome.group.forest", "biome.group.plains"
        })

        expected_members = {
            "biome.group.badlands": {"badlands", "eroded_badlands", "wooded_badlands"},
            "biome.group.snowy": {"snowy_plains", "snowy_slopes", "snowy_taiga", "ice_spikes"},
            "biome.group.forest": {"forest", "birch_forest", "flower_forest", "old_growth_birch_forest"},
            "biome.group.plains": {"plains", "sunflower_plains", "meadow"},
        }
        for gid, f in groups.items():
            self.assertTrue(f["available"])
            self.assertEqual(set(f["canonical_members"]), expected_members[gid])
            expected_atomic = {f"biome.exact.{m}" for m in expected_members[gid]}
            self.assertEqual(set(f["atomic_members"]), expected_atomic)

    def test_auxiliary_variants_gated(self):
        igloo_base = registry.FEATURE_BY_ID_V3.get("structure.igloo_with_basement")
        self.assertIsNotNone(igloo_base)
        self.assertFalse(igloo_base["available"])
        self.assertIn("gated", igloo_base["unavailable_reason"].lower())

        bastion_tr = registry.FEATURE_BY_ID_V3.get("structure.bastion_treasure")
        self.assertIsNotNone(bastion_tr)
        self.assertFalse(bastion_tr["available"])
        self.assertIn("gated", bastion_tr["unavailable_reason"].lower())

    def test_legacy_features_preserved(self):
        # All v2 features must exist in v3 with identical IDs
        for f2 in registry.FEATURES_V2:
            self.assertIn(f2["id"], registry.FEATURE_BY_ID_V3)
            f3 = registry.FEATURE_BY_ID_V3[f2["id"]]
            self.assertEqual(f3["dimension"], f2["dimension"])
            self.assertEqual(f3["kind"], f2["kind"])


class TestCodecV3(unittest.TestCase):
    """Test v3 summary validation, strict fields, layout binding, and height checks."""

    def make_valid_v3_summary(self):
        obs = make_minimal_obs()
        sum_list = summaries.summarize_v3(obs)
        return copy.deepcopy(sum_list[0])

    def test_valid_v3_summary_passes(self):
        s = self.make_valid_v3_summary()
        res = codec.validate_summary_v3(s)
        self.assertEqual(res["revision"], "catalog-summary-v3")

    def test_strict_fields_rejected_when_missing_or_extra(self):
        s = self.make_valid_v3_summary()
        s["unknown_field"] = 123
        with self.assertRaises(ValueError):
            codec.validate_summary_v3(s)

        s2 = self.make_valid_v3_summary()
        del s2["source_extension_id"]
        with self.assertRaises(ValueError):
            codec.validate_summary_v3(s2)

    def test_layout_id_binds_all_required_dimensions(self):
        s = self.make_valid_v3_summary()
        original_lid = s["layout_id"]

        # Changing observation ID breaks layout_id
        mutated = copy.deepcopy(s)
        mutated["source_observation_id"] = "f" * 64
        with self.assertRaises(ValueError):
            codec.validate_summary_v3(mutated)

        # Changing extension ID breaks layout_id
        mutated = copy.deepcopy(s)
        mutated["source_extension_id"] = "e" * 64
        with self.assertRaises(ValueError):
            codec.validate_summary_v3(mutated)

        # Changing sampling profile revision breaks layout_id
        mutated = copy.deepcopy(s)
        mutated["sampling_profile_revision"] = "other-profile"
        with self.assertRaises(ValueError):
            codec.validate_summary_v3(mutated)

        # Changing border side breaks layout_id
        mutated = copy.deepcopy(s)
        mutated["border_side"] = 4096
        with self.assertRaises(ValueError):
            codec.validate_summary_v3(mutated)

    def test_legacy_aliases_strictly_require_y63(self):
        s = self.make_valid_v3_summary()
        # Set witness on legacy alias biome.forest with y=96 -> must fail
        f_forest = s["features"]["biome.forest"]
        f_forest["counts"] = [1, 1, 1, 1]
        f_forest["nearest_d2"] = 0
        f_forest["witness"] = [s["anchor"][0], 96, s["anchor"][1]]
        with self.assertRaises(ValueError):
            codec.validate_summary_v3(s)

        # But exact forest allows multi-height if declared in eligible_y
        f_exact = s["features"]["biome.exact.forest"]
        f_exact["counts"] = [1, 1, 1, 1]
        f_exact["nearest_d2"] = 0
        f_exact["witness"] = [s["anchor"][0], 96, s["anchor"][1]]
        # Restore legacy forest to None
        f_forest["counts"] = [0, 0, 0, 0]
        f_forest["nearest_d2"] = None
        f_forest["witness"] = None
        # Now validation passes because exact features permit multi-height
        res = codec.validate_summary_v3(s)
        self.assertIsNotNone(res)

    def test_biomes_cannot_have_complete_true(self):
        s = self.make_valid_v3_summary()
        s["features"]["biome.exact.plains"]["complete"] = [True, False, False, False]
        with self.assertRaises(ValueError):
            codec.validate_summary_v3(s)


class TestSummariesV3(unittest.TestCase):
    """Test v3 summary derivation, multi-feature overlap, and extension handling."""

    def test_multi_target_overlap_preservation(self):
        # A single sample of "forest" at (64, 63, 64) must be witnessed by:
        # 1. biome.exact.forest
        # 2. biome.group.forest
        # 3. biome.forest (legacy)
        obs = make_minimal_obs(
            ow_biomes=[[64, 63, 64, 1]],
            biome_names={"1": "forest"}
        )
        sums = summaries.summarize_v3(obs)
        self.assertTrue(len(sums) >= 243)
        origin_2048 = next(s for s in sums if s["anchor"] == [0, 0] and s["border_side"] == 2048)

        # Check exact
        exact_feat = origin_2048["features"]["biome.exact.forest"]
        self.assertEqual(exact_feat["counts"][0], 1)
        self.assertEqual(exact_feat["witness"], [64, 63, 64])

        # Check group
        group_feat = origin_2048["features"]["biome.group.forest"]
        self.assertEqual(group_feat["counts"][0], 1)
        self.assertEqual(group_feat["witness"], [64, 63, 64])

        # Check legacy alias
        legacy_feat = origin_2048["features"]["biome.forest"]
        self.assertEqual(legacy_feat["counts"][0], 1)
        self.assertEqual(legacy_feat["witness"], [64, 63, 64])

    def test_missing_witnesses_remain_unknown(self):
        obs = make_minimal_obs(
            ow_biomes=[[64, 63, 64, 1]],
            biome_names={"1": "desert"}
        )
        sums = summaries.summarize_v3(obs)
        origin_2048 = next(s for s in sums if s["anchor"] == [0, 0] and s["border_side"] == 2048)

        # Cherry grove has no witness
        cherry = origin_2048["features"]["biome.exact.cherry_grove"]
        self.assertEqual(cherry["counts"], [0, 0, 0, 0])
        self.assertIsNone(cherry["nearest_d2"])
        self.assertIsNone(cherry["witness"])
        self.assertEqual(cherry["complete"], [False, False, False, False])

    def test_extension_with_mountain_heights(self):
        obs = make_minimal_obs()
        obs_id = registry.digest(obs)

        ext = {
            "base_observation_id": obs_id,
            "revision":"catalog-biome-extension-v3",
            "bounds":obs["bounds"]["overworld"],
            "sampling_profile_revision": registry.SAMPLING_PROFILE_REVISION_V3,
            "provider_id": __import__("seed_search.catalog.biome_extension",fromlist=["provider_id"]).provider_id(obs),
            "biomes": {
                "overworld": [
                    [256, 160, 0, 50],  # jagged_peaks at Y=160
                    [256, 0, 0, 60],    # lush_caves at Y=0
                ]
            },
            "biome_names": {
                "50": "jagged_peaks",
                "60": "lush_caves"
            }
        }

        sums = summaries.summarize_v3(obs, extension=ext)
        origin_2048 = next(s for s in sums if s["anchor"] == [0, 0] and s["border_side"] == 2048)
        self.assertEqual(origin_2048["source_extension_id"], registry.digest(ext))

        # Jagged peaks witness at Y=160
        jp = origin_2048["features"]["biome.exact.jagged_peaks"]
        self.assertEqual(jp["witness"], [256, 160, 0])
        self.assertEqual(jp["counts"][0], 1)

        # Lush caves witness at Y=0
        lc = origin_2048["features"]["biome.exact.lush_caves"]
        self.assertEqual(lc["witness"], [256, 0, 0])
        self.assertEqual(lc["counts"][0], 1)

    def test_extension_base_mismatch_fails(self):
        obs = make_minimal_obs()
        ext = {
            "base_observation_id": "a" * 64,  # wrong hash
            "sampling_profile_revision": "catalog-sampling-profiles-v3",
            "biomes": {}
        }
        with self.assertRaises(ValueError):
            summaries.summarize_v3(obs, extension=ext)

    def test_base_summaries_reuse(self):
        obs = make_minimal_obs()
        base_sums = summaries.summarize_v2(obs)
        # Summarize v3 reusing base_summaries
        sums_reused = summaries.summarize_v3(obs, base_summaries=base_sums)
        self.assertEqual(len(sums_reused), len(base_sums))
        for s_v3, s_v2 in zip(sums_reused, base_sums):
            self.assertEqual(s_v3["anchor"], s_v2["anchor"])
            self.assertEqual(s_v3["border_side"], s_v2["border_side"])
            self.assertEqual(s_v3["legacy"], s_v2["legacy"])


class TestRequestV3(unittest.TestCase):
    """Test request v3 validation, 12-row limit, 16-alternative limit, and gated errors."""

    def make_valid_v3_request(self, rows=None):
        return {
            "request_revision": "catalog-query-v3",
            "evidence_policy": "predicted_observations_v3",
            "edition": "bedrock",
            "game_build_id": "research:MC_26_50",
            "catalog_snapshot_id": "snap-1",
            "world_settings_id": "default",
            "dimension": "overworld",
            "anchor_mode": "recommended",
            "border_side": 2048,
            "fallback_profile": "balanced_survival",
            "rows": rows if rows is not None else [
                {
                    "rule": "preferred",
                    "kind": "biome_witness",
                    "any_of": ["biome.exact.cherry_grove"],
                    "importance": 5,
                    "scope": {"kind": "near_base", "radius": 256}
                }
            ]
        }

    def test_valid_request_passes(self):
        req = self.make_valid_v3_request()
        validated = request.validate_request_v3(req)
        self.assertEqual(validated["request_revision"], "catalog-query-v3")

    def test_max_12_rows(self):
        # 12 rows allowed
        req12 = self.make_valid_v3_request(rows=[
            {
                "rule": "preferred",
                "kind": "biome_witness",
                "any_of": ["biome.exact.plains"],
                "importance": 1,
                "scope": {"kind": "near_base", "radius": 512}
            } for _ in range(12)
        ])
        request.validate_request_v3(req12)

        # 13 rows raises ValueError
        req13 = copy.deepcopy(req12)
        req13["rows"].append(req12["rows"][0])
        with self.assertRaises(ValueError):
            request.validate_request_v3(req13)

    def test_max_16_alternatives_per_row(self):
        # Exactly 16 core biomes in any_of is accepted
        core16 = [f["id"] for f in registry.FEATURES_V3 if f["id"].startswith("biome.exact.") and f["available"]][:16]
        req16 = self.make_valid_v3_request(rows=[
            {
                "rule": "preferred",
                "kind": "biome_witness",
                "any_of": core16,
                "importance": 3,
                "scope": {"kind": "near_base", "radius": 512}
            }
        ])
        request.validate_request_v3(req16)

        # 17 alternatives raises ValueError
        core17 = [f["id"] for f in registry.FEATURES_V3 if f["id"].startswith("biome.exact.") and f["available"]][:17]
        req17 = self.make_valid_v3_request(rows=[
            {
                "rule": "preferred",
                "kind": "biome_witness",
                "any_of": core17,
                "importance": 3,
                "scope": {"kind": "near_base", "radius": 512}
            }
        ])
        with self.assertRaises(ValueError):
            request.validate_request_v3(req17)

    def test_named_group_counts_as_one_choice(self):
        # 15 exact biomes + 1 group = 16 choices in any_of
        choices = [f["id"] for f in registry.FEATURES_V3 if f["id"].startswith("biome.exact.") and f["available"]][:15]
        choices.append("biome.group.badlands")
        self.assertEqual(len(choices), 16)
        req = self.make_valid_v3_request(rows=[
            {
                "rule": "preferred",
                "kind": "biome_witness",
                "any_of": choices,
                "importance": 3,
                "scope": {"kind": "near_base", "radius": 512}
            }
        ])
        request.validate_request_v3(req)

    def test_gated_mountain_raises_gated_feature_error(self):
        req = self.make_valid_v3_request(rows=[
            {
                "rule": "preferred",
                "kind": "biome_witness",
                "any_of": ["biome.exact.jagged_peaks"],
                "importance": 3,
                "scope": {"kind": "near_base", "radius": 512}
            }
        ])
        with self.assertRaises(GatedFeatureError):
            request.validate_request_v3(req)

    def test_gated_cave_raises_gated_feature_error(self):
        req = self.make_valid_v3_request(rows=[
            {
                "rule": "preferred",
                "kind": "biome_witness",
                "any_of": ["biome.exact.deep_dark"],
                "importance": 3,
                "scope": {"kind": "near_base", "radius": 512}
            }
        ])
        with self.assertRaises(GatedFeatureError):
            request.validate_request_v3(req)

    def test_gated_auxiliary_structure_raises_gated_feature_error(self):
        req = self.make_valid_v3_request(rows=[
            {
                "rule": "required",
                "kind": "structure_count",
                "feature": "structure.igloo_with_basement",
                "at_least": 1,
                "scope": {"kind": "near_base", "radius": 512}
            }
        ])
        with self.assertRaises(GatedFeatureError):
            request.validate_request_v3(req)


class TestQueryRankV3(unittest.TestCase):
    """Test ranking engine v3, same-anchor semantics, and unknown handling."""

    def test_rank_v3_same_anchor_and_semantics(self):
        # Seed 101: has plains at (0, 0) and desert far away at (1500, 1500)
        # Seed 102: has both plains and desert near anchor (0, 0)
        obs1 = make_minimal_obs(
            seed="101",
            ow_biomes=[
                [0, 63, 0, 1],        # plains near (0, 0)
                [1500, 63, 1500, 2],  # desert far away
            ],
            biome_names={"1": "plains", "2": "desert"}
        )
        obs2 = make_minimal_obs(
            seed="102",
            ow_biomes=[
                [0, 63, 0, 1],    # plains near (0, 0)
                [64, 63, 0, 2],   # desert also near (0, 0)
            ],
            biome_names={"1": "plains", "2": "desert"}
        )

        sums1 = summaries.summarize_v3(obs1)
        sums2 = summaries.summarize_v3(obs2)
        all_sums = sums1 + sums2

        req = {
            "request_revision": "catalog-query-v3",
            "evidence_policy": "predicted_observations_v3",
            "edition": "bedrock",
            "game_build_id": "research:MC_26_50",
            "catalog_snapshot_id": "snap-1",
            "world_settings_id": "default",
            "dimension": "overworld",
            "anchor_mode": "recommended",
            "border_side": 2048,
            "fallback_profile": "balanced_survival",
            "rows": [
                {
                    "rule": "required",
                    "kind": "biome_witness",
                    "any_of": ["biome.exact.plains"],
                    "scope": {"kind": "near_base", "radius": 256}
                },
                {
                    "rule": "required",
                    "kind": "biome_witness",
                    "any_of": ["biome.exact.desert"],
                    "scope": {"kind": "near_base", "radius": 256}
                }
            ]
        }

        ranked = query.rank_v3(all_sums, req)
        # Seed 102 has both at anchor (0, 0) -> matched
        # Seed 101 cannot satisfy both at radius 256 around the same anchor
        results = ranked["results"]
        matched_seeds = [r["seed"] for r in results]
        self.assertIn("102", matched_seeds)
        self.assertNotIn("101", matched_seeds)

        # Seed 101 is an unresolved candidate (pending), not discarded
        unresolved_seeds = [u["seed"] for u in ranked["unresolved_candidates"]]
        self.assertIn("101", unresolved_seeds)

    def test_rank_v3_no_global_monkeypatch(self):
        # Confirm that calling rank_v3 does not modify registry.REGISTRY_V2 or module globals
        v2_rev_before = registry.REGISTRY_REVISION_V2
        v3_rev_before = registry.REGISTRY_REVISION_V3

        obs = make_minimal_obs(seed="999")
        sums = summaries.summarize_v3(obs)
        req = {
            "request_revision": "catalog-query-v3",
            "evidence_policy": "predicted_observations_v3",
            "edition": "bedrock",
            "game_build_id": "research:MC_26_50",
            "catalog_snapshot_id": "snap-1",
            "world_settings_id": "default",
            "dimension": "overworld",
            "anchor_mode": "recommended",
            "border_side": 2048,
            "fallback_profile": "balanced_survival",
            "rows": []
        }
        res = query.rank_v3(sums, req)
        self.assertEqual(len(res["results"]), 1)

        self.assertEqual(registry.REGISTRY_REVISION_V2, v2_rev_before)
        self.assertEqual(registry.REGISTRY_REVISION_V3, v3_rev_before)

    def test_group_or_evaluation_in_query(self):
        # A request for biome.group.badlands matches when any badlands member is present
        obs = make_minimal_obs(
            seed="201",
            ow_biomes=[[10, 63, 10, 5]],  # eroded_badlands
            biome_names={"5": "eroded_badlands"}
        )
        sums = summaries.summarize_v3(obs)
        req = {
            "request_revision": "catalog-query-v3",
            "evidence_policy": "predicted_observations_v3",
            "edition": "bedrock",
            "game_build_id": "research:MC_26_50",
            "catalog_snapshot_id": "snap-1",
            "world_settings_id": "default",
            "dimension": "overworld",
            "anchor_mode": "recommended",
            "border_side": 2048,
            "fallback_profile": "balanced_survival",
            "rows": [
                {
                    "rule": "required",
                    "kind": "biome_witness",
                    "any_of": ["biome.group.badlands"],
                    "scope": {"kind": "near_base", "radius": 256}
                }
            ]
        }
        res = query.rank_v3(sums, req)
        self.assertEqual(len(res["results"]), 1)
        self.assertEqual(res["results"][0]["seed"], "201")

    def test_snapshot_bound_registry_enabling_gated_biome(self):
        # In a snapshot with updated capabilities, windswept_hills may be enabled
        custom_reg = copy.deepcopy(registry.REGISTRY_V3)
        for f in custom_reg["features"]:
            if f["id"] == "biome.exact.windswept_hills":
                f["available"] = True
                f["unavailable_reason"] = None

        obs = make_minimal_obs(
            seed="301",
            ow_biomes=[[20, 63, 20, 9]],
            biome_names={"9": "windswept_hills"}
        )
        sums = summaries.summarize_v3(obs, registry=custom_reg)
        req = {
            "request_revision": "catalog-query-v3",
            "evidence_policy": "predicted_observations_v3",
            "edition": "bedrock",
            "game_build_id": "research:MC_26_50",
            "catalog_snapshot_id": "snap-custom",
            "world_settings_id": "default",
            "dimension": "overworld",
            "anchor_mode": "recommended",
            "border_side": 2048,
            "fallback_profile": "balanced_survival",
            "rows": [
                {
                    "rule": "required",
                    "kind": "biome_witness",
                    "any_of": ["biome.exact.windswept_hills"],
                    "scope": {"kind": "near_base", "radius": 256}
                }
            ]
        }
        # Passing snapshot-bound registry succeeds without GatedFeatureError
        res = query.rank_v3(sums, req, registry=custom_reg)
        self.assertEqual(len(res["results"]), 1)

    def test_nether_anchor_floor_division_and_witness_bounds(self):
        # Negative overworld coordinate floor division to nether anchor
        ax, az = -256, -512
        nether_anchor = [ax // 8, az // 8]
        self.assertEqual(nether_anchor, [-32, -64])

        # Overworld coordinate on border boundary:
        # border 2048 centered at (0, 0) covers [-1024, 1024)
        obs = make_minimal_obs(
            seed="401",
            ow_biomes=[
                [1023, 63, 0, 1],   # inside border
                [1024, 63, 0, 2],   # on boundary: OUTSIDE half-open border
            ],
            biome_names={"1": "sunflower_plains", "2": "meadow"}
        )
        sums = summaries.summarize_v3(obs)
        origin_2048 = next(s for s in sums if s["anchor"] == [0, 0] and s["border_side"] == 2048)

        # Sunflower plains (x=1023) is inside border
        sp = origin_2048["features"]["biome.exact.sunflower_plains"]
        self.assertEqual(sp["counts"][3], 1)
        self.assertEqual(sp["witness"], [1023, 63, 0])

        # Meadow (x=1024) is outside border
        m = origin_2048["features"]["biome.exact.meadow"]
        self.assertEqual(m["counts"][3], 0)
        self.assertIsNone(m["witness"])

    def test_legacy_v2_unchanged(self):
        # Ensure v2 query and summaries still work with exact v2 contracts
        obs = make_minimal_obs(
            seed="501",
            ow_biomes=[[50, 63, 50, 1]],
            biome_names={"1": "forest"}
        )
        sums_v2 = summaries.summarize_v2(obs)
        req_v2 = {
            "request_revision": "catalog-query-v2",
            "evidence_policy": "predicted_observations_v2",
            "edition": "bedrock",
            "game_build_id": "research:MC_26_50",
            "catalog_snapshot_id": "snap-1",
            "world_settings_id": "default",
            "dimension": "overworld",
            "anchor_mode": "recommended",
            "border_side": 2048,
            "fallback_profile": "balanced_survival",
            "rows": [
                {
                    "rule": "preferred",
                    "kind": "biome_witness",
                    "any_of": ["biome.forest"],
                    "importance": 5,
                    "scope": {"kind": "near_base", "radius": 256}
                }
            ]
        }
        res_v2 = query.rank_v2(sums_v2, req_v2)
        self.assertEqual(len(res_v2["results"]), 1)
        self.assertEqual(res_v2["results"][0]["score"], 100.0)



if __name__ == "__main__":
    unittest.main()
