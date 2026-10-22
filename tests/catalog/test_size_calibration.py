"""Tests for catalog size threshold calibration fitter.

Verifies pure Python calibration component according to CALIBRATION_FITTER_INTERFACES.md:
- Hand-computable CDF and tie-breaking cases
- Zero variance baseline mean-shift fallback
- Strict input validation and error rejection
- Original 2048 thresholds exact preservation
- Held-out data isolation (no leakage/poisoning)
- Strict tier monotonicity and size monotonicity
- Sparse tier preservation policy
- Floor 0 and Floor 1 preservation
- map_count baseline equivalent mapping, clamping, and monotonicity
"""

import math
import pytest

from seed_search.catalog.calibration import fit, map_count, REVISION, SIZES


def _make_world_id(index: int) -> str:
    """Generate deterministic 64-char hex SHA string."""
    return f"{index:064x}"


def test_hand_computed_cdf_and_affine_tie_breaker():
    """Verify hand-computable CDF plateau and affine reference tie-breaking."""
    # 10 development rows
    # 2048 counts: five 1s, five 10s. Mean = 5.5, Var = 20.25, Std = 4.5
    # Tier T=5: 5 worlds have count >= 5 (tail p = 5/10 = 0.5)
    # 4096 counts: [2, 2, 2, 2, 8, 8, 12, 12, 12, 12]
    # At 4096, k in {3..8} has 6 hits (p = 6/10, diff = 1/10)
    # k in {9..12} has 4 hits (p = 4/10, diff = 1/10)
    # Affine ref: mean_S = 7.2, std_S = sqrt(20.16) ~= 4.48999
    # R_affine = 7.2 + (5 - 5.5) * (4.48999 / 4.5) ~= 6.701
    # Closest candidate among tied integers is k=7 (|7 - 6.701| ~= 0.299 vs |6 - 6.701| ~= 0.701)
    c_2048 = [1, 1, 1, 1, 1, 10, 10, 10, 10, 10]
    c_4096 = [2, 2, 2, 2, 8, 8, 12, 12, 12, 12]
    c_8192 = [x * 2 for x in c_4096]

    rows = []
    for i in range(10):
        rows.append({
            "world_id": _make_world_id(i + 1),
            "split": "development",
            "counts": {
                "2048": {"feat_a": c_2048[i]},
                "4096": {"feat_a": c_4096[i]},
                "8192": {"feat_a": c_8192[i]},
            },
        })

    schedules = {
        "feat_a": {"floor": 1, "levels": [1, 5, 10]},
    }

    result = fit(rows, schedules)
    assert result["revision"] == REVISION

    # 2048 preserved exactly
    assert result["sizes"]["2048"]["feat_a"]["thresholds"] == [1, 5, 10]

    # At 4096:
    # Tier 0 (floor 1) stays 1
    # Tier 1 (T=5) ties broken by affine reference -> 7
    thresh_4096 = result["sizes"]["4096"]["feat_a"]["thresholds"]
    assert thresh_4096[0] == 1
    assert thresh_4096[1] == 7
    assert thresh_4096[2] >= 10


def test_zero_variance_baseline_mean_shift():
    """Verify that zero baseline variance uses mean shift and flags diagnostic."""
    # All 2048 counts are identical (variance 0)
    rows = []
    for i in range(6):
        rows.append({
            "world_id": _make_world_id(i + 1),
            "split": "development",
            "counts": {
                "2048": {"monument": 3},
                "4096": {"monument": 6 + i},
                "8192": {"monument": 12 + i * 2},
            },
        })

    schedules = {
        "monument": {"floor": 3, "levels": [3, 5]},
    }

    result = fit(rows, schedules)
    diag_2048 = result["diagnostics"]["2048"]["monument"]
    diag_4096 = result["diagnostics"]["4096"]["monument"]

    # Zero variance flag must be True
    assert diag_2048[0]["zero_variance"] is True
    assert diag_4096[0]["zero_variance"] is True


def test_sparse_tier_preservation():
    """Verify sparse tier policy: when both baseline and larger hit original tier < 5 times, preserve tier."""
    # 10 development rows, only 2 rows have count >= 8 at 2048 and 3 rows have count >= 8 at 4096
    rows = []
    for i in range(10):
        rows.append({
            "world_id": _make_world_id(i + 1),
            "split": "development",
            "counts": {
                "2048": {"outpost": 8 if i < 2 else 1},
                "4096": {"outpost": 8 if i < 3 else 2},
                "8192": {"outpost": 10 if i < 3 else 3},
            },
        })

    schedules = {
        "outpost": {"floor": 1, "levels": [1, 8]},
    }

    result = fit(rows, schedules)
    # Tier 8 has 2 hits at 2048 (<5) and 3 hits at 4096 (<5) -> sparse preserved
    thresh_4096 = result["sizes"]["4096"]["outpost"]["thresholds"]
    assert thresh_4096[1] == 8
    diag_4096 = result["diagnostics"]["4096"]["outpost"]
    assert diag_4096[1]["sparse"] is True
    assert diag_4096[1]["fit_method"] == "sparse_preserved"


def test_held_out_data_isolation():
    """Verify held-out rows do NOT affect fitted thresholds, but are measured in diagnostics."""
    rows_clean = []
    # 8 development rows
    for i in range(8):
        rows_clean.append({
            "world_id": _make_world_id(i + 1),
            "split": "development",
            "counts": {
                "2048": {"mansion": i},
                "4096": {"mansion": i * 2},
                "8192": {"mansion": i * 4},
            },
        })
    # 4 held-out rows
    for i in range(8, 12):
        rows_clean.append({
            "world_id": _make_world_id(i + 1),
            "split": "held_out",
            "counts": {
                "2048": {"mansion": 2},
                "4096": {"mansion": 4},
                "8192": {"mansion": 8},
            },
        })

    schedules = {"mansion": {"floor": 0, "levels": [0, 2, 5]}}

    res1 = fit(rows_clean, schedules)

    # Poison held-out rows with extreme counts
    rows_poisoned = [dict(r) for r in rows_clean[:8]]
    for i in range(8, 12):
        rows_poisoned.append({
            "world_id": _make_world_id(i + 1),
            "split": "held_out",
            "counts": {
                "2048": {"mansion": 200000},
                "4096": {"mansion": 200000},
                "8192": {"mansion": 200000},
            },
        })

    res2 = fit(rows_poisoned, schedules)

    # Thresholds must be strictly identical
    for s in SIZES:
        assert res1["sizes"][s]["mansion"]["thresholds"] == res2["sizes"][s]["mansion"]["thresholds"]

    # Diagnostics should reflect changed held_out hits
    assert res1["diagnostics"]["n_held_out"] == 4
    assert res2["diagnostics"]["n_held_out"] == 4
    assert res2["diagnostics"]["4096"]["mansion"][1]["held_hits"] == 4


def test_floors_and_monotonicity():
    """Verify optional floor 0, hard presence floor 1, and strict count/size monotonicity."""
    rows = []
    for i in range(15):
        rows.append({
            "world_id": _make_world_id(i + 1),
            "split": "development",
            "counts": {
                "2048": {"opt": i % 4, "req": 1 + i},
                "4096": {"opt": (i % 4) * 2, "req": 2 + i * 2},
                "8192": {"opt": (i % 4) * 3, "req": 3 + i * 3},
            },
        })

    schedules = {
        "opt": {"floor": 0, "levels": [0, 2, 4]},
        "req": {"floor": 1, "levels": [1, 5, 12]},
    }

    res = fit(rows, schedules)

    # Floor 0 stays 0 at all sizes
    for s in SIZES:
        assert res["sizes"][s]["opt"]["thresholds"][0] == 0

    # Floor 1 stays 1 at all sizes
    for s in SIZES:
        assert res["sizes"][s]["req"]["thresholds"][0] == 1

    # Monotonicity checks
    for feat in ("opt", "req"):
        t2048 = res["sizes"]["2048"][feat]["thresholds"]
        t4096 = res["sizes"]["4096"][feat]["thresholds"]
        t8192 = res["sizes"]["8192"][feat]["thresholds"]

        # Tier monotonicity (strictly increasing at each size)
        for t_list in (t2048, t4096, t8192):
            for i in range(len(t_list) - 1):
                assert t_list[i] < t_list[i + 1], f"Tier violation in {t_list}"

        # Size monotonicity (thresholds non-decreasing across sizes)
        for i in range(len(t2048)):
            assert t2048[i] <= t4096[i] <= t8192[i], f"Size violation at tier {i}: {t2048[i]}, {t4096[i]}, {t8192[i]}"


def test_input_validations_and_error_handling():
    """Verify rejection of malformed schedules, invalid counts, missing sizes/features, booleans, and splits."""
    valid_row = {
        "world_id": _make_world_id(1),
        "split": "development",
        "counts": {
            "2048": {"f": 1},
            "4096": {"f": 2},
            "8192": {"f": 4},
        },
    }
    valid_sched = {"f": {"floor": 1, "levels": [1, 3]}}

    # Empty rows
    with pytest.raises(ValueError, match="rows cannot be empty"):
        fit([], valid_sched)

    # Empty schedules
    with pytest.raises(ValueError, match="schedules cannot be empty"):
        fit([valid_row], {})

    # Duplicate world IDs
    with pytest.raises(ValueError, match="Duplicate world ID"):
        fit([valid_row, valid_row], valid_sched)

    # Unknown split
    bad_split = dict(valid_row, world_id=_make_world_id(2), split="eval")
    with pytest.raises(ValueError, match="unknown split"):
        fit([bad_split], valid_sched)

    # No development rows
    held_only = dict(valid_row, split="held_out")
    with pytest.raises(ValueError, match="No development rows"):
        fit([held_only], valid_sched)

    # Missing size
    bad_sizes = {
        "world_id": _make_world_id(1),
        "split": "development",
        "counts": {"2048": {"f": 1}, "4096": {"f": 2}},
    }
    with pytest.raises(ValueError, match="missing size '8192'"):
        fit([bad_sizes], valid_sched)

    # Missing feature
    bad_feat = {
        "world_id": _make_world_id(1),
        "split": "development",
        "counts": {"2048": {}, "4096": {"f": 2}, "8192": {"f": 4}},
    }
    with pytest.raises(ValueError, match="missing feature 'f'"):
        fit([bad_feat], valid_sched)

    # Boolean count rejection (bool is subclass of int)
    bad_bool = {
        "world_id": _make_world_id(1),
        "split": "development",
        "counts": {"2048": {"f": True}, "4096": {"f": 2}, "8192": {"f": 4}},
    }
    with pytest.raises(ValueError, match="count must be an integer"):
        fit([bad_bool], valid_sched)

    # Negative count
    bad_neg = {
        "world_id": _make_world_id(1),
        "split": "development",
        "counts": {"2048": {"f": -1}, "4096": {"f": 2}, "8192": {"f": 4}},
    }
    with pytest.raises(ValueError, match="out of bounds"):
        fit([bad_neg], valid_sched)

    # Count exceeding bound 200000
    bad_overflow = {
        "world_id": _make_world_id(1),
        "split": "development",
        "counts": {"2048": {"f": 200001}, "4096": {"f": 2}, "8192": {"f": 4}},
    }
    with pytest.raises(ValueError, match="out of bounds"):
        fit([bad_overflow], valid_sched)

    # Malformed schedule: first level != floor
    with pytest.raises(ValueError, match="must equal floor"):
        fit([valid_row], {"f": {"floor": 1, "levels": [2, 4]}})

    # Malformed schedule: not strictly increasing
    with pytest.raises(ValueError, match="strictly increasing"):
        fit([valid_row], {"f": {"floor": 1, "levels": [1, 1, 3]}})


def test_map_count():
    """Verify map_count baseline equivalent integer count mapping, below floor, and capping."""
    entry = {
        "base_levels": [1, 5, 10],
        "thresholds": [1, 8, 16],
    }

    # Below threshold floor -> max(0, base_floor - 1) = 0
    assert map_count(0, entry) == 0

    # Exactly at thresholds
    assert map_count(1, entry) == 1
    assert map_count(8, entry) == 5
    assert map_count(16, entry) == 10

    # In between
    assert map_count(4, entry) == 1
    assert map_count(7, entry) == 1
    assert map_count(9, entry) == 5
    assert map_count(15, entry) == 5

    # Capped to last tier
    assert map_count(20, entry) == 10
    assert map_count(1000, entry) == 10

    # Optional feature with floor 0
    entry_opt = {
        "base_levels": [0, 3, 6],
        "thresholds": [0, 5, 11],
    }
    assert map_count(0, entry_opt) == 0
    assert map_count(4, entry_opt) == 0
    assert map_count(5, entry_opt) == 3
    assert map_count(10, entry_opt) == 3
    assert map_count(11, entry_opt) == 6

    # Validation errors
    with pytest.raises(ValueError, match="count must be an integer"):
        map_count(True, entry)
    with pytest.raises(ValueError, match="count must be non-negative"):
        map_count(-1, entry)
    with pytest.raises(ValueError, match="entry must contain"):
        map_count(5, {"base_levels": [1]})


def test_map_rejects_unordered_or_noninteger_thresholds():
    for entry in ({'base_levels':[0,1], 'thresholds':[0,False]},
                  {'base_levels':[0,1], 'thresholds':[0,0]},
                  {'base_levels':[1,2], 'thresholds':[0,2]}):
        with pytest.raises(ValueError):
            map_count(1,entry)


def test_fast_plateau_search_matches_exhaustive_candidates():
    from fractions import Fraction
    from seed_search.catalog.calibration import _find_best_threshold
    counts=[0,0,3500,3500,7000,8000]
    for probability in (Fraction(1,6),Fraction(1,2),Fraction(2,3)):
        for reference in (22.3,4200.25,9500.0):
            expected=min(range(2,8002),key=lambda k:(abs(Fraction(sum(n>=k for n in counts),6)-probability),abs(k-reference),k))
            assert _find_best_threshold(counts,6,probability,reference,2,8001)==expected
