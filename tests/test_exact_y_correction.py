"""Exact block-Y regression against frozen BDS positives and the old quart API."""
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'fixtures/bedrock-26.52/generalization'

WRAPPER = r'''
#include "generator.h"
#include "finders.h"
#include <stdlib.h>
#include <string.h>
#include <limits.h>
int legacySampleBiomeNoise(const BiomeNoise*,int64_t*,int,int,int,uint64_t*,uint32_t);
int probe_integer_parity(void) {
    Generator *g=calloc(1,sizeof(*g)); if(!g)return -1;
    uint64_t seeds[]={0,1,UINT64_MAX,5050725658938791990ULL,4613350367979055430ULL};
    int versions[]={MC_1_18,MC_1_20,MC_1_21_60,MC_26_50};
    int flags[]={0,SAMPLE_NO_SHIFT,SAMPLE_NO_DEPTH,SAMPLE_NO_BIOME,
                 SAMPLE_NO_SHIFT|SAMPLE_NO_DEPTH|SAMPLE_NO_BIOME};
    int count=0;
    for(int s=0;s<5;s++)for(int v=0;v<4;v++) {
        setupGenerator(g,versions[v],0);applySeed(g,DIM_OVERWORLD,seeds[s]);
        for(int x=-9;x<=9;x+=3)for(int y=-16;y<=79;y+=5)
        for(int z=-9;z<=9;z+=3)for(int f=0;f<5;f++) {
            int64_t old[6],now[6];uint64_t a=0,b=0;
            int oa=legacySampleBiomeNoise(&g->bn,old,x,y,z,&a,flags[f]);
            int nb=sampleBiomeNoise(&g->bn,now,x,y,z,&b,flags[f]);
            if(oa!=nb || a!=b || memcmp(old,now,sizeof(old))) {free(g);return -2;}
            count++;
        }
    }
    free(g);return count;
}
int probe_exact(uint64_t seed,int x,int y,int z,int flags,int64_t *np) {
    Generator *g=calloc(1,sizeof(*g));if(!g)return -999;
    setupGenerator(g,MC_26_50,0);applySeed(g,DIM_OVERWORLD,seed);
    int id=sampleBiomeNoiseAtBlockY(&g->bn,np,x,y,z,NULL,flags);free(g);return id;
}
int probe_extreme_integer_parity(void) {
    Generator *g=calloc(1,sizeof(*g));if(!g)return -1;
    setupGenerator(g,MC_26_50,0);applySeed(g,DIM_OVERWORLD,UINT64_MAX);
    int ys[]={INT_MIN,INT_MIN/4-1,INT_MIN/4,INT_MIN/4+1,
              INT_MAX/4,INT_MAX/4+1,INT_MAX};
    int count=0;
    for(int i=0;i<7;i++)for(int flags=0;flags<8;flags++) {
        int64_t old[6],now[6];uint64_t a=0,b=0;
        int x=legacySampleBiomeNoise(&g->bn,old,-17,ys[i],-9,&a,flags);
        int y=sampleBiomeNoise(&g->bn,now,-17,ys[i],-9,&b,flags);
        if(x!=y || a!=b || memcmp(old,now,sizeof(old))) {free(g);return -2;}
        count++;
    }
    free(g);return count;
}
int probe_quart(uint64_t seed,int x,int y,int z,int flags,int64_t *np) {
    Generator *g=calloc(1,sizeof(*g));if(!g)return -999;
    setupGenerator(g,MC_26_50,0);applySeed(g,DIM_OVERWORLD,seed);
    int id=legacySampleBiomeNoise(&g->bn,np,x,y,z,NULL,flags);free(g);return id;
}
int probe_viable(uint64_t seed,int mc,int type,int x,int z) {
    Generator *g=calloc(1,sizeof(*g));if(!g)return -1;
    int dim=(type==Fortress || type==Bastion || type==Ruined_Portal_N)?DIM_NETHER:DIM_OVERWORLD;
    setupGenerator(g,mc,0);applySeed(g,dim,seed);
    int result=isViableStructurePos(type,g,x,z,0);free(g);return result;
}
int probe_version(int index) {
    int versions[]={MC_1_18,MC_1_20,MC_1_21_60,MC_26_50};return versions[index];
}
int probe_type(int outpost) {return outpost?Outpost:Village;}
'''


@pytest.fixture(scope='module')
def exact_native(tmp_path_factory):
    out = tmp_path_factory.mktemp('exact-y')
    wrapper = out / 'wrapper.c'
    wrapper.write_text(WRAPPER)
    vendor = ROOT / 'vendor/cubiomes-bedrock'
    library = out / 'exact-y.dylib'
    units = 'noise biomes layers biomenoise cave generator finders util quadbase mt'.split()
    command = ['cc', '-shared', '-fPIC', '-O2', '-std=c11', '-fwrapv', '-ffp-contract=off',
               '-I', str(vendor), str(wrapper), str(FIXTURE / 'exact-y-legacy-sampler.c'),
               *[str(vendor / (u + '.c')) for u in units], '-lm', '-o', str(library)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    assert result.returncode == 0, result.stderr
    lib = ctypes.CDLL(str(library))
    for name in ('probe_exact', 'probe_quart'):
        getattr(lib, name).argtypes = [ctypes.c_uint64, *([ctypes.c_int] * 4), ctypes.POINTER(ctypes.c_int64)]
    lib.probe_viable.argtypes = [ctypes.c_uint64, *([ctypes.c_int] * 4)]
    return lib


def test_98000_legacy_integer_quart_vectors_include_climate_and_search_cache(exact_native):
    assert exact_native.probe_integer_parity() == 98000
    assert exact_native.probe_extreme_integer_parity() == 56


def test_all_14_frozen_bds_exact_rejected_villages_are_retained(exact_native):
    path = FIXTURE / 'exact-y-completed-audit-prototype-v1.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == path.with_suffix('.sha256').read_text().strip()
    rows = json.loads(path.read_text())['restored_bds_exact_references']
    assert len(rows) == 14 and len({r['seed'] for r in rows}) == 8
    for row in rows:
        assert exact_native.probe_viable(int(row['seed']) % (1 << 64),
            exact_native.probe_version(3), exact_native.probe_type(0), *row['reference']) > 0


def test_frozen_outposts_legacy_models_and_retained_bds_positive_villages(exact_native):
    path = FIXTURE / 'exact-y-structure-parity-v1.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == path.with_suffix('.sha256').read_text().strip()
    data = json.loads(path.read_text())
    assert data['original_manifest_sha256'] == 'bbc14d21fba0455ed8f7cfe66099f34b6734575dfb7d8ffbcb00337eced72f1c'
    assert len(data['rows']) == 916
    unchanged = retained = 0
    for row in data['rows']:
        value = exact_native.probe_viable(int(row['seed']) % (1 << 64),
            exact_native.probe_version(row['version_index']),
            exact_native.probe_type(row['type'] == 'outpost'), *row['position'])
        if row['version_index'] != 3 or row['type'] == 'outpost':
            assert value == row['old_viable'], row
            unchanged += 1
        elif row['bds_outcome'] in ('reference_exact', 'navigation_exact'):
            assert value > 0, row
            retained += 1
    assert unchanged > 700 and retained >= 72


def test_exact_negative_fractional_y_and_flags_preserve_horizontal_climate(exact_native):
    # At whole quart planes the two APIs must agree; between planes the depth
    # parameter is bounded by the adjacent planes, while all horizontal values
    # remain identical. This catches floor/truncation and accidental X/Z scaling.
    between = 0
    for seed in (0, (1 << 64)-1):
        for x,z in ((-17,-9),(-1,0),(0,-1),(19,7)):
            for y in (-65,-64,-5,-4,-3,-2,-1,0,1,2,3,4,63,319):
                for flags in (0,1,2,4,7):
                    current=(ctypes.c_int64*6)();low=(ctypes.c_int64*6)();high=(ctypes.c_int64*6)()
                    actual=exact_native.probe_exact(seed,x,y,z,flags,current)
                    lo=exact_native.probe_quart(seed,x,y//4,z,flags,low)
                    exact_native.probe_quart(seed,x,y//4+1,z,flags,high)
                    if y%4==0:
                        assert actual==lo and list(current)==list(low)
                    else:
                        assert [current[i] for i in (0,1,2,3,5)]==[low[i] for i in (0,1,2,3,5)]
                        assert min(low[4],high[4])<=current[4]<=max(low[4],high[4])
                        if high[4]!=low[4]:
                            assert current[4] not in (low[4],high[4])
                            between+=1
    assert between>0
