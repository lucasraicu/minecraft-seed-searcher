"""Read the existing source-tree contracts, without enabling product flags."""
from pathlib import Path
import hashlib
import json

CONTRACT_ROOT = Path(__file__).resolve().parents[3] / 'docs/catalog/v1'


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


REGISTRY = json.loads((CONTRACT_ROOT / 'feature_registry.json').read_text())
POLICY = json.loads((CONTRACT_ROOT / 'public_policy.json').read_text())
REQUEST_SCHEMA = json.loads((CONTRACT_ROOT / 'request_schema.json').read_text())
REGISTRY_REVISION = digest(REGISTRY)
STRUCTURES = tuple(sorted((f for f in REGISTRY['features'] if f['kind'] == 'structure_count'), key=lambda f: f['slot']))
BIOMES = tuple(sorted((f for f in REGISTRY['features'] if f['kind'] == 'biome_witness'), key=lambda f: f['slot']))
FEATURES = STRUCTURES + BIOMES
FEATURE_IDS = tuple(f['id'] for f in FEATURES)
SIDES = tuple(POLICY['public']['border_sides'])
RADII = tuple(POLICY['public']['near_radii'])
AXIS = tuple(POLICY['public']['anchor_grid_axis'])
ENVELOPE = tuple(POLICY['public']['tile_aligned_max_envelope'])
PROFILES = {p['id']: tuple(p['coefficients_VTAOEBHR']) for p in POLICY['profiles']}

# Additive vocabulary: the legacy slots and byte contracts above remain frozen.
REGISTRY_V2 = json.loads((CONTRACT_ROOT.parent / 'v2' / 'feature_registry.json').read_text())
FEATURES_V2 = tuple(REGISTRY_V2['features'])
FEATURE_BY_ID_V2 = {f['id']: f for f in FEATURES_V2}
REGISTRY_REVISION_V2 = digest(REGISTRY_V2)

REGISTRY_V3 = json.loads((CONTRACT_ROOT.parent / 'v3' / 'feature_registry.json').read_text())
FEATURES_V3 = tuple(REGISTRY_V3['features'])
FEATURE_BY_ID_V3 = {f['id']: f for f in FEATURES_V3}
REGISTRY_REVISION_V3 = digest(REGISTRY_V3)
SAMPLING_PROFILES_V3 = json.loads((CONTRACT_ROOT.parent / 'v3' / 'sampling_profiles.json').read_text())
SAMPLING_PROFILE_REVISION_V3 = digest(SAMPLING_PROFILES_V3)


