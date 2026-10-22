# Narrow query performance review

New lazy features are used only for checksum-bound V5 projections with the current writer-validator ID. Stale validators fully decode and validate all features. Full response feature_counts/feature_complete remain unchanged. No data/policy rewrite or cap increase. Evaluate only concrete semantic/integrity defects; rows are schema-validated at publication.


class _PackedFeatures(Mapping):
    """Decode trusted immutable feature blocks only when the query needs them."""
    def __init__(self, blocks, slots):
        self.blocks=blocks;self.slots=slots;self.decoded={}

    def __len__(self):return len(self.slots)

    def __iter__(self):return iter(self.slots)

    def __getitem__(self,key):
        if key not in self.decoded:
            index,feature=self.slots[key];block=self.blocks[index]
            if not isinstance(block,list) or len(block)!=4:raise ValueError('Invalid packed feature block')
            counts,complete,distance,witness=block
            if feature['kind']=='biome_witness':
                if type(counts)is not int or not 0<=counts<=15:raise ValueError('Invalid packed biome mask')
                counts=[int(bool(counts&(1<<i))) for i in range(4)]
            elif not isinstance(counts,list) or len(counts)!=4:raise ValueError('Invalid packed structure counts')
            if type(complete)is not int or not 0<=complete<=15:raise ValueError('Invalid packed completeness mask')
            if (witness is None)!=(distance is None):raise ValueError('Incomplete packed witness')
            self.decoded[key]=dict(dimension=feature['dimension'],counts=counts,complete=[bool(complete&(1<<i)) for i in range(4)],nearest_d2=distance,witness=witness)
        return self.decoded[key]




    def _unpack_query_rows(self,rows,entry,definition,side,mode=None,*,validate=True,lazy_features=False):
        features=definition['features'];result=[];seen=set()
        slots={f['id']:(i,f) for i,f in enumerate(features)}
        count_bits=tuple(tuple(int(bool(n&(1<<i))) for i in range(4)) for n in range(16))
        complete_bits=tuple(tuple(bool(n&(1<<i)) for i in range(4)) for n in range(16))
        for packed in rows:
            if not isinstance(packed,list) or len(packed)!=5:raise ValueError('Invalid packed query row')
            lid,anchor,modes,legacy,blocks=packed;self._sha(lid)
            if (lid in seen or not isinstance(anchor,list) or len(anchor)!=2 or any(type(n)is not int or abs(n)>30000000 for n in anchor)
                    or not isinstance(modes,list) or not modes or len(modes)!=len(set(modes)) or any(m not in ('origin','recommended','world_spawn_estimated','world_spawn_observed') for m in modes)
                    or not isinstance(legacy,dict) or not isinstance(blocks,list) or len(blocks)!=len(features)):raise ValueError('Invalid packed query scope')
            seen.add(lid)
            if mode is not None and mode not in modes:continue
            if lazy_features and not validate:
                values=_PackedFeatures(blocks,slots)
            else:
                values={}
                for feature,block in zip(features,blocks):
                    if not isinstance(block,list) or len(block)!=4:raise ValueError('Invalid packed feature block')
                    counts,complete,distance,witness=block
                    if feature['kind']=='biome_witness':
                        if type(counts)is not int or not 0<=counts<=15:raise ValueError('Invalid packed biome mask')
                        counts=list(count_bits[counts])
                    elif not isinstance(counts,list) or len(counts)!=4 or (validate and any(type(n)is not int or not 0<=n<=200000 for n in counts)):raise ValueError('Invalid packed structure counts')
                    if type(complete)is not int or not 0<=complete<=15:raise ValueError('Invalid packed completeness mask')
                    complete=list(complete_bits[complete])
                    if validate and distance is not None and (type(distance)is not int or not 0<=distance<=2*(60000000**2)):raise ValueError('Invalid packed distance')
                    if validate and witness is not None and (not isinstance(witness,list) or len(witness)!=3 or any(type(witness[i])is not int or abs(witness[i])>30000000 for i in (0,2)) or (witness[1] is not None and (type(witness[1])is not int or not -64<=witness[1]<=319))):raise ValueError('Invalid packed XYZ witness')
                    if (witness is None)!=(distance is None):raise ValueError('Incomplete packed witness')
                    values[feature['id']]=dict(dimension=feature['dimension'],counts=counts,complete=complete,nearest_d2=distance,witness=witness)
            result.append(dict(revision='catalog-summary-v3',registry_revision=entry['registry_revision'],
                source_observation_id=entry['observation_id'],source_extension_id=entry['source_extension_id'],
                sampling_profile_revision=entry['sampling_profile_revision'],world_id=entry['world_id'],seed=entry['identity']['seed'],
                anchor=anchor,nether_anchor=[n//8 for n in anchor],anchor_modes=modes,border_side=side,layout_id=lid,features=values,legacy=legacy))
        return result

    def _projection(self,entry,side,mode=None,*,lazy_features=False):
        """The immutable snapshot binds this derived view to its verified raw bundle."""
        value=self.artifacts.get_json(entry['summary_artifacts'][str(side)])
        fields={'revision','world_id','identity','observation_id','bundle_sha256','border_side','rows'}
        if (not isinstance(value,dict) or
                (value.get('revision'),frozenset(value)) not in (
                    ('catalog-query-projection-v2',frozenset(fields)),
                    ('catalog-query-projection-v3',frozenset(fields|{'summary_validator_sha256','row_count'})),
                    ('catalog-query-projection-v4',frozenset(fields|{'summary_validator_sha256','row_count','registry','sampling_profile_revision','source_extension_id'})),
                    ('catalog-query-projection-v5',frozenset(fields|{'summary_validator_sha256','row_count','registry','sampling_profile_revision','source_extension_id'})))
                or any(value[k]!=entry[k] for k in ('world_id','identity','observation_id'))
                or value['bundle_sha256']!=entry['artifact']['sha256'] or value['border_side']!=side
                or not isinstance(value['rows'],list) or len(value['rows'])>1024):raise ValueError('Invalid query projection binding')
        v3=value['revision'] in ('catalog-query-projection-v4','catalog-query-projection-v5')
        current=value['revision'] in ('catalog-query-projection-v3','catalog-query-projection-v4','catalog-query-projection-v5')
        if v3 and (registry.digest(value['registry'])!=entry['registry_revision'] or any(value[k]!=entry[k] for k in ('sampling_profile_revision','source_extension_id'))):raise ValueError('Projected v3evidence differs')
        if current:
            self._sha(value['summary_validator_sha256'])
            if type(value['row_count']) is not int or value['row_count']!=len(value['rows']):raise ValueError('Projection row count mismatch')
        trusted=current and value['summary_validator_sha256']==self._query_validator_id()
        if value['revision']=='catalog-query-projection-v5':
            value=dict(value,rows=self._unpack_query_rows(value['rows'],entry,value['registry'],side,mode,validate=not trusted,lazy_features=lazy_features))
        seen=set()
        for row in value['rows']:
            if (not isinstance(row,dict) or row.get('world_id')!=entry['world_id'] or row.get('source_observation_id')!=entry['observation_id']
                    or row.get('seed')!=entry['identity']['seed'] or row.get('border_side')!=side
                    or row.get('layout_id') in seen):raise ValueError('Invalid projected summary source')
            seen.add(row['layout_id'])
            if not trusted:
                if v3:
                    from .codec import validate_summary_v3
                    validate_summary_v3(row,registry=value['registry'])
                else:
                    from .codec import validate_summary_v2
                    validate_summary_v2(row)
        return value['rows']

    def iter_query_summaries(self,manifest,side,mode,*,lazy_features=False):
        """Read only the requested border; old immutable snapshots use their bundles."""
        for entry in manifest['worlds']:
            rows=self._projection(entry,side,mode,lazy_features=lazy_features) if 'summary_artifacts' in entry else self._bundle(self.artifacts.get_json(entry['artifact']),entry)['summaries']
            for row in rows:
                if row['border_side']==side and mode in row['anchor_modes']:
                    # Current projections are exact views of fully validated writer
                    # input, bound by validator revision and the immutable CAS root.
                    yield row



def _rank_features(summaries, req, limit=1000, *, keep_keys=False, registry=None):
    if type(limit) is not int or limit < 1:
        raise ValueError('Limit must be a positive integer')

    active_registry = registry if registry is not None else REGISTRY_V2
    feature_by_id = {f['id']: f for f in active_registry['features']}
    ow_radii_map = {r: i for i, r in enumerate(active_registry.get('overworld_radii', (256, 512, 1024)))}
    nether_radii_map = {r: i for i, r in enumerate(active_registry.get('nether_radii', (64, 128, 256)))}

    req_side = req['border_side']
    req_mode = req['anchor_mode']

    required_rows = [r for r in req['rows'] if r['rule'] == 'required']
    preferred_rows = [r for r in req['rows'] if r['rule'] == 'preferred']

    best_matches_by_world = {}
    best_pending_by_world = {}

    for summary in summaries:
        if summary.get('border_side') != req_side:
            continue
        if req_mode not in summary.get('anchor_modes', []):
            continue

        # Evaluate Required rows: ALL must pass on this same summary
        has_failed_required = False
        has_pending_required = False
        pending_reasons = []

        for r in required_rows:
            scope_kind = r['scope']['kind']
            if r['kind'] == 'structure_count':
                feat_id = r['feature']
                dim = feature_by_id[feat_id]['dimension']
                scope_idx = 3 if scope_kind == 'inside_border' else (
                    ow_radii_map[r['scope']['radius']] if dim == 'overworld' else nether_radii_map[r['scope']['radius']]
                )
                feat_data = summary['features'][feat_id]
                count = feat_data['counts'][scope_idx]
                comp = feat_data['complete'][scope_idx]
                at_least = r['at_least']
                if count >= at_least:
                    pass
                else:
                    if comp:
                        has_failed_required = True
                        break
                    else:
                        has_pending_required = True
                        pending_reasons.append(f"{feat_id} count {count} < {at_least} (incomplete)")
            elif r['kind'] == 'biome_witness':
                any_of = r['any_of']
                dim = feature_by_id[any_of[0]]['dimension']
                scope_idx = 3 if scope_kind == 'inside_border' else (
                    ow_radii_map[r['scope']['radius']] if dim == 'overworld' else nether_radii_map[r['scope']['radius']]
                )
                has_witness = False
                for b_id in any_of:
                    if summary['features'][b_id]['counts'][scope_idx] > 0:
                        has_witness = True
                        break
                if has_witness:
                    pass
                else:
                    has_pending_required = True
                    pending_reasons.append(f"biome witness missing for {any_of}")

        if has_failed_required:
            continue

        # Distance tie calculation across ALL selected rows in request
        distance_tie = 0
        for r in req['rows']:
            scope_kind = r['scope']['kind']
            if r['kind'] == 'structure_count':
                feat_id = r['feature']
                dim = feature_by_id[feat_id]['dimension']
                scope_idx = 3 if scope_kind == 'inside_border' else (
                    ow_radii_map[r['scope']['radius']] if dim == 'overworld' else nether_radii_map[r['scope']['radius']]
                )
                normalizer = (req_side // 2 if dim == 'overworld' else 512) if scope_kind == 'inside_border' else r['scope']['radius']
                feat_data = summary['features'][feat_id]
                count = feat_data['counts'][scope_idx]
                d2 = feat_data['nearest_d2']
                radius = r['scope']['radius'] if scope_kind == 'near_base' else None
                r2 = radius ** 2 if radius is not None else None
                if count == 0 or d2 is None or (r2 is not None and d2 > r2):
                    term = 1_000_000
                else:
                    term = min(math.isqrt(d2 * 10**12) // normalizer, 1_000_000)
                distance_tie += term
            elif r['kind'] == 'biome_witness':
                any_of = r['any_of']
                dim = feature_by_id[any_of[0]]['dimension']
                scope_idx = 3 if scope_kind == 'inside_border' else (
                    ow_radii_map[r['scope']['radius']] if dim == 'overworld' else nether_radii_map[r['scope']['radius']]
                )
                normalizer = (req_side // 2 if dim == 'overworld' else 512) if scope_kind == 'inside_border' else r['scope']['radius']
                radius = r['scope']['radius'] if scope_kind == 'near_base' else None
                r2 = radius ** 2 if radius is not None else None
                min_d2 = None
                for b_id in any_of:
                    b_data = summary['features'][b_id]
                    if b_data['counts'][scope_idx] > 0 and b_data['nearest_d2'] is not None:
                        d2 = b_data['nearest_d2']
                        if r2 is None or d2 <= r2:
                            if min_d2 is None or d2 < min_d2:
                                min_d2 = d2
                if min_d2 is None:
                    term = 1_000_000
                else:
                    term = min(math.isqrt(min_d2 * 10**12) // normalizer, 1_000_000)
                distance_tie += term

        # Utility scoring
        if preferred_rows:
            total_units = 0
            max_units = 0
            contributions = []
            for r in preferred_rows:
                w = r['importance']
                max_units += w * LCM
                scope_kind = r['scope']['kind']
                if r['kind'] == 'structure_count':
                    feat_id = r['feature']
                    dim = feature_by_id[feat_id]['dimension']
                    scope_idx = 3 if scope_kind == 'inside_border' else (
                        ow_radii_map[r['scope']['radius']] if dim == 'overworld' else nether_radii_map[r['scope']['radius']]
                    )
                    feat_data = summary['features'][feat_id]
                    count = feat_data['counts'][scope_idx]
                    comp = feat_data['complete'][scope_idx]
                    at_least = r['at_least']
                    frac_num = min(count, at_least)
                    units = w * (frac_num * LCM // at_least)
                    status = 'known' if comp else 'unknown'
                    contributions.append({
                        'feature': feat_id,
                        'rule': 'preferred',
                        'kind': 'structure_count',
                        'count': count,
                        'at_least': at_least,
                        'importance': w,
                        'utility_units': units,
                        'max_units': w * LCM,
                        'complete': comp,
                        'status': status,
                        'positive_witness': count > 0,
                    })
                    total_units += units
                elif r['kind'] == 'biome_witness':
                    any_of = r['any_of']
                    dim = feature_by_id[any_of[0]]['dimension']
                    scope_idx = 3 if scope_kind == 'inside_border' else (
                        ow_radii_map[r['scope']['radius']] if dim == 'overworld' else nether_radii_map[r['scope']['radius']]
                    )
                    witness_found = False
                    witness_b_id = None
                    for b_id in any_of:
                        b_data = summary['features'][b_id]
                        if b_data['counts'][scope_idx] > 0:
                            witness_found = True
                            witness_b_id = b_id
                            break
                    if witness_found:
                        units = w * LCM
                        status = 'known'
                    else:
                        units = 0
                        status = 'unknown'
                    contributions.append({
                        'any_of': any_of,
                        'rule': 'preferred',
                        'kind': 'biome_witness',
                        'witness_found': witness_found,
                        'witness_feature': witness_b_id,
                        'importance': w,
                        'utility_units': units,
                        'max_units': w * LCM,
                        'complete': False,
                        'status': status,
                        'positive_witness': witness_found,
                    })
                    total_units += units
            score = (total_units * 100.0) / max_units if max_units > 0 else 0.0
        else:
            profile_id = req['fallback_profile']
            legacy = summary.get('legacy', {})
            total_units, max_units, _ = scoring.profile_units(legacy, profile_id)
            score = float(total_units * 100 / max_units) if max_units > 0 else 0.0

            coefficients = PROFILES[profile_id]
            counts = [row[2] for row in legacy.get('counts', [])]
            known = [all(legacy.get('complete', [])[slot][2] for slot in group) for group in scoring.GROUPS] if 'complete' in legacy else [False] * len(scoring.GROUPS)
            n_biomes = sum(d != MISSING and d <= 1024**2 for d in legacy.get('biome_nearest_d2', []))
            units = [
                min(counts[0], 6) * (LCM // 6) if len(counts) > 0 else 0,
                min(counts[1], 4) * (LCM // 4) if len(counts) > 1 else 0,
                min(counts[2], 2) * (LCM // 2) if len(counts) > 2 else 0,
                min(counts[4] + counts[12], 6) * (LCM // 6) if len(counts) > 12 else 0,
                sum(n > 0 for n in counts) * (LCM // 14) if counts else 0,
                min(n_biomes, 8) * (LCM // 8),
                0,
                min(sum(counts[i] for i in (7, 8, 9, 10)), 4) * (LCM // 4) if len(counts) > 10 else 0,
            ]
            if counts and counts[0] and legacy.get('structure_nearest_d2', [MISSING])[0] != MISSING:
                with localcontext() as context:
                    context.prec = 50
                    units[6] = max(Decimal(0), 1 - Decimal(legacy['structure_nearest_d2'][0]).sqrt() / 1024) * LCM
            feature_units = [u if k else 0 for u, k in zip(units, known)]
            contributions = [
                {
                    'feature': k,
                    'coefficient': c,
                    'utility_units': float(u),
                    'max_units': LCM,
                    'status': 'known' if complete_flag else 'unknown',
                }
                for k, c, u, complete_flag in zip('VTAOEBHR', coefficients, feature_units, known)
            ]

        unsigned_seed = int(summary['seed']) & ((1 << 64) - 1)
        sort_key = (
            -total_units,
            distance_tie,
            unsigned_seed,
            summary['anchor'][0],
            summary['anchor'][1],
            summary['layout_id'],
        )

        # Build complete display data only for a new best anchor.  All required
        # and preferred tests and exact sort keys have already been evaluated.
        wid=summary['world_id']
        destination=best_pending_by_world if has_pending_required else best_matches_by_world
        if wid in destination and sort_key>=destination[wid]['_sort_key']:
            continue

        legacy = summary.get('legacy', {})
        feature_counts = {fid: fdata['counts'] for fid, fdata in summary.get('features', {}).items()}
        feature_complete = {fid: fdata['complete'] for fid, fdata in summary.get('features', {}).items()}
        nether_anchor = list(summary.get('nether_anchor', [summary['anchor'][0] // 8, summary['anchor'][1] // 8]))

        candidate = {
            'world_id': summary['world_id'],
            'seed': summary['seed'],
            'layout_id': summary['layout_id'],
            'anchor': list(summary['anchor']),
            'nether_anchor': nether_anchor,
            'border_side': summary['border_side'],
            'border': summary['border_side'],
            'bounds': list(bounds_for(summary['anchor'], summary['border_side'])),
            'score': score,
            'utility_units': int(total_units),
            'distance_tie': distance_tie,
            'contributions': contributions,
            'counts': legacy.get('counts'),
            'structure_nearest_d2': legacy.get('structure_nearest_d2'),
            'biome_nearest_d2': legacy.get('biome_nearest_d2'),
            'complete': legacy.get('complete'),
            'feature_counts': feature_counts,
            'feature_complete': feature_complete,
            '_sort_key': sort_key,
        }
        if 'biome_witness_refs' in legacy:
            candidate['biome_witness_refs'] = legacy['biome_witness_refs']

        wid = summary['world_id']
        if not has_pending_required:
            if wid not in best_matches_by_world or sort_key < best_matches_by_world[wid]['_sort_key']:
                best_matches_by_world[wid] = candidate
        else:
            candidate['status'] = 'pending'
            candidate['reason'] = '; '.join(pending_reasons)
            candidate['reasons'] = pending_reasons
            if wid not in best_pending_by_world or sort_key < best_pending_by_world[wid]['_sort_key']:
                best_pending_by_world[wid] = candidate

    matched_worlds = len(best_matches_by_world)
    ranked_matches = sorted(best_matches_by_world.values(), key=lambda c: c['_sort_key'])
    results = ranked_matches[:limit]

    unresolved_by_world = {
        wid: cand for wid, cand in best_pending_by_world.items()
        if wid not in best_matches_by_world
    }
    unresolved_candidates = sorted(unresolved_by_world.values(), key=lambda c: c['_sort_key'])[:limit]

    if not keep_keys:
        for r in results:
            r.pop('_sort_key', None)
        for u in unresolved_candidates:
            u.pop('_sort_key', None)

    return {
        'results': results,
        'unresolved_candidates': unresolved_candidates,
        'matched_worlds': matched_worlds,
        'unresolved_worlds': len(unresolved_by_world),
    }


