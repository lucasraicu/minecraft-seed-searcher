"""Catalog size threshold calibration fitter.

Pure Python, deterministic component for fitting size-scaled integer thresholds
for Overworld count features across world sizes (2048, 4096, 8192).
Conforms to docs/catalog/v2/CALIBRATION_FITTER_INTERFACES.md.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from fractions import Fraction
import math
import re
from typing import Any, Dict, List, Optional, Tuple

REVISION = "catalog-size-thresholds-v1"
SIZES: Tuple[str, ...] = ("2048", "4096", "8192")
MAX_COUNT = 200000
MAX_COHORT = 2000
MAX_FEATURES = 32
MAX_TIERS = 32
SPARSE_HIT_THRESHOLD = 5


def _validate_inputs(rows: Any, schedules: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Validate input rows and schedules according to CALIBRATION_FITTER_INTERFACES.md."""
    if not isinstance(rows, (list, tuple)):
        raise TypeError("rows must be a list or tuple")
    if len(rows) == 0:
        raise ValueError("rows cannot be empty")
    if len(rows) > MAX_COHORT:
        raise ValueError(f"Cohort size {len(rows)} exceeds maximum {MAX_COHORT}")

    if not isinstance(schedules, dict):
        raise TypeError("schedules must be a dict")
    if len(schedules) == 0:
        raise ValueError("schedules cannot be empty")
    if len(schedules) > MAX_FEATURES:
        raise ValueError(f"Features count {len(schedules)} exceeds maximum {MAX_FEATURES}")

    # Validate schedules
    for feat, sched in schedules.items():
        if not isinstance(feat, str) or not feat:
            raise ValueError(f"Invalid feature name: {feat!r}")
        if not isinstance(sched, dict):
            raise ValueError(f"Schedule for {feat} must be a dict")
        if "floor" not in sched or "levels" not in sched:
            raise ValueError(f"Malformed schedule for {feat}: missing 'floor' or 'levels'")

        floor = sched["floor"]
        if isinstance(floor, bool) or not isinstance(floor, int):
            raise ValueError(f"Floor for {feat} must be an integer, got {floor!r}")
        if floor < 0 or floor > MAX_COUNT:
            raise ValueError(f"Floor for {feat} out of bounds [0, {MAX_COUNT}]: {floor}")

        levels = sched["levels"]
        if not isinstance(levels, (list, tuple)):
            raise ValueError(f"Levels for {feat} must be a list or tuple, got {levels!r}")
        if len(levels) == 0 or len(levels) > MAX_TIERS:
            raise ValueError(f"Levels count for {feat} must be between 1 and {MAX_TIERS}, got {len(levels)}")
        if levels[0] != floor:
            raise ValueError(f"First level {levels[0]} for {feat} must equal floor {floor}")

        prev = None
        for lvl in levels:
            if isinstance(lvl, bool) or not isinstance(lvl, int):
                raise ValueError(f"Level for {feat} must be an integer, got {lvl!r}")
            if lvl < 0 or lvl > MAX_COUNT:
                raise ValueError(f"Level for {feat} out of bounds [0, {MAX_COUNT}]: {lvl}")
            if prev is not None and lvl <= prev:
                raise ValueError(f"Levels for {feat} must be strictly increasing: {levels}")
            prev = lvl

    seen_world_ids = set()
    dev_rows: List[Dict[str, Any]] = []
    held_rows: List[Dict[str, Any]] = []

    for r_idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TypeError(f"Row {r_idx} must be a dict, got {type(row).__name__}")

        world_id = row.get("world_id")
        if not isinstance(world_id, str) or not re.fullmatch(r"[0-9a-f]{64}", world_id):
            raise ValueError(f"Row {r_idx} invalid or missing world_id: {world_id!r}")
        if world_id in seen_world_ids:
            raise ValueError(f"Duplicate world ID: {world_id}")
        seen_world_ids.add(world_id)

        split = row.get("split")
        if split not in ("development", "held_out"):
            raise ValueError(f"Row {world_id} unknown split: {split!r}")

        counts = row.get("counts")
        if not isinstance(counts, dict):
            raise ValueError(f"Row {world_id} counts must be a dict")

        for s in SIZES:
            if s not in counts:
                raise ValueError(f"Row {world_id} missing size '{s}'")
            size_counts = counts[s]
            if not isinstance(size_counts, dict):
                raise ValueError(f"Row {world_id} size '{s}' counts must be a dict")

            for feat in schedules:
                if feat not in size_counts:
                    raise ValueError(f"Row {world_id} size '{s}' missing feature '{feat}'")
                cnt = size_counts[feat]
                if isinstance(cnt, bool) or not isinstance(cnt, int):
                    raise ValueError(f"Row {world_id} size '{s}' feature '{feat}' count must be an integer, got {cnt!r}")
                if cnt < 0 or cnt > MAX_COUNT:
                    raise ValueError(f"Row {world_id} size '{s}' feature '{feat}' count out of bounds [0, {MAX_COUNT}]: {cnt}")

        if split == "development":
            dev_rows.append(row)
        else:
            held_rows.append(row)

    if len(dev_rows) == 0:
        raise ValueError("No development rows found")

    return dev_rows, held_rows


def _find_best_threshold(
    counts_S_sorted: List[int],
    n_dev: int,
    target_p: Fraction,
    r_affine: float,
    lower_bound: int,
    cand_max: int,
) -> int:
    """Find candidate integer k >= lower_bound that minimizes empirical tail probability diff.

    Ties broken by closest distance to r_affine, then smallest k.
    Uses bounded CDF plateau candidates avoiding quadratic per-count loops.
    """
    if lower_bound >= cand_max:
        return lower_bound

    span = cand_max - lower_bound
    if span <= 2000:
        candidate_set = set(range(lower_bound, cand_max + 1))
    else:
        candidate_set = {lower_bound, cand_max}
        r_floor = int(math.floor(r_affine))
        r_ceil = int(math.ceil(r_affine))
        if lower_bound <= r_floor <= cand_max:
            candidate_set.add(r_floor)
        if lower_bound <= r_ceil <= cand_max:
            candidate_set.add(r_ceil)

        unique_counts = sorted(set(counts_S_sorted))
        for u in unique_counts:
            for k in (u, u + 1):
                if lower_bound <= k <= cand_max:
                    candidate_set.add(k)

    best_k = lower_bound
    best_p_diff: Optional[Fraction] = None
    best_affine_diff: float = float("inf")

    for k in sorted(candidate_set):
        hits_k = n_dev - bisect_left(counts_S_sorted, k)
        tail_p = Fraction(hits_k, n_dev)
        p_diff = abs(tail_p - target_p)
        affine_diff = abs(k - r_affine)

        if best_p_diff is None or p_diff < best_p_diff:
            best_p_diff = p_diff
            best_affine_diff = affine_diff
            best_k = k
        elif p_diff == best_p_diff:
            if affine_diff < best_affine_diff:
                best_affine_diff = affine_diff
                best_k = k
            elif affine_diff == best_affine_diff and k < best_k:
                best_k = k

    return best_k


def fit(rows: Any, schedules: Any) -> Dict[str, Any]:
    """Fit size-scaled count thresholds from development rows.

    Parameters:
        rows: List of dicts matching CALIBRATION_FITTER_INTERFACES.md.
        schedules: Mapping feature -> {'floor': int, 'levels': list[int]}.

    Returns:
        Dict with 'revision', 'sizes', and 'diagnostics'.
    """
    dev_rows, held_rows = _validate_inputs(rows, schedules)
    n_dev = len(dev_rows)
    n_held = len(held_rows)

    sizes_result: Dict[str, Dict[str, Dict[str, Any]]] = {s: {} for s in SIZES}
    diagnostics_by_size: Dict[str, Dict[str, List[Dict[str, Any]]]] = {s: {} for s in SIZES}

    for feat, sched in schedules.items():
        base_levels = list(sched["levels"])
        m_tiers = len(base_levels)

        # Baseline 2048 is preserved EXACTLY
        thresholds_2048 = list(base_levels)
        sizes_result["2048"][feat] = {
            "base_levels": base_levels,
            "thresholds": thresholds_2048,
        }

        counts_2048 = [r["counts"]["2048"][feat] for r in dev_rows]
        mean_2048 = sum(counts_2048) / n_dev
        var_2048 = sum((x - mean_2048) ** 2 for x in counts_2048) / n_dev
        std_2048 = math.sqrt(var_2048)
        zero_variance = (var_2048 == 0.0)

        held_counts_2048 = [r["counts"]["2048"][feat] for r in held_rows] if n_held > 0 else []

        diag_2048 = []
        for t_idx, t_val in enumerate(thresholds_2048):
            d_hits = sum(1 for x in counts_2048 if x >= t_val)
            h_hits = sum(1 for x in held_counts_2048 if x >= t_val) if n_held > 0 else 0
            diag_2048.append({
                "tier": t_val,
                "threshold": t_val,
                "dev_hits": d_hits,
                "dev_n": n_dev,
                "held_hits": h_hits,
                "held_n": n_held,
                "fit_method": "identity",
                "sparse": d_hits < SPARSE_HIT_THRESHOLD,
                "zero_variance": zero_variance,
            })
        diagnostics_by_size["2048"][feat] = diag_2048

        # Fit larger sizes in order
        prev_size = "2048"
        for s in ("4096", "8192"):
            fitted_thresholds: List[int] = []
            diag_s: List[Dict[str, Any]] = []

            counts_S = [r["counts"][s][feat] for r in dev_rows]
            counts_S_sorted = sorted(counts_S)
            mean_S = sum(counts_S) / n_dev
            var_S = sum((x - mean_S) ** 2 for x in counts_S) / n_dev
            std_S = math.sqrt(var_S)

            held_counts_S = [r["counts"][s][feat] for r in held_rows] if n_held > 0 else []
            max_observed_larger = counts_S_sorted[-1] if counts_S_sorted else 0

            for i in range(m_tiers):
                t_val = base_levels[i]
                prev_size_thresh = sizes_result[prev_size][feat]["thresholds"][i]
                preceding_thresh = fitted_thresholds[i - 1] if i > 0 else None

                if i == 0:
                    lower_bound = max(t_val, prev_size_thresh)
                else:
                    assert preceding_thresh is not None
                    lower_bound = max(t_val, prev_size_thresh, preceding_thresh + 1)

                hits_2048_T = sum(1 for x in counts_2048 if x >= t_val)
                hits_S_T = sum(1 for x in counts_S if x >= t_val)

                # Special cases: optional floor 0 and hard presence floor 1
                if i == 0 and t_val == 0:
                    k = 0
                    fit_method = "floor_0"
                    sparse_flag = False
                elif i == 0 and t_val == 1:
                    k = 1
                    fit_method = "floor_1"
                    sparse_flag = False
                elif hits_2048_T < SPARSE_HIT_THRESHOLD and hits_S_T < SPARSE_HIT_THRESHOLD:
                    # Sparse tier policy: preserve tier unless monotonicity forces it up
                    k = max(t_val, lower_bound)
                    fit_method = "sparse_preserved"
                    sparse_flag = True
                else:
                    # Adapting count tier via empirical tail probability matching
                    target_p = Fraction(hits_2048_T, n_dev)
                    if zero_variance:
                        r_affine = mean_S + (t_val - mean_2048)
                    else:
                        r_affine = mean_S + (t_val - mean_2048) * (std_S / std_2048)

                    cand_max = max(lower_bound, max_observed_larger + 1)
                    k = _find_best_threshold(
                        counts_S_sorted=counts_S_sorted,
                        n_dev=n_dev,
                        target_p=target_p,
                        r_affine=r_affine,
                        lower_bound=lower_bound,
                        cand_max=cand_max,
                    )
                    fit_method = "tail_probability"
                    sparse_flag = False

                fitted_thresholds.append(k)

                d_hits = sum(1 for x in counts_S if x >= k)
                h_hits = sum(1 for x in held_counts_S if x >= k) if n_held > 0 else 0
                diag_s.append({
                    "tier": t_val,
                    "threshold": k,
                    "dev_hits": d_hits,
                    "dev_n": n_dev,
                    "held_hits": h_hits,
                    "held_n": n_held,
                    "fit_method": fit_method,
                    "sparse": sparse_flag,
                    "zero_variance": zero_variance,
                })

            sizes_result[s][feat] = {
                "base_levels": base_levels,
                "thresholds": fitted_thresholds,
            }
            diagnostics_by_size[s][feat] = diag_s
            prev_size = s

    diagnostics = {
        "sizes": diagnostics_by_size,
        "2048": diagnostics_by_size["2048"],
        "4096": diagnostics_by_size["4096"],
        "8192": diagnostics_by_size["8192"],
        "n_development": n_dev,
        "n_held_out": n_held,
    }

    return {
        "revision": REVISION,
        "sizes": sizes_result,
        "diagnostics": diagnostics,
    }


def map_count(count: int, entry: Dict[str, Any]) -> int:
    """Map observed count at a fitted size to baseline equivalent count for dynamic_v3_score.

    Parameters:
        count: Observed non-negative integer count.
        entry: Dict with 'base_levels' and 'thresholds'.

    Returns:
        Baseline equivalent integer count. Below threshold floor returns max(0, base_floor - 1).
        Otherwise returns highest base level whose threshold was reached.
    """
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError(f"count must be an integer, got {count!r}")
    if count < 0:
        raise ValueError(f"count must be non-negative, got {count}")
    if not isinstance(entry, dict):
        raise TypeError(f"entry must be a dict, got {type(entry).__name__}")
    if "base_levels" not in entry or "thresholds" not in entry:
        raise ValueError("entry must contain 'base_levels' and 'thresholds'")

    base_levels = entry["base_levels"]
    thresholds = entry["thresholds"]
    if not isinstance(base_levels, (list, tuple)) or not isinstance(thresholds, (list, tuple)):
        raise TypeError("base_levels and thresholds must be lists or tuples")
    if len(base_levels) == 0 or len(base_levels) != len(thresholds):
        raise ValueError("base_levels and thresholds must be non-empty and of equal length")

    for values in (base_levels, thresholds):
        if len(values) > MAX_TIERS or any(type(v) is not int or not 0 <= v <= MAX_COUNT + MAX_TIERS for v in values):
            raise ValueError("Invalid calibrated count levels")
        if any(a >= b for a,b in zip(values, values[1:])):
            raise ValueError("Calibrated count levels must increase")
    if any(t < b for b,t in zip(base_levels, thresholds)):
        raise ValueError("Calibrated thresholds cannot weaken baseline tiers")
    threshold_floor = thresholds[0]
    base_floor = base_levels[0]

    if count < threshold_floor:
        return max(0, base_floor - 1)

    idx = bisect_right(thresholds, count) - 1
    return base_levels[idx]
