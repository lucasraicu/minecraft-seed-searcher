#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "bridge.c"

static uint64_t g_nb_alloc_total = 0;
static uint64_t g_raw_malloc_total = 0;
static int g_in_eval = 0;

static void *tracked_malloc(size_t sz) {
    if (g_in_eval) {
        g_raw_malloc_total += sz;
        printf("RAW MALLOC: %zu bytes (total raw: %llu)\n", sz, (unsigned long long)g_raw_malloc_total);
    }
    return malloc(sz);
}

#define malloc(sz) tracked_malloc(sz)
#include "blueprint_batch.inc"
#undef malloc

static void setup_dynamic_policy(NBPolicy *p) {
    memset(p, 0, sizeof(*p));
    p->max_buffer_bytes = (uint64_t)256 << 20;
    p->spacing = 64;
    p->batch_size = 16;
    p->dynamic = 1;
    p->locked = 1;
    p->two_group = 1;
    p->overworld_half = 832;
    p->nether_half = 416;
    p->max_misses = 2;
    p->discovery[0] = -2000;
    p->discovery[1] = -2000;
    p->discovery[2] = 1999;
    p->discovery[3] = 1999;
    p->outpost_goal = 2;
    p->nether_goal = 2;
    p->bastion_goal = 2;
    p->retention = 1;

    const int types[13] = {Mansion, Jungle_Pyramid, Desert_Pyramid, Monument, Ancient_City,
                           Village, Trial_Chambers, Ruined_Portal, Shipwreck, Mineshaft,
                           Fortress, Bastion, Outpost};
    memcpy(p->types, types, sizeof(types));

    const int floors[13] = {1, 2, 2, 1, 3, 8, 7, 5, 4, 12, 2, 2, 2};
    memcpy(p->floors, floors, sizeof(floors));
    memcpy(p->goals, floors, 10 * sizeof(int));

    p->flexible_mask = (1u<<1)|(1u<<2)|(1u<<4)|(1u<<5)|(1u<<6)|(1u<<7)|(1u<<8)|(1u<<9);

    const int y[4] = {63, -48, 0, 160};
    memcpy(p->y, y, sizeof(y));

    for (int i = 0; i < 6; i++) p->density_weights[i] = 10;
    for (int i = 0; i < 5; i++) p->nether_ids[i] = nether_wastes + i;
    for (int i = 0; i < 256; i++) p->biome_members[i] = 0x1fff;
}

int main(void) {
    NBPolicy policy;
    setup_dynamic_policy(&policy);

    uint64_t seed = 12345ULL;
    NBFixture fix = {0, 0, -1, 0, 1};

    g_in_eval = 1;
    NBBatch *b = nb_fixture_sweep(&seed, &fix, 1, &policy, 1);
    g_in_eval = 0;

    printf("Batch: count=%d, result_count=%d, error=%d\n", b->count, b->result_count, b->error);
    printf("Total raw malloc: %llu bytes\n", (unsigned long long)g_raw_malloc_total);
    nb_free(b);
    return 0;
}
