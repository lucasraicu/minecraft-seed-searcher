#define _POSIX_C_SOURCE 200809L
#include "generator.h"
#include "finders.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC,&t);
    return t.tv_sec+t.tv_nsec*1e-9;
}
int main(void) {
    Generator *g=calloc(1,sizeof(*g));
    if(!g)return 2;
    setupGenerator(g,MC_26_50,0);
    char value[128];
    while(fgets(value,sizeof(value),stdin)) {
        uint64_t seed=strtoull(value,NULL,10);
        double begin=now();
        applySeed(g,DIM_OVERWORLD,seed);
        Pos estimate=estimateSpawn(g,NULL);
        double estimate_seconds=now()-begin;
        begin=now();
        applySeed(g,DIM_OVERWORLD,seed);
        Pos detailed=getSpawn(g);
        double detailed_seconds=now()-begin;
        applySeed(g,DIM_OVERWORLD,seed);
        Pos repeat=estimateSpawn(g,NULL);
        printf("{\"seed\":\"%" PRId64 "\",\"estimate\":[%d,%d],\"detailed\":[%d,%d],\"repeat_estimate\":[%d,%d],\"estimate_seconds\":%.9f,\"detailed_seconds\":%.9f}\n",
               (int64_t)seed,estimate.x,estimate.z,detailed.x,detailed.z,repeat.x,repeat.z,estimate_seconds,detailed_seconds);
        fflush(stdout);
    }
    free(g);
    return 0;
}
