"""Exercise native ownership and buffers in an isolated AddressSanitizer binary."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.blueprint_batch_prototype import Prototype
from scripts.build_blueprint_batch import UNITS
from seed_search.realm.config import blueprint_config,locked_blueprint_config,river_blueprint_config,outpost_blueprint_config


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--locked',action='store_true')
    parser.add_argument('--river',action='store_true')
    parser.add_argument('--outpost',action='store_true')
    parser.add_argument('--profile',action='store_true',help='Also exercise diagnostic timing buffer ownership')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    p=Prototype(args.native,outpost_blueprint_config() if args.outpost else river_blueprint_config() if args.river else locked_blueprint_config() if args.locked else blueprint_config()).policy
    setup=[]
    for field,n in [('discovery',4),('types',13),('goals',10),('y',4),('fixture_surface',10),('fixture_caves',3),('structure_order',9)]:
        setup += [f'p.{field}[{i}]={getattr(p,field)[i]};' for i in range(n)]
    for i in range(256):setup.append(f'p.biome_members[{i}]={p.biome_members[i]}u;')
    for field in ('dark_id','pale_id','spacing','batch_size','locked','overworld_half','nether_half','nether_goal','river','bastion_goal','outpost_goal'):setup.append(f'p.{field}={getattr(p,field)};')
    source='''#include "bridge.c"
#include "'''+('blueprint_profile.inc' if args.profile else 'blueprint_batch.inc')+'''"
#include <assert.h>
#include <stdio.h>
int main(void) {
 NBPolicy p={0}; p.max_buffer_bytes=256ULL<<20;
'''+ '\n'.join(setup)+'''
 uint64_t seeds[32];NBFixture fixtures[32];
 for(int i=0;i<32;i++){
  seeds[i]=i==0?UINT64_MAX:i==1?(UINT64_C(1)<<63):i==2?UINT64_C(12345)+(UINT64_C(1)<<32):(uint64_t)i*UINT64_C(6364136223846793005);
  fixtures[i]=(NBFixture){i==0?-1:0,i==0?-7:0,i<4?-1:i-4};
 }
 int inputs=0;
 for(int complete=0;complete<=1;complete++) {
  p.complete=complete;
  for(int repeat=0;repeat<8;repeat++) {
   NBBatch *b=nb_fixture_sweep(seeds,fixtures,32,&p,1);assert(b&&b->effective_threads==1);
   for(int i=0;i<32;i++){assert(!b->results[i].error);if(i<4)assert(b->results[i].anchors[0].biome_mask==8191);}
   inputs+=32;nb_free(b);
  }
  NBBatch *b=nb_sweep(seeds,32,&p,1);assert(b);
  for(int i=0;i<32;i++)assert(!b->results[i].error);
  inputs+=32;nb_free(b);
 }
 p.complete=0;p.retention=1;
 for(int limit=0;limit<=3;limit++) {
  p.max_misses=limit;
  for(int i=0;i<32;i++){fixtures[i].missing=-1;fixtures[i].extra_mask=(i%4)==0?0:(i%4)==1?1:(i%4)==2?(1u|(1u<<13)):(1u|(1u<<13)|(1u<<14));}
  for(int repeat=0;repeat<4;repeat++) {
   NBBatch *b=nb_fixture_sweep(seeds,fixtures,32,&p,1);assert(b&&!b->error);
   assert(b->result_count==8*(limit+1));
   for(int i=0;i<b->result_count;i++)assert(b->results[i].nanchors==1);
   inputs+=32;nb_free(b);
  }
 }
 for(int limit=10;limit<=16;limit+=3) {
  p.max_misses=limit;
  NBBatch *b=nb_sweep(seeds,32,&p,1);assert(b&&!b->error);
  inputs+=32;nb_free(b);
 }
 p.retention=0;p.max_misses=0;
'''+('''
 for(int complete=0;complete<=1;complete++) {
  p.complete=complete;p.retention=!complete;p.max_misses=complete?0:2;
  NBProfileBatch *b=nb_profile_sweep(seeds,32,&p,1);assert(b&&b->batch&&!b->batch->error);
  for(int i=0;i<32;i++)assert(b->samples[i].stages[0].count==1);
  inputs+=32;nb_profile_free(b);
 }
 assert(!nb_profile_sweep(seeds,513,&p,1));nb_profile_free(NULL);
 p.retention=0;p.max_misses=0;
''' if args.profile else '')+'''
 p.goals[5]=4;assert(!nb_sweep(seeds,32,&p,1));nb_free(NULL);
 printf("{\\"sanitized_inputs\\":%d,\\"errors\\":0}\\n",inputs);
 return 0;
}
'''
    path=args.output/'ownership.c';path.write_text(source);binary=(args.output/'ownership').resolve()
    cmd=['clang','-O1','-g','-std=c11','-fwrapv','-fsanitize=address','-fno-omit-frame-pointer',
         '-I'+str(ROOT/'native'),'-I'+str(ROOT/'vendor/cubiomes-bedrock'),str(path.resolve()),
         *[str(ROOT/f'vendor/cubiomes-bedrock/{u}.c') for u in UNITS],'-lm','-o',str(binary)]
    compilation=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    (args.output/'compile.log').write_text(compilation.stdout+compilation.stderr);compilation.check_returncode()
    env=dict(os.environ);env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1'
    result=subprocess.run([str(binary)],cwd=ROOT,env=env,text=True,capture_output=True)
    (args.output/'execution.log').write_text(result.stdout+result.stderr);result.check_returncode()
    evidence={**json.loads(result.stdout),'tool':'AddressSanitizer','threads':1,
              'profile_buffers':args.profile,'locked_geometry':args.locked or args.river or args.outpost,'river_policy':args.river or args.outpost,
              'outpost_policy':args.outpost,
              'scope':'buffer/use-after-free checks; leak detection unsupported on this macOS ASan runtime',
              'compile_command':cmd,'production_extension_replaced':False}
    (args.output/'result.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence))


if __name__=='__main__':main()
