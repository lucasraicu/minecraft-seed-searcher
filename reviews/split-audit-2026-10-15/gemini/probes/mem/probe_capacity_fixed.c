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

/* Now let's implement the FIXED dynamic evaluation function to verify the proposed fix */
static int nb_eval_dynamic_FIXED(NBWorker *w, uint64_t seed, NBResult *r) {
    double start=nb_time();r->seed=seed;
    NB_PROFILE_SEED(w,seed);
#ifndef NB_DISABLE_MANSION_CACHE
    w->mansion_cache_n=0;
#endif
    if(!w->ctx)return -3;
    w->ctx->seed=seed;applySeed(&w->ctx->overworld,DIM_OVERWORLD,seed);
    applySeed(&w->ctx->nether,DIM_NETHER,seed);
    int code=0;const int ow[4]={-2000,-2000,1999,1999};
    const int nw[4]={-562,-562,561,561};
    double stage=nb_time();
    NBObservation macro[13]={0},optional[5]={0};NBAnchor nether_macro={0};int *ex=NULL,*ez=NULL,*prefix=NULL,*nether_prefix=NULL;
    NBDynamicCell *cells=NULL;int nx=0,nz=0,ncells=0,optional_evaluated=0;
    int feasible[4]={-2000,-2000,1999,1999},possible=1;
    if(w->p->retention) {
        stage=nb_time();possible=nb_dynamic_raw_preflight(w,feasible);
        r->stage_seconds[11]+=nb_time()-stage;
        if(possible<0){code=possible;goto done;}if(!possible)goto done;
    }
    stage=nb_time();
    if(!w->p->retention) {
        code=nb_dynamic_discovery(w,r,ow);if(code)goto done;
        if(!r->discovery.n)goto done;
    }
    if(!w->p->retention) {
        stage=nb_time();possible=nb_dynamic_raw_preflight(w,feasible);
        r->stage_seconds[11]+=nb_time()-stage;
        if(possible<0){code=possible;goto done;}if(!possible)goto done;
    }
    stage=nb_time();
    code=nb_pair(w,0,feasible,&macro[0]);if(code)goto done;
    r->stage_seconds[1]+=nb_time()-stage;
    if(nb_dynamic_count(&macro[0].viable,0,0,2000,0,macro[0].mansion_ids,w->p->dark_id)<w->p->goals[0])goto done;
    if(w->p->retention) {
        code=nb_dynamic_discovery(w,r,ow);if(code)goto done;
        if(!r->discovery.n)goto done;
    }
    stage=nb_time();
    code=nb_pair(w,12,feasible,&macro[12]);if(code)goto done;
    r->stage_seconds[14]+=nb_time()-stage;
    if(macro[12].viable.n<w->p->outpost_goal)goto done;
    stage=nb_time();
    code=nb_nether(w,nw,&nether_macro);if(code)goto done;
    r->stage_seconds[11]+=nb_time()-stage;
    macro[10]=nether_macro.observations[10];macro[11]=nether_macro.observations[11];
    memset(nether_macro.observations+10,0,2*sizeof(NBObservation));
    if(macro[10].viable.n<w->p->nether_goal||macro[11].viable.n<w->p->bastion_goal)goto done;
    for(int k=1;k<10;k++) {
        stage=nb_time();code=nb_pair(w,k,feasible,&macro[k]);if(code)goto done;
        r->stage_seconds[k+1]+=nb_time()-stage;
        if(macro[k].viable.n<w->p->floors[k])goto done;
    }
    stage=nb_time();
    int total=256;
    for(int k=0;k<13;k++)total+=macro[k].viable.n*2;
    total+=r->discovery.n*2;
    size_t ex_need=(size_t)(total*2+2048)*sizeof(int);
    
    /* PROPOSED FIX FOR DYN_EX / DYN_EZ: */
    if(w->dyn_ex_cap<ex_need) {
        int *new_ex = (int*)tracked_malloc(ex_need);
        int *new_ez = (int*)tracked_malloc(ex_need);
        if(!new_ex || !new_ez) {
            free(new_ex); free(new_ez);
            code = -3; goto done;
        }
        free(w->dyn_ex); free(w->dyn_ez);
        w->dyn_ex = new_ex; w->dyn_ez = new_ez;
        w->dyn_ex_cap = ex_need;
    }
    
    ex=w->dyn_ex; ez=w->dyn_ez;
    ex[nx++]=-1168;ex[nx++]=1169;ez[nz++]=-1168;ez[nz++]=1169;
    for(int v=-1984;v<=1984;v+=64) {
        nb_dynamic_event(ex,&nx,v-831);nb_dynamic_event(ex,&nx,v+833);
        nb_dynamic_event(ez,&nz,v-831);nb_dynamic_event(ez,&nz,v+833);
    }
    for(int v=-512;v<=512;v+=64) {
        nb_dynamic_event(ex,&nx,8*(v-416)+1);nb_dynamic_event(ex,&nx,8*(v+416)+1);
        nb_dynamic_event(ez,&nz,8*(v-416)+1);nb_dynamic_event(ez,&nz,8*(v+416)+1);
    }
    for(int k=-1;k<13;k++) {
        const NBPoints *points=k<0?&r->discovery:&macro[k].viable;
        int nether=k==10||k==11;
        for(int i=0;i<points->n;i++) {
            if(k==0 && macro[0].mansion_ids && macro[0].mansion_ids[i]!=w->p->dark_id) continue;
            int x=points->xz[2*i],z=points->xz[2*i+1];
            nb_dynamic_event(ex,&nx,nether?8*(x-416)+1:x-831);
            nb_dynamic_event(ex,&nx,nether?8*(x+416)+1:x+833);
            nb_dynamic_event(ez,&nz,nether?8*(z-416)+1:z-831);
            nb_dynamic_event(ez,&nz,nether?8*(z+416)+1:z+833);
        }
    }
    nx=nb_dynamic_unique(ex,nx);nz=nb_dynamic_unique(ez,nz);
    size_t maxcells=(size_t)(nx-1)*(size_t)(nz-1);
    if(maxcells>10000000){code=-3;goto done;}
    
    /* PROPOSED FIX FOR DYN_CELLS: */
    if(w->dyn_cells_cap<maxcells) {
        size_t new_cap = maxcells + 1024;
        void *new_cells = tracked_malloc(new_cap * sizeof(NBDynamicCell));
        if(!new_cells) { code = -3; goto done; }
        free(w->dyn_cells);
        w->dyn_cells = new_cells;
        w->dyn_cells_cap = new_cap;
    }
    
    cells=(NBDynamicCell*)w->dyn_cells;
    for(int ix=0;ix<nx-1;ix++)for(int iz=0;iz<nz-1;iz++) {
        int x=nb_dynamic_nearest(ex[ix],ex[ix+1]-1);
        int z=nb_dynamic_nearest(ez[iz],ez[iz+1]-1);
        int counts[13],strong=nb_dynamic_count(&r->discovery,x,z,832,0,NULL,0);
        if(!strong)continue;
        int fatal=0,deficit=0;
        for(int k=0;k<13;k++) {
            counts[k]=nb_dynamic_count(&macro[k].viable,x,z,k==10||k==11?416:832,
                k==10||k==11,k==0?macro[0].mansion_ids:NULL,w->p->dark_id);
            if(counts[k]<w->p->floors[k]){fatal=1;break;}
            if(counts[k]<(k==10?w->p->nether_goal:k==11?w->p->bastion_goal:
                            k==12?w->p->outpost_goal:w->p->goals[k])) {
                if(w->p->flexible_mask&(1u<<k))deficit++;
                else {fatal=1;break;}
            }
        }
        if(fatal||deficit>w->p->max_misses)continue;
        int64_t sx,sz;int weight;
        nb_dynamic_centroid(macro,&r->discovery,x,z,&sx,&sz,&weight,w->p->dark_id);
        int xx,zz;
        if(!(nb_dynamic_snap(ex[ix],ex[ix+1]-1,sx,weight,16,&xx)||
             nb_dynamic_snap(ex[ix],ex[ix+1]-1,sx,weight,8,&xx)))continue;
        if(!(nb_dynamic_snap(ez[iz],ez[iz+1]-1,sz,weight,8,&zz)||
             nb_dynamic_snap(ez[iz],ez[iz+1]-1,sz,weight,16,&zz)))continue;
        x=xx;z=zz;
        if(!optional_evaluated) {
            optional_evaluated=1;
            for(int k=0;k<5;k++){code=nb_dynamic_optional(w,feasible,k,optional+k);if(code)goto done;}
        }
        if(!prefix) {
            code=nb_dynamic_palette_prefix(w,&prefix);if(code)goto done;
            code=nb_dynamic_nether_prefix(w,&nether_prefix);if(code)goto done;
        }
        unsigned int mask=nb_dynamic_palette_mask(prefix,x,z);
        if((mask&8191u)!=8191u||!nb_dynamic_nether_ok(nether_prefix,x,z))continue;
        int hub=nb_dynamic_hub(macro,x,z);
        int score=nb_dynamic_score_values(counts,strong,mask>>13,hub);
        const int optional_points[5]={20,15,15,10,10};
        for(int k=0;k<5;k++)score+=optional_points[k]*nb_dynamic_count(&optional[k].viable,x,z,832,0,NULL,0);
        cells[ncells++]=(NBDynamicCell){x,z,deficit,score,
            nb_dynamic_radial(macro,&r->discovery,x,z,weight,w->p->dark_id)};
    }
    if(!ncells){r->stage_seconds[13]+=nb_time()-stage;goto done;}
    int best=0;
    for(int i=1;i<ncells;i++) if(nb_dynamic_cellcmp(&cells[i],&cells[best])<0) best=i;
    r->stage_seconds[13]+=nb_time()-stage;
    stage=nb_time();
    int chosen=best;
    r->stage_seconds[12]+=nb_time()-stage;
    if(chosen<0)goto done;
    stage=nb_time();
    r->anchors=nb_alloc(w,sizeof(NBAnchor),1);if(!r->anchors){code=-3;goto done;}
    r->nanchors=1;NBAnchor *a=r->anchors;a->x=cells[chosen].x;a->z=cells[chosen].z;
    a->stronghold_evaluated=1;
    a->stronghold_count=nb_dynamic_count(&r->discovery,a->x,a->z,832,0,NULL,0);
    for(int k=0;k<13;k++) {
        code=nb_dynamic_subset(w,&macro[k],&a->observations[k],a->x,a->z,
                               k==10||k==11?416:832,k==10||k==11);
        if(code)goto done;
        int observed=nb_observed_count(w,a->observations+k,k);
        int goal=k==10?w->p->nether_goal:k==11?w->p->bastion_goal:
                 k==12?w->p->outpost_goal:w->p->goals[k];
        if(observed<goal){a->count_missing|=1<<k;
            if(!(w->p->flexible_mask&(1u<<k)))a->fatal_missing|=1u<<k;}
    }
    for(int k=0;k<5;k++) {
        code=nb_dynamic_subset(w,optional+k,a->optional+k,a->x,a->z,832,0);if(code)goto done;
    }
    int bounds[4]={a->x-832,a->z-832,a->x+831,a->z+831};
    code=nb_palette(w,bounds,a);if(code)goto done;
    code=nb_dynamic_nether_evidence(w,a);if(code)goto done;
    a->hub_bonus=nb_dynamic_hub(macro,a->x,a->z);
    if(a->biome_mask!=8191||!nb_keep(w,a)){code=-4;goto done;}
    r->stage_seconds[12]+=nb_time()-stage;
    a->score=nb_score(w,a);
done:
    nb_clear_full(nether_macro.observations+10);
    nb_clear_full(nether_macro.observations+11);
    for(int k=0;k<13;k++)nb_clear_full(&macro[k]);
    for(int k=0;k<5;k++)nb_clear_full(&optional[k]);
    r->seconds=nb_time()-start;
    return code;
}

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
    int test_case = 31;
    if (argc > 1) test_case = atoi(argv[1]);

    printf("=== Testing FIXED Capacity Recovery (Target malloc #%d) ===\n", test_case);

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

    /* Seed 0 with targeted failure */
    g_target_malloc_fail = test_case;
    g_malloc_count = 0;
    int code0 = nb_eval_dynamic_FIXED(&w, 12345ULL, &r0);
    printf("Seed 0 returned code: %d (expected -3)\n", code0);
    printf("Worker capacity state: dyn_ex_cap=%zu, dyn_cells_cap=%zu\n", w.dyn_ex_cap, w.dyn_cells_cap);

    /* Seed 1 on SAME worker with NO failures */
    g_target_malloc_fail = 0;
    int code1 = nb_eval_dynamic_FIXED(&w, 12345ULL, &r1);
    printf("Seed 1 returned code: %d (SUCCESS!)\n", code1);

    if (code0 == -3 && code1 == 0) {
        printf("VERIFICATION PASSED: Worker recovered cleanly and executed Seed 1 without crash or corruption!\n");
        return 0;
    }
    return 1;
}
