/* Exact event-cell selector for the 1664/832 dynamic predictor. */
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
static int nb_dynamic_nearest(int lo,int hi) {
    return lo<=0&&hi>=0?0:hi<0?hi:lo;
}
static void nb_dynamic_event(int *events,int *n,int value) {
    if(value>-1168&&value<=1168)events[(*n)++]=value;
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
static unsigned int nb_dynamic_palette_mask(const int *p,int x,int z) {
    int x0=-floordiv(-((x-832)+1984),64),z0=-floordiv(-((z-832)+1984),64);
    int x1=-floordiv(-((x+832)+1984),64),z1=-floordiv(-((z+832)+1984),64);
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
    if(!w->dyn_nether_prefix) {
        w->dyn_nether_prefix=nb_alloc(w,5*18*18*sizeof(int),0);
        if(!w->dyn_nether_prefix)return -3;
    }
    if(!w->dyn_nether_grid) {
        w->dyn_nether_grid=nb_alloc(w,18*18*sizeof(int),0);
        if(!w->dyn_nether_grid)return -3;
    }
    int *p=w->dyn_nether_prefix;
    memset(p,0,5*18*18*sizeof(int));
    for(int ix=1;ix<=17;ix++)for(int iz=1;iz<=17;iz++) {
        int id=nb_dynamic_nether_point(w,-512+(ix-1)*64,-512+(iz-1)*64);
        w->dyn_nether_grid[ix*18+iz]=id;
        for(int k=0;k<5;k++) {
            int at=k*18*18+ix*18+iz;
            p[at]=p[at-18]+p[at-1]-p[at-19]+(id==w->p->nether_ids[k]);
        }
    }
    *out=p;return 0;
}
static int nb_dynamic_nether_ok(const int *p,int x,int z) {
    int x0=-floordiv(-(x-3328+4096),512),z0=-floordiv(-(z-3328+4096),512);
    int x1=-floordiv(-(x+3328+4096),512),z1=-floordiv(-(z+3328+4096),512);
    for(int f=0;f<5;f++) {
        const int *a=p+f*18*18;
        if(!(a[x1*18+z1]-a[x0*18+z1]-a[x1*18+z0]+a[x0*18+z0]))return 0;
    }
    return 1;
}
static int nb_dynamic_nether_evidence(NBWorker *w,NBAnchor *a) {
    a->nether_biome_xyz=nb_alloc(w,169*3*sizeof(int),0);
    a->nether_biome_ids=nb_alloc(w,169*sizeof(int),0);
    if(!a->nether_biome_xyz||!a->nether_biome_ids)return -3;
    int x0=-floordiv(-(a->x-3328),512)*64,z0=-floordiv(-(a->z-3328),512)*64;
    for(int iz=0;iz<13;iz++)for(int ix=0;ix<13;ix++) {
        int x=x0+ix*64,z=z0+iz*64,k=a->nether_biome_n++;
        a->nether_biome_xyz[3*k]=x;a->nether_biome_xyz[3*k+1]=64;a->nether_biome_xyz[3*k+2]=z;
        int id;
        if(w->dyn_nether_grid && x>=-512 && x<=576 && z>=-512 && z<=576) {
            int gix=(x-(-512))/64+1,giz=(z-(-512))/64+1;
            if(gix>=1 && gix<=17 && giz>=1 && giz<=17)id=w->dyn_nether_grid[gix*18+giz];
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
static int nb_dynamic_captured(int px,int pz,int x,int z) {
    return x-832<=px&&px<x+832&&z-832<=pz&&pz<z+832;
}
static void nb_dynamic_centroid(const NBObservation *macro,const NBPoints *strong,int x,int z,
                                int64_t *sx,int64_t *sz,int *weight,int dark_id) {
    *sx=*sz=0;*weight=0;
    for(int k=-1;k<13;k++) {
        int w=k<0?1:nb_centroid_weights[k];if(!w)continue;
        const NBPoints *p=k<0?strong:&macro[k].viable;
        for(int i=0;i<p->n;i++) {
            int px=p->xz[2*i],pz=p->xz[2*i+1];
            if(k==0&&macro[0].mansion_ids[i]!=dark_id)continue;
            if(nb_dynamic_captured(px,pz,x,z)) {*sx+=(int64_t)w*px;*sz+=(int64_t)w*pz;*weight+=w;}
        }
    }
}
static double nb_dynamic_radial(const NBObservation *macro,const NBPoints *strong,int x,int z,int weight,int dark_id) {
    double distance=0;
    for(int k=-1;k<13;k++) {
        int w=k<0?1:nb_centroid_weights[k];if(!w)continue;
        const NBPoints *p=k<0?strong:&macro[k].viable;
        for(int i=0;i<p->n;i++) {
            int px=p->xz[2*i],pz=p->xz[2*i+1];
            if(k==0&&macro[0].mansion_ids[i]!=dark_id)continue;
            if(nb_dynamic_captured(px,pz,x,z))distance+=w*hypot((double)px-x,(double)pz-z);
        }
    }
    return weight?distance/weight:0;
}
static int nb_dynamic_hub(const NBObservation *macro,int x,int z) {
    const int slots[5]={5,2,1,12,7};int bonus=0;
    for(int j=0;j<5;j++) {
        const NBPoints *p=&macro[slots[j]].viable;
        for(int i=0;i<p->n;i++) {
            int64_t dx=p->xz[2*i]-x,dz=p->xz[2*i+1]-z;
            if(nb_dynamic_captured(p->xz[2*i],p->xz[2*i+1],x,z)&&dx*dx+dz*dz<=512*512)bonus+=j==4?4:6;
        }
    }
    return bonus>40?40:bonus;
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
int nb_dynamic_raw_bounds(const int *fort,int nf,const int *bast,int nb,int fort_goal,int bast_goal,int *feasible) {
    if(!fort||!bast||!feasible||nf<0||nb<0||nf>256||nb>256||fort_goal<1||bast_goal<1)return -1;
    if(nf<fort_goal||nb<bast_goal)return 0;
    int xs[1030],zs[1030],nx=2,nz=2;
    xs[0]=zs[0]=-1168;xs[1]=zs[1]=1169;
    for(int k=0;k<2;k++) {
        int n=k?nb:nf;const int *points=k?bast:fort;
        for(int i=0;i<n;i++) {
            nb_dynamic_event(xs,&nx,8*(points[2*i]-416)+1);
            nb_dynamic_event(xs,&nx,8*(points[2*i]+416)+1);
            nb_dynamic_event(zs,&nz,8*(points[2*i+1]-416)+1);
            nb_dynamic_event(zs,&nz,8*(points[2*i+1]+416)+1);
        }
    }
    nx=nb_dynamic_unique(xs,nx);nz=nb_dynamic_unique(zs,nz);
    NBPoints fp={nf,(int*)fort},bp={nb,(int*)bast};int xmin=1169,zmin=1169,xmax=-1169,zmax=-1169;
    for(int ix=0;ix<nx-1;ix++)for(int iz=0;iz<nz-1;iz++) {
        int x=-floordiv(-xs[ix],8)*8,z=-floordiv(-zs[iz],8)*8;
        if(x>=xs[ix+1]||z>=zs[iz+1])continue;
        if(nb_dynamic_count(&fp,x,z,416,1,NULL,0)<fort_goal ||
           nb_dynamic_count(&bp,x,z,416,1,NULL,0)<bast_goal)continue;
        int hx=floordiv(xs[ix+1]-1,8)*8,hz=floordiv(zs[iz+1]-1,8)*8;
        if(x<xmin)xmin=x;if(z<zmin)zmin=z;if(hx>xmax)xmax=hx;if(hz>zmax)zmax=hz;
    }
    if(xmin>xmax||zmin>zmax)return 0;
    feasible[0]=xmin-832;feasible[1]=zmin-832;feasible[2]=xmax+831;feasible[3]=zmax+831;
    return 1;
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
    int n=ss_nether_raw_pair(w->ctx,-562,-562,561,561,pairs,256);
    if(n<0)return n;
    for(int i=0;i<n;i++) {
        int *points=pairs[3*i+2]?fort:bast;int at=pairs[3*i+2]?nf++:nb++;
        points[2*at]=pairs[3*i];points[2*at+1]=pairs[3*i+1];
    }
    int possible=nb_dynamic_raw_bounds(fort,nf,bast,nb,w->p->nether_goal,w->p->bastion_goal,feasible);
    if(possible<=0)return possible;
    const int slots[5]={12,0,6,4,5};
    for(int j=0;j<5;j++) {
        int slot=slots[j];
        int goal=(w->p->flexible_mask&(1u<<slot))?w->p->floors[slot]:(slot==12?w->p->outpost_goal:w->p->goals[slot]);
        if(goal<=0)continue;
        int ok=nb_raw_atleast(w,w->p->types[slot],feasible,goal);
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
           nb_point(w,p.x,63,p.z)==w->p->dark_id&&++n>=w->p->goals[0])return 1;
      }
    return 0;
}
static int nb_eval_dynamic(NBWorker *w,uint64_t seed,NBResult *r) {
    double start=nb_time();r->seed=seed;
    NB_PROFILE_SEED(w,seed);
#ifndef NB_DISABLE_MANSION_CACHE
    w->mansion_cache_n=0;
#endif
    if(!w->ctx)return -3;
    w->ctx->seed=seed;
    int code=0;const int ow[4]={-2000,-2000,1999,1999};
    const int nw[4]={-562,-562,561,561};
    double stage=nb_time();
    NBObservation macro[13]={0},optional[5]={0};NBAnchor nether_macro={0};int *ex=NULL,*ez=NULL,*prefix=NULL,*nether_prefix=NULL;
    NBDynamicCell *cells=NULL;int nx=0,nz=0,ncells=0,optional_evaluated=0;
    int feasible[4]={-2000,-2000,1999,1999},possible=1;
    /* Compact rejects carry a range decision, not an invented discovery row.
     * Defer Stronghold's expensive village path until raw floors can succeed. */
    if(w->p->retention) {
        stage=nb_time();possible=nb_dynamic_raw_preflight(w,feasible);
        r->stage_seconds[11]+=nb_time()-stage;
        if(possible<0){code=possible;goto done;}if(!possible)goto done;
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
    if(w->p->retention)applySeed(&w->ctx->overworld,DIM_OVERWORLD,seed);
    /* One inexpensive macro Mansion preflight before all other structure inventories. */
    stage=nb_time();
    possible=nb_audit_dark_possible(w,feasible);
    if(possible<0){code=possible;goto done;}if(!possible)goto done;
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
    applySeed(&w->ctx->nether,DIM_NETHER,seed);
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
    if(w->dyn_cells_cap<maxcells) {
        size_t need=maxcells+1024;
        void *new_cells=nb_alloc(w,need*sizeof(NBDynamicCell),0);
        if(!new_cells){code=-3;goto done;}
        free(w->dyn_cells);
        w->dyn_cells=new_cells;
        w->dyn_cells_cap=need;
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
        if(!(nb_dynamic_snap(ez[iz],ez[iz+1]-1,sz,weight,16,&zz)||
             nb_dynamic_snap(ez[iz],ez[iz+1]-1,sz,weight,8,&zz)))continue;
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
