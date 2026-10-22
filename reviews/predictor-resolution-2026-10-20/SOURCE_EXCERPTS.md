# Source excerpts for independent critique

Read-only excerpts; line numbers refer to current working files.

## vendor/cubiomes-bedrock/finders.c:981

```c
int getStaticStronghold(StructureConfig sconf, uint64_t seed,
    int regionX, int regionZ, Pos *pos)
{
    int a = sconf.regionSize * regionX + 100;
    int b = sconf.regionSize * regionZ + 100;
    setSeed(784295783249ULL * a + 827828252345ULL * b + seed + sconf.salt);
    int x = nextIntRange(-50, 50) + a;
    int z = nextIntRange(-50, 50) + b;
    if (nextFloat() >= sconf.rarity)
       return 0;
    pos->x = x*16+4;
    pos->z = z*16+4;
    return 1;
}


static
uint64_t calcFitness(const Generator *g, int x, int z)
{
```

## vendor/cubiomes-bedrock/finders.c:1719

```c
    case Village:
    {
        if (g->mc < MC_1_18)
        {
            if (g->mc < MC_1_11)
            {
                g->entry = &g->ls.layers[L_VORONOI_1];
                sampleX = chunkX * 16 + 9;
                sampleZ = chunkZ * 16 + 9;
            }
            else
            {
                g->entry = &g->ls.layers[L_RIVER_MIX_4];
                sampleX = chunkX * 4 + 2;
                sampleZ = chunkZ * 4 + 2;
            }
            id = getBiomeAt(g, 0, sampleX, 0, sampleZ);
            if (g->mc < MC_1_11) {
                if (id < 0 || !isViableFeatureBiome(g->mc, structureType, id))
                    goto L_not_viable;
            } else {
                if (!areBiomesViable(g, x, 0, z, 2, g_village_biomes, 0, 0))
                    goto L_not_viable;
            }
            if (flags && (uint32_t) id != flags)
                goto L_not_viable;
            if (g->mc < MC_1_0)
            {
                sampleX = chunkX * 16 + 2;
                sampleZ = chunkZ * 16 + 2;
                id = getBiomeAt(g, 1, sampleX, 0, sampleZ);
                if (id < 0 || !isViableFeatureBiome(g->mc, structureType, id))
                    goto L_not_viable;
            }
            viable = id; // biome for viablility, useful for further analysis
            goto L_viable;
        }
        else
        {
            uint64_t m = (1ULL << (meadow - 128) | 1ULL << (sunflower_plains - 128));
            if (!areBiomesViable(g, x, 319, z, 2, g_village_biomes, m, 0))
                goto L_not_viable;
            viable = getBiomeAt(g, 0, x >> 2, 319>>2, z >> 2);
            goto L_viable;
        }
        goto L_not_viable;
    }

    case Outpost:
    {
        if (g->mc <= MC_1_10)
            goto L_not_viable;
        if (g->mc >= MC_1_18)
        {
            sampleX = (chunkX * 16 + 8) >> 2;
            sampleZ = (chunkZ * 16 + 8) >> 2;
        }
        else if (g->mc >= MC_1_16)
        {
            g->entry = &g->ls.layers[L_RIVER_MIX_4];
            sampleX = chunkX * 4 + 2;
            sampleZ = chunkZ * 4 + 2;
        }
        else
        {
            g->entry = &g->ls.layers[L_VORONOI_1];
            sampleX = chunkX * 16 + 9;
            sampleZ = chunkZ * 16 + 9;
        }
        id = getBiomeAt(g, 0, sampleX, 319>>2, sampleZ);
        if (id < 0 || !isViableFeatureBiome(g->mc, structureType, id))
            goto L_not_viable;
        goto L_viable;
    }

    case Monument:
        if (g->mc < MC_1_0)
```

## vendor/cubiomes-bedrock/finders.c:1879

```c


    case Mineshaft:
    case Stronghold:
        goto L_viable;

    case Ravine:
```

## vendor/cubiomes-bedrock/biomenoise.c:1206

```c
int sampleBiomeNoise(const BiomeNoise *bn, int64_t *np, int x, int y, int z,
    uint64_t *dat, uint32_t sample_flags)
{
    if (bn->nptype >= 0)
    {   // initialized for a specific climate parameter
        if (np)
            memset(np, 0, NP_MAX*sizeof(*np));
        int64_t id = (int64_t) (10000.0 * sampleClimatePara(bn, np, x, z));
        return (int) id;
    }

    float t = 0, h = 0, c = 0, e = 0, d = 0, w = 0;
    double px = x, pz = z;
    if (!(sample_flags & SAMPLE_NO_SHIFT))
    {
        double xs[4] = { (double)x, (double)z, 0, 0 };
        double ys[4] = { 0,         (double)x, 0, 0 };
        double zs[4] = { (double)z, 0,         0, 0 };
        double shift[4];
        sampleDoublePerlin_4x(&bn->climate[NP_SHIFT], xs, ys, zs, shift);
        px += shift[0] * 4.0;
        pz += shift[1] * 4.0;
    }

    c = sampleDoublePerlin(&bn->climate[NP_CONTINENTALNESS], px, 0, pz);
    e = sampleDoublePerlin(&bn->climate[NP_EROSION], px, 0, pz);
    w = sampleDoublePerlin(&bn->climate[NP_WEIRDNESS], px, 0, pz);

    if (!(sample_flags & SAMPLE_NO_DEPTH))
    {
        float np_param[] = {
            c, e, -3.0F * ( fabsf( fabsf(w) - 0.6666667F ) - 0.33333334F ), w,
        };
        double off = getSpline(bn->sp, np_param) + 0.015F;

        //double py = y + sampleDoublePerlin(&bn->shift, y, z, x) * 4.0;
        d = 1.0 - (y * 4) / 128.0 - 83.0/160.0 + off;
    }

    t = sampleDoublePerlin(&bn->climate[NP_TEMPERATURE], px, 0, pz);
    h = sampleDoublePerlin(&bn->climate[NP_HUMIDITY], px, 0, pz);

    int64_t l_np[6];
    int64_t *p_np = np ? np : l_np;
    p_np[0] = (int64_t)(10000.0F*t);
    p_np[1] = (int64_t)(10000.0F*h);
    p_np[2] = (int64_t)(10000.0F*c);
    p_np[3] = (int64_t)(10000.0F*e);
    p_np[4] = (int64_t)(10000.0F*d);
    p_np[5] = (int64_t)(10000.0F*w);

    int id = none;
    if (!(sample_flags & SAMPLE_NO_BIOME))
        id = climateToBiome(bn->mc, (const uint64_t*)p_np, dat);
    return id;
}

```

## native/bridge.c:328

```c
#include "filters.inc"
int ss_scan(SeedContext *ctx,int type,int x0,int z0,int x1,int z1,
            int viable_only,int *xz,int capacity) {
    StructureConfig cfg;
    if (x0>x1 || z0>z1 || capacity<1 || !getStructureConfig(type,MC_26_50,&cfg)) return -1;
    int n=0;
    if (type==Mineshaft) {
return ss_mineshaft_inventory(ctx,x0,z0,x1,z1,xz,capacity);
    }
    int size=cfg.regionSize*16;
    Generator *g=ss_generator(ctx,cfg.dim);
    if (!g) return -1;
    /* Only Stronghold has reviewed starts displaced outside its region. */
    int halo=type==Stronghold ? 1 : 0;
    for (int rx=floordiv(x0,size)-halo;rx<=floordiv(x1,size)+halo;rx++) {
        for (int rz=floordiv(z0,size)-halo;rz<=floordiv(z1,size)+halo;rz++) {
            Pos p;
            int found=getStructurePos(type,MC_26_50,ctx->seed,rx,rz,&p);
            /* Keep the selected Bedrock structure type. Promoting a rejected
             * Bastion to a Fortress produced the absent seed-12345 start at
             * (-152,120); phone inspection supplied the negative fixture. */
            if (!found || !inside(p,x0,z0,x1,z1)) continue;
            if (viable_only && type!=Stronghold && !isViableStructurePos(type,g,p.x,p.z,0)) continue;
            n=emit(p,xz,n,capacity);
            if (n<0) return n;
        }
    }
    if (type==Stronghold) {
        StrongholdIter it={0};
        for (int i=0;i<3;i++) {
            nextVillageStronghold(&it,&ctx->overworld);
            if (inside(it.pos,x0,z0,x1,z1)) {
                n=emit(it.pos,xz,n,capacity);
                if (n<0) return n;
            }
        }
    }
    return n;
}
int ss_attempt(SeedContext *ctx,int type,int rx,int rz,int *xz) {
    if (type<0 || type==Mineshaft) return -1;
    Pos p;
    int ok=getStructurePos(type,MC_26_50,ctx->seed,rx,rz,&p);
    if (ok) { xz[0]=p.x; xz[1]=p.z; }
    return ok;
}
/* Validate enumerated starts without repeating placement or Stronghold iteration.
 * Match ss_scan's special adapters: those two families never veto raw starts. */
int ss_filter_starts(SeedContext *ctx,int type,const int *xz,int n,int *viable) {
    StructureConfig cfg;
    if (n<0 || !getStructureConfig(type,MC_26_50,&cfg)) return -1;
    Generator *g=ss_generator(ctx,cfg.dim);
    if (!g) return -1;
    for (int i=0;i<n;i++)
        viable[i]=(type==Stronghold || type==Mineshaft) ? 1 :
            !!isViableStructurePos(type,g,xz[2*i],xz[2*i+1],0);
    return 0;
}
/* Expose the actual viability sampling convention for evidence, not a new rule.
 * out: quart x/y/z, sampled biome, rotation, variant, offset x/z, size x/z. */
int ss_diagnostic(SeedContext *ctx, int type, int x, int z, int *out) {
    if (type == Ancient_City) {
```
