"""Pure standard library coordinate conventions for structure navigation references.

This module provides deterministic coordinate navigation projections for a strictly
audited whitelist of structure types under pinned predictor and BDS build scopes.

IMPORTANT CONCEPTUAL BOUNDARIES:
1. Tested conventions, NOT universal Bedrock guarantees:
   The coordinate offsets (+8, +8 for outpost, -8, -8 for mineshaft and fortress)
   are empirically tested conventions observed between predictor starting points
   and BDS 1.26.52.3 `/locate structure` reference outputs across audited seeds
   (reviews/predictor-corrections-2026-10-20/EVIDENCE.json and DISCOVERY_CONTROLS.json).
   They reflect Minecraft BDS locate targeting conventions, NOT universal guarantees
   across all Bedrock versions or world-generation configurations.
2. Navigation projection ONLY, NOT verified physical generation:
   A projected navigation reference indicates the expected coordinate reported by
   locate commands if the structure generates. It does NOT guarantee that the
   structure physically generated, does not verify world-generation piece placement,
   and does not alter candidate admission, catalog geometry, or seed score counts.
3. Diagnostic-only exclusions:
   Stronghold (-2, -2 offset) has known unresolved remote mismatches (e.g. -722, -322)
   and remains diagnostic-only without a production navigation adapter.
   Trial chambers and trail ruins have variable observed offsets; their causes
   remain unresolved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

SUPPORTED_PREDICTION_REVISION = "cubiomes-bedrock-26.50"
SUPPORTED_BDS_BUILD = "1.26.52.3"

# Tested convention identifiers
CONVENTION_OUTPOST_OVERWORLD = "bedrock_26_52_outpost_p8_p8"
CONVENTION_MINESHAFT_OVERWORLD = "bedrock_26_52_mineshaft_m8_m8"
CONVENTION_FORTRESS_NETHER = "bedrock_26_52_fortress_m8_m8"

# Exact whitelist: (structure_type, dimension) -> (delta_x, delta_z, convention_id)
# Note: Dimensions are strictly scoped; no 8x coordinate scaling is applied.
_WHITELIST = {
    ("outpost", "overworld"): (8, 8, CONVENTION_OUTPOST_OVERWORLD),
    ("mineshaft", "overworld"): (-8, -8, CONVENTION_MINESHAFT_OVERWORLD),
    ("fortress", "nether"): (-8, -8, CONVENTION_FORTRESS_NETHER),
}


@dataclass(frozen=True, slots=True)
class NavigationProjection:
    """Frozen, immutable coordinate projection for player navigation reference.

    Retains candidate coordinates, navigation coordinates, dimension, convention ID,
    and observed BDS build scope. Never asserts physical generation or verification.
    """

    structure_type: str
    candidate_x: int
    candidate_z: int
    navigation_x: int
    navigation_z: int
    dimension: str
    convention_id: str
    observed_build_scope: str

    def __post_init__(self) -> None:
        for field in ('candidate_x', 'candidate_z', 'navigation_x', 'navigation_z'):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f'{field} must be an integer')

    @property
    def observed_build(self) -> str:
        """Alias for observed_build_scope."""
        return self.observed_build_scope


def project_navigation_reference(
    structure_type: Any,
    x: Any,
    z: Any,
    *,
    prediction_revision: Optional[str] = None,
    bds_build: Optional[str] = None,
    dimension: Optional[str] = None,
) -> Optional[NavigationProjection]:
    """Project candidate structure coordinates to a predicted navigation reference.

    Parameters
    ----------
    structure_type:
        Structure type identifier (exact whitelist only: 'outpost', 'mineshaft', 'fortress').
        No aliases, prefixes (e.g. 'structure.outpost'), or suffix guessing permitted.
    x:
        Candidate structure coordinate along X axis (strict integer, rejecting bool).
    z:
        Candidate structure coordinate along Z axis (strict integer, rejecting bool).
    prediction_revision:
        Pinned prediction revision string (strictly 'cubiomes-bedrock-26.50').
    bds_build:
        Pinned BDS build string (strictly '1.26.52.3').
    dimension:
        Target dimension ('overworld' for outpost/mineshaft, 'nether' for fortress).
        No 8x coordinate scaling is performed between dimensions.

    Returns
    -------
    Optional[NavigationProjection]:
        Frozen NavigationProjection if all guards and whitelist checks pass,
        otherwise None.
    """
    # Version guards: strict version matching; missing or wrong versions return None
    if prediction_revision != SUPPORTED_PREDICTION_REVISION:
        return None
    if bds_build != SUPPORTED_BDS_BUILD:
        return None

    # Strict integer coordinates rejecting bool
    if isinstance(x, bool) or isinstance(z, bool) or not isinstance(x, int) or not isinstance(z, int):
        return None

    # Exact whitelist lookup; unknown or malformed identifiers return None.
    if not isinstance(structure_type, str) or not isinstance(dimension, str):
        return None
    rule = _WHITELIST.get((structure_type, dimension))
    if rule is None:
        return None

    delta_x, delta_z, convention_id = rule

    return NavigationProjection(
        structure_type=structure_type,
        candidate_x=x,
        candidate_z=z,
        navigation_x=x + delta_x,
        navigation_z=z + delta_z,
        dimension=dimension,
        convention_id=convention_id,
        observed_build_scope=bds_build,
    )
