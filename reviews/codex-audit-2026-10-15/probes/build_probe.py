from pathlib import Path
from cffi import FFI
ROOT=Path.cwd(); out=Path('/tmp/minecraft-audit-20261015')
ffi=FFI(); header=(ROOT/'native/blueprint_batch.h').read_text()
ffi.cdef('\n'.join(l for l in header.splitlines() if not l.startswith('#'))+'''
void audit_reset(int fail_call);
size_t audit_peak(void);
size_t audit_live(void);
int audit_calls(void);
''')
source=r'''
#include "bridge.c"
#include <stdio.h>
#include <stddef.h>
static size_t audit_bytes=0,audit_high=0;
static int audit_n=0,audit_fail=0;
typedef union { max_align_t align; size_t n; } AuditHeader;
static void *audit_malloc(size_t n) {
    audit_n++;
    if(audit_n==audit_fail) {fprintf(stderr,"INJECTED malloc failure call=%d bytes=%zu\n",audit_n,n);return NULL;}
    AuditHeader *p=malloc(sizeof(*p)+n);if(!p)return NULL;p->n=n;
    audit_bytes+=n;if(audit_bytes>audit_high)audit_high=audit_bytes;
    return p+1;
}
static void *audit_calloc(size_t n,size_t s){void *p=audit_malloc(n*s);if(p)memset(p,0,n*s);return p;}
static void audit_free(void *p){if(p){AuditHeader *h=(AuditHeader*)p-1;audit_bytes-=h->n;free(h);}}
void audit_reset(int f){audit_high=audit_bytes;audit_n=0;audit_fail=f;}
size_t audit_peak(void){return audit_high;}
size_t audit_live(void){return audit_bytes;}
int audit_calls(void){return audit_n;}
#define malloc audit_malloc
#define calloc audit_calloc
#define free audit_free
#include "blueprint_batch.inc"
'''
ffi.set_source('audit_batch',source,sources=[str(ROOT/f'vendor/cubiomes-bedrock/{u}.c') for u in ['noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt']],include_dirs=[str(ROOT/'native'),str(ROOT/'vendor/cubiomes-bedrock')],extra_compile_args=['-O2','-std=c11','-fwrapv'],libraries=['m'])
print(ffi.compile(tmpdir=str(out),verbose=False))
