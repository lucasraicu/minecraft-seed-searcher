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
    int centroid_x, centroid_z, centroid_score;
    int refinement_grid_step, refinement_coarse_points, refinement_fine_points;
    double refinement_seconds;
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
    unsigned int required_biome_mask; /* Stable 13-family bit positions; v2 only. */
    int cutoff_score;
    int refine_centers; /* v3 only: exhaustive 16 grid plus local 8 grid. */
} NBPolicy;
/* Complete macro inventories and immutable caches; never selected-window replay.
 * Prefix/cache layouts are those produced by the dynamic evaluator. */
typedef struct NBRefinementInput {
    const NBPolicy *policy;
    const NBObservation *macro, *optional;
    const NBPoints *strong;
    const int *palette_prefix, *nether_prefix, *scenic_river;
    const unsigned char *village_sep;
    const int *bastion_variants;
    int bastion_count;
} NBRefinementInput;
typedef struct NBRefinementResult {
    int found, x, z, score, radial_key, grid_step;
    int coarse_points, fine_points;
    double radial, seconds;
} NBRefinementResult;
/* grid_step=0: hierarchical; 16/8: complete declared grid. No generation calls.
 * Returns 0 on success (found may be zero), negative on invalid input/allocation.
 * Output is deterministic across thread counts. */
int nb_dynamic_v3_refine_center(const NBRefinementInput *input, int grid_step,
                                int threads, NBRefinementResult *out);
/* Diagnostic score/radial oracle for arbitrary 8-aligned centers, same checks. */
int nb_dynamic_v3_score_centers(const NBRefinementInput *input, const int *xz,
                              int count, NBRefinementResult *out);
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
const char *ss_source_fingerprint(void);
int nb_dynamic_raw_bounds(const int *fort, int nf, const int *bast, int nb, int fort_goal, int bast_goal, int *feasible);

void nb_diag_reset(void);
void nb_diag_get(uint64_t *out);
