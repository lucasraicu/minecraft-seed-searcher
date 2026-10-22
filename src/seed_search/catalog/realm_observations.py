"""Internal Realm observations for personal scoring.

Shared internal facts stored once in obs.realm.inventory:
- ocean_ruin: viable Overworld start locations [x, z]
- buried_treasure: viable Overworld start locations [x, z]
- igloo_basement: Overworld igloos with predicted basements [x, z]
- bastion_variant: Nether bastions with structure variants [x, z, variant]

Pure helpers with stub backend compatibility; no native imports or job launches.
"""
import copy
import json

INVENTORY_KEYS = ("ocean_ruin", "buried_treasure", "igloo_basement", "bastion_variant")
ENTRY_KEYS = frozenset({"status", "bounds", "method_id", "points", "errors"})
STATUSES = frozenset({"unknown", "partial", "complete", "failed"})

METHOD_OCEAN_RUIN = "predictor_viable_starts_v1"
METHOD_BURIED_TREASURE = "predictor_viable_starts_v1"
METHOD_IGLOO_BASEMENT = "predictor_igloo_basement_v1"
METHOD_BASTION_VARIANT = "predictor_bastion_variant_v1"

METHODS = {
    "ocean_ruin": METHOD_OCEAN_RUIN,
    "buried_treasure": METHOD_BURIED_TREASURE,
    "igloo_basement": METHOD_IGLOO_BASEMENT,
    "bastion_variant": METHOD_BASTION_VARIANT,
}

DIMENSIONS = {
    "ocean_ruin": "overworld",
    "buried_treasure": "overworld",
    "igloo_basement": "overworld",
    "bastion_variant": "nether",
}

CREDENTIAL_TERMS = ("password", "passwd", "secret", "bearer ", "private_key", "token")


def _error(exc):
    # Error category is sufficient for retries; do not persist arbitrary provider text.
    return type(exc).__name__


def _validate_int(val, lo=-(1 << 31), hi=(1 << 31) - 1, name="coordinate"):
    if type(val) is not int:
        raise ValueError(f"{name} must be an integer, got {type(val).__name__}")
    if not (lo <= val <= hi):
        raise ValueError(f"{name} {val} out of declared range [{lo}, {hi}]")
    return val


def _get_dimension_bounds(obs, dimension):
    if not isinstance(obs, dict):
        raise ValueError("obs must be a dictionary")
    bounds = obs.get("bounds")
    if isinstance(bounds, dict):
        if dimension not in bounds:
            raise ValueError(f"obs['bounds'] missing dimension '{dimension}'")
        b = bounds[dimension]
    elif isinstance(bounds, list) and dimension == "overworld":
        b = bounds
    else:
        raise ValueError("Invalid obs['bounds'] format")
    if not isinstance(b, list) or len(b) != 4:
        raise ValueError(f"Invalid bounds format for dimension '{dimension}'")
    for n in b:
        _validate_int(n, -30_000_000, 30_000_000, "bounds coordinate")
    if b[0] >= b[2] or b[1] >= b[3]:
        raise ValueError(f"Empty bounds for dimension '{dimension}': {b}")
    return list(b)


def _inside_bounds(x, z, bounds):
    return bounds[0] <= x < bounds[2] and bounds[1] <= z < bounds[3]


def _validate_entry(key, entry, obs):
    if not isinstance(entry, dict):
        raise ValueError(f"Entry '{key}' must be a dictionary")
    if set(entry.keys()) != ENTRY_KEYS:
        raise ValueError(f"Entry '{key}' has invalid keys: {set(entry.keys())}")

    status = entry["status"]
    if status not in STATUSES:
        raise ValueError(f"Entry '{key}' has invalid status: {status}")

    dimension = DIMENSIONS[key]
    expected_bounds = _get_dimension_bounds(obs, dimension)
    if entry["bounds"] != expected_bounds:
        raise ValueError(f"Entry '{key}' bounds {entry['bounds']} do not match obs bounds {expected_bounds}")

    expected_method = METHODS[key]
    if entry["method_id"] != expected_method:
        raise ValueError(f"Entry '{key}' method_id '{entry['method_id']}' does not match expected '{expected_method}'")

    errors = entry["errors"]
    if not isinstance(errors, list):
        raise ValueError(f"Entry '{key}' errors must be a list")
    if len(errors) > 10:
        raise ValueError(f"Entry '{key}' errors list exceeds 10 items")
    for err in errors:
        if not isinstance(err, str) or len(err) > 500:
            raise ValueError(f"Entry '{key}' error message must be a string <= 500 chars")
        err_lower = err.lower()
        for cred in CREDENTIAL_TERMS:
            if cred in err_lower:
                raise ValueError(f"Entry '{key}' error contains credential substring: '{cred}'")

    points = entry["points"]
    if not isinstance(points, list):
        raise ValueError(f"Entry '{key}' points must be a list")
    if len(points) > 200_000:
        raise ValueError(f"Entry '{key}' points list exceeds 200,000 items")

    if status in ("unknown", "failed") and len(points) > 0:
        raise ValueError(f"Entry '{key}' with status '{status}' cannot have points")

    if status == "complete" and len(errors) > 0:
        raise ValueError(f"Entry '{key}' with status 'complete' cannot have errors")

    structures = obs.get("structures", {})
    coverage = obs.get("coverage", {})

    if key in ("ocean_ruin", "buried_treasure"):
        seen = set()
        prev = None
        for pt in points:
            if not isinstance(pt, list) or len(pt) != 2:
                raise ValueError(f"Entry '{key}' point must be a list [x, z]")
            x = _validate_int(pt[0], -30_000_000, 30_000_000, "x")
            z = _validate_int(pt[1], -30_000_000, 30_000_000, "z")
            if not _inside_bounds(x, z, expected_bounds):
                raise ValueError(f"Entry '{key}' point [{x}, {z}] outside bounds")
            cur = (x, z)
            if cur in seen or (prev is not None and cur <= prev):
                raise ValueError(f"Entry '{key}' points must be strictly sorted and unique")
            seen.add(cur)
            prev = cur

    elif key == "igloo_basement":
        public_igloos = structures.get("structure.igloo", [])
        if not isinstance(public_igloos, list):
            raise ValueError("obs['structures']['structure.igloo'] must be a list")
        public_set = set()
        for p in public_igloos:
            if isinstance(p, list) and len(p) == 2 and type(p[0]) is int and type(p[1]) is int:
                public_set.add((p[0], p[1]))

        seen = set()
        prev = None
        for pt in points:
            if not isinstance(pt, list) or len(pt) != 2:
                raise ValueError(f"Entry '{key}' point must be a list [x, z]")
            x = _validate_int(pt[0], -30_000_000, 30_000_000, "x")
            z = _validate_int(pt[1], -30_000_000, 30_000_000, "z")
            if not _inside_bounds(x, z, expected_bounds):
                raise ValueError(f"Entry '{key}' point [{x}, {z}] outside bounds")
            cur = (x, z)
            if cur in seen or (prev is not None and cur <= prev):
                raise ValueError(f"Entry '{key}' points must be strictly sorted and unique")
            if cur not in public_set:
                raise ValueError(f"Entry '{key}' point [{x}, {z}] is not in public igloo starts")
            seen.add(cur)
            prev = cur

        if status == "complete":
            source_cov = coverage.get("structure.igloo", {})
            if not isinstance(source_cov, dict) or source_cov.get("status") != "complete":
                raise ValueError("igloo_basement complete requires structure.igloo coverage complete")

    elif key == "bastion_variant":
        public_bastions = structures.get("structure.bastion", [])
        if not isinstance(public_bastions, list):
            raise ValueError("obs['structures']['structure.bastion'] must be a list")
        public_set = set()
        for p in public_bastions:
            if isinstance(p, list) and len(p) == 2 and type(p[0]) is int and type(p[1]) is int:
                public_set.add((p[0], p[1]))

        seen_coords = set()
        prev = None
        for pt in points:
            if not isinstance(pt, list) or len(pt) != 3:
                raise ValueError(f"Entry '{key}' point must be a list [x, z, variant]")
            x = _validate_int(pt[0], -30_000_000, 30_000_000, "x")
            z = _validate_int(pt[1], -30_000_000, 30_000_000, "z")
            v = _validate_int(pt[2], 0, 3, "variant")
            if not _inside_bounds(x, z, expected_bounds):
                raise ValueError(f"Entry '{key}' point [{x}, {z}, {v}] outside bounds")
            coord = (x, z)
            cur = (x, z, v)
            if coord in seen_coords or (prev is not None and cur <= prev):
                raise ValueError(f"Entry '{key}' points must be strictly sorted and unique by coordinate")
            if coord not in public_set:
                raise ValueError(f"Entry '{key}' point [{x}, {z}] is not in public bastion starts")
            seen_coords.add(coord)
            prev = cur

        if status == "complete":
            source_cov = coverage.get("structure.bastion", {})
            if not isinstance(source_cov, dict) or source_cov.get("status") != "complete":
                raise ValueError("bastion_variant complete requires structure.bastion coverage complete")
            if len(seen_coords) != len(public_set):
                raise ValueError("bastion_variant complete requires all public bastions to have variants")


def validate_realm_inventory(obs):
    """Validate internal Realm inventory in obs['realm']['inventory'].

    Raises ValueError on any violation. Makes no backend calls.
    Returns the validated inventory dictionary.
    """
    if not isinstance(obs, dict):
        raise ValueError("obs must be a dictionary")
    realm = obs.get("realm")
    if not isinstance(realm, dict):
        raise ValueError("obs['realm'] must be a dictionary")
    inventory = realm.get("inventory")
    if not isinstance(inventory, dict):
        raise ValueError("obs['realm']['inventory'] must be a dictionary")

    if set(inventory.keys()) != set(INVENTORY_KEYS):
        raise ValueError(f"Inventory keys must be {INVENTORY_KEYS}, got {set(inventory.keys())}")

    for key in INVENTORY_KEYS:
        _validate_entry(key, inventory[key], obs)

    # Validate JSON serializability and reject non-finite numbers (NaN/Infinity)
    json.dumps(inventory, sort_keys=True, separators=(",", ":"), allow_nan=False)

    return inventory


def extract_realm_inventory(obs, backend):
    """Extract internal Realm observations into obs['realm']['inventory'].

    May mutate obs; preserves other realm keys.
    Returns the updated obs.
    """
    if not isinstance(obs, dict):
        raise ValueError("obs must be a dictionary")

    ow_bounds = _get_dimension_bounds(obs, "overworld")
    nether_bounds = _get_dimension_bounds(obs, "nether")

    realm = obs.get("realm")
    if realm is None:
        obs["realm"] = {}
        realm = obs["realm"]
    elif not isinstance(realm, dict):
        raise ValueError("obs['realm'] must be None or a dict")

    existing_inv = realm.get("inventory")
    existing_is_dict = isinstance(existing_inv, dict)

    inventory = {}

    # 1. ocean_ruin
    resumed = False
    if existing_is_dict and "ocean_ruin" in existing_inv:
        cand = existing_inv["ocean_ruin"]
        if (isinstance(cand, dict) and cand.get("status") == "complete"
                and cand.get("bounds") == ow_bounds
                and cand.get("method_id") == METHOD_OCEAN_RUIN):
            try:
                _validate_entry("ocean_ruin", cand, obs)
                inventory["ocean_ruin"] = copy.deepcopy(cand)
                resumed = True
            except ValueError:
                resumed = False
    if not resumed:
        try:
            inclusive = (ow_bounds[0], ow_bounds[1], ow_bounds[2] - 1, ow_bounds[3] - 1)
            raw = backend.structures("ocean_ruin", inclusive, viable=True)
            if len(raw) > 200_000:
                raise ValueError("Structure count exceeds 200,000")
            unique = set()
            for pt in raw:
                if len(pt) != 2:
                    raise ValueError("Invalid point length")
                x = _validate_int(pt[0], -30_000_000, 30_000_000, "x")
                z = _validate_int(pt[1], -30_000_000, 30_000_000, "z")
                if not _inside_bounds(x, z, ow_bounds):
                    raise ValueError(f"Point [{x}, {z}] outside bounds")
                unique.add((x, z))
            points = [list(p) for p in sorted(unique)]
            inventory["ocean_ruin"] = {
                "status": "complete",
                "bounds": list(ow_bounds),
                "method_id": METHOD_OCEAN_RUIN,
                "points": points,
                "errors": [],
            }
        except Exception as exc:
            inventory["ocean_ruin"] = {
                "status": "failed",
                "bounds": list(ow_bounds),
                "method_id": METHOD_OCEAN_RUIN,
                "points": [],
                "errors": [_error(exc)],
            }

    # 2. buried_treasure
    resumed = False
    if existing_is_dict and "buried_treasure" in existing_inv:
        cand = existing_inv["buried_treasure"]
        if (isinstance(cand, dict) and cand.get("status") == "complete"
                and cand.get("bounds") == ow_bounds
                and cand.get("method_id") == METHOD_BURIED_TREASURE):
            try:
                _validate_entry("buried_treasure", cand, obs)
                inventory["buried_treasure"] = copy.deepcopy(cand)
                resumed = True
            except ValueError:
                resumed = False
    if not resumed:
        try:
            inclusive = (ow_bounds[0], ow_bounds[1], ow_bounds[2] - 1, ow_bounds[3] - 1)
            raw = backend.structures("buried_treasure", inclusive, viable=True)
            if len(raw) > 200_000:
                raise ValueError("Structure count exceeds 200,000")
            unique = set()
            for pt in raw:
                if len(pt) != 2:
                    raise ValueError("Invalid point length")
                x = _validate_int(pt[0], -30_000_000, 30_000_000, "x")
                z = _validate_int(pt[1], -30_000_000, 30_000_000, "z")
                if not _inside_bounds(x, z, ow_bounds):
                    raise ValueError(f"Point [{x}, {z}] outside bounds")
                unique.add((x, z))
            points = [list(p) for p in sorted(unique)]
            inventory["buried_treasure"] = {
                "status": "complete",
                "bounds": list(ow_bounds),
                "method_id": METHOD_BURIED_TREASURE,
                "points": points,
                "errors": [],
            }
        except Exception as exc:
            inventory["buried_treasure"] = {
                "status": "failed",
                "bounds": list(ow_bounds),
                "method_id": METHOD_BURIED_TREASURE,
                "points": [],
                "errors": [_error(exc)],
            }

    # 3. igloo_basement
    resumed = False
    if existing_is_dict and "igloo_basement" in existing_inv:
        cand = existing_inv["igloo_basement"]
        if (isinstance(cand, dict) and cand.get("status") == "complete"
                and cand.get("bounds") == ow_bounds
                and cand.get("method_id") == METHOD_IGLOO_BASEMENT):
            try:
                _validate_entry("igloo_basement", cand, obs)
                inventory["igloo_basement"] = copy.deepcopy(cand)
                resumed = True
            except ValueError:
                resumed = False
    if not resumed:
        structures = obs.get("structures", {})
        coverage = obs.get("coverage", {})
        raw_public_igloos = structures.get("structure.igloo", [])
        if not isinstance(raw_public_igloos, list):
            raise ValueError("obs['structures']['structure.igloo'] must be a list")

        public_igloos = []
        for pt in raw_public_igloos:
            if isinstance(pt, list) and len(pt) == 2:
                x = _validate_int(pt[0], -30_000_000, 30_000_000, "x")
                z = _validate_int(pt[1], -30_000_000, 30_000_000, "z")
                if _inside_bounds(x, z, ow_bounds):
                    public_igloos.append((x, z))
        public_igloos_set = set(public_igloos)

        igloo_cov = coverage.get("structure.igloo", {})
        source_complete = (isinstance(igloo_cov, dict) and igloo_cov.get("status") == "complete")

        known_positives = set()
        if existing_is_dict and "igloo_basement" in existing_inv:
            cand = existing_inv["igloo_basement"]
            if isinstance(cand, dict) and isinstance(cand.get("points"), list):
                for pt in cand["points"]:
                    if isinstance(pt, list) and len(pt) == 2 and type(pt[0]) is int and type(pt[1]) is int:
                        coord = (pt[0], pt[1])
                        if coord in public_igloos_set and _inside_bounds(coord[0], coord[1], ow_bounds):
                            known_positives.add(coord)

        errors = []
        all_succeeded = True
        for x, z in sorted(public_igloos_set):
            try:
                has_basement = backend.igloo_basement(x, z)
                if type(has_basement) is not bool:
                    raise ValueError(f"igloo_basement returned non-bool {type(has_basement).__name__}")
                if has_basement:
                    known_positives.add((x, z))
                else:
                    known_positives.discard((x, z))
            except Exception as exc:
                all_succeeded = False
                if len(errors) < 10:
                    errors.append(_error(exc))

        status = "complete" if (source_complete and all_succeeded) else "partial"
        inventory["igloo_basement"] = {
            "status": status,
            "bounds": list(ow_bounds),
            "method_id": METHOD_IGLOO_BASEMENT,
            "points": [list(p) for p in sorted(known_positives)],
            "errors": errors if status != "complete" else [],
        }

    # 4. bastion_variant
    resumed = False
    if existing_is_dict and "bastion_variant" in existing_inv:
        cand = existing_inv["bastion_variant"]
        if (isinstance(cand, dict) and cand.get("status") == "complete"
                and cand.get("bounds") == nether_bounds
                and cand.get("method_id") == METHOD_BASTION_VARIANT):
            try:
                _validate_entry("bastion_variant", cand, obs)
                inventory["bastion_variant"] = copy.deepcopy(cand)
                resumed = True
            except ValueError:
                resumed = False
    if not resumed:
        structures = obs.get("structures", {})
        coverage = obs.get("coverage", {})
        raw_public_bastions = structures.get("structure.bastion", [])
        if not isinstance(raw_public_bastions, list):
            raise ValueError("obs['structures']['structure.bastion'] must be a list")

        public_bastions = []
        for pt in raw_public_bastions:
            if isinstance(pt, list) and len(pt) == 2:
                x = _validate_int(pt[0], -30_000_000, 30_000_000, "x")
                z = _validate_int(pt[1], -30_000_000, 30_000_000, "z")
                if _inside_bounds(x, z, nether_bounds):
                    public_bastions.append((x, z))
        public_bastions_set = set(public_bastions)

        bastion_cov = coverage.get("structure.bastion", {})
        source_complete = (isinstance(bastion_cov, dict) and bastion_cov.get("status") == "complete")

        known_variants = {}
        if existing_is_dict and "bastion_variant" in existing_inv:
            cand = existing_inv["bastion_variant"]
            if isinstance(cand, dict) and isinstance(cand.get("points"), list):
                for pt in cand["points"]:
                    if isinstance(pt, list) and len(pt) == 3:
                        x, z, v = pt
                        if type(x) is int and type(z) is int and type(v) is int and 0 <= v <= 3:
                            coord = (x, z)
                            if coord in public_bastions_set and _inside_bounds(x, z, nether_bounds):
                                known_variants[coord] = v

        errors = []
        all_succeeded = True
        for x, z in sorted(public_bastions_set):
            try:
                v = backend.bastion_variant(x, z)
                if type(v) is not int or not (0 <= v <= 3):
                    raise ValueError(f"bastion_variant returned invalid variant: {v}")
                known_variants[(x, z)] = v
            except Exception as exc:
                all_succeeded = False
                if len(errors) < 10:
                    errors.append(_error(exc))

        status = "complete" if (source_complete and all_succeeded and len(known_variants) == len(public_bastions_set)) else "partial"
        inventory["bastion_variant"] = {
            "status": status,
            "bounds": list(nether_bounds),
            "method_id": METHOD_BASTION_VARIANT,
            "points": [[x, z, known_variants[(x, z)]] for (x, z) in sorted(known_variants.keys())],
            "errors": errors if status != "complete" else [],
        }

    realm["inventory"] = inventory
    validate_realm_inventory(obs)
    return obs
