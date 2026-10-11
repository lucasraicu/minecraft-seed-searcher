"""Exercise the actual pack's pure JS policy, without BDS or world generation."""
import ctypes
import ctypes.util
import json
from pathlib import Path
import pytest
from seed_search.realm.verification import raster_from_columns

POLICY=Path(__file__).parents[1]/'src/seed_search/realm/bds_tools/column_policy.js'

def evaluate(cells=None, expression=None, result_expression=None, extra_source=""):
    library=ctypes.util.find_library('JavaScriptCore')
    if not library:
        pytest.skip('JavaScriptCore required for pure Script API policy fixtures')
    js=ctypes.CDLL(library)
    ptr=ctypes.c_void_p
    js.JSGlobalContextCreate.argtypes=[ptr];js.JSGlobalContextCreate.restype=ptr
    js.JSStringCreateWithUTF8CString.argtypes=[ctypes.c_char_p];js.JSStringCreateWithUTF8CString.restype=ptr
    js.JSEvaluateScript.argtypes=[ptr,ptr,ptr,ptr,ctypes.c_int,ctypes.POINTER(ptr)];js.JSEvaluateScript.restype=ptr
    js.JSValueToStringCopy.argtypes=[ptr,ptr,ctypes.POINTER(ptr)];js.JSValueToStringCopy.restype=ptr
    js.JSStringGetMaximumUTF8CStringSize.argtypes=[ptr];js.JSStringGetMaximumUTF8CStringSize.restype=ctypes.c_size_t
    js.JSStringGetUTF8CString.argtypes=[ptr,ctypes.c_char_p,ctypes.c_size_t];js.JSStringGetUTF8CString.restype=ctypes.c_size_t
    js.JSStringRelease.argtypes=[ptr];js.JSGlobalContextRelease.argtypes=[ptr]
    context=js.JSGlobalContextCreate(None)
    source=POLICY.read_text().replace('export ','')+extra_source+'\nJSON.stringify('+(result_expression or 'interpretColumn('+(expression or json.dumps(cells))+')')+');'
    script=js.JSStringCreateWithUTF8CString(source.encode());exception=ptr()
    try:
        value=js.JSEvaluateScript(context,script,None,None,1,ctypes.byref(exception))
        string=js.JSValueToStringCopy(context,exception if exception.value else value,None)
        size=js.JSStringGetMaximumUTF8CStringSize(string);buffer=ctypes.create_string_buffer(size)
        js.JSStringGetUTF8CString(string,buffer,size);js.JSStringRelease(string)
        assert not exception.value,buffer.value.decode()
        return json.loads(buffer.value)
    finally:
        js.JSStringRelease(script);js.JSGlobalContextRelease(context)

def block(y,name,logged=False):
    return {'y':y,'block':'minecraft:'+name,'waterlogged':logged}

def test_waterlogged_aquatic_plant_continues_elevated_water_depth():
    row=evaluate([block(101,'water'),block(100,'kelp',True),block(99,'seagrass',True),block(98,'clay')])
    assert (row['waterTop'],row['waterBottom'],row['waterDepth'])==(101,99,3)
    assert row['waterKnown'] is True
    assert row['waterSurface']['continuousHeight'] is None
    assert row['ground']['provenance']=='unverified'

@pytest.mark.parametrize('cell',[{'y':65,'block':'minecraft:kelp'},block(65,'kelp',None)])
def test_missing_or_failed_waterlogging_is_unknown(cell):
    # The live wrapper records null both for a missing getter and a caught throw.
    row=evaluate([cell,block(64,'sand')]);assert row['waterKnown'] is False
    r=raster_from_columns((0,0,1,1),1,[{'x':0,'z':0,**row}],{'stable':True})
    assert not r.known[0,0]

def test_solid_waterlogged_block_is_not_open_water():
    row=evaluate([block(80,'oak_slab',True),block(79,'water')])
    assert row['waterPresent'] is True and row['waterDepth']==0
    assert row['ground']['classification']=='obstruction_unclassified'
    assert row['waterKnown'] is True

@pytest.mark.parametrize('name,kind',[('ice','frozen_cover'),('packed_ice','frozen_cover'),('powder_snow','snow_cover'),('snow','snow_cover')])
def test_cover_does_not_expose_buried_lake(name,kind):
    row=evaluate([block(100,name),block(99,'water'),block(98,'stone')])
    assert row['waterDepth']==0 and row['cover'][0]['kind']==kind
    assert row['substrateStatus']=='hidden_by_cover'
    assert row['ground']['y']==100

def test_thin_snow_records_cover_and_support():
    row=evaluate([block(90,'snow_layer'),block(89,'grass_block')])
    assert row['ground']['y']==89 and row['cover'][0]['kind']=='thin_snow_cover'
    assert row['substrateStatus']=='observed_material_provenance_unverified'

def test_air_gap_and_dry_vegetation_do_not_inflate_depth():
    for middle in ('air','kelp'):
        row=evaluate([block(70,'water'),block(69,middle),block(68,'water'),block(67,'sand')])
        assert row['waterDepth']==1 and row['waterBottom']==70

def test_raster_known_water_has_no_natural_certification_and_legacy_unknown():
    row=evaluate([block(70,'water'),block(69,'sand')])
    r=raster_from_columns((0,0,2,1),1,[{'x':0,'z':0,**row}, {'x':1,'z':0,'ground':{'y':69},'waterDepth':1}],{'stable':True})
    assert r.known.tolist()==[[True,False]] and r.water[0,0]
    assert not r.natural_ground.any()

@pytest.mark.parametrize('getter',["", "get isWaterlogged(){throw new Error('unloaded');},"])
def test_live_observer_missing_and_throwing_getter(getter):
    expression="[observeBlock({"+getter+"typeId:'minecraft:kelp'},65), {y:64,block:'minecraft:sand',waterlogged:false}]"
    row=evaluate(expression=expression)
    assert row['waterKnown'] is False

@pytest.mark.parametrize('depth',[None,-1,True,1.5,'invalid'])
def test_invalid_depth_is_not_known_geometry(depth):
    row={'x':0,'z':0,'ground':{'y':80},'waterDepth':depth,'waterKnown':True,'policy':'actual-column-v2'}
    r=raster_from_columns((0,0,1,1),1,[row],{'stable':True})
    assert not r.known[0,0]

def test_capacity_does_not_establish_actual_water():
    row=evaluate(expression="[observeBlock({typeId:'minecraft:kelp',isWaterlogged:false,canContainLiquid(){return true;}},65),{y:64,block:'minecraft:sand',waterlogged:false}]")
    assert row['waterKnown'] is True and row['waterDepth']==0

@pytest.mark.parametrize('logged,layers,expected',[
    (True,['minecraft:kelp','minecraft:water'],True),
    (False,['minecraft:kelp','minecraft:air'],True),
    (True,['minecraft:kelp','minecraft:air'],False),
    (False,['minecraft:kelp','minecraft:water'],False),
])
def test_saved_probe_checks_actual_overlay(logged,layers,expected):
    # Load only the pure helpers, avoiding reader-only NBT/LevelDB dependencies
    # and the command-line extraction side effects.
    import ast
    script=POLICY.with_name('compare_saved_blocks.py')
    tree=ast.parse(script.read_text())
    helpers=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('overlay_water','probe_matches')],type_ignores=[])
    scope={};exec(compile(helpers,str(script),'exec'),scope)
    assert scope['probe_matches']({'block':'minecraft:kelp','waterlogged':logged},layers) is expected
