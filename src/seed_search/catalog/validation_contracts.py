"""Frozen bounds for the explicitly approved100-world validation stage."""
from .registry import digest, POLICY, REGISTRY_REVISION
from ..seeds import seed_from_index

SCHEMA = 'catalog-validation-v1'
COUNT = 100
PREFLIGHT = 10
MAX_EXTRACT_SECONDS = 900
MAX_JOB_SECONDS = 1800
MAX_RSS_BYTES = 4 << 30
MAX_OUTPUT_BYTES = 2 << 30
MAX_RECORD_SECONDS = 30


def cohort():
    return [str(seed_from_index(i, 0xCA7A11)) for i in range(COUNT)]


def controls(build):
    """Build is a pinned JSON identity supplied by the coordinator, no seed eval."""
    return {'schema': SCHEMA, 'cohort': cohort(), 'preflight': PREFLIGHT, 'threads': 1,
            'extract_seconds': MAX_EXTRACT_SECONDS, 'job_seconds': MAX_JOB_SECONDS,
            'rss_bytes': MAX_RSS_BYTES, 'output_bytes': MAX_OUTPUT_BYTES,
            'record_seconds': MAX_RECORD_SECONDS, 'registry_revision': REGISTRY_REVISION,
            'policy_sha256': digest(POLICY), 'build': build}


def validate_controls(value):
    if not isinstance(value, dict) or 'build' not in value:
        raise ValueError('Validation controls must match frozen100-world limits')
    expected = pilot_controls(value['build']) if value.get('schema') == 'catalog-pilot-new100-v1' else controls(value['build'])
    if value != expected:
        raise ValueError('Validation controls must match frozen100-world limits')
    return value


def pilot_controls(build):
    """Separate approved indices100..199 campaign; original controls stay frozen."""
    value=controls(build)
    value.update(schema='catalog-pilot-new100-v1',cohort_start=100,
                 cohort=[str(seed_from_index(i,0xCA7A11)) for i in range(100,200)])
    return value

