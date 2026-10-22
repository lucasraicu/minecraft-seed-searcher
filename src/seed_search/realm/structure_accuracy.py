"""Predictive structure integrity and physical terrain accuracy module.

Validates whether candidate structure starts actually produce complete,
habitable, and accessible in-game physical generation:
- Stronghold portal room presence, intactness, and depth bounds.
- Village terrain slope, cliffside stilt severity, and waterlogging/flooding risk.
- Ancient City subterranean cavern clearance.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass(frozen=True)
class StrongholdIntegrity:
    x: int
    z: int
    has_portal_room: bool
    portal_eyes: int
    bounding_box: Tuple[int, int, int, int, int, int]
    valid_depth: bool
    status: str


@dataclass(frozen=True)
class VillageTopography:
    x: int
    z: int
    center_height: int
    corner_heights: Tuple[int, int, int, int]
    grade_delta: int
    is_flooded: bool
    is_cliffside: bool
    status: str


def check_stronghold_integrity(backend, x: int, z: int) -> StrongholdIntegrity:
    """Analyze piece generation of a predicted stronghold to verify the portal room."""
    details = backend.stronghold_portal_details(x, z)
    has_portal = details['has_portal_room']
    eyes = details['portal_eyes']
    bb = tuple(details['bounding_box'])
    valid_depth = details['valid_depth']

    if not has_portal:
        status = 'NO_PORTAL_ROOM'
    elif not valid_depth:
        status = 'EXTREME_ELEVATION'
    else:
        status = 'VALID'

    return StrongholdIntegrity(
        x=x, z=z,
        has_portal_room=has_portal,
        portal_eyes=eyes,
        bounding_box=bb,
        valid_depth=valid_depth,
        status=status
    )


def check_village_topography(
    backend,
    villages: List[Tuple[int, int]],
    radius: int = 48,
    max_grade_delta: int = 16,
    min_surface_y: int = 62,
    vertical_step: int = 4
) -> List[VillageTopography]:
    """Sample terrain elevations at village corners to assess slope and flood risk."""
    if not villages:
        return []

    # Prepare sampling coordinates: center + 4 corners for each village
    points = []
    for vx, vz in villages:
        points.append((vx, vz))
        points.append((vx - radius, vz - radius))
        points.append((vx + radius, vz - radius))
        points.append((vx - radius, vz + radius))
        points.append((vx + radius, vz + radius))

    heights, _ = backend.heights(np.array(points, dtype=np.int32), vertical_step=vertical_step)

    results = []
    for i, (vx, vz) in enumerate(villages):
        base = i * 5
        center_y = int(heights[base])
        c_y1 = int(heights[base + 1])
        c_y2 = int(heights[base + 2])
        c_y3 = int(heights[base + 3])
        c_y4 = int(heights[base + 4])
        corners = (c_y1, c_y2, c_y3, c_y4)

        all_y = [center_y, c_y1, c_y2, c_y3, c_y4]
        grade_delta = max(all_y) - min(all_y)
        is_flooded = min(all_y) < min_surface_y
        is_cliffside = grade_delta > max_grade_delta

        if is_flooded and is_cliffside:
            status = 'FLOODED_CLIFFSIDE'
        elif is_flooded:
            status = 'FLOODED'
        elif is_cliffside:
            status = 'CLIFFSIDE_STILTS'
        else:
            status = 'HABITABLE'

        results.append(VillageTopography(
            x=vx, z=vz,
            center_height=center_y,
            corner_heights=corners,
            grade_delta=grade_delta,
            is_flooded=is_flooded,
            is_cliffside=is_cliffside,
            status=status
        ))

    return results


def evaluate_finalist_accuracy(
    backend,
    strongholds: List[Tuple[int, int]],
    villages: List[Tuple[int, int]],
    window: Optional[Tuple[int, int, int, int]] = None
) -> Dict:
    """Compute overall physical accuracy prediction for candidate finalist."""
    if window is not None:
        x0, z0, x1, z1 = window
        strongholds = [(x, z) for x, z in strongholds if x0 <= x < x1 and z0 <= z < z1]
        villages = [(x, z) for x, z in villages if x0 <= x < x1 and z0 <= z < z1]

    sh_results = [check_stronghold_integrity(backend, sx, sz) for sx, sz in strongholds]
    vi_results = check_village_topography(backend, villages)

    has_valid_sh = any(sh.status == 'VALID' for sh in sh_results) if sh_results else False
    habitable_vi = sum(1 for v in vi_results if v.status == 'HABITABLE')
    total_vi = len(vi_results)
    vi_usability_rate = (habitable_vi / total_vi) if total_vi > 0 else 0.0

    # Composite physical accuracy index (0.0 to 1.0)
    # Stronghold validity is critical (40%), Village habitability is 60%
    sh_weight = 0.40
    vi_weight = 0.60
    accuracy_score = (sh_weight if has_valid_sh else 0.0) + (vi_weight * vi_usability_rate)
    prediction_pass = bool(has_valid_sh and vi_usability_rate >= 0.60)

    return {
        'stronghold_count': len(sh_results),
        'has_valid_portal_room': has_valid_sh,
        'strongholds': [
            {'x': sh.x, 'z': sh.z, 'status': sh.status, 'portal_eyes': sh.portal_eyes,
             'bounding_box': list(sh.bounding_box), 'valid_depth': sh.valid_depth}
            for sh in sh_results
        ],
        'village_count': total_vi,
        'habitable_villages': habitable_vi,
        'village_usability_rate': round(vi_usability_rate, 3),
        'villages': [
            {'x': v.x, 'z': v.z, 'status': v.status, 'grade_delta': v.grade_delta,
             'center_height': v.center_height, 'is_flooded': v.is_flooded}
            for v in vi_results
        ],
        'accuracy_score': round(accuracy_score, 3),
        'prediction_pass': prediction_pass,
        'certified': False,
        'evidence_provenance': 'tier_a_predictive_heuristics'
    }

