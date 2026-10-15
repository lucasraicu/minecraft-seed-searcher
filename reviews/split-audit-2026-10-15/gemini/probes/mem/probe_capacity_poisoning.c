#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <signal.h>
#include <sys/resource.h>
#include <unistd.h>

#include "bridge.c"

static int g_target_malloc_fail = 0;
static int g_malloc_count = 0;

static void *tracked_malloc(size_t sz) {
    g_malloc_count++;
    if (g_target_malloc_fail > 0 && g_malloc_count == g_target_malloc_fail) {
        fprintf(stderr, "[FAULT_INJECT] Injected malloc failure at call #%d (%zu bytes)\n", g_malloc_count, sz);
        return NULL;
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

int main(int argc, char **argv) {
    /* Disable core dumps */
    struct rlimit rl = {0, 0};
    setrlimit(RLIMIT_CORE, &rl);

    int test_case = 31; /* Default to call #31: dyn_ex */
    if (argc > 1) {
        test_case = atoi(argv[1]);
    }

    fprintf(stderr, "=== Running Capacity Poisoning Probe (Target malloc #%d) ===\n", test_case);

    NBPolicy policy;
    setup_dynamic_policy(&policy);

    uint64_t allocated_bytes = 1024;
    NBWorker w = {0};
    w.ctx = ss_create(0);
    w.p = &policy;
    w.allocated_bytes = &allocated_bytes;

    NBFixture fix = {0, 0, -1, 0, 1};
    w.fixture = &fix;

    NBResult r0 = {0};
    NBResult r1 = {0};

    /* Phase 1: Run Seed 0 with targeted malloc failure */
    g_target_malloc_fail = test_case;
    g_malloc_count = 0;
    int code0 = nb_eval_dynamic(&w, 12345ULL, &r0);
    fprintf(stderr, "Seed 0 result: code=%d, dyn_ex=%p, dyn_ez=%p, dyn_ex_cap=%zu, dyn_cells=%p, dyn_cells_cap=%zu\n",
            code0, (void*)w.dyn_ex, (void*)w.dyn_ez, w.dyn_ex_cap, (void*)w.dyn_cells, w.dyn_cells_cap);

    if (code0 != -3) {
        fprintf(stderr, "Unexpected: Seed 0 did not return -3 (got %d)\n", code0);
        return 1;
    }

    fprintf(stderr, "State inspection after failed Seed 0:\n");
    if (test_case == 31) {
        fprintf(stderr, "  dyn_ex: %p (expected NULL due to failure)\n", (void*)w.dyn_ex);
        fprintf(stderr, "  dyn_ex_cap: %zu (POISONED: non-zero despite NULL pointer!)\n", w.dyn_ex_cap);
    } else if (test_case == 32) {
        fprintf(stderr, "  dyn_ex: %p (LEAKED: allocated but ez failed!)\n", (void*)w.dyn_ex);
        fprintf(stderr, "  dyn_ez: %p (expected NULL due to failure)\n", (void*)w.dyn_ez);
        fprintf(stderr, "  dyn_ex_cap: %zu (POISONED: non-zero despite NULL pointer!)\n", w.dyn_ex_cap);
    } else if (test_case == 33) {
        fprintf(stderr, "  dyn_cells: %p (expected NULL due to failure)\n", (void*)w.dyn_cells);
        fprintf(stderr, "  dyn_cells_cap: %zu (POISONED: non-zero despite NULL pointer!)\n", w.dyn_cells_cap);
    }

    /* Phase 2: Run Seed 1 on the SAME reused worker with NO malloc failures */
    fprintf(stderr, "Now executing Seed 1 on reused worker...\n");
    fflush(stderr);
    g_target_malloc_fail = 0; /* All subsequent mallocs succeed */
    
    int code1 = nb_eval_dynamic(&w, 12345ULL, &r1);
    fprintf(stderr, "Seed 1 result: code=%d (SURVIVED without crash)\n", code1);

    return 0;
}
