"""Test that structure_centers preserves coordinate pairs and does not create phantom centers."""
from seed_search.structures import structure_centers


def test_structure_centers_preserves_pairs_no_phantom():
    cfg = {
        'search': {'center_axis_bounds_blocks': [-1000, 1000]},
        'structures': {'required_overworld_types': ['stronghold']},
        'nether': {'fortress_required': False, 'bastion_required': False},
        'deployment': {'overworld_side_blocks': 512, 'nether_side_blocks': 256},
    }
    # Two distinct strongholds inside the box
    scans = {
        'stronghold': {
            'raw': [(104, 208), (304, 408)],
            'viable': [(104, 208), (304, 408)],
        }
    }
    centers = structure_centers(scans, cfg)
    # The actual stronghold centers (or their 8-block snapped coords) must be present
    assert (104, 208) in centers
    assert (304, 408) in centers
    # Phantom cross-combinations must NOT be present
    assert (104, 408) not in centers
    assert (304, 208) not in centers
