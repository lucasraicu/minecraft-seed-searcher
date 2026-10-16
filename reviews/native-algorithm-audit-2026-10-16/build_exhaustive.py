import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));from scripts import build_blueprint_batch as builder
base=Path(__file__).resolve().parent;builder.ROOT=base/'source';p=builder.ROOT/'native/blueprint_dynamic.inc';s=p.read_text();needle='    nx=nb_dynamic_unique(ex,nx);nz=nb_dynamic_unique(ez,nz);';assert s.count(needle)==1
p.write_text(s.replace(needle,'    for(int v=min_c;v<=max_c;v+=8){nb_dynamic_event(ex,&nx,v,min_c,max_c);nb_dynamic_event(ez,&nz,v,min_c,max_c);}\n'+needle))
try:print(json.dumps(builder.build(base/'exhaustive',openmp_prefix=str(ROOT/'runs/master-implementation-2026-10-10/openmp/install'),cpu_native=True,avx2=True,lto=True)))
finally:p.write_text(s)
