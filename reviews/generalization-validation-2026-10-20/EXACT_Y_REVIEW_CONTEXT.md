# Neutral High review: block Y for village preliminary biome checks
User approved bounded BDS generalization audit; insists rejection rules must not weed out real villages. Before any consequential predictor implementation, critique this narrow proposal. No production native edit yet. No commands/network/readers/edits/agents. Use only this supplied evidence. Distinguish proven cause vs plausible remaining float/cache/version details. <=700 words final.

Pinned BDS 1.26.52.3 binary SHA256 0a490c711d4a2ce075debcd979e8862b7eaba008373f9970f0edbb67f98f9207. Village ending calls BiomeSource3d::containsOnly center(chunk*16+8, preliminaryHeight), radius2. containsOnly at0x493b030 really checks all8 corners, step4, in3D. It calls _getBiome vtable+0x38. _getBiome0x493b2a0 may use old-chunk blending cache; noncache fallback0x51582f0 shown below. Do not assume blending active in default fresh worlds. Its X/Z sar2; block Y extracted int16 then NO sar2, float*(-1/128)+1+offset. ELF constants independently read:0x1098698=-0.0078125;0x10983f0=1.0.

Current native helper rounds ALL XYZ down to quart coords, so height-2 samples lower4plane. Radius remains2, full3Dcube necessary; do not remove cave sensitivity/check onlycenter. Outpost radius0heightmultiple8 unaffected bythisYquantization.

Proposed implementation: private core sampleBiomeNoise accepting double quartY; existing public intquartY API wraps unchanged semantics; new sampleBiomeNoiseAtBlockY converts exactblockY/4.0 and preserves np/dat/flags. MC_26_50 preliminary structure helper only calls newAPI (floorX/Z unchanged). All scales, ordinary generator sampling, oldversions, fullcube andcenterID retained. Do not change globally float algebra/quantization without separate evidence. Tests: integerquart parity inclnp/dat/flags vs prepatch compiledsource; all3newBDSpositive village cases;51oldpositives/two oldabsencecontrols; existing8320+330+3920native parity. New heldout worlds continue using frozen BEFORE-fix predictions for honest comparison. No seed exceptions/candidate blacklist/tolerances.

## Three BDS exact positive counterexamples
[
  {
    "case_id": "2-68",
    "structure_type": "village",
    "dimension": "overworld",
    "disposition": "rejected",
    "predicted": [
      -472,
      -328
    ],
    "origin": [
      -472,
      -328
    ],
    "reported": [
      -472,
      -328
    ],
    "outcome": "reference_exact",
    "grouped_command": false,
    "interpretation": "Game locate agrees with predicted reference; not a physical census; possible over-rejection: retain and investigate this candidate",
    "seed": "4613350367979055430",
    "cohort": "blind",
    "rejection_basis": "current_raw_placement_rejection"
  },
  {
    "case_id": "16-70",
    "structure_type": "village",
    "dimension": "overworld",
    "disposition": "rejected",
    "predicted": [
      -1048,
      -1432
    ],
    "origin": [
      -1048,
      -1432
    ],
    "reported": [
      -1048,
      -1432
    ],
    "outcome": "reference_exact",
    "grouped_command": false,
    "interpretation": "Game locate agrees with predicted reference; not a physical census; possible over-rejection: retain and investigate this candidate",
    "seed": "5050725658938791990",
    "cohort": "targeted",
    "rejection_basis": "removed_by_engine_fix"
  },
  {
    "case_id": "16-71",
    "structure_type": "village",
    "dimension": "overworld",
    "disposition": "rejected",
    "predicted": [
      2888,
      -2616
    ],
    "origin": [
      2888,
      -2616
    ],
    "reported": [
      2888,
      -2616
    ],
    "outcome": "reference_exact",
    "grouped_command": false,
    "interpretation": "Game locate agrees with predicted reference; not a physical census; possible over-rejection: retain and investigate this candidate",
    "seed": "5050725658938791990",
    "cohort": "targeted",
    "rejection_basis": "removed_by_engine_fix"
  }
]
## Isolated exactY prototype (old viability 0, new1; 51 oldpositives1,2knownbad0)
5050725658938791990 -1048 -1432 48 0 1
5050725658938791990 2888 -2616 72 0 1
-3509659830737203357 -296 -312 24 0 0
-3509659830737203357 528 512 136 0 0
-3509659830737203357 -1816 264 56 1 1
-3509659830737203357 -1480 -344 48 1 1
-3509659830737203357 -1464 248 56 1 1
-3509659830737203357 -1448 -744 56 1 1
-3509659830737203357 -1432 1256 56 1 1
-3509659830737203357 -1416 -1400 64 1 1
-3509659830737203357 -904 840 56 1 1
-3509659830737203357 -888 136 72 1 1
-3509659830737203357 -760 1272 56 1 1
-3509659830737203357 -504 1848 56 1 1
-3509659830737203357 -360 248 96 1 1
-3509659830737203357 -344 712 104 1 1
-3509659830737203357 -296 -1528 56 1 1
-3509659830737203357 -248 1320 56 1 1
-3509659830737203357 -232 -904 104 1 1
-3509659830737203357 40 -1880 48 1 1
-3509659830737203357 88 1880 48 1 1
-3509659830737203357 136 -1608 56 1 1
-3509659830737203357 264 -872 104 1 1
-3509659830737203357 760 -920 56 1 1
-3509659830737203357 824 -1512 56 1 1
-3509659830737203357 1144 1272 56 1 1
-3509659830737203357 1176 -792 56 1 1
-3509659830737203357 1176 -376 88 1 1
-3509659830737203357 1256 -1480 56 1 1
-3509659830737203357 1320 792 56 1 1
-3509659830737203357 1832 40 56 1 1
-9103892851552028103 -264 344 56 1 1
-9103892851552028103 296 360 56 1 1
-9103892851552028103 -376 -488 56 1 1
-9103892851552028103 -944 320 80 1 1
-9103892851552028103 3008 -640 56 1 1
-9103892851552028103 1696 2752 56 1 1
-9103892851552028103 -2008 -1480 56 1 1
-9103892851552028103 744 1384 56 1 1
-9103892851552028103 -3280 -832 48 1 1
-4565879772552070118 -856 -312 56 1 1
-4565879772552070118 376 1240 56 1 1
-4565879772552070118 -1320 88 56 1 1
-4565879772552070118 -432 656 80 1 1
-4565879772552070118 208 1728 56 1 1
-4565879772552070118 -816 -1968 72 1 1
-4565879772552070118 -1880 -1896 64 1 1
-4565879772552070118 840 1256 88 1 1
-4565879772552070118 -2256 -2176 64 1 1
3477702448211353566 -200 40 72 1 1
3477702448211353566 312 104 48 1 1
3477702448211353566 328 -200 88 1 1
3477702448211353566 -832 512 56 1 1
3477702448211353566 224 1344 88 1 1
3477702448211353566 -1856 -528 112 1 1

Additional blind seed4613350367979055430 (-472,-328), height56 old0/new1; BDSexact reference.
## Current helper
```c
/* Bedrock checks raw 3D biomes at a preliminary density height, rather than
 * the actual surface or sky. Keep the seed-independent spline local so calls
 * from independent search threads share no mutable initialization state. */
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
        int id = getBiomeAt(g, 4, floordiv(cx * 16 + 8 + dx, 4),
                            floordiv(y, 4), floordiv(cz * 16 + 8 + dz, 4));
        if (id < 0 || !isViableFeatureBiome(g->mc, type, id)) return 0;
    }
    if (lo <= hi)
        *centerId = getBiomeAt(g, 4, cx * 4 + 2, floordiv(height, 4), cz * 4 + 2);
    return 1;
}

```
## Current sampler
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
## BDS fallback assembly
```

/Users/lucasraicu/.local/share/antigravity-worker-mcp/predictor-engine-20261020/bedrock_server:	file format elf64-x86-64

Disassembly of section .text:

0000000004008240 <.text>:
 51582f0:      	push	r15
 51582f2:      	push	r14
 51582f4:      	push	r12
 51582f6:      	push	rbx
 51582f7:      	sub	rsp, 0x58
 51582fb:      	mov	r14, rdx
 51582fe:      	mov	r15, rsi
 5158301:      	mov	rbx, rdi
 5158304:      	mov	eax, r14d
 5158307:      	sar	eax, 0x2
 515830a:      	sar	ecx, 0x2
 515830d:      	cvtsi2ss	xmm0, eax
 5158311:      	movss	dword ptr [rsp + 0x10], xmm0
 5158317:      	lea	r12, [rsi + 0x118]
 515831e:      	cvtsi2ss	xmm2, ecx
 5158322:      	movss	dword ptr [rsp + 0x8], xmm2
 5158328:      	xorps	xmm1, xmm1
 515832b:      	mov	rdi, r12
 515832e:      	call	0xd2414e0 <.text+0x92392a0>
 5158333:      	mulss	xmm0, dword ptr [rip - 0x40bfb43] # 0x10987f8
 515833b:      	movss	xmm1, dword ptr [rsp + 0x10]
 5158341:      	addss	xmm0, xmm1
 5158345:      	movss	dword ptr [rsp + 0xc], xmm0
 515834b:      	xorps	xmm2, xmm2
 515834e:      	mov	rdi, r12
 5158351:      	movss	xmm0, dword ptr [rsp + 0x8]
 5158357:      	call	0xd2414e0 <.text+0x92392a0>
 515835c:      	movaps	xmm2, xmm0
 515835f:      	mulss	xmm2, dword ptr [rip - 0x40bfb6f] # 0x10987f8
 5158367:      	addss	xmm2, dword ptr [rsp + 0x8]
 515836d:      	movss	dword ptr [rsp + 0x8], xmm2
 5158373:      	lea	rdi, [r15 + 0x70]
 5158377:      	xorps	xmm1, xmm1
 515837a:      	movss	xmm0, dword ptr [rsp + 0xc]
 5158380:      	call	0xd2414e0 <.text+0x92392a0>
 5158385:      	movss	dword ptr [rsp + 0x10], xmm0
 515838b:      	lea	rdi, [r15 + 0xa8]
 5158392:      	xorps	xmm1, xmm1
 5158395:      	movss	xmm0, dword ptr [rsp + 0xc]
 515839b:      	movss	xmm2, dword ptr [rsp + 0x8]
 51583a1:      	call	0xd2414e0 <.text+0x92392a0>
 51583a6:      	movss	dword ptr [rsp + 0x14], xmm0
 51583ac:      	lea	rdi, [r15 + 0xe0]
 51583b3:      	xorps	xmm1, xmm1
 51583b6:      	movss	xmm0, dword ptr [rsp + 0xc]
 51583bc:      	movss	xmm2, dword ptr [rsp + 0x8]
 51583c2:      	call	0xd2414e0 <.text+0x92392a0>
 51583c7:      	movss	xmm1, dword ptr [rsp + 0x10]
 51583cd:      	movss	dword ptr [rsp + 0x20], xmm1
 51583d3:      	movaps	xmm2, xmmword ptr [rip - 0x3d7083a] # 0x13e7ba0
 51583da:      	movaps	xmm1, xmm0
 51583dd:      	andps	xmm1, xmm2
 51583e0:      	addss	xmm1, dword ptr [rip - 0x40bfebc] # 0x109852c
 51583e8:      	andps	xmm1, xmm2
 51583eb:      	addss	xmm1, dword ptr [rip - 0x40bfb4b] # 0x10988a8
 51583f3:      	mulss	xmm1, dword ptr [rip - 0x40bfacb] # 0x1098930
 51583fb:      	movss	xmm2, dword ptr [rsp + 0x14]
 5158401:      	movss	dword ptr [rsp + 0x24], xmm2
 5158407:      	movss	dword ptr [rsp + 0x28], xmm1
 515840d:      	movaps	xmmword ptr [rsp + 0x40], xmm0
 5158412:      	movss	dword ptr [rsp + 0x2c], xmm0
 5158418:      	lea	rax, [rsp + 0x20]
 515841d:      	mov	qword ptr [rsp + 0x30], rax
 5158422:      	mov	eax, dword ptr [r15 + 0x200]
 5158429:      	mov	ecx, 0xffffffff
 515842e:      	cmp	rax, rcx
 5158431:      	je	0x515857c <.text+0x115033c>
 5158437:      	lea	rsi, [r15 + 0x188]
 515843e:      	shr	r14, 0x20
 5158442:      	lea	rcx, [rsp + 0x30]
 5158447:      	mov	qword ptr [rsp + 0x38], rcx
 515844c:      	lea	rcx, [rip + 0x9cfb21d]  # 0xee53670
 5158453:      	lea	rdi, [rsp + 0x38]
 5158458:      	call	qword ptr [rcx + 8*rax]
 515845b:      	addss	xmm0, dword ptr [r15 + 0x350]
 5158464:      	movss	dword ptr [rsp + 0x1c], xmm0
 515846a:      	xorps	xmm1, xmm1
 515846d:      	mov	rdi, r15
 5158470:      	movss	xmm0, dword ptr [rsp + 0xc]
 5158476:      	movss	xmm2, dword ptr [rsp + 0x8]
 515847c:      	call	0xd2414e0 <.text+0x92392a0>
 5158481:      	movss	dword ptr [rsp + 0x18], xmm0
 5158487:      	add	r15, 0x38
 515848b:      	xorps	xmm1, xmm1
 515848e:      	mov	rdi, r15
 5158491:      	movss	xmm0, dword ptr [rsp + 0xc]
 5158497:      	movss	xmm2, dword ptr [rsp + 0x8]
 515849d:      	call	0xd2414e0 <.text+0x92392a0>
 51584a2:      	movss	xmm1, dword ptr [rsp + 0x18]
 51584a8:      	xorps	xmm2, xmm2
 51584ab:      	cvtss2sd	xmm2, xmm1
 51584af:      	movsd	xmm1, qword ptr [rip - 0x3d67fcf] # 0x13f04e8
 51584b7:      	mulsd	xmm2, xmm1
 51584bb:      	cvttsd2si	rax, xmm2
 51584c0:      	movsx	ecx, r14w
 51584c4:      	xorps	xmm2, xmm2
 51584c7:      	cvtsi2ss	xmm2, ecx
 51584cb:      	mulss	xmm2, dword ptr [rip - 0x40bfe3b] # 0x1098698
 51584d3:      	addss	xmm2, dword ptr [rip - 0x40c00eb] # 0x10983f0
 51584db:      	addss	xmm2, dword ptr [rsp + 0x1c]
 51584e1:      	cvtss2sd	xmm0, xmm0
 51584e5:      	mulsd	xmm0, xmm1
 51584e9:      	cvttsd2si	rcx, xmm0
 51584ee:      	movss	xmm0, dword ptr [rsp + 0x10]
 51584f4:      	cvtss2sd	xmm0, xmm0
 51584f8:      	mov	qword ptr [rbx], rax
 51584fb:      	mulsd	xmm0, xmm1
 51584ff:      	cvttsd2si	rdx, xmm0
 5158504:      	mov	qword ptr [rbx + 0x8], rcx
 5158508:      	movss	xmm0, dword ptr [rsp + 0x14]
 515850e:      	cvtss2sd	xmm0, xmm0
 5158512:      	mulsd	xmm0, xmm1
 5158516:      	cvttsd2si	rsi, xmm0
 515851b:      	xorps	xmm0, xmm0
 515851e:      	cvtss2sd	xmm0, xmm2
 5158522:      	mov	qword ptr [rbx + 0x10], rdx
 5158526:      	mulsd	xmm0, xmm1
 515852a:      	cvttsd2si	rdi, xmm0
 515852f:      	mov	qword ptr [rbx + 0x18], rsi
 5158533:      	mov	qword ptr [rbx + 0x20], rdi
 5158537:      	movaps	xmm0, xmmword ptr [rsp + 0x40]
 515853c:      	cvtss2sd	xmm0, xmm0
 5158540:      	mulsd	xmm0, xmm1
 5158544:      	cvttsd2si	r8, xmm0
 5158549:      	mov	qword ptr [rbx + 0x28], r8
 515854d:      	mov	qword ptr [rbx + 0x30], rax
 5158551:      	mov	qword ptr [rbx + 0x38], rcx
 5158555:      	mov	qword ptr [rbx + 0x40], rdx
 5158559:      	mov	qword ptr [rbx + 0x48], rsi
 515855d:      	mov	qword ptr [rbx + 0x50], rdi
 5158561:      	mov	qword ptr [rbx + 0x58], r8
 5158565:      	mov	qword ptr [rbx + 0x60], 0x0
 515856d:      	mov	rax, rbx
 5158570:      	add	rsp, 0x58
 5158574:      	pop	rbx
 5158575:      	pop	r12
 5158577:      	pop	r14
 5158579:      	pop	r15
 515857b:      	ret
 515857c:      	call	0x4831450 <.text+0x829210>
```
