"""Same-build-flags comparison; run from repository root with .venv/bin/python."""
import json
import statistics
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.benchmark_dynamic_baseline import kernel_measure
from seed_search.realm.config import dynamic_v2_blueprint_config, dynamic_blueprint_config
from seed_search.realm.native_batch import Prototype, seeds_np, semantic_record

OUT=Path(__file__).resolve().parent
BUILD=ROOT/'runs/kernel-preflight-2026-10-15'
names=['baseline','reuse']
prototypes={n:Prototype(BUILD/n,dynamic_v2_blueprint_config()) for n in names}
rows=[]
seeds=seeds_np(0,300000,7015102026)
expected=None
for p in prototypes.values():
    with p.sweep(seeds[:4096],34,retention='survivors'):pass
for trial in range(3):
    order=names[trial%2:]+names[:trial%2]
    for name in order:
        row=kernel_measure(name,prototypes[name],34,16384,seeds)
        row.update(trial=trial,cohort='tuning')
        if expected is None:expected=row['fingerprint']
        assert row['fingerprint']==expected,(name,'decision mismatch')
        rows.append(row)
        print(name,trial,round(row['kernel_inputs_per_second']),flush=True)
medians={name:statistics.median(r['kernel_inputs_per_second'] for r in rows if r['arm']==name) for name in names}
winner='reuse'
# Disjoint input indexes (not merely nearby run keys).
heldout=seeds_np(1000000,1600000,7015102026)
for trial in range(3):
    expected=None
    for name in (['baseline',winner] if trial%2==0 else [winner,'baseline']):
        row=kernel_measure(name,prototypes[name],34,16384,heldout)
        row.update(trial=trial,cohort='heldout')
        if expected is None:expected=row['fingerprint']
        assert row['fingerprint']==expected,(name,'heldout mismatch')
        rows.append(row)
        print('heldout',name,trial,round(row['kernel_inputs_per_second']),flush=True)
# Full evidence and synthetic positive late-stage parity for both policy revisions.
for factory in (dynamic_blueprint_config,dynamic_v2_blueprint_config):
    arms=[Prototype(BUILD/n,factory()) for n in ('baseline',winner)]
    for fixtures,inputs in [(None,seeds[:256]), ([(0,0,-1),(1,-1,-1),(0,0,5)],[123,456,789])]:
        records=[]
        for arm in arms:
            with arm.sweep(inputs,1,fixtures=fixtures,retention='full') as batch:
                records.append([semantic_record(r) for r in batch.records()])
        assert records[0]==records[1],('full parity',factory.__name__,fixtures)
summary={'tuning_medians':medians,'winner':winner,'rows':rows,
         'heldout_medians':{n:statistics.median(r['kernel_inputs_per_second'] for r in rows if r['arm']==n and r['cohort']=='heldout') for n in ('baseline',winner)},
         'parity':'all decision fingerprints, full records (256 real inputs per revision), and positive synthetic fixtures match',
         'flags':prototypes[winner].identity['flags'],'scope':'private native kernel builds; CPU-native + LTO, no PGO; 34 threads, batch 16384; not durable pipeline throughput'}
(OUT/'reuse-results.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='rows'},indent=2))
