"""Standalone ownership/bounds checks under AddressSanitizer and UBSan."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/master-implementation-2026-10-10/safety'
DRIVER=r'''
#include "bridge.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
int main(void) {
 const int n=100000;int *xz=malloc(2*n*sizeof(int)),*land=malloc(n*sizeof(int));
 int heights[512],biomes[512],grid[512];double climate[3072],approx[512];
 assert(xz && land);
 for(int i=0;i<n;i++){xz[2*i]=(i%33)-17;xz[2*i+1]=(i%29)-15;}
 for(int pass=0;pass<64;pass++) {
  SeedContext *ctx=ss_create((uint64_t)pass*UINT64_C(11400714819323198485));assert(ctx);
  assert(ss_set_threads(ctx,1)==0);
  assert(ss_land(ctx,xz,0,land)==0);assert(ss_land(ctx,xz,-1,land)==-1);
  assert(ss_land(ctx,xz,n+1,land)==-1);
  assert(ss_land(ctx,xz,pass%2?15:n,land)==0);
  assert(ss_heights(ctx,xz,512,pass%2?1:8,heights,biomes)==0);
  assert(ss_grid(ctx,-17,-15,32,16,4,63,grid,climate,approx)==0);
  ss_destroy(ctx);
 }
 int types[]={ss_structure_type("village"),ss_structure_type("fortress")};
 int bounds[]={-577,-301,578,301,-511,-511,511,511};int counts[128];
 assert(ss_sweep_raw((UINT64_C(1)<<32)-64,64,types,bounds,2,1,counts,128)==0);
 assert(ss_sweep_raw((UINT64_C(1)<<32)-64,65,types,bounds,2,1,counts,128)==-1);
 assert(ss_sweep_raw(0,64,types,bounds,2,1,counts,127)==-1);
 free(xz);free(land);puts("PASS: bounded batches, negative edges, repeated context ownership, raw final boundary/capacity");
}
'''


def main():
    OUT.mkdir(exist_ok=True);driver=OUT/'driver.c';driver.write_text(DRIVER)
    sources=[str(ROOT/'native/bridge.c')]+[str(ROOT/f'vendor/cubiomes-bedrock/{u}.c') for u in ('noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt')]
    cmd=['clang','-O1','-g','-std=c11','-fwrapv','-fno-omit-frame-pointer','-fsanitize=address,undefined',
         '-I'+str(ROOT/'native'),'-I'+str(ROOT/'vendor/cubiomes-bedrock'),str(driver),*sources,'-lm','-o',str(OUT/'probe')]
    with (OUT/'build.log').open('w') as stream:subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,check=True)
    import os
    env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}
    with (OUT/'run.log').open('w') as stream:result=subprocess.run([str(OUT/'probe')],env=env,stdout=stream,stderr=subprocess.STDOUT)
    (OUT/'report.json').write_text(json.dumps({'status':'PASS' if result.returncode==0 else 'FAIL','exit_code':result.returncode,
          'compiler_command':cmd,'driver_sha256':hashlib.sha256(driver.read_bytes()).hexdigest(),
          'limitations':'Serial native path; Apple runtime leak detection disabled; no claim of exhaustive leak/race proof. OpenMP separately covered by ownership audit and all-thread output tests.'},indent=2)+'\n')
    if result.returncode:raise SystemExit(result.returncode)
    print((OUT/'run.log').read_text())


if __name__=='__main__':main()
