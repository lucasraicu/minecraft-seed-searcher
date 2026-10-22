"""Container-only reader: copy a stopped DB to tmpfs before opening LevelDB.

The host mounts input read-only. Numeric IDs are stored-world IDs, never predictor
IDs. This reader exports bytes only; interpretation is a separate pure module.
"""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile



def parse_biome_key(key):
    if not isinstance(key,bytes):raise TypeError('Expected database key bytes')
    if len(key) not in (9,13) or key[-1]!=0x2b:return None
    cx,cz=struct.unpack('<ii',key[:8])
    number=0 if len(key)==9 else struct.unpack('<i',key[8:12])[0]
    dimension={0:'overworld',1:'nether',2:'the_end'}.get(number)
    if dimension is None:return None
    return cx,cz,dimension


def main():
    import amulet_nbt
    from leveldb import LevelDB
    source = Path('/input')
    raw_level = (source / 'level.dat').read_bytes()
    if len(raw_level) > 4 << 20:
        raise ValueError('Oversized level.dat')
    level = amulet_nbt.load(raw_level[8:], compressed=False, little_endian=True).compound
    result = dict(revision='stopped-biome-export-dimensions-v1', world_identity=dict(
        seed=str(int(level['RandomSeed'])), world_spawn={k:int(level[k]) for k in ('SpawnX','SpawnY','SpawnZ')}, level_dat_sha256=hashlib.sha256(raw_level).hexdigest()), records=[])
    inventory = {}
    total = 0
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / 'db'
        shutil.copytree(source / 'db', target)
        db = LevelDB(str(target))
        try:
            for key, value in db.iterate():
                if len(key) in (9, 10):
                    cx, cz = struct.unpack('<ii', key[:8])
                    entry = inventory.setdefault((cx, cz), dict(cx=cx, cz=cz, tags=set(), subchunks=0))
                    entry['tags'].add(key[8])
                    if key[8] == 0x2f and len(key) == 10:
                        entry['subchunks'] += 1
                    if key[8] == 0x36 and len(value) in (1, 4):
                        entry['finalization'] = int.from_bytes(value, 'little', signed=True)
                parsed=parse_biome_key(key)
                if parsed is None:continue
                total += len(value)
                if len(value) > 1 << 20 or total > 8 << 20 or len(result['records']) >= 4096:
                    raise ValueError('Export cap exceeded')
                cx,cz,dimension=parsed
                result['records'].append(dict(cx=cx, cz=cz, dimension=dimension, key=key.hex(),
                    sha256=hashlib.sha256(value).hexdigest(), data=value.hex()))
        finally:
            db.close()
    result['chunk_inventory'] = [dict(row, tags=sorted(row['tags'])) for _, row in sorted(inventory.items())]
    print(json.dumps(result, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
