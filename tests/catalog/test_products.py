"""Independent raw-coordinate checks for offline record previews."""
import copy
import json
import time

import pytest

from seed_search.catalog.models import world_id
from seed_search.catalog.product_views import derive_previews,write_previews,read_previews
from seed_search.catalog.registry import digest
from seed_search.catalog.segments import SegmentedCatalog
from seed_search.catalog.summaries import summarize
from tests.catalog.test_integrated_pilot import sample


def catalog(tmp_path):
    first,_=sample(-(1<<63));second,_=sample((1<<63)-1)
    first['structures']['structure.village']=[[-2000,0],[0,-2000],[0,2000],[1200,1600],[1800,1800],[2000,0],[2000,1]]
    second['structures']['structure.village']=[[0,0]]
    second['coverage']['structure.trial_chamber']['status']='partial'
    root=tmp_path/'catalog'
    with SegmentedCatalog(root) as store:
        sid=store.publish([first,second],summarize(first)+summarize(second))
    return root,sid,first,second


def test_research_circle_exact_boundary_unknown_and_string_seed(tmp_path):
    root,sid,first,second=catalog(tmp_path)
    with SegmentedCatalog(root) as store:payload=derive_previews(store,sid)
    rows=payload['lists']['research.origin.village.r2000']
    assert [(r['seed'],r['count']) for r in rows]==[(str(-(1<<63)),5),(str((1<<63)-1),1)]
    for row in rows:
        source=first if row['world_id']==world_id(first['identity']) else second
        expected=sorted(p for p in source['structures']['structure.village'] if sum(n*n for n in p)<=2000**2)
        assert row['witnesses']==expected and row['scope']['radius']==2000
    trial=payload['lists']['research.origin.trial_chamber.r2000']
    assert len(trial)==1 and trial[0]['seed']==str(-(1<<63))
    path=write_previews(root,payload)
    assert read_previews(root,sid,expected_header=payload['header'])==payload
    assert write_previews(root,payload)==path


def test_artifact_corruption_definition_header_and_wrong_scope_rejected(tmp_path):
    root,sid,_,_=catalog(tmp_path)
    with SegmentedCatalog(root) as store:payload=derive_previews(store,sid)
    path=write_previews(root,payload)
    with pytest.raises(ValueError):read_previews(root,sid,expected_header=dict(payload['header'],model_id='different'))
    value=json.loads(path.read_text());value['payload']['lists']['research.origin.village.r2000'][0]['count']=100
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='checksum'):read_previews(root,sid)
    value['sha256']=digest(value['payload']);path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='Witness count'):read_previews(root,sid)
    bad=copy.deepcopy(payload);bad['definition_sha256']='0'*64
    with pytest.raises(ValueError):write_previews(root,bad)
    bad=copy.deepcopy(payload);bad['lists']['research.origin.village.r2000'][0]['scope']['radius']=2048
    with pytest.raises(ValueError):write_previews(root,bad)


def test_missing_symlink_and_deadline(tmp_path):
    root,sid,_,_=catalog(tmp_path)
    with pytest.raises(FileNotFoundError):read_previews(root,sid)
    with SegmentedCatalog(root) as store:
        with pytest.raises(TimeoutError):derive_previews(store,sid,deadline=time.monotonic()-1)
        payload=derive_previews(store,sid)
    outside=tmp_path/'outside';outside.mkdir()
    (root/'product-previews').symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError):write_previews(root,payload)


def test_top100_ties_omit_zero_and_duplicate_starts_rejected(tmp_path):
    observations=[];layouts=[]
    for seed in range(105):
        obs,_=sample(seed+1)
        obs['structures']['structure.village']=[] if seed==0 else [[0,0]]
        observations.append(obs);layouts.extend(r for r in summarize(obs) if r['anchor']==[0,0] and r['border_side']==4096)
    root=tmp_path/'rank'
    with SegmentedCatalog(root) as store:
        sid=store.publish(observations,layouts);payload=derive_previews(store,sid)
    rows=payload['lists']['research.origin.village.r2000']
    assert len(rows)==100
    assert [r['world_id'] for r in rows]==sorted(world_id(o['identity']) for o in observations[1:])[:100]
    duplicate=copy.deepcopy(observations[1]);duplicate['structures']['structure.village']=[[0,0],[0,0]]
    with pytest.raises(ValueError):summarize(duplicate)
