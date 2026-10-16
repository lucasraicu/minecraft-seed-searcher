import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));from scripts import build_blueprint_batch as builder
base=Path(__file__).resolve().parent;builder.ROOT=base/'source';p=builder.ROOT/'native/blueprint_dynamic.inc';h=builder.ROOT/'native/blueprint_batch.h';s=p.read_text();hs=h.read_text()
# This diagnostic build is used ONLY with one native thread.
p.write_text('static double audit_times[16];\nvoid nb_audit_times(double *out){for(int i=0;i<16;i++)out[i]=audit_times[i];}\n'+s.replace('done:\n','done:\n    for(int ai=0;ai<15;ai++)audit_times[ai]+=r->stage_seconds[ai];\n    audit_times[15]+=nb_time()-start;\n'))
h.write_text(hs+'\nvoid nb_audit_times(double *out);\n')
try:print(json.dumps(builder.build(base/'timing',openmp_prefix=str(ROOT/'runs/master-implementation-2026-10-10/openmp/install'),cpu_native=True,avx2=True,lto=True)))
finally:p.write_text(s);h.write_text(hs)
