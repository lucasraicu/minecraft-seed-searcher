"""Address/undefined-behavior checks for compact filters and generator ownership."""
import json
import os
from pathlib import Path
import subprocess

OUT=Path('runs/compact-implementation-2026-10-10/safety');OUT.mkdir(exist_ok=True)
DRIVER=r'''
#include "bridge.h"
#include <assert.h>
#include <limits.h>
#include <stdlib.h>
#include <stdio.h>
int main(void) {
 int xz[40000],xzt[3000],flags[1000],ids[600],xyz[1800];
 int types[]={ss_structure_type("village"),ss_structure_type("ancient_city"),ss_structure_type("fortress"),ss_structure_type("bastion"),ss_structure_type("fortress")};
 int bounds[]={-2768,-2768,2766,2766,-2768,-2768,2766,2766,-698,-698,697,697,-698,-698,697,697,-2000,-2000,1999,1999};int counts[320];
 assert(ss_mineshaft_first(NULL,0,0,8,8,xz)==-1);
 for(int pass=0;pass<32;pass++) {
  SeedContext *ctx=ss_create((uint64_t)pass*UINT64_C(11400714819323198485));assert(ctx);
  assert(ss_mineshaft_first(ctx,INT_MIN,0,8,8,xz)==-1);
  assert(ss_mineshaft_inventory(ctx,-768,-768,767,767,xz,20000)>=0);
  assert(ss_mineshaft_first(ctx,-768,-768,767,767,xz)>=0);
  assert(ss_mineshaft_first(ctx,-1,-1,1,1,xz)==0);
  assert(ss_nether_pair(ctx,-698,-698,697,697,xzt,flags,1000)>=0);
  assert(ss_structure_first(ctx,ss_structure_type("stronghold"),-10,-10,10,10,xz)==-1);
  assert(ss_structure_first(ctx,ss_structure_type("buried_treasure"),-768,-768,767,767,xz)>=0);
  assert(ss_structure_first(ctx,ss_structure_type("end_city"),-2000,-2000,1999,1999,xz)>=0);
  for(int i=0;i<600;i++){xyz[3*i]=(i%24)*64-768;xyz[3*i+1]=63;xyz[3*i+2]=(i/24)*64-768;}
  for(int dimension=-1;dimension<=1;dimension++)assert(ss_biome_points(ctx,dimension,xyz,600,ids)==0);
  assert(ss_biome_points(ctx,2,xyz,600,ids)==-1);
  ss_destroy(ctx);
 }
 for(int mode=0;mode<=3;mode++) {
  assert(ss_sweep_raw_mode((UINT64_C(1)<<32)-64,64,types,bounds,5,1,counts,320,mode)==0);
  assert(ss_sweep_raw_mode((UINT64_C(1)<<32)-64,65,types,bounds,5,1,counts,320,mode)==-1);
  assert(ss_sweep_raw_mode(0,64,types,bounds,5,1,counts,319,mode)==-1);
 }
 puts("PASS: compact native filters, capacity/unsigned boundaries, all dimensions, repeated ownership");
}
'''

def main():
 driver=OUT/'driver.c';driver.write_text(DRIVER)
 units=['noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt']
 cmd=['clang','-O1','-g','-std=c11','-fwrapv','-fno-omit-frame-pointer','-fsanitize=address,undefined','-Inative','-Ivendor/cubiomes-bedrock',str(driver),'native/bridge.c']+[f'vendor/cubiomes-bedrock/{u}.c' for u in units]+['-lm','-o',str(OUT/'probe')]
 with (OUT/'build.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}
 with (OUT/'run.log').open('w') as f:r=subprocess.run([str(OUT/'probe')],env=env,stdout=f,stderr=subprocess.STDOUT)
 record={'status':'PASS' if r.returncode==0 else 'FAIL','exit_code':r.returncode,'command':cmd,'limitations':'Serial native path. Apple leak detection disabled; not exhaustive race or leak proof.'}
 (OUT/'report.json').write_text(json.dumps(record,indent=2)+'\n');print((OUT/'run.log').read_text())
 raise SystemExit(r.returncode)

if __name__=='__main__':main()
