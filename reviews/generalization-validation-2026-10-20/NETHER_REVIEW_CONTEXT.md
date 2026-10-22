# Nether bastion omission — neutral High source review
User requires all Overworld/Nether features, including rejected candidates. Approved bounded default BDS1.26.52.3 audit currently running; no predictor changes authorized by this prompt. Tool-free review only: embedded context, no commands/readers/network/edit/agents. <=600words. Need falsifiable source mechanism and minimal independent checks, no global acceptance-rule change fromonecase.

Seed219044158440418215; game independent /locate bastion_remnant from1536,1536 returns1640,1672, exactly raw placement candidate. Viable inventory omits it. Original fresh default settings seed/image/build/save/cleanup bound. Nether fixed XYZ biome probes match their native predictions; no sameXYZ BDS biome read ATthisbastionyet. Do NOT claim actualstart biome known merely from native prediction.

Native diagnostic: rotation2,start1 (hoglinstable),bboxrelative -29,-47,30,48; raw center biome nativeID8(netherwastes); sampledvariantcenter quart404,410 (block1616,1640),ID173(basaltdeltas); nativeviable0. Offsets use Java-like jigsawvariant; Bedrock actualvariant/biomepredicate notproven. Fortress/bastion regionsharing important.

## Current Nether viability
```c
    if (g->dim == DIM_NETHER)
    {
        if (structureType == Fortress && g->mc < MC_1_16)
            return 1;
        if (g->mc <= MC_1_14)
            return 0;
        if (structureType == Ruined_Portal_N)
            return 1;
        if (structureType == Fortress)
        {   // in 1.18+ fortresses generate everywhere, where bastions don't
            StructureConfig sc;
            if (!getStructureConfig(Fortress, g->mc, &sc))
                return 0;
            Pos rp = {
                floordiv(x, sc.regionSize << 4),
                floordiv(z, sc.regionSize << 4)
            };
            if (!getStructurePos(Bastion, g->mc, g->seed, rp.x, rp.z, &rp))
                return 1;
            return !isViableStructurePos(Bastion, g, x, z, flags);
        }
        sampleY = 0;
        if (g->mc >= MC_1_16 && structureType == Bastion)
        {
            StructureVariant sv;
            getVariant(&sv, Bastion, g->mc, g->seed, x, z, -1);
            sampleX = (chunkX*32 + 2*sv.x + sv.sx-1) / 2 >> 2;
            sampleZ = (chunkZ*32 + 2*sv.z + sv.sz-1) / 2 >> 2;
            if (g->mc >= MC_1_19)
                sampleY = 33 >> 2; // nether biomes don't actually vary in Y
        }
        else
        {
            sampleX = (chunkX * 4) + 2;
            sampleZ = (chunkZ * 4) + 2;
        }
        id = getBiomeAt(g, 4, sampleX, sampleY, sampleZ);
        return isViableFeatureBiome(g->mc, structureType, id);
    }
```
## Current variant
```c
    case Bastion:
        setRegionSeed(seed, rpos.x, rpos.z, sc.salt);
        skipNextN(3);
        r->rotation = nextInt(4);
        r->start = 3 - nextInt(4); // ooposite 0->3, 1->2, 2->1, 3->0
        switch (r->start)
        {
        case 0: sx = 46; sy = 24; sz = 46; break; // units/air_base
        case 1: sx = 30; sy = 24; sz = 48; break; // hoglin_stable/air_base
        case 2: sx = 38; sy = 48; sz = 38; break; // treasure/big_air_full
        case 3: sx = 16; sy = 32; sz = 32; break; // bridge/starting_pieces/entrance_base
        }
    L_rotate_village_bastion:
        r->sy = sy;
        if (mc >= MC_1_18)
        {
            switch (r->rotation)
            { // 0:0, 1:cw90, 2:cw180, 3:cw270=ccw90
            case 0: r->x = 0;    r->z = 0;    r->sx = sx; r->sz = sz; break;
            case 1: r->x = 1-sz; r->z = 0;    r->sx = sz; r->sz = sx; break;
            case 2: r->x = 1-sx; r->z = 1-sz; r->sx = sx; r->sz = sz; break;
            case 3: r->x = 0;    r->z = 1-sx; r->sx = sz; r->sz = sx; break;
            }
        }
        else
        {
            switch (r->rotation)
            { // 0:0, 1:cw90, 2:cw180, 3:cw270=ccw90
            case 0: r->x = 0;        r->z = 0;        r->sx = sx; r->sz = sz; break;
            case 1: r->x = (x<0)-sz; r->z = 0;        r->sx = sz; r->sz = sx; break;
            case 2: r->x = (x<0)-sx; r->z = (z<0)-sz; r->sx = sx; r->sz = sz; break;
            case 3: r->x = 0;        r->z = (z<0)-sx; r->sx = sz; r->sz = sx; break;
            }
        }
        return 1;

```
## Current biome predicates
```c
    case Fortress:
        return (biomeID == nether_wastes || biomeID == soul_sand_valley ||
                biomeID == warped_forest || biomeID == crimson_forest ||
                biomeID == basalt_deltas);

    case Bastion:
        if (mc <= MC_1_14) return 0;
        return (biomeID == nether_wastes || biomeID == soul_sand_valley ||
                biomeID == warped_forest || biomeID == crimson_forest);

```
