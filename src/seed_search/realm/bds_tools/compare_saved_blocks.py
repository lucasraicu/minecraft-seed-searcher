"""Focused Bedrock v8/v9 palette decoder, validated against sampled API blocks.

Format reference: Amulet's BaseLevelDBInterface. This reads only snapshot copies;
unknown encodings, missing chunks or missing subchunks remain explicit unknowns.
"""
from pathlib import Path
import sys,struct,json,tempfile,shutil
import amulet_nbt
from leveldb import LevelDB
def palette_entry(tag):
    entry={'name':tag.compound['name'].py_str,'states':None,'statesError':None}
    try:
        compound=tag.compound['states'];states={}
        for key,value in compound.items():
            kind=type(value).__name__
            if kind=='StringTag':states[key]=value.py_str
            elif kind in ('ByteTag','ShortTag','IntTag','LongTag'):states[key]=value.py_int
            else:raise ValueError('Unsupported state tag '+kind)
        entry['states']=states
    except Exception as error:entry['statesError']=str(error)
    return entry

def decode(data):
    version=data[0]
    if version not in (8,9):raise ValueError('Unsupported subchunk version '+str(version))
    count=data[1];offset=3 if version==9 else 2;layers=[]
    for _ in range(count):
        header=data[offset];offset+=1
        if header&1:raise ValueError('Runtime palette in saved world')
        bits=header>>1
        if bits not in (0,1,2,3,4,5,6,8,16):raise ValueError('Unknown bits '+str(bits))
        if bits:
            per=32//bits;words=(4096+per-1)//per
            packed=struct.unpack_from('<'+'I'*words,data,offset);offset+=4*words
            n=struct.unpack_from('<I',data,offset)[0];offset+=4
        else:packed=();per=0;n=1
        context=amulet_nbt.ReadContext()
        tags=amulet_nbt.load_many(data[offset:],count=n,compressed=False,little_endian=True,read_context=context)
        offset+=context.offset
        names=[palette_entry(tag) for tag in tags]
        if not names:raise ValueError('Empty palette')
        layers.append((bits,per,packed,names))
    if offset!=len(data):raise ValueError('Unexpected trailing data')
    return layers
def entries_at(layers,x,y,z):
    index=(x%16)*256+(z%16)*16+(y%16)
    out=[]
    for bits,per,words,names in layers:
        palette_index=0 if not bits else (words[index//per]>>((index%per)*bits))&((1<<bits)-1)
        out.append(names[palette_index])
    return out
def names_at(layers,x,y,z):
    return [entry['name'] for entry in entries_at(layers,x,y,z)]

def states_match(expected,observed):
    # Return explicit unknown for missing/unsupported saved or API state evidence.
    if not isinstance(expected,dict) or not isinstance(observed,dict):return None
    return expected==observed

def overlay_water(names):
    return any(n in ('minecraft:water','minecraft:flowing_water') for n in names[1:])

def probe_matches(p,names):
    primary=(any(n in ('minecraft:water','minecraft:flowing_water') for n in names) if p.get('waterEither') else bool(names) and names[0]==p['block'])
    return primary and ('waterlogged' not in p or overlay_water(names)==p['waterlogged'])

source=Path(sys.argv[1]);columns=json.loads(Path(sys.argv[2]).read_text())
tmp=Path(tempfile.mkdtemp());shutil.copytree(source,tmp/'world')
db=LevelDB(str(tmp/'world/db'));cache={};matches=0;unknown=[];mismatch=[];overlayWater=0;overlayChecked=0;overlayMatched=0;stateChecked=0;stateMatched=0;stateUnknown=0;probes=0
for col in columns:
    targets=list(col['probes'])
    if col['waterBottom'] is not None:targets.append({'x':col['x'],'y':col['waterBottom'],'z':col['z'],'block':'minecraft:water','waterEither':True})
    for p in targets:
        key=struct.pack('<ii',p['x']//16,p['z']//16)+b'\x2f'+struct.pack('b',p['y']//16)
        if key not in cache:
            try:data=db.get(key)
            except KeyError:data=None
            cache[key]=decode(data) if data is not None else None
        probes+=1
        if cache[key] is None:unknown.append(p);continue
        entries=entries_at(cache[key],p['x'],p['y'],p['z'])
        names=[entry['name'] for entry in entries]
        okay=probe_matches(p,names)
        if 'states' in p:
            state_result=states_match(p['states'],entries[0]['states'] if entries else None)
            if state_result is None:
                stateUnknown+=1;unknown.append({'probe':p,'reason':'API or saved permutation states unavailable','savedEntries':entries});continue
            stateChecked+=1
            if state_result:stateMatched+=1
            okay=okay and state_result
        if 'waterlogged' in p:
            overlayChecked+=1
            if overlay_water(names)==p['waterlogged']:overlayMatched+=1
        if okay:matches+=1
        else:mismatch.append({'probe':p,'savedLayers':names,'savedEntries':entries})
        if any(n in ('minecraft:water','minecraft:flowing_water') for n in names[1:]):overlayWater+=1
db.close();shutil.rmtree(tmp)
print(json.dumps({'probes':probes,'matches':matches,'unknownCount':len(unknown),'mismatches':mismatch,'unknown':unknown,'overlayWaterProbes':overlayWater,'overlayCheckedProbes':overlayChecked,'overlayMatchedProbes':overlayMatched,'stateCheckedProbes':stateChecked,'stateMatchedProbes':stateMatched,'stateUnknownProbes':stateUnknown},indent=2))
