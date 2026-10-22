# World-spawn correction: fresh Bedrock controls

Eight signed seeds were frozen before generation, disjoint from the116 retained
controls. BDS1.26.52.3 / Script API2.10.0 default world-spawn X/Z at load and
ticks20/40 matched independent saved level.dat metadata and the corrected compiled
helper on all eight. No player joined. This does not verify first-player landing,
ground height, safety or all seeds/versions.

manifest.json checksums all31 members of spawn-evidence.tar.gz. It includes the
frozen protocol, predictions made before generation, API observations, independent
metadata-reader results and raw level.dat, observer/runner source, properties,
logs and helper build provenance. World databases and binaries stay excluded.
Two retained startup failures generated no world database; the repaired harness
created exactly the eight complete controls and removed its owned containers.

Replay the actual helper against both archived cohorts without running BDS:

```sh
.venv/bin/python -m pytest -q tests/catalog/test_spawn_world_reference.py
```

The helper is built once outside the repository for this test; the personal native
engines are neither rebuilt nor replaced.
