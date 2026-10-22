# Practical accuracy evidence

`manifest.json` checksums every member of the101-file `accuracy-evidence-v2.tar.gz`.
The original84-file archive and its manifest remain preserved. Version2 adds
reproduction sources to the same raw observations; it does not rerun or relabel them.
The archive contains eight fresh default-world point experiments, frozen native
predictions, independent saved metadata/biome bytes, explicit aliases, bounded
Beta-copy type witnesses, camp command discriminators and an owned-copy persistence
repair. Generated world databases, credentials and game binaries are excluded.

Replay without Docker or native generation:

```sh
.venv/bin/python -m pytest -q tests/test_accuracy_game_evidence.py tests/test_accuracy_storage_reader.py
```

The default pilot contains four blind and four targeted worlds. Counts and ID/name
associations have their stated finite scopes. First-player landing and complete
physical instance totals were not verified. Historical missing records and failed
methods are retained; supplementary success does not rewrite their original result.
See docs/catalog/ACCURACY.md and reviews/correction-plan-2026-10-21/ACCURACY_RECONCILIATION.md.
