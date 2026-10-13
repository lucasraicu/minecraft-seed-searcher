/* Bounded diagnostic-only timing histograms. Never used by production builds. */
typedef struct NBTiming {
    uint64_t count, bins[32];
    double total_seconds, min_seconds, max_seconds;
    int max_x, max_y, max_z;
} NBTiming;
typedef struct NBProfileSample {
    uint64_t seed;
    uint64_t mansion_queries, mansion_cache_hits;
    NBTiming stages[30], biome_y[4], biome_ids[256], biome_families[13];
} NBProfileSample;
typedef struct NBProfileBatch {
    NBBatch *batch;
    NBProfileSample *samples;
    int count;
} NBProfileBatch;
NBProfileBatch *nb_profile_sweep(const uint64_t *seeds, int count, const NBPolicy *policy, int threads);
void nb_profile_free(NBProfileBatch *profile);
