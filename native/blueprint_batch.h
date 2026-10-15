#include <stdint.h>
typedef struct NBPoints { int n; int *xz; } NBPoints;
typedef struct NBObservation {
    int evaluated, full;
    NBPoints raw, viable, floor;
    int *mansion_ids;
} NBObservation;
typedef struct NBAnchor {
    int x, z, count_missing, biome_evaluated, biome_n, score;
    int stronghold_count;
    int stronghold_evaluated;
    unsigned int bonus_biomes;
    unsigned int biome_mask;
    NBObservation observations[13];
    int *biome_xyz, *biome_ids;
    int first_witness[13];
    int nether_biome_n, *nether_biome_xyz, *nether_biome_ids;
    int hub_bonus;
    NBObservation optional[5];
    unsigned int fatal_missing;
    int scenic_bonus;
    int scenic_witness[2];
    int river_witness[2];
    int village_spread_bonus;
    int village_triple[6];
    int treasure_bastion;
    int bastion_count;
    int bastion_coords[16];
    int bastion_variants[8];
    int starter_hub_village[2];
    int deficit_penalty;
    int bonus_total;
    int radial_key;
    int64_t origin_distance_squared;
} NBAnchor;
typedef struct NBResult {
    uint64_t seed;
    int error, nanchors, input_offset;
    NBPoints discovery;
    NBAnchor *anchors;
    double seconds, stage_seconds[15];
} NBResult;
typedef struct NBPolicy {
    uint64_t max_buffer_bytes;
    int discovery[4], types[13], goals[10];
    unsigned int biome_members[256];
    int dark_id, pale_id, y[4], spacing, batch_size, complete;
    int retention, max_misses;
    int locked, overworld_half, nether_half, nether_goal;
    int river, bastion_goal;
    int outpost_goal, structure_order[9];
    int origin, bonus_biome_members[256];
    int fixture_surface[10], fixture_caves[3];
    int two_group, floors[13];
    unsigned int flexible_mask;
    int marine_baseline;
    int dynamic, density_weights[6], nether_ids[5], optional_types[5];
    int dynamic_v2, river_id;
    unsigned char is_scenic[256];
} NBPolicy;
/* Zero-initialized fixed-width decision receipts are hashed without building
 * per-input Python records. They are not persisted as individual rows. */
typedef struct NBVerdict { uint64_t seed; uint32_t anchors, retained; } NBVerdict;
typedef struct NBBatch {
    int count, effective_threads, result_count, error;
    NBResult *results;
    NBVerdict *verdicts;
    uint64_t discovered_anchors, retained_anchors;
} NBBatch;
typedef struct NBFixture { int x, z, missing; uint32_t extra_mask; int deficit_depth; } NBFixture;
NBBatch *nb_sweep(const uint64_t *seeds, int count, const NBPolicy *policy, int threads);
/* Explicit synthetic-provider entry point; never called by the normal sweep. */
NBBatch *nb_fixture_sweep(const uint64_t *seeds, const NBFixture *fixtures,
                        int count, const NBPolicy *policy, int threads);
void nb_free(NBBatch *batch);
int nb_stronghold_after(void);

int ss_openmp_enabled(void);
const char *ss_openmp_library(void);

int nb_dynamic_raw_bounds(const int *fort, int nf, const int *bast, int nb, int fort_goal, int bast_goal, int *feasible);
