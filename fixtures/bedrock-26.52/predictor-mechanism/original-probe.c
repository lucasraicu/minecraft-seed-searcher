#define main unused_original_probe_main
#include "/Users/lucasraicu/Downloads/minecraft-seed-searcher/scripts/biome_sampling_probe.c"
#undef main
int main(void) {
 Generator *g=calloc(1,sizeof(*g)); if(!g)return 2;
 setupGenerator(g,MC_26_50,0); uint64_t previous=0; int have=0,count=0;
 char line[192];
 while(fgets(line,sizeof(line),stdin)) {
  char *p=line; int64_t seed,x,y,z;
  if(++count>4096||!parse(&p,&seed)||!parse(&p,&x)||!parse(&p,&y)||!parse(&p,&z))return 3;
  while(isspace((unsigned char)*p))++p;
  if(*p||x < -2048||x>2048||z < -2048||z>2048||y < -17||y>80)return 3;
  if(!have||previous!=(uint64_t)seed){applySeed(g,DIM_OVERWORLD,(uint64_t)seed);previous=(uint64_t)seed;have=1;}
  int64_t np[6]; int id=sampleBiomeNoise(&g->bn,np,x,y,z,0,0); const char *n=name(id);if(!n)return 4;
  printf("%d %s %" PRIu64, id,n,g->sha);
  for(int i=0;i<6;i++)printf(" %" PRId64,np[i]);printf("\n");
 }
 free(g);return ferror(stdin)?3:0;
}
