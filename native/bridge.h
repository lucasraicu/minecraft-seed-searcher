#include <stdint.h>
typedef struct SeedContext SeedContext;
SeedContext *ss_create(uint64_t seed);
void ss_destroy(SeedContext *ctx);
int ss_model(void);
const char *ss_model_name(void);
const char *ss_biome_name(int id);
int ss_structure_type(const char *name);
int ss_structure_rng(int type);
int ss_biome(SeedContext *ctx, int dimension, int x, int y, int z);
int ss_grid(SeedContext *ctx, int x0, int z0, int nx, int nz, int step,
            int y, int *biomes, double *climate, double *approx_height);
int ss_heights(SeedContext *ctx, const int *xz, int n, int vertical_step,
               int *heights, int *surface_biomes);
int ss_scan(SeedContext *ctx, int type, int x0, int z0, int x1, int z1,
            int viable_only, int *xz, int capacity);
int ss_attempt(SeedContext *ctx, int type, int rx, int rz, int *xz);
int ss_filter_starts(SeedContext *ctx, int type, const int *xz, int n, int *viable);
int ss_diagnostic(SeedContext *ctx, int type, int x, int z, int *out);
int ss_land(SeedContext *ctx, const int *xz, int n, int *land);
