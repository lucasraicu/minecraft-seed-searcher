# Additional structure source excerpts

## finders.c:1944
```c
int isViableStructureTerrain(int structType, Generator *g, int x, int z)
{
    int sx, sz;
    if (g->mc < MC_1_18)
        return 1;
    if (structType == Desert_Pyramid || structType == Jungle_Temple)
    {
        sx = (structType == Desert_Pyramid ? 21 : 12);
        sz = (structType == Desert_Pyramid ? 21 : 15);
    }
    // else if (structType == Mansion)
    // {
    //     int cx = x >> 4, cz = z >> 4;
    //     Pos region = chunkToRegion(cx, cz, 80);
    //     setRegionSeed(g->seed, region.x, region.z, 10387319);
    //     skipNextN(4);
    //     int rot = nextInt(4);
    //     sx = 5;
    //     sz = 5;
    //     if (rot == 0) { sx = -5; }
    //     if (rot == 1) { sx = -5; sz = -5; }
    //     if (rot == 2) { sz = -5; }
    //     x = cx * 16 + 7;
    //     z = cz * 16 + 7;
    // }
    else
    {
        return 1;
    }

    // approx surface height using depth parameter (0.5 ~ sea level)
    double corners[][2] = {
        {(x+ 0)/4.0, (z+ 0)/4.0},
        {(x+sx)/4.0, (z+sz)/4.0},
        {(x+ 0)/4.0, (z+sz)/4.0},
        {(x+sx)/4.0, (z+ 0)/4.0},
    };
    int nptype = g->bn.nptype;
    int i, ret = 1;
    g->bn.nptype = NP_DEPTH;
    for (i = 0; i < 4; i++)
    {
        double depth = sampleClimatePara(&g->bn, 0, corners[i][0], corners[i][1]);
        if (depth < 0.48)
        {
            ret = 0;
            break;
        }
    }
    g->bn.nptype = nptype;
    return ret;
}


/* Given bordering noise columns and a fractional position between those,
 * determine the surface block height (i.e. where the interpolated noise > 0).
 * Note that the noise columns should be of size: ncolxz[ colheight+1 ]
 */
int getSurfaceHeight(
        const double ncol00[], const double ncol01[],
        const double ncol10[], const double ncol11[],
        int colymin, int colymax, int blockspercell, double dx, double dz);

void sampleNoiseColumnEnd(double column[], const SurfaceNoise *sn,
        const EndNoise *en, int x, int z, int colymin, int colymax);

int isViableEndCityTerrain(const Generator *g, const SurfaceNoise *sn,
        int blockX, int blockZ)
{
    const EndNoise *en = &g->en;
    int chunkX = blockX >> 4;
    int chunkZ = blockZ >> 4;
    blockX = chunkX * 16 + 7;
    blockZ = chunkZ * 16 + 7;

    int x0 = blockX, z0 = blockZ;
    int x1, z1, x2, z2, x3, z3;
```

## finders.c:2198
```c
    case Village:
        if (mc < MC_1_11)
        {
            int regX = cx < 0 ? cx - 40+1 : cx;
            int regZ = cz < 0 ? cz - 40+1 : cz;
            setRegionSeed(seed, regX, regZ, 10387312);
            r->abandoned = nextInt(sc.rarity) == 0;
            return 0;
        }
        if (!isViableFeatureBiome(mc, Village, biomeID))
            return 0;
        r->biome = biomeID;
        setRegionSeed(seed, rpos.x, rpos.z, sc.salt);
        skipNextN(4);
        r->rotation = nextInt(4);
        if (mc >= MC_1_13)
            r->abandoned = nextFloat() < sc.rarity;
        switch (biomeID)
        {
        case meadow:
        case sunflower_plains:
            r->biome = plains;
            // fallthrough
        case plains:
            t = nextInt(1+1+1+1);
            if      (t < 1) { r->start = 0; sx =  9; sy = 4; sz =  9; } // plains_fountain_01
            else if (t < 2) { r->start = 1; sx = 10; sy = 7; sz = 10; } // plains_meeting_point_1
            else if (t < 3) { r->start = 2; sx =  8; sy = 5; sz = 15; } // plains_meeting_point_2
            else if (t < 4) { r->start = 3; sx = 11; sy = 9; sz = 11; } // plains_meeting_point_3
            else  UNREACHABLE();
            break;
        case desert:
            t = nextInt(3+3+1);
            if      (t < 3) { r->start = 1; sx = 17; sy = 6; sz =  9; } // desert_meeting_point_1
            else if (t < 6) { r->start = 2; sx = 12; sy = 6; sz = 12; } // desert_meeting_point_2
            else if (t < 7) { r->start = 3; sx = 15; sy = 6; sz = 15; } // desert_meeting_point_3
            else  UNREACHABLE();
            break;
        case savanna:
            t = nextInt(2+1+3+3);
            if      (t < 2) { r->start = 1; sx = 14; sy = 5; sz = 12; } // savanna_meeting_point_1
            else if (t < 3) { r->start = 2; sx = 11; sy = 6; sz = 11; } // savanna_meeting_point_2
            else if (t < 6) { r->start = 3; sx =  9; sy = 6; sz = 11; } // savanna_meeting_point_3
            else if (t < 9) { r->start = 4; sx =  9; sy = 6; sz =  9; } // savanna_meeting_point_4
            else  UNREACHABLE();
            break;
        case snowy_taiga:
            r->biome = taiga;
            // fallthrough
        case taiga:
            t = nextInt(2+2);
            if      (t < 2) { r->start = 1; sx = 22; sy = 3; sz = 18; } // taiga_meeting_point_1
            else if (t < 4) { r->start = 2; sx =  9; sy = 7; sz =  9; } // taiga_meeting_point_2
            else  UNREACHABLE();
            break;
        case snowy_plains:
            t = nextInt(2+1+3);
            if      (t < 2) { r->start = 1; sx = 12; sy = 8; sz =  8; } // snowy_meeting_point_1
            else if (t < 3) { r->start = 2; sx = 11; sy = 5; sz =  9; } // snowy_meeting_point_2
            else if (t < 6) { r->start = 3; sx =  7; sy = 7; sz =  7; } // snowy_meeting_point_3
            else  UNREACHABLE();
            break;
        default:
            sx = sy = sz = 0;
            return 0;
        }
        goto L_rotate_village_bastion;

    case Outpost:
        setRegionSeed(seed, rpos.x, rpos.z, sc.salt);
        skipNextN(4);
        r->rotation = nextInt(4);
        sx = sz = 15;
        sy = 21;
        goto L_rotate_village_bastion;

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
```

## finders.c:4632
```c
// Outpost Generator
//==============================================================================

static const struct
{
    Pos3 size;
    const char* name;
}
outpost_info[] = {
    // vanilla\structures\pillageroutpost
    {{6, 5, 6}, "feature_cage1"}, // cage1 is the golem cage in Bedrock
    {{6, 5, 6}, "feature_cage2"},
    {{7, 4, 7}, "feature_cage_with_allays"},
    {{6, 3, 7}, "feature_logs"},
    {{3, 3, 7}, "feature_targets"},
    {{6, 5, 7}, "feature_tent1"},
    {{6, 5, 7}, "feature_tent2"},
};

const struct {
    int x, z;
}
scatter_bases[4] = {
    { 16, 16},
    {-16, 16},
    { 16,-16},
    {-16,-16}
};

int getOutpostPieces(Piece* pieces, uint64_t seed, int chunkX, int chunkZ)
{
    StructureConfig sc;
    getStructureConfig(Outpost, MC_NEWEST, &sc);
    Pos rpos = chunkToRegion(chunkX, chunkZ, sc.regionSize);
    setRegionSeed(seed, rpos.x, rpos.z, sc.salt);
    skipNextN(4);

    int rotation = nextInt(4);
    int baseX = chunkX << 4;
    int baseZ = chunkZ << 4;

    int size = 15;
    int ox, oz;
    rotatePos2D(rotation, 0, 0, size, size, &ox, &oz);

    int centerX = baseX + ox;
    int centerZ = baseZ + oz;
    if (baseX <= centerX) centerX = baseX;
    if (baseZ <= centerZ) centerZ = baseZ;
    centerX += 8;
    centerZ += 8;

    Pos3 positions[4];
    for (int i = 0; i < 4; i++) {
        positions[i].x = centerX + scatter_bases[i].x - (4 - nextInt(8));
        positions[i].y = 90;
        positions[i].z = centerZ + scatter_bases[i].z - (4 - nextInt(8));
    }

    int n = 0;
    for (int i = 0; i < 4; i++) {
        if (nextFloat() >= 0.9f)
            continue;

        int rot = nextInt(4);
        int type = nextInt(7);

        Piece* p = &pieces[n];
        p->name = outpost_info[type].name;
        p->pos.x = positions[i].x;
        p->pos.y = positions[i].y;
        p->pos.z = positions[i].z;

        int sizeX = outpost_info[type].size.x;
        int sizeY = outpost_info[type].size.y;
        int sizeZ = outpost_info[type].size.z;

        Pos3 bb0 = p->pos, bb1 = p->pos;
        switch(rot) {
            case 0: // North
                bb1.x += sizeX - 1;
                bb1.y += sizeY - 1;
                bb1.z += sizeZ - 1;
                break;
            case 1: // East
                bb0.x -= sizeZ + 1;
                bb1.y += sizeY - 1;
                bb1.z += sizeX - 1;
                break;
            case 2: // South
                bb0.x -= sizeX + 1;
                bb1.y += sizeY - 1;
                bb0.z -= sizeZ + 1;
                break;
            case 3: // West
                bb1.x += sizeZ - 1;
                bb1.y += sizeY - 1;
                bb0.z -= sizeX + 1;
                break;
        }
        p->bb = bb3(bb0.x, bb0.y, bb0.z, bb1.x, bb1.y, bb1.z);
        p->rot = (uint8_t)rot;
        p->type = (int8_t)type;
    
        n++;
    }
    return n;
}

//==============================================================================
```
