"""Fixed-border Coastal Continent sampling model, independent of island geometry.

Cells carry sampled evidence, never a claim that every intervening block was
observed. A contiguous boundary-sector strip implements the blueprint edge-or-sector
wording with an explicit minimum length; a tiny boundary patch cannot pass.
"""
from __future__ import annotations

import time
import numpy as np
from scipy import ndimage
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import breadth_first_order, dijkstra

COASTAL = dict(land_fraction_min=.75, land_fraction_max=.85,
               ocean_edge_min_width_blocks=250, ocean_edge_fraction_min=.5,
               ocean_edge_preferred_max_width_blocks=400,
               monument_envelope_half_size_blocks=80)


def coastal_mode(cfg):
    return ((cfg.get('terrain') or {}).get('v1') or {}).get('mode') == 'coastal_continent'


def monument_inputs(candidate):
    inventory = (candidate.get('required_structures') or {}).get('monument') or {}
    return inventory.get('footprints', inventory.get('coordinates', inventory.get('predicted_viable', [])))


def _overlap(raster, bounds):
    """Cell areas clipped to the requested half-open box, including partial cells."""
    x0, z0, x1, z1 = raster.bounds
    xx = x0 + np.arange(raster.shape[1])*raster.resolution
    zz = z0 + np.arange(raster.shape[0])*raster.resolution
    widths = np.maximum(0, np.minimum(np.minimum(xx+raster.resolution, x1), bounds[2])-np.maximum(xx, bounds[0]))
    depths = np.maximum(0, np.minimum(np.minimum(zz+raster.resolution, z1), bounds[3])-np.maximum(zz, bounds[1]))
    return depths[:, None]*widths[None, :]


def _biome_water_mask(raster, names):
    from .biomes import canonical
    metadata = raster.metadata
    if metadata.get('source') == 'actual' and 'surface_biome_observations' in metadata:
        ocean = np.zeros(raster.shape, dtype=bool)
        observed = {}
        conflicts = set()
        for row in metadata['surface_biome_observations']:
            if row.get('status') != 'OBSERVED' or not row.get('name'):
                continue
            x, z = row.get('x'), row.get('z')
            if not isinstance(x, int) or not isinstance(z, int):
                continue
            index = raster.index((x,z))
            if index is None or (x-raster.bounds[0])%raster.resolution or (z-raster.bounds[1])%raster.resolution:
                continue
            name = canonical(row['name'])
            if index in observed and observed[index] != name:
                conflicts.add(index)
            observed[index] = name
        for index, name in observed.items():
            ocean[index] = name in names and index not in conflicts
        proven = (metadata.get('surface_biome_evidence') == 'actual_api_string_names'
                  and metadata.get('stable_sampled_observations') is True
                  and len(observed) == raster.height.size and not conflicts)
        return raster.water_mask() & ocean, bool(observed), proven
    if raster.biomes is None:
        return np.zeros(raster.shape, dtype=bool), False, False
    from ..backend import biome_name
    ids = [int(value) for value in np.unique(raster.biomes) if biome_name(int(value)) in names]
    # Numeric IDs supplied alongside actual blocks can still be predictions.
    proven = (metadata.get('source') == 'actual' and metadata.get('biome_evidence') == 'actual_generated'
              and metadata.get('biome_mapping_version') == metadata.get('target_version', '26.52'))
    return raster.water_mask() & np.isin(raster.biomes, ids), True, proven


def _ocean_mask(raster):
    from .biomes import FAMILIES
    return _biome_water_mask(raster, FAMILIES['ocean'])


def _freshwater_masks(raster, inside, land, ocean):
    """Positive river witnesses and enclosed non-ocean water; unknowns never bridge."""
    from ..backend import biome_catalog
    from .biomes import FAMILIES
    river, _, _ = _biome_water_mask(raster, {'river','frozen_river'})
    open_river, _, _ = _biome_water_mask(raster, {'river'})
    non_ocean, _, _ = _biome_water_mask(raster, {r['name'] for r in biome_catalog()}-FAMILIES['ocean'])
    river &= inside & raster.known
    open_river &= river
    # Land/river enclosure is geographic, not a claim of a traversable bridge.
    enclosed = ndimage.binary_fill_holes(land | river)
    lake_labels, n = ndimage.label(non_ocean & inside & raster.known & ~river & ~ocean)
    forbidden = ~enclosed | ndimage.binary_dilation(~raster.known & inside)
    bad = np.unique(lake_labels[forbidden])
    good = np.setdiff1d(np.arange(1,n+1),bad)
    lakes = np.isin(lake_labels,good)
    return river | lakes, river, open_river, lakes


def _corridor_components(mask, raster, stronghold, coastal_water, minimum, hub_radius, *, river_witnesses=None):
    """Face-connected sampled paths with a conservative geodesic length witness.

    Two breadth-first sweeps give a diameter lower bound, not cell-count length
    or a bounding-box estimate. These samples do not prove boat clearance/depth.
    """
    labels, count = ndimage.label(mask)
    witnessed = None if river_witnesses is None else set(np.unique(labels[river_witnesses]))-{0}
    touching = np.unique(labels[ndimage.binary_dilation(coastal_water) & mask])
    reports = []
    for ident, slices in enumerate(ndimage.find_objects(labels),1):
        if slices is None:continue
        if witnessed is not None and ident not in witnessed:continue
        component = labels[slices]==ident
        rr,cc = np.nonzero(component)
        # Sparse face graph, with up/down/left/right adjacency order matching
        # the independent queue oracle. Only two single-source traversals and
        # one distance vector are allocated; never an N-by-N distance matrix.
        index=np.full((component.shape[0]+2,component.shape[1]+2),-1,dtype=np.int32)
        index[rr+1,cc+1]=np.arange(len(rr),dtype=np.int32)
        neighbors=np.column_stack((index[rr,cc+1],index[rr+2,cc+1],index[rr+1,cc],index[rr+1,cc+2]))
        valid=neighbors>=0
        indptr=np.empty(len(rr)+1,dtype=np.int32);indptr[0]=0
        np.cumsum(valid.sum(axis=1),out=indptr[1:])
        indices=neighbors[valid]
        graph=csr_matrix((np.ones(len(indices)),indices,indptr),shape=(len(rr),len(rr)))
        end_index=int(breadth_first_order(graph,0,directed=True,return_predecessors=False)[-1])
        other_index=int(breadth_first_order(graph,end_index,directed=True,return_predecessors=False)[-1])
        distances=dijkstra(graph,directed=True,indices=end_index,unweighted=True)
        steps=int(distances[other_index])
        end=(int(rr[end_index]),int(cc[end_index]));other=(int(rr[other_index]),int(cc[other_index]))
        length = steps*raster.resolution
        rows,cols = rr+slices[0].start,cc+slices[1].start
        xs = raster.bounds[0]+cols*raster.resolution
        zs = raster.bounds[1]+rows*raster.resolution
        distance = float(np.sqrt(np.min((xs-stronghold[0])**2+(zs-stronghold[1])**2)))
        endpoints = [[int(raster.bounds[0]+(point[1]+slices[1].start)*raster.resolution),
                      int(raster.bounds[1]+(point[0]+slices[0].start)*raster.resolution)] for point in (end,other)]
        reports.append(dict(component_id=ident,sampled_cells=len(rr),length_lower_bound_blocks=length,
                            minimum_length_model_pass=bool(length>=minimum),
                            hub_distance_blocks=distance,within_hub_radius=bool(distance<=hub_radius),
                            touches_coastal_ocean=bool(ident in touching),path_endpoints=endpoints))
    return reports


def _coastal_line_ids(lines, masks):
    """Common nonzero ocean label for every selected cell in each strip line."""
    columns=np.flatnonzero(masks.any(axis=0))
    if not len(columns):return np.zeros(len(lines),dtype=lines.dtype)
    values=lines[:,columns];selected=masks[:,columns]
    low=np.min(values,axis=1,where=selected,initial=np.iinfo(lines.dtype).max)
    high=np.max(values,axis=1,where=selected,initial=0)
    return np.where((low==high)&(low>0),low,0)


def evaluate_coastal(raster, center=None, bounds=None, stronghold=(0, 0), *, thresholds=None,
                     monuments=(), rays=32, biome_fit=0., baseline_quality=0., require_monument=True):
    """Evaluate one configured Stronghold-centered square; expose model and actual evidence separately.

    Predicted monument starts receive a deliberately broad configurable envelope.
    Its sampled coastal-water coverage is a model screen only. Physical monument
    containment requires an explicit generated structure footprint in addition to
    complete block-resolution water, natural-ground and ocean-biome evidence.
    """
    from .terrain import _finish, apply_score_policy
    started = time.perf_counter()
    values = thresholds or {}
    p = {**COASTAL, **(values.get('coastal_continent') or values)}
    side=values.get('square_side_blocks',1536)
    if side not in (1536,2048):raise ValueError('Unsupported coastal square')
    sx, sz = stronghold;half=side//2
    expected = (sx-half, sz-half, sx+half, sz+half)
    bounds = tuple(bounds or expected)
    if bounds != expected:
        raise ValueError(f'Coastal Continent requires the exact Stronghold-centered {side} square')
    area = _overlap(raster, bounds)
    inside = area > 0
    total = side**2
    covered = float(area.sum()) == total
    known = raster.known & inside
    water = raster.water_mask() & inside
    land = known & ~water
    ocean, biome_available, actual_biomes = _ocean_mask(raster)
    ocean &= inside
    freshwater=river=open_river=lakes=np.zeros(raster.shape,bool)
    river_enabled='river_corridor_min_length_blocks' in p
    if river_enabled:freshwater,river,open_river,lakes=_freshwater_masks(raster,inside,land,ocean)
    connectivity=p.get('land_connectivity',4)
    structure=np.ones((3,3),dtype=bool) if connectivity==8 else ndimage.generate_binary_structure(2,1)
    labels, count = ndimage.label(land | (freshwater if p.get('bridge_inland_freshwater') else False),structure=structure)
    sizes = np.bincount(labels.ravel(), weights=(area*land).ravel(), minlength=count+1)
    sizes[0] = 0
    main_id = int(sizes.argmax())
    if river_enabled:
        # An offshore island's river cannot satisfy the mainland waterway gate.
        # Keep bridges for labeling, then qualify only the primary landmass.
        freshwater &= labels==main_id
        river &= freshwater;open_river &= freshwater;lakes &= freshwater
    main_fraction = float(sizes[main_id]/total)
    known_fraction = float(area[known].sum()/total)
    land_fraction = float(area[land].sum()/total)
    land_done = time.perf_counter()
    ocean_labels, _ = ndimage.label(ocean)
    width = p['ocean_edge_min_width_blocks']
    x0, z0, x1, z1 = bounds
    strips = {'west': (x0,z0,x0+width,z1), 'east': (x1-width,z0,x1,z1),
              'north': (x0,z0,x1,z0+width), 'south': (x0,z1-width,x1,z1)}
    accepted = []
    coast_ids = set()
    sectors = []
    for edge, box in strips.items():
        if edge in ('west','east') and not raster.bounds[0] <= box[0] < box[2] <= raster.bounds[2]:
            continue
        if edge in ('north','south') and not raster.bounds[1] <= box[1] < box[3] <= raster.bounds[3]:
            continue
        strip_area = _overlap(raster, box)
        mask = strip_area > 0
        # Scan tangent cell runs. Every cell across the minimum inward width
        # must belong to the same ocean component; unknowns break the run.
        tangent_rows = edge in ('west', 'east')
        lines = ocean_labels if tangent_rows else ocean_labels.T
        masks = mask if tangent_rows else mask.T
        lengths = strip_area.sum(axis=1 if tangent_rows else 0)/width
        best = run = 0.
        prior = 0
        for ident, length in zip(_coastal_line_ids(lines,masks), lengths):
            ident=int(ident)
            run = (run if ident == prior else 0.) + float(length) if ident else 0.
            prior = ident
            best = max(best, run)
            if run >= side*p['ocean_edge_fraction_min']:
                coast_ids.add(ident)
        if best >= side*p['ocean_edge_fraction_min']:
            accepted.append(edge)
            sectors.append(dict(edge=edge, contiguous_length_blocks=best, minimum_width_blocks=width))
    coastal_water = np.isin(ocean_labels, list(coast_ids)) if coast_ids else np.zeros(raster.shape, bool)
    river_metrics={}
    if river_enabled:
        minimum=p['river_corridor_min_length_blocks'];hub=p['river_highway_hub_radius_blocks']
        corridors=_corridor_components(freshwater,raster,stronghold,coastal_water,minimum,hub,river_witnesses=river)
        # Lakes can join a river route; frozen river cells cannot supply an open
        # water highway. A lake without a river witness never satisfies the gate.
        open_freshwater=freshwater & ~(river & ~open_river)
        open_corridors=corridors if np.array_equal(freshwater,open_freshwater) else _corridor_components(
            open_freshwater,raster,stronghold,coastal_water,minimum,hub,river_witnesses=open_river)
        river_metrics=dict(inland_freshwater_area=float(area[freshwater].sum()),
                           inland_lake_area=float(area[lakes].sum()),river_area=float(area[river].sum()),
                           river_components=corridors,river_corridor_min_length_blocks=minimum,
                           river_corridor_model_pass=any(c['minimum_length_model_pass'] for c in corridors),
                           river_highway_hub_radius_blocks=hub,river_highway_bonus_points=p['river_highway_bonus_points'],
                           river_highway_connected=any(c['minimum_length_model_pass'] and c['within_hub_radius'] and c['touches_coastal_ocean'] for c in open_corridors),
                           river_highway_components=open_corridors,
                           river_evidence='sampled water/biome connectivity; depth, clearance, ice and unsampled continuity unverified',
                           river_navigability_verified=False)
    coast_done = time.perf_counter()
    reports = []
    for monument in monuments or ():
        explicit = isinstance(monument, dict) and monument.get('footprint') is not None
        if explicit:
            footprint = list(monument['footprint'])
            position = monument.get('position')
            actual_extent = monument.get('footprint_evidence') == 'actual_structure_bounds'
        else:
            position = monument.get('position', monument.get('coordinates')) if isinstance(monument, dict) else monument
            if position is None or len(position) != 2:
                continue
            mx, mz = position
            radius = p['monument_envelope_half_size_blocks']
            footprint = [mx-radius, mz-radius, mx+radius, mz+radius]
            actual_extent = False
        if len(footprint) != 4 or not all(isinstance(v, (int, float)) and np.isfinite(v) for v in footprint) or footprint[0] >= footprint[2] or footprint[1] >= footprint[3]:
            raise ValueError('Monument footprint must be a finite nonempty half-open rectangle')
        fits = x0 <= footprint[0] and z0 <= footprint[1] and footprint[2] <= x1 and footprint[3] <= z1
        overlap = _overlap(raster, footprint)
        expected_area = (footprint[2]-footprint[0])*(footprint[3]-footprint[1])
        footprint_known = float(overlap[raster.known].sum()) == expected_area
        fraction = float(overlap[coastal_water].sum()/expected_area)
        model_pass = bool(fits and footprint_known and fraction == 1.)
        reports.append(dict(position=position, footprint=footprint, inside_border=bool(fits),
                            coastal_water_fraction=fraction, coverage_complete=bool(footprint_known),
                            model_pass=model_pass, footprint_evidence='actual_structure_bounds' if actual_extent else 'engineering_model_envelope',
                            actual_footprint_verified=bool(model_pass and actual_extent and raster.quality() == 'VERIFIED'
                                                           and actual_biomes)))
    monument_pass = any(row['model_pass'] for row in reports)
    actual_monument = any(row['actual_footprint_verified'] for row in reports)
    all_known = covered and known_fraction == 1.
    reasons = []
    if not p['land_fraction_min'] <= main_fraction <= p['land_fraction_max']:
        reasons.append(f"single connected mainland must occupy {100*p['land_fraction_min']:g}–{100*p['land_fraction_max']:g}% of Stronghold{side}")
    if not accepted:
        reasons.append('no complete ocean-connected border strip at minimum width')
    if require_monument and not monument_pass:
        reasons.append('no complete monument footprint envelope inside coastal water and border')
    if not all_known:
        reasons.append(f'unknown or missing cells inside Stronghold{side}')
    if not biome_available:
        reasons.append('ocean biome evidence unavailable')
    if river_enabled and not river_metrics['river_corridor_model_pass']:
        reasons.append(f'no sampled river corridor with continuous path length at least {minimum:g} blocks')
    actual = raster.metadata.get('source') == 'actual'
    complete = all_known and biome_available and (not actual or actual_monument or not require_monument)
    geometry = 60.*max(0., 1.-abs(main_fraction-.8)/.8) + 25.*bool(accepted) + 15.*monument_pass
    metrics = dict(mode='coastal_continent', mainland_fraction=main_fraction, land_fraction=land_fraction,
                   mainland_area=float(sizes[main_id]), known_fraction=known_fraction,
                   unknown_fraction=1.-known_fraction, connected_land_components=count,
                   mainland_connectivity=f'{connectivity}-way sampled land; inland freshwater bridges geographic components without adding dry-land area' if river_enabled else f'face-connected sampled cells clipped to exact Stronghold{side}',
                   ocean_edges=accepted, ocean_sectors=sectors, ocean_edge_min_width_blocks=width,
                   ocean_edge_fraction_min=p['ocean_edge_fraction_min'],
                   ocean_edge_preferred_max_width_blocks=p['ocean_edge_preferred_max_width_blocks'],
                   ocean_policy='contiguous boundary sector with complete minimum inward width in one ocean-family component',
                   ocean_biome_policy='all ocean family variants, including warm/cold/frozen; water evidence also required',
                   monument_footprints=reports, monument_coastal_model_pass=monument_pass,
                   monument_actual_footprint_verified=actual_monument,
                   footprint_policy=f'fixed Stronghold{side}; no formation halo or recentering',
                   evidence_scope='sampled model; unsampled blocks and generated structure extent remain unverified' if not actual_monument else 'generated block and structure footprint evidence',
                   stage_seconds={'land_connectivity':land_done-started, 'ocean_edge':coast_done-land_done,
                                  'monument_footprints':time.perf_counter()-coast_done})
    metrics.update(river_metrics)
    result = _finish('v1', raster, stronghold, bounds, stronghold, metrics, reasons, geometry,
                     list(bounds), complete, biome_fit, baseline_quality, footprint_complete=all_known)
    if actual and not complete:
        result['evidence'] = 'PARTIAL'
        apply_score_policy(result, component_status={'geometry':'PARTIAL'})
    if side==2048:metrics['coastal_component_ids']=sorted(coast_ids)
    result['mode'] = 'coastal_continent'
    result['evaluation_scope'] = 'coastal_geometry_subset'
    result['full_blueprint_certification'] = False
    result['unverified_terrain_requirements'] = ['actual sheer stony-shore cliffs',
                                                'rolling terrain without an enclosing mountain wall']
    result['model_geometry_pass'] = bool(not reasons)
    if not require_monument:
        result['marine_stage']='DEFERRED'
        result['pending_work'].append('query marine structures after complete finest-resolution coastal footprint')
    if not actual_monument:
        result['pending_work'].append('verify generated monument extent and every footprint column in coastal ocean')
    if river_enabled:
        result['pending_work'].append('verify river continuity, water depth, boat clearance and ice in actual generated blocks')
    if not complete:
        result['pending_work'] = [v for v in result['pending_work'] if v != 'expand or verify coverage/connectivity']
        result['pending_work'].append(f'verify missing evidence within fixed Stronghold{side}; no halo expansion')
    return result
