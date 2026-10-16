# Minecraft Seed Searcher — Full Source Code Bundle for Deep Audit

> **Files Included:**

> 1. `native/blueprint_dynamic.inc`

> 2. `native/blueprint_batch.inc`

> 3. `src/seed_search/realm/blueprint.py`

> 4. `src/seed_search/realm/dynamic.py`

---

## File: `native/blueprint_dynamic.inc` (C11 Dynamic Envelope Evaluation Kernel)

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

## File: `native/blueprint_batch.inc` (C11 OpenMP Batch Runner & Memory Manager)

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

## File: `src/seed_search/realm/blueprint.py` (Python Reference Scoring Oracle & Differential Evaluator)

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

## File: `src/seed_search/realm/dynamic.py` (Python Spatial Helpers & Nether Lattice Sampler)

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
