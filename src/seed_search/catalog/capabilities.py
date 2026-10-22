"""Developer-reference capabilities; product activation stays disabled."""
from .registry import FEATURES, SIDES, RADII, REGISTRY_REVISION


def capabilities():
    return {
        'status': 'research_reference_only', 'public_runtime_enabled': False,
        'accepted_game_builds': [], 'registry_revision': REGISTRY_REVISION,
        'border_sides': list(SIDES), 'near_radii': list(RADII),
        'anchor_modes': ['origin', 'recommended'],
        'features': {f['id']: {'reference_supported': True,
            'evidence_label': f['evidence_label'], 'actual_game_verified': False,
            'requires_completed_observation': True} for f in FEATURES},
        'unsupported': ['spawn', 'stronghold', 'igloo_basement', 'nether',
                        'surface_area', 'absence', 'arbitrary_radius'],
    }

