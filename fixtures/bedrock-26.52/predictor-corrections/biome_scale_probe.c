#include "generator.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
int main(void){
 Generator *g=calloc(1,sizeof(*g)); if(!g)return 2;
 setupGenerator(g,MC_26_50,0);
 int64_t s; int x,y,z;
 while(scanf("%" SCNd64 " %d %d %d",&s,&x,&y,&z)==4){
  applySeed(g,DIM_OVERWORLD,(uint64_t)s);
  int qx=x/4-(x<0&&x%4),qy=y/4-(y<0&&y%4),qz=z/4-(z<0&&z%4);
  int direct=getBiomeAt(g,4,qx,qy,qz);
  int interpolated=getBiomeAt(g,1,x,y,z);
  printf("%d %d\n",direct,interpolated);
 }
 free(g);return 0;
}
