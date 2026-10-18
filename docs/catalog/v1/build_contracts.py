"""Generate proposed catalog contract artifacts; does not activate runtime features."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def dump(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")


categories = [
    ("general", "General catalog", "balanced_survival"),
    ("builders", "Builders", "biome_variety"),
    ("rare", "Rare & unusual", "structure_collector"),
    ("survival", "Survival & realms", "village_life"),
    ("adventure", "Adventure", "trial_adventurer"),
    ("biomes", "Biome explorers", "biome_variety"),
    ("ocean", "Ocean exploration", "ocean_explorer"),
    ("technical", "Technical planning", "archaeology"),
]
structures = [
    ("village", "Village", ["general", "builders", "survival"], 6),
    ("trial_chamber", "Trial chamber", ["general", "adventure"], 4),
    ("ancient_city", "Ancient city", ["rare", "adventure"], 2),
    ("mansion", "Woodland mansion", ["rare", "adventure"], 1),
    ("monument", "Ocean monument", ["rare", "ocean", "technical"], 2),
    ("outpost", "Pillager outpost", ["survival", "technical"], 2),
    ("desert_pyramid", "Desert pyramid", ["adventure"], 2),
    ("jungle_temple", "Jungle temple", ["rare", "adventure"], 2),
    ("swamp_hut", "Swamp hut", ["rare", "technical"], 2),
    ("igloo", "Igloo", ["rare", "adventure"], 2),
    ("trail_ruins", "Trail ruins", ["adventure"], 2),
    ("ruined_portal", "Ruined portal", ["general", "survival"], 6),
    ("shipwreck", "Shipwreck", ["ocean", "adventure"], 4),
    ("mineshaft", "Mineshaft", ["adventure", "technical"], 8),
]
biomes = [
    ("cherry_grove", "Cherry grove", ["cherry_grove"], ["builders", "biomes"]),
    ("mushroom_fields", "Mushroom fields", ["mushroom_fields", "mushroom_field_shore"], ["rare", "builders", "biomes"]),
    ("bamboo_jungle", "Bamboo jungle", ["bamboo_jungle"], ["builders", "biomes"]),
    ("desert", "Desert", ["desert", "desert_hills", "desert_lakes"], ["builders", "biomes"]),
    ("badlands", "Badlands", ["badlands", "badlands_plateau", "wooded_badlands_plateau", "eroded_badlands", "modified_badlands_plateau", "modified_wooded_badlands_plateau", "wooded_badlands"], ["rare", "builders", "biomes"]),
    ("snowy", "Snowy terrain", ["snowy_plains", "snowy_mountains", "ice_spikes", "snowy_slopes", "snowy_taiga"], ["builders", "biomes"]),
    ("mangrove_swamp", "Mangrove swamp", ["mangrove_swamp"], ["builders", "biomes"]),
    ("forest", "Forest / birch", ["forest", "birch_forest", "flower_forest", "old_growth_birch_forest"], ["general", "builders", "survival", "biomes"]),
    ("plains", "Plains / meadow", ["plains", "sunflower_plains", "meadow"], ["general", "builders", "survival", "biomes"]),
]
features = []
for slot, (key, label, groups, target) in enumerate(structures):
    features.append({
        "id": "structure." + key, "slot": slot, "label": label,
        "kind": "structure_count", "dimension": "overworld", "category_tags": groups,
        "contract_status": "planned_filter", "runtime_enabled": False,
        "extractor_key": key, "semantics": "distinct_viable_predicted_start",
        "supported_rules": ["required", "preferred"], "supported_scopes": ["near_base", "inside_border"],
        "count_min": 1, "count_max": 16, "importance": [1, 3, 5],
        "evidence_label": "Predicted structure start", "complete_negative_evidence": False,
        "specialist_reference_target": target,
        "known_caveat": "Known candidate/viability disagreement; actual generation unverified" if key == "ancient_city" else "Actual generation unverified",
    })
for slot, (key, label, members, groups) in enumerate(biomes):
    features.append({
        "id": "biome." + key, "slot": slot, "label": label,
        "kind": "biome_witness", "dimension": "overworld", "category_tags": groups,
        "contract_status": "planned_filter", "runtime_enabled": False,
        "canonical_members": members, "canonicalizer": "seed_search.realm.biomes.canonical",
        "method": "predictor_world_lattice_y63_stride64_v1", "sample_y": 63, "sample_stride": 64,
        "supported_rules": ["required", "preferred"], "supported_scopes": ["near_base", "inside_border"],
        "supports_any_of": True, "importance": [1, 3, 5],
        "evidence_label": "Sampled biome observation", "surface_claim": False,
        "complete_negative_evidence": False,
    })
roadmap = [
    ("structure.stronghold", "map_only", "Known incomplete enumeration; no mandatory-count filter"),
    ("variant.igloo_basement", "gated", "Separate predictor/variant validation"),
    ("terrain.base_surface_biome", "gated", "Validated surface query"),
    ("terrain.flat_build_area", "gated", "Surface slope and connected area"),
    ("terrain.biome_patch_area", "gated", "Surface-biome raster and connectivity"),
    ("terrain.island", "gated", "Land/water geometry and connectivity"),
    ("relation.structure_biome", "gated", "Structure-relative biome query"),
    ("relation.structure_cluster", "gated", "Pair/cluster geometry; does not establish farm function"),
    ("verification.portal_room", "gated", "Actual block evidence and footprint coverage"),
    ("dimension.nether", "deferred", "Independent public dimensional contract"),
    ("anchor.spawn", "gated", "Version-matched accuracy and incremental-cost experiment"),
]
dump("feature_registry.json", {
    "schema_version": 1, "registry_id": "catalog-features-proposed-v1", "status": "proposed_not_implemented",
    "scope": {"edition": "bedrock", "exact_game_builds": [], "model_candidate": "MC_26_50", "silent_version_fallback": False},
    "categories": [{"id": key, "label": label, "default_profile": profile} for key, label, profile in categories],
    "features": features,
    "roadmap": [{"id": key, "status": state, "runtime_enabled": False, "requires": reason} for key, state, reason in roadmap],
})

def sr(feature, count, radius=None, importance=3):
    return {"rule":"preferred","kind":"structure_count","feature":"structure."+feature,
            "at_least":count,"importance":importance,
            "scope":{"kind":"near_base","radius":radius} if radius else {"kind":"inside_border"}}


def br(members, radius=1024, importance=3):
    return {"rule":"preferred","kind":"biome_witness","any_of":["biome."+m for m in members],
            "importance":importance,"scope":{"kind":"near_base","radius":radius}}


preset_rows = {
    "general": [],
    "builders": [br(["cherry_grove"],256,5), sr("village",1,512,1)],
    "rare": [br(["mushroom_fields"],1024,5), sr("mansion",1,None,3)],
    "survival": [sr("village",1,512,5), sr("ruined_portal",1,512,3), br(["plains"],512,1)],
    "adventure": [sr("trial_chamber",2,1024,5), sr("ancient_city",1,1024,3), sr("desert_pyramid",1,1024,1)],
    "biomes": [br(["forest","plains"],1024,1), br(["cherry_grove","mushroom_fields"],1024,5), br(["mangrove_swamp","bamboo_jungle"],1024,3)],
    "ocean": [sr("monument",1,None,5), sr("shipwreck",2,1024,3)],
    "technical": [sr("outpost",1,1024,5), sr("swamp_hut",1,None,3)],
}
dump("ui_presets.json", {
    "revision":"catalog-ui-presets-proposed-v1", "status":"hypotheses_not_validated_demand", "runtime_enabled":False,
    "presets":[{"id":key,"label":label,"fallback_profile":profile,"rows":preset_rows[key],"editable":True,"adds_hidden_requirements":False} for key,label,profile in categories],
})

profile_rows = [
    ("balanced_survival", [2,1,1,1,2,2,2,1]),
    ("village_life", [5,0,0,0,1,1,5,0]),
    ("trial_adventurer", [1,5,1,0,1,1,2,0]),
    ("ancient_city_explorer", [1,1,5,0,1,1,1,0]),
    ("ocean_explorer", [0,0,0,5,2,2,1,1]),
    ("biome_variety", [0,0,0,1,1,5,1,0]),
    ("structure_collector", [1,1,1,1,5,1,0,2]),
    ("archaeology", [0,0,0,0,2,2,1,5]),
    ("compact_starter", [2,1,0,0,1,1,5,0]),
    ("village_and_trials", [4,4,0,0,1,1,2,0]),
    ("village_and_ocean", [4,0,0,4,1,1,2,0]),
    ("village_and_biomes", [4,0,0,0,1,4,2,0]),
    ("cities_and_trials", [0,4,4,0,1,1,1,0]),
    ("ocean_and_biomes", [0,0,0,4,1,4,1,0]),
    ("rare_and_biomes", [0,0,0,0,1,4,1,4]),
    ("multiplayer_variety", [4,3,1,1,3,3,2,1]),
]
policy = {
    "policy_id": "catalog-policy-proposed-v1", "status": "proposed_not_implemented", "runtime_enabled": False,
    "personal_policy": {"revision": "dynamic-envelope-2048-v3", "top_k": 50, "change_personal_behavior": False},
    "public": {
        "border_sides": [2048,4096,8192], "near_radii": [256,512,1024],
        "anchor_grid_axis": [-976,-768,-512,-256,0,256,512,768,976],
        "anchor_modes_active_when_catalog_enabled": ["origin","recommended"], "default_anchor_mode": "recommended",
        "spawn_mode": "gated_off_until_accuracy_and_cost_validation", "origin_is_spawn": False,
        "geometry": "half_open_square_and_closed_circle_intersection_v1", "absolute_coordinate_dtype": "int32",
        "tile_side_blocks": 256, "biome_stride": 64, "biome_y_planes": [63], "biome_id_dtype": "uint16_le",
        "nominal_max_envelope": [-5072,-5072,5072,5072], "tile_aligned_max_envelope": [-5120,-5120,5120,5120],
        "first_reference_worlds": 100, "full_reference_worlds": 10000,
        "storage_budget_gib": 20, "pause_ingestion_at_fraction": 0.8,
        "no_row_per_rejected_seed": True, "sampling_policy": "explicit_per_campaign_independent_of_personal_qualification",
    },
    "score": {"revision": "request-relative-v1", "utility_lcm": 720720, "importance": [1,3,5],
              "required_compensation": False, "default_profile": "balanced_survival",
              "tie_distance_scale": 1000000, "tie_distance_rounding": "integer_floor_normalized_sqrt",
              "canonical_seed_order": "unsigned_64_bit_pattern_ascending"},
    "retention": {
        "modes": ["origin","recommended"], "border_sides": [2048,4096,8192],
        "structure_count": {"features": 14, "scopes_per_border": 4, "k": 100, "admit_count_at_least": 1},
        "structure_proximity": {"features": 14, "k": 100, "admit_within_blocks": 256},
        "biome_proximity": {"features": 9, "k": 100, "admit_within_blocks": 1024},
        "biome_landmark_pairs": {"biomes": 9, "landmarks": ["structure.village","structure.trial_chamber","structure.monument","structure.desert_pyramid"], "k": 50, "biome_within": 256, "landmark_within": 512},
        "profiles": {"count": 16, "k": 100},
        "diversity": {"bits": ["biome.cherry_grove","biome.mushroom_fields","biome.bamboo_jungle","biome.snowy","structure.village","structure.trial_chamber","structure.ancient_city","structure.monument"], "within": 1024, "profiles": ["balanced_survival","biome_variety","compact_starter","archaeology"], "k_each": 1},
        "reference_sample": {"k": 10000, "hash": "sha256", "salt": "catalog-reference-proposed-v1", "before_relevance_gates": True},
        "world_cap_before_pins_and_dedup": 83944, "world_cap_with_spawn_before_pins_and_dedup": 120916,
        "capacities_are_pilot_defaults_not_quality_guarantees": True,
    },
    "profile_features": {
        "V": "min(village_count_near1024/6,1)", "T": "min(trial_count_near1024/4,1)",
        "A": "min(ancient_city_count_near1024/2,1)", "O": "min((monument+shipwreck)_near1024/6,1)",
        "E": "distinct_observed_launch_structure_types_near1024/14",
        "B": "min(distinct_observed_launch_biome_families_near1024/8,1)",
        "H": "max(0,1-nearest_village_distance/1024); zero if none in scope",
        "R": "min((jungle_temple+swamp_hut+igloo+trail_ruins)_near1024/4,1)",
    },
    "profiles": [{"id": key, "coefficients_VTAOEBHR": values} for key, values in profile_rows],
    "billing": {
        "enabled": False, "currency": "usd", "prices_are_hypotheses": True,
        "free": {"price_cents": 0, "searches_daily": 20, "max_rows": 3, "max_worlds_per_request": 5, "favorites": 10, "saved_alerts": 0, "comparison_worlds": 2, "exports_daily": 0},
        "plus": {"monthly_price_cents": 499, "nonrenewing_7_day_price_cents": 299, "searches_daily": 200, "max_rows": 12, "max_worlds_per_request": 50, "favorites": 200, "saved_alerts": 20, "comparison_worlds": 5, "exports_daily": 20},
        "all_categories_and_supported_borders_on_both_tiers": True, "paid_accuracy_upgrade": False,
        "full_sweeps_or_bds_jobs_included": False, "quota_day": "UTC_calendar_day_display_reset_in_user_timezone",
    },
    "serving": {"initial_p95_target_ms": 1000, "benchmark_concurrent_users": 5, "index_segment_layout_rows_max": 1048576,
                "exact_over_saved_layouts": True, "raw_observation_store_replicas": 2, "no_unverified_top25_shortcut": True},
}
dump("public_policy.json", policy)
request = {
    "request_revision": "catalog-query-v1", "edition": "bedrock", "game_build_id": "example-only-build",
    "catalog_snapshot_id": "example-only-snapshot", "world_settings_id":"vanilla-default-proposed", "dimension":"overworld", "anchor_mode": "recommended", "border_side": 4096,
    "evidence_policy": "predicted_observations_v1", "fallback_profile": "balanced_survival",
    "rows": [
        {"rule":"required","kind":"structure_count","feature":"structure.village","at_least":3,"scope":{"kind":"near_base","radius":512}},
        {"rule":"required","kind":"biome_witness","any_of":["biome.cherry_grove","biome.mushroom_fields"],"scope":{"kind":"near_base","radius":256}},
        {"rule":"preferred","kind":"structure_count","feature":"structure.trial_chamber","at_least":2,"importance":5,"scope":{"kind":"inside_border"}},
    ],
}
dump("example_request.json", request)
scope_schema = {"oneOf":[
    {"type":"object","properties":{"kind":{"const":"near_base"},"radius":{"enum":[256,512,1024]}},"required":["kind","radius"],"additionalProperties":False},
    {"type":"object","properties":{"kind":{"const":"inside_border"}},"required":["kind"],"additionalProperties":False},
]}
row_common = {"rule":{"enum":["required","preferred"]},"scope":scope_schema,"importance":{"enum":[1,3,5]}}
row_rules = [{"if":{"properties":{"rule":{"const":"preferred"}}},"then":{"required":["importance"]},"else":{"not":{"required":["importance"]}}}]
row_schemas = []
for kind in ["structure_count","biome_witness"]:
    properties = {**row_common,"kind":{"const":kind}}
    required = ["rule","kind","scope"]
    if kind == "structure_count":
        properties.update(feature={"enum":["structure."+r[0] for r in structures]},at_least={"type":"integer","minimum":1,"maximum":16})
        required += ["feature","at_least"]
    else:
        properties["any_of"]={"type":"array","items":{"enum":["biome."+r[0] for r in biomes]},"minItems":1,"maxItems":9,"uniqueItems":True}
        required += ["any_of"]
    row_schemas.append({"type":"object","properties":properties,"required":required,"allOf":row_rules,"additionalProperties":False})
request_properties = {
    "request_revision":{"const":"catalog-query-v1"},"edition":{"const":"bedrock"},
    "game_build_id":{"type":"string","minLength":1},"catalog_snapshot_id":{"type":"string","minLength":1},
    "world_settings_id":{"type":"string","minLength":1},"dimension":{"const":"overworld"},
    "anchor_mode":{"enum":["origin","recommended","spawn"]},"border_side":{"enum":[2048,4096,8192]},
    "evidence_policy":{"const":"predicted_observations_v1"},
    "fallback_profile":{"enum":[r[0] for r in profile_rows]},
    "rows":{"type":"array","maxItems":12,"items":{"oneOf":row_schemas}},
}
dump("request_schema.json",{"$schema":"https://json-schema.org/draft/2020-12/schema","title":"Proposed catalog query; runtime capability and entitlement checks are additionally required", "type":"object","properties":request_properties,"required":list(request_properties),"additionalProperties":False})
dump("storage_layout.json", {
    "revision": "catalog-storage-proposed-v1", "authoritative": {
        "coordinates": "absolute signed int32 block positions; dimension always explicit",
        "structure_columns": {"feature_slot":"uint16","x":"int32","z":"int32","y":"nullable int16","variant":"nullable uint16","evidence_ref":"dictionary reference"},
        "biome_tile": {"tile_side":256,"sample_stride":64,"sample_y":63,"shape":[4,4],"axis_order":"z_then_x","dtype":"uint16_le","bytes_per_plane_tile_before_compression":32},
        "tile_coordinate": "floor(block_coordinate/256); local=block_coordinate-tile*256", "no_all_blocks_volume": True,
    }, "summary": {
        "count_scopes": ["near256","near512","near1024","inside_border"],
        "structure_counts": {"shape":[14,4],"dtype":"uint32_le","bytes":224},
        "structure_nearest_d2": {"shape":[14],"dtype":"uint32_le","bytes":56},
        "biome_nearest_d2": {"shape":[9],"dtype":"uint32_le","bytes":36},
        "biome_witness_sample_ref": {"shape":[9],"dtype":"uint32_le","bytes":36},
        "scope_complete_bits": {"features":23,"scopes":4,"bytes":12},
        "nearest_missing_sentinel":4294967295, "witness_missing_sentinel":4294967295,
        "fixed_feature_payload_bytes":364, "layout_metadata_estimate_bytes":36,
        "illustrative_layout_total_bytes":400, "estimate_is_not_sqlite_row_size_or_compression_measurement":True,
    }, "index": {
        "row_identity":"catalog_snapshot + segment_id + local_layout_row", "local_row_dtype":"uint32",
        "max_rows_per_segment":1048576,"sidecar_arrays":["world_ref","anchor_ref","role_flags","border_side","coverage_ref"],
        "bitmap_index":"feature/count-threshold/radius/role/coverage as needed; same layout row throughout intersection",
        "all_caches_include":["canonical_query","catalog_snapshot","registry_revision","observation_revision","geometry_revision","score_revision","evidence_policy"],
    }, "formats": {
        "pilot":"SQLite metadata + layout summary BLOBs and checksummed compressed observation bundles",
        "scale_candidate":"immutable partitioned Parquet/Arrow + service-owned metadata + memory-mapped column arrays/bitmaps",
        "custom_engine_candidate":"same contracts over an existing durable KV engine, or versioned immutable column segments after benchmarks",
    },
})
print("Generated six proposed contract JSON files; runtime and billing remain disabled.")
