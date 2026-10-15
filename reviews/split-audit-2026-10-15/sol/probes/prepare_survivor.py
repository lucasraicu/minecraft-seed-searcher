"""Extend the private diagnostic build; never edit production sources."""
from pathlib import Path
import json
from experiment import WORK, replace_once

target = WORK / 'diagnostic'
p = target / 'native/blueprint_dynamic.inc'
text = p.read_text()
for anchor, slot in [
    ('            for(int k=0;k<5;k++){code=nb_dynamic_optional(w,feasible,k,optional+k);if(code)goto done;}', 35),
    ('            code=nb_dynamic_palette_prefix(w,&prefix);if(code)goto done;', 36),
    ('            code=nb_dynamic_nether_prefix(w,&nether_prefix);if(code)goto done;', 37),
]:
    text = replace_once(text, anchor,
        f'            double sol_extra_{slot}=sol_audit_time();\n' + anchor +
        f'\n            sol_audit_elapsed({slot},sol_audit_time()-sol_extra_{slot});')
text = replace_once(text, '    int total=256;',
                    '    double sol_events=sol_audit_time();\n    int total=256;')
text = replace_once(text, '    cells=(NBDynamicCell*)w->dyn_cells;',
                    '    sol_audit_elapsed(38,sol_audit_time()-sol_events);\n    cells=(NBDynamicCell*)w->dyn_cells;')
text = replace_once(text, '    int best=0;', '    double sol_argmin=sol_audit_time();\n    int best=0;')
text = replace_once(text, '    r->stage_seconds[13]+=nb_time()-stage;\n    stage=nb_time();',
    '    sol_audit_elapsed(39,sol_audit_time()-sol_argmin);\n'
    '    r->stage_seconds[13]+=nb_time()-stage;\n    stage=nb_time();')
p.write_text(text)
header = target / 'native/blueprint_batch.h'
header.write_text(header.read_text() + '''
int sol_stage_probe(uint64_t seed,const NBPolicy *p,double *seconds,int *counts);
''')
p = target / 'native/blueprint_batch.inc'
p.write_text(p.read_text() + '''
/* Forced components: these calls are not evidence a seed passed any gate. */
int sol_stage_probe(uint64_t seed,const NBPolicy *p,double *seconds,int *counts) {
    uint64_t allocated=0;
    NBWorker w={0};w.ctx=ss_create(seed);w.p=p;w.allocated_bytes=&allocated;
    NBObservation mandatory[13]={0},optional[5]={0};NBAnchor a={0};
    const int ow[4]={-2000,-2000,1999,1999},nw[4]={-562,-562,561,561};
    int code=0,*prefix=NULL,*nether=NULL;double t;
    if(!w.ctx)return -3;
    sol_current=NULL;
    t=nb_time();
    for(int k=0;k<13;k++) {
        if(k==10||k==11)continue;
        code=nb_pair(&w,k,ow,mandatory+k);if(code)goto cleanup;
        counts[k]=mandatory[k].viable.n;
    }
    code=nb_nether(&w,nw,&a);if(code)goto cleanup;
    counts[10]=a.observations[10].viable.n;counts[11]=a.observations[11].viable.n;
    seconds[0]=nb_time()-t;
    t=nb_time();for(int k=0;k<5;k++) {
        code=nb_dynamic_optional(&w,ow,k,optional+k);if(code)goto cleanup;
        counts[13+k]=optional[k].viable.n;
    }seconds[1]=nb_time()-t;
    t=nb_time();code=nb_dynamic_palette_prefix(&w,&prefix);if(code)goto cleanup;
    seconds[2]=nb_time()-t;
    t=nb_time();code=nb_dynamic_nether_prefix(&w,&nether);if(code)goto cleanup;
    seconds[3]=nb_time()-t;
    /* Center-zero complete evidence uses the cached palette grids. */
    const int bounds[4]={-832,-832,831,831};
    t=nb_time();code=nb_palette(&w,bounds,&a);if(code)goto cleanup;
    code=nb_dynamic_nether_evidence(&w,&a);if(code)goto cleanup;
    seconds[4]=nb_time()-t;
    counts[18]=a.biome_mask;counts[19]=a.nether_biome_n;
cleanup:
    for(int k=0;k<13;k++)nb_clear_full(mandatory+k);
    for(int k=0;k<5;k++)nb_clear_full(optional+k);
    nb_clear_anchor(&a);ss_destroy(w.ctx);free(w.scratch);free(w.flags);
    free(w.dyn_prefix);free(w.dyn_nether_prefix);free(w.dyn_biome_grid);free(w.dyn_nether_grid);
    return code;
}
''')
print('Prepared survivor diagnostic hooks and forced-component probe.')
label_file=Path(__file__).resolve().parents[1]/'diagnostic-labels.json'
labels=json.loads(label_file.read_text())
labels['labels'][35:40]=['optional_inventories','overworld_prefix','nether_prefix','event_build','argmin']
labels['status']='extended survivor diagnostics prepared; baseline profile used slots0..34 only'
label_file.write_text(json.dumps(labels,indent=2)+'\n')
