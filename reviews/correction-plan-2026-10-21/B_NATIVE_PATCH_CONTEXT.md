# Actual approved B native patch review
User approved B_NATIVE_PROPOSAL.md. Review only actual diff and test source
provided. No edits/tools/tests; independent High source critique, <=550words.
Codex ran8new tests in9.71s atO3 with ff-contract off AND fast,16existingnative
checks alreadypass (98kquart+56extreme,14restoredVillage,916structures,8320stored,
330direct/3920raw). Actual newisolatedO3CFFI source72694b…5c1a/binary19a4b8…965e
passes8320stored/330direct/51positive/2negative/14restored/95outpost. Newportable
68.6KB evidencearchive42files keepsall8freshreports/logs/settings+manifest,
1260frozenAlegacybiomecases,324old-versionstructuregates,800rawfortress/bastion
selections.4unseenpairedseedworlds,100Netherpoints vs73old,13exactqueries incl
4restoredBastion+1City; selectionbiased controls, notcensus/universalaccuracy.
Native test originallyhad canonicalizationonlyone-side bug (hell vsnether_wastes),
fixedusingfrozenexplicit aliases onboth sides, nogameobs/nativebehaviorchanged.

Checkespecially coordinate overflow/safeint guards, float rounding/FMA/ties,
Yindependence/gridoutputorder/versiondimension scale boundaries, sourcegates,
fortresscoupling (getStructurePos alreadyrejectsnonfortresstype, no new fallback),
actualtestcoverage. Do not turn different locate intoabsence or require global
basalt allowance. KeepOWcached-ceiling unspecified,no hardcoded95.

```diff
--- A/generator.c
+++ B/generator.c
@@ -58,6 +58,44 @@
             out[0] = cx * 2; out[1] = cy * 2; out[2] = cz * 2;
         }
     }
+    return 0;
+}
+
+int getBedrockNetherQuart(uint64_t seed, int x, int z, int out[2])
+{
+    /* Source: Bedrock 26.50 Pos2d Zoom4xVoronoi. Keep the subtract-two,
+     * corner coordinates and coordinate*4 representable in signed int. */
+    if (!out || x < INT_MIN + 2 || z < INT_MIN + 2 ||
+        x > INT_MAX - 5 || z > INT_MAX - 5)
+        return -1;
+    int bx = floordiv(x - 2, 4), bz = floordiv(z - 2, 4);
+    float fx = (x - 2) - 4 * bx, fz = (z - 2) - 4 * bz;
+    uint64_t salt = getStartSalt(seed, getLayerSalt(10));
+    uint64_t start = mcStepSeed(salt, 0);
+    float distance[4];
+    for (int k = 0; k < 4; k++)
+    {
+        int dx = k & 1, dz = k >> 1;
+        uint64_t state = getChunkSeed(start, (bx + dx) * 4, (bz + dz) * 4);
+        /* The original chunk state supplies X; its next step supplies Z.
+         * Explicit binary32 rounding prevents host FMA contraction. */
+        volatile float ux = ((state >> 24) & 1023) * 0x1p-10f;
+        volatile float sx = ux - 0.5f;
+        volatile float jx = sx * 3.6f;
+        state = mcStepSeed(state, salt);
+        volatile float uz = ((state >> 24) & 1023) * 0x1p-10f;
+        volatile float sz = uz - 0.5f;
+        volatile float jz = sz * 3.6f;
+        float vx = fx - (jx + dx * 4.0f);
+        float vz = fz - (jz + dz * 4.0f);
+        volatile float xx = vx * vx, zz = vz * vz;
+        distance[k] = xx + zz;
+    }
+    /* Strict comparisons, including the source's final-corner tie fallback. */
+    int k = distance[0] < distance[1] && distance[0] < distance[2] && distance[0] < distance[3] ? 0 :
+            distance[1] < distance[0] && distance[1] < distance[2] && distance[1] < distance[3] ? 1 :
+            distance[2] < distance[0] && distance[2] < distance[1] && distance[2] < distance[3] ? 2 : 3;
+    out[0] = bx + (k & 1); out[1] = bz + (k >> 1);
     return 0;
 }
 
@@ -353,6 +391,26 @@
     }
     else if (g->dim == DIM_NETHER)
     {
+        if (g->mc == MC_26_50 && r.scale == 1)
+        {
+            int sy = r.sy ? r.sy : 1;
+            if (!cache || r.sx < 1 || r.sz < 1 || sy < 1 ||
+                (int64_t)r.x + r.sx - 1 > INT_MAX ||
+                (int64_t)r.z + r.sz - 1 > INT_MAX)
+                return -1;
+            size_t plane = (size_t)r.sx * r.sz, index = 0;
+            if (plane > SIZE_MAX / (size_t)sy / sizeof(*cache)) return -1;
+            for (int iz = 0; iz < r.sz; iz++)
+            for (int ix = 0; ix < r.sx; ix++)
+            {
+                int q[2];
+                if (getBedrockNetherQuart(g->seed, r.x + ix, r.z + iz, q)) return -1;
+                cache[index++] = getNetherBiome(&g->nn, q[0], 0, q[1], NULL);
+            }
+            for (int iy = 1; iy < sy; iy++)
+                memcpy(cache + (size_t)iy * plane, cache, plane * sizeof(*cache));
+            return 0;
+        }
         return genNetherScaled(&g->nn, cache, r, g->mc, g->sha);
     }
     else if (g->dim == DIM_END)
--- A/generator.h
+++ B/generator.h
@@ -95,6 +95,11 @@
  * Only the jitter uses the lower 32 seed bits. Noise retains the full seed.
  * Returns zero, or -1 for a null output. No stored-chunk ceiling is inferred. */
 int getBedrockBiomeQuart(uint64_t seed, int x, int y, int z, int out[3]);
+/** Bedrock 26.50 Nether Pos2d block XZ to a raw quart node, using the full
+ * 64-bit seed. Y does not participate. Returns -1 for null output or coordinates
+ * too close to signed-int edges for the source's subtract-two/corner arithmetic.
+ * Normal Minecraft world coordinates are supported. */
+int getBedrockNetherQuart(uint64_t seed, int x, int z, int out[2]);
 /**
  * Gets the biome for a specified scaled position. Note that the scale should
  * be either 1 or 4, for block or biome coordinates respectively.
--- A/finders.c
+++ B/finders.c
@@ -1599,6 +1599,17 @@
             return 0;
         if (structureType == Ruined_Portal_N)
             return 1;
+        if (structureType == Bastion && g->mc == MC_26_50)
+        {
+            /* containsOnly(origin, Y=1, radius=2) on the raw Pos2d
+             * biome source covers four quart cells, not the variant center. */
+            for (int qx = chunkX * 4 - 1; qx <= chunkX * 4; qx++)
+            for (int qz = chunkZ * 4 - 1; qz <= chunkZ * 4; qz++)
+                if (!isViableFeatureBiome(g->mc, Bastion,
+                        getNetherBiome(&g->nn, qx, 0, qz, NULL)))
+                    return 0;
+            return 1;
+        }
         if (structureType == Fortress)
         {   // in 1.18+ fortresses generate everywhere, where bastions don't
             StructureConfig sc;
@@ -1891,7 +1902,11 @@
 
     case Ancient_City:
         if (g->mc <= MC_1_18) goto L_not_viable;
-        id = getBiomeAt(g, 0, x>>2, -27>>2, z>>2);
+        if (g->mc == MC_26_50)
+            id = sampleBiomeNoiseAtBlockY(&g->bn, NULL,
+                    chunkX * 4, -27, chunkZ * 4, NULL, 0);
+        else
+            id = getBiomeAt(g, 0, x>>2, -27>>2, z>>2);
         if (id < 0 || !isViableFeatureBiome(g->mc, structureType, id))
             goto L_not_viable;
         goto L_viable;

```
