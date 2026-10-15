#include "bridge.h"
#include "generator.h"
#include "finders.h"
#include "cave.h"
#include "util.h"
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#ifdef _OPENMP
#include <omp.h>
#endif

/* The opaque handle owns all generator/spline buffers. Never copy it. */
struct SeedContext {
    uint64_t seed;
    Generator overworld, nether, end;
    int end_ready;
    TerrainNoise terrain;
    TerrainShaper shaper;
    int terrain_ready;
    int threads;
};

/* Pinned raw model: the expensive noise term is constant within each eight-Y
 * cell. Preserve the exact scalar expression and all Y decisions; this is not
 * interpolation or a coarse vertical scan. No state crosses columns/seeds. */
typedef struct DensityCell { int y; double noise; } DensityCell;
static double density_cell(const TerrainNoise *terrain, double offset, double factor,
                           int x, int y, int z, DensityCell *cell) {
    int m=floordiv(y,8);
    if (cell->y!=m) {
        cell->noise=sampleSurfaceNoise(&terrain->sn,floordiv(x,4),m,floordiv(z,4))/128.0;
        cell->y=m;
    }
    double g=(1.0-(double)y/128.0)+offset;
    double e=g*factor;
    e *= (e>0.0) ? 4.0 : 1.0;
    double result=e+cell->noise;
    if(result>64.0)result=64.0;
    if(result<-64.0)result=-64.0;
    int yc=m+8;
    result=clampedLerp(((double)(48-yc)-8.0)/2.0,-0.0781250,result);
    result=clampedLerp((double)yc/3.0,0.1171875,result);
    if(result>64.0)result=64.0;
    if(result<-64.0)result=-64.0;
    return result;
}

SeedContext *ss_create(uint64_t seed) {
    SeedContext *ctx = calloc(1, sizeof(*ctx));
    if (!ctx) return NULL;
    ctx->seed = seed;
    ctx->threads = 1;
    setupGenerator(&ctx->overworld, MC_26_50, 0);
    setupGenerator(&ctx->nether, MC_26_50, 0);
    applySeed(&ctx->overworld, DIM_OVERWORLD, seed);
    applySeed(&ctx->nether, DIM_NETHER, seed);
    return ctx;
}
void ss_destroy(SeedContext *ctx) { free(ctx); }
int ss_openmp_enabled(void) {
#ifdef _OPENMP
    return 1;
#else
    return 0;
#endif
}
const char *ss_openmp_library(void) {
#ifdef SS_OPENMP_LIBRARY
    return SS_OPENMP_LIBRARY;
#else
    return NULL;
#endif
}
int ss_set_threads(SeedContext *ctx,int threads) {
    if(!ctx || threads<1 || threads>36 || (threads>1 && !ss_openmp_enabled()))return -1;
    ctx->threads=threads;
    return 0;
}
int ss_model(void) { return MC_26_50; }
const char *ss_model_name(void) { return mc2str(MC_26_50); }
const char *ss_biome_name(int id) {
    /* Pinned util.c omits these existing enum entries. */
    switch (id) {
        case small_end_islands: return "small_end_islands";
        case end_midlands: return "end_midlands";
        case end_highlands: return "end_highlands";
        case end_barrens: return "end_barrens";
        case grove: return "grove";
        case snowy_slopes: return "snowy_slopes";
        case jagged_peaks: return "jagged_peaks";
        case frozen_peaks: return "frozen_peaks";
        default: return biome2str(MC_26_50,id);
    }
}
int ss_biome_catalog(int id,int *dimension,int *generates) {
    if(!dimension || !generates || id<0 || id>255)return -1;
    *dimension=getDimension(id);
    *generates=(*dimension==DIM_OVERWORLD)?isOverworld(MC_26_50,id):biomeExists(MC_26_50,id);
    return biomeExists(MC_26_50,id);
}
int ss_structure_type(const char *name) {
    if (!strcmp(name,"desert_pyramid")) return Desert_Pyramid;
    if (!strcmp(name,"jungle_temple")) return Jungle_Pyramid;
    if (!strcmp(name,"swamp_hut")) return Swamp_Hut;
    if (!strcmp(name,"igloo")) return Igloo;
    if (!strcmp(name,"ocean_ruin")) return Ocean_Ruin;
    if (!strcmp(name,"mansion")) return Mansion;
    if (!strcmp(name,"buried_treasure")) return Treasure;
    if (!strcmp(name,"trail_ruins")) return Trail_Ruins;
    if (!strcmp(name,"abandoned_camp")) return Abandoned_Camp;
    if (!strcmp(name,"ruined_portal_nether")) return Ruined_Portal_N;
    if (!strcmp(name,"end_city")) return End_City;
    if (!strcmp(name,"trial_chamber")) return Trial_Chambers;
    if (!strcmp(name,"stronghold")) return Stronghold;
    if (!strcmp(name,"mineshaft")) return Mineshaft;
    if (!strcmp(name,"ancient_city")) return Ancient_City;
    if (!strcmp(name,"village")) return Village;
    if (!strcmp(name,"ruined_portal")) return Ruined_Portal;
    if (!strcmp(name,"shipwreck")) return Shipwreck;
    if (!strcmp(name,"monument")) return Monument;
    if (!strcmp(name,"outpost")) return Outpost;
    if (!strcmp(name,"fortress")) return Fortress;
    if (!strcmp(name,"bastion")) return Bastion;
    return -1;
}
int ss_structure_rng(int type) {
    StructureConfig config;
    return getStructureConfig(type, MC_26_50, &config) ? config.rngType : -1;
}
static Generator *ss_generator(SeedContext *ctx, int dimension) {
    if (!ctx) return NULL;
    if (dimension == DIM_OVERWORLD) return &ctx->overworld;
    if (dimension == DIM_NETHER) return &ctx->nether;
    if (dimension != DIM_END) return NULL;
    if (!ctx->end_ready) {
        setupGenerator(&ctx->end, MC_26_50, 0);
        applySeed(&ctx->end, DIM_END, ctx->seed);
        ctx->end_ready=1;
    }
    return &ctx->end;
}
int ss_biome(SeedContext *ctx, int dimension, int x, int y, int z) {
    Generator *g=ss_generator(ctx, dimension);
    if (!g) return none;
    if (dimension==DIM_OVERWORLD) {
        int x4,y4,z4;
        voronoiAccess3D(g->sha,x,y,z,&x4,&y4,&z4);
        /* Exact single-point MC_26_50 path. NULL hint preserves tie handling. */
        return sampleBiomeNoise(&g->bn,NULL,x4,y4,z4,NULL,0);
    }
    if (dimension==DIM_END) {
        Range r={1,x,z,1,1,y,1},s=getVoronoiSrcRange(r);
        int64_t a=llabs(floordiv(s.x,4)),b=llabs(floordiv(s.x+s.sx-1,4));
        int64_t c=llabs(floordiv(s.z,4)),d=llabs(floordiv(s.z+s.sz-1,4));
        int64_t mx=a>b?a:b,mz=c>d?c:d;
        if(mx*mx+mz*mz<=4096)return the_end;
        /* The pinned End adapter uses its own planar Voronoi helper. Do not
         * substitute Overworld's 3D nearest-cell rule. */
    }
    return getBiomeAt(g,1,x,y,z);
}
int ss_grid(SeedContext *ctx, int x0, int z0, int nx, int nz, int step,
            int y, int *biomes, double *climate, double *approx_height) {
    if (!ctx || !biomes || !climate || !approx_height || nx < 1 || nz < 1 || step < 1) return -1;
#ifdef _OPENMP
    #pragma omp parallel for schedule(static) num_threads(ctx->threads) if(ctx->threads>1 && nx*nz>=256)
#endif
    for (int z = 0; z < nz; z++) for (int x = 0; x < nx; x++) {
        int bx = x0 + x*step, bz = z0 + z*step;
        int i = z*nx + x;
        int64_t np[6];
        biomes[i] = getBiomeAt(&ctx->overworld,1,bx,y,bz);
        /* Depth at y=0, matching this fork's mapApproxHeight heuristic. */
        sampleBiomeNoise(&ctx->overworld.bn,np,floordiv(bx,4),0,
                         floordiv(bz,4),NULL,SAMPLE_NO_BIOME);
        for (int k=0;k<6;k++) climate[6*i+k] = np[k] / 10000.0;
        approx_height[i] = np[NP_DEPTH] / 76.0;
    }
    return 0;
}
int ss_heights(SeedContext *ctx, const int *xz, int n, int vertical_step,
               int *heights, int *surface_biomes) {
    if (!ctx || !xz || !heights || !surface_biomes || n < 0 || vertical_step < 1 || vertical_step > 16) return -1;
    if (!ctx->terrain_ready) {
        initTerrainNoise(&ctx->terrain,ctx->seed);
        initTerrainShaper(&ctx->shaper);
        ctx->terrain_ready = 1;
    }
#ifdef _OPENMP
    #pragma omp parallel for schedule(static) num_threads(ctx->threads) if(ctx->threads>1 && n>=256)
#endif
    for (int i=0;i<n;i++) {
        int x=xz[2*i], z=xz[2*i+1], top=-65;
        double offset, factor;
        DensityCell cell={INT_MIN,0};
        sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,
                           floordiv(x,4),floordiv(z,4),&offset,&factor);
        /* Raw density estimate: excludes cave, aquifer, decoration and
           actual chunk interpolation. Coarse scans can miss thin overhangs. */
        for (int y=319;;y-=vertical_step) {
            if (y < -64) y=-64;
            if (density_cell(&ctx->terrain,offset,factor,x,y,z,&cell)>0) {
                top=y;
                for (int yy=y+vertical_step-1;yy>y;yy--) {
                    if (yy<=319 && density_cell(&ctx->terrain,offset,factor,x,yy,z,&cell)>0) {
                        top=yy; break;
                    }
                }
                break;
            }
            if (y==-64) break;
        }
        heights[i]=top;
        int sample_y=top<63 ? 63 : top+1;
        surface_biomes[i]=getBiomeAt(&ctx->overworld,1,x,sample_y,z);
    }
    return 0;
}
static int inside(Pos p,int x0,int z0,int x1,int z1) {
    return p.x>=x0 && p.x<=x1 && p.z>=z0 && p.z<=z1;
}
static int emit(Pos p,int *out,int n,int cap) {
    if (n>=cap) return -2;
    out[2*n]=p.x; out[2*n+1]=p.z;
    return n+1;
}
/* Generator-free adapter, restricted to reviewed low32 MT families. */
int ss_raw_layout(uint32_t low32,int type,int x0,int z0,int x1,int z1,int *xz,int capacity) {
    if (!(type==Village || type==Ancient_City || type==Ruined_Portal ||
          type==Shipwreck || type==Monument || type==Outpost ||
          type==Fortress || type==Bastion)) return -1;
    StructureConfig cfg;
    if (x0>x1 || z0>z1 || capacity<1 || !getStructureConfig(type,MC_26_50,&cfg)) return -1;
    int n=0,size=cfg.regionSize*16;
    for (int rx=floordiv(x0,size)-1;rx<=floordiv(x1,size)+1;rx++)
        for (int rz=floordiv(z0,size)-1;rz<=floordiv(z1,size)+1;rz++) {
            Pos p;
            if (!getStructurePos(type,MC_26_50,(uint64_t)low32,rx,rz,&p) || !inside(p,x0,z0,x1,z1)) continue;
            n=emit(p,xz,n,capacity);
            if (n<0) return n;
        }
    return n;
}
/* Version 1: finite all-input counts, explicit inclusive regions, no generator or
 * viability. Native bounded batches never truncate scan coverage/top selection.
 * getStructurePos re-seeds the pinned thread-local MT for each region. */
int ss_sweep_raw(uint64_t start,uint64_t count,const int *types,const int *bounds,
                 int families,int threads,int *counts,uint64_t capacity) {
    const uint64_t limit=UINT64_C(1)<<32;
    if(start>limit || count>65536 || count>limit-start || families<1 || families>8 ||
       capacity<count*(uint64_t)families || threads<1 || threads>36 ||
       (threads>1 && !ss_openmp_enabled()))return -1;
    StructureConfig configs[8];
    for(int j=0;j<families;j++) {
        int t=types[j];const int *b=bounds+4*j;
        if(!(t==Village || t==Ancient_City || t==Ruined_Portal || t==Shipwreck ||
             t==Monument || t==Outpost || t==Fortress || t==Bastion) ||
           b[0]>b[2] || b[1]>b[3] || !getStructureConfig(t,MC_26_50,&configs[j]))return -1;
        int size=configs[j].regionSize*16;
        /* Bound work per seed, including the exact one-region reference halo. */
        int64_t nx=(int64_t)floordiv(b[2],size)-floordiv(b[0],size)+3;
        int64_t nz=(int64_t)floordiv(b[3],size)-floordiv(b[1],size)+3;
        if(nx<1 || nz<1 || nx>4096 || nz>4096 || nx*nz>4096)return -1;
    }
#ifdef _OPENMP
    #pragma omp parallel for schedule(static) num_threads(threads) if(threads>1 && count>=64)
#endif
    for(uint64_t i=0;i<count;i++) {
        uint32_t seed=(uint32_t)(start+i);
        for(int j=0;j<families;j++) {
            int size=configs[j].regionSize*16,n=0;const int *b=bounds+4*j;
            for(int rx=floordiv(b[0],size)-1;rx<=floordiv(b[2],size)+1;rx++)
                for(int rz=floordiv(b[1],size)-1;rz<=floordiv(b[3],size)+1;rz++) {
                    Pos p;
                    if(getStructurePos(types[j],MC_26_50,seed,rx,rz,&p) && inside(p,b[0],b[1],b[2],b[3]))n++;
                }
            counts[i*families+j]=n;
        }
    }
    return 0;
}
int ss_biome_points(SeedContext *ctx,int dimension,const int *xyz,int n,int *biomes) {
    if (n<0 || !ss_generator(ctx,dimension) || (n && (!xyz || !biomes))) return -1;
    /* End point queries otherwise build overlapping 27-cell height halos for
     * every point. Share one bounded reference map for dense batches. The
     * exact End planar Voronoi and negative-coordinate rules remain.
     * All temporary memory belongs to this call, before any parallel loop. */
    if (dimension==DIM_END && n>=256 && n<=100000) {
        int *cells=malloc((size_t)n*4*sizeof(*cells));
        if (cells) {
            int x0=INT_MAX,z0=INT_MAX,x1=INT_MIN,z1=INT_MIN;
            for (int i=0;i<n;i++) {
                Range r={1,xyz[3*i],xyz[3*i+2],1,1,xyz[3*i+1],1},s=getVoronoiSrcRange(r);
                cells[4*i]=s.x;cells[4*i+1]=s.z;cells[4*i+2]=s.sx;cells[4*i+3]=s.sz;
                int cx=floordiv(s.x,4),cz=floordiv(s.z,4);
                int hx=floordiv(s.x+s.sx-1,4),hz=floordiv(s.z+s.sz-1,4);
                if(cx<x0)x0=cx;if(hx>x1)x1=hx;
                if(cz<z0)z0=cz;if(hz>z1)z1=hz;
            }
            int64_t w=(int64_t)x1-x0+1,h=(int64_t)z1-z0+1,area=w*h;
            if(w<=1024 && h<=1024 && area<=65536 && area<=(int64_t)n*128) {
                int *map=malloc((size_t)area*sizeof(*map));
                if(map) {
                    mapEndBiome(&ctx->end.en,map,x0,z0,(int)w,(int)h);
                    for(int i=0;i<n;i++) {
                        int px=cells[4*i],pz=cells[4*i+1],pw=cells[4*i+2],ph=cells[4*i+3],src[9];
                        for(int j=0;j<ph;j++)for(int k=0;k<pw;k++)
                            src[j*pw+k]=map[(floordiv(pz+j,4)-z0)*w+floordiv(px+k,4)-x0];
                        mapVoronoiPlane(ctx->end.sha,biomes+i,src,xyz[3*i],xyz[3*i+2],1,1,xyz[3*i+1],px,pz,pw,ph);
                    }
                    free(map);free(cells);return 0;
                }
            }
            free(cells);
        }
    }
#ifdef _OPENMP
    #pragma omp parallel for schedule(static) num_threads(ctx->threads) if(ctx->threads>1 && n>=256)
#endif
    for (int i=0;i<n;i++) biomes[i]=ss_biome(ctx,dimension,xyz[3*i],xyz[3*i+1],xyz[3*i+2]);
    return 0;
}
#include "filters.inc"
int ss_scan(SeedContext *ctx,int type,int x0,int z0,int x1,int z1,
            int viable_only,int *xz,int capacity) {
    StructureConfig cfg;
    if (x0>x1 || z0>z1 || capacity<1 || !getStructureConfig(type,MC_26_50,&cfg)) return -1;
    int n=0;
    if (type==Mineshaft) {
return ss_mineshaft_inventory(ctx,x0,z0,x1,z1,xz,capacity);
    }
    int size=cfg.regionSize*16;
    Generator *g=ss_generator(ctx,cfg.dim);
    if (!g) return -1;
    /* Only Stronghold has reviewed starts displaced outside its region. */
    int halo=type==Stronghold ? 1 : 0;
    for (int rx=floordiv(x0,size)-halo;rx<=floordiv(x1,size)+halo;rx++) {
        for (int rz=floordiv(z0,size)-halo;rz<=floordiv(z1,size)+halo;rz++) {
            Pos p;
            int found=getStructurePos(type,MC_26_50,ctx->seed,rx,rz,&p);
            /* Keep the selected Bedrock structure type. Promoting a rejected
             * Bastion to a Fortress produced the absent seed-12345 start at
             * (-152,120); phone inspection supplied the negative fixture. */
            if (!found || !inside(p,x0,z0,x1,z1)) continue;
            if (viable_only && type!=Stronghold && !isViableStructurePos(type,g,p.x,p.z,0)) continue;
            n=emit(p,xz,n,capacity);
            if (n<0) return n;
        }
    }
    if (type==Stronghold) {
        StrongholdIter it={0};
        for (int i=0;i<3;i++) {
            nextVillageStronghold(&it,&ctx->overworld);
            if (inside(it.pos,x0,z0,x1,z1)) {
                n=emit(it.pos,xz,n,capacity);
                if (n<0) return n;
            }
        }
    }
    return n;
}
int ss_attempt(SeedContext *ctx,int type,int rx,int rz,int *xz) {
    if (type<0 || type==Mineshaft) return -1;
    Pos p;
    int ok=getStructurePos(type,MC_26_50,ctx->seed,rx,rz,&p);
    if (ok) { xz[0]=p.x; xz[1]=p.z; }
    return ok;
}
/* Validate enumerated starts without repeating placement or Stronghold iteration.
 * Match ss_scan's special adapters: those two families never veto raw starts. */
int ss_filter_starts(SeedContext *ctx,int type,const int *xz,int n,int *viable) {
    StructureConfig cfg;
    if (n<0 || !getStructureConfig(type,MC_26_50,&cfg)) return -1;
    Generator *g=ss_generator(ctx,cfg.dim);
    if (!g) return -1;
    for (int i=0;i<n;i++)
        viable[i]=(type==Stronghold || type==Mineshaft) ? 1 :
            !!isViableStructurePos(type,g,xz[2*i],xz[2*i+1],0);
    return 0;
}
/* Expose the actual viability sampling convention for evidence, not a new rule.
 * out: quart x/y/z, sampled biome, rotation, variant, offset x/z, size x/z. */
int ss_diagnostic(SeedContext *ctx, int type, int x, int z, int *out) {
    if (type == Ancient_City) {
        out[0]=x>>2; out[1]=-27>>2; out[2]=z>>2;
        out[3]=getBiomeAt(&ctx->overworld,0,out[0],out[1],out[2]);
        for (int i=4;i<10;i++) out[i]=0;
        return 1;
    }
    if (type != Bastion) return 0;
    StructureVariant sv;
    if (!getVariant(&sv,Bastion,MC_26_50,ctx->seed,x,z,-1)) return 0;
    int cx=x>>4,cz=z>>4;
    out[0]=(cx*32+2*sv.x+sv.sx-1)/2>>2;
    out[1]=33>>2;
    out[2]=(cz*32+2*sv.z+sv.sz-1)/2>>2;
    out[3]=getBiomeAt(&ctx->nether,4,out[0],out[1],out[2]);
    out[4]=sv.rotation;out[5]=sv.start;
    out[6]=sv.x;out[7]=sv.z;out[8]=sv.sx;out[9]=sv.sz;
    return 1;
}
/* Exact sea-level classification relative to the stride-one raw density model.
 * Checking upward permits early success for land while retaining thin overhangs.
 * Unlike a monotonic/binary-search shortcut, every Y>=63 is checked for water. */
static int land_column(SeedContext *ctx,int x,int z) {
    double offset,factor;
    DensityCell cell={INT_MIN,0};
    sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,floordiv(x,4),floordiv(z,4),&offset,&factor);
    for(int y=63;y<=319;y++)
        if(density_cell(&ctx->terrain,offset,factor,x,y,z,&cell)>0)return 1;
    return 0;
}
typedef struct LandCell { int x,z,representative; } LandCell;
static uint64_t land_hash(int x,int z) {
    uint64_t key=((uint64_t)(uint32_t)x<<32)|(uint32_t)z;
    key^=key>>30;key*=UINT64_C(0xbf58476d1ce4e5b9);
    key^=key>>27;key*=UINT64_C(0x94d049bb133111eb);
    return key^(key>>31);
}
int ss_land(SeedContext *ctx, const int *xz, int n, int *land) {
    if (!ctx || !xz || !land || n<0 || n>100000) return -1;
    if (!ctx->terrain_ready) {
        initTerrainNoise(&ctx->terrain,ctx->seed);
        initTerrainShaper(&ctx->shaper);
        ctx->terrain_ready=1;
    }
    if(n<16) {
        for(int i=0;i<n;i++)land[i]=land_column(ctx,xz[2*i],xz[2*i+1]);
        return 0;
    }
    size_t size=16;
    while(size<(size_t)n*2)size*=2;
    LandCell *cells=calloc(size,sizeof(*cells));
    int *representatives=malloc((size_t)n*sizeof(*representatives));
    if(!cells || !representatives) {free(cells);free(representatives);return -1;}
    for(int i=0;i<n;i++) {
        int x=floordiv(xz[2*i],4),z=floordiv(xz[2*i+1],4);
        size_t slot=(size_t)land_hash(x,z)&(size-1);
        while(cells[slot].representative && (cells[slot].x!=x || cells[slot].z!=z))slot=(slot+1)&(size-1);
        if(!cells[slot].representative) {
            cells[slot]=(LandCell){x,z,i+1};
        }
        representatives[i]=cells[slot].representative-1;
    }
    /* Immutable mapping is constructed serially. Each representative/output has
     * one owner; broadcast only after the team joins. Sampling is read-only. */
#ifdef _OPENMP
    #pragma omp parallel for schedule(static) num_threads(ctx->threads) if(ctx->threads>1 && n>=256)
#endif
    for(int i=0;i<n;i++)if(representatives[i]==i)land[i]=land_column(ctx,xz[2*i],xz[2*i+1]);
    for(int i=0;i<n;i++)land[i]=land[representatives[i]];
    free(cells);free(representatives);
    return 0;
}

/* Diagnostic interface for exact raw-density parity/calibration. */
int ss_density_points(SeedContext *ctx,const int *xyz,int n,double *out) {
    if (!ctx || !xyz || !out || n<0 || n>100000) return -1;
    if(!ctx->terrain_ready) {
        initTerrainNoise(&ctx->terrain,ctx->seed);
        initTerrainShaper(&ctx->shaper);ctx->terrain_ready=1;
    }
    for(int i=0;i<n;i++) {
        int x=xyz[3*i],y=xyz[3*i+1],z=xyz[3*i+2];double offset,factor;
        DensityCell cell={INT_MIN,0};
        sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,floordiv(x,4),floordiv(z,4),&offset,&factor);
        out[i]=density_cell(&ctx->terrain,offset,factor,x,y,z,&cell);
    }
    return 0;
}

/* Variant evidence is a pinned predictor, not observed generated loot. */
int ss_igloo_basement(SeedContext *ctx,int x,int z) {
    StructureVariant variant={0};
    if(!ctx||!getVariant(&variant,Igloo,MC_26_50,ctx->seed,x,z,-1))return -1;
    return !!variant.basement;
}
