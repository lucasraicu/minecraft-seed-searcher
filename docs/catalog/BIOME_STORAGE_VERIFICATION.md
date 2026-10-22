# Stored-biome verification

The diagnostic tools compare explicit block coordinates with saved Overworld
Data3D biome records. They do not certify structure counts. The original experiment
is retained in [the historical stage report](../../reviews/storage-bds-verification-2026-10-20/REPORT.md).
The follow-up evidence is in [the resolution fixtures](../../fixtures/bedrock-26.52/predictor-resolution/README.md).

## Offline replay

`compare` needs only Python's standard library. Supply a JSON array of integer
block coordinates, for example `[[-256,-48,-256],[-256,63,-256]]` in `/tmp/points.json`:

```sh
python3 -S scripts/predictor_storage_probe.py compare   --export fixtures/bedrock-26.52/storage-regressions/world-0/export.json   --points /tmp/points.json
```

Each result preserves world seed, block XYZ, chunk/local/quart coordinates and
record checksum. `stored` supplies a saved-world numeric ID. `unknown_section`
means the section is absent or explicitly unknown; `missing_data3d_record` means
no matching exported record. Neither unknown status means biome absence or a
missing structure. Saved numeric IDs belong to a different namespace from native
predictor IDs; the tool deliberately does not guess a name mapping.

## Stopped-world export

The export tool accepts only a completed audit bound to its world directory,
pinned BDS image/build, exact seed and clean shutdown. Targeted reports also need
a save acknowledgement. Run against retained external evidence, with a new output
path outside the source world and repository:

```sh
python3 scripts/predictor_storage_probe.py export   --world /audit/world-0/worlds/world/worlds/spawn_audit   --report /audit/world-0/report.json --output /external/new-export.json
```

The source is mounted read-only. A network-disabled helper opens a temporary
LevelDB copy; source file hashes must match before and after export. Symlinks,
active overlapping mounts and excessive input sizes fail closed. The reader needs
the locally installed pinned container image and its LevelDB/NBT dependencies.

## Bounded game harness

```sh
python3 scripts/predictor_targeted_bds.py   --manifest reviews/storage-bds-verification-2026-10-20/CASES.json   --output /external/new-game-audit
```

This command is a dry run. `--execute` explicitly starts the frozen two-world
experiment; it is unnecessary for offline replay or tests. The harness checks
cumulative budgets before launch, verifies Script API seed/build identity, uses
owned containers, requests saves, stops cleanly and captures raw console output.
The manifest allows at most 54 biome reads, 3,530 block reads and six locate
commands. A column's highest non-air block can be water, vegetation or canopy;
it is not a guaranteed ground surface. Terrain observations do not establish a
structure rejection rule.

## Decoder boundaries

The pure Python decoder supports uniform and packed Data3D sections, YZX indexing,
negative world Y, word padding and explicit unknown markers. It bounds input to
1 MiB and 25 sections; the observed Overworld exports contain 24 sections starting
at section -4. Header heightmap values remain raw unsigned values without an
assumed elevation datum. The default strict decoder leaves repeat markers unknown. Explicit
`resolve_repeated_sections` / CLI `--resolve-repeats` retains the historical v2
whole-previous-section experiment for replay. Its agreement at the original,
mostly uniform high-Y coordinates did not establish Bedrock runtime semantics.
It must not be used as a runtime biome oracle.

Use `sample_bedrock_runtime` / CLI `--runtime-ceiling` (v3) for the separately
checked BDS 1.26.52.3 runtime interpretation. Above the explicit stored section
count, the game clamps to its last Y=15 plane. Three new copies (fresh generation,
reload, retained-world copy) agree at all 33 frozen coordinates each; the old v2
interpretation gives the wrong answers at three discriminating Y80 positions.
The pinned chunk lookup's above-count branch also explicitly selects the last
section and Y=15. Missing records, absent sections and unsupported interior
markers remain unknown. This storage rule does not impose a global Y cap on
seed-based biome generation. Evidence: `fixtures/bedrock-26.52/predictor-engine/`.
Synthetic packing tests and a separately produced Amulet-based
oracle check all 4,096 values in every populated exported section.

The historical exports still supply only 27/54 decoded points under strict v1:
21 points lack entire records and six Y319 points use repeat markers. Raw key
inspection confirmed that the missing records were not an export-filter bug.

In the equal-dwell follow-up, read-only calls saved 9/11 requested chunks;
explicitly dirtying and restoring an originally-air block in each fresh disposable
chunk saved 11/11. All 78 follow-up points decode with explicit repeat resolution,
and all original 54 target coordinates are now readable in the new worlds. This
is a tested persistence protocol, not a promise that every loaded chunk always
saves. Original stopped worlds were never mutated. Saved readability and predictor
accuracy are separate checks. The subsequent engine investigation identifies an
8-block biome sampling grid; integration and validation are tracked in
`reviews/predictor-resolution-2026-10-20/ENGINE_INTEGRATION_PLAN.md`.
