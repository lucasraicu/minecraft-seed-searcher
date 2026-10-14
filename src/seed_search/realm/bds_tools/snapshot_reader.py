"""Inspect a temporary copy of a stopped-world snapshot, never a live DB."""
from pathlib import Path
import sys,json,struct,tempfile,shutil
import amulet_nbt
from leveldb import LevelDB
src=Path(sys.argv[1]);regions=json.loads(Path(sys.argv[2]).read_text())
with tempfile.TemporaryDirectory() as tmp:
    tmp_path=Path(tmp);shutil.copytree(src,tmp_path/'world')
    root=amulet_nbt.load((tmp_path/'world/level.dat').read_bytes()[8:],compressed=False,little_endian=True).compound
    db=LevelDB(str(tmp_path/'world/db'));chunks={}
    try:
        for key,value in db.iterate():
            if len(key) not in (9,10):continue
            cx,cz=struct.unpack('<ii',key[:8]);tag=key[8]
            if tag not in (0x2c,0x2f,0x36):continue
            c=chunks.setdefault((cx,cz),{})
            if tag==0x36:c['finalization']=int.from_bytes(value,'little',signed=True)
            if tag==0x2f:c.setdefault('subchunks',[]).append(int.from_bytes(key[9:10],'little',signed=True))
        rows=[]
        for q in regions:
            expected=[(x,z) for z in range(q['z0']//16,(q['z0']+q['side']-1)//16+1) for x in range(q['x0']//16,(q['x0']+q['side']-1)//16+1)]
            present=[p for p in expected if p in chunks]
            rows.append({'id':q['id'],'expectedChunks':len(expected),'presentChunks':len(present),'withSubchunks':sum(bool(chunks[p].get('subchunks')) for p in present),'finalized':sum(chunks[p].get('finalization')==2 for p in present),'missing':[list(p) for p in expected if p not in chunks]})
    finally:
        db.close()
    print(json.dumps({'seed':str(int(root['RandomSeed'])),'regions':rows},indent=2))
