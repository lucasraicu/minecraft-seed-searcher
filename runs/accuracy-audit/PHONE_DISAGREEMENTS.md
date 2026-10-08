# Minecraft checks for unresolved predictor disagreements

These are follow-up checks, not completed observations. Use a separate default-generation **Bedrock 26.52** world for each listed seed, with cheats enabled. Use `/gamemode spectator` before teleporting so buried locations do not trap you. Y values below are inspection heights, not verified structure elevations. Do not use TNT as a generation check.

| Seed | Dimension | Type | Chunkbase target X,Z | Local result |
|---|---|---|---|---|
| 12345 | Nether | Bastion Remnant | 1185,376 | Raw 1208,408 rejected by viability |
| -1 | Overworld | Stronghold | 6212,-4700 | No nearby local start |
| -1 | Overworld | Stronghold | 3524,-7276 | No nearby local start |
| -1 | Overworld | Ancient City | -3048,3256 | Exact raw start rejected by viability |
| 4294979641 | Overworld | Ancient City | -680,6216 | Exact raw start rejected by viability |
| 4294979641 | Nether | Bastion Remnant | 1185,376 | Same disagreement as seed 12345 |

From the matching world, use the relevant command sequence:

```mcfunction
/gamemode spectator
/execute in nether run tp @s 1185 80 376
/locate structure bastion_remnant
```

```mcfunction
/gamemode spectator
/execute in overworld run tp @s 6212 70 -4700
/locate structure stronghold
```

For the second stronghold, replace teleport coordinates with `3524 70 -7276`.

```mcfunction
/gamemode spectator
/execute in overworld run tp @s -3048 -40 3256
/locate structure ancient_city
```

For seed 4294979641’s ancient city, replace coordinates with `-680 -40 6216`.

Record the exact seed, version, dimension, `/locate` output and whether you can visually confirm the structure nearby. A locate output and a generation visit remain separate observations. Do not treat a single obstructed view as proof of absence. None of these checks require revisiting the previously skipped Overworld point.
