/* Experimental four-Y AVX2 density kernel, appended to a private bridge copy.
 * Based on the pinned cubiomes-bedrock samplePerlin/sampleSurfaceNoise/density
 * equations (MIT; see vendor/cubiomes-bedrock/LICENSE). Never installed by this
 * test. Scalar permutation lookups and gradients; packed four-lane interpolation
 * and octave accumulation. No FMA or reassociation in the strict variant.
 */
#include <immintrin.h>
typedef __m256d V4;
static inline V4 vs(double x) { return _mm256_set1_pd(x); }
static inline V4 va(V4 a,V4 b) { return _mm256_add_pd(a,b); }
static inline V4 vb(V4 a,V4 b) { return _mm256_sub_pd(a,b); }
static inline V4 vm(V4 a,V4 b) { return _mm256_mul_pd(a,b); }
static inline V4 vl(V4 t,V4 a,V4 b) { return va(a,vm(t,vb(b,a))); }
static inline V4 vcl(V4 t,V4 a,V4 b) {
    V4 r=vl(t,a,b);
    r=_mm256_blendv_pd(r,a,_mm256_cmp_pd(t,vs(0),_CMP_LE_OQ));
    return _mm256_blendv_pd(r,b,_mm256_cmp_pd(t,vs(1),_CMP_GE_OQ));
}
static inline double grad4(uint8_t h,double a,double b,double c) {
    switch(h&15) {
    case 0:return a+b;case 1:return -a+b;case 2:return a-b;case 3:return -a-b;
    case 4:return a+c;case 5:return -a+c;case 6:return a-c;case 7:return -a-c;
    case 8:return b+c;case 9:return -b+c;case 10:return b-c;case 11:return -b-c;
    case 12:return a+b;case 13:return -b+c;case 14:return -a+b;default:return -b-c;
    }
}
static inline V4 perlin4(const PerlinNoise *noise,double x,V4 y,double z,
                          double yamp,V4 ymin) {
    double dx=x+noise->a,dz=z+noise->c;
    double ix=floor(dx),iz=floor(dz);dx-=ix;dz-=iz;
    uint8_t hx=(int)ix,hz=(int)iz;
    double tx=dx*dx*dx*(dx*(dx*6.0-15.0)+10.0);
    double tz=dz*dz*dz*(dz*(dz*6.0-15.0)+10.0);
    V4 zero=_mm256_cmp_pd(y,vs(0),_CMP_EQ_OQ);
    V4 yy=va(y,vs(noise->b)),iy=_mm256_floor_pd(yy);
    V4 dy=vb(yy,iy);
    V4 ty=vm(vm(vm(dy,dy),dy),va(vm(dy,vb(vm(dy,vs(6)),vs(15))),vs(10)));
    dy=_mm256_blendv_pd(dy,vs(noise->d2),zero);
    ty=_mm256_blendv_pd(ty,vs(noise->t2),zero);
    iy=_mm256_blendv_pd(iy,vs(noise->h2),zero);
    if(yamp) {
        V4 clamped=_mm256_blendv_pd(dy,ymin,_mm256_cmp_pd(ymin,dy,_CMP_LT_OQ));
        dy=vb(dy,vm(_mm256_floor_pd(_mm256_div_pd(clamped,vs(yamp))),vs(yamp)));
    }
    double ys[4],is[4],g[8][4];
    _mm256_storeu_pd(ys,dy);_mm256_storeu_pd(is,iy);
    const uint8_t *idx=noise->d;
    for(int lane=0;lane<4;lane++) {
        uint8_t hy=(int)is[lane];double v=ys[lane];
        uint8_t a1=idx[hx]+hy,b1=idx[hx+1]+hy;
        uint8_t a2=idx[a1]+hz,b2=idx[b1]+hz;
        uint8_t a3=idx[a1+1]+hz,b3=idx[b1+1]+hz;
        g[0][lane]=grad4(idx[a2],dx,v,dz);
        g[1][lane]=grad4(idx[b2],dx-1,v,dz);
        g[2][lane]=grad4(idx[a3],dx,v-1,dz);
        g[3][lane]=grad4(idx[b3],dx-1,v-1,dz);
        g[4][lane]=grad4(idx[a2+1],dx,v,dz-1);
        g[5][lane]=grad4(idx[b2+1],dx-1,v,dz-1);
        g[6][lane]=grad4(idx[a3+1],dx,v-1,dz-1);
        g[7][lane]=grad4(idx[b3+1],dx-1,v-1,dz-1);
    }
    V4 a=vl(vs(tx),_mm256_loadu_pd(g[0]),_mm256_loadu_pd(g[1]));
    V4 b=vl(vs(tx),_mm256_loadu_pd(g[2]),_mm256_loadu_pd(g[3]));
    V4 c=vl(vs(tx),_mm256_loadu_pd(g[4]),_mm256_loadu_pd(g[5]));
    V4 d=vl(vs(tx),_mm256_loadu_pd(g[6]),_mm256_loadu_pd(g[7]));
    return vl(vs(tz),vl(ty,a,b),vl(ty,c,d));
}
static V4 surface4(const SurfaceNoise *sn,int x,V4 y,int z) {
    double xs=684.412*sn->xzScale,ys=684.412*sn->yScale;
    double xstep=xs/sn->xzFactor,ystep=ys/sn->yFactor;
    V4 min=vs(0),max=vs(0),main=vs(0);
    double persist=1,contrib=1;
    for(int i=0;i<16;i++) {
        double dx=x*xs*persist,dz=z*xs*persist,sy=ys*persist;
        V4 dy=vm(vm(y,vs(ys)),vs(persist)),ty=vm(y,vs(sy));
        min=va(min,vm(perlin4(&sn->octmin.octaves[i],dx,dy,dz,sy,ty),vs(contrib)));
        max=va(max,vm(perlin4(&sn->octmax.octaves[i],dx,dy,dz,sy,ty),vs(contrib)));
        if(i<8) {
            dx=x*xstep*persist;dz=z*xstep*persist;sy=ystep*persist;
            dy=vm(vm(y,vs(ystep)),vs(persist));ty=vm(y,vs(sy));
            main=va(main,vm(perlin4(&sn->octmain.octaves[i],dx,dy,dz,sy,ty),vs(contrib)));
        }
        persist*=.5;contrib*=2;
    }
    return vcl(va(vs(.5),vm(vs(.05),main)),_mm256_div_pd(min,vs(512)),_mm256_div_pd(max,vs(512)));
}
static void density4(const TerrainNoise *tn,double offset,double factor,
                      int x,const int *y,int z,double *out) {
    double yd[4],md[4];
    for(int i=0;i<4;i++){yd[i]=y[i];md[i]=floordiv(y[i],8);}
    V4 m=_mm256_loadu_pd(md),yv=_mm256_loadu_pd(yd);
    V4 d=_mm256_div_pd(surface4(&tn->sn,floordiv(x,4),m,floordiv(z,4)),vs(128));
    V4 g=va(vb(vs(1),_mm256_div_pd(yv,vs(128))),vs(offset));
    V4 e=vm(g,vs(factor));
    e=vm(e,_mm256_blendv_pd(vs(1),vs(4),_mm256_cmp_pd(e,vs(0),_CMP_GT_OQ)));
    V4 r=va(e,d);
    r=_mm256_max_pd(vs(-64),_mm256_min_pd(vs(64),r));
    V4 yc=va(m,vs(8));
    r=vcl(_mm256_div_pd(vb(vb(vs(48),yc),vs(8)),vs(2)),vs(-.078125),r);
    r=vcl(_mm256_div_pd(yc,vs(3)),vs(.1171875),r);
    r=_mm256_max_pd(vs(-64),_mm256_min_pd(vs(64),r));
    _mm256_storeu_pd(out,r);
}
static void ready4(SeedContext *ctx) {
    if(!ctx->terrain_ready){initTerrainNoise(&ctx->terrain,ctx->seed);initTerrainShaper(&ctx->shaper);ctx->terrain_ready=1;}
}
int ss_heights(SeedContext *ctx,const int *xz,int n,int stride,int *heights,int *biomes) {
    if(n<0||stride<1||stride>16)return -1;
    ready4(ctx);
    for(int i=0;i<n;i++) {
        int x=xz[2*i],z=xz[2*i+1],top=-65;double offset,factor;
        sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,floordiv(x,4),floordiv(z,4),&offset,&factor);
        for(int y=319;;y-=4*stride) {
            int ys[4];double d[4];for(int j=0;j<4;j++)ys[j]=y-j*stride < -64 ? -64 : y-j*stride;
            density4(&ctx->terrain,offset,factor,x,ys,z,d);
            for(int j=0;j<4;j++)if(d[j]>0) {
                top=ys[j];
                for(int yy=top+stride-1;yy>ys[j];yy--) {
                    if(yy<=319&&sampleTerrainDensity(&ctx->terrain,offset,factor,x,yy,z)>0){top=yy;break;}
                }
                break;
            }
            if(top!=-65||ys[3]==-64)break;
        }
        heights[i]=top;biomes[i]=getBiomeAt(&ctx->overworld,1,x,top<63?63:top+1,z);
    }
    return 0;
}
int ss_land(SeedContext *ctx,const int *xz,int n,int *land) {
    if(n<0)return -1;ready4(ctx);
    for(int i=0;i<n;i++) {
        int x=xz[2*i],z=xz[2*i+1];double offset,factor;
        sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,floordiv(x,4),floordiv(z,4),&offset,&factor);
        land[i]=0;
        for(int y=63;y<=319;y+=4) {
            int ys[4];double d[4];for(int j=0;j<4;j++)ys[j]=y+j>319?319:y+j;
            density4(&ctx->terrain,offset,factor,x,ys,z,d);
            if(d[0]>0||d[1]>0||d[2]>0||d[3]>0){land[i]=1;break;}
        }
    }
    return 0;
}
int ss_probe_density4(SeedContext *ctx,const int *xyz,int n,double *out) {
    ready4(ctx);
    for(int i=0;i<n;i+=4) {
        if(i+4>n)return -1;
        int x=xyz[3*i],z=xyz[3*i+2],ys[4];double offset,factor;
        for(int j=0;j<4;j++){if(xyz[3*(i+j)]!=x||xyz[3*(i+j)+2]!=z)return -2;ys[j]=xyz[3*(i+j)+1];}
        sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,floordiv(x,4),floordiv(z,4),&offset,&factor);
        density4(&ctx->terrain,offset,factor,x,ys,z,out+i);
    }
    return 0;
}
