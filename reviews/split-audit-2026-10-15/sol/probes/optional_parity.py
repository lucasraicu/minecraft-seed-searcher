"""Check nonempty real optional inventories after Mansion RNG consumers."""
import ctypes as ct
import hashlib
import json
from experiment import ROOT, WORK, OUT, write_json
from parity import Component, fingerprint
from seed_search.realm.native_batch import Prototype
from seed_search.realm.config import dynamic_blueprint_config
from seed_search.backend import structure_type
from seed_search.seeds import seed_from_index

arms=('control','dark-gate')
prototypes={a:Prototype(WORK/a/'chunk-16/optimized',dynamic_blueprint_config()) for a in arms}
components={a:Component(p) for a,p in prototypes.items()}
types={n:structure_type(n) for n in ('mansion','stronghold','outpost','fortress','bastion')}
prior=json.loads((OUT/'parity-control-vs-lazy-vs-no-surface-init-vs-lazy-no-surface-init.json').read_text())
seeds=[int(r['seed']) for r in prior['positive_mansion_inputs']]
seeds.extend(seed_from_index(i,2026101401) for i in range(130000000,130000128))
names=('swamp_hut','igloo','trail_ruins','ocean_ruin','buried_treasure')
hashes={a:hashlib.sha256() for a in arms};totals={n:0 for n in names};basements=0
for a,c in components.items():
    c.lib.ss_igloo_basement.restype=ct.c_int
    c.lib.ss_igloo_basement.argtypes=[ct.c_void_p,ct.c_int,ct.c_int]
for seed in seeds:
    reference=None
    for arm,c in components.items():
        # Fresh context for the complete interleaving, not independent per-query contexts.
        ctx=c.lib.ss_create(seed&((1<<64)-1));result={}
        if not ctx:raise MemoryError('Context')
        try:
            for name in ('mansion',*names):
                points=(ct.c_int*32768)();flags=(ct.c_int*16384)()
                n=c.lib.ss_scan(ctx,structure_type(name),-2000,-2000,1999,1999,0,points,16384)
                if n<0:raise RuntimeError((name,n))
                code=c.lib.ss_filter_starts(ctx,structure_type(name),points,n,flags)
                if code:raise RuntimeError((name,code))
                viable=[(points[2*i],points[2*i+1]) for i in range(n) if flags[i]]
                row=dict(raw=[(points[2*i],points[2*i+1]) for i in range(n)],viable=viable)
                if name=='igloo':
                    row['basement']=[c.lib.ss_igloo_basement(ctx,x,z) for x,z in viable]
                    if any(v<0 for v in row['basement']):raise RuntimeError('Basement')
                result[name]=row
        finally:c.lib.ss_destroy(ctx)
        if reference is None:
            reference=result
            for n in names:totals[n]+=len(result[n]['viable'])
            basements+=sum(result['igloo']['basement'])
        elif result!=reference:raise RuntimeError(f'Optional interleaving mismatch: seed{seed},arm{arm}')
        hashes[arm].update(fingerprint(result).encode())
write_json(OUT/'optional-component-parity.json',dict(status='passed',arms=arms,count=len(seeds),
    positive_mansion_seeds_from_prior=len(prior['positive_mansion_inputs']),
    extra_run_key=2026101401,extra_start_index=130000000,extra_count=128,
    viable_optional_totals=totals,igloo_basements=basements,
    fingerprints={a:h.hexdigest() for a,h in hashes.items()},
    limitations=['Component inventories, not a complete eligible natural-world survivor',
                 'No promise of identical ambient MT state for arbitrary external API users']))
print('Optional component/interleaving parity passed',len(seeds),totals,'basements',basements)
