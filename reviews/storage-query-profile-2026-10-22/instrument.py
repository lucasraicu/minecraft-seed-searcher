"""Disposable process-local profiling instrumentation; no production file edits."""
import cProfile,json,os,pstats,time,zlib,gzip,hashlib
from collections import defaultdict
from pathlib import Path

class Probe:
 def __init__(self):self.rows=defaultdict(lambda:dict(calls=0,wall_seconds=0.,cpu_seconds=0.,input_bytes=0,output_bytes=0));self.restore=[]
 def wrap(self,obj,name,label=None,byte_input=False,byte_output=False):
  old=getattr(obj,name);label=label or name
  def call(*a,**kw):
   start=time.perf_counter();cpu=time.process_time()
   try:result=old(*a,**kw)
   finally:
    row=self.rows[label];row['calls']+=1;row['wall_seconds']+=time.perf_counter()-start;row['cpu_seconds']+=time.process_time()-cpu
    if byte_input and a and isinstance(a[0],(str,bytes,bytearray)):row['input_bytes']+=len(a[0])
   if byte_output and isinstance(result,(str,bytes,bytearray)):row['output_bytes']+=len(result)
   return result
  setattr(obj,name,call);self.restore.append((obj,name,old))
 def start(self):
  self.wrap(json,'loads','json.loads',True);self.wrap(json,'dumps','json.dumps',False,True)
  self.wrap(gzip,'compress','gzip.compress',True,True);self.wrap(zlib,'compress','zlib.compress',True,True)
  self.wrap(os,'fsync','os.fsync');self.wrap(hashlib,'sha256','sha256.initial',True)
  from seed_search.catalog.artifacts import ArtifactStore
  self.wrap(ArtifactStore,'_read_verified_raw','artifact.read_verified',False,True)
  self.wrap(ArtifactStore,'get_json','artifact.get_json');self.wrap(ArtifactStore,'put_json','artifact.put_json')
  old=zlib.decompressobj;probe=self
  class Inflater:
   def __init__(self,obj):self.obj=obj
   def __getattr__(self,k):return getattr(self.obj,k)
   def decompress(self,*a,**kw):
    start=time.perf_counter();cpu=time.process_time();out=self.obj.decompress(*a,**kw);row=probe.rows['zlib.decompress'];row['calls']+=1;row['wall_seconds']+=time.perf_counter()-start;row['cpu_seconds']+=time.process_time()-cpu;row['input_bytes']+=len(a[0]);row['output_bytes']+=len(out);return out
  zlib.decompressobj=lambda *a,**kw:Inflater(old(*a,**kw));self.restore.append((zlib,'decompressobj',old));return self
 def stop(self):
  for o,n,v in reversed(self.restore):setattr(o,n,v)
  return dict(self.rows)

def stats_json(path,limit=65):
 s=pstats.Stats(str(path));rows=[]
 for (file,line,name),(cc,nc,tt,ct,callers) in s.stats.items():rows.append(dict(file=file,line=line,function=name,primitive_calls=cc,total_calls=nc,self_seconds=tt,cumulative_seconds=ct))
 return dict(total_calls=s.total_calls,total_self_seconds=s.total_tt,top_self=sorted(rows,key=lambda x:-x['self_seconds'])[:limit],top_cumulative=sorted(rows,key=lambda x:-x['cumulative_seconds'])[:limit])
