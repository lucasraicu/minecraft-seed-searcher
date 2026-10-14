"""Tests verifying Native C & CFFI build hardening and safety guards."""
import pytest
from seed_search._native import ffi, lib
from seed_search.realm.config import two_group_blueprint_config, validate_config, TWO_GROUP_STRONGHOLD_AFTER
from seed_search.realm.native_batch import Prototype


def test_native_null_pointer_guards():
    # NULL context guards
    assert lib.ss_grid(ffi.NULL, 0, 0, 10, 10, 4, 63, ffi.NULL, ffi.NULL, ffi.NULL) == -1
    assert lib.ss_heights(ffi.NULL, ffi.NULL, 10, 4, ffi.NULL, ffi.NULL) == -1
    assert lib.ss_land(ffi.NULL, ffi.NULL, 10, ffi.NULL) == -1
    assert lib.ss_density_points(ffi.NULL, ffi.NULL, 10, ffi.NULL) == -1

    # Valid context with NULL buffers
    ctx = lib.ss_create(12345)
    assert ctx != ffi.NULL
    try:
        assert lib.ss_grid(ctx, 0, 0, 10, 10, 4, 63, ffi.NULL, ffi.NULL, ffi.NULL) == -1
        assert lib.ss_heights(ctx, ffi.NULL, 10, 4, ffi.NULL, ffi.NULL) == -1
        assert lib.ss_land(ctx, ffi.NULL, 10, ffi.NULL) == -1
        assert lib.ss_density_points(ctx, ffi.NULL, 10, ffi.NULL) == -1
    finally:
        lib.ss_destroy(ctx)


def test_structure_goal_clamping():
    cfg = two_group_blueprint_config()
    cfg['structures']['minimum_counts']['village'] = 64
    cfg['structures']['nether_minimum_counts']['bastion'] = 64
    validate_config(cfg)

    # Over 64 raises ValueError
    cfg_invalid = two_group_blueprint_config()
    cfg_invalid['structures']['minimum_counts']['village'] = 65
    with pytest.raises(ValueError, match=r'minimum_counts\.village must be an integer in 0–64'):
        validate_config(cfg_invalid)

    cfg_invalid_nether = two_group_blueprint_config()
    cfg_invalid_nether['structures']['nether_minimum_counts']['bastion'] = 65
    with pytest.raises(ValueError, match=r'nether_minimum_counts\.bastion must be an integer in 0–64'):
        validate_config(cfg_invalid_nether)


def test_packaged_native_prototype_stronghold_placement():
    cfg = two_group_blueprint_config()
    p = Prototype(None, cfg)
    assert p.identity['stronghold_after'] == TWO_GROUP_STRONGHOLD_AFTER
    assert p.identity['scope'] == 'packaged complete native blueprint baseline'
