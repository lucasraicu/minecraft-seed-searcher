> **Current Realm target, 10 October 2026:** 4000×4000 discovery in both dimensions; 1536×1536 Overworld centered on the Stronghold; 896×896 Nether centered on exact Stronghold/8. See [COMPACT_SEARCH_IMPLEMENTATION_PLAN.md](COMPACT_SEARCH_IMPLEMENTATION_PLAN.md) and `config/realm.yaml`. The specifications, commands and measurements below describe earlier contracts; they do not override this target.

# Sweep commands for the implemented 2304/928 search

Implementation and bounded verification are complete; the production sweep is unstarted. **Reference is recommended: reserve 3–5 hours for 2000 seeds at 12 workers on this machine.** The staged 256-seed alternative is implemented; reserve **35–50 minutes**, including its raw scan and map export. The large reference command requires the new readiness record to pass live checks; historical records are incompatible.

From the project directory:

```sh
cd /Users/lucasraicu/Downloads/minecraft-seed-searcher
```

## Bounded lower32 / upper32 search

This configuration examines 10,000 new raw low32 layouts, retains 48 top + 16 exploration layouts, then evaluates four upper32 siblings each: **256 complete seeds**. It checks all four categories, all eleven supported structure families at full-seed viability, and the configured surface/Nether biome inventory. Raw reuse covers only the eight audited MT families. It does not certify every biome, cave or generated structure footprint.

Validate the exact command without starting it:

```sh
.venv/bin/python -m seed_search --config config/staged-sweep.yaml search --count 256 --start-index 10000 --workers 12 --output runs/staged-sweep-256 --dry-run
```

Start:

```sh
.venv/bin/python -m seed_search --config config/staged-sweep.yaml search --count 256 --start-index 10000 --workers 12 --output runs/staged-sweep-256
```

Resume after interruption:

```sh
.venv/bin/python -m seed_search resume --run runs/staged-sweep-256 --workers 12
```

In staged mode `--start-index` starts the **raw layout interval**. The full job IDs begin at that index, but each candidate also records its selected `layout_index`, retained slot and sibling index. A subsequent independent raw interval starts at **20000**, rather than advancing by the 256 full-seed count. Use a new output directory for that interval. Resume always reuses the original frozen selection and completed full-seed IDs.

## Larger full64 reference search

This evaluates 2000 independent complete seeds after the first 256 reference enumeration indices used for verification. It remains gated by the new configuration/source/runtime/evidence identity.

Validate:

```sh
.venv/bin/python -m seed_search --config config/reference-sweep.yaml search --count 2000 --start-index 256 --workers 12 --readiness runs/implementation-2026-10-08/readiness.json --output runs/reference-sweep-2000 --dry-run
```

Start:

```sh
.venv/bin/python -m seed_search --config config/reference-sweep.yaml search --count 2000 --start-index 256 --workers 12 --readiness runs/implementation-2026-10-08/readiness.json --output runs/reference-sweep-2000
```

Resume:

```sh
.venv/bin/python -m seed_search resume --run runs/reference-sweep-2000 --workers 12
```

## Results and recovery

Open `candidates.json`, `candidates.csv`, `summary.json` and `shortlist/` in the chosen run. Each category has separate known-score and interval-review lists. `decisions.jsonl` explains failures and budget deferrals. Structures-only is explicitly terrain-unqualified; its successes do not count as island or basin successes. Website-supported candidates remain distinct from native predictions and game observations.

If `stronghold-deferred-seeds.txt` is nonempty, review those seeds in a **new** run using `config/review-all.yaml`. For a bounded staged run the saved seed count is at most 256:

```sh
.venv/bin/python -m seed_search --config config/review-all.yaml rank --seeds runs/staged-sweep-256/stronghold-deferred-seeds.txt --workers 12 --output runs/staged-recovery
```

Do not resume a fast-mode checkpoint with the recovery configuration. A recovery file above 1000 seeds needs its own measured readiness record or explicitly bounded input batches. A matching-version required-marker and terrain review still precedes choosing a world for deployment.

Measurements, mode decision and ETA assumptions are in [IMPLEMENTATION_RESULTS.md](IMPLEMENTATION_RESULTS.md). These estimates exclude manual website/game review. Keep frozen configurations unchanged; changes invalidate the large-run readiness identity.
