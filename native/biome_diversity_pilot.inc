/* Count distinct allowed IDs, never repeated locations of one biome. */
int bd_count(SeedContext *ctx,int dimension,const int *xyz,int points,const int *allow,int goal,int *queried) {
    if(!ctx || !xyz || !allow || !queried || points<0 || goal<1 || !ss_generator(ctx,dimension))return -1;
    int available=0;for(int id=0;id<256;id++)available+=!!allow[id];
    *queried=0;
    if(available<goal)return 0; /* Exact catalog-capacity impossibility. */
    unsigned char seen[256]={0};int count=0;
    for(int i=0;i<points;i++) {
        if(points-i<goal-count)break;
        int id=ss_biome(ctx,dimension,xyz[3*i],xyz[3*i+1],xyz[3*i+2]);(*queried)++;
        if(id<0)return -1;
        if(id<256 && allow[id] && !seen[id]) {
            seen[id]=1;if(++count==goal)return count;
        }
    }
    return count;
}
/* One full64 point stream can satisfy several family-diversity requirements. */
int bd_combo(SeedContext *ctx,int dimension,const int *xyz,int points,const int *allow,const int *goals,
             int families,int *queried) {
    if(!ctx || !xyz || !allow || !goals || !queried || points<0 || families<1 || families>66 || !ss_generator(ctx,dimension))return -1;
    *queried=0;
    unsigned char seen[66][256]={{0}};int counts[66]={0},complete=0;
    for(int f=0;f<families;f++) {
        if(goals[f]<1)return -1;
        int capacity=0;for(int id=0;id<256;id++)capacity+=!!allow[256*f+id];
        if(capacity<goals[f])return 0;
    }
    for(int i=0;i<points;i++) {
        int id=ss_biome(ctx,dimension,xyz[3*i],xyz[3*i+1],xyz[3*i+2]);(*queried)++;
        if(id<0)return -1;
        if(id>=256)continue;
        for(int f=0;f<families;f++)if(counts[f]<goals[f] && allow[256*f+id] && !seen[f][id]) {
            seen[f][id]=1;if(++counts[f]==goals[f])complete++;
        }
        if(complete==families)return 1;
    }
    return 0;
}
