"""Unit tests for structure navigation coordinates module."""

from dataclasses import FrozenInstanceError, asdict, is_dataclass
import unittest

from seed_search.realm.structure_coordinates import (
    CONVENTION_FORTRESS_NETHER,
    CONVENTION_MINESHAFT_OVERWORLD,
    CONVENTION_OUTPOST_OVERWORLD,
    SUPPORTED_BDS_BUILD,
    SUPPORTED_PREDICTION_REVISION,
    NavigationProjection,
    project_navigation_reference,
)


class TestStructureCoordinates(unittest.TestCase):
    """Test suite covering deterministic navigation projections and semantic guards."""

    def test_outpost_whitelist_projection_positive(self):
        """Outpost in Overworld applies exact +8, +8 offset under pinned scope."""
        proj = project_navigation_reference(
            "outpost",
            100,
            200,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension="overworld",
        )
        self.assertIsNotNone(proj)
        self.assertEqual(proj.structure_type, "outpost")
        self.assertEqual(proj.candidate_x, 100)
        self.assertEqual(proj.candidate_z, 200)
        self.assertEqual(proj.navigation_x, 108)
        self.assertEqual(proj.navigation_z, 208)
        self.assertEqual(proj.dimension, "overworld")
        self.assertEqual(proj.convention_id, CONVENTION_OUTPOST_OVERWORLD)
        self.assertEqual(proj.observed_build_scope, "1.26.52.3")
        self.assertEqual(proj.observed_build, "1.26.52.3")

    def test_mineshaft_whitelist_projection_positive(self):
        """Mineshaft in Overworld applies exact -8, -8 offset under pinned scope."""
        proj = project_navigation_reference(
            "mineshaft",
            64,
            128,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension="overworld",
        )
        self.assertIsNotNone(proj)
        self.assertEqual(proj.structure_type, "mineshaft")
        self.assertEqual(proj.candidate_x, 64)
        self.assertEqual(proj.candidate_z, 128)
        self.assertEqual(proj.navigation_x, 56)
        self.assertEqual(proj.navigation_z, 120)
        self.assertEqual(proj.dimension, "overworld")
        self.assertEqual(proj.convention_id, CONVENTION_MINESHAFT_OVERWORLD)
        self.assertEqual(proj.observed_build_scope, "1.26.52.3")
        self.assertEqual(proj.observed_build, "1.26.52.3")

    def test_fortress_whitelist_projection_positive(self):
        """Fortress in Nether applies exact -8, -8 offset under pinned scope."""
        proj = project_navigation_reference(
            "fortress",
            300,
            400,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension="nether",
        )
        self.assertIsNotNone(proj)
        self.assertEqual(proj.structure_type, "fortress")
        self.assertEqual(proj.candidate_x, 300)
        self.assertEqual(proj.candidate_z, 400)
        self.assertEqual(proj.navigation_x, 292)
        self.assertEqual(proj.navigation_z, 392)
        self.assertEqual(proj.dimension, "nether")
        self.assertEqual(proj.convention_id, CONVENTION_FORTRESS_NETHER)
        self.assertEqual(proj.observed_build_scope, "1.26.52.3")
        self.assertEqual(proj.observed_build, "1.26.52.3")

    def test_keyword_and_positional_calling_modes(self):
        """project_navigation_reference accepts both positional and keyword structure/coords."""
        p_pos = project_navigation_reference(
            "outpost", 16, 32,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension="overworld",
        )
        p_kw = project_navigation_reference(
            structure_type="outpost", x=16, z=32,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension="overworld",
        )
        self.assertEqual(p_pos, p_kw)

    def test_negative_quadrants(self):
        """Test coordinate offsets across all 4 quadrants including fully negative coordinates."""
        test_quadrants = [
            (100, 200),    # (+, +)
            (100, -200),   # (+, -)
            (-100, 200),   # (-, +)
            (-100, -200),  # (-, -)
            (0, 0),        # origin
        ]
        for x, z in test_quadrants:
            with self.subTest(structure="outpost", quadrant=(x, z)):
                p = project_navigation_reference(
                    "outpost", x, z,
                    prediction_revision=SUPPORTED_PREDICTION_REVISION,
                    bds_build=SUPPORTED_BDS_BUILD,
                    dimension="overworld",
                )
                self.assertIsNotNone(p)
                self.assertEqual(p.candidate_x, x)
                self.assertEqual(p.candidate_z, z)
                self.assertEqual(p.navigation_x, x + 8)
                self.assertEqual(p.navigation_z, z + 8)

            with self.subTest(structure="mineshaft", quadrant=(x, z)):
                p = project_navigation_reference(
                    "mineshaft", x, z,
                    prediction_revision=SUPPORTED_PREDICTION_REVISION,
                    bds_build=SUPPORTED_BDS_BUILD,
                    dimension="overworld",
                )
                self.assertIsNotNone(p)
                self.assertEqual(p.candidate_x, x)
                self.assertEqual(p.candidate_z, z)
                self.assertEqual(p.navigation_x, x - 8)
                self.assertEqual(p.navigation_z, z - 8)

            with self.subTest(structure="fortress", quadrant=(x, z)):
                p = project_navigation_reference(
                    "fortress", x, z,
                    prediction_revision=SUPPORTED_PREDICTION_REVISION,
                    bds_build=SUPPORTED_BDS_BUILD,
                    dimension="nether",
                )
                self.assertIsNotNone(p)
                self.assertEqual(p.candidate_x, x)
                self.assertEqual(p.candidate_z, z)
                self.assertEqual(p.navigation_x, x - 8)
                self.assertEqual(p.navigation_z, z - 8)

    def test_boundary_crossing_raw_coord_retained(self):
        """Ensure boundary-crossing raw candidate coordinates are strictly retained without alteration."""
        # 0-boundary crossing: candidate is negative, navigation reference becomes positive
        p_zero = project_navigation_reference(
            "outpost", -4, -6,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension="overworld",
        )
        self.assertIsNotNone(p_zero)
        self.assertEqual(p_zero.candidate_x, -4)
        self.assertEqual(p_zero.candidate_z, -6)
        self.assertEqual(p_zero.navigation_x, 4)
        self.assertEqual(p_zero.navigation_z, 2)

        # Chunk boundary crossing: candidate is in chunk 0 (x=10), nav_x crosses into chunk 1 (x=18)
        p_chunk = project_navigation_reference(
            "outpost", 10, 12,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension="overworld",
        )
        self.assertIsNotNone(p_chunk)
        self.assertEqual(p_chunk.candidate_x, 10)
        self.assertEqual(p_chunk.candidate_z, 12)
        self.assertEqual(p_chunk.candidate_x // 16, 0)
        self.assertEqual(p_chunk.navigation_x // 16, 1)
        self.assertEqual(p_chunk.navigation_x, 18)
        self.assertEqual(p_chunk.navigation_z, 20)

        # Negative chunk boundary crossing for mineshaft: candidate in chunk -1 (x=-1), nav_x in chunk -1 (x=-9)
        p_neg_chunk = project_navigation_reference(
            "mineshaft", -1, -5,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension="overworld",
        )
        self.assertIsNotNone(p_neg_chunk)
        self.assertEqual(p_neg_chunk.candidate_x, -1)
        self.assertEqual(p_neg_chunk.candidate_z, -5)
        self.assertEqual(p_neg_chunk.navigation_x, -9)
        self.assertEqual(p_neg_chunk.navigation_z, -13)

    def test_wrong_and_missing_build(self):
        """Test that wrong, missing, or mismatched build and revision identifiers return None."""
        valid_kwargs = {
            "structure_type": "outpost",
            "x": 100,
            "z": 100,
            "dimension": "overworld",
            "prediction_revision": SUPPORTED_PREDICTION_REVISION,
            "bds_build": SUPPORTED_BDS_BUILD,
        }

        # Missing bds_build (passed None or omitted)
        kwargs_no_build = dict(valid_kwargs)
        kwargs_no_build["bds_build"] = None
        self.assertIsNone(project_navigation_reference(**kwargs_no_build))

        # Wrong bds_build
        for wrong_build in ["1.26.50.0", "1.26.52.2", "1.26.52.4", "preview", "", "1.26"]:
            kwargs = dict(valid_kwargs, bds_build=wrong_build)
            self.assertIsNone(project_navigation_reference(**kwargs))

        # Missing prediction_revision
        kwargs_no_rev = dict(valid_kwargs, prediction_revision=None)
        self.assertIsNone(project_navigation_reference(**kwargs_no_rev))

        # Wrong prediction_revision
        for wrong_rev in ["cubiomes-bedrock-26.40", "cubiomes-java", "cubiomes-bedrock-26.50.1", ""]:
            kwargs = dict(valid_kwargs, prediction_revision=wrong_rev)
            self.assertIsNone(project_navigation_reference(**kwargs))

    def test_dimension_no_8x_scaling(self):
        """Nether structures stay in Nether block coordinates; no 8x coordinate scaling is performed."""
        candidate_x = 320
        candidate_z = 640
        proj = project_navigation_reference(
            "fortress",
            candidate_x,
            candidate_z,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension="nether",
        )
        self.assertIsNotNone(proj)
        self.assertEqual(proj.candidate_x, 320)
        self.assertEqual(proj.candidate_z, 640)
        self.assertEqual(proj.navigation_x, 312)
        self.assertEqual(proj.navigation_z, 632)

        # Explicitly verify NO 8x multiplication or floor division occurred
        self.assertNotEqual(proj.navigation_x, candidate_x * 8)
        self.assertNotEqual(proj.navigation_x, candidate_x // 8)
        self.assertNotEqual(proj.navigation_z, candidate_z * 8)
        self.assertNotEqual(proj.navigation_z, candidate_z // 8)

        # Cross-dimension mismatches must return None
        # Fortress in overworld -> None
        self.assertIsNone(
            project_navigation_reference(
                "fortress", candidate_x, candidate_z,
                prediction_revision=SUPPORTED_PREDICTION_REVISION,
                bds_build=SUPPORTED_BDS_BUILD,
                dimension="overworld",
            )
        )
        # Outpost in nether -> None
        self.assertIsNone(
            project_navigation_reference(
                "outpost", candidate_x, candidate_z,
                prediction_revision=SUPPORTED_PREDICTION_REVISION,
                bds_build=SUPPORTED_BDS_BUILD,
                dimension="nether",
            )
        )
        # Mineshaft in nether -> None
        self.assertIsNone(
            project_navigation_reference(
                "mineshaft", candidate_x, candidate_z,
                prediction_revision=SUPPORTED_PREDICTION_REVISION,
                bds_build=SUPPORTED_BDS_BUILD,
                dimension="nether",
            )
        )
        # End or unknown dimensions -> None
        for dim in ["the_end", "end", "minecraft:overworld", "minecraft:the_nether", "custom"]:
            self.assertIsNone(
                project_navigation_reference(
                    "outpost", 0, 0,
                    prediction_revision=SUPPORTED_PREDICTION_REVISION,
                    bds_build=SUPPORTED_BDS_BUILD,
                    dimension=dim,
                )
            )

    def test_immutable_object(self):
        """NavigationProjection is a frozen immutable dataclass that prevents attribute mutation."""
        proj = project_navigation_reference(
            "outpost",
            16,
            32,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension="overworld",
        )
        self.assertIsNotNone(proj)
        self.assertTrue(is_dataclass(proj))

        with self.assertRaises(FrozenInstanceError):
            proj.navigation_x = 999

        with self.assertRaises(FrozenInstanceError):
            proj.candidate_x = 999

        with self.assertRaises(FrozenInstanceError):
            proj.observed_build_scope = "changed"

        with self.assertRaises(FrozenInstanceError):
            del proj.navigation_x

        # Immutable dataclasses support hashing and set inclusion
        proj_set = {proj}
        self.assertIn(proj, proj_set)

        # Dataclass equality
        proj_copy = project_navigation_reference(
            "outpost",
            16,
            32,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension="overworld",
        )
        self.assertEqual(proj, proj_copy)

        # asdict verification
        d = asdict(proj)
        self.assertEqual(d["structure_type"], "outpost")
        self.assertEqual(d["candidate_x"], 16)
        self.assertEqual(d["candidate_z"], 32)
        self.assertEqual(d["navigation_x"], 24)
        self.assertEqual(d["navigation_z"], 40)
        self.assertEqual(d["dimension"], "overworld")
        self.assertEqual(d["convention_id"], CONVENTION_OUTPOST_OVERWORLD)
        self.assertEqual(d["observed_build_scope"], "1.26.52.3")

    def test_unsupported_stronghold_trial_ruins_and_aliases(self):
        """Strongholds, trial chambers, trail ruins, and other structures return None; no alias guessing."""
        unsupported = [
            # Diagnostic-only or unproved piece structures
            "stronghold",
            "trial_chamber",
            "trail_ruins",
            # Common structures outside exact whitelist
            "village",
            "ancient_city",
            "monument",
            "mansion",
            "swamp_hut",
            "desert_pyramid",
            "jungle_temple",
            "igloo",
            "shipwreck",
            "ocean_ruin",
            "pillager_outpost",
            "bastion",
            "end_city",
            # Prefixed or namespaced aliases must NOT be guessed
            "structure.outpost",
            "structure.mineshaft",
            "structure.fortress",
            "minecraft:outpost",
            "minecraft:mineshaft",
            "minecraft:fortress",
            "outpost ",
            "OUTPOST",
            "fortress_nether",
        ]
        for stype in unsupported:
            for dim in ["overworld", "nether", "the_end"]:
                res = project_navigation_reference(
                    stype,
                    100,
                    100,
                    prediction_revision=SUPPORTED_PREDICTION_REVISION,
                    bds_build=SUPPORTED_BDS_BUILD,
                    dimension=dim,
                )
                self.assertIsNone(
                    res,
                    f"Expected None for unsupported type '{stype}' in dimension '{dim}', got {res}",
                )

    def test_integer_bool_rejection(self):
        """Booleans must be strictly rejected as integer coordinates; non-ints rejected."""
        valid_kwargs = {
            "structure_type": "outpost",
            "dimension": "overworld",
            "prediction_revision": SUPPORTED_PREDICTION_REVISION,
            "bds_build": SUPPORTED_BDS_BUILD,
        }

        # Passing bool to project_navigation_reference returns None
        self.assertIsNone(project_navigation_reference(x=True, z=0, **valid_kwargs))
        self.assertIsNone(project_navigation_reference(x=0, z=False, **valid_kwargs))
        self.assertIsNone(project_navigation_reference(x=True, z=True, **valid_kwargs))
        self.assertIsNone(project_navigation_reference(x=False, z=False, **valid_kwargs))

        # Floats, strings, None coordinates return None
        self.assertIsNone(project_navigation_reference(x=10.5, z=20, **valid_kwargs))
        self.assertIsNone(project_navigation_reference(x=10, z=20.5, **valid_kwargs))
        self.assertIsNone(project_navigation_reference(x="100", z=200, **valid_kwargs))
        self.assertIsNone(project_navigation_reference(x=None, z=200, **valid_kwargs))

        # Direct instantiation of NavigationProjection rejects bool coordinates with TypeError
        with self.assertRaises(TypeError):
            NavigationProjection(
                structure_type="outpost",
                candidate_x=True,
                candidate_z=0,
                navigation_x=8,
                navigation_z=8,
                dimension="overworld",
                convention_id=CONVENTION_OUTPOST_OVERWORLD,
                observed_build_scope=SUPPORTED_BDS_BUILD,
            )
        with self.assertRaises(TypeError):
            NavigationProjection(
                structure_type="outpost",
                candidate_x=0,
                candidate_z=False,
                navigation_x=8,
                navigation_z=8,
                dimension="overworld",
                convention_id=CONVENTION_OUTPOST_OVERWORLD,
                observed_build_scope=SUPPORTED_BDS_BUILD,
            )

    def test_navigation_never_claims_verified_or_generated(self):
        """Navigation projection must not include or claim verified or physical generation status."""
        proj = project_navigation_reference(
            "outpost",
            64,
            64,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension="overworld",
        )
        self.assertIsNotNone(proj)

        # Ensure no verified or generated attributes exist
        self.assertFalse(hasattr(proj, "verified"))
        self.assertFalse(hasattr(proj, "is_verified"))
        self.assertFalse(hasattr(proj, "generated"))
        self.assertFalse(hasattr(proj, "is_generated"))

        # Dataclass fields inspection
        field_names = [f.name for f in getattr(proj, "__dataclass_fields__").values()]
        for prohibited in ["verified", "is_verified", "generated", "is_generated", "count", "border"]:
            self.assertNotIn(prohibited, field_names)

    def test_inputs_not_modified(self):
        """Function invocation does not modify input arguments."""
        x = 50
        z = 75
        stype = "outpost"
        dim = "overworld"
        proj = project_navigation_reference(
            stype, x, z,
            prediction_revision=SUPPORTED_PREDICTION_REVISION,
            bds_build=SUPPORTED_BDS_BUILD,
            dimension=dim,
        )
        self.assertIsNotNone(proj)
        self.assertEqual(x, 50)
        self.assertEqual(z, 75)
        self.assertEqual(stype, "outpost")
        self.assertEqual(dim, "overworld")


if __name__ == "__main__":
    unittest.main()
