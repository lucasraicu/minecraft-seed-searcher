"""Pinned reader: bounded exact block probes in an OWNED stopped-world copy."""
import ast
import json
from pathlib import Path
import struct
import amulet_nbt
from leveldb import LevelDB

request=json.loads(Path('/request.json').read_text());points=request['points']
if not 0<len(points)<=8192 or len({tuple(p)for p in points})!=len(points):raise ValueError('Probe count/duplicates')
if any(len(p)!=3 or any(type(v)is not int for v in p)or not -64<=p[1]<=319 for p in points):raise ValueError('Probe coordinate')
if len({(p[0]//16,p[2]//16)for p in points})>16:raise ValueError('Probe chunk cap')
scope=dict(amulet_nbt=amulet_nbt,struct=struct)
tree=ast.parse(Path('/decoder.py').read_text())
for n in tree.body:
    if isinstance(n,ast.FunctionDef)and n.name in ('palette_entry','decode','entries_at'):
        exec(compile(ast.Module(body=[n],type_ignores=[]),'/decoder.py','exec'),scope)
db=LevelDB('/world/db');cache={};rows=[]
try:
    for x,y,z in points:
        key=struct.pack('<ii',x//16,z//16)+b'\x2f'+struct.pack('b',y//16)
        if key not in cache:
            try:raw=db.get(key)
            except KeyError:raw=None
            cache[key]=scope['decode'](raw)if raw is not None else None
        if cache[key]is None:rows.append(dict(position=[x,y,z],unknown='missing_subchunk'))
        else:rows.append(dict(position=[x,y,z],layers=scope['entries_at'](cache[key],x,y,z)))
finally:db.close()
print(json.dumps(dict(revision='bounded-saved-block-probes-v1',rows=rows,probes=len(rows),subchunks=len(cache))))
