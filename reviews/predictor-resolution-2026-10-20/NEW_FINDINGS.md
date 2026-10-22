# New observations for source reasoning

Four paired fresh BDS1.26.52.3 worlds with equal200tickwait, read_only vs
synchronous air->barrier->original permutation atY319 in each owned chunk.
Both modes2chunks persisted in world1; world0read_only7/9,dirty_restore9/9.
All markers restored, clean saves/stops, no original DB mutations. Post-generation
locate queries remain identical to pre-generation queries, including three remote
mismatches. Timing alone is not a robust persistence guarantee; explicitly dirtying
is a reliable tested procedure (not a universal engine theorem).

Full block-palette decode of persisted static-stronghold chunk(51,-107), seed
-9103892851552028103, finds stone_bricks,mossy_stone_bricks,cracked_stone_bricks,
infested_stone_bricks,stone_brick_slab, while locate(820,-1708) still returns
village-linked98,-2030. Block positioning/identity verification ongoing; never
remove static-stronghold enumeration merely to agree with locate.

Pure Data3D decode full-resolution atlocalx0,z0, seed-3509659830737203357:
X/Z(-256,-256): Y-64..-27 stored190(deep_darkAPI),-26..37stored12(ice_plainsAPI),
38..59stored188(dripstoneAPI),60..127stored12;upper0xff.
X/Z(-448,320): Y-64..-47 stored190, -46..30stored30(cold_taigaAPI),31..57stored187
(lushAPI),58..127stored30;upper0xff. These are whole block arrays, not4-block
lattices. Dragonfly pinned disk decoder explicitly inherits previous whole16³
array on0xff. Six oldunknown Y319 points inherit correct same-record control IDs;
new128/160/192/256/304/319 BDS comparisons being retained. No global ID equivalence.

Isolated native diagnostics:
- Rawquart floor(block/4): pilot253/256,cohort311/330,vertical25/28,fresh58/63.
- Rawquart plusY1: pilot256/256,cohort323/330,vertical27/28,fresh62/63; BREAKS
(-256,32,-256) originally correct. Thus cannot adopt blanket+4.
- Clone sampleBiomeNoise with double x,y,z and true x/4,y/4,z/4: fresh60/63,
misses bothY60 cave exits and thirdcaveY63; not a complete fix.
- TestedJava Voronoi seed variations(fullseedSHA,lower32SHA,signextendedSHA,zero,
SHAzero,rawseed/rawlower32/rawsigned32) andremovalof -2 inputoffsets. Best no-2
allaxes yields pilot256/256,cohort327/330(afteraliasbelow),vertical28/28,butfresh61/63;
not an exact fix. Do not pick variant on targeted score alone.

Existing name alias likely defective: redwood_taiga_mutated->taiga vs six native
old_growth_spruce_taiga predictions acrossthreeindependentseeds. Mojang current
bedrock-samples biome JSON tags this identifier mega+mutated+taiga; officialwolf
JSON calls matching biome-tagpredicate Old Growth Spruce Taiga. Other legacy aliases
need individual evidence; immutable diagnostic manifest retains historicalmapping.
This accounts for6previouslyreportedcohortmismatches, notphysicalgenerationerrors.

Goal: isolate defensible mechanism for fullblockcave/biome assignment differences
and distinguish locate selection from physical structures. Need falsifiable narrow
hypotheses and source evidence, not a new ad-hoc correction or universal claims.
