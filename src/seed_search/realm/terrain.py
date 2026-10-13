"""Independent Realm geometry tasks. Predictions never delete baseline records.

Ray measurements are conservative sampled estimates, not proof that a narrow
bridge is absent. Certification additionally requires block-resolution actual
water and verified natural-ground evidence supplied by the Raster provider.
"""
from __future__ import annotations

import math
import time
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull, distance

from .raster import Raster, RasterCache

V1 = dict(diameter_min=250, diameter_max=750, water_rays=24, water_width=48,
          area=12000, ideal_diameter_min=300, ideal_diameter_max=700,
          ideal_water_rays=29, ideal_water_width=100, ideal_area=20000)
V2 = dict(ridge_rays=20, relief=35, distance_min=300, distance_max=850,
          ideal_ridge_rays=26, ideal_relief=55, ideal_distance_min=350,
          ideal_distance_max=750, ridge_support_width=32, ridge_support_area=4096,
          largest_gap_rays=12, ridge_min_arc_rays=4, ridge_min_arc_aspect=2.,
          enclosure_policy='continuous_arcs')

# Explicit active search preferences. Low-level fallbacks above retain the
# historical controls; saved configurations without the new policy stay strict.
SEARCH_V1 = {**V1, 'diameter_min': 500, 'diameter_max': 1300,
             'area': 250000, 'ideal_diameter_min': 800,
             'ideal_diameter_max': 1100, 'ideal_area': 650000}
SEARCH_V2 = {**V2, 'enclosure_policy': 'surrounding_mountains',
             'ridge_rays': 16, 'relief': 24, 'distance_min': 150,
             'distance_max': 700, 'ideal_ridge_rays': 24,
             'ideal_relief': 50, 'ideal_distance_min': 250,
             'ideal_distance_max': 600}


def _score(value, ideal):
    return min(100., max(0., float(value)/ideal*100))


def _range_score(value, low, high, outer_low, outer_high):
    if low <= value <= high:
        return 100.
    if value < low:
        return 100.*max(0., (value-outer_low)/(low-outer_low))
    return 100.*max(0., (outer_high-value)/(outer_high-high))


def _touches_edge(mask):
    return bool(mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any())


def _component_diameter(raster, mask):
    """Maximum diameter of the sampled component's exact clipped cell footprint."""
    boundary = mask & ~ndimage.binary_erosion(mask, structure=np.ones((3, 3)))
    rr, cc = np.nonzero(boundary)
    if not len(rr): return 0.
    x0, z0, x1, z1 = raster.bounds
    left = x0+cc*raster.resolution
    top = z0+rr*raster.resolution
    right = np.minimum(x1, left+raster.resolution)
    bottom = np.minimum(z1, top+raster.resolution)
    points = np.concatenate([np.column_stack(pair) for pair in ((left, top), (right, top), (right, bottom), (left, bottom))])
    hull = points[ConvexHull(points).vertices]
    return float(distance.pdist(hull).max())


def _border(footprint, bounds, stronghold, complete):
    if footprint is None:
        return dict(state='unknown', status='unknown', border_fit='unknown', footprint=None, complete=False, minimum_side_blocks=None)
    x0, z0, x1, z1 = footprint
    bx0, bz0, bx1, bz1 = bounds
    overflow = dict(west=max(0, bx0-x0), north=max(0, bz0-z0),
                    east=max(0, x1-bx1), south=max(0, z1-bz1))
    sx, sz = stronghold
    minimum = 2*math.ceil(max(sx-x0, x1-sx, sz-z0, z1-sz))
    state = 'outside' if any(overflow.values()) else 'within' if complete else 'unknown'
    return dict(state=state, status=state, border_fit=state,
                footprint=footprint, overflow=overflow, minimum_centered_size=minimum,
                minimum_size_is_lower_bound=not complete, minimum_is_lower_bound=not complete,
                minimum_side_blocks=minimum, minimum_addon_side_blocks=math.ceil(minimum/32)*32, complete=bool(complete),
                policy='local-formation-v1')


def _rays(raster, center, maximum, count):
    distances = np.arange(0, maximum+raster.resolution/2, raster.resolution, dtype=float)
    rays = []
    x0, z0, _, _ = raster.bounds
    for angle in np.arange(count)*2*np.pi/count:
        xs = center[0]+np.cos(angle)*distances
        zs = center[1]+np.sin(angle)*distances
        cols = np.floor((xs-x0)/raster.resolution).astype(int)
        rows = np.floor((zs-z0)/raster.resolution).astype(int)
        valid = (rows >= 0)&(rows < raster.shape[0])&(cols >= 0)&(cols < raster.shape[1])
        rays.append((distances[valid], rows[valid], cols[valid]))
    return rays


def apply_score_policy(result, policy=None, *, component_status=None, source=None, biome_fit=None):
    """Score recorded components without promoting their evidence provenance."""
    weights = {'geometry_weight': .8, 'biome_fit_weight': .1, 'baseline_weight': .1,
               **(policy or {})}
    source = source or result.get('score_generation_source', result.get('provider', {}).get('source', 'prediction'))
    # Callers may reassert a freshly computed raster fit with explicit evidence.
    # Never restore an older unverified numeric input merely from a status change.
    if biome_fit is not None:
        result['biome_fit'] = float(biome_fit)
    status = dict(result.get('score_component_status', {}))
    status.update(component_status or {})
    status.setdefault('geometry', result.get('evidence', 'UNKNOWN'))
    # Numeric inputs alone cannot certify biome or baseline evidence.
    status.setdefault('biome_fit', 'UNKNOWN')
    status.setdefault('baseline_quality', 'UNKNOWN')
    if source == 'actual' and status['biome_fit'] == 'UNKNOWN' and result.get('biome_fit', 0):
        result['unverified_biome_fit_input'] = result['biome_fit']
        result['biome_fit'] = 0.
    parts = [('geometry', 'geometry_score', 'geometry_weight'),
             ('biome_fit', 'biome_fit', 'biome_fit_weight'),
             ('baseline_quality', 'baseline_quality', 'baseline_weight')]
    score = sum(weights[w]*float(result.get(f, 0)) for _, f, w in parts)
    unknown = {'UNKNOWN', 'PENDING', 'PARTIAL', 'UNSUPPORTED', 'FAILED'}
    low = sum(weights[w]*float(result.get(f, 0)) for c, f, w in parts if status[c] not in unknown)
    high = low+sum(100*weights[w] for c, _, w in parts if status[c] in unknown)
    verified = (source == 'actual' and result.get('evidence') == 'VERIFIED'
                and result.get('border_fit', {}).get('complete', False)
                and all(status[c] == 'VERIFIED' for c, _, w in parts if weights[w] > 0))
    result.update(score=float(score), score_policy=dict(weights), score_generation_source=source,
                  score_component_status=status, score_verified_complete=verified,
                  predicted_score=score if source != 'actual' else None,
                  verified_score=score if verified else None,
                  actual_partial_score=score if source == 'actual' and not verified else None,
                  score_is_estimate=not verified,
                  score_interval={'low': max(0., low), 'high': min(100., high),
                                  'policy': 'unknown-components-bounds; prediction error not calibrated'})
    return result


def attach_actual_evaluation(prediction, actual, policy=None):
    """Keep prediction and generated-world scores as independent saved views."""
    apply_score_policy(actual, policy)
    prediction['actual_evaluation'] = actual
    prediction['verified_score'] = actual['verified_score']
    prediction['actual_partial_score'] = actual['actual_partial_score']
    return prediction


def _finish(variant, raster, center, bounds, stronghold, metrics, reasons, geometry,
            footprint, complete, biome_fit=0., baseline_quality=0., *, footprint_complete=None):
    quality = raster.quality()
    footprint_complete = complete if footprint_complete is None else footprint_complete
    incomplete = not complete or quality in {'PARTIAL', 'UNSUPPORTED', 'FAILED'}
    qualification = 'PENDING' if incomplete else ('VERIFIED' if quality == 'VERIFIED' else 'PREDICTED')
    if reasons and not incomplete:
        qualification = 'FAILED' if quality == 'VERIFIED' else 'PREDICTED_NEAR_MATCH'
    result = dict(variant=variant, center=list(center), geometry_pass=not reasons,
                qualification=qualification, evidence=quality, reasons=reasons,
                metrics=metrics, geometry_score=float(geometry), biome_fit=float(biome_fit),
                baseline_quality=float(baseline_quality),
                border_fit=_border(footprint, bounds, stronghold, footprint_complete),
                resolution=raster.resolution, provider=raster.metadata,
                pending_work=['expand or verify coverage/connectivity'] if incomplete else
                             (['actual generation verification'] if quality != 'VERIFIED' else []) +
                             (['resolve complete formation footprint'] if not footprint_complete and not incomplete else []))
    return apply_score_policy(result)


def evaluate_v1(raster: Raster, center, bounds=None, stronghold=(0, 0), *, thresholds=None,
                rays=32, biome_fit=0., baseline_quality=0., monuments=(), require_monument=True):
    """Closed land component plus a common enclosing water body, including lakes."""
    if (thresholds or {}).get('mode') == 'coastal_continent':
        from .coastal import evaluate_coastal
        return evaluate_coastal(raster, center, bounds, stronghold, thresholds=thresholds,
                                monuments=monuments, biome_fit=biome_fit, baseline_quality=baseline_quality, require_monument=require_monument)
    p = {**V1, **(thresholds or {})}
    bounds = bounds or raster.bounds
    water = raster.water_mask()
    # Diagonal land contacts are treated as possible bridges; water uses face connectivity.
    land_labels, _ = ndimage.label(raster.known & ~water, np.ones((3, 3)))
    water_labels, _ = ndimage.label(water)
    index = raster.index(center)
    component = int(land_labels[index]) if index is not None else 0
    island = land_labels == component if component else np.zeros(raster.shape, bool)
    area = float(raster.cell_areas()[island].sum())
    footprint = raster.mask_bounds(island)
    crossings, widths, ids, ray_details, opposite_shores = [], [], [], [], []
    maxdistance = p['diameter_max']+max(p['ideal_water_width'], p['water_width'])+raster.resolution
    for distance, rr, cc in _rays(raster, center, maxdistance, rays):
        on_island = island[rr, cc]
        exits = np.flatnonzero(~on_island)
        if not component or not len(exits) or exits[0] == 0:
            crossings.append(None); widths.append(0.); ids.append(0); opposite_shores.append(False); continue
        start = int(exits[0]); wid = int(water_labels[rr[start], cc[start]])
        end = start
        while wid and end < len(distance) and water_labels[rr[end], cc[end]] == wid:
            end += 1
        width = max(0., float((end-start)*raster.resolution))
        crossings.append(float(distance[start])); widths.append(width); ids.append(wid)
        opposite_shore = bool(wid and end < len(distance) and raster.known[rr[end], cc[end]] and not water[rr[end], cc[end]])
        opposite_shores.append(opposite_shore)
        ray_details.append(dict(shore_distance=float(distance[start]), water_width=width, water_component=wid, opposite_shore_observed=opposite_shore, water_width_is_lower_bound=bool(wid) and not opposite_shore))
    counts = {i: sum(i == j and w >= p['water_width'] for j, w in zip(ids, widths)) for i in set(ids) if i}
    enclosing = max(counts, key=counts.get) if counts else 0
    water_rays = counts.get(enclosing, 0)
    supported_widths = [w for i, w in zip(ids, widths) if i == enclosing and w > 0]
    median_width = float(np.median(supported_widths)) if supported_widths else 0.
    diameters = [crossings[i]+crossings[(i+rays//2)%rays] for i in range(rays//2)
                 if crossings[i] is not None and crossings[(i+rays//2)%rays] is not None]
    ray_diameter = max(diameters, default=0.)
    hull_span = _component_diameter(raster, island)
    diameter = 2*math.sqrt(area/math.pi)
    # A local finite-lake belt can be complete only when its enclosing ray
    # endpoints reach known opposite shores. Component closure alone does not
    # prove this: a wide lake can close beyond every ray's sampling radius.
    # Open water supplies a minimum local belt, never a complete fit claim.
    distance_from_island = ndimage.distance_transform_edt(~island)*raster.resolution
    belt_width = max(p['water_width'], min(median_width, p['ideal_water_width']))
    enclosing_body = water_labels == enclosing if enclosing else np.zeros_like(island)
    water_body_closed = bool(enclosing) and not _touches_edge(enclosing_body) and not bool((ndimage.binary_dilation(enclosing_body) & ~raster.known).any())
    observed_closed_widths = [width for width, ident, closed in zip(widths, ids, opposite_shores) if ident == enclosing and closed]
    enclosing_shores_resolved = bool(enclosing) and all(closed for ident, closed in zip(ids, opposite_shores) if ident == enclosing)
    local_belt_width = max(belt_width, max(observed_closed_widths, default=0.)+raster.resolution if observed_closed_widths else 0.)
    if water_body_closed and not observed_closed_widths and supported_widths:
        # Preserve the measured lower bound rather than substituting the ideal
        # 100-block width when all sampled rays are still inside the lake.
        local_belt_width = max(local_belt_width, min(supported_widths))
    local_water_belt = enclosing_body & (distance_from_island <= local_belt_width)
    formation = island | local_water_belt
    complete = bool(component) and not _touches_edge(island) and raster.known.all()
    if component:
        # Unknown immediate neighbors prevent a closure claim even if other data are known.
        complete &= not bool((ndimage.binary_dilation(island, structure=np.ones((3, 3))) & ~raster.known).any())
    footprint_complete = complete and water_body_closed and enclosing_shores_resolved
    reasons = []
    if not component: reasons.append('center is not supported land')
    if _touches_edge(island): reasons.append('land component reaches analysis boundary')
    if not p['diameter_min'] <= diameter <= p['diameter_max']: reasons.append('island diameter')
    if area < p['area']: reasons.append('island area')
    if water_rays < p['water_rays']: reasons.append('connected water enclosure')
    if median_width < p['water_width']: reasons.append('water belt width')
    shape = .5*_range_score(diameter, p['ideal_diameter_min'], p['ideal_diameter_max'], 0, p['diameter_max']*1.5)+.5*_score(area, p['ideal_area'])
    enclosure = .5*_score(water_rays, p['ideal_water_rays'])+.5*_score(median_width, p['ideal_water_width'])
    access = _score(water_rays, rays)
    metrics = dict(diameter=diameter, equivalent_diameter=diameter, hull_span=hull_span, ray_diameter=ray_diameter, island_area=area, water_rays=water_rays,
                   diameter_policy='area-equivalent: 2*sqrt(island_area/pi)',
                   footprint_policy='bounded-local-water-belt-through-observed-opposite-shores' if footprint_complete else 'observed-local-water-belt; outer extent unresolved' if observed_closed_widths else 'sampled-local-water-belt; outer extent unresolved' if water_body_closed else 'minimum-local-water-belt; outer extent unresolved',
                   minimum_local_belt_width=belt_width, measured_local_belt_width=local_belt_width, enclosing_water_body_closed=water_body_closed,
                   enclosing_opposite_shores_resolved=enclosing_shores_resolved,
                   enclosing_water_component_bounds=raster.mask_bounds(enclosing_body),
                   opposite_shore_rays=sum(hit and ident == enclosing for hit, ident in zip(opposite_shores, ids)),
                   median_water_width=median_width, separate_land_component=bool(component) and not _touches_edge(island),
                   enclosing_water_component=enclosing, shoreline_rays=ray_details)
    return _finish('v1', raster, center, bounds, stronghold, metrics, reasons,
                   .3*shape+.55*enclosure+.15*access, raster.mask_bounds(formation), complete,
                   biome_fit, baseline_quality, footprint_complete=footprint_complete)


def _largest_gap(hits):
    if all(hits): return 0
    if not any(hits): return len(hits)
    doubled = hits+hits
    longest = run = 0
    for hit in doubled:
        run = 0 if hit else run+1
        longest = max(longest, run)
    return min(longest, len(hits))


def _circular_component_runs(components):
    """Consecutive same-component ray runs, including runs across bearing zero."""
    count = len(components)
    if not count: return []
    if len(set(components)) == 1:
        return [(components[0], list(range(count)))] if components[0] else []
    start = next(i for i in range(count) if components[i] != components[(i-1)%count])
    runs = []; current = []; ident = components[start]
    for offset in range(count):
        index = (start+offset)%count
        if components[index] != ident:
            if ident: runs.append((ident, current))
            ident = components[index]; current = []
        current.append(index)
    if ident: runs.append((ident, current))
    return runs


def evaluate_v2(raster: Raster, center, bounds=None, stronghold=(0, 0), *, thresholds=None,
                rays=32, biome_fit=0., baseline_quality=0.):
    """Relative surrounding mountains, with optional strict continuous-arc policy."""
    p = {**V2, **(thresholds or {})}
    strict_arcs = p['enclosure_policy'] == 'continuous_arcs'
    if p['enclosure_policy'] not in ('continuous_arcs', 'surrounding_mountains'):
        raise ValueError('Unknown V2 enclosure policy')
    bounds = bounds or raster.bounds
    xx, zz = raster.coordinates()
    radial = np.hypot(xx-center[0], zz-center[1])
    interior = (radial <= min(150, p['distance_min']/2)) & raster.known
    representative = float(np.median(raster.height[interior])) if interior.any() else 0.
    # The nomination distance limits ray starts, not the physical ridge extent.
    # Label continuous support beyond that annulus before extracting its footprint.
    ridge = raster.known & (raster.height >= representative+p['relief']) & (radial >= p['distance_min'])
    labels, count = ndimage.label(ridge, np.ones((3, 3)))
    areas = np.bincount(labels.ravel(), weights=raster.cell_areas().ravel(), minlength=count+1)
    supports, distances, reliefs, components = [], [], [], []
    for distance, rr, cc in _rays(raster, center, p['distance_max'], rays):
        values = labels[rr, cc]
        selected = None
        for start in np.flatnonzero(values):
            ident = int(values[start]); end = int(start)
            while end < len(values) and values[end] == ident: end += 1
            if (end-start)*raster.resolution >= p['ridge_support_width'] and areas[ident] >= p['ridge_support_area']:
                selected = (ident, float(distance[start]), float(np.max(raster.height[rr[start:end], cc[start:end]])-representative)); break
        supports.append(selected is not None)
        components.append(selected[0] if selected else 0)
        distances.append(selected[1] if selected else None)
        reliefs.append(selected[2] if selected else None)
    # All policies require spatially substantial raised terrain. The inclusive
    # search allows separate mountains to surround an interior; arc aspect and
    # run length remain diagnostics unless the saved strict policy requests them.
    raw_components = [ident if hit else 0 for ident, hit in zip(components, supports)]
    raw_hits = sum(supports)
    supports = [False]*rays
    arc_runs = []; radial_stats = {}
    for ident, indices in _circular_component_runs(raw_components):
        if ident not in radial_stats:
            values = radial[(labels == ident)&(radial <= p['distance_max'])]
            if not values.size:
                arc_runs.append(dict(component=ident, ray_indices=indices, rays=len(indices), qualified=False,
                                     reason='no support cells inside nomination annulus', radial_thickness=None, arc_aspect=None))
                continue
            thickness = float(np.percentile(values, 90)-np.percentile(values, 10)+raster.resolution)
            radial_stats[ident] = (float(np.median(values)), thickness)
        radius, thickness = radial_stats[ident]
        arc_length = len(indices)*2*np.pi/rays*radius
        aspect = float(arc_length/thickness)
        qualified = not strict_arcs or (len(indices) >= p['ridge_min_arc_rays'] and aspect >= p['ridge_min_arc_aspect'])
        arc_runs.append(dict(component=ident, ray_indices=indices, rays=len(indices),
                             degrees=len(indices)*360/rays, median_radius=radius,
                             radial_thickness=thickness, tangential_arc_length=float(arc_length),
                             arc_aspect=aspect, qualified=bool(qualified)))
        if qualified:
            for index in indices: supports[index] = True
    supported_ids = {ident for ident, hit in zip(components, supports) if hit}
    hits = sum(supports); gap = _largest_gap(supports)
    distances_ok = [v for v, hit in zip(distances, supports) if hit]
    relief_ok = [v for v, hit in zip(reliefs, supports) if hit]
    median_distance = float(np.median(distances_ok)) if distances_ok else 0.
    median_relief = float(np.median(relief_ok)) if relief_ok else 0.
    supporting_ridges = np.isin(labels, list(supported_ids))
    ridge_footprint_radius = p['distance_max']+8*p['ridge_support_width']
    local_support = supporting_ridges & (radial <= ridge_footprint_radius)
    support_truncated = bool(supporting_ridges.any()) and (
        _touches_edge(supporting_ridges) or bool((supporting_ridges & (radial > ridge_footprint_radius)).any())
        or bool((ndimage.binary_dilation(supporting_ridges, structure=np.ones((3, 3))) & ~raster.known).any()))
    formation = (radial <= max(distances_ok, default=p['distance_min'])) | local_support
    # All relevant cells and the enclosing ray extent must be available.
    full_extent = (center[0]-p['distance_max'] >= raster.bounds[0] and center[1]-p['distance_max'] >= raster.bounds[1]
                   and center[0]+p['distance_max'] < raster.bounds[2] and center[1]+p['distance_max'] < raster.bounds[3])
    complete = bool(interior.any()) and full_extent and bool(raster.known[radial <= p['distance_max']].all())
    footprint_complete = complete and bool(supported_ids) and not support_truncated
    reasons = []
    if raw_hits >= p['ridge_rays'] and hits < p['ridge_rays']: reasons.append('ridge arc continuity/support')
    if hits < p['ridge_rays']: reasons.append('ridge angular enclosure')
    if gap > p['largest_gap_rays']: reasons.append('largest angular gap')
    if median_relief < p['relief']: reasons.append('interior-relative relief')
    if not p['distance_min'] <= median_distance <= p['distance_max']: reasons.append('ridge distance')
    enclosure = .5*_score(hits, p['ideal_ridge_rays'])+.3*_score(median_relief, p['ideal_relief'])+.2*_range_score(median_distance, p['ideal_distance_min'], p['ideal_distance_max'], 0, p['distance_max']*1.5)
    access = _score(max(0, rays-gap), rays)
    roughness = float(np.std(raster.height[interior])) if interior.any() else None
    metrics = dict(ridge_rays=hits, raw_ridge_rays=raw_hits, ridge_arc_runs=arc_runs,
                   ridge_continuity_policy={'enclosure_policy': p['enclosure_policy'],
                                            'arc_shape_required': strict_arcs,
                                            'minimum_arc_rays': p['ridge_min_arc_rays'] if strict_arcs else None,
                                            'minimum_arc_aspect': p['ridge_min_arc_aspect'] if strict_arcs else None,
                                            'radial_thickness': '10th-to-90th percentile in nomination annulus plus one sample width',
                                            'calibration': 'sampled engineering policy; actual-world calibration pending'},
                   rejected_support_components=sorted(set(raw_components)-{0}-supported_ids),
                   relative_relief=median_relief, ridge_distance=median_distance,
                   interior_elevation=representative, interior_roughness=roughness,
                   largest_gap_rays=gap, largest_gap_degrees=gap*360/rays,
                   ridge_distances=distances, ridge_reliefs=reliefs, connected_support_components=sorted(supported_ids),
                   ridge_footprint_radius=ridge_footprint_radius, supporting_ridges_truncated=support_truncated,
                   supporting_ridge_component_bounds=raster.mask_bounds(supporting_ridges),
                   footprint_policy='basin-and-connected-supporting-ridges-with-local-halo',
                   geometry_weights={'enclosure': .875, 'access': .125})
    return _finish('v2', raster, center, bounds, stronghold, metrics, reasons,
                   .875*enclosure+.125*access, raster.mask_bounds(formation), complete,
                   biome_fit, baseline_quality, footprint_complete=footprint_complete)


def propose_centers(raster, bounds, variant, spacing=64):
    """Feature centroids/minima plus an unsnapped regular grid over the entire Realm."""
    x0, z0, x1, z1 = bounds
    centers = {(x, z) for z in range(z0, z1, spacing) for x in range(x0, x1, spacing)}
    xx, zz = raster.coordinates()
    if variant == 'v1':
        labels, count = ndimage.label(raster.known & ~raster.water_mask(), np.ones((3, 3)))
        for ident in range(1, count+1):
            mask = labels == ident
            if not _touches_edge(mask):
                centers.add((int(round(xx[mask].mean())), int(round(zz[mask].mean()))))
    elif variant == 'v2':
        values = np.where(raster.known, raster.height, np.inf)
        minima = raster.known & (values == ndimage.minimum_filter(values, size=3))
        centers.update((int(x), int(z)) for x, z in zip(xx[minima], zz[minima]))
    else:
        raise ValueError('Realm variants are v1 and v2')
    return sorted((x, z) for x, z in centers if x0 <= x < x1 and z0 <= z < z1)


def biome_fit_score(observed, preferred):
    """Fixed reward denominator; Savanna neither rewards nor dilutes fit."""
    neutral = {'savanna', 'savanna_plateau', 'windswept_savanna', 'shattered_savanna', 'shattered_savanna_plateau'}
    preferred = set(preferred)-neutral
    return 100.*len((set(observed)-neutral)&preferred)/len(preferred) if preferred else 0.


def _native_terrain_identity():
    """Hash the selected extension and wrapper files without importing/rebuilding it."""
    import importlib.util
    spec = importlib.util.find_spec('seed_search._native')
    if spec is None or not spec.origin or not Path(spec.origin).is_file():
        raise ValueError('Native terrain extension unavailable; cannot establish resume identity')
    root = Path(__file__).resolve().parents[3]
    paths = {'native_extension': Path(spec.origin),
             'backend_wrapper': root/'src/seed_search/backend.py',
             'seed_wrapper': root/'src/seed_search/seeds.py',
             'backend_manifest': root/'vendor/backend.json'}
    return {'kind': 'native', 'extension_name': Path(spec.origin).name,
            'sha256': {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}}


def terrain_provider_identity(provider_factory=None, declared=None):
    """Custom factories declare static JSON build/settings identity before creation.

    A factory attribute `terrain_identity` (or static `cache_identity`) or the
    explicit run_terrain provider_identity argument supplies the declaration.
    Object addresses and callable identity suppliers are intentionally rejected.
    The declaration must include every provider build/model/extraction setting
    outside the already pinned Realm configuration.
    """
    if provider_factory is None:
        if declared is not None:
            raise ValueError('provider_identity requires a custom provider_factory')
        return _native_terrain_identity()
    if declared is None:
        declared = getattr(provider_factory, 'terrain_identity', None)
    if declared is None:
        declared = getattr(provider_factory, 'cache_identity', None)
    def static(value):
        if value is None or type(value) in (str, bool, int): return True
        if type(value) is float: return math.isfinite(value)
        if type(value) is list: return all(static(item) for item in value)
        if type(value) is dict: return all(type(key) is str and static(item) for key, item in value.items())
        return False
    if declared is None or not declared or not static(declared):
        raise ValueError('Persistent custom terrain providers require a nonempty static JSON provider_identity or factory.terrain_identity before sampling or resume')
    return {'kind': 'custom', 'declared': json.loads(json.dumps(declared, sort_keys=True, allow_nan=False))}


def terrain_algorithm_identity(cfg, *, provider_factory=None, provider_identity=None):
    """Pin terrain computation independently of baseline enumeration and reporting.

    Pure weighting changes have a separate identity so explicit rescore can use
    saved metrics. Provider builds and extraction settings remain computational.
    """
    root = Path(__file__).parent
    sources = {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
               for name in ('terrain.py', 'coastal.py', 'marine.py', 'blueprint.py', 'verification_plan.py', 'raster.py', 'biomes.py')}
    bds = {key: value for key, value in cfg.get('bds', {}).items()
           if key not in {'cpus', 'memory_gib', 'verification_budget'}}
    value = dict(policy='realm-terrain-v3', work_schema='center-stage-pool-v1', raster_encoding='npz-base64-v1', sampling_provider=terrain_provider_identity(provider_factory, provider_identity), sources=sources, terrain=cfg.get('terrain', {}),
                 game=cfg.get('game', {}), world_settings=cfg.get('world_settings', {}),
                 provider=bds, baseline_quality_cap=cfg.get('scoring', {}).get('baseline_quality_cap', 60))
    value['sha256'] = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return value


def terrain_scoring_identity(cfg):
    scoring = cfg.get('scoring', {})
    return {name: scoring.get(name, default) for name, default in
            (('geometry_weight', .8), ('biome_fit_weight', .1), ('baseline_weight', .1))}


def _pin_task_identity(store, cfg, provider_factory=None, provider_identity=None):
    if not (hasattr(store, 'get_state') and hasattr(store, 'set_state')):
        return
    identity = terrain_algorithm_identity(cfg, provider_factory=provider_factory, provider_identity=provider_identity)
    prior = store.get_state('terrain_algorithm_identity')
    if prior is not None and prior != identity:
        raise ValueError('Terrain algorithm/provider/settings identity changed; completed terrain tasks cannot silently resume. Use a separate terrain evaluation checkpoint.')
    scoring = terrain_scoring_identity(cfg)
    previous_scoring = store.get_state('terrain_scoring_identity')
    if previous_scoring is not None and previous_scoring != scoring:
        raise ValueError('Terrain score weights changed; explicitly rescore saved terrain metrics before resuming.')
    if prior is None:
        recorded = hasattr(store, 'iter_variants') and next(iter(store.iter_variants()), None) is not None
        completed = hasattr(store, 'iter_variant_tasks') and any(next(iter(store.iter_variant_tasks(status=status)), None) is not None for status in ('started', 'complete'))
        if recorded or completed:
            raise ValueError('Saved terrain evidence/tasks lack a pinned terrain provider identity; use a separate terrain evaluation checkpoint, preserving historical records')
        store.set_state('terrain_algorithm_identity', identity)
    if previous_scoring is None: store.set_state('terrain_scoring_identity', scoring)


def _run_terrain_legacy(store, cfg, variants=('v1', 'v2'), limit=None, resume=True, progress=None, *, provider_factory=None, provider_identity=None):
    """Consume the persistent pool independently, sharing nomination and height tiles.

    Limits count pairs with unfinished requested tasks; completed pairs do not
    consume the invocation budget. Fine sampling is restricted
    to each variant's own refinement budget. Tasks are committed per center so a
    cancellation retries missing centers, never removes or rewrites the baseline.
    """
    if any(v not in {'v1', 'v2'} for v in variants): raise ValueError('Realm variants are v1 and v2')
    if limit is not None and limit < 0: raise ValueError('Limit must be nonnegative')
    _pin_task_identity(store, cfg, provider_factory, provider_identity)
    if provider_factory is None:
        from ..backend import Backend
        provider_factory = lambda seed: Backend(seed)
    terrain = cfg.get('terrain', {})
    spacing = terrain.get('center_spacing', 64)
    refinements = terrain.get('max_refinements', terrain.get('maximum_refinements_per_anchor', 8))
    resolutions = terrain.get('resolutions', [128, 64, 32, 16, 8, 4])
    cache = RasterCache(terrain.get('cache_entries', 32))
    summary = dict(candidates=0, results=0, resumed=0, resumed_tasks=0, cache_hits=0, cache_misses=0)
    started = time.monotonic()
    from .coastal import coastal_mode, monument_inputs
    coastal = coastal_mode(cfg)
    policies = {variant: {**(V1 if variant == 'v1' else V2), **terrain.get(variant, cfg.get('variants', {}).get(variant, {}))} for variant in terrain.get('variants',('v1','v2'))}
    extents = {variant: (policy['diameter_max']+max(policy['ideal_water_width'], policy['water_width']) if variant == 'v1' else policy['distance_max']+8*policy['ridge_support_width']) for variant, policy in policies.items()}
    if refinements == 0:
        return dict(summary, elapsed_seconds=0.)
    if len(set(resolutions)) < 2:
        raise ValueError('Terrain requires nomination and at least one height resolution')
    statuses = ['PREDICTED', 'VERIFIED']+(['PENDING'] if terrain.get('include_pending', False) else [])
    for candidate in store.iter_candidates(statuses=statuses):
        if limit is not None and summary['candidates'] >= limit: break
        stored_bounds = candidate['bounds']
        bounds = tuple(stored_bounds['overworld'] if isinstance(stored_bounds, dict) else stored_bounds)
        seed, stronghold = candidate['seed'], candidate['stronghold']
        active_variants = [v for v in variants if not (resume and hasattr(store, 'get_variant_task_status') and store.get_variant_task_status(candidate['id'], v) == 'complete')]
        summary['resumed_tasks'] += len(variants)-len(active_variants)
        if not active_variants:
            continue
        provider = provider_factory(seed)
        settings = {'game': cfg.get('game', {}), 'world_settings': cfg.get('world_settings', {})}
        try:
            # Cheap 2D nomination precedes any density height computation.
            halo = math.ceil(max(extents.values())+max(resolutions)+terrain.get('refine_center_spacing', 16))
            nomination_bounds = bounds if coastal and active_variants == ['v1'] else (bounds[0]-halo, bounds[1]-halo, bounds[2]+halo, bounds[3]+halo)
            nomination = cache.sample(provider, seed, nomination_bounds, max(resolutions), stage='nomination', settings=settings)
            for variant in active_variants:
                evaluate = evaluate_v1 if variant == 'v1' else evaluate_v2
                thresholds = policies[variant]
                options = dict(thresholds=thresholds, rays=terrain.get('rays', 32))
                fixed = coastal and variant == 'v1'
                if fixed:
                    options['monuments'] = monument_inputs(candidate)
                    if cfg.get('screening_revision'):options['require_monument']=candidate.get('marine_stage',{}).get('status')!='DEFERRED'
                coarse = []
                for center in ([tuple(stronghold)] if fixed else propose_centers(nomination, bounds, variant, spacing)):
                    result = evaluate(nomination, center, bounds, stronghold, **options)
                    coarse.append((result['geometry_score'], center))
                selected = [c for _, c in sorted(coarse, key=lambda row: (-row[0], row[1]))[:refinements]]
                for coarse_center in selected:
                    cx, cz = coarse_center
                    local_spacing = terrain.get('refine_center_spacing', 16)
                    nearby = [(cx+dx, cz+dz) for dx in (-local_spacing, 0, local_spacing) for dz in (-local_spacing, 0, local_spacing)
                              if bounds[0] <= cx+dx < bounds[2] and bounds[1] <= cz+dz < bounds[3]]
                    if fixed: nearby = [tuple(stronghold)]
                    center = coarse_center
                    for resolution in sorted(set(resolutions)-{max(resolutions)}, reverse=True):
                        radius = math.ceil(max(extents.values())+2*resolution+local_spacing)
                        local = bounds if fixed else (cx-radius, cz-radius, cx+radius+1, cz+radius+1)
                        sampled = cache.sample(provider, seed, local, resolution, stage='height', settings=settings)
                        quality = candidate.get('baseline_score')
                        if quality is None:quality=candidate.get('baseline_score_observed',0)
                        quality = quality.get('normalized', quality.get('quality', 0)) if isinstance(quality, dict) else 100.*float(quality or 0)/cfg.get('scoring', {}).get('baseline_quality_cap', 60)
                        from .biomes import variant_fit
                        from ..backend import biome_name
                        observed = [biome_name(int(b)) for b in np.unique(sampled.biomes[sampled.known])] if sampled.biomes is not None else []
                        fit = variant_fit(observed, variant)
                        evaluated = [evaluate(sampled, c, bounds, stronghold, biome_fit=fit, baseline_quality=min(100., max(0., float(quality or 0))), **options) for c in nearby]
                        result = max(evaluated, key=lambda r: r['geometry_score']); center = tuple(result['center'])
                        nearby = [center]
                        result['sampling_schedule'] = {'nomination_resolution': max(resolutions), 'last_height_resolution': resolution, 'coarse_center': list(coarse_center), 'independent_refinement_budget': refinements}
                        if resolution <= 32 and result['geometry_score'] < terrain.get('fine_refinement_score', 40):
                            result['pending_work'].append('below fine-refinement scheduling threshold; baseline retained')
                            break
                    if fixed and cfg.get('screening_revision') and resolution==min(resolutions):
                        from .marine import evaluate_marine_stage
                        result,marine_update=evaluate_marine_stage(candidate,cfg,sampled,result)
                        if marine_update:
                            store.upsert_candidate(marine_update);candidate={**candidate,**marine_update}
                    apply_score_policy(result, cfg.get('scoring', {}), source=sampled.metadata.get('source', 'prediction'), biome_fit=fit,
                                       component_status={'geometry': result['evidence'],
                                                         'biome_fit': 'PREDICTED' if sampled.biomes is not None else 'UNKNOWN',
                                                         'baseline_quality': candidate.get('qualification', 'PENDING')})
                    existing = store.get_variant(candidate['id'], variant, list(center)) if resume else None
                    if existing:
                        summary['resumed'] += 1
                    else:
                        store.upsert_variant(candidate['id'], variant, list(center), result)
                        summary['results'] += 1
                if hasattr(store, 'set_variant_task_status'):
                    store.set_variant_task_status(candidate['id'], variant, 'complete')
            summary['candidates'] += 1
            if progress: progress(dict(summary, seed=seed, elapsed_seconds=time.monotonic()-started))
        finally:
            if hasattr(provider, 'close'): provider.close()
    summary.update(cache_hits=cache.hits, cache_misses=cache.misses, elapsed_seconds=time.monotonic()-started)
    return summary


def _encode_terrain_raster(raster, unit):
    import base64
    import io
    arrays={'height':raster.height,'known':raster.known}
    for name in ('biomes','water','natural_ground'):
        value=getattr(raster,name)
        if value is not None:arrays[name]=value
    output=io.BytesIO();np.savez_compressed(output,**arrays)
    return {'id':unit['sampling_key'],'kind':'terrain_raster','bounds':list(raster.bounds),
            'resolution':raster.resolution,'lattice':unit['payload']['lattice'],
            'channels':{'encoding':'npz-base64','data':base64.b64encode(output.getvalue()).decode('ascii')},
            'metadata':raster.metadata}


def _decode_terrain_raster(observation):
    import base64
    import io
    channels=observation['channels']
    if channels.get('encoding')!='npz-base64':raise ValueError('Unsupported durable terrain raster encoding')
    with np.load(io.BytesIO(base64.b64decode(channels['data'])),allow_pickle=False) as archive:
        arrays={name:archive[name] for name in archive.files}
    return Raster(bounds=observation['bounds'],resolution=observation['resolution'],
                  metadata=observation['metadata'],**arrays)


def _terrain_work_payload(stage, coarse_center, resolution, raster_bounds, **state):
    bounds=list(raster_bounds)
    return dict(stage=stage,coarse_center=list(coarse_center),resolution=int(resolution),
                halo_level=state.pop('halo_level',0),raster_bounds=bounds,
                lattice={'x0':bounds[0],'z0':bounds[1],'step':int(resolution),
                         'shape':[math.ceil((bounds[3]-bounds[1])/resolution),math.ceil((bounds[2]-bounds[0])/resolution)]},
                **state)


def _preserve_actual_variant(store,candidate_id,variant,result):
    existing=store.get_variant(candidate_id,variant,result['center'])
    if existing:
        for key in ('actual_evaluation','actual_observation_id','verified_score','actual_partial_score'):
            if key in existing['result']:result[key]=existing['result'][key]
    return result


def _terrain_sampling_retry_reason(raster):
    source=raster.metadata.get('source')
    if raster.metadata.get('failed') or raster.metadata.get('unsupported'):
        return 'failed or unsupported sampling; retry required, absence not established'
    if source not in {'prediction','actual'}:
        return 'sampling source is undeclared; retry with explicit provenance'
    if not raster.known.all():
        return 'sampling lattice has missing/unknown cells; retry required'
    if source=='actual' and raster.metadata.get('stable_sampled_observations') is not True:
        return 'actual sampled observations are unstable or stability is unknown; retry required'
    return None


def _retry_terrain_observation(observation,unit):
    if observation is None:return None
    observation=dict(observation)
    observation['sampling_key']=unit['sampling_key']
    observation['id']=f"{unit['sampling_key']}:unit:{unit['unit_id']}:attempt:{unit['attempts']}"
    return observation


def _rotating_terrain_pool(store,revision,cursor):
    yield from store.iter_terrain_pool_candidates(revision,start_after=cursor)
    if cursor:
        yield from store.iter_terrain_pool_candidates(revision,stop_at=cursor)


def _run_terrain_durable(store,cfg,variants,limit,resume,progress,provider_factory,provider_identity,
                         pool_revision,new_pool_revision,continue_deferred_halos):
    import fcntl
    lock=(store.run/'terrain-scheduler.lock').open('a+')
    try:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Another terrain scheduler owns this checkpoint') from None
        _pin_task_identity(store,cfg,provider_factory,provider_identity)
        identity=store.get_state('terrain_algorithm_identity')
        statuses=['PREDICTED','VERIFIED']+(['PENDING'] if cfg.get('terrain',{}).get('include_pending') else [])
        revision=store.ensure_terrain_pool(identity,statuses,revision=pool_revision,new_revision=new_pool_revision)
        store.recover_terrain_work(revision)
        terrain=cfg.get('terrain',{})
        from .store import TerrainCapacityError
        from .resources import disk_policy,disk_status,WorkspaceCapacityError
        store.configure_terrain_disk_policy(terrain.get('durable_cache_limit_bytes',8 << 30),
                                            terrain.get('free_disk_reserve_bytes',16 << 30))
        class CapacityBlocked(Exception):pass
        def persist(method,unit,**values):
            try:
                if cfg.get('search'):
                    disk_status(store.run,disk_policy(cfg['search']),additional_bytes=len(json.dumps(values,allow_nan=False).encode())*2)
                return method(unit['unit_id'],**values)
            except (TerrainCapacityError,WorkspaceCapacityError) as exc:
                retained=values.get('variant_results',())
                proposals=(values.get('result') or {}).get('proposals',[])
                if not retained and proposals:
                    nearest=max(proposals,key=lambda r:r['geometry_score'])
                    _preserve_actual_variant(store,unit['candidate_id'],unit['variant'],nearest)
                    retained=[dict(candidate_id=unit['candidate_id'],variant=unit['variant'],center=nearest['center'],result=nearest)]
                for saved in retained:
                    saved['result'].setdefault('pending_work',[]).append('durable raster write blocked by disk policy; retry this stage')
                store.defer_terrain_work(unit['unit_id'],result=values.get('result'),
                    variant_results=retained,state={'capacity_failure':str(exc)},
                    expected_attempt=unit['attempts'],worker=unit['worker'])
                summary.update(resource_blocked=True,capacity_failure=str(exc))
                raise CapacityBlocked from exc
        budget=terrain.get('max_refinements',terrain.get('maximum_refinements_per_anchor',8))
        resolutions=sorted(set(terrain.get('resolutions',[128,64,32,16,8,4])),reverse=True)
        if len(resolutions)<2:raise ValueError('Terrain requires nomination and at least one height resolution')
        spacing=terrain.get('center_spacing',64);local_spacing=terrain.get('refine_center_spacing',16)
        halo_cap=terrain.get('maximum_halo_expansions',2)
        if isinstance(halo_cap,bool) or not isinstance(halo_cap,int) or halo_cap<0:raise ValueError('maximum_halo_expansions must be a nonnegative integer')
        from .coastal import coastal_mode, monument_inputs
        coastal=coastal_mode(cfg)
        policies={v:{**(V1 if v=='v1' else V2),**terrain.get(v,cfg.get('variants',{}).get(v,{}))} for v in terrain.get('variants',('v1','v2'))}
        extents={v:p['diameter_max']+max(p['ideal_water_width'],p['water_width']) if v=='v1' else p['distance_max']+8*p['ridge_support_width'] for v,p in policies.items()}
        cache=RasterCache(terrain.get('cache_entries',32))
        summary=dict(candidates=0,results=0,resumed=0,resumed_tasks=0,work_completed=0,
                     durable_raster_hits=0,cache_hits=0,cache_misses=0,blocked_variants=0,pool_revision=revision)
        started=time.monotonic()
        if provider_factory is None:
            from ..backend import Backend, configure_native_threads
            configure_native_threads(terrain.get('native_threads',1))
            provider_factory=lambda seed:Backend(seed)
        provider_source=identity['sampling_provider'].get('declared',{})
        actual_provider=isinstance(provider_source,dict) and provider_source.get('source')=='actual'
        settings={'game':cfg.get('game',{}),'world_settings':cfg.get('world_settings',{})}
        worker=f'terrain-{__import__("os").getpid()}'
        cursor_key=f"terrain_pool_cursor:{revision}:{','.join(sorted(set(variants)))}"
        cursor=store.get_state(cursor_key)
        def eligible(unit):
            return unit['status'] in {'pending','deferred'} and (not unit['payload'].get('manual_continuation_required') or continue_deferred_halos)
        def pending(cid,variant):
            if scheduled is not None:
                current=store.get_terrain_work(scheduled['unit_id'])
                return iter([scheduled] if current['status']=='leased' and scheduled['candidate_id']==cid and scheduled['variant']==variant else [])
            return (u for u in store.iter_terrain_work(revision,candidate_id=cid,variant=variant) if eligible(u))
        def payload(stage,coarse,resolution,bounds,**extra):
            value=_terrain_work_payload(stage,coarse,resolution,bounds,**extra)
            if actual_provider:value['sampling_scope']=json.dumps({'revision':revision,'variant':extra.get('variant_scope'),'center':list(coarse),'stage':stage,'halo_level':value['halo_level']},sort_keys=True)
            return value
        mode=terrain.get('scheduler','rotation')
        if mode not in ('rotation','priority'):raise ValueError('Unknown terrain scheduler')
        def priority_pool():
            import uuid
            epoch=uuid.uuid4().hex
            members=iter(_rotating_terrain_pool(store,revision,cursor))
            exhausted=False
            while True:
                if budget==0 or limit is not None and summary['candidates']>=limit:return
                # Bounded ready window; all other members remain in the durable
                # frozen pool. Refill includes independent V1/V2 nominations.
                ready=store.db.execute("SELECT count(*) FROM terrain_work WHERE revision=? AND status IN ('pending','deferred')",(revision,)).fetchone()[0]
                if ready<128 and not exhausted:
                    for _ in range(64):
                        member=next(members,None)
                        if member is None:exhausted=True;break
                        mb=member['bounds'];mb=mb['overworld'] if isinstance(mb,dict) else mb
                        halo=math.ceil(max(extents.values())+resolutions[0]+local_spacing)
                        b=[mb[0]-halo,mb[1]-halo,mb[2]+halo,mb[3]+halo]
                        for v in variants:
                            if not next(store.iter_terrain_work(revision,candidate_id=member['id'],variant=v),None):
                                store.ensure_terrain_work(revision,member['id'],v,payload('nomination',member['stronghold'],resolutions[0],mb if coastal and v=='v1' else b,priority=100000.,variant_scope=v))
                unit=store.claim_priority_terrain(revision,variants,worker,epoch,continue_manual=continue_deferred_halos,max_refinements=budget)
                if unit is None:
                    if exhausted:return
                    # Ineligible/manual/failed tasks cannot prevent refill.
                    ready=0
                    member=next(members,None)
                    if member is None:exhausted=True;continue
                    mb=member['bounds'];mb=mb['overworld'] if isinstance(mb,dict) else mb
                    halo=math.ceil(max(extents.values())+resolutions[0]+local_spacing)
                    b=[mb[0]-halo,mb[1]-halo,mb[2]+halo,mb[3]+halo]
                    for v in variants:
                        if not next(store.iter_terrain_work(revision,candidate_id=member['id'],variant=v),None):
                            store.ensure_terrain_work(revision,member['id'],v,payload('nomination',member['stronghold'],resolutions[0],mb if coastal and v=='v1' else b,priority=100000.,variant_scope=v))
                    continue
                member=store.get_candidate(unit['candidate_id']);member['_scheduled_unit']=unit
                yield member
        candidates=priority_pool() if mode=='priority' else _rotating_terrain_pool(store,revision,cursor)
        scheduled=None
        def claim(unit):
            return unit if scheduled is not None and unit['unit_id']==scheduled['unit_id'] else store.claim_terrain_work(unit['unit_id'],worker)
        for candidate in candidates:
            scheduled=candidate.get('_scheduled_unit')
            if budget==0 or limit is not None and summary['candidates']>=limit:break
            if candidate.get('inventory', {}).get('tasks'):
                from .inventory import run_inventory
                run_inventory(store, cfg, candidate_id=candidate['id'], include_pending=True)
                candidate = {**candidate, **store.get_candidate(candidate['id'])}
            bounds=candidate['bounds'];bounds=tuple(bounds['overworld'] if isinstance(bounds,dict) else bounds)
            cid=candidate['id'];stronghold=candidate['stronghold'];seed=candidate['seed']
            nomination_halo=math.ceil(max(extents.values())+resolutions[0]+local_spacing)
            nomination_bounds=[bounds[0]-nomination_halo,bounds[1]-nomination_halo,bounds[2]+nomination_halo,bounds[3]+nomination_halo]
            for variant in variants:
                # Insert once; completed nomination units retain the original proposal queue.
                if not next(iter(store.iter_terrain_work(revision,candidate_id=cid,variant=variant)),None):
                    store.ensure_terrain_work(revision,cid,variant,payload('nomination',stronghold,resolutions[0],bounds if coastal and variant=='v1' else nomination_bounds,priority=100000.,variant_scope=variant))
            active=[v for v in variants if next(pending(cid,v),None)]
            summary['resumed_tasks']+=sum(store.terrain_work_complete(revision,cid,v) for v in variants if v not in active)
            summary['blocked_variants']+=sum(not store.terrain_work_complete(revision,cid,v) for v in variants if v not in active)
            if not active:continue
            provider=None;did_work=False
            def sample(unit):
                nonlocal provider
                saved=store.get_observation(unit['sampling_key'])
                if saved and saved.get('metadata',{}).get('source')=='prediction':
                    decoded=_decode_terrain_raster(saved)
                    if _terrain_sampling_retry_reason(decoded) is None:
                        summary['durable_raster_hits']+=1
                        return decoded,None
                if provider is None:provider=provider_factory(seed)
                item=unit['payload']
                raster=cache.sample(provider,seed,item['raster_bounds'],item['resolution'],
                                    stage='nomination' if item['stage']=='nomination' else 'height',settings=settings)
                if raster.metadata.get('source')=='actual' and not actual_provider:
                    raise ValueError("Persistent actual terrain factories must declare provider_identity source='actual'; actual snapshots cannot share prediction cache keys")
                observation=_encode_terrain_raster(raster,unit)
                return raster,observation
            try:
                for variant in active:
                    evaluate=evaluate_v1 if variant=='v1' else evaluate_v2
                    options=dict(thresholds=policies[variant],rays=terrain.get('rays',32))
                    fixed=coastal and variant=='v1'
                    if fixed:
                        options['monuments']=monument_inputs(candidate)
                        if cfg.get('screening_revision'):options['require_monument']=candidate.get('marine_stage',{}).get('status')!='DEFERRED'
                    initial=next((u for u in pending(cid,variant) if u['payload']['stage']=='nomination'),None)
                    if initial:
                        unit=claim(initial)
                        store.set_state(cursor_key,cid)
                        raster,observation=sample(unit)
                        proposals=[];successors=[]
                        retry_reason=_terrain_sampling_retry_reason(raster)
                        centers=([tuple(stronghold)] if fixed else propose_centers(raster,bounds,variant,spacing) if retry_reason is None else [(x,z) for z in range(bounds[1],bounds[3],spacing) for x in range(bounds[0],bounds[2],spacing)])
                        for center in centers:
                            coarse=evaluate(raster,center,bounds,stronghold,**options)
                            proposals.append(coarse)
                            radius=math.ceil(max(extents.values())+2*resolutions[1]+local_spacing)
                            x,z=center;local=[x-radius,z-radius,x+radius+1,z+radius+1]
                            nearby=[[x+dx,z+dz] for dx in (-local_spacing,0,local_spacing) for dz in (-local_spacing,0,local_spacing)
                                    if bounds[0]<=x+dx<bounds[2] and bounds[1]<=z+dz<bounds[3]]
                            if fixed:local=list(bounds);nearby=[list(stronghold)]
                            successors.append(dict(candidate_id=cid,variant=variant,payload=payload('height',center,resolutions[1],local,
                                center=list(center),nearby_centers=nearby,coarse_score=coarse['geometry_score'],priority=coarse['geometry_score'],variant_scope=variant)))
                        if retry_reason:
                            for result in proposals:
                                result.update(qualification='PENDING',evidence='PARTIAL')
                                result['pending_work'].append(retry_reason)
                                apply_score_policy(result,cfg.get('scoring',{}),source=raster.metadata.get('source','unknown'),
                                                   component_status={'geometry':'PARTIAL','biome_fit':'UNKNOWN','baseline_quality':'UNKNOWN'})
                            nearest=max(proposals,key=lambda r:r['geometry_score']) if proposals else None
                            if nearest:_preserve_actual_variant(store,cid,variant,nearest)
                            variants_saved=[] if nearest is None else [dict(candidate_id=cid,variant=variant,center=nearest['center'],result=nearest)]
                            persist(store.defer_terrain_work,unit,result={'proposals':proposals,'sampling_failure':retry_reason},
                                observation=_retry_terrain_observation(observation,unit),variant_results=variants_saved,expected_attempt=unit['attempts'],worker=worker)
                            did_work=True
                            store.set_state(cursor_key,cid)
                            continue
                        persist(store.complete_terrain_work,unit,result={'proposals':proposals},successor_units=successors,observation=observation)
                        summary['work_completed']+=1;did_work=True
                        store.set_state(cursor_key,cid)
                    processed=set();deferred_first=True
                    while len(processed)<budget:
                        units=(u for u in pending(cid,variant) if tuple(u['payload']['coarse_center']) not in processed)
                        unit=None
                        if deferred_first:
                            unit=next((u for u in units if u['status']=='deferred'),None)
                            deferred_first=False
                        if unit is None:unit=next((u for u in pending(cid,variant) if tuple(u['payload']['coarse_center']) not in processed),None)
                        if unit is None:break
                        coarse_center=tuple(unit['payload']['coarse_center']);processed.add(coarse_center)
                        while unit:
                            unit=claim(unit)
                            store.set_state(cursor_key,cid)
                            item=unit['payload'];raster,observation=sample(unit)
                            from .biomes import raster_variant_fit
                            fit,fit_status,fit_provenance=raster_variant_fit(raster,variant,target_version=cfg.get('game',{}).get('target_version','26.52'))
                            quality=candidate.get('baseline_score')
                            if quality is None:quality=candidate.get('baseline_score_observed',0)
                            quality=quality.get('normalized',quality.get('quality',0)) if isinstance(quality,dict) else 100.*float(quality or 0)/cfg.get('scoring',{}).get('baseline_quality_cap',60)
                            results=[evaluate(raster,c,bounds,stronghold,biome_fit=fit,baseline_quality=min(100.,max(0.,float(quality or 0))),**options)
                                     for c in item.get('nearby_centers',[item.get('center',coarse_center)])]
                            result=max(results,key=lambda r:r['geometry_score']);center=result['center'];result['biome_fit_provenance']=fit_provenance
                            marine_update=None
                            if fixed and cfg.get('screening_revision') and item['resolution']==min(resolutions):
                                from .marine import evaluate_marine_stage
                                result,marine_update=evaluate_marine_stage(candidate,cfg,raster,result)
                                if marine_update:
                                    options['monuments']=marine_update['required_structures']['monument']['predicted_viable']
                                    options['require_monument']=True
                                    results=[result]

                            apply_score_policy(result,cfg.get('scoring',{}),source=raster.metadata.get('source','prediction'),biome_fit=fit,
                                               component_status={'geometry':result['evidence'],'biome_fit':fit_status,'baseline_quality':candidate.get('qualification','PENDING')})
                            result['sampling_schedule']={'nomination_resolution':resolutions[0],'last_height_resolution':item['resolution'],
                                'coarse_center':list(coarse_center),'halo_level':item['halo_level'],'independent_refinement_budget':budget,'work_unit_id':unit['unit_id'],'pool_revision':revision}
                            retry_reason=_terrain_sampling_retry_reason(raster)
                            if retry_reason:
                                result.update(qualification='PENDING',evidence='PARTIAL')
                                result['pending_work'].append(retry_reason)
                                apply_score_policy(result,cfg.get('scoring',{}),source=raster.metadata.get('source','unknown'),biome_fit=fit,
                                                   component_status={'geometry':'PARTIAL','biome_fit':fit_status,'baseline_quality':candidate.get('qualification','PENDING')})
                                _preserve_actual_variant(store,cid,variant,result)
                                persist(store.defer_terrain_work,unit,result={'best':result,'evaluated_centers':results,'sampling_failure':retry_reason},
                                    variant_results=[dict(candidate_id=cid,variant=variant,center=center,result=result)],observation=_retry_terrain_observation(observation,unit),expected_attempt=unit['attempts'],worker=worker)
                                did_work=True;summary['results']+=1
                                store.set_state(cursor_key,cid)
                                break
                            successor=None;successor_status='pending';continue_chain=False
                            remaining=[r for r in resolutions[1:] if r<item['resolution']]
                            low=item['resolution']<=32 and result['geometry_score']<terrain.get('fine_refinement_score',40)
                            if remaining and item['stage']=='height':
                                resolution=remaining[0];radius=math.ceil(max(extents.values())+2*resolution+local_spacing)
                                x,z=coarse_center;local=[x-radius,z-radius,x+radius+1,z+radius+1]
                                if fixed:local=list(bounds)
                                successor=payload('height',coarse_center,resolution,local,center=center,nearby_centers=[center],
                                                  priority=item.get('coarse_score',0),coarse_score=item.get('coarse_score',0),variant_scope=variant)
                                if low:
                                    successor_status='deferred';successor['pending_reason']='below fine scheduling threshold; finer geometry remains unevaluated'
                                    result['pending_work'].append(successor['pending_reason'])
                                else:continue_chain=True
                            elif not fixed and (result['qualification']=='PENDING' or result['geometry_pass'] and not result['border_fit']['complete']):
                                level=item['halo_level']+1;x,z=coarse_center
                                radius=math.ceil(max(extents.values())+2*item['resolution']+local_spacing)*2**level
                                local=[x-radius,z-radius,x+radius+1,z+radius+1]
                                successor=payload('halo',coarse_center,item['resolution'],local,center=center,nearby_centers=[center],halo_level=level,
                                                  priority=item.get('coarse_score',0),coarse_score=item.get('coarse_score',0),variant_scope=variant,
                                                  manual_continuation_required=level>halo_cap,needed_bounds=local,
                                                  pending_reason='formation coverage/connectivity unresolved; expand local halo')
                                successor_status='deferred';result['pending_work'].append(successor['pending_reason'])
                                if level>halo_cap:result['pending_work'].append('automatic halo expansion cap reached; explicit continuation required')
                            successors=[] if successor is None else [dict(candidate_id=cid,variant=variant,payload=successor,status=successor_status)]
                            _preserve_actual_variant(store,cid,variant,result)
                            persist(store.complete_terrain_work,unit,result={'best':result,'evaluated_centers':results},successor_units=successors,
                                variant_results=[dict(candidate_id=cid,variant=variant,center=center,result=result)],observation=observation,
                                **({'candidate_update':marine_update} if marine_update else {}))
                            if marine_update:candidate={**candidate,**marine_update}
                            summary['work_completed']+=1;summary['results']+=1;did_work=True
                            store.set_state(cursor_key,cid)
                            if progress:progress(dict(summary,seed=seed,variant=variant,work_status=store.terrain_work_counts(revision),elapsed_seconds=time.monotonic()-started))
                            unit=store.get_terrain_work(store.ensure_terrain_work(revision,cid,variant,successor,status=successor_status)) if successor and continue_chain and scheduled is None else None
                        if scheduled is not None:break
                    if store.terrain_work_complete(revision,cid,variant):store.set_variant_task_status(cid,variant,'complete',pool_revision=revision)
                    else:store.set_variant_task_status(cid,variant,'started',pool_revision=revision)
                if did_work:
                    summary['candidates']+=1
                    if progress:progress(dict(summary,seed=seed,work_status=store.terrain_work_counts(revision),elapsed_seconds=time.monotonic()-started))
            except CapacityBlocked:
                summary['candidates']+=1
            finally:
                if provider is not None and hasattr(provider,'close'):provider.close()
            if summary.get('resource_blocked'):break
        saved_counts=store.terrain_work_counts(revision)
        counts={status:saved_counts.get(status,0) for status in ('pending','deferred','leased','complete')}
        all_uninitialized=store.terrain_pool_uninitialized_counts(revision)
        uninitialized={v:all_uninitialized.get(v,0) for v in terrain.get('variants',('v1','v2'))}
        summary.update(pool_uninitialized_by_variant=uninitialized,uninitialized_variant_tasks=sum(uninitialized.values()),
                       requested_uninitialized_variant_tasks=sum(uninitialized[v] for v in set(variants)),
                       pool_cursor=store.get_state(cursor_key),work_status=counts,pending_work=counts.get('pending',0),deferred_work=counts.get('deferred',0),cache_hits=cache.hits,
                       cache_misses=cache.misses,elapsed_seconds=time.monotonic()-started)
        return summary
    finally:
        fcntl.flock(lock.fileno(),fcntl.LOCK_UN);lock.close()


def run_terrain(store,cfg,variants=None,limit=None,resume=True,progress=None,*,provider_factory=None,provider_identity=None,
                pool_revision=None,new_pool_revision=False,continue_deferred_halos=False):
    """Resume active center/stage queues against one fixed baseline membership."""
    active=tuple(cfg.get('terrain',{}).get('variants',('v1','v2')))
    variants=active if variants is None else tuple(variants)
    if any(v not in active for v in variants):raise ValueError('Requested terrain variant is inactive in this saved configuration')
    if any(v not in {'v1','v2'} for v in variants):raise ValueError('Realm variants are v1 and v2')
    if limit is not None and limit<0:raise ValueError('Limit must be nonnegative')
    if hasattr(store,'ensure_terrain_work'):
        return _run_terrain_durable(store,cfg,variants,limit,resume,progress,provider_factory,provider_identity,
                                    pool_revision,new_pool_revision,continue_deferred_halos)
    return _run_terrain_legacy(store,cfg,variants,limit,resume,progress,provider_factory=provider_factory,provider_identity=provider_identity)
