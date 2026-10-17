#include "generator.h"
#include "biomenoise.h"
#include <stdlib.h>
static Generator g;
void prepare(unsigned long long seed) {setupGenerator(&g,MC_26_50,0);applySeed(&g,DIM_OVERWORLD,seed);}
int biome(int x,int y,int z) {return getBiomeAt(&g,1,x,y,z);}
double climate(int slot,double x,double y,double z) {return sampleDoublePerlin(&g.bn.climate[slot],x,y,z);}
int dark_filter(int x,int z) {return isMansionDarkForestPossible(&g.bn,g.sha,x,z);}
