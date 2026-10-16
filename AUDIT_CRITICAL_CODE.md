# Minecraft Seed Searcher (`dynamic-envelope-2048-v3`) — Master Critical Codebase Bundle
> **Notice for Claude:**
> This file contains the complete, uncompressed, verbatim source code for all 15 crucial files comprising the `dynamic-envelope-2048-v3` architecture as of commit `9e3f3a7`.
> Below is the executive response to your preliminary findings, followed by the complete source code for each file.

## Executive Clarifications to Claude's Preliminary Findings

1. **Macro Region Union vs. Origin Windows (Finding 1):**
   The macro stage does NOT test an origin-centered `[-1024, 1024]` window. In `native/blueprint_dynamic.inc:880`, `feasible` is initialized to `{-2000, -2000, 1999, 1999}` (the full discovery bounds). In `nb_dynamic_raw_bounds_core` (lines 713–758), `xmin` and `xmax` are computed across all valid raw Nether co-window pairs and set `feasible = [xmin - ow_half, zmin - ow_half, xmax + ow_half - 1, zmax + ow_half - 1]`. It is strictly the union of all feasible windows (spanning up to `[-2000, 2000]`), so seeds with clusters in offset windows are never falsely pruned.

2. **C vs. Python Integer Division Rounding (Finding 2):**
   The C code does NOT use plain `/` or `%` for coordinate math. It calls `floordiv(a, b)` defined in `vendor/cubiomes-bedrock/rng.h:75`:
   ```c
   static inline int32_t floordiv(int32_t a, int32_t b) {
       int32_t q = a / b;
       int32_t r = a % b;
       return q - ((a ^ b) < 0 && !!r);
   }
   ```
   This is branchless flooring division identical to Python's `//` (e.g. `floordiv(-7, 8) == -1`, `floordiv(-9, 8) == -2`). All coordinate downscaling (`C/8`, chunk 16, lattice 64) uses `floordiv`.

3. **Wave 3 Speedup Attribution (Finding 4):**
   You are 100% correct. Under $B=0$ with 0 survivors, the Top-50 tracker remains empty (`cutoff_score = 0`), so the early-abort gates could not have fired during natural sweeps. The 59.2k -> 63.1k jump was run-to-run CPU burst variance and cache warmness, not cutoff pruning.

4. **C Memory Safety & Cell Cap (Q3):**
   In `blueprint_dynamic.inc:1010-1019`, `dyn_ex` and `dyn_ez` grow via temp pointers (`new_ex`, `new_ez`) and check `if (!new_ex || !new_ez) { free(...); code = -3; goto done; }`. For sliding cells, line 1046 enforces a hard cap: `if (maxcells > 10000000) { code = -3; goto done; }` which aborts safely without crashing.

5. **Luxury Biome Arithmetic (Finding 5):**
   The luxury bonus list in Python has 10 luxury scoring buckets totaling 240 pts + threshold bonuses (>=5 gives +10, >=7 gives +25) for 265 pts total. The Outpost floor is 1 with surplus ladder `{0, 15, 30, 40}`.

---

## Table of Contents & Manifest

| # | File Path | Language | Lines | Description |
| :--- | :--- | :--- | :--- | :--- |
| 1 | [`native/blueprint_batch.h`](#file-1) | C | 85 | C11 Header Struct Definitions (NBPolicy, NBCandidate, NBDynamicCell, NBWorker) |
| 2 | [`native/blueprint_dynamic.inc`](#file-2) | C | 1,276 | C11 Dynamic Envelope 2048-v3 Kernel (Stage 1A/1B, Sliding Window, Biome Prefix, Cutoff Pruning) |
| 3 | [`native/blueprint_batch.inc`](#file-3) | C | 651 | C11 OpenMP Multi-Threaded Batch Sweep, Buffer Retention & Memory Manager |
| 4 | [`vendor/cubiomes-bedrock/rng.h`](#file-4) | C | 406 | Cubiomes PRNG & Branchless floordiv(a, b) Definition |
| 5 | [`src/seed_search/realm/config.py`](#file-5) | PYTHON | 494 | Specification Source of Truth: dynamic_v3_blueprint_config(), 14 Hard Floors & Bounds |
| 6 | [`src/seed_search/realm/blueprint.py`](#file-6) | PYTHON | 983 | Python Reference Scoring Oracle: dynamic_v3_score() 1,250 Pts Model & evaluate_dynamic_seed() |
| 7 | [`src/seed_search/realm/dynamic.py`](#file-7) | PYTHON | 421 | Python Spatial Geometry: 256-point Nether Lattice, Centroid Snapping, Scenic, Spread, Bastion |
| 8 | [`src/seed_search/realm/top_tracker.py`](#file-8) | PYTHON | 288 | Top-50 In-Memory Priority Queue, RevStr Lexical Inversion, Tie-Breaking |
| 9 | [`src/seed_search/realm/reports.py`](#file-9) | PYTHON | 568 | Candidate Rescore Idempotence, Dispatch & Serialization (_candidate_rescore) |
| 10 | [`src/seed_search/realm/native_batch.py`](#file-10) | PYTHON | 703 | Python CFFI Engine Wrapper: Prototype, Buffer Decoding & persist_pipeline() |
| 11 | [`scripts/pilot_v3_2048.py`](#file-11) | PYTHON | 245 | Production Sweep Runner with Dynamic Top-50 Cutoff Feedback Loop |
| 12 | [`tests/test_dynamic_v3_2048.py`](#file-12) | PYTHON | 678 | Core Dynamic-Envelope-2048-v3 Verification Suite (17 Tests) |
| 13 | [`web-ui/src/constants/searchProfiles.json`](#file-13) | JSON | 323 | Web UI Profile Registry: dynamic2048 Profile, Floors & Miss Budget |
| 14 | [`web-ui/src/utils/ranking.ts`](#file-14) | TYPESCRIPT | 30 | Web UI Sorting Comparator: Score-First Ordering (compareCandidateRank) |
| 15 | [`tests/web_structure_policy.cjs`](#file-15) | JAVASCRIPT | 252 | Web UI & Backend Policy Contract Test Suite (13 Tests) |

**Total Lines of Crucial Code:** 7,403

---

<a id="file-1"></a>
### File 1: `native/blueprint_batch.h`
> **Purpose:** C11 Header Struct Definitions (NBPolicy, NBCandidate, NBDynamicCell, NBWorker)  
> **Length:** 85 lines | **Language:** C

```c
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
    unsigned int required_biome_mask; /* Stable 13-family bit positions; v2 only. */
    int cutoff_score;
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

void nb_diag_reset(void);
void nb_diag_get(uint64_t *out);

```

---

<a id="file-2"></a>
### File 2: `native/blueprint_dynamic.inc`
> **Purpose:** C11 Dynamic Envelope 2048-v3 Kernel (Stage 1A/1B, Sliding Window, Biome Prefix, Cutoff Pruning)  
> **Length:** 1,276 lines | **Language:** C

```c
/* Exact event-cell selector for the 1664/832 dynamic predictor. */
static uint64_t g_diag_inputs = 0;
static uint64_t g_diag_pass_preflight = 0;
static uint64_t g_diag_pass_mansion_dark = 0;
static uint64_t g_diag_pass_mansion_macro = 0;
static uint64_t g_diag_pass_stronghold_macro = 0;
static uint64_t g_diag_pass_outpost_macro = 0;
static uint64_t g_diag_pass_nether_macro = 0;
static uint64_t g_diag_pass_all_structures_macro = 0;
static uint64_t g_diag_had_candidate_cells = 0;
static uint64_t g_diag_had_floor_cells = 0;
static uint64_t g_diag_had_biome_cells = 0;
static uint64_t g_diag_reached_anchor = 0;

void nb_diag_reset(void) {
    g_diag_inputs = 0;
    g_diag_pass_preflight = 0;
    g_diag_pass_mansion_dark = 0;
    g_diag_pass_mansion_macro = 0;
    g_diag_pass_stronghold_macro = 0;
    g_diag_pass_outpost_macro = 0;
    g_diag_pass_nether_macro = 0;
    g_diag_pass_all_structures_macro = 0;
    g_diag_had_candidate_cells = 0;
    g_diag_had_floor_cells = 0;
    g_diag_had_biome_cells = 0;
    g_diag_reached_anchor = 0;
}

void nb_diag_get(uint64_t *out) {
    out[0] = g_diag_inputs;
    out[1] = g_diag_pass_preflight;
    out[2] = g_diag_pass_mansion_dark;
    out[3] = g_diag_pass_mansion_macro;
    out[4] = g_diag_pass_stronghold_macro;
    out[5] = g_diag_pass_outpost_macro;
    out[6] = g_diag_pass_nether_macro;
    out[7] = g_diag_pass_all_structures_macro;
    out[8] = g_diag_had_candidate_cells;
    out[9] = g_diag_had_floor_cells;
    out[10] = g_diag_had_biome_cells;
    out[11] = g_diag_reached_anchor;
}

typedef struct NBDynamicCell {int x,z,deficits,score;double radial;} NBDynamicCell;
static int nb_dynamic_intcmp(const void *av,const void *bv) {
    int a=*(const int*)av,b=*(const int*)bv;return a<b?-1:a>b;
}
static int nb_dynamic_cellcmp(const void *av,const void *bv) {
    const NBDynamicCell *a=av,*b=bv;
    if(a->deficits!=b->deficits)return a->deficits<b->deficits?-1:1;
    if(a->score!=b->score)return a->score>b->score?-1:1;
    int64_t ar=llround(a->radial*1e6),br=llround(b->radial*1e6);
    if(ar!=br)return ar<br?-1:1;
    int64_t da=(int64_t)a->x*a->x+(int64_t)a->z*a->z;
    int64_t db=(int64_t)b->x*b->x+(int64_t)b->z*b->z;
    if(da!=db)return da<db?-1:1;
    if(a->x!=b->x)return a->x<b->x?-1:1;
    return a->z<b->z?-1:a->z>b->z;
}
static int nb_dynamic_cellcmp_v2(const void *av,const void *bv) {
    const NBDynamicCell *a=av,*b=bv;
    if(a->score!=b->score)return a->score>b->score?-1:1;
    if(a->deficits!=b->deficits)return a->deficits<b->deficits?-1:1;
    int64_t ar=llround(a->radial*1e6),br=llround(b->radial*1e6);
    if(ar!=br)return ar<br?-1:1;
    int64_t da=(int64_t)a->x*a->x+(int64_t)a->z*a->z;
    int64_t db=(int64_t)b->x*b->x+(int64_t)b->z*b->z;
    if(da!=db)return da<db?-1:1;
    if(a->x!=b->x)return a->x<b->x?-1:1;
    return a->z<b->z?-1:a->z>b->z;
}
static int nb_dynamic_nearest(int lo,int hi) {
    return lo<=0&&hi>=0?0:hi<0?hi:lo;
}
static void nb_dynamic_event(int *events,int *n,int value,int min_c,int max_c) {
    if(value>min_c&&value<=max_c)events[(*n)++]=value;
}
static int nb_dynamic_unique(int *events,int n) {
    qsort(events,(size_t)n,sizeof(int),nb_dynamic_intcmp);
    int k=0;for(int i=0;i<n;i++)if(!k||events[i]!=events[k-1])events[k++]=events[i];
    return k;
}
static int nb_dynamic_count(const NBPoints *points,int x,int z,int half,int nether,
                            const int *mansion_ids,int dark_id) {
    int n=0;
    for(int i=0;i<points->n;i++) {
        if(mansion_ids&&mansion_ids[i]!=dark_id)continue;
        int px=points->xz[2*i],pz=points->xz[2*i+1];
        if(nether ? (8*(px-half)<x&&x<=8*(px+half)&&8*(pz-half)<z&&z<=8*(pz+half)) :
                    (x-half<=px&&px<x+half&&z-half<=pz&&pz<z+half))n++;
    }
    return n;
}
static int nb_dynamic_subset(NBWorker *w,const NBObservation *src,NBObservation *dst,
                             int x,int z,int half,int nether) {
    const NBPoints *lists[2]={&src->raw,&src->viable};NBPoints *out[2]={&dst->raw,&dst->viable};
    for(int k=0;k<2;k++) {
        int n=0;const NBPoints *p=lists[k];
        for(int i=0;i<p->n;i++) {
            int px=p->xz[2*i],pz=p->xz[2*i+1];
            if(nether ? (8*(px-half)<x&&x<=8*(px+half)&&8*(pz-half)<z&&z<=8*(pz+half)) :
                        (x-half<=px&&px<x+half&&z-half<=pz&&pz<z+half))n++;
        }
        out[k]->xz=n?nb_alloc(w,(size_t)n*2*sizeof(int),0):NULL;
        if(n&&!out[k]->xz)return -3;
        out[k]->n=n;n=0;
        for(int i=0;i<p->n;i++) {
            int px=p->xz[2*i],pz=p->xz[2*i+1];
            if(nether ? (8*(px-half)<x&&x<=8*(px+half)&&8*(pz-half)<z&&z<=8*(pz+half)) :
                        (x-half<=px&&px<x+half&&z-half<=pz&&pz<z+half)) {
                out[k]->xz[2*n]=px;out[k]->xz[2*n+1]=pz;n++;
            }
        }
    }
    if(src->mansion_ids&&dst->viable.n) {
        dst->mansion_ids=nb_alloc(w,(size_t)dst->viable.n*sizeof(int),0);
        if(!dst->mansion_ids)return -3;
        int j=0;
        for(int i=0;i<src->viable.n;i++) {
            int px=src->viable.xz[2*i],pz=src->viable.xz[2*i+1];
            if(x-half<=px&&px<x+half&&z-half<=pz&&pz<z+half)
                dst->mansion_ids[j++]=src->mansion_ids[i];
        }
    }
    dst->full=dst->evaluated=1;return 0;
}
/* Prefix tables retain all defined lattice witnesses and Y=63 luxury bonuses.
 * Structure viability is not a substitute for a sampled biome witness. */
static int nb_dynamic_palette_prefix(NBWorker *w,int **out) {
    const int side=64;
    if(!w->dyn_prefix) {
        w->dyn_prefix=nb_alloc(w,23*side*side*sizeof(int),0);
        if(!w->dyn_prefix)return -3;
    }
    if(!w->dyn_biome_grid) {
        w->dyn_biome_grid=nb_alloc(w,4*side*side*sizeof(int),0);
        if(!w->dyn_biome_grid)return -3;
    }
    int *prefix=w->dyn_prefix;
    memset(prefix,0,23*side*side*sizeof(int));
    for(int ix=1;ix<64;ix++)for(int iz=1;iz<64;iz++) {
        int x=-1984+(ix-1)*64,z=-1984+(iz-1)*64;
        unsigned int mask=0,bonus=0;
        for(int layer=0;layer<4;layer++) {
            int y=w->p->y[layer],id=nb_point(w,x,y,z);
            w->dyn_biome_grid[layer*side*side+ix*side+iz]=id;
            unsigned int bits=id>=0&&id<256?w->p->biome_members[id]:0;
            mask|=bits&((y==-48||y==0)?7168u:1023u);
            if(y==63&&id>=0&&id<256)bonus=w->p->bonus_biome_members[id];
        }
        mask|=bonus<<13;
        for(int f=0;f<23;f++) {
            int at=f*side*side+ix*side+iz;
            prefix[at]=prefix[at-side]+prefix[at-1]-prefix[at-side-1]+!!(mask&(1u<<f));
        }
    }
    *out=prefix;return 0;
}
static unsigned int nb_dynamic_palette_mask(const int *p,int x,int z,int ow_half) {
    int x0=-floordiv(-((x-ow_half)+1984),64),z0=-floordiv(-((z-ow_half)+1984),64);
    int x1=-floordiv(-((x+ow_half)+1984),64),z1=-floordiv(-((z+ow_half)+1984),64);
    if(x0<0)x0=0;if(z0<0)z0=0;if(x1>63)x1=63;if(z1>63)z1=63;
    unsigned int mask=0;
    for(int f=0;f<23;f++) {
        const int *a=p+f*64*64;
        if(a[x1*64+z1]-a[x0*64+z1]-a[x1*64+z0]+a[x0*64+z0])mask|=1u<<f;
    }
    return mask;
}
static int nb_dynamic_nether_point(NBWorker *w,int x,int z) {
    if(!w->fixture)return ss_biome(w->ctx,DIM_NETHER,x,64,z);
    int k=(floordiv(x,64)+floordiv(z,64))%5;if(k<0)k+=5;
    return w->fixture->missing==29+k?none:w->p->nether_ids[k];
}
static int nb_dynamic_nether_prefix(NBWorker *w,int **out) {
    int nh=w->p->nether_half;
    int side=(nh==512)?22:18;
    int grid_min=(nh==512)?-640:-512;
    size_t needed=(size_t)(5*22*22)*sizeof(int);
    if(!w->dyn_nether_prefix) {
        w->dyn_nether_prefix=nb_alloc(w,needed,0);
        if(!w->dyn_nether_prefix)return -3;
    }
    if(!w->dyn_nether_grid) {
        w->dyn_nether_grid=nb_alloc(w,22*22*sizeof(int),0);
        if(!w->dyn_nether_grid)return -3;
    }
    int *p=w->dyn_nether_prefix;
    memset(p,0,(size_t)(5*side*side)*sizeof(int));
    for(int ix=1;ix<side;ix++)for(int iz=1;iz<side;iz++) {
        int id=nb_dynamic_nether_point(w,grid_min+(ix-1)*64,grid_min+(iz-1)*64);
        w->dyn_nether_grid[ix*side+iz]=id;
        for(int k=0;k<5;k++) {
            int at=k*side*side+ix*side+iz;
            p[at]=p[at-side]+p[at-1]-p[at-side-1]+(id==w->p->nether_ids[k]);
        }
    }
    *out=p;return 0;
}
static int nb_dynamic_nether_ok(const int *p,int x,int z,int nether_half) {
    int side=(nether_half==512)?22:18;
    int offset=(nether_half==512)?5120:4096;
    int half_span=8*nether_half;
    int x0=-floordiv(-(x-half_span+offset),512),z0=-floordiv(-(z-half_span+offset),512);
    int x1=-floordiv(-(x+half_span+offset),512),z1=-floordiv(-(z+half_span+offset),512);
    if(x0<0)x0=0;if(z0<0)z0=0;if(x1>=side)x1=side-1;if(z1>=side)z1=side-1;
    for(int f=0;f<5;f++) {
        const int *a=p+f*side*side;
        if(!(a[x1*side+z1]-a[x0*side+z1]-a[x1*side+z0]+a[x0*side+z0]))return 0;
    }
    return 1;
}
static int nb_dynamic_nether_evidence(NBWorker *w,NBAnchor *a) {
    int nh=w->p->nether_half;
    int side=(nh==512)?22:18;
    int grid_min=(nh==512)?-640:-512;
    int samples_side=(nh==512)?16:13;
    int nsamples=samples_side*samples_side;
    a->nether_biome_xyz=nb_alloc(w,(size_t)nsamples*3*sizeof(int),0);
    a->nether_biome_ids=nb_alloc(w,(size_t)nsamples*sizeof(int),0);
    if(!a->nether_biome_xyz||!a->nether_biome_ids)return -3;
    int half_span=8*nh;
    int x0=-floordiv(-(a->x-half_span),512)*64,z0=-floordiv(-(a->z-half_span),512)*64;
    for(int iz=0;iz<samples_side;iz++)for(int ix=0;ix<samples_side;ix++) {
        int x=x0+ix*64,z=z0+iz*64,k=a->nether_biome_n++;
        a->nether_biome_xyz[3*k]=x;a->nether_biome_xyz[3*k+1]=64;a->nether_biome_xyz[3*k+2]=z;
        int id;
        if(w->dyn_nether_grid && x>=grid_min && x<=grid_min+(side-2)*64 && z>=grid_min && z<=grid_min+(side-2)*64) {
            int gix=(x-grid_min)/64+1,giz=(z-grid_min)/64+1;
            if(gix>=1 && gix<side && giz>=1 && giz<side)id=w->dyn_nether_grid[gix*side+giz];
            else id=nb_dynamic_nether_point(w,x,z);
        } else id=nb_dynamic_nether_point(w,x,z);
        a->nether_biome_ids[k]=id;
    }
    return 0;
}
static int64_t nb_dynamic_floor64(int64_t value,int64_t divisor) {
    int64_t q=value/divisor;return q-(value%divisor<0);
}
static int nb_dynamic_snap(int lo,int hi,int64_t sum,int weight,int step,int *value) {
    int lower=-floordiv(-lo,step)*step,upper=floordiv(hi,step)*step;
    if(lower>upper)return 0;
    int rounded=weight?(int)(nb_dynamic_floor64(sum+(step/2)*weight,(int64_t)step*weight)*step):0;
    *value=rounded<lower?lower:rounded>upper?upper:rounded;return 1;
}
static const int nb_centroid_weights[13]={1,1,1,1,2,3,2,2,1,0,0,0,1};
static const int nb_centroid_weights_v2[13]={1,1,1,1,2,3,2,0,0,0,0,0,1};
static const int nb_centroid_weights_v3[13]={2,2,2,1,2,3,2,0,0,0,0,0,1};
static int nb_dynamic_captured(int px,int pz,int x,int z,int ow_half) {
    return x-ow_half<=px&&px<x+ow_half&&z-ow_half<=pz&&pz<z+ow_half;
}
static void nb_dynamic_centroid(const NBObservation *macro,const NBPoints *strong,int x,int z,
                                int64_t *sx,int64_t *sz,int *weight,int dark_id,const int *weights,int ow_half) {
    *sx=*sz=0;*weight=0;
    for(int k=-1;k<13;k++) {
        int w=k<0?1:weights[k];if(!w)continue;
        const NBPoints *p=k<0?strong:&macro[k].viable;
        for(int i=0;i<p->n;i++) {
            int px=p->xz[2*i],pz=p->xz[2*i+1];
            if(k==0&&macro[0].mansion_ids[i]!=dark_id)continue;
            if(nb_dynamic_captured(px,pz,x,z,ow_half)) {*sx+=(int64_t)w*px;*sz+=(int64_t)w*pz;*weight+=w;}
        }
    }
}
static double nb_dynamic_radial(const NBObservation *macro,const NBPoints *strong,int x,int z,int weight,int dark_id,const int *weights,int ow_half) {
    double distance=0;
    for(int k=-1;k<13;k++) {
        int w=k<0?1:weights[k];if(!w)continue;
        const NBPoints *p=k<0?strong:&macro[k].viable;
        for(int i=0;i<p->n;i++) {
            int px=p->xz[2*i],pz=p->xz[2*i+1];
            if(k==0&&macro[0].mansion_ids[i]!=dark_id)continue;
            if(nb_dynamic_captured(px,pz,x,z,ow_half))distance+=w*hypot((double)px-x,(double)pz-z);
        }
    }
    return weight?distance/weight:0;
}
static int nb_dynamic_hub(const NBObservation *macro,int x,int z,int ow_half) {
    const int slots[5]={5,2,1,12,7};int bonus=0;
    for(int j=0;j<5;j++) {
        const NBPoints *p=&macro[slots[j]].viable;
        for(int i=0;i<p->n;i++) {
            int64_t dx=p->xz[2*i]-x,dz=p->xz[2*i+1]-z;
            if(nb_dynamic_captured(p->xz[2*i],p->xz[2*i+1],x,z,ow_half)&&dx*dx+dz*dz<=512*512)bonus+=j==4?4:6;
        }
    }
    return bonus>40?40:bonus;
}

static int nb_dynamic_v2_core_bonus(const int *counts,int strong) {
    int core=(counts[0]>=2?50:0)+(strong>=2?35:0)+(counts[3]>=2?35:0);
    int v=counts[5];
    core+=(v>=10?25:0)+(v>=11?10:0)+(v>=12?5:0);
    int tc=counts[6];
    core+=(tc>=9?10:0)+(tc>=10?10:0)+(tc>=11?10:0);
    core+=(counts[4]>=5?25:0);
    core+=(counts[2]>=4?20:0);
    core+=(counts[1]>=4?20:0);
    core+=(counts[12]>=3?20:0);
    core+=(counts[10]>=3?20:0);
    core+=(counts[11]>=3?20:0);
    int rp=counts[7];
    core+=(rp>=8?5:0)+(rp>=9?5:0);
    int sw=counts[8];
    core+=(sw>=7?5:0)+(sw>=8?5:0);
    int ms=counts[9];
    core+=(ms>15?(ms>=20?5:ms-15):0);
    return core;
}

static inline int nb_clamp_i32(int val,int lo,int hi) {
    return val<lo?lo:(val>hi?hi:val);
}

static int nb_dynamic_v3_core_bonus(const int *counts,int strong) {
    static const int temple_lut[4] = {0, 25, 45, 60};
    static const int wm_lut[3]     = {0, 55, 85};
    static const int ac_lut[5]     = {0, 20, 40, 55, 65};
    static const int sh_lut[3]     = {0, 20, 50};
    static const int om_lut[4]     = {0, 25, 40, 50};
    static const int ba_lut[4]     = {0, 20, 35, 50};
    static const int ft_lut[4]     = {0, 20, 35, 50};
    static const int vi_lut[6]     = {0, 10, 20, 30, 40, 50};
    static const int op_lut[4]     = {0, 15, 30, 40};
    static const int tc_lut[5]     = {0, 10, 18, 25, 30};

    int score = 0;
    score += wm_lut[nb_clamp_i32(counts[0] - 1, 0, 2)];
    score += temple_lut[nb_clamp_i32(counts[1] - 1, 0, 3)];
    score += temple_lut[nb_clamp_i32(counts[2] - 1, 0, 3)];
    score += om_lut[nb_clamp_i32(counts[3] - 1, 0, 3)];
    score += ac_lut[nb_clamp_i32(counts[4] - 2, 0, 4)];
    score += vi_lut[nb_clamp_i32(counts[5] - 6, 0, 5)];
    score += tc_lut[nb_clamp_i32(counts[6] - 8, 0, 4)];
    score += nb_clamp_i32(counts[7] - 8, 0, 4) * 5;
    score += nb_clamp_i32(counts[8] - 4, 0, 4) * 5;
    score += nb_clamp_i32(counts[9] - 10, 0, 10) * 2;
    score += ft_lut[nb_clamp_i32(counts[10] - 1, 0, 3)];
    score += ba_lut[nb_clamp_i32(counts[11] - 2, 0, 3)];
    score += op_lut[nb_clamp_i32(counts[12] - 1, 0, 3)];
    score += sh_lut[nb_clamp_i32(strong - 1, 0, 2)];
    return score;
}

static int nb_dynamic_v2_deficit_penalty(const int *counts,const int *goals,int outpost_goal,int *deficits_out) {
    int penalty=0,defs=0;
    if(counts[7]<goals[7]){penalty+=5;defs++;}
    if(counts[8]<goals[8]){penalty+=5;defs++;}
    if(counts[5]<goals[5]){penalty+=10;defs++;}
    if(counts[6]<goals[6]){penalty+=10;defs++;}
    if(counts[4]<goals[4]){penalty+=10;defs++;}
    if(counts[2]<goals[2]){penalty+=10;defs++;}
    if(counts[1]<goals[1]){penalty+=10;defs++;}
    if(counts[9]<goals[9]){penalty+=10;defs++;}
    if(counts[0]<goals[0]){penalty+=10;defs++;}
    if(counts[3]<goals[3]){penalty+=10;defs++;}
    if(counts[12]<outpost_goal){penalty+=10;defs++;}
    if(deficits_out)*deficits_out=defs;
    return penalty;
}

static int nb_dynamic_v2_optional(const int *opt_counts,int treasure_bastion) {
    int opt=(opt_counts[0]>=1?20:0)+(opt_counts[0]>=2?10:0);
    opt+=(opt_counts[1]>=1?10:0)+(opt_counts[1]>=2?5:0);
    opt+=(opt_counts[2]>=1?15:0)+(opt_counts[2]>=2?10:0);
    opt+=(opt_counts[3]>=1?10:0)+(opt_counts[3]>=2?10:0);
    opt+=(opt_counts[4]>=4?24:opt_counts[4]*6);
    opt+=(treasure_bastion?15:0);
    return opt;
}

static int nb_dynamic_v2_biome_bonus(unsigned int bonus) {
    const int points[10]={25,20,25,25,15,10,10,15,15,15};
    int score=0;
    for(int i=0;i<10;i++)if(bonus&(1u<<i))score+=points[i];
    return score;
}

static int nb_dynamic_v2_hub(const NBObservation *macro,int x,int z,int *nearest_village,int ow_half) {
    int v_hub=0;
    int best_d2=512*512+1;
    int best_vx=0,best_vz=0;
    const NBPoints *vp=&macro[5].viable;
    for(int i=0;i<vp->n;i++) {
        int px=vp->xz[2*i],pz=vp->xz[2*i+1];
        if(nb_dynamic_captured(px,pz,x,z,ow_half)) {
            int64_t dx=px-x,dz=pz-z;
            int64_t d2=dx*dx+dz*dz;
            if(d2<=256*256)v_hub=10;
            else if(d2<=512*512&&v_hub<6)v_hub=6;
            if(d2<=512*512) {
                if((int)d2<best_d2||((int)d2==best_d2&&(px<best_vx||(px==best_vx&&pz<best_vz)))) {
                    best_d2=(int)d2;best_vx=px;best_vz=pz;
                }
            }
        }
    }
    if(nearest_village) {
        if(best_d2<=512*512){nearest_village[0]=best_vx;nearest_village[1]=best_vz;}
        else{nearest_village[0]=0;nearest_village[1]=0;}
    }
    int other=0;
    const int other_slots[3]={2,1,12};
    for(int j=0;j<3;j++) {
        const NBPoints *p=&macro[other_slots[j]].viable;
        for(int i=0;i<p->n;i++) {
            int px=p->xz[2*i],pz=p->xz[2*i+1];
            if(nb_dynamic_captured(px,pz,x,z,ow_half)) {
                int64_t dx=px-x,dz=pz-z;
                if(dx*dx+dz*dz<=512*512){other+=6;if(other>=30){other=30;goto done_other;}}
            }
        }
    }
    {
        const NBPoints *p=&macro[7].viable;
        for(int i=0;i<p->n;i++) {
            int px=p->xz[2*i],pz=p->xz[2*i+1];
            if(nb_dynamic_captured(px,pz,x,z,ow_half)) {
                int64_t dx=px-x,dz=pz-z;
                if(dx*dx+dz*dz<=512*512){other+=4;if(other>=30){other=30;goto done_other;}}
            }
        }
    }
done_other:
    return v_hub+(other>30?30:other);
}

static int nb_dynamic_v3_optional(const int *opt_counts) {
    static const int hut_lut[4]   = {0, 30, 50, 60};
    static const int trail_lut[4] = {0, 25, 40, 50};
    static const int igloo_lut[3] = {0, 25, 40};
    static const int or_lut[3]    = {0, 10, 20};
    static const int bt_lut[5]    = {0, 10, 20, 25, 30};

    int score = hut_lut[nb_clamp_i32(opt_counts[0], 0, 3)]
              + igloo_lut[nb_clamp_i32(opt_counts[1], 0, 2)]
              + trail_lut[nb_clamp_i32(opt_counts[2], 0, 3)]
              + or_lut[nb_clamp_i32(opt_counts[3], 0, 2)]
              + bt_lut[nb_clamp_i32(opt_counts[4], 0, 4)];
    return score;
}

static int nb_dynamic_v3_biome_bonus(unsigned int bonus) {
    static const int points[10] = {25, 35, 40, 35, 20, 15, 10, 20, 25, 15};
    int score = 0, n_lux = 0;
    for(int i = 0; i < 10; i++) {
        if(bonus & (1u << i)) {
            score += points[i];
            n_lux++;
        }
    }
    if(n_lux >= 7) score += 25;
    else if(n_lux >= 5) score += 10;
    return score;
}

static int nb_dynamic_v3_hub(const NBObservation *macro,int x,int z,int *nearest_village,int ow_half) {
    int v_hub = 0;
    int best_d2 = 512*512 + 1, best_vx = 0, best_vz = 0;
    const NBPoints *vp = &macro[5].viable;
    for(int i = 0; i < vp->n; i++) {
        int px = vp->xz[2*i], pz = vp->xz[2*i+1];
        if(nb_dynamic_captured(px, pz, x, z, ow_half)) {
            int64_t dx = px - x, dz = pz - z;
            int64_t d2 = dx*dx + dz*dz;
            if(d2 <= 256*256) v_hub = 15;
            else if(d2 <= 512*512 && v_hub < 10) v_hub = 10;
            if(d2 <= 512*512 && ((int)d2 < best_d2 || ((int)d2 == best_d2 && (px < best_vx || (px == best_vx && pz < best_vz))))) {
                best_d2 = (int)d2; best_vx = px; best_vz = pz;
            }
        }
    }
    if(nearest_village) {
        if(best_d2 <= 512*512) { nearest_village[0] = best_vx; nearest_village[1] = best_vz; }
        else { nearest_village[0] = 0; nearest_village[1] = 0; }
    }
    int other = 0;
    const int other_slots[4] = {2, 1, 12, 4};
    for(int j = 0; j < 4; j++) {
        const NBPoints *p = &macro[other_slots[j]].viable;
        for(int i = 0; i < p->n; i++) {
            int px = p->xz[2*i], pz = p->xz[2*i+1];
            if(nb_dynamic_captured(px, pz, x, z, ow_half)) {
                int64_t dx = px - x, dz = pz - z;
                if(dx*dx + dz*dz <= 512*512) {
                    other += 6;
                    if(other >= 30) { other = 30; goto done_v3_hub; }
                }
            }
        }
    }
    {
        const NBPoints *p = &macro[7].viable;
        for(int i = 0; i < p->n; i++) {
            int px = p->xz[2*i], pz = p->xz[2*i+1];
            if(nb_dynamic_captured(px, pz, x, z, ow_half)) {
                int64_t dx = px - x, dz = pz - z;
                if(dx*dx + dz*dz <= 512*512) {
                    other += 4;
                    if(other >= 30) { other = 30; goto done_v3_hub; }
                }
            }
        }
    }
done_v3_hub:
    return v_hub + (other > 30 ? 30 : other);
}

static int nb_dynamic_v3_nether_core(const NBObservation *macro, int x, int z) {
    int pnx = floordiv(x, 8), pnz = floordiv(z, 8);
    int bonus = 0;
    const NBPoints *fort = &macro[10].viable;
    for(int i = 0; i < fort->n; i++) {
        int64_t dx = fort->xz[2*i] - pnx, dz = fort->xz[2*i+1] - pnz;
        if(dx*dx + dz*dz <= 256*256) { bonus += 10; break; }
    }
    const NBPoints *bast = &macro[11].viable;
    for(int i = 0; i < bast->n; i++) {
        int64_t dx = bast->xz[2*i] - pnx, dz = bast->xz[2*i+1] - pnz;
        if(dx*dx + dz*dz <= 256*256) { bonus += 10; break; }
    }
    return bonus;
}

static const int nb_river_offsets[13][2]={
    {-2,0},{-1,-1},{-1,0},{-1,1},
    {0,-2},{0,-1},{0,0},{0,1},{0,2},
    {1,-1},{1,0},{1,1},{2,0}
};

static int nb_dynamic_build_scenic_cache(NBWorker *w) {
    if(!w->dyn_scenic_river) {
        w->dyn_scenic_river=(int*)nb_alloc(w,64*64*sizeof(int),1);
        if(!w->dyn_scenic_river)return -3;
        w->dyn_scenic_river_cap=64*64*sizeof(int);
    }
    int *cache=w->dyn_scenic_river;
    memset(cache,0,64*64*sizeof(int));
    for(int ix=1;ix<=63;ix++)for(int iz=1;iz<=63;iz++) {
        int id=w->dyn_biome_grid[0*64*64+ix*64+iz];
        if(id>=0&&id<256&&w->p->is_scenic[id]) {
            int best_rx=9999,best_rz=9999;
            for(int t=0;t<13;t++) {
                int rix=ix+nb_river_offsets[t][0],riz=iz+nb_river_offsets[t][1];
                if(rix>=1&&rix<=63&&riz>=1&&riz<=63) {
                    int rid=w->dyn_biome_grid[0*64*64+rix*64+riz];
                    if(rid==w->p->river_id) {
                        int rx=-1984+(rix-1)*64,rz=-1984+(riz-1)*64;
                        if(rx<best_rx||(rx==best_rx&&rz<best_rz)){best_rx=rx;best_rz=rz;}
                    }
                }
            }
            if(best_rx!=9999) {
                int rix=(best_rx+1984)/64+1,riz=(best_rz+1984)/64+1;
                cache[ix*64+iz]=0x10000|(rix<<8)|riz;
            }
        }
    }
    return 0;
}

static int nb_dynamic_check_scenic_pair(NBWorker *w,int cx,int cz,int *scenic_wit,int *river_wit,int ow_half) {
    if(!w->dyn_scenic_river)return 0;
    int min_ix=floordiv(cx-192+1984,64)+1,max_ix=floordiv(cx+192+1984,64)+1;
    int min_iz=floordiv(cz-192+1984,64)+1,max_iz=floordiv(cz+192+1984,64)+1;
    if(min_ix<1)min_ix=1;if(max_ix>63)max_ix=63;
    if(min_iz<1)min_iz=1;if(max_iz>63)max_iz=63;
    int best_sx=9999,best_sz=9999,best_rx=9999,best_rz=9999;
    for(int ix=min_ix;ix<=max_ix;ix++) {
        int sx=-1984+(ix-1)*64;
        for(int iz=min_iz;iz<=max_iz;iz++) {
            int sz=-1984+(iz-1)*64;
            int64_t dx=sx-cx,dz=sz-cz;
            if(dx*dx+dz*dz<=192*192&&nb_dynamic_captured(sx,sz,cx,cz,ow_half)) {
                int entry=w->dyn_scenic_river[ix*64+iz];
                if(entry&0x10000) {
                    int rix=(entry>>8)&0xff,riz=entry&0xff;
                    int rx=-1984+(rix-1)*64,rz=-1984+(riz-1)*64;
                    if(nb_dynamic_captured(rx,rz,cx,cz,ow_half)) {
                        if(sx<best_sx||(sx==best_sx&&sz<best_sz)){
                            best_sx=sx;best_sz=sz;best_rx=rx;best_rz=rz;
                        }
                    }
                }
            }
        }
    }
    if(best_sx!=9999) {
        if(scenic_wit){scenic_wit[0]=best_sx;scenic_wit[1]=best_sz;}
        if(river_wit){river_wit[0]=best_rx;river_wit[1]=best_rz;}
        return 1;
    }
    return 0;
}

static int nb_dynamic_build_village_cache(NBWorker *w,const NBPoints *villages) {
    int n=villages->n;if(n<=0)return 0;
    size_t need=(size_t)n*(size_t)n;
    if(w->dyn_village_sep_cap<need) {
        unsigned char *new_sep=(unsigned char*)nb_alloc(w,need,0);
        if(!new_sep)return -3;
        free(w->dyn_village_sep);
        w->dyn_village_sep=new_sep;
        w->dyn_village_sep_cap=need;
    }
    for(int i=0;i<n;i++) {
        int ix=villages->xz[2*i],iz=villages->xz[2*i+1];
        for(int j=0;j<n;j++) {
            int64_t dx=ix-villages->xz[2*j],dz=iz-villages->xz[2*j+1];
            w->dyn_village_sep[i*n+j]=(dx*dx+dz*dz>=256*256);
        }
    }
    return 0;
}

static int nb_dynamic_check_village_spread(NBWorker *w,const NBPoints *villages,int cx,int cz,int *triple_out,int ow_half) {
    int n=villages->n;if(n<3||!w->dyn_village_sep)return 0;
    int q_indices[4][64];int q_count[4]={0,0,0,0};
    for(int i=0;i<n;i++) {
        int px=villages->xz[2*i],pz=villages->xz[2*i+1];
        if(nb_dynamic_captured(px,pz,cx,cz,ow_half)) {
            int q=(px>=cx?(pz>=cz?0:3):(pz>=cz?1:2));
            if(q_count[q]<64)q_indices[q][q_count[q]++]=i;
        }
    }
    int occupied=(q_count[0]>0)+(q_count[1]>0)+(q_count[2]>0)+(q_count[3]>0);
    if(occupied<3)return 0;
    static const int quad_combos[4][3]={{0,1,2},{0,1,3},{0,2,3},{1,2,3}};
    int found=0;int best_triple[6];
    for(int c=0;c<4;c++) {
        int qa=quad_combos[c][0],qb=quad_combos[c][1],qc=quad_combos[c][2];
        if(!q_count[qa]||!q_count[qb]||!q_count[qc])continue;
        for(int ia=0;ia<q_count[qa];ia++) {
            int idx_a=q_indices[qa][ia];
            for(int ib=0;ib<q_count[qb];ib++) {
                int idx_b=q_indices[qb][ib];
                if(!w->dyn_village_sep[idx_a*n+idx_b])continue;
                for(int ic=0;ic<q_count[qc];ic++) {
                    int idx_c=q_indices[qc][ic];
                    if(w->dyn_village_sep[idx_a*n+idx_c]&&w->dyn_village_sep[idx_b*n+idx_c]) {
                        int cur[3][2]={{villages->xz[2*idx_a],villages->xz[2*idx_a+1]},
                                       {villages->xz[2*idx_b],villages->xz[2*idx_b+1]},
                                       {villages->xz[2*idx_c],villages->xz[2*idx_c+1]}};
                        for(int i=0;i<2;i++)for(int j=i+1;j<3;j++) {
                            if(cur[i][0]>cur[j][0]||(cur[i][0]==cur[j][0]&&cur[i][1]>cur[j][1])) {
                                int tx=cur[i][0],tz=cur[i][1];
                                cur[i][0]=cur[j][0];cur[i][1]=cur[j][1];
                                cur[j][0]=tx;cur[j][1]=tz;
                            }
                        }
                        int flat[6]={cur[0][0],cur[0][1],cur[1][0],cur[1][1],cur[2][0],cur[2][1]};
                        if(!found){memcpy(best_triple,flat,6*sizeof(int));found=1;}
                        else {
                            for(int k=0;k<6;k++) {
                                if(flat[k]<best_triple[k]){memcpy(best_triple,flat,6*sizeof(int));break;}
                                else if(flat[k]>best_triple[k])break;
                            }
                        }
                    }
                }
            }
        }
    }
    if(found) {
        if(triple_out)memcpy(triple_out,best_triple,6*sizeof(int));
        return 1;
    }
    return 0;
}

static int nb_dynamic_build_bastion_cache(NBWorker *w,const NBPoints *bastions) {
    int n=bastions->n;if(n>32)return -3;w->dyn_bastion_n=n;
    for(int i=0;i<n;i++) {
        int v=ss_bastion_variant(w->ctx,bastions->xz[2*i],bastions->xz[2*i+1]);
        if(v<0)return -4;
        w->dyn_bastion_variants[i]=v;
    }
    return 0;
}

static int nb_dynamic_check_treasure_bastion(NBWorker *w,const NBPoints *bastions,int cx,int cz) {
    int n=w->dyn_bastion_n;
    int nh=w->p->nether_half;
    for(int i=0;i<n;i++) {
        int bx=bastions->xz[2*i],bz=bastions->xz[2*i+1];
        if(8*(bx-nh)<cx&&cx<=8*(bx+nh)&&8*(bz-nh)<cz&&cz<=8*(bz+nh)) {
            if(w->dyn_bastion_variants[i]==2)return 1;
        }
    }
    return 0;
}
static int nb_dynamic_optional(NBWorker *w,const int *bounds,int slot,NBObservation *o) {
    o->full=o->evaluated=1;
    if(w->fixture)return 0;
    int code=nb_capacity(w,bounds);if(code)return code;
    int n=ss_scan(w->ctx,w->p->optional_types[slot],bounds[0],bounds[1],bounds[2],bounds[3],0,w->scratch,w->cap);
    if(n<0)return n;
    code=nb_copy(w,&o->raw,w->scratch,n);if(code)return code;
    code=ss_filter_starts(w->ctx,w->p->optional_types[slot],o->raw.xz,o->raw.n,w->flags);if(code)return code;
    n=0;
    for(int i=0;i<o->raw.n;i++)if(w->flags[i]) {
        int x=o->raw.xz[2*i],z=o->raw.xz[2*i+1];
        if(slot==1) {
            int basement=ss_igloo_basement(w->ctx,x,z);
            if(basement<0)return -4;if(!basement)continue;
        }
        w->scratch[2*n]=x;w->scratch[2*n+1]=z;n++;
    }
    return nb_copy(w,&o->viable,w->scratch,n);
}
/* Raw starts are a superset of viable starts. Explore ALL raw co-window cells,
 * then use only their enclosing union bounds as an OW scan upper bound. A
 * single arbitrarily chosen pair would incorrectly discard valid alternatives. */
static int nb_dynamic_raw_bounds_core(const int *fort,int nf,const int *bast,int nb,
                                      int fort_goal,int bast_goal,int *feasible,
                                      const Pos *mansions,int nm,int mansion_goal,int *overlap_out,
                                      int ow_half,int nether_half) {
    if(!fort||!bast||!feasible||nf<0||nb<0||nf>256||nb>256||fort_goal<1||bast_goal<1)return -1;
    if(nf<fort_goal||nb<bast_goal)return 0;
    if(ow_half<=0)ow_half=832;
    if(nether_half<=0)nether_half=416;
    int max_c = 2000 - ow_half;
    int min_c = -max_c;
    int xs[1030],zs[1030],nx=2,nz=2;
    xs[0]=zs[0]=min_c;xs[1]=zs[1]=max_c+1;
    for(int k=0;k<2;k++) {
        int n=k?nb:nf;const int *points=k?bast:fort;
        for(int i=0;i<n;i++) {
            nb_dynamic_event(xs,&nx,8*(points[2*i]-nether_half)+1,min_c,max_c);
            nb_dynamic_event(xs,&nx,8*(points[2*i]+nether_half)+1,min_c,max_c);
            nb_dynamic_event(zs,&nz,8*(points[2*i+1]-nether_half)+1,min_c,max_c);
            nb_dynamic_event(zs,&nz,8*(points[2*i+1]+nether_half)+1,min_c,max_c);
        }
    }
    nx=nb_dynamic_unique(xs,nx);nz=nb_dynamic_unique(zs,nz);
    NBPoints fp={nf,(int*)fort},bp={nb,(int*)bast};int xmin=max_c+1,zmin=max_c+1,xmax=min_c-1,zmax=min_c-1;
    int mansion_overlap=0;
    for(int ix=0;ix<nx-1;ix++)for(int iz=0;iz<nz-1;iz++) {
        int x=-floordiv(-xs[ix],8)*8,z=-floordiv(-zs[iz],8)*8;
        if(x>=xs[ix+1]||z>=zs[iz+1])continue;
        if(nb_dynamic_count(&fp,x,z,nether_half,1,NULL,0)<fort_goal ||
           nb_dynamic_count(&bp,x,z,nether_half,1,NULL,0)<bast_goal)continue;
        int hx=floordiv(xs[ix+1]-1,8)*8,hz=floordiv(zs[iz+1]-1,8)*8;
        if(x<xmin)xmin=x;if(z<zmin)zmin=z;if(hx>xmax)xmax=hx;if(hz>zmax)zmax=hz;
        if(mansion_goal>0 && mansions && nm>0 && !mansion_overlap) {
            for(int m=0;m<nm;m++) {
                if(mansions[m].x+ow_half>=x && mansions[m].x-(ow_half-1)<=hx &&
                   mansions[m].z+ow_half>=z && mansions[m].z-(ow_half-1)<=hz) {
                    mansion_overlap=1;
                    break;
                }
            }
        }
    }
    if(overlap_out)*overlap_out=mansion_overlap;
    if(xmin>xmax||zmin>zmax)return 0;
    feasible[0]=xmin-ow_half;feasible[1]=zmin-ow_half;feasible[2]=xmax+(ow_half-1);feasible[3]=zmax+(ow_half-1);
    return 1;
}
int nb_dynamic_raw_bounds(const int *fort,int nf,const int *bast,int nb,int fort_goal,int bast_goal,int *feasible) {
    return nb_dynamic_raw_bounds_core(fort,nf,bast,nb,fort_goal,bast_goal,feasible,NULL,0,0,NULL,832,416);
}
#ifndef NB_DYNAMIC_PREFLIGHT
#define NB_DYNAMIC_PREFLIGHT 1
#endif
static int nb_raw_atleast(NBWorker *w,int type,const int *b,int goal){
    StructureConfig cfg;if(!getStructureConfig(type,MC_26_50,&cfg))return -1;
    int size=cfg.regionSize*16,n=0;
    for(int rx=floordiv(b[0],size);rx<=floordiv(b[2],size);rx++)
      for(int rz=floordiv(b[1],size);rz<=floordiv(b[3],size);rz++){
        Pos p;
        if(getStructurePos(type,MC_26_50,w->ctx->seed,rx,rz,&p)&&inside(p,b[0],b[1],b[2],b[3])&&++n>=goal)return 1;
      }
    return 0;
}
static int nb_dynamic_raw_preflight(NBWorker *w,int *feasible) {
    if(w->fixture||!NB_DYNAMIC_PREFLIGHT)return 1;
    int fort[512],bast[512],pairs[768],nf=0,nb=0;
    int max_c = 2000 - w->p->overworld_half;
    int nw_bound = floordiv(max_c, 8) + w->p->nether_half;
    int n=ss_nether_raw_pair(w->ctx,-nw_bound,-nw_bound,nw_bound-1,nw_bound-1,pairs,256);
    if(n<0)return n;
    for(int i=0;i<n;i++) {
        int *points=pairs[3*i+2]?fort:bast;int at=pairs[3*i+2]?nf++:nb++;
        points[2*at]=pairs[3*i];points[2*at+1]=pairs[3*i+1];
    }
    Pos mansions[64];int nm=0;
    int mansion_goal=(w->p->flexible_mask&(1u<<0))?w->p->floors[0]:w->p->goals[0];
    if(mansion_goal>0) {
        StructureConfig mcfg;
        if(!getStructureConfig(Mansion,MC_26_50,&mcfg))return -1;
        int msize=mcfg.regionSize*16;
        for(int rx=floordiv(-2000,msize);rx<=floordiv(1999,msize);rx++)
          for(int rz=floordiv(-2000,msize);rz<=floordiv(1999,msize);rz++){
            Pos p;
            if(getStructurePos(Mansion,MC_26_50,w->ctx->seed,rx,rz,&p)&&inside(p,-2000,-2000,1999,1999)){
                if(nm<64)mansions[nm++]=p;
            }
          }
        if(nm<mansion_goal)return 0;
    }
    int mansion_overlap=0;
    int possible=nb_dynamic_raw_bounds_core(fort,nf,bast,nb,w->p->nether_goal,w->p->bastion_goal,feasible,
                                           mansion_goal>0?mansions:NULL,nm,mansion_goal,&mansion_overlap,
                                           w->p->overworld_half,w->p->nether_half);
    if(possible<=0)return possible;
    if(mansion_goal>0 && !mansion_overlap)return 0;
    const int slots[5]={12,0,6,4,5};
    for(int j=0;j<5;j++) {
        int slot=slots[j];
        int goal=(w->p->flexible_mask&(1u<<slot))?w->p->floors[slot]:(slot==12?w->p->outpost_goal:w->p->goals[slot]);
        if(goal<=0)continue;
        int ok;
        if(slot==0) {
            /* Reuse the complete macro-envelope enumeration above. These
             * bounds are a subset, so another placement RNG scan is redundant. */
            int count=0;
            for(int m=0;m<nm;m++)
                if(inside(mansions[m],feasible[0],feasible[1],feasible[2],feasible[3]))count++;
            ok=count>=goal;
        } else ok=nb_raw_atleast(w,w->p->types[slot],feasible,goal);
        if(ok<0)return -3;if(!ok)return 0;
    }
    return 1;
}
static int nb_dynamic_discovery(NBWorker *w,NBResult *r,const int *ow) {
    double start=nb_time();int code=nb_capacity(w,ow);if(code)return code;
    int n;
    if(w->fixture) {
        n=nb_missing(w,28)?0:2;
        for(int i=0;i<n;i++){w->scratch[2*i]=16+i*16;w->scratch[2*i+1]=0;}
    } else n=ss_scan(w->ctx,Stronghold,ow[0],ow[1],ow[2],ow[3],0,w->scratch,w->cap);
    if(n<0)return n;
    code=nb_copy(w,&r->discovery,w->scratch,n);
    r->stage_seconds[0]+=nb_time()-start;return code;
}
/* Necessary Y=63 witness only; positive seeds retain full inventories. */
static int nb_audit_dark_possible(NBWorker *w,const int *b) {
    if(w->fixture)return 1;
    StructureConfig cfg;if(!getStructureConfig(Mansion,MC_26_50,&cfg))return -1;
    int size=cfg.regionSize*16,n=0;
    for(int rx=floordiv(b[0],size);rx<=floordiv(b[2],size);rx++)
      for(int rz=floordiv(b[1],size);rz<=floordiv(b[3],size);rz++) {
        Pos p;
        if(getStructurePos(Mansion,MC_26_50,w->ctx->seed,rx,rz,&p)&&
           inside(p,b[0],b[1],b[2],b[3])&&
           isMansionDarkForestPossible(&w->ctx->overworld.bn,w->ctx->overworld.sha,p.x,p.z)&&
           nb_point(w,p.x,63,p.z)==w->p->dark_id&&++n>=w->p->goals[0])return 1;
      }
    return 0;
}
void applySeedPhase1(Generator *g, int dim, uint64_t seed);
void applySeedPhase2(Generator *g, int dim, uint64_t seed);
static int nb_eval_dynamic(NBWorker *w,uint64_t seed,NBResult *r) {
    double start=nb_time();r->seed=seed;
    NB_PROFILE_SEED(w,seed);
#ifndef NB_DISABLE_MANSION_CACHE
    w->mansion_cache_n=0;
#endif
    if(!w->ctx)return -3;
    w->ctx->seed=seed;
#ifdef _OPENMP
    #pragma omp atomic
#endif
    g_diag_inputs++;
    int code=0;const int ow[4]={-2000,-2000,1999,1999};
    int ow_half=w->p->overworld_half>0?w->p->overworld_half:832;
    int nether_half=w->p->nether_half>0?w->p->nether_half:416;
    int is_v3=ow_half==1024;
    int max_c=2000-ow_half;
    int min_c=-max_c;
    int nw_bound=floordiv(max_c,8)+nether_half;
    const int nw[4]={-nw_bound,-nw_bound,nw_bound-1,nw_bound-1};
    double stage=nb_time();
    NBObservation macro[13]={0},optional[5]={0};NBAnchor nether_macro={0};int *ex=NULL,*ez=NULL,*prefix=NULL,*nether_prefix=NULL;
    NBDynamicCell *cells=NULL;int nx=0,nz=0,ncells=0,optional_evaluated=0;
    int scenic_cached=0,village_cached=0,bastion_cached=0;
    const int *weights=is_v3?nb_centroid_weights_v3:(w->p->dynamic_v2?nb_centroid_weights_v2:nb_centroid_weights);
    int feasible[4]={-2000,-2000,1999,1999},possible=1;
    /* Compact rejects carry a range decision, not an invented discovery row.
     * Defer Stronghold's expensive village path until raw floors can succeed. */
    if(w->p->retention) {
        stage=nb_time();possible=nb_dynamic_raw_preflight(w,feasible);
        r->stage_seconds[11]+=nb_time()-stage;
        if(possible<0){code=possible;goto done;}if(!possible)goto done;
#ifdef _OPENMP
        #pragma omp atomic
#endif
        g_diag_pass_preflight++;
    }
    stage=nb_time();
    /* Full evidence retains discovery even for rejects. Compact decisions
     * need no discarded discovery row, so defer village/Stronghold biome work
     * until the mandatory Mansion predicate has passed. */
    if(!w->p->retention) {
        applySeed(&w->ctx->overworld,DIM_OVERWORLD,seed);
        code=nb_dynamic_discovery(w,r,ow);if(code)goto done;
        if(!r->discovery.n)goto done;
    }
    if(!w->p->retention) {
        stage=nb_time();possible=nb_dynamic_raw_preflight(w,feasible);
        r->stage_seconds[11]+=nb_time()-stage;
        if(possible<0){code=possible;goto done;}if(!possible)goto done;
    }
    if(w->p->retention) {
        if(!w->fixture) {
            applySeedPhase1(&w->ctx->overworld,DIM_OVERWORLD,seed);
            int mansion_goal=(w->p->flexible_mask&(1u<<0))?w->p->floors[0]:w->p->goals[0];
            if(mansion_goal>0) {
                StructureConfig mcfg;
                if(!getStructureConfig(Mansion,MC_26_50,&mcfg)){code=-1;goto done;}
                int msize=mcfg.regionSize*16;
                int dark_ok=0;
                for(int rx=floordiv(feasible[0],msize);rx<=floordiv(feasible[2],msize);rx++) {
                    for(int rz=floordiv(feasible[1],msize);rz<=floordiv(feasible[3],msize);rz++) {
                        Pos p;
                        if(getStructurePos(Mansion,MC_26_50,w->ctx->seed,rx,rz,&p)&&inside(p,feasible[0],feasible[1],feasible[2],feasible[3])) {
                            if(isMansionDarkForestPossible(&w->ctx->overworld.bn,w->ctx->overworld.sha,p.x,p.z)) {
                                dark_ok=1;break;
                            }
                        }
                    }
                    if(dark_ok)break;
                }
                if(!dark_ok)goto done;
#ifdef _OPENMP
                #pragma omp atomic
#endif
                g_diag_pass_mansion_dark++;
            }
            applySeedPhase2(&w->ctx->overworld,DIM_OVERWORLD,seed);
        } else {
            applySeed(&w->ctx->overworld,DIM_OVERWORLD,seed);
        }
    }
    /* One inexpensive macro Mansion preflight before all other structure inventories. */
    stage=nb_time();
    possible=nb_audit_dark_possible(w,feasible);
    if(possible<0){code=possible;goto done;}if(!possible)goto done;
    code=nb_pair(w,0,feasible,&macro[0]);if(code)goto done;
    r->stage_seconds[1]+=nb_time()-stage;
    if(nb_dynamic_count(&macro[0].viable,0,0,2000,0,macro[0].mansion_ids,w->p->dark_id)<w->p->goals[0])goto done;
#ifdef _OPENMP
    #pragma omp atomic
#endif
    g_diag_pass_mansion_macro++;
    if(w->p->retention) {
        code=nb_dynamic_discovery(w,r,ow);if(code)goto done;
        if(!r->discovery.n)goto done;
#ifdef _OPENMP
        #pragma omp atomic
#endif
        g_diag_pass_stronghold_macro++;
    }
    stage=nb_time();
    code=nb_pair(w,12,feasible,&macro[12]);if(code)goto done;
    r->stage_seconds[14]+=nb_time()-stage;
    if(macro[12].viable.n<w->p->outpost_goal)goto done;
#ifdef _OPENMP
    #pragma omp atomic
#endif
    g_diag_pass_outpost_macro++;
    /* Evaluate rarest Overworld structures before Nether to skip Nether on doomed seeds */
    static const int rare_ow_order[4] = {2, 4, 1, 3};
    for(int i=0;i<4;i++) {
        int k=rare_ow_order[i];
        stage=nb_time();code=nb_pair(w,k,feasible,&macro[k]);if(code)goto done;
        r->stage_seconds[k+1]+=nb_time()-stage;
        if(macro[k].viable.n<w->p->floors[k])goto done;
    }
    stage=nb_time();
    applySeed(&w->ctx->nether,DIM_NETHER,seed);
    code=nb_nether(w,nw,&nether_macro);if(code)goto done;
    r->stage_seconds[11]+=nb_time()-stage;
    macro[10]=nether_macro.observations[10];macro[11]=nether_macro.observations[11];
    memset(nether_macro.observations+10,0,2*sizeof(NBObservation));
    if(macro[10].viable.n<w->p->nether_goal||macro[11].viable.n<w->p->bastion_goal)goto done;
#ifdef _OPENMP
    #pragma omp atomic
#endif
    g_diag_pass_nether_macro++;
    /* Remaining Overworld structures: Village, Shipwreck, Trial Chamber, Ruined Portal, Mineshaft */
    static const int remaining_ow_order[5] = {5, 8, 6, 7, 9};
    for(int i=0;i<5;i++) {
        int k=remaining_ow_order[i];
        stage=nb_time();code=nb_pair(w,k,feasible,&macro[k]);if(code)goto done;
        r->stage_seconds[k+1]+=nb_time()-stage;
        if(macro[k].viable.n<w->p->floors[k])goto done;
    }
#ifdef _OPENMP
    #pragma omp atomic
#endif
    g_diag_pass_all_structures_macro++;
    stage=nb_time();
    if(w->p->cutoff_score > 0) {
        int macro_counts[13];
        for(int k=0;k<13;k++) macro_counts[k] = macro[k].viable.n;
        int max_core = is_v3 ? nb_dynamic_v3_core_bonus(macro_counts, r->discovery.n)
                             : nb_dynamic_v2_core_bonus(macro_counts, r->discovery.n);
        int max_potential = max_core + (is_v3 ? 600 : 389);
        if(max_potential < w->p->cutoff_score) {
            goto done;
        }
    }
    int total=256;
    for(int k=0;k<13;k++)total+=macro[k].viable.n*2;
    total+=r->discovery.n*2;
    size_t ex_need=(size_t)(total*2+2048)*sizeof(int);
    if(w->dyn_ex_cap<ex_need) {
        int *new_ex=(int*)nb_alloc(w,ex_need,0);
        int *new_ez=(int*)nb_alloc(w,ex_need,0);
        if(!new_ex||!new_ez) {
            free(new_ex);free(new_ez);
            code=-3;goto done;
        }
        free(w->dyn_ex);free(w->dyn_ez);
        w->dyn_ex=new_ex;w->dyn_ez=new_ez;
        w->dyn_ex_cap=ex_need;
    }
    ex=w->dyn_ex; ez=w->dyn_ez;
    ex[nx++]=min_c;ex[nx++]=max_c+1;ez[nz++]=min_c;ez[nz++]=max_c+1;
    for(int v=-1984;v<=1984;v+=64) {
        nb_dynamic_event(ex,&nx,v-(ow_half-1),min_c,max_c);nb_dynamic_event(ex,&nx,v+(ow_half+1),min_c,max_c);
        nb_dynamic_event(ez,&nz,v-(ow_half-1),min_c,max_c);nb_dynamic_event(ez,&nz,v+(ow_half+1),min_c,max_c);
    }
    int nether_lat_max=((nw_bound-1)/64)*64;
    for(int v=-nether_lat_max;v<=nether_lat_max;v+=64) {
        nb_dynamic_event(ex,&nx,8*(v-nether_half)+1,min_c,max_c);nb_dynamic_event(ex,&nx,8*(v+nether_half)+1,min_c,max_c);
        nb_dynamic_event(ez,&nz,8*(v-nether_half)+1,min_c,max_c);nb_dynamic_event(ez,&nz,8*(v+nether_half)+1,min_c,max_c);
    }
    for(int k=-1;k<13;k++) {
        const NBPoints *points=k<0?&r->discovery:&macro[k].viable;
        int nether=k==10||k==11;
        for(int i=0;i<points->n;i++) {
            if(k==0 && macro[0].mansion_ids && macro[0].mansion_ids[i]!=w->p->dark_id) continue;
            int x=points->xz[2*i],z=points->xz[2*i+1];
            nb_dynamic_event(ex,&nx,nether?8*(x-nether_half)+1:x-(ow_half-1),min_c,max_c);
            nb_dynamic_event(ex,&nx,nether?8*(x+nether_half)+1:x+(ow_half+1),min_c,max_c);
            nb_dynamic_event(ez,&nz,nether?8*(z-nether_half)+1:z-(ow_half-1),min_c,max_c);
            nb_dynamic_event(ez,&nz,nether?8*(z+nether_half)+1:z+(ow_half+1),min_c,max_c);
        }
    }
    nx=nb_dynamic_unique(ex,nx);nz=nb_dynamic_unique(ez,nz);
    size_t maxcells=(size_t)(nx-1)*(size_t)(nz-1);
    if(maxcells>10000000){code=-3;goto done;}
    if(w->dyn_cells_cap<maxcells) {
        size_t need=maxcells+1024;
        void *new_cells=nb_alloc(w,need*sizeof(NBDynamicCell),0);
        if(!new_cells){code=-3;goto done;}
        free(w->dyn_cells);
        w->dyn_cells=new_cells;
        w->dyn_cells_cap=need;
    }
    cells=(NBDynamicCell*)w->dyn_cells;
    int seed_had_floor=0, seed_had_biome=0;
    if(maxcells>0) {
#ifdef _OPENMP
        #pragma omp atomic
#endif
        g_diag_had_candidate_cells++;
    }
    for(int ix=0;ix<nx-1;ix++)for(int iz=0;iz<nz-1;iz++) {
        int x=nb_dynamic_nearest(ex[ix],ex[ix+1]-1);
        int z=nb_dynamic_nearest(ez[iz],ez[iz+1]-1);
        int counts[13],strong=nb_dynamic_count(&r->discovery,x,z,ow_half,0,NULL,0);
        if(!strong)continue;
        int fatal=0,deficit=0;
        static const int cell_rarity_order[13] = {4, 2, 1, 0, 11, 12, 10, 3, 5, 8, 6, 7, 9};
        for(int oi=0;oi<13;oi++) {
            int k=cell_rarity_order[oi];
            counts[k]=nb_dynamic_count(&macro[k].viable,x,z,k==10||k==11?nether_half:ow_half,
                k==10||k==11,k==0?macro[0].mansion_ids:NULL,w->p->dark_id);
            if(counts[k]<w->p->floors[k]){fatal=1;break;}
            if(counts[k]<(k==10?w->p->nether_goal:k==11?w->p->bastion_goal:
                            k==12?w->p->outpost_goal:w->p->goals[k])) {
                if(w->p->flexible_mask&(1u<<k))deficit++;
                else {fatal=1;break;}
            }
        }
        if(fatal||deficit>w->p->max_misses)continue;
        int cell_core = is_v3 ? nb_dynamic_v3_core_bonus(counts, strong)
                              : nb_dynamic_v2_core_bonus(counts, strong);
        if(w->p->cutoff_score > 0) {
            int cell_max_potential = cell_core + (is_v3 ? 600 : 389);
            if(cell_max_potential < w->p->cutoff_score) continue;
        }
        seed_had_floor=1;
        int64_t sx,sz;int weight;
        nb_dynamic_centroid(macro,&r->discovery,x,z,&sx,&sz,&weight,w->p->dark_id,weights,ow_half);
        int xx,zz;
        if(!(nb_dynamic_snap(ex[ix],ex[ix+1]-1,sx,weight,16,&xx)||
             nb_dynamic_snap(ex[ix],ex[ix+1]-1,sx,weight,8,&xx)))continue;
        if(!(nb_dynamic_snap(ez[iz],ez[iz+1]-1,sz,weight,16,&zz)||
             nb_dynamic_snap(ez[iz],ez[iz+1]-1,sz,weight,8,&zz)))continue;
        x=xx;z=zz;
        if(!prefix) {
            code=nb_dynamic_palette_prefix(w,&prefix);if(code)goto done;
            code=nb_dynamic_nether_prefix(w,&nether_prefix);if(code)goto done;
        }
        unsigned int mask=nb_dynamic_palette_mask(prefix,x,z,ow_half);
        if(!nb_biomes_ok(w,mask)||!nb_dynamic_nether_ok(nether_prefix,x,z,nether_half))continue;
        seed_had_biome=1;
        if(w->p->dynamic_v2) {
            int lux=is_v3 ? nb_dynamic_v3_biome_bonus(mask>>13) : nb_dynamic_v2_biome_bonus(mask>>13);
            if(w->p->cutoff_score > 0) {
                int max_rem = is_v3 ? 335 : (129 + 95);
                if(cell_core + lux + max_rem < w->p->cutoff_score) continue;
            }
            if(!optional_evaluated) {
                optional_evaluated=1;
                for(int k=0;k<5;k++){code=nb_dynamic_optional(w,feasible,k,optional+k);if(code)goto done;}
            }
            int opt_counts[5];
            for(int k=0;k<5;k++)opt_counts[k]=nb_dynamic_count(&optional[k].viable,x,z,ow_half,0,NULL,0);
            int opt=is_v3 ? nb_dynamic_v3_optional(opt_counts) : 0;
            if(w->p->cutoff_score > 0 && is_v3) {
                if(cell_core + lux + opt + 135 < w->p->cutoff_score) continue;
            }
            if(!scenic_cached) {
                code=nb_dynamic_build_scenic_cache(w);if(code)goto done;
                scenic_cached=1;
            }
            if(!village_cached) {
                code=nb_dynamic_build_village_cache(w,&macro[5].viable);if(code)goto done;
                village_cached=1;
            }
            if(!bastion_cached) {
                code=nb_dynamic_build_bastion_cache(w,&macro[11].viable);if(code)goto done;
                bastion_cached=1;
            }
            int scenic=nb_dynamic_check_scenic_pair(w,x,z,NULL,NULL,ow_half);
            int spread=nb_dynamic_check_village_spread(w,&macro[5].viable,x,z,NULL,ow_half);
            int treasure=nb_dynamic_check_treasure_bastion(w,&macro[11].viable,x,z);
            if(!is_v3) {
                opt=nb_dynamic_v2_optional(opt_counts,treasure);
            }
            int hub=is_v3 ? nb_dynamic_v3_hub(macro,x,z,NULL,ow_half) : nb_dynamic_v2_hub(macro,x,z,NULL,ow_half);
            int nether_core=is_v3 ? nb_dynamic_v3_nether_core(macro,x,z) : 0;
            int core=cell_core;
            int goals[13];
            for(int k=0;k<10;k++)goals[k]=w->p->goals[k];
            goals[10]=w->p->nether_goal;goals[11]=w->p->bastion_goal;goals[12]=w->p->outpost_goal;
            int def_count=0;
            int penalty=is_v3 ? 0 : nb_dynamic_v2_deficit_penalty(counts,goals,w->p->outpost_goal,&def_count);
            if(is_v3)def_count=0;
            int total_score;
            if(is_v3) {
                total_score=core+opt+lux+hub+nether_core+(scenic?25:0)+(spread?25:0)+(treasure?20:0);
            } else {
                total_score=core+opt+lux+hub+(scenic?20:0)+(spread?15:0)-penalty;
            }
            if(w->p->cutoff_score > 0 && total_score < w->p->cutoff_score) continue;
            cells[ncells++]=(NBDynamicCell){x,z,def_count,total_score,
                nb_dynamic_radial(macro,&r->discovery,x,z,weight,w->p->dark_id,weights,ow_half)};
        } else {
            int hub=nb_dynamic_hub(macro,x,z,ow_half);
            int score=nb_dynamic_score_values(counts,strong,mask>>13,hub);
            const int optional_points[5]={20,15,15,10,10};
            for(int k=0;k<5;k++)score+=optional_points[k]*nb_dynamic_count(&optional[k].viable,x,z,ow_half,0,NULL,0);
            if(w->p->cutoff_score > 0 && score < w->p->cutoff_score) continue;
            cells[ncells++]=(NBDynamicCell){x,z,deficit,score,
                nb_dynamic_radial(macro,&r->discovery,x,z,weight,w->p->dark_id,weights,ow_half)};
        }
    }
    if(seed_had_floor) {
#ifdef _OPENMP
        #pragma omp atomic
#endif
        g_diag_had_floor_cells++;
    }
    if(seed_had_biome) {
#ifdef _OPENMP
        #pragma omp atomic
#endif
        g_diag_had_biome_cells++;
    }
    if(!ncells){r->stage_seconds[13]+=nb_time()-stage;goto done;}
    int best=0;
    if(w->p->dynamic_v2) {
        for(int i=1;i<ncells;i++) if(nb_dynamic_cellcmp_v2(&cells[i],&cells[best])<0) best=i;
    } else {
        for(int i=1;i<ncells;i++) if(nb_dynamic_cellcmp(&cells[i],&cells[best])<0) best=i;
    }
    r->stage_seconds[13]+=nb_time()-stage;
    stage=nb_time();
    int chosen=best;
    r->stage_seconds[12]+=nb_time()-stage;
    if(chosen<0)goto done;
    stage=nb_time();
    r->anchors=nb_alloc(w,sizeof(NBAnchor),1);if(!r->anchors){code=-3;goto done;}
    r->nanchors=1;NBAnchor *a=r->anchors;a->x=cells[chosen].x;a->z=cells[chosen].z;
#ifdef _OPENMP
    #pragma omp atomic
#endif
    g_diag_reached_anchor++;
    a->stronghold_evaluated=1;
    a->stronghold_count=nb_dynamic_count(&r->discovery,a->x,a->z,ow_half,0,NULL,0);
    for(int k=0;k<13;k++) {
        code=nb_dynamic_subset(w,&macro[k],&a->observations[k],a->x,a->z,
                               k==10||k==11?nether_half:ow_half,k==10||k==11);
        if(code)goto done;
        int observed=nb_observed_count(w,a->observations+k,k);
        int goal=k==10?w->p->nether_goal:k==11?w->p->bastion_goal:
                 k==12?w->p->outpost_goal:w->p->goals[k];
        if(observed<goal){a->count_missing|=1<<k;
            if(!(w->p->flexible_mask&(1u<<k)))a->fatal_missing|=1u<<k;}
    }
    for(int k=0;k<5;k++) {
        code=nb_dynamic_subset(w,optional+k,a->optional+k,a->x,a->z,ow_half,0);if(code)goto done;
    }
    int bounds[4]={a->x-ow_half,a->z-ow_half,a->x+ow_half-1,a->z+ow_half-1};
    code=nb_palette(w,bounds,a);if(code)goto done;
    code=nb_dynamic_nether_evidence(w,a);if(code)goto done;
    if(w->p->dynamic_v2) {
        int opt_counts[5];
        for(int k=0;k<5;k++)opt_counts[k]=a->optional[k].viable.n;
        int nearest_v[2]={0,0};
        a->hub_bonus=is_v3 ? nb_dynamic_v3_hub(macro,a->x,a->z,nearest_v,ow_half) : nb_dynamic_v2_hub(macro,a->x,a->z,nearest_v,ow_half);
        a->starter_hub_village[0]=nearest_v[0];
        a->starter_hub_village[1]=nearest_v[1];
        int scenic_wit[2]={0,0},river_wit[2]={0,0};
        int has_scenic=nb_dynamic_check_scenic_pair(w,a->x,a->z,scenic_wit,river_wit,ow_half);
        a->scenic_bonus=has_scenic?(is_v3?25:20):0;
        a->scenic_witness[0]=scenic_wit[0];a->scenic_witness[1]=scenic_wit[1];
        a->river_witness[0]=river_wit[0];a->river_witness[1]=river_wit[1];
        int triple[6]={0};
        int has_spread=nb_dynamic_check_village_spread(w,&macro[5].viable,a->x,a->z,triple,ow_half);
        a->village_spread_bonus=has_spread?(is_v3?25:15):0;
        memcpy(a->village_triple,triple,6*sizeof(int));
        int has_treasure=nb_dynamic_check_treasure_bastion(w,&macro[11].viable,a->x,a->z);
        a->treasure_bastion=has_treasure?1:0;
        int nether_core=is_v3 ? nb_dynamic_v3_nether_core(macro,a->x,a->z) : 0;
        int defs=0;
        int goals[13];
        for(int k=0;k<10;k++)goals[k]=w->p->goals[k];
        goals[10]=w->p->nether_goal;goals[11]=w->p->bastion_goal;goals[12]=w->p->outpost_goal;
        int counts[13];
        for(int k=0;k<13;k++)counts[k]=nb_observed_count(w,a->observations+k,k);
        a->deficit_penalty=is_v3 ? 0 : nb_dynamic_v2_deficit_penalty(counts,goals,w->p->outpost_goal,&defs);
        int core=is_v3 ? nb_dynamic_v3_core_bonus(counts,a->stronghold_count) : nb_dynamic_v2_core_bonus(counts,a->stronghold_count);
        int opt=is_v3 ? nb_dynamic_v3_optional(opt_counts) : nb_dynamic_v2_optional(opt_counts,has_treasure);
        int lux=is_v3 ? nb_dynamic_v3_biome_bonus(a->bonus_biomes) : nb_dynamic_v2_biome_bonus(a->bonus_biomes);
        if(is_v3) {
            a->bonus_total=core+opt+lux+a->hub_bonus+nether_core+a->scenic_bonus+a->village_spread_bonus+(has_treasure?20:0);
        } else {
            a->bonus_total=core+opt+lux+a->hub_bonus+a->scenic_bonus+a->village_spread_bonus;
        }
        a->score=a->bonus_total-a->deficit_penalty;
        a->radial_key=(int)llround(cells[chosen].radial*1e6);
        a->origin_distance_squared=(int64_t)a->x*a->x+(int64_t)a->z*a->z;
        int bcount=0;
        for(int i=0;i<w->dyn_bastion_n&&bcount<8;i++) {
            int bx=macro[11].viable.xz[2*i],bz=macro[11].viable.xz[2*i+1];
            if(8*(bx-nether_half)<a->x&&a->x<=8*(bx+nether_half)&&8*(bz-nether_half)<a->z&&a->z<=8*(bz+nether_half)) {
                a->bastion_coords[2*bcount]=bx;
                a->bastion_coords[2*bcount+1]=bz;
                a->bastion_variants[bcount]=w->dyn_bastion_variants[i];
                bcount++;
            }
        }
        a->bastion_count=bcount;
    } else {
        a->hub_bonus=nb_dynamic_hub(macro,a->x,a->z,ow_half);
    }
    if(!nb_biomes_ok(w,a->biome_mask)||!nb_keep(w,a)){code=-4;goto done;}
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

```

---

<a id="file-3"></a>
### File 3: `native/blueprint_batch.inc`
> **Purpose:** C11 OpenMP Multi-Threaded Batch Sweep, Buffer Retention & Memory Manager  
> **Length:** 651 lines | **Language:** C

```c
/* Private prototype, included after bridge.c. One owning context per OMP
 * thread; no shared generator, viability cache, or low-bit sibling evidence.
 * Errors fail a batch at the Python boundary and never certify absence.
 * Outputs own their buffers until nb_free; no hidden truncation is allowed. */
#ifndef NB_HEADER_INCLUDED
#include "blueprint_batch.h"
#endif
#include <time.h>

/* Keep the scheduling control independently measurable without changing ABI. */
#ifndef NB_WORK_CHUNK
#define NB_WORK_CHUNK 16
#endif
#if NB_WORK_CHUNK != 16 && NB_WORK_CHUNK != 64 && NB_WORK_CHUNK != 128
#error NB_WORK_CHUNK must be 16, 64 or 128
#endif
#ifndef NB_EXPERIMENT_ORDER
#define NB_EXPERIMENT_ORDER 0
#endif
#ifndef NB_STRONGHOLD_AFTER
#define NB_STRONGHOLD_AFTER 4
#endif
int nb_stronghold_after(void) { return NB_STRONGHOLD_AFTER; }
#if NB_EXPERIMENT_ORDER < 0 || NB_EXPERIMENT_ORDER > 2
#error NB_EXPERIMENT_ORDER must be 0, 1 or 2
#endif
#if NB_STRONGHOLD_AFTER < 1 || NB_STRONGHOLD_AFTER > 5
#error NB_STRONGHOLD_AFTER must be between 1 and 5
#endif

#ifndef NB_PROFILE_BIND
#define NB_PROFILE_BIND(w,p,i) ((void)0)
#define NB_PROFILE_SEED(w,s) ((void)0)
#define NB_PROFILE_STAGE(w,k,s,x,z) ((void)0)
#define NB_PROFILE_POINT_BEGIN(w)
#define NB_PROFILE_POINT_END(w,id,x,y,z) ((void)0)
#define NB_PROFILE_INVENTORY_BEGIN(w)
#define NB_PROFILE_INVENTORY_END(w,k,x,z) ((void)0)
#define NB_PROFILE_CACHE(w,hit) ((void)0)
#endif

typedef struct NBWorker {
    SeedContext *ctx;
    int cap, *scratch, *flags;
    const NBPolicy *p;
    const NBFixture *fixture;
    uint64_t *allocated_bytes;
    void *profile;
#ifndef NB_DISABLE_MANSION_CACHE
    int mansion_cache_n, mansion_cache[64][3];
#endif
    int *dyn_prefix;
    int *dyn_nether_prefix;
    int *dyn_ex;
    int *dyn_ez;
    size_t dyn_ex_cap;
    void *dyn_cells;
    size_t dyn_cells_cap;
    int *dyn_biome_grid;
    int *dyn_nether_grid;
    int *dyn_scenic_river;
    size_t dyn_scenic_river_cap;
    unsigned char *dyn_village_sep;
    size_t dyn_village_sep_cap;
    int dyn_bastion_variants[32];
    int dyn_bastion_n;
} NBWorker;

/* A call-wide allocation reservation bounds owned outputs and scratch even for
 * dense late-stage batches. The monotonically counted reservation is deliberate:
 * failure cannot publish a partial batch or silently truncate its evidence. */
static void *nb_alloc(NBWorker *w,size_t bytes,int zero) {
    uint64_t previous;
#ifdef _OPENMP
    #pragma omp atomic capture
#endif
    {previous=*w->allocated_bytes;*w->allocated_bytes+=bytes;}
    if(previous>w->p->max_buffer_bytes || bytes>w->p->max_buffer_bytes-previous)return NULL;
    return zero?calloc(1,bytes):malloc(bytes);
}
static double nb_time(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
    return (double)t.tv_sec+(double)t.tv_nsec*1e-9;
}
static int nb_cmp(const void *a,const void *b) {
    const int *x=a,*y=b;
    if(x[0]!=y[0])return x[0]<y[0]?-1:1;
    return x[1]<y[1]?-1:x[1]>y[1];
}
static void nb_sort(NBPoints *p) {
    if(p->n<2)return;
    qsort(p->xz,p->n,2*sizeof(int),nb_cmp);
    int n=1;
    for(int i=1;i<p->n;i++)if(nb_cmp(p->xz+2*(n-1),p->xz+2*i)) {
        p->xz[2*n]=p->xz[2*i];p->xz[2*n+1]=p->xz[2*i+1];n++;
    }
    p->n=n;
}
static int nb_copy(NBWorker *w,NBPoints *p,const int *xz,int n) {
    if(n<0)return n;
    p->n=n;p->xz=n?nb_alloc(w,(size_t)n*2*sizeof(int),0):NULL;
    if(n&&!p->xz)return -3;
    if(n)memcpy(p->xz,xz,(size_t)n*2*sizeof(int));
    nb_sort(p);return 0;
}
static void nb_clear_points(NBPoints *p) {free(p->xz);p->xz=NULL;p->n=0;}
static void nb_clear_full(NBObservation *o) {
    nb_clear_points(&o->raw);nb_clear_points(&o->viable);
    free(o->mansion_ids);o->mansion_ids=NULL;o->full=0;
}
static int nb_reserve(NBWorker *w,int n) {
    if(n<=w->cap)return 0;
    int *scratch=nb_alloc(w,(size_t)n*4*sizeof(int),0),*flags=nb_alloc(w,(size_t)n*sizeof(int),0);
    if(!scratch||!flags){free(scratch);free(flags);return -3;}
    free(w->scratch);free(w->flags);w->scratch=scratch;w->flags=flags;w->cap=n;
    return 0;
}
static int nb_capacity(NBWorker *w,const int *b) {
    int64_t n=((int64_t)(b[2]-b[0])/16+3)*((int64_t)(b[3]-b[1])/16+3)+20;
    return n>1000000?-1:nb_reserve(w,(int)n);
}
static int nb_missing(NBWorker *w,int slot) {
    return w->fixture->missing==slot || (w->fixture->extra_mask & (1u<<slot));
}
static int nb_fixture_count(NBWorker *w,int slot) {
    int goal=slot<10?w->p->goals[slot]:(slot==10?w->p->nether_goal:slot==11?w->p->bastion_goal:w->p->outpost_goal?w->p->outpost_goal:1);
    return nb_missing(w,slot)?(goal>w->fixture->deficit_depth?goal-w->fixture->deficit_depth:0):goal+2;
}
static int nb_point(NBWorker *w,int x,int y,int z) {
    if(!w->fixture) {
        NB_PROFILE_POINT_BEGIN(w);
        int id=ss_biome(w->ctx,DIM_OVERWORLD,x,y,z);
        NB_PROFILE_POINT_END(w,id,x,y,z);
        return id;
    }
    if(x%64||z%64) {
        if(nb_missing(w,27)||x==w->fixture->x+32)return w->p->pale_id;
        return w->p->dark_id;
    }
    int cave=y==-48||y==0;
    if(nb_missing(w,26))return cave?w->p->dark_id:w->p->fixture_caves[0];
    int n=cave?3:10,k=(floordiv(x,64)+floordiv(z,64))%n;if(k<0)k+=n;
    int family=cave?k+10:k;
    if(nb_missing(w,family+13))return none;
    return cave?w->p->fixture_caves[k]:w->p->fixture_surface[k];
}
static int nb_pair(NBWorker *w,int slot,const int *b,NBObservation *o) {
    int code=nb_capacity(w,b);if(code)return code;
    int n;
    if(w->fixture) {
        n=nb_fixture_count(w,slot);
        for(int i=0;i<n;i++){w->scratch[2*i]=b[0]+800+i*16+(w->p->dynamic?w->fixture->x:0);
            w->scratch[2*i+1]=b[1]+800+(w->p->dynamic?w->fixture->z:0);}
    } else n=ss_scan(w->ctx,w->p->types[slot],b[0],b[1],b[2],b[3],0,w->scratch,w->cap);
    nb_clear_full(o);
    code=nb_copy(w,&o->raw,w->scratch,n);if(code)return code;
    if(w->fixture)for(int i=0;i<o->raw.n;i++)w->flags[i]=1;
    else {
#ifndef NB_DISABLE_MANSION_CACHE
        if(slot==0) {
            /* Same exact full64 input and position only. Reset before every
             * seed; a full cache merely bypasses reuse, never truncates starts. */
            for(int i=0;i<o->raw.n;i++) {
                int x=o->raw.xz[2*i],z=o->raw.xz[2*i+1],found=-1;
                for(int k=0;k<w->mansion_cache_n;k++)if(w->mansion_cache[k][0]==x && w->mansion_cache[k][1]==z){found=k;break;}
                NB_PROFILE_CACHE(w,found>=0);
                if(found>=0)w->flags[i]=w->mansion_cache[found][2];
                else {
                    w->flags[i]=!!isViableStructurePos(Mansion,&w->ctx->overworld,x,z,0);
                    if(w->mansion_cache_n<64) {
                        int *entry=w->mansion_cache[w->mansion_cache_n++];entry[0]=x;entry[1]=z;entry[2]=w->flags[i];
                    }
                }
            }
        } else
#endif
        {code=ss_filter_starts(w->ctx,w->p->types[slot],o->raw.xz,o->raw.n,w->flags);if(code)return code;}
    }
    n=0;
    for(int i=0;i<o->raw.n;i++)if(w->flags[i]){
        w->scratch[2*n]=o->raw.xz[2*i];w->scratch[2*n+1]=o->raw.xz[2*i+1];n++;
    }
    code=nb_copy(w,&o->viable,w->scratch,n);if(code)return code;
    if(slot==0&&n) {
        o->mansion_ids=nb_alloc(w,(size_t)n*sizeof(int),0);if(!o->mansion_ids)return -3;
        for(int i=0;i<n;i++)o->mansion_ids[i]=nb_point(w,o->viable.xz[2*i],63,o->viable.xz[2*i+1]);
    }
    o->evaluated=1;o->full=1;return 0;
}
static int nb_observed_count(const NBWorker *w,const NBObservation *o,int slot) {
    if(!o->full)return o->floor.n;
    if(slot)return o->viable.n;
    int n=0;for(int i=0;i<o->viable.n;i++)n+=o->mansion_ids[i]==w->p->dark_id;
    return n;
}
static int nb_floor(NBWorker *w,int slot,const int *b,NBObservation *o) {
    if(!slot||w->p->complete)return nb_pair(w,slot,b,o);
    int goal=slot==12?w->p->outpost_goal:w->p->goals[slot],code=nb_reserve(w,64);if(code)return code;
    int n;
    if(w->fixture) {
        n=nb_fixture_count(w,slot);if(n>goal)n=goal;
        for(int i=0;i<n;i++){w->scratch[2*i]=b[0]+800+i*16;w->scratch[2*i+1]=b[1]+800;}
    } else n=ss_structure_count(w->ctx,w->p->types[slot],b[0],b[1],b[2],b[3],w->scratch,goal);
    code=nb_copy(w,&o->floor,w->scratch,n);if(code)return code;
    o->evaluated=1;return 0;
}
static int nb_nether(NBWorker *w,const int *b,NBAnchor *a) {
    if(w->fixture) {
        int code=nb_pair(w,10,b,&a->observations[10]);if(code)return code;
        return nb_pair(w,11,b,&a->observations[11]);
    }
    int code=nb_capacity(w,b);if(code)return code;
    int n=ss_nether_pair(w->ctx,b[0],b[1],b[2],b[3],w->scratch,w->flags,w->cap);
    if(n<0)return n;
    for(int slot=10;slot<=11;slot++) {
        NBObservation *o=a->observations+slot;
        o->raw.xz=nb_alloc(w,(size_t)(n?n:1)*2*sizeof(int),0);
        o->viable.xz=nb_alloc(w,(size_t)(n?n:1)*2*sizeof(int),0);
        if(!o->raw.xz||!o->viable.xz)return -3;
        for(int i=0;i<n;i++)if(w->scratch[3*i+2]==(slot==10)) {
            int x=w->scratch[3*i],z=w->scratch[3*i+1],k=o->raw.n++;
            o->raw.xz[2*k]=x;o->raw.xz[2*k+1]=z;
            if(w->flags[i]){k=o->viable.n++;o->viable.xz[2*k]=x;o->viable.xz[2*k+1]=z;}
        }
        nb_sort(&o->raw);nb_sort(&o->viable);o->full=o->evaluated=1;
    }
    return 0;
}
static int nb_gcd(int a,int b){while(b){int t=a%b;a=b;b=t;}return a;}
static int nb_palette(NBWorker *w,const int *b,NBAnchor *a) {
    int step=w->p->spacing,x0=-floordiv(-b[0],step)*step,z0=-floordiv(-b[1],step)*step;
    int nx=(b[2]-x0)/step+1,nz=(b[3]-z0)/step+1,n=nx*nz;
    if(n<1||n>100000)return -1;
    a->biome_xyz=nb_alloc(w,(size_t)n*12*sizeof(int),0);a->biome_ids=nb_alloc(w,(size_t)n*4*sizeof(int),0);
    if(!a->biome_xyz||!a->biome_ids)return -3;
    int stride=(int)(n*.618033988749895);if(stride<1)stride=1;
    while(nb_gcd(stride,n)!=1)stride++;
    for(int f=0;f<13;f++)a->first_witness[f]=-1;
    int batch=w->p->batch_size*4;
    for(int offset=0;offset<n*4;offset+=batch) {
        if(a->biome_mask==8191&&!w->p->complete&&!w->p->origin&&!w->p->dynamic)break;
        int end=offset+batch;if(end>n*4)end=n*4;
        for(int i=offset;i<end;i++) {
            int index=(int)(((int64_t)(i/4)*stride)%n),layer=i%4;
            int x=x0+(index%nx)*step,z=z0+(index/nx)*step,y=w->p->y[layer];
            int id;
            if(w->p->dynamic && w->dyn_biome_grid && x>=-1984 && x<=2048 && z>=-1984 && z<=2048) {
                int ix=(x-(-1984))/64+1,iz=(z-(-1984))/64+1;
                if(ix>=1 && ix<64 && iz>=1 && iz<64)id=w->dyn_biome_grid[layer*64*64+ix*64+iz];
                else id=nb_point(w,x,y,z);
            } else id=nb_point(w,x,y,z);
            int k=a->biome_n++;
            a->biome_xyz[3*k]=x;a->biome_xyz[3*k+1]=y;a->biome_xyz[3*k+2]=z;a->biome_ids[k]=id;
            if((w->p->origin||w->p->dynamic)&&y==63&&id>=0&&id<256)a->bonus_biomes|=(unsigned int)w->p->bonus_biome_members[id];
            unsigned int mask=(id>=0&&id<256)?w->p->biome_members[id]:0;
            mask&=(y==-48||y==0)?7168:1023;
            for(int f=0;f<13;f++)if((mask&(1u<<f))&&!(a->biome_mask&(1u<<f)))a->first_witness[f]=k;
            a->biome_mask|=mask;
        }
    }
    a->biome_evaluated=1;return 0;
}
static int nb_dynamic_score_values(const int *n,int strong,unsigned int bonus,int hub) {
    int score=(n[0]>=2?50:0)+(strong>=2?50:0)+
        (n[5]>8?(n[5]-8)*25:0)+(n[6]>7?(n[6]-7)*10:0)+
        (n[4]>=4?25:0)+(n[2]>=3?20:0)+
        (n[1]>=3?20:0)+(n[12]>=3?20:0)+
        (n[10]>=3?20:0)+(n[11]>=3?20:0)+
        (n[3]>=2?30:0)+(n[8]>6?(n[8]-6)*5:0)+
        (n[7]>7?(n[7]-7)*5:0)+(n[9]>15?n[9]-15:0)+hub;
    const int points[10]={30,20,25,30,25,10,10,15,15,15};
    for(int i=0;i<10;i++)if(bonus&(1u<<i))score+=points[i];
    return score;
}
static int nb_score(NBWorker *w,NBAnchor *a) {
    if(w->p->dynamic) {
        if(w->p->dynamic_v2)return a->score;
        int n[13];for(int i=0;i<13;i++)n[i]=nb_observed_count(w,a->observations+i,i);
        int score=nb_dynamic_score_values(n,a->stronghold_count,a->bonus_biomes,a->hub_bonus);
        const int points[5]={20,15,15,10,10};
        for(int k=0;k<5;k++)score+=a->optional[k].viable.n*points[k];
        return score;
    }
    if(w->p->locked) {
        int n[13];for(int i=0;i<13;i++)n[i]=nb_observed_count(w,a->observations+i,i);
        if(w->p->origin) {
            if(w->p->two_group) {
                int score=(n[0]>=1?50:0)+(n[0]>=2?50:0)+(a->stronghold_count>=2?50:0)+
                    (n[4]>2?((n[4]<4?n[4]:4)-2)*25:0)+
                    (n[10]>2?((n[10]<4?n[10]:4)-2)*20:0)+
                    (n[11]>3?(n[11]-3)*20:0)+
                    (n[6]>10?(n[6]-10)*10:0)+
                    (n[5]>7?(n[5]-7)*5:0)+
                    (n[7]>7?(n[7]-7)*5:0)+
                    (n[9]>20?n[9]-20:0)+
                    (n[12]>1?(n[12]-1)*10:0)+
                    (w->p->marine_baseline&&n[8]>5?(n[8]-5)*5:0)+
                    (n[2]>=2?10:0)+(n[1]>=2?10:0);
                for(int i=0;i<3;i++)if(a->bonus_biomes&(1u<<i))score+=15;
                return score;
            }
            int score=(n[5]>6?(n[5]-6)*5:0)+(n[7]>6?(n[7]-6)*5:0)+
                (n[8]>5?(n[8]-5)*5:0)+(n[9]>15?n[9]-15:0)+
                (n[6]>5?(n[6]-5)*10:0)+
                (n[4]>2?((n[4]<4?n[4]:4)-2)*25:0)+
                (n[10]>2?((n[10]<4?n[10]:4)-2)*20:0)+
                (n[11]>3?(n[11]-3)*20:0)+
                (n[0]>=2?50:0)+(a->stronghold_count>=2?50:0)+
                (n[2]>=2?10:0)+(n[1]>=2?10:0)+(n[3]>=2?30:0)+
                (n[12]>2?(n[12]-2)*10:0);
            for(int i=0;i<3;i++)if(a->bonus_biomes&(1u<<i))score+=15;
            return score;
        }
        int score=(n[5]>6?(n[5]-6)*5:0)+(n[7]>6?(n[7]-6)*5:0)+
                  (n[8]>w->p->goals[8]?(n[8]-w->p->goals[8])*5:0)+(n[9]>15?n[9]-15:0);
        score+=(n[6]>5?(n[6]-5)*10:0);
        for(int i=4;i<=11;i++)if(i==4||i==10||i==11){
            if(i==11&&w->p->river)score+=(n[i]>3?(n[i]-3)*15:0);
            else score+=(n[i]>2?((n[i]<4?n[i]:4)-2)*15:0);
        }
        if(w->p->river&&n[0]>=2)score+=50;
        score+=(n[2]>=2?20:0)+(n[2]>=3?10:0)+(n[1]>=2?20:0);
        score+=(n[3]>=2?30:0)+n[12]*10;
        return score;
    }
    int n[13];for(int i=0;i<13;i++)n[i]=nb_observed_count(w,a->observations+i,i);
    int score=(n[5]>5?(n[5]-5)*5:0)+(n[7]>3?(n[7]-3)*5:0)+
              (n[8]>2?(n[8]-2)*5:0)+(n[9]>5?n[9]-5:0);
    score+=(n[6]>2?((n[6]<4?n[6]:4)-2)*10:0);
    for(int i=4;i<=11;i++)if(i==4||i==10||i==11)score+=(n[i]>1?((n[i]<3?n[i]:3)-1)*15:0);
    for(int i=1;i<=2;i++)score+=(n[i]>=2?20:0)+(n[i]>=3?10:0);
    score+=(n[3]>=2?30:0)+n[12]*10;
    return score;
}
static void nb_clear_anchor(NBAnchor *a) {
    for(int k=0;k<13;k++){nb_clear_full(a->observations+k);nb_clear_points(&a->observations[k].floor);}
    for(int k=0;k<5;k++)nb_clear_full(a->optional+k);
    free(a->nether_biome_xyz);free(a->nether_biome_ids);
    free(a->biome_xyz);free(a->biome_ids);memset(a,0,sizeof(*a));
}
static void nb_clear_result(NBResult *r) {
    nb_clear_points(&r->discovery);
    if(r->anchors)for(int j=0;j<r->nanchors;j++)nb_clear_anchor(r->anchors+j);
    free(r->anchors);r->anchors=NULL;r->nanchors=0;
}
static int nb_bits(unsigned int n) {int k=0;while(n){k+=(n&1u);n>>=1;}return k;}
static int nb_budget_ok(const NBWorker *w,const NBAnchor *a) {
    if(w->p->two_group)
        return !a->fatal_missing && nb_bits((unsigned int)a->count_missing&w->p->flexible_mask)<=w->p->max_misses;
    return w->p->retention ? nb_bits((unsigned int)a->count_missing)<=w->p->max_misses : !a->count_missing;
}
static unsigned int nb_required_biomes(const NBWorker *w) {
    return w->p->dynamic_v2?w->p->required_biome_mask:8191u;
}
static int nb_biomes_ok(const NBWorker *w,unsigned int mask) {
    unsigned int required=nb_required_biomes(w);return (mask&required)==required;
}
static int nb_keep(const NBWorker *w,const NBAnchor *a) {
    if(w->p->two_group)
        return a->stronghold_count>=1 && nb_budget_ok(w,a) && a->biome_evaluated && nb_biomes_ok(w,a->biome_mask);
    return (!w->p->origin||a->stronghold_count>=1) && a->biome_evaluated && nb_bits((unsigned int)a->count_missing)+13-nb_bits(a->biome_mask)<=w->p->max_misses;
}
#include "blueprint_dynamic.inc"
static int nb_eval(NBWorker *w,uint64_t seed,NBResult *r) {
    if(w->p->dynamic)return nb_eval_dynamic(w,seed,r);
    double start=nb_time();r->seed=seed;
    NB_PROFILE_SEED(w,seed);
#ifndef NB_DISABLE_MANSION_CACHE
    w->mansion_cache_n=0;
#endif
    if(!w->ctx)return -3;
    w->ctx->seed=seed;applySeed(&w->ctx->overworld,DIM_OVERWORLD,seed);
    applySeed(&w->ctx->nether,DIM_NETHER,seed);
    double t=nb_time();int code=0;
    if(!w->p->origin){code=nb_capacity(w,w->p->discovery);if(code)return code;}
    int n;
    if(w->p->origin){n=1;code=nb_reserve(w,64);if(code)return code;w->scratch[0]=0;w->scratch[1]=0;}
    else if(w->fixture){n=1;w->scratch[0]=w->fixture->x;w->scratch[1]=w->fixture->z;}
    else n=ss_scan(w->ctx,Stronghold,w->p->discovery[0],w->p->discovery[1],w->p->discovery[2],w->p->discovery[3],0,w->scratch,w->cap);
    if(n<0)return n;
    if(!w->p->origin){code=nb_copy(w,&r->discovery,w->scratch,n);if(code)return code;}
    r->stage_seconds[0]=nb_time()-t;r->nanchors=w->p->origin?1:r->discovery.n;
    if(w->p->origin&&!w->p->retention) {
        /* Full evidence retains discovery for every input, regardless of
         * later early structure failure. Compact delays this exact query. */
        t=nb_time();code=nb_capacity(w,w->p->discovery);if(code)return code;
        n=w->fixture?(nb_missing(w,28)?0:2):ss_scan(w->ctx,Stronghold,w->p->discovery[0],w->p->discovery[1],w->p->discovery[2],w->p->discovery[3],0,w->scratch,w->cap);
        if(n<0)return n;
        if(w->fixture)for(int q=0;q<n;q++){w->scratch[2*q]=16+q*16;w->scratch[2*q+1]=0;}
        code=nb_copy(w,&r->discovery,w->scratch,n);if(code)return code;
        r->stage_seconds[0]+=nb_time()-t;
    }
    NB_PROFILE_STAGE(w,0,r->stage_seconds[0],0,0);
    r->anchors=nb_alloc(w,(size_t)(r->nanchors?r->nanchors:1)*sizeof(NBAnchor),1);if(!r->anchors)return -3;
    for(int j=0;j<r->nanchors;j++) {
        NBAnchor *a=r->anchors+j;a->x=w->p->origin?0:r->discovery.xz[2*j];a->z=w->p->origin?0:r->discovery.xz[2*j+1];
        if(w->p->origin&&!w->p->retention){a->stronghold_evaluated=1;a->stronghold_count=r->discovery.n;}
        int h=w->p->overworld_half,nh=w->p->nether_half;
        int b[4]={a->x-h,a->z-h,a->x+h-1,a->z+h-1};
        if(w->p->locked) {
            int x=-floordiv(-a->x,8),z=-floordiv(-a->z,8),nb[4]={x-nh,z-nh,x+nh-1,z+nh-1};
            t=nb_time();code=nb_nether(w,nb,a);double elapsed=nb_time()-t;r->stage_seconds[11]+=elapsed;
            NB_PROFILE_STAGE(w,11,elapsed,a->x,a->z);if(code)return code;
            for(int slot=10;slot<=11;slot++) {
                int observed=a->observations[slot].viable.n;
                if(observed<(slot==10?w->p->nether_goal:w->p->bastion_goal))a->count_missing|=1<<slot;
                if(w->p->two_group && observed<w->p->floors[slot])a->fatal_missing|=1u<<slot;
            }
            if(w->p->two_group && a->fatal_missing && a->stronghold_evaluated && !a->stronghold_count)
                a->fatal_missing|=1u<<13;
        }
        const int locked_order[8]={7,6,0,2,1,4,5,9};
        /* Experimental orders rearrange only identical supported predicates.
         * Complete retained inventories are filled in the original slot map. */
        const int order_first_strict[9]={12,2,1,7,6,0,4,5,9};
        const int order_chamber_first[9]={6,12,2,1,7,0,4,5,9};
        for(int k=0;k<(w->p->outpost_goal?9:w->p->locked?8:10);k++) {
            int slot=w->p->outpost_goal?
                (w->p->two_group&&w->p->retention&&NB_EXPERIMENT_ORDER==1?order_first_strict[k]:
                 w->p->two_group&&w->p->retention&&NB_EXPERIMENT_ORDER==2?order_chamber_first[k]:w->p->structure_order[k]):
                 w->p->locked?locked_order[k]:k;
            if(!w->p->complete && !nb_budget_ok(w,a))break;
            t=nb_time();code=nb_floor(w,slot,b,a->observations+slot);
            double elapsed=nb_time()-t;r->stage_seconds[slot==12?14:slot+1]+=elapsed;
            NB_PROFILE_STAGE(w,slot==12?29:slot+1,elapsed,a->x,a->z);if(code)return code;
            int observed=nb_observed_count(w,a->observations+slot,slot);
            if(observed<(slot==12?w->p->outpost_goal:w->p->goals[slot]))a->count_missing|=1<<slot;
            if(w->p->two_group && observed<w->p->floors[slot])a->fatal_missing|=1u<<slot;
            if(w->p->origin&&k==(w->p->two_group?NB_STRONGHOLD_AFTER-1:1)&&!a->stronghold_evaluated) {
                /* Mandatory Stronghold is queried only after cheap floors. Its
                 * full supported inventory is retained for the second-start bonus. */
                t=nb_time();code=nb_capacity(w,b);if(code)return code;
                n=w->fixture?(nb_missing(w,28)?0:2):ss_scan(w->ctx,Stronghold,b[0],b[1],b[2],b[3],0,w->scratch,w->cap);
                if(n<0)return n;
                if(w->fixture)for(int q=0;q<n;q++){w->scratch[2*q]=16+q*16;w->scratch[2*q+1]=0;}
                code=nb_copy(w,&r->discovery,w->scratch,n);if(code)return code;
                a->stronghold_count=r->discovery.n;
                a->stronghold_evaluated=1;
                if(w->p->two_group && !a->stronghold_count)a->fatal_missing|=1u<<13;
                double stronghold_elapsed=nb_time()-t;
                r->stage_seconds[0]+=stronghold_elapsed;
                NB_PROFILE_STAGE(w,0,stronghold_elapsed,a->x,a->z);
                if(!a->stronghold_count&&!w->p->complete)break;
            }
            if(w->p->origin&&k==(w->p->two_group?NB_STRONGHOLD_AFTER-1:1)&&a->stronghold_evaluated&&!a->stronghold_count) {
                if(w->p->two_group)a->fatal_missing|=1u<<13;
                if(!w->p->complete)break;
            }
        }
        if(w->p->two_group&&a->stronghold_evaluated&&!a->stronghold_count)a->fatal_missing|=1u<<13;
        if(w->p->origin&&a->stronghold_evaluated&&!a->stronghold_count&&!w->p->complete){a->score=nb_score(w,a);continue;}
        if(!w->p->locked && (w->p->complete||nb_budget_ok(w,a))) {
            int x=-floordiv(-a->x,8),z=-floordiv(-a->z,8),nb[4]={x-nh,z-nh,x+nh-1,z+nh-1};
            t=nb_time();code=nb_nether(w,nb,a);double elapsed=nb_time()-t;r->stage_seconds[11]+=elapsed;
            NB_PROFILE_STAGE(w,11,elapsed,a->x,a->z);if(code)return code;
            for(int slot=10;slot<=11;slot++) {
                int observed=a->observations[slot].viable.n;
                if(observed<(slot==10?w->p->nether_goal:w->p->bastion_goal))a->count_missing|=1<<slot;
                if(w->p->two_group && observed<w->p->floors[slot])a->fatal_missing|=1u<<slot;
            }
        }
        if(w->p->complete||nb_budget_ok(w,a)) {
            t=nb_time();code=nb_palette(w,b,a);double elapsed=nb_time()-t;r->stage_seconds[12]+=elapsed;
            NB_PROFILE_STAGE(w,12,elapsed,a->x,a->z);if(code)return code;
        }
        /* Marine starts are strict baseline counts in v3. Query them only after
         * the cheap structure and biome gates, before retaining a survivor. */
        if(w->p->marine_baseline && (w->p->complete ||
            (nb_budget_ok(w,a)&&a->biome_evaluated&&a->biome_mask==8191))) {
            for(int slot=3;slot<=8;slot+=5) {
                t=nb_time();code=nb_floor(w,slot,b,a->observations+slot);
                double elapsed=nb_time()-t;r->stage_seconds[slot+1]+=elapsed;
                NB_PROFILE_STAGE(w,slot+1,elapsed,a->x,a->z);if(code)return code;
                int observed=nb_observed_count(w,a->observations+slot,slot);
                if(observed<w->p->goals[slot])a->count_missing|=1<<slot;
                if(observed<w->p->floors[slot])a->fatal_missing|=1u<<slot;
                if(!w->p->complete && a->fatal_missing)break;
            }
        }
        if((nb_budget_ok(w,a)&&a->biome_mask==8191)||(w->p->retention&&nb_keep(w,a))) {
            t=nb_time();
            for(int slot=0;slot<10;slot++)if(!(w->p->locked&&!w->p->marine_baseline&&(slot==3||slot==8))&&!a->observations[slot].full){
                NB_PROFILE_INVENTORY_BEGIN(w);
                code=nb_pair(w,slot,b,a->observations+slot);
                NB_PROFILE_INVENTORY_END(w,slot,a->x,a->z);if(code)return code;
            }
            if((w->p->outpost_goal&&!a->observations[12].full)||(!w->p->locked&&!a->count_missing&&a->biome_mask==8191)){
                NB_PROFILE_INVENTORY_BEGIN(w);
                code=nb_pair(w,12,b,a->observations+12);
                NB_PROFILE_INVENTORY_END(w,12,a->x,a->z);if(code)return code;
            }
            double elapsed=nb_time()-t;r->stage_seconds[13]+=elapsed;
            NB_PROFILE_STAGE(w,13,elapsed,a->x,a->z);
        }
        a->score=nb_score(w,a);
    }
    r->seconds=nb_time()-start;return 0;
}
static NBBatch *nb_run(const uint64_t *seeds,const NBFixture *fixtures,int count,const NBPolicy *p,int threads,void *profiles) {
    if(!seeds||!p||count<1||count>16384||threads<1||threads>36||
       (threads>1&&!ss_openmp_enabled())||p->spacing!=64||p->batch_size<1||p->batch_size>576||
       (p->complete!=0&&p->complete!=1)||p->retention<0||p->retention>1||p->max_misses<0||p->max_misses>25||
       (p->retention&&p->complete))return NULL;
    for(int i=0;i<4;i++)if(p->discovery[i]<-1000000||p->discovery[i]>1000000)return NULL;
    if(p->discovery[0]>p->discovery[2]||p->discovery[1]>p->discovery[3]||
       p->discovery[2]-p->discovery[0]>14000||p->discovery[3]-p->discovery[1]>14000)return NULL;
    const int types[13]={Mansion,Jungle_Pyramid,Desert_Pyramid,Monument,Ancient_City,Village,Trial_Chambers,Ruined_Portal,Shipwreck,Mineshaft,Fortress,Bastion,Outpost};
    const int old_goals[10]={1,1,1,1,1,5,2,3,2,5},new_goals[10]={1,1,1,1,2,6,5,6,4,15};
    const int group_floors[13]={0,1,1,0,1,5,8,5,0,17,1,2,1};
    const unsigned int group_flexible=(1u<<0)|(1u<<4)|(1u<<5)|(1u<<6)|(1u<<7)|(1u<<9)|(1u<<10)|(1u<<11);
    const int y[4]={63,-48,0,160};
    for(int i=0;i<13;i++)if(p->types[i]!=types[i])return NULL;
    if(p->dynamic) {
        if(p->dynamic_v2 && (p->required_biome_mask & ~8191u))return NULL;
        int is_v3 = (p->overworld_half == 1024);
        const int floors_v2[13]={1,2,2,1,3,8,7,5,4,12,2,2,2};
        const int floors_v3[13]={1,1,1,1,2,6,8,8,4,10,1,2,1};
        const unsigned int flexible=(1u<<1)|(1u<<2)|(1u<<4)|(1u<<5)|
            (1u<<6)|(1u<<7)|(1u<<8)|(1u<<9);
        const int *expected_floors = is_v3 ? floors_v3 : floors_v2;
        const unsigned int expected_flexible = is_v3 ? 0 : flexible;
        int min_goal = is_v3 ? 1 : 2;
        int max_misses_limit = is_v3 ? 0 : (p->dynamic_v2 ? 3 : 2);
        if(p->dynamic!=1||!p->locked||!p->two_group||p->origin||p->marine_baseline||p->river||
           (p->overworld_half!=832&&p->overworld_half!=1024)||(p->nether_half!=416&&p->nether_half!=512)||p->max_misses>max_misses_limit||
           p->discovery[0]!=-2000||p->discovery[1]!=-2000||
           p->discovery[2]!=1999||p->discovery[3]!=1999||
           p->outpost_goal<min_goal||p->outpost_goal>64||
           p->nether_goal<min_goal||p->nether_goal>64||p->bastion_goal<min_goal||p->bastion_goal>64||
           p->flexible_mask!=expected_flexible||p->cutoff_score<0)return NULL;
        for(int i=0;i<13;i++)if(p->floors[i]!=expected_floors[i])return NULL;
        for(int i=0;i<10;i++)if(p->goals[i]<expected_floors[i]||p->goals[i]>64)return NULL;
        int positive_weights=0;
        for(int i=0;i<6;i++){
            if(p->density_weights[i]<0||p->density_weights[i]>1000)return NULL;
            positive_weights+=p->density_weights[i];
        }
        if(!positive_weights)return NULL;
    } else {
    if((p->locked!=0&&p->locked!=1)||(p->river!=0&&p->river!=1)||(p->river&&!p->locked)||(p->origin!=0&&p->origin!=1)||(p->two_group!=0&&p->two_group!=1)||(p->two_group&&!p->origin)||(p->marine_baseline!=0&&p->marine_baseline!=1)||(p->marine_baseline&&!p->two_group)||(p->origin&&(!p->locked||!p->river||p->outpost_goal!=(p->two_group?1:2))))return NULL;
    if(p->origin&&(p->discovery[0]!=-1024||p->discovery[1]!=-1024||p->discovery[2]!=1023||p->discovery[3]!=1023))return NULL;
    if(p->bastion_goal!=(p->river?3:p->locked?2:1) && !(p->two_group&&p->bastion_goal>=2&&p->bastion_goal<=100))return NULL;
    if(p->outpost_goal!=0&&p->outpost_goal!=2&&!(p->two_group&&p->outpost_goal==1))return NULL;
    if(p->outpost_goal) {
        if(!p->river)return NULL;
        unsigned int seen=0;
        for(int i=0;i<9;i++) {
            int slot=p->structure_order[i];
            if(slot<0||slot>12||slot==3||slot==8||slot==10||slot==11||(seen&(1u<<slot)))return NULL;
            seen|=1u<<slot;
        }
        if(seen!=((1u<<0)|(1u<<1)|(1u<<2)|(1u<<4)|(1u<<5)|(1u<<6)|(1u<<7)|(1u<<9)|(1u<<12)))return NULL;
    }
    if(p->overworld_half!=(p->locked?1024:768)||p->nether_half!=(p->locked?512:448)||
       (p->two_group?(p->nether_goal<1||p->nether_goal>100):(p->nether_goal!=(p->locked?2:1))))return NULL;
    for(int i=0;i<10;i++) {
        if(p->two_group) {
            if(p->goals[i]<group_floors[i]||p->goals[i]>100||
               ((i==1||i==2)&&p->goals[i]!=1)||
               (p->marine_baseline&&i==3&&p->goals[i]!=1)||
               (p->marine_baseline&&i==8&&p->goals[i]!=3))return NULL;
        } else if(p->goals[i]!=(p->river&&i==8?5:p->locked?new_goals[i]:old_goals[i]))return NULL;
    }
    if(p->two_group) {
        if(p->flexible_mask!=group_flexible||p->max_misses>8)return NULL;
        for(int i=0;i<13;i++)if(p->floors[i]!=(p->marine_baseline&&i==3?1:p->marine_baseline&&i==8?3:group_floors[i]))return NULL;
    }
    }
    for(int i=0;i<4;i++)if(p->y[i]!=y[i])return NULL;
    if(fixtures)for(int i=0;i<count;i++)if(fixtures[i].x<-1000000||fixtures[i].x>1000000||fixtures[i].z<-1000000||fixtures[i].z>1000000||
        fixtures[i].missing<-1||fixtures[i].missing>(p->dynamic?33:28)||fixtures[i].deficit_depth<1||fixtures[i].deficit_depth>32)return NULL;
    uint64_t allocated_bytes=sizeof(NBBatch)+(uint64_t)count*(sizeof(NBResult)+(p->retention?sizeof(NBVerdict):0));
    if(p->max_buffer_bytes<allocated_bytes || p->max_buffer_bytes>((uint64_t)4<<30))return NULL;
    NBBatch *batch=calloc(1,sizeof(*batch));if(!batch)return NULL;
    batch->count=count;batch->results=calloc((size_t)count,sizeof(NBResult));
    if(!batch->results){free(batch);return NULL;}
    if(p->retention){batch->verdicts=calloc((size_t)count,sizeof(NBVerdict));if(!batch->verdicts){nb_free(batch);return NULL;}}
    int next=0;
#ifdef _OPENMP
    #pragma omp parallel num_threads(threads) if(threads>1)
#endif
    {
#ifdef _OPENMP
        #pragma omp single
        batch->effective_threads=omp_get_num_threads();
#else
        batch->effective_threads=1;
#endif
        NBWorker w={0};w.ctx=ss_create(0);w.p=p;w.allocated_bytes=&allocated_bytes;
        /* Atomic chunk claiming preserves dynamic load balancing without the
         * newer compiler's dispatch-deinit ABI absent in the pinned libomp. */
        while(1) {
            int first;
#ifdef _OPENMP
            #pragma omp atomic capture
#endif
            {first=next;next+=NB_WORK_CHUNK;}
            if(first>=count)break;
            int end=first+NB_WORK_CHUNK;if(end>count)end=count;
            for(int i=first;i<end;i++) {
                w.fixture=fixtures?fixtures+i:NULL;
                NB_PROFILE_BIND(&w,profiles,i);
                NBResult *r=batch->results+i;r->input_offset=i;
                r->error=nb_eval(&w,seeds[i],r);
                if(p->retention && !r->error) {
                    NBVerdict *v=batch->verdicts+i;v->seed=seeds[i];v->anchors=(uint32_t)(p->origin?r->discovery.n:r->nanchors);
                    int kept=0,original=r->nanchors;
                    for(int j=0;j<original;j++) {
                        if(nb_keep(&w,r->anchors+j)) {
                            if(j!=kept){r->anchors[kept]=r->anchors[j];memset(r->anchors+j,0,sizeof(NBAnchor));}
                            kept++;
                        } else nb_clear_anchor(r->anchors+j);
                    }
                    r->nanchors=kept;v->retained=(uint32_t)kept;
                    if(!kept)nb_clear_result(r);
                }
            }
        }
        ss_destroy(w.ctx);free(w.scratch);free(w.flags);
        free(w.dyn_prefix);free(w.dyn_nether_prefix);free(w.dyn_ex);free(w.dyn_ez);
        free(w.dyn_cells);free(w.dyn_biome_grid);free(w.dyn_nether_grid);
        free(w.dyn_scenic_river);free(w.dyn_village_sep);
    }
    batch->result_count=count;
    if(p->retention) {
        int kept=0;
        for(int i=0;i<count;i++) {
            batch->discovered_anchors+=batch->verdicts[i].anchors;batch->retained_anchors+=batch->verdicts[i].retained;
            NBResult *r=batch->results+i;
            if(r->error){batch->error=r->error;break;}
            if(r->nanchors) {
                if(i!=kept){batch->results[kept]=*r;memset(r,0,sizeof(*r));}
                kept++;
            }
        }
        if(!batch->error)batch->result_count=kept;
    }
    return batch;
}
NBBatch *nb_sweep(const uint64_t *seeds,int count,const NBPolicy *p,int threads){return nb_run(seeds,NULL,count,p,threads,NULL);}
NBBatch *nb_fixture_sweep(const uint64_t *seeds,const NBFixture *fixtures,int count,const NBPolicy *p,int threads){
    if(!fixtures)return NULL;return nb_run(seeds,fixtures,count,p,threads,NULL);
}
void nb_free(NBBatch *batch) {
    if(!batch)return;
    int limit = (batch->verdicts && !batch->error) ? batch->result_count : batch->count;
    for(int i=0;i<limit;i++) {
        nb_clear_result(batch->results+i);
    }
    free(batch->verdicts);free(batch->results);free(batch);
}

```

---

<a id="file-4"></a>
### File 4: `vendor/cubiomes-bedrock/rng.h`
> **Purpose:** Cubiomes PRNG & Branchless floordiv(a, b) Definition  
> **Length:** 406 lines | **Language:** C

```c
#ifndef RNG_H_
#define RNG_H_

#define __STDC_FORMAT_MACROS 1

#include <stdlib.h>
#include <stddef.h>
#include <inttypes.h>


///=============================================================================
///                      Compiler and Platform Features
///=============================================================================

typedef int8_t      i8;
typedef uint8_t     u8;
typedef int16_t     i16;
typedef uint16_t    u16;
typedef int32_t     i32;
typedef uint32_t    u32;
typedef int64_t     i64;
typedef uint64_t    u64;
typedef float       f32;
typedef double      f64;


#define STRUCT(S) typedef struct S S; struct S

#if __GNUC__

#define IABS(X)                 __builtin_abs(X)
#define PREFETCH(PTR,RW,LOC)    __builtin_prefetch(PTR,RW,LOC)
#define likely(COND)            (__builtin_expect(!!(COND),1))
#define unlikely(COND)          (__builtin_expect((COND),0))
#define ATTR(...)               __attribute__((__VA_ARGS__))
#define BSWAP32(X)              __builtin_bswap32(X)
#define UNREACHABLE()           __builtin_unreachable()

#else

#define IABS(X)                 ((int)abs(X))
#define PREFETCH(PTR,RW,LOC)
#define likely(COND)            (COND)
#define unlikely(COND)          (COND)
#define ATTR(...)
static inline uint32_t BSWAP32(uint32_t x) {
    x = ((x & 0x000000ff) << 24) | ((x & 0x0000ff00) <<  8) |
        ((x & 0x00ff0000) >>  8) | ((x & 0xff000000) >> 24);
    return x;
}
#if _MSC_VER
#define UNREACHABLE()           __assume(0)
#else
#define UNREACHABLE()           exit(1) // [[noreturn]]
#endif

#endif

/// imitate amd64/x64 rotate instructions

static inline ATTR(const, always_inline, artificial)
uint64_t rotl64(uint64_t x, uint8_t b)
{
    return (x << b) | (x >> (64-b));
}

static inline ATTR(const, always_inline, artificial)
uint32_t rotr32(uint32_t a, uint8_t b)
{
    return (a >> b) | (a << (32-b));
}

/// integer floor divide
static inline ATTR(const, always_inline)
int32_t floordiv(int32_t a, int32_t b)
{
    int32_t q = a / b;
    int32_t r = a % b;
    return q - ((a ^ b) < 0 && !!r);
}

///=============================================================================
///                    C implementation of Java Random
///=============================================================================

static inline void JsetSeed(uint64_t *seed, uint64_t value)
{
    *seed = (value ^ 0x5deece66d) & ((1ULL << 48) - 1);
}

static inline int Jnext(uint64_t *seed, const int bits)
{
    *seed = (*seed * 0x5deece66d + 0xb) & ((1ULL << 48) - 1);
    return (int) ((int64_t)*seed >> (48 - bits));
}

static inline int JnextInt(uint64_t *seed, const int n)
{
    int bits, val;
    const int m = n - 1;

    if ((m & n) == 0) {
        uint64_t x = n * (uint64_t)Jnext(seed, 31);
        return (int) ((int64_t) x >> 31);
    }

    do {
        bits = Jnext(seed, 31);
        val = bits % n;
    }
    while ((int32_t)((uint32_t)bits - val + m) < 0);
    return val;
}

static inline uint64_t JnextLong(uint64_t *seed)
{
    return ((uint64_t) Jnext(seed, 32) << 32) + Jnext(seed, 32);
}

static inline float JnextFloat(uint64_t *seed)
{
    return Jnext(seed, 24) / (float) (1 << 24);
}

static inline double JnextDouble(uint64_t *seed)
{
    uint64_t x = (uint64_t)Jnext(seed, 26);
    x <<= 27;
    x += Jnext(seed, 27);
    return (int64_t) x / (double) (1ULL << 53);
}

/* A macro to generate the ideal assembly for X = JnextInt(*S, 24)
 * This is a macro and not an inline function, as many compilers can make use
 * of the additional optimisation passes for the surrounding code.
 */
#define JAVA_NEXT_INT24(S,X)                \
    do {                                    \
        uint64_t a = (1ULL << 48) - 1;      \
        uint64_t c = 0x5deece66dULL * (S);  \
        c += 11; a &= c;                    \
        (S) = a;                            \
        a = (uint64_t) ((int64_t)a >> 17);  \
        c = 0xaaaaaaab * a;                 \
        c = (uint64_t) ((int64_t)c >> 36);  \
        (X) = (int)a - (int)(c << 3) * 3;   \
    } while (0)


/* Jumps forwards in the random number sequence by simulating 'n' calls to next.
 */
static inline void JskipNextN(uint64_t *seed, uint64_t n)
{
    uint64_t m = 1;
    uint64_t a = 0;
    uint64_t im = 0x5deece66dULL;
    uint64_t ia = 0xb;
    uint64_t k;

    for (k = n; k; k >>= 1)
    {
        if (k & 1)
        {
            m *= im;
            a = im * a + ia;
        }
        ia = (im + 1) * ia;
        im *= im;
    }

    *seed = *seed * m + a;
    *seed &= 0xffffffffffffULL;
}


///=============================================================================
///                               Xoroshiro 128
///=============================================================================

STRUCT(Xoroshiro)
{
    uint64_t lo, hi;
};

static inline void xSetSeed(Xoroshiro *xr, uint64_t value)
{
    const uint64_t XL = 0x9e3779b97f4a7c15ULL;
    const uint64_t XH = 0x6a09e667f3bcc909ULL;
    const uint64_t A = 0xbf58476d1ce4e5b9ULL;
    const uint64_t B = 0x94d049bb133111ebULL;
    uint64_t l = value ^ XH;
    uint64_t h = l + XL;
    l = (l ^ (l >> 30)) * A;
    h = (h ^ (h >> 30)) * A;
    l = (l ^ (l >> 27)) * B;
    h = (h ^ (h >> 27)) * B;
    l = l ^ (l >> 31);
    h = h ^ (h >> 31);
    xr->lo = l;
    xr->hi = h;
}

static inline uint64_t xNextLong(Xoroshiro *xr)
{
    uint64_t l = xr->lo;
    uint64_t h = xr->hi;
    uint64_t n = rotl64(l + h, 17) + l;
    h ^= l;
    xr->lo = rotl64(l, 49) ^ h ^ (h << 21);
    xr->hi = rotl64(h, 28);
    return n;
}

static inline int xNextInt(Xoroshiro *xr, uint32_t n)
{
    uint64_t r = (xNextLong(xr) & 0xFFFFFFFF) * n;
    if ((uint32_t)r < n)
    {
        while ((uint32_t)r < (~n + 1) % n)
        {
            r = (xNextLong(xr) & 0xFFFFFFFF) * n;
        }
    }
    return r >> 32;
}

static inline double xNextDouble(Xoroshiro *xr)
{
    return (xNextLong(xr) >> (64-53)) * 1.1102230246251565E-16;
}

static inline float xNextFloat(Xoroshiro *xr)
{
    return (xNextLong(xr) >> (64-24)) * 5.9604645E-8F;
}

static inline void xSkipN(Xoroshiro *xr, int count)
{
    while (count --> 0)
        xNextLong(xr);
}

static inline uint64_t xNextLongJ(Xoroshiro *xr)
{
    int32_t a = xNextLong(xr) >> 32;
    int32_t b = xNextLong(xr) >> 32;
    return ((uint64_t)a << 32) + b;
}

static inline int xNextIntJ(Xoroshiro *xr, uint32_t n)
{
    int bits, val;
    const int m = n - 1;

    if ((m & n) == 0) {
        uint64_t x = n * (xNextLong(xr) >> 33);
        return (int) ((int64_t) x >> 31);
    }

    do {
        bits = (xNextLong(xr) >> 33);
        val = bits % n;
    }
    while ((int32_t)((uint32_t)bits - val + m) < 0);
    return val;
}


//==============================================================================
//                              MC Seed Helpers
//==============================================================================

/**
 * The seed pipeline:
 *
 * getLayerSalt(n)                -> layerSalt (ls)
 * layerSalt (ls), worldSeed (ws) -> startSalt (st), startSeed (ss)
 * startSeed (ss), coords (x,z)   -> chunkSeed (cs)
 *
 * The chunkSeed alone is enough to generate the first PRNG integer with:
 *   mcFirstInt(cs, mod)
 * subsequent PRNG integers are generated by stepping the chunkSeed forwards,
 * salted with startSalt:
 *   cs_next = mcStepSeed(cs, st)
 */

static inline uint64_t mcStepSeed(uint64_t s, uint64_t salt)
{
    return s * (s * 6364136223846793005ULL + 1442695040888963407ULL) + salt;
}

static inline int mcFirstInt(uint64_t s, int mod)
{
    int ret = (int)(((int64_t)s >> 24) % mod);
    if (ret < 0)
        ret += mod;
    return ret;
}

static inline int mcFirstIsZero(uint64_t s, int mod)
{
    return (int)(((int64_t)s >> 24) % mod) == 0;
}

static inline uint64_t getChunkSeed(uint64_t ss, int x, int z)
{
    uint64_t cs = ss + x;
    cs = mcStepSeed(cs, z);
    cs = mcStepSeed(cs, x);
    cs = mcStepSeed(cs, z);
    return cs;
}

static inline uint64_t getLayerSalt(uint64_t salt)
{
    uint64_t ls = mcStepSeed(salt, salt);
    ls = mcStepSeed(ls, salt);
    ls = mcStepSeed(ls, salt);
    return ls;
}

static inline uint64_t getStartSalt(uint64_t ws, uint64_t ls)
{
    uint64_t st = ws;
    st = mcStepSeed(st, ls);
    st = mcStepSeed(st, ls);
    st = mcStepSeed(st, ls);
    return st;
}

static inline uint64_t getStartSeed(uint64_t ws, uint64_t ls)
{
    uint64_t ss = ws;
    ss = getStartSalt(ss, ls);
    ss = mcStepSeed(ss, 0);
    return ss;
}


///============================================================================
///                               Arithmatic
///============================================================================


/* Linear interpolations
 */
static inline double lerp(double part, double from, double to)
{
    return from + part * (to - from);
}

static inline double lerp2(
        double dx, double dy, double v00, double v10, double v01, double v11)
{
    return lerp(dy, lerp(dx, v00, v10), lerp(dx, v01, v11));
}

static inline double lerp3(
        double dx, double dy, double dz,
        double v000, double v100, double v010, double v110,
        double v001, double v101, double v011, double v111)
{
    v000 = lerp2(dx, dy, v000, v100, v010, v110);
    v001 = lerp2(dx, dy, v001, v101, v011, v111);
    return lerp(dz, v000, v001);
}

static inline double clampedLerp(double part, double from, double to)
{
    if (part <= 0) return from;
    if (part >= 1) return to;
    return lerp(part, from, to);
}

/* Find the modular inverse: (1/x) | mod m.
 * Assumes x and m are positive (less than 2^63), co-prime.
 */
static inline ATTR(const)
uint64_t mulInv(uint64_t x, uint64_t m)
{
    uint64_t t, q, a, b, n;
    if ((int64_t)m <= 1)
        return 0; // no solution

    n = m;
    a = 0; b = 1;

    while ((int64_t)x > 1)
    {
        if (m == 0)
            return 0; // x and m are co-prime
        q = x / m;
        t = m; m = x % m;     x = t;
        t = a; a = b - q * a; b = t;
    }

    if ((int64_t)b < 0)
        b += n;
    return b;
}


#endif /* RNG_H_ */




```

---

<a id="file-5"></a>
### File 5: `src/seed_search/realm/config.py`
> **Purpose:** Specification Source of Truth: dynamic_v3_blueprint_config(), 14 Hard Floors & Bounds  
> **Length:** 494 lines | **Language:** PYTHON

```python
"""New profile validation; legacy schema 3/4 contracts keep their own validation."""
import copy
import math
from .. import BACKEND_COMMIT
from .resources import disk_policy

DEFAULT = {
    'schema_version':5,
    'game':{'edition':'bedrock','target_version':'26.52','backend_model':'MC_26_50',
            'backend_commit':BACKEND_COMMIT,'bds_version':'1.26.52.3'},
    'deployment':{'overworld_side_blocks':1536,'nether_side_blocks':896},
    'discovery':{'overworld_bounds':[-2000,-2000,2000,2000],
                 'nether_bounds':[-2000,-2000,2000,2000]},
    'search':{'mode':'prediction','sequence':'permutation','run_key':'0','workers':30,'max_workers':36,
              'numeric_threads_per_worker':1,'native_threads_per_worker':1,'batch_size':32,'pilot_limit':1000,'inventory_mode':'eligibility',
              'memory_target_gib':25,'memory_ceiling_gib':30,'docker_reserve_gib':8,
              'run_disk_limit_bytes':128 << 30,'free_disk_reserve_bytes':16 << 30,
              'projected_bytes_per_seed':65536,
              'structure_order':['ancient_city','village','trial_chamber','mineshaft']},
    'structures':{'required':['stronghold','village','trial_chamber','ancient_city','mineshaft'],
                  'nether_required':['fortress','bastion'],
                  'optional_bonuses':{'monument':5,'outpost':5,'shipwreck':2,'ruined_portal':2,
                                      'buried_treasure':1,'monster_room':1}},
    'biomes':{'spacing':64,'sample_y':63,'lattice':'world','gate_batch_size':16,'refinement_budget':128,'wooded_minimum_families':2,
              'family_bonuses':{'desert':3,'swamp':3,'snowy_ice':2,'badlands':2,'mushroom':3,
                                'plains_meadow':1,'mountains':2,'ocean':2,'rivers_shores':1},
              'variant_bonuses':{'pale_garden':3,'mangrove_swamp':3,'bamboo_jungle':2,
                                 'dappled_forest':2,'warm_ocean':3}},
    'scoring':{'geometry_weight':.8,'biome_fit_weight':.1,'baseline_weight':.1,'baseline_quality_cap':60},
    'terrain':{'variants':['v1','v2'],'native_threads':1,'scheduler':'rotation','resolutions':[128,64,32,16,8,4],
               'center_spacing':64,'refine_center_spacing':16,'rays':32,
               'maximum_refinements_per_anchor':8},
    'bds':{'enabled':True,'version':'1.26.52.3',
           'docker_cli':'/Applications/Docker.app/Contents/Resources/bin/docker',
           'image':'bedrock-verification-poc:1.26.52.3',
           'image_id':'sha256:cf479afd0ab8a8bb095f7aa71fd42064cf5ba7aff6c8a8f4f5503aac826511d8',
           'cpus':4,'memory_gib':6,'verification_budget':20,'persist_snapshot':False,
           'compare_reference':True,'maximum_region_side':256},
    'caves':{'automatic':False,'y_levels':[0,-16,-32,-48],'spacing':64,'maximum_samples':10000},
}


def default_config():
    cfg=copy.deepcopy(DEFAULT)
    from .terrain import SEARCH_V1, SEARCH_V2
    cfg['terrain']['v1']=dict(SEARCH_V1)
    cfg['terrain']['v2']=dict(SEARCH_V2)
    return cfg


BLUEPRINT_CONTRACT='master_seed_blueprint_v1'
BLUEPRINT_COUNTS={'stronghold':1,'mansion':1,'village':5,'trial_chamber':2,
                  'ancient_city':1,'desert_pyramid':1,'jungle_temple':1,
                  'monument':1,'ruined_portal':3,'shipwreck':2,'mineshaft':5}
BLUEPRINT_ORDER=['mansion','jungle_temple','desert_pyramid','monument','ancient_city',
                 'village','trial_chamber','ruined_portal','shipwreck','mineshaft']


def blueprint_config():
    """Historical audited blueprint policy; locked_blueprint_config is current."""
    cfg=default_config()
    cfg['contract']=BLUEPRINT_CONTRACT
    cfg['search']['structure_order']=list(BLUEPRINT_ORDER)
    cfg['structures']={'required':list(BLUEPRINT_COUNTS),
                       'minimum_counts':dict(BLUEPRINT_COUNTS),
                       'nether_required':['fortress','bastion'],
                       'nether_minimum_counts':{'fortress':1,'bastion':1},
                       'optional_bonuses':{'outpost':10}}
    cfg['biomes'].update(sample_y_levels=[63,-48,0,160],
                         required_families=['plains','desert','forest','taiga','jungle','swamp',
                                            'snowy_ice','dark_forest','peaks','stony_shore',
                                            'lush_caves','dripstone_caves','deep_dark'],
                         family_bonuses={},variant_bonuses={})
    cfg['terrain']['variants']=['v1']
    cfg['terrain']['v1']={'mode':'coastal_continent','coastal_continent':{
        'land_fraction_min':.75,'land_fraction_max':.85,'ocean_edge_min_width_blocks':250,
        'ocean_edge_preferred_max_width_blocks':400,'ocean_edge_fraction_min':.5,
        'monument_envelope_half_size_blocks':80}}
    cfg['terrain'].pop('v2',None)
    return cfg


def _integer(value, lo, hi, name):
    if isinstance(value,bool) or not isinstance(value,int) or not lo<=value<=hi:
        raise ValueError(f'{name} must be an integer in {lo}–{hi}')


def memory_budget_gib(search, *, docker_reserve_default=8):
    """Validate the combined scanner/Docker budget before checkpoint mutation."""
    values=[search.get('memory_target_gib',25),search.get('memory_ceiling_gib',30),
            search.get('docker_reserve_gib',docker_reserve_default)]
    for name,value in zip(('memory_target_gib','memory_ceiling_gib','docker_reserve_gib'),values):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or (isinstance(value,float) and not math.isfinite(value)):
            raise ValueError(f'{name} must be a finite number')
    target,ceiling,reserve=values
    if not 0<target<=ceiling<=30:
        raise ValueError('Memory target must fit the agreed 30 GiB combined ceiling')
    if not 0<=reserve<ceiling:
        raise ValueError('Docker reserve must be nonnegative and below the combined memory ceiling')
    return target,ceiling,reserve


def validate_config(cfg):
    if cfg.get('contract')==BLUEPRINT_CONTRACT:
        return validate_blueprint_config(cfg)
    if cfg.get('contract') is not None:raise ValueError('Unknown Realm contract')
    if cfg.get('schema_version')!=5:
        raise ValueError('Realm profile requires schema_version 5')
    for name in DEFAULT:
        if name not in cfg:raise ValueError(f'Missing Realm configuration section {name}')
    for key,value in DEFAULT['game'].items():
        if cfg['game'].get(key)!=value:raise ValueError(f'Unsupported or unpinned game setting {key}')
    if cfg['deployment'] != DEFAULT['deployment']:
        raise ValueError('This Realm contract uses 1536 Overworld and 896 Nether blocks')
    if cfg['discovery'] != DEFAULT['discovery']:
        raise ValueError('Discovery must use exactly half-open [-2000,2000) in each dimension')
    s=cfg['search']
    if s.get('mode')!='prediction' or s.get('sequence') not in ('permutation','sequential','manifest'):
        raise ValueError('Realm scan mode must explicitly label predictions and supported seed sequence')
    if s.get('sequence')=='manifest':
        from ..seeds import parse_seed
        values=s.get('manifest_seeds')
        if not isinstance(values,list) or not 1<=len(values)<=10000 or any(not isinstance(v,str) or str(parse_seed(v))!=v for v in values):
            raise ValueError('Manifest requires 1–10000 canonical signed decimal seeds')
        if len(set(values))!=len(values):raise ValueError('Manifest seeds must be distinct')
    if s.get('inventory_mode','complete') not in ('complete','eligibility'):raise ValueError('Invalid inventory mode')
    if cfg['biomes'].get('lattice','border') not in ('border','world'):raise ValueError('Invalid biome lattice')
    _integer(cfg['biomes'].get('gate_batch_size',16),1,256,'biome gate batch size')
    _integer(cfg['biomes'].get('refinement_budget',0),0,4096,'biome refinement budget')
    key=s.get('run_key')
    if not isinstance(key,str) or not key.isdigit() or not 0<=int(key)<2**64:
        raise ValueError('run_key must be a decimal uint64 string')
    if s['sequence']=='sequential' and int(key)!=0:raise ValueError('Sequential scans require run_key 0')
    _integer(s.get('max_workers'),1,36,'max_workers');_integer(s.get('workers'),1,s['max_workers'],'workers')
    _integer(s.get('batch_size'),1,4096,'batch_size');_integer(s.get('pilot_limit'),1,1000,'pilot_limit')
    if s.get('numeric_threads_per_worker')!=1:raise ValueError('Use exactly one numeric thread per worker')
    _integer(s.get('native_threads_per_worker',1),1,36,'native_threads_per_worker')
    if s['workers']*s.get('native_threads_per_worker',1)>36:
        raise ValueError('Process/native thread product must fit 36 logical CPUs')
    if 'memory_target_gib' not in s or 'memory_ceiling_gib' not in s:
        raise ValueError('Memory target and ceiling must be configured')
    memory_budget_gib(s)
    disk_policy(s)
    if cfg.get('terrain',{}).get('scheduler','rotation') not in ('rotation','priority'):
        raise ValueError('Terrain scheduler must be rotation or priority')
    _integer(cfg.get('terrain',{}).get('native_threads',1),1,36,'terrain.native_threads')
    order=s.get('structure_order',[])
    if len(order)!=4 or set(order)!=set(DEFAULT['search']['structure_order']):
        raise ValueError('All four mandatory non-anchor structures must be checked')
    if cfg['structures'].get('required')!=DEFAULT['structures']['required']:
        raise ValueError('Required structure eligibility cannot be relaxed')
    if cfg['structures'].get('nether_required',DEFAULT['structures']['nether_required'])!=['fortress','bastion']:
        raise ValueError('Both Fortress and Bastion are mandatory in the final Nether square')
    for section,keys in (('structures',('optional_bonuses',)),('biomes',('family_bonuses','variant_bonuses'))):
        for key in keys:
            vals=cfg[section].get(key,{})
            if set(vals)!=set(DEFAULT[section][key]) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in vals.values()):
                raise ValueError(f'Invalid configurable {key}')
    if cfg['biomes'].get('wooded_minimum_families')!=2:raise ValueError('At least two wooded families remain mandatory')
    if cfg['biomes'].get('spacing') not in (4,8,16,32,64,128):raise ValueError('Invalid biome spacing')
    if cfg['biomes'].get('sample_y')!=63:raise ValueError('Fixed-Y predictor must retain declared Y=63 provenance')
    t=cfg['terrain']
    if t.get('variants')!=['v1','v2'] or t.get('rays')!=32:raise ValueError('Only independent V1/V2 with 32 rays are supported')
    if t.get('resolutions')!=[128,64,32,16,8,4]:raise ValueError('Keep the declared adaptive terrain resolutions')
    _integer(t.get('maximum_refinements_per_anchor'),0,10000,'maximum_refinements_per_anchor')
    for key in ('center_spacing','refine_center_spacing'):_integer(t.get(key),1,256,key)
    from .terrain import V1,V2
    for name,defaults in (('v1',V1),('v2',V2)):
        if name in t:
            values=t[name]
            required=set(defaults)-({'ridge_min_arc_rays','ridge_min_arc_aspect','enclosure_policy'} if name=='v2' else set())
            if not isinstance(values,dict) or not required.issubset(values) or set(values)-set(defaults) or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for k,v in values.items() if k!='enclosure_policy'):
                raise ValueError(f'Invalid configurable {name} geometry thresholds')
            if name=='v2':
                _integer(values.get('ridge_min_arc_rays',defaults['ridge_min_arc_rays']),1,t['rays'],'ridge_min_arc_rays')
                if values.get('enclosure_policy','continuous_arcs') not in ('continuous_arcs','surrounding_mountains'):
                    raise ValueError('Invalid configurable v2 enclosure_policy')
    weights=[cfg['scoring'].get(n) for n in ('geometry_weight','biome_fit_weight','baseline_weight')]
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in weights) or abs(sum(weights)-1)>1e-9:
        raise ValueError('Variant weights must be finite, nonnegative and sum to one')
    if cfg['scoring']['baseline_quality_cap']<=0:raise ValueError('Baseline quality cap must be positive')
    if cfg['caves'].get('automatic') is not False:raise ValueError('Cave inventory requires explicit manual invocation')
    if cfg['caves'].get('y_levels')!=[0,-16,-32,-48]:raise ValueError('Keep the agreed initial cave Y levels')
    _integer(cfg['caves'].get('maximum_samples'),1,1000000,'maximum_samples')
    if cfg['caves'].get('spacing') not in (4,8,16,32,64,128):raise ValueError('Invalid manual cave spacing')
    b=cfg['bds']
    for key in ('version','image_id','image'):
        if b.get(key)!=DEFAULT['bds'][key]:raise ValueError(f'BDS {key} must match the verified pin')
    from .verification import validate_bds_pins
    validate_bds_pins(cfg)
    _integer(b.get('cpus'),4,4,'BDS CPUs');_integer(b.get('verification_budget'),0,10000,'verification_budget')
    if b.get('memory_gib')!=6:raise ValueError('Tested BDS allocation requires exactly 6 GiB memory')
    return cfg


LOCKED_REVISION='locked-2048-1024-v1'
RIVER_REVISION='locked-2048-1024-river-v2'
OUTPOST_REVISION='locked-2048-1024-outpost-v3'
ORIGIN_REVISION='origin-fixed-2048-v1'
TWO_GROUP_REVISION='origin-fixed-2048-two-group-v2'
TWO_GROUP_MARINE_REVISION='origin-fixed-2048-two-group-marine-v3'
DYNAMIC_REVISION='dynamic-envelope-1664-v1'
DYNAMIC_V2_REVISION='dynamic-envelope-1664-v2'
DYNAMIC_V3_REVISION='dynamic-envelope-2048-v3'
ORIGIN_ORDER=['ruined_portal','trial_chamber','outpost','desert_pyramid','jungle_temple',
              'mansion','ancient_city','village','mineshaft']
TWO_GROUP_ORDER=['outpost','desert_pyramid','jungle_temple','ruined_portal',
                 'trial_chamber','mansion','ancient_city','village','mineshaft']
TWO_GROUP_STRONGHOLD_AFTER=4


def stronghold_after(cfg):
    """Preserve replay ordering for v2 runs created before the new filter order."""
    return cfg['search'].get('stronghold_after_structure_count',2) if two_group_policy(cfg) else 2
OUTPOST_ORDER=['ruined_portal','outpost','desert_pyramid','jungle_temple','mansion',
               'ancient_city','village','trial_chamber','mineshaft']
LOCKED_ORDER=['ruined_portal','trial_chamber','mansion','desert_pyramid',
              'jungle_temple','ancient_city','village','mineshaft']


def locked_blueprint_config():
    """Current geometry; blueprint_config retains the historical audited policy."""
    cfg=blueprint_config()
    cfg['screening_revision']=LOCKED_REVISION
    cfg['deployment']={'overworld_side_blocks':2048,'nether_side_blocks':1024}
    cfg['search']['structure_order']=list(LOCKED_ORDER)
    cfg['structures']['minimum_counts'].update(village=6,trial_chamber=5,ruined_portal=6,
                                              mineshaft=15,ancient_city=2,shipwreck=4)
    cfg['structures']['nether_minimum_counts']={'fortress':2,'bastion':2}
    cfg['structures']['deferred_until_coastal_terrain']=['monument','shipwreck','outpost']
    cfg['terrain']['v1']['square_side_blocks']=2048
    return cfg


def locked_policy(cfg):
    return cfg.get('screening_revision') in (LOCKED_REVISION,RIVER_REVISION,OUTPOST_REVISION,ORIGIN_REVISION,TWO_GROUP_REVISION,TWO_GROUP_MARINE_REVISION,DYNAMIC_REVISION,DYNAMIC_V2_REVISION,DYNAMIC_V3_REVISION)


def river_policy(cfg):
    return cfg.get('screening_revision') in (RIVER_REVISION,OUTPOST_REVISION,ORIGIN_REVISION,TWO_GROUP_REVISION,TWO_GROUP_MARINE_REVISION)


def outpost_policy(cfg):
    return cfg.get('screening_revision') in (OUTPOST_REVISION,ORIGIN_REVISION,TWO_GROUP_REVISION,TWO_GROUP_MARINE_REVISION,DYNAMIC_REVISION,DYNAMIC_V2_REVISION,DYNAMIC_V3_REVISION)


def origin_policy(cfg):
    return cfg.get('screening_revision') in (ORIGIN_REVISION,TWO_GROUP_REVISION,TWO_GROUP_MARINE_REVISION)


def baseline_requirements(cfg):
    if dynamic_v2_policy(cfg):return 19+len(cfg['biomes']['required_families'])
    return 32 if dynamic_policy(cfg) else 26 if marine_baseline_policy(cfg) else 24 if outpost_policy(cfg) else 23 if locked_policy(cfg) else 25


def river_blueprint_config():
    """Historical river profile retained for reproducible controls and checkpoints."""
    cfg=locked_blueprint_config()
    cfg['screening_revision']=RIVER_REVISION
    cfg['structures']['nether_minimum_counts']['bastion']=3
    cfg['structures']['minimum_counts']['shipwreck']=5
    cfg['terrain']['v1']['coastal_continent'].update(
        land_connectivity=8,bridge_inland_freshwater=True,
        river_corridor_min_length_blocks=600,
        river_highway_hub_radius_blocks=250,river_highway_bonus_points=20)
    return cfg


def outpost_blueprint_config():
    cfg=river_blueprint_config()
    cfg['screening_revision']=OUTPOST_REVISION
    cfg['search']['structure_order']=list(OUTPOST_ORDER)
    cfg['structures']['required'].append('outpost')
    cfg['structures']['minimum_counts']['outpost']=2
    cfg['structures']['optional_bonuses']={}
    cfg['structures']['deferred_until_coastal_terrain']=['monument','shipwreck']
    return cfg


def origin_blueprint_config():
    """Origin is an evaluation center; Strongholds remain real predicted starts."""
    cfg=outpost_blueprint_config()
    cfg['screening_revision']=ORIGIN_REVISION
    cfg['discovery']['overworld_bounds']=[-1024,-1024,1024,1024]
    cfg['discovery']['nether_bounds']=[-512,-512,512,512]
    cfg['search']['structure_order']=list(ORIGIN_ORDER)
    cfg['terrain']['v1']['coastal_continent']['river_highway_bonus_points']=35
    return cfg


def two_group_blueprint_config():
    """Versioned B=2 target categories; hard floors never consume the budget."""
    cfg=origin_blueprint_config()
    cfg['screening_revision']=TWO_GROUP_REVISION
    cfg['search']['structure_order']=list(TWO_GROUP_ORDER)
    cfg['search']['stronghold_after_structure_count']=TWO_GROUP_STRONGHOLD_AFTER
    cfg['search']['max_misses']=2
    cfg['structures']['minimum_counts'].update(
        trial_chamber=10,village=7,ruined_portal=7,mineshaft=20,outpost=1,shipwreck=3)
    cfg['structures']['hard_floors']={
        'stronghold':1,'jungle_temple':1,'desert_pyramid':1,'outpost':1,
        'mansion':0,'trial_chamber':8,'village':5,'ruined_portal':5,
        'mineshaft':17,'ancient_city':1,'fortress':1,'bastion':2}
    return cfg


def marine_baseline_blueprint_config():
    """Versioned v2 baseline with strict predicted marine start counts, no terrain gate."""
    cfg=two_group_blueprint_config()
    cfg['screening_revision']=TWO_GROUP_MARINE_REVISION
    cfg['structures']['hard_floors'].update(monument=1,shipwreck=3)
    cfg['structures']['deferred_until_coastal_terrain']=[]
    coastal=cfg['terrain']['v1']['coastal_continent']
    for key in ('river_corridor_min_length_blocks','river_highway_hub_radius_blocks','river_highway_bonus_points'):
        coastal.pop(key,None)
    return cfg


def marine_baseline_policy(cfg):
    return cfg.get('screening_revision')==TWO_GROUP_MARINE_REVISION


def dynamic_policy(cfg):
    return cfg.get('screening_revision') in (DYNAMIC_REVISION, DYNAMIC_V2_REVISION, DYNAMIC_V3_REVISION)


def dynamic_v1_policy(cfg):
    return cfg.get('screening_revision') == DYNAMIC_REVISION


def dynamic_v2_policy(cfg):
    return cfg.get('screening_revision') in (DYNAMIC_V2_REVISION, DYNAMIC_V3_REVISION)


def dynamic_v3_policy(cfg):
    return cfg.get('screening_revision') == DYNAMIC_V3_REVISION


def dynamic_blueprint_config():
    """Historical sliding-center policy (v1, 1664x1664)."""
    cfg=marine_baseline_blueprint_config()
    cfg['screening_revision']=DYNAMIC_REVISION
    cfg['deployment']={'overworld_side_blocks':1664,'nether_side_blocks':832}
    cfg['discovery']={'overworld_bounds':[-2000,-2000,2000,2000],
                      'nether_bounds':[-562,-562,562,562]}
    cfg['structures']['minimum_counts'].update(village=9,trial_chamber=8,
        ancient_city=4,desert_pyramid=3,jungle_temple=3,monument=1,
        ruined_portal=7,shipwreck=6,mineshaft=15,outpost=2,mansion=1)
    cfg['structures']['nether_minimum_counts']={'fortress':2,'bastion':2}
    cfg['structures']['hard_floors']={'stronghold':1,'mansion':1,'village':8,
        'trial_chamber':7,'ancient_city':3,'desert_pyramid':2,'jungle_temple':2,
        'monument':1,'ruined_portal':5,'shipwreck':4,'mineshaft':12,
        'outpost':2,'fortress':2,'bastion':2}
    cfg['structures']['deferred_until_coastal_terrain']=[]
    cfg['terrain']['v1']['square_side_blocks']=1664
    cfg['terrain']['v1']['coastal_continent'].update(
        land_fraction_min=.70,land_fraction_max=.80,
        ocean_edge_min_width_blocks=200,ocean_edge_preferred_max_width_blocks=300)
    cfg['search']['density_weights']={'village':3,'trial_chamber':2,'ancient_city':2,'desert_pyramid':1,'jungle_temple':1,'outpost':1}
    cfg['search']['centroid_weights']={'village':3,'trial_chamber':2,'ruined_portal':2,'ancient_city':2,'outpost':1,'desert_pyramid':1,'jungle_temple':1,'mansion':1,'monument':1,'stronghold':1,'shipwreck':1}
    cfg['biomes']['include_frozen_peaks']=True
    cfg['biomes']['nether_required']=['nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas']
    cfg['search'].pop('stronghold_after_structure_count',None)
    return cfg


def dynamic_v2_blueprint_config():
    """Historical player-envelope policy (v2, 1664x1664)."""
    cfg=dynamic_blueprint_config()
    cfg['screening_revision']=DYNAMIC_V2_REVISION
    cfg['search']['max_misses']=3
    cfg['search']['centroid_weights']={
        'village':3,'trial_chamber':2,'ruined_portal':0,'ancient_city':2,
        'outpost':1,'desert_pyramid':1,'jungle_temple':1,'mansion':1,
        'monument':1,'stronghold':1,'shipwreck':0
    }
    cfg['terrain']['variants']=[]
    cfg['terrain'].pop('v1',None)
    return cfg


def dynamic_v3_blueprint_config():
    """Active player-envelope policy (v3, 2048x2048 overworld, 1024x1024 nether)."""
    cfg=dynamic_v2_blueprint_config()
    cfg['screening_revision']=DYNAMIC_V3_REVISION
    cfg['deployment']={'overworld_side_blocks':2048,'nether_side_blocks':1024}
    cfg['discovery']={'overworld_bounds':[-2000,-2000,2000,2000],
                      'nether_bounds':[-634,-634,634,634]}
    cfg['structures']['minimum_counts'].update(
        village=6,trial_chamber=8,ancient_city=2,desert_pyramid=1,
        jungle_temple=1,monument=1,ruined_portal=8,shipwreck=4,
        mineshaft=10,outpost=1,mansion=1
    )
    cfg['structures']['nether_minimum_counts']={'fortress':1,'bastion':2}
    cfg['structures']['hard_floors']={
        'stronghold':1,'mansion':1,'village':6,'trial_chamber':8,
        'ancient_city':2,'desert_pyramid':1,'jungle_temple':1,
        'monument':1,'ruined_portal':8,'shipwreck':4,'mineshaft':10,
        'outpost':1,'fortress':1,'bastion':2
    }
    cfg['search']['centroid_weights']={
        'village':3,'trial_chamber':2,'ruined_portal':0,'ancient_city':2,
        'outpost':1,'desert_pyramid':2,'jungle_temple':2,'mansion':2,
        'monument':1,'stronghold':1,'shipwreck':0
    }
    cfg['search']['max_misses']=0
    return cfg


def two_group_policy(cfg):
    return cfg.get('screening_revision') in (TWO_GROUP_REVISION,TWO_GROUP_MARINE_REVISION,DYNAMIC_REVISION,DYNAMIC_V2_REVISION,DYNAMIC_V3_REVISION)


def validate_blueprint_config(cfg):
    """Validate common pins through legacy validation, then the explicit contract."""
    expected=(dynamic_v3_blueprint_config() if dynamic_v3_policy(cfg) else
              dynamic_v2_blueprint_config() if dynamic_v2_policy(cfg) else
              dynamic_blueprint_config() if dynamic_policy(cfg) else
              marine_baseline_blueprint_config() if marine_baseline_policy(cfg) else
              two_group_blueprint_config() if two_group_policy(cfg) else
              origin_blueprint_config() if origin_policy(cfg) else
              outpost_blueprint_config() if outpost_policy(cfg) else
              river_blueprint_config() if river_policy(cfg) else
              locked_blueprint_config() if locked_policy(cfg) else
              blueprint_config())
    if cfg.get('screening_revision') not in (None,LOCKED_REVISION,RIVER_REVISION,OUTPOST_REVISION,ORIGIN_REVISION,TWO_GROUP_REVISION,TWO_GROUP_MARINE_REVISION,DYNAMIC_REVISION,DYNAMIC_V2_REVISION,DYNAMIC_V3_REVISION):raise ValueError('Unknown blueprint screening revision')
    if cfg['deployment']!=expected['deployment']:raise ValueError('Blueprint geometry differs from its revision')
    if cfg['discovery']!=expected['discovery']:raise ValueError('Blueprint discovery bounds differ from its revision')
    legacy=copy.deepcopy(cfg)
    legacy.pop('contract',None)
    legacy['deployment']=copy.deepcopy(DEFAULT['deployment'])
    legacy['discovery']=copy.deepcopy(DEFAULT['discovery'])
    legacy['search']['structure_order']=list(DEFAULT['search']['structure_order'])
    legacy['structures']=copy.deepcopy(DEFAULT['structures'])
    legacy['biomes']['family_bonuses']=copy.deepcopy(DEFAULT['biomes']['family_bonuses'])
    legacy['biomes']['variant_bonuses']=copy.deepcopy(DEFAULT['biomes']['variant_bonuses'])
    legacy['terrain'].update(variants=['v1','v2'])
    from .terrain import SEARCH_V1,SEARCH_V2
    legacy['terrain']['v1']=dict(SEARCH_V1);legacy['terrain']['v2']=dict(SEARCH_V2)
    validate_config(legacy)
    if two_group_policy(cfg) and not dynamic_policy(cfg):
        _integer(cfg['search'].get('max_misses'),0,8,'max_misses')
        expected_after=TWO_GROUP_STRONGHOLD_AFTER if cfg['search']['structure_order']==TWO_GROUP_ORDER else 2
        if stronghold_after(cfg)!=expected_after:
            raise ValueError('Stronghold placement differs from the resolved filter order')
    if dynamic_policy(cfg):
        max_misses_limit=0 if dynamic_v3_policy(cfg) else (3 if dynamic_v2_policy(cfg) else 2)
        _integer(cfg['search'].get('max_misses'),0,max_misses_limit,'max_misses')
        weights=cfg['search'].get('density_weights')
        if not isinstance(weights,dict) or set(weights)!=set(expected['search']['density_weights']):
            raise ValueError('Dynamic density weights must name all six supported structures')
        for name,weight in weights.items():_integer(weight,0,1000,f'density_weights.{name}')
        if not any(weights.values()):raise ValueError('At least one density weight must be positive')
        if cfg['search'].get('centroid_weights')!=expected['search']['centroid_weights']:raise ValueError('Centroid weights differ from the blueprint')
        if cfg['biomes'].get('include_frozen_peaks') is not True:raise ValueError('Dynamic peak witnesses include Frozen Peaks')
        if cfg['biomes'].get('nether_required')!=expected['biomes']['nether_required']:raise ValueError('All five Nether biome families are required')
    if two_group_policy(cfg):
        actual=cfg['structures'];baseline=expected['structures']
        if set(actual)!=set(baseline) or any(actual[k]!=baseline[k] for k in baseline if k not in ('minimum_counts','nether_minimum_counts')):
            raise ValueError('Blueprint structure floors and allowed bonuses cannot be relaxed')
        if set(actual['minimum_counts'])!=set(baseline['minimum_counts']) or set(actual['nether_minimum_counts'])!=set(baseline['nether_minimum_counts']):
            raise ValueError('Blueprint structure goal keys differ from the policy')
        strict={'stronghold'} if dynamic_policy(cfg) else {'stronghold','jungle_temple','desert_pyramid','outpost'}
        if marine_baseline_policy(cfg):strict.update(('monument','shipwreck'))
        for name,goal in actual['minimum_counts'].items():
            _integer(goal,0,64,f'minimum_counts.{name}')
            floor=baseline['hard_floors'].get(name,baseline['minimum_counts'][name])
            if goal<floor or (name in strict and goal!=baseline['minimum_counts'][name]):
                raise ValueError(f'Blueprint goal below fixed floor or strict target: {name}')
        for name,goal in actual['nether_minimum_counts'].items():
            _integer(goal,0,64,f'nether_minimum_counts.{name}')
            if goal<baseline['hard_floors'][name]:raise ValueError(f'Blueprint goal below fixed floor: {name}')
    elif cfg['structures']!=expected['structures']:
        raise ValueError('Blueprint structure floors and allowed bonuses cannot be relaxed')
    order=cfg['search']['structure_order']
    if len(order)!=len(expected['search']['structure_order']) or set(order)!=set(expected['search']['structure_order']):
        raise ValueError('Blueprint must check every required non-anchor structure')
    for key in ('spacing','sample_y','sample_y_levels','lattice','required_families','family_bonuses','variant_bonuses'):
        if key=='required_families' and dynamic_v2_policy(cfg):
            selected=cfg['biomes'].get(key)
            allowed=expected['biomes'][key]
            if (not isinstance(selected,list) or not all(isinstance(f,str) for f in selected) or
                len(set(selected))!=len(selected) or not set(selected)<=set(allowed)):
                raise ValueError('Required biome families must be a unique subset of the supported v2 families')
            continue
        if cfg['biomes'].get(key)!=expected['biomes'][key]:
            raise ValueError(f'Blueprint biome policy differs: {key}')
    if dynamic_v2_policy(cfg):
        if cfg['terrain'].get('variants')!=[]:
            raise ValueError('Dynamic V2 requires empty terrain active variants')
    else:
        if cfg['terrain'].get('variants')!=['v1'] or cfg['terrain'].get('v1')!=expected['terrain']['v1'] or 'v2' in cfg['terrain']:
            raise ValueError('Blueprint requires only V1 Coastal Continent with its declared thresholds')
    return cfg

```

---

<a id="file-6"></a>
### File 6: `src/seed_search/realm/blueprint.py`
> **Purpose:** Python Reference Scoring Oracle: dynamic_v3_score() 1,250 Pts Model & evaluate_dynamic_seed()  
> **Length:** 983 lines | **Language:** PYTHON

```python
"""Explicit Master Seed Blueprint predictor contract, separate from legacy Realm V1.

Sparse biome witnesses and count floors are model evidence, never Bedrock truth.
The exhaustive reference path uses the same constraints without early exits.
"""
import os
import platform
import resource
import time

import numpy as np

from ..backend import Backend, biome_name
from ..seeds import parse_seed
from .biomes import canonical, FAMILIES, WOOD
from .bounds import square, native_bounds, nether_square, json_bounds, contains
from .config import BLUEPRINT_CONTRACT, stronghold_after
from .sampling import BiomeSampler, grid_points, dispersed_indices

PALETTE={
    'plains':{'plains','sunflower_plains','meadow'},
    'desert':FAMILIES['desert'], 'forest':{'forest','birch_forest','flower_forest','old_growth_birch_forest'},
    'taiga':{'taiga','old_growth_pine_taiga','old_growth_spruce_taiga'},
    'jungle':{'jungle','bamboo_jungle'}, 'swamp':FAMILIES['swamp'],
    'snowy_ice':FAMILIES['snowy_ice']|{'frozen_ocean','deep_frozen_ocean','frozen_river'},
    'dark_forest':{'dark_forest'}, 'peaks':{'jagged_peaks','stony_peaks'},
    'stony_shore':{'stony_shore'}, 'lush_caves':{'lush_caves'},
    'dripstone_caves':{'dripstone_caves'}, 'deep_dark':{'deep_dark'},
}
CAVE_FAMILIES={'lush_caves','dripstone_caves','deep_dark'}


def biome_gate(backend,bounds,cfg,*,complete=False):
    """Public benchmark entry point; bounds are half-open block coordinates."""
    sampler=BiomeSampler(backend)
    result=biome_palette(sampler,bounds,cfg['biomes'],complete=complete)
    result['queried_points']=sampler.queried
    result['cache_hits']=sampler.hits
    return result


def biome_palette(sampler,bounds,policy,*,complete=False):
    """Sample all four Y planes; surface and cave witness roles stay distinct."""
    expected=list(policy['required_families'])
    grids=[grid_points(bounds,policy['spacing'],y,'world') for y in policy['sample_y_levels']]
    # Interleave Y at each dispersed XZ. This does not confuse Y with surface height.
    points=np.stack(grids,axis=1).reshape(-1,3)
    xz_order=dispersed_indices(len(grids[0]))
    order=(xz_order[:,None]*len(grids)+np.arange(len(grids))).ravel()
    found={};samples=[];names=set();batch_size=policy.get('gate_batch_size',16)*len(grids)
    for offset in range(0,len(order),batch_size):
        if len(found)==len(expected) and not complete:break
        batch=points[order[offset:offset+batch_size]]
        values=sampler.sample(batch)
        for point,value in zip(batch,values):
            name=canonical(biome_name(int(value)));names.add(name)
            row={'coordinate':point.tolist(),'id':int(value),'biome':name}
            samples.append(row)
            for family in expected:
                role_y=(-48,0) if family in CAVE_FAMILIES else (63,160)
                if family not in found and int(point[1]) in role_y and name in (PALETTE[family]|({'frozen_peaks'} if family=='peaks' and policy.get('include_frozen_peaks') else set())):
                    found[family]=row
    missing=[f for f in expected if f not in found]
    return {'qualification':'PENDING' if missing else 'PREDICTED','data_status':'PREDICTED',
            'raw_names':sorted(names),'required_families':expected,'observed_families':list(found),
            'missing_families':missing,'witnesses':found,'sample_count':len(samples),
            'bounds':json_bounds(bounds),'spacing':policy['spacing'],
            'sample_y_levels':list(policy['sample_y_levels']),
            'sampling':{'version':'blueprint-four-y-v1','lattice':'world','expected_points':len(points),
                        'samples':samples,'complete_defined_lattice':len(samples)==len(points)},
            'inventory_status':'COMPLETE' if len(samples)==len(points) else 'POSITIVE_WITNESSES',
            'surface_generation_verified':False,'cave_generation_verified':False,
            'source':'MC_26_50 3D biome prediction at four fixed Y planes; not actual surface/cave generation',
            'negative_meaning':'unseen families remain unknown; no exhaustive absence claim',
            'score':0,'uncertainty':{'domain':'prediction_model_only','score_interval':[0,0],
                                   'actual_generation_score_interval':[0,0],'exhaustive_verified':False}}


def count_observation(backend,name,bounds,minimum,*,capped=True,combined=True):
    from .baseline import structure_observation
    # The pinned Mansion predictor also permits Pale Garden. The blueprint
    # specifically asks for a Dark Forest anchor; inspect every start before
    # selecting the qualifying subset, so an early Pale Garden cannot hide one.
    if name=='mansion':capped=False
    if capped and hasattr(backend,'structure_count'):
        points=backend.structure_count(name,native_bounds(bounds),minimum)
        coords=sorted({tuple(p) for p in points if contains(p,bounds)})
        observation={'type':name,'bounds':json_bounds(bounds),'raw':[],
                     'coordinates':[list(p) for p in coords],
                     'predicted_viable':[list(p) for p in coords],
                     'data_status':'PREDICTED' if coords else 'PARTIAL',
                     'verification':'UNVERIFIED','complete':False,'confirmed_absent':False,
                     'inventory_status':'FLOOR_WITNESSES' if len(coords)>=minimum else 'COMPLETE',
                     'detection_method':'native_count_floor','raw_inventory_status':'NOT_RECORDED',
                     'negative_meaning':'predictor count below floor; not confirmed actual absence'}
    else:
        observation=structure_observation(backend,name,bounds,combined)
    if name=='mansion' and observation['predicted_viable']:
        starts=observation['predicted_viable']
        xyz=np.array([[x,63,z] for x,z in starts],dtype=np.int32)
        ids=backend.biome_points(xyz)
        names=[canonical(biome_name(int(value))) for value in ids]
        observation['unfiltered_predicted_viable']=starts
        observation['anchor_biome_witnesses']=[{'coordinate':p.tolist(),'biome':n} for p,n in zip(xyz,names)]
        observation['predicted_viable']=[p for p,n in zip(starts,names) if n=='dark_forest']
        observation['coordinates']=observation['predicted_viable']
        observation['anchor_biome_policy']='Dark Forest at start Y=63; fixed-Y predictor witness, actual surface unresolved'
    count=len(observation['predicted_viable'])
    observation.update(minimum_count=minimum,predicted_count=count,
                       count_is_complete=observation['inventory_status']=='COMPLETE',
                       floor_status='PREDICTED' if count>=minimum else 'PENDING')
    return observation


def smart_score(structures,nether,optional,*,coastal_footprint_verified=False,locked=False,river=False,metrics=None,origin=False,biome_names=(),two_group=False,river_bonus=True):
    """Blueprint bonuses from predictor counts; footprint bonus needs actual bounds."""
    counts={k:len(v.get('predicted_viable',[])) for k,v in {**structures,**nether,**optional}.items()}
    if two_group:
        names=set(biome_names)
        bonuses={
            'mansion':50*min(counts.get('mansion',0),2),
            'stronghold':50*int(counts.get('stronghold',0)>=2),
            'mega_ravine_hub':35*int((metrics or {}).get('mega_ravine_hub') is True),
            'river_highway':35*int((metrics or {}).get('river_highway_connected') is True),
            'ancient_city':25*max(0,min(counts.get('ancient_city',0),4)-2),
            'fortress':20*max(0,min(counts.get('fortress',0),4)-2),
            'bastion':20*max(0,counts.get('bastion',0)-3),
            'monument':30*int(coastal_footprint_verified and counts.get('monument',0)>=2),
            'trial_chamber':10*max(0,counts.get('trial_chamber',0)-10),
            'village':5*max(0,counts.get('village',0)-7),
            'ruined_portal':5*max(0,counts.get('ruined_portal',0)-7),
            'mineshaft':max(0,counts.get('mineshaft',0)-20),
            'outpost':10*max(0,counts.get('outpost',0)-1),
            'desert_pyramid':10*int(counts.get('desert_pyramid',0)>=2),
            'jungle_temple':10*int(counts.get('jungle_temple',0)>=2),
            'shipwreck':5*max(0,counts.get('shipwreck',0)-5),
            'cherry_grove':15*int('cherry_grove' in names),
            'badlands':15*int(bool(names & {'badlands','wooded_badlands','eroded_badlands'})),
            'mushroom_fields':15*int('mushroom_fields' in names),
        }
        if not river_bonus:bonuses.pop('river_highway',None)
        return {'score':sum(bonuses.values()),'bonuses':bonuses,'counts':counts,
                'source':'v2 predictor starts and supported deferred feature evidence; actual generation unverified',
                'coastal_footprint_bonus_status':'VERIFIED' if coastal_footprint_verified else 'PENDING actual footprint containment'}
    bonuses={}
    for name,floor,points in (('village',6 if locked else 5,5),('ruined_portal',6 if locked else 3,5),('shipwreck',5 if river else 4 if locked else 2,5),('mineshaft',15 if locked else 5,1)):
        bonuses[name]=max(0,counts.get(name,0)-floor)*points
    for name,floor,cap,points in (('trial_chamber',5,counts.get('trial_chamber',0),10),('ancient_city',2,4,15),('fortress',2,4,15),('bastion',2,4,15)) if locked else (('trial_chamber',2,4,10),('ancient_city',1,3,15),('fortress',1,3,15),('bastion',1,3,15)):
        bonuses[name]=max(0,min(cap,counts.get(name,0))-floor)*points
    for name in ('desert_pyramid','jungle_temple'):
        n=counts.get(name,0);bonuses[name]=(20 if n>=2 else 0)+(10 if n>=3 and (not locked or name=='desert_pyramid') else 0)
    bonuses['monument']=30*int(counts.get('monument',0)>=2)
    if river:
        bonuses['bastion']=max(0,counts.get('bastion',0)-3)*15
        bonuses['mansion']=50*int(counts.get('mansion',0)>=2)
        bonuses['river_highway']=20*int((metrics or {}).get('river_highway_connected') is True)
    bonuses['coastal_monument_footprint']=25*int(coastal_footprint_verified)
    bonuses['outpost']=10*counts.get('outpost',0)
    if origin:
        # The origin policy's advertised jackpots are scored from observed
        # predictor evidence; deferred marine/terrain bonuses arrive later.
        bonuses.update(stronghold=50*int(counts.get('stronghold',0)>=2),
                       ancient_city=25*max(0,min(counts.get('ancient_city',0),4)-2),
                       fortress=20*max(0,min(counts.get('fortress',0),4)-2),
                       bastion=20*max(0,counts.get('bastion',0)-3),
                       desert_pyramid=10*int(counts.get('desert_pyramid',0)>=2),
                       jungle_temple=10*int(counts.get('jungle_temple',0)>=2),
                       outpost=10*max(0,counts.get('outpost',0)-2),
                       river_highway=35*int((metrics or {}).get('river_highway_connected') is True),
                       mega_ravine_hub=35*int((metrics or {}).get('mega_ravine_hub') is True))
        observed=set(biome_names)
        bonuses.update(cherry_grove=15*int('cherry_grove' in observed),
                       badlands=15*int(bool(observed & {'badlands','wooded_badlands','eroded_badlands'})),
                       mushroom_fields=15*int('mushroom_fields' in observed))
    if not river_bonus:bonuses.pop('river_highway',None)
    return {'score':sum(bonuses.values()),'bonuses':bonuses,'counts':counts,
            'source':'predictor start counts; actual generation unverified',
            'coastal_footprint_bonus_status':'VERIFIED' if coastal_footprint_verified else 'PENDING actual footprint containment'}


def score_uncertainty(score,pending,complete):
    return {'domain':'prediction_model_only','prediction_score_interval':[score,score if complete else None],
            'actual_generation_score_interval':[0,None],'pending_prediction_requirements':list(pending),
            'eligibility_verified':False,'interpretation':'Count and biome witnesses are predictions; actual counts, surface palette, cave generation and monument extent require verification.'}


def evaluate_seed(index,seed,cfg,*,backend_factory=Backend,combined=True,short_circuit=True):
    from .config import locked_policy, dynamic_policy
    if dynamic_policy(cfg):return evaluate_dynamic_seed(index,seed,cfg,backend_factory=backend_factory,combined=combined,short_circuit=short_circuit)
    if locked_policy(cfg):return evaluate_locked_seed(index,seed,cfg,backend_factory=backend_factory,combined=combined,short_circuit=short_circuit)
    from .baseline import structure_observation
    seed=parse_seed(seed);start=time.perf_counter();cpu=time.process_time();times={};counts={};anchors=[]
    def timed(name,fn):
        before=time.perf_counter()
        try:return fn()
        finally:times[name]=times.get(name,0)+time.perf_counter()-before
    # Complete/reference mode uses full scans and evaluates all constraints.
    capped=short_circuit and cfg['search'].get('inventory_mode')=='eligibility'
    with backend_factory(seed) as backend:
        sampler=BiomeSampler(backend)
        discovery_bounds=cfg['discovery']['overworld_bounds']
        strongholds=timed('stronghold',lambda:structure_observation(backend,'stronghold',discovery_bounds,combined))
        # Broad Nether discovery is irrelevant to the centered final border.
        fortress={'type':'fortress','bounds':list(cfg['discovery']['nether_bounds']),
                  'raw':[],'predicted_viable':[],'coordinates':[],'data_status':'NOT_REQUESTED',
                  'verification':'UNVERIFIED','confirmed_absent':False,'complete':False}
        counts['stronghold_anchors']=len(strongholds['predicted_viable'])
        for anchor in strongholds['predicted_viable']:
            bounds=square(anchor,1536);nb=nether_square(anchor,896)
            required={'stronghold':{**strongholds,'bounds':json_bounds(bounds),'coordinates':[anchor],
                'raw':[anchor],'predicted_viable':[anchor],'minimum_count':1,'predicted_count':1,'floor_status':'PREDICTED'}}
            pending=[];nether={};optional={};biomes=None
            counts['structure_stage_entered']=counts.get('structure_stage_entered',0)+1
            for name in cfg['search']['structure_order']:
                if pending and short_circuit:
                    required[name]={'type':name,'bounds':json_bounds(bounds),'raw':[],
                        'coordinates':[],'predicted_viable':[],'minimum_count':cfg['structures']['minimum_counts'][name],
                        'data_status':'PARTIAL','verification':'DEFERRED','confirmed_absent':False,
                        'complete':False,'inventory_status':'DEFERRED','floor_status':'PENDING'}
                    continue
                goal=cfg['structures']['minimum_counts'][name]
                observation=timed('structure_'+name,lambda n=name,g=goal:count_observation(backend,n,bounds,g,capped=capped,combined=combined))
                required[name]=observation
                counts['checked_'+name]=counts.get('checked_'+name,0)+1
                if observation['floor_status']!='PREDICTED':
                    pending.append('count_'+name);counts['pending_'+name]=counts.get('pending_'+name,0)+1
            if not pending or not short_circuit:
                counts['nether_stage_entered']=counts.get('nether_stage_entered',0)+1
                pairs=timed('final_nether_pair',lambda:backend.nether_structure_pairs(native_bounds(nb))) if combined and hasattr(backend,'nether_structure_pairs') else None
                for name in ('fortress','bastion'):
                    observation=timed('final_'+name,lambda n=name:structure_observation(backend,n,nb,combined,pair=pairs[n] if pairs else None))
                    observation.update(minimum_count=1,predicted_count=len(observation['predicted_viable']))
                    nether[name]=observation
                    if not observation['predicted_viable']:pending.append('count_'+name)
            if not pending:counts['structure_stage_passed']=counts.get('structure_stage_passed',0)+1
            if not pending or not short_circuit:
                counts['biome_stage_entered']=counts.get('biome_stage_entered',0)+1
                before=sampler.queried
                biomes=timed('biome_palette_4y',lambda:biome_palette(sampler,bounds,cfg['biomes'],complete=not short_circuit))
                counts['biome_samples']=counts.get('biome_samples',0)+sampler.queried-before
                if biomes['missing_families']:pending.extend('biome_'+f for f in biomes['missing_families'])
                else:counts['biome_stage_passed']=counts.get('biome_stage_passed',0)+1
            # All jackpot counts are inventoried only for full baseline survivors.
            # No legacy presence inventory can overwrite this count contract.
            inventory_complete=not pending
            if inventory_complete:
                for name in cfg['search']['structure_order']:
                    if not required[name].get('count_is_complete',False):
                        required[name]=timed('ranking_inventory',lambda n=name:count_observation(backend,n,bounds,cfg['structures']['minimum_counts'][n],capped=False,combined=combined))
                optional['outpost']=timed('ranking_inventory',lambda:structure_observation(backend,'outpost',bounds,combined))
            ranking=smart_score(required,nether,optional)
            score=ranking['score'];status='PENDING' if pending else 'PREDICTED'
            anchors.append({'id':f'{seed}:{anchor[0]}:{anchor[1]}','index':index,'seed':str(seed),'stronghold':anchor,
                'contract':BLUEPRINT_CONTRACT,'game_version':cfg['game']['target_version'],
                'bds_version':cfg['game']['bds_version'],'backend_model':cfg['game']['backend_model'],
                'backend_commit':cfg['game']['backend_commit'],
                'bounds':{'overworld':json_bounds(bounds),'initial_overworld':list(discovery_bounds),
                          'initial_nether':list(cfg['discovery']['nether_bounds']),'final_nether':json_bounds(nb)},
                'required_structures':required,'required_nether_structures':nether,'optional_structures':optional,
                'initial_fortress':fortress,'biomes':biomes,'ranking':ranking,
                'final_nether_prediction':{'required':['fortress','bastion'],'status':'PREDICTED' if len(nether)==2 and all(v['predicted_viable'] for v in nether.values()) else 'PENDING','bounds':json_bounds(nb),'actual_generation_verified':False},
                'baseline_score':score if inventory_complete else None,'baseline_score_observed':score,
                'baseline_score_complete':inventory_complete,'baseline_score_status':'PREDICTED count bonuses' if inventory_complete else 'PARTIAL; baseline unresolved',
                'baseline_score_uncertainty':score_uncertainty(score,pending,inventory_complete),
                'inventory':{'version':'blueprint-count-inventory-v1','status':'COMPLETE' if inventory_complete else 'UNRESOLVED',
                    'tasks':[],'completion_scope':'complete required predictor counts for survivors; actual generation unverified'},
                'qualification':status,'data_status':'PREDICTED','pending_reasons':pending,
                'processing_status':'baseline_complete' if inventory_complete else 'baseline_pending',
                'final_nether_status':'UNVERIFIED','terrain_status':{'v1':'not_evaluated'}})
        work=getattr(backend,'native_work',{})
    counts.update(baseline_predicted=sum(a['qualification']=='PREDICTED' for a in anchors),
                  baseline_pending=sum(a['qualification']=='PENDING' for a in anchors),confirmed_rejections=0,
                  unresolved_discovery=int(not anchors),unresolved_stronghold_coverage=1)
    return {'index':index,'seed':str(seed),'contract':BLUEPRINT_CONTRACT,'anchors':anchors,
            'counts':counts,'stage_seconds':times,'native_work':work,
            'worker_cpu_seconds':time.process_time()-cpu,'total_seconds':time.perf_counter()-start,
            'worker_pid':os.getpid(),'worker_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024),
            'biome_cache_hits':sampler.hits,'discovery_status':'PREDICTED' if anchors else 'PENDING',
            'discovery':{'stronghold':strongholds,'fortress':fortress,'seed':str(seed),'settings':dict(cfg['discovery']),
                         'coverage':{'status':'UNRESOLVED','stronghold_recall':'UNVALIDATED','authoritative_absence':False,'complete':False}},
            'effective_seed_bits':{'viability':64,'raw_MT_placement':32}}


def evaluate_locked_seed(index,seed,cfg,*,backend_factory=Backend,combined=True,short_circuit=True):
    from .config import river_policy, origin_policy, two_group_policy
    two_group=two_group_policy(cfg)
    floors=cfg['structures'].get('hard_floors',{}) if two_group else {}
    budget=cfg['search'].get('max_misses',0) if two_group else 0
    from .baseline import structure_observation
    seed=parse_seed(seed);start=time.perf_counter();cpu=time.process_time();times={};counts={};anchors=[]
    def timed(name,fn):
        before=time.perf_counter()
        try:return fn()
        finally:times[name]=times.get(name,0)+time.perf_counter()-before
    # Complete/reference mode uses full scans and evaluates all constraints.
    capped=short_circuit and cfg['search'].get('inventory_mode')=='eligibility'
    origin=origin_policy(cfg)
    with backend_factory(seed) as backend:
        sampler=BiomeSampler(backend)
        discovery_bounds=cfg['discovery']['overworld_bounds']
        strongholds=timed('stronghold',lambda:structure_observation(backend,'stronghold',discovery_bounds,combined))
        # Broad Nether discovery is irrelevant to the centered final border.
        fortress={'type':'fortress','bounds':list(cfg['discovery']['nether_bounds']),
                  'raw':[],'predicted_viable':[],'coordinates':[],'data_status':'NOT_REQUESTED',
                  'verification':'UNVERIFIED','confirmed_absent':False,'complete':False}
        counts['stronghold_anchors']=len(strongholds['predicted_viable'])
        if origin:counts['evaluation_centers']=1
        for anchor in ([(0,0)] if origin else strongholds['predicted_viable']):
            if origin:anchor=[0,0]
            bounds=square(anchor,2048);nb=nether_square(anchor,1024)
            actual=strongholds['predicted_viable'] if origin else [anchor]
            required={'stronghold':{**strongholds,'bounds':json_bounds(bounds),'coordinates':actual,
                'raw':strongholds['raw'] if origin else [anchor],
                'predicted_viable':actual,'minimum_count':1,'predicted_count':len(actual),
                **({'count_is_complete':True} if origin else {}),
                'floor_status':'PREDICTED' if actual else 'PENDING'}}
            pending=[];fatal=[];deficits=[];nether={};optional={};biomes=None
            if True:
                counts['nether_stage_entered']=counts.get('nether_stage_entered',0)+1
                pairs=timed('final_nether_pair',lambda:backend.nether_structure_pairs(native_bounds(nb))) if combined and hasattr(backend,'nether_structure_pairs') else None
                for name in ('fortress','bastion'):
                    observation=timed('final_'+name,lambda n=name:structure_observation(backend,n,nb,combined,pair=pairs[n] if pairs else None))
                    minimum=cfg['structures']['nether_minimum_counts'][name]
                    observation.update(minimum_count=minimum,predicted_count=len(observation['predicted_viable']))
                    nether[name]=observation
                    observed=len(observation['predicted_viable'])
                    if observed<minimum:
                        pending.append('count_'+name)
                        if two_group: deficits.append(name)
                    if two_group and observed<floors[name]:fatal.append('floor_'+name)
            counts['structure_stage_entered']=counts.get('structure_stage_entered',0)+1
            for position,name in enumerate(cfg['search']['structure_order']):
                # The full/reference provider has already inventoried Strongholds,
                # so report absence even when another predicate rejected earlier.
                if origin and position==stronghold_after(cfg) and not actual:
                    pending.append('count_stronghold')
                    if two_group:fatal.append('floor_stronghold')
                blocked=(fatal or len(deficits)>budget) if two_group else pending
                if blocked and short_circuit:
                    required[name]={'type':name,'bounds':json_bounds(bounds),'raw':[],
                        'coordinates':[],'predicted_viable':[],'minimum_count':cfg['structures']['minimum_counts'][name],
                        'data_status':'PARTIAL','verification':'DEFERRED','confirmed_absent':False,
                        'complete':False,'inventory_status':'DEFERRED','floor_status':'PENDING'}
                    continue
                goal=cfg['structures']['minimum_counts'][name]
                observation=timed('structure_'+name,lambda n=name,g=goal:count_observation(backend,n,bounds,g,capped=capped,combined=combined))
                required[name]=observation
                counts['checked_'+name]=counts.get('checked_'+name,0)+1
                observed=observation['predicted_count']
                if observed<goal:
                    pending.append('count_'+name);counts['pending_'+name]=counts.get('pending_'+name,0)+1
                    if two_group and name not in ('outpost','desert_pyramid','jungle_temple'):deficits.append(name)
                if two_group and observed<floors[name]:fatal.append('floor_'+name)
            structure_pass=(not fatal and len(deficits)<=budget) if two_group else not pending
            if structure_pass:counts['structure_stage_passed']=counts.get('structure_stage_passed',0)+1
            if structure_pass or not short_circuit:
                counts['biome_stage_entered']=counts.get('biome_stage_entered',0)+1
                before=sampler.queried
                biomes=timed('biome_palette_4y',lambda:biome_palette(sampler,bounds,cfg['biomes'],complete=origin or not short_circuit))
                counts['biome_samples']=counts.get('biome_samples',0)+sampler.queried-before
                if biomes['missing_families']:pending.extend('biome_'+f for f in biomes['missing_families'])
                else:counts['biome_stage_passed']=counts.get('biome_stage_passed',0)+1
            from .config import marine_baseline_policy
            marine_baseline=marine_baseline_policy(cfg)
            if marine_baseline and (not short_circuit or (biomes and not biomes['missing_families'] and structure_pass)):
                for name in ('monument','shipwreck'):
                    goal=cfg['structures']['minimum_counts'][name]
                    observation=timed('structure_'+name,lambda n=name,g=goal:count_observation(backend,n,bounds,g,capped=capped,combined=combined))
                    required[name]=observation
                    counts['checked_'+name]=counts.get('checked_'+name,0)+1
                    if observation['predicted_count']<goal:
                        pending.append('count_'+name)
                        fatal.append('floor_'+name)
                        counts['pending_'+name]=counts.get('pending_'+name,0)+1
                        if short_circuit:break
            if marine_baseline:
                for name in ('monument','shipwreck'):
                    if name not in required:
                        required[name]={'type':name,'bounds':json_bounds(bounds),'raw':[],
                            'coordinates':[],'predicted_viable':[],
                            'minimum_count':cfg['structures']['minimum_counts'][name],
                            'data_status':'PARTIAL','verification':'DEFERRED','confirmed_absent':False,
                            'complete':False,'inventory_status':'DEFERRED','floor_status':'PENDING'}
            # All jackpot counts are inventoried only for full baseline survivors.
            # No legacy presence inventory can overwrite this count contract.
            biome_failures=['biome_'+f for f in biomes['missing_families']] if biomes else []
            inventory_complete=structure_pass and not fatal and not biome_failures if two_group else not pending
            if inventory_complete:
                for name in cfg['search']['structure_order']:
                    if not required[name].get('count_is_complete',False) or required[name].get('raw_inventory_status')=='NOT_RECORDED':
                        required[name]=timed('ranking_inventory',lambda n=name:count_observation(backend,n,bounds,cfg['structures']['minimum_counts'][n],capped=False,combined=combined))
                if marine_baseline:
                    for name in ('monument','shipwreck'):
                        if not required[name].get('count_is_complete',False) or required[name].get('raw_inventory_status')=='NOT_RECORDED':
                            required[name]=timed('ranking_inventory',lambda n=name:count_observation(backend,n,bounds,cfg['structures']['minimum_counts'][n],capped=False,combined=combined))
            ranking=smart_score(required,nether,optional,locked=True,river=river_policy(cfg),origin=origin,two_group=two_group,river_bonus=not marine_baseline,
                                biome_names=(s['biome'] for s in biomes['sampling']['samples'] if s['coordinate'][1]==63) if biomes else ())
            score=ranking['score'];status='PREDICTED' if inventory_complete else 'PENDING'
            anchors.append({'id':f'{seed}:{anchor[0]}:{anchor[1]}','index':index,'seed':str(seed),'stronghold':anchor,
                **({'evaluation_center':[0,0],'center_kind':'world_origin','predicted_strongholds':actual} if origin else {}),
                'contract':BLUEPRINT_CONTRACT,'screening_revision':cfg['screening_revision'],
                'deferred_requirements':([] if marine_baseline else ['count_monument','count_shipwreck']+([] if 'outpost' in cfg['structures']['minimum_counts'] else ['optional_outpost'])),
                'marine_stage':({'status':'PREDICTED' if all(required.get(n,{}).get('predicted_count',0)>=cfg['structures']['minimum_counts'][n] for n in ('monument','shipwreck')) else 'PENDING',
                                 'required_counts':{n:cfg['structures']['minimum_counts'][n] for n in ('monument','shipwreck')},
                                 'predicted_counts':{n:required.get(n,{}).get('predicted_count') for n in ('monument','shipwreck')},
                                 'actual_generation_verified':False} if marine_baseline else
                                {'status':'DEFERRED','required_counts':{n:cfg['structures']['minimum_counts'][n] for n in ('monument','shipwreck')},'trigger':'complete coastal ocean/water/land footprint'}),
                'full_blueprint_certification':False,'game_version':cfg['game']['target_version'],
                'bds_version':cfg['game']['bds_version'],'backend_model':cfg['game']['backend_model'],
                'backend_commit':cfg['game']['backend_commit'],
                'bounds':{'overworld':json_bounds(bounds),'initial_overworld':list(discovery_bounds),
                          'initial_nether':list(cfg['discovery']['nether_bounds']),'final_nether':json_bounds(nb)},
                'required_structures':required,'required_nether_structures':nether,'optional_structures':optional,
                'initial_fortress':fortress,'biomes':biomes,'ranking':ranking,
                'final_nether_prediction':{'required':['fortress','bastion'],'status':'PREDICTED' if len(nether)==2 and all(len(v['predicted_viable'])>=cfg['structures']['nether_minimum_counts'][name] for name,v in nether.items()) else 'PENDING','bounds':json_bounds(nb),'actual_generation_verified':False},
                'baseline_score':score if inventory_complete else None,'baseline_score_observed':score,
                'baseline_score_complete':inventory_complete,'baseline_score_status':'PREDICTED count bonuses' if inventory_complete else 'PARTIAL; baseline unresolved',
                'baseline_score_uncertainty':score_uncertainty(score,fatal+biome_failures if two_group else pending,inventory_complete),
                'inventory':{'version':'blueprint-count-inventory-v1','status':'COMPLETE' if inventory_complete else 'UNRESOLVED',
                    'tasks':[],'completion_scope':'complete required predictor counts for survivors; actual generation unverified'},
                'qualification':status,'data_status':'PREDICTED','pending_reasons':pending,
                **({'deficit_categories':deficits,'fatal_reasons':fatal,'biome_failures':biome_failures,
                    'deficit_budget':budget,'baseline_qualification':status} if two_group else {}),
                'processing_status':'baseline_complete' if inventory_complete else 'baseline_pending',
                'final_nether_status':'UNVERIFIED','terrain_status':{'v1':'not_evaluated'}})
            if two_group:
                from .spawn import classify_spawn
                anchors[-1]['spawn_stage']=classify_spawn(anchors[-1],cfg)
        work=getattr(backend,'native_work',{})
    counts.update(baseline_predicted=sum(a['qualification']=='PREDICTED' for a in anchors),
                  baseline_pending=sum(a['qualification']=='PENDING' for a in anchors),confirmed_rejections=0,
                  unresolved_discovery=int(not strongholds['predicted_viable'] if origin else not anchors),unresolved_stronghold_coverage=1)
    return {'index':index,'seed':str(seed),'contract':BLUEPRINT_CONTRACT,'anchors':anchors,
            'counts':counts,'stage_seconds':times,'native_work':work,
            'worker_cpu_seconds':time.process_time()-cpu,'total_seconds':time.perf_counter()-start,
            'worker_pid':os.getpid(),'worker_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024),
            'biome_cache_hits':sampler.hits,'discovery_status':'PREDICTED' if (strongholds['predicted_viable'] if origin else anchors) else 'PENDING',
            'discovery':{'stronghold':strongholds,'fortress':fortress,'seed':str(seed),'settings':dict(cfg['discovery']),
                         'coverage':{'status':'UNRESOLVED','stronghold_recall':'UNVALIDATED','authoritative_absence':False,'complete':False}},
            'effective_seed_bits':{'viability':64,'raw_MT_placement':32}}


def dynamic_score(counts,biome_names,hub=0):
    """Revision 4.1 predictor score; named ordinal jackpots are awarded once."""
    n=lambda name:counts.get(name,0)
    score=50*(n('mansion')>=2)+50*(n('stronghold')>=2)+30*(n('monument')>=2)
    score+=max(0,n('village')-8)*25+max(0,n('trial_chamber')-7)*10
    score+=25*(n('ancient_city')>=4)
    score+=sum(20*(n(name)>=3) for name in ('desert_pyramid','jungle_temple','outpost','fortress','bastion'))
    score+=max(0,n('shipwreck')-6)*5+max(0,n('ruined_portal')-7)*5
    score+=max(0,n('mineshaft')-15)+min(40,max(0,hub))
    score+=sum(n(name)*points for name,points in zip(('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure'),(20,15,15,10,10)))
    names=set(biome_names)
    for points,members in DYNAMIC_LUXURIES:
        if names.intersection(members):score+=points
    return score


DYNAMIC_LUXURIES=((30,('cherry_grove',)),(20,('badlands','wooded_badlands','eroded_badlands')),
    (25,('mushroom_fields',)),(30,('pale_garden',)),(25,('mangrove_swamp',)),
    (10,('flower_forest',)),(10,('bamboo_jungle',)),(15,('warm_ocean',)),
    (15,('ice_spikes',)),(15,('windswept_savanna','shattered_savanna')))

DYNAMIC_V2_LUXURIES=(
    (25,('cherry_grove',)),
    (20,('badlands','wooded_badlands','eroded_badlands')),
    (25,('mushroom_fields',)),
    (25,('pale_garden',)),
    (15,('old_growth_pine_taiga','old_growth_spruce_taiga')),
    (10,('flower_forest',)),
    (10,('bamboo_jungle',)),
    (15,('warm_ocean',)),
    (15,('ice_spikes',)),
    (15,('savanna','savanna_plateau','windswept_savanna','shattered_savanna')),
)

DYNAMIC_V3_LUXURIES=(
    (25,('cherry_grove',)),
    (35,('badlands','wooded_badlands','eroded_badlands')),
    (40,('mushroom_fields',)),
    (35,('pale_garden',)),
    (20,('old_growth_pine_taiga','old_growth_spruce_taiga')),
    (15,('flower_forest',)),
    (10,('bamboo_jungle',)),
    (20,('warm_ocean',)),
    (25,('ice_spikes',)),
    (15,('savanna','savanna_plateau','windswept_savanna','shattered_savanna')),
)


DEFAULT_V2_TARGETS = {
    'ruined_portal': 7,
    'shipwreck': 6,
    'village': 9,
    'trial_chamber': 8,
    'ancient_city': 4,
    'desert_pyramid': 3,
    'jungle_temple': 3,
    'mineshaft': 15,
    'mansion': 1,
    'stronghold': 1,
    'monument': 1,
    'outpost': 2,
    'fortress': 2,
    'bastion': 2,
}


def dynamic_v2_score(counts,biome_names=(),hub=0,scenic=0,village_spread=0,treasure_bastion=0,optional_counts=None,*,targets=None):
    """Authoritative Section 8.3 dynamic-envelope-1664-v2 player scoring."""
    n=lambda name:counts.get(name,0)
    opt=(lambda name:(optional_counts or {}).get(name,0)) if optional_counts is not None else n
    tgt=lambda name:targets.get(name,DEFAULT_V2_TARGETS[name]) if targets else DEFAULT_V2_TARGETS[name]

    core=0
    core+=50 if n('mansion')>=2 else 0
    core+=35 if n('stronghold')>=2 else 0
    core+=35 if n('monument')>=2 else 0
    v=n('village')
    core+=(25 if v>=10 else 0)+(10 if v>=11 else 0)+(5 if v>=12 else 0)
    tc=n('trial_chamber')
    core+=(10 if tc>=9 else 0)+(10 if tc>=10 else 0)+(10 if tc>=11 else 0)
    core+=25 if n('ancient_city')>=5 else 0
    core+=20 if n('desert_pyramid')>=4 else 0
    core+=20 if n('jungle_temple')>=4 else 0
    core+=20 if n('outpost')>=3 else 0
    core+=20 if n('fortress')>=3 else 0
    core+=20 if n('bastion')>=3 else 0
    rp=n('ruined_portal')
    core+=(5 if rp>=8 else 0)+(5 if rp>=9 else 0)
    sw=n('shipwreck')
    core+=(5 if sw>=7 else 0)+(5 if sw>=8 else 0)
    ms=n('mineshaft')
    core+=min(5,max(0,ms-15))

    optional=0
    sh=opt('swamp_hut')
    optional+=(20 if sh>=1 else 0)+(10 if sh>=2 else 0)
    tr=opt('trail_ruins')
    optional+=(15 if tr>=1 else 0)+(10 if tr>=2 else 0)
    oru=opt('ocean_ruin')
    optional+=(10 if oru>=1 else 0)+(10 if oru>=2 else 0)
    bt=opt('buried_treasure')
    optional+=min(24,6*max(0,bt))
    ig=opt('igloo')
    optional+=(10 if ig>=1 else 0)+(5 if ig>=2 else 0)
    optional+=15 if treasure_bastion else 0

    luxury=0
    names=set(biome_names)
    for points,members in DYNAMIC_V2_LUXURIES:
        if names.intersection(members):luxury+=points

    hub_pts=min(40,max(0,hub))
    scenic_pts=20 if scenic else 0
    spread_pts=15 if village_spread else 0
    bonus_total=core+optional+luxury+hub_pts+scenic_pts+spread_pts

    deficits=[]
    penalty=0
    if n('ruined_portal')<tgt('ruined_portal'):penalty+=5;deficits.append('ruined_portal')
    if n('shipwreck')<tgt('shipwreck'):penalty+=5;deficits.append('shipwreck')
    if n('village')<tgt('village'):penalty+=10;deficits.append('village')
    if n('trial_chamber')<tgt('trial_chamber'):penalty+=10;deficits.append('trial_chamber')
    if n('ancient_city')<tgt('ancient_city'):penalty+=10;deficits.append('ancient_city')
    if n('desert_pyramid')<tgt('desert_pyramid'):penalty+=10;deficits.append('desert_pyramid')
    if n('jungle_temple')<tgt('jungle_temple'):penalty+=10;deficits.append('jungle_temple')
    if n('mineshaft')<tgt('mineshaft'):penalty+=10;deficits.append('mineshaft')
    if n('mansion')<tgt('mansion'):penalty+=10;deficits.append('mansion')
    if n('stronghold')<tgt('stronghold'):penalty+=10;deficits.append('stronghold')
    if n('monument')<tgt('monument'):penalty+=10;deficits.append('monument')
    if n('outpost')<tgt('outpost'):penalty+=10;deficits.append('outpost')
    if n('fortress')<tgt('fortress'):penalty+=10;deficits.append('fortress')
    if n('bastion')<tgt('bastion'):penalty+=10;deficits.append('bastion')

    final_score=bonus_total-penalty
    components={
        'score_revision':'dynamic-envelope-1664-v2',
        'final_score':final_score,
        'bonus_total':bonus_total,
        'deficit_penalty':penalty,
        'core_surplus':core,
        'optional_bonus':optional,
        'luxury_biomes':luxury,
        'hub_bonus':hub_pts,
        'scenic_bonus':scenic_pts,
        'village_spread_bonus':spread_pts,
        'treasure_bastion_bonus':(15 if treasure_bastion else 0),
    }
    return final_score,components,deficits


def dynamic_v3_score(counts,biome_names=(),hub=0,scenic=0,village_spread=0,treasure_bastion=0,optional_counts=None,*,targets=None,nether_core=0):
    """Authoritative Section 5.1 dynamic-envelope-2048-v3 pure additive player scoring (no deficits)."""
    n=lambda name:counts.get(name,0)
    opt=(lambda name:(optional_counts or {}).get(name,0)) if optional_counts is not None else n

    core=0
    # Mansion (F=1): 2nd=+55, 3rd+=+30 (Max 85)
    man=n('mansion')
    core+=(55 if man>=2 else 0)+(30 if man>=3 else 0)
    # Stronghold (F=1): 2nd=+20, 3rd+=+30 (Max 50)
    sh=n('stronghold')
    core+=(20 if sh>=2 else 0)+(30 if sh>=3 else 0)
    # Monument (F=1): 2nd=+25, 3rd=+15, 4th+=+10 (Max 50)
    mon=n('monument')
    core+=(25 if mon>=2 else 0)+(15 if mon>=3 else 0)+(10 if mon>=4 else 0)
    # Village (F=6): 7th..11th+ = +10 each (Max 50)
    v=n('village')
    core+=10*min(5,max(0,v-6))
    # Trial Chamber (F=8): 9th=+10, 10th=+8, 11th=+7, 12th+=+5 (Max 30)
    tc=n('trial_chamber')
    core+=(10 if tc>=9 else 0)+(8 if tc>=10 else 0)+(7 if tc>=11 else 0)+(5 if tc>=12 else 0)
    # Ancient City (F=2): 3rd=+20, 4th=+20, 5th=+15, 6th+=+10 (Max 65)
    ac=n('ancient_city')
    core+=(20 if ac>=3 else 0)+(20 if ac>=4 else 0)+(15 if ac>=5 else 0)+(10 if ac>=6 else 0)
    # Desert Pyramid (F=1): 2nd=+25, 3rd=+20, 4th+=+15 (Max 60)
    dp=n('desert_pyramid')
    core+=(25 if dp>=2 else 0)+(20 if dp>=3 else 0)+(15 if dp>=4 else 0)
    # Jungle Temple (F=1): 2nd=+25, 3rd=+20, 4th+=+15 (Max 60)
    jt=n('jungle_temple')
    core+=(25 if jt>=2 else 0)+(20 if jt>=3 else 0)+(15 if jt>=4 else 0)
    # Outpost (F=1): 2nd=+15, 3rd=+15, 4th+=+10 (Max 40)
    out=n('outpost')
    core+=(15 if out>=2 else 0)+(15 if out>=3 else 0)+(10 if out>=4 else 0)
    # Fortress (F=1): 2nd=+20, 3rd=+15, 4th+=+15 (Max 50)
    fort=n('fortress')
    core+=(20 if fort>=2 else 0)+(15 if fort>=3 else 0)+(15 if fort>=4 else 0)
    # Bastion (F=2): 3rd=+20, 4th=+15, 5th+=+15 (Max 50)
    bast=n('bastion')
    core+=(20 if bast>=3 else 0)+(15 if bast>=4 else 0)+(15 if bast>=5 else 0)
    # Ruined Portal (F=8): 9th..12th = +5 each (Max 20)
    rp=n('ruined_portal')
    core+=5*min(4,max(0,rp-8))
    # Shipwreck (F=4): 5th..8th = +5 each (Max 20)
    sw=n('shipwreck')
    core+=5*min(4,max(0,sw-4))
    # Mineshaft (F=10): 11th..20th = +2 each (Max 20)
    ms=n('mineshaft')
    core+=2*min(10,max(0,ms-10))

    optional=0
    # Swamp Hut: 1st=+30, 2nd=+20, 3rd+=+10 (Max 60)
    sh_opt=opt('swamp_hut')
    optional+=(30 if sh_opt>=1 else 0)+(20 if sh_opt>=2 else 0)+(10 if sh_opt>=3 else 0)
    # Trail Ruins: 1st=+25, 2nd=+15, 3rd+=+10 (Max 50)
    tr=opt('trail_ruins')
    optional+=(25 if tr>=1 else 0)+(15 if tr>=2 else 0)+(10 if tr>=3 else 0)
    # Igloo: 1st=+25, 2nd+=+15 (Max 40)
    ig=opt('igloo')
    optional+=(25 if ig>=1 else 0)+(15 if ig>=2 else 0)
    # Ocean Ruins: 1st=+10, 2nd+=+10 (Max 20)
    oru=opt('ocean_ruin')
    optional+=(10 if oru>=1 else 0)+(10 if oru>=2 else 0)
    # Buried Treasure: 1st=+10, 2nd=+10, 3rd=+5, 4th+=+5 (Max 30)
    bt=opt('buried_treasure')
    optional+=(10 if bt>=1 else 0)+(10 if bt>=2 else 0)+(5 if bt>=3 else 0)+(5 if bt>=4 else 0)

    luxury=0
    names=set(biome_names)
    distinct_lux=0
    for points,members in DYNAMIC_V3_LUXURIES:
        if names.intersection(members):
            luxury+=points
            distinct_lux+=1
    if distinct_lux>=7:luxury+=25
    elif distinct_lux>=5:luxury+=10

    hub_pts=min(45,max(0,hub))
    scenic_pts=25 if scenic else 0
    spread_pts=25 if village_spread else 0
    tbast_pts=20 if treasure_bastion else 0
    nether_core_pts=min(20,max(0,nether_core))
    bonus_total=core+optional+luxury+hub_pts+nether_core_pts+scenic_pts+spread_pts+tbast_pts

    deficits=[]
    penalty=0
    final_score=bonus_total

    components={
        'score_revision':'dynamic-envelope-2048-v3',
        'final_score':final_score,
        'bonus_total':bonus_total,
        'deficit_penalty':0,
        'core_surplus':core,
        'optional_bonus':optional,
        'luxury_biomes':luxury,
        'hub_bonus':hub_pts,
        'nether_core_bonus':nether_core_pts,
        'scenic_bonus':scenic_pts,
        'village_spread_bonus':spread_pts,
        'treasure_bastion_bonus':tbast_pts,
    }
    return final_score,components,deficits


def evaluate_dynamic_seed(index,seed,cfg,*,backend_factory=Backend,combined=True,short_circuit=True):
    """Independent complete-inventory oracle for the exact dynamic center."""
    import math
    from .baseline import structure_observation
    from .dynamic import (candidate_centers,OVERWORLD_NAMES,NETHER_NAMES,OPTIONAL_NAMES,
                          overworld_bounds,nether_bounds,nether_palette,hub_bonus,weighted_radial,PaletteIndex,
                          DYNAMIC_V2_CENTROID_WEIGHTS,hub_bonus_v2,hub_village_v2,weighted_radial_v2,
                          scenic_pair_bonus_v2,village_spread_bonus_v2,treasure_bastion_bonus_v2,
                          hub_bonus_v3,nether_core_bonus_v3,weighted_radial_v3)
    from .config import baseline_requirements,dynamic_v2_policy,dynamic_v3_policy
    is_v3=dynamic_v3_policy(cfg)
    is_v2=dynamic_v2_policy(cfg)
    seed=parse_seed(seed);started=time.perf_counter();cpu=time.process_time()
    timings={};anchors=[];counts={}
    def timed(name,fn):
        before=time.perf_counter()
        try:return fn()
        finally:timings[name]=timings.get(name,0)+time.perf_counter()-before
    ow_macro=tuple(cfg['discovery']['overworld_bounds'])
    nw_macro=tuple(cfg['discovery']['nether_bounds'])
    with backend_factory(seed) as backend:
        sampler=BiomeSampler(backend)
        strongholds=timed('stronghold',lambda:structure_observation(backend,'stronghold',ow_macro,combined))
        inventories={'stronghold':strongholds}
        replay_center=getattr(backend,'dynamic_center',None)
        if getattr(backend,'dynamic_no_anchor',False):eligible=[]
        elif replay_center is None:
            mansion=timed('structure_mansion',lambda:count_observation(backend,'mansion',ow_macro,1,capped=False,combined=combined))
            inventories['mansion']=mansion
            if mansion['predicted_viable']:
                inventories['outpost']=timed('structure_outpost',lambda:structure_observation(backend,'outpost',ow_macro,combined))
            if mansion['predicted_viable'] and len(inventories.get('outpost',{}).get('predicted_viable',[]))>=cfg['structures']['hard_floors']['outpost']:
                pairs=timed('final_nether_pair',lambda:backend.nether_structure_pairs(native_bounds(nw_macro))) if combined and hasattr(backend,'nether_structure_pairs') else None
                for name in NETHER_NAMES:
                    inventories[name]=timed('final_'+name,lambda name=name:structure_observation(backend,name,nw_macro,combined,pair=pairs[name] if pairs else None))
            if (strongholds['predicted_viable'] and mansion['predicted_viable'] and
                    len(inventories.get('outpost',{}).get('predicted_viable',[]))>=cfg['structures']['hard_floors']['outpost'] and
                    len(inventories.get('fortress',{}).get('predicted_viable',[]))>=cfg['structures']['hard_floors']['fortress'] and
                    len(inventories.get('bastion',{}).get('predicted_viable',[]))>=cfg['structures']['nether_minimum_counts']['bastion']):
                for name in OVERWORLD_NAMES:
                    if name not in inventories:
                        inventories[name]=timed('structure_'+name,lambda name=name:structure_observation(backend,name,ow_macro,combined))
                for name in OPTIONAL_NAMES:
                    ob=structure_observation(backend,name,ow_macro,combined)
                    if name=='igloo':
                        ob['predicted_viable']=[p for p in ob['predicted_viable'] if backend.igloo_basement(*p)]
                        ob['coordinates']=ob['predicted_viable']
                        ob['data_status']='PREDICTED' if ob['predicted_viable'] else 'PARTIAL'
                    inventories[name]=ob
                all_points={name:[tuple(p) for p in observation['predicted_viable']]
                            for name,observation in inventories.items()}
                all_ideals={**cfg['structures']['minimum_counts'],**cfg['structures']['nether_minimum_counts']}
                strict={'stronghold','mansion','monument','outpost','fortress','bastion'}
                ideals={name:all_ideals[name] for name in all_ideals if name not in strict}
                cw=cfg['search'].get('centroid_weights') if is_v2 else None
                ow_half=cfg['deployment']['overworld_side_blocks']//2
                nw_half=cfg['deployment']['nether_side_blocks']//2
                eligible=candidate_centers(all_points,cfg['structures']['hard_floors'],
                    ideals,cfg['search']['density_weights'],cfg['search']['max_misses'],centroid_weights=cw,
                    overworld_half=ow_half,nether_half=nw_half)
                # Strict categories reject below their configurable targets.
                eligible=[item for item in eligible if all(item.counts[name]>=all_ideals[name] for name in strict)]
            else:eligible=[]
        else:
            ow_half=cfg['deployment']['overworld_side_blocks']//2
            nw_half=cfg['deployment']['nether_side_blocks']//2
            eligible=[type('Selected',(),{'center':tuple(replay_center)})()]
        selected=None;biomes=None;nether_biomes=None
        if replay_center is None and eligible:
            palette_index=timed('biome_palette_4y',lambda:PaletteIndex(sampler,cfg['biomes'],v2=is_v2,overworld_half=ow_half,nether_half=nw_half))
            if is_v2:
                def center_key_v2(item):
                    center=item.center
                    structures={name:[p for p in points if contains(p,overworld_bounds(center,ow_half))]
                                for name,points in all_points.items() if name in OVERWORLD_NAMES}
                    opt_counts={name:sum(contains(p,overworld_bounds(center,ow_half)) for p in all_points[name])
                                for name in OPTIONAL_NAMES}
                    get_var=getattr(backend,'bastion_variant',lambda x,z:-1)
                    tb_points,_=treasure_bastion_bonus_v2(all_points.get('bastion',[]),center,get_var,nw_half)
                    scenic_pts,_,_=palette_index.scenic_pair(center)
                    spread_pts,_=village_spread_bonus_v2(structures.get('village',[]),center,ow_half)
                    hub=hub_bonus_v3(structures,center) if is_v3 else hub_bonus_v2(structures,center)
                    nether_core=nether_core_bonus_v3(all_points,center) if is_v3 else 0
                    tb_pts=20 if (tb_points and is_v3) else tb_points
                    scenic_pts_eff=25 if (scenic_pts and is_v3) else scenic_pts
                    spread_pts_eff=25 if (spread_pts and is_v3) else spread_pts
                    if is_v3:
                        score,_,defs=dynamic_v3_score(item.counts,palette_index.luxuries(center),hub,scenic_pts_eff,spread_pts_eff,tb_pts,opt_counts,targets=all_ideals,nether_core=nether_core)
                    else:
                        score,_,defs=dynamic_v2_score(item.counts,palette_index.luxuries(center),hub,scenic_pts_eff,spread_pts_eff,tb_pts,opt_counts,targets=all_ideals)
                    radial=weighted_radial_v3(structures,center,overworld_half=ow_half) if is_v3 else weighted_radial_v2(structures,center,overworld_half=ow_half)
                    radial_key=int(math.floor(radial*1_000_000.0+0.5))
                    orig_dist_sq=center[0]**2+center[1]**2
                    return (-score,len(defs),radial_key,orig_dist_sq,center[0],center[1])
                eligible=sorted((item for item in eligible if palette_index.valid(item.center)),key=center_key_v2)
            else:
                def center_key(item):
                    center=item.center
                    structures={name:[p for p in points if contains(p,overworld_bounds(center,ow_half))]
                                for name,points in all_points.items() if name in OVERWORLD_NAMES}
                    score=dynamic_score(item.counts,palette_index.luxuries(center),hub_bonus(structures,center))
                    return (len(item.deficits),-score,round(item.radial,6),center[0]**2+center[1]**2,*center)
                eligible=sorted((item for item in eligible if palette_index.valid(item.center)),key=center_key)
        for item in eligible:
            center=item.center;bounds=overworld_bounds(center,ow_half)
            palette=timed('biome_palette_4y',lambda:biome_palette(sampler,bounds,cfg['biomes'],complete=True))
            npalette=timed('nether_palette',lambda:nether_palette(sampler,center,nw_half))
            if not palette['missing_families'] and not npalette['missing_families']:
                selected=center;biomes=palette;nether_biomes=npalette;break
        if selected is not None:
            ow=overworld_bounds(selected,ow_half);nw=nether_bounds(selected,nw_half)
            def trim(name,bounds):
                if replay_center is not None and name!='stronghold':
                    return count_observation(backend,name,bounds,0,capped=False,combined=combined) if name=='mansion' else structure_observation(backend,name,bounds,combined)
                source=inventories[name]
                raw=[p for p in source['raw'] if contains(p,bounds)]
                viable=[p for p in source['predicted_viable'] if contains(p,bounds)]
                ob={**source,'bounds':json_bounds(bounds),'raw':raw,
                    'predicted_viable':viable,'coordinates':viable,
                    'inventory_status':'COMPLETE','count_is_complete':True}
                if name=='mansion':
                    ob['unfiltered_predicted_viable']=[p for p in source.get('unfiltered_predicted_viable',[]) if contains(p,bounds)]
                    ob['anchor_biome_witnesses']=[row for row in source.get('anchor_biome_witnesses',[]) if contains((row['coordinate'][0],row['coordinate'][2]),bounds)]
                return ob
            required={name:trim(name,ow) for name in OVERWORLD_NAMES}
            nether={name:trim(name,nw) for name in NETHER_NAMES}
            optional={name:trim(name,ow) for name in OPTIONAL_NAMES}
            for ob in optional.values():ob['count_is_complete']=True
            optional['igloo']['variant_policy']='Pinned MC_26_50 basement PRNG prediction; generated basement unverified'
            all_observations={**required,**nether}
            all_ideals={**cfg['structures']['minimum_counts'],**cfg['structures']['nether_minimum_counts']}
            strict={'stronghold','mansion','monument','outpost','fortress','bastion'}
            deficits=[];fatal=[]
            for name,ob in all_observations.items():
                observed=len(ob['predicted_viable']);goal=all_ideals[name]
                ob.update(minimum_count=goal,predicted_count=observed,count_is_complete=True,
                          floor_status='PREDICTED' if observed>=goal else 'PENDING')
                if observed<cfg['structures']['hard_floors'][name]:fatal.append('floor_'+name)
                elif observed<goal:
                    if name in strict:fatal.append('count_'+name)
                    else:deficits.append(name)
            actual=required['stronghold']['predicted_viable']
            surface=[row['biome'] for row in biomes['sampling']['samples'] if row['coordinate'][1]==63]
            structures={name:ob['predicted_viable'] for name,ob in required.items()}
            density=sum(cfg['search']['density_weights'][name]*len(required[name]['predicted_viable'])
                        for name in cfg['search']['density_weights'])
            if is_v2:
                hub=hub_bonus_v3(structures,selected) if is_v3 else hub_bonus_v2(structures,selected)
                hub_village=hub_village_v2(structures,selected)
                radial=weighted_radial_v3(structures,selected,overworld_half=ow_half) if is_v3 else weighted_radial_v2(structures,selected,overworld_half=ow_half)
                radial_key=int(math.floor(radial*1_000_000.0+0.5))
                orig_dist_sq=selected[0]**2+selected[1]**2
                if hasattr(backend,'scenic_bonus'):
                    scenic_pts=getattr(backend,'scenic_bonus')
                    scenic_wit=getattr(backend,'scenic_witness',None)
                    river_wit=getattr(backend,'river_witness',None)
                elif 'palette_index' in locals():
                    scenic_pts,scenic_wit,river_wit=palette_index.scenic_pair(selected)
                else:
                    surface_grid=np.array([canonical(biome_name(int(v))) for v in sampler.sample(grid_points((-2000,-2000,2000,2000),64,63,'world'))]).reshape(63,63)
                    scenic_pts,scenic_wit,river_wit=scenic_pair_bonus_v2(surface_grid,selected,overworld_half=ow_half)
                if hasattr(backend,'village_spread_bonus'):
                    spread_pts=getattr(backend,'village_spread_bonus')
                    v_triple=getattr(backend,'village_triple',None)
                else:
                    spread_pts,v_triple=village_spread_bonus_v2(structures.get('village',[]),selected,overworld_half=ow_half)
                if hasattr(backend,'treasure_bastion'):
                    tb_points=15 if getattr(backend,'treasure_bastion') else 0
                    tb_list=[[x, z, var] for (x, z), var in getattr(backend, 'bastion_variants', {}).items()]
                else:
                    get_var=getattr(backend,'bastion_variant',lambda x,z:-1)
                    tb_points,tb_list=treasure_bastion_bonus_v2(nether['bastion']['predicted_viable'],selected,get_var,nether_half=nw_half)
                nether_core=nether_core_bonus_v3({name:ob['predicted_viable'] for name,ob in nether.items()},selected) if is_v3 else 0
                tb_points_eff=20 if (tb_points and is_v3) else tb_points
                scenic_pts_eff=25 if (scenic_pts and is_v3) else scenic_pts
                spread_pts_eff=25 if (spread_pts and is_v3) else spread_pts
                if is_v3:
                    score,components,score_defs=dynamic_v3_score(
                        {name:len(ob['predicted_viable']) for name,ob in {**all_observations,**optional}.items()},
                        surface,hub,scenic_pts_eff,spread_pts_eff,tb_points_eff,
                        {name:len(ob['predicted_viable']) for name,ob in optional.items()},
                        targets=all_ideals,
                        nether_core=nether_core
                    )
                else:
                    score,components,score_defs=dynamic_v2_score(
                        {name:len(ob['predicted_viable']) for name,ob in {**all_observations,**optional}.items()},
                        surface,hub,scenic_pts_eff,spread_pts_eff,tb_points_eff,
                        {name:len(ob['predicted_viable']) for name,ob in optional.items()},
                        targets=all_ideals
                    )
            else:
                hub=hub_bonus(structures,selected)
                radial=weighted_radial(structures,selected)
                score=dynamic_score({name:len(ob['predicted_viable']) for name,ob in {**all_observations,**optional}.items()},surface,hub)
            qualified=not fatal and len(deficits)<=cfg['search']['max_misses'] and not biomes['missing_families']
            if qualified:
                span=8*nw_half
                anchor={'id':f'{seed}:{selected[0]}:{selected[1]}','index':index,'seed':str(seed),
                    'stronghold':actual[0],'evaluation_center':list(selected),
                    'center_kind':'snapped_weighted_centroid','predicted_strongholds':actual,
                    'contract':BLUEPRINT_CONTRACT,'screening_revision':cfg['screening_revision'],
                    'full_blueprint_certification':False,'game_version':cfg['game']['target_version'],
                    'bds_version':cfg['game']['bds_version'],'backend_model':cfg['game']['backend_model'],
                    'backend_commit':cfg['game']['backend_commit'],
                    'bounds':{'overworld':json_bounds(ow),'initial_overworld':list(ow_macro),
                              'initial_nether':list(nw_macro),'final_nether':json_bounds(nw),
                              'nether_center_exact':{'x':[selected[0],8],'z':[selected[1],8]},
                              'final_nether_exact':[[selected[0]-span,8],[selected[1]-span,8],
                                                    [selected[0]+span,8],[selected[1]+span,8]]},
                    'required_structures':required,'required_nether_structures':nether,
                    'optional_structures':optional,'initial_fortress':{'type':'fortress','data_status':'NOT_REQUESTED'},
                    'biomes':biomes,'nether_biomes':nether_biomes,
                    'final_nether_prediction':{'required':['fortress','bastion'],'status':'PREDICTED',
                                               'bounds':json_bounds(nw),'actual_generation_verified':False},
                    'marine_stage':{'status':'PREDICTED','required_counts':{n:all_ideals[n] for n in ('monument','shipwreck')},
                                    'predicted_counts':{n:len(required[n]['predicted_viable']) for n in ('monument','shipwreck')},
                                    'actual_generation_verified':False},
                    'deferred_requirements':[],'baseline_score':score,'baseline_score_observed':score,
                    'baseline_score_complete':True,'baseline_score_status':'PREDICTED count and palette bonuses',
                    'baseline_score_uncertainty':score_uncertainty(score,[],True),
                    'inventory':{'version':'dynamic-2048-count-inventory-v3' if is_v3 else ('dynamic-1664-count-inventory-v2' if is_v2 else 'dynamic-1664-count-inventory-v1'),'status':'COMPLETE','tasks':[],
                                 'completion_scope':'complete predictor counts at selected center; actual generation unverified'},
                    'qualification':'PREDICTED','data_status':'PREDICTED','pending_reasons':[],
                    'deficit_categories':deficits,'fatal_reasons':[],'biome_failures':[],
                    'deficit_budget':cfg['search']['max_misses'],'baseline_qualification':'PREDICTED',
                    'processing_status':'baseline_complete','final_nether_status':'UNVERIFIED',
                    'terrain_status':{'v1':'not_applicable' if is_v2 else 'not_evaluated'},
                    'density_score':density}
                if is_v2:
                    anchor['hub_bonus']=components.get('hub_bonus', 0)
                    if is_v3:
                        anchor['nether_core_bonus']=components.get('nether_core_bonus', 0)
                    anchor['scenic_bonus']=scenic_pts
                    anchor['scenic_witness']=list(scenic_wit) if scenic_wit else None
                    anchor['river_witness']=list(river_wit) if river_wit else None
                    anchor['village_spread_bonus']=spread_pts
                    anchor['village_triple']=[list(p) for p in v_triple] if v_triple else None
                    anchor['treasure_bastion']=1 if tb_points else 0
                    anchor['bastion_variants']=[list(item) for item in tb_list] if tb_list else []
                    anchor['configured_targets']=dict(all_ideals)
                    anchor['starter_hub_village']=list(hub_village) if hub_village else None
                    anchor['deficit_penalty']=components['deficit_penalty']
                    anchor['bonus_total']=components['bonus_total']
                    anchor['radial_key']=radial_key
                    anchor['origin_distance_squared']=orig_dist_sq
                    anchor['ranking']={'score':score,'final_score':score,'deficit_tier':len(deficits),
                                       'weighted_radial_dist':radial,'radial_key':radial_key,
                                       'origin_distance_squared':orig_dist_sq,'origin_distance':float(np.hypot(*selected)),
                                       'components':components}
                    anchor['weighted_radial_dist']=radial
                    anchor['origin_distance']=float(np.hypot(*selected))
                    scenic_names={'plains','sunflower_plains','meadow','cherry_grove'}
                    cx,cz=selected
                    spawn_cands=[((row['coordinate'][0]-cx)**2+(row['coordinate'][2]-cz)**2,row['coordinate'][0],row['coordinate'][2],row['coordinate'][1],row['biome'])
                                 for row in biomes['sampling']['samples'] if row['coordinate'][1]==63 and row['biome'] in scenic_names and (row['coordinate'][0]-cx)**2+(row['coordinate'][2]-cz)**2<=256**2]
                    if spawn_cands:
                        spawn_cands.sort()
                        best_sp=spawn_cands[0]
                        anchor['suggested_spawn']={'status':'PREDICTED_SCENIC_SUGGESTION','coordinates':[best_sp[1],best_sp[3],best_sp[2]],'biome':best_sp[4],'distance':math.sqrt(best_sp[0])}
                    else:
                        anchor['suggested_spawn']={'status':'UNAVAILABLE','coordinates':None,'reason':'no scenic witness within 256 blocks'}
                    from .spawn import player_inspection_statuses
                    anchor['player_inspections']=player_inspection_statuses(anchor)
                else:
                    anchor['ranking']={'score':score,'deficit_tier':len(deficits),
                                       'weighted_radial_dist':radial,'origin_distance':float(np.hypot(*selected)),
                                       'components':{'dynamic_density':density,'hub_bonus':hub}}
                    anchor['weighted_radial_dist']=radial
                    anchor['origin_distance']=float(np.hypot(*selected))
                anchors=[anchor]
                from .spawn import classify_spawn
                anchor['spawn_stage']=classify_spawn(anchor,cfg)
        work=getattr(backend,'native_work',{})
    counts.update(stronghold_anchors=len(strongholds['predicted_viable']),evaluation_centers=len(anchors),
                  baseline_predicted=len(anchors),baseline_pending=0,confirmed_rejections=0,
                  unresolved_discovery=int(not anchors),unresolved_stronghold_coverage=1)
    return {'index':index,'seed':str(seed),'contract':BLUEPRINT_CONTRACT,'anchors':anchors,
            'counts':counts,'stage_seconds':timings,'native_work':work,
            'worker_cpu_seconds':time.process_time()-cpu,'total_seconds':time.perf_counter()-started,
            'worker_pid':os.getpid(),'worker_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024),
            'biome_cache_hits':sampler.hits,'discovery_status':'PREDICTED' if anchors else 'PENDING',
            'discovery':{'stronghold':strongholds,'fortress':{'type':'fortress','data_status':'NOT_REQUESTED'},
                         'seed':str(seed),'settings':dict(cfg['discovery']),
                         'coverage':{'status':'UNRESOLVED','stronghold_recall':'UNVALIDATED',
                                     'authoritative_absence':False,'complete':False}},
            'effective_seed_bits':{'viability':64,'raw_MT_placement':32}}

```

---

<a id="file-7"></a>
### File 7: `src/seed_search/realm/dynamic.py`
> **Purpose:** Python Spatial Geometry: 256-point Nether Lattice, Centroid Snapping, Scenic, Spread, Bastion  
> **Length:** 421 lines | **Language:** PYTHON

```python
"""Exact integer-center selection for the 1664/832 predictor policy.

Every event is a coordinate where a structure or a world-lattice biome sample
enters or leaves a window. Counts and sampled biome sets are constant between
events. Each rectangle uses its captured weighted centroid, constrained to
the valid 16/8 grid, before palette and score ranking.
"""
from dataclasses import dataclass
import math

from .bounds import contains

OVERWORLD_HALF=832
NETHER_HALF=416
MIN_CENTER=-1168
MAX_CENTER=1168

OVERWORLD_HALF_V3=1024
NETHER_HALF_V3=512
MIN_CENTER_V3=-976
MAX_CENTER_V3=976

DENSITY_NAMES=('village','trial_chamber','ancient_city','desert_pyramid',
               'jungle_temple','outpost')
OVERWORLD_NAMES=('stronghold','mansion','village','trial_chamber','ancient_city',
                 'desert_pyramid','jungle_temple','monument','ruined_portal',
                 'shipwreck','mineshaft','outpost')
NETHER_NAMES=('fortress','bastion')
OPTIONAL_NAMES=('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure')
CENTROID_WEIGHTS={'village':3,'trial_chamber':2,'ruined_portal':2,'ancient_city':2,'outpost':1,'desert_pyramid':1,'jungle_temple':1,'mansion':1,'monument':1,'stronghold':1,'shipwreck':1}
DYNAMIC_V2_CENTROID_WEIGHTS={'village':3,'trial_chamber':2,'ruined_portal':0,'ancient_city':2,'outpost':1,'desert_pyramid':1,'jungle_temple':1,'mansion':1,'monument':1,'stronghold':1,'shipwreck':0}
NETHER_BIOMES=('nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas')


def overworld_bounds(center, overworld_half=None):
    half = OVERWORLD_HALF if overworld_half is None else overworld_half
    x,z=center
    return x-half,z-half,x+half,z+half


def nether_bounds(center, nether_half=None):
    """Exact rational center/8; return inclusive lower and exclusive upper ints."""
    half = NETHER_HALF if nether_half is None else nether_half
    x,z=center
    return ((x-8*half+7)//8,(z-8*half+7)//8,
            (x+8*half+7)//8,(z+8*half+7)//8)


def _axis_events(points,half,nether=False,min_c=MIN_CENTER,max_c=MAX_CENTER):
    events={min_c,max_c+1}
    for value in points:
        if nether:
            lo=8*(value-half)+1
            hi=8*(value+half)+1
        else:
            lo=value-half+1
            hi=value+half+1
        if min_c<lo<=max_c:events.add(lo)
        if min_c<hi<=max_c:events.add(hi)
    return sorted(events)


def _nearest_zero(lo,hi):
    return 0 if lo<=0<=hi else hi if hi<0 else lo


_LAT = {v for s in range(-1984, 1985, 64) for v in (s - 831, s + 833)} | \
       {v for n in range(-512, 513, 64) for v in (8 * n - 3327, 8 * n + 3329)}
_LAT = {v for v in _LAT if MIN_CENTER < v <= MAX_CENTER}


@dataclass(frozen=True)
class Candidate:
    center:tuple[int,int]
    density:int
    counts:dict[str,int]
    deficits:tuple[str,...]
    radial:float=0.


def candidate_centers(inventories, floors, ideals, weights, max_misses=2, centroid_weights=None,
                      overworld_half=None, nether_half=None):
    """Yield all floor/budget-eligible equivalence cells in exact density order.

    ``inventories`` are complete, viable macro-envelope coordinates. The
    mansion list must already be filtered to Dark Forest starts at Y=63.
    Biome lattice events are included here; a palette check on the returned
    representative therefore applies to the entire event rectangle.
    """
    cw = centroid_weights if centroid_weights is not None else CENTROID_WEIGHTS
    ow_half = OVERWORLD_HALF if overworld_half is None else overworld_half
    nw_half = NETHER_HALF if nether_half is None else nether_half
    min_c = -2000 + ow_half
    max_c = 2000 - ow_half
    lat_events = {v for s in range(-1984, 1985, 64) for v in (s - (ow_half - 1), s + (ow_half + 1))} | \
                 {v for n in range(-((max_c // 8 + nw_half) // 64) * 64, ((max_c // 8 + nw_half) // 64) * 64 + 1, 64)
                  for v in (8 * n - (8 * nw_half - 1), 8 * n + (8 * nw_half + 1))}
    lat_events = {v for v in lat_events if min_c < v <= max_c}
    xs=[];zs=[];nether_x=[];nether_z=[]
    for name,points in inventories.items():
        if name in OPTIONAL_NAMES:continue
        target_x,target_z=(nether_x,nether_z) if name in NETHER_NAMES else (xs,zs)
        for x,z in points:target_x.append(x);target_z.append(z)
    ex=sorted(set(_axis_events(xs,ow_half,False,min_c,max_c)+_axis_events(nether_x,nw_half,True,min_c,max_c))|lat_events)
    ez=sorted(set(_axis_events(zs,ow_half,False,min_c,max_c)+_axis_events(nether_z,nw_half,True,min_c,max_c))|lat_events)
    rows=[]
    for xi in range(len(ex)-1):
        cx=_nearest_zero(ex[xi],ex[xi+1]-1)
        for zi in range(len(ez)-1):
            cz=_nearest_zero(ez[zi],ez[zi+1]-1)
            center=(cx,cz);ow=overworld_bounds(center,ow_half);nb=nether_bounds(center,nw_half)
            counts={name:sum(contains(point,nb if name in NETHER_NAMES else ow)
                             for point in points) for name,points in inventories.items()}
            if any(counts.get(name,0)<floor for name,floor in floors.items()):continue
            deficits=tuple(name for name,ideal in ideals.items() if counts.get(name,0)<ideal)
            if len(deficits)>max_misses:continue
            captured=[(x,z,cw[name]) for name,points in inventories.items() if name in cw and cw[name]>0
                      for x,z in points if contains((x,z),ow)]
            weight=sum(row[2] for row in captured)
            sx=sum(x*w for x,z,w in captured);sz=sum(z*w for x,z,w in captured)
            axes=[]
            for lo,hi,total in ((ex[xi],ex[xi+1]-1,sx),(ez[zi],ez[zi+1]-1,sz)):
                value=None
                for step in (16,8):
                    lower=-(-lo//step)*step;upper=(hi//step)*step
                    if lower>upper:continue
                    rounded=((total+(step//2)*weight)//(step*weight))*step if weight else 0
                    value=min(upper,max(lower,rounded));break
                axes.append(value)
            if any(value is None for value in axes):continue
            snapped=tuple(axes)
            s_ow=overworld_bounds(snapped,ow_half)
            c=dict(counts)
            for name in OPTIONAL_NAMES:
                if name in inventories:c[name]=sum(contains(p,s_ow) for p in inventories[name])
            radial=sum(w*math.hypot(x-snapped[0],z-snapped[1]) for x,z,w in captured)/weight if weight else 0.
            density=sum(weights[name]*c.get(name,0) for name in DENSITY_NAMES)
            rows.append(Candidate(snapped,density,c,deficits,radial))
    rows.sort(key=lambda row:(len(row.deficits),-row.density,row.radial,row.center[0]**2+row.center[1]**2,
                              row.center[0],row.center[1]))
    return rows


def nether_palette(backend,center,nether_half=None):
    from ..backend import biome_name
    bounds=nether_bounds(center,nether_half)
    x0=-(-bounds[0]//64)*64;z0=-(-bounds[1]//64)*64
    nh=NETHER_HALF if nether_half is None else nether_half
    side=16 if nh==512 else 13
    points=[(x0+x*64,64,z0+z*64) for z in range(side) for x in range(side)]
    values=backend.sample(points,dimension=-1)
    if len(values)!=len(points):raise ValueError('Incomplete Nether biome sample batch')
    samples=[{'coordinate':list(point),'id':int(value),'biome':biome_name(int(value))} for point,value in zip(points,values)]
    found={row['biome']:row for row in samples if row['biome'] in NETHER_BIOMES}
    return {'status':'PREDICTED' if len(found)==5 else 'PENDING','required_families':list(NETHER_BIOMES),
            'missing_families':[name for name in NETHER_BIOMES if name not in found],
            'witnesses':found,'sample_count':len(samples),'sampling':{'lattice':'world','spacing':64,'y':64,'samples':samples},
            'actual_generation_verified':False}


def hub_bonus(structures,center):
    points={'village':6,'desert_pyramid':6,'jungle_temple':6,'outpost':6,'ruined_portal':4}
    return min(40,sum(value for name,value in points.items() for x,z in structures.get(name,())
                      if (x-center[0])**2+(z-center[1])**2<=512**2))


def hub_bonus_v2(structures,center):
    villages=structures.get('village',())
    d2=lambda p:(p[0]-center[0])**2+(p[1]-center[1])**2
    v_hub=10 if any(d2(p)<=256**2 for p in villages) else 6 if any(d2(p)<=512**2 for p in villages) else 0
    other_pts={'desert_pyramid':6,'jungle_temple':6,'outpost':6}
    other_hub=sum(6 for name in other_pts for p in structures.get(name,()) if d2(p)<=512**2)
    other_hub+=sum(4 for p in structures.get('ruined_portal',()) if d2(p)<=512**2)
    return v_hub+min(30,other_hub)


def hub_bonus_v3(structures,center):
    villages=structures.get('village',())
    d2=lambda p:(p[0]-center[0])**2+(p[1]-center[1])**2
    v_hub=15 if any(d2(p)<=256**2 for p in villages) else 10 if any(d2(p)<=512**2 for p in villages) else 0
    other_pts={'desert_pyramid':6,'jungle_temple':6,'outpost':6,'ancient_city':6}
    other_hub=sum(6 for name in other_pts for p in structures.get(name,()) if d2(p)<=512**2)
    other_hub+=sum(4 for p in structures.get('ruined_portal',()) if d2(p)<=512**2)
    return v_hub+min(30,other_hub)


def nether_core_bonus_v3(nether_points,center):
    pnx = center[0] // 8
    pnz = center[1] // 8
    bonus = 0
    d2 = lambda p: (p[0] - pnx)**2 + (p[1] - pnz)**2
    if any(d2(p) <= 256**2 for p in nether_points.get('fortress', ())):
        bonus += 10
    if any(d2(p) <= 256**2 for p in nether_points.get('bastion', ())):
        bonus += 10
    return bonus


def hub_village_v2(structures,center):
    villages=structures.get('village',())
    d2=lambda p:(p[0]-center[0])**2+(p[1]-center[1])**2
    nearby=[(d2(p),p[0],p[1]) for p in villages if d2(p)<=512**2]
    if not nearby:return None
    nearby.sort()
    return (nearby[0][1],nearby[0][2])


def weighted_radial(structures,center):
    total=sum(weight*len(structures.get(name,())) for name,weight in CENTROID_WEIGHTS.items())
    return sum(weight*math.hypot(x-center[0],z-center[1]) for name,weight in CENTROID_WEIGHTS.items()
               for x,z in structures.get(name,()))/total if total else 0.


ORDER_V2_RADIAL = (
    ('stronghold', 1),
    ('mansion', 1),
    ('jungle_temple', 1),
    ('desert_pyramid', 1),
    ('monument', 1),
    ('ancient_city', 2),
    ('village', 3),
    ('trial_chamber', 2),
    ('outpost', 1),
)


def weighted_radial_v2(structures, center, dark_forest_mansions=None, overworld_half=None):
    cx, cz = center
    ow = overworld_bounds(center, overworld_half)
    total_weight = 0
    distance = 0.0
    for name, weight in ORDER_V2_RADIAL:
        pts = structures.get(name, ())
        for p in pts:
            x, z = p[0], p[1]
            if name == 'mansion' and dark_forest_mansions is not None and (x, z) not in dark_forest_mansions:
                continue
            if contains((x, z), ow):
                total_weight += weight
                distance += weight * math.hypot(x - cx, z - cz)
    return distance / total_weight if total_weight else 0.0


ORDER_V3_RADIAL = (
    ('stronghold', 1),
    ('mansion', 2),
    ('jungle_temple', 2),
    ('desert_pyramid', 2),
    ('monument', 1),
    ('ancient_city', 2),
    ('village', 3),
    ('trial_chamber', 2),
    ('outpost', 1),
)


def weighted_radial_v3(structures, center, dark_forest_mansions=None, overworld_half=None):
    cx, cz = center
    ow = overworld_bounds(center, overworld_half)
    total_weight = 0
    distance = 0.0
    for name, weight in ORDER_V3_RADIAL:
        pts = structures.get(name, ())
        for p in pts:
            x, z = p[0], p[1]
            if name == 'mansion' and dark_forest_mansions is not None and (x, z) not in dark_forest_mansions:
                continue
            if contains((x, z), ow):
                total_weight += weight
                distance += weight * math.hypot(x - cx, z - cz)
    return distance / total_weight if total_weight else 0.0


SCENIC_BIOMES=frozenset(('plains','sunflower_plains','meadow','cherry_grove'))
RIVER_OFFSETS=sorted([(dix,diz) for dix in range(-2,3) for diz in range(-2,3) if dix*dix+diz*diz<=4],
                     key=lambda o:(o[0],o[1]))


def scenic_pair_bonus_v2(surface_grid,center,overworld_half=None):
    """Exact scenic river pairing on the 64-block grid; surface_grid is 63x63 names at Y=63."""
    cx,cz=center
    ow=overworld_bounds(center,overworld_half)
    c_ix=(cx+1984)//64
    c_iz=(cz+1984)//64
    min_ix=max(0,c_ix-3);max_ix=min(62,c_ix+4)
    min_iz=max(0,c_iz-3);max_iz=min(62,c_iz+4)
    scenic_candidates=[]
    for ix in range(min_ix,max_ix+1):
        for iz in range(min_iz,max_iz+1):
            sx=-1984+ix*64
            sz=-1984+iz*64
            if (sx-cx)**2+(sz-cz)**2<=192**2 and contains((sx,sz),ow):
                if surface_grid[iz,ix] in SCENIC_BIOMES:
                    scenic_candidates.append((sx,sz,ix,iz))
    scenic_candidates.sort(key=lambda c:(c[0],c[1]))
    for sx,sz,ix,iz in scenic_candidates:
        for dix,diz in RIVER_OFFSETS:
            rix=ix+dix;riz=iz+diz
            if 0<=rix<63 and 0<=riz<63:
                rx=-1984+rix*64;rz=-1984+riz*64
                if contains((rx,rz),ow) and surface_grid[riz,rix]=='river':
                    return 20,(sx,sz),(rx,rz)
    return 0,None,None


def retained_scenic_pair_v2(samples, center, overworld_half=None):
    """Recompute the pair from a complete retained selected-window surface grid."""
    from .biomes import canonical
    grid = {}
    ow = overworld_bounds(center, overworld_half)
    for row in samples:
        x, y, z = row['coordinate']
        if y == 63 and x % 64 == 0 and z % 64 == 0 and contains((x, z), ow):
            grid[((z + 1984) // 64, (x + 1984) // 64)] = canonical(row['biome'])
    for x in range(-(-ow[0] // 64) * 64, ow[2], 64):
        for z in range(-(-ow[1] // 64) * 64, ow[3], 64):
            if ((z + 1984) // 64, (x + 1984) // 64) not in grid:
                raise ValueError('Incomplete retained Y=63 evidence; re-evaluate this seed before rescoring')
    return scenic_pair_bonus_v2(grid, center, overworld_half)


def village_spread_bonus_v2(villages,center,overworld_half=None):
    cx,cz=center
    ow=overworld_bounds(center,overworld_half)
    captured=[tuple(p) for p in villages if contains(p,ow)]
    q_villages=[[] for _ in range(4)]
    for x,z in captured:
        if x>=cx:q=0 if z>=cz else 3
        else:q=1 if z>=cz else 2
        q_villages[q].append((x,z))
    occupied=[q for q in range(4) if q_villages[q]]
    if len(occupied)<3:return 0,None
    quad_combos=[(0,1,2),(0,1,3),(0,2,3),(1,2,3)]
    qualifying=[]
    for qa,qb,qc in quad_combos:
        if not (q_villages[qa] and q_villages[qb] and q_villages[qc]):continue
        for va in q_villages[qa]:
            for vb in q_villages[qb]:
                if (va[0]-vb[0])**2+(va[1]-vb[1])**2<256**2:continue
                for vc in q_villages[qc]:
                    if ((va[0]-vc[0])**2+(va[1]-vc[1])**2>=256**2 and
                        (vb[0]-vc[0])**2+(vb[1]-vc[1])**2>=256**2):
                        qualifying.append(tuple(sorted([va,vb,vc])))
    if not qualifying:return 0,None
    qualifying.sort()
    return 15,qualifying[0]


def treasure_bastion_bonus_v2(bastions,center,get_variant_fn,nether_half=None):
    nb=nether_bounds(center,nether_half)
    captured=[tuple(p) for p in bastions if contains(p,nb)]
    variants=[]
    for p in captured:
        var=get_variant_fn(p[0],p[1])
        if var<0:
            raise RuntimeError(f'Bastion variant prediction failed at {p}: code {var}')
        variants.append((p[0],p[1],var))
    has_treasure=any(var==2 for _,_,var in variants)
    return (15 if has_treasure else 0),variants


class PaletteIndex:
    """Independent prefix counts over the fixed macro lattice for cheap windows."""
    def __init__(self,sampler,policy,v2=False,overworld_half=None,nether_half=None):
        import numpy as np
        from ..backend import biome_name
        from .biomes import canonical
        from .blueprint import PALETTE,CAVE_FAMILIES,DYNAMIC_LUXURIES,DYNAMIC_V2_LUXURIES
        from .sampling import grid_points
        self.np=np
        self.v2=v2
        self.ow_half = policy.get('overworld_half', OVERWORLD_HALF if overworld_half is None else overworld_half)
        self.nw_half = policy.get('nether_half', NETHER_HALF if nether_half is None else nether_half)
        self.required_indices=[i for i,f in enumerate(PALETTE) if f in policy['required_families']]
        luxuries_table=DYNAMIC_V2_LUXURIES if v2 else DYNAMIC_LUXURIES
        masks=np.zeros((23,63,63),dtype=np.int32)
        for y in policy['sample_y_levels']:
            points=grid_points((-2000,-2000,2000,2000),64,y,'world')
            values=sampler.sample(points)
            names=np.array([canonical(biome_name(int(v))) for v in values]).reshape(63,63)
            for i,family in enumerate(PALETTE):
                if y in ((-48,0) if family in CAVE_FAMILIES else (63,160)):
                    members=PALETTE[family]|({'frozen_peaks'} if family=='peaks' and policy.get('include_frozen_peaks') else set())
                    masks[i]|=np.isin(names,list(members))
            if y==63:
                self.surface=names
                for i,(_,members) in enumerate(luxuries_table):masks[13+i]=np.isin(names,members)
        self.prefix=np.pad(masks,((0,0),(1,0),(1,0))).cumsum(1).cumsum(2)
        nw_bound = 640 if self.nw_half == 512 else 512
        points=grid_points((-nw_bound,-nw_bound,nw_bound+1,nw_bound+1),64,64,'world')
        values=sampler.sample(points,dimension=-1)
        grid_side = (2 * nw_bound) // 64 + 1
        names=np.array([biome_name(int(v)) for v in values]).reshape(grid_side,grid_side)
        mask=np.array([names==name for name in NETHER_BIOMES],dtype=np.int32)
        self.nether=np.pad(mask,((0,0),(1,0),(1,0))).cumsum(1).cumsum(2)

    @staticmethod
    def counts(prefix,x0,z0,x1,z1):
        return prefix[:,z1,x1]-prefix[:,z0,x1]-prefix[:,z1,x0]+prefix[:,z0,x0]

    def window(self,center):
        x,z=center
        return self.counts(self.prefix,-(-(x-self.ow_half+1984)//64),-(-(z-self.ow_half+1984)//64),
                           -(-(x+self.ow_half+1984)//64),-(-(z+self.ow_half+1984)//64))

    def valid(self,center):
        x,z=center
        half_span = 8 * self.nw_half
        grid_min = -640 if self.nw_half == 512 else -512
        grid_offset = -grid_min * 8
        return bool(self.np.all(self.window(center)[self.required_indices]>0) and self.np.all(self.counts(self.nether,
            -(-(x-half_span+grid_offset)//512),-(-(z-half_span+grid_offset)//512),
            -(-(x+half_span+grid_offset)//512),-(-(z+half_span+grid_offset)//512))>0))

    def luxuries(self,center):
        from .blueprint import DYNAMIC_LUXURIES,DYNAMIC_V2_LUXURIES
        table=DYNAMIC_V2_LUXURIES if self.v2 else DYNAMIC_LUXURIES
        return [members[0] for count,(_,members) in zip(self.window(center)[13:],table) if count]

    def scenic_pair(self,center):
        return scenic_pair_bonus_v2(self.surface,center,overworld_half=self.ow_half)

```

---

<a id="file-8"></a>
### File 8: `src/seed_search/realm/top_tracker.py`
> **Purpose:** Top-50 In-Memory Priority Queue, RevStr Lexical Inversion, Tie-Breaking  
> **Length:** 288 lines | **Language:** PYTHON

```python
"""In-memory Top-50 candidate tracker with pure arithmetic ordering and persistence.

Maintains the top 50 discovered realm candidate seeds in memory with zero
per-batch disk bottleneck, matching the exact candidate_leaderboard_v2 ordering.
Provides O(1) cutoff score inspection and periodic serialization to JSON/SQLite.
"""
import copy
import heapq
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple


class RevStr:
    """Reversed string wrapper for binary lexical comparison in min-heaps.

    In a min-heap storing (key, ...), smaller keys represent worse candidates.
    ORDER_V2 orders candidates by `id ASC` (smaller lexical ID is better).
    Therefore, a better candidate (smaller id) must have a larger RevStr key,
    and a worse candidate (larger id) must have a smaller RevStr key.
    """
    __slots__ = ('s',)

    def __init__(self, s: str):
        self.s = str(s)

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, RevStr):
            return self.s > other.s
        return self.s > str(other)

    def __le__(self, other: Any) -> bool:
        if isinstance(other, RevStr):
            return self.s >= other.s
        return self.s >= str(other)

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, RevStr):
            return self.s < other.s
        return self.s < str(other)

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, RevStr):
            return self.s <= other.s
        return self.s <= str(other)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, RevStr):
            return self.s == other.s
        return self.s == str(other)

    def __ne__(self, other: Any) -> bool:
        if isinstance(other, RevStr):
            return self.s != other.s
        return self.s != str(other)

    def __repr__(self) -> str:
        return f"RevStr({self.s!r})"


class Top50Tracker:
    """Bounded in-memory priority queue maintaining the top N candidates."""

    def __init__(self, capacity: int = 50):
        if capacity < 1:
            raise ValueError("Capacity must be at least 1")
        self.capacity = capacity
        # Min-heap storing tuples: (sort_key, insertion_index, record)
        # sort_key is constructed so that WORSE candidates have SMALLER keys,
        # placing the worst candidate among the top N at root (index 0).
        self._heap: List[Tuple[Tuple[Any, ...], int, Dict[str, Any]]] = []
        self._seed_map: Dict[str, Tuple[Tuple[Any, ...], int, Dict[str, Any]]] = {}
        self._counter: int = 0

    def _extract_seed(self, record: Dict[str, Any]) -> str:
        anchor = record['anchors'][0] if (isinstance(record.get('anchors'), list) and record['anchors']) else record
        return str(record.get('seed') or anchor.get('seed') or '')

    def _extract_key(self, record: Dict[str, Any]) -> Tuple[int, int, int, int, int, int, int, RevStr]:
        """Extract arithmetic ranking tuple matching ORDER_V2.

        ORDER_V2: ranking_tier ASC, smart_score DESC, unmet_requirements ASC,
                  radial_key ASC, origin_distance_squared ASC, eval_cx ASC, eval_cz ASC, id ASC.

        For min-heap (worst at root), worse candidate must have smaller key:
        - tier: higher is worse -> -tier
        - score: lower is worse -> +score
        - misses: higher is worse -> -misses
        - radial_key: higher is worse -> -radial_key
        - orig_dist_sq: higher is worse -> -orig_dist_sq
        - eval_cx: higher is worse -> -eval_cx
        - eval_cz: higher is worse -> -eval_cz
        - id: higher is worse -> RevStr(raw_id)
        """
        anchor = record['anchors'][0] if (isinstance(record.get('anchors'), list) and record['anchors']) else record

        # Tier: 0 for PREDICTED/VERIFIED, 1 for PENDING, 2 for FAILED/NEAR_MISS
        if 'ranking_tier' in record:
            tier = int(record['ranking_tier'])
        elif 'ranking_tier' in anchor:
            tier = int(anchor['ranking_tier'])
        else:
            qual = record.get('qualification') or anchor.get('qualification')
            if qual in ('VERIFIED', 'PREDICTED'):
                tier = 0
            elif qual == 'PENDING':
                tier = 1
            else:
                tier = 2

        score = int(
            record.get('baseline_score_observed')
            or anchor.get('baseline_score_observed')
            or record.get('baseline_score')
            or anchor.get('baseline_score')
            or (record.get('ranking', {}).get('score') if isinstance(record.get('ranking'), dict) else None)
            or (anchor.get('ranking', {}).get('score') if isinstance(anchor.get('ranking'), dict) else None)
            or 0
        )

        deficits = record.get('deficit_categories') or anchor.get('deficit_categories')
        misses = len(deficits) if isinstance(deficits, list) else int(record.get('unmet_requirements', anchor.get('unmet_requirements', 0)))

        radial_key = int(
            record.get('radial_key')
            or anchor.get('radial_key')
            or (record.get('ranking', {}).get('radial_key') if isinstance(record.get('ranking'), dict) else None)
            or (anchor.get('ranking', {}).get('radial_key') if isinstance(anchor.get('ranking'), dict) else None)
            or 0
        )

        orig_dist_sq = int(
            record.get('origin_distance_squared')
            or anchor.get('origin_distance_squared')
            or (record.get('ranking', {}).get('origin_distance_squared') if isinstance(record.get('ranking'), dict) else None)
            or (anchor.get('ranking', {}).get('origin_distance_squared') if isinstance(anchor.get('ranking'), dict) else None)
            or 0
        )

        center = record.get('evaluation_center') or anchor.get('evaluation_center')
        if not center or len(center) < 2:
            cx, cz = 0, 0
        else:
            cx, cz = int(center[0]), int(center[1])

        raw_id = str(record.get('id') or anchor.get('id') or record.get('seed') or anchor.get('seed') or '')

        return (-tier, score, -misses, -radial_key, -orig_dist_sq, -cx, -cz, RevStr(raw_id))

    def observe(self, record: Dict[str, Any]) -> bool:
        """Observe a candidate record. Returns True if accepted into top N, False otherwise.

        Deduplicates by seed: if the exact same seed already exists in the heap,
        updates it only if the new record is better, avoiding duplicate slots.
        Deep copies record on insertion so external mutations don't invalidate heap keys.
        """
        record_copy = copy.deepcopy(record)
        key = self._extract_key(record_copy)
        seed = self._extract_seed(record_copy)

        if seed and seed in self._seed_map:
            existing_entry = self._seed_map[seed]
            existing_key = existing_entry[0]
            if key <= existing_key:
                return False
            # Better observation for the same seed: replace it in-place
            self._counter += 1
            new_entry = (key, self._counter, record_copy)
            self._seed_map[seed] = new_entry
            old_counter = existing_entry[1]
            for i, item in enumerate(self._heap):
                if item[1] == old_counter:
                    self._heap[i] = new_entry
                    heapq.heapify(self._heap)
                    break
            return True

        self._counter += 1
        entry = (key, self._counter, record_copy)

        if len(self._heap) < self.capacity:
            heapq.heappush(self._heap, entry)
            if seed:
                self._seed_map[seed] = entry
            return True

        # When at capacity, compare with current 50th-best (the heap root)
        if key > self._heap[0][0]:
            popped = heapq.heappushpop(self._heap, entry)
            popped_seed = self._extract_seed(popped[2])
            if popped_seed and popped_seed in self._seed_map:
                del self._seed_map[popped_seed]
            if seed:
                self._seed_map[seed] = entry
            return True

        return False

    def cutoff_score(self) -> Optional[int]:
        """Return the minimum score required to displace the current Nth-best candidate.

        Returns None if fewer than capacity candidates have been observed.
        """
        if len(self._heap) < self.capacity:
            return None
        return self._heap[0][0][1]

    def cutoff_key(self) -> Optional[Tuple[Any, ...]]:
        """Return the raw sorting key of the Nth-best candidate."""
        if len(self._heap) < self.capacity:
            return None
        return self._heap[0][0]

    def __len__(self) -> int:
        return len(self._heap)

    def top_records(self) -> List[Dict[str, Any]]:
        """Return records sorted from Rank 1 (best) to Rank N (worst)."""
        # In our heap, larger key is better. So descending order gives Rank 1 first.
        sorted_entries = sorted(self._heap, key=lambda item: item[0], reverse=True)
        return [copy.deepcopy(item[2]) for item in sorted_entries]

    def save_to_json(self, path: str) -> None:
        """Atomically dump current top records to a JSON file."""
        records = self.top_records()
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        import os
        os.replace(tmp_path, path)

    def load_from_json(self, path: str) -> int:
        """Load candidate records from JSON file. Returns count loaded."""
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)
        count = 0
        for r in records:
            if isinstance(r, dict):
                self.observe(r)
                count += 1
        return count

    def save_to_sqlite(self, db_or_conn: Any, table_name: str = "top_candidates", *, transactional: bool = True) -> None:
        """Save current top records into SQLite table."""
        records = self.top_records()
        is_path = isinstance(db_or_conn, (str, bytes)) or hasattr(db_or_conn, '__fspath__')
        conn = sqlite3.connect(db_or_conn) if is_path else getattr(db_or_conn, 'db', db_or_conn)
        try:
            with conn:
                conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        rank INTEGER PRIMARY KEY,
                        seed TEXT NOT NULL,
                        score INTEGER NOT NULL,
                        result TEXT NOT NULL
                    )
                """)
                conn.execute(f"DELETE FROM {table_name}")
                rows = []
                for rank, rec in enumerate(records, start=1):
                    anchor = rec['anchors'][0] if (isinstance(rec.get('anchors'), list) and rec['anchors']) else rec
                    raw_seed = str(rec.get('seed') or anchor.get('seed') or '')
                    score = int(
                        anchor.get('baseline_score_observed')
                        or anchor.get('baseline_score')
                        or rec.get('baseline_score_observed')
                        or rec.get('baseline_score')
                        or (anchor.get('ranking', {}).get('score') if isinstance(anchor.get('ranking'), dict) else None)
                        or (rec.get('ranking', {}).get('score') if isinstance(rec.get('ranking'), dict) else None)
                        or 0
                    )
                    rows.append((rank, raw_seed, score, json.dumps(rec)))
                if rows:
                    conn.executemany(
                        f"INSERT INTO {table_name} (rank, seed, score, result) VALUES (?, ?, ?, ?)",
                        rows
                    )
        finally:
            if is_path:
                conn.close()

    def flush(self, db_or_conn: Any, table_name: str = "top_candidates") -> None:
        """Periodic flush of current top records to SQLite."""
        self.save_to_sqlite(db_or_conn, table_name=table_name, transactional=True)

    def flush_transactional(self, db_or_conn: Any, table_name: str = "top_candidates") -> None:
        """Atomic transactional save of current top records to SQLite."""
        self.save_to_sqlite(db_or_conn, table_name=table_name, transactional=True)

```

---

<a id="file-9"></a>
### File 9: `src/seed_search/realm/reports.py`
> **Purpose:** Candidate Rescore Idempotence, Dispatch & Serialization (_candidate_rescore)  
> **Length:** 568 lines | **Language:** PYTHON

```python
"""Streaming full candidate exports and independently ranked variant views."""
import csv
import json
import math
import copy
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import time
import uuid

from .store import canonical


def _ranked(store, variant='baseline', limit=20):
    if variant=='baseline':
        from .leaderboard import rows
        result=[]
        for encoded,score,tier,misses in rows(store.db,limit):
            row=json.loads(encoded)
            near=(row.get('retention') or {}).get('classification')=='NEAR_MISS'
            row['smart_score']=score
            row['unmet_requirements']=misses if near else None
            row['leaderboard_rank']=len(result)+1
            row['ranking_view']='observed_partial_predictor_score; near miss' if near else 'complete_predictor_score' if row.get('baseline_score_complete',True) else 'provisional_interval_midpoint; inventory pending'
            result.append(row)
        return result
    elif variant in ('v1','v2'):
        # Only a complete score with verified weighted components replaces prediction.
        actual="json_extract(result,'$.result.actual_evaluation.score_verified_complete')=1"
        sql=f"""SELECT result FROM variants WHERE variant=? ORDER BY
            CASE WHEN {actual} OR json_extract(result,'$.result.score_verified_complete')=1 THEN 0
                 WHEN json_extract(result,'$.result.evidence')='PREDICTED' THEN 1 ELSE 2 END,
            CASE WHEN {actual} THEN CASE json_extract(result,'$.result.actual_evaluation.geometry_pass') WHEN 1 THEN 0 ELSE 1 END
                 ELSE CASE json_extract(result,'$.result.geometry_pass') WHEN 1 THEN 0 ELSE 1 END END,
            CASE WHEN {actual} THEN CAST(json_extract(result,'$.result.actual_evaluation.score') AS REAL)
                 ELSE CAST(json_extract(result,'$.result.score') AS REAL) END DESC,candidate_id,center LIMIT ?"""
        rows=[json.loads(r[0]) for r in store.db.execute(sql,(variant,limit))]
        for row in rows:
            result=row['result'];generated=result.get('actual_evaluation',{})
            row['ranking_view']='verified' if generated.get('score_verified_complete') or result.get('score_verified_complete') else 'prediction' if result.get('score_generation_source')!='actual' else 'actual_partial'
            row['ranking_result']=generated if generated.get('score_verified_complete') else result
        return rows
    else:raise ValueError('Results variant must be baseline, v1 or v2')


def _export_files(store, root, output):
    counts={}
    for variant in ('baseline','v1','v2'):
        rows=store.iter_candidates(include_score=True) if variant=='baseline' else store.iter_variants(variant=variant)
        # JSONL preserves all nested evidence; CSV contains independently useful summaries.
        fields=['candidate_id','seed','stronghold','evaluation_center','predicted_strongholds','screening_revision',
                'deficit_categories','fatal_reasons','marine_status','spawn_status','suggested_spawn','player_inspections','actual_generation_status',
                'variant','center','qualification','data_status',
                'smart_score',
                'retention_classification','unmet_requirements','pending_reasons','score','score_status','inventory_status','predicted_score','actual_partial_score','verified_score','geometry_score','border_fit','final_nether_status',
                'surface_wooded_requirement','surface_wooded_families','surface_bonus_interval','raw_record']
        with (root/f'{variant}.jsonl').open('w') as js,(root/f'{variant}.csv').open('w',newline='') as csvfile:
            writer=csv.DictWriter(csvfile,fieldnames=fields);writer.writeheader();n=0
            for row in rows:
                record=row.get('result',row)
                cid=row.get('candidate_id',row.get('id'))
                if variant!='baseline':
                    candidate=json.loads(store.db.execute('SELECT result FROM candidates WHERE id=?',(cid,)).fetchone()[0])
                    row={**row,'baseline':candidate}
                else:candidate=row
                surface=candidate.get('surface_biome_verification',{})
                surface_classification=surface.get('classification',{})
                smart_score=row.get('smart_score') if variant=='baseline' else None
                encoded=json.dumps(row,allow_nan=False,separators=(',',':'))
                js.write(encoded+'\n')
                starts=candidate.get('predicted_strongholds')
                writer.writerow({'candidate_id':cid,'seed':candidate['seed'],
                                 'stronghold':json.dumps(starts[0] if starts else None if candidate.get('evaluation_center') is not None else candidate['stronghold']),
                                 'evaluation_center':json.dumps(candidate.get('evaluation_center')),
                                 'predicted_strongholds':json.dumps(starts),
                                 'screening_revision':candidate.get('screening_revision'),
                                 'deficit_categories':json.dumps(candidate.get('deficit_categories',[])),
                                 'fatal_reasons':json.dumps(candidate.get('fatal_reasons',[])),
                                 'marine_status':(candidate.get('marine_stage') or {}).get('status','DEFERRED'),
                                 'spawn_status':(candidate.get('spawn_stage') or {}).get('status','PENDING'),
                                 'suggested_spawn':json.dumps(candidate.get('suggested_spawn')),
                                 'player_inspections':json.dumps(candidate.get('player_inspections')),
                                 'actual_generation_status':(candidate.get('actual_generation_verification') or {}).get('status','PENDING'),
                                 'variant':variant,'center':json.dumps(record.get('center')),
                                 'qualification':record.get('qualification'),'data_status':record.get('evidence',record.get('data_status')),
                                 'smart_score':smart_score,
                                 'retention_classification':(candidate.get('retention') or {}).get('classification'),
                                 'unmet_requirements':(candidate.get('retention') or {}).get('unmet_requirements'),
                                 'pending_reasons':json.dumps(candidate.get('pending_reasons',[])),
                                 'score':record.get('score',record.get('baseline_score')),
                                 'score_status':record.get('baseline_score_status',record.get('score_component_status')),
                                 'inventory_status':(candidate.get('inventory') or {}).get('status','legacy'),
                                 'predicted_score':record.get('predicted_score'),
                                 'actual_partial_score':record.get('actual_partial_score'),'verified_score':record.get('verified_score'),'geometry_score':record.get('geometry_score'),
                                 'border_fit':json.dumps(record.get('border_fit')),
                                 'final_nether_status':candidate.get('final_nether_status'),
                                 'surface_wooded_requirement':surface.get('wooded_requirement'),
                                 'surface_wooded_families':json.dumps(surface_classification.get('wooded_families',[])),
                                 'surface_bonus_interval':json.dumps(((surface_classification.get('uncertainty') or {}).get('actual_generation_score_interval'))),
                                 'raw_record':encoded})
                n+=1
        counts[variant]=n
    structure_rows=0
    with (root/'structure_starts.csv').open('w',newline='') as handle:
        fields=['candidate_id','seed','screening_revision','structure','dimension','x','y','z','predicted_viable',
                'horizontal_distance_blocks','distance_frame','hub_x','hub_z','hub_kind',
                'evidence_status','actual_generation_status']
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for candidate in store.iter_candidates():
            center=candidate.get('evaluation_center',candidate['stronghold'])
            for group,dimension in (('required_structures','overworld'),('required_nether_structures','nether'),('optional_structures','overworld')):
                for name,observation in candidate.get(group,{}).items():
                    hub=[center[0]/8,center[1]/8] if dimension=='nether' else center
                    viable={tuple(point[:2]) for point in observation.get('predicted_viable',[]) if isinstance(point,(list,tuple)) and len(point)>=2}
                    raw={tuple(point[:2]) for point in observation.get('raw',[]) if isinstance(point,(list,tuple)) and len(point)>=2}
                    for point in sorted(raw|viable):
                        if not isinstance(point,(list,tuple)) or len(point)<2:continue
                        x,z=point[:2]
                        writer.writerow({'candidate_id':candidate['id'],'seed':candidate['seed'],
                            'screening_revision':candidate.get('screening_revision'),'structure':name,
                            'dimension':dimension,'x':x,'y':'','z':z,'predicted_viable':point in viable,
                            'horizontal_distance_blocks':round(math.hypot(x-hub[0],z-hub[1]),3),
                            'distance_frame':'nether block coordinates' if dimension=='nether' else 'overworld block coordinates',
                            'hub_x':hub[0],'hub_z':hub[1],
                            'hub_kind':'fixed_world_origin' if candidate.get('evaluation_center')==[0,0] else 'candidate_center',
                            'evidence_status':observation.get('data_status','PREDICTED'),
                            'actual_generation_status':(candidate.get('actual_generation_verification') or {}).get('status','PENDING')})
                        structure_rows+=1
    summary={'status':store.status(),'exported_records':counts,'output':str(output.resolve())}
    summary['structure_start_rows']=structure_rows
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    lines=['Realm candidate results','',f"Distinct full64 inputs committed: {summary['status']['completed_seeds']}",
           'Predictions and unknown evidence remain separate from actual-generation verification.','']
    for variant in ('baseline','v1','v2'):
        lines.append(f'{variant}: {counts[variant]} saved records')
        for row in _ranked(store,variant,10):
            r=row.get('ranking_result',row.get('result',row))
            lines.append(f"- {row.get('candidate_id',row.get('id'))}: {r.get('qualification')}; score {row.get('smart_score',r.get('score',r.get('baseline_score')))}; border {r.get('border_fit','not evaluated')}")
            if variant=='baseline' and row.get('suggested_spawn'):
                suggestion=row['suggested_spawn']
                lines.append(f"  Community spawn suggestion: {suggestion.get('coordinates')}; {suggestion['status']}; biome sample Y is not verified ground height or safety.")
            if variant=='baseline' and row.get('player_inspections'):
                lines.append('  Optional inspections: '+', '.join(f"{name}: {evidence['status']}" for name,evidence in row['player_inspections'].items()))
            if variant=='baseline' and row.get('surface_biome_verification'):
                surface=row['surface_biome_verification']
                lines.append(f"  Actual surface wooded requirement: {surface['wooded_requirement']}; families {', '.join(surface['classification']['wooded_families'])}; point samples cannot establish absence.")
        lines.append('')
    (root/'SUMMARY.md').write_text('\n'.join(lines)+'\n')
    return summary



def ensure_score_revision_complete(store):
    """Reject mixed-score views while a bounded rescore revision remains incomplete."""
    revision=store.get_state('rescore_revision')
    if revision and revision.get('status')!='complete':
        raise ValueError('Incomplete score revision; resume rescore with its saved policy before ranking, export or generation')


@contextmanager
def _read_snapshot(store):
    snapshot=copy.copy(store)
    snapshot.db=sqlite3.connect((store.run/'realm.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
    try:
        snapshot.db.execute('BEGIN')
        ensure_score_revision_complete(snapshot)
        yield snapshot
    finally:
        snapshot.db.close()


@contextmanager
def _rescore_lock(store):
    with (store.run/'.realm-scan.lock').open('a+') as lock:
        try:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Another scanner or rescore owns this run') from exc
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def ranked(store, variant='baseline', limit=20):
    with _read_snapshot(store) as snapshot:
        return _ranked(snapshot,variant,limit)


def _fsync_directory(path):
    fd=os.open(path,os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _sync_file(path):
    with path.open('rb') as handle:
        os.fsync(handle.fileno())


def _write_manifest(generation, metadata):
    files={}
    for path in sorted(generation.iterdir()):
        if path.is_file() and path.name!='manifest.json':
            digest=hashlib.sha256()
            with path.open('rb') as handle:
                for chunk in iter(lambda:handle.read(1<<20),b''):
                    digest.update(chunk)
            files[path.name]={'bytes':path.stat().st_size,'sha256':digest.hexdigest()}
            _sync_file(path)
    manifest={**metadata,'files':files}
    (generation/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    _sync_file(generation/'manifest.json')
    _fsync_directory(generation)
    return manifest


def _publish_pointer(root,generation):
    temporary=root/f'.current-{uuid.uuid4().hex}'
    try:
        temporary.symlink_to(generation.relative_to(root),target_is_directory=True)
        os.replace(temporary,root/'current')
        _fsync_directory(root)
    finally:
        temporary.unlink(missing_ok=True)


EXPORT_FILES=('baseline.jsonl','baseline.csv','v1.jsonl','v1.csv','v2.jsonl','v2.csv','structure_starts.csv','summary.json','SUMMARY.md','manifest.json')


def _prepare_compatibility_paths(root):
    """Migrate prior flat exports without changing their bytes before publication."""
    current=root/'current'
    old=[root/name for name in EXPORT_FILES if (root/name).is_file() and not (root/name).is_symlink()]
    if old:
        legacy=root/'.generations'/f'legacy-{uuid.uuid4().hex}'
        legacy.mkdir()
        # A partial earlier migration has links to current; copy that complete view too.
        for name in EXPORT_FILES:
            source=root/name
            if source.is_file():
                shutil.copyfile(source,legacy/name)
        if not (legacy/'manifest.json').exists():
            _write_manifest(legacy,{'generation':legacy.name,'kind':'legacy-export-migration'})
        else:
            for path in legacy.iterdir():
                _sync_file(path)
            _fsync_directory(legacy)
        _publish_pointer(root,legacy)
    for name in EXPORT_FILES:
        destination=root/name
        target=Path('current')/name
        if destination.is_symlink() and os.readlink(destination)==str(target):
            continue
        temporary=root/f'.alias-{uuid.uuid4().hex}'
        try:
            temporary.symlink_to(target)
            os.replace(temporary,destination)
        finally:
            temporary.unlink(missing_ok=True)
    _fsync_directory(root)


@contextmanager
def _export_lock(root):
    with (root/'.export.lock').open('a+') as lock:
        try:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Another export owns this output directory') from exc
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def export(store, output=None):
    """Publish one immutable complete export generation through an atomic pointer.

    Stable root paths resolve through current; multi-file consumers must resolve
    current once and read the pinned generation to avoid crossing a later switch.
    """
    root=Path(output or store.run/'results').resolve()
    root.mkdir(parents=True,exist_ok=True)
    with _export_lock(root):
        return _export_generation(store,root)


def _export_generation(store,root):
    generations=root/'.generations';generations.mkdir(exist_ok=True)
    generation=generations/f'export-{uuid.uuid4().hex}'
    generation.mkdir()
    try:
        with _read_snapshot(store) as snapshot:
            summary=_export_files(snapshot,generation,root)
            summary['generation']=generation.name
            summary['generation_path']=str(generation)
            (generation/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
            if not all((generation/name).is_file() for name in EXPORT_FILES if name!='manifest.json'):
                raise ValueError('Export generation is missing required files')
            revision=snapshot.get_state('rescore_revision')
            identity=snapshot.get_state('identity')
            _write_manifest(generation,{'generation':generation.name,'kind':'complete-export','status':'complete',
                'created_at':time.time(),'score_revision':revision,'source_identity_sha256':hashlib.sha256(canonical(identity).encode()).hexdigest(),
                'exported_records':summary['exported_records'],'completed_seeds':summary['status']['completed_seeds']})
        _fsync_directory(generations)
        _prepare_compatibility_paths(root)
        _publish_pointer(root,generation)
        return summary
    except BaseException:
        # Complete-but-unpublished generations are safe to retain for inspection.
        # Incomplete staging directories are never made current.
        raise


def _candidate_rescore(candidate,policy,revision_id):
    if candidate.get('contract')=='master_seed_blueprint_v1':
        from .config import dynamic_policy
        if dynamic_policy(candidate):
            from .config import dynamic_v2_policy, dynamic_v3_policy
            cfg = policy if (policy and dynamic_policy(policy)) else candidate
            if dynamic_v3_policy(cfg) or dynamic_v2_policy(cfg):
                is_v3 = dynamic_v3_policy(cfg)
                from .blueprint import dynamic_v2_score, dynamic_v3_score, score_uncertainty
                from .dynamic import (hub_bonus_v2, hub_bonus_v3, hub_village_v2,
                                      weighted_radial_v2, weighted_radial_v3,
                                      village_spread_bonus_v2, retained_scenic_pair_v2,
                                      treasure_bastion_bonus_v2, nether_core_bonus_v3)
                import math
                center=candidate['evaluation_center']
                required=candidate['required_structures']
                structures={name:ob['predicted_viable'] for name,ob in required.items()}
                observations={**required,**candidate['required_nether_structures'],**candidate['optional_structures']}
                counts={name:len(ob['predicted_viable']) for name,ob in observations.items()}
                names=[s['biome'] for s in candidate['biomes']['sampling']['samples'] if s['coordinate'][1]==63]
                ow_half = 1024 if is_v3 else None
                nether_half = 512 if is_v3 else None
                hub=hub_bonus_v3(structures,center) if is_v3 else hub_bonus_v2(structures,center)
                scenic,scenic_witness,river_witness=retained_scenic_pair_v2(
                    candidate['biomes']['sampling']['samples'],center,overworld_half=ow_half)
                spread,triple=village_spread_bonus_v2(structures['village'],center,overworld_half=ow_half)
                variants=candidate.get('bastion_variants')
                if not isinstance(variants,list):
                    raise ValueError('Missing retained Bastion variants; re-evaluate this seed before rescoring')
                by_coordinate={(x,z):variant for x,z,variant in variants}
                bastions=candidate['required_nether_structures']['bastion']['predicted_viable']
                if any(tuple(p) not in by_coordinate for p in bastions):
                    raise ValueError('Incomplete retained Bastion variants; re-evaluate this seed before rescoring')
                tb,_=treasure_bastion_bonus_v2(bastions,center,lambda x,z:by_coordinate[(x,z)],nether_half=nether_half)
                targets=candidate.get('configured_targets') or (policy.get('structures',{}).get('minimum_counts') if policy else None)
                opt_counts={name:len(ob['predicted_viable']) for name,ob in candidate['optional_structures'].items()}
                if is_v3:
                    nether_points = {name: ob['predicted_viable'] for name, ob in candidate['required_nether_structures'].items()}
                    nether_core = nether_core_bonus_v3(nether_points, center)
                    score,components,deficits=dynamic_v3_score(
                        counts,
                        biome_names=names,
                        hub=hub,
                        scenic=scenic,
                        village_spread=spread,
                        treasure_bastion=tb,
                        optional_counts=opt_counts,
                        nether_core=nether_core,
                    )
                else:
                    score,components,deficits=dynamic_v2_score(counts,names,hub,scenic,spread,tb,opt_counts,targets=targets)
                radial=weighted_radial_v3(structures,center,overworld_half=ow_half) if is_v3 else weighted_radial_v2(structures,center)
                radial_key=int(math.floor(radial*1e6+0.5))
                orig_dist_sq=center[0]**2+center[1]**2
                origin=math.hypot(*center)
                update_fields=dict(baseline_score_observed=score,baseline_score=score,
                    baseline_score_uncertainty=score_uncertainty(score,[],True),score_revision=revision_id,
                    weighted_radial_dist=radial,origin_distance=origin,radial_key=radial_key,
                    origin_distance_squared=orig_dist_sq,deficit_penalty=components['deficit_penalty'],
                    bonus_total=components['bonus_total'],
                    hub_bonus=components.get('hub_bonus', 0),
                    scenic_bonus=scenic,scenic_witness=list(scenic_witness) if scenic_witness else None,
                    river_witness=list(river_witness) if river_witness else None,
                    village_spread_bonus=spread,village_triple=[list(p) for p in triple] if triple else None,
                    treasure_bastion=int(bool(tb)),
                    starter_hub_village=hub_village_v2(structures,center),deficit_categories=deficits)
                if is_v3:
                    update_fields['nether_core_bonus']=components.get('nether_core_bonus', 0)
                candidate.update(update_fields)
                candidate['ranking']={**candidate.get('ranking',{}),'score':score,'final_score':score,
                    'deficit_tier':len(candidate['deficit_categories']),'weighted_radial_dist':radial,
                    'radial_key':radial_key,'origin_distance_squared':orig_dist_sq,'origin_distance':origin,
                    'components':components}
                return candidate
            from .blueprint import dynamic_score,score_uncertainty
            from .dynamic import hub_bonus,weighted_radial
            import math
            center=candidate['evaluation_center']
            required=candidate['required_structures']
            structures={name:ob['predicted_viable'] for name,ob in required.items()}
            observations={**required,**candidate['required_nether_structures'],**candidate['optional_structures']}
            counts={name:len(ob['predicted_viable']) for name,ob in observations.items()}
            names=[s['biome'] for s in candidate['biomes']['sampling']['samples'] if s['coordinate'][1]==63]
            hub=hub_bonus(structures,center);score=dynamic_score(counts,names,hub)
            radial=weighted_radial(structures,center);origin=math.hypot(*center)
            candidate.update(baseline_score_observed=score,baseline_score=score,
                baseline_score_uncertainty=score_uncertainty(score,[],True),score_revision=revision_id,
                weighted_radial_dist=radial,origin_distance=origin)
            candidate['ranking']={**candidate.get('ranking',{}),'score':score,
                'deficit_tier':len(candidate['deficit_categories']),'weighted_radial_dist':radial,'origin_distance':origin,
                'components':{**candidate.get('ranking',{}).get('components',{}),'hub_bonus':hub}}
            return candidate
        from .blueprint import smart_score,score_uncertainty
        from .config import river_policy,origin_policy,two_group_policy,marine_baseline_policy
        v2=two_group_policy(candidate)
        marine_baseline=marine_baseline_policy(candidate)
        names=(s['biome'] for s in ((candidate.get('biomes') or {}).get('sampling') or {}).get('samples',()) if s['coordinate'][1]==63)
        required=candidate['required_structures']
        optional=candidate['optional_structures']
        # Historical v2 terrain work may append marine inventories; v3 already
        # includes them in its baseline. Keep baseline and combined scores distinct.
        baseline_required={k:v for k,v in required.items() if k not in ('monument','shipwreck')} if v2 and not marine_baseline else required
        baseline_optional={k:v for k,v in optional.items() if k not in ('monument','shipwreck')} if v2 and not marine_baseline else optional
        ranking=smart_score(baseline_required,candidate['required_nether_structures'],baseline_optional,
                            locked=bool(candidate.get('screening_revision')),river=river_policy(candidate),
                            origin=origin_policy(candidate),two_group=v2,biome_names=names,river_bonus=not marine_baseline,
                            metrics=None if v2 else candidate.get('terrain_score_metrics'))
        candidate.update(baseline_score_observed=ranking['score'],
                         baseline_score=ranking['score'] if candidate['baseline_score_complete'] else None,
                         baseline_score_uncertainty=score_uncertainty(ranking['score'],
                             candidate.get('fatal_reasons',[])+candidate.get('biome_failures',[]) if v2 else candidate['pending_reasons'],
                             candidate['baseline_score_complete']),score_revision=revision_id)
        if v2 and (candidate.get('marine_stage') or {}).get('status') in ('PREDICTED','VERIFIED'):
            source=(candidate.get('terrain_status') or {}).get('source')
            actual=isinstance(source,dict) and source.get('kind')=='actual_generation'
            prior_ranking=candidate.get('ranking') or {}
            combined=smart_score(required,candidate['required_nether_structures'],optional,
                                 locked=True,river=river_policy(candidate),origin=True,two_group=True,river_bonus=not marine_baseline,
                                 biome_names=(s['biome'] for s in ((candidate.get('biomes') or {}).get('sampling') or {}).get('samples',()) if s['coordinate'][1]==63),
                                 metrics=candidate.get('terrain_score_metrics') if actual else None,
                                 coastal_footprint_verified=actual and prior_ranking.get('coastal_footprint_bonus_status')=='VERIFIED')
            candidate.update(ranking=combined,combined_score=combined['score'])
        else:
            candidate['ranking']=ranking
        return candidate
    from .biomes import classify
    from .baseline import baseline_score_uncertainty
    if candidate.get('biomes'):
        evidence=candidate['biomes'].get('uncertainty',{})
        detection=classify(candidate['biomes']['raw_names'],policy['biomes'],
                           complete=evidence.get('exhaustive_verified') is True,
                           verified=evidence.get('domain')=='actual_generated_surface')
        candidate['biomes'].update({k:detection[k] for k in ('wooded_bonus','family_bonuses','variant_bonuses','surface_bonus','score','uncertainty')})
        observed_score=detection['score']+sum(policy['structures']['optional_bonuses'].get(k,0) for k,v in candidate['optional_structures'].items() if v.get('predicted_viable'))
        candidate['baseline_score_observed']=observed_score
        candidate['baseline_score']=observed_score if candidate.get('baseline_score_complete',True) else None
        for key,observation in candidate['optional_structures'].items():
            observation['bonus']=policy['structures']['optional_bonuses'].get(key,0) if observation.get('predicted_viable') else 0
    candidate['baseline_score_uncertainty']=baseline_score_uncertainty(candidate.get('biomes'),candidate.get('optional_structures') or {},policy,candidate.get('pending_reasons',[]))
    surface=candidate.get('surface_biome_verification')
    if surface and surface.get('classification'):
        detected=surface['classification']
        # Keep actual point evidence separate from the predictor baseline score.
        surface['classification']=classify(detected['raw_names'],policy['biomes'],complete=False,
                                            verified=(detected.get('uncertainty') or {}).get('domain')=='actual_generated_surface')
        surface['wooded_requirement']=surface['classification']['qualification']
        surface['score_revision']=revision_id
    candidate['score_revision']=revision_id
    return candidate


def _variant_rescore(wrapper,candidate,policy,revision_id):
    from .terrain import apply_score_policy,attach_actual_evaluation
    result=wrapper['result']
    result['baseline_quality']=min(100,max(0,100*(candidate.get('baseline_score') if candidate.get('baseline_score') is not None else candidate.get('baseline_score_observed',0))/policy['scoring']['baseline_quality_cap']))
    apply_score_policy(result,policy['scoring'],component_status={'baseline_quality':candidate.get('qualification','PENDING') if candidate.get('baseline_score_complete',True) else 'PARTIAL'})
    if result.get('actual_evaluation'):
        actual=result['actual_evaluation']
        actual['baseline_quality']=result['baseline_quality']
        apply_score_policy(actual,policy['scoring'],source='actual',component_status={'baseline_quality':candidate.get('qualification','PENDING') if candidate.get('baseline_score_complete',True) else 'PARTIAL'})
        attach_actual_evaluation(result,actual,policy['scoring'])
    result['rescore_policy']=dict(policy['scoring'])
    result['score_revision']=revision_id
    return wrapper


def _validate_rescore_policy(store,policy):
    from .config import validate_config
    validate_config(policy)
    old=copy.deepcopy(store.identity['config']);new=copy.deepcopy(policy)
    for cfg in (old,new):
        cfg.pop('scoring',None)
        for section,key in (('structures','optional_bonuses'),('biomes','family_bonuses'),('biomes','variant_bonuses')):
            cfg[section].pop(key,None)
    if old!=new:
        raise ValueError('Rescore may change bonus weights and score weights; generation or eligibility settings require a separate run')


def rescore(store, policy, *, batch_size=256, progress=None):
    """Bounded generation-free rescore; restart the same policy to finish its revision."""
    if isinstance(batch_size,bool) or not isinstance(batch_size,int) or not 1<=batch_size<=4096:
        raise ValueError('Rescore batch_size must be between 1 and 4096')
    if store.db.in_transaction:
        raise ValueError('Finish the caller transaction before starting rescore')
    _validate_rescore_policy(store,policy)
    policy=copy.deepcopy(policy)
    policy_hash=hashlib.sha256(canonical(policy).encode()).hexdigest()
    with _rescore_lock(store):
        revision=store.get_state('rescore_revision')
        if revision and revision.get('status')!='complete':
            if revision['policy_sha256']!=policy_hash:
                raise ValueError('Another score revision is incomplete; resume its saved policy first')
        else:
            number=(revision or {}).get('number',0)+1
            revision={'id':f'{number}-{policy_hash[:16]}','number':number,'status':'running','phase':'candidates',
                      'candidate_cursor':'','variant_cursor':['','',''],'policy':policy,'policy_sha256':policy_hash,
                      'rescored_candidates':0,'rescored_variants':0}
            store.set_state('rescore_revision',revision)
        while revision['phase']=='candidates':
            rows=store.db.execute('SELECT id,result FROM candidates WHERE id>? ORDER BY id LIMIT ?',
                                  (revision['candidate_cursor'],batch_size)).fetchall()
            if not rows:
                revision={**revision,'phase':'variants'}
                store.set_state('rescore_revision',revision)
                break
            updated=[]
            count=0
            for cid,payload in rows:
                candidate=json.loads(payload)
                count+=int(bool(candidate.get('biomes')))
                updated.append((canonical(_candidate_rescore(candidate,policy,revision['id'])),cid))
            next_revision={**revision,'candidate_cursor':rows[-1][0],
                           'rescored_candidates':revision['rescored_candidates']+count}
            with store.db:
                store.db.executemany('UPDATE candidates SET result=? WHERE id=?',updated)
                store._set('rescore_revision',next_revision)
            revision=next_revision
            if progress:
                progress(copy.deepcopy(revision))
        while revision['phase']=='variants':
            rows=store.db.execute('SELECT candidate_id,variant,center,result FROM variants WHERE (candidate_id,variant,center)>(?,?,?) ORDER BY candidate_id,variant,center LIMIT ?',
                                  (*revision['variant_cursor'],batch_size)).fetchall()
            if not rows:
                break
            updated=[]
            for cid,variant,center,payload in rows:
                candidate=store.get_candidate(cid)
                wrapper=_variant_rescore(json.loads(payload),candidate,policy,revision['id'])
                updated.append((canonical(wrapper),cid,variant,center))
            next_revision={**revision,'variant_cursor':list(rows[-1][:3]),
                           'rescored_variants':revision['rescored_variants']+len(rows)}
            with store.db:
                store.db.executemany('UPDATE variants SET result=? WHERE candidate_id=? AND variant=? AND center=?',updated)
                store._set('rescore_revision',next_revision)
            revision=next_revision
            if progress:
                progress(copy.deepcopy(revision))
        from .terrain import terrain_scoring_identity
        finished={**revision,'status':'complete','phase':'complete'}
        with store.db:
            store._set('score_policy',policy)
            store._set('rescore_revision',finished)
            if store.get_state('terrain_scoring_identity') is not None:
                store._set('terrain_scoring_identity',terrain_scoring_identity(policy))
        return {'rescored_candidates':finished['rescored_candidates'],'rescored_variants':finished['rescored_variants'],
                'generation_queries':0,'score_revision':finished['id']}

```

---

<a id="file-10"></a>
### File 10: `src/seed_search/realm/native_batch.py`
> **Purpose:** Python CFFI Engine Wrapper: Prototype, Buffer Decoding & persist_pipeline()  
> **Length:** 703 lines | **Language:** PYTHON

```python
"""Explicit native blueprint execution with owned, bounded durable stages.

All discovery/filter/inventory calculations happen in C. Python prepares owned
records directly; the replay provider remains an independent oracle. Full retention
keeps every input and anchor. Compact retention is an explicit separate contract
that saves predicted survivors and configured near misses with range receipts.
"""
import hashlib
import importlib.util
import json
import statistics
import time
from pathlib import Path
import os
import sys
import numpy as np

from seed_search.backend import biome_catalog, structure_type
from seed_search.realm.blueprint import PALETTE, evaluate_seed, evaluate_dynamic_seed
from seed_search.realm.biomes import canonical
from seed_search.realm.bounds import native_bounds
from seed_search.realm.config import BLUEPRINT_CONTRACT, validate_config, locked_policy, river_policy, LOCKED_ORDER, outpost_policy, origin_policy, two_group_policy, marine_baseline_policy, dynamic_policy, dynamic_v2_policy, dynamic_v3_policy, stronghold_after, baseline_requirements
from seed_search.realm.capabilities import identity as production_identity
from seed_search.realm.store import RealmStore
from seed_search.realm.native_records import build_record
from seed_search.seeds import MASK64, parse_seed, seed_from_index

NAMES=('mansion','jungle_temple','desert_pyramid','monument','ancient_city','village',
       'trial_chamber','ruined_portal','shipwreck','mineshaft','fortress','bastion','outpost')
METRICS={'biome_cache_hits','stage_seconds','native_work','worker_cpu_seconds','total_seconds','worker_pid',
         'worker_peak_rss_bytes','prototype'}


def semantic_record(value):
    return {k:v for k,v in value.items() if k not in METRICS}


def seeds_np(first: int, end: int, run_key: int):
    import numpy as np
    indices = np.arange(first, end, dtype=np.uint64)
    z = (indices + np.uint64(run_key & MASK64)) & np.uint64(MASK64)
    z = ((z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)) & np.uint64(MASK64)
    z = ((z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)) & np.uint64(MASK64)
    z ^= (z >> np.uint64(31))
    return z.astype(np.int64)


class Prototype:
    def __init__(self,directory,cfg):
        validate_config(cfg)
        if cfg.get('contract')!=BLUEPRINT_CONTRACT:raise ValueError('Prototype requires the exact blueprint contract')
        if not outpost_policy(cfg) and tuple(cfg['search']['structure_order'])!=(tuple(LOCKED_ORDER) if locked_policy(cfg) else NAMES[:10]):raise ValueError('Prototype requires its audited structure order')
        if cfg['search']['inventory_mode']!='eligibility':raise ValueError('Native baseline requires eligibility inventory mode; use the Python route for other profiles')
        if cfg['biomes']['spacing']!=64 or cfg['biomes']['lattice']!='world':raise ValueError('Prototype requires the world-aligned 64-block lattice')
        if directory is None:
            try:self.module=importlib.import_module('seed_search._blueprint_batch')
            except ImportError as exc:raise ValueError('Native blueprint extension unavailable; build native/blueprint_build.py or supply --native-build') from exc
            self.directory=None;path=Path(self.module.__file__).resolve()
            ffi,lib=self.module.ffi,self.module.lib
            runtime=ffi.string(lib.ss_openmp_library()).decode() if lib.ss_openmp_enabled() else None
            self.identity={'extension':str(path),'extension_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'openmp':bool(lib.ss_openmp_enabled()),'runtime':runtime,
                'runtime_sha256':hashlib.sha256(Path(runtime).read_bytes()).hexdigest() if runtime else None,
                'scope':'packaged complete native blueprint baseline','production_extension_replaced':False,
                'stronghold_after':int(lib.nb_stronghold_after()) if hasattr(lib,'nb_stronghold_after') else None}
        else:
            self.directory=Path(directory).resolve();self.identity=json.loads((self.directory/'identity.json').read_text())
            path=Path(self.identity['extension'])
            if not path.is_relative_to(self.directory) or hashlib.sha256(path.read_bytes()).hexdigest()!=self.identity['extension_sha256']:
                raise ValueError('Private extension identity mismatch')
            runtime=self.identity.get('runtime')
            if runtime and hashlib.sha256(Path(runtime).read_bytes()).hexdigest()!=self.identity.get('runtime_sha256'):
                raise ValueError('Native OpenMP runtime identity mismatch')
            spec=importlib.util.spec_from_file_location('_blueprint_batch',path)
            self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        if two_group_policy(cfg) and not dynamic_policy(cfg) and self.identity.get('stronghold_after',2)!=stronghold_after(cfg):
            raise ValueError('Native Stronghold placement differs from the resolved policy')
        self.ffi,self.lib=self.module.ffi,self.module.lib;self.cfg=json.loads(json.dumps(cfg))
        self.policy=self.ffi.new('NBPolicy *')
        self.policy.max_buffer_bytes=256<<20
        if not hasattr(self.policy,'outpost_goal'):raise ValueError('Native blueprint ABI changed; rebuild the extension before using this adapter')
        if two_group_policy(cfg) and not all(hasattr(self.policy,n) for n in ('two_group','floors','flexible_mask')):
            raise ValueError('Two-group policy requires the rebuilt native hard-floor ABI')
        if marine_baseline_policy(cfg) and not hasattr(self.policy,'marine_baseline'):
            raise ValueError('Marine baseline policy requires a rebuilt native extension')
        if dynamic_policy(cfg) and not all(hasattr(self.policy,name) for name in ('dynamic','nether_ids','optional_types')):
            raise ValueError('Dynamic baseline requires a rebuilt native extension')
        self.policy.locked=int(locked_policy(cfg))
        self.policy.river=int(river_policy(cfg))
        self.policy.outpost_goal=cfg['structures']['minimum_counts']['outpost'] if outpost_policy(cfg) else 0
        if two_group_policy(cfg):
            self.policy.two_group=1
            self.policy.floors=[cfg['structures']['hard_floors'].get(n,0) for n in NAMES]
            self.policy.flexible_mask=sum(1<<NAMES.index(n) for n in
                (() if dynamic_v3_policy(cfg) else
                 (('trial_chamber','village','ruined_portal','mineshaft','ancient_city',
                   'desert_pyramid','jungle_temple','shipwreck') if dynamic_policy(cfg) else
                  ('mansion','trial_chamber','village','ruined_portal','mineshaft','ancient_city','fortress','bastion'))))
        if dynamic_policy(cfg):
            self.policy.dynamic=1
            self.policy.density_weights=[cfg['search']['density_weights'][n] for n in
                ('village','trial_chamber','ancient_city','desert_pyramid','jungle_temple','outpost')]
        if hasattr(self.policy,'marine_baseline'):self.policy.marine_baseline=int(marine_baseline_policy(cfg))
        if origin_policy(cfg) and not hasattr(self.policy,'origin'):
            raise ValueError('Origin policy needs the rebuilt native ABI')
        if hasattr(self.policy,'origin'):self.policy.origin=int(origin_policy(cfg))
        if outpost_policy(cfg):self.policy.structure_order=[NAMES.index(n) for n in cfg['search']['structure_order']]
        self.policy.bastion_goal=cfg['structures']['nether_minimum_counts']['bastion']
        self.policy.overworld_half=cfg['deployment']['overworld_side_blocks']//2
        self.policy.nether_half=cfg['deployment']['nether_side_blocks']//2
        self.policy.nether_goal=cfg['structures']['nether_minimum_counts']['fortress']
        self.policy.discovery=native_bounds(cfg['discovery']['overworld_bounds'])
        self.policy.types=[structure_type(n) for n in NAMES]
        self.policy.goals=[cfg['structures']['minimum_counts'][n] for n in NAMES[:10]]
        self.policy.y=cfg['biomes']['sample_y_levels'];self.policy.spacing=64
        self.policy.batch_size=cfg['biomes']['gate_batch_size']
        if hasattr(self.policy, 'cutoff_score'):
            self.policy.cutoff_score = int(cfg.get('search', {}).get('cutoff_score', 0))
        catalog=biome_catalog();ids={row['name']:row['id'] for row in catalog}
        self.families=list(PALETTE)  # Native surface/cave bits must never shift with selection.
        self.required_biome_mask=sum(1<<i for i,f in enumerate(self.families) if f in cfg['biomes']['required_families'])
        if dynamic_v2_policy(cfg):
            if not hasattr(self.policy,'required_biome_mask'):
                raise ValueError('Biome selection requires a rebuilt native extension')
            self.policy.required_biome_mask=self.required_biome_mask
        is_v2=dynamic_v2_policy(cfg)
        for row in catalog:
            self.policy.biome_members[row['id']]=sum(1<<i for i,f in enumerate(self.families) if canonical(row['name']) in (PALETTE[f]|({'frozen_peaks'} if dynamic_policy(cfg) and f=='peaks' else set())))
            name=canonical(row['name'])
            if hasattr(self.policy,'bonus_biome_members'):
                if is_v2:
                    self.policy.bonus_biome_members[row['id']]=(int(name=='cherry_grove')|
                        int(name in ('badlands','wooded_badlands','eroded_badlands'))<<1|
                        int(name=='mushroom_fields')<<2|
                        int(name=='pale_garden')<<3|
                        int(name in ('old_growth_pine_taiga','old_growth_spruce_taiga'))<<4|
                        int(name=='flower_forest')<<5|
                        int(name=='bamboo_jungle')<<6|
                        int(name=='warm_ocean')<<7|
                        int(name=='ice_spikes')<<8|
                        int(name in ('savanna','savanna_plateau','windswept_savanna','shattered_savanna'))<<9)
                else:
                    self.policy.bonus_biome_members[row['id']]=(int(name=='cherry_grove')|
                        int(name in ('badlands','wooded_badlands','eroded_badlands'))<<1|
                        int(name=='mushroom_fields')<<2|
                        int(name=='pale_garden')<<3|
                        int(name=='mangrove_swamp')<<4|
                        int(name=='flower_forest')<<5|
                        int(name=='bamboo_jungle')<<6|
                        ((int(name=='warm_ocean')<<7|int(name=='ice_spikes')<<8|int(name in ('windswept_savanna','shattered_savanna'))<<9) if dynamic_policy(cfg) else 0))
        if dynamic_policy(cfg):self.policy.nether_ids=[ids[name] for name in cfg['biomes']['nether_required']]
        if dynamic_policy(cfg):self.policy.optional_types=[structure_type(n) for n in ('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure')]
        if is_v2:
            self.policy.dynamic_v2=1
            self.policy.river_id=ids['river']
            for sname in ('plains','sunflower_plains','meadow','cherry_grove'):
                self.policy.is_scenic[ids[sname]]=1
        self.policy.dark_id=ids['dark_forest'];self.policy.pale_id=ids['pale_garden']
        self.policy.fixture_surface=[ids[n] for n in ('plains','desert','forest','taiga','jungle',
                                                     'swamp','snowy_plains','dark_forest','jagged_peaks','stony_shore')]
        self.policy.fixture_caves=[ids[n] for n in ('lush_caves','dripstone_caves','deep_dark')]
        self.identity={**self.identity,
            'record_adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'record_sources_sha256':{name:hashlib.sha256((Path(build_record.__code__.co_filename).parent/name).read_bytes()).hexdigest() for name in ('native_records.py','native_encoding.py')},
            'policy_sha256':hashlib.sha256(bytes(self.ffi.buffer(self.policy))).hexdigest(),
            'record_computation_identity':production_identity()}

    def sweep(self,seeds,threads=1,*,complete=False,fixtures=None,retention="full",max_misses=None,fixture_masks=None,fixture_deltas=None,cutoff_score=None):
        is_np = hasattr(seeds, '__array_interface__') or isinstance(seeds, np.ndarray)
        if is_np:
            try:
                buf = memoryview(seeds)
            except (TypeError, ValueError) as exc:
                raise ValueError(f'Invalid buffer object: {exc}')
            if buf.ndim != 1:
                raise ValueError('NumPy seed array must be 1-dimensional')
            if not buf.c_contiguous:
                raise ValueError('NumPy seed array must be C-contiguous')
            if buf.itemsize != 8:
                raise TypeError('NumPy seed array must be int64 or uint64')
            dtype = getattr(seeds, 'dtype', None)
            if dtype is not None:
                if dtype.name not in ('int64', 'uint64'):
                    raise TypeError('NumPy seed array must be int64 or uint64')
                if dtype.byteorder not in ('=', '|', '<' if sys.byteorder == 'little' else '>'):
                    raise ValueError('NumPy seed array must have native byte order')
            if len(buf) != len(seeds) or buf.nbytes != len(seeds) * 8:
                raise ValueError('NumPy seed array buffer length does not match seeds count')
        else:
            seeds=[parse_seed(s) for s in seeds]
        if max_misses is None:max_misses=self.cfg['search']['max_misses'] if retention=='survivors' and two_group_policy(self.cfg) else 0
        if not 1<=len(seeds)<=16384:raise ValueError('Native batches must contain 1–16,384 inputs')
        if isinstance(threads,bool) or not isinstance(threads,int) or not 1<=threads<=36:raise ValueError('Threads must be 1–36')
        if threads>1 and not self.identity['openmp']:raise ValueError('Parallel sweep needs an OpenMP private build')
        if not isinstance(complete,bool):raise ValueError('complete must be boolean')
        if retention not in ('full','survivors'):raise ValueError('Unknown retention mode')
        if isinstance(max_misses,bool) or not isinstance(max_misses,int) or not 0<=max_misses<=25:raise ValueError('max_misses must be 0–25')
        if retention=='full' and max_misses:raise ValueError('max_misses requires survivor retention')
        if retention=='survivors' and complete:raise ValueError('Compact retention and complete oracle sweep are separate paths')
        if fixture_masks is not None and (fixtures is None or len(fixture_masks)!=len(seeds) or any(isinstance(v,bool) or not isinstance(v,int) or not 0<=v<1<<29 for v in fixture_masks)):
            raise ValueError('Invalid synthetic missing masks')
        if fixture_deltas is not None and (fixtures is None or len(fixture_deltas)!=len(seeds) or any(type(v) is not int or not 1<=v<=32 for v in fixture_deltas)):
            raise ValueError('Invalid synthetic deficit depths')
        # Independent call-local policy and buffers; shared adapters never mutate
        # a policy while CFFI releases the GIL for another call.
        policy=self.ffi.new('NBPolicy *');self.ffi.memmove(policy,self.policy,self.ffi.sizeof('NBPolicy'))
        policy.complete=int(complete);policy.retention=int(retention=='survivors');policy.max_misses=(self.cfg['search']['max_misses'] if two_group_policy(self.cfg) and retention=='full' else max_misses)
        if cutoff_score is not None:
            if isinstance(cutoff_score, bool) or not isinstance(cutoff_score, int) or cutoff_score < 0:
                raise ValueError('cutoff_score must be non-negative int')
            if hasattr(policy, 'cutoff_score'):
                policy.cutoff_score = cutoff_score
        if is_np:
            values = self.ffi.from_buffer('uint64_t[]', seeds)
            if len(values) != len(seeds):
                raise ValueError('NumPy seed array buffer length does not match seeds count')
        else:
            values = self.ffi.new('uint64_t[]', [s & MASK64 for s in seeds])
        fixture_values=None
        if fixtures is not None:
            if len(fixtures)!=len(seeds):raise ValueError('One explicit fixture per input required')
            for x,z,missing in fixtures:
                if any(isinstance(v,bool) or not isinstance(v,int) for v in (x,z,missing)) or not -1000000<=x<=1000000 or not -1000000<=z<=1000000 or not -1<=missing<=(33 if dynamic_policy(self.cfg) else 28):
                    raise ValueError('Invalid synthetic fixture')
            fixture_values=self.ffi.new('NBFixture[]',[(*f, fixture_masks[i] if fixture_masks else 0,
                fixture_deltas[i] if fixture_deltas else 1) for i,f in enumerate(fixtures)])
        start=time.perf_counter()
        pointer=(self.lib.nb_sweep(values,len(seeds),policy,threads) if fixtures is None else
                 self.lib.nb_fixture_sweep(values,fixture_values,len(seeds),policy,threads))
        native_seconds=time.perf_counter()-start
        if pointer==self.ffi.NULL:raise RuntimeError('Native batch allocation or policy error')
        batch=Batch(self,pointer,seeds,native_seconds,complete,fixtures is not None,retention,max_misses)
        try:
            if pointer.count!=len(seeds) or pointer.effective_threads!=threads:
                raise RuntimeError('Native batch count or CPU team differs from request')
            if pointer.error:raise RuntimeError(f'Native batch failed with code {pointer.error}; no range may be committed')
            for i in range(pointer.result_count):
                offset=pointer.results[i].input_offset
                if not 0<=offset<len(seeds) or pointer.results[i].seed!=(int(seeds[offset])&MASK64):raise RuntimeError('Native full64 input identity mismatch')
                if pointer.results[i].error:raise RuntimeError(f'Native input {i} failed with code {pointer.results[i].error}; no range may be committed')
            return batch
        except BaseException:
            batch.close();raise


class Batch:
    def __init__(self,prototype,pointer,seeds,seconds,complete,synthetic,retention="full",max_misses=0):
        self.prototype=prototype;self.pointer=pointer;self.seeds=seeds
        self.native_seconds=seconds;self.complete=complete;self.synthetic=synthetic
        self.retention=retention;self.max_misses=max_misses

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def close(self):
        if self.pointer is not None:self.prototype.lib.nb_free(self.pointer);self.pointer=None

    def summary(self):
        if self.pointer is None:raise ValueError('Closed native batch')
        rows=[]
        for i in range(self.pointer.result_count):
            r=self.pointer.results[i];raw_seed=int(self.seeds[r.input_offset])
            seed=raw_seed if raw_seed<(1<<63) else raw_seed-(1<<64)
            rows.append({'seed':str(seed),'anchors':[
                {'stronghold':[a.x,a.z],'count_missing':a.count_missing,
                 'biome_evaluated':bool(a.biome_evaluated),'biome_mask':a.biome_mask,
                 'biome_n':a.biome_n,'score':a.score,
                 'qualification':('PREDICTED' if not a.fatal_missing and a.stronghold_count>=1 and (a.biome_mask & self.prototype.required_biome_mask)==self.prototype.required_biome_mask and
                     int(a.count_missing & self.prototype.policy.flexible_mask).bit_count()<=self.prototype.cfg['search']['max_misses'] else 'PENDING') if two_group_policy(self.prototype.cfg) else
                     ('PREDICTED' if not a.count_missing and (a.biome_mask & self.prototype.required_biome_mask)==self.prototype.required_biome_mask else 'PENDING')}
                for a in [r.anchors[j] for j in range(r.nanchors)]]})
        return rows

    def records(self,start_index=0,*,adapter='direct'):
        if self.pointer is None:raise ValueError('Closed native batch')
        if isinstance(start_index,bool) or not isinstance(start_index,int) or not 0<=start_index<=MASK64 or start_index+len(self.seeds)>MASK64+1:
            raise ValueError('Invalid full64 index range')
        cfg=self.prototype.cfg;records=[]
        if adapter not in ('direct','replay'):raise ValueError('Unknown record adapter')
        if self.retention!='full':raise ValueError('Use retained_records for compact batches')
        for i,seed in enumerate(self.seeds):
            raw_seed=int(seed)
            signed_seed=raw_seed if raw_seed<(1<<63) else raw_seed-(1<<64)
            native=self.pointer.results[i]
            if dynamic_policy(cfg):
                if adapter=='direct':record=build_record(native,start_index+i,signed_seed,cfg)
                else:
                    provider=ReplayProvider(native,self.prototype)
                    record=evaluate_dynamic_seed(start_index+i,signed_seed,cfg,backend_factory=lambda _:provider)
                if len(record['anchors'])!=native.nanchors:raise RuntimeError('Dynamic center count parity failure')
                if native.nanchors:
                    a=record['anchors'][0];c=native.anchors[0]
                    if (a['evaluation_center']!=[c.x,c.z] or
                        a['baseline_score_observed']!=c.score or
                        a['biomes']['sample_count']!=c.biome_n or
                        a['qualification']!='PREDICTED'):
                        raise RuntimeError('Native dynamic center, palette, or score parity failure')
                stage_keys=['stronghold',*[f'structure_{n}' for n in NAMES[:10]],
                    'final_nether_pair','biome_palette_4y','dynamic_center_search','structure_outpost']
                record['stage_seconds']={key:float(native.stage_seconds[k])
                    for k,key in enumerate(stage_keys) if native.stage_seconds[k]}
                record['total_seconds']+=float(native.seconds)
                record['prototype']={'provider':'isolated_native_blueprint_batch',
                    'synthetic':self.synthetic,'evidence':'pinned predictor only; actual generation unverified',
                    'python_role':'record reconstruction and checkpoint persistence'}
                records.append(record)
                continue
            if adapter=='direct':record=build_record(native,start_index+i,signed_seed,cfg)
            else:
                provider=ReplayProvider(native,self.prototype)
                record=evaluate_seed(start_index+i,signed_seed,cfg,backend_factory=lambda _:provider,short_circuit=not self.complete)
            if len(record['anchors'])!=native.nanchors:raise RuntimeError('Native/reconstructed anchor count mismatch')
            for j,a in enumerate(record['anchors']):
                c=native.anchors[j]
                expected=(not c.fatal_missing and c.stronghold_count>=1 and (c.biome_mask & self.prototype.required_biome_mask)==self.prototype.required_biome_mask and
                          (int(c.count_missing & self.prototype.policy.flexible_mask).bit_count()<=cfg['search']['max_misses'])) if two_group_policy(cfg) else (not origin_policy(cfg) or c.stronghold_count>=1) and not c.count_missing and (c.biome_mask & self.prototype.required_biome_mask)==self.prototype.required_biome_mask
                order=[10,11,*[NAMES.index(n) for n in cfg['search']['structure_order']]] if locked_policy(cfg) else range(12)
                pending=['count_'+NAMES[k] for k in order if c.count_missing&(1<<k)]
                if origin_policy(cfg) and c.stronghold_evaluated and c.stronghold_count<1:
                    pending.insert(sum(bool(c.count_missing&(1<<k)) for k in order[:2+stronghold_after(cfg)]),'count_stronghold')
                if c.biome_evaluated:pending+=['biome_'+f for k,f in enumerate(self.prototype.families) if not c.biome_mask&(1<<k)]
                if marine_baseline_policy(cfg):pending+=['count_'+NAMES[k] for k in (3,8) if c.count_missing&(1<<k)]
                if (a['qualification']=='PREDICTED')!=expected or a['pending_reasons']!=pending or a['baseline_score_observed']!=c.score:
                    raise RuntimeError('Native decision/count/biome/ranking parity failure')
                if c.biome_evaluated:
                    if a['biomes']['sample_count']!=c.biome_n:raise RuntimeError('Native biome stop position mismatch')
                    for k,f in enumerate(self.prototype.families):
                        index=c.first_witness[k]
                        if index>=0 and a['biomes']['witnesses'][f]['coordinate']!=[c.biome_xyz[index*3+t] for t in range(3)]:
                            raise RuntimeError('Native first biome witness mismatch')
            keys=['stronghold',*[f'structure_{n}' for n in NAMES[:10]],'final_nether_pair','biome_palette_4y','ranking_inventory','structure_outpost']
            record['stage_seconds']={key:float(native.stage_seconds[k]) for k,key in enumerate(keys) if native.stage_seconds[k]}
            record['total_seconds']+=float(native.seconds)
            record['prototype']={'provider':'isolated_native_blueprint_batch','synthetic':self.synthetic,
                'evidence':'pinned predictor only; actual generation unverified',
                'stage_seconds_scope':'inclusive native evaluator wall time; no replay generation calls',
                'python_role':'record reconstruction and checkpoint persistence'}
            records.append(record)
        return records

    def retained_records(self,start_index=0):
        if self.pointer is None:raise ValueError('Closed native batch')
        if self.retention!='survivors':raise ValueError('Expected compact batch')
        if isinstance(start_index,bool) or not isinstance(start_index,int) or not 0<=start_index<=MASK64 or start_index+len(self.seeds)>MASK64+1:
            raise ValueError('Invalid full64 range')
        records=[]
        cfg=self.prototype.cfg
        if two_group_policy(cfg):
            cfg=dict(cfg);cfg['search']=dict(cfg.get('search',{}));cfg['search']['max_misses']=self.max_misses
        for i in range(self.pointer.result_count):
            native=self.pointer.results[i];offset=native.input_offset
            raw_seed=int(self.seeds[offset])
            signed_seed=raw_seed if raw_seed<(1<<63) else raw_seed-(1<<64)
            if dynamic_policy(cfg):
                provider=ReplayProvider(native,self.prototype)
                record=evaluate_dynamic_seed(start_index+offset,signed_seed,cfg,
                    backend_factory=lambda _:provider)
                if len(record['anchors'])!=1 or record['anchors'][0]['baseline_score_observed']!=native.anchors[0].score:
                    raise RuntimeError('Native dynamic retained-record parity failure')
                stage_keys=['stronghold',*[f'structure_{n}' for n in NAMES[:10]],
                    'final_nether_pair','biome_palette_4y','dynamic_center_search','structure_outpost']
                record['stage_seconds']={key:float(native.stage_seconds[k])
                    for k,key in enumerate(stage_keys) if native.stage_seconds[k]}
                record['total_seconds']+=float(native.seconds)
            else:record=build_record(native,start_index+offset,signed_seed,cfg)
            for j,a in enumerate(record['anchors']):
                c=native.anchors[j]
                misses=int(c.count_missing & self.prototype.policy.flexible_mask).bit_count() if two_group_policy(cfg) else int(c.count_missing).bit_count()+13-int(c.biome_mask).bit_count()
                if (not c.biome_evaluated or misses>self.max_misses or
                    (two_group_policy(cfg) and (c.fatal_missing or (c.biome_mask & self.prototype.required_biome_mask)!=self.prototype.required_biome_mask)) or
                    (not two_group_policy(cfg) and misses!=len(a['pending_reasons'])) or
                    (origin_policy(cfg) and c.stronghold_count<1)):
                    raise RuntimeError('Native retention decision parity failure')
                a['retention']={'classification':'PREDICTED_SURVIVOR' if two_group_policy(cfg) or not misses else 'NEAR_MISS',
                    'unmet_requirements':misses,'allowed_unmet_requirements':self.max_misses,
                    'requirements_total':baseline_requirements(self.prototype.cfg),
                    'scope':('14 structure categories, 13 Overworld biome families and 5 Nether biome families; no terrain gate' if dynamic_policy(self.prototype.cfg) else f'{baseline_requirements(self.prototype.cfg)-13} structure-count and 13 biome-family predictor requirements; marine starts required, terrain unassessed' if marine_baseline_policy(self.prototype.cfg) else f'{baseline_requirements(self.prototype.cfg)-13} core structure-count and 13 biome-family requirements; marine deferred' if locked_policy(self.prototype.cfg) else '12 structure-count and 13 biome-family predictor requirements at this anchor')}
            if self.synthetic:record['prototype']={'synthetic':True,'provider':'explicit_native_retention_fixture','evidence':'synthetic provider fixture; not a natural-world discovery'}
            record['retention']={'mode':'survivors','max_misses':self.max_misses,
                                 'discarded_anchor_records_not_retained':True}
            records.append(record)
        return records

    def retention_receipt(self):
        if self.pointer is None or self.retention!='survivors':raise ValueError('Expected open compact batch')
        # C allocated this zero-initialized fixed-width buffer. Hashing visits no
        # per-input Python dictionaries and covers every input and decision.
        raw=self.prototype.ffi.buffer(self.pointer.verdicts,self.pointer.count*self.prototype.ffi.sizeof('NBVerdict'))
        digest=hashlib.sha256(raw).hexdigest()
        # Totals from retained records; full anchor count is summed in C below.
        return {'version':'native-retention-receipt-v1','inputs':self.pointer.count,
                'input_decisions_sha256':digest,'retained_inputs':self.pointer.result_count,
                'retained_anchors':int(self.pointer.retained_anchors),
                'discovered_anchors':int(self.pointer.discovered_anchors)}


class ReplayProvider:
    """Return only evidence already calculated by C; unknown queries fail closed."""
    def __init__(self,result,prototype):
        self.native_work={};self.discovery=self.points(result.discovery)
        self.dynamic_center=(int(result.anchors[0].x),int(result.anchors[0].z)) if dynamic_policy(prototype.cfg) and result.nanchors else None
        self.dynamic_no_anchor=bool(dynamic_policy(prototype.cfg) and not result.nanchors)
        self.queries={};self.ids={};self.nether_ids={};self.pairs={};self.igloo_basements=set()
        for j in range(result.nanchors):
            a=result.anchors[j];h=prototype.policy.overworld_half;nh=prototype.policy.nether_half
            bounds=(a.x-h,a.z-h,a.x+h-1,a.z+h-1)
            if dynamic_policy(prototype.cfg):
                from seed_search.realm.dynamic import nether_bounds
                bb=nether_bounds((a.x,a.z),nh);nb=native_bounds(bb)
            else:
                nx=-((-a.x)//8);nz=-((-a.z)//8);nb=(nx-nh,nz-nh,nx+nh-1,nz+nh-1)
            for k,name in enumerate(NAMES):
                o=a.observations[k]
                if not o.evaluated:continue
                b=nb if k in (10,11) else bounds
                self.queries[(name,b)]={'raw':self.points(o.raw),'viable':self.points(o.viable),
                                       'floor':self.points(o.floor),'full':bool(o.full)}
                if name=='mansion':
                    for q,(x,z) in enumerate(self.points(o.viable)):self.ids[(x,63,z)]=int(o.mansion_ids[q])
            if a.observations[10].evaluated:
                self.pairs[nb]={n:(self.queries[(n,nb)]['raw'],self.queries[(n,nb)]['viable']) for n in ('fortress','bastion')}
            for q in range(a.biome_n):
                self.ids[tuple(int(a.biome_xyz[3*q+t]) for t in range(3))]=int(a.biome_ids[q])
            if dynamic_policy(prototype.cfg):
                for k,name in enumerate(('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure')):
                    o=a.optional[k]
                    self.queries[(name,bounds)]={'raw':self.points(o.raw),'viable':self.points(o.viable),'floor':[],'full':True}
                    if name=='igloo':self.igloo_basements.update(self.points(o.viable))
                for q in range(a.nether_biome_n):
                    self.nether_ids[tuple(int(a.nether_biome_xyz[3*q+t]) for t in range(3))]=int(a.nether_biome_ids[q])
                if hasattr(a,'bastion_count'):
                    self.bastion_variants={(int(a.bastion_coords[2*b_idx]),int(a.bastion_coords[2*b_idx+1])):int(a.bastion_variants[b_idx])
                                           for b_idx in range(a.bastion_count)}
                else:self.bastion_variants={}
                if hasattr(a,'scenic_bonus'):
                    self.scenic_bonus=int(a.scenic_bonus)
                    self.scenic_witness=(int(a.scenic_witness[0]),int(a.scenic_witness[1])) if a.scenic_bonus else None
                    self.river_witness=(int(a.river_witness[0]),int(a.river_witness[1])) if a.scenic_bonus else None
                if hasattr(a,'village_spread_bonus'):
                    self.village_spread_bonus=int(a.village_spread_bonus)
                    self.village_triple=tuple((int(a.village_triple[2*i]),int(a.village_triple[2*i+1])) for i in range(3)) if a.village_spread_bonus else None
                if hasattr(a,'treasure_bastion'):
                    self.treasure_bastion=int(a.treasure_bastion)
        self.discovery_bounds=native_bounds(prototype.cfg['discovery']['overworld_bounds'])

    @staticmethod
    def points(points):return [(int(points.xz[2*i]),int(points.xz[2*i+1])) for i in range(points.n)]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def structure_pair(self,name,bounds):
        if name=='stronghold':
            if tuple(bounds)!=self.discovery_bounds:raise RuntimeError('Uncomputed discovery bounds')
            return self.discovery,self.discovery
        q=self.queries[(name,tuple(bounds))]
        if not q['full']:raise RuntimeError('Complete inventory was not calculated in native code')
        return q['raw'],q['viable']
    def structure_count(self,name,bounds,minimum):
        q=self.queries[(name,tuple(bounds))]
        return q['floor']
    def igloo_basement(self,x,z):return (x,z) in self.igloo_basements
    def bastion_variant(self,x,z):return self.bastion_variants.get((x,z),-1)
    def nether_structure_pairs(self,bounds):return self.pairs[tuple(bounds)]
    def biome_points(self,points,dimension=0):
        source=self.nether_ids if dimension==-1 else self.ids
        return np.array([source[tuple(map(int,p))] for p in points],dtype=np.int32)


def persist_scan(prototype,run,count,*,run_key=0,threads=18,batch_size=256,resume=False):
    """Bounded experimental scan using the complete existing RealmStore schema."""
    if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=100000:raise ValueError('Pilot count must be 1–100,000')
    if not 1<=batch_size<=16384:raise ValueError('Invalid native batch size')
    cfg=json.loads(json.dumps(prototype.cfg));cfg['search']['run_key']=str(run_key)
    identity={'config':cfg,'prototype':prototype.identity,'count':count,'evidence_schema':'realm-full-records-v1'}
    wall=time.perf_counter();native=decode=persist=0.;batches=0
    with RealmStore(run,identity=identity,resume=resume) as store:
        store.configure_range(0,count,batch_size);store.recover_assignments()
        while True:
            assigned=store.claim_range('native-prototype')
            if assigned is None:break
            start,end=assigned;seeds=[seed_from_index(i,run_key) for i in range(start,end)]
            with prototype.sweep(seeds,threads) as batch:
                native+=batch.native_seconds;t=time.perf_counter();records=batch.records(start)
                decode+=time.perf_counter()-t
            for i,record in enumerate(records):
                if record['seed']!=str(seeds[i]) or record['index']!=start+i:raise RuntimeError('Batch coverage identity mismatch')
            t=time.perf_counter();store.complete_range(start,end,records);persist+=time.perf_counter()-t;batches+=1
        status=store.status()
        if status['completed_seeds']!=count:raise RuntimeError('Incomplete persisted native pilot')
    seconds=time.perf_counter()-wall
    return {'count':count,'wall_seconds':seconds,'input_seeds_per_second':count/seconds,
            'native_seconds':native,'reconstruction_seconds':decode,'persistence_seconds':persist,
            'batches':batches,'threads':threads,'batch_size':batch_size,'status':status,
            'scope':'native baseline + complete Python evidence reconstruction + RealmStore FULL SQLite; no terrain/BDS',
            'resume_note':'A resumed completed pilot does not measure new-input throughput'}


def persist_pipeline(prototype,run,count,*,run_key=0,threads=30,batch_size=1024,
                     resume=False,encoded=True,max_prepared_bytes=256<<20,
                     stop_after=None,progress=None,start_index=0,identity=None,
                     allow_prediction_scale=False,production=False,inflight=3,retention="full",max_misses=0,
                     prepare_on_writer=False):
    """Bounded native producer, record preparer and connection-owning writer.

    CFFI releases the GIL during generation. Record preparation runs on its own thread; SQLite stays on
    the writer thread. No initialized OpenMP state is forked. Every outstanding
    batch has a native allocation cap. Exceptions close all buffers, stop new
    claims, and recover uncommitted leases. No fallback changes implementation.
    """
    from concurrent.futures import ThreadPoolExecutor
    from collections import deque,Counter
    from seed_search.realm.native_encoding import fast_records
    from seed_search.realm.runner import (_scan_lock,_numerical_threads,_scale_gate,
                                         _seed,_validate_batch_seeds,process_tree_resources)
    from seed_search.realm.resources import disk_policy,disk_status
    from seed_search.realm.config import memory_budget_gib
    if isinstance(count,bool) or not isinstance(count,int) or not 0<=count<=MASK64+1:
        raise ValueError('Invalid finite native pipeline count')
    if count>100000 and not (production and allow_prediction_scale):
        raise ValueError('Native ranges above 100,000 require explicit production prediction scale')
    if isinstance(batch_size,bool) or not isinstance(batch_size,int) or not 1<=batch_size<=16384:
        raise ValueError('Invalid native batch size')
    if isinstance(threads,bool) or not isinstance(threads,int) or not 1<=threads<=34:
        raise ValueError('Native pipeline reserves two of 36 CPU slots for preparation/writing')
    if isinstance(inflight,bool) or not isinstance(inflight,int) or not 2<=inflight<=3:
        raise ValueError('Pipeline supports two or three bounded in-flight batches')
    if isinstance(max_prepared_bytes,bool) or not isinstance(max_prepared_bytes,int) or max_prepared_bytes<1:
        raise ValueError('Invalid prepared byte budget')
    if type(prepare_on_writer) is not bool:raise ValueError('Invalid preparation scheduling mode')
    if isinstance(start_index,bool) or not isinstance(start_index,int) or not 0<=start_index<=MASK64+1 or start_index+count>MASK64+1:
        raise ValueError('Invalid full64 range')
    if stop_after is not None and (isinstance(stop_after,bool) or not isinstance(stop_after,int) or stop_after<0):
        raise ValueError('Invalid stop_after')
    if retention not in ('full','survivors'):raise ValueError('Unknown retention mode')
    if isinstance(max_misses,bool) or not isinstance(max_misses,int) or not 0<=max_misses<=25 or (retention=='full' and max_misses):raise ValueError('Invalid retention threshold')
    cfg=json.loads(json.dumps(prototype.cfg));cfg['search']['run_key']=str(run_key)
    identity=identity or {'config':cfg,'prototype':prototype.identity,'count':count,'start_index':start_index,
                         'evidence_schema':'realm-full-records-v1','adapter':'owned-native-pipeline-v1'}
    identity={**identity,'retention':{'mode':retention,'max_misses':max_misses}}
    if production:_scale_gate(cfg,run,count,allow_prediction_scale)
    os.environ.setdefault("KMP_BLOCKTIME", "0")
    limits=disk_policy(cfg['search'],retention=retention);_,ceiling,reserve=memory_budget_gib(cfg['search'])
    wall=time.perf_counter();cpu=time.process_time();service=Counter();latencies=deque(maxlen=4096);pending=deque()
    peak=0;batches=committed=dispatched=0;failure=None;interrupted=False;max_pending=0;max_payload=0
    pool=None;preparer=None;native_futures=set();last_monitor=0.;last_progress=0.
    run_key_val=cfg['search'].get('run_key', 0)
    try:run_key_int=int(run_key_val)
    except (ValueError,TypeError):run_key_int=int.from_bytes(hashlib.sha256(str(run_key_val).encode()).digest()[:8], 'big')
    use_np_permutation=(cfg['search'].get('sequence', 'permutation') == 'permutation')
    def compute(first,end):
        before=time.perf_counter()
        seeds=seeds_np(first,end,run_key_int) if use_np_permutation else [_seed(i,cfg['search']) for i in range(first,end)]
        seed_seconds=time.perf_counter()-before
        return prototype.sweep(seeds,threads,**({'retention':retention,'max_misses':max_misses} if retention=='survivors' else {})),seed_seconds
    def prepare(native_future,first,end,store):
        batch,seed_seconds=native_future.result()
        with batch:
            before=time.perf_counter()
            records=batch.retained_records(first) if retention=='survivors' else (
                fast_records(batch,first,store) if encoded and not origin_policy(cfg) else batch.records(first))
            record_seconds=time.perf_counter()-before
            if retention=='full':_validate_batch_seeds(first,end,records,cfg['search'])
            else:
                for record in records:_validate_batch_seeds(record['index'],record['index']+1,[record],cfg['search'])
            before=time.perf_counter();prepared=(store.prepare_retained_range(first,end,records,batch.retention_receipt()) if retention=='survivors' else store.prepare_range(first,end,records))
            prepare_seconds=time.perf_counter()-before
            owned_estimate=prepared.payload_bytes*2+sum(len(r)*64 for r in prepared.seed_rows+prepared.candidate_rows)
            if owned_estimate>max_prepared_bytes:
                raise RuntimeError('Prepared batch exceeds owned byte budget; retry with smaller batches')
            return prepared,{'seed_preparation_seconds':seed_seconds,'native_seconds':batch.native_seconds,
                             'record_seconds':record_seconds,'preparation_wall_seconds':prepare_seconds},owned_estimate
    def submit(store):
        nonlocal dispatched,max_pending
        budget=None if stop_after is None else stop_after-dispatched
        if budget is not None and budget<=0:return False
        assigned=store.claim_range('native-pipeline',max_seeds=batch_size if budget is None else min(batch_size,budget))
        if assigned is None:return False
        first,end=assigned
        attempt=store.db.execute('SELECT attempts FROM ranges WHERE start=?',(f'{first:020d}',)).fetchone()[0]
        native_future=pool.submit(compute,first,end);native_futures.add(native_future)
        future=None if prepare_on_writer else preparer.submit(prepare,native_future,first,end,store)
        pending.append((first,end,attempt,future,time.perf_counter(),native_future))
        dispatched+=end-first;max_pending=max(max_pending,len(pending));return True
    with _scan_lock(run),_numerical_threads(),RealmStore(run,identity=identity,resume=resume) as store:
        store.configure_range(start_index,start_index+count,batch_size);store.recover_assignments()
        completed=store.get_state('completed_seeds')
        initial_disk=disk_status(store.run,limits,remaining_seeds=count-completed,
            completed_seeds=completed,previous_sample=store.get_state('workspace_disk'))
        store.set_state('workspace_disk',initial_disk)
        def check_capacity(additional_bytes):
            completed=store.get_state('completed_seeds')
            return disk_status(store.run,limits,additional_bytes=additional_bytes,
                completed_seeds=completed,remaining_seeds=count-completed)
        pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='native-blueprint')
        preparer=ThreadPoolExecutor(max_workers=1,thread_name_prefix='native-records')
        try:
            while len(pending)<inflight and submit(store):pass
            while pending:
                first,end,attempt,future,queued,native_future=pending.popleft()
                before=time.perf_counter()
                if future is None:
                    native_future.result()
                    service['queue_wait_seconds']+=time.perf_counter()-before
                    prepared,stage_times,owned_estimate=prepare(native_future,first,end,store)
                else:
                    prepared,stage_times,owned_estimate=future.result()
                    service['queue_wait_seconds']+=time.perf_counter()-before
                service.update(stage_times)
                max_payload=max(max_payload,owned_estimate)
                before=time.perf_counter()
                store.complete_prepared(prepared,lease=('native-pipeline',attempt),
                    capacity_check=check_capacity)
                service['writer_wall_seconds']+=time.perf_counter()-before
                service.update(store.last_range_timings)
                batches+=1;committed+=end-first;latencies.append(time.perf_counter()-queued)
                del prepared
                native_futures.discard(native_future)
                while len(pending)<inflight and submit(store):pass
                now=time.perf_counter()
                if now-last_monitor>=1:
                    resources=process_tree_resources() or {}
                    if not resources.get('available'):raise RuntimeError('Process-tree monitoring unavailable; checkpoint retained')
                    peak=max(peak,resources['rss_bytes']);last_monitor=now
                    if resources['rss_bytes']+reserve*(1<<30)>ceiling*(1<<30):
                        raise RuntimeError('Process-tree RSS plus reserve exceeded memory ceiling')
                if progress is not None and now-last_progress>=10:
                    progress(store.status());last_progress=now
                while len(pending)<inflight and submit(store):pass
        except KeyboardInterrupt:
            interrupted=True
        except BaseException as exc:
            failure=exc
        finally:
            before=time.perf_counter()
            # Running C calls are finite/capped and cannot be killed safely;
            # cancellation prevents queued starts, then closes every owned result.
            for first,end,attempt,future,queued,native_future in pending:
                if future is not None:future.cancel()
            for native_future in native_futures:native_future.cancel()
            pool.shutdown(wait=True,cancel_futures=True)
            preparer.shutdown(wait=True,cancel_futures=True)
            for native_future in native_futures:
                if not native_future.cancelled():
                    try:native_future.result()[0].close()
                    except BaseException:pass
            service['shutdown_seconds']=time.perf_counter()-before
            store.recover_assignments()
            store.set_state('native_pipeline',{'threads':threads,'cpu_slots':threads+2,'batch_size':batch_size,
                'max_outstanding_batches':max_pending,'max_prepared_owned_estimate_bytes':max_payload,
                'max_native_buffer_bytes_per_batch':int(prototype.policy.max_buffer_bytes),
                'max_prepared_bytes':max_prepared_bytes,'service_seconds':dict(service),'batches':batches,
                'prepare_on_writer':prepare_on_writer,
                'retention':retention,'max_misses':max_misses,'invocation_completed_seeds':committed,'interrupted':interrupted,
                'error':str(failure) if failure else None})
            status=store.status()
        if failure is not None:raise failure
    seconds=time.perf_counter()-wall
    return {'count':count,'newly_committed':committed,'wall_seconds':seconds,
            'input_seeds_per_second':committed/seconds,'process_cpu_seconds':time.process_time()-cpu,
            **dict(service),'batches':batches,'threads':threads,'batch_size':batch_size,
            'batch_latencies_seconds':list(latencies),'batch_latency_sample_scope':'last 4096 completed batches',
            'max_outstanding_batches':max_pending,
            'max_prepared_owned_estimate_bytes':max_payload,'peak_process_tree_rss_bytes':peak,
            'status':status,'interrupted':interrupted,'encoded':encoded,'retention':retention,'max_misses':max_misses,
            'scope':('complete baseline evidence and FULL SQLite' if retention=='full' else 'C-filtered survivor/near-miss evidence and FULL SQLite range checkpoints')+', startup/drain/close included; no terrain/BDS'}



def run_native_scan(cfg,output,count,start_index=0,resume=False,identity=None,*,native_build=None,
                    native_threads=16,native_batch_size=4096,stop_after=None,progress=None,
                    allow_prediction_scale=False,retention="full",max_misses=None):
    """Production opt-in; unsupported profiles fail before any input publication."""
    validate_config(cfg)
    if max_misses is None:max_misses=cfg['search']['max_misses'] if retention=='survivors' and two_group_policy(cfg) else 0
    if two_group_policy(cfg) and retention=='survivors' and max_misses!=cfg['search']['max_misses']:
        raise ValueError('V2 survivor budget must match the resolved config; set search.max_misses in the policy')
    if isinstance(count,bool) or not isinstance(count,int) or not 0<=count<=MASK64+1 or isinstance(start_index,bool) or not isinstance(start_index,int) or not 0<=start_index<=MASK64+1 or start_index+count>MASK64+1:raise ValueError('Invalid bounded full64 range')
    if count>100000 and not allow_prediction_scale:
        raise ValueError('Native ranges above 100,000 require explicit prediction scale')
    search=cfg['search']
    if search.get('numeric_threads_per_worker',1)!=1:raise ValueError('Numerical threads must equal one')
    if search.get('sequence')=='manifest':
        values=search.get('manifest_seeds')
        if (not isinstance(values,list) or not 1<=len(values)<=10000 or
            any(not isinstance(v,str) or str(parse_seed(v))!=v for v in values) or
            len(set(values))!=len(values) or start_index+count>len(values)):
            raise ValueError('Invalid or insufficient canonical full64 seed manifest')
    prototype=Prototype(native_build,cfg)
    if native_threads>1 and not prototype.identity['openmp']:raise ValueError('Native threads above one need an explicitly built OpenMP extension')
    ident=dict(identity or {'config':cfg,'count':count,'start_index':start_index,'backend':production_identity()})
    ident.update(execution='native',native=prototype.identity,
                 native_build=str(Path(native_build).resolve()) if native_build is not None else None,
                 evaluator='seed_search.realm.native_batch:run_native_scan')
    result=persist_pipeline(prototype,output,count,run_key=search['run_key'],threads=native_threads,
        batch_size=native_batch_size,resume=resume,stop_after=stop_after,progress=progress,
        start_index=start_index,identity=ident,allow_prediction_scale=allow_prediction_scale,production=True,retention=retention,max_misses=max_misses)
    status=result['status'];status['interrupted']=result['interrupted']
    status['execution']={'kind':'native','threads':native_threads,'batch_size':native_batch_size,
                         'newly_committed':result['newly_committed'],'wall_seconds':result['wall_seconds'],
                         'batch_latency_sample_scope':result['batch_latency_sample_scope'],
                         'batch_latency_p50_seconds':statistics.median(result['batch_latencies_seconds']) if result['batch_latencies_seconds'] else None,
                         'batch_latency_p95_seconds':sorted(result['batch_latencies_seconds'])[min(len(result['batch_latencies_seconds'])-1,int(.95*len(result['batch_latencies_seconds'])))] if result['batch_latencies_seconds'] else None,
                         'retention':retention,'max_misses':max_misses,
                         ('durably_persisted_inputs_per_second' if retention=='full' else 'checkpointed_scanned_inputs_per_second'):result['input_seeds_per_second']}
    return status

```

---

<a id="file-11"></a>
### File 11: `scripts/pilot_v3_2048.py`
> **Purpose:** Production Sweep Runner with Dynamic Top-50 Cutoff Feedback Loop  
> **Length:** 245 lines | **Language:** PYTHON

```python
#!/usr/bin/env python3
"""Pilot sweep runner for dynamic-envelope-2048-v3.

Executes high-throughput multi-threaded sweeps using the native OpenMP prototype,
validates surviving candidates against Python evaluate_dynamic_seed, tracks the
Top-50 candidates in a bounded min-heap, and outputs comprehensive funnel,
throughput, and candidate breakdown reports.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import numpy as np

from seed_search.realm.blueprint import evaluate_dynamic_seed
from seed_search.realm.config import dynamic_v3_blueprint_config
from seed_search.realm.native_batch import Prototype, semantic_record, seeds_np
from seed_search.realm.top_tracker import Top50Tracker
from seed_search.seeds import seed_from_index


def extract_summary(rec: Dict[str, Any]) -> Dict[str, Any]:
    anchor = rec["anchors"][0]
    req = anchor.get("required_structures", {})
    nether = anchor.get("required_nether_structures", {})
    opt = anchor.get("optional_structures", {})
    return {
        "seed": rec["seed"],
        "score": anchor.get("baseline_score_observed", 0),
        "center": anchor.get("evaluation_center", [0, 0]),
        "radial_key": anchor.get("radial_key", 0),
        "orig_dist_sq": anchor.get("origin_distance_squared", 0),
        "structures": {
            "stronghold": len(req.get("stronghold", {}).get("predicted_viable", [])),
            "mansion": len(req.get("mansion", {}).get("predicted_viable", [])),
            "monument": len(req.get("monument", {}).get("predicted_viable", [])),
            "village": len(req.get("village", {}).get("predicted_viable", [])),
            "trial_chamber": len(req.get("trial_chamber", {}).get("predicted_viable", [])),
            "ancient_city": len(req.get("ancient_city", {}).get("predicted_viable", [])),
            "desert_pyramid": len(req.get("desert_pyramid", {}).get("predicted_viable", [])),
            "jungle_temple": len(req.get("jungle_temple", {}).get("predicted_viable", [])),
            "outpost": len(req.get("outpost", {}).get("predicted_viable", [])),
            "ruined_portal": len(req.get("ruined_portal", {}).get("predicted_viable", [])),
            "shipwreck": len(req.get("shipwreck", {}).get("predicted_viable", [])),
            "mineshaft": len(req.get("mineshaft", {}).get("predicted_viable", [])),
            "fortress": len(nether.get("fortress", {}).get("predicted_viable", [])),
            "bastion": len(nether.get("bastion", {}).get("predicted_viable", [])),
            "swamp_hut": len(opt.get("swamp_hut", {}).get("predicted_viable", [])),
            "igloo": len(opt.get("igloo", {}).get("predicted_viable", [])),
            "trail_ruins": len(opt.get("trail_ruins", {}).get("predicted_viable", [])),
            "ocean_ruin": len(opt.get("ocean_ruin", {}).get("predicted_viable", [])),
            "buried_treasure": len(opt.get("buried_treasure", {}).get("predicted_viable", [])),
        },
        "bonuses": {
            "scenic_river": anchor.get("scenic_bonus", 0),
            "village_spread": anchor.get("village_spread_bonus", 0),
            "treasure_bastion": anchor.get("treasure_bastion", 0),
            "hub": anchor.get("hub_bonus", 0),
            "nether_core": anchor.get("nether_core_bonus", 0),
        },
    }


def run_pilot(
    count: int = 100_000,
    start_index: int = 0,
    run_key: int = 2026101501,
    threads: int = 34,
    batch_size: int = 16384,
    top_n: int = 50,
    output_dir: Path | None = None,
) -> Dict[str, Any]:
    print("=" * 78)
    print("MINECRAFT SEED SEARCHER - PILOT RUNNER (dynamic-envelope-2048-v3)")
    print(f"Target count: {count:,} seeds | Start index: {start_index:,}")
    print(f"Run key: {run_key} | Threads: {threads} | Batch size: {batch_size:,}")
    print("=" * 78)

    cfg = dynamic_v3_blueprint_config()
    cfg["search"]["run_key"] = str(run_key)
    prototype = Prototype(None, cfg)

    if not prototype.identity.get("openmp"):
        print("WARNING: OpenMP is disabled in Prototype; run will be single-threaded.")
    else:
        print(f"OpenMP enabled: {prototype.identity.get('runtime')}")

    tracker = Top50Tracker(capacity=top_n)

    total_scanned = 0
    total_retained_candidates = 0
    total_native_seconds = 0.0
    start_wall = time.perf_counter()

    num_batches = (count + batch_size - 1) // batch_size
    print(f"\nStarting execution across {num_batches} batches...")

    for b_idx in range(num_batches):
        b_start = start_index + b_idx * batch_size
        b_count = min(batch_size, count - (b_idx * batch_size))
        b_end = b_start + b_count

        t_batch_0 = time.perf_counter()
        # Fast numpy seed generator
        seeds_arr = seeds_np(b_start, b_end, run_key)

        cutoff = tracker.cutoff_score() or 0
        with prototype.sweep(seeds_arr, threads=threads, retention="survivors", cutoff_score=cutoff) as batch:
            total_native_seconds += batch.native_seconds
            t_batch_1 = time.perf_counter()

            retained_list = list(batch.retained_records(b_start))
            batch_retained = len(retained_list)
            total_retained_candidates += batch_retained

            # Process any retained survivors
            for rec in retained_list:
                sem = semantic_record(rec)
                admitted = tracker.observe(sem)
                info = extract_summary(sem)
                str_counts = info["structures"]
                if admitted:
                    print(
                        f"  [NEW TOP CANDIDATE] Seed: {info['seed']} | Score: {info['score']} | "
                        f"Center: ({info['center'][0]}, {info['center'][1]}) | "
                        f"AC={str_counts['ancient_city']} TC={str_counts['trial_chamber']} "
                        f"Vil={str_counts['village']} Mon={str_counts['monument']} Man={str_counts['mansion']} "
                        f"Fort={str_counts['fortress']} Bast={str_counts['bastion']} "
                        f"SH={str_counts['stronghold']} Out={str_counts['outpost']}"
                    )

        total_scanned += b_count
        elapsed_so_far = time.perf_counter() - start_wall
        rate_so_far = total_scanned / elapsed_so_far
        batch_rate = b_count / (t_batch_1 - t_batch_0)

        if (b_idx + 1) % max(1, num_batches // 10) == 0 or b_idx == num_batches - 1:
            cutoff = tracker.cutoff_score()
            cutoff_str = str(cutoff) if cutoff is not None else "None (<50)"
            print(
                f"Batch {b_idx + 1:3d}/{num_batches:3d} ({total_scanned:8,d}/{count:8,d} seeds) | "
                f"Batch rate: {batch_rate:8,.1f} s/s | Overall rate: {rate_so_far:8,.1f} s/s | "
                f"Survivors: {total_retained_candidates:3d} | Cutoff: {cutoff_str}"
            )

    total_wall_seconds = time.perf_counter() - start_wall
    overall_throughput = total_scanned / total_wall_seconds if total_wall_seconds > 0 else 0.0

    print("\n" + "=" * 78)
    print("PILOT SWEEP COMPLETE")
    print(f"Total Scanned:         {total_scanned:,} seeds")
    print(f"Total Wall Time:       {total_wall_seconds:.2f} seconds")
    print(f"Native Kernel Time:    {total_native_seconds:.2f} seconds")
    print(f"Overall Throughput:    {overall_throughput:,.1f} seeds/second")
    print(
        f"Candidate Survivors:   {total_retained_candidates:,} "
        f"(Pass rate: {total_retained_candidates/max(1, total_scanned):.6%})"
    )
    print(f"Top-{top_n} Score Cutoff:   {tracker.cutoff_score()}")
    print("=" * 78)

    top_candidates = tracker.top_records()
    if top_candidates:
        print(f"\nTop {len(top_candidates)} Candidates Ranked:")
        for idx, rec in enumerate(top_candidates[:15], 1):
            info = extract_summary(rec)
            sc = info["structures"]
            bn = info["bonuses"]
            print(
                f"#{idx:2d} | Seed: {info['seed']:<20} | Score: {info['score']:3d} | "
                f"Center: ({info['center'][0]:5d}, {info['center'][1]:5d}) | Dist^2: {info['orig_dist_sq']:<10d} | "
                f"AC={sc['ancient_city']} TC={sc['trial_chamber']} Vil={sc['village']} "
                f"Mon={sc['monument']} Man={sc['mansion']} Fort={sc['fortress']} Bast={sc['bastion']} "
                f"SH={sc['stronghold']} Out={sc['outpost']} DP={sc['desert_pyramid']} JT={sc['jungle_temple']} "
                f"Ship={sc['shipwreck']} RP={sc['ruined_portal']} Mine={sc['mineshaft']} | "
                f"Scenic={bn['scenic_river']} Spread={bn['village_spread']} TBast={bn['treasure_bastion']} NCore={bn['nether_core']}"
            )

    result_data = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "config_contract": cfg.get("contract"),
        "realm_size": "2048x2048",
        "nether_size": "1024x1024",
        "macro_envelope": "4000x4000",
        "total_scanned": total_scanned,
        "total_wall_seconds": total_wall_seconds,
        "total_native_seconds": total_native_seconds,
        "throughput_seeds_per_sec": overall_throughput,
        "total_survivors": total_retained_candidates,
        "survivor_pass_rate": total_retained_candidates / max(1, total_scanned),
        "cutoff_score": tracker.cutoff_score(),
        "top_candidates_count": len(top_candidates),
        "top_candidates": [extract_summary(r) for r in top_candidates],
    }

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "pilot_summary.json"
        tracker.save_to_json(str(output_dir / "top50_candidates.json"))
        tracker.save_to_sqlite(str(output_dir / "top50_candidates.db"))
        with open(json_path, "w") as f:
            json.dump(result_data, f, indent=2)
        print(f"\nArtifacts saved to {output_dir}")

    return result_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=100_000, help="Number of seeds to scan")
    parser.add_argument("--start-index", type=int, default=0, help="Starting index")
    parser.add_argument("--run-key", type=int, default=2026101501, help="Seed generator run key")
    parser.add_argument("--threads", type=int, default=34, help="OpenMP threads")
    parser.add_argument("--batch-size", type=int, default=16384, help="Native batch chunk size")
    parser.add_argument("--top-n", type=int, default=50, help="Number of top candidates to keep")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory to save summary")
    args = parser.parse_args()

    run_pilot(
        count=args.count,
        start_index=args.start_index,
        run_key=args.run_key,
        threads=args.threads,
        batch_size=args.batch_size,
        top_n=args.top_n,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()

```

---

<a id="file-12"></a>
### File 12: `tests/test_dynamic_v3_2048.py`
> **Purpose:** Core Dynamic-Envelope-2048-v3 Verification Suite (17 Tests)  
> **Length:** 678 lines | **Language:** PYTHON

```python
"""Comprehensive tests for dynamic-envelope-2048-v3 realm geometry and center rules."""
import pytest
from seed_search.realm.config import (
    DYNAMIC_V3_REVISION,
    dynamic_v3_blueprint_config,
    validate_blueprint_config,
    validate_config,
    dynamic_v3_policy,
)
from seed_search.realm.spawn import classify_spawn
from seed_search.realm.native_batch import Prototype


def test_v3_config_geometry():
    cfg = dynamic_v3_blueprint_config()
    validate_config(cfg)
    validate_blueprint_config(cfg)
    assert cfg['screening_revision'] == DYNAMIC_V3_REVISION
    assert dynamic_v3_policy(cfg) is True
    assert cfg['deployment']['overworld_side_blocks'] == 2048
    assert cfg['deployment']['nether_side_blocks'] == 1024
    assert cfg['discovery']['overworld_bounds'] == [-2000, -2000, 2000, 2000]
    assert cfg['discovery']['nether_bounds'] == [-634, -634, 634, 634]


def test_v3_center_extents():
    cfg = dynamic_v3_blueprint_config()
    ow_side = cfg['deployment']['overworld_side_blocks']
    nw_side = cfg['deployment']['nether_side_blocks']
    ow_bounds = cfg['discovery']['overworld_bounds']
    nw_bounds = cfg['discovery']['nether_bounds']

    ow_half = ow_side // 2  # 1024
    nw_half = nw_side // 2  # 512

    # Overworld center limits: [-2000 + 1024, 2000 - 1024] = [-976, +976]
    min_c = ow_bounds[0] + ow_half
    max_c = ow_bounds[2] - ow_half
    assert min_c == -976
    assert max_c == 976

    # Nether center limits: [-976 // 8, 976 // 8] = [-122, 122]
    nether_min_c = min_c // 8
    nether_max_c = max_c // 8
    assert nether_min_c == -122
    assert nether_max_c == 122

    # Nether coordinate bounds: [-122 - 512, 122 + 512] = [-634, 634]
    assert nether_min_c - nw_half == nw_bounds[0]
    assert nether_max_c + nw_half == nw_bounds[2]


def test_v3_spawn_validation():
    cfg = dynamic_v3_blueprint_config()
    # Inside [-976, 976]
    c_ok = classify_spawn({'evaluation_center': [0, 0]}, cfg)
    assert c_ok['status'] == 'PENDING'
    c_boundary = classify_spawn({'evaluation_center': [976, -976]}, cfg)
    assert c_boundary['status'] == 'PENDING'

    # Outside [-976, 976]
    with pytest.raises(ValueError, match='inside the envelope'):
        classify_spawn({'evaluation_center': [977, 0]}, cfg)
    with pytest.raises(ValueError, match='inside the envelope'):
        classify_spawn({'evaluation_center': [-977, 0]}, cfg)
    with pytest.raises(ValueError, match='inside the envelope'):
        classify_spawn({'evaluation_center': [1168, 0]}, cfg)


def test_v3_prototype_native_init():
    cfg = dynamic_v3_blueprint_config()
    p = Prototype(None, cfg)
    assert p.policy.overworld_half == 1024
    assert p.policy.nether_half == 512
    assert p.policy.dynamic_v2 == 1  # Uses v2 structure bonuses and layout


def test_v3_native_batch_sweep():
    cfg = dynamic_v3_blueprint_config()
    p = Prototype(None, cfg)
    # Run small sweep over seeds
    seeds = [12345, 67890, 11111]
    with p.sweep(seeds, threads=1, retention='full') as batch:
        results = batch.records()
    assert len(results) == len(seeds)
    for r in results:
        # Results should be clean rejected or accepted with anchor within [-976, 976]
        if r.get('anchors'):
            a = r['anchors'][0]
            cx, cz = a['evaluation_center']
            assert -976 <= cx <= 976
            assert -976 <= cz <= 976


def test_v3_floors_and_zero_misses():
    cfg = dynamic_v3_blueprint_config()
    validate_blueprint_config(cfg)
    floors = cfg['structures']['hard_floors']
    assert floors['stronghold'] == 1
    assert floors['mansion'] == 1
    assert floors['village'] == 6
    assert floors['trial_chamber'] == 8
    assert floors['ancient_city'] == 2
    assert floors['desert_pyramid'] == 1
    assert floors['jungle_temple'] == 1
    assert floors['monument'] == 1
    assert floors['ruined_portal'] == 8
    assert floors['shipwreck'] == 4
    assert floors['mineshaft'] == 10
    assert floors['outpost'] == 1
    assert floors['fortress'] == 1
    assert floors['bastion'] == 2
    assert cfg['search']['max_misses'] == 0


def test_v3_dynamic_scoring_pure_additive():
    from seed_search.realm.blueprint import dynamic_v3_score

    # Baseline: meeting baseline hard floors exactly yields 0 core surplus and 0 deficit penalty
    baseline_counts = {
        'stronghold': 1, 'mansion': 1, 'monument': 1, 'village': 6,
        'trial_chamber': 8, 'ancient_city': 2, 'desert_pyramid': 1,
        'jungle_temple': 1, 'outpost': 1, 'fortress': 1, 'bastion': 2,
        'ruined_portal': 8, 'shipwreck': 4, 'mineshaft': 10
    }
    score, comp, defs = dynamic_v3_score(baseline_counts)
    assert score == 0
    assert comp['deficit_penalty'] == 0
    assert comp['core_surplus'] == 0
    assert defs == []

    # 1. Stronghold: 2nd = +20, 3rd+ = +30 (+50 total)
    counts = dict(baseline_counts, stronghold=2)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 20
    counts = dict(baseline_counts, stronghold=3)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 50

    # 2. Mansion: 2nd = +55, 3rd+ = +30 (+85 total)
    counts = dict(baseline_counts, mansion=2)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 55
    counts = dict(baseline_counts, mansion=3)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 85

    # 3. Ocean Monument: 2nd = +25, 3rd = +15, 4th+ = +10 (+50 total)
    counts = dict(baseline_counts, monument=2)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 25
    counts = dict(baseline_counts, monument=3)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 40
    counts = dict(baseline_counts, monument=4)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 50

    # 4. Outpost (F=1): 2nd = +15, 3rd = +15, 4th+ = +10 (+40 max)
    counts = dict(baseline_counts, outpost=1)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 0
    counts = dict(baseline_counts, outpost=2)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 15
    counts = dict(baseline_counts, outpost=3)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 30
    counts = dict(baseline_counts, outpost=4)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 40
    counts = dict(baseline_counts, outpost=5)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 40

    # 5. Fortress: 2nd = +20, 3rd = +15, 4th+ = +15 (+50 max)
    counts = dict(baseline_counts, fortress=1)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 0
    counts = dict(baseline_counts, fortress=2)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 20
    counts = dict(baseline_counts, fortress=3)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 35
    counts = dict(baseline_counts, fortress=4)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 50

    # 6. Bastion: 3rd = +20, 4th = +15, 5th+ = +15 (+50 max; +20 treasure)
    counts = dict(baseline_counts, bastion=2)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 0
    s_tb, _, _ = dynamic_v3_score(counts, treasure_bastion=1)
    assert s_tb == 20
    counts = dict(baseline_counts, bastion=3)
    s, _, _ = dynamic_v3_score(counts)
    assert s == 20

    # 7. Village: 7th..11th+ = +10 each (floor is 6, 0 at floor, +50 max)
    v_ladder = [(6, 0), (7, 10), (8, 20), (9, 30), (10, 40), (11, 50), (12, 50)]
    for v_cnt, expected_pts in v_ladder:
        counts = dict(baseline_counts, village=v_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts, f"Village count {v_cnt} expected {expected_pts}, got {s}"

    # 8. Trial Chamber: 9th=+10, 10th=+8, 11th=+7, 12th+=+5 (floor is 8, 0 at floor, +30 max)
    tc_ladder = [(8, 0), (9, 10), (10, 18), (11, 25), (12, 30), (13, 30)]
    for tc_cnt, expected_pts in tc_ladder:
        counts = dict(baseline_counts, trial_chamber=tc_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts

    # 9. Ancient City: 3rd=+20, 4th=+20, 5th=+15, 6th+=+10 (floor is 2, 0 at floor, +65 max)
    ac_ladder = [(2, 0), (3, 20), (4, 40), (5, 55), (6, 65), (7, 65)]
    for ac_cnt, expected_pts in ac_ladder:
        counts = dict(baseline_counts, ancient_city=ac_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts

    # 10. Desert Pyramid: 2nd = +25, 3rd = +20, 4th+ = +15 (Max +60)
    dp_ladder = [(1, 0), (2, 25), (3, 45), (4, 60), (5, 60)]
    for dp_cnt, expected_pts in dp_ladder:
        counts = dict(baseline_counts, desert_pyramid=dp_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts

    # 11. Jungle Temple: 2nd = +25, 3rd = +20, 4th+ = +15 (Max +60)
    jt_ladder = [(1, 0), (2, 25), (3, 45), (4, 60), (5, 60)]
    for jt_cnt, expected_pts in jt_ladder:
        counts = dict(baseline_counts, jungle_temple=jt_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts

    # 12. Shipwreck: 5th..8th = +5 each (floor is 4, 0 at floor, +20 max)
    sw_ladder = [(4, 0), (5, 5), (6, 10), (7, 15), (8, 20), (9, 20)]
    for sw_cnt, expected_pts in sw_ladder:
        counts = dict(baseline_counts, shipwreck=sw_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts

    # 13. Ruined Portal: 9th..12th = +5 each (floor is 8, 0 at floor, +20 max)
    rp_ladder = [(8, 0), (9, 5), (10, 10), (11, 15), (12, 20), (13, 20)]
    for rp_cnt, expected_pts in rp_ladder:
        counts = dict(baseline_counts, ruined_portal=rp_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts

    # 14. Mineshaft: +2 each over 10 up to 20 max
    ms_ladder = [(10, 0), (11, 2), (15, 10), (20, 20), (25, 20)]
    for ms_cnt, expected_pts in ms_ladder:
        counts = dict(baseline_counts, mineshaft=ms_cnt)
        s, _, _ = dynamic_v3_score(counts)
        assert s == expected_pts


def test_top50_tracker_capacity_and_cutoff():
    from seed_search.realm.top_tracker import Top50Tracker

    tracker = Top50Tracker(capacity=50)
    assert len(tracker) == 0
    assert tracker.cutoff_score() is None

    # Insert 40 candidates with increasing scores
    for i in range(40):
        tracker.observe({
            'seed': str(1000 + i),
            'baseline_score_observed': 100 + i,
            'ranking_tier': 0,
            'unmet_requirements': 0,
            'radial_key': 500000,
            'origin_distance_squared': 10000,
            'evaluation_center': [0, 0]
        })
    assert len(tracker) == 40
    # Still less than capacity, so cutoff is None
    assert tracker.cutoff_score() is None

    # Insert 10 more candidates (scores 140 to 149) -> reaches capacity 50
    for i in range(40, 50):
        tracker.observe({
            'seed': str(1000 + i),
            'baseline_score_observed': 100 + i,
            'ranking_tier': 0,
            'unmet_requirements': 0,
            'radial_key': 500000,
            'origin_distance_squared': 10000,
            'evaluation_center': [0, 0]
        })
    assert len(tracker) == 50
    # Now capacity is reached: cutoff score should be 100 (the lowest among 100..149)
    assert tracker.cutoff_score() == 100

    # Observe a candidate with score 90 (below cutoff 100) -> should be rejected
    accepted = tracker.observe({
        'seed': '9999',
        'baseline_score_observed': 90,
        'ranking_tier': 0,
        'unmet_requirements': 0,
        'radial_key': 500000,
        'origin_distance_squared': 10000,
        'evaluation_center': [0, 0]
    })
    assert accepted is False
    assert len(tracker) == 50
    assert tracker.cutoff_score() == 100

    # Observe a candidate with score 155 (above cutoff 100) -> accepted, displacing 100
    accepted = tracker.observe({
        'seed': '8888',
        'baseline_score_observed': 155,
        'ranking_tier': 0,
        'unmet_requirements': 0,
        'radial_key': 500000,
        'origin_distance_squared': 10000,
        'evaluation_center': [0, 0]
    })
    assert accepted is True
    assert len(tracker) == 50
    # Now the lowest score in top 50 is 101!
    assert tracker.cutoff_score() == 101

    # Check top_records order: Rank 1 must have score 155
    records = tracker.top_records()
    assert len(records) == 50
    assert records[0]['seed'] == '8888'
    assert records[0]['baseline_score_observed'] == 155
    assert records[-1]['baseline_score_observed'] == 101


def test_top50_tracker_serialization(tmp_path):
    from seed_search.realm.top_tracker import Top50Tracker

    tracker = Top50Tracker(capacity=5)
    for i in range(5):
        tracker.observe({
            'seed': str(i),
            'baseline_score_observed': 200 + i * 10,
            'ranking_tier': 0,
            'unmet_requirements': 0,
            'radial_key': 1000,
            'origin_distance_squared': 500,
            'evaluation_center': [16, -16]
        })

    # Test JSON serialization
    json_file = str(tmp_path / "top50.json")
    tracker.save_to_json(json_file)

    tracker2 = Top50Tracker(capacity=5)
    loaded = tracker2.load_from_json(json_file)
    assert loaded == 5
    assert tracker2.cutoff_score() == 200
    assert tracker2.top_records()[0]['baseline_score_observed'] == 240

    # Test SQLite serialization
    import sqlite3
    db_file = str(tmp_path / "top50.db")
    tracker.save_to_sqlite(db_file)

    conn = sqlite3.connect(db_file)
    rows = conn.execute("SELECT rank, seed, score FROM top_candidates ORDER BY rank ASC").fetchall()
    conn.close()
    assert len(rows) == 5
    assert rows[0] == (1, '4', 240)
    assert rows[-1] == (5, '0', 200)


def test_v3_fixture_sweep_parity():
    from seed_search.realm.native_batch import semantic_record
    cfg = dynamic_v3_blueprint_config()
    p = Prototype(None, cfg)
    with p.sweep([456], fixtures=[(0, 0, -1)]) as batch:
        direct = batch.records()[0]
        replay = batch.records(adapter='replay')[0]
        assert direct['anchors'][0]['screening_revision'] == 'dynamic-envelope-2048-v3'
        assert direct['anchors'][0]['deficit_penalty'] == 0
        assert direct['anchors'][0]['baseline_score'] == direct['anchors'][0]['bonus_total']
        assert direct['anchors'][0]['inventory']['version'] == 'dynamic-2048-count-inventory-v3'
        assert semantic_record(direct) == semantic_record(replay)


def test_v3_nether_lattice_bounds():
    from seed_search.realm.dynamic import nether_palette, nether_bounds

    class MockBackend:
        def sample(self, points, dimension=-1):
            return [8] * len(points)  # nether_wastes

    for center in [(0, 0), (976, -976), (-976, 976), (123, -456), (-500, 500)]:
        bounds = nether_bounds(center, 512)
        res = nether_palette(MockBackend(), center, nether_half=512)
        assert res['sample_count'] == 256
        for s in res['sampling']['samples']:
            x, y, z = s['coordinate']
            assert bounds[0] <= x < bounds[2], f"x={x} not in [{bounds[0]}, {bounds[2]}) for center {center}"
            assert bounds[1] <= z < bounds[3], f"z={z} not in [{bounds[1]}, {bounds[3]}) for center {center}"


def test_v3_cutoff_score_pruning():
    cfg = dynamic_v3_blueprint_config()
    p = Prototype(None, cfg)
    assert p.policy.cutoff_score == 0

    # With high cutoff score, fixture anchor should be pruned early
    with p.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=9999) as batch:
        records = batch.records()
        assert len(records) == 1
        assert len(records[0]['anchors']) == 0

    # With cutoff score 0, normal anchor is retained
    with p.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=0) as batch:
        records = batch.records()
        assert len(records) == 1
        assert len(records[0]['anchors']) == 1
        observed_score = records[0]['anchors'][0]['baseline_score_observed']
        assert observed_score == 482

    # Exact boundary: cutoff == observed_score must retain
    with p.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=observed_score) as batch:
        records = batch.records()
        assert len(records[0]['anchors']) == 1
        assert records[0]['anchors'][0]['baseline_score_observed'] == observed_score

    # Exact boundary: cutoff == observed_score + 1 must prune
    with p.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=observed_score + 1) as batch:
        records = batch.records()
        assert len(records[0]['anchors']) == 0

    # Top50Tracker integration: cutoff_score feeds back into sweep dynamically
    from seed_search.realm.top_tracker import Top50Tracker
    tracker = Top50Tracker(capacity=1)
    assert tracker.cutoff_score() is None

    # First seed observed fills tracker
    with p.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=tracker.cutoff_score() or 0) as batch:
        records = batch.records()
        tracker.observe(records[0])
    assert tracker.cutoff_score() == 482

    # Next sweep with tracker's cutoff score prunes anything strictly less than 482
    with p.sweep([456], fixtures=[(0, 0, -1)], cutoff_score=tracker.cutoff_score() + 1) as batch:
        records = batch.records()
        assert len(records[0]['anchors']) == 0


def test_v3_candidate_rescore_idempotence():
    import copy
    from seed_search.realm.reports import _candidate_rescore

    # Construct complete v3 candidate scoring exactly 281
    candidate_281 = {
        'contract': 'master_seed_blueprint_v1',
        'screening_revision': 'dynamic-envelope-2048-v3',
        'evaluation_center': [0, 0],
        'required_structures': {
            'stronghold': {'predicted_viable': [[100, 100]]},
            'mansion': {'predicted_viable': [[120, 120]]},
            'village': {'predicted_viable': [[100, 100], [-300, 300], [-300, -300], [300, -300], [500, 500], [600, 600], [700, 700]]},
            'trial_chamber': {'predicted_viable': [[i * 50, i * 50] for i in range(1, 10)]},
            'ancient_city': {'predicted_viable': [[200, 200], [400, 400], [600, 600]]},
            'desert_pyramid': {'predicted_viable': [[150, 150], [300, 300]]},
            'jungle_temple': {'predicted_viable': [[250, 250]]},
            'monument': {'predicted_viable': [[350, 350]]},
            'outpost': {'predicted_viable': [[450, 450]]},
            'ruined_portal': {'predicted_viable': [[i * 40, -i * 40] for i in range(1, 13)]},
            'shipwreck': {'predicted_viable': [[i * 60, i * 60] for i in range(1, 5)]},
            'mineshaft': {'predicted_viable': [[i * 30, -i * 30] for i in range(1, 19)]},
        },
        'required_nether_structures': {
            'fortress': {'predicted_viable': [[10, 10], [50, 50]]},
            'bastion': {'predicted_viable': [[20, 20], [60, 60]]},
        },
        'optional_structures': {
            'swamp_hut': {'predicted_viable': []},
            'trail_ruins': {'predicted_viable': []},
            'igloo': {'predicted_viable': []},
            'ocean_ruin': {'predicted_viable': []},
            'buried_treasure': {'predicted_viable': []},
        },
        'bastion_variants': [[20, 20, 2], [60, 60, 0]],
        'biomes': {
            'sampling': {
                'samples': [
                    {'coordinate': [x, 63, z], 'biome': 'cherry_grove' if (x == 0 and z == 0) else ('river' if (x == 64 and z == 0) else 'plains')}
                    for x in range(-1024, 1025, 64)
                    for z in range(-1024, 1025, 64)
                ]
            }
        }
    }

    cfg = dynamic_v3_blueprint_config()
    rescored = _candidate_rescore(copy.deepcopy(candidate_281), cfg, 'rev_v3_initial')
    assert rescored['baseline_score'] == 281
    assert rescored['baseline_score_observed'] == 281
    assert rescored['ranking']['score'] == 281
    assert rescored['ranking']['components']['bonus_total'] == 281
    assert rescored['ranking']['components']['deficit_penalty'] == 0
    assert rescored['ranking']['components']['scenic_bonus'] == 25
    assert rescored['ranking']['components']['village_spread_bonus'] == 25
    assert rescored['ranking']['components']['treasure_bastion_bonus'] == 20
    assert rescored['ranking']['components']['nether_core_bonus'] == 20

    # Test idempotence: rescore again and assert complete equality
    rescored_again = _candidate_rescore(copy.deepcopy(rescored), cfg, 'rev_v3_second')
    assert rescored_again['baseline_score'] == 281
    assert rescored_again['baseline_score'] == rescored['baseline_score']
    assert rescored_again['ranking']['components'] == rescored['ranking']['components']
    assert rescored_again['weighted_radial_dist'] == rescored['weighted_radial_dist']
    assert rescored_again['radial_key'] == rescored['radial_key']
    assert rescored_again['evaluation_center'] == rescored['evaluation_center']
    assert rescored_again['origin_distance'] == rescored['origin_distance']
    assert rescored_again['origin_distance_squared'] == rescored['origin_distance_squared']
    assert rescored_again['deficit_categories'] == rescored['deficit_categories']

    # Also test idempotence on a candidate generated by native sweep
    p = Prototype(None, cfg)
    with p.sweep([456], fixtures=[(0, 0, -1)]) as batch:
        native_anchor = batch.records()[0]['anchors'][0]
    orig_score = native_anchor['baseline_score']
    res_native_1 = _candidate_rescore(copy.deepcopy(native_anchor), cfg, 'rev_sweep_1')
    assert res_native_1['baseline_score'] == orig_score
    assert res_native_1['ranking']['components'] == native_anchor['ranking']['components']
    assert res_native_1['radial_key'] == native_anchor['radial_key']
    assert res_native_1['weighted_radial_dist'] == native_anchor['weighted_radial_dist']

    res_native_2 = _candidate_rescore(copy.deepcopy(res_native_1), cfg, 'rev_sweep_2')
    assert res_native_2['baseline_score'] == orig_score
    assert res_native_2['ranking'] == res_native_1['ranking']
    assert res_native_2['radial_key'] == res_native_1['radial_key']


def test_top50_tracker_nested_sqlite_saving(tmp_path):
    import sqlite3
    from seed_search.realm.top_tracker import Top50Tracker

    tracker = Top50Tracker(capacity=10)
    nested_record = {
        'seed': '987654321',
        'contract': 'master_seed_blueprint_v1',
        'anchors': [
            {
                'id': '987654321:0:0',
                'seed': '987654321',
                'baseline_score_observed': 281,
                'baseline_score': 281,
                'ranking_tier': 0,
                'unmet_requirements': 0,
                'radial_key': 123456,
                'origin_distance_squared': 500,
                'evaluation_center': [0, 0],
                'ranking': {'score': 281}
            }
        ]
    }
    accepted = tracker.observe(nested_record)
    assert accepted is True
    assert len(tracker) == 1

    # Save to SQLite and verify non-zero score is stored in top_candidates table
    db_file = str(tmp_path / "nested_top50.db")
    tracker.save_to_sqlite(db_file)

    conn = sqlite3.connect(db_file)
    rows = conn.execute("SELECT rank, seed, score FROM top_candidates ORDER BY rank ASC").fetchall()
    conn.close()

    assert len(rows) == 1
    rank, seed, score = rows[0]
    assert rank == 1
    assert seed == '987654321'
    assert score == 281, f"Expected non-zero score 281, got {score}"

    # Test flush and flush_transactional methods
    tracker.flush(db_file)
    conn2 = sqlite3.connect(db_file)
    rows2 = conn2.execute("SELECT rank, seed, score FROM top_candidates ORDER BY rank ASC").fetchall()
    conn2.close()
    assert rows2 == rows

    tracker.flush_transactional(db_file)
    conn3 = sqlite3.connect(db_file)
    rows3 = conn3.execute("SELECT rank, seed, score FROM top_candidates ORDER BY rank ASC").fetchall()
    conn3.close()
    assert rows3 == rows


def test_top50_tracker_lexical_id_tiebreaking():
    from seed_search.realm.top_tracker import Top50Tracker

    tracker = Top50Tracker(capacity=2)
    # Three candidates with identical arithmetic metrics, differing only by id
    rec_gamma = {'id': 'gamma', 'seed': '3', 'baseline_score_observed': 200, 'ranking_tier': 0, 'unmet_requirements': 0, 'radial_key': 100, 'origin_distance_squared': 100, 'evaluation_center': [0, 0]}
    rec_beta = {'id': 'beta', 'seed': '2', 'baseline_score_observed': 200, 'ranking_tier': 0, 'unmet_requirements': 0, 'radial_key': 100, 'origin_distance_squared': 100, 'evaluation_center': [0, 0]}
    rec_alpha = {'id': 'alpha', 'seed': '1', 'baseline_score_observed': 200, 'ranking_tier': 0, 'unmet_requirements': 0, 'radial_key': 100, 'origin_distance_squared': 100, 'evaluation_center': [0, 0]}

    tracker.observe(rec_gamma)
    tracker.observe(rec_beta)
    assert len(tracker) == 2
    # In ORDER_V2 ('id ASC'), 'beta' < 'gamma', so beta is Rank 1, gamma is Rank 2 (worst)
    assert tracker.top_records()[0]['id'] == 'beta'
    assert tracker.top_records()[1]['id'] == 'gamma'

    # Now observe 'alpha': 'alpha' < 'beta' < 'gamma'. Alpha is better than gamma, displacing gamma.
    accepted = tracker.observe(rec_alpha)
    assert accepted is True
    assert len(tracker) == 2

    records = tracker.top_records()
    assert records[0]['id'] == 'alpha'
    assert records[1]['id'] == 'beta'


def test_v3_outpost_floor_one_qualification_and_scoring():
    from seed_search.realm.blueprint import dynamic_v3_score

    cfg = dynamic_v3_blueprint_config()
    # 1. Floor verification
    assert cfg['structures']['hard_floors']['outpost'] == 1
    assert cfg['structures']['minimum_counts']['outpost'] == 1

    # 2. Pure additive scoring ladder: floor is 1, 2nd=+15, 3rd=+15, 4th+=+10 (Max 40)
    baseline_counts = {
        'stronghold': 1, 'mansion': 1, 'monument': 1, 'village': 6,
        'trial_chamber': 8, 'ancient_city': 2, 'desert_pyramid': 1,
        'jungle_temple': 1, 'outpost': 1, 'fortress': 1, 'bastion': 2,
        'ruined_portal': 8, 'shipwreck': 4, 'mineshaft': 10
    }
    # Meeting floor gives 0 bonus points
    s1, _, defs1 = dynamic_v3_score(dict(baseline_counts, outpost=1))
    assert s1 == 0
    assert defs1 == []

    # 2nd outpost = +15
    s2, comp2, _ = dynamic_v3_score(dict(baseline_counts, outpost=2))
    assert s2 == 15
    assert comp2['core_surplus'] == 15

    # 3rd outpost = +15 (30 total)
    s3, comp3, _ = dynamic_v3_score(dict(baseline_counts, outpost=3))
    assert s3 == 30
    assert comp3['core_surplus'] == 30

    # 4th outpost = +10 (40 total)
    s4, comp4, _ = dynamic_v3_score(dict(baseline_counts, outpost=4))
    assert s4 == 40
    assert comp4['core_surplus'] == 40

    # 5th outpost capped at 40
    s5, comp5, _ = dynamic_v3_score(dict(baseline_counts, outpost=5))
    assert s5 == 40
    assert comp5['core_surplus'] == 40


def test_top50_tracker_seed_deduplication_and_deepcopy():
    from seed_search.realm.top_tracker import Top50Tracker

    tracker = Top50Tracker(capacity=5)
    rec = {'seed': '123', 'id': '123:0:0', 'baseline_score_observed': 100}
    assert tracker.observe(rec) is True
    assert len(tracker) == 1

    # External mutation of rec should not affect stored record
    rec['baseline_score_observed'] = 999
    assert tracker.top_records()[0]['baseline_score_observed'] == 100

    # Observing same seed with better score updates the entry in-place
    better_rec = {'seed': '123', 'id': '123:0:0', 'baseline_score_observed': 150}
    assert tracker.observe(better_rec) is True
    assert len(tracker) == 1
    assert tracker.top_records()[0]['baseline_score_observed'] == 150

    # Observing same seed with worse score is rejected and does not add a duplicate slot
    worse_rec = {'seed': '123', 'id': '123:0:0', 'baseline_score_observed': 80}
    assert tracker.observe(worse_rec) is False
    assert len(tracker) == 1
    assert tracker.top_records()[0]['baseline_score_observed'] == 150

```

---

<a id="file-13"></a>
### File 13: `web-ui/src/constants/searchProfiles.json`
> **Purpose:** Web UI Profile Registry: dynamic2048 Profile, Floors & Miss Budget  
> **Length:** 323 lines | **Language:** JSON

```json
{
  "dynamic1664": {
    "name": "1664 sliding center",
    "revision": "dynamic-envelope-1664-v2",
    "counts": {
      "stronghold": 1,
      "mansion": 1,
      "village": 9,
      "trial_chamber": 8,
      "ancient_city": 4,
      "desert_pyramid": 3,
      "jungle_temple": 3,
      "monument": 1,
      "ruined_portal": 7,
      "shipwreck": 6,
      "mineshaft": 15,
      "outpost": 2,
      "fortress": 2,
      "bastion": 2
    },
    "floors": {
      "stronghold": 1,
      "mansion": 1,
      "village": 8,
      "trial_chamber": 7,
      "ancient_city": 3,
      "desert_pyramid": 2,
      "jungle_temple": 2,
      "monument": 1,
      "ruined_portal": 5,
      "shipwreck": 4,
      "mineshaft": 12,
      "outpost": 2,
      "fortress": 2,
      "bastion": 2
    },
    "flexible": [
      "village",
      "trial_chamber",
      "ancient_city",
      "desert_pyramid",
      "jungle_temple",
      "ruined_portal",
      "shipwreck",
      "mineshaft"
    ],
    "editableCounts": [
      "mansion",
      "village",
      "trial_chamber",
      "ancient_city",
      "desert_pyramid",
      "jungle_temple",
      "monument",
      "ruined_portal",
      "shipwreck",
      "mineshaft",
      "outpost",
      "fortress",
      "bastion"
    ],
    "requiredBiomes": [
      "plains",
      "desert",
      "forest",
      "taiga",
      "jungle",
      "swamp",
      "snowy_ice",
      "dark_forest",
      "peaks",
      "stony_shore",
      "lush_caves",
      "dripstone_caves",
      "deep_dark"
    ],
    "netherBiomes": [
      "nether_wastes",
      "crimson_forest",
      "warped_forest",
      "soul_sand_valley",
      "basalt_deltas"
    ],
    "defaultMisses": 3,
    "overworldSide": 1664,
    "netherSide": 832,
    "maxMisses": 3,
    "deferredMarine": false
  },
  "dynamic2048": {
    "name": "2048 sliding center (v3)",
    "revision": "dynamic-envelope-2048-v3",
    "counts": {
      "stronghold": 1,
      "mansion": 1,
      "village": 6,
      "trial_chamber": 8,
      "ancient_city": 2,
      "desert_pyramid": 1,
      "jungle_temple": 1,
      "monument": 1,
      "ruined_portal": 8,
      "shipwreck": 4,
      "mineshaft": 10,
      "outpost": 1,
      "fortress": 1,
      "bastion": 2
    },
    "floors": {
      "stronghold": 1,
      "mansion": 1,
      "village": 6,
      "trial_chamber": 8,
      "ancient_city": 2,
      "desert_pyramid": 1,
      "jungle_temple": 1,
      "monument": 1,
      "ruined_portal": 8,
      "shipwreck": 4,
      "mineshaft": 10,
      "outpost": 1,
      "fortress": 1,
      "bastion": 2
    },
    "flexible": [],
    "editableCounts": [
      "mansion",
      "village",
      "trial_chamber",
      "ancient_city",
      "desert_pyramid",
      "jungle_temple",
      "monument",
      "ruined_portal",
      "shipwreck",
      "mineshaft",
      "outpost",
      "fortress",
      "bastion"
    ],
    "requiredBiomes": [
      "plains",
      "desert",
      "forest",
      "taiga",
      "jungle",
      "swamp",
      "snowy_ice",
      "dark_forest",
      "peaks",
      "stony_shore",
      "lush_caves",
      "dripstone_caves",
      "deep_dark"
    ],
    "netherBiomes": [
      "nether_wastes",
      "crimson_forest",
      "warped_forest",
      "soul_sand_valley",
      "basalt_deltas"
    ],
    "defaultMisses": 0,
    "overworldSide": 2048,
    "netherSide": 1024,
    "maxMisses": 0,
    "deferredMarine": false
  },
  "marine2048": {
    "name": "2048 marine baseline",
    "revision": "origin-fixed-2048-two-group-marine-v3",
    "counts": {
      "stronghold": 1,
      "mansion": 1,
      "village": 7,
      "trial_chamber": 10,
      "ancient_city": 2,
      "desert_pyramid": 1,
      "jungle_temple": 1,
      "monument": 1,
      "ruined_portal": 7,
      "shipwreck": 3,
      "mineshaft": 20,
      "outpost": 1,
      "fortress": 2,
      "bastion": 3
    },
    "floors": {
      "stronghold": 1,
      "jungle_temple": 1,
      "desert_pyramid": 1,
      "outpost": 1,
      "mansion": 0,
      "trial_chamber": 8,
      "village": 5,
      "ruined_portal": 5,
      "mineshaft": 17,
      "ancient_city": 1,
      "fortress": 1,
      "bastion": 2,
      "monument": 1,
      "shipwreck": 3
    },
    "flexible": [
      "mansion",
      "village",
      "trial_chamber",
      "ancient_city",
      "ruined_portal",
      "mineshaft",
      "fortress",
      "bastion"
    ],
    "editableCounts": [
      "mansion",
      "village",
      "trial_chamber",
      "ancient_city",
      "ruined_portal",
      "mineshaft",
      "fortress",
      "bastion"
    ],
    "requiredBiomes": [
      "plains",
      "desert",
      "forest",
      "taiga",
      "jungle",
      "swamp",
      "snowy_ice",
      "dark_forest",
      "peaks",
      "stony_shore",
      "lush_caves",
      "dripstone_caves",
      "deep_dark"
    ],
    "netherBiomes": [],
    "defaultMisses": 2,
    "overworldSide": 2048,
    "netherSide": 1024,
    "maxMisses": 8,
    "deferredMarine": false
  },
  "twoGroup2048": {
    "name": "2048 historical baseline",
    "revision": "origin-fixed-2048-two-group-v2",
    "counts": {
      "stronghold": 1,
      "mansion": 1,
      "village": 7,
      "trial_chamber": 10,
      "ancient_city": 2,
      "desert_pyramid": 1,
      "jungle_temple": 1,
      "monument": 1,
      "ruined_portal": 7,
      "shipwreck": 3,
      "mineshaft": 20,
      "outpost": 1,
      "fortress": 2,
      "bastion": 3
    },
    "floors": {
      "stronghold": 1,
      "jungle_temple": 1,
      "desert_pyramid": 1,
      "outpost": 1,
      "mansion": 0,
      "trial_chamber": 8,
      "village": 5,
      "ruined_portal": 5,
      "mineshaft": 17,
      "ancient_city": 1,
      "fortress": 1,
      "bastion": 2
    },
    "flexible": [
      "mansion",
      "village",
      "trial_chamber",
      "ancient_city",
      "ruined_portal",
      "mineshaft",
      "fortress",
      "bastion"
    ],
    "editableCounts": [
      "mansion",
      "village",
      "trial_chamber",
      "ancient_city",
      "monument",
      "ruined_portal",
      "shipwreck",
      "mineshaft",
      "fortress",
      "bastion"
    ],
    "requiredBiomes": [
      "plains",
      "desert",
      "forest",
      "taiga",
      "jungle",
      "swamp",
      "snowy_ice",
      "dark_forest",
      "peaks",
      "stony_shore",
      "lush_caves",
      "dripstone_caves",
      "deep_dark"
    ],
    "netherBiomes": [],
    "defaultMisses": 2,
    "overworldSide": 2048,
    "netherSide": 1024,
    "maxMisses": 8,
    "deferredMarine": true
  }
}

```

---

<a id="file-14"></a>
### File 14: `web-ui/src/utils/ranking.ts`
> **Purpose:** Web UI Sorting Comparator: Score-First Ordering (compareCandidateRank)  
> **Length:** 30 lines | **Language:** TYPESCRIPT

```typescript
import type { SeedCandidate } from '../types';

const cmpId = (x: string, y: string) => (x < y ? -1 : x > y ? 1 : 0);

/** Match the saved-run leaderboard; user-selected alternate sorts remain separate. */
export function compareCandidateRank(a: SeedCandidate, b: SeedCandidate): number {
  if ((a.screeningRevision === 'dynamic-envelope-1664-v2' || a.screeningRevision === 'dynamic-envelope-2048-v3') && b.screeningRevision === a.screeningRevision) {
    const primary = (a.rankingTier ?? 99) - (b.rankingTier ?? 99)
      || (b.score ?? -Infinity) - (a.score ?? -Infinity)
      || (a.unmetRequirements ?? 0) - (b.unmetRequirements ?? 0)
      || (a.radialKey ?? (a.weightedRadialDistance != null ? Math.round(a.weightedRadialDistance * 1e6) : Infinity))
       - (b.radialKey ?? (b.weightedRadialDistance != null ? Math.round(b.weightedRadialDistance * 1e6) : Infinity))
      || (a.originDistanceSquared ?? (a.originDistance != null ? Math.round(a.originDistance ** 2) : Infinity))
       - (b.originDistanceSquared ?? (b.originDistance != null ? Math.round(b.originDistance ** 2) : Infinity))
      || (a.evaluationCenter?.[0] ?? 0) - (b.evaluationCenter?.[0] ?? 0)
      || (a.evaluationCenter?.[1] ?? 0) - (b.evaluationCenter?.[1] ?? 0)
      || cmpId(a.id, b.id);
    return primary;
  }
  const primary = (a.rankingTier ?? 99) - (b.rankingTier ?? 99)
    || (a.unmetRequirements ?? 0) - (b.unmetRequirements ?? 0)
    || (b.score ?? -Infinity) - (a.score ?? -Infinity);
  if (primary) return primary;
  if (a.screeningRevision === 'dynamic-envelope-1664-v1' && b.screeningRevision === a.screeningRevision) {
    const distance = (a.weightedRadialDistance ?? Infinity) - (b.weightedRadialDistance ?? Infinity)
      || (a.originDistance ?? Infinity) - (b.originDistance ?? Infinity);
    if (distance) return distance;
  }
  return cmpId(a.id, b.id);
}

```

---

<a id="file-15"></a>
### File 15: `tests/web_structure_policy.cjs`
> **Purpose:** Web UI & Backend Policy Contract Test Suite (13 Tests)  
> **Length:** 252 lines | **Language:** JAVASCRIPT

```javascript
// Exercise actual sidebar handlers and App launch validation without a backend.
const assert = require('node:assert/strict');
const test = require('node:test');
const { load, root, hooks } = require('./web_test_loader.cjs');
const { SEARCH_PROFILES } = load(root + '/web-ui/src/constants/baselinePolicy.ts');
const { INITIAL_CONFIG } = load(root + '/web-ui/src/mockData.ts');
const { FilterSidebar } = load(root + '/web-ui/src/components/FilterSidebar.tsx');
const { buildSweepRequest } = load(root + '/web-ui/src/utils/sweep.ts');
const validate = config => buildSweepRequest(config).counts;

function nodes(node) {
  if (node == null) return [];
  if (Array.isArray(node)) return node.flatMap(nodes);
  if (typeof node !== 'object') return [];
  return [node, ...nodes(node.props?.children)];
}
function sidebar(config, tab = 'targets', running = false) {
  hooks.state = value => value === 'targets' ? tab : value;
  let changed;
  const tree = FilterSidebar({ config, onChangeConfig: value => changed = value,
    logs: [], onResumeSweep: () => {}, sweepRunning: running });
  hooks.state = value => value;
  return { all: nodes(tree), changed: () => changed };
}
function pyramidRow(view) { return view.all.find(node => node.key === 'desert_pyramid'); }
function displayedCount(row) {
  return nodes(row).find(node => node.type === 'span' && typeof node.props.children === 'number').props.children;
}

test('legacy alias displays, estimates and edits the same count that App launches', () => {
  const config = { ...INITIAL_CONFIG,
    requiredStructures: INITIAL_CONFIG.requiredStructures.map(key => key === 'desert_pyramid' ? 'pyramid' : key),
    structureFloorCounts: { ...INITIAL_CONFIG.structureFloorCounts, pyramid: 4 } };
  delete config.structureFloorCounts.desert_pyramid;
  const view = sidebar(config), row = pyramidRow(view);
  assert.equal(displayedCount(row), 4);
  assert.equal(validate(config).desert_pyramid, 4);
  nodes(row).find(node => node.type === 'button' && node.props.title === 'Increase target count').props.onClick();
  const changed = view.changed();
  assert.equal(changed.structureFloorCounts.desert_pyramid, 5);
  assert.equal(validate(changed).desert_pyramid, 5);
  assert.ok(!('pyramid' in changed.structureFloorCounts));
  assert.ok(!changed.requiredStructures.includes('pyramid'));
  assert.equal(changed.requiredStructures.filter(key => key === 'desert_pyramid').length, 1);
  assert.equal(config.structureFloorCounts.pyramid, 4); // Reading never mutates historical input.
});

test('canonical value takes precedence over a stale alias, including zero', () => {
  for (const count of [0, 3, 5]) {
    const config = { ...INITIAL_CONFIG, structureFloorCounts: {
      ...INITIAL_CONFIG.structureFloorCounts, desert_pyramid: count, pyramid: 9 } };
    assert.equal(displayedCount(pyramidRow(sidebar(config))), count);
    if (count === 0) assert.throws(() => validate(config), /requires at least 2/);
    else assert.equal(validate(config).desert_pyramid ?? 3, count);
  }
});

test('all profile defaults, steppers, reset and profile changes stay canonical', () => {
  assert.ok(!('pyramid' in INITIAL_CONFIG.structureFloorCounts));
  for (const [profile, policy] of Object.entries(SEARCH_PROFILES)) {
    const config = { ...INITIAL_CONFIG, profile, structureFloorCounts: { ...policy.counts },
      requiredStructures: Object.keys(policy.counts) };
    const view = sidebar(config), row = pyramidRow(view);
    assert.equal(displayedCount(row), policy.counts.desert_pyramid);
    assert.equal(JSON.stringify(validate(config)), JSON.stringify(policy.counts));
    const increase = nodes(row).find(node => node.type === 'button' && node.props.title === 'Increase target count');
    assert.equal(increase.props.disabled, !policy.editableCounts.includes('desert_pyramid'));
    increase.props.onClick();
    if (policy.editableCounts.includes('desert_pyramid')) assert.equal(validate(view.changed()).desert_pyramid, policy.counts.desert_pyramid + 1);
    else assert.equal(view.changed(), undefined);
    view.all.find(node => node.type === 'button' && node.props.children === 'Reset').props.onClick();
    assert.ok(!('pyramid' in view.changed().structureFloorCounts));
    assert.equal(JSON.stringify(validate(view.changed())), JSON.stringify(SEARCH_PROFILES[view.changed().profile].counts));
    view.all.find(node => node.type === 'select' && node.props.value === profile)
      .props.onChange({ target: { value: 'dynamic1664' } });
    assert.ok(!view.changed().requiredStructures.includes('pyramid'));
    assert.equal(JSON.stringify(validate(view.changed())), JSON.stringify(SEARCH_PROFILES[view.changed().profile].counts));
  }
});


const { CandidateFeed } = load(root + '/web-ui/src/components/CandidateFeed.tsx');
const { SeedDetailModal } = load(root + '/web-ui/src/components/SeedDetailModal.tsx');
const noop = () => {};
function text(node) {
  if (node == null || typeof node === 'boolean') return '';
  if (Array.isArray(node)) return node.map(text).join(' ');
  if (typeof node === 'object') return text(node.props?.children);
  return String(node);
}

test('candidate page controls can reach results beyond the former pool cap', () => {
  let next;
  const tree = CandidateFeed({ candidates: [], selectedCandidate: null,
    onSelectCandidate: noop, onInspectCandidate: noop, onCopyNotice: noop,
    pagination: { offset: 5000, total: 5101, limit: 100, onChangeOffset: value => { next = value; } } });
  assert.match(text(tree), /5001–5100 of 5,101/);
  const button = nodes(tree).find(node => node.props?.['aria-label'] === 'Next candidate page');
  assert.equal(button.props.disabled, false);
  button.props.onClick();
  assert.equal(next, 5100);
});

test('negative eligible scores are visible before the user applies a score filter', () => {
  const tree = CandidateFeed({ candidates: [{ id: 'a', seed: '1', score: -10, structures: [] }],
    selectedCandidate: null, onSelectCandidate: noop, onInspectCandidate: noop, onCopyNotice: noop });
  assert.ok(nodes(tree).some(node => node.key === 'a'));
});

test('player detail shows predictive suggestion separately from unverified inspections', () => {
  const candidate = { id: 'a', seed: '1', score: 100, structures: [], evaluationCenter: [0, 0],
    suggestedSpawn: { status: 'PREDICTED_SCENIC_SUGGESTION', coordinates: [64, 63, 0], biome: 'plains', distance: 64 },
    playerInspections: { end_access: { status: 'UNVERIFIED', reason: 'Portal room not inspected', source: null } } };
  const tree = SeedDetailModal({ candidate, onClose: noop, onCopyNotice: noop });
  assert.match(text(tree), /Suggested community spawn/);
  assert.match(text(tree), /Actual ground height and safety remain unverified/);
  assert.match(text(tree), /Portal room not inspected/);
});


test('every editable run setting is included in the shared preview/launch request', () => {
  const changes = { 'Seed count': ['sweepSeedCount', '1234', 'count', 1234],
    'Starting seed index': ['startIndex', '18446744073709550000', 'startIndex', '18446744073709550000'],
    'Deficit budget': ['maxMisses', '2', 'maxMisses', 2],
    'Native threads': ['openmpThreads', '7', 'threads', 7],
    'Native batch size': ['batchSize', '128', 'batchSize', 128] };
  for (const [label, [state, value, requestKey, expected]] of Object.entries(changes)) {
    const view = sidebar({ ...INITIAL_CONFIG, sweepSeedCount: 10 }, 'engine');
    const control = view.all.find(node => node.props?.['aria-label'] === label);
    control.props.onChange({ target: { value } });
    assert.equal(view.changed()[state], expected);
    assert.equal(buildSweepRequest(view.changed())[requestKey], expected);
  }
});

test('fixed policy controls cannot drift and running settings are locked', () => {
  const view = sidebar(INITIAL_CONFIG);
  assert.ok(!view.all.some(node => node.props?.type === 'checkbox'));
  const stronghold = view.all.find(node => node.key === 'stronghold');
  for (const button of nodes(stronghold).filter(node => node.type === 'button')) assert.equal(button.props.disabled, true);
  const floor = { ...INITIAL_CONFIG, structureFloorCounts: { ...INITIAL_CONFIG.structureFloorCounts, village: 8 } };
  const village = sidebar(floor).all.find(node => node.key === 'village');
  assert.equal(nodes(village).find(node => node.props?.title === 'Decrease target count').props.disabled, true);
  assert.ok(sidebar(INITIAL_CONFIG, 'engine', true).all.some(node => node.type === 'fieldset' && node.props.disabled));
});


test('command card includes the resolved target policy and last executed command', () => {
  const receipt = { kind: 'preview', shellCommand: 'cd /repo && python scan --config policy.yaml',
    cwd: '/repo', policyYaml: 'minimum_counts: village: 10',
    controls: { count: 123, start_index: '9007199254741001', threads: 7, batch_size: 128, max_misses: 2 } };
  const tree = FilterSidebar({ config: INITIAL_CONFIG, onChangeConfig: noop, logs: [],
    onResumeSweep: noop, sweepRunning: false, preview: receipt, lastLaunch: { ...receipt, kind: 'scan' } });
  assert.match(text(tree), /minimum_counts: village: 10/);
  assert.match(text(tree), /Last executed command/);
  assert.match(text(tree), /9007199254741001/);
  assert.match(text(tree), /Copy runnable command/);
});

test('live biome toggles reach the request without changing run controls', () => {
  const config = { ...INITIAL_CONFIG, selectedBiomes: [...SEARCH_PROFILES.dynamic1664.requiredBiomes] };
  const view = sidebar(config);
  view.all.find(n => n.type === 'button' && n.props['aria-label'] === 'Require Deep Dark').props.onClick();
  const changed = view.changed();
  assert.ok(!changed.selectedBiomes.includes('deep_dark'));
  assert.deepEqual([...buildSweepRequest(changed).biomes], [...changed.selectedBiomes]);
  assert.equal(changed.openmpThreads, config.openmpThreads);
  assert.equal(changed.batchSize, config.batchSize);
  assert.ok(sidebar(config, 'targets', true).all.find(n => n.props?.['aria-label'] === 'Require Deep Dark').props.disabled);
  assert.deepEqual([...buildSweepRequest({ ...config, selectedBiomes: [] }).biomes], []);
  assert.throws(() => buildSweepRequest({ ...config, selectedBiomes: ['unsupported'] }), /supported biome/);
});

test('dynamic2048 profile supports live biome toggling and valid sweep requests', () => {
  assert.ok(SEARCH_PROFILES.dynamic2048);
  assert.equal(SEARCH_PROFILES.dynamic2048.revision, 'dynamic-envelope-2048-v3');
  const config = { ...INITIAL_CONFIG, profile: 'dynamic2048',
    structureFloorCounts: { ...SEARCH_PROFILES.dynamic2048.counts },
    requiredStructures: Object.keys(SEARCH_PROFILES.dynamic2048.counts),
    selectedBiomes: [...SEARCH_PROFILES.dynamic2048.requiredBiomes] };
  const view = sidebar(config);
  const deepDarkBtn = view.all.find(n => n.type === 'button' && n.props['aria-label'] === 'Require Deep Dark');
  assert.equal(deepDarkBtn.props.disabled, false);
  deepDarkBtn.props.onClick();
  const changed = view.changed();
  assert.ok(!changed.selectedBiomes.includes('deep_dark'));
  assert.deepEqual([...buildSweepRequest(changed).biomes], [...changed.selectedBiomes]);
});

test('compareCandidateRank prioritizes score for dynamic-envelope-2048-v3', () => {
  const { compareCandidateRank } = load(root + '/web-ui/src/utils/ranking.ts');
  const a = { id: 'a', seed: '1', score: 850, screeningRevision: 'dynamic-envelope-2048-v3', rankingTier: 1, unmetRequirements: 0 };
  const b = { id: 'b', seed: '2', score: 920, screeningRevision: 'dynamic-envelope-2048-v3', rankingTier: 1, unmetRequirements: 0 };
  assert.ok(compareCandidateRank(a, b) > 0); // b ranks higher than a
  assert.ok(compareCandidateRank(b, a) < 0);
});

test('SeedDetailModal renders dynamic-v3 1,250 Pts Max breakdown, nether core badge, and hides deficits when zero', () => {
  const candZeroDeficit = {
    id: 'cand1',
    seed: '12345',
    score: 950,
    bonusTotal: 950,
    deficitPenalty: 0,
    unmetRequirements: 0,
    evaluationCenter: [64, 64],
    structures: [
      { type: 'fortress', x: 8, z: 8 },
      { type: 'bastion', x: 10, z: 10 },
    ],
    scoreComponents: {
      core_surplus: 340,
      optional_bonus: 80,
      luxury_biomes: 120,
      hub_bonus: 45,
      nether_core_bonus: 20,
      scenic_bonus: 25,
      village_spread_bonus: 25,
      treasure_bastion_bonus: 20,
    },
    treasureBastion: 1,
  };
  const modalText = text(SeedDetailModal({ candidate: candZeroDeficit, onClose: noop, onCopyNotice: noop }));
  assert.match(modalText, /Player Quality Score Breakdown \(dynamic-v3: 1,250 Pts Max\)/);
  assert.match(modalText, /Core Surplus/);
  assert.match(modalText, /\+650 max/);
  assert.match(modalText, /Optional Structures/);
  assert.match(modalText, /\+200 max/);
  assert.match(modalText, /Luxury Biomes/);
  assert.match(modalText, /\+265 max/);
  assert.match(modalText, /Spatial & Nether/);
  assert.match(modalText, /\+135 max/);
  assert.match(modalText, /Nether Portal Core/);
  assert.match(modalText, /Fortress ≤256m/);
  assert.match(modalText, /Bastion ≤256m/);
  assert.match(modalText, /Treasure Bastion/);
  assert.match(modalText, /\+20 max \(v3\)/);
  // Zero deficits should hide the deficit penalty card
  assert.doesNotMatch(modalText, /Deficits Penalty/);

  // Candidate with deficit penalty displays the deficit card
  const candWithDeficit = {
    ...candZeroDeficit,
    deficitPenalty: 10,
    unmetRequirements: 1,
    scoreComponents: { ...candZeroDeficit.scoreComponents, deficit_penalty: 10 },
  };
  const modalWithDeficitText = text(SeedDetailModal({ candidate: candWithDeficit, onClose: noop, onCopyNotice: noop }));
  assert.match(modalWithDeficitText, /Deficits Penalty/);
  assert.match(modalWithDeficitText, /missing requirement/);
});


```

---

