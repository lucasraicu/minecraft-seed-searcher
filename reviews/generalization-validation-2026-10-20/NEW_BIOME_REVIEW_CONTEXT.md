# New biome disagreements — High independent diagnosis, no implementation
User explicitly selected FINISH AUDIT BEFORE CHANGING PREDICTOR. Read ONLY embedded context; no commands/readers/edit/network/agents. <=650words final start BIOME_DIAGNOSIS. Need ranked falsifiable mechanisms, alternative explanations, specific minimal observations; challenge assumptions. Do not invent generic accuracy or change filters.

Pinned BDS1.26.52.3 API2.10.0 default, owned24worldcohort (16blind+8biasedtargeted) frozenbeforegame. Current22worlds3086pointattempts: first4biome mismatches all on targetedseed7370389603366252746 below. All61activeOverworld/Netherclasseshaveothermatchingwitnesses, notglobalguarantee. Exactseed/dimension/XYZ/API/build/settings/save/cleanstop/rawconsole bindings pass. Netherpoint16 requiredtickingarealoadthenrealnetherrackblockread,64wasair,112netherrack; APIcold_beach highOverworld319air. Loadingerrorselsewhereretainedaserrors, notmismatches orabsence.

Nether both nativeJava4Voronoi and copiedOverworldBedrock8grid hypothesis predict soul_sand_valley atall3disagreedheights. Previous162Netherfixedpoints hadold==8predictionsandmatchedBDS, so those were nondiscriminating. Native seed truncated32 or48 gives same wronglabel; do notassume64seedbug fromthis. NethergetNetherBiome forcesy=0; actualblockselection maystillvarywithY. BDS noise/source/rng itself notprovenfromSDK.

Overworld8grid source backedbyactualBDSdisassembly and8320stored/330priorgamepoints; newY319disagreementdoesnotjustifyglobalreroute. EarlierrepeatsectionY80 discrepancy was STORAGE interpretation: fresh/reloaded/copiedstableAPI99readsagreed, decodingaboveencodedceilinguseslastexplicitplane; raw8gridnativewasretained. Currentnew319case mightbeheightboundary/cache/noisefloat, notproven. Do notfitYoffset/cavemask.

Alreadyfrozen46pointdefaultAPI recheck (noBeta): same stoppedworld20copied unchanged,exact4originalpoints+OverworldsamecolumnY63,64,72,79,80,95,96,127,128,159,160,255,256,311,312,318,319+4neighborsY319; NethercolumnY0,16,32,48,64,80,96,112,127+local1/4blockneighborsat64. Stable2.10twodimensions,separatesavedcopies,zero locates/membership/volumescans,originalsourcehashesbeforeafter. 600sperseed/7200stotalcapsunchanged (world20original240.3s), runonlyafteroriginalcohortand137pointBeta-copymembershipphase lockreleased. Noactivegamecode altered. Propose additionaldiscriminatorONLYif46pointsinsufficient, withinbudget; do notclaimcausefromselfreportedresult.

## Actual mismatches
[
  {
    "position": [
      248,
      319,
      -312
    ],
    "sample_group": "retained_structure_context",
    "predicted_name": "snowy_taiga",
    "observed_name": "minecraft:cold_beach",
    "canonical_predicted": "snowy_taiga",
    "canonical_observed": "snowy_beach",
    "outcome": "mismatch",
    "reason": "mismatch: predicted 'snowy_taiga' != observed 'snowy_beach'",
    "dimension": "overworld",
    "seed": "7370389603366252746",
    "cohort": "targeted"
  },
  {
    "position": [
      512,
      16,
      512
    ],
    "sample_group": "fixed_xyz",
    "predicted_name": "soul_sand_valley",
    "observed_name": "minecraft:hell",
    "canonical_predicted": "soul_sand_valley",
    "canonical_observed": "nether_wastes",
    "outcome": "mismatch",
    "reason": "mismatch: predicted 'soul_sand_valley' != observed 'nether_wastes'",
    "dimension": "nether",
    "seed": "7370389603366252746",
    "cohort": "targeted"
  },
  {
    "position": [
      512,
      64,
      512
    ],
    "sample_group": "fixed_xyz",
    "predicted_name": "soul_sand_valley",
    "observed_name": "minecraft:hell",
    "canonical_predicted": "soul_sand_valley",
    "canonical_observed": "nether_wastes",
    "outcome": "mismatch",
    "reason": "mismatch: predicted 'soul_sand_valley' != observed 'nether_wastes'",
    "dimension": "nether",
    "seed": "7370389603366252746",
    "cohort": "targeted"
  },
  {
    "position": [
      512,
      112,
      512
    ],
    "sample_group": "fixed_xyz",
    "predicted_name": "soul_sand_valley",
    "observed_name": "minecraft:hell",
    "canonical_predicted": "soul_sand_valley",
    "canonical_observed": "nether_wastes",
    "outcome": "mismatch",
    "reason": "mismatch: predicted 'soul_sand_valley' != observed 'nether_wastes'",
    "dimension": "nether",
    "seed": "7370389603366252746",
    "cohort": "targeted"
  }
]
## Nether source
```c
void setNetherSeed(NetherNoise *nn, uint64_t seed)
{
    setSeed(seed);
    doublePerlinInit(&nn->temperature, &nn->oct[0], &nn->oct[2], -7, 2);
    setSeed(seed+1);
    doublePerlinInit(&nn->humidity, &nn->oct[4], &nn->oct[6], -7, 2);
}

/* Gets the 3D nether biome at scale 1:4 (for 1.16+).
 */
int getNetherBiome(const NetherNoise *nn, int x, int y, int z, float *ndel)
{
    const float npoints[5][4] = {
        { 0,    0,      0,              nether_wastes       },
        { 0,   -0.5,    0,              soul_sand_valley    },
        { 0.4,  0,      0,              crimson_forest      },
        { 0,    0.5,    0.375*0.375,    warped_forest       },
        {-0.5,  0,      0.175*0.175,    basalt_deltas       },
    };

    y = 0;
    float temp = sampleDoublePerlin(&nn->temperature, x, y, z);
    float humidity = sampleDoublePerlin(&nn->humidity, x, y, z);

    int i, id = 0;
    float dmin = FLT_MAX;
    float dmin2 = FLT_MAX;
    for (i = 0; i < 5; i++)
    {
        float dx = npoints[i][0] - temp;
        float dy = npoints[i][1] - humidity;
        float dsq = dx*dx + dy*dy + npoints[i][2];
        if (dsq < dmin)
        {
            dmin2 = dmin;
            dmin = dsq;
            id = i;
        }
        else if (dsq < dmin2)
            dmin2 = dsq;
    }

    if (ndel)
        *ndel = sqrtf(dmin2) - sqrtf(dmin);

    id = (int) npoints[id][3];
    return id;
}


```
## Existing raw Overworld sampler
```c
/// Biome sampler for MC 1.18
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
## Bedrock selector helper
```c
#include "generator.h"
#include "layers.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <float.h>
#include <limits.h>

#if defined(__FAST_MATH__)
#error "Biome selection requires IEEE float ordering; fast-math is unsupported"
#endif

static int floorEight(int v)
{
    return v / 8 - (v < 0 && v % 8 != 0);
}

int getBedrockBiomeQuart(uint64_t seed, int x, int y, int z, int out[3])
{
    if (!out) return -1;
    int base[3] = {floorEight(x), floorEight(y), floorEight(z)};
    float t[3] = {((uint32_t)x & 7) * 0.125f,
                  ((uint32_t)y & 7) * 0.125f,
                  ((uint32_t)z & 7) * 0.125f};
    float best = FLT_MAX;
    for (int dx = 0; dx < 2; dx++)
    for (int dz = 0; dz < 2; dz++)
    for (int dy = 0; dy < 2; dy++)
    {
        int cx = base[0] + dx, cy = base[1] + dy, cz = base[2] + dz;
        /* The X/Y part truncates to int32 before sign extension. The Z
         * product and subsequent quadratic/LCG steps wrap at 64 bits. */
        uint32_t a = (uint32_t)cx * UINT32_C(3129871) ^ (uint32_t)cy;
        int64_t sx = (a & UINT32_C(0x80000000)) ?
                     (int64_t)a - INT64_C(4294967296) : (int64_t)a;
        uint64_t n = (uint64_t)sx ^ ((uint64_t)(int64_t)cz * UINT64_C(116129781));
        n *= n * UINT64_C(42317861) + 11;
        uint64_t state = (n >> 16) ^ ((uint64_t)(uint32_t)seed ^ UINT64_C(0x5deece66d));
        float jitter[3];
        for (int i = 0; i < 3; i++)
        {
            state = state * UINT64_C(0x5deece66d) + 11;
            float unit = (float)((state >> 24) & UINT64_C(0xffffff)) * 0x1p-24f;
            jitter[i] = (unit - 0.5f) * 0.9f;
        }
        float vx = (t[0] - dx) + jitter[0];
        float vy = (t[1] - dy) + jitter[1];
        float vz = (t[2] - dz) + jitter[2];
        /* Explicit rounding also prevents contraction on FMA-capable hosts. */
        volatile float xx = vx * vx, yy = vy * vy, zz = vz * vz;
        volatile float xy = xx + yy;
        float distance = xy + zz;
        if (distance < best)
        {
            best = distance;
            out[0] = cx * 2; out[1] = cy * 2; out[2] = cz * 2;
        }
    }
    return 0;
}


```
