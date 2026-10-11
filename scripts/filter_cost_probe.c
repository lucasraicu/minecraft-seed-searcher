/* Private diagnostics appended to a copy of bridge.c. Never linked into the
 * installed backend. All shortcuts target the pinned predictor, not the game. */
#include "mt.h"

static uint32_t diag_temper(uint32_t y) {
    y ^= y >> 11; y ^= (y << 7) & UINT32_C(0x9d2c5680);
    y ^= (y << 15) & UINT32_C(0xefc60000); return y ^ (y >> 18);
}
static uint32_t diag_twist(uint32_t a,uint32_t b) {
    return (((a & UINT32_C(0x80000000)) | (b & UINT32_C(0x7fffffff))) >> 1)
        ^ ((b & 1) ? UINT32_C(0x9908b0df) : 0);
}
static void diag_first3(uint32_t seed,uint32_t *out) {
    uint32_t early[4]={seed,0,0,0},v=seed;
    for(uint32_t i=1;i<=399;i++) {
        v=UINT32_C(1812433253)*(v^(v>>30))+i;
        if(i<4)early[i]=v;
        if(i>=397)out[i-397]=diag_temper(v^diag_twist(early[i-397],early[i-396]));
    }
}
int diag_mt_parity(const uint32_t *seeds,int n) {
    for(int i=0;i<n;i++) {
        uint32_t v[3];diag_first3(seeds[i],v);mt_seed(seeds[i]);
        for(int j=0;j<3;j++)if(v[j]!=mt_next())return i+1;
    }
    return 0;
}
typedef uint32_t DiagU4 __attribute__((vector_size(16)));
static DiagU4 diag_temper4(DiagU4 y) {
    y ^= y >> 11; y ^= (y << 7) & UINT32_C(0x9d2c5680);
    y ^= (y << 15) & UINT32_C(0xefc60000); return y ^ (y >> 18);
}
static DiagU4 diag_twist4(DiagU4 a,DiagU4 b) {
    return (((a & UINT32_C(0x80000000)) | (b & UINT32_C(0x7fffffff))) >> 1)
        ^ ((b & 1)*UINT32_C(0x9908b0df));
}
static void diag_second_third4(DiagU4 seeds,DiagU4 *second,DiagU4 *third) {
    DiagU4 u1=UINT32_C(1812433253)*(seeds^(seeds>>30))+1;
    DiagU4 u2=UINT32_C(1812433253)*(u1^(u1>>30))+2;
    DiagU4 u3=UINT32_C(1812433253)*(u2^(u2>>30))+3,v=u3;
    for(uint32_t i=4;i<=398;i++)v=UINT32_C(1812433253)*(v^(v>>30))+i;
    *second=diag_temper4(v^diag_twist4(u1,u2));
    v=UINT32_C(1812433253)*(v^(v>>30))+399;
    *third=diag_temper4(v^diag_twist4(u2,u3));
}
int diag_mineshaft(SeedContext *ctx,int x0,int z0,int x1,int z1,
                  int mode,int *xz,int cap,int *visited) {
    if(mode<0 || mode>2 || x0>x1 || z0>z1 || cap<1)return -1;
    /* Only chunks whose +8 start can belong to the inclusive query. */
    int cx0=-floordiv(8-x0,16),cz0=-floordiv(8-z0,16);
    int cx1=floordiv(x1-8,16),cz1=floordiv(z1-8,16),n=0;
    *visited=0;
    if(cx0>cx1 || cz0>cz1)return 0;
    if(mode<2) {
        for(int x=cx0;x<=cx1;x++)for(int z=cz0;z<=cz1;z++) {
            Pos p;(*visited)++;
            if(getMineshafts(MC_26_50,ctx->seed,x,z,x,z,&p,1)) {
                n=emit(p,xz,n,cap);if(n<0 || mode==1)return n;
            }
        }
        return n;
    }
    uint32_t world[3];diag_first3((uint32_t)ctx->seed,world);
    uint32_t a=world[0]>>1,b=world[1]>>1;
    for(int x=cx0;x<=cx1;x++)for(int z=cz0;z<=cz1;z+=4) {
        DiagU4 seeds;
        for(int lane=0;lane<4;lane++)seeds[lane]=((uint32_t)x*a)^((uint32_t)(z+lane)*b)^(uint32_t)ctx->seed;
        DiagU4 second,third;diag_second_third4(seeds,&second,&third);
        for(int lane=0;lane<4 && z+lane<=cz1;lane++) {
            int zz=z+lane;(*visited)++;
            if((float)(second[lane]*(1.0/4294967296.0))<0.004 &&
               third[lane]%80 < (uint32_t)(abs(x)>abs(zz) ? abs(x) : abs(zz))) {
                n=emit((Pos){x*16+8,zz*16+8},xz,n,cap);if(n<0)return n;
            }
        }
    }
    return n;
}
int diag_biomes(SeedContext *ctx,const int *xyz,int n,int *out,int mode,int threads) {
    if(mode<0 || mode>2 || n<0 || threads<1 || threads>36)return -1;
    if(mode==0)return ss_biome_points(ctx,DIM_OVERWORLD,xyz,n,out);
    uint64_t hint=0;
#ifdef _OPENMP
    #pragma omp parallel for schedule(static) num_threads(threads) if(threads>1 && mode==1)
#endif
    for(int i=0;i<n;i++) {
        int x4,y4,z4;
        voronoiAccess3D(ctx->overworld.sha,xyz[3*i],xyz[3*i+1],xyz[3*i+2],&x4,&y4,&z4);
        /* The hint arm is a deliberately untrusted experiment: equal-distance
         * ties can change IDs. Only mode 1 preserves the source's NULL hint. */
        out[i]=sampleBiomeNoise(&ctx->overworld.bn,NULL,x4,y4,z4,mode==2 ? &hint : NULL,0);
    }
    return 0;
}
int diag_region_size(int type) {
    StructureConfig cfg;return getStructureConfig(type,MC_26_50,&cfg) ? cfg.regionSize*16 : -1;
}
int diag_guaranteed_count(int type,const int *b) {
    if(type!=Village && type!=Ancient_City)return 0;
    StructureConfig cfg;if(!getStructureConfig(type,MC_26_50,&cfg))return 0;
    int size=cfg.regionSize*16,last=(cfg.chunkRange-1)*16+8;
    int rx0=-floordiv(8-b[0],size),rz0=-floordiv(8-b[1],size);
    int rx1=floordiv(b[2]-last,size),rz1=floordiv(b[3]-last,size);
    if(rx0>rx1 || rz0>rz1)return 0;
    return (rx1-rx0+1)*(rz1-rz0+1);
}
static int diag_raw_count(uint32_t seed,int type,const int *b,int cap) {
    int size=diag_region_size(type),n=0;
    if(diag_guaranteed_count(type,b)>=cap)return cap;
    for(int rx=floordiv(b[0],size);rx<=floordiv(b[2],size);rx++)
        for(int rz=floordiv(b[1],size);rz<=floordiv(b[3],size);rz++) {
            Pos p;if(getStructurePos(type,MC_26_50,seed,rx,rz,&p) && inside(p,b[0],b[1],b[2],b[3])) {
                n++;if(n>=cap)return n;
            }
        }
    return n;
}
int diag_raw_sweep(uint64_t start,uint64_t count,const int *types,const int *bounds,
                   int families,int threads,int *counts,uint64_t capacity,int mode) {
    if(mode==0)return ss_sweep_raw(start,count,types,bounds,families,threads,counts,capacity);
    if(mode<1 || mode>4 || start+count>(UINT64_C(1)<<32) || count>65536 || families!=5 || capacity<count*5)return -1;
    if(types[0]!=Village || types[1]!=Ancient_City || types[2]!=Fortress || types[3]!=Bastion || types[4]!=Fortress)return -1;
    const int *small=bounds+8,*bastion=bounds+12,*large=bounds+16;
    for(int k=0;k<4;k++)if(small[k]!=bastion[k])return -1;
    if(small[0]<large[0] || small[1]<large[1] || small[2]>large[2] || small[3]>large[3])return -1;
#ifdef _OPENMP
    #pragma omp parallel for schedule(static) num_threads(threads) if(threads>1 && count>=64)
#endif
    for(uint64_t i=0;i<count;i++) {
        uint32_t seed=(uint32_t)(start+i);int *out=counts+i*5;
        if(mode==1 || mode>=3) {
            int cap=mode==3 ? 1 : mode==4 ? 32 : INT_MAX;
            for(int j=0;j<5;j++)out[j]=diag_raw_count(seed,types[j],bounds+j*4,cap);
            continue;
        }
        out[0]=diag_raw_count(seed,Village,bounds,INT_MAX);out[1]=diag_raw_count(seed,Ancient_City,bounds+4,INT_MAX);
        out[2]=out[3]=out[4]=0;int size=diag_region_size(Fortress);
        for(int rx=floordiv(large[0],size);rx<=floordiv(large[2],size);rx++)
            for(int rz=floordiv(large[1],size);rz<=floordiv(large[3],size);rz++) {
                Pos p;int fortress=getStructurePos(Fortress,MC_26_50,seed,rx,rz,&p);
                if(fortress && inside(p,large[0],large[1],large[2],large[3]))out[4]++;
                if(inside(p,small[0],small[1],small[2],small[3]))out[fortress ? 2 : 3]++;
            }
    }
    return 0;
}
