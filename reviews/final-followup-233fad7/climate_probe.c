#include "generator.h"
#include "finders.h"
#include <stdio.h>
#include <inttypes.h>
int main(void) {
    Generator g; setupGenerator(&g, MC_26_50, 0);
    uint64_t samples=0,dark=0,miss=0;
    printf("{\"failures\":[");
    for(uint64_t seed=0;seed<10000;seed++) {
        applySeed(&g,DIM_OVERWORLD,seed);
        for(int rx=-2;rx<=1;rx++)for(int rz=-2;rz<=1;rz++) {
            Pos p;
            if(!getStructurePos(Mansion,MC_26_50,seed,rx,rz,&p))continue;
            if(p.x < -2000 || p.x >= 2000 || p.z < -2000 || p.z >= 2000)continue;
            samples++;
            int biome=getBiomeAt(&g,1,p.x,63,p.z);
            if(biome!=dark_forest)continue;
            dark++;
            if(!isMansionDarkForestPossible(&g.bn,g.sha,p.x,p.z)) {
                if(miss<10)printf("%s{\"seed\":\"%" PRIu64 "\",\"x\":%d,\"z\":%d,\"biome\":%d,\"new_gate\":0}",miss?",":"",seed,p.x,p.z,biome);
                miss++;
            }
        }
    }
    printf("],\"samples\":%" PRIu64 ",\"dark_forest\":%" PRIu64 ",\"false_rejections\":%" PRIu64 "}\n",samples,dark,miss);
    return 0;
}
