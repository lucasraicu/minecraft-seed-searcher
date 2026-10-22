"""Fresh diagnostic builds must preserve caps, not just frozen-binary parity."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

import pytest

from scripts.build_count_pilot import ROOT, build, build_source, mineshaft_source


def test_mineshaft_extraction_caps_both_compiler_paths_independent_of_first_policy():
    filters=(ROOT/'native/filters.inc').read_text()
    old_filters=filters.replace('n<0 || (first && n>=first)','n<0 || first')
    for source in (filters,old_filters):
        fragment=mineshaft_source(source)
        assert fragment.count('if(n>=cap)return n;')==4
        assert '#if defined(__GNUC__) || defined(__clang__)' in fragment
    with pytest.raises(ValueError,match='emit sites'):
        mineshaft_source(filters.replace('n=emit(p,xz,n,cap);','n=0;'))
    assert build_source().count('if(n>=cap)return n;')==8


def test_fresh_count_pilot_build_preserves_positive_mineshaft_caps(tmp_path):
    frozen=ROOT/'runs/count-bits-2026-10-11/native/identity.json'
    frozen_before=frozen.read_bytes() if frozen.exists() else None
    output=tmp_path/'fresh-native'
    identity=build(output)
    assert Path(identity['extension']).is_relative_to(output)
    assert identity['production_extension_replaced'] is False
    assert identity['inputs']['scripts/build_count_pilot.py']==hashlib.sha256((ROOT/'scripts/build_count_pilot.py').read_bytes()).hexdigest()
    # A separate interpreter prevents accidentally testing the already imported
    # frozen extension with the same module name in other historical tests.
    script=r'''
import importlib.util,json,sys
from seed_search.backend import Backend
spec=importlib.util.spec_from_file_location('_count_pilot',sys.argv[1])
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
ffi,lib=module.ffi,module.lib
checked=0;positive=0;restricted_positive=0
for seed in (12345,-1,2**32+12345):
    ctx=lib.ss_create(seed&((1<<64)-1));assert ctx!=ffi.NULL
    try:
        with Backend(seed) as reference:
            for bounds in ((-768,-768,767,767),(-1537,-1025,-2,510),(0,0,0,0)):
                starts=reference.structures('mineshaft',bounds)
                ids=[reference.biome(x,0,z) for x,z in starts]
                b=ffi.new('int[4]',bounds)
                selected={v for v in ids[:2]}
                allow=ffi.new('int[256]')
                for value in selected:allow[value]=1
                for goal in (1,2,4,8,32):
                    for bits in (0,32,48):
                        for raw in (0,1):
                            stats=ffi.new('int[8]')
                            result=lib.pc_count(ctx,lib.ss_structure_type(b'mineshaft'),b,goal,raw,bits,ffi.NULL,0,stats)
                            assert result==min(goal,len(starts)),(seed,bounds,goal,raw,bits,result,len(starts))
                            checked+=1;positive+=int(len(starts)>goal)
                        stats=ffi.new('int[8]')
                        result=lib.pc_count(ctx,lib.ss_structure_type(b'mineshaft'),b,goal,0,bits,allow,0,stats)
                        expected=sum(value in selected for value in ids)
                        assert result==min(goal,expected),(seed,bounds,goal,bits,result,expected)
                        checked+=1;restricted_positive+=int(expected>goal)
    finally:lib.ss_destroy(ctx)
assert positive>0 and restricted_positive>0
print(json.dumps(dict(checked=checked,positive_over_cap=positive,qualified_over_cap=restricted_positive)))
'''
    result=subprocess.run([sys.executable,'-c',script,identity['extension']],cwd=ROOT,text=True,capture_output=True,check=True)
    evidence=json.loads(result.stdout)
    assert evidence['checked']==405
    assert evidence['positive_over_cap']>0 and evidence['qualified_over_cap']>0
    (output/'parity.json').write_text(json.dumps(evidence,indent=2)+'\n')
    if frozen_before is not None:assert frozen.read_bytes()==frozen_before


def test_extraction_ignores_intervening_helper_comments_and_literal_braces():
    source = r'''static int ss_mineshaft_query(void) {
    const char *label = "brace } and escaped \" quote";
    /* A misleading closing brace: } */
    // And another: }
    #if defined(__GNUC__) || defined(__clang__)
    n=emit((Pos){x*16+8,zz*16+8},xz,n,cap);
    #else
    n=emit(p,xz,n,cap);
    #endif
    return n;
}
static int unrelated_helper(void) { n=emit(p,xz,n,cap); return n; }
int ss_mineshaft_first(void) { return 0; }
'''
    fragment = mineshaft_source(source)
    assert fragment.count('if(n>=cap)return n;') == 2
    assert 'unrelated_helper' not in fragment
    assert 'ss_mineshaft_first' not in fragment


@pytest.mark.parametrize('source', ['', 'static int ss_mineshaft_query(void);',
                                   'static int ss_mineshaft_query(void) { /* }',
                                   'static int ss_mineshaft_query(void) { "}";'])
def test_extraction_fails_closed_for_incomplete_function(source):
    with pytest.raises(ValueError, match='Mineshaft extraction'):
        mineshaft_source(source)
