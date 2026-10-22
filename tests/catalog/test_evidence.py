"""Tests for Stage D frozen evidence overlay interfaces and persistence."""
import copy
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from seed_search.catalog.evidence import (
    EVIDENCE_REVISION,
    SUMMARY_REVISION,
    FEATURE_TO_COMMAND,
    TEMPLE_FEATURE_IDS,
    build_evidence,
    validate_evidence,
    write_evidence,
    read_evidence,
    summarize_structure,
)
from seed_search.catalog.models import (
    identity,
    empty_observation,
    world_id,
    observation_id,
)
from seed_search.catalog.registry import digest


def _make_base_observation():
    ident = identity(
        12345,
        model_id="MC_26_50",
        native_sha256="a" * 64,
        source_sha256="b" * 64,
    )
    obs = empty_observation(ident)
    obs["structures"]["structure.village"] = [[100, 200], [300, 400]]
    obs["structures"]["structure.desert_pyramid"] = [[500, 600]]
    obs["biomes"] = [[64, 63, 64, 1]]
    obs["biome_names"] = {"1": "plains"}
    return obs


def _make_base_verifier():
    return {
        "edition": "bedrock",
        "game_build_id": "1.21.50.07",
        "image_sha256": "c" * 64,
        "script_api": "2.10.0",
        "settings_sha256": "d" * 64,
        "report_sha256s": ["e" * 64],
    }


class TestEvidenceOverlay(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.root = Path(self.tmp_dir).resolve()
        self.snapshot_id = "1" * 64

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_build_and_validate_evidence_valid(self):
        obs = _make_base_observation()
        verifier = _make_base_verifier()
        struct_checks = [
            {
                "feature_id": "structure.village",
                "command_id": "village",
                "predicted": [100, 200],
                "reported": [100, 200],
                "outcome": "located_exact",
            },
            {
                "feature_id": "structure.village",
                "command_id": "village",
                "predicted": [300, 400],
                "reported": [305, 405],
                "outcome": "coordinate_difference",
            },
            {
                "feature_id": "structure.desert_pyramid",
                "command_id": "temple",
                "predicted": [500, 600],
                "reported": None,
                "outcome": "no_location",
            },
        ]
        biome_checks = [
            {
                "position": [64, 63, 64],
                "observed_name": "minecraft:plains",
                "outcome": "observed",
            }
        ]

        payload = build_evidence(
            obs,
            self.snapshot_id,
            verifier,
            struct_checks,
            biome_checks,
        )

        self.assertEqual(payload["revision"], EVIDENCE_REVISION)
        self.assertEqual(payload["snapshot_id"], self.snapshot_id)
        self.assertEqual(payload["world_id"], world_id(obs["identity"]))
        self.assertEqual(payload["observation_id"], observation_id(obs))
        self.assertEqual(payload["source_identity"], obs["identity"])
        self.assertEqual(payload["verifier"], verifier)
        self.assertEqual(len(payload["structure_checks"]), 3)
        self.assertEqual(len(payload["biome_checks"]), 1)

        # Standalone validation and with observation
        validated_standalone = validate_evidence(payload)
        self.assertIs(validated_standalone, payload)
        validated_obs = validate_evidence(payload, observation=obs)
        self.assertIs(validated_obs, payload)

    def test_build_evidence_does_not_mutate_caller_data(self):
        obs = _make_base_observation()
        obs_copy = copy.deepcopy(obs)
        verifier = _make_base_verifier()
        verifier_copy = copy.deepcopy(verifier)
        struct_checks = [
            {
                "feature_id": "structure.village",
                "command_id": "village",
                "predicted": [100, 200],
                "reported": [100, 200],
                "outcome": "located_exact",
            }
        ]
        struct_checks_copy = copy.deepcopy(struct_checks)
        biome_checks = [
            {
                "position": [64, 63, 64],
                "observed_name": "plains",
                "outcome": "observed",
            }
        ]
        biome_checks_copy = copy.deepcopy(biome_checks)

        payload = build_evidence(obs, self.snapshot_id, verifier, struct_checks, biome_checks)
        self.assertEqual(obs, obs_copy)
        self.assertEqual(verifier, verifier_copy)
        self.assertEqual(struct_checks, struct_checks_copy)
        self.assertEqual(biome_checks, biome_checks_copy)

        # Modifying payload does not affect caller structures
        payload["structure_checks"].append({})
        self.assertEqual(len(struct_checks), 1)

    def test_structure_outcomes_and_coordinate_rules(self):
        obs = _make_base_observation()
        verifier = _make_base_verifier()

        def make_payload_with_check(reported, outcome):
            return {
                "revision": EVIDENCE_REVISION,
                "snapshot_id": self.snapshot_id,
                "world_id": world_id(obs["identity"]),
                "observation_id": observation_id(obs),
                "source_identity": copy.deepcopy(obs["identity"]),
                "verifier": copy.deepcopy(verifier),
                "structure_checks": [
                    {
                        "feature_id": "structure.village",
                        "command_id": "village",
                        "predicted": [100, 200],
                        "reported": reported,
                        "outcome": outcome,
                    }
                ],
                "biome_checks": [],
            }

        # located_exact
        validate_evidence(make_payload_with_check([100, 200], "located_exact"))
        with self.assertRaises(ValueError):
            validate_evidence(make_payload_with_check([105, 200], "located_exact"))
        with self.assertRaises(ValueError):
            validate_evidence(make_payload_with_check(None, "located_exact"))

        # coordinate_difference
        validate_evidence(make_payload_with_check([105, 200], "coordinate_difference"))
        with self.assertRaises(ValueError):
            validate_evidence(make_payload_with_check([100, 200], "coordinate_difference"))
        with self.assertRaises(ValueError):
            validate_evidence(make_payload_with_check(None, "coordinate_difference"))

        # no_location
        validate_evidence(make_payload_with_check(None, "no_location"))
        with self.assertRaises(ValueError):
            validate_evidence(make_payload_with_check([100, 200], "no_location"))

        # error
        validate_evidence(make_payload_with_check(None, "error"))
        with self.assertRaises(ValueError):
            validate_evidence(make_payload_with_check([100, 200], "error"))

        # invalid outcome
        with self.assertRaises(ValueError):
            validate_evidence(make_payload_with_check([100, 200], "verified"))

    def test_no_boolean_coordinates_and_safe_bounds(self):
        obs = _make_base_observation()
        verifier = _make_base_verifier()

        # bool in predicted
        p1 = {
            "revision": EVIDENCE_REVISION,
            "snapshot_id": self.snapshot_id,
            "world_id": world_id(obs["identity"]),
            "observation_id": observation_id(obs),
            "source_identity": copy.deepcopy(obs["identity"]),
            "verifier": copy.deepcopy(verifier),
            "structure_checks": [
                {
                    "feature_id": "structure.village",
                    "command_id": "village",
                    "predicted": [True, 200],
                    "reported": [1, 200],
                    "outcome": "coordinate_difference",
                }
            ],
            "biome_checks": [],
        }
        with self.assertRaises(ValueError):
            validate_evidence(p1)

        # bool in reported
        p2 = copy.deepcopy(p1)
        p2["structure_checks"][0]["predicted"] = [100, 200]
        p2["structure_checks"][0]["reported"] = [100, False]
        with self.assertRaises(ValueError):
            validate_evidence(p2)

        # bool in biome position
        p3 = copy.deepcopy(p2)
        p3["structure_checks"][0]["reported"] = [100, 200]
        p3["structure_checks"][0]["outcome"] = "located_exact"
        p3["biome_checks"] = [{"position": [0, True, 0], "observed_name": "plains", "outcome": "observed"}]
        with self.assertRaises(ValueError):
            validate_evidence(p3)

        # bounds abs >= 2**30
        p4 = copy.deepcopy(p2)
        p4["structure_checks"][0]["reported"] = [100, 200]
        p4["structure_checks"][0]["outcome"] = "located_exact"
        p4["structure_checks"][0]["predicted"] = [1 << 30, 0]
        with self.assertRaises(ValueError):
            validate_evidence(p4)

    def test_feature_to_command_adapter_mapping(self):
        self.assertEqual(len(FEATURE_TO_COMMAND), 14)
        expected = {
            "structure.village": "village",
            "structure.trial_chamber": "trial_chambers",
            "structure.ancient_city": "ancient_city",
            "structure.mansion": "mansion",
            "structure.monument": "monument",
            "structure.outpost": "pillager_outpost",
            "structure.desert_pyramid": "temple",
            "structure.jungle_temple": "temple",
            "structure.swamp_hut": "temple",
            "structure.igloo": "temple",
            "structure.trail_ruins": "trail_ruins",
            "structure.ruined_portal": "ruined_portal",
            "structure.shipwreck": "shipwreck",
            "structure.mineshaft": "mineshaft",
        }
        self.assertEqual(FEATURE_TO_COMMAND, expected)

        obs = _make_base_observation()
        verifier = _make_base_verifier()

        for feat, cmd in expected.items():
            payload = {
                "revision": EVIDENCE_REVISION,
                "snapshot_id": self.snapshot_id,
                "world_id": world_id(obs["identity"]),
                "observation_id": observation_id(obs),
                "source_identity": copy.deepcopy(obs["identity"]),
                "verifier": copy.deepcopy(verifier),
                "structure_checks": [
                    {
                        "feature_id": feat,
                        "command_id": cmd,
                        "predicted": [0, 0],
                        "reported": [0, 0],
                        "outcome": "located_exact",
                    }
                ],
                "biome_checks": [],
            }
            validate_evidence(payload)

            # Mismatched command
            payload_bad = copy.deepcopy(payload)
            payload_bad["structure_checks"][0]["command_id"] = "unknown_cmd"
            with self.assertRaises(ValueError):
                validate_evidence(payload_bad)

        # Unregistered feature
        payload_bad_feat = {
            "revision": EVIDENCE_REVISION,
            "snapshot_id": self.snapshot_id,
            "world_id": world_id(obs["identity"]),
            "observation_id": observation_id(obs),
            "source_identity": copy.deepcopy(obs["identity"]),
            "verifier": copy.deepcopy(verifier),
            "structure_checks": [
                {
                    "feature_id": "structure.bastion",
                    "command_id": "bastion",
                    "predicted": [0, 0],
                    "reported": [0, 0],
                    "outcome": "located_exact",
                }
            ],
            "biome_checks": [],
        }
        with self.assertRaises(ValueError):
            validate_evidence(payload_bad_feat)

    def test_uniqueness_checks(self):
        obs = _make_base_observation()
        verifier = _make_base_verifier()

        # duplicate structure check (same feature, same predicted point)
        p_dup_struct = {
            "revision": EVIDENCE_REVISION,
            "snapshot_id": self.snapshot_id,
            "world_id": world_id(obs["identity"]),
            "observation_id": observation_id(obs),
            "source_identity": copy.deepcopy(obs["identity"]),
            "verifier": copy.deepcopy(verifier),
            "structure_checks": [
                {
                    "feature_id": "structure.village",
                    "command_id": "village",
                    "predicted": [100, 200],
                    "reported": [100, 200],
                    "outcome": "located_exact",
                },
                {
                    "feature_id": "structure.village",
                    "command_id": "village",
                    "predicted": [100, 200],
                    "reported": [105, 205],
                    "outcome": "coordinate_difference",
                },
            ],
            "biome_checks": [],
        }
        with self.assertRaises(ValueError):
            validate_evidence(p_dup_struct)

        # duplicate biome check
        p_dup_biome = {
            "revision": EVIDENCE_REVISION,
            "snapshot_id": self.snapshot_id,
            "world_id": world_id(obs["identity"]),
            "observation_id": observation_id(obs),
            "source_identity": copy.deepcopy(obs["identity"]),
            "verifier": copy.deepcopy(verifier),
            "structure_checks": [],
            "biome_checks": [
                {"position": [64, 63, 64], "observed_name": "plains", "outcome": "observed"},
                {"position": [64, 63, 64], "observed_name": "forest", "outcome": "observed"},
            ],
        }
        with self.assertRaises(ValueError):
            validate_evidence(p_dup_biome)

    def test_verifier_validation_rules(self):
        obs = _make_base_observation()
        base_payload = {
            "revision": EVIDENCE_REVISION,
            "snapshot_id": self.snapshot_id,
            "world_id": world_id(obs["identity"]),
            "observation_id": observation_id(obs),
            "source_identity": copy.deepcopy(obs["identity"]),
            "structure_checks": [],
            "biome_checks": [],
        }

        # game_build_id cannot start with research:
        p = copy.deepcopy(base_payload)
        v = _make_base_verifier()
        v["game_build_id"] = "research:MC_26_50"
        p["verifier"] = v
        with self.assertRaises(ValueError):
            validate_evidence(p)

        # image_sha256 cannot have sha256: prefix
        p = copy.deepcopy(base_payload)
        v = _make_base_verifier()
        v["image_sha256"] = "sha256:" + ("a" * 64)
        p["verifier"] = v
        with self.assertRaises(ValueError):
            validate_evidence(p)

        # report_sha256s empty or >32 or duplicate
        p = copy.deepcopy(base_payload)
        v = _make_base_verifier()
        v["report_sha256s"] = []
        p["verifier"] = v
        with self.assertRaises(ValueError):
            validate_evidence(p)

        p = copy.deepcopy(base_payload)
        v = _make_base_verifier()
        v["report_sha256s"] = ["f" * 64, "f" * 64]
        p["verifier"] = v
        with self.assertRaises(ValueError):
            validate_evidence(p)

        p = copy.deepcopy(base_payload)
        v = _make_base_verifier()
        v["report_sha256s"] = [f"{i:064x}" for i in range(33)]
        p["verifier"] = v
        with self.assertRaises(ValueError):
            validate_evidence(p)

    def test_source_membership_validation(self):
        obs = _make_base_observation()
        verifier = _make_base_verifier()

        # Structure point not in source observation
        payload_bad_struct = {
            "revision": EVIDENCE_REVISION,
            "snapshot_id": self.snapshot_id,
            "world_id": world_id(obs["identity"]),
            "observation_id": observation_id(obs),
            "source_identity": copy.deepcopy(obs["identity"]),
            "verifier": copy.deepcopy(verifier),
            "structure_checks": [
                {
                    "feature_id": "structure.village",
                    "command_id": "village",
                    "predicted": [9999, 9999],
                    "reported": [9999, 9999],
                    "outcome": "located_exact",
                }
            ],
            "biome_checks": [],
        }
        with self.assertRaises(ValueError):
            validate_evidence(payload_bad_struct, observation=obs)

        # Biome point not in source observation
        payload_bad_biome = {
            "revision": EVIDENCE_REVISION,
            "snapshot_id": self.snapshot_id,
            "world_id": world_id(obs["identity"]),
            "observation_id": observation_id(obs),
            "source_identity": copy.deepcopy(obs["identity"]),
            "verifier": copy.deepcopy(verifier),
            "structure_checks": [],
            "biome_checks": [
                {
                    "position": [0, 0, 0],
                    "observed_name": "plains",
                    "outcome": "observed",
                }
            ],
        }
        with self.assertRaises(ValueError):
            validate_evidence(payload_bad_biome, observation=obs)

        # Mismatched observation identity / world_id / observation_id
        obs2 = copy.deepcopy(obs)
        obs2["identity"]["seed"] = "99999"
        with self.assertRaises(ValueError):
            validate_evidence(payload_bad_struct, observation=obs2)

    def test_persistence_write_and_read(self):
        obs = _make_base_observation()
        verifier = _make_base_verifier()
        payload = build_evidence(
            obs,
            self.snapshot_id,
            verifier,
            [
                {
                    "feature_id": "structure.village",
                    "command_id": "village",
                    "predicted": [100, 200],
                    "reported": [100, 200],
                    "outcome": "located_exact",
                }
            ],
        )

        target_path = write_evidence(self.root, payload)
        expected_path = self.root / "evidence" / self.snapshot_id / f"{payload['world_id']}.json"
        self.assertEqual(target_path, expected_path)
        self.assertTrue(target_path.exists())

        # Check raw file contents
        raw = json.loads(target_path.read_text())
        self.assertEqual(set(raw), {"sha256", "payload"})
        self.assertEqual(raw["sha256"], digest(payload))

        # Read back
        read_back = read_evidence(
            self.root,
            self.snapshot_id,
            payload["world_id"],
            payload["observation_id"],
        )
        self.assertEqual(read_back, payload)

    def test_persistence_missing_returns_none(self):
        missing = read_evidence(
            self.root,
            self.snapshot_id,
            "2" * 64,
            "3" * 64,
        )
        self.assertIsNone(missing)

    def test_persistence_immutability_and_no_clobber(self):
        obs = _make_base_observation()
        verifier = _make_base_verifier()
        payload = build_evidence(
            obs,
            self.snapshot_id,
            verifier,
            [
                {
                    "feature_id": "structure.village",
                    "command_id": "village",
                    "predicted": [100, 200],
                    "reported": [100, 200],
                    "outcome": "located_exact",
                }
            ],
        )

        p1 = write_evidence(self.root, payload)
        # Re-publishing identical payload succeeds
        p2 = write_evidence(self.root, payload)
        self.assertEqual(p1, p2)

        # Modifying payload for same snapshot_id and world_id raises ValueError
        payload_alt = copy.deepcopy(payload)
        payload_alt["verifier"]["script_api"] = "2.11.0"
        with self.assertRaises(ValueError):
            write_evidence(self.root, payload_alt)

    def test_persistence_corruption_and_mismatch(self):
        obs = _make_base_observation()
        verifier = _make_base_verifier()
        payload = build_evidence(obs, self.snapshot_id, verifier, [])
        target_path = write_evidence(self.root, payload)

        # 1. Invalid JSON
        target_path.write_text("corrupted json {")
        with self.assertRaises(ValueError):
            read_evidence(self.root, self.snapshot_id, payload["world_id"], payload["observation_id"])

        # 2. Checksum mismatch
        bad_envelope = {"sha256": "0" * 64, "payload": payload}
        target_path.write_text(json.dumps(bad_envelope))
        with self.assertRaises(ValueError):
            read_evidence(self.root, self.snapshot_id, payload["world_id"], payload["observation_id"])

        # 3. Duplicate JSON keys
        dup_json = '{"sha256": "' + digest(payload) + '", "payload": {}, "payload": {}}'
        target_path.write_text(dup_json)
        with self.assertRaises(ValueError):
            read_evidence(self.root, self.snapshot_id, payload["world_id"], payload["observation_id"])

        # 4. Nonfinite number (NaN)
        target_path.write_text('{"sha256": "...", "payload": NaN}')
        with self.assertRaises(ValueError):
            read_evidence(self.root, self.snapshot_id, payload["world_id"], payload["observation_id"])

        # 5. Provenance mismatch in call vs content
        target_path.write_text(json.dumps({"sha256": digest(payload), "payload": payload}))
        # Place valid bytes under the wrong identity path: a missing path is
        # legitimately None and cannot test cross-identity artifact substitution.
        wrong_world = target_path.parent / ("4" * 64 + ".json")
        wrong_world.write_bytes(target_path.read_bytes())
        with self.assertRaises(ValueError):
            read_evidence(self.root, self.snapshot_id, "4" * 64, payload["observation_id"])
        wrong_snapshot = self.root / 'evidence' / ('5' * 64) / (payload['world_id'] + '.json')
        wrong_snapshot.parent.mkdir()
        wrong_snapshot.write_bytes(target_path.read_bytes())
        with self.assertRaises(ValueError):
            read_evidence(self.root, "5" * 64, payload["world_id"], payload["observation_id"])
        with self.assertRaises(ValueError):
            read_evidence(self.root, self.snapshot_id, payload["world_id"], "6" * 64)

    def test_persistence_symlink_rejection(self):
        obs = _make_base_observation()
        verifier = _make_base_verifier()
        payload = build_evidence(obs, self.snapshot_id, verifier, [])

        # Symlink at snapshot_id dir
        real_target_dir = self.root / "real_dir"
        real_target_dir.mkdir(parents=True, exist_ok=True)
        symlink_snap_dir = self.root / "evidence" / self.snapshot_id
        (self.root / "evidence").mkdir(parents=True, exist_ok=True)
        os.symlink(real_target_dir, symlink_snap_dir)

        with self.assertRaises(ValueError):
            write_evidence(self.root, payload)
        with self.assertRaises(ValueError):
            read_evidence(self.root, self.snapshot_id, payload["world_id"], payload["observation_id"])

    def test_summarize_structure_none_payload(self):
        summary = summarize_structure(None, "structure.village", [[100, 200], [300, 400]])
        self.assertEqual(summary["revision"], SUMMARY_REVISION)
        self.assertEqual(summary["feature_id"], "structure.village")
        self.assertEqual(summary["predicted_count"], 2)
        self.assertEqual(summary["tested_count"], 0)
        self.assertEqual(summary["located_exact"], 0)
        self.assertEqual(summary["coordinate_difference"], 0)
        self.assertEqual(summary["no_location"], 0)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["untested_count"], 2)
        self.assertFalse(summary["grouped_command"])
        self.assertIsNone(summary["verifier_game_build_id"])
        self.assertIsNone(summary["generated_count"])
        self.assertIsNone(summary["exhaustive_count"])

    def test_summarize_structure_with_payload_and_scopes(self):
        obs = _make_base_observation()
        verifier = _make_base_verifier()
        payload = build_evidence(
            obs,
            self.snapshot_id,
            verifier,
            [
                {
                    "feature_id": "structure.village",
                    "command_id": "village",
                    "predicted": [100, 200],
                    "reported": [100, 200],
                    "outcome": "located_exact",
                },
                {
                    "feature_id": "structure.village",
                    "command_id": "village",
                    "predicted": [300, 400],
                    "reported": [305, 405],
                    "outcome": "coordinate_difference",
                },
            ],
        )

        # Scoped to both
        s_both = summarize_structure(payload, "structure.village", [[100, 200], [300, 400]])
        self.assertEqual(s_both["predicted_count"], 2)
        self.assertEqual(s_both["tested_count"], 2)
        self.assertEqual(s_both["located_exact"], 1)
        self.assertEqual(s_both["coordinate_difference"], 1)
        self.assertEqual(s_both["untested_count"], 0)
        self.assertEqual(s_both["verifier_game_build_id"], "1.21.50.07")

        # Scoped to only [100, 200]
        s_one = summarize_structure(payload, "structure.village", [[100, 200]])
        self.assertEqual(s_one["predicted_count"], 1)
        self.assertEqual(s_one["tested_count"], 1)
        self.assertEqual(s_one["located_exact"], 1)
        self.assertEqual(s_one["coordinate_difference"], 0)
        self.assertEqual(s_one["untested_count"], 0)

        # Scoped with extra untested prediction
        s_extra = summarize_structure(payload, "structure.village", [[100, 200], [999, 999]])
        self.assertEqual(s_extra["predicted_count"], 2)
        self.assertEqual(s_extra["tested_count"], 1)
        self.assertEqual(s_extra["located_exact"], 1)
        self.assertEqual(s_extra["untested_count"], 1)

        # Scoped with total_count override
        s_total = summarize_structure(payload, "structure.village", [[100, 200]], total_count=5)
        self.assertEqual(s_total["predicted_count"], 5)
        self.assertEqual(s_total["tested_count"], 1)
        self.assertEqual(s_total["untested_count"], 4)

        # total_count smaller than supplied unique predictions raises ValueError
        with self.assertRaises(ValueError):
            summarize_structure(payload, "structure.village", [[100, 200], [300, 400]], total_count=1)

    def test_summarize_structure_temple_grouping(self):
        for temple_feat in (
            "structure.desert_pyramid",
            "structure.jungle_temple",
            "structure.swamp_hut",
            "structure.igloo",
        ):
            summary = summarize_structure(None, temple_feat, [])
            self.assertTrue(summary["grouped_command"])

        for non_temple in (
            "structure.village",
            "structure.trial_chamber",
            "structure.ancient_city",
            "structure.mansion",
            "structure.monument",
            "structure.outpost",
            "structure.trail_ruins",
            "structure.ruined_portal",
            "structure.shipwreck",
            "structure.mineshaft",
        ):
            summary = summarize_structure(None, non_temple, [])
            self.assertFalse(summary["grouped_command"])


if __name__ == "__main__":
    unittest.main()
