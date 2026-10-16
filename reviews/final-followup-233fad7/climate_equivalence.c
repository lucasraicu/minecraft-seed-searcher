#include "generator.h"
#include "biomenoise.c"
#include <stdio.h>
static void reference_seed(BiomeNoise *bn,uint64_t seed,int large) {
    Xoroshiro pxr;xSetSeed(&pxr,seed);
    uint64_t lo=xNextLong(&pxr),hi=xNextLong(&pxr);
    int n=0;for(int i=0;i<NP_MAX;i++)n+=init_climate_seed(&bn->climate[i],bn->oct+n,lo,hi,large,i,-1);
    bn->nptype=-1;
}
int main(void){
    int mismatch=0,checks=0,heap_diff=0;
    Generator a,b;setupGenerator(&a,MC_26_50,0);setupGenerator(&b,MC_26_50,0);
    for(uint64_t seed=0;seed<1000;seed++){
        applySeed(&a,DIM_OVERWORLD,seed);applySeed(&b,DIM_OVERWORLD,seed);reference_seed(&b.bn,seed,0);
        for(int i=0;i<32;i++){
            int x=(int)((seed*1337+i*7919)%4000)-2000,z=(int)((seed*757+i*179)%4000)-2000;
            int y=(int[]){63,-48,0,160}[i%4];
            int actual=getBiomeAt(&a,1,x,y,z),expected=getBiomeAt(&b,1,x,y,z);
            mismatch+=actual!=expected;checks++;
            Range r={1,x,z,1,1,y,1};int *ids=allocCache(&a,r);int err=genBiomes(&a,ids,r);
            heap_diff+=actual!=(err?none:ids[0]);free(ids);
        }
    }
    printf("{\"point_checks\":%d,\"split_seed_mismatches\":%d,\"stack_heap_mismatches\":%d}\n",checks,mismatch,heap_diff);
    return mismatch||heap_diff;
}
