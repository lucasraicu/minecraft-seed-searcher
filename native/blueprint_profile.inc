/* Include instead of blueprint_batch.inc in a separate diagnostic extension. */
#include "blueprint_batch.h"
#include "blueprint_profile.h"
static double nb_time(void);
static void nb_timing(NBTiming *t,double seconds,int x,int y,int z) {
    if(!t->count || seconds<t->min_seconds)t->min_seconds=seconds;
    if(!t->count || seconds>t->max_seconds){t->max_seconds=seconds;t->max_x=x;t->max_y=y;t->max_z=z;}
    t->count++;t->total_seconds+=seconds;
    double ns=seconds*1e9;int bin=0;
    while(bin<31 && ns>=2.0){ns*=0.5;bin++;}
    t->bins[bin]++;
}
#define NB_PROFILE_BIND(w,p,i) ((w)->profile=(p)?((NBProfileSample *)(p))+(i):NULL)
#define NB_PROFILE_SEED(w,s) do {if((w)->profile)((NBProfileSample *)(w)->profile)->seed=(s);} while(0)
#define NB_PROFILE_CACHE(w,hit) do {if((w)->profile){NBProfileSample *np=(NBProfileSample *)(w)->profile;np->mansion_queries++;np->mansion_cache_hits+=(hit);}} while(0)
#define NB_PROFILE_STAGE(w,k,s,x,z) do {if((w)->profile)nb_timing(&((NBProfileSample *)(w)->profile)->stages[k],s,x,0,z);} while(0)
#define NB_PROFILE_POINT_BEGIN(w) double nb_query_started=(w)->profile?nb_time():0
#define NB_PROFILE_POINT_END(w,id,x,y,z) do {if((w)->profile){ \
    NBProfileSample *np=(NBProfileSample *)(w)->profile;double elapsed=nb_time()-nb_query_started; \
    if((id)>=0 && (id)<256)nb_timing(np->biome_ids+(id),elapsed,x,y,z); \
    for(int ny=0;ny<4;ny++)if((y)==(w)->p->y[ny]){nb_timing(np->biome_y+ny,elapsed,x,y,z);break;} \
    unsigned int mask=((id)>=0 && (id)<256)?(w)->p->biome_members[id]:0; \
    mask&=((y)==-48||(y)==0)?7168:1023; \
    for(int family=0;family<13;family++)if(mask&(1u<<family))nb_timing(np->biome_families+family,elapsed,x,y,z); \
}} while(0)
#define NB_PROFILE_INVENTORY_BEGIN(w) double nb_inventory_started=(w)->profile?nb_time():0
#define NB_PROFILE_INVENTORY_END(w,k,x,z) NB_PROFILE_STAGE(w,14+(k),nb_time()-nb_inventory_started,x,z)

/* The public header lacks a guard because CFFI reads it verbatim; the batch
 * implementation uses this marker to avoid including it a second time. */
#define NB_HEADER_INCLUDED 1
#include "blueprint_batch.inc"

NBProfileBatch *nb_profile_sweep(const uint64_t *seeds,int count,const NBPolicy *p,int threads) {
    if(count<1 || count>512 || (uint64_t)count*sizeof(NBProfileSample)>(64ULL<<20))return NULL;
    NBProfileBatch *profile=calloc(1,sizeof(*profile));if(!profile)return NULL;
    profile->count=count;profile->samples=calloc((size_t)count,sizeof(NBProfileSample));
    if(!profile->samples){free(profile);return NULL;}
    profile->batch=nb_run(seeds,NULL,count,p,threads,profile->samples);
    if(!profile->batch){nb_profile_free(profile);return NULL;}
    /* Complete diagnostic probes inventory Outpost even when the target fails.
     * This is separate forced work, never an active-pipeline eligibility change. */
    if(p->complete) {
        uint64_t allocated=0;
        NBWorker w={0};w.p=p;w.allocated_bytes=&allocated;w.ctx=ss_create(0);
        if(!w.ctx){nb_profile_free(profile);return NULL;}
        for(int i=0;i<count;i++) {
            NBResult *r=profile->batch->results+i;w.profile=profile->samples+i;
            w.ctx->seed=seeds[i];applySeed(&w.ctx->overworld,DIM_OVERWORLD,seeds[i]);
            applySeed(&w.ctx->nether,DIM_NETHER,seeds[i]);
            for(int j=0;j<r->nanchors;j++) {
                NBAnchor *a=r->anchors+j;
                for(int slot=10;slot<=12;slot++) {
                    if(slot==12 && (p->locked||a->observations[12].evaluated))continue;
                    int nx=-floordiv(-a->x,8),nz=-floordiv(-a->z,8);
                    int b[4]={slot==12?a->x-p->overworld_half:nx-p->nether_half,slot==12?a->z-p->overworld_half:nz-p->nether_half,
                              slot==12?a->x+p->overworld_half-1:nx+p->nether_half-1,slot==12?a->z+p->overworld_half-1:nz+p->nether_half-1};
                    NBObservation out={0};double t=nb_time();int code=nb_pair(&w,slot,b,&out);
                    NB_PROFILE_STAGE(&w,slot==12?26:27+slot-10,nb_time()-t,a->x,a->z);
                    nb_clear_full(&out);if(code){profile->batch->error=code;break;}
                }
            }
        }
        ss_destroy(w.ctx);free(w.scratch);free(w.flags);
    }
    return profile;
}
void nb_profile_free(NBProfileBatch *profile) {
    if(!profile)return;
    nb_free(profile->batch);free(profile->samples);free(profile);
}
