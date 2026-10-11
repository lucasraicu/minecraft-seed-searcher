# Historical 2304/928 sweep readiness

> This record is historical and does not authorize the current 2688/1024 Realm pipeline or its rebuilt native binary. Use [MASTER_SWEEP_READINESS.md](MASTER_SWEEP_READINESS.md) and [MASTER_IMPLEMENTATION_RESULTS.md](MASTER_IMPLEMENTATION_RESULTS.md) for the current contract and open accuracy gates. No production sweep has started.

The approved implementation and bounded verification are complete. The production sweep is unstarted. Current configuration: `config/reference-sweep.yaml`; evidence: `runs/implementation-2026-10-08/readiness.json`. A launch must pass that record's live identity, artifact and budget checks. Prior records are historical and incompatible.

**Recommend full64 reference, 2000 seeds at 12 workers: reserve 3–5 hours.** The bounded staged alternative is implemented: 10000 low32 layouts, 48 top + 16 exploration layouts, four high32 siblings each, 256 full seeds; reserve 35–50 minutes. Detailed commands: [SWEEP_COMMANDS.md](SWEEP_COMMANDS.md).

## Completed evidence

- Supported native rebuild, pinned vendor hashes, installed license and locked dependency checks.
- 141 unit/native tests pass; 880 structure / 159 coordinate external comparisons match the explicit baseline, including six documented disagreements.
- Three alternating-order 20-seed cache trials preserve all deterministic predictions, with 26.4% median wall / 25.0% CPU savings.
- Two independent keys × two 256-input mode arms. Reference has greater predicted category yield per CPU-hour in every category for both keys; no verified terrain-yield or recall promotion claim for staged mode.
- Raw checkpoint interruption and exact full-seed resume/worker comparisons at 1/8/12 requested workers.
- Four matched fast/recovery seeds; four additional unresolved centers, no additional native-eligible centers in that cohort.
- Interrupted/resumed 20-seed map pilot exactly matches its independent repeat, with 132 centers and per-category outputs. Representative maps for all four categories were inspected.
- Fresh matching-version required markers for two structures-only controls, including high-bit and negative-center cases, at the new borders. Optional score uncertainty stays in interval lists.
- Actual finite CLI smoke and resume dry run. Missing/historical evidence rejects the large command; the final gate also checks altered evidence and excess budgets. Neither production output directory has been created.

## Contract and limits

All four categories require Stronghold and Fortress within squares sharing one selected center. Other structures are preferences. Structures-only explicitly skips terrain qualification. The other categories retain their branch checks and independent terrain review. Biome inventory is sampled surface/Nether evidence; cave coverage is unmeasured by default. Stronghold root correction, substantial SIMD and a hard island pre-filter remain deferred. A real reviewed basin-positive and generated-game suitability/footprint observations remain unestablished.

The current record seals configuration, predictor/native/runtime identity, sources/tests, measured evidence, browser provenance and command budgets. Editing a sealed file invalidates a large launch until readiness is regenerated from current verification.

Results, timing assumptions and decision details: [IMPLEMENTATION_RESULTS.md](IMPLEMENTATION_RESULTS.md). Workflow: [SEED_SELECTION_WORKFLOW.md](SEED_SELECTION_WORKFLOW.md). The superseded report is preserved in [HISTORICAL_SWEEP_READINESS.md](runs/implementation-2026-10-08/HISTORICAL_SWEEP_READINESS.md).
