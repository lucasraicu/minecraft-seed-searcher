"""Describe the optimized finite workload from newly measured evidence."""
import json
from pathlib import Path

if __name__=='__main__':
    p=Path('runs/filter-optimization')
    read=lambda n:json.loads((p/n).read_text())
    m=read('pilot-measurements.json');ab=read('shortcuts-ab.json');cmd=read('command-validation.json')
    worker=read('worker-ab.json');best=worker['recommended_workers']
    projected=worker['measurements'][str(best)]['analysis_wall_seconds']/20*2000/3600+m['report_wall_seconds']/3600
    parity=read('optimization-parity.json');summary=json.loads((p/'pilot-20/summary.json').read_text())
    tests=read('verification.json')['tests']['passed_count']
    stage='\n'.join(f'| {k} | {v:.2f} | {m["stage_percentages"][k]:.2f}% |' for k,v in m['stage_seconds_summed'].items())
    (Path('SWEEP_READINESS.md')).write_text(f'''# Optimized Bedrock search: finite sweep readiness

The large sweep remains unstarted. The current verified package is
`runs/filter-optimization/readiness.json`; it supersedes prior readiness identities.
Prior sources and readiness are retained in `runs/filter-optimization/prior-sources.zip`
and `prior-readiness.json`. Details: [FILTER_OPTIMIZATION.md](FILTER_OPTIMIZATION.md).

Bedrock26.52 maps to pinned MC_26_50. Full signed64-bit worlds, three landscape
types, exact3008/992 squares, required Fortress and Stronghold, optional Bastion,
flatness, ocean isolation and mountain criteria are unchanged. This is a finite
heuristic search with explicit deferred cases, not an exhaustive stronghold census.

## Implemented shortcuts

Stronghold and Fortress placement run before discovery terrain. A joint
eight-block center-window intersection filters nominal locations before
preliminary/coast/full-raster work; fixed island centers are checked again before
full landscape sampling. Unknown predictions are exported in
`stronghold-deferred.json` and `stronghold-deferred-seeds.txt`. They are **deferred**,
not proven absent. The default `defer_unpredicted` mode can miss worthy seeds because
the Stronghold iterator is incomplete and nomination envelopes are heuristic.
`config/review-all.yaml` disables that fast exclusion for a separate recovery run.
Accepted candidates still need matching-version website marker confirmation.

One native placement enumeration followed by full-seed viability replaces duplicate
raw/viable scans. A bounded128-entry per-process cache shares ONLY raw lower32-bit
MT layouts for eight tested families. Stronghold village iteration, Mineshaft,
Trial Chamber, biome, density and viability never share those raw keys. The seed
sequence still covers full64-bit numeric values. Random lower32 collisions are rare;
this cache is most useful for explicit high-bit sibling workloads, and no generic
speed improvement from it is claimed.

Necessary dry/gentle upper bounds inspect a small basin patch including all eight
allowed nearby floor proposals and gradient/kernel halo. Lazy mountain rays stop
after enough proven misses make75% impossible; unseen rays remain possible, with
a5000-point overhead budget. Survivors retain full-raster global connectivity and
the original criteria. Shared immutable raster calculations avoid repeated labels,
gradients and local ranges. Exact per-seed/stride cache and persisted maps remain.

Controlled four-negative-basin A/B: {ab['reference_basin_seconds']:.2f}s →
{ab['bound_basin_seconds']:.2f}s, {ab['computed_columns_reference']} →
{ab['computed_columns_bound']} native density columns. All four early failures also
fail the original full-raster/recenter criteria. Synthetic positive and nearby-floor
controls pass. Combined structure scan saves
{100*(1-sum(ab['native_structure_scan_seconds']['combined'])/sum(ab['native_structure_scan_seconds']['duplicate'])):.2f}%
in the isolated four-seed test, with identical typed predictions.

## Verification and scope

{tests} tests pass. Supported editable native rebuild and dependency checks pass;
vendor source/license hashes are preserved. Frozen880 structure/159 coordinate
comparison remains874 unique typed correspondences, six visible disagreements,
zero reused starts; original height MAE1/max5. Independent20-seed checkpoint/resume
and worker-count comparison matches exact predictions, metrics, cache counts,
rejections and deterministic counters, excluding only timings/RSS/PIDs.

Common old/new centers have exact unchanged metrics and scores:
{parity['common_centers']} compared, {parity['unchanged_common_centers']} identical.
Fast exclusions and newly reached finite-budget nominees change candidate coverage;
this is not an unchanged-workload overall A/B speed claim. Fresh matching-version
UI checks re-confirm both required markers for two retained ocean-island controls,
including high-bit/negative-coordinate seed4294979641. Prior landscape/control
observations are preserved with their original scope/date and new checks identified
separately. No actual Minecraft generation evidence was invented. No real dry-basin
positive is established by this chosen sample.

## Measured workload

Twenty fixed input seeds, {m['scored_centers']} scored locations;
{m['wall_seconds']:.2f}s total including two exports, {m['analysis_wall_seconds']:.2f}s
analysis, {m['report_wall_seconds']:.2f}s reports, {m['effective_seconds_per_seed']:.2f}s
effective per input. Individual worker mean{m['worker_seed_seconds_mean']:.2f}s,
range{m['worker_seed_seconds_percentiles'][0]:.2f}–{m['worker_seed_seconds_percentiles'][-1]:.2f}s.
These are input costs, not time to find worthy seeds. Uninterrupted identical20-seed
cohorts take{worker['measurements']['8']['analysis_wall_seconds']:.2f}s with8 workers
versus{worker['measurements']['12']['analysis_wall_seconds']:.2f}s with12; all exact
results match. Twelve saves{worker['analysis_saving_of_12_vs_8_percent']:.2f}% analysis
wall time in this one-trial comparison and is the current recommendation. Both use
reusable maps so report time is separate. No18-worker/global-optimality claim.
For2000 inputs, measured12-worker analysis plus amortized reports projects
**{projected:.2f}h**; applying the interrupted8-worker pilot's full overhead per
input gives a conservative{m['future_2000_naive_hours']:.2f}h. A1.5× planning allowance
is{projected*1.5:.2f}–{m['future_2000_naive_hours']*1.5:.2f}h, plus manual review.
Yield and throughput can vary; the chosen sample is small.

| Stage | Summed worker seconds | Share |
|---|---:|---:|
{stage}

Source/config/backend/evidence hashes gate the finite2000-input launch. The actual
command passes a positive dry run from `/tmp`, missing/stale/tampered readiness is
rejected, and no sweep directory has been created. Resume uses the original identity.

Start (unstarted):

```sh
{cmd['sweep_command']}
```

Resume after interruption:

```sh
{cmd['resume_command']}
```

Recovery uses the supplied review-all config and the saved deferred seed list in
a **new** bounded rank run; prediction/config changes cannot resume fast-mode
checkpoints. The CLI continues to require separately verified readiness for any
recovery workload over1000 inputs. Split review batches into at most1000 supplied
seeds rather than bypassing that gate.
''')
