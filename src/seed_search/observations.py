"""Compare observations without upgrading predictions to game confirmations."""
from __future__ import annotations

import math

from .backend import STRUCTURES

NETHER_STRUCTURES = frozenset({"fortress", "bastion"})
# This limits a diagnostic read, not the allowed error for a match.
STRUCTURE_WINDOW_HALF = 256


def coordinate(value):
    if isinstance(value, bool) or not isinstance(value, int) or not -(1 << 30) <= value < (1 << 30):
        raise ValueError("Observation coordinates must be integers in the safe prototype range")
    return value


def optional_bool(value, field):
    if value is not None and not isinstance(value, bool):
        raise ValueError(f"{field} must be true, false, or null")
    return value


def border_center(data, cfg):
    center = data.get("border_center")
    if center is None:
        return None
    if not isinstance(center, list) or len(center) != 2:
        raise ValueError("border_center must be an Overworld [x, z] pair or null")
    center = tuple(coordinate(v) for v in center)
    low, high = cfg["search"]["center_axis_bounds_blocks"]
    if any(v % 8 or not low <= v <= high for v in center):
        raise ValueError("Observation border_center must be on the eight-block grid inside the center envelope")
    return center


def inside_border(position, name, center, cfg):
    if center is None or position is None:
        return None
    if name in NETHER_STRUCTURES:
        center = (center[0] // 8, center[1] // 8)
        half = cfg["deployment"]["nether_side_blocks"] // 2
    else:
        half = cfg["deployment"]["overworld_side_blocks"] // 2
    return all(abs(position[i] - center[i]) <= half for i in range(2))


def nearest_prediction(positions, actual):
    if not positions:
        return None
    nearest = min(positions, key=lambda p: ((p[0] - actual[0])**2 + (p[1] - actual[1])**2, p))
    delta = [nearest[0] - actual[0], nearest[1] - actual[1]]
    return {"position": list(nearest), "delta_xz": delta,
            "horizontal_offset_blocks": math.hypot(*delta)}


def compare_structures(backend, data, cfg):
    rows = data.get("structures", [])
    if not isinstance(rows, list) or len(rows) > 1000:
        raise ValueError("Expected at most 1,000 structure observation records")
    center = border_center(data, cfg)
    results = []
    for row in rows:
        if not isinstance(row, dict) or row.get("type") not in STRUCTURES:
            raise ValueError("Structure observations must name a supported type")
        name = row["type"]
        dimension = "nether" if name in NETHER_STRUCTURES else "overworld"
        if row.get("dimension", dimension) != dimension:
            raise ValueError(f"{name} observations require dimension {dimension}")
        generated = optional_bool(row.get("actual_generated"), "actual_generated")
        x, z = row.get("actual_x"), row.get("actual_z")
        if (x is None) != (z is None):
            raise ValueError("Provide both actual_x and actual_z, or leave both null")
        actual = None if x is None else (coordinate(x), coordinate(z))
        y = row.get("actual_y")
        if y is not None and (coordinate(y) != y or not -64 <= y <= 319):
            raise ValueError("actual_y must be a block Y in -64..319 or null")
        if actual is None and (y is not None or generated is not None):
            raise ValueError("A structure visit/Y observation requires its X/Z coordinates")
        result = {"type": name, "dimension": dimension, "actual_position_xz": list(actual) if actual else None,
                  "actual_y": y, "actual_generated": generated,
                  "actual_reported_position_inside_border": inside_border(actual, name, center, cfg),
                  "prediction_window_bounds": None, "nearest_viable_prediction": None,
                  "nearest_placement_attempt": None, "manual_review_required": True,
                  "status": "unvisited" if actual is None else "reported_position_pending_review",
                  "notes": row.get("notes", "")}
        if actual is not None:
            half = STRUCTURE_WINDOW_HALF
            bounds = (x - half, z - half, x + half, z + half)
            coordinate(bounds[0]); coordinate(bounds[1]); coordinate(bounds[2]); coordinate(bounds[3])
            result["prediction_window_bounds"] = list(bounds)
            result["nearest_viable_prediction"] = nearest_prediction(backend.structures(name, bounds), actual)
            result["nearest_placement_attempt"] = nearest_prediction(backend.structures(name, bounds, viable=False), actual)
            if result["nearest_viable_prediction"] is not None:
                p = result["nearest_viable_prediction"]["position"]
                result["predicted_start_inside_border"] = inside_border(p, name, center, cfg)
            result["comparison_scope"] = "Nearest starts only within the reported 512-square diagnostic window; offsets are not automatic match decisions."
            if result["nearest_viable_prediction"] is None:
                result["status"] = "no_viable_prediction_in_window_pending_review"
        results.append(result)
    return results


def landscape_observations(data):
    landscape = data.get("landscape", {})
    if not isinstance(landscape, dict):
        raise ValueError("landscape must be an observation object")
    for field in ("actual_island_separated", "actual_surrounding_mountains", "actual_surrounding_forest_abundant"):
        optional_bool(landscape.get(field), field)
    bridge = landscape.get("known_bridge_example")
    if bridge is not None:
        if not isinstance(bridge, dict):
            raise ValueError("known_bridge_example must give x, z, actual_connection_present, and optional notes")
        coordinate(bridge["x"]); coordinate(bridge["z"])
        optional_bool(bridge.get("actual_connection_present"), "actual_connection_present")
    return landscape
