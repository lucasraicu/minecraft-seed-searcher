import copy
import pytest
from seed_search.catalog.codec import pack_summary, unpack_summary, summary_metadata, layout_id, MISSING
from seed_search.catalog.models import SUMMARY_REVISION


def record():
    return {'revision':SUMMARY_REVISION,'observation_id':'a'*64,'world_id':'b'*64,
        'layout_id':layout_id('a'*64,[0,0],8192),'seed':'-9223372036854775808',
        'anchor':[0,0],'border_side':8192,'counts':[[0,1,300,500] for _ in range(14)],
        'structure_nearest_d2':[512**2]*14,'biome_nearest_d2':[MISSING]*9,
        'biome_witness_refs':[MISSING]*9,'complete':[[True,False,True,False] for _ in range(23)]}


def test_independent_packed_offsets_and_size():
    summary=record(); blob=pack_summary(summary)
    assert len(blob)==364
    assert int.from_bytes(blob[8:12],'little')==300
    assert int.from_bytes(blob[12:16],'little')==500
    assert int.from_bytes(blob[224:228],'little')==512**2
    assert int.from_bytes(blob[280:284],'little')==MISSING
    assert blob[352:]==b'\x55'*11+b'\x05'
    assert unpack_summary(blob,summary_metadata(summary))==summary


@pytest.mark.parametrize('mutator',[
    lambda r:r['counts'][0].__setitem__(0,-1),
    lambda r:r['counts'][0].__setitem__(3,1<<32),
    lambda r:r['complete'][0].__setitem__(0,1),
    lambda r:r.__setitem__('seed',0),
    lambda r:r.__setitem__('layout_id','c'*64),
    lambda r:r.__setitem__('border_side',16384),
])
def test_invalid_records_fail_closed(mutator):
    r=record(); mutator(r)
    with pytest.raises(ValueError): pack_summary(r)


def test_reserved_bits_and_truncation():
    r=record(); blob=pack_summary(r)
    for bad in (blob[:-1],blob+b'\0',blob[:-1]+b'\xf5'):
        with pytest.raises(ValueError): unpack_summary(bad,summary_metadata(r))
