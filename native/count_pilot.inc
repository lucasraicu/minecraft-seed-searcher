/* Diagnostic count-N kernels: compiled beside, never replacing, production. */
#define PC_MAX 32
#define PC_FAMILIES 22
int pc_bits(int type) {
    StructureConfig c;
    if(type==Stronghold)return 64;
    if(type==Mineshaft)return 32;
    if(!getStructureConfig(type,MC_26_50,&c))return -1;
    return c.rngType==JAVA_RANDOM?48:32;
}
static uint64_t pc_seed(uint64_t seed,int bits) {
    return bits==32?(uint32_t)seed:bits==48?seed&UINT64_C(0xffffffffffff):seed;
}
static int pc_valid(const int *b,int goal) {
    return b && goal>=1 && goal<=PC_MAX && b[0]<=b[2] && b[1]<=b[3] &&
           b[0]>=-(1<<30) && b[1]>=-(1<<30) && b[2]<(1<<30) && b[3]<(1<<30) &&
           (int64_t)b[2]-b[0]<=14000 && (int64_t)b[3]-b[1]<=14000;
}
static int pc_strongholds(SeedContext *ctx,const int *b,int goal,const int *allow,int y,int *stats) {
    int pts[4096*2],n=ss_scan(ctx,Stronghold,b[0],b[1],b[2],b[3],1,pts,4096),count=0;
    if(n<0)return n;
    for(int i=0;i<n;i++) {
        int duplicate=0;
        for(int j=0;j<i;j++)if(pts[2*i]==pts[2*j] && pts[2*i+1]==pts[2*j+1]){duplicate=1;break;}
        if(!duplicate) {
            if(allow) {stats[2]++;int id=ss_biome(ctx,0,pts[2*i],y,pts[2*i+1]);if(id<0 || id>=256 || !allow[id])continue;}
            if(++count==goal)return count;
        }
    }
    return count;
}
/* Prefix retains candidates and the region cursor. No raw re-enumeration is
 * needed when a fused caller proceeds to viability after obtaining N starts. */
static int pc_prefix_uncached(SeedContext *ctx,int type,const int *b,int goal,Pos *out,int *cursor,int *stats) {
    if(type==Stronghold)return -1;
    if(type==Mineshaft) {
        int xy[2*PC_MAX];
        int n=pc_mineshaft_query(ctx,b[0],b[1],b[2],b[3],xy,goal,0);
        for(int i=0;i<n;i++)out[i]=(Pos){xy[2*i],xy[2*i+1]};
        *cursor=-1;return n;
    }
    StructureConfig cfg;getStructureConfig(type,MC_26_50,&cfg);
    int size=cfg.regionSize*16,rx0=floordiv(b[0],size),rz0=floordiv(b[1],size);
    int nx=floordiv(b[2],size)-rx0+1,nz=floordiv(b[3],size)-rz0+1,n=0;
    uint64_t seed=pc_seed(ctx->seed,pc_bits(type));
    while(*cursor<nx*nz) {
        int index=(*cursor)++;Pos p;stats[0]++;
        if(getStructurePos(type,MC_26_50,seed,rx0+index/nz,rz0+index%nz,&p) && inside(p,b[0],b[1],b[2],b[3])) {
            out[n++]=p;if(n==goal)break;
        }
    }
    return n;
}
/* Bounded direct-mapped cache stores only immutable raw prefixes. */
typedef struct PCCache { int valid,type,b[4],goal,n,cursor;uint64_t seed;Pos p[PC_MAX]; } PCCache;
static PCCache pc_cache[4096];
static int pc_cache_enabled=0;
void pc_cache_reset(int enabled) {memset(pc_cache,0,sizeof(pc_cache));pc_cache_enabled=!!enabled;}
static int pc_prefix(SeedContext *ctx,int type,const int *b,int goal,Pos *out,int *cursor,int *stats) {
    if(!pc_cache_enabled || type==Mineshaft)return pc_prefix_uncached(ctx,type,b,goal,out,cursor,stats);
    uint64_t seed=pc_seed(ctx->seed,pc_bits(type)),h=seed^(uint64_t)type*UINT64_C(0x9e3779b97f4a7c15);
    for(int k=0;k<4;k++)h=(h^(uint32_t)b[k])*UINT64_C(0xbf58476d1ce4e5b9);
    h^=(uint64_t)goal;h^=h>>32;
    PCCache *entry=pc_cache+(h&4095);
    if(entry->valid && entry->seed==seed && entry->type==type && entry->goal==goal && !memcmp(entry->b,b,4*sizeof(int))) {
        memcpy(out,entry->p,entry->n*sizeof(Pos));*cursor=entry->cursor;stats[6]++;return entry->n;
    }
    stats[7]++;
    int n=pc_prefix_uncached(ctx,type,b,goal,out,cursor,stats);
    if(n>=0) {
        entry->valid=1;entry->type=type;entry->seed=seed;entry->goal=goal;entry->n=n;entry->cursor=*cursor;
        memcpy(entry->b,b,4*sizeof(int));memcpy(entry->p,out,n*sizeof(Pos));
    }
    return n;
}
static int pc_accept(SeedContext *ctx,int type,Pos p,const int *allow,int y,int *stats) {
    if(type!=Mineshaft && type!=Stronghold) {
        StructureConfig cfg;getStructureConfig(type,MC_26_50,&cfg);stats[1]++;
        if(!isViableStructurePos(type,ss_generator(ctx,cfg.dim),p.x,p.z,0))return 0;
    }
    if(allow) {
        StructureConfig cfg;getStructureConfig(type,MC_26_50,&cfg);stats[2]++;
        int id=ss_biome(ctx,cfg.dim,p.x,y,p.z);
        if(id<0 || id>=256 || !allow[id])return 0;
    }
    return 1;
}
static int pc_finish(SeedContext *ctx,int type,const int *b,int goal,Pos *prefix,int n,int cursor,
                     const int *allow,int y,int *stats) {
    int count=0;
    for(int i=0;i<n;i++)if(pc_accept(ctx,type,prefix[i],allow,y,stats) && ++count==goal)return count;
    if(type==Mineshaft) {
        if(!allow)return count;
        /* A family restriction needs more than the retained raw prefix. This
         * diagnostic obtains a complete inventory only for this special case. */
        int cap=((b[2]-b[0])/16+3)*((b[3]-b[1])/16+3)+20;
        int *xy=malloc((size_t)cap*2*sizeof(int));if(!xy)return -1;
        int found=ss_mineshaft_inventory(ctx,b[0],b[1],b[2],b[3],xy,cap);count=0;
        for(int i=0;i<found && count<goal;i++)if(pc_accept(ctx,type,(Pos){xy[2*i],xy[2*i+1]},allow,y,stats))count++;
        free(xy);return found<0?found:count;
    }
    StructureConfig cfg;getStructureConfig(type,MC_26_50,&cfg);
    int size=cfg.regionSize*16,rx0=floordiv(b[0],size),rz0=floordiv(b[1],size);
    int nx=floordiv(b[2],size)-rx0+1,nz=floordiv(b[3],size)-rz0+1;
    while(cursor<nx*nz) {
        int index=cursor++;Pos p;stats[0]++;
        if(getStructurePos(type,MC_26_50,ctx->seed,rx0+index/nz,rz0+index%nz,&p) && inside(p,b[0],b[1],b[2],b[3]) &&
           pc_accept(ctx,type,p,allow,y,stats) && ++count==goal)return count;
    }
    return count;
}
int pc_count(SeedContext *ctx,int type,const int *b,int goal,int raw_only,int gate_bits,const int *allow,int y,int *stats) {
    if(!ctx || !stats || !pc_valid(b,goal) || pc_bits(type)<0 || (gate_bits!=0 && gate_bits!=32 && gate_bits!=48))return -1;
    memset(stats,0,8*sizeof(int));
    if(type==Stronghold) {
        return pc_strongholds(ctx,b,goal,allow,y,stats);
    }
    if(type==Mineshaft) {
        int xy[2*PC_MAX];
        return allow && !raw_only ? pc_mineshaft_qual_query(ctx,b[0],b[1],b[2],b[3],xy,goal,0,allow,y,stats)
                                 : pc_mineshaft_query(ctx,b[0],b[1],b[2],b[3],xy,goal,0);
    }
    Pos starts[PC_MAX];int cursor=0,n=0;
    if(raw_only || (gate_bits && pc_bits(type)<=gate_bits) || type==Mineshaft) {
        n=pc_prefix(ctx,type,b,goal,starts,&cursor,stats);
        if(n<0)return n;
        if(raw_only)return n;
        if(n<goal){stats[3]=1;return -3;} /* Safe failed requirement; count not claimed. */
    }
    return pc_finish(ctx,type,b,goal,starts,n,cursor,allow,y,stats);
}
int pc_combo(SeedContext *ctx,const int *types,const int *bounds,const int *goals,int families,int gate_bits,
             int known_anchor,const int *raw_order,int *stats) {
    if(!ctx || !types || !bounds || !goals || !stats || families<1 || families>PC_FAMILIES ||
       (gate_bits!=0 && gate_bits!=32 && gate_bits!=48))return -1;
    memset(stats,0,8*sizeof(int));
    Pos starts[PC_FAMILIES][PC_MAX];int count[PC_FAMILIES]={0},cursor[PC_FAMILIES]={0},ready[PC_FAMILIES]={0};
    int shared[4]={-1,-1,-1,-1},shared_total=0;
    for(int j=0;j<families;j++) {
        if(!pc_valid(bounds+4*j,goals[j]) || pc_bits(types[j])<0)return -1;
        int slot=types[j]==Desert_Pyramid?0:types[j]==Jungle_Pyramid?1:types[j]==Swamp_Hut?2:types[j]==Igloo?3:-1;
        if(slot>=0){shared[slot]=j;shared_total+=goals[j];}
    }
    if(gate_bits)for(int at=0;at<families;at++) {
        int j=raw_order?raw_order[at]:at;
        if(j<0 || j>=families)return -1;
        if(ready[j] || types[j]==Mineshaft || pc_bits(types[j])>gate_bits)continue;
        int all_shared=shared[0]>=0 && shared[1]>=0 && shared[2]>=0 && shared[3]>=0;
        int is_shared=types[j]==Desert_Pyramid || types[j]==Jungle_Pyramid || types[j]==Swamp_Hut || types[j]==Igloo;
        if(all_shared && is_shared) {
            if(shared_total>PC_MAX)return -1;
            int c=0;Pos tmp[PC_MAX];int n=pc_prefix(ctx,Desert_Pyramid,bounds+4*j,shared_total,tmp,&c,stats);
            if(n<shared_total){stats[3]=j+1;return 0;}
            for(int k=0;k<4;k++) {
                int index=shared[k];
                if(memcmp(bounds+4*j,bounds+4*index,4*sizeof(int)))return -1;
                memcpy(starts[index],tmp,n*sizeof(Pos));count[index]=n;cursor[index]=c;ready[index]=1;
            }
        } else {
            count[j]=pc_prefix(ctx,types[j],bounds+4*j,goals[j],starts[j],&cursor[j],stats);ready[j]=1;
            if(count[j]<goals[j]){stats[3]=j+1;return 0;}
        }
    }
    for(int j=0;j<families;j++) {
        if(types[j]==Stronghold && goals[j]==1 && known_anchor)continue;
        int n;
        if(types[j]==Stronghold)n=pc_strongholds(ctx,bounds+4*j,goals[j],NULL,63,stats);
        else if(ready[j]) {
            stats[5]+=count[j];
            n=pc_finish(ctx,types[j],bounds+4*j,goals[j],starts[j],count[j],cursor[j],NULL,63,stats);
        } else {
            int work[8];n=pc_count(ctx,types[j],bounds+4*j,goals[j],0,0,NULL,63,work);
            for(int k=0;k<3;k++)stats[k]+=work[k];
            if(n==-3)n=0;
        }
        if(n<0)return n;
        if(n<goals[j]){stats[4]=j+1;return 0;}
    }
    return 1;
}
int pc_biome_count(SeedContext *ctx,int dimension,const int *xyz,int points,const int *allow,int goal,int *queried) {
    if(!ctx || !xyz || !allow || !queried || points<0 || goal<1)return -1;
    int count=0;*queried=0;
    for(int i=0;i<points;i++) {
        if(points-i<goal-count)break;
        int id=ss_biome(ctx,dimension,xyz[3*i],xyz[3*i+1],xyz[3*i+2]);(*queried)++;
        if(id<0)return -1;
        if(id<256 && allow[id] && ++count==goal)return count;
    }
    return count;
}
