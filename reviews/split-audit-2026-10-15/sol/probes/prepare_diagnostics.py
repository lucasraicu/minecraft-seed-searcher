"""Prepare diagnostic-only source hooks. Does not compile or execute native code.

The prepared hooks need compilation and functional validation after user release.
They deliberately keep their stage labels separate from the legacy profiler.
"""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[4]
WORK = Path('/tmp/minecraft-sol-audit-20261015')
sys.path.insert(0, str(Path(__file__).parent))
from experiment import replace_once

LABELS = [
    'raw_nether_pair', 'raw_nether_bounds', 'raw_outpost', 'raw_mansion',
    'raw_trial_chamber', 'raw_ancient_city', 'raw_village', 'nether_viability_pair',
    'outpost_inventory', 'mansion_inventory', 'mansion_y63_witnesses', 'mansion_viability',
    'mansion_surface_initialization', 'mansion_approx_height', 'mansion_radius',
    'biome_point', 'mansion_cache_queries', 'mansion_cache_hits',
    'mansion_raw_starts', 'mansion_viable_starts',
    'stage_stronghold', 'stage_mansion', 'stage_jungle_temple', 'stage_desert_pyramid',
    'stage_monument', 'stage_ancient_city', 'stage_village', 'stage_trial_chamber',
    'stage_ruined_portal', 'stage_shipwreck', 'stage_mineshaft',
    'stage_raw_preflight_plus_final_nether', 'stage_final_evidence',
    'stage_dynamic_center_search', 'stage_outpost', 'reserved_35', 'reserved_36',
    'reserved_37', 'reserved_38', 'reserved_39',
]


def main():
    target = WORK / 'diagnostic'
    if target.exists():
        raise ValueError(f'Refusing to overwrite {target}')
    shutil.copytree(WORK / 'control', target)
    header = target / 'native/blueprint_batch.h'
    header.write_text(header.read_text() + '''
typedef struct SolAuditSample {
    uint64_t seed;
    double seconds[40];
    uint64_t counts[40];
    double eval_seconds;
    int worker;
} SolAuditSample;
NBBatch *sol_diag_sweep(const uint64_t *seeds,int count,const NBPolicy *p,
                      int threads,SolAuditSample *samples);
NBBatch *sol_diag_fixture_sweep(const uint64_t *seeds,const NBFixture *fixtures,
                              int count,const NBPolicy *p,int threads,SolAuditSample *samples);
''')
    (target / 'native/sol_diagnostics_api.h').write_text('''
double sol_audit_time(void);
void sol_audit_elapsed(int slot,double seconds);
''')
    (target / 'native/sol_diagnostics.h').write_text('''
#include "blueprint_batch.h"
#define NB_HEADER_INCLUDED 1
#include <time.h>
static _Thread_local SolAuditSample *sol_current;
double sol_audit_time(void) {
    struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);
    return (double)t.tv_sec+(double)t.tv_nsec*1e-9;
}
void sol_audit_elapsed(int slot,double seconds) {
    if(sol_current){sol_current->seconds[slot]+=seconds;sol_current->counts[slot]++;}
}
#ifdef _OPENMP
#define SOL_WORKER omp_get_thread_num()
#else
#define SOL_WORKER 0
#endif
#define NB_PROFILE_BIND(w,p,i) do { \\
    sol_current=(p)?((SolAuditSample*)(p))+(i):NULL; \\
    (w)->profile=sol_current;if(sol_current)sol_current->worker=SOL_WORKER; \\
} while(0)
#define NB_PROFILE_SEED(w,s) do {if(sol_current)sol_current->seed=(s);} while(0)
#define NB_PROFILE_STAGE(w,k,s,x,z) ((void)0)
#define NB_PROFILE_POINT_BEGIN(w) double sol_point_started=sol_audit_time()
#define NB_PROFILE_POINT_END(w,id,x,y,z) sol_audit_elapsed(15,sol_audit_time()-sol_point_started)
#define NB_PROFILE_INVENTORY_BEGIN(w)
#define NB_PROFILE_INVENTORY_END(w,k,x,z) ((void)0)
#define NB_PROFILE_CACHE(w,hit) do {if(sol_current){ \\
    sol_current->counts[16]++;sol_current->counts[17]+=!!(hit);}} while(0)
''')
    bridge = target / 'native/bridge.c'
    bridge.write_text(bridge.read_text() + '\n#include "sol_diagnostics.h"\n')
    batch = target / 'native/blueprint_batch.inc'
    text = batch.read_text()
    text = replace_once(text,
        '                    w->flags[i]=!!isViableStructurePos(Mansion,&w->ctx->overworld,x,z,0);',
        '                    double sol_viable_started=sol_audit_time();\n'
        '                    w->flags[i]=!!isViableStructurePos(Mansion,&w->ctx->overworld,x,z,0);\n'
        '                    sol_audit_elapsed(11,sol_audit_time()-sol_viable_started);')
    text = replace_once(text, '    nb_clear_full(o);\n    code=nb_copy(w,&o->raw,w->scratch,n);',
        '    if(slot==0&&sol_current&&n>=0)sol_current->counts[18]+=(uint64_t)n;\n'
        '    nb_clear_full(o);\n    code=nb_copy(w,&o->raw,w->scratch,n);')
    text = replace_once(text, '    if(slot==0&&n) {',
        '    if(slot==0&&sol_current)sol_current->counts[19]+=(uint64_t)n;\n'
        '    if(slot==0&&n) {')
    text = replace_once(text,
        '        for(int i=0;i<n;i++)o->mansion_ids[i]=nb_point(w,o->viable.xz[2*i],63,o->viable.xz[2*i+1]);',
        '        double sol_witness_started=sol_audit_time();\n'
        '        for(int i=0;i<n;i++)o->mansion_ids[i]=nb_point(w,o->viable.xz[2*i],63,o->viable.xz[2*i+1]);\n'
        '        sol_audit_elapsed(10,sol_audit_time()-sol_witness_started);')
    text = replace_once(text, '                r->error=nb_eval(&w,seeds[i],r);',
        '                r->error=nb_eval(&w,seeds[i],r);\n'
        '                if(sol_current)sol_current->eval_seconds=r->seconds;\n'
        '                if(sol_current)for(int k=0;k<15;k++) {\n'
        '                    sol_current->seconds[20+k]=r->stage_seconds[k];\n'
        '                    sol_current->counts[20+k]=(r->stage_seconds[k]>0);\n'
        '                }')
    text += '''
NBBatch *sol_diag_sweep(const uint64_t *seeds,int count,const NBPolicy *p,
                      int threads,SolAuditSample *samples) {
    if(!samples||count<1||count>16384)return NULL;
    memset(samples,0,(size_t)count*sizeof(*samples));
    return nb_run(seeds,NULL,count,p,threads,samples);
}
NBBatch *sol_diag_fixture_sweep(const uint64_t *seeds,const NBFixture *fixtures,
                              int count,const NBPolicy *p,int threads,SolAuditSample *samples) {
    if(!samples||!fixtures||count<1||count>16384)return NULL;
    memset(samples,0,(size_t)count*sizeof(*samples));
    return nb_run(seeds,fixtures,count,p,threads,samples);
}
'''
    batch.write_text(text)
    dynamic = target / 'native/blueprint_dynamic.inc'
    text = dynamic.read_text()
    for anchor, slot in [
        ('    int n=ss_nether_raw_pair(w->ctx,-562,-562,561,561,pairs,256);', 0),
        ('    int possible=nb_dynamic_raw_bounds(fort,nf,bast,nb,w->p->nether_goal,w->p->bastion_goal,feasible);', 1),
    ]:
        text = replace_once(text, anchor,
            f'    double sol_raw_started_{slot}=sol_audit_time();\n' + anchor +
            f'\n    sol_audit_elapsed({slot},sol_audit_time()-sol_raw_started_{slot});')
    text = replace_once(text,
        '        int ok=nb_raw_atleast(w,w->p->types[slot],feasible,goal);',
        '        double sol_floor_started=sol_audit_time();\n'
        '        int ok=nb_raw_atleast(w,w->p->types[slot],feasible,goal);\n'
        '        sol_audit_elapsed(2+j,sol_audit_time()-sol_floor_started);')
    for anchor, slot in [
        ('    code=nb_nether(w,nw,&nether_macro);if(code)goto done;', 7),
        ('    code=nb_pair(w,12,feasible,&macro[12]);if(code)goto done;', 8),
        ('    code=nb_pair(w,0,feasible,&macro[0]);if(code)goto done;', 9),
    ]:
        statement, error = anchor.split(';if(code)')
        text = replace_once(text, anchor,
            f'    double sol_stage_started_{slot}=sol_audit_time();\n' + statement + ';\n' +
            f'    sol_audit_elapsed({slot},sol_audit_time()-sol_stage_started_{slot});\n' +
            '    if(code)' + error)
    dynamic.write_text(text)
    finder = target / 'vendor/cubiomes-bedrock/finders.c'
    text = '#include "sol_diagnostics_api.h"\n' + finder.read_text()
    start = text.index('    case Mansion:', text.index('int isViableStructurePos('))
    end = text.index('    case Ruined_Portal:', start)
    block = text[start:end]
    for anchor, slot in [
        ('                initSurfaceNoise(&sn, DIM_OVERWORLD, g->seed);', 12),
        ('                mapApproxHeight(&height, &biome_id, g, &sn, x >> 2, z >> 2, 1, 1);', 13),
    ]:
        block = replace_once(block, anchor,
            f'                double sol_component_{slot}=sol_audit_time();\n' + anchor +
            f'\n                sol_audit_elapsed({slot},sol_audit_time()-sol_component_{slot});')
    anchor = '                if (!areBiomesViable(g, sampleX, (int)height+23/*mansion height*/, sampleZ, 32, b, m, approx))'
    block = replace_once(block, anchor,
        '                double sol_radius_started=sol_audit_time();\n'
        '                int sol_radius_ok=areBiomesViable(g, sampleX, (int)height+23/*mansion height*/, sampleZ, 32, b, m, approx);\n'
        '                sol_audit_elapsed(14,sol_audit_time()-sol_radius_started);\n'
        '                if (!sol_radius_ok)')
    finder.write_text(text[:start] + block + text[end:])
    path = ROOT / 'reviews/split-audit-2026-10-15/sol/diagnostic-labels.json'
    path.write_text(json.dumps({'labels': LABELS,
        'counts_20_to_34': 'nonzero native result timing fields; not exact entered-predicate counters',
        'worker': 'OpenMP worker index for each input before compaction',
        'status': 'source prepared; not compiled or validated'}, indent=2) + '\n')
    print('Prepared diagnostic sources only. Native compilation and validation remain pending.')


if __name__ == '__main__':
    main()
