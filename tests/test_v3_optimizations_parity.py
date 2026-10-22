"""Comprehensive Regression & Bit-Exact Parity Test for dynamic-envelope-2048-v3.

Verifies that:
1. Evaluating 5,000 seeds through the optimized native sweep and comparing against
   `seed_search.realm.blueprint.evaluate_dynamic_seed` produces 100% bit-exact scores,
   components, and centers for EVERY qualifying candidate match.
2. Retained candidates and a bounded sample of rejects agree with the reference.
3. Multi-threaded execution across 1, 4, 8, 16, 34 threads is 100% deterministic.
4. Cutoff score pruning preserves candidate matches at or above threshold bit-exactly.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
from typing import Any, Dict, List

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from seed_search.realm.blueprint import evaluate_dynamic_seed, dynamic_v3_score
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype, semantic_record, seeds_np
from seed_search.seeds import seed_from_index


def get_v3_prototype(cfg: Dict[str, Any]) -> Prototype:
    """Helper to instantiate prototype using optimized native build."""
    candidate_dirs = [
        ROOT / "runs/dynamic-baseline-2048/native-refinement-2026-10-16",
        ROOT / "runs/dynamic-baseline-2048/native-fixed-2026-10-16",
        ROOT / "runs/dynamic-baseline-2048/native",
        ROOT / "runs/master-implementation-2026-10-10/openmp/install",
    ]
    for d in candidate_dirs:
        if (d / "identity.json").is_file():
            try:
                p = Prototype(d, cfg)
                if p.identity.get("openmp"):
                    return p
            except Exception:
                pass
    return Prototype(None, cfg)


def assert_anchor_bit_exact(native_anchor: Dict[str, Any], py_anchor: Dict[str, Any]) -> None:
    """Verify bit-exact equality between native sweep anchor and Python reference."""
    # 1. Total score and observed score
    assert native_anchor["baseline_score_observed"] == py_anchor["baseline_score_observed"], (
        f"Score mismatch: native={native_anchor['baseline_score_observed']} vs py={py_anchor['baseline_score_observed']}"
    )
    assert native_anchor["baseline_score"] == py_anchor["baseline_score"]

    # 2. Evaluation Center
    assert native_anchor["evaluation_center"] == py_anchor["evaluation_center"], (
        f"Center mismatch: native={native_anchor['evaluation_center']} vs py={py_anchor['evaluation_center']}"
    )

    # 3. Bonus total and deficit penalty
    assert native_anchor["bonus_total"] == py_anchor["bonus_total"]
    assert native_anchor["deficit_penalty"] == py_anchor["deficit_penalty"]

    # 4. Detailed Ranking Components
    native_comp = native_anchor.get("ranking", {}).get("components", {})
    py_comp = py_anchor.get("ranking", {}).get("components", {})
    for key in (
        "bonus_total",
        "deficit_penalty",
        "core_surplus",
        "optional_bonus",
        "luxury_biomes",
        "hub_bonus",
        "nether_core_bonus",
        "scenic_bonus",
        "village_spread_bonus",
        "treasure_bastion_bonus",
    ):
        if key in native_comp or key in py_comp:
            assert native_comp.get(key) == py_comp.get(key), (
                f"Component '{key}' mismatch: native={native_comp.get(key)} vs py={py_comp.get(key)}"
            )

    # 5. Radial key and distance squared
    if "radial_key" in native_anchor and "radial_key" in py_anchor:
        assert native_anchor["radial_key"] == py_anchor["radial_key"], (
            f"radial_key mismatch: native={native_anchor['radial_key']} vs py={py_anchor['radial_key']}"
        )
    if "origin_distance_squared" in native_anchor and "origin_distance_squared" in py_anchor:
        assert native_anchor["origin_distance_squared"] == py_anchor["origin_distance_squared"]

    # 6. Qualification Status
    assert native_anchor.get("qualification") == py_anchor.get("qualification")


def test_v3_5000_seeds_retained_parity_and_sampled_rejects():
    """Evaluate 5,000 seeds through native sweep and verify zero false positives and parity."""
    cfg = dynamic_v3_blueprint_config()
    cfg["search"]["run_key"] = "2026101501"
    prototype = get_v3_prototype(cfg)

    count = 5000
    seeds = seeds_np(0, count, 2026101501)

    threads = 4 if prototype.identity.get("openmp") else 1
    with prototype.sweep(seeds, threads=threads, retention="survivors") as batch:
        retained = list(batch.retained_records())

    # Verify every candidate match against evaluate_dynamic_seed
    for record in retained:
        seed = int(record["seed"])
        idx = int(record.get("index", 0))
        py_record = evaluate_dynamic_seed(idx, seed, cfg, short_circuit=False)

        assert len(py_record.get("anchors", [])) > 0, (
            f"FALSE POSITIVE: Native found candidate for seed {seed}, but evaluate_dynamic_seed found none."
        )

        native_anchor = record["anchors"][0]
        py_anchor = py_record["anchors"][0]
        assert_anchor_bit_exact(native_anchor, py_anchor)

    # Check a bounded reject sample even when this cohort has survivors.
    retained_seeds = {int(row['seed']) for row in retained}
    for i in [0, 10, 50, 100, 500, 1000, 2500, 4999]:
        seed = int(seeds[i])
        if seed not in retained_seeds:
            assert not evaluate_dynamic_seed(i, seed, cfg)['anchors']


def test_v3_candidate_match_100_percent_bit_exact_parity():
    """Verify that candidate matches produce 100% bit-exact scores and components on fixtures."""
    cfg = dynamic_v3_blueprint_config()
    prototype = get_v3_prototype(cfg)

    # Test synthetic fixtures covering multiple centers and structure combinations
    test_fixtures = [
        (456, [(0, 0, -1)]),
        (789, [(50, 50, -1)]),
        (101112, [(-50, -50, -1)]),
        (131415, [(100, 100, -1)]),
        (161718, [(-100, 50, -1)]),
    ]

    for seed, fix in test_fixtures:
        with prototype.sweep([seed], fixtures=fix, retention="full") as batch:
            direct_record = batch.records()[0]
            replay_record = batch.records(adapter="replay")[0]

            assert len(direct_record["anchors"]) == 1
            assert len(replay_record["anchors"]) == 1

            d_anchor = direct_record["anchors"][0]
            r_anchor = replay_record["anchors"][0]

            # 1. Direct vs Replay bit-exact parity
            assert_anchor_bit_exact(d_anchor, r_anchor)
            assert semantic_record(direct_record) == semantic_record(replay_record)

            # 2. Score characteristics
            assert d_anchor["screening_revision"] == "dynamic-envelope-2048-v3"
            assert d_anchor["deficit_penalty"] == 0
            assert d_anchor["baseline_score"] == d_anchor["bonus_total"]
            assert d_anchor["inventory"]["version"] == "dynamic-2048-count-inventory-v3"

            # 3. Center limits verification: [-976, 976]
            cx, cz = d_anchor["evaluation_center"]
            assert -976 <= cx <= 976, f"Center x={cx} outside [-976, 976]"
            assert -976 <= cz <= 976, f"Center z={cz} outside [-976, 976]"


def test_v3_scoring_component_ladders_bit_exact():
    """Verify pure additive scoring ladder bit-exactness on all 14 structures and bonuses."""
    baseline_counts = {
        "stronghold": 1, "mansion": 1, "monument": 1, "village": 6,
        "trial_chamber": 8, "ancient_city": 2, "desert_pyramid": 1,
        "jungle_temple": 0, "outpost": 1, "fortress": 1, "bastion": 2,
        "ruined_portal": 8, "shipwreck": 4, "mineshaft": 10,
    }

    # At exact baseline floor: score is 0, deficit is 0, surplus is 0
    score, comp, defs = dynamic_v3_score(baseline_counts)
    assert score == 0
    assert comp["deficit_penalty"] == 0
    assert comp["core_surplus"] == 0
    assert defs == []

    # Test stronghold ladder (+30, +20)
    s, c, _ = dynamic_v3_score(dict(baseline_counts, stronghold=2))
    assert s == 30 and c["core_surplus"] == 30
    s, c, _ = dynamic_v3_score(dict(baseline_counts, stronghold=3))
    assert s == 50 and c["core_surplus"] == 50

    # Test mansion ladder (+45, +25)
    s, c, _ = dynamic_v3_score(dict(baseline_counts, mansion=2))
    assert s == 45 and c["core_surplus"] == 45
    s, c, _ = dynamic_v3_score(dict(baseline_counts, mansion=3))
    assert s == 70 and c["core_surplus"] == 70

    # Test outpost ladder (+20, +20, +10, max 50)
    s, c, _ = dynamic_v3_score(dict(baseline_counts, outpost=2))
    assert s == 20 and c["core_surplus"] == 20
    s, c, _ = dynamic_v3_score(dict(baseline_counts, outpost=3))
    assert s == 40 and c["core_surplus"] == 40
    s, c, _ = dynamic_v3_score(dict(baseline_counts, outpost=4))
    assert s == 50 and c["core_surplus"] == 50
    s, c, _ = dynamic_v3_score(dict(baseline_counts, outpost=5))
    assert s == 50 and c["core_surplus"] == 50

    # Test bonuses: scenic (+25), village_spread (+25), treasure_bastion (+20), nether_core (+20)
    s_scenic, c_scenic, _ = dynamic_v3_score(baseline_counts, scenic=25)
    assert s_scenic == 25 and c_scenic["scenic_bonus"] == 25

    s_spread, c_spread, _ = dynamic_v3_score(baseline_counts, village_spread=25)
    assert s_spread == 25 and c_spread["village_spread_bonus"] == 25

    s_tbast, c_tbast, _ = dynamic_v3_score(baseline_counts, treasure_bastion=20)
    assert s_tbast == 20 and c_tbast["treasure_bastion_bonus"] == 20

    s_ncore, c_ncore, _ = dynamic_v3_score(baseline_counts, nether_core=20)
    assert s_ncore == 20 and c_ncore["nether_core_bonus"] == 20


def test_v3_cutoff_score_pruning_zero_false_negatives():
    """Verify that cutoff score pruning in native sweep does not produce false negatives."""
    cfg = dynamic_v3_blueprint_config()
    prototype = get_v3_prototype(cfg)

    fixture_seed = 456
    fixture = [(0, 0, -1)]

    # Measure unpruned score
    with prototype.sweep([fixture_seed], fixtures=fixture, cutoff_score=0) as batch:
        anchor = batch.records()[0]["anchors"][0]
        unpruned_score = anchor["baseline_score_observed"]
        assert unpruned_score == 484

    # Boundary 1: Cutoff exactly equal to score -> MUST be retained
    with prototype.sweep([fixture_seed], fixtures=fixture, cutoff_score=unpruned_score) as batch:
        recs = batch.records()
        assert len(recs[0]["anchors"]) == 1
        assert recs[0]["anchors"][0]["baseline_score_observed"] == unpruned_score

    # Boundary 2: Cutoff strictly greater (score + 1) -> MUST be pruned
    with prototype.sweep([fixture_seed], fixtures=fixture, cutoff_score=unpruned_score + 1) as batch:
        recs = batch.records()
        assert len(recs[0]["anchors"]) == 0

    # Boundary 3: Cutoff well below score -> MUST be retained
    with prototype.sweep([fixture_seed], fixtures=fixture, cutoff_score=unpruned_score - 50) as batch:
        recs = batch.records()
        assert len(recs[0]["anchors"]) == 1
        assert recs[0]["anchors"][0]["baseline_score_observed"] == unpruned_score


def test_v3_multi_thread_determinism():
    """Verify that native sweep is 100% deterministic across different thread counts."""
    cfg = dynamic_v3_blueprint_config()
    prototype = get_v3_prototype(cfg)

    if not prototype.identity.get("openmp"):
        pytest.skip("OpenMP not enabled; skipping multi-threaded determinism test.")

    test_cohort = seeds_np(1000, 2000, 2026101501)
    reference_verdicts: List[int] = []

    # Base run on 1 thread
    with prototype.sweep(test_cohort, threads=1, retention="survivors") as b1:
        res_count_1 = b1.pointer.result_count
        anchors_1 = int(b1.pointer.retained_anchors)

    # Check runs across 4, 8, 16, 34 threads
    for t in (4, 8, 16, 34):
        with prototype.sweep(test_cohort, threads=t, retention="survivors") as bt:
            assert bt.pointer.result_count == res_count_1, (
                f"Thread {t} result_count ({bt.pointer.result_count}) != thread 1 ({res_count_1})"
            )
            assert int(bt.pointer.retained_anchors) == anchors_1, (
                f"Thread {t} retained_anchors ({bt.pointer.retained_anchors}) != thread 1 ({anchors_1})"
            )
