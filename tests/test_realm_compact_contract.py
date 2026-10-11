from pathlib import Path

import pytest
import yaml

from seed_search.realm.bounds import contains, native_bounds, nether_square
from seed_search.realm.config import default_config, validate_config
from seed_search.realm.raw import FAMILIES, center_rectangle
from seed_search.realm.verification import VerificationAdapter


def test_explicit_and_default_profiles_share_compact_geometry():
    cfg = default_config()
    explicit = yaml.safe_load((Path(__file__).parents[1] / 'config/realm.yaml').read_text())
    for profile in (cfg, explicit):
        validate_config(profile)
        assert profile['deployment'] == {'overworld_side_blocks': 1536, 'nether_side_blocks': 896}
        assert set(map(tuple, profile['discovery'].values())) == {(-2000, -2000, 2000, 2000)}
    assert FAMILIES == (
        ('village', (-2768, -2768, 2766, 2766)),
        ('ancient_city', (-2768, -2768, 2766, 2766)),
        ('fortress', (-698, -698, 697, 697)),
        ('bastion', (-698, -698, 697, 697)),
        ('fortress', (-2000, -2000, 1999, 1999)),
    )


@pytest.mark.parametrize('anchor', [(-2000, -2000), (1999, 1999), (-1, -9), (7, 15)])
def test_nether_verifier_and_raw_center_domain_match_baseline(anchor):
    exact = nether_square(anchor)
    x0, z0, x1, z1 = native_bounds(exact)
    adapter = VerificationAdapter(default_config())
    assert adapter.verify_final_nether('1', anchor)['bounds'] == [x0, z0, x1+1, z1+1]
    for point in ((x0, z0), (x1, z1), (x0-1, z0), (x1+1, z1)):
        rectangle = center_rectangle(point, nether=True)
        raw_membership = rectangle is not None and (
            rectangle[0] <= anchor[0] <= rectangle[2] and rectangle[1] <= anchor[1] <= rectangle[3])
        assert raw_membership == contains(point, exact)


def test_explicit_historical_verification_geometry_is_not_reinterpreted():
    adapter = VerificationAdapter({'deployment': {'nether_side_blocks': 1024}})
    assert adapter.verify_final_nether('1', (-1, -9))['bounds'] == [-512, -513, 512, 511]
