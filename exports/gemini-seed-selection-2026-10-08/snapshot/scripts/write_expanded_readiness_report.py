"""Write the current expanded-search readiness report from measured artifacts."""
import json
from pathlib import Path
p=Path('runs/landscape-expansion')
def read(name):return json.loads((p/name).read_text())
if __name__=='__main__':
 m=read('pilot-measurements.json');cmd=read('command-validation.json');fresh=read('fresh-prediction-comparison.json');proof=read('resume-proof.json');summary=json.loads((p/'pilot-20-verified/summary.json').read_text());cache=read('cache-ab.json');reuse=read('report-reuse-proof.json')
 naive=m['effective_seconds_per_seed']*2000/3600;amortized=m['analysis_wall_seconds']/m['seed_count']*2000/3600+m['report_wall_seconds']/3600
 stages='\n'.join(f'| {k} | {v:.2f} | {m["stage_percentages"][k]:.2f}% |' for k,v in m['stage_seconds_summed'].items())
 passed=json.loads((p/'verification.json').read_text())['tests']['passed_count']
 tested='The exact finite launch command passed a positive dry run from /tmp without creating its output directory.' if cmd.get('sweep_dry_run_exit_code')==0 else 'All preparation evidence is verified; the exact large-command positive dry run is the final remaining command check.'
 text=f'''# Expanded Bedrock search: finite sweep readiness

Current requirements supersede the original enclosed-island/Bastion-required package. Bedrock **26.52** uses pinned **MC_26_50**, full signed64-bit seeds, exact **3008×3008** Overworld square and **992×992** Nether square at chosen land center/8. **Fortress and Stronghold are required; Bastion is optional** and supplies at most two total score points. Ocean islands and dry flat mountain basins are implemented alongside enclosed inner islands. The large sweep remains unstarted.

The original100-seed pilot and frozen comparison are retained under `runs/sweep-readiness`; prior readiness is deliberately superseded and archived in `runs/landscape-expansion/prior-readiness.json`. This package uses newly verified sources/configuration/pilot/reviews; the old pilot is not relabeled as the new algorithm. Full audit, user-guide/blueprint decisions and evidence details: [LANDSCAPE_EXPANSION.md](LANDSCAPE_EXPANSION.md).

## Implementation and verification

- Typed opaque CFFI context, one native import per worker, actual Bedrock region placement and viability; Java first-three-ring and48-bit shortcuts remain disabled. The blueprint's two structure symbols do not exist in the pinned library, and several biome IDs are wrong. Native bridge/build inputs/binary and provenance are unchanged from the supported successful editable native build. Dependency/license/version hashes are rechecked by readiness derivation; current doctor calls the binary successfully.
- Shared finite32-preliminary/8-refinement budget across three branches. Majority-ocean1400-square nomination plus refined density/coast separation; dry basin requires a connected192-block-diameter floor, at least85% dry/gentle ground, relief≤16, slope≤0.30, and75% connected mountain bearings within800 blocks, relative height≥50. Deep Dark contrast atY-32 is a ranking hint, not a terrain proof. No criteria were loosened to create a basin result.
- 64MiB bounded per-worker/seed exact cache preserves seed/coordinate/stride/scale semantics. Controlled alternating A/B unchanged predictions on two seeds/six centers:160.2392→150.8928s, **5.83%** analysis saving. Persisted identity/hash-checked report terrain and content-keyed PNGs avoid repeated queries/redraws. A full unchanged refresh reused all {reuse['map_count']} PNGs in {reuse['wall_seconds']:.2f}s with identical hashes, zero native height/biome queries and zero redraws, enforced by failing hooks. A renderer-level regression covers the corrected cache-key collision.
- **{passed} tests passed** including exact cache/eviction, negative/full seeds, corrected false Fortress, structure borders, unknown/raw review, one-block bridge geometry, dry flat versus moat/steep basin geometry, persisted cache integrity and real1-versus2-worker resume. Frozen regression remains874/880 unique typed structure correspondences, six explicit known disagreements, no reused starts;129/135 surface biome matches, raw height MAE1,max5 on its original sample.
- Independent ten-seed repeat exactly matches{proof['candidate_count']} candidates plus rejections/counts/cache statistics from the interrupted/resumed current-source run. Only timing/RSS/PIDs excluded. The comparison previously exposed tiny score differences from YAML versus sorted checkpoint weight ordering; canonical score accumulation fixes that generally, with a dedicated regression. Prior diagnostic runs are preserved rather than resealed.

## Fresh external selection evidence

Actual matching-version Chunkbase browser UI checked four candidates in both dimensions and three geometry controls with Terrain. Seven unique required markers match7/7 native type-specific conventions. Five chosen new terrain points match5/5 biome labels; height MAE**{fresh['height_mae']}**, maximum**{fresh['height_max_error']}**. The new nine-block mountain discrepancy remains visible; the historical maximumfive was not a global bound. Both tools are predictors, and these selected samples do not establish whole-world accuracy/recall.

| Seed / chosen center | Fresh website selection outcome |
|---|---|
|12853964 /(-416,112)|User's ocean mountain island near predicted spawn detected(D604). Required markers fit; sloped proposed core/small caldera floor make buildability a near miss. Actual southern shoreline appendage differs from density.|
|12853964 /(0,960)|Supported low forest ocean island with useful gentle ground, required Stronghold(-1292,1396) and Fortress(155,11). Tree clearing needed; not an open mountain-ring ideal.|
|4294979641 /(-2304,-4480)|Supported compact ocean forest island, Stronghold(-1116,-5324), Fortress(-469,-853), exact-square eligibility. Rolling ground/clearing; not the strict flat-basin branch.|
|3471015484745077182 /(4432,-2080)|Top known-score island/ocean/wood and required markers supported; uneven wooded build ground remains unresolved, so score alone does not promote it.|

Reviewed basin control12853964(1792,-960) supports rejection of uneven ground/pond/incomplete ring. Synthetic geometry independently distinguishes a dry basin from a mountain-enclosed inner island/water moat. **No mountain-basin candidate passed in this20-seed sample**. That branch's measured positive-candidate yield is unknown; the implementation and rejection path work, but no real positive basin quality is claimed. Finite nomination/refinement can miss suitable areas. Candidate promotion remains type-specific; no ocean result is presented as a successful dry basin.

`chunkbase_checked` and marker eligibility remain separate from `actual_minecraft`, which is null. Capped marker lists cannot prove absence; missing local Strongholds stay unresolved. Accessible structure footprints, exact trees, portal arrival, spawn and thin bridges need optional actual-game checks. Website spawn for12853964 is(0,0), with its own stated prediction limit.

## Measured current end-to-end pilot

Current full configured pilot: **{m['seed_count']} input seeds**, **{m['scored_centers']} scored locations**, **{m['wall_seconds']:.2f}s({m['wall_seconds']/60:.2f}min)** including checkpoint and final reports; analysis{m['analysis_wall_seconds']:.2f}s, exports{m['report_wall_seconds']:.2f}s. Throughput{m['effective_seconds_per_seed']:.2f}s/input seed; this is not time per worthy match. Worker average{m['worker_seed_seconds_mean']:.2f}s, median{m['worker_seed_seconds_percentiles'][2]:.2f}s, range{m['worker_seed_seconds_percentiles'][0]:.2f}–{m['worker_seed_seconds_percentiles'][-1]:.2f}s. Parallel throughput and individual latency differ.

First invocation requested8 workers but only5 jobs were available; resume actually used8 processes for15 seeds. Recommend the measured **8 processes**, one numerical-library thread each. Eighteen physical cores alone do not establish that18 workers are faster; no claim of optimality. Peak parent{m['peak_parent_rss_mb']:.1f}MiB and individual worker{m['peak_worker_rss_mb']:.1f}MiB are process peaks, not simultaneous aggregate measurements.

| Stage (summed worker time) | Seconds | Share |
|---|---:|---:|
{stages}

Original100-seed pilot:41.24min,24.74s/input seed inclreports,139.51s average individual worker latency; coast51.22% and landscape43.82%. The changed workload shares branch budgets and avoids duplicate terrain/report work, so comparing total throughput is not a controlled cache-only speedup. Controlled cache saving is the5.83% result above. Complete candidates, raw/viable/website states, metrics, bounds, maps, scores and deferred/rejected reasons remain in [current JSON](runs/landscape-expansion/pilot-20-verified/candidates.json), CSV, packets and parent-owned SQLite.

## Finite future workload and tested commands

Future budget **2000 seeds**, deterministic indices100..2099, identical±5000 candidate-center axes and finite native envelope/configuration. Estimated **{amortized:.1f}h** amortized measured analysis plus exports, or **{naive:.1f}h** applying full pilot cost per seed; a1.5× uncertainty allowance is{amortized*1.5:.1f}–{naive*1.5:.1f}h, excluding manual review. This small chosen20-seed sample is not a universal timing/yield estimate. The decoded results occupy{m['decoded_result_mb']:.2f}MiB; linear2000-seed scaling≈{m['decoded_result_mb']/20*2000/1024:.2f}GiB, with four-buffer allowance≈{m['decoded_result_mb']/20*2000*4/1024:.2f}GiB plus worker/report overhead on the64GiB host. Disk has ample measured space; cached rasters/maps are bounded by finite seeds and shortlist depth.

The tiny equivalent and actual current pilot resume parse successfully. Missing readiness rejects count2000 with exit2 and creates no run directory. A source/config/evidence-hashed readiness record must derive every check from its measured artifacts; toggling the large-search flag is insufficient. Multi-kind candidate keys retain separate evidence even at identical centers. {tested}

Start (unstarted):

```sh
{cmd['sweep_command']}
```

Resume after interruption:

```sh
{cmd['resume_command']}
```

Changing prediction code/config invalidates checkpoints; changing hashed verification artifacts invalidates readiness. Retain the frozen current configuration, runtime and evidence. No large sweep, server or game verifier has been started.
'''
 Path('SWEEP_READINESS.md').write_text(text)
