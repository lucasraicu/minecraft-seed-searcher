"""Known-policy capacity dispatch; callers cannot supply larger storage limits."""
from .registry import digest

LEGACY_SLOTS = 105644
EXPANDED_PRIMARY_SLOTS = 115964
EXPANDED_SLOTS = 231928
EXPANDED_OBJECTIVES = 7543


def contract():
    from .retention import automation_primary_objectives_v3, automation_objectives_v3
    primary = automation_primary_objectives_v3()
    effective = automation_objectives_v3()
    if (len(primary)!=EXPANDED_OBJECTIVES or sum(primary.values())!=EXPANDED_PRIMARY_SLOTS
            or effective!={k:2*v for k,v in primary.items()}):
        raise ValueError('Expanded policy capacity contract differs')
    return dict(revision='catalog-reserve-policy-v3',reserve_factor=2,
                primary_objectives=primary,retained_objectives=effective)


def contract_id():
    return digest(contract())


def validate_contract(value):
    if value != contract_id():
        raise ValueError('Unknown expanded retention policy')
    return EXPANDED_OBJECTIVES, EXPANDED_SLOTS


def reserve_metadata(*, historically_complete=False):
    return dict(reserve_factor=2,historically_complete=historically_complete,
                evidence_status='predicted',primary_slots=EXPANDED_PRIMARY_SLOTS,
                retained_slots=EXPANDED_SLOTS)
