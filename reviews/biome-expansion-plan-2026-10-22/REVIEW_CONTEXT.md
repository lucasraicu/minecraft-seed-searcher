# Actual-source evidence for independent plan critique
Read-only supplied excerpts, not an implementation instruction. No game runs or source changes have occurred. Existing code has 31 public features: 17 structures, nine OW biome groups and five Nether biome types. Model inventory has 56 active OW canonical IDs plus five Nether IDs; shipped assets include legacy aliases. Registry name completeness is not accuracy.
Current public backend is idle and serves 222 worlds. Primary workspace has 182+ inherited dirty paths. Personal process is separate. Byte-immutable old root is retained. Existing query deadline 10s, latest nine local cases 5.80–6.81s; this is not throughput proof. Two query workers. Existing object/projection size caps apply.
Current Realm auxiliary inventories contain predicted igloo basement coordinates and bastion variants; not publicly selectable. No independent universal variant accuracy certificate exists. Legacy packed codecs are frozen, and current summaries/projectors need version-aware feature handling.

## summaries.py actual overlap and Y handling
```python
    # 2. Group feature points once outside anchor loop
    canonical_to_feature_id = {
        member: f['id']
        for f in FEATURES_V2
        if f['kind'] == 'biome_witness'
        for member in f.get('canonical_members', ())
    }

    struct_points_by_feature = {}
    for f in FEATURES_V2:
        if f['kind'] == 'structure_count':
            feat_id = f['id']
            starts = obs.get('structures', {}).get(feat_id, [])
            struct_points_by_feature[feat_id] = starts

    raw_biomes = obs.get('biomes', {})
    if isinstance(raw_biomes, dict):
        ow_biome_samples = raw_biomes.get('overworld', [])
        nether_biome_samples = raw_biomes.get('nether', [])
    elif isinstance(raw_biomes, list):
        ow_biome_samples = raw_biomes
        nether_biome_samples = []
    else:
        ow_biome_samples = []
        nether_biome_samples = []

    biome_names = obs.get('biome_names', {})
    biome_points_by_feature = {f['id']: [] for f in FEATURES_V2 if f['kind'] == 'biome_witness'}

    # Overworld biomes: Y63 only
    for idx, pt in enumerate(ow_biome_samples):
        x, y, z, raw_id = int(pt[0]), int(pt[1]), int(pt[2]), int(pt[3])
        if y == 63:
            bname = biome_names.get(str(raw_id))
            if bname in canonical_to_feature_id:
                target_feat = canonical_to_feature_id[bname]
                biome_points_by_feature[target_feat].append((x, y, z, idx))

    # Nether biomes: Y64 only
    for idx, pt in enumerate(nether_biome_samples):
        x, y, z, raw_id = int(pt[0]), int(pt[1]), int(pt[2]), int(pt[3])
        if y == 64:
            bname = biome_names.get(str(raw_id))
            if bname in canonical_to_feature_id:
                target_feat = canonical_to_feature_id[bname]
                biome_points_by_feature[target_feat].append((x, y, z, idx))

```

## retention.py actual capacities
```python
def automation_objectives():
    """Registered finite objective set; never enumerate arbitrary query subsets."""
    from .products import launch_definitions
    values={oid:DEFAULT_CAPACITIES[oid.split(':',1)[0]] for oid in ALL_OBJECTIVE_IDS}
    for mode in MODES:
        for side in SIDES:
            for scope in range(4):values[f'v2.count:structure.stronghold:{scope}:{side}:{mode}']=100
            values[f'v2.near:structure.stronghold:{side}:{mode}']=100
        for feature in ('structure.fortress','structure.bastion'):
            for scope in range(4):values[f'v2.count:{feature}:{scope}:{mode}']=100
            values[f'v2.near:{feature}:{mode}']=100
        for biome in ('nether_wastes','crimson_forest','warped_forest','soul_sand_valley','basalt_deltas'):
            values[f'v2.near:biome.{biome}:{mode}']=100
    products=launch_definitions()
    for p in [products['realm'],*products.get('realm_sizes',[]),*products['presets'],*products['records']]:values[p['id']]=p['capacity']
    assert len(values)==7027 and sum(values.values())==105644
    return values

```

## Other actual facts
extract.py surveys OW Y63 and Nether Y64 at stride64; each sample is stored [x,y,z,biome_id] with name mapping. It marks structure.stronghold partial. Existing validators restrict feature IDs to registry; new contracts require old readers to remain frozen. Existing raw biome samples can contain additional heights from Realm logic; points must be validated for compatible provider/source/settings before reuse. Unknown samples do not prove absence.
Variants must remain predicted, same-anchor and dimension-aware. The 1024-square Nether border is independent of OW side. Existing policy revision hashes registry/source/calibration; changing modules invalidates policy and needs staged migration. Plan's 25% cost ceiling is proposed, not measured. Max world budget 120s and existing600s allocation apply.
