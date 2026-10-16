import re,subprocess
from pathlib import Path
base=Path(__file__).resolve().parent;s=(base/'source/native/blueprint_dynamic.inc').read_text()
def extract(name):
 m=re.search(r'^static [^\n]*\b'+name+r'\(',s,re.M);a=m.start();b=s.index('{',a);d=1;e=b+1
 while d:
  d+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
code='''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
typedef struct {int n;int *xz;} NBPoints;
typedef struct {int x,z;} Pos;
static int floordiv(int x,int y){return x/y-(x%y<0);}
'''
for n in ('nb_dynamic_intcmp','nb_dynamic_event','nb_dynamic_unique','nb_dynamic_count','nb_dynamic_floor64','nb_dynamic_snap','nb_dynamic_raw_bounds_core'):code+=extract(n)+'\n'
code+='''int main(void){srand(521);int snaps=200000;
for(int i=0;i<snaps;i++){int lo=rand()%1953-976,hi=lo+rand()%(977-lo),step=(i&1)?8:16,w=1+rand()%100;int64_t sum=(rand()%400001-200000);int v=9999;int ok=nb_dynamic_snap(lo,hi,sum,w,step,&v);int exists=0;for(int x=lo;x<=hi;x++)if(x%step==0)exists=1;assert(ok==exists);if(ok){assert(v>=lo&&v<=hi&&v%step==0);}}
for(int t=0;t<300;t++){int f[6],b[8],got[4];for(int i=0;i<6;i++)f[i]=rand()%1401-700;for(int i=0;i<8;i++)b[i]=rand()%1401-700;NBPoints fp={3,f},bp={4,b};int xmin=9999,zmin=9999,xmax=-9999,zmax=-9999;
for(int x=-976;x<=976;x+=8)for(int z=-976;z<=976;z+=8){int nf=0,nb=0;for(int i=0;i<3;i++)nf+=(x/8-512<=f[2*i]&&f[2*i]<x/8+512&&z/8-512<=f[2*i+1]&&f[2*i+1]<z/8+512);for(int i=0;i<4;i++)nb+=(x/8-512<=b[2*i]&&b[2*i]<x/8+512&&z/8-512<=b[2*i+1]&&b[2*i+1]<z/8+512);assert(nf==nb_dynamic_count(&fp,x,z,512,1,NULL,0));assert(nb==nb_dynamic_count(&bp,x,z,512,1,NULL,0));if(nf>=1&&nb>=2){if(x<xmin)xmin=x;if(x>xmax)xmax=x;if(z<zmin)zmin=z;if(z>zmax)zmax=z;}}
int ok=nb_dynamic_raw_bounds_core(f,3,b,4,1,2,got,NULL,0,0,NULL,1024,512);assert(ok==(xmin<=xmax));if(ok){assert(got[0]==xmin-1024&&got[1]==zmin-1024&&got[2]==xmax+1023&&got[3]==zmax+1023);}}
printf("200000 snap cases; 300 exhaustive 245x245 Nether co-window grids; no assertion failures\\n");return 0;}
'''
(base/'geometry.c').write_text(code)
subprocess.run(['clang','-O1','-g','-fsanitize=address,undefined',str(base/'geometry.c'),'-o',str(base/'geometry')],check=True)
subprocess.run([str(base/'geometry')],check=True)
