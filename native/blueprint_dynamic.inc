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
        if(mansion_goal>0 && mansions && nm>0) {
            for(int m=0;m<nm;m++) {
                int lx=mansions[m].x-(ow_half-1),lz=mansions[m].z-(ow_half-1);
                int ux=mansions[m].x+ow_half,uz=mansions[m].z+ow_half;
                if(lx<x)lx=x;if(lz<z)lz=z;if(ux>hx)ux=hx;if(uz>hz)uz=hz;
                lx=-floordiv(-lx,8)*8;lz=-floordiv(-lz,8)*8;
                ux=floordiv(ux,8)*8;uz=floordiv(uz,8)*8;
                if(lx>ux||lz>uz)continue;
                mansion_overlap=1;
                if(lx<xmin)xmin=lx;if(lz<zmin)zmin=lz;
                if(ux>xmax)xmax=ux;if(uz>zmax)zmax=uz;
            }
            continue;
        }
        if(x<xmin)xmin=x;if(z<zmin)zmin=z;if(hx>xmax)xmax=hx;if(hz>zmax)zmax=hz;
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
    Pos mansions[64];int nm=0;
    int mansion_goal=(w->p->flexible_mask&(1u<<0))?w->p->floors[0]:w->p->goals[0];
    Pos dark_mansions[64];int nm_dark=0;
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
        applySeedPhase1(&w->ctx->overworld,DIM_OVERWORLD,w->ctx->seed);
        for(int m=0;m<nm;m++) {
            if(isMansionDarkForestPossible(&w->ctx->overworld.bn,w->ctx->overworld.sha,mansions[m].x,mansions[m].z)) {
                dark_mansions[nm_dark++]=mansions[m];
            }
        }
        if(nm_dark<mansion_goal)return 0;
    }
    int fort[512],bast[512],pairs[768],nf=0,nb=0;
    int max_c = 2000 - w->p->overworld_half;
    int nw_bound = floordiv(max_c, 8) + w->p->nether_half;
    int n=ss_nether_raw_pair(w->ctx,-nw_bound,-nw_bound,nw_bound-1,nw_bound-1,pairs,256);
    if(n<0)return n;
    for(int i=0;i<n;i++) {
        int *points=pairs[3*i+2]?fort:bast;int at=pairs[3*i+2]?nf++:nb++;
        points[2*at]=pairs[3*i];points[2*at+1]=pairs[3*i+1];
    }
    int mansion_overlap=0;
    int possible=nb_dynamic_raw_bounds_core(fort,nf,bast,nb,w->p->nether_goal,w->p->bastion_goal,feasible,
                                           mansion_goal>0?dark_mansions:NULL,nm_dark,mansion_goal,&mansion_overlap,
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
            int count=0;
            for(int m=0;m<nm_dark;m++)
                if(inside(dark_mansions[m],feasible[0],feasible[1],feasible[2],feasible[3]))count++;
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
#ifdef _OPENMP
            #pragma omp atomic
#endif
            g_diag_pass_mansion_dark++;
            if(!NB_DYNAMIC_PREFLIGHT ||
               ((w->p->flexible_mask&1u)?w->p->floors[0]:w->p->goals[0])<=0)
                applySeedPhase1(&w->ctx->overworld,DIM_OVERWORLD,seed);
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
