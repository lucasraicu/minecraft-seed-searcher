"""Conservative feature/method-specific coverage for the initial full envelope."""
from .geometry import bounds_for, contains

STRUCTURE_METHOD = 'predictor_viable_starts_v1'
BIOME_METHOD = 'predictor_world_lattice_y63_stride64_v1'
REVIEWED_STRUCTURE_METHOD = 'predictor_viable_starts_reviewed_exclusions_v1'
STRUCTURE_METHODS = (STRUCTURE_METHOD, REVIEWED_STRUCTURE_METHOD)


def complete_for(obs, feature, anchor, side, radius=None):
    record = obs['coverage'].get(feature, {})
    method = BIOME_METHOD if feature.startswith('biome.') else STRUCTURE_METHOD
    if record.get('status') != 'complete' or record.get('method_id') not in ((method,) if feature.startswith('biome.') else STRUCTURE_METHODS):
        return False
    box = bounds_for(anchor, side)
    if radius is not None:
        x, z = anchor
        box = (max(box[0], x-radius), max(box[1], z-radius),
               min(box[2], x+radius+1), min(box[3], z+radius+1))
    return contains(record['bounds'], box)

