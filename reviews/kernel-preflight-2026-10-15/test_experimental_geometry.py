"""Check the native preflight geometry against every legal lattice center."""
from pathlib import Path
import importlib.util

from cffi import FFI
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def raw_geometry(tmp_path_factory):
    # Compile the actual static helpers without exposing a production test ABI.
    source = (ROOT / 'reviews/kernel-preflight-2026-10-15/tight-blueprint_dynamic.inc.txt').read_text()
    def section(start, end):
        return source[source.index(start):source.index(end)]
    code = '#include <stdlib.h>\n#include <string.h>\n#include "rng.h"\n'
    code += 'typedef struct {int x,z;} Pos;\ntypedef struct {int n,*xz;} NBPoints;\n'
    code += section('static int nb_dynamic_intcmp', 'static int nb_dynamic_cellcmp')
    code += section('static void nb_dynamic_event', 'static int nb_dynamic_subset')
    code += section('static int nb_dynamic_raw_bounds_core', 'int nb_dynamic_raw_bounds(')
    code += '''
int probe(const int *f,int nf,const int *b,int nb,int fg,int bg,
          const int *m,int nm,int *wide,int *tight) {
    Pos mansions[64];
    for(int i=0;i<nm;i++){mansions[i].x=m[2*i];mansions[i].z=m[2*i+1];}
    return nb_dynamic_raw_bounds_core(f,nf,b,nb,fg,bg,wide,
                                      m?mansions:NULL,nm,tight);
}
'''
    ffi = FFI()
    ffi.cdef('int probe(const int*,int,const int*,int,int,int,const int*,int,int*,int*);')
    ffi.set_source('_raw_geometry', code, include_dirs=[str(ROOT/'vendor/cubiomes-bedrock')])
    path = ffi.compile(tmpdir=str(tmp_path_factory.mktemp('raw-geometry')), verbose=False)
    spec = importlib.util.spec_from_file_location('_raw_geometry', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ffi, module.lib


def check_geometry(raw_geometry, fort, bast, mansions, fg=2, bg=2):
    ffi, lib = raw_geometry
    axis = np.arange(-1168, 1169, 8)
    x, z = np.meshgrid(axis, axis)
    def nether_count(points):
        return sum((8*(px-416)<x)&(x<=8*(px+416)) &
                   (8*(pz-416)<z)&(z<=8*(pz+416)) for px,pz in points)
    nether = (nether_count(fort)>=fg)&(nether_count(bast)>=bg)
    allowed = nether.copy()
    if mansions is not None:
        captured = np.zeros_like(allowed)
        for px,pz in mansions:
            captured |= (x-832<=px)&(px<x+832)&(z-832<=pz)&(pz<z+832)
        allowed &= captured
    def array(points):
        return ffi.new('int[]',np.asarray(points,dtype=int).reshape(-1).tolist() or [0])
    wide, tight = ffi.new('int[4]'), ffi.new('int[4]')
    status = lib.probe(array(fort),len(fort),array(bast),len(bast),fg,bg,
                       ffi.NULL if mansions is None else array(mansions),
                       0 if mansions is None else len(mansions),wide,tight)
    assert status == int(allowed.any())
    def bounds(mask):
        return [int(x[mask].min())-832,int(z[mask].min())-832,
                int(x[mask].max())+831,int(z[mask].max())+831]
    if nether.any():
        assert list(wide) == bounds(nether)
    if allowed.any():
        assert list(tight) == bounds(allowed)
        return list(tight)


def test_mansion_window_is_expanded_back_to_structure_positions(raw_geometry):
    bounds = check_geometry(raw_geometry,[(0,0),(16,16)],[(0,16),(16,0)],[(0,0)])
    assert bounds == [-1656,-1656,1663,1663]
    assert bounds[0] <= 1600 <= bounds[2]  # Center 800 captures mansion 0 AND structure 1600.


@pytest.mark.parametrize('mansions', [None,[],[(-1999,-1999)],[(1999,1999)],
    [(-1168,0),(1168,0)],[(1999,-1999),(-1999,1999)],[(1,-1)],[(7,-7)],[(8,-8)]])
def test_boundaries_and_alternative_mansions(raw_geometry,mansions):
    check_geometry(raw_geometry,[(-400,0),(400,0)],[(0,-400),(0,400)],mansions)


def test_randomized_geometry_matches_exhaustive_center_union(raw_geometry):
    rng=np.random.default_rng(2026101507)
    for case in range(100):
        fort=rng.integers(-562,562,size=(6,2))
        bast=rng.integers(-562,562,size=(6,2))
        mansions=rng.integers(-2000,2000,size=(1+case%4,2))
        check_geometry(raw_geometry,fort,bast,mansions,2+case%2,2+(case//2)%2)
