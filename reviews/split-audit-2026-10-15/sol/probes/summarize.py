"""Assemble reports from retained raw data; no benchmarks or production edits."""
import difflib
import hashlib
import json
import statistics as st
import subprocess
from pathlib import Path
from experiment import ROOT, OUT, WORK, write_json

def read(name):return json.loads((OUT/(name+'.json')).read_text())
def rate_summary(rows,key='arm'):
    result={}
    for value in dict.fromkeys(r[key] for r in rows):
        selected=[r for r in rows if r[key]==value];rates=[r['kernel_rate'] for r in selected]
        result[str(value)]=dict(trials=rates,median=st.median(rates),minimum=min(rates),maximum=max(rates),
                                cv=st.pstdev(rates)/st.mean(rates))
    return result
def paired(rows,baseline,candidate):
    indexed={(r['arm'],r['trial']):r for r in rows}
    trials=sorted(r['trial'] for r in rows if r['arm']==baseline)
    ratios=[indexed[candidate,i]['kernel_rate']/indexed[baseline,i]['kernel_rate'] for i in trials]
    return dict(ratios=ratios,median_ratio=st.median(ratios),minimum=min(ratios),maximum=max(ratios))
def trials_table(rows):
    arms=list(dict.fromkeys(r['arm'] for r in rows));d={(r['arm'],r['trial']):r for r in rows}
    text='| Trial | '+' | '.join(arms)+' |\n| --- |'+' ---: |'*len(arms)+'\n'
    for trial in sorted({r['trial'] for r in rows}):
        text+='| '+str(trial+1)+' | '+' | '.join(f"{d[a,trial]['kernel_rate']:,.0f}" for a in arms)+' |\n'
    text+='| Median | '+' | '.join(f"{st.median(r['kernel_rate'] for r in rows if r['arm']==a):,.0f}" for a in arms)+' |\n'
    return text

main=read('confirm-main');gate=read('confirm-dark-gate');schedule=read('scheduling')
for rows in (main,gate):
    assert len({r['trial'] for r in rows})==5
    assert min(r['native_seconds'] for r in rows)>=5
    for trial in range(5):
        selected=[r for r in rows if r['trial']==trial]
        assert len({r['receipt_fingerprint'] for r in selected})==1
        assert len({r['survivor_content_fingerprint'] for r in selected})==1
assert read('optional-component-parity')['status']=='passed'
effects={a:paired(main,'control',a) for a in ('lazy','no-surface-init','lazy-no-surface-init')}
effects['gate_over_combined']=paired(gate,'lazy-no-surface-init','dark-gate')
effects['lazy_over_no_surface']=paired(main,'no-surface-init','lazy-no-surface-init')

production=read('manifest')['production_build'];identity_checks=[]
for path in sorted((OUT/'builds').glob('*-optimized.json')):
    if path.name.startswith('diagnostic'):continue
    identity=json.loads(path.read_text());arm=path.name.rsplit('-',2)[0]
    source=WORK/arm
    mismatches=[n for n,h in identity['inputs'].items()
                if hashlib.sha256((source/n).read_bytes()).hexdigest()!=h]
    binary=hashlib.sha256(Path(identity['extension']).read_bytes()).hexdigest()
    profile=Path(identity['extension']).parents[1]/'trained.profdata'
    meta=json.loads(profile.with_suffix('.json').read_text())
    good=not mismatches and binary==identity['extension_sha256'] and meta['inputs']==identity['inputs']
    good=good and hashlib.sha256(profile.read_bytes()).hexdigest()==identity['pgo_profile_sha256']
    assert good,(path,mismatches)
    identity_checks.append(dict(build=path.name,source_inputs_match=True,binary_sha256_match=True,
                                pgo_sha256_and_source_match=True,extension_sha256=binary))
for name,digest in production['inputs'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
assert hashlib.sha256(Path(production['extension']).read_bytes()).hexdigest()==production['extension_sha256']
assert hashlib.sha256(Path(production['runtime']).read_bytes()).hexdigest()==production['runtime_sha256']
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==read('manifest')['commit']

survivor=read('survivor');survivor_summary={}
for category in ('synthetic_trials','natural_late_stage_trials'):
    rows=survivor[category]
    survivor_summary[category]={k:st.median(r[k]/r['count'] for r in rows)
        for k in ('native_seconds_instrumented','reconstruction_seconds','serialization_seconds','serialized_bytes')}
forced=survivor['forced_natural_components']
survivor_summary['forced_median_seconds']={k:st.median(r['seconds'][k] for r in forced) for k in forced[0]['seconds']}

schedule_summary={}
for stage in ('threads','chunks','batches','confirmation'):
    selected=[r for r in schedule if r['stage']==stage]
    configs=list(dict.fromkeys((r['threads'],r['chunk'],r['batch']) for r in selected));summary=[]
    for config in configs:
        rows=[r for r in selected if (r['threads'],r['chunk'],r['batch'])==config]
        summary.append(dict(threads=config[0],chunk=config[1],batch=config[2],
            trial_rates=[r['kernel_rate'] for r in rows],median=st.median(r['kernel_rate'] for r in rows),
            median_batch_seconds=st.median(t for r in rows for t in r['batch_seconds']),
            median_cpu_percent=st.median(r['process_cpu_percent'] for r in rows)))
    schedule_summary[stage]=summary
longsched=[r for r in schedule if r['stage']=='confirmation']
assert len(longsched)==10 and min(r['native_seconds'] for r in longsched)>=5
by={(r['trial'],r['batch']):r for r in longsched}
sched_ratios=[by[i,16384]['kernel_rate']/by[i,8192]['kernel_rate'] for i in range(5)]

measurement=dict(status='complete; isolated audit only',main=rate_summary(main),paired_effects=effects,
    gate=rate_summary(gate),scheduling=schedule_summary,scheduling_16384_over_8192_ratios=sched_ratios,
    survivor=survivor_summary,allocation_boundary=read('allocation-boundary'),
    build_identity_checks=identity_checks,
    raw_files=['confirm-main.json','confirm-dark-gate.json','screen-main.json','screen-dark-gate.json',
               'scheduling.json','profile-50000000-100000-34.json','profile-optimized.json','profile-gate.json',
               'survivor.json','allocation-boundary.json','codex-performance-recheck.json','codex-gate-recheck.json',
               'optional-component-parity.json'],
    limitations=['Kernel, attribution, reconstruction, and serialization are separate measurements',
                 'No usable hardware PMU counters; no exclusive desktop/affinity control',
                 'Gate/control main medians are from different cohorts; do not divide them as a paired estimate',
                 'No natural retained survivor in bounded attribution cohort',
                 'Diagnostic baseline binary was rebuilt for S4; its recorded identity/raw measurements remain, not the original executable'])
write_json(OUT/'measurements.json',measurement)

perf=("**MEASURED: five alternating confirmation trials, rates in native inputs/sec.** "
      "Each arm processes1.2M inputs per trial (6M distinct inputs, indices52M–58M); "
      "all trial arms exceed five seconds. Seeds, record walking and receipt hashing are outside the native timer.\n\n"+
      trials_table(main)+'\n')
for name in ('lazy','no-surface-init','lazy-no-surface-init'):
    x=effects[name];perf+=f"- `{name}` versus matched control: median paired **+{100*(x['median_ratio']-1):.2f}%**, ratio range{x['minimum']:.3f}–{x['maximum']:.3f}.\n"
perf+=(f"- Lazy seeding added after removing surface initialization: **+{100*(effects['lazy_over_no_surface']['median_ratio']-1):.2f}%** median paired. Effects are not additive.\n\n"
       "**MEASURED: the raw witness gate versus the already optimized control**, five alternating trials of1.5M inputs "
       "each (7.5M distinct inputs, indices100M–107.5M), all arms over five seconds:\n\n"+trials_table(gate)+
       f"\nMedian paired gate improvement: **+{100*(effects['gate_over_combined']['median_ratio']-1):.2f}%**, "
       f"range{effects['gate_over_combined']['minimum']:.3f}–{effects['gate_over_combined']['maximum']:.3f}. "
       "Main control and gate medians are different cohorts; their quotient is not a directly paired total improvement. "
       "The corresponding full before/after receipts match on every trial. No natural retained survivor appears in these ordinary benchmark cohorts.\n\n"
       "Codex additionally reran two alternating300k-input trials for the four main arms and two for the gate comparison "
       "on new index ranges. Both confirm the direction/large magnitude and identical receipts; short trials vary more and "
       "are not substituted for the long confirmation estimates. The machine had normal light desktop load, no competing audit "
       "build/test/scan during timings, and no affinity/thermal control. All per-trial rates and build hashes are retained.\n")
text=(OUT/'REPORT.md').read_text().replace('<!-- PERFORMANCE_RESULTS -->',perf)

sched='| Screen | Threads/chunk/batch | Median inputs/sec |\n| --- | --- | ---: |\n'
for stage in ('threads','chunks','batches'):
    for row in schedule_summary[stage]:
        sched+=f"| {stage} | {row['threads']}/{row['chunk']}/{row['batch']} | {row['median']:,.0f} |\n"
sched+=(f"\n**MEASURED operating point: retain34 threads, chunk16, batch16,384 on this host.** "
        f"Five long paired trials give batch16,384 a **+{100*(st.median(sched_ratios)-1):.2f}%** median paired gain over8,192 "
        "on the initialization-optimized arm. Chunk64's small screen difference is within screen variability; chunk128 is "
        "clearly weaker in this sample. No justification to change chunk16. The long batch confirmation includes median "
        f"native batch latencies of{schedule_summary['confirmation'][0]['median_batch_seconds']*1000:.1f} ms "
        f"(batch16,384) and{schedule_summary['confirmation'][1]['median_batch_seconds']*1000:.1f} ms (batch8,192); "
        "partial tail batches are present in raw data. CPU utilization includes wrapper/hash work, uses process CPU/wall "
        "outside kernel timing, and is recorded per row. Scheduling was measured on the initialization-optimized arm; "
        "the gate is confirmed at the retained operating point, not subjected to an additional full scheduling sweep.\n")
text=text.replace('<!-- SCHEDULING_RESULTS -->',sched)

s='| Isolated component | Median per input | Input provenance |\n| --- | ---: | --- |\n'
for name,seconds in survivor_summary['forced_median_seconds'].items():
    s+=f"| {name} | {seconds*1000:.3f} ms | 11 forced natural component inputs |\n"
syn=survivor_summary['synthetic_trials']
for name in ('native_seconds_instrumented','reconstruction_seconds','serialization_seconds'):
    s+=f"| {name} | {syn[name]*1000:.3f} ms | 32 passing fixtures, five trials |\n"
s+=(f"\nSynthetic JSON output averages{syn['serialized_bytes']:,.0f} bytes per retained input. "
    "Fixture per-input medians: event construction7.344µs, OW prefix740.469µs, Nether prefix1.594µs, "
    "argmin0.281µs, final evidence98.563µs; the encompassing cell stage873.250µs includes prefixes/optional work. "
    "The residual cell scanning/snapping/scoring work is about124µs by subtraction; nested timings are not independent. "
    "These fixtures bypass real viability and optional inventories, explaining why forced natural prefix/inventory costs "
    "are much larger. All11 late-stage natural inputs reject before optional/prefix work; no eligible natural prefix "
    "entry frequency can be extrapolated from the forced calls.\n\n"
    "Allocation traffic on one worker for1/2/32 passing fixtures is72/132/1,932 allocation calls; "
    "requested-live peaks are1,872,336/1,921,244/3,388,484 bytes. All tracked memory is released after `nb_free`. "
    "This confirms scratch reuse while retained output grows with fixture count.\n\n"
    f"Seed-array marshaling (16,384 precomputed seeds,20 trials) takes{read('allocation-boundary')['boundary']['array_creation_median_seconds']*1000:.3f} ms median; "
    f"hashing its fixed-width verdict buffer takes{read('allocation-boundary')['boundary']['verdict_hash_median_seconds']*1000:.3f} ms. "
    "No native generator work is included in these two timings. This measures marshaling/hash work, not isolated CFFI dispatch latency.\n")
text=text.replace('<!-- SURVIVOR_RESULTS -->',s)

original=read('profile-50000000-100000-34');optimized=read('profile-optimized');gated=read('profile-gate')
def attribution(profile):
    total=sum(w['eval_seconds'] for w in profile['workers'].values())
    return total,{k:100*v['seconds']/total for k,v in profile['counters'].items()}
_,o=attribution(optimized);_,g=attribution(gated)
remaining=(f"\n**MEASURED remaining attribution:** after both initialization changes, Mansion inventory remains{o['mansion_inventory']:.2f}% "
           f"of instrumented summed evaluation (height{o['mansion_approx_height']:.2f}%, radius{o['mansion_radius']:.2f}% nested). "
           f"After the witness gate, Mansion inventory runs on3,941 inputs /26,592 starts; the gate consumes{g['raw_dark_gate']:.2f}%, "
           f"remaining Mansion inventory{g['mansion_inventory']:.2f}%, and raw-preflight-plus-final-Nether{g['stage_raw_preflight_plus_final_nether']:.2f}%. "
           "The biome-point hook overlaps gate/witness time and must not be added again. This profile no longer has a single "
           "75% redundant initializer. The optimized non-gated capture retains an empty slot12 timing hook; it is not initialization work. "
           "The gate capture removes that empty hook and explicitly relabels slot12. These are non-PGO diagnostic fractions, not throughput comparisons.\n")
text=text.replace('## S3: Staged scheduling',remaining+'\n## S3: Staged scheduling')
optional=read('optional-component-parity')
text=text.replace('The fixed half-open envelopes,',
    f"Additional natural optional-component parity passes on{optional['count']} inputs, including134 known viable-Mansion seeds, "
    f"followed in the same context by all five optional inventories and igloo-basement decisions. Nonempty viable totals are "
    f"{optional['viable_optional_totals']}; basement positives{optional['igloo_basements']}. This checks relevant RNG interleavings "
    "and nonempty optional generation, not full natural survivor eligibility.\n\nThe fixed half-open envelopes,")
text=text.replace('**Status: final measurements in progress.**','**Status: complete; handoff reviewed by Codex.**')
(OUT/'REPORT.md').write_text(text)

codex=OUT.parent/'codex/FINAL_REVIEW.md';review=codex.read_text()
review=review.replace('**Review status: measurements and final verification in progress.** The completed version of this document will replace this line.',
    '**Review status: complete.** Raw artifacts, all21 Gemini claim dispositions, performance methodology, critical reproductions, and proposed-patch applicability were reviewed. Scope exclusions remain explicit.')
table=("Uninstrumented matched-PGO results (native kernel only):\n\n"
       "| Experiment | Control median | Candidate median | Median paired improvement |\n| --- | ---: | ---: | ---: |\n"
       f"| Remove unused surface initialization | {measurement['main']['control']['median']:,.0f}/sec | {measurement['main']['no-surface-init']['median']:,.0f}/sec | +{100*(effects['no-surface-init']['median_ratio']-1):.2f}% |\n"
       f"| Combine with delayed seeding | {measurement['main']['control']['median']:,.0f}/sec | {measurement['main']['lazy-no-surface-init']['median']:,.0f}/sec | +{100*(effects['lazy-no-surface-init']['median_ratio']-1):.2f}% |\n"
       f"| Add necessary raw Dark Forest gate | {measurement['gate']['lazy-no-surface-init']['median']:,.0f}/sec | {measurement['gate']['dark-gate']['median']:,.0f}/sec | +{100*(effects['gate_over_combined']['median_ratio']-1):.2f}% |\n\n"
       "Each comparison has five alternating paired trials with at least five seconds per arm; raw individual trials are in "
       "[Sol's report](../sol/REPORT.md) and [measurements](../sol/measurements.json). Gate confirmation uses a different cohort "
       "from the four-arm main comparison; do not divide those medians as though they were a directly paired total gain. "
       "Codex's additional alternating checks confirm the direction and receipt parity. The quoted production47.8k/sec "
       "is historical; this machine's fresh control is46.2k/sec. No checkpointed/end-to-end speed claim follows.\n\n"
       "Retain34 threads / chunk16 / batch16,384 on this host. Chunk64 is not a demonstrated improvement; chunk128 and "
       "smaller batches screen worse. Five long batch trials support16,384 over8,192. No operating-setting change was made.\n\n"
       "Post-gate attribution is spread across the raw witness gate23.88%, remaining Mansion inventory22.32%, and "
       "raw preflight plus Nether24.19% (overlapping biome subqueries must not be double-counted). Natural forced "
       "OW prefix work costs88.593ms median per forced input, but none of the100k profile inputs reaches that palette, "
       "so it is not an observed aggregate bottleneck. Passing fixtures take30.518ms to reconstruct and3.094ms to serialize "
       "per retained input; their natural aggregate impact is unknown. Seed-array marshaling and verdict hashing take1.711ms "
       "and0.547ms per16,384 precomputed inputs, outside native timing.\n")
review=review.replace('<!-- FINAL_MEASUREMENTS -->',table)
start=review.index('Only two changes are proposed for adoption review:')
end=review.index('The [combined diff]',start)
review=review[:start]+'''Only two **new** proposals are retained for adoption review:

1. [Remove unused modern Mansion SurfaceNoise initialization](../sol/proposals/no-surface-init.patch). `finders.c` builds a `SurfaceNoise` object, while the active Overworld `mapApproxHeight` branch in `generator.c:623` returns without reading it. Each initialization consumes **18,160 MT draws** plus reseeding. Remove it only in this modern branch and pass `NULL`; preserve all noise arithmetic and older paths. The previously proposed [delayed generator seeding](../sol/proposals/lazy.patch) is independently reconfirmed (+9.36% against unchanged control) and complements this change; the combined arm measures their interaction.
2. [Add the necessary raw Dark Forest witness gate](../sol/proposals/dark-gate-incremental.patch), applied after the combined initialization patch. A viable qualifying Mansion is a raw start with the exact required Y=63 witness. If too few raw starts have it, the viable subset cannot meet the goal. Positive gates retain the original complete inventory, including non-Dark-Forest viable starts. This small loop adds no index, relaxed bounds, or mathematical shortcut. Its +18.51% median paired gain is measured against the already optimized control.

''' + review[end:]
review=review.replace('The [combined diff](../sol/proposals/lazy-no-surface-init.patch) contains both.',
    'The [combined initialization diff](../sol/proposals/lazy-no-surface-init.patch) contains the first change plus the prior delayed-seeding proposal.')
review=review.replace('before adoption. No mathematical tolerance,',
    f"before adoption. Additional nonempty optional-component/interleaving parity passes on{optional['count']} natural inputs, "
    f"including{optional['igloo_basements']} positive igloo basements. No mathematical tolerance,")
review=review.replace('was altered in these two experiments.','was altered in these experiments.')
codex.write_text(review)

# Minimal incremental gate diff, explicitly based on the already combined arm.
name='native/blueprint_dynamic.inc'
a=(WORK/'lazy-no-surface-init'/name).read_text();b=(WORK/'dark-gate'/name).read_text()
(OUT/'proposals/dark-gate-incremental.patch').write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))

manifest=read('manifest');manifest['status']='complete; isolated audit and final Codex review; no production changes'
manifest['proposed_workloads']['confirm']['count']=1200000
manifest['actual_workloads']={
 'training':dict(key=2026101402,start=0,count=10000,threads=4),
 'profile':dict(key=2026101401,start=50000000,count=100000,repeated_for=['baseline','initialization-optimized','gated']),
 'screen_main':dict(start=51000000,count=100000,trials=3),
 'confirm_main':dict(start=52000000,count=1200000,trials=5),
 'record_parity':dict(start=60000000,count=256,retention=['full','survivors']),
 'component_parity':dict(start=61000000,count=2000),
 'sampling':dict(start=70000000,count=16384,repetitions=5,threads=1),
 'screen_gate':dict(start=75000000,count=200000,trials=3),
 'scheduling_screen':dict(start=80000000,count=200000,trials=3,reuse='fixed cohort across all configurations/trials'),
 'scheduling_confirm':dict(start=82000000,count=1500000,trials=5,reuse='fixed cohort across all configurations/trials'),
 'codex_main_recheck':dict(start=90000000,count=300000,trials=2),
 'confirm_gate':dict(start=100000000,count=1500000,trials=5),
 'boundary_marshaling':dict(start=110000000,count=16384,trials=20,native=False),
 'codex_gate_recheck':dict(start=120000000,count=300000,trials=2),
 'optional_components':dict(start=130000000,count=128,plus='134 archived viable-Mansion inputs'),
 'defaults':dict(key=2026101401,retention='survivors',max_misses=2,threads=34,chunk=16,batch=16384),
 'fixtures':dict(seed_labels='0..39 and repeated123',provider='NBFixture; explicitly synthetic; not actual world discoveries'),
 'forced_natural_components':dict(inputs='11 archived profile inputs',scope='component costs only, not eligibility'),
}
manifest['natural_late_stage_inputs']='profile report contains11 cell-stage inputs; no retained natural survivor'
manifest['final_identity_checks']=identity_checks
manifest['host_load_observations']=['Only one CPU-intensive experiment at a time',
 'Main confirmation ps snapshot: benchmark3348.9% CPU; VS Code20.4%, Chrome13.1%, WindowServer9.5%',
 'Normal desktop processes remained; no affinity pinning or thermal isolation',
 'No usable hardware PMU event values in exported CPU Counters trace']
manifest['diagnostic_limitations']=measurement['limitations'][-1:]
manifest['diagnostic_extra_headers']={str(p.relative_to(WORK)):hashlib.sha256(p.read_bytes()).hexdigest()
 for d in ['diagnostic','diagnostic-optimized','diagnostic-gate'] for p in (WORK/d/'native').glob('sol_*.h')}
write_json(OUT/'manifest.json',manifest)
source_review=OUT/'SOURCE_REVIEW.md';s=source_review.read_text()
source_review.write_text('> Historical preparation notes from the paused window. Subsequent experiments are complete; '
                        'the authoritative handoff is [REPORT.md](REPORT.md). Statements below about pending work refer to that earlier window.\n\n'+s)
print('Reports and measurements assembled; production identity unchanged; optimized builds validated:',len(identity_checks))
