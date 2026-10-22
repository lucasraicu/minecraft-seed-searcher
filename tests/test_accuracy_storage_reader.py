import struct
import pytest
from seed_search.realm.bds_tools.accuracy_storage_reader import parse_biome_key


def test_dimension_tag_is_not_part_of_chunk_coordinate_or_ignored():
    base=struct.pack('<ii',-7,2147483647)
    assert parse_biome_key(base+b'\x2b')==(-7,2147483647,'overworld')
    assert parse_biome_key(base+struct.pack('<i',1)+b'\x2b')==(-7,2147483647,'nether')
    assert parse_biome_key(base+struct.pack('<i',2)+b'\x2b')==(-7,2147483647,'the_end')
    assert parse_biome_key(base+struct.pack('<i',99)+b'\x2b') is None
    assert parse_biome_key(base+b'\x2f\x01') is None
    assert parse_biome_key(base+struct.pack('<i',1)+b'\x2f\x00') is None
    with pytest.raises(TypeError):parse_biome_key('not bytes')
