"""Runs inside pinned reader image against an owned stopped-world COPY only."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import amulet_nbt
from leveldb import LevelDB

source=Path('/source');target=Path('/output/storage-copy');report=json.loads(Path('/output/report.json').read_text())
if report['status']!='observed'or not report['clean_shutdown']or not report['owned_container_removed']or not report['build_verified']:raise ValueError('Unclean/unbound source')
if target.exists():raise FileExistsError(target)
files=[p for p in source.rglob('*')if p.is_file()]
if any(p.is_symlink()for p in source.rglob('*'))or sum(p.stat().st_size for p in files)>128<<20:raise ValueError('Source copy cap/link')
hashes={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files}
shutil.copytree(source,target)
root=amulet_nbt.load((target/'level.dat').read_bytes()[8:],compressed=False,little_endian=True).compound
seed=str(int(root['RandomSeed']))
if seed!=report['case']['seed']:raise ValueError('Stored seed mismatch')
chunks={tuple(c)for r in report['results']for c in r['chunks']};dimension=0 if report['case']['dimension']=='overworld'else 1
entities=[];missing=[];total=0;records=[];db=LevelDB(str(target/'db'))
try:
    for cx,cz in sorted(chunks):
        prefix=struct.pack('<ii',cx,cz)+(struct.pack('<i',dimension)if dimension else b'')
        try:raw=db.get(prefix+b'\x31')
        except KeyError:missing.append([cx,cz]);continue
        if len(raw)>1<<20:raise ValueError('Record cap')
        total+=len(raw)
        if total>8<<20:raise ValueError('Total NBT cap')
        records.append(dict(chunk=[cx,cz],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        offset=0
        while offset<len(raw):
            context=amulet_nbt.ReadContext()
            tag=amulet_nbt.load(raw[offset:],compressed=False,little_endian=True,read_context=context).compound
            if context.offset<=0:raise ValueError('NBT progress')
            offset+=context.offset
            if len(entities)>=4096:raise ValueError('Entity count cap')
            pos=[int(tag[k])for k in ('x','y','z')]
            if (pos[0]//16,pos[2]//16)!=(cx,cz):raise ValueError('Entity chunk mismatch')
            e=dict(position=pos,id=str(tag.get('id','')),loot_table=str(tag.get('LootTable','')),spawn_entity=str(tag.get('EntityIdentifier','')))
            if 'SpawnData'in tag and not e['spawn_entity']:e['spawn_entity']=str(tag['SpawnData'].get('id',''))
            entities.append(e)
finally:db.close()
if hashes!={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()for p in files}:raise ValueError('Source drift')
print(json.dumps(dict(seed=seed,dimension=dimension,entities=entities,records=records,chunks_without_blockentity_record=missing,source_hashes=hashes,source_unchanged=True)))
