"""Build attribution-only hooks in an isolated source copy; never modifies production."""
from pathlib import Path
import shutil,sys,json
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).parent
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts import build_blueprint_batch as builder
W=Path('/tmp/final-audit-233fad7-diagnostic')
if W.exists():raise SystemExit('Refusing to overwrite diagnostic source')
for sub in ['native','vendor/cubiomes-bedrock']:
    shutil.copytree(ROOT/sub,W/sub,ignore=shutil.ignore_patterns('.git','__pycache__','*.so','*.o'))
(W/'scripts').mkdir();shutil.copy2(ROOT/'scripts/build_blueprint_batch.py',W/'scripts/build_blueprint_batch.py')
h=W/'native/blueprint_batch.h'
h.write_text(h.read_text()+'''
typedef struct AuditSample { uint64_t seed; double seconds[10]; unsigned int calls[10]; double eval_seconds; } AuditSample;
NBBatch *audit_sweep(const uint64_t *seeds,int count,const NBPolicy *p,int threads,AuditSample *samples);
''')
b=W/'native/bridge.c'
b.write_text(b.read_text()+'''
#include "blueprint_batch.h"
#define NB_HEADER_INCLUDED 1
static _Thread_local AuditSample *audit_current;
#define NB_PROFILE_BIND(w,p,i) do {audit_current=(p)?((AuditSample*)(p))+(i):NULL;} while(0)
#define NB_PROFILE_SEED(w,s) do {if(audit_current)audit_current->seed=(s);} while(0)
#define NB_PROFILE_STAGE(w,k,s,x,z) ((void)0)
#define NB_PROFILE_POINT_BEGIN(w)
#define NB_PROFILE_POINT_END(w,id,x,y,z) ((void)0)
#define NB_PROFILE_INVENTORY_BEGIN(w)
#define NB_PROFILE_INVENTORY_END(w,k,x,z) ((void)0)
#define NB_PROFILE_CACHE(w,hit) ((void)0)
#define AUDIT_BEGIN(k) double audit_started_##k=nb_time()
#define AUDIT_END(k) do { if(audit_current) { audit_current->seconds[k]+=nb_time()-audit_started_##k; audit_current->calls[k]++; } } while(0)
''')
d=W/'native/blueprint_dynamic.inc';s=d.read_text()
def replace(a,b,n=1):
    global s
    assert s.count(a)==n,(a,s.count(a),n)
    s=s.replace(a,b)
replace('stage=nb_time();possible=nb_dynamic_raw_preflight(w,feasible);','stage=nb_time();AUDIT_BEGIN(0);possible=nb_dynamic_raw_preflight(w,feasible);AUDIT_END(0);',2)
replace('if(w->p->retention)applySeed(&w->ctx->overworld,DIM_OVERWORLD,seed);','if(w->p->retention){AUDIT_BEGIN(1);applySeed(&w->ctx->overworld,DIM_OVERWORLD,seed);AUDIT_END(1);}')
replace('possible=nb_audit_dark_possible(w,feasible);','AUDIT_BEGIN(2);possible=nb_audit_dark_possible(w,feasible);AUDIT_END(2);')
replace('code=nb_pair(w,0,feasible,&macro[0]);if(code)goto done;','AUDIT_BEGIN(3);code=nb_pair(w,0,feasible,&macro[0]);AUDIT_END(3);if(code)goto done;')
replace('code=nb_dynamic_discovery(w,r,ow);if(code)goto done;','AUDIT_BEGIN(4);code=nb_dynamic_discovery(w,r,ow);AUDIT_END(4);if(code)goto done;',2)
replace('code=nb_pair(w,12,feasible,&macro[12]);if(code)goto done;','AUDIT_BEGIN(5);code=nb_pair(w,12,feasible,&macro[12]);AUDIT_END(5);if(code)goto done;')
replace('applySeed(&w->ctx->nether,DIM_NETHER,seed);','AUDIT_BEGIN(6);applySeed(&w->ctx->nether,DIM_NETHER,seed);')
replace('code=nb_nether(w,nw,&nether_macro);if(code)goto done;','code=nb_nether(w,nw,&nether_macro);AUDIT_END(6);if(code)goto done;')
replace('stage=nb_time();code=nb_pair(w,k,feasible,&macro[k]);if(code)goto done;','stage=nb_time();AUDIT_BEGIN(7);code=nb_pair(w,k,feasible,&macro[k]);AUDIT_END(7);if(code)goto done;')
replace('    int total=256;','    AUDIT_BEGIN(8);\n    int total=256;')
replace('if(!ncells){r->stage_seconds[13]+=nb_time()-stage;goto done;}','if(!ncells){AUDIT_END(8);r->stage_seconds[13]+=nb_time()-stage;goto done;}')
replace('    int chosen=best;','    AUDIT_END(8);\n    AUDIT_BEGIN(9);\n    int chosen=best;')
replace('    a->score=nb_score(w,a);\ndone:','    a->score=nb_score(w,a);AUDIT_END(9);\ndone:')
d.write_text(s)
b=W/'native/blueprint_batch.inc';s=b.read_text()
s=s.replace('r->error=nb_eval(&w,seeds[i],r);','r->error=nb_eval(&w,seeds[i],r);if(audit_current)audit_current->eval_seconds=r->seconds;')
s+='''
NBBatch *audit_sweep(const uint64_t *seeds,int count,const NBPolicy *p,int threads,AuditSample *samples) {
    if(!samples)return NULL;
    memset(samples,0,(size_t)count*sizeof(*samples));
    return nb_run(seeds,NULL,count,p,threads,samples);
}
'''
b.write_text(s)
builder.ROOT=W
identity=builder.build(W/'build',ROOT/'runs/master-implementation-2026-10-10/openmp/install',cpu_native=True,lto=True)
(OUT/'diagnostic-build.json').write_text(json.dumps(identity,indent=2)+'\n')
print('Built isolated attribution hooks; no PGO, not a throughput comparison.')
