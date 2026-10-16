import subprocess
from pathlib import Path
b=Path(__file__).resolve().parent;s=(b/'geometry.c').read_text()
needle='        if(x<xmin)xmin=x;if(z<zmin)zmin=z;if(hx>xmax)xmax=hx;if(hz>zmax)zmax=hz;'
s=s.replace(needle,(b/'tight-change.txt').read_text())
s=s.replace('int f[6],b[8],got[4];','Pos mansions[2]={{rand()%4000-2000,rand()%4000-2000},{rand()%4000-2000,rand()%4000-2000}};int f[6],b[8],got[4];')
s=s.replace('if(nf>=1&&nb>=2){','int mansion=0;for(int m=0;m<2;m++)mansion|=(x-1024<=mansions[m].x&&mansions[m].x<x+1024&&z-1024<=mansions[m].z&&mansions[m].z<z+1024);if(nf>=1&&nb>=2&&mansion){')
s=s.replace('got,NULL,0,0,NULL,1024,512','got,mansions,2,1,NULL,1024,512').replace('Nether co-window grids','Nether plus two-Mansion co-window grids')
(b/'geometry-tight.c').write_text(s)
subprocess.run(['clang','-O1','-g','-fsanitize=address,undefined',str(b/'geometry-tight.c'),'-o',str(b/'geometry-tight')],check=True)
subprocess.run([str(b/'geometry-tight')],check=True)
