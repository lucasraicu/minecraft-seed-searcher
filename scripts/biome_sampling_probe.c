/* Diagnostic only: never linked into serving/search binaries.
 * Input: signed-64 seed, block x y z. Output: raw-quart and block biome names.
 * Neither sampling path is asserted to be Bedrock's physical-generation oracle.
 */
#include "generator.h"
#include "util.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>

static int parse(char **p, int64_t *out) {
    char *end;
    while (isspace((unsigned char)**p)) ++*p;
    if (!**p) return 0;
    errno = 0;
    intmax_t v = strtoimax(*p, &end, 10);
    if (errno || end == *p || (*end && !isspace((unsigned char)*end)) ||
        v < INT64_MIN || v > INT64_MAX) return 0;
    *p = end; *out = (int64_t)v; return 1;
}

static int quart(int v) { return v / 4 - (v < 0 && v % 4 != 0); }

/* Same explicit enum-name supplements as native/bridge.c:ss_biome_name.
 * This is a predictor name table, never a Bedrock string-ID conversion. */
static const char *name(int id) {
    switch (id) {
        case small_end_islands: return "small_end_islands";
        case end_midlands: return "end_midlands";
        case end_highlands: return "end_highlands";
        case end_barrens: return "end_barrens";
        case grove: return "grove";
        case snowy_slopes: return "snowy_slopes";
        case jagged_peaks: return "jagged_peaks";
        case frozen_peaks: return "frozen_peaks";
        default: return biome2str(MC_26_50, id);
    }
}

int main(void) {
    Generator *g = calloc(1, sizeof(*g));
    if (!g) return 2;
    setupGenerator(g, MC_26_50, 0);
    char line[192];
    unsigned count = 0;
    while (fgets(line, sizeof(line), stdin)) {
        char *p = line;
        int64_t seed, x, y, z;
        if (++count > 4096 || !parse(&p, &seed) || !parse(&p, &x) ||
            !parse(&p, &y) || !parse(&p, &z)) { free(g); return 3; }
        while (isspace((unsigned char)*p)) ++p;
        if (*p || x < -(1LL << 30) || x >= (1LL << 30) ||
            z < -(1LL << 30) || z >= (1LL << 30) || y < -64 || y > 319) {
            free(g); return 3;
        }
        applySeed(g, DIM_OVERWORLD, (uint64_t)seed);
        int raw = getBiomeAt(g, 4, quart((int)x), quart((int)y), quart((int)z));
        int block = getBiomeAt(g, 1, (int)x, (int)y, (int)z);
        const char *a = name(raw), *b = name(block);
        if (!a || !b) { free(g); return 4; }
        printf("%s %s\n", a, b);
    }
    free(g);
    return ferror(stdin) ? 3 : 0;
}
