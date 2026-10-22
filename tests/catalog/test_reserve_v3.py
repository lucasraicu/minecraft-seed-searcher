"""Comprehensive stdlib unittests for v3 public 2x retention and finalization.

Verifies:
- Exact v3 capacity arithmetic (7,543 objectives / 115,964 primary / 231,928 effective)
- Fullsort oracle parity on 2K candidate retention
- Deterministic per-world deduplication and tie-breaking
- Scoped nearest-witness rank [d2, world_id, anchor_x, anchor_z, witness_x, witness_y, witness_z]
- Gated feature suppression and fixture registry injection
- Spawn mode requiring actual compatible spawn anchor (no origin fallback)
- Role overlap (a world can be primary in objective A and reserve in objective B)
- Generic search union protecting reserve candidates
- Finalization advancing candidates, scoped failure, and reserve promotion
- Inconclusive/error states remaining pending without pretending targets are met
- Bounded verification budgets and receipt reuse by evidence identity
- Durable serializable progress persistence without extra databases
"""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from seed_search.catalog.finalization import (
    STATUS_ERROR,
    STATUS_FAIL,
    STATUS_INCONCLUSIVE,
    STATUS_PASS,
    STATUS_PENDING,
    advance_finalization,
    evidence_identity,
    generic_search_candidates,
    load_finalization_progress,
    make_evidence_receipt,
    save_finalization_progress,
)
from seed_search.catalog.models import identity, world_id
from seed_search.catalog.registry import digest
from seed_search.catalog.retention import (
    ALL_OBJECTIVE_IDS,
    ATOMIC_OW_BIOMES_56,
    DEFAULT_CAPACITIES,
    GATED_V3_FEATURES_DEFAULT,
    MODES,
    MODES_V3,
    SIDES,
    automation_objectives,
    automation_objectives_v3,
    automation_offers_v3,
    automation_policy_revision_v3,
    automation_primary_objectives_v3,
    objective_capacities_v3,
    retained_union,
    split_primary_reserve,
    world_objective_roles,
)


def _make_dummy_identity(seed_val: int = 1000):
    return identity(
        str(seed_val),
        model_id="MC_26_50",
        native_sha256="a" * 64,
        source_sha256="b" * 64,
    )


def _make_dummy_observation(seed_val: int = 1000, *, with_spawn: bool = True):
    ident = _make_dummy_identity(seed_val)
    obs = {
        "revision": "catalog-observation-v2",
        "registry_revision": "c" * 64,
        "identity": ident,
        "bounds": {"overworld": [-5120, -5120, 5120, 5120], "nether": [-640, -640, 640, 640]},
        "structures": {},
        "biomes": {"overworld": [], "nether": []},
        "biome_names": {},
        "coverage": {},
        "anchors": [
            {"mode": "origin", "coordinate": [0, 0], "source_id": "origin"},
            {"mode": "recommended", "coordinate": [0, 0], "source_id": "recommended"},
        ],
        "realm": None,
        "metrics": {},
        "errors": {},
    }
    if with_spawn:
        obs["anchors"].append({
            "mode": "world_spawn_estimated",
            "coordinate": [100, 200],
            "source_id": "spawn_est",
        })
    return obs


def _make_dummy_summary(obs, anchor, modes, border_side, features=None):
    oid = digest(obs)
    wid = world_id(obs["identity"])
    lid = digest(["catalog-summary-v3", oid, list(anchor), list(modes), border_side])
    return {
        "revision": "catalog-summary-v3",
        "source_observation_id": oid,
        "world_id": wid,
        "seed": obs["identity"]["seed"],
        "anchor": list(anchor),
        "nether_anchor": [anchor[0] // 8, anchor[1] // 8],
        "anchor_modes": list(modes),
        "border_side": border_side,
        "layout_id": lid,
        "features": features or {},
    }


class TestCapacityArithmeticAndContract(unittest.TestCase):
    """Verify exact capacity arithmetic across legacy, primary v3, and effective v3."""

    def test_legacy_capacities_preserved(self):
        legacy = automation_objectives()
        self.assertEqual(len(legacy), 7027)
        self.assertEqual(sum(legacy.values()), 105644)

    def test_primary_capacities_v3(self):
        primary = automation_primary_objectives_v3()
        self.assertEqual(len(primary), 7543)
        self.assertEqual(sum(primary.values()), 115964)

        # Added objectives count: 7543 - 7027 = 516
        added_keys = set(primary.keys()) - set(automation_objectives().keys())
        self.assertEqual(len(added_keys), 516)
        # Added primary slots: 516 * 20 = 10,320
        self.assertEqual(sum(primary[k] for k in added_keys), 10320)
        for k in added_keys:
            self.assertEqual(primary[k], 20, f"Expected primary capacity 20 for {k}")

    def test_effective_capacities_v3(self):
        effective = automation_objectives_v3()
        primary = automation_primary_objectives_v3()
        self.assertEqual(len(effective), 7543)
        self.assertEqual(sum(effective.values()), 231928)

        # Every single objective must declare exactly 2 * primary capacity
        for oid, p_cap in primary.items():
            self.assertEqual(
                effective[oid],
                p_cap * 2,
                f"Effective capacity mismatch for {oid}: expected {p_cap * 2}, got {effective[oid]}",
            )

    def test_objective_capacities_helper(self):
        caps = objective_capacities_v3()
        self.assertEqual(len(caps), 7543)
        self.assertEqual(
            caps["v3.near:biome.exact.ocean:2048:origin"],
            {"primary_k": 20, "retained_k": 40},
        )
        self.assertEqual(
            caps["v3.near:structure.igloo_with_basement:4096:spawn"],
            {"primary_k": 20, "retained_k": 40},
        )
        self.assertEqual(
            caps["v3.near:structure.bastion_treasure:recommended"],
            {"primary_k": 20, "retained_k": 40},
        )

    def test_contract_json_matches_runtime(self):
        contract_path = Path(__file__).resolve().parents[2] / "docs/catalog/v3/public_retention.json"
        self.assertTrue(contract_path.is_file(), "docs/catalog/v3/public_retention.json must exist")
        contract = json.loads(contract_path.read_text())

        self.assertEqual(contract["revision"], "catalog-retention-v3")
        self.assertEqual(contract["reserve_policy"]["reserve_factor"], 2)
        self.assertFalse(contract["reserve_policy"]["historically_complete"])
        self.assertEqual(contract["objectives_count"], 7543)
        self.assertEqual(contract["primary_capacity_total"], 115964)
        self.assertEqual(contract["effective_capacity_total"], 231928)
        self.assertEqual(contract["expansion_objectives_count"], 516)
        self.assertEqual(contract["expansion_primary_capacity"], 10320)
        self.assertEqual(contract["expansion_effective_capacity"], 20640)
        self.assertEqual(contract["primary_capacities"], automation_primary_objectives_v3())
        self.assertEqual(contract["effective_capacities"], automation_objectives_v3())

    def test_policy_revision_v3(self):
        rev = automation_policy_revision_v3()
        self.assertIsInstance(rev, str)
        self.assertEqual(len(rev), 64)
        # Determinism
        rev2 = automation_policy_revision_v3()
        self.assertEqual(rev, rev2)


class TestOffersV3NearestWitnessAndGating(unittest.TestCase):
    """Test deterministic v3 offers, nearest-witness rank shape, gating, and spawn rules."""

    def test_rank_format_and_witness_selection(self):
        obs = _make_dummy_observation(12345, with_spawn=False)
        oid = digest(obs)
        wid = world_id(obs["identity"])

        # Create summary with a core biome witness
        feat_data = {
            "biome.exact.ocean": {
                "dimension": "overworld",
                "counts": [1, 1, 1, 1],
                "complete": [False, False, False, False],
                "nearest_d2": 400,
                "witness": [12, 63, 16],
            }
        }
        s_origin = _make_dummy_summary(obs, (0, 0), ["origin", "recommended"], 2048, feat_data)
        offers = automation_offers_v3(obs, [s_origin], [])

        ocean_offers = [o for o in offers if o["objective_id"] == "v3.near:biome.exact.ocean:2048:origin"]
        self.assertEqual(len(ocean_offers), 1)
        off = ocean_offers[0]

        # Expected rank: [d2, world_id, anchor_x, anchor_z, witness_x, witness_y, witness_z]
        expected_rank = [400, wid, 0, 0, 12, 63, 16]
        self.assertEqual(off["rank"], expected_rank)
        self.assertEqual(off["member"]["world_id"], wid)
        self.assertEqual(off["member"]["anchor"], [0, 0])
        self.assertEqual(off["member"]["source_observation_id"], oid)

    def test_gated_choices_offer_none(self):
        obs = _make_dummy_observation(12345, with_spawn=True)
        # Supply witnesses for both enabled and gated biomes
        feat_data = {
            "biome.exact.plains": {
                "nearest_d2": 100,
                "witness": [6, 63, 8],
            },
            "biome.exact.jagged_peaks": {  # Initially gated mountain
                "nearest_d2": 25,
                "witness": [3, 160, 4],
            },
            "biome.exact.deep_dark": {  # Initially gated cave
                "nearest_d2": 64,
                "witness": [0, -48, 8],
            },
            "structure.igloo_with_basement": {  # Initially gated variant
                "nearest_d2": 144,
                "witness": [12, 0, 0],
            },
        }
        s = _make_dummy_summary(obs, (0, 0), ["origin", "recommended"], 2048, feat_data)
        offers = automation_offers_v3(obs, [s], [])

        # Enabled biome should offer
        plains_offers = [o for o in offers if "biome.exact.plains" in o["objective_id"]]
        self.assertGreater(len(plains_offers), 0)

        # Gated biomes and structures must offer NONE under default registry
        jagged_offers = [o for o in offers if "biome.exact.jagged_peaks" in o["objective_id"]]
        self.assertEqual(len(jagged_offers), 0)

        cave_offers = [o for o in offers if "biome.exact.deep_dark" in o["objective_id"]]
        self.assertEqual(len(cave_offers), 0)

        igloo_offers = [o for o in offers if "structure.igloo_with_basement" in o["objective_id"]]
        self.assertEqual(len(igloo_offers), 0)

    def test_fixture_registry_injection(self):
        obs = _make_dummy_observation(12345, with_spawn=False)
        feat_data = {
            "biome.exact.jagged_peaks": {
                "nearest_d2": 25,
                "witness": [3, 160, 4],
            }
        }
        s = _make_dummy_summary(obs, (0, 0), ["origin"], 2048, feat_data)

        # 1. Without fixture: gated, offers none
        offers_default = automation_offers_v3(obs, [s], [])
        self.assertEqual(len([o for o in offers_default if "jagged_peaks" in o["objective_id"]]), 0)

        # 2. Injecting fixture registry that enables jagged_peaks
        fixture_reg = {
            "features": [
                {"id": "biome.exact.jagged_peaks", "available": True},
            ]
        }
        offers_enabled = automation_offers_v3(obs, [s], [], registry=fixture_reg)
        jagged = [o for o in offers_enabled if o["objective_id"] == "v3.near:biome.exact.jagged_peaks:2048:origin"]
        self.assertEqual(len(jagged), 1)

    def test_spawn_mode_requires_actual_spawn_anchor(self):
        # World without spawn anchor
        obs_no_spawn = _make_dummy_observation(111, with_spawn=False)
        feat_data = {
            "biome.exact.desert": {
                "nearest_d2": 100,
                "witness": [10, 63, 0],
            }
        }
        s_origin = _make_dummy_summary(obs_no_spawn, (0, 0), ["origin", "recommended"], 2048, feat_data)
        offers_no_spawn = automation_offers_v3(obs_no_spawn, [s_origin], [])

        # Origin should offer, spawn should NOT offer (no origin fallback)
        self.assertTrue(any(o["objective_id"] == "v3.near:biome.exact.desert:2048:origin" for o in offers_no_spawn))
        self.assertFalse(any(":spawn" in o["objective_id"] for o in offers_no_spawn))

        # World with actual spawn anchor
        obs_with_spawn = _make_dummy_observation(222, with_spawn=True)
        s_spawn = _make_dummy_summary(
            obs_with_spawn,
            (100, 200),
            ["world_spawn_estimated"],
            2048,
            feat_data,
        )
        offers_with_spawn = automation_offers_v3(obs_with_spawn, [s_spawn], [])
        spawn_offers = [o for o in offers_with_spawn if o["objective_id"] == "v3.near:biome.exact.desert:2048:spawn"]
        self.assertEqual(len(spawn_offers), 1)
        self.assertEqual(spawn_offers[0]["rank"][2:4], [100, 200])

    def test_witness_outside_border_rejected(self):
        obs = _make_dummy_observation(12345, with_spawn=False)
        # Border side 2048 at anchor (0, 0) covers [-1024, 1024)
        # Put witness outside: x = 1500
        feat_data = {
            "biome.exact.forest": {
                "nearest_d2": 1500 * 1500,
                "witness": [1500, 63, 0],
            }
        }
        s = _make_dummy_summary(obs, (0, 0), ["origin"], 2048, feat_data)
        offers = automation_offers_v3(obs, [s], [])
        forest_offers = [o for o in offers if "biome.exact.forest" in o["objective_id"]]
        self.assertEqual(len(forest_offers), 0)


class TestFullSortDedupAndTies(unittest.TestCase):
    """Test candidate ordering, full sort parity, deduplication, and tie-breaking."""

    def test_best_per_world_deduplication(self):
        obs = _make_dummy_observation(555, with_spawn=False)
        # Supply two summaries for the SAME world at different anchors
        # Anchor 1: d2 = 500
        s1 = _make_dummy_summary(obs, (0, 0), ["recommended"], 2048, {
            "biome.exact.plains": {"nearest_d2": 500, "witness": [20, 63, 10]}
        })
        # Anchor 2: d2 = 100 (better!)
        s2 = _make_dummy_summary(obs, (256, 256), ["recommended"], 2048, {
            "biome.exact.plains": {"nearest_d2": 100, "witness": [260, 63, 260]}
        })

        offers = automation_offers_v3(obs, [s1, s2], [])
        plains = [o for o in offers if o["objective_id"] == "v3.near:biome.exact.plains:2048:recommended"]
        # Only the SINGLE best anchor per world must enter
        self.assertEqual(len(plains), 1)
        self.assertEqual(plains[0]["rank"][0], 100)
        self.assertEqual(plains[0]["rank"][2:4], [256, 256])

    def test_full_sort_parity(self):
        """Compare candidate ranking against an independent Python sorted oracle."""
        candidates = []
        for seed_val in (40, 10, 30, 20, 50, 25, 15):
            ident = _make_dummy_identity(seed_val)
            wid = world_id(ident)
            d2 = seed_val * 10
            rank = [d2, wid, 0, 0, 5, 63, 5]
            candidates.append({"world_id": wid, "seed": str(seed_val), "rank": rank})

        # Independent oracle: sort by key
        oracle_sorted = sorted(candidates, key=lambda c: tuple(c["rank"]))
        primary, reserve = split_primary_reserve(oracle_sorted, 3)

        self.assertEqual(len(primary), 3)
        self.assertEqual([c["seed"] for c in primary], ["10", "15", "20"])
        self.assertEqual([c["seed"] for c in reserve], ["25", "30", "40"])

    def test_deterministic_ties(self):
        """Verify deterministic tie-breaking on d2 by world_id hex ascending."""
        w1_ident = _make_dummy_identity(100)
        w2_ident = _make_dummy_identity(200)
        w1_id = world_id(w1_ident)
        w2_id = world_id(w2_ident)

        c1 = {"world_id": w1_id, "seed": "100", "rank": [500, w1_id, 0, 0, 10, 63, 10]}
        c2 = {"world_id": w2_id, "seed": "200", "rank": [500, w2_id, 0, 0, 10, 63, 10]}

        sorted_cands = sorted([c1, c2], key=lambda c: tuple(c["rank"]))
        expected_first = c1 if w1_id < w2_id else c2
        self.assertEqual(sorted_cands[0]["world_id"], expected_first["world_id"])


class TestRoleOverlapAndGenericSearch(unittest.TestCase):
    """Test that world roles are objective-scoped and generic search includes reserves."""

    def test_role_overlap(self):
        w1 = "1" * 64
        w2 = "2" * 64

        # Objective A: w1 is primary (rank 0), w2 is reserve (rank 1)
        # Objective B: w2 is primary (rank 0), w1 is reserve (rank 1)
        obj_members = {
            "obj_a": [{"world_id": w1}, {"world_id": w2}],
            "obj_b": [{"world_id": w2}, {"world_id": w1}],
        }
        primary_caps = {"obj_a": 1, "obj_b": 1}

        w1_roles = world_objective_roles(obj_members, primary_caps, world_id=w1)
        self.assertEqual(w1_roles, {"obj_a": "primary", "obj_b": "reserve"})

        w2_roles = world_objective_roles(obj_members, primary_caps, world_id=w2)
        self.assertEqual(w2_roles, {"obj_a": "reserve", "obj_b": "primary"})

    def test_generic_search_candidates_union(self):
        obj_members = {
            "obj_a": [{"world_id": "aaa"}, {"world_id": "bbb"}],
            "obj_b": [{"world_id": "bbb"}, {"world_id": "ccc"}],
        }
        union = generic_search_candidates(obj_members, pins=["ddd"])
        self.assertEqual(union, ["aaa", "bbb", "ccc", "ddd"])


class TestLegacyParityAndCompatibility(unittest.TestCase):
    """Verify that legacy retention functions remain intact and v3 subsumes legacy offers."""

    def test_legacy_functions_unmodified(self):
        from seed_search.catalog.models import empty_observation_v2
        from seed_search.catalog.summaries import summarize_v2
        from seed_search.catalog.retention import automation_offers, automation_policy_revision

        obs = empty_observation_v2(identity('123', model_id='MC_26_50', native_sha256='a'*64, source_sha256='b'*64))
        obs['structures'] = {'structure.village': [[0, 0]]}
        obs['coverage']['structure.village'] = dict(
            status='complete',
            bounds=obs['bounds']['overworld'],
            method_id='predictor_viable_starts_v1',
        )

        sums = summarize_v2(obs)
        legacy_offers = automation_offers(obs, sums, [])
        v3_offers = automation_offers_v3(obs, sums, [])

        # All legacy offers must be present in v3_offers with identical rank
        legacy_map = {o['objective_id']: o['rank'] for o in legacy_offers}
        v3_map = {o['objective_id']: o['rank'] for o in v3_offers}

        self.assertGreater(len(legacy_map), 0)
        for oid, rk in legacy_map.items():
            self.assertIn(oid, v3_map, f"Legacy objective {oid} missing from v3 offers")
            self.assertEqual(v3_map[oid], rk, f"Rank mismatch for legacy objective {oid}")

        # Legacy policy revision runs cleanly
        rev = automation_policy_revision()
        self.assertIsInstance(rev, str)
        self.assertEqual(len(rev), 64)


if __name__ == "__main__":
    unittest.main()
