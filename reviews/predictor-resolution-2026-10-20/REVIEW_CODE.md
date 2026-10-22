## src/seed_search/realm/bedrock_biome_storage.py
```python
def resolve_repeated_sections(decoded: Data3D) -> Data3D:
    """Resolve Data3D 0xff previous-section markers explicitly.

    ``decode_data3d`` deliberately retains the raw marker as ``unknown`` for
    historical diagnostics. This separate operation applies the disk-format
    repeat rule, copying the *entire* previous 16³ array, not one ID or plane.
    Missing records/sections are never synthesized. A leading repeat is invalid.
    See the pinned Dragonfly reference and BDS evidence in BIOME_STORAGE_VERIFICATION.
    """
    if not isinstance(decoded, Data3D):
        raise TypeError("Expected decoded Data3D")
    sections = []
    for section in decoded.sections:
        if section.kind == "unknown":
            if not sections or sections[-1].section_y != section.section_y - 1:
                raise ValueError("Repeat marker has no previous contiguous section")
            previous = sections[-1]
            section = BiomeSection(section.section_y, previous.kind,
                                   previous.palette, previous.indices)
        sections.append(section)
    return Data3D(decoded.heightmap, tuple(sections))

```
## scripts/predictor_storage_probe.py
```python
def compare_points(export, points, *, resolve_repeats=False):
    from seed_search.realm.bedrock_biome_storage import decode_data3d, resolve_repeated_sections
    if type(resolve_repeats) is not bool:
        raise TypeError('resolve_repeats must be boolean')
    if export.get('revision') != 'stopped-biome-export-v1':
        raise ValueError('Unknown export format')
    seed = export['world_identity']['seed']
    if not isinstance(seed, str) or not re.fullmatch(r'-?\d+', seed) or not -(1 << 63) <= int(seed) < (1 << 63):
        raise ValueError('Expected exact signed-64 seed identity')
    if not isinstance(points, list) or not 1 <= len(points) <= 4096:
        raise ValueError('Point count must be 1..4096')
    cache = {}
    records = export['records']
    if not isinstance(records, list) or len(records) > 4096:
        raise ValueError('Export record-count cap')
    total = 0
    for row in records:
        if type(row['cx']) is not int or type(row['cz']) is not int:
            raise ValueError('Chunk coordinates must be integers')
        if any(not -(1 << 31) <= row[c] < (1 << 31) for c in ('cx', 'cz')):
            raise ValueError('Chunk coordinates exceed int32')
        if row['key'] != (struct.pack('<ii', row['cx'], row['cz']) + b'\x2b').hex():
            raise ValueError('Raw record key does not bind its chunk coordinates')
        if len(row['data']) > 2 << 20:
            raise ValueError('Record-size cap')
        raw = bytes.fromhex(row['data'])
        total += len(raw)
        if total > 8 << 20 or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Record size/hash mismatch')
        key = (row['cx'], row['cz'])
        if key in cache:
            raise ValueError('Duplicate chunk record')
        decoded = decode_data3d(raw)
        repeats = {s.section_y for s in decoded.sections if s.kind == 'unknown'}
        cache[key] = (resolve_repeated_sections(decoded) if resolve_repeats else decoded,
                      row['sha256'], repeats)
    results = []
    for point in points:
        if not isinstance(point, list) or len(point) != 3 or any(type(v) is not int for v in point):
            raise ValueError('Expected integer block XYZ')
        x, y, z = point
        if not -64 <= y <= 319 or max(abs(x), abs(z)) > 5120:
            raise ValueError('Point exceeds inspected bounds')
        found = cache.get((x // 16, z // 16))
        result = dict(position=point, chunk=[x // 16, z // 16],
                      local=[x % 16, y % 16, z % 16], quart=[x // 4, y // 4, z // 4],
                      stored_id=None, status='missing_data3d_record')
        if found:
            decoded, sha, repeats = found
            value = decoded.sample(x % 16, y, z % 16)
            result.update(stored_id=value, record_sha256=sha,
                          status='stored' if value is not None else 'unknown_section')
            if resolve_repeats and value is not None and y // 16 in repeats:
                result['status'] = 'stored_repeated'
        results.append(result)
    return dict(revision='stored-biome-point-diagnostics-v2' if resolve_repeats else 'stored-biome-point-diagnostics-v1', world_identity=export['world_identity'],
                namespace='bedrock_saved_world_numeric_ids_not_predictor_ids', rows=results,
                stored=sum(r['stored_id'] is not None for r in results),
                unknown=sum(r['stored_id'] is None for r in results),
                scope='Persisted data only; no inferred biome name, generation rule or structure completeness.')


```
