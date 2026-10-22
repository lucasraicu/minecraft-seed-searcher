ImplementationdiffagainstactualGitbaseline; newstorageuntrackedmodulefullcontextseparate. No activecodingworkers; bothtimedoutwithoutchanges. Codeximplemented.

```diff
diff --git a/vendor/cubiomes-bedrock/cave.c b/vendor/cubiomes-bedrock/cave.c
index 5823404..58bf39d 100644
--- a/vendor/cubiomes-bedrock/cave.c
+++ b/vendor/cubiomes-bedrock/cave.c
@@ -693,6 +693,36 @@ static double maxDistance(int d1, int d2)
     return 1.0 - (double) IABS(d2 - d1) / 25.0;
 }
 
+int getPreliminarySurfaceLevel(const BiomeNoise *bn, const TerrainShaper *ts,
+                              int biomeX, int biomeZ)
+{
+    double rawOffset, rawFactor;
+    sampleTerrainShape(bn, ts, biomeX, biomeZ, &rawOffset, &rawFactor);
+    float offset = (float)rawOffset, factor = (float)rawFactor;
+    for (int y = 248, top = 1, bottom = 39; y >= -64; y -= 8, top++, bottom--)
+    {
+        float gradient = (1.0f - y * (1.0f / 128.0f)) + offset;
+        gradient *= factor;
+        gradient *= gradient > 0.0f ? 4.0f : 1.0f;
+        volatile float scaled = gradient * 128.0f;
+        float density = scaled - 90.0f;
+        float upper = top * 0.5f;
+        if (upper <= 1.0f)
+        {
+            volatile float blend = (density + 10.0f) * upper;
+            density = blend - 10.0f;
+        }
+        float lower = bottom / 3.0f;
+        if (lower <= 1.0f)
+        {
+            volatile float blend = (density - 15.0f) * lower;
+            density = blend + 15.0f;
+        }
+        if (density > 50.0f) return y;
+    }
+    return 32767;
+}
+
 static int getSurfaceHeightNoCaves(const BiomeNoise *bn, const TerrainShaper *ts, int x, int z)
 {
     double offset, factor;
@@ -989,4 +1019,4 @@ int getCaveBlockStateCached(
 
     double extra = sampleNoodleAdjustedDensityInterpolated(cn, tc, density, x, y, z);
     return applyAquiferState(bn, ts, cn, tc, x, y, z, extra);
-}
\ No newline at end of file
+}
diff --git a/vendor/cubiomes-bedrock/cave.h b/vendor/cubiomes-bedrock/cave.h
index 269d60c..b3f1701 100644
--- a/vendor/cubiomes-bedrock/cave.h
+++ b/vendor/cubiomes-bedrock/cave.h
@@ -42,6 +42,12 @@ void sampleTerrainShape(
     double *offset,
     double *factor);
 
+/* Preliminary structure-biome query height for the pinned 1.26.50 research
+ * model. Quart coordinates refer to the chunk origin, not its center.
+ * This is not actual terrain elevation. The engaged-short no-hit value is 32767. */
+int getPreliminarySurfaceLevel(const BiomeNoise *bn, const TerrainShaper *ts,
+                              int biomeX, int biomeZ);
+
 /**
  * Density at block (x,y,z); caves/aquifers not included.
  * >0 means solid.
diff --git a/vendor/cubiomes-bedrock/finders.c b/vendor/cubiomes-bedrock/finders.c
index d88a0aa..58d6d2a 100644
--- a/vendor/cubiomes-bedrock/finders.c
+++ b/vendor/cubiomes-bedrock/finders.c
@@ -1,6 +1,7 @@
 #include "finders.h"
 #include "biomes.h"
 #include "util.h"
+#include "cave.h"
 
 #include <stdio.h>
 #include <string.h>
@@ -1550,6 +1551,32 @@ static int monumentNearby(Generator *g, int chunkX, int chunkZ)
     return 0;
 }
 
+/* Bedrock checks raw 3D biomes at a preliminary density height, rather than
+ * the actual surface or sky. Keep the seed-independent spline local so calls
+ * from independent search threads share no mutable initialization state. */
+static int viablePreliminaryBiomes(int type, const Generator *g, int cx, int cz,
+                                  int radius, int *centerId)
+{
+    TerrainShaper shaper;
+    initTerrainShaper(&shaper);
+    int height = getPreliminarySurfaceLevel(&g->bn, &shaper, cx * 4, cz * 4);
+    int lo = height - radius, hi = height + radius;
+    if (lo < -64) lo = -64;
+    if (hi > 319) hi = 319;
+    *centerId = 1;
+    for (int dx = -radius; dx <= radius; dx += 4)
+    for (int y = lo; y <= hi; y += 4)
+    for (int dz = -radius; dz <= radius; dz += 4)
+    {
+        int id = getBiomeAt(g, 4, floordiv(cx * 16 + 8 + dx, 4),
+                            floordiv(y, 4), floordiv(cz * 16 + 8 + dz, 4));
+        if (id < 0 || !isViableFeatureBiome(g->mc, type, id)) return 0;
+    }
+    if (lo <= hi)
+        *centerId = getBiomeAt(g, 4, cx * 4 + 2, floordiv(height, 4), cz * 4 + 2);
+    return 1;
+}
+
 int isViableStructurePos(int structureType, Generator *g, int x, int z, uint32_t flags)
 {
     int approx = 0; // enables approximation levels
@@ -1718,6 +1745,13 @@ L_feature:
 
     case Village:
     {
+        if (g->mc == MC_26_50)
+        {
+            if (!viablePreliminaryBiomes(Village, g, (int)chunkX, (int)chunkZ, 2, &id))
+                goto L_not_viable;
+            viable = id;
+            goto L_viable;
+        }
         if (g->mc < MC_1_18)
         {
             if (g->mc < MC_1_11)
@@ -1766,6 +1800,12 @@ L_feature:
 
     case Outpost:
     {
+        if (g->mc == MC_26_50)
+        {
+            if (!viablePreliminaryBiomes(Outpost, g, (int)chunkX, (int)chunkZ, 0, &id))
+                goto L_not_viable;
+            goto L_viable;
+        }
         if (g->mc <= MC_1_10)
             goto L_not_viable;
         if (g->mc >= MC_1_18)
diff --git a/vendor/cubiomes-bedrock/generator.c b/vendor/cubiomes-bedrock/generator.c
index e4b5e77..efc0e8d 100644
--- a/vendor/cubiomes-bedrock/generator.c
+++ b/vendor/cubiomes-bedrock/generator.c
@@ -5,6 +5,61 @@
 #include <stdlib.h>
 #include <string.h>
 #include <math.h>
+#include <float.h>
+#include <limits.h>
+
+#if defined(__FAST_MATH__)
+#error "Biome selection requires IEEE float ordering; fast-math is unsupported"
+#endif
+
+static int floorEight(int v)
+{
+    return v / 8 - (v < 0 && v % 8 != 0);
+}
+
+int getBedrockBiomeQuart(uint64_t seed, int x, int y, int z, int out[3])
+{
+    if (!out) return -1;
+    int base[3] = {floorEight(x), floorEight(y), floorEight(z)};
+    float t[3] = {((uint32_t)x & 7) * 0.125f,
+                  ((uint32_t)y & 7) * 0.125f,
+                  ((uint32_t)z & 7) * 0.125f};
+    float best = FLT_MAX;
+    for (int dx = 0; dx < 2; dx++)
+    for (int dz = 0; dz < 2; dz++)
+    for (int dy = 0; dy < 2; dy++)
+    {
+        int cx = base[0] + dx, cy = base[1] + dy, cz = base[2] + dz;
+        /* The X/Y part truncates to int32 before sign extension. The Z
+         * product and subsequent quadratic/LCG steps wrap at 64 bits. */
+        uint32_t a = (uint32_t)cx * UINT32_C(3129871) ^ (uint32_t)cy;
+        int64_t sx = (a & UINT32_C(0x80000000)) ?
+                     (int64_t)a - INT64_C(4294967296) : (int64_t)a;
+        uint64_t n = (uint64_t)sx ^ ((uint64_t)(int64_t)cz * UINT64_C(116129781));
+        n *= n * UINT64_C(42317861) + 11;
+        uint64_t state = (n >> 16) ^ ((uint64_t)(uint32_t)seed ^ UINT64_C(0x5deece66d));
+        float jitter[3];
+        for (int i = 0; i < 3; i++)
+        {
+            state = state * UINT64_C(0x5deece66d) + 11;
+            float unit = (float)((state >> 24) & UINT64_C(0xffffff)) * 0x1p-24f;
+            jitter[i] = (unit - 0.5f) * 0.9f;
+        }
+        float vx = (t[0] - dx) + jitter[0];
+        float vy = (t[1] - dy) + jitter[1];
+        float vz = (t[2] - dz) + jitter[2];
+        /* Explicit rounding also prevents contraction on FMA-capable hosts. */
+        volatile float xx = vx * vx, yy = vy * vy, zz = vz * vz;
+        volatile float xy = xx + yy;
+        float distance = xy + zz;
+        if (distance < best)
+        {
+            best = distance;
+            out[0] = cx * 2; out[1] = cy * 2; out[2] = cz * 2;
+        }
+    }
+    return 0;
+}
 
 
 int mapOceanMixMod(const Layer * l, int * out, int x, int z, int w, int h)
@@ -254,6 +309,25 @@ int genBiomes(const Generator *g, int *cache, Range r)
         }
         else if (g->mc >= MC_1_18)
         {
+            if (g->mc == MC_26_50 && r.scale == 1)
+            {
+                int sy = r.sy ? r.sy : 1;
+                if (r.sx < 1 || r.sz < 1 || sy < 1 ||
+                    (int64_t)r.x + r.sx - 1 > INT_MAX ||
+                    (int64_t)r.y + sy - 1 > INT_MAX ||
+                    (int64_t)r.z + r.sz - 1 > INT_MAX)
+                    return -1;
+                size_t index = 0;
+                for (int iy = 0; iy < sy; iy++)
+                for (int iz = 0; iz < r.sz; iz++)
+                for (int ix = 0; ix < r.sx; ix++)
+                {
+                    int q[3];
+                    getBedrockBiomeQuart(g->seed, r.x + ix, r.y + iy, r.z + iz, q);
+                    cache[index++] = sampleBiomeNoise(&g->bn, NULL, q[0], q[1], q[2], NULL, 0);
+                }
+                return 0;
+            }
             return genBiomeNoiseScaled(&g->bn, cache, r, g->sha);
         }
         else // g->mc <= MC_B1_7
diff --git a/vendor/cubiomes-bedrock/generator.h b/vendor/cubiomes-bedrock/generator.h
index d2b4809..2c83c68 100644
--- a/vendor/cubiomes-bedrock/generator.h
+++ b/vendor/cubiomes-bedrock/generator.h
@@ -91,6 +91,10 @@ int *allocCache(const Generator *g, Range r);
  * The return value is zero upon success.
  */
 int genBiomes(const Generator *g, int *cache, Range r);
+/** Bedrock 1.26.50 research model: block XYZ to the selected raw quart node.
+ * Only the jitter uses the lower 32 seed bits. Noise retains the full seed.
+ * Returns zero, or -1 for a null output. No stored-chunk ceiling is inferred. */
+int getBedrockBiomeQuart(uint64_t seed, int x, int y, int z, int out[3]);
 /**
  * Gets the biome for a specified scaled position. Note that the scale should
  * be either 1 or 4, for block or biome coordinates respectively.

```
