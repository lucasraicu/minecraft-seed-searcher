# Chunkbase comparison — seed 12345, 7 October 2026

**Current result:** the user subsequently inspected around Nether (-152,120) and reports no Fortress. The false local promotion of failed Bastion attempts was removed; all 44 tests pass. The refreshed diagnostic square contains no predicted Fortress. Earlier sections below preserve the sequence of evidence.

Interactive browser access works in the resumed conversation. Selected seed **12345**, **Bedrock 26.50–26.52**, and the appropriate Overworld/Nether dimension on [Chunkbase Seed Map](https://www.chunkbase.com/apps/seed-map). The separately stored [prediction fixture](../../fixtures/bedrock-26.52/seed-12345.chunkbase-predictions.json) preserves this evidence without changing the actual phone-observation fixture.

## Overworld comparison

Reference X/Z `(-3712,3328)`.

| Structure | Phone locate X/Z | Chunkbase X/Z | Horizontal difference |
|---|---|---|---:|
| Trial Chamber | (-3689,3513) | (-3689,3513), Y=-23 | 0 blocks |
| Stronghold | (-5134,5522) | (-5132,5524), Stairway | 2.8 blocks |
| Mineshaft | (-3680,3312) | (-3672,3320) | 11.3 blocks |

These three anchors agree closely. Chunkbase and the local prototype return identical Stronghold and Mineshaft starts; Chunkbase returns the phone's exact Trial Chamber X/Z. Differences in anchor definitions remain relevant. Chunkbase's Mineshaft result list put the corresponding 41m entry at index 7, after a 79m first entry; its results must not be treated as strictly distance-sorted. No actual structure visits are inferred.

## Nether results and discrepancy

Reference `(-464,416)`, diagnostic square X `[-960,32]`, Z `[-80,912]`.

| Chunkbase structure | Anchor X/Z | Nearby local start X/Z | Anchor inside square? |
|---|---|---|---|
| Fortress (Crossing) | (75,827) | (72,824) | No; 43 blocks beyond eastern edge |
| Bastion (Treasure room) | (-418,765), Y=33 | (-392,792) | Yes |
| Bastion (Treasure room) | (-642,829) | (-616,856) | Yes |
| Bastion (Housing units) | (-537,-6) | (-552,24) | Yes |

The local model additionally reports a Fortress at **(-152,120)** inside the square. This did not appear in Chunkbase's observed Fortress search list. The local region `(-1,0)` has no direct Fortress attempt; its Bastion attempt is `(-152,120)` and fails local biome viability in Basalt Deltas. `native/bridge.c` then promotes that attempt into the Fortress scan. `test_fortress_fallback_is_kept` verifies the implementation of this rule, not its agreement with actual Bedrock generation.

Treat that fallback prediction as **unresolved**, not a validated in-border Fortress. A 99-result capped third-party list does not prove actual absence; the next decisive evidence is the user's in-game Fortress locate result and inspection of the disputed location. Leave the generator behavior unchanged until the disagreement is resolved. No large search or ranking pilot has run.

## Next actual-game check

In the same seed 12345 world:

```text
/gamemode spectator
/execute in nether run tp @s -464 80 416
/locate structure minecraft:fortress
/locate structure minecraft:bastion_remnant
```

Record the returned X/Z separately from the Chunkbase predictions. Actual visits and landscape/forest calibration remain required. Do not reuse third-party predictions as phone observations or automatically open the search gate.

## New phone Fortress locate result

The user reported **X=64, Z=816**, with Y unknown, in response to the requested locate from Nether `(-464,416)`. No visit or independently confirmed reference was supplied. The actual locate anchor is 11.3 blocks from the ordinary local start `(72,824)` and 15.6 blocks from Chunkbase's crossing `(75,827)`. The actual anchor is **32 blocks beyond the eastern border X=32**.

This supports the ordinary Fortress placement near Chunkbase's prediction and increases concern about the additional in-border fallback `(-152,120)`. It does not alone establish absence at the fallback spot; inspect that location before removing the rule. The actual locate is saved in the phone fixture, with `actual_generated` and Y left null. Bastion locate and visits remain pending.

## New phone Bastion locate result

The user reported **X=-680, Z=-168**, with Y unknown. The actual command reference and visit status were not supplied; do not infer nearest-result ordering from the earlier requested reference. This matches the local viable Bastion start exactly. The previously observed Chunkbase list's fourth entry was Treasure-room Bastion `(-669,-194)`, 28.2 blocks away. These are different coordinate anchors, not an inferred structure visit.

The phone locate anchor is **88 blocks beyond the minimum-Z edge Z=-80** of the diagnostic Nether square. This is useful compatibility evidence outside the square; it does not establish an in-border Bastion or disprove the other predicted in-border Bastions. The disputed Fortress fallback `(-152,120)` still needs inspection.

## Disputed Fortress point inspection

The user teleported to **(-152,70,120)**, reported netherrack and no visible structure, and was unable to leave the surrounding block mass after using TNT. Surrounding positions/heights were not inspected. Record this as an **obstructed point inspection** with generation status unknown, not a confirmed whole-Fortress absence. It does not validate the fallback. Spectator mode and `/execute in overworld run tp @s 256 160 -256` were provided to return to the previously observed spruce location. No successful escape has been reported yet.

## Fortress false positive corrected

The user followed up after looking around the supposed Fortress area and reports none. Generation absence is now recorded separately from the initially obstructed point inspection. Removed the local adapter's failed-Bastion promotion, rebuilt it, and verified 44 passing tests. The absent prediction no longer appears in either raw placement or viable Fortress scans; ordinary Fortress (72,824) and Bastion (-680,-168) starts remain. [Correction record](fortress-correction.json). The search gate stays closed pending the remaining actual visits and landscape checks.
