"""Versioned evidence identities; no record implies completeness or absence."""
import copy
import re
from .models import validate_identity
from .registry import digest

REVISION = 'catalog-accuracy-v1'
PROVIDERS = frozenset(('procedural_model_v1', 'bds_saved_runtime_v3',
    'bds_script_api_v1', 'bds_locate_v1', 'bds_feature_membership_v1',
    'estimated_world_spawn_v1', 'observed_world_spawn_v1'))
MODEL_PROVIDERS = frozenset(('procedural_model_v1', 'estimated_world_spawn_v1'))
BUILD = '1.26.52.3'


def sha256(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Expected lowercase SHA256')
    return value


def integer(value, low=-(1 << 31), high=(1 << 31)-1):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('Expected bounded integer')
    return value


def validate_context(value):
    if not isinstance(value, dict) or set(value) != {'identity', 'dimension',
            'provider', 'observed_build', 'evidence_sha256'}:
        raise ValueError('Invalid accuracy context')
    validate_identity(value['identity'])
    if value['dimension'] not in ('overworld', 'nether') or value['provider'] not in PROVIDERS:
        raise ValueError('Unsupported accuracy provider/dimension')
    expected = None if value['provider'] in MODEL_PROVIDERS else BUILD
    if value['observed_build'] != expected:
        raise ValueError('Unsupported provider build')
    sha256(value['evidence_sha256'])
    digest(value)
    return copy.deepcopy(value)


def context_id(value):
    return digest(validate_context(value))
