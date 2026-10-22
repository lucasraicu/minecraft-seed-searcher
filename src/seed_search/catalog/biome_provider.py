"""Explicit per-chunk saved-runtime biome lookup; never a procedural fallback."""
import copy
from collections.abc import Mapping
from .accuracy import validate_context,context_id,integer
from ..realm.bedrock_biome_storage import decode_data3d,sample_bedrock_runtime


class StoredBiomeProvider:
    def __init__(self,context,records,*,names=None):
        self._context=validate_context(context)
        if self._context['provider']!='bds_saved_runtime_v3':raise ValueError('Expected saved-runtime provider')
        self._id=context_id(self._context)
        self._floor,self._count,self._low,self._high=((-4,25,-64,319) if self._context['dimension']=='overworld' else (0,8,0,127))
        if not isinstance(records,list) or len(records)>256:raise ValueError('Chunk record cap')
        self._chunks={};size=0
        for record in records:
            if not isinstance(record,dict) or set(record)!={'chunk_x','chunk_z','payload'}:raise ValueError('Invalid chunk record')
            key=(integer(record['chunk_x']),integer(record['chunk_z']))
            if key in self._chunks:raise ValueError('Duplicate chunk')
            raw=record['payload']
            if not isinstance(raw,(bytes,bytearray,memoryview)):raise TypeError('Expected chunk bytes')
            n=raw.nbytes if isinstance(raw,memoryview) else len(raw)
            if n>1<<20 or size+n>16<<20:raise ValueError('Chunk byte cap')
            size+=n
            self._chunks[key]=decode_data3d(bytes(raw),floor_section=self._floor,max_sections=self._count)
        if names is not None and not isinstance(names,Mapping):raise ValueError('Expected explicit ID namespace')
        self._names={}
        for key,value in (() if names is None else names.items()):
            integer(key,0,0xffffffff)
            if not isinstance(value,str) or not value or len(value)>256:raise ValueError('Invalid biome name')
            self._names[key]=value

    @property
    def context(self):return copy.deepcopy(self._context)
    @property
    def context_id(self):return self._id
    @property
    def dimension(self):return self._context['dimension']

    def sample(self,x,y,z):
        for n in (x,y,z):integer(n)
        result=dict(status='unknown',raw_id=None,name=None,context_id=self._id,coordinate=[x,y,z],reason=None)
        if not self._low<=y<=self._high:
            result['reason']='y_out_of_bounds';return result
        chunk=self._chunks.get((x//16,z//16))
        if chunk is None:
            result['reason']='missing_chunk';return result
        raw=sample_bedrock_runtime(chunk,x%16,y,z%16)
        if raw is None:
            result['reason']='unresolved';return result
        result.update(status='observed',raw_id=raw,name=self._names.get(raw))
        return result
