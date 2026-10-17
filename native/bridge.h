#include <stdint.h>
typedef struct SeedContext SeedContext;
SeedContext *ss_create(uint64_t seed);
void ss_destroy(SeedContext *ctx);
int ss_openmp_enabled(void);
const char *ss_openmp_library(void);
const char *ss_source_fingerprint(void);
int ss_set_threads(SeedContext *ctx, int threads);
int ss_model(void);
const char *ss_model_name(void);
const char *ss_biome_name(int id);
int ss_biome_catalog(int id, int *dimension, int *generates);
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
int ss_raw_layout(uint32_t low32, int type, int x0, int z0, int x1, int z1, int *xz, int capacity);
int ss_sweep_raw(uint64_t start, uint64_t count, const int *types, const int *bounds,
                 int families, int threads, int *counts, uint64_t capacity);
int ss_biome_points(SeedContext *ctx, int dimension, const int *xyz, int n, int *biomes);
int ss_mineshaft_first(SeedContext *ctx, int x0, int z0, int x1, int z1, int *xz);
int ss_structure_first(SeedContext *ctx, int type, int x0, int z0, int x1, int z1, int *xz);
int ss_structure_count(SeedContext *ctx, int type, int x0, int z0, int x1, int z1, int *xz, int goal);
int ss_mineshaft_inventory(SeedContext *ctx, int x0, int z0, int x1, int z1, int *xz, int capacity);
int ss_nether_pair(SeedContext *ctx, int x0, int z0, int x1, int z1, int *xzt, int *viable, int capacity);
int ss_sweep_raw_mode(uint64_t start, uint64_t count, const int *types, const int *bounds,
                      int families, int threads, int *counts, uint64_t capacity, int mode);
int ss_density_points(SeedContext *ctx, const int *xyz, int n, double *out);

int ss_igloo_basement(SeedContext *ctx, int x, int z);
int ss_bastion_variant(SeedContext *ctx, int x, int z);

int ss_nether_raw_pair(SeedContext *ctx, int x0, int z0, int x1, int z1, int *xzt, int capacity);
