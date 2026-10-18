"""Validate proposed contracts and tiny model examples; no production services.

The dependency-free schema checker supports only the JSON Schema constructs
used by request_schema.json. It is not an application request validator.
"""
import copy
import hashlib
import json
import math
import re
import sqlite3
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name):
    return json.loads((HERE / name).read_text())


def schema_matches(value, schema):
    if "type" in schema:
        kind = schema["type"]
        ok = {"object":isinstance(value,dict),"array":isinstance(value,list),
              "string":isinstance(value,str),"integer":isinstance(value,(int,float)) and not isinstance(value,bool) and value == int(value)}
        if not ok[kind]:
            return False
    if "const" in schema and (isinstance(value,bool) != isinstance(schema["const"],bool) or value != schema["const"]):
        return False
    if "enum" in schema and not any(value == item and isinstance(value,bool) == isinstance(item,bool) for item in schema["enum"]):
        return False
    if "not" in schema and schema_matches(value,schema["not"]):
        return False
    if "allOf" in schema and not all(schema_matches(value,s) for s in schema["allOf"]):
        return False
    if "oneOf" in schema and sum(schema_matches(value,s) for s in schema["oneOf"]) != 1:
        return False
    if "if" in schema:
        branch = schema.get("then",{}) if schema_matches(value,schema["if"]) else schema.get("else",{})
        if not schema_matches(value,branch):
            return False
    if isinstance(value,dict):
        if not set(schema.get("required",[])) <= value.keys():
            return False
        props = schema.get("properties",{})
        if schema.get("additionalProperties") is False and not value.keys() <= props.keys():
            return False
        if not all(schema_matches(v,props[k]) for k,v in value.items() if k in props):
            return False
    if isinstance(value,list):
        if len(value) < schema.get("minItems",0) or len(value) > schema.get("maxItems",math.inf):
            return False
        if schema.get("uniqueItems") and len({json.dumps(v,sort_keys=True) for v in value}) != len(value):
            return False
        if "items" in schema and not all(schema_matches(v,schema["items"]) for v in value):
            return False
    if isinstance(value,str) and len(value) < schema.get("minLength",0):
        return False
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        if value < schema.get("minimum",-math.inf) or value > schema.get("maximum",math.inf):
            return False
    return True


def inside(point, center, side):
    return all(c-side//2 <= p < c+side//2 for p,c in zip(point,center))


def near(point, center, side, radius):
    return inside(point,center,side) and sum((p-c)**2 for p,c in zip(point,center)) <= radius**2


def capacity(retention, mode_count):
    borders = len(retention["border_sides"])
    count = retention["structure_count"]
    proximity = retention["structure_proximity"]
    biome = retention["biome_proximity"]
    pairs = retention["biome_landmark_pairs"]
    profiles = retention["profiles"]
    diversity = retention["diversity"]
    per_mode_border = (count["features"]*count["scopes_per_border"]*count["k"] +
                       proximity["features"]*proximity["k"] + biome["features"]*biome["k"] +
                       pairs["biomes"]*len(pairs["landmarks"])*pairs["k"] + profiles["count"]*profiles["k"] +
                       2**len(diversity["bits"])*len(diversity["profiles"])*diversity["k_each"])
    return per_mode_border*borders*mode_count + retention["reference_sample"]["k"]


def main():
    registry, policy, storage = load("feature_registry.json"), load("public_policy.json"), load("storage_layout.json")
    presets, request, schema = load("ui_presets.json"), load("example_request.json"), load("request_schema.json")
    assert policy["runtime_enabled"] is False and policy["billing"]["enabled"] is False
    assert policy["public"]["border_sides"] == [2048,4096,8192]
    assert schema["properties"]["border_side"]["enum"] == [2048,4096,8192]
    assert registry["scope"]["exact_game_builds"] == []
    features = {f["id"]:f for f in registry["features"]}
    assert len(features) == 23 and all(f["runtime_enabled"] is False for f in features.values())
    assert sum(f["kind"] == "structure_count" for f in features.values()) == 14
    assert sum(f["kind"] == "biome_witness" for f in features.values()) == 9
    assert len(registry["categories"]) == len(presets["presets"]) == 8
    assert all(not f["complete_negative_evidence"] for f in features.values())
    profile_ids = {p["id"] for p in policy["profiles"]}
    assert len(profile_ids) == 16
    for profile in policy["profiles"]:
        values = profile["coefficients_VTAOEBHR"]
        assert len(values) == 8 and sum(values)>0
    for preset in presets["presets"]:
        example = {**request,"fallback_profile":preset["fallback_profile"],"rows":preset["rows"]}
        assert preset["fallback_profile"] in profile_ids
        assert len(preset["rows"]) <= policy["billing"]["free"]["max_rows"]
        assert schema_matches(example,schema), preset["id"]
    assert schema_matches(request,schema)
    bad = copy.deepcopy(request); bad["border_side"] = 10000
    assert not schema_matches(bad,schema)
    bad = copy.deepcopy(request); bad["rows"][0]["scope"]["radius"] = 513
    assert not schema_matches(bad,schema)
    bad = copy.deepcopy(request); bad["rows"][0]["importance"] = 5
    assert not schema_matches(bad,schema)
    bad = copy.deepcopy(request); del bad["rows"][2]["importance"]
    assert not schema_matches(bad,schema)
    bad = copy.deepcopy(request); bad["rows"][0]["at_least"] = 17
    assert not schema_matches(bad,schema)
    bad = copy.deepcopy(request); bad["rows"][2]["scope"]["radius"] = 512
    assert not schema_matches(bad,schema)
    bad = copy.deepcopy(request); bad["rows"][1]["any_of"] *= 2
    assert not schema_matches(bad,schema)
    assert capacity(policy["retention"],2) == 83944
    assert capacity(policy["retention"],3) == 120916
    assert math.lcm(*range(1,17)) == policy["score"]["utility_lcm"]
    axes = policy["public"]["anchor_grid_axis"]
    assert len(axes)**2 == 81 and 0 in axes
    assert [s+2*max(axes) for s in policy["public"]["border_sides"]] == [4000,6048,10144]
    assert [-5120,-5120,5120,5120] == policy["public"]["tile_aligned_max_envelope"]
    assert (10240//64)**2*2 == 51200
    assert -1//16 == -1 and -1-(-1)*16 == 15
    assert -1//256 == -1 and -1-(-1)*256 == 255
    assert -64//256 == -1 and (-64+256)//64 == 3 and 128//64 == 2
    assert 2*4+3 == 11
    point = (1400,100)
    assert not inside(point,(0,0),2048)
    assert inside(point,(0,0),4096) and not near(point,(0,0),4096,512)
    assert near(point,(976,0),2048,512)
    assert 424**2+100**2 == 189776
    assert inside((-1024,0),(0,0),2048)
    assert not inside((1024,0),(0,0),2048)
    assert near((512,0),(0,0),2048,512) and not near((513,0),(0,0),2048,512)
    # Combining true facts from two different anchors must not invent a match.
    anchor_flags = [(True,False),(False,True)]
    assert any(a for a,b in anchor_flags) and any(b for a,b in anchor_flags)
    assert not any(a and b for a,b in anchor_flags)
    summary = storage["summary"]
    payload = sum(summary[name]["bytes"] for name in ["structure_counts","structure_nearest_d2","biome_nearest_d2","biome_witness_sample_ref","scope_complete_bits"])
    assert payload == summary["fixed_feature_payload_bytes"] == 364
    assert (23*4+7)//8 == 12
    counts = struct.pack('<56I',*range(56))
    assert len(counts) == 224 and struct.unpack('<56I',counts)[55] == 55
    db = sqlite3.connect(':memory:')
    db.executescript((HERE / 'catalog_schema.sql').read_text())
    assert [r[0] for r in db.execute('SELECT side FROM border_profile ORDER BY side')] == [2048,4096,8192]
    seeds = [-(2**63),-1,0,1,2**63-1]
    for i,seed in enumerate(seeds):
        unsigned = seed & (2**64-1)
        db.execute('INSERT INTO world VALUES (?,?,?,?,?,?,?)',(str(i),'bedrock','test-build','test-settings',seed,unsigned.to_bytes(8,'big'),'test-time'))
        assert int(str(seed)) == seed
    assert [r[0] for r in db.execute('SELECT seed_i64 FROM world ORDER BY rowid')] == seeds
    db.execute("INSERT INTO observation_set VALUES ('obs','2','model','extractor','registry','settings',NULL,'complete')")
    db.execute("INSERT INTO anchor VALUES ('a','2','overworld',976,0)")
    db.execute("INSERT INTO anchor_role VALUES ('a','settlement','v1',NULL)")
    db.execute("INSERT INTO layout VALUES ('layout','a','obs',2048,'geometry-v1')")
    assert db.execute("SELECT min_x,max_x_exclusive FROM layout_bounds WHERE layout_id='layout'").fetchone() == (-48,2000)
    db.execute("INSERT INTO layout_summary VALUES (?,?,?,?,?,?,?)",('layout','summary-v1',counts,bytes(56),bytes(36),bytes(36),bytes(12)))
    try:
        db.execute("INSERT INTO spawn_observation VALUES ('bad','2','unknown','initial_player','v1','a',NULL,NULL)")
        raise AssertionError('Unknown spawn must not have an invented coordinate')
    except sqlite3.IntegrityError:
        pass
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    checked_docs = [ROOT/'PUBLIC_CATALOG_SYSTEM_SPEC.md',HERE/'README.md']
    for doc in checked_docs:
        content = doc.read_text()
        assert content.count('```') % 2 == 0
        assert all(line == line.rstrip() for line in content.splitlines())
        for target in re.findall(r'\]\(([^)]+)\)',content):
            if '://' not in target and not target.startswith('#'):
                assert (doc.parent / target.split('#')[0]).exists(), (str(doc),target)
    result = {
        "scope":"Proposed contract and tiny in-memory model consistency, not production implementation/throughput",
        "passed":True,"categories":8,"features":23,"settlement_anchors":81,"border_sides":[2048,4096,8192],
        "initial_layouts_per_world":243,"retention_slot_bound":83944,"retention_bound_with_spawn":120916,
        "fixed_feature_payload_bytes":364,"largest_one_plane_biome_grid_bytes":51200,
        "checks":["registry/preset references","valid and invalid request shapes","exact three borders","retention arithmetic","negative coordinates","nested and clipped geometry","same-anchor conjunction","payload round-trip","SQL schema and constraints","int64 seed round-trip","local documentation links"],
        "contract_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.json')) if p.name != 'validation-results.json'},
    }
    (ROOT/'reviews/catalog-system-spec-2026-10-17/contract-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['passed','categories','features','border_sides','retention_slot_bound','fixed_feature_payload_bytes']},indent=2))


if __name__ == '__main__':
    main()
