import pytest
from seed_search.realm.raw import run_raw,prepare_siblings,FAMILIES,center_rectangle,joint_center_witness
from seed_search.realm.bounds import square,nether_square,contains
import numpy as np
from seed_search.realm.raw import exploration_keys,_hash


def test_exploration_permutation_matches_scalar_and_is_unique():
    values=np.array([0,1,2**32-1,*range(10000)],dtype=np.uint64)
    mask=2**64-1;salt=_hash(0,'control');expected=[]
    for low in values:
        v=((int(low)^salt)+0x9e3779b97f4a7c15)&mask
        v=((v^(v>>30))*0xbf58476d1ce4e5b9)&mask
        v=((v^(v>>27))*0x94d049bb133111eb)&mask
        expected.append(v^(v>>31))
    assert exploration_keys(values,'control').tolist()==expected
    assert len(set(expected))==len(set(map(int,values)))


def test_raw_resume_has_identical_selection_and_exact_coverage(tmp_path):
    first=run_raw(tmp_path/'resume',2**32-67,67,top=5,exploration=4,chunk_size=13,stop_after=29)
    assert first['status']=='PARTIAL' and first['completed_lower32_inputs']==29
    resumed=run_raw(tmp_path/'resume',2**32-67,67,top=5,exploration=4,chunk_size=8,resume=True)
    other=run_raw(tmp_path/'single',2**32-67,67,top=5,exploration=4,chunk_size=17)
    assert resumed['completed_lower32_inputs']==other['completed_lower32_inputs']==67
    assert resumed['selected']==other['selected']
    assert resumed['necessary_missing']==other['necessary_missing']
    with pytest.raises(ValueError,match='identity'):run_raw(tmp_path/'resume',2**32-67,67,top=6,exploration=4,resume=True)
    inputs=prepare_siblings(resumed,(0,1,2**32-1),limit=18)
    assert len(inputs)==len({r['seed'] for r in inputs})==18
    assert all((int(r['seed'])&0xffffffff)==r['low32'] for r in inputs)
    assert any(int(r['seed'])<0 for r in inputs)


@pytest.mark.parametrize('point,nether',[(p,n) for p in [(-698,-698),(697,697),(-2768,-2768),(2766,2766),(0,0),(-1,1)] for n in (False,True)])
def test_integer_center_envelope_matches_fractional_membership(point,nether):
    rect=center_rectangle(point,nether)
    edge=set([-2000,-1999,0,1998,1999])
    if rect:edge.update([rect[0]-1,rect[0],rect[2],rect[2]+1])
    for x in sorted(edge):
        if not -2000<=x<=1999:continue
        for z in (-2000,0,1999):
            actual=contains(point,nether_square((x,z)) if nether else square((x,z),1536))
            predicted=rect is not None and rect[0]<=x<=rect[2] and rect[1]<=z<=rect[3]
            assert actual==predicted


def test_joint_center_rejects_independent_but_incompatible_families():
    assert joint_center_witness([[(-2768,0)],[(2766,0)],[(0,0)],[(0,0)]]) is None
    groups=[[(-700,300)],[(700,300)],[(-100,0)],[(100,0)]]
    center=joint_center_witness(groups)
    assert center is not None
    assert all(any(contains(p,nether_square(center) if j>=2 else square(center,1536)) for p in points) for j,points in enumerate(groups))
