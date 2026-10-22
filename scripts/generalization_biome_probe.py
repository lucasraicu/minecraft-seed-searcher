"""Generalization biome audit probe helper.

Pure standard-library analysis comparing predicted biomes against observed
biomes at identical coordinates. Implements exact INTERFACES.md specification.
"""

from __future__ import annotations

import collections.abc
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

INT32_MIN = -2147483648
INT32_MAX = 2147483647
Y_MIN = -64
Y_MAX = 319

VALID_OUTCOMES = ("match", "mismatch", "unknown", "error", "not_comparable")


def _validate_coord(val: Any, name: str, min_val: int, max_val: int) -> int:
    """Validate that val is a strict integer (not bool) within [min_val, max_val]."""
    if isinstance(val, bool) or not isinstance(val, int):
        raise ValueError(f"{name} must be a strict integer (not bool), got {type(val).__name__}")
    if not (min_val <= val <= max_val):
        raise ValueError(f"{name} {val} is outside allowed range [{min_val}, {max_val}]")
    return val


def _strip_minecraft_namespace(name: str) -> str:
    """Strip only 'minecraft:' namespace prefix from name."""
    prefix = "minecraft:"
    if name.startswith(prefix):
        return name[len(prefix):]
    return name


def _is_unknown_label(label: str) -> bool:
    """Check if label represents an Unknown_* identifier."""
    return label.startswith("Unknown_") or label.startswith("unknown_")


def compare_biomes(
    predictions: List[Dict[str, Any]],
    observations: List[Dict[str, Any]],
    *,
    aliases: Optional[Mapping[str, str]] = None,
    non_comparable: Iterable[str] = (),
) -> List[Dict[str, Any]]:
    """Compare predicted biomes against observations at exact same XYZ coordinates.

    Parameters:
        predictions: list of dicts with exact fields:
            position=[x, y, z], biome_name=str, sample_group=str
        observations: list of dicts with x, y, z and either id=str or error=str.
            Optional extra fields preserved if present but not interpreted.
        aliases: explicit string->string mapping. Namespace 'minecraft:' is stripped.
            Rejects cycles and ambiguous normalized aliases.
        non_comparable: collection of labels yielding 'not_comparable' outcome.

    Returns:
        list of dicts, each containing:
            position, sample_group, predicted_name, observed_name,
            canonical_predicted, canonical_observed, outcome, reason.
    """
    if not isinstance(predictions, list):
        raise ValueError(f"predictions must be a list, got {type(predictions).__name__}")
    if not isinstance(observations, list):
        raise ValueError(f"observations must be a list, got {type(observations).__name__}")

    # Validate predictions schema and check for duplicates
    seen_pred_xyz: set[tuple[int, int, int]] = set()
    validated_predictions: list[tuple[list[int], str, str, tuple[int, int, int]]] = []

    for idx, pred in enumerate(predictions):
        if not isinstance(pred, dict):
            raise ValueError(f"predictions[{idx}] must be a dict, got {type(pred).__name__}")
        if set(pred.keys()) != {"position", "biome_name", "sample_group"}:
            raise ValueError(
                f"predictions[{idx}] must contain exact fields ('position', 'biome_name', 'sample_group'), "
                f"got keys: {sorted(pred.keys())}"
            )

        pos = pred["position"]
        if not isinstance(pos, (list, tuple)) or len(pos) != 3:
            raise ValueError(f"predictions[{idx}]['position'] must be a 3-element list/tuple [x, y, z]")

        x = _validate_coord(pos[0], f"predictions[{idx}]['position'][0] (x)", INT32_MIN, INT32_MAX)
        y = _validate_coord(pos[1], f"predictions[{idx}]['position'][1] (y)", Y_MIN, Y_MAX)
        z = _validate_coord(pos[2], f"predictions[{idx}]['position'][2] (z)", INT32_MIN, INT32_MAX)

        biome_name = pred["biome_name"]
        if not isinstance(biome_name, str) or not biome_name.strip():
            raise ValueError(f"predictions[{idx}]['biome_name'] must be a non-empty str")

        sample_group = pred["sample_group"]
        if not isinstance(sample_group, str) or not sample_group.strip():
            raise ValueError(f"predictions[{idx}]['sample_group'] must be a non-empty str")

        xyz = (x, y, z)
        if xyz in seen_pred_xyz:
            raise ValueError(f"Duplicate XYZ in predictions: {xyz}")
        seen_pred_xyz.add(xyz)

        validated_predictions.append(([x, y, z], biome_name, sample_group, xyz))

    # Validate observations schema and check for duplicates
    seen_obs_xyz: set[tuple[int, int, int]] = set()
    obs_by_xyz: dict[tuple[int, int, int], Dict[str, Any]] = {}

    for idx, obs in enumerate(observations):
        if not isinstance(obs, dict):
            raise ValueError(f"observations[{idx}] must be a dict, got {type(obs).__name__}")

        if "x" not in obs or "y" not in obs or "z" not in obs:
            raise ValueError(f"observations[{idx}] missing required coordinate key(s) among x, y, z")

        x = _validate_coord(obs["x"], f"observations[{idx}]['x']", INT32_MIN, INT32_MAX)
        y = _validate_coord(obs["y"], f"observations[{idx}]['y']", Y_MIN, Y_MAX)
        z = _validate_coord(obs["z"], f"observations[{idx}]['z']", INT32_MIN, INT32_MAX)

        has_id = "id" in obs and obs["id"] is not None
        has_error = "error" in obs and obs["error"] is not None

        if not has_id and not has_error:
            raise ValueError(f"observations[{idx}] must have either non-null 'id' or 'error'")
        if has_id and has_error:
            raise ValueError(f"observations[{idx}] cannot have both non-null 'id' and 'error'")

        if has_id:
            if not isinstance(obs["id"], str) or not obs["id"].strip():
                raise ValueError(f"observations[{idx}]['id'] must be a non-empty str")
        if has_error:
            if not isinstance(obs["error"], str) or not obs["error"].strip():
                raise ValueError(f"observations[{idx}]['error'] must be a non-empty str")

        xyz = (x, y, z)
        if xyz in seen_obs_xyz:
            raise ValueError(f"Duplicate XYZ in observations: {xyz}")
        seen_obs_xyz.add(xyz)
        obs_by_xyz[xyz] = obs

    # Orphan observed XYZ check: all observed points must correspond to a prediction
    for xyz in seen_obs_xyz:
        if xyz not in seen_pred_xyz:
            raise ValueError(f"Orphan observed XYZ {xyz} has no corresponding prediction")

    # Validate and normalize aliases
    canonical_alias_map: dict[str, str] = {}
    if aliases is not None:
        if not isinstance(aliases, collections.abc.Mapping):
            raise ValueError(f"aliases must be a mapping, got {type(aliases).__name__}")

        normalized_aliases: dict[str, str] = {}
        for k, v in aliases.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ValueError(
                    f"aliases must map str to str, got key {type(k).__name__} and value {type(v).__name__}"
                )
            norm_k = _strip_minecraft_namespace(k)
            norm_v = _strip_minecraft_namespace(v)
            if not norm_k or not norm_v:
                raise ValueError("alias keys and values cannot be empty after namespace stripping")

            if norm_k in normalized_aliases and normalized_aliases[norm_k] != norm_v:
                raise ValueError(
                    f"Ambiguous normalized alias for '{norm_k}': '{normalized_aliases[norm_k]}' vs '{norm_v}'"
                )
            normalized_aliases[norm_k] = norm_v

        # Cycle detection and transitive deterministic alias resolution
        for start_k in normalized_aliases:
            visited: list[str] = []
            curr = start_k
            while curr in normalized_aliases:
                if curr in visited:
                    cycle_slice = visited[visited.index(curr):] + [curr]
                    raise ValueError(f"Cycle detected in aliases: {' -> '.join(cycle_slice)}")
                visited.append(curr)
                curr = normalized_aliases[curr]
            canonical_alias_map[start_k] = curr

    # Validate non_comparable collection
    non_comp_set: set[str] = set()
    if non_comparable is not None:
        if not isinstance(non_comparable, collections.abc.Iterable) or isinstance(non_comparable, (str, bytes)):
            raise ValueError(f"non_comparable must be an iterable of strings, got {type(non_comparable).__name__}")
        for item in non_comparable:
            if not isinstance(item, str):
                raise ValueError(f"non_comparable elements must be strings, got {type(item).__name__}")
            non_comp_set.add(item)
            non_comp_set.add(_strip_minecraft_namespace(item))

    # Compare row by row preserving source order
    results: list[dict[str, Any]] = []

    for pos, pred_raw, sample_group, xyz in validated_predictions:
        norm_pred = _strip_minecraft_namespace(pred_raw)
        canonical_pred = canonical_alias_map.get(norm_pred, norm_pred)

        if xyz not in obs_by_xyz:
            results.append({
                "position": list(pos),
                "sample_group": sample_group,
                "predicted_name": pred_raw,
                "observed_name": None,
                "canonical_predicted": canonical_pred,
                "canonical_observed": None,
                "outcome": "unknown",
                "reason": "missing observation",
            })
            continue

        obs = obs_by_xyz[xyz]
        if "error" in obs and obs["error"] is not None:
            results.append({
                "position": list(pos),
                "sample_group": sample_group,
                "predicted_name": pred_raw,
                "observed_name": None,
                "canonical_predicted": canonical_pred,
                "canonical_observed": None,
                "outcome": "error",
                "reason": f"observation error: {obs['error']}",
            })
            continue

        obs_raw = obs["id"]
        norm_obs = _strip_minecraft_namespace(obs_raw)
        canonical_obs = canonical_alias_map.get(norm_obs, norm_obs)

        # Check non_comparable
        if (
            pred_raw in non_comp_set
            or norm_pred in non_comp_set
            or canonical_pred in non_comp_set
            or obs_raw in non_comp_set
            or norm_obs in non_comp_set
            or canonical_obs in non_comp_set
        ):
            reasons = []
            if pred_raw in non_comp_set or norm_pred in non_comp_set or canonical_pred in non_comp_set:
                reasons.append(f"predicted '{pred_raw}' is non-comparable")
            if obs_raw in non_comp_set or norm_obs in non_comp_set or canonical_obs in non_comp_set:
                reasons.append(f"observed '{obs_raw}' is non-comparable")
            results.append({
                "position": list(pos),
                "sample_group": sample_group,
                "predicted_name": pred_raw,
                "observed_name": obs_raw,
                "canonical_predicted": canonical_pred,
                "canonical_observed": canonical_obs,
                "outcome": "not_comparable",
                "reason": "; ".join(reasons),
            })
            continue

        # Check Unknown_* labels
        if (
            _is_unknown_label(pred_raw)
            or _is_unknown_label(norm_pred)
            or _is_unknown_label(canonical_pred)
            or _is_unknown_label(obs_raw)
            or _is_unknown_label(norm_obs)
            or _is_unknown_label(canonical_obs)
        ):
            reasons = []
            if _is_unknown_label(pred_raw) or _is_unknown_label(norm_pred) or _is_unknown_label(canonical_pred):
                reasons.append(f"predicted '{pred_raw}' is unknown label")
            if _is_unknown_label(obs_raw) or _is_unknown_label(norm_obs) or _is_unknown_label(canonical_obs):
                reasons.append(f"observed '{obs_raw}' is unknown label")
            results.append({
                "position": list(pos),
                "sample_group": sample_group,
                "predicted_name": pred_raw,
                "observed_name": obs_raw,
                "canonical_predicted": canonical_pred,
                "canonical_observed": canonical_obs,
                "outcome": "unknown",
                "reason": "; ".join(reasons),
            })
            continue

        # Match vs Mismatch
        if canonical_pred == canonical_obs:
            results.append({
                "position": list(pos),
                "sample_group": sample_group,
                "predicted_name": pred_raw,
                "observed_name": obs_raw,
                "canonical_predicted": canonical_pred,
                "canonical_observed": canonical_obs,
                "outcome": "match",
                "reason": "canonical names match",
            })
        else:
            results.append({
                "position": list(pos),
                "sample_group": sample_group,
                "predicted_name": pred_raw,
                "observed_name": obs_raw,
                "canonical_predicted": canonical_pred,
                "canonical_observed": canonical_obs,
                "outcome": "mismatch",
                "reason": f"mismatch: predicted '{canonical_pred}' != observed '{canonical_obs}'",
            })

    return results


def summarize_biomes(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize comparison rows into aggregate outcome counts.

    Returns:
        dict with:
            total: count of rows
            by_group: {group: {outcome: count}}
            by_name: {canonical_predicted: {outcome: count}}
        No accuracy percentages or population conclusions.
    """
    if not isinstance(rows, list):
        raise ValueError(f"rows must be a list, got {type(rows).__name__}")

    by_group: dict[str, dict[str, int]] = {}
    by_name: dict[str, dict[str, int]] = {}

    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"rows[{idx}] must be a dict, got {type(row).__name__}")
        for key in ("sample_group", "canonical_predicted", "outcome"):
            if key not in row:
                raise ValueError(f"rows[{idx}] missing required key '{key}'")
            if not isinstance(row[key], str):
                raise ValueError(f"rows[{idx}]['{key}'] must be str, got {type(row[key]).__name__}")

        group = row["sample_group"]
        name = row["canonical_predicted"]
        outcome = row["outcome"]

        if group not in by_group:
            by_group[group] = {}
        by_group[group][outcome] = by_group[group].get(outcome, 0) + 1

        if name not in by_name:
            by_name[name] = {}
        by_name[name][outcome] = by_name[name].get(outcome, 0) + 1

    return {
        "total": len(rows),
        "by_group": by_group,
        "by_name": by_name,
    }


__all__ = ["compare_biomes", "summarize_biomes", "INT32_MIN", "INT32_MAX", "Y_MIN", "Y_MAX"]
