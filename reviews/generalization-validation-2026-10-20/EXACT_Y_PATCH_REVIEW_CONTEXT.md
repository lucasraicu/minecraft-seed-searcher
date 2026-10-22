# Approved exact-Y patch independent review
User approved NEXT_FIX_PLAN. Codex made only nativebiomenoise.c/h +finders.c changes. Positivecontrols51 andnegative2 pass unchanged tests/test_bedrock_engine_corrections.py (12passed). New tests4passed:14BDS-exactcounterexamples,98000 oldintegerquart vectors climate/cache/5flags/fourmodels/fiveseeds,negativefractionY/flags,916frozenoldstructure checks (outposts+oldermodels unchanged,allcurrentBDSexact village refs retained). Isolated O3CFFI build succeeds;full3411replay pending.
No deployment/catalogrefresh/primaryextensionreplacement. Review concrete correctness risks, full3D/clamp/version/center semantics,definedintegercompatibility,np/dat/flags. No floatreorder or broadermodelchanges. No tools/readers/commands/edits/network/delegates, <=650words final EXACT_Y_PATCH_REVIEW. Test failuresinitiallymissingtestreferenceheaders (fixed), notnativefailure.

--- before/vendor/cubiomes-bedrock/biomenoise.c
+++ after/vendor/cubiomes-bedrock/biomenoise.c
@@ -1203,7 +1203,7 @@
 
 
 /// Biome sampler for MC 1.18
-int sampleBiomeNoise(const BiomeNoise *bn, int64_t *np, int x, int y, int z,
+static int sampleBiomeNoiseCore(const BiomeNoise *bn, int64_t *np, int x, double y, int z,
     uint64_t *dat, uint32_t sample_flags)
 {
     if (bn->nptype >= 0)
@@ -1258,6 +1258,20 @@
     if (!(sample_flags & SAMPLE_NO_BIOME))
         id = climateToBiome(bn->mc, (const uint64_t*)p_np, dat);
     return id;
+}
+
+int sampleBiomeNoise(const BiomeNoise *bn, int64_t *np, int x, int y, int z,
+    uint64_t *dat, uint32_t sample_flags)
+{
+    return sampleBiomeNoiseCore(bn, np, x, y, z, dat, sample_flags);
+}
+
+/* X/Z remain quart coordinates; Y is an exact block coordinate. Keep the
+ * integer-quart entry point above for all existing grid/climate callers. */
+int sampleBiomeNoiseAtBlockY(const BiomeNoise *bn, int64_t *np, int x, int blockY, int z,
+    uint64_t *dat, uint32_t sample_flags)
+{
+    return sampleBiomeNoiseCore(bn, np, x, blockY / 4.0, z, dat, sample_flags);
 }
 
 // Note: Climate noise is sampled at a 1:1 scale.

--- before/vendor/cubiomes-bedrock/biomenoise.h
+++ after/vendor/cubiomes-bedrock/biomenoise.h
@@ -258,6 +258,9 @@
 void setBetaBiomeSeed(BiomeNoiseBeta *bnb, uint64_t seed);
 int sampleBiomeNoise(const BiomeNoise *bn, int64_t *np, int x, int y, int z,
     uint64_t *dat, uint32_t sample_flags);
+/* Quart X/Z with exact block Y; legacy integer-quart sampling stays separate. */
+int sampleBiomeNoiseAtBlockY(const BiomeNoise *bn, int64_t *np, int x, int blockY, int z,
+    uint64_t *dat, uint32_t sample_flags);
 int sampleBiomeNoiseBeta(const BiomeNoiseBeta *bnb, int64_t *np, double *nv,
     int x, int z);
 double approxSurfaceBeta(const BiomeNoiseBeta *bnb, const SurfaceNoiseBeta *snb,

--- before/vendor/cubiomes-bedrock/finders.c
+++ after/vendor/cubiomes-bedrock/finders.c
@@ -1568,12 +1568,14 @@
     for (int y = lo; y <= hi; y += 4)
     for (int dz = -radius; dz <= radius; dz += 4)
     {
-        int id = getBiomeAt(g, 4, floordiv(cx * 16 + 8 + dx, 4),
-                            floordiv(y, 4), floordiv(cz * 16 + 8 + dz, 4));
+        int id = sampleBiomeNoiseAtBlockY(&g->bn, NULL,
+                            floordiv(cx * 16 + 8 + dx, 4), y,
+                            floordiv(cz * 16 + 8 + dz, 4), NULL, 0);
         if (id < 0 || !isViableFeatureBiome(g->mc, type, id)) return 0;
     }
     if (lo <= hi)
-        *centerId = getBiomeAt(g, 4, cx * 4 + 2, floordiv(height, 4), cz * 4 + 2);
+        *centerId = sampleBiomeNoiseAtBlockY(&g->bn, NULL,
+                            cx * 4 + 2, height, cz * 4 + 2, NULL, 0);
     return 1;
 }
 

Existing helper/callsite context:
static int viablePreliminaryBiomes(int type, const Generator *g, int cx, int cz,
                                  int radius, int *centerId)
{
    TerrainShaper shaper;
    initTerrainShaper(&shaper);
    int height = getPreliminarySurfaceLevel(&g->bn, &shaper, cx * 4, cz * 4);
    int lo = height - radius, hi = height + radius;
    if (lo < -64) lo = -64;
    if (hi > 319) hi = 319;
    *centerId = 1;
    for (int dx = -radius; dx <= radius; dx += 4)
    for (int y = lo; y <= hi; y += 4)
    for (int dz = -radius; dz <= radius; dz += 4)
    {
        int id = sampleBiomeNoiseAtBlockY(&g->bn, NULL,
                            floordiv(cx * 16 + 8 + dx, 4), y,
                            floordiv(cz * 16 + 8 + dz, 4), NULL, 0);
        if (id < 0 || !isViableFeatureBiome(g->mc, type, id)) return 0;
    }
    if (lo <= hi)
        *centerId = sampleBiomeNoiseAtBlockY(&g->bn, NULL,
                            cx * 4 + 2, height, cz * 4 + 2, NULL, 0);
    return 1;
}

int isViableStructurePos(int structureType, Generator *g, int x, int z, uint32_t flags)
{
    int approx = 0; // enables approximation levels
    int viable = 0;

    int64_t chunkX = x >> 4;
    int64_t chunkZ = z >> 4;

    int sampleX, sampleZ, sampleY;
    int id;


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
            if 