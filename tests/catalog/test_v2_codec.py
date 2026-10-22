"""Reject corrupted published summaries rather than trusting positive query hits."""
import copy
import pytest
from seed_search.catalog.codec import validate_summary_v2
from seed_search.catalog.models import identity,empty_observation_v2
from seed_search.catalog.summaries import summarize_v2


@pytest.fixture(scope='module')
def row():
    obs=empty_observation_v2(identity('123',model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64))
    obs['structures']={'structure.village':[[5,0]],'structure.bastion':[[-1,0]]}
    return next(r for r in summarize_v2(obs) if r['anchor']==[0,0] and r['border_side']==2048)


def test_generated_summary_is_valid_and_typed(row):
    assert validate_summary_v2(row) is row
    assert row['features']['structure.bastion']['nearest_d2']==1
    assert row['features']['structure.bastion']['witness']==[-1,None,0]


@pytest.mark.parametrize('damage',[
    lambda r:r.update(nether_anchor=[-1,0]),
    lambda r:r['features']['biome.cherry_grove'].update(complete=[True]*4),
    lambda r:r['features']['structure.village'].update(nearest_d2=0),
    lambda r:r['features']['structure.village'].update(counts=[2,1,1,1]),
    lambda r:r['legacy'].update(world_id='f'*64),
    lambda r:r.update(layout_id='e'*64),
    lambda r:r['features']['structure.village'].update(counts=[0,1,1,1]),
    lambda r:r['features']['structure.bastion'].update(dimension='overworld'),
])
def test_invalid_source_geometry_or_absence_claim_rejected(row,damage):
    broken=copy.deepcopy(row);damage(broken)
    with pytest.raises(ValueError):validate_summary_v2(broken)
