#include "bridge.c"
#include "blueprint_batch.inc"
#include <stdio.h>

static void set_pair(NBWorker *w,int layer) {
    /* Native grid uses [layer][x][z], index 32 corresponds to world (0,0). */
    w->dyn_biome_grid[layer*4096+32*64+32]=plains;
    w->dyn_biome_grid[layer*4096+33*64+32]=river;
}
int main(void) {
    NBPolicy p={0}; p.max_buffer_bytes=1<<24; p.river_id=river; p.is_scenic[plains]=1;
    p.y[0]=63;p.y[1]=-48;p.y[2]=0;p.y[3]=160;
    uint64_t accounted=0;
    NBWorker w={0};w.p=&p;w.allocated_bytes=&accounted;
    w.dyn_biome_grid=malloc(4*4096*sizeof(int));
    for(int i=0;i<4*4096;i++)w.dyn_biome_grid[i]=dark_forest;
    set_pair(&w,0);nb_dynamic_build_scenic_cache(&w);
    int surface_pair=nb_dynamic_check_scenic_pair(&w,0,0,NULL,NULL);
    for(int i=0;i<4*4096;i++)w.dyn_biome_grid[i]=dark_forest;
    set_pair(&w,2);nb_dynamic_build_scenic_cache(&w);
    int underground_pair=nb_dynamic_check_scenic_pair(&w,0,0,NULL,NULL);
    printf("{\"surface_y63_pair_native_bonus\":%d,\"surface_expected\":20,\"underground_y0_only_native_bonus\":%d,\"underground_expected\":0}\n",20*surface_pair,20*underground_pair);
    free(w.dyn_biome_grid);free(w.dyn_scenic_river);
    return 0;
}
