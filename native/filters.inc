/* Exact pinned-predictor filters. Included after bridge helpers; no shared MT
 * state is used by the four-lane Mineshaft inventory kernel. */
static uint32_t ss_temper(uint32_t y) {
    y^=y>>11; y^=(y<<7)&UINT32_C(0x9d2c5680);
    y^=(y<<15)&UINT32_C(0xefc60000); return y^(y>>18);
}
static uint32_t ss_twist(uint32_t a,uint32_t b) {
    return (((a&UINT32_C(0x80000000))|(b&UINT32_C(0x7fffffff)))>>1)
        ^((b&1)?UINT32_C(0x9908b0df):0);
}
static void ss_first3(uint32_t seed,uint32_t *out) {
    uint32_t early[4]={seed,0,0,0},v=seed;
    for(uint32_t i=1;i<=399;i++) {
        v=UINT32_C(1812433253)*(v^(v>>30))+i;
        if(i<4)early[i]=v;
        if(i>=397)out[i-397]=ss_temper(v^ss_twist(early[i-397],early[i-396]));
    }
}
#if defined(__GNUC__) || defined(__clang__)
typedef uint32_t SSU4 __attribute__((vector_size(16)));
static SSU4 ss_temper4(SSU4 y) {
    y^=y>>11; y^=(y<<7)&UINT32_C(0x9d2c5680);
    y^=(y<<15)&UINT32_C(0xefc60000); return y^(y>>18);
}
static void ss_second_third4(SSU4 seed,SSU4 *second,SSU4 *third) {
    SSU4 u1=UINT32_C(1812433253)*(seed^(seed>>30))+1;
    SSU4 u2=UINT32_C(1812433253)*(u1^(u1>>30))+2;
    SSU4 u3=UINT32_C(1812433253)*(u2^(u2>>30))+3,v=u3;
    for(uint32_t i=4;i<=398;i++)v=UINT32_C(1812433253)*(v^(v>>30))+i;
    SSU4 a=(((u1&UINT32_C(0x80000000))|(u2&UINT32_C(0x7fffffff)))>>1)^((u2&1)*UINT32_C(0x9908b0df));
    *second=ss_temper4(v^a);
    v=UINT32_C(1812433253)*(v^(v>>30))+399;
    a=(((u2&UINT32_C(0x80000000))|(u3&UINT32_C(0x7fffffff)))>>1)^((u3&1)*UINT32_C(0x9908b0df));
    *third=ss_temper4(v^a);
}
#endif
static int ss_mineshaft_query(SeedContext *ctx,int x0,int z0,int x1,int z1,int *xz,int cap,int first) {
    if(!ctx || !xz || cap<1 || x0>x1 || z0>z1 ||
       x0<-(1<<30) || z0<-(1<<30) || x1>=(1<<30) || z1>=(1<<30) ||
       (int64_t)x1-x0>14000 || (int64_t)z1-z0>14000)return -1;
    int cx0=-floordiv(8-x0,16),cz0=-floordiv(8-z0,16);
    int cx1=floordiv(x1-8,16),cz1=floordiv(z1-8,16),n=0;
    if(cx0>cx1 || cz0>cz1)return 0;
#if defined(__GNUC__) || defined(__clang__)
    uint32_t world[3];ss_first3((uint32_t)ctx->seed,world);
    uint32_t a=world[0]>>1,b=world[1]>>1;
    for(int x=cx0;x<=cx1;x++)for(int z=cz0;z<=cz1;z+=4) {
        SSU4 seeds;
        for(int lane=0;lane<4;lane++)seeds[lane]=((uint32_t)x*a)^((uint32_t)(z+lane)*b)^(uint32_t)ctx->seed;
        SSU4 second,third;ss_second_third4(seeds,&second,&third);
        for(int lane=0;lane<4 && z+lane<=cz1;lane++) {
            int zz=z+lane;
            if((float)(second[lane]*(1.0/4294967296.0))<0.004 &&
               third[lane]%80<(uint32_t)(abs(x)>abs(zz)?abs(x):abs(zz))) {
                n=emit((Pos){x*16+8,zz*16+8},xz,n,cap);
                if(n<0 || first)return n;
            }
        }
    }
#else
    for(int x=cx0;x<=cx1;x++)for(int z=cz0;z<=cz1;z++) {
        Pos p;
        if(getMineshafts(MC_26_50,ctx->seed,x,z,x,z,&p,1)) {
            n=emit(p,xz,n,cap);if(n<0 || first)return n;
        }
    }
#endif
    return n;
}
int ss_mineshaft_first(SeedContext *ctx,int x0,int z0,int x1,int z1,int *xz) {
    return ss_mineshaft_query(ctx,x0,z0,x1,z1,xz,1,1);
}
int ss_mineshaft_inventory(SeedContext *ctx,int x0,int z0,int x1,int z1,int *xz,int cap) {
    return ss_mineshaft_query(ctx,x0,z0,x1,z1,xz,cap,0);
}
int ss_structure_first(SeedContext *ctx,int type,int x0,int z0,int x1,int z1,int *xz) {
    if(type==Mineshaft)return ss_mineshaft_first(ctx,x0,z0,x1,z1,xz);
    StructureConfig cfg;
    if(!ctx || !xz || x0>x1 || z0>z1 || type==Stronghold || !getStructureConfig(type,MC_26_50,&cfg) ||
       x0<-(1<<30) || z0<-(1<<30) || x1>=(1<<30) || z1>=(1<<30) ||
       (int64_t)x1-x0>14000 || (int64_t)z1-z0>14000)return -1;
    Generator *g=ss_generator(ctx,cfg.dim);if(!g)return -1;
    int size=cfg.regionSize*16;
    for(int rx=floordiv(x0,size);rx<=floordiv(x1,size);rx++)
        for(int rz=floordiv(z0,size);rz<=floordiv(z1,size);rz++) {
            Pos p;
            if(getStructurePos(type,MC_26_50,ctx->seed,rx,rz,&p) && inside(p,x0,z0,x1,z1) &&
               isViableStructurePos(type,g,p.x,p.z,0)) {
                xz[0]=p.x;xz[1]=p.z;return 1;
            }
        }
    return 0;
}
int ss_nether_pair(SeedContext *ctx,int x0,int z0,int x1,int z1,int *xzt,int *viable,int cap) {
    StructureConfig cfg;
    if(!ctx || !xzt || !viable || x0>x1 || z0>z1 || cap<1 || !getStructureConfig(Fortress,MC_26_50,&cfg) ||
       x0<-(1<<30) || z0<-(1<<30) || x1>=(1<<30) || z1>=(1<<30) ||
       (int64_t)x1-x0>14000 || (int64_t)z1-z0>14000)return -1;
    int n=0,size=cfg.regionSize*16;
    for(int rx=floordiv(x0,size);rx<=floordiv(x1,size);rx++)
        for(int rz=floordiv(z0,size);rz<=floordiv(z1,size);rz++) {
            Pos p;int fortress=getStructurePos(Fortress,MC_26_50,ctx->seed,rx,rz,&p);
            if(!inside(p,x0,z0,x1,z1))continue;
            if(n>=cap)return -2;
            int type=fortress?Fortress:Bastion;
            xzt[3*n]=p.x;xzt[3*n+1]=p.z;xzt[3*n+2]=fortress;
            viable[n]=!!isViableStructurePos(type,&ctx->nether,p.x,p.z,0);n++;
        }
    return n;
}
static int ss_guaranteed(int type,const int *b) {
    if(type!=Village && type!=Ancient_City)return 0;
    StructureConfig cfg;if(!getStructureConfig(type,MC_26_50,&cfg))return 0;
    int size=cfg.regionSize*16,last=(cfg.chunkRange-1)*16+8;
    int rx0=-floordiv(8-b[0],size),rz0=-floordiv(8-b[1],size);
    int rx1=floordiv(b[2]-last,size),rz1=floordiv(b[3]-last,size);
    if(rx0>rx1 || rz0>rz1)return 0;
    return (rx1-rx0+1)*(rz1-rz0+1);
}
static int ss_capped_raw(uint32_t seed,int type,const int *b,int cap) {
    StructureConfig cfg;getStructureConfig(type,MC_26_50,&cfg);
    if(ss_guaranteed(type,b)>=cap)return cap;
    int n=0,size=cfg.regionSize*16;
    for(int rx=floordiv(b[0],size);rx<=floordiv(b[2],size);rx++)
        for(int rz=floordiv(b[1],size);rz<=floordiv(b[3],size);rz++) {
            Pos p;if(getStructurePos(type,MC_26_50,seed,rx,rz,&p) && inside(p,b[0],b[1],b[2],b[3])) {
                if(++n>=cap)return n;
            }
        }
    return n;
}
/* mode 0=reference full, 1=presence, 2=capped at 32, 3=trim/shared full.
 * Only the reviewed five-family predicate is accepted by optimized modes. */
int ss_sweep_raw_mode(uint64_t start,uint64_t count,const int *types,const int *bounds,
                      int families,int threads,int *counts,uint64_t capacity,int mode) {
    if(mode==0)return ss_sweep_raw(start,count,types,bounds,families,threads,counts,capacity);
    const uint64_t limit=UINT64_C(1)<<32;
    if(mode<1 || mode>3 || start>limit || count>65536 || count>limit-start ||
       families!=5 || !types || !bounds || !counts || capacity<count*5 || threads<1 || threads>36 ||
       (threads>1 && !ss_openmp_enabled()))return -1;
    if(types[0]!=Village || types[1]!=Ancient_City || types[2]!=Fortress || types[3]!=Bastion || types[4]!=Fortress)return -1;
    const int *small=bounds+8,*large=bounds+16;
    for(int k=0;k<4;k++)if(small[k]!=bounds[12+k])return -1;
    if(small[0]<large[0] || small[1]<large[1] || small[2]>large[2] || small[3]>large[3])return -1;
    StructureConfig fc;getStructureConfig(Fortress,MC_26_50,&fc);int size=fc.regionSize*16;
    for(int j=0;j<5;j++) {
        StructureConfig cfg;getStructureConfig(types[j],MC_26_50,&cfg);
        const int *b=bounds+4*j;
        int64_t nx=(int64_t)floordiv(b[2],cfg.regionSize*16)-floordiv(b[0],cfg.regionSize*16)+1;
        int64_t nz=(int64_t)floordiv(b[3],cfg.regionSize*16)-floordiv(b[1],cfg.regionSize*16)+1;
        if(b[0]>b[2] || b[1]>b[3] || nx<1 || nz<1 || nx*nz>4096)return -1;
    }
#ifdef _OPENMP
    #pragma omp parallel for schedule(static) num_threads(threads) if(threads>1 && count>=64)
#endif
    for(uint64_t i=0;i<count;i++) {
        uint32_t seed=(uint32_t)(start+i);int *out=counts+i*5;
        int cap=mode==1?1:mode==2?32:INT_MAX;
        out[0]=ss_capped_raw(seed,Village,bounds,cap);out[1]=ss_capped_raw(seed,Ancient_City,bounds+4,cap);
        out[2]=out[3]=out[4]=0;
        /* Presence scans the small envelope first; shared final Fortress implies
         * initial presence, avoiding an unnecessary broad-region scan. */
        const int *scan=mode==1?small:large;
        for(int rx=floordiv(scan[0],size);rx<=floordiv(scan[2],size);rx++) {
            for(int rz=floordiv(scan[1],size);rz<=floordiv(scan[3],size);rz++) {
                Pos p;int fortress=getStructurePos(Fortress,MC_26_50,seed,rx,rz,&p);
                if(fortress && inside(p,large[0],large[1],large[2],large[3]) && out[4]<cap)out[4]++;
                if(inside(p,small[0],small[1],small[2],small[3])) {
                    int slot=fortress?2:3;if(out[slot]<cap)out[slot]++;
                }
                if(out[2]>=cap && out[3]>=cap && out[4]>=cap)break;
            }
            if(out[2]>=cap && out[3]>=cap && out[4]>=cap)break;
        }
        if(mode==1 && !out[4])out[4]=ss_capped_raw(seed,Fortress,large,1);
    }
    return 0;
}
