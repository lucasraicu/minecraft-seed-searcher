# Predictor resolution evidence (BDS 1.26.52.3)

Portable, hash-bound replay of two known seeds, four fresh lifecycle worlds, and
five copied-world structure-membership runs. `manifest.json` inventories raw
reports, console output, settings, frozen inputs, observers and reference excerpts.
It does not certify every biome or structure in a world.

```sh
python3 -S scripts/predictor_diagnostics.py --resolution-fixtures fixtures/bedrock-26.52/predictor-resolution
```

The command performs no game execution. It validates report identities and hashes,
preserves empty membership observations, and distinguishes locate coordinates from
physical structure membership. Existing storage-regressions and predictor-corrections
fixtures retain their original strict decoding/name policies.

Persistence: read-only API calls followed by an equal 200-tick dwell saved 9/11
requested chunk records across the two worlds. Dirty/restore of an originally-air
Y319 block in fresh disposable worlds saved 11/11, with no marker left behind.
The new explicit repeat-section decoder makes all 78 points readable; separate
`old54-recovered.json` records recovery of all 54 earlier target coordinates in
these newly persisted worlds. This does not retroactively add records to old worlds.

Structures: beta Script API 2.11.0-beta on isolated copies confirmed the static
stronghold, village/outpost positive controls, and no village/outpost membership
in the two disputed start chunks. Four complete 16×384×16 chunk volumes contain
393,216 query positions. Membership totals count blocks, not distinct structures.
No empty point or locate discrepancy alone establishes structure absence.

Reference material retained with its license:

- Dragonfly disk palette decoder, commit
  `4c7b5074be94fa83a1cd98e9c752083ad04a6e21`:
  https://github.com/df-mc/dragonfly/blob/4c7b5074be94fa83a1cd98e9c752083ad04a6e21/server/world/chunk/decode.go
  (`reference/dragonfly-decode.go`, MIT license). A repeat marker inherits the
  entire previous section array; it is not a uniform fill with one value.
- Mojang bedrock-samples `behavior_pack/biomes/` redwood mutated biome files and
  `behavior_pack/entities/wolf.json` Chestnut filter excerpt:
  https://github.com/Mojang/bedrock-samples
  (`reference/` excerpts and Mojang license). These support the canonical name
  old_growth_spruce_taiga, rather than ordinary taiga, for both mutated redwood IDs.

See the resolution report under `reviews/predictor-resolution-2026-10-20/` for
hypotheses rejected against held-out controls and remaining native-model limits.
