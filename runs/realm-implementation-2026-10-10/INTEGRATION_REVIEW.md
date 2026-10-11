# Independent Realm integration review

Reviewed 2026-10-10; read-only source inspection plus two small synthetic Python checks. No native scan, terrain generation, BDS startup, or benchmark was launched. Findings describe the source at inspection time; other implementation agents may fix them afterward.

## Findings

1. **High: V2 can assert complete formation fit after clipping enclosing ridges.** `terrain.py` builds ridge components only inside the configured distance annulus, then uses those clipped labels as the entire formation and checks completeness only through `distance_max`. A known synthetic annulus from radius 500 through 1100, with the default ridge distance maximum 850 and a Realm of `[-900,-900,900,900)`, returned `geometry_pass=True`, `border_fit=within`, `complete=True`, and footprint `[-848,-848,856,856]`. The same enclosing ridge extends outside that border. Distinguish the ridge encounter/search distance from the measured local supporting-ridge extent; resolve the outer edge or mark the footprint unknown/lower-bound. The contract permits excluding unrelated ranges but requires the complete relevant enclosing ridge footprint.

2. **High: repeated bounded terrain commands cannot advance the pool.** `run_terrain` charges `summary['candidates']` for already-completed pairs. A two-pair stub with pair 0 complete, pair 1 pending, and `limit=1` returns zero results and never opens the provider for pair 1. After an initial `terrain --limit N`, repeating that same command repeatedly inspects only the first N completed candidates. Count active work against the limit and keep a separate inspected/skipped count.

3. **Medium: configurable geometry thresholds do not control terrain halos/radii.** `run_terrain` calculates nomination halo and local sampling radius from module `V1`/`V2` constants, although validated configuration permits changing all thresholds. Increasing V2 `distance_max` beyond 850 therefore cannot receive sufficient local coverage and leaves otherwise valid formations pending. Calculate sizes from merged configured thresholds and allow measured footprint expansion. Include altered-threshold fixtures.

4. **Medium: variant ranking mixes evidence and qualification states.** Baseline ranking explicitly groups verified/predicted/pending; variant SQL orders only the generic numeric score. Pending observations, predicted near matches, failed geometry and actual verified matches therefore compete directly without separated rank groups. The plan requires rankings to distinguish actual verified, supported predictions, and pending evidence. Preserve all raw results while producing clearly grouped or separate views.

5. **Low: new optional-structure defaults differ from the agreed defaults.** `config.py` currently assigns Shipwreck and Ruined Portal 1 each. The plan specifies 2 each. This is configurable but the initial profile should use the agreed defaults or explicitly document a later authorized change.

## Cross-module observations

- Baseline scans preserve half-open discovery/evaluation membership, keep independent anchors, and do not promote unsupported or approximate negatives to confirmed absence.
- Nether integer membership conversion and comparison preserve the fractional negative Stronghold/8 center semantics.
- Parent-owned range commits include all anchors and both variant tasks atomically; retry digests and immutable anchor identities are present.
- BDS imports and rasters keep natural-ground provenance unresolved, so real runtime observations cannot automatically certify geometry or full Realm eligibility.
- Cave-variety calls are absent from automatic legacy/new pipelines; explicit cave observations stay separate.
- The review did not repeat root's planned rescore/score-policy integration work and made no exact-world correctness claim.
