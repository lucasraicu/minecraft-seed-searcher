"""Versioned exact V3 derivation accelerator; historical summary source stays frozen.

Configured through a source-bound derivation pin in new policy workspaces only.
"""
from .summaries import (
    canonical_biome_name, _validate_obs_v2, legacy_observation_v2, summarize,
    summarize_at, SIDES, REGISTRY_V3, SAMPLING_PROFILE_REVISION_V3,
    SAMPLING_PROFILES_V3, digest, world_id, parse_seed, anchors, contains,
    validate_summary_v3,
)

def _biome_arrays(points_by_feature):
    """One call-local integer index; never retain a mutable observation globally."""
    import numpy as np
    return {fid: np.asarray(points,dtype=np.int64) for fid,points in points_by_feature.items()
            if len(points)>64}


def _indexed_biome_summary(points, cx, cz, box, radii):
    """Exact integer distances and lexicographic XYZ ties, matching the V3 loop."""
    import numpy as np
    lo_x,hi_x,lo_z,hi_z=box
    selected=points[(points[:,0]>=lo_x)&(points[:,0]<hi_x)&
                    (points[:,2]>=lo_z)&(points[:,2]<hi_z)]
    if not len(selected):return [0,0,0,0],None,None
    d2=(selected[:,0]-cx)**2+(selected[:,2]-cz)**2
    nearest=int(d2.min());tied=selected[d2==nearest]
    index=np.lexsort((tied[:,2],tied[:,1],tied[:,0]))[0]
    witness=[int(n) for n in tied[index,:3]]
    return [int(nearest<=r*r) for r in radii]+[1],nearest,witness


def summarize_v3(obs, *, extension=None, base_summaries=None, registry=None):
    """Additive summaries preserving legacy payload and anchor modes.

    Fields same as v2 plus source_extension_id (nullable), sampling_profile_revision.
    Layout ID binds revision/base/extension/profile/registry/anchor/modes/side.
    Reuses base_summaries v2 when supplied to avoid recomputation.
    """
    _validate_obs_v2(obs)
    obs_id = digest(obs)
    w_id = world_id(obs['identity'])
    seed_str = str(parse_seed(obs['identity']['seed']))

    active_registry = registry if registry is not None else REGISTRY_V3
    active_features = active_registry['features']
    active_feature_by_id = {f['id']: f for f in active_features}
    reg_rev = digest(active_registry)

    # 1. Validate extension if provided
    source_extension_id = None
    sampling_prof_rev = SAMPLING_PROFILE_REVISION_V3
    ext_ow_biomes = []
    ext_nether_biomes = []
    ext_biome_names = {}

    if extension is not None:
        from .biome_extension import validate_extension
        validate_extension(extension,obs)
        source_extension_id=digest(extension)
        ext_ow_biomes=extension['biomes']['overworld']
        ext_biome_names=extension['biome_names']

    # 2. Preserve per-mode legacy payloads when spawn overlaps a grid coordinate.
    legacy_by_modes = {}
    if base_summaries is not None:
        anchor_rows = []
        seen_anchor_keys = set()
        legacy_by_coord_side = {}
        from .codec import validate_summary_v2
        for s in base_summaries:
            validate_summary_v2(s)
            if s['source_observation_id']!=obs_id or s['world_id']!=w_id:raise ValueError('Base summary source differs')
            for mode in ('world_spawn_estimated','world_spawn_observed'):
                if mode in s['anchor_modes'] and not any(a['mode']==mode and a['coordinate']==s['anchor'] for a in obs['anchors']):raise ValueError('Base summary spawn differs')
            coord = list(s['anchor'])
            modes = list(s['anchor_modes'])
            side = s['border_side']
            key = (coord[0], coord[1], tuple(modes))
            if key not in seen_anchor_keys:
                seen_anchor_keys.add(key)
                anchor_rows.append((coord, modes))
            legacy_by_modes[(tuple(coord), side, tuple(modes))] = s['legacy']
            legacy_by_coord_side[(tuple(coord), side)] = s['legacy']
    else:
        legacy_obs = legacy_observation_v2(obs)
        anchor_rows = []
        for coord in anchors():
            ax, az = coord
            if ax == 0 and az == 0:
                modes = ['origin', 'recommended']
            else:
                modes = ['recommended']
            anchor_rows.append(([ax, az], modes))

        seen_spawns = set()
        for a in obs.get('anchors', []):
            mode = a.get('mode')
            if mode in ('world_spawn_estimated', 'world_spawn_observed'):
                coord = [int(a['coordinate'][0]), int(a['coordinate'][1])]
                spawn_key = (coord[0], coord[1], mode)
                if spawn_key not in seen_spawns:
                    seen_spawns.add(spawn_key)
                    anchor_rows.append((coord, [mode]))

        for a in obs.get('anchors', []):
            if a.get('mode') == 'recommended' and not any(coord == a.get('coordinate') and 'recommended' in modes for coord, modes in anchor_rows):
                anchor_rows.append((list(a['coordinate']), ['recommended']))

        unique_anchor_coords = []
        seen_coords = set()
        for coord, _ in anchor_rows:
            key = (coord[0], coord[1])
            if key not in seen_coords:
                seen_coords.add(key)
                unique_anchor_coords.append(coord)

        legacy_by_coord_side = {(tuple(row['anchor']), row['border_side']): row for row in summarize(legacy_obs)}
        for coord in unique_anchor_coords:
            if (tuple(coord), SIDES[0]) in legacy_by_coord_side:
                continue
            legacy_list = summarize_at(legacy_obs, coord)
            for l_sum in legacy_list:
                legacy_by_coord_side[(tuple(coord), l_sum['border_side'])] = l_sum

    # 3. Structures
    struct_points_by_feature = {}
    for f in active_features:
        if f['kind'] == 'structure_count':
            feat_id = f['id']
            ext_key = f.get('extractor_key')
            starts = obs.get('structures', {}).get(feat_id)
            if starts is None and ext_key:
                starts = obs.get('structures', {}).get(ext_key)
            struct_points_by_feature[feat_id] = starts or []
            if feat_id in ('structure.igloo_with_basement','structure.bastion_treasure'):
                inventory=(obs.get('realm') or {}).get('inventory',{})
                key='igloo_basement' if feat_id=='structure.igloo_with_basement' else 'bastion_variant'
                entry=inventory.get(key,{})
                parent='structure.igloo' if key=='igloo_basement' else 'structure.bastion'
                parents={tuple(p) for p in obs['structures'].get(parent,[])}
                struct_points_by_feature[feat_id]=sorted({tuple(p[:2]) for p in entry.get('points',[]) if (key=='igloo_basement' or p[2]==2) and tuple(p[:2]) in parents})


    # 4. Biomes with full overlap preservation across exact, group, and legacy features
    canonical = canonical_biome_name

    name_to_features = {}
    for f in active_features:
        if f['kind'] == 'biome_witness':
            feat_id = f['id']
            members = set(f.get('canonical_members', ()))
            if feat_id.startswith('biome.exact.'):
                cname = feat_id.removeprefix('biome.exact.')
                members.add(cname)
            for atom_id in f.get('atomic_members', ()):
                if atom_id.startswith('biome.exact.'):
                    members.add(atom_id.removeprefix('biome.exact.'))
                else:
                    members.add(atom_id)
            for m in members:
                c_m = canonical(m)
                name_to_features.setdefault(c_m, set()).add(feat_id)
                name_to_features.setdefault(m, set()).add(feat_id)

    raw_biomes = obs.get('biomes', {})
    if isinstance(raw_biomes, dict):
        base_ow = raw_biomes.get('overworld', [])
        base_nether = raw_biomes.get('nether', [])
    elif isinstance(raw_biomes, list):
        base_ow = raw_biomes
        base_nether = []
    else:
        base_ow = []
        base_nether = []

    all_names = dict(obs.get('biome_names', {}))
    all_names.update(ext_biome_names)

    biome_points_by_feature = {f['id']: [] for f in active_features if f['kind'] == 'biome_witness'}

    # Process Overworld samples (base Y63 + extension samples)
    all_ow_samples = list(base_ow) + list(ext_ow_biomes)
    for idx, pt in enumerate(all_ow_samples):
        x, y, z = int(pt[0]), int(pt[1]), int(pt[2])
        raw_val = pt[3]
        bname = all_names.get(str(raw_val), str(raw_val))
        cname = canonical(bname)

        matching_fids = name_to_features.get(cname, set()) | name_to_features.get(bname, set())
        for fid in matching_fids:
            fdef = active_feature_by_id[fid]
            if fdef['dimension'] != 'overworld':
                continue
            # Legacy aliases remain v2 Y63 even when exact features multi-height
            is_legacy_alias = fid.startswith('biome.') and not fid.startswith('biome.exact.') and not fid.startswith('biome.group.')
            if is_legacy_alias:
                if y != 63:
                    continue
            else:
                eligible_y = fdef.get('eligible_y')
                if eligible_y and y not in eligible_y:
                    continue
            biome_points_by_feature[fid].append((x, y, z, idx))

    # Process Nether samples (base Y64 + extension samples)
    all_nether_samples = list(base_nether) + list(ext_nether_biomes)
    for idx, pt in enumerate(all_nether_samples):
        x, y, z = int(pt[0]), int(pt[1]), int(pt[2])
        raw_val = pt[3]
        bname = all_names.get(str(raw_val), str(raw_val))
        cname = canonical(bname)

        matching_fids = name_to_features.get(cname, set()) | name_to_features.get(bname, set())
        for fid in matching_fids:
            fdef = active_feature_by_id[fid]
            if fdef['dimension'] != 'nether':
                continue
            is_legacy_alias = fid.startswith('biome.') and not fid.startswith('biome.exact.') and not fid.startswith('biome.group.')
            if is_legacy_alias:
                if y != 64:
                    continue
            else:
                eligible_y = fdef.get('eligible_y')
                if eligible_y and y not in eligible_y:
                    continue
            biome_points_by_feature[fid].append((x, y, z, idx))

    for f in active_features:
        if f['id'].startswith('biome.group.'):
            points=set()
            for member in f['atomic_members']:
                if active_feature_by_id[member].get('available',True):
                    points.update(biome_points_by_feature[member])
            biome_points_by_feature[f['id']]=sorted(points)

    ow_radii = tuple(active_registry.get('overworld_radii', (256, 512, 1024)))
    nether_radii = tuple(active_registry.get('nether_radii', (64, 128, 256)))

    summaries_v3_list = []
    biome_arrays = _biome_arrays(biome_points_by_feature)
    for anchor, anchor_modes in anchor_rows:
        ax, az = anchor
        nether_anchor = [ax // 8, az // 8]
        nax, naz = nether_anchor

        for side in SIDES:
            ow_lo_x = ax - side // 2
            ow_hi_x = ax + side // 2
            ow_lo_z = az - side // 2
            ow_hi_z = az + side // 2

            n_lo_x = nax - 1024 // 2
            n_hi_x = nax + 1024 // 2
            n_lo_z = naz - 1024 // 2
            n_hi_z = naz + 1024 // 2

            row_features = {}
            for f in active_features:
                feat_id = f['id']
                dim = f['dimension']
                kind = f['kind']

                if dim == 'overworld':
                    cx, cz = ax, az
                    lo_x, hi_x, lo_z, hi_z = ow_lo_x, ow_hi_x, ow_lo_z, ow_hi_z
                    radii = ow_radii
                else:
                    cx, cz = nax, naz
                    lo_x, hi_x, lo_z, hi_z = n_lo_x, n_hi_x, n_lo_z, n_hi_z
                    radii = nether_radii

                r0_sq = radii[0] * radii[0]
                r1_sq = radii[1] * radii[1]
                r2_sq = radii[2] * radii[2]

                if kind == 'structure_count':
                    pts = struct_points_by_feature[feat_id]
                    c0 = c1 = c2 = cInside = 0
                    min_d2 = None
                    witness = None
                    for pt in pts:
                        x, z = int(pt[0]), int(pt[1])
                        if lo_x <= x < hi_x and lo_z <= z < hi_z:
                            d2 = (x - cx) ** 2 + (z - cz) ** 2
                            cInside += 1
                            if d2 <= r2_sq:
                                c2 += 1
                                if d2 <= r1_sq:
                                    c1 += 1
                                    if d2 <= r0_sq:
                                        c0 += 1
                            if min_d2 is None or d2 < min_d2:
                                min_d2 = d2
                                if len(pt) >= 3:
                                    witness = [int(pt[0]), int(pt[1]), int(pt[2])]
                                else:
                                    witness = [x, None, z]
                    counts = [c0, c1, c2, cInside]
                    nearest_d2 = min_d2

                    cov = obs.get('coverage', {}).get(feat_id)
                    if feat_id in ('structure.igloo_with_basement','structure.bastion_treasure'):
                        key='igloo_basement' if feat_id=='structure.igloo_with_basement' else 'bastion_variant'
                        entry=(obs.get('realm') or {}).get('inventory',{}).get(key,{})
                        parent='structure.igloo' if key=='igloo_basement' else 'structure.bastion'
                        parent_cov=obs.get('coverage',{}).get(parent,{})
                        cov=entry if entry.get('status')=='complete' and parent_cov.get('status')=='complete' else None
                    if cov and cov.get('status') == 'complete' and cov.get('bounds') and len(cov['bounds']) == 4:
                        cov_bounds = cov['bounds']
                        box3 = (lo_x, lo_z, hi_x, hi_z)
                        comp3 = contains(cov_bounds, box3)
                        box2 = (max(lo_x, cx - radii[2]), max(lo_z, cz - radii[2]),
                                min(hi_x, cx + radii[2]+1), min(hi_z, cz + radii[2]+1))
                        comp2 = contains(cov_bounds, box2)
                        box1 = (max(lo_x, cx - radii[1]), max(lo_z, cz - radii[1]),
                                min(hi_x, cx + radii[1]+1), min(hi_z, cz + radii[1]+1))
                        comp1 = contains(cov_bounds, box1)
                        box0 = (max(lo_x, cx - radii[0]), max(lo_z, cz - radii[0]),
                                min(hi_x, cx + radii[0]+1), min(hi_z, cz + radii[0]+1))
                        comp0 = contains(cov_bounds, box0)
                        complete = [comp0, comp1, comp2, comp3]
                    else:
                        complete = [False, False, False, False]

                else:
                    if feat_id in biome_arrays:
                        counts,nearest_d2,witness=_indexed_biome_summary(
                            biome_arrays[feat_id],cx,cz,(lo_x,hi_x,lo_z,hi_z),radii)
                        row_features[feat_id]=dict(dimension=dim,counts=counts,
                            complete=[False]*4,nearest_d2=nearest_d2,witness=witness)
                        continue
                    pts = biome_points_by_feature[feat_id]
                    c0 = c1 = c2 = cInside = 0
                    best_d2 = None
                    best_idx = None
                    witness = None
                    for x, y, z, idx in pts:
                        if lo_x <= x < hi_x and lo_z <= z < hi_z:
                            d2 = (x - cx) ** 2 + (z - cz) ** 2
                            cInside = 1
                            if d2 <= r2_sq:
                                c2 = 1
                                if d2 <= r1_sq:
                                    c1 = 1
                                    if d2 <= r0_sq:
                                        c0 = 1
                            if best_d2 is None or (d2,x,y,z) < (best_d2,*witness):
                                best_d2 = d2
                                best_idx = idx
                                witness = [x, y, z]
                    counts = [c0, c1, c2, cInside]
                    nearest_d2 = best_d2
                    complete = [False, False, False, False]

                row_features[feat_id] = {
                    'dimension': dim,
                    'counts': counts,
                    'complete': complete,
                    'nearest_d2': nearest_d2,
                    'witness': witness,
                }

            lid = digest([
                'catalog-summary-v3',
                obs_id,
                source_extension_id,
                sampling_prof_rev,
                reg_rev,
                list(anchor),
                list(anchor_modes),
                side
            ])
            legacy = legacy_by_modes.get((tuple(anchor), side, tuple(anchor_modes)), legacy_by_coord_side[(tuple(anchor), side)])

            summary = {
                'revision': 'catalog-summary-v3',
                'registry_revision': reg_rev,
                'source_observation_id': obs_id,
                'source_extension_id': source_extension_id,
                'sampling_profile_revision': sampling_prof_rev,
                'world_id': w_id,
                'seed': seed_str,
                'anchor': list(anchor),
                'nether_anchor': list(nether_anchor),
                'anchor_modes': list(anchor_modes),
                'border_side': side,
                'layout_id': lid,
                'features': row_features,
                'legacy': legacy,
            }
            validate_summary_v3(summary, registry=active_registry)
            summaries_v3_list.append(summary)

    return summaries_v3_list


