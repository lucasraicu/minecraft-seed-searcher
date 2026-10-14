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
        for(int i=0;i<n;i++){w->scratch[2*i]=b[0]+800+i*16;w->scratch[2*i+1]=b[1]+800;}
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
        if(a->biome_mask==8191&&!w->p->complete&&!w->p->origin)break;
        int end=offset+batch;if(end>n*4)end=n*4;
        for(int i=offset;i<end;i++) {
            int index=(int)(((int64_t)(i/4)*stride)%n),layer=i%4;
            int x=x0+(index%nx)*step,z=z0+(index/nx)*step,y=w->p->y[layer];
            int id=nb_point(w,x,y,z),k=a->biome_n++;
            a->biome_xyz[3*k]=x;a->biome_xyz[3*k+1]=y;a->biome_xyz[3*k+2]=z;a->biome_ids[k]=id;
            if(w->p->origin&&y==63&&id>=0&&id<256)a->bonus_biomes|=(unsigned int)w->p->bonus_biome_members[id];
            unsigned int mask=(id>=0&&id<256)?w->p->biome_members[id]:0;
            mask&=(y==-48||y==0)?7168:1023;
            for(int f=0;f<13;f++)if((mask&(1u<<f))&&!(a->biome_mask&(1u<<f)))a->first_witness[f]=k;
            a->biome_mask|=mask;
        }
    }
    a->biome_evaluated=1;return 0;
}
static int nb_score(NBWorker *w,NBAnchor *a) {
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
                (n[2]>=2?10:0)+(n[1]>=2?10:0)+(n[3]>=2?25:0)+
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
        score+=(n[3]>=2?25:0)+n[12]*10;
        return score;
    }
    int n[13];for(int i=0;i<13;i++)n[i]=nb_observed_count(w,a->observations+i,i);
    int score=(n[5]>5?(n[5]-5)*5:0)+(n[7]>3?(n[7]-3)*5:0)+
              (n[8]>2?(n[8]-2)*5:0)+(n[9]>5?n[9]-5:0);
    score+=(n[6]>2?((n[6]<4?n[6]:4)-2)*10:0);
    for(int i=4;i<=11;i++)if(i==4||i==10||i==11)score+=(n[i]>1?((n[i]<3?n[i]:3)-1)*15:0);
    for(int i=1;i<=2;i++)score+=(n[i]>=2?20:0)+(n[i]>=3?10:0);
    score+=(n[3]>=2?25:0)+n[12]*10;
    return score;
}
static void nb_clear_anchor(NBAnchor *a) {
    for(int k=0;k<13;k++){nb_clear_full(a->observations+k);nb_clear_points(&a->observations[k].floor);}
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
static int nb_keep(const NBWorker *w,const NBAnchor *a) {
    if(w->p->two_group)
        return a->stronghold_count>=1 && nb_budget_ok(w,a) && a->biome_evaluated && a->biome_mask==8191;
    return (!w->p->origin||a->stronghold_count>=1) && a->biome_evaluated && nb_bits((unsigned int)a->count_missing)+13-nb_bits(a->biome_mask)<=w->p->max_misses;
}
static int nb_eval(NBWorker *w,uint64_t seed,NBResult *r) {
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
        if((nb_budget_ok(w,a)&&a->biome_mask==8191)||(w->p->retention&&nb_keep(w,a))) {
            t=nb_time();
            for(int slot=0;slot<10;slot++)if(!(w->p->locked&&(slot==3||slot==8))&&!a->observations[slot].full){
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
    if((p->locked!=0&&p->locked!=1)||(p->river!=0&&p->river!=1)||(p->river&&!p->locked)||(p->origin!=0&&p->origin!=1)||(p->two_group!=0&&p->two_group!=1)||(p->two_group&&!p->origin)||(p->origin&&(!p->locked||!p->river||p->outpost_goal!=(p->two_group?1:2))))return NULL;
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
               ((i==1||i==2)&&p->goals[i]!=1))return NULL;
        } else if(p->goals[i]!=(p->river&&i==8?5:p->locked?new_goals[i]:old_goals[i]))return NULL;
    }
    if(p->two_group) {
        if(p->flexible_mask!=group_flexible||p->max_misses>8)return NULL;
        for(int i=0;i<13;i++)if(p->floors[i]!=group_floors[i])return NULL;
    }
    for(int i=0;i<4;i++)if(p->y[i]!=y[i])return NULL;
    if(fixtures)for(int i=0;i<count;i++)if(fixtures[i].x<-1000000||fixtures[i].x>1000000||fixtures[i].z<-1000000||fixtures[i].z>1000000||
        fixtures[i].missing<-1||fixtures[i].missing>28||fixtures[i].deficit_depth<1||fixtures[i].deficit_depth>32)return NULL;
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
    for(int i=0;i<batch->count;i++) {
        nb_clear_result(batch->results+i);
    }
    free(batch->verdicts);free(batch->results);free(batch);
}
