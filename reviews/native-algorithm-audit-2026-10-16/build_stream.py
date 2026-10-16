import sys,re,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));from scripts import build_blueprint_batch as builder
base=Path(__file__).resolve().parent;builder.ROOT=base/'source';p=builder.ROOT/'native/blueprint_dynamic.inc';s=p.read_text();original=s
s=s.replace('if(w->dyn_cells_cap<maxcells) {','if(w->dyn_cells_cap<1) {').replace('size_t need=maxcells+1024;','size_t need=1;')
pattern=r'cells\[ncells\+\+\]=(\(NBDynamicCell\)\{.*?\});'
def sub(m):return 'NBDynamicCell candidate='+m[1]+';\n            if(!ncells || (w->p->dynamic_v2 ? nb_dynamic_cellcmp_v2(&candidate,&cells[0]) : nb_dynamic_cellcmp(&candidate,&cells[0]))<0) cells[0]=candidate;\n            ncells=1;'
s,n=re.subn(pattern,sub,s,flags=re.S);assert n==2,n;p.write_text(s)
try:print(json.dumps(builder.build(base/'stream',openmp_prefix=str(ROOT/'runs/master-implementation-2026-10-10/openmp/install'),cpu_native=True,avx2=True,lto=True)))
finally:p.write_text(original)
