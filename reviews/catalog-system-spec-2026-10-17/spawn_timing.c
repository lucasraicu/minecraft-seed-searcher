#define _POSIX_C_SOURCE 200809L
#include "generator.h"
#include "finders.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static double seconds(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}
static uint64_t mix(uint64_t x) {
    x = (x ^ (x >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)) * UINT64_C(0x94d049bb133111eb);
    return x ^ (x >> 31);
}
int main(void) {
    Generator *g = calloc(1, sizeof(*g));
    if (!g) return 1;
    setupGenerator(g, MC_26_50, 0);
    puts("{\"scope\":\"unvalidated vendor spawn routines; CPU time only; no Bedrock ground truth\",\"rows\":[");
    for (int i = 0; i < 32; ++i) {
        uint64_t seed = mix((uint64_t)i + UINT64_C(0x9e3779b97f4a7c15));
        double begin = seconds();
        applySeed(g, DIM_OVERWORLD, seed);
        Pos estimate = estimateSpawn(g, NULL);
        double estimate_s = seconds() - begin;
        double detail_s = -1;
        Pos detailed = {0, 0};
        if (i < 8) {
            begin = seconds();
            applySeed(g, DIM_OVERWORLD, seed);
            detailed = getSpawn(g);
            detail_s = seconds() - begin;
        }
        printf("%s{\"seed_u64\":\"%" PRIu64 "\",\"estimate_x\":%d,\"estimate_z\":%d,\"estimate_seconds_including_apply\":%.9f,\"detailed_x\":%d,\"detailed_z\":%d,\"detailed_seconds_including_apply\":%.9f}",
            i ? ",\n" : "", seed, estimate.x, estimate.z, estimate_s,
            detailed.x, detailed.z, detail_s);
        fflush(stdout);
    }
    puts("\n]}");
    free(g);
    return 0;
}
