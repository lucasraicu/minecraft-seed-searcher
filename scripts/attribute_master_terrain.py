"""Isolated sensitivity probes on retained actual columns; no production model edit."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from verify_master_native import module

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'runs/master-implementation-2026-10-10'
PROBE=r'''
int ss_attribution(SeedContext *ctx,const int *xz,int n,int *out) {
 if(n<0 || n>256)return -1;
 if(!ctx->terrain_ready){initTerrainNoise(&ctx->terrain,ctx->seed);initTerrainShaper(&ctx->shaper);ctx->terrain_ready=1;}
 CaveNoise *cn=malloc(sizeof(*cn));TerrainCache *tc=malloc(sizeof(*tc));
 if(!cn || !tc){free(cn);free(tc);return -1;}
 initCaveNoise(cn,ctx->seed);initTerrainCache(tc);
 for(int i=0;i<n;i++) {
  int x=xz[2*i],z=xz[2*i+1],x0=floordiv(x,4)*4,z0=floordiv(z,4)*4;
  double offsets[4],factors[4],offset,factor,v[8];int cell=INT_MIN;
  for(int zz=0;zz<2;zz++)for(int xx=0;xx<2;xx++)sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,x0/4+xx,z0/4+zz,&offsets[2*zz+xx],&factors[2*zz+xx]);
  sampleTerrainShape(&ctx->overworld.bn,&ctx->shaper,floordiv(x,4),floordiv(z,4),&offset,&factor);
  int interpolated=-65,caves=-65,full=-65,water=-65,lava=-65;
  for(int y=319;y>=-64;y--) {
   if(interpolated==-65) {
    int y0=floordiv(y,8)*8;
    if(cell!=y0) {
     for(int zz=0;zz<2;zz++)for(int yy=0;yy<2;yy++)for(int xx=0;xx<2;xx++)
      v[4*zz+2*yy+xx]=sampleTerrainDensity(&ctx->terrain,offsets[2*zz+xx],factors[2*zz+xx],x0+xx*4,y0+yy*8,z0+zz*4);
     cell=y0;
    }
    if(lerp3((x-x0)/4.,(y-y0)/8.,(z-z0)/4.,v[0],v[1],v[2],v[3],v[4],v[5],v[6],v[7])>0)interpolated=y;
   }
   if(caves==-65 && sampleTerrainDensityCaves(&ctx->terrain,cn,offset,factor,x,y,z)>0)caves=y;
   if(full==-65 && y>=-60 && y<=254) {
    int state=getCaveBlockStateCached(&ctx->overworld.bn,&ctx->terrain,&ctx->shaper,cn,tc,x,y,z);
    if(state==CAVE_STONE)full=y;
    else if(state==CAVE_WATER && water==-65)water=y;
    else if(state==CAVE_LAVA && lava==-65)lava=y;
   }
   if(interpolated!=-65 && caves!=-65 && full!=-65)break;
  }
  out[5*i]=interpolated;out[5*i+1]=caves;out[5*i+2]=full;out[5*i+3]=water;out[5*i+4]=lava;
 }
 free(cn);free(tc);return 0;
}
'''


def build():
    from cffi import FFI
    folder=OUT/'terrain-attribution';folder.mkdir(exist_ok=True)
    code=(ROOT/'native/bridge.c').read_text()+PROBE
    (folder/'bridge.c').write_text(code)
    header=(ROOT/'native/bridge.h').read_text()
    ffi=FFI();ffi.cdef('\n'.join(line for line in header.splitlines() if not line.startswith('#'))+'\nint ss_attribution(SeedContext *,const int *,int,int *);')
    ffi.set_source('_master_attribution','#include "bridge.h"\nint ss_attribution(SeedContext *,const int *,int,int *);',
        sources=[str(folder/'bridge.c')]+[str(ROOT/f'vendor/cubiomes-bedrock/{u}.c') for u in ('noise','biomes','layers','biomenoise','cave','generator','finders','util','quadbase','mt')],
        include_dirs=[str(ROOT/'native'),str(ROOT/'vendor/cubiomes-bedrock')],extra_compile_args=['-O3','-std=c11','-fwrapv'],libraries=['m'])
    path=ffi.compile(tmpdir=str(folder),verbose=True)
    (folder/'build.json').write_text(json.dumps({'path':path,'module':'_master_attribution','probe_sha256':hashlib.sha256(code.encode()).hexdigest()},indent=2)+'\n')


def run():
    from seed_search.backend import Backend
    source=ROOT/'runs/realm-implementation-2026-10-10/final-bds-selected-check.json'
    saved=json.loads(source.read_text());raster=saved['observation']['raster'];x0,z0,x1,z1=raster['bounds'];step=raster['resolution']
    xx,zz=np.meshgrid(np.arange(x0,x1,step),np.arange(z0,z1,step))
    known=np.asarray(raster['known'],bool);observed=np.asarray(raster['height'],float)[known];water=np.asarray(raster['water'],bool)[known]
    points=np.ascontiguousarray(np.column_stack((xx[known],zz[known])),dtype=np.int32)
    with Backend(saved['seed']) as b:h8,_=b.heights(points,8);h1,_=b.heights(points,1);land=b.land(points)
    build=json.loads((OUT/'terrain-attribution/build.json').read_text());native=module(build['path'],build['module'])
    ctx=native.lib.ss_create(int(saved['seed'])&((1<<64)-1));values=np.empty((len(points),5),np.int32)
    try:assert native.lib.ss_attribution(ctx,native.ffi.from_buffer('int[]',points),len(points),native.ffi.from_buffer('int[]',values))==0
    finally:native.lib.ss_destroy(ctx)
    variants={'raw_stride8':h8,'raw_stride1':h1,'raw_interpolated':values[:,0],'caves_noninterpolated':values[:,1],'caves_interpolated_noodle_fluid':values[:,2]}
    summaries={name:{'height_mae':float(np.abs(v-observed).mean()),'height_max_error':float(np.abs(v-observed).max()),'water_height_proxy_mismatches':int(((v<=63)!=water).sum()),'changed_from_raw_stride1':int((v!=h1).sum())} for name,v in variants.items()}
    fields=['x','z','observed_support_y','actual_exposed_water','raw_stride8','raw_stride1','raw_interpolated','caves_noninterpolated','caves_interpolated_noodle_fluid','modeled_exposed_water_top','modeled_exposed_lava_top','raw_sea_level_convention_sensitive','attribution_status']
    rows=[]
    for i,p in enumerate(points):
        rows.append({'x':int(p[0]),'z':int(p[1]),'observed_support_y':float(observed[i]),'actual_exposed_water':bool(water[i]),
                     **{name:int(v[i]) for name,v in variants.items()},'modeled_exposed_water_top':int(values[i,3]),'modeled_exposed_lava_top':int(values[i,4]),
                     'raw_sea_level_convention_sensitive':bool(h1[i]==63),'attribution_status':'SENSITIVITY_ONLY; actual causal mechanism unresolved'})
    with (OUT/'terrain-attribution/columns.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    report={'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'seed':saved['seed'],'columns':len(points),'variants':summaries,'exact_raw_land_water_mismatches':int((~land!=water).sum()),
            'modeled_exposed_water_mismatches':int(((values[:,3]>-65)!=water).sum()),'actual_policy':saved['observation'].get('interpretation',raster.get('metadata')),
            'cave_block_model_range':[-60,254],'probe_build':build,
            'decision':'Keep production raw model and unknown actual qualification. This selected sample tests sensitivity, not independent validation of cave/interpolation/fluid accuracy; no automatic cave inventory or scoring.',
            'remaining_causes':['actual structure/natural-ground provenance','block-state/surface interpretation','version-matched interpolation/cave/fluid parity','independent whole-formation coverage']}
    (OUT/'terrain-attribution/report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=('build','run'));args=p.parse_args();{'build':build,'run':run}[args.command]()
