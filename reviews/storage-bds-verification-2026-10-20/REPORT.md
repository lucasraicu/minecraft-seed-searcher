# Storage verifier and targeted BDS stage — completed

The approved [two-world stage](../predictor-root-cause-2026-10-20/PLAN.md) is
complete. It delivers a bounded read-only storage verifier, portable regressions
and fresh game evidence. It does **not** resolve the remaining biome/structure
prediction errors or establish exact catalog counts. No native sampler,
production catalog, UI count or physical structure verification claim changed.

## Findings

Pinned BDS 1.26.52.3, Script API 2.10.0, reproduced all three selected structure
mismatches. The three positive controls agreed with their previously observed
coordinate conventions:

| Seed | Feature | Query X,Z | BDS locate X,Z | Interpretation |
|---|---|---|---|---|
| -3509659830737203357 | Village | -296,-312 | -888,136 | Known disagreement persists |
| -3509659830737203357 | Village | -360,248 | -360,248 | Positive control |
| -3509659830737203357 | Outpost | 528,512 | -1000,408 | Known disagreement persists |
| -3509659830737203357 | Outpost | -1008,400 | -1000,408 | Positive control, +8,+8 |
| -9103892851552028103 | Stronghold | 820,-1708 | 98,-2030 | Known disagreement persists |
| -9103892851552028103 | Stronghold | 100,-2028 | 98,-2030 | Positive control, -2,-2 |

These locate checks are not a physical structure census or proof of the game's
internal rejection cause. The outpost positive control does not explain the
remote failed outpost. Stronghold support remains unresolved.

The three selected cave disagreements at Y=63 reproduced. Two have readable
stored records: at (-256,63,-256), BDS reports ice_plains and storage ID 12 while
the quart predictor says dripstone_caves; at (-448,63,320), BDS reports cold_taiga
and storage ID 30 while the predictor says lush_caves. The third location lacks
an exported Data3D record. Stored IDs are not treated as predictor IDs or mapped
to names by assumption.

A proposed terrain shortcut is ruled out: BDS reports Deep Dark at
(-448,-48,320) inside **solid deepslate**, with saved ID 190. Replacing cave biomes
whenever the block is solid would erase a legitimate result. Depth-zero and
Y=319 flattening also erase valid underground biomes. No global sampling switch
is justified by this experiment.

| Fresh comparison cohort | Quart | Block | Depth zero | Y=319 |
|---|---:|---:|---:|---:|
| 45 fixed XYZ observations | 39 | 34 | 39 | 39 |
| 9 observations above highest non-air block | 9 | 9 | 9 | 9 |

Cells count matches after the existing explicit biome aliases. Equal totals hide
different failures. These are targeted repeats and positive controls, not held-out
population accuracy. Highest non-air includes water/canopy, not necessarily ground.
Column observations are descriptive; they do not establish structure viability.

## Storage evidence and implementation

The pure standard-library Data3D decoder handles bounded uniform/packed sections,
YZX ordering, negative coordinates, padding and explicit unknown markers. The
exporter binds stopped-world evidence to build/seed/report, mounts sources
read-only, opens only a temporary database copy and verifies unchanged source
hashes. Point replay preserves raw numeric namespaces and unknowns. Details and
commands: [BIOME_STORAGE_VERIFICATION.md](../../docs/catalog/BIOME_STORAGE_VERIFICATION.md).

Seven exported records contain 81 populated sections (29 packed, 52 uniform) and
87 unknown sections. Every one of the 4,096 block values in each populated section
matches an independent oracle produced with the reviewed decoding arithmetic from
[Amulet Core 1.9.25](https://github.com/Amulet-Team/Amulet-Core/blob/1.9.25/amulet/level/formats/leveldb_world/interface/chunk/base_leveldb_interface.py).
The retained reference source SHA-256 is
`8ef6c5213a1f32d5a953f83f355fe790472bd1a676f2f89b8c09050870d24004`.

**27/54 observed positions have readable stored values; 27 remain unknown.**
Some requested records were absent despite successful block reads, ticking areas,
save acknowledgements and clean shutdown. Missing records and unknown markers
are not evidence of biome or structure absence. No inherited palette or numeric
ID equivalence was invented to close this gap. The portable
[fixtures](../../fixtures/bedrock-26.52/storage-regressions/README.md) retain raw
reports, exports, checksums and the independent oracle.

## Execution, workers and validation

Both owned worlds finished with save acknowledgement, clean shutdown and container
removal. Total game harness wall time was **53.28 seconds**, using **54 biome reads,
2,055 block reads and six locate commands**, within the frozen maximum of
54/3,530/6 and the approved outer caps of 128/8,192/32. This is diagnostic runtime,
not a seed-search throughput benchmark. [RUN_SUMMARY.json](RUN_SUMMARY.json) and
[SAMPLING_COMPARISONS.json](SAMPLING_COMPARISONS.json) contain the results.

Gemini worker `c4e029f63fd3` implemented the decoder and its tests in an isolated
snapshot using `gemini-3.8-flash-high --effort high`. It completed in 303.10 seconds,
exit 0, denied_actions empty, 13 standalone tests passed; reported usage was
164,917 tokens. Codex reviewed the patch, added a pre-allocation memoryview size
check, implemented the exporter/game harness and independently verified integration.
The worker did not merge or push. Full terminal evidence is in
[GEMINI_DECODER_WORKER.json](GEMINI_DECODER_WORKER.json).

Final focused regression: **118 tests and 29 subtests passed** in 1.65 seconds,
covering storage, harness budgets, coordinate diagnostics, biome semantics and
catalog evidence/import. Observer JavaScript syntax passed. No production native
build, broad seed search or expensive benchmark was run. Browser QA remains
explicitly deferred; this stage changes no frontend.

The inherited dirty workspace and native binaries were preserved. Original Sweep
PID 60144 and the catalog preview processes were left running. Personal Sweep
still selects inspection run `web-sweep-20261020-143452-e5161c27`, seed
`-3336796033057908633`, saved diagnostic score 336 (the historical 281 used a
different relaxed policy). No commit, push, reset, stash or cleanup was performed.

## Remaining work

The next investigation should explain why some API-loaded chunks lack exported
records, then identify the actual Bedrock cave selection and structure viability
rules using controlled evidence. This stage does not authorize a native sampler
replacement, catalog migration or a larger game campaign. Keep existing evidence
gates and uncertain counts until those separate correctness questions are resolved.
