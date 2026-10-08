#include "bridge.h"
#include "generator.h"
#include "finders.h"
#include "cave.h"
#include "util.h"
#include <stdlib.h>
#include <string.h>

/* The opaque handle owns all generator/spline buffers. Never copy it. */
struct SeedContext {
    uint64_t seed;
    Generator overworld, nether;
    TerrainNoise terrain;
    TerrainShaper shaper;
    int terrain_ready;
};

SeedContext *ss_create(uint64_t seed) {
    SeedContext *ctx = calloc(1, sizeof(*ctx));
    if (!ctx) return NULL;
    ctx->seed = seed;
    setupGenerator(&ctx->overworld, MC_26_50, 0);
    setupGenerator(&ctx->nether, MC_26_50, 0);
    applySeed(&ctx->overworld, DIM_OVERWORLD, seed);
    applySeed(&ctx->nether, DIM_NETHER, seed);
    return ctx;
}
void ss_destroy(SeedContext *ctx) { free(ctx); }
int ss_model(void) { return MC_26_50; }
const char *ss_model_name(void) { return mc2str(MC_26_50); }
const char *ss_biome_name(int id) {
    /* Pinned util.c omits these existing enum entries. */
    switch (id) {
        case grove: return "grove";
        case snowy_slopes: return "snowy_slopes";
        case jagged_peaks: return "jagged_peaks";
        case frozen_peaks: return "frozen_peaks";
        default: return biome2str(MC_26_50,id);
    }
}
int ss_structure_type(const char *name) {
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
int ss_biome(SeedContext *ctx, int dimension, int x, int y, int z) {
    Generator *g = dimension == DIM_OVERWORLD ? &ctx->overworld : &ctx->nether;
    return getBiomeAt(g, 1, x, y, z);
}
int ss_grid(SeedContext *ctx, int x0, int z0, int nx, int nz, int step,
            int y, int *biomes, double *climate, double *approx_height) {
    if (nx < 1 || nz < 1 || step < 1) return -1;
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
    if (n < 0 || vertical_step < 1 || vertical_step > 16) return -1;
    if (!ctx->terrain_ready) {
        initTerrainNoise(&ctx->terrain,ctx->seed);
        initTerrainShaper(&ctx->shaper);
        ctx->terrain_ready = 1;
    }
    for (int i=0;i<n;i++) {
        int x=xz[2*i], z=xz[2*i+1], top=-65;
        double offset, factor;
        sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,
                           floordiv(x,4),floordiv(z,4),&offset,&factor);
        /* Raw density estimate: excludes cave, aquifer, decoration and
           actual chunk interpolation. Coarse scans can miss thin overhangs. */
        for (int y=319;;y-=vertical_step) {
            if (y < -64) y=-64;
            if (sampleTerrainDensity(&ctx->terrain,offset,factor,x,y,z)>0) {
                top=y;
                for (int yy=y+vertical_step-1;yy>y;yy--) {
                    if (yy<=319 && sampleTerrainDensity(&ctx->terrain,offset,factor,x,yy,z)>0) {
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
int ss_scan(SeedContext *ctx,int type,int x0,int z0,int x1,int z1,
            int viable_only,int *xz,int capacity) {
    StructureConfig cfg;
    if (x0>x1 || z0>z1 || capacity<1 || !getStructureConfig(type,MC_26_50,&cfg)) return -1;
    int n=0;
    if (type==Mineshaft) {
        /* Source uses inclusive END chunks, despite stale header width docs. */
        Pos *p=malloc(sizeof(*p)*capacity);
        if (!p) return -1;
        int count=getMineshafts(MC_26_50,ctx->seed,floordiv(x0,16),floordiv(z0,16),
                               floordiv(x1,16),floordiv(z1,16),p,capacity);
        if (count>capacity) { free(p); return -2; }
        for (int i=0;i<count;i++) if (inside(p[i],x0,z0,x1,z1)) {
            n=emit(p[i],xz,n,capacity);
            if (n<0) break;
        }
        free(p); return n;
    }
    int size=cfg.regionSize*16;
    Generator *g=cfg.dim==DIM_NETHER ? &ctx->nether : &ctx->overworld;
    /* One-region halo includes displaced static Stronghold starts. */
    for (int rx=floordiv(x0,size)-1;rx<=floordiv(x1,size)+1;rx++) {
        for (int rz=floordiv(z0,size)-1;rz<=floordiv(z1,size)+1;rz++) {
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
    Generator *g=cfg.dim==DIM_NETHER ? &ctx->nether : &ctx->overworld;
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
int ss_land(SeedContext *ctx, const int *xz, int n, int *land) {
    if (n<0) return -1;
    if (!ctx->terrain_ready) {
        initTerrainNoise(&ctx->terrain,ctx->seed);
        initTerrainShaper(&ctx->shaper);
        ctx->terrain_ready=1;
    }
    for (int i=0;i<n;i++) {
        int x=xz[2*i],z=xz[2*i+1];
        double offset,factor;
        sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,floordiv(x,4),floordiv(z,4),&offset,&factor);
        land[i]=0;
        for (int y=63;y<=319;y++) {
            if (sampleTerrainDensity(&ctx->terrain,offset,factor,x,y,z)>0) {
                land[i]=1;break;
            }
        }
    }
    return 0;
}
