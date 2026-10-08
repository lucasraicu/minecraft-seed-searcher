# Phone validation — first observations

## Current progress

The three initial surface observations and three Overworld locate outputs have been recorded. Skip the initial surface/Overworld locate steps already completed; continue with the Nether commands below. Structure visits and landscape checks remain pending. Chunkbase now agrees closely with the three Overworld locate anchors, but the local Fortress fallback at (-152,120) has been disproved by the user's surrounding-area inspection and removed; actual Fortress locate is now recorded at (64,816), outside the Nether square; Bastion locate is recorded at (-680,-168), also outside; continue with actual positive visits and landscape checks. See [the comparison](../preflight/CHUNKBASE_COMPARISON.md).

| Type | Actual locate X, Z | Nearby predicted start X, Z | Inside diagnostic Overworld square? |
|---|---|---|---|
| Trial Chamber | −3689, 3513 | −3672, 3512 | Yes |
| Stronghold | −5134, 5522 | −5132, 5524 | No |
| Mineshaft | −3680, 3312 | −3672, 3320 | Yes |

Locate Y is unknown for all three. These coordinates are not visit confirmations. Actual observations are preserved in `fixtures/bedrock-26.52/seed-12345.user-observations.json`; regenerating this packet does not replace that fixture.

The diagnostic playable square is **3008 × 3008**, centered at `(-3712,3328)`. The planned initial per-seed center-search window is separately **10,000 × 10,000** (±5000 each axis), with a **13,008 × 13,008** terrain envelope before sample-grid snapping. This is bounded regional coverage, not an entire-world scan.

## Commands and predictions

Create a disposable **default-generation Bedrock 26.52 world with seed `12345`**, cheats and Show Coordinates enabled.
Use Spectator mode for inspection. These predictions have not been checked in game.

```text
/gamemode spectator
```

At each X/Z, report water versus land, natural ground Y if on land, and whether the surroundings are wooded.
Ground Y is feet Y minus one when standing on the natural ground, excluding logs/leaves.

| Location | Command | Predicted ground / biome |
|---|---|---|
| 0, 0 | `/tp @s 0 320 0` | 48 / ocean |
| 256, 256 | `/tp @s 256 320 256` | 90 / dark_forest |
| 256, -256 | `/tp @s 256 320 -256` | 146 / grove |

After the first terrain observations, check these core structures from the indicated reference positions:

`/tp @s -3712 320 3328`
```text
/locate structure minecraft:trial_chambers
/locate structure minecraft:stronghold
/locate structure minecraft:mineshaft
```

For the Nether, use:

```text
/execute in nether run tp @s -464 80 416
/locate structure minecraft:fortress
/locate structure minecraft:bastion_remnant
```

Send the coordinates returned by each command, including structures outside the border. Do not assume they are inside.
The matching predicted starts are recorded in `probe.json`; compare nearby starts rather than assuming identical locate offsets.

| Type | Nearest predicted start inside border (X, Z) | Distance from reference center |
|---|---|---:|
| trial_chamber | -3672, 3512 | 188.3 |
| stronghold | None predicted in this square; actual presence unknown | — |
| mineshaft | -3672, 3320 | 40.8 |
| ancient_city | None predicted in this square; actual presence unknown | — |
| village | -4072, 4552 | 1275.8 |
| ruined_portal | -3560, 3528 | 251.2 |
| shipwreck | -3752, 3096 | 235.4 |
| monument | -3000, 3640 | 777.4 |
| outpost | None predicted in this square; actual presence unknown | — |
| fortress | None predicted in this square after correction | — |
| bastion | -392, 792 | 382.8 |

Fill `actual_x` and `actual_z` for a `/locate` result. Leave `actual_y` null if the command gives no usable Y.
Set `actual_generated` only after visiting: true when the structure is present; false for an inspected prediction that is absent. Leave unvisited entries null.
`compare` reports nearby placement/viable starts and offsets, but does not equate a locate coordinate with a start or certify a structure match.

Island separation, an actual bridge negative example, surrounding mountains and forest abundance still need landscape inspection.
The map center is a diagnostic prediction, not a proposed final seed or a verified island.

Sources: [locate syntax](https://learn.microsoft.com/en-us/minecraft/creator/commands/commands/locate?view=minecraft-bedrock-stable), [dimension commands](https://learn.microsoft.com/en-us/minecraft/creator/commands/commands/execute?view=minecraft-bedrock-stable).

## Recorded actual Fortress locate

User report: `(64,816)`, Y unknown, unvisited. Ordinary predicted start `(72,824)` is 11.3 blocks away; actual locate anchor is outside the eastern edge X=32. The user inspected around former fallback `(-152,120)` and reports no Fortress. The false prediction was removed; no further inspection of that spot is requested.

## Recorded actual Bastion locate

User report: `(-680,-168)`, Y/reference/visit unknown. Exact local viable start; 88 blocks beyond minimum-Z boundary Z=-80. Chunkbase previously listed Treasure-room anchor (-669,-194), 28.2 blocks away. A located anchor is not a confirmed visit or in-border requirement pass. Both requested Nether locate outputs are recorded; the former Fortress (-152,120) has been inspected and reported absent. Continue with positive visits and landscape checks.
