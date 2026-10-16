import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));from scripts import build_blueprint_batch as builder
base=Path(__file__).resolve().parent;builder.ROOT=base/'source';p=builder.ROOT/'native/blueprint_dynamic.inc';original=p.read_text()
needle='''        if(x<xmin)xmin=x;if(z<zmin)zmin=z;if(hx>xmax)xmax=hx;if(hz>zmax)zmax=hz;'''
replacement='''        if(mansion_goal>0 && mansions && nm>0) {
            for(int m=0;m<nm;m++) {
                int lx=mansions[m].x-(ow_half-1),lz=mansions[m].z-(ow_half-1);
                int ux=mansions[m].x+ow_half,uz=mansions[m].z+ow_half;
                if(lx<x)lx=x;if(lz<z)lz=z;if(ux>hx)ux=hx;if(uz>hz)uz=hz;
                lx=-floordiv(-lx,8)*8;lz=-floordiv(-lz,8)*8;ux=floordiv(ux,8)*8;uz=floordiv(uz,8)*8;
                if(lx>ux||lz>uz)continue;
                mansion_overlap=1;
                if(lx<xmin)xmin=lx;if(lz<zmin)zmin=lz;if(ux>xmax)xmax=ux;if(uz>zmax)zmax=uz;
            }
            continue;
        }
'''+needle
assert original.count(needle)==1;p.write_text(original.replace(needle,replacement))
try:print(json.dumps(builder.build(base/'tight',openmp_prefix=str(ROOT/'runs/master-implementation-2026-10-10/openmp/install'),cpu_native=True,avx2=True,lto=True)))
finally:p.write_text(original)
(base/'tight-change.txt').write_text(replacement)
